"""
Test Tanglish duplicate detection with Morgan-Tanglish-v7.
Run with: GIIPS_TANGLISH_MODEL=1 pytest test_tanglish_dup.py -v
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from duplicate_detection.engine import (
    DuplicateDetector,
    _TanglishDuplicateDetector,
    _is_tanglish_text,
    _TANGLISH_ENABLED,
)

# Detect if sentence_transformers is mocked by conftest.py
_SENTENCE_TRANSFORMERS_REAL = True
try:
    import sentence_transformers
    if isinstance(sentence_transformers.SentenceTransformer, MagicMock):
        _SENTENCE_TRANSFORMERS_REAL = False
except (ImportError, AttributeError):
    _SENTENCE_TRANSFORMERS_REAL = False


TANGLISH_DUP_PAIRS = [
    # (complaint_a, complaint_b, is_duplicate)
    ("machi road la periya kuzhi, vehicles ellam damage aagudhu",
     "bro road la valiya pothole, cars ellam kettu poguthu",
     True),
    ("street light eriyala, night la total darkness, vali kooda theriyala",
     "enna da street light off eruku, night la romba iruttu ah eruku",
     True),
    ("garbage van varala, 2 weeks ah garbage collect pannala, street la kuppa",
     "enna garbage collector varadha, 2 weeks ayiduchu trash collect pannama",
     True),
    ("water pipe leak agudhu, main road la vellam oothitu eruku waste ah",
     "tanni pipe vituduchi, road full ah water oothitu eruku",
     True),
    ("sewage drain block ah eruku, sokka nikkuthu, road mela vandhuduchu",
     "drain block ah iruku, sewage water road la vandhu nikkuthu",
     True),
]

NONDUP_PAIRS = [
    # Different issues, same Tanglish style
    ("pothole on the road near the school, danger ah iruku",
     "garbage not collected, 2 weeks ah street la kuppa ah iruku",
     False),
    ("water supply problem, tanni eh varadha",
     "power cut, electricity illa, inverter um illa",
     False),
    ("street light broken at junction",
     "road pothole near the bus stop, valiya kuzhi",
     False),
    # English-only
    ("Large pothole on the main road",
     "Water pipe burst on the highway",
     False),
    ("Garbage overflowing from the bin",
     "Water pipe burst causing flooding",
     False),
]


class TestTanglishDetection:
    def test_is_tanglish_text_detects_tanglish(self):
        assert _is_tanglish_text("machi road la kuzhi iruku")
        assert _is_tanglish_text("street light eriyala da")
        assert _is_tanglish_text("tanni pipe vituduchi")
        assert _is_tanglish_text("bro nalla complaint podu")

    def test_is_tanglish_text_rejects_english(self):
        assert not _is_tanglish_text("There is a large pothole on the main road")
        assert not _is_tanglish_text("The water supply has not been working")
        assert not _is_tanglish_text("Please fix the street light at the junction")
        assert not _is_tanglish_text("Garbage overflowing from the bin on the corner")
        assert not _is_tanglish_text("Water pipe burst on the highway causing flooding")


@pytest.mark.skipif(
    not _TANGLISH_ENABLED,
    reason="Set GIIPS_TANGLISH_MODEL=1 to enable Tanglish model tests",
)
@pytest.mark.skipif(
    not _SENTENCE_TRANSFORMERS_REAL,
    reason="sentence_transformers is mocked by conftest.py — cannot load real model",
)
class TestTanglishDuplicateDetector:
    def test_tanglish_model_loads(self):
        det = _TanglishDuplicateDetector()
        model = det.get_model()
        assert model is not None
        dim = model.get_embedding_dimension()
        assert dim > 0, f"Expected positive embedding dimension, got {dim}"
        # paraphrase-multilingual-MiniLM-L12-v2 produces 384-d,
        # but the fine-tuned model may differ — accept whatever it is
        print(f"Tanglish model embedding dim: {dim}")

    def test_tanglish_duplicates_detected_correctly(self):
        det = DuplicateDetector()
        for a_text, b_text, expected in TANGLISH_DUP_PAIRS:
            a = {"title": a_text, "description": "", "lat": 11.0, "lon": 77.0, "category": "Roads"}
            b = {"title": b_text, "description": "", "lat": 11.0, "lon": 77.0, "category": "Roads"}
            incident_id, conf = det.detect_duplicates(a, [b])
            assert conf > 0.7, (
                f"Expected high confidence for Tanglish duplicate pair, got {conf:.3f}\n"
                f"  A: {a_text[:60]}\n  B: {b_text[:60]}"
            )

    def test_nonduplicates_get_low_confidence(self):
        det = DuplicateDetector()
        for a_text, b_text, _ in NONDUP_PAIRS:
            a = {"title": a_text, "description": "", "lat": 11.0, "lon": 77.0, "category": "Roads"}
            b = {"title": b_text, "description": "", "lat": 11.0, "lon": 77.0, "category": "Roads"}
            incident_id, conf = det.detect_duplicates(a, [b])
            assert conf < 0.75, (
                f"Expected low confidence for non-duplicate pair, got {conf:.3f}\n"
                f"  A: {a_text[:60]}\n  B: {b_text[:60]}"
            )

    def test_tanglish_dup_edge_different_categories(self):
        """Same Tanglish text but different categories should get lower confidence."""
        det = DuplicateDetector()
        text_a = "machi road la periya kuzhi"
        text_b = "bro road la valiya pothole"
        a = {"title": text_a, "description": "", "lat": 11.0, "lon": 77.0, "category": "Roads"}
        b = {"title": text_b, "description": "", "lat": 11.0, "lon": 77.0, "category": "Water Supply"}
        incident_id, conf = det.detect_duplicates(a, [b])
        # Category weight is 0.1, so diff category should reduce conf slightly
        assert 0.65 <= conf <= 0.85, f"Expected moderate confidence, got {conf:.3f}"
