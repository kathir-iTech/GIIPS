"""
Service layer for GIIPS backend.
Handles business logic and model interactions.
"""

import json
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import joinedload

logger = logging.getLogger(__name__)

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal, Complaint, Incident, PriorityHistory
from classification.train import ComplaintClassifier
from classification.tamil_fallback import is_tamil_text, tamil_keyword_classify
from clustering.cluster import ComplaintClusterer
from priority.priority import PriorityEngine
from duplicate_detection.engine import DuplicateDetector
_AI_DEPS_AVAILABLE = True
try:
    import sentence_transformers  # noqa: F401
except ImportError:
    _AI_DEPS_AVAILABLE = False
from models import (
    ClassifyRequest, ClassifyResponse,
    ClusterRequest, ClusterResponse, ClusterAssignment,
    PriorityRequest, PriorityResponse, PriorityFactor,
    IncidentResponse
)

# --- Service Classes ---

class ClassificationService:
    _classifier = None
    @classmethod
    def get_classifier(cls) -> ComplaintClassifier:
        if cls._classifier is None:
            models_dir = Path(__file__).parent.parent / 'models' / 'classification'
            if models_dir.exists() and (models_dir / 'classifier.pkl').exists():
                try: cls._classifier = ComplaintClassifier.load(models_dir)
                except Exception: pass
        return cls._classifier

    async def classify(self, request: ClassifyRequest) -> ClassifyResponse:
        classifier = self.get_classifier()
        if classifier is None: return await self._fallback_classify(request)
        combined_text = request.text + (f" {request.detail}" if request.detail else "")

        if is_tamil_text(combined_text):
            category, keywords_matched, confidence = tamil_keyword_classify(combined_text)
            if category:
                # Phase 1.5 TEMPORARY: Tamil keyword fallback
                reason = f"Classified as {category} via Tamil keyword match (terms: {', '.join(keywords_matched)})"
                return ClassifyResponse(
                    predicted_category=category,
                    confidence=confidence,
                    top_predictions=[{"category": category, "confidence": confidence}],
                    reason=reason,
                    supporting_factors=keywords_matched,
                    method="tamil_keyword_fallback",
                )

        try:
            prediction = classifier.predict([combined_text])[0]
            probabilities = classifier.predict_proba([combined_text])[0]
            import numpy as np
            top_indices = np.argsort(probabilities)[::-1][:5]
            top_predictions = [{"category": str(classifier.classes_[idx]), "confidence": float(probabilities[idx])} for idx in top_indices]
            confidence = float(probabilities[classifier.classes_.tolist().index(prediction)])
            
            # Explainability
            reason = f"Classified as {prediction} with {confidence:.2%} confidence based on ML model content analysis."
            keywords = {'Road': ['pothole', 'road', 'street'], 'Water': ['water', 'pipe', 'leak'], 'Waste': ['garbage', 'waste', 'trash']}
            text_lower = combined_text.lower()
            supporting_factors = []
            for cat, words in keywords.items():
                if cat in prediction:
                    supporting_factors = [w for w in words if w in text_lower]
                    break
                    
            return ClassifyResponse(predicted_category=str(prediction), confidence=confidence, top_predictions=top_predictions, reason=reason, supporting_factors=supporting_factors, method="ml_model")
        except Exception: return await self._fallback_classify(request)

    async def _fallback_classify(self, request: ClassifyRequest) -> ClassifyResponse:
        text_lower = request.text.lower()
        keywords = {
            'Roads': ['pothole', 'road', 'street', 'pavement', 'speed breaker'],
            'Water Supply': ['water', 'pipe', 'leak', 'tap', 'supply'],
            'Waste Management': ['garbage', 'waste', 'trash', 'bin', 'dump', 'litter'],
            'Sanitation': ['sewage', 'drain', 'blockage', 'overflow', 'stagnant'],
            'Street Lighting': ['light', 'lamp', 'bulb', 'flickering', 'dark'],
            'Electricity': ['power', 'voltage', 'transformer', 'electric', 'cut'],
            'Public Health': ['health', 'mosquito', 'dengue', 'fogging', 'disease'],
        }
        predicted, confidence = 'Roads', 0.5
        supporting_factors = []
        for cat, words in keywords.items():
            matched = [w for w in words if w in text_lower]
            if matched:
                predicted, confidence, supporting_factors = cat, 0.75, matched
                break
        reason = f"Classified as {predicted} using heuristic fallback based on detected keywords."
        return ClassifyResponse(predicted_category=predicted, confidence=confidence, top_predictions=[{"category": predicted, "confidence": confidence}], reason=reason, supporting_factors=supporting_factors, method="heuristic_fallback")


class ClusteringService:
    _clusterer = None
    @classmethod
    def get_clusterer(cls) -> ComplaintClusterer:
        if cls._clusterer is None: cls._clusterer = ComplaintClusterer(eps=0.3, min_samples=2)
        return cls._clusterer

    async def cluster(self, request: ClusterRequest) -> ClusterResponse:
        return await self._fallback_cluster(request)

    async def _fallback_cluster(self, request: ClusterRequest) -> ClusterResponse:
        from collections import defaultdict
        buckets = defaultdict(list)
        for i, complaint in enumerate(request.complaints):
            text = complaint.get(request.text_key, '') or complaint.get('text', '')
            bucket_key = text[:50].lower() if text else 'empty'
            buckets[bucket_key].append(i)
        cluster_labels, cluster_id = {}, 0
        for key, indices in buckets.items():
            if len(indices) >= 2:
                for idx in indices: cluster_labels[idx] = cluster_id
                cluster_id += 1
            else:
                for idx in indices: cluster_labels[idx] = -1
        assignments = [ClusterAssignment(complaint_id=request.complaints[i].get('id', i), cluster_label=cluster_labels.get(i, -1), is_noise=cluster_labels.get(i, -1) == -1) for i in range(len(request.complaints))]
        return ClusterResponse(n_clusters=cluster_id, n_noise=sum(1 for a in assignments if a.is_noise), cluster_assignments=assignments, cluster_details={})

    async def find_similar(self, text: str, existing_complaints: List[Dict[str, Any]], threshold: float) -> List[Dict[str, Any]]:
        text_keywords = set(text.lower().split()[:10])
        similar = []
        for complaint in existing_complaints:
            ct = complaint.get('text', '').lower()
            ct_keywords = set(ct.split()[:10])
            overlap = len(text_keywords & ct_keywords) / max(len(text_keywords), 1)
            if overlap >= threshold * 0.5:
                similar.append({"id": complaint.get('id'), "text": ct[:100], "similarity": overlap})
        return similar[:5]


class PriorityService:
    _engine = None
    @classmethod
    def get_engine(cls) -> PriorityEngine:
        if cls._engine is None: cls._engine = PriorityEngine()
        return cls._engine

    async def calculate(self, request: PriorityRequest) -> PriorityResponse:
        engine = self.get_engine()
        result = engine.compute(
            incident_id=request.incident_id,
            cluster_size=request.cluster_size,
            first_complaint_date=request.first_complaint_date,
            last_complaint_date=request.last_complaint_date,
            category=request.category,
            location_hints=request.location_hints,
            incident_latitude=request.incident_latitude,
            incident_longitude=request.incident_longitude,
        )
        return PriorityResponse(incident_id=result.incident_id, priority_score=result.priority_score, priority_label=result.priority_label, factors=[], explanation=result.explanation)


class DashboardService:
    async def get_summary(self, db) -> Dict[str, Any]:
        total_complaints = db.query(Complaint).count()
        total_incidents = db.query(Incident).count()
        priority_counts = db.query(Incident.priority_label, func.count(Incident.id)).group_by(Incident.priority_label).all()
        priority_dist = {label: count for label, count in priority_counts}
        cat_dist = db.query(Complaint.predicted_category, func.count(Complaint.id)).group_by(Complaint.predicted_category).all()
        category_breakdown = [{"category": cat or "Unknown", "count": count} for cat, count in cat_dist]
        recent = db.query(Incident).order_by(Incident.created_at.desc()).limit(10).all()
        recent_incidents = [{
            "id": i.id, "incident_number": i.incident_number, "category": i.category,
            "ward": i.ward, "priority_score": i.priority_score, 
            "priority_label": i.priority_label, "status": i.status,
            "summary": i.summary, "days_open": i.days_open, "recommended_action": i.recommended_action
        } for i in recent]
        return {
            "totalComplaints": total_complaints,
            "uniqueIncidents": total_incidents,
            "workloadReduction": 85.0,
            "criticalIncidents": priority_dist.get('Critical', 0),
            "highPriorityIncidents": priority_dist.get('High', 0),
            "mediumPriorityIncidents": priority_dist.get('Medium', 0),
            "lowPriorityIncidents": priority_dist.get('Low', 0),
            "categoryBreakdown": category_breakdown,
            "priorityDistribution": priority_dist,
            "recentIncidents": recent_incidents
        }
    async def get_incidents(self, db, priority: Optional[str] = None, category: Optional[str] = None, limit: int = 10) -> List[Incident]:
        query = db.query(Incident)
        if priority: query = query.filter(Incident.priority_label.ilike(priority))
        if category: query = query.filter(Incident.category.ilike(f"%{category}%"))
        return query.limit(limit).all()
    async def get_incident_by_id(self, db, incident_id: str) -> Optional[Incident]:
        return db.query(Incident).options(joinedload(Incident.complaints), joinedload(Incident.priority_history)).filter(Incident.id == incident_id).first()


class DecisionService:
    async def get_executive_summary(self, db) -> Dict[str, Any]:
        critical_count = db.query(Incident).filter(Incident.priority_label == 'Critical').count()
        worst_ward = db.query(Incident.ward, func.count(Incident.id)).group_by(Incident.ward).order_by(func.count(Incident.id).desc()).first()
        emerging = db.query(Complaint.predicted_category, func.count(Complaint.id)).filter(Complaint.created_at > datetime.utcnow() - timedelta(days=7)).group_by(Complaint.predicted_category).order_by(func.count(Complaint.id).desc()).first()
        return {
            "criticalIncidentCount": critical_count,
            "worstPerformingWard": worst_ward[0] if worst_ward else "N/A",
            "emergingIssueCategory": emerging[0] if emerging else "None",
            "topRecommendation": f"Allocate resources to {worst_ward[0] if worst_ward else 'high-load areas'}."
        }
    async def get_ward_health(self, db) -> List[Dict[str, Any]]:
        wards = db.query(Incident.ward).distinct().all()
        return [{"ward": w[0], "healthScore": max(0, 100 - db.query(Incident).filter(Incident.ward == w[0]).count() * 10)} for w in wards]
    async def get_dept_workload(self, db) -> List[Dict[str, Any]]:
        from department_map import get_department
        data = db.query(Incident.category, func.count(Incident.id)).filter(Incident.status != 'resolved').group_by(Incident.category).all()
        merged: dict[str, int] = {}
        for cat, count in data:
            dept = get_department(cat)
            merged[dept] = merged.get(dept, 0) + count
        return [{"department": dept, "activeIncidents": cnt} for dept, cnt in merged.items()]

class SpatialService:
    async def get_heatmap(self, db) -> List[Dict[str, Any]]:
        data = db.query(Complaint.ward, func.avg(Complaint.latitude), func.avg(Complaint.longitude), func.count(Complaint.id)).group_by(Complaint.ward).all()
        return [{"ward": w, "count": c, "latitude": lat, "longitude": lon} for w, lat, lon, c in data if lat and lon]
    async def get_hotspots(self, db) -> List[Dict[str, Any]]:
        from collections import Counter

        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        two_weeks_ago = now - timedelta(days=14)

        complaints = db.query(
            Complaint.ward, Complaint.predicted_category,
            Complaint.created_at, Complaint.latitude, Complaint.longitude,
        ).filter(Complaint.ward.isnot(None)).all()

        grouped: Dict[str, List] = {}
        for c in complaints:
            grouped.setdefault(c.ward, []).append(c)

        priority = PriorityEngine()
        results: List[Dict[str, Any]] = []

        for ward, items in grouped.items():
            n = len(items)
            cat_counter = Counter(it.predicted_category for it in items)
            modal_category = cat_counter.most_common(1)[0][0] if cat_counter else 'General Construction'

            dates = [it.created_at for it in items if it.created_at]
            first_date = min(dates).isoformat() if dates else now.isoformat()
            last_date = max(dates).isoformat() if dates else now.isoformat()

            # Severity via PriorityEngine (considers count + category + age)
            ward_result = priority.compute(
                incident_id=f"ward-{ward}",
                cluster_size=n,
                first_complaint_date=first_date,
                last_complaint_date=last_date,
                category=modal_category,
                location_hints=[ward.lower()],
                incident_latitude=None,
                incident_longitude=None,
            )

            if ward_result.priority_score >= 75:
                severity = "Critical"
            elif ward_result.priority_score >= 55:
                severity = "High"
            elif ward_result.priority_score >= 35:
                severity = "Medium"
            else:
                severity = "Low"

            # Growth: week-over-week
            recent = sum(1 for it in items if it.created_at and it.created_at >= week_ago)
            prev = sum(1 for it in items if it.created_at and two_weeks_ago <= it.created_at < week_ago)
            if prev > 0:
                growth = round(((recent - prev) / prev) * 100.0, 1)
            elif recent > 0:
                growth = 100.0
            else:
                growth = 0.0

            avg_lat = sum(it.latitude for it in items if it.latitude) / n
            avg_lon = sum(it.longitude for it in items if it.longitude) / n

            results.append({
                "ward": ward,
                "latitude": round(avg_lat, 6) if avg_lat else 12.0,
                "longitude": round(avg_lon, 6) if avg_lon else 78.0,
                "count": n,
                "growth": growth,
                "severity": severity,
            })

        return results
    async def get_forecast(self, db, days: int) -> List[Dict[str, Any]]:
        from prediction.engine import PredictiveEngine
        engine = PredictiveEngine()
        now = datetime.utcnow()
        four_weeks_ago = now - timedelta(weeks=4)
        rows = db.query(
            Complaint.ward, Complaint.created_at
        ).filter(
            Complaint.created_at >= four_weeks_ago,
            Complaint.ward.isnot(None)
        ).all()
        from collections import defaultdict
        ward_weekly: Dict[str, List[int]] = defaultdict(lambda: [0, 0, 0, 0])
        for r in rows:
            week_index = min(3, (now - r.created_at).days // 7)
            ward_weekly[r.ward][week_index] += 1
        results = []
        for ward, history in ward_weekly.items():
            history = history[::-1]
            forecast_result = engine.forecast_complaints('week', history=history)
            predicted_volume = forecast_result.get('predicted_volume', 0)
            confidence = forecast_result.get('confidence', 0)
            recent_avg = sum(history[-2:]) / max(len(history[-2:]), 1)
            trend = 'worsening' if predicted_volume > recent_avg else 'stable'
            results.append({
                "district": ward,
                "ward": ward,
                "forecast": round(predicted_volume, 1),
                "confidence": round(confidence, 4),
                "trend": trend,
                "expected_to_worsen": trend == 'worsening',
                "historical": [round(h, 1) for h in history],
                "predicted": [round(predicted_volume, 1)]
            })
        results.sort(key=lambda r: r['confidence'], reverse=True)
        return results
    async def get_risk_analysis(self, db) -> List[Dict[str, Any]]:
        wards = await self.get_heatmap(db)
        max_count = max((w["count"] for w in wards), default=1)
        from priority.priority import PriorityEngine
        priority = PriorityEngine()
        results = []
        for w in wards:
            density_score = min(100, (w["count"] / max_count) * 100) if max_count > 0 else 0
            ward_result = priority.compute(
                incident_id=f"ward-{w['ward']}",
                cluster_size=w["count"],
                first_complaint_date=datetime.utcnow().isoformat(),
                last_complaint_date=datetime.utcnow().isoformat(),
                category="General",
                location_hints=[w["ward"].lower()],
                incident_latitude=None,
                incident_longitude=None,
            )
            severity_bonus = ward_result.priority_score * 0.3
            riskScore = round(min(100, density_score + severity_bonus), 1)
            healthScore = round(max(0, 100 - riskScore), 1)
            results.append({
                "ward": w["ward"],
                "district": w["ward"],
                "riskScore": riskScore,
                "risk_score": riskScore,
                "healthScore": healthScore,
                "health_score": healthScore,
                "complaint_count": w["count"]
            })
        return results
    async def simulate_resources(self, db, additional_teams: int) -> Dict[str, Any]:
        unresolved = db.query(Incident).filter(Incident.status != 'resolved').count()
        total = db.query(Incident).count()
        if total == 0:
            return {
                "projectedImpact": "No complaint data available for simulation.",
                "estimatedReduction": 0,
                "currentBacklog": 0,
                "teamsAdded": additional_teams
            }
        resolution_rate = (total - unresolved) / max(total, 1)
        avg_throughput_per_team = resolution_rate * 10
        added_capacity = additional_teams * avg_throughput_per_team
        new_backlog = max(0, unresolved - added_capacity)
        reduction_pct = round(((unresolved - new_backlog) / unresolved) * 100, 1) if unresolved > 0 else 0
        return {
            "projectedImpact": f"Adding {additional_teams} team(s) could reduce backlog by ~{reduction_pct}% ({added_capacity:.0f} additional complaints resolved).",
            "estimatedReduction": round(added_capacity),
            "currentBacklog": unresolved,
            "teamsAdded": additional_teams,
            "newProjectedBacklog": round(new_backlog)
        }

class ComplaintService:
    def __init__(self):
        self.classifier = ClassificationService()
        try:
            self.duplicate_detector = DuplicateDetector()
        except Exception as exc:
            logger.warning("DuplicateDetector initialisation failed: %s. Duplicate detection disabled for this session.", exc)
            self.duplicate_detector = None
        self.priority = PriorityService()

    async def submit_complaint(self, db, complaint_data: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
        classify_res = await self.classifier.classify(ClassifyRequest(text=complaint_data['title'], detail=complaint_data['description']))
        category, confidence = classify_res.predicted_category, classify_res.confidence

        incident_id, dup_conf = None, 0.0
        is_duplicate = False

        if self.duplicate_detector is not None:
            try:
                ninety_days_ago = datetime.utcnow() - timedelta(days=90)
                existing_complaints = (
                    db.query(Complaint)
                    .filter(
                        and_(
                            Complaint.created_at >= ninety_days_ago,
                            or_(
                                Complaint.ward == complaint_data.get('ward'),
                                Complaint.predicted_category == category,
                            ),
                        )
                    )
                    .order_by(Complaint.created_at.desc())
                    .limit(1000)
                    .all()
                )
                formatted_existing = [{
                    'title': c.title, 'description': c.description,
                    'lat': getattr(c, 'latitude', 0) or 0, 'lon': getattr(c, 'longitude', 0) or 0,
                    'category': c.predicted_category, 'ward': c.ward,
                    'incident_id': c.incident_id
                } for c in existing_complaints]
                incident_id, dup_conf = self.duplicate_detector.detect_duplicates(complaint_data, formatted_existing)
                is_duplicate = dup_conf > 0.8
            except Exception as exc:
                logger.warning("Duplicate detection failed: %s. Continuing without duplicate detection.", exc)

        incident = None

        if is_duplicate and incident_id:
            incident = db.query(Incident).filter(Incident.id == incident_id).first()
            if incident:
                incident.cluster_size += 1
                merge_reason = f"Automated merge based on {dup_conf:.2%} confidence score."
            else:
                is_duplicate = False

        if not incident:
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
            db.add(incident)
            merge_reason = "New incident created."

        priority_res = await self.priority.calculate(PriorityRequest(
            incident_id=incident.id,
            cluster_size=incident.cluster_size,
            first_complaint_date=datetime.utcnow().isoformat(),
            last_complaint_date=datetime.utcnow().isoformat(),
            category=category,
            location_hints=[complaint_data.get('location', '')],
            incident_latitude=complaint_data.get('latitude'),
            incident_longitude=complaint_data.get('longitude'),
        ))
        if incident.priority_score != priority_res.priority_score:
            db.add(PriorityHistory(id=str(uuid.uuid4()), incident_id=incident.id, old_score=incident.priority_score, new_score=priority_res.priority_score, reason="Automatic update"))
        incident.priority_score, incident.priority_label = priority_res.priority_score, priority_res.priority_label
        
        new_complaint = Complaint(
            id=str(uuid.uuid4()), 
            title=complaint_data['title'], 
            description=complaint_data['description'], 
            location=complaint_data.get('location', ''), 
            ward=complaint_data['ward'], 
            predicted_category=category, 
            confidence=confidence, 
            incident=incident,
            merge_reason=merge_reason,
            user_id=user_id
        )
        db.add(new_complaint)
        db.commit()
        db.refresh(new_complaint)
        db.refresh(incident)
        
        return {
            "complaintId": new_complaint.id, 
            "incidentId": incident.id, 
            "predictedCategory": category, 
            "priority": incident.priority_label, 
            "confidence": dup_conf if is_duplicate else confidence, 
            "duplicate": is_duplicate, 
            "message": "Complaint processed successfully."
        }
