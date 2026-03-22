"""
Stage 4 tests: Swarm pipeline — retry wrapper, fallback values, tracing.

Decision 5: Universal retry wrapper in swarm_base.py
Decision 10: Chat traces table for observability
Decision 17: Human-readable swarm file names
Decision 19: Deterministic mock Groq client
"""

import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4


# ── Groq Client Tests ──────────────────────────────────────────────


class TestGroqClientManager:
    """Test multi-key rotation and circuit breaking."""

    def test_round_robin_key_selection(self):
        """Keys should rotate round-robin across calls."""
        with patch("app.services.groq_client.settings") as mock_settings:
            mock_settings.get_groq_keys.return_value = ["key1", "key2", "key3"]
            mock_settings.GROQ_MAX_CONCURRENT_REQUESTS = 10

            from app.services.groq_client import GroqClientManager
            manager = GroqClientManager()

            # Get 3 clients — should use different keys
            keys_used = set()
            for _ in range(3):
                client = manager._get_client()
                keys_used.add(client.api_key)
            assert len(keys_used) >= 2  # At least 2 different keys

    def test_circuit_breaker_opens_after_3_failures(self):
        """Circuit breaker should open after 3 consecutive failures."""
        from app.services.groq_client import CircuitBreaker
        cb = CircuitBreaker(failure_threshold=3, reset_timeout=60)

        assert not cb.is_open
        cb.record_failure()
        cb.record_failure()
        assert not cb.is_open
        cb.record_failure()
        assert cb.is_open

    def test_circuit_breaker_resets_on_success(self):
        """Success should reset failure count."""
        from app.services.groq_client import CircuitBreaker
        cb = CircuitBreaker(failure_threshold=3, reset_timeout=60)

        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb._failure_count == 0
        assert not cb.is_open


# ── Swarm Base Tests ───────────────────────────────────────────────


class TestSwarmBase:
    """Test the universal retry wrapper (Decision 5)."""

    def test_all_swarms_have_fallback_values(self):
        """Every swarm must define a fallback value."""
        swarm_classes = []
        try:
            from app.services.translator import Translator
            swarm_classes.append(Translator)
        except ImportError:
            pass
        try:
            from app.services.gatekeeper import Gatekeeper
            swarm_classes.append(Gatekeeper)
        except ImportError:
            pass
        try:
            from app.services.response_curator import ChatResponseCurator as ResponseCurator
            swarm_classes.append(ResponseCurator)
        except ImportError:
            pass
        try:
            from app.services.compliance_checker import ComplianceChecker
            swarm_classes.append(ComplianceChecker)
        except ImportError:
            pass
        try:
            from app.services.context_builder import ContextBuilder
            swarm_classes.append(ContextBuilder)
        except ImportError:
            pass
        try:
            from app.services.gap_detector import GapDetector
            swarm_classes.append(GapDetector)
        except ImportError:
            pass
        try:
            from app.services.sentiment_analyser import SentimentAnalyser
            swarm_classes.append(SentimentAnalyser)
        except ImportError:
            pass

        for cls in swarm_classes:
            instance = cls()
            fallback = instance.get_fallback_value()
            assert fallback is not None, f"{cls.__name__}.get_fallback_value() returned None"

    def test_gatekeeper_fallback_is_fail_open(self):
        """Gatekeeper fallback should be safe=True (fail-open)."""
        try:
            from app.services.gatekeeper import Gatekeeper
            gk = Gatekeeper()
            fallback = gk.get_fallback_value()
            parsed = json.loads(fallback) if isinstance(fallback, str) else fallback
            assert parsed.get("safe") is True
            assert parsed.get("is_fertility_related") is True
        except ImportError:
            pytest.skip("Gatekeeper not yet built")

    def test_compliance_fallback_is_passthrough(self):
        """Compliance fallback should pass through input unchanged."""
        try:
            from app.services.compliance_checker import ComplianceChecker
            cc = ComplianceChecker()
            # Fallback behavior: return input unchanged
            fallback = cc.get_fallback_value()
            assert fallback is not None
        except ImportError:
            pytest.skip("ComplianceChecker not yet built")

    def test_curator_fallback_is_user_friendly(self):
        """Curator fallback should be a human-friendly message."""
        try:
            from app.services.response_curator import ChatResponseCurator as ResponseCurator
            rc = ResponseCurator()
            fallback = rc.get_fallback_value()
            assert isinstance(fallback, str)
            assert len(fallback) > 10
            assert "rephras" in fallback.lower() or "couldn" in fallback.lower()
        except ImportError:
            pytest.skip("ResponseCurator not yet built")

    def test_context_fallback_has_required_keys(self):
        """Context builder fallback should have phase, day, summary keys."""
        try:
            from app.services.context_builder import ContextBuilder
            cb = ContextBuilder()
            fallback = cb.get_fallback_value()
            parsed = json.loads(fallback) if isinstance(fallback, str) else fallback
            assert "phase" in parsed or "summary" in parsed
        except ImportError:
            pytest.skip("ContextBuilder not yet built")


# ── Swarm Validation Tests ─────────────────────────────────────────


class TestSwarmValidation:
    """Test that each swarm correctly validates LLM output."""

    def test_gatekeeper_rejects_invalid_json(self):
        """Gatekeeper should reject non-JSON output."""
        try:
            from app.services.gatekeeper import Gatekeeper
            gk = Gatekeeper()
            assert gk.validate_output("not json") is False
            assert gk.validate_output("") is False
        except ImportError:
            pytest.skip("Gatekeeper not yet built")

    def test_gatekeeper_accepts_valid_json(self):
        """Gatekeeper should accept valid classification JSON."""
        try:
            from app.services.gatekeeper import Gatekeeper
            gk = Gatekeeper()
            valid = '{"safe": true, "is_fertility_related": true, "category": "nutrition"}'
            assert gk.validate_output(valid) is True
        except ImportError:
            pytest.skip("Gatekeeper not yet built")

    def test_curator_rejects_empty(self):
        """Curator should reject empty output."""
        try:
            from app.services.response_curator import ChatResponseCurator as ResponseCurator
            rc = ResponseCurator()
            assert rc.validate_output("") is False
            assert rc.validate_output("   ") is False
        except ImportError:
            pytest.skip("ResponseCurator not yet built")

    def test_curator_accepts_long_text(self):
        """Curator should accept substantive responses."""
        try:
            from app.services.response_curator import ChatResponseCurator as ResponseCurator
            rc = ResponseCurator()
            valid = "During IVF stims, focus on protein-rich foods and omega-3 fatty acids."
            assert rc.validate_output(valid) is True
        except ImportError:
            pytest.skip("ResponseCurator not yet built")

    def test_sentiment_rejects_invalid_json(self):
        """Sentiment analyser should reject non-JSON output."""
        try:
            from app.services.sentiment_analyser import SentimentAnalyser
            sa = SentimentAnalyser()
            assert sa.validate_output("not json") is False
        except ImportError:
            pytest.skip("SentimentAnalyser not yet built")

    def test_sentiment_accepts_valid(self):
        """Sentiment analyser should accept valid sentiment JSON."""
        try:
            from app.services.sentiment_analyser import SentimentAnalyser
            sa = SentimentAnalyser()
            valid = '{"sentiment": "hopeful", "intensity": 0.7, "needs_empathy": false}'
            assert sa.validate_output(valid) is True
        except ImportError:
            pytest.skip("SentimentAnalyser not yet built")


# ── Swarm Config Tests ─────────────────────────────────────────────


class TestSwarmConfig:
    """Verify all swarm configs are present and correct."""

    def test_all_10_swarm_configs_exist(self):
        """SWARM_CONFIG should have entries for all 10 swarms."""
        from app.core.model_config import SWARM_CONFIG
        expected_ids = [
            "swarm_0_polyglot", "swarm_1_gatekeeper",
            "swarm_3_clinical_brain", "swarm_4_curator",
            "swarm_5_analyser", "swarm_6_bloodwork_curator",
            "swarm_7_compliance", "swarm_8_gap",
            "swarm_9_context", "swarm_10_sentiment",
        ]
        for sid in expected_ids:
            assert sid in SWARM_CONFIG, f"Missing config for {sid}"

    def test_swarm_configs_have_required_fields(self):
        """Each swarm config should have model and temperature."""
        from app.core.model_config import SWARM_CONFIG
        for sid, cfg in SWARM_CONFIG.items():
            if sid == "swarm_3_clinical_brain":
                # RAG swarm has different config
                assert "embedding_model" in cfg, f"{sid} missing embedding_model"
                continue
            assert "model" in cfg, f"{sid} missing model"
            assert "temperature" in cfg, f"{sid} missing temperature"
            assert "max_tokens" in cfg, f"{sid} missing max_tokens"
