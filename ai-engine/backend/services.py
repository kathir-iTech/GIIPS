"""
Service layer for GIIPS backend.

Handles business logic and model interactions.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from database import SessionLocal, Complaint, Incident, PriorityHistory
import uuid

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from classification.train import ComplaintClassifier
from clustering.cluster import ComplaintClusterer
from priority.priority import PriorityEngine

from models import (
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


from sqlalchemy import func

class DashboardService:
    """Service for dashboard data."""

    def __init__(self):
        self.db = SessionLocal()

    async def get_summary(self) -> Dict[str, Any]:
        """Get dashboard summary statistics."""
        total_complaints = self.db.query(Complaint).count()
        total_incidents = self.db.query(Incident).count()

        priority_counts = self.db.query(
            Incident.priority_label, func.count(Incident.id)
        ).group_by(Incident.priority_label).all()
        
        priority_dist = {label: count for label, count in priority_counts}
        
        # Aggregate stats
        critical = priority_dist.get('Critical', 0)
        high = priority_dist.get('High', 0)
        medium = priority_dist.get('Medium', 0)
        low = priority_dist.get('Low', 0)

        # Basic category distribution from complaints
        cat_dist = self.db.query(
            Complaint.predicted_category, func.count(Complaint.id)
        ).group_by(Complaint.predicted_category).all()
        
        category_breakdown = [
            {"category": cat or "Unknown", "count": count} for cat, count in cat_dist
        ]

        return {
            "totalComplaints": total_complaints,
            "uniqueIncidents": total_incidents,
            "workloadReduction": 85.0, # Placeholder
            "criticalIncidents": critical,
            "highPriorityIncidents": high,
            "mediumPriorityIncidents": medium,
            "lowPriorityIncidents": low,
            "categoryBreakdown": category_breakdown,
            "priorityDistribution": priority_dist,
        }

    async def get_incidents(
        self,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[Incident]:
        """Get list of incidents."""
        query = self.db.query(Incident)
        
        if priority:
            query = query.filter(Incident.priority_label.ilike(priority))
        if category:
            query = query.filter(Incident.category.ilike(f"%{category}%"))

        return query.limit(limit).all()

    async def get_incident_by_id(self, incident_id: str) -> Optional[Incident]:
        """Get a specific incident by ID."""
        return self.db.query(Incident).options(
            joinedload(Incident.complaints),
            joinedload(Incident.priority_history)
        ).filter(Incident.id == incident_id).first()

class ComplaintService:
    """Service to handle complaint submission workflow."""

    def __init__(self):
        self.db = SessionLocal()
        self.classifier = ClassificationService()
        self.clusterer = ClusteringService()
        self.priority = PriorityService()

    async def submit_complaint(self, complaint_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process new complaint: classify, find/create incident, calculate priority, save."""
        
        # 1. AI Classification
        classify_res = await self.classifier.classify(ClassifyRequest(
            text=complaint_data['title'],
            detail=complaint_data['description']
        ))
        category = classify_res.predicted_category
        confidence = classify_res.confidence

        # 2. Duplicate Detection
        existing_complaints = self.db.query(Complaint).all()
        complaints_dict = [{"id": c.id, "text": f"{c.title} {c.description}"} for c in existing_complaints]
        
        similar = await self.clusterer.find_similar(
            f"{complaint_data['title']} {complaint_data['description']}",
            complaints_dict,
            threshold=0.8
        )

        incident = None
        is_duplicate = False

        if similar:
            most_similar_id = similar[0]['id']
            existing_c = self.db.query(Complaint).filter(Complaint.id == most_similar_id).first()
            if existing_c and existing_c.incident_id:
                incident = self.db.query(Incident).filter(Incident.id == existing_c.incident_id).first()
                is_duplicate = True
                
                # Sprint 5: Add explainability
                new_complaint_similarity = similar[0].get('similarity', 0.0)
                
        if not incident:
            # Create new incident
            incident = Incident(
                id=str(uuid.uuid4()),
                incident_number=f"INC-{uuid.uuid4().hex[:6].upper()}",
                category=category,
                ward=complaint_data['ward'],
                cluster_size=1,
                priority_score=0.0,
                priority_label="Low",
                summary=complaint_data['title']
            )
            self.db.add(incident)
        else:
            # Link to existing incident and increment size
            incident.cluster_size += 1

        # 3. Calculate Priority
        priority_res = await self.priority.calculate(PriorityRequest(
            incident_id=incident.id,
            cluster_size=incident.cluster_size,
            first_complaint_date=datetime.utcnow().isoformat(),
            last_complaint_date=datetime.utcnow().isoformat(),
            category=category,
            location_hints=[complaint_data['location']]
        ))

        # Track history if score changes
        if incident.priority_score != priority_res.priority_score:
            hist = PriorityHistory(
                id=str(uuid.uuid4()),
                incident_id=incident.id,
                old_score=incident.priority_score,
                new_score=priority_res.priority_score,
                reason="Automatic update from new complaint"
            )
            self.db.add(hist)

        incident.priority_score = priority_res.priority_score
        incident.priority_label = priority_res.priority_label

        # 4. Save Complaint
        new_complaint = Complaint(
            id=str(uuid.uuid4()),
            title=complaint_data['title'],
            description=complaint_data['description'],
            location=complaint_data['location'],
            ward=complaint_data['ward'],
            image_path=complaint_data.get('image_path'),
            predicted_category=category,
            confidence=confidence,
            priority=priority_res.priority_label,
            incident=incident,
            # Sprint 5: Explainability
            similarity_score=new_complaint_similarity if is_duplicate else None,
            merge_reason=f"Matched with {most_similar_id}" if is_duplicate else None,
            merged_at=datetime.utcnow() if is_duplicate else None
        )
        
        self.db.add(new_complaint)
        self.db.commit()
        self.db.refresh(new_complaint)
        self.db.refresh(incident)

        return {
            "complaintId": new_complaint.id,
            "incidentId": incident.id,
            "predictedCategory": category,
            "priority": priority_res.priority_label,
            "confidence": confidence,
            "duplicate": is_duplicate,
            "message": "Complaint submitted successfully"
        }
