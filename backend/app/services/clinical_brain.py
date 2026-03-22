"""
Swarm 3 — ClinicalBrain: RAG retrieval over the medical knowledge base.

Unlike other swarms this agent does **not** inherit from ``SwarmBase``
because it performs embedding + vector search rather than LLM chat
completion.  It uses OpenAI ``text-embedding-3-small`` for embeddings
and Supabase pgvector (via the ``match_documents`` RPC) for similarity
search.

Swarm index: 3
Config key:  ``swarm_3_clinical_brain``
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.database import get_supabase_admin as get_supabase_client
from app.core.logging_config import get_logger
from app.core.metrics import observe_chat_latency, record_swarm_error
from app.core.model_config import SWARM_CONFIG, get_swarm_config
from app.core.timeouts import EMBEDDING_TIMEOUT, with_timeout

logger = get_logger(__name__)

_SWARM_ID = "swarm_3_clinical_brain"


# ── Data classes ──────────────────────────────────────────────────────────


@dataclass
class RAGMatch:
    """A single document matched by vector similarity search.

    Attributes:
        id:         Document identifier from the knowledge base.
        content:    The document text chunk.
        metadata:   Arbitrary metadata attached to the document row.
        similarity: Cosine similarity score (0.0 – 1.0).
    """

    id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    similarity: float = 0.0


@dataclass
class RAGResult:
    """Aggregated result from a multi-query RAG search.

    Attributes:
        matches:           Deduplicated, score-boosted document matches
                           sorted by descending similarity (max 5).
        degradation_level: Quality indicator from 0 (excellent) to 4
                           (no results).

                           - 0: >= 5 matches with similarity > 0.7
                           - 1: >= 3 matches with similarity > 0.6
                           - 2: >= 1 match  with similarity > 0.5
                           - 3: matches found but all below threshold
                           - 4: no matches at all
        message:           Human-readable quality summary.
    """

    matches: list[RAGMatch] = field(default_factory=list)
    degradation_level: int = 4
    message: str = "No results found."


# ── ClinicalBrain ─────────────────────────────────────────────────────────


class ClinicalBrain:
    """RAG retrieval agent for the Izana medical knowledge base.

    This agent generates embeddings for one or more search queries,
    issues parallel vector-similarity searches against Supabase
    pgvector, and returns a deduplicated, score-boosted set of the
    top-matching document chunks.

    Performance note (A6.2):
        Embedding calls are parallelised with ``asyncio.gather()`` to
        minimise wall-clock latency when multiple queries are provided.
    """

    swarm_id: str = _SWARM_ID

    def __init__(self) -> None:
        self._config: dict[str, Any] = get_swarm_config(_SWARM_ID)
        self._openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._supabase = get_supabase_client()

        # Pull tunables from config.
        self._embedding_model: str = self._config.get(
            "embedding_model", "text-embedding-3-small"
        )
        self._dimensions: int = self._config.get("embedding_dimensions", 384)
        self._match_threshold: float = self._config.get("match_threshold", 0.5)
        self._match_count: int = self._config.get("match_count", 10)

    # ── Public API ──────────────────────────────────────────────────────

    async def search(self, queries: list[str]) -> RAGResult:
        """Run a multi-query RAG search.

        For each query string an embedding is generated (in parallel)
        and a pgvector similarity search is executed.  Results are
        deduplicated across queries — documents found by multiple
        queries receive a +0.1 score boost per additional hit.  The
        final list is sorted by descending similarity and capped at 5.

        Args:
            queries: One or more natural-language search queries.

        Returns:
            A ``RAGResult`` containing the top matches and a
            degradation level indicating result quality.
        """
        if not queries:
            return RAGResult(
                matches=[],
                degradation_level=4,
                message="No queries provided.",
            )

        try:
            # A6.2: parallelise embedding generation.
            embeddings = await asyncio.gather(
                *(self._embed(q) for q in queries)
            )

            # Run vector searches (also in parallel).
            search_tasks = [
                self._vector_search(emb) for emb in embeddings
            ]
            all_results = await asyncio.gather(*search_tasks)

            # Deduplicate and boost.
            merged = self._deduplicate_and_boost(all_results)

            # Sort by similarity (descending) and take top 5.
            merged.sort(key=lambda m: m.similarity, reverse=True)
            top = merged[:5]

            degradation, message = self._assess_quality(top)

            logger.info(
                "ClinicalBrain search completed",
                extra={
                    "swarm_id": self.swarm_id,
                    "num_queries": len(queries),
                    "num_results": len(top),
                    "degradation_level": degradation,
                },
            )

            return RAGResult(
                matches=top,
                degradation_level=degradation,
                message=message,
            )

        except Exception as exc:
            record_swarm_error(self.swarm_id, type(exc).__name__)
            logger.error(
                "ClinicalBrain search failed",
                extra={
                    "swarm_id": self.swarm_id,
                    "error": str(exc),
                },
            )
            return RAGResult(
                matches=[],
                degradation_level=4,
                message=f"Search failed: {exc}",
            )

    # ── Internal methods ────────────────────────────────────────────────

    async def _embed(self, text: str) -> list[float]:
        """Generate an embedding vector for *text*.

        Uses OpenAI ``text-embedding-3-small`` with 384 dimensions as
        specified in the swarm config.

        Args:
            text: The text to embed.

        Returns:
            A list of floats with length equal to ``_dimensions``.

        Raises:
            AssertionError: If the returned embedding has an unexpected
                            number of dimensions.
        """
        async with with_timeout(EMBEDDING_TIMEOUT, "clinical_brain_embedding"):
            response = await self._openai.embeddings.create(
                model=self._embedding_model,
                input=text,
                dimensions=self._dimensions,
            )

        embedding = response.data[0].embedding
        assert len(embedding) == self._dimensions, (
            f"Expected {self._dimensions} dimensions, got {len(embedding)}"
        )
        return embedding

    async def _vector_search(
        self, embedding: list[float]
    ) -> list[RAGMatch]:
        """Execute a pgvector similarity search via the Supabase RPC.

        Calls the ``match_documents`` database function which is
        expected to accept ``query_embedding``, ``match_threshold``,
        and ``match_count`` parameters.

        Args:
            embedding: The query embedding vector.

        Returns:
            A list of ``RAGMatch`` objects from the search results.
        """
        try:
            response = self._supabase.rpc(
                "match_documents",
                {
                    "query_embedding": embedding,
                    "match_threshold": self._match_threshold,
                    "match_count": self._match_count,
                },
            ).execute()

            matches: list[RAGMatch] = []
            for row in response.data or []:
                matches.append(
                    RAGMatch(
                        id=str(row.get("id", "")),
                        content=row.get("content", ""),
                        metadata=row.get("metadata") or {},
                        similarity=float(row.get("similarity", 0.0)),
                    )
                )
            return matches

        except Exception as exc:
            logger.warning(
                "Vector search failed",
                extra={
                    "swarm_id": self.swarm_id,
                    "error": str(exc),
                },
            )
            return []

    @staticmethod
    def _deduplicate_and_boost(
        result_sets: list[list[RAGMatch]],
    ) -> list[RAGMatch]:
        """Merge multiple result sets, deduplicating by document ID.

        Documents that appear in more than one result set receive a
        +0.1 similarity boost for each additional occurrence, rewarding
        documents that are relevant across multiple query angles.

        Args:
            result_sets: A list of match lists, one per query.

        Returns:
            A single deduplicated list of ``RAGMatch`` objects with
            boosted scores.
        """
        seen: dict[str, RAGMatch] = {}
        hit_counts: dict[str, int] = {}

        for matches in result_sets:
            for match in matches:
                doc_id = match.id
                if doc_id in seen:
                    hit_counts[doc_id] += 1
                    # Keep the higher base similarity.
                    if match.similarity > seen[doc_id].similarity:
                        seen[doc_id] = match
                else:
                    seen[doc_id] = match
                    hit_counts[doc_id] = 1

        # Apply score boost for multi-query hits.
        for doc_id, match in seen.items():
            extra_hits = hit_counts[doc_id] - 1
            if extra_hits > 0:
                match.similarity = min(1.0, match.similarity + 0.1 * extra_hits)

        return list(seen.values())

    @staticmethod
    def _assess_quality(
        matches: list[RAGMatch],
    ) -> tuple[int, str]:
        """Determine the degradation level for a set of matches.

        Args:
            matches: The final top-N matches after deduplication.

        Returns:
            A ``(degradation_level, message)`` tuple.
        """
        if not matches:
            return 4, "No matching documents found."

        high_quality = [m for m in matches if m.similarity > 0.7]
        medium_quality = [m for m in matches if m.similarity > 0.6]
        any_above_threshold = [m for m in matches if m.similarity > 0.5]

        if len(high_quality) >= 5:
            return 0, "Excellent match quality."
        if len(medium_quality) >= 3:
            return 1, "Good match quality."
        if len(any_above_threshold) >= 1:
            return 2, "Partial match — some relevant documents found."
        return 3, "Low confidence — matches found but below quality threshold."
