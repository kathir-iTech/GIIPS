"""
Service layer for GIIPS backend.

Handles business logic and model interactions.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from classification.train import ComplaintClassifier
from clustering.cluster import ComplaintClusterer
from priority.priority import PriorityEngine

from .models import (
    ClassifyRequest, ClassifyResponse,
    ClusterRequest, ClusterResponse, ClusterAssignment,
    PriorityRequest, PriorityResponse, PriorityFactor,
    DashboardResponse, IncidentResponse, ComplaintModel
)


class ClassificationService:
    """Service for complaint classification."""

    _classifier = None

    @classmethod
    def get_classifier(cls) -> ComplaintClassifier:
        """Get or load the classifier."""
        if cls._classifier is None:
            models_dir = Path(__file__).parent.parent / 'models' / 'classification'
            if models_dir.exists() and (models_dir / 'classifier.pkl').exists():
                try:
                    cls._classifier = ComplaintClassifier.load(models_dir)
                except Exception:
                    pass
        return cls._classifier

    async def classify(self, request: ClassifyRequest) -> ClassifyResponse:
        """Classify a single complaint."""
        classifier = self.get_classifier()

        if classifier is None:
            return await self._fallback_classify(request)

        # Combine text
        combined_text = request.text
        if request.detail:
            combined_text += f" {request.detail}"

        try:
            prediction = classifier.predict([combined_text])[0]
            probabilities = classifier.predict_proba([combined_text])[0]

            import numpy as np
            top_indices = np.argsort(probabilities)[::-1][:5]
            top_predictions = [
                {"category": str(classifier.classes_[idx]), "confidence": float(probabilities[idx])}
                for idx in top_indices
            ]

            confidence = float(probabilities[classifier.classes_.tolist().index(prediction)])

            return ClassifyResponse(
                predicted_category=str(prediction),
                confidence=confidence,
                top_predictions=top_predictions
            )
        except Exception as e:
            return await self._fallback_classify(request)

    async def _fallback_classify(self, request: ClassifyRequest) -> ClassifyResponse:
        """Keyword-based fallback classification."""
        text_lower = request.text.lower()
        category_scores = {
            'Road Infrastructure': any(kw in text_lower for kw in ['pothole', 'road', 'street', 'pavement', 'crack']),
            'Water Supply': any(kw in text_lower for kw in ['water', 'pipe', 'leak', 'supply', 'tap', 'drainage']),
            'Waste Management': any(kw in text_lower for kw in ['garbage', 'waste', 'trash', 'rubbish', 'bin', 'collection']),
            'Sanitation': any(kw in text_lower for kw in ['sewage', 'toilet', 'sanitation', 'sewer', 'overflow']),
            'Street Lighting': any(kw in text_lower for kw in ['light', 'lamp', 'bulb', 'dark', 'street light']),
        }

        predicted = 'Public Works'
        confidence = 0.5

        for cat, match in category_scores.items():
            if match:
                predicted = cat
                confidence = 0.75
                break

        return ClassifyResponse(
            predicted_category=predicted,
            confidence=confidence,
            top_predictions=[{"category": predicted, "confidence": confidence}]
        )


class ClusteringService:
    """Service for complaint clustering."""

    _clusterer = None

    @classmethod
    def get_clusterer(cls) -> ComplaintClusterer:
        """Get or create the clusterer."""
        if cls._clusterer is None:
            cls._clusterer = ComplaintClusterer(eps=0.3, min_samples=2)
        return cls._clusterer

    async def cluster(self, request: ClusterRequest) -> ClusterResponse:
        """Cluster complaints into incidents."""
        clusterer = self.get_clusterer()

        if request.eps:
            clusterer.eps = request.eps

        try:
            result = clusterer.cluster_with_ward_separation(
                request.complaints,
                text_key=request.text_key
            )

            assignments = [
                ClusterAssignment(
                    complaint_id=request.complaints[i].get('id', i),
                    cluster_label=int(label),
                    is_noise=label == -1
                )
                for i, label in enumerate(result.get('labels', []))
            ]

            cluster_details = {}
            for label, members in result.get('clusters', {}).items():
                cluster_details[str(label)] = {
                    "size": len(members),
                    "sample_text": members[0].get('text', '')[:100] if members else ''
                }

            return ClusterResponse(
                n_clusters=result['n_clusters'],
                n_noise=result['n_noise'],
                cluster_assignments=assignments,
                cluster_details=cluster_details
            )
        except Exception as e:
            # Fallback to simple grouping
            return await self._fallback_cluster(request)

    async def _fallback_cluster(self, request: ClusterRequest) -> ClusterResponse:
        """Simple fallback clustering."""
        from collections import defaultdict

        buckets = defaultdict(list)
        for i, complaint in enumerate(request.complaints):
            text = complaint.get(request.text_key, '') or complaint.get('text', '')
            bucket_key = text[:50].lower() if text else 'empty'
            buckets[bucket_key].append(i)

        cluster_labels = {}
        cluster_id = 0

        for key, indices in buckets.items():
            if len(indices) >= 2:
                for idx in indices:
                    cluster_labels[idx] = cluster_id
                cluster_id += 1
            else:
                for idx in indices:
                    cluster_labels[idx] = -1

        assignments = [
            ClusterAssignment(
                complaint_id=request.complaints[i].get('id', i),
                cluster_label=cluster_labels.get(i, -1),
                is_noise=cluster_labels.get(i, -1) == -1
            )
            for i in range(len(request.complaints))
        ]

        return ClusterResponse(
            n_clusters=cluster_id,
            n_noise=sum(1 for a in assignments if a.is_noise),
            cluster_assignments=assignments,
            cluster_details={}
        )

    async def find_similar(
        self,
        text: str,
        existing_complaints: List[Dict[str, Any]],
        threshold: float
    ) -> List[Dict[str, Any]]:
        """Find similar complaints."""
        clusterer = self.get_clusterer()

        try:
            duplicates = clusterer.find_duplicates(text, existing_complaints, threshold)
            return [{k: v for k, v in d.items() if k in ['id', 'text', 'similarity']}
                    for d in duplicates]
        except Exception:
            # Fallback to keyword matching
            text_keywords = set(text.lower().split()[:10])
            similar = []
            for complaint in existing_complaints:
                ct = complaint.get('text', '').lower()
                ct_keywords = set(ct.split()[:10])
                overlap = len(text_keywords & ct_keywords) / max(len(text_keywords), 1)
                if overlap >= threshold * 0.5:
                    similar.append({
                        "id": complaint.get('id'),
                        "text": ct[:100],
                        "similarity": overlap
                    })
            return similar[:5]


class PriorityService:
    """Service for priority calculation."""

    _engine = None

    @classmethod
    def get_engine(cls) -> PriorityEngine:
        """Get or create the priority engine."""
        if cls._engine is None:
            cls._engine = PriorityEngine()
        return cls._engine

    async def calculate(self, request: PriorityRequest) -> PriorityResponse:
        """Calculate priority for an incident."""
        engine = self.get_engine()

        result = engine.compute(
            incident_id=request.incident_id,
            cluster_size=request.cluster_size,
            first_complaint_date=request.first_complaint_date,
            last_complaint_date=request.last_complaint_date,
            category=request.category,
            location_hints=request.location_hints
        )

        return PriorityResponse(
            incident_id=result.incident_id,
            priority_score=result.priority_score,
            priority_label=result.priority_label,
            factors=[
                PriorityFactor(
                    name=f.name,
                    raw_value=f.raw_value,
                    normalized_value=f.normalized_value,
                    weight=f.weight,
                    contribution=f.contribution,
                    description=f.description
                )
                for f in result.factors
            ],
            explanation=result.explanation
        )


class DashboardService:
    """Service for dashboard data."""

    async def get_summary(self) -> DashboardResponse:
        """Get dashboard summary statistics."""
        outputs_dir = Path(__file__).parent.parent / 'outputs'
        data_file = outputs_dir / 'dashboard_data.json'

        if data_file.exists():
            try:
                with open(data_file, 'r') as f:
                    data = json.load(f)
                return DashboardResponse(**data)
            except Exception:
                pass

        # Default sample data
        return DashboardResponse(
            total_complaints=100,
            unique_incidents=15,
            workload_reduction=85.0,
            critical_incidents=3,
            high_priority_incidents=5,
            category_distribution=[
                {"category": "Road Infrastructure", "count": 30},
                {"category": "Water Supply", "count": 25},
                {"category": "Waste Management", "count": 20},
                {"category": "Street Lighting", "count": 15},
                {"category": "Sanitation", "count": 10}
            ],
            priority_distribution={"Critical": 3, "High": 5, "Medium": 4, "Low": 3}
        )

    async def get_incidents(
        self,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[IncidentResponse]:
        """Get list of incidents."""
        outputs_dir = Path(__file__).parent.parent / 'outputs'

        incidents = []
        for i in range(min(limit, 15)):
            incidents.append(IncidentResponse(
                id=f"inc-{i+1}",
                incident_number=f"INC-2024-{i+1:04d}",
                category="Road Infrastructure" if i % 3 == 0 else "Water Supply" if i % 3 == 1 else "Sanitation",
                ward=f"Ward {(i % 8) + 1}",
                cluster_size=5 + (i * 2),
                days_open=5 + i,
                priority_score=90 - (i * 3),
                priority_label=["Critical", "High", "Medium", "Low"][min(i % 4, 3)],
                summary=f"Sample incident {i+1}",
                recommended_action="Immediate repair required",
                status="open",
                complaints=[]
            ))

        # Apply filters
        if priority:
            incidents = [i for i in incidents if i.priority_label.lower() == priority.lower()]
        if category:
            incidents = [i for i in incidents if category.lower() in i.category.lower()]

        return incidents[:limit]

    async def get_incident_by_id(self, incident_id: str) -> Optional[IncidentResponse]:
        """Get a specific incident by ID."""
        incidents = await self.get_incidents(limit=100)
        for incident in incidents:
            if incident.id == incident_id or incident.incident_number == incident_id:
                return incident
        return None
