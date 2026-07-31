"""
Tests for the ONNX semantic duplicate-detection path (fastembed backend).
The fastembed module is mocked here so tests are hermetic (no network, no model download).
"""

import sys
import sysconfig
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pytest

from duplicate_detection import engine
from duplicate_detection.engine import (
    DuplicateDetector,
    _SemanticDuplicateDetector,
    DUP_CONF_THRESHOLD,
)


class _FakeTextEmbedding:
    """Deterministic token-hash embeddings: identical text -> identical vector,
    disjoint text -> orthogonal vector."""

    def __init__(self, model_name=None, threads=None):
        pass

    def embed(self, texts):
        out = []
        for t in texts:
            vec = np.zeros(256, dtype=np.float32)
            for tok in t.lower().split():
                h = hash(tok) % 256
                vec[h] += 1.0
            norm = np.linalg.norm(vec)
            out.append(vec / norm if norm > 0 else vec)
        return iter(out)


@pytest.fixture(autouse=True)
def _mock_fastembed(monkeypatch):
    fake_module = MagicMock()
    fake_module.TextEmbedding = _FakeTextEmbedding
    monkeypatch.setitem(sys.modules, "fastembed", fake_module)
    monkeypatch.setattr(engine, "_FASTEMBED_AVAILABLE", True)
    _SemanticDuplicateDetector._model = None
    yield
    _SemanticDuplicateDetector._model = None


def _complaint(title, category="Roads", lat=11.0168, lon=76.9558, incident_id="inc-1"):
    return {
        "title": title, "description": "",
        "lat": lat, "lon": lon, "category": category, "incident_id": incident_id,
    }


class TestONNXBackendSelection:
    def test_fastembed_is_default_backend(self):
        det = DuplicateDetector()
        assert isinstance(det._backend, _SemanticDuplicateDetector)

    def test_model_is_singleton(self):
        det1 = DuplicateDetector()
        det2 = DuplicateDetector()
        assert det1._backend.get_model() is det2._backend.get_model()

    def test_threshold_constant_matches_benchmark(self):
        assert DUP_CONF_THRESHOLD == 0.71


class TestONNXDuplicateDetection:
    def test_identical_text_high_confidence(self):
        det = DuplicateDetector()
        a = _complaint("machi road la periya kuzhi", incident_id="new")
        b = _complaint("machi road la periya kuzhi", incident_id="inc-1")
        incident_id, conf = det.detect_duplicates(a, [b])
        assert incident_id == "inc-1"
        assert conf > DUP_CONF_THRESHOLD

    def test_semantic_duplicate_detected(self):
        det = DuplicateDetector()
        a = _complaint("machi road la periya kuzhi vehicles damage aagudhu", incident_id="new")
        b = _complaint("vehicles damage machi road la periya kuzhi", incident_id="inc-1")
        incident_id, conf = det.detect_duplicates(a, [b])
        assert incident_id == "inc-1"
        assert conf > DUP_CONF_THRESHOLD

    def test_disjoint_topics_low_confidence(self):
        det = DuplicateDetector()
        a = _complaint("pothole on the road near the school", incident_id="new")
        b = _complaint("garbage not collected in our street", incident_id="inc-1")
        incident_id, conf = det.detect_duplicates(a, [b])
        assert conf < DUP_CONF_THRESHOLD

    def test_picks_best_match(self):
        det = DuplicateDetector()
        a = _complaint("water pipe leak road la vellam", incident_id="new")
        candidates = [
            _complaint("garbage truck varala 2 weeks", incident_id="inc-far"),
            _complaint("tanni pipe leak road full water", incident_id="inc-near"),
        ]
        incident_id, _ = det.detect_duplicates(a, candidates)
        assert incident_id == "inc-near"

    def test_empty_candidates(self):
        det = DuplicateDetector()
        a = _complaint("anything", incident_id="new")
        assert det.detect_duplicates(a, []) == (None, 0.0)

    def test_location_weighting_reduces_confidence(self):
        det = DuplicateDetector()
        a = _complaint("water pipe leak road la vellam", incident_id="new")
        same_place = _complaint("tanni pipe leak road full water", incident_id="inc-1",
                                lat=11.0168, lon=76.9558)
        far_place = _complaint("tanni pipe leak road full water", incident_id="inc-2",
                               lat=11.2, lon=77.1)
        _, conf_same = det.detect_duplicates(a, [same_place])
        _, conf_far = det.detect_duplicates(a, [far_place])
        assert conf_same > conf_far

    def test_category_weighting_reduces_confidence(self):
        det = DuplicateDetector()
        a = _complaint("water pipe leak road la vellam", incident_id="new",
                       category="Water Supply")
        same_cat = _complaint("tanni pipe leak road full water", incident_id="inc-1",
                              category="Water Supply")
        diff_cat = _complaint("tanni pipe leak road full water", incident_id="inc-2",
                              category="Roads")
        _, conf_same = det.detect_duplicates(a, [same_cat])
        _, conf_diff = det.detect_duplicates(a, [diff_cat])
        assert conf_same > conf_diff
