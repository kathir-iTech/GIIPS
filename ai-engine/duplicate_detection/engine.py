"""
AI Duplicate Detection Engine.

Uses Sentence Transformers and scikit-learn NearestNeighbors for efficient semantic similarity.
Falls back to a lightweight keyword-overlap strategy when heavy ML dependencies are unavailable.
Supports a Tanglish-specific path via Morgan-Tanglish-v7 for Romanised Tamil-English code-mixed text.
"""

import logging
import os
import re
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from geopy.distance import geodesic

logger = logging.getLogger(__name__)

_SENTENCE_TRANSFORMERS_AVAILABLE = False
_SKLEARN_AVAILABLE = False
_TANGLISH_MODEL_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    _SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.warning("sentence-transformers not available. Duplicate detection will use lightweight fallback.")

try:
    from sklearn.neighbors import NearestNeighbors
    _SKLEARN_AVAILABLE = True
except ImportError:
    logger.warning("scikit-learn not available. Duplicate detection will use lightweight fallback.")

# Tanglish detection — common Romanised Tamil particles and patterns
_TANGLISH_PARTICLES = {
    "da", "ma", "la", "ah", "nu", "na", "tha", "pa", "va", "ya",
    "dha", "ndha", "nnu", "nga", "chu", "dhu", "ru", "lu",
}
_TANGLISH_WORDS = {
    "machi", "machan", "bro", "thala", "thalaiva",
    "sema", "semma", "romba", "nalla", "sari", "seri", "poda",
    "podi", "vaada", "enna", "yenna", "epdi", "eppadi",
    "enga", "engay", "inga", "ingay", "anga", "angay",
    "vaa", "vaanga", "ponga", "pottu", "pannu", "pannuthu",
    "iruku", "irukku", "irundhu", "vandhu", "poguthu", "aagudhu",
    "vekanum", "vekanam", "mudiyala", "mudiyadhu",
    "theriyala", "theriyadhu", "tanni", "thanni",
    "vellam", "kuzhi",
}

# Tanglish detection is gated by env var (default: disabled on constrained tiers)
_TANGLISH_ENABLED = os.environ.get("GIIPS_TANGLISH_MODEL", "0") == "1"

TANGLISH_MODEL_NAME = os.environ.get(
    "GIIPS_TANGLISH_MODEL_NAME",
    "vishnu-n/Morgan-Tanglish-v7",
)


def _is_tanglish_text(text: str) -> bool:
    """Heuristic detection of Tanglish (Romanised Tamil-English code-mixed) text.
    Checks for known Tanglish particles and word patterns.
    Not exhaustive — a lightweight gate to avoid routing pure English through Tanglish model.
    """
    lower = text.lower()
    tokens = lower.split()
    particle_hits = sum(1 for t in tokens if t in _TANGLISH_PARTICLES)
    word_hits = sum(1 for t in tokens if t in _TANGLISH_WORDS)
    # If >10% of tokens are Tanglish particles or any known Tanglish word present
    return particle_hits >= 1 or word_hits >= 1


class _TanglishDuplicateDetector:
    """Morgan-Tanglish-v7 based duplicate detector for Tanglish code-mixed text.
    Lazy-loaded on first use to minimise memory when Tanglish text is rare.
    Only activated when GIIPS_TANGLISH_MODEL=1 is set and Tanglish text is detected.
    """

    _model = None

    # Calibrated on 50-pair Tanglish benchmark:
    # text-only (no geo/category) at threshold 0.56 gives F1=0.816
    _TANGLISH_CONF_THRESHOLD = 0.56

    @classmethod
    def get_model(cls):
        if cls._model is None:
            if not _SENTENCE_TRANSFORMERS_AVAILABLE:
                return None
            try:
                cls._model = SentenceTransformer(TANGLISH_MODEL_NAME)
                logger.info("Tanglish model '%s' loaded.", TANGLISH_MODEL_NAME)
            except Exception as exc:
                logger.warning("Tanglish model load failed: %s", exc)
                return None
        return cls._model

    def detect_duplicates(
        self, new_complaint: Dict, existing_complaints: List[Dict]
    ) -> Tuple[Optional[str], float]:
        if not existing_complaints:
            return None, 0.0

        model = self.get_model()
        if model is None:
            return None, -1.0

        new_text = f"{new_complaint.get('title', '')} {new_complaint.get('description', '')}"
        new_emb = model.encode([new_text])

        existing_texts = [
            f"{c.get('title', '')} {c.get('description', '')}" for c in existing_complaints
        ]
        existing_embs = model.encode(existing_texts)

        from sklearn.metrics.pairwise import cosine_similarity
        sims = cosine_similarity(new_emb, existing_embs)[0]
        best_idx = int(np.argmax(sims))
        best_sim = float(sims[best_idx])
        best_match = existing_complaints[best_idx]

        conf = self._compute_confidence(best_sim)

        if conf <= 0.0:
            return None, 0.0

        # Normalise: map [0.56, 1.0] → [0.80, 1.0] so caller's dup_conf > 0.8
        # threshold still works correctly for Tanglish.
        normalised = 0.80 + (conf - self._TANGLISH_CONF_THRESHOLD) * (0.20 / (1.0 - self._TANGLISH_CONF_THRESHOLD))
        normalised = min(max(normalised, 0.0), 1.0)

        return best_match.get('incident_id'), normalised

    def _compute_confidence(self, text_sim: float) -> float:
        """Text-only (100/0/0) confidence — no geo/category weighting.
        Benchmark-proven to outperform 60/30/10 for Tanglish text.
        """
        if text_sim < self._TANGLISH_CONF_THRESHOLD:
            return 0.0
        return text_sim


class _FallbackDuplicateDetector:
    """Lightweight keyword-overlap duplicate detector used when ML deps are unavailable."""

    def detect_duplicates(self, new_complaint: Dict, existing_complaints: List[Dict]) -> Tuple[Optional[str], float]:
        if not existing_complaints:
            return None, 0.0

        new_text = f"{new_complaint.get('title', '')} {new_complaint.get('description', '')}".lower()
        new_words = set(new_text.split())
        new_lat = new_complaint.get('lat', 0)
        new_lon = new_complaint.get('lon', 0)

        best_id, best_conf = None, 0.0

        for comp in existing_complaints:
            comp_text = f"{comp.get('title', '')} {comp.get('description', '')}".lower()
            comp_words = set(comp_text.split())
            overlap = len(new_words & comp_words) / max(len(new_words | comp_words), 1)
            if overlap > best_conf:
                best_conf = overlap
                best_id = comp.get('incident_id')

        return best_id, best_conf


class DuplicateDetector:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.is_fitted = False
        self.existing_data = []
        self._en_tanglish = _TanglishDuplicateDetector() if _TANGLISH_ENABLED else None

        if _SENTENCE_TRANSFORMERS_AVAILABLE and _SKLEARN_AVAILABLE:
            try:
                self.model = SentenceTransformer(model_name)
                self.nn = NearestNeighbors(n_neighbors=5, metric='cosine')
                logger.info("DuplicateDetector initialised with ML model '%s'.", model_name)
                self._backend = 'ml'
            except Exception as exc:
                logger.warning("ML model initialisation failed (%s). Falling back to lightweight detector.", exc)
                self.model = None
                self.nn = None
                self._backend = _FallbackDuplicateDetector()
        else:
            logger.info("ML dependencies unavailable. Using lightweight fallback duplicate detector.")
            self.model = None
            self.nn = None
            self._backend = _FallbackDuplicateDetector()

        if _TANGLISH_ENABLED:
            logger.info(
                "Tanglish duplicate detection enabled (model=%s). "
                "Will use Morgan-Tanglish-v7 for code-mixed Tamil-English text.",
                TANGLISH_MODEL_NAME,
            )

    def _fit(self, existing_complaints: List[Dict]):
        if not existing_complaints:
            return
        if self._backend == 'ml':
            texts = [f"{c.get('title', '')} {c.get('description', '')}" for c in existing_complaints]
            embeddings = self.model.encode(texts)
            self.nn.fit(embeddings)
        self.existing_data = existing_complaints
        self.is_fitted = True

    def detect_duplicates(self, new_complaint: Dict, existing_complaints: List[Dict]) -> Tuple[Optional[str], float]:
        """Detect best match using vector search or keyword fallback.

        Routing order:
        1. Tanglish path (if enabled + Tanglish text detected) → Morgan-Tanglish-v7
        2. ML path (if SBERT available) → all-MiniLM-L6-v2 + NearestNeighbors
        3. Fallback → Jaccard keyword overlap
        """
        if not existing_complaints:
            return None, 0.0

        # Phase 1: Try Tanglish model if enabled and text looks like Tanglish
        if self._en_tanglish is not None:
            new_text = f"{new_complaint.get('title', '')} {new_complaint.get('description', '')}"
            # Also check existing texts for Tanglish content
            existing_texts = [
                f"{c.get('title', '')} {c.get('description', '')}" for c in existing_complaints
            ]
            any_tanglish = _is_tanglish_text(new_text) or any(
                _is_tanglish_text(t) for t in existing_texts[:20]
            )
            if any_tanglish:
                incident_id, conf = self._en_tanglish.detect_duplicates(
                    new_complaint, existing_complaints
                )
                if conf >= 0:  # Model loaded successfully
                    logger.debug("Tanglish duplicate detection: id=%s conf=%.3f", incident_id, conf)
                    return incident_id, conf
                # conf == -1 means model failed to load — fall through

        # Phase 2: Standard ML path
        if self._backend == 'ml':
            self._fit(existing_complaints)
            text = f"{new_complaint.get('title', '')} {new_complaint.get('description', '')}"
            query_emb = self.model.encode([text])
            n = len(existing_complaints)
            # NearestNeighbors may have been initialised with n_neighbors > n
            self.nn.n_neighbors = min(self.nn.n_neighbors, max(n, 1))
            distances, indices = self.nn.kneighbors(query_emb)
            best_idx = indices[0][0]
            best_match = existing_complaints[best_idx]
            conf = self._compute_confidence(new_complaint, best_match, 1 - distances[0][0])
            return best_match.get('incident_id'), conf

        # Phase 3: Lightweight fallback
        return self._backend.detect_duplicates(new_complaint, existing_complaints)

    def _compute_confidence(self, comp1: Dict, comp2: Dict, text_sim: float) -> float:
        weights = {'text': 0.6, 'location': 0.3, 'category': 0.1}
        loc1 = (comp1.get('lat', 0), comp1.get('lon', 0))
        loc2 = (comp2.get('lat', 0), comp2.get('lon', 0))
        dist = geodesic(loc1, loc2).meters
        loc_sim = max(0, 1 - (dist / 1000))
        cat_sim = 1.0 if comp1.get('category') == comp2.get('category') else 0.0
        return text_sim * weights['text'] + loc_sim * weights['location'] + cat_sim * weights['category']
