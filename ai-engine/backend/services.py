"""
Service layer for GIIPS backend.

Handles business logic and model interactions.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from database import SessionLocal, Complaint, Incident
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


class DashboardService:
    """Service for dashboard data."""

    async def get_summary(self) -> Dict[str, Any]:
        """Get dashboard summary statistics."""
        outputs_dir = Path(__file__).parent.parent / 'outputs'
        data_file = outputs_dir / 'dashboard_data.json'

        data = {}
        if data_file.exists():
            try:
                with open(data_file, 'r') as f:
                    data = json.load(f)
            except Exception:
                pass

        # Base values from data or defaults
        total_complaints = data.get('total_complaints', 100)
        unique_incidents = data.get('unique_incidents', 15)
        workload_reduction = data.get('workload_reduction', 85.0)
        critical_incidents = data.get('critical_incidents', 3)
        high_priority_incidents = data.get('high_priority_incidents', 5)
        
        # Handle priority distribution if present
        priority_dist = data.get('priority_distribution', {"Critical": 3, "High": 5, "Medium": 4, "Low": 3})
        medium_priority = priority_dist.get('Medium', 4)
        low_priority = priority_dist.get('Low', 3)

        # Category breakdown with colors
        category_colors = {
            'Road Infrastructure': '#1e293b',
            'Water Supply': '#0369a1',
            'Waste Management': '#7c3aed',
            'Sanitation': '#b45309',
            'Street Lighting': '#059669',
            'Public Works': '#be123c'
        }
        cat_dist = data.get('category_distribution', [
            {"category": "Road Infrastructure", "count": 30},
            {"category": "Water Supply", "count": 25},
            {"category": "Waste Management", "count": 20},
            {"category": "Street Lighting", "count": 15},
            {"category": "Sanitation", "count": 10}
        ])
        category_breakdown = [
            {"category": c['category'], "count": c['count'], "color": category_colors.get(c['category'], '#64748b')}
            for c in cat_dist
        ]

        # Sample values for missing fields
        trend_data = [
            {"date": "2024-01", "complaints": 95, "incidents": 15},
            {"date": "2024-02", "complaints": 127, "incidents": 18},
            {"date": "2024-03", "complaints": 143, "incidents": 22},
            {"date": "2024-04", "complaints": 108, "incidents": 16},
            {"date": "2024-05", "complaints": 89, "incidents": 12},
            {"date": "2024-06", "complaints": total_complaints, "incidents": unique_incidents},
        ]
        
        ward_breakdown = [
            {"ward": "W1", "count": 12},
            {"ward": "W2", "count": 8},
            {"ward": "W3", "count": 15},
            {"ward": "W4", "count": 5},
            {"ward": "W5", "count": 7},
        ]

        # Recent incidents
        incidents_list = await self.get_incidents(limit=5)
        recent_incidents = []
        for inc in incidents_list:
            recent_incidents.append({
                "id": inc.id,
                "incidentNumber": inc.incident_number,
                "category": inc.category,
                "clusterSize": inc.cluster_size,
                "ward": inc.ward,
                "daysOpen": inc.days_open,
                "priorityScore": inc.priority_score,
                "priorityLabel": inc.priority_label,
                "summary": inc.summary,
                "recommendedAction": inc.recommended_action,
                "status": inc.status,
                "complaints": [
                    {
                        "id": c.id,
                        "complaintNumber": getattr(c, 'complaint_number', ''),
                        "text": getattr(c, 'text', ''),
                        "similarityScore": getattr(c, 'similarity_score', 0.0),
                        "dateReceived": getattr(c, 'date_received', '')
                    } for c in inc.complaints
                ]
            })

        return {
            "totalComplaints": total_complaints,
            "uniqueIncidents": unique_incidents,
            "workloadReduction": workload_reduction,
            "criticalIncidents": critical_incidents,
            "highPriorityIncidents": high_priority_incidents,
            "mediumPriorityIncidents": medium_priority,
            "lowPriorityIncidents": low_priority,
            "avgDaysOpen": 12,
            "avgResolutionScore": 75,
            "trendData": trend_data,
            "categoryBreakdown": category_breakdown,
            "wardBreakdown": ward_breakdown,
            "recentIncidents": recent_incidents,
        }

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
            incident=incident
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
