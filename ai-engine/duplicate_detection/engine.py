"""
AI Duplicate Detection Engine.

Uses Sentence Transformers and scikit-learn NearestNeighbors for efficient semantic similarity.
"""

import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from sentence_transformers import SentenceTransformer
from sklearn.neighbors import NearestNeighbors
from geopy.distance import geodesic

class DuplicateDetector:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)
        self.nn = NearestNeighbors(n_neighbors=5, metric='cosine')
        self.is_fitted = False
        self.existing_data = []

    def _fit(self, existing_complaints: List[Dict]):
        if not existing_complaints: return
        texts = [f"{c.get('title', '')} {c.get('description', '')}" for c in existing_complaints]
        embeddings = self.model.encode(texts)
        self.nn.fit(embeddings)
        self.existing_data = existing_complaints
        self.is_fitted = True

    def detect_duplicates(self, new_complaint: Dict, existing_complaints: List[Dict]) -> Tuple[Optional[str], float]:
        """Detect best match using vector search."""
        if not existing_complaints: return None, 0.0
        
        self._fit(existing_complaints)
        
        text = f"{new_complaint.get('title', '')} {new_complaint.get('description', '')}"
        query_emb = self.model.encode([text])
        
        distances, indices = self.nn.kneighbors(query_emb)
        
        best_idx = indices[0][0]
        best_match = existing_complaints[best_idx]
        
        # Calculate confidence using the same logic as Phase 2
        conf = self._compute_confidence(new_complaint, best_match, 1 - distances[0][0])
        
        return best_match.get('incident_id'), conf

    def _compute_confidence(self, comp1: Dict, comp2: Dict, text_sim: float) -> float:
        # Simplified weights
        weights = {'text': 0.6, 'location': 0.3, 'category': 0.1}
        
        loc1 = (comp1.get('lat', 0), comp1.get('lon', 0))
        loc2 = (comp2.get('lat', 0), comp2.get('lon', 0))
        dist = geodesic(loc1, loc2).meters
        loc_sim = max(0, 1 - (dist / 1000)) # 1km radius

        cat_sim = 1.0 if comp1.get('category') == comp2.get('category') else 0.0
        
        return (text_sim * weights['text'] + loc_sim * weights['location'] + cat_sim * weights['category'])
