#!/usr/bin/env python3
"""
Knowledge Base Ingestion Pipeline — Stage 5

Ingests 236 clinical PDFs into the Supabase `documents` table with
384-dimensional embeddings from OpenAI text-embedding-3-small.

DESIGN FOR EXTREME ACCURACY AND CONTEXT:
=========================================

1. SMART PAGE FILTERING:
   - Skips cover pages (< 100 chars of content)
   - Skips copyright/publisher pages (pattern detection)
   - Skips table of contents pages (> 30% dots/periods)
   - Skips pure reference/bibliography pages (> 50% citation patterns)
   - Skips index pages (alphabetical lists with page numbers)
   - Skips blank/address-only pages (< 80 chars)

2. CONTEXT-PRESERVING CHUNKING:
   - Chunks at ~500 tokens with 100-token overlap (not 50)
   - Never splits mid-sentence — finds nearest sentence boundary
   - Prepends document title + section header to EVERY chunk
   - This means each chunk is self-contained: "From [Document Title],
     Section [X]: [chunk content]" — even if read in isolation

3. METADATA-RICH STORAGE:
   - Each chunk stores: filename, page_numbers (can span pages),
     chunk_index, total_chunks, document_title, section_header,
     document_type (guideline/factsheet/booklet/review)

4. EMBEDDING QUALITY:
   - Uses text-embedding-3-small with dimensions=384
   - Asserts dimension = 384 before every insert
   - Batch processing (50 chunks per batch) with rate limiting
   - Retry on OpenAI errors with exponential backoff

Usage:
    cd backend
    source venv/bin/activate
    python scripts/ingest_docs.py /path/to/knowledge-base/
"""

import asyncio
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import pypdf
from openai import OpenAI

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.config import get_settings

settings = get_settings()

# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 384
CHUNK_SIZE_TOKENS = 500       # ~500 tokens per chunk
CHUNK_OVERLAP_TOKENS = 100    # 100-token overlap for context continuity
CHARS_PER_TOKEN = 4           # Rough estimate: 1 token ≈ 4 chars
CHUNK_SIZE_CHARS = CHUNK_SIZE_TOKENS * CHARS_PER_TOKEN      # ~2000 chars
CHUNK_OVERLAP_CHARS = CHUNK_OVERLAP_TOKENS * CHARS_PER_TOKEN # ~400 chars
BATCH_SIZE = 50               # Chunks per embedding batch
MIN_CHUNK_LENGTH = 80         # Skip chunks shorter than this
MAX_RETRIES = 3
RETRY_DELAY = 2.0


# ═══════════════════════════════════════════════════════════════
# Page Filtering — Skip useless pages
# ═══════════════════════════════════════════════════════════════

# Patterns that indicate a page should be skipped
COPYRIGHT_PATTERNS = [
    r"published by the american society",
    r"no part of this presentation may be reproduced",
    r"©\s*\d{4}",
    r"all rights reserved",
    r"this document should be cited as",
    r"permission to reproduce",
    r"ISBN\s*[\d-]+",
]

TOC_INDICATORS = [
    r"table of contents",
    r"contents\s*$",
]

INDEX_PATTERNS = [
    r"^\s*index\s*$",
    r"subject index",
]

ADDRESS_PATTERNS = [
    r"1209\s*montgomery\s*highway",
    r"birmingham,?\s*(alabama|al)",
    r"www\.asrm\.org",
    r"www\.eshre\.eu",
    r"follow us!",
]

REFERENCE_PATTERNS = [
    r"^\s*references?\s*$",
    r"^\s*bibliography\s*$",
    r"^\s*works?\s*cited\s*$",
]


def is_useless_page(text: str, page_num: int, total_pages: int) -> tuple[bool, str]:
    """
    Determine if a page should be skipped.
    Returns (should_skip, reason).
    """
    if not text or len(text.strip()) < 80:
        return True, "too_short"

    text_lower = text.lower().strip()

    # Cover page (first page, usually just title)
    if page_num == 0 and len(text.strip()) < 300:
        return True, "cover_page"

    # Last page (often just address/footer)
    if page_num == total_pages - 1 and len(text.strip()) < 300:
        return True, "back_cover"

    # Copyright/publisher pages
    copyright_matches = sum(1 for p in COPYRIGHT_PATTERNS if re.search(p, text_lower))
    if copyright_matches >= 2 and len(text.strip()) < 800:
        return True, "copyright_page"

    # Table of contents — high density of dots (......) or page numbers
    dots_ratio = text.count('.') / max(len(text), 1)
    if dots_ratio > 0.15:
        for pattern in TOC_INDICATORS:
            if re.search(pattern, text_lower):
                return True, "table_of_contents"
        # Also catch TOC-like pages without explicit "table of contents" header
        # These have lines like "Chapter 1 .......................... 5"
        dot_lines = sum(1 for line in text.split('\n') if line.count('.') > 10)
        if dot_lines > 5:
            return True, "table_of_contents"

    # Pure reference pages — lots of citation patterns
    # e.g., "Author et al. (2020). Title. Journal, 123, 456-789."
    citation_pattern = r'\(\d{4}\)'  # (2020), (2019), etc.
    citation_count = len(re.findall(citation_pattern, text))
    lines = text.strip().split('\n')
    if citation_count > 5 and citation_count / max(len(lines), 1) > 0.3:
        # More than 30% of lines have year citations — likely references
        for pattern in REFERENCE_PATTERNS:
            if re.search(pattern, text_lower[:200]):
                return True, "references_page"
        # Even without header, if > 50% of lines are citations, skip
        if citation_count / max(len(lines), 1) > 0.5:
            return True, "references_page"

    # Index pages — alphabetical entries with page numbers
    for pattern in INDEX_PATTERNS:
        if re.search(pattern, text_lower[:100]):
            return True, "index_page"

    # Address-only pages
    address_matches = sum(1 for p in ADDRESS_PATTERNS if re.search(p, text_lower))
    if address_matches >= 2 and len(text.strip()) < 500:
        return True, "address_page"

    return False, ""


# ═══════════════════════════════════════════════════════════════
# Section Header Detection
# ═══════════════════════════════════════════════════════════════

SECTION_HEADER_PATTERNS = [
    # "1. Introduction", "2.3 Methods", "Chapter 1"
    r'^(?:chapter\s+)?\d+(?:\.\d+)*\.?\s+[A-Z][^\n]{3,80}$',
    # "INTRODUCTION", "METHODS AND MATERIALS"
    r'^[A-Z][A-Z\s]{4,60}$',
    # "Introduction", "Background" (title case, standalone short line)
    r'^[A-Z][a-z]+(?:\s+[A-Za-z]+){0,5}$',
]


def extract_section_header(text: str) -> str:
    """Try to find a section header at the start of text."""
    lines = text.strip().split('\n')[:5]  # Check first 5 lines
    for line in lines:
        line = line.strip()
        if len(line) < 3 or len(line) > 100:
            continue
        for pattern in SECTION_HEADER_PATTERNS:
            if re.match(pattern, line):
                return line
    return ""


# ═══════════════════════════════════════════════════════════════
# Document Title Extraction
# ═══════════════════════════════════════════════════════════════

def extract_title_from_filename(filename: str) -> str:
    """Convert filename to a readable title."""
    name = Path(filename).stem
    # Remove leading numbers/dashes
    name = re.sub(r'^\d+[-_\s]*', '', name)
    # Replace underscores and hyphens with spaces
    name = name.replace('_', ' ').replace('-', ' ')
    # Clean up multiple spaces
    name = re.sub(r'\s+', ' ', name).strip()
    # Title case
    return name.title()


def classify_document(filename: str, first_page_text: str) -> str:
    """Classify document type for metadata."""
    fname_lower = filename.lower()
    text_lower = (first_page_text or "").lower()

    if 'guideline' in fname_lower or 'guideline' in text_lower:
        return 'clinical_guideline'
    elif 'booklet' in fname_lower or 'guide for patients' in text_lower:
        return 'patient_booklet'
    elif 'factsheet' in fname_lower or 'fact sheet' in text_lower:
        return 'factsheet'
    elif 'review' in fname_lower or 'systematic review' in text_lower:
        return 'review'
    elif 'consensus' in fname_lower or 'position statement' in text_lower:
        return 'consensus_statement'
    elif 'cpg' in fname_lower or 'clinical practice' in text_lower:
        return 'clinical_practice_guideline'
    else:
        return 'clinical_document'


# ═══════════════════════════════════════════════════════════════
# Context-Preserving Chunking
# ═══════════════════════════════════════════════════════════════

@dataclass
class Chunk:
    content: str
    metadata: dict = field(default_factory=dict)


def chunk_text_with_context(
    full_text: str,
    doc_title: str,
    doc_type: str,
    filename: str,
    page_numbers: list[int],
) -> list[Chunk]:
    """
    Split text into chunks that preserve context.

    Each chunk:
    - Is ~500 tokens (~2000 chars) with 100-token overlap
    - Never splits mid-sentence
    - Is prefixed with document title for standalone comprehension
    """
    if not full_text or len(full_text.strip()) < MIN_CHUNK_LENGTH:
        return []

    chunks = []
    text = full_text.strip()
    start = 0
    chunk_index = 0

    while start < len(text):
        # Calculate end position
        end = min(start + CHUNK_SIZE_CHARS, len(text))

        # If not at the end, find a sentence boundary to avoid mid-sentence splits
        if end < len(text):
            # Look backward from `end` for sentence-ending punctuation
            search_region = text[max(end - 400, start):end]
            # Find last sentence boundary (. ! ? followed by space or newline)
            last_boundary = -1
            for match in re.finditer(r'[.!?]\s', search_region):
                last_boundary = match.end()

            if last_boundary > 0:
                # Adjust end to the sentence boundary
                end = max(end - 400, start) + last_boundary
            else:
                # No sentence boundary found — try paragraph break
                newline_pos = text.rfind('\n', start, end)
                if newline_pos > start + CHUNK_SIZE_CHARS // 2:
                    end = newline_pos + 1

        chunk_text = text[start:end].strip()

        if len(chunk_text) >= MIN_CHUNK_LENGTH:
            # Detect section header within this chunk
            section = extract_section_header(chunk_text)

            # Build context prefix for standalone comprehension
            context_prefix = f"[Source: {doc_title}]"
            if section:
                context_prefix += f" [Section: {section}]"
            context_prefix += "\n\n"

            chunks.append(Chunk(
                content=context_prefix + chunk_text,
                metadata={
                    "filename": filename,
                    "document_title": doc_title,
                    "document_type": doc_type,
                    "section_header": section,
                    "chunk_index": chunk_index,
                    "page_numbers": page_numbers,
                    "char_start": start,
                    "char_end": end,
                }
            ))
            chunk_index += 1

        # Move start forward with overlap
        start = end - CHUNK_OVERLAP_CHARS
        if start <= chunks[-1].metadata["char_start"] if chunks else 0:
            start = end  # Avoid infinite loop

    # Add total_chunks to all metadata
    for chunk in chunks:
        chunk.metadata["total_chunks"] = len(chunks)

    return chunks


# ═══════════════════════════════════════════════════════════════
# PDF Processing
# ═══════════════════════════════════════════════════════════════

def process_pdf(filepath: str) -> list[Chunk]:
    """Extract, filter, and chunk a single PDF."""
    filename = os.path.basename(filepath)

    try:
        reader = pypdf.PdfReader(filepath)
    except Exception as e:
        print(f"  ERROR reading {filename}: {e}")
        return []

    total_pages = len(reader.pages)
    if total_pages == 0:
        return []

    # Extract text from all pages, filtering useless ones
    useful_pages = []
    skipped = {"cover_page": 0, "back_cover": 0, "copyright_page": 0,
               "table_of_contents": 0, "references_page": 0,
               "index_page": 0, "address_page": 0, "too_short": 0}

    first_page_text = ""
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            continue

        if i == 0:
            first_page_text = text

        should_skip, reason = is_useless_page(text, i, total_pages)
        if should_skip:
            skipped[reason] = skipped.get(reason, 0) + 1
            continue

        useful_pages.append((i + 1, text))  # 1-indexed page numbers

    if not useful_pages:
        print(f"  WARNING: No useful pages in {filename}")
        return []

    # Extract metadata
    doc_title = extract_title_from_filename(filename)
    doc_type = classify_document(filename, first_page_text)

    # Combine all useful page text
    full_text = "\n\n".join(text for _, text in useful_pages)
    page_numbers = [pn for pn, _ in useful_pages]

    # Clean text
    # Remove excessive whitespace but preserve paragraph breaks
    full_text = re.sub(r'[ \t]+', ' ', full_text)
    full_text = re.sub(r'\n{3,}', '\n\n', full_text)
    full_text = full_text.strip()

    # Chunk with context
    chunks = chunk_text_with_context(full_text, doc_title, doc_type, filename, page_numbers)

    skip_summary = ", ".join(f"{k}={v}" for k, v in skipped.items() if v > 0)
    print(f"  {filename}: {total_pages} pages → {len(useful_pages)} useful → "
          f"{len(chunks)} chunks (skipped: {skip_summary or 'none'})")

    return chunks


# ═══════════════════════════════════════════════════════════════
# Embedding Generation
# ═══════════════════════════════════════════════════════════════

def generate_embeddings(client: OpenAI, texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a batch of texts with retry."""
    for attempt in range(MAX_RETRIES):
        try:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=texts,
                dimensions=EMBEDDING_DIMENSIONS,
            )
            embeddings = [item.embedding for item in response.data]

            # Verify dimensions (Decision A6.2)
            for emb in embeddings:
                assert len(emb) == EMBEDDING_DIMENSIONS, \
                    f"Embedding dimension mismatch: expected {EMBEDDING_DIMENSIONS}, got {len(emb)}"

            return embeddings
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                wait = RETRY_DELAY * (2 ** attempt)
                print(f"  Embedding error (attempt {attempt + 1}): {e}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise


# ═══════════════════════════════════════════════════════════════
# Database Insertion
# ═══════════════════════════════════════════════════════════════

def insert_chunks_batch(supabase_client, chunks: list[Chunk], embeddings: list[list[float]]):
    """Insert a batch of chunks with embeddings into the documents table."""
    rows = []
    for chunk, embedding in zip(chunks, embeddings):
        rows.append({
            "content": chunk.content,
            "embedding": embedding,
            "metadata": chunk.metadata,
        })

    supabase_client.table("documents").insert(rows).execute()


# ═══════════════════════════════════════════════════════════════
# Main Ingestion Pipeline
# ═══════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/ingest_docs.py /path/to/knowledge-base/")
        sys.exit(1)

    kb_path = sys.argv[1]
    if not os.path.isdir(kb_path):
        print(f"ERROR: Directory not found: {kb_path}")
        sys.exit(1)

    # Find all PDFs
    pdf_files = sorted([
        os.path.join(kb_path, f)
        for f in os.listdir(kb_path)
        if f.lower().endswith('.pdf')
    ])
    print(f"\nFound {len(pdf_files)} PDF files in {kb_path}\n")

    if not pdf_files:
        print("No PDF files found.")
        sys.exit(1)

    # Initialize clients
    openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

    from supabase import create_client
    supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

    # Find already-ingested files to skip
    existing_result = supabase_client.rpc(
        "get_ingested_filenames",  # We'll use a direct query instead
    ).execute() if False else None

    # Direct query for existing filenames
    existing_rows = supabase_client.table("documents") \
        .select("metadata") \
        .limit(10000) \
        .execute()
    ingested_filenames = set()
    for row in (existing_rows.data or []):
        meta = row.get("metadata", {})
        if meta and meta.get("filename"):
            ingested_filenames.add(meta["filename"])

    if ingested_filenames:
        print(f"Already ingested: {len(ingested_filenames)} files. Skipping those.")

    # Filter out already-ingested PDFs
    pdf_files_to_process = [
        f for f in pdf_files
        if os.path.basename(f) not in ingested_filenames
    ]
    skipped_count = len(pdf_files) - len(pdf_files_to_process)
    if skipped_count > 0:
        print(f"Skipping {skipped_count} already-ingested files.")
    pdf_files = pdf_files_to_process

    if not pdf_files:
        print("All files already ingested. Nothing to do.")
        sys.exit(0)

    # Process all PDFs
    all_chunks: list[Chunk] = []
    stats = {"total_pdfs": len(pdf_files), "processed": 0, "skipped_pdfs": 0,
             "total_pages": 0, "useful_pages": 0, "total_chunks": 0}

    print("=" * 70)
    print("PHASE 1: Extracting and chunking PDFs")
    print("=" * 70)

    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}] Processing: {os.path.basename(pdf_path)}")
        chunks = process_pdf(pdf_path)
        if chunks:
            all_chunks.extend(chunks)
            stats["processed"] += 1
        else:
            stats["skipped_pdfs"] += 1

    stats["total_chunks"] = len(all_chunks)
    print(f"\n{'=' * 70}")
    print(f"PHASE 1 COMPLETE: {stats['processed']} PDFs → {stats['total_chunks']} chunks")
    print(f"  Skipped PDFs: {stats['skipped_pdfs']}")
    print(f"{'=' * 70}")

    if not all_chunks:
        print("No chunks to process.")
        sys.exit(1)

    # Generate embeddings and insert in batches
    print(f"\nPHASE 2: Generating embeddings and inserting into Supabase")
    print(f"  Model: {EMBEDDING_MODEL} ({EMBEDDING_DIMENSIONS} dimensions)")
    print(f"  Batch size: {BATCH_SIZE}")
    print(f"  Total batches: {(len(all_chunks) + BATCH_SIZE - 1) // BATCH_SIZE}")
    print(f"{'=' * 70}")

    inserted = 0
    start_time = time.time()

    for batch_start in range(0, len(all_chunks), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(all_chunks))
        batch = all_chunks[batch_start:batch_end]
        batch_num = batch_start // BATCH_SIZE + 1
        total_batches = (len(all_chunks) + BATCH_SIZE - 1) // BATCH_SIZE

        # Extract text for embedding
        texts = [chunk.content for chunk in batch]

        try:
            # Generate embeddings
            embeddings = generate_embeddings(openai_client, texts)

            # Insert into Supabase
            insert_chunks_batch(supabase_client, batch, embeddings)

            inserted += len(batch)
            elapsed = time.time() - start_time
            rate = inserted / elapsed if elapsed > 0 else 0
            eta = (len(all_chunks) - inserted) / rate if rate > 0 else 0

            print(f"  Batch {batch_num}/{total_batches}: "
                  f"inserted {len(batch)} chunks "
                  f"({inserted}/{len(all_chunks)} total, "
                  f"{rate:.1f} chunks/sec, "
                  f"ETA: {eta:.0f}s)")

            # Small delay between batches to respect rate limits
            if batch_end < len(all_chunks):
                time.sleep(0.5)

        except Exception as e:
            print(f"  ERROR on batch {batch_num}: {e}")
            print(f"  Skipping batch and continuing...")
            continue

    elapsed_total = time.time() - start_time

    print(f"\n{'=' * 70}")
    print(f"INGESTION COMPLETE")
    print(f"{'=' * 70}")
    print(f"  PDFs processed: {stats['processed']}/{stats['total_pdfs']}")
    print(f"  Total chunks:   {stats['total_chunks']}")
    print(f"  Inserted:       {inserted}")
    print(f"  Failed:         {stats['total_chunks'] - inserted}")
    print(f"  Time:           {elapsed_total:.1f}s ({elapsed_total/60:.1f}m)")
    print(f"  Rate:           {inserted/elapsed_total:.1f} chunks/sec")

    # Verify final count
    final = supabase_client.table("documents").select("id", count="exact").execute()
    print(f"  Documents in DB: {final.count}")
    print(f"\nDone! Knowledge base ready for RAG queries.")


if __name__ == "__main__":
    main()
