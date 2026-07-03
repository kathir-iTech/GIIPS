"""
AI Duplicate Detection Engine.

Uses Sentence Transformers and scikit-learn NearestNeighbors for efficient semantic similarity.
Falls back to a lightweight keyword-overlap strategy when heavy ML dependencies are unavailable.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from geopy.distance import geodesic

logger = logging.getLogger(__name__)

_SENTENCE_TRANSFORMERS_AVAILABLE = False
_SKLEARN_AVAILABLE = False

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


class _FallbackDuplicateDetector:
    """Lightweight keyword-overlap duplicate detector used when ML deps are unavailable."""

    def detect_duplicates(self, new_complaint: Dict, existing_complaints: List[Dict]) -> Tuple[Optional[str], float]:
        if not existing_complaints:
            return None, 0.0

        new_text = f"{new_complaint.get('title', '')} {new_complaint.get('description', '')}".lower()
        new_words = set(new_text.split())
        new_cat = new_complaint.get('category', '')
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
        """Detect best match using vector search or keyword fallback."""
        if self._backend != 'ml':
            return self._backend.detect_duplicates(new_complaint, existing_complaints)

        if not existing_complaints:
            return None, 0.0

        self._fit(existing_complaints)

        text = f"{new_complaint.get('title', '')} {new_complaint.get('description', '')}"
        query_emb = self.model.encode([text])

        distances, indices = self.nn.kneighbors(query_emb)

        best_idx = indices[0][0]
        best_match = existing_complaints[best_idx]

        conf = self._compute_confidence(new_complaint, best_match, 1 - distances[0][0])

        return best_match.get('incident_id'), conf

    def _compute_confidence(self, comp1: Dict, comp2: Dict, text_sim: float) -> float:
        weights = {'text': 0.6, 'location': 0.3, 'category': 0.1}

        loc1 = (comp1.get('lat', 0), comp1.get('lon', 0))
        loc2 = (comp2.get('lat', 0), comp2.get('lon', 0))
        dist = geodesic(loc1, loc2).meters
        loc_sim = max(0, 1 - (dist / 1000))

        cat_sim = 1.0 if comp1.get('category') == comp2.get('category') else 0.0

        return text_sim * weights['text'] + loc_sim * weights['location'] + cat_sim * weights['category']
