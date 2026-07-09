"""
Arq worker for background ML inference (classify, dup-detect, priority).
Runs as:  arq ai_engine.backend.worker.WorkerSettings
"""

import os
import sys
import json
import uuid
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger("arq.worker")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

os.environ.setdefault("GIIPS_JWT_SECRET", "arq-worker-secret")
os.environ.setdefault("GIIPS_ALLOWED_ORIGINS", "*")

from services import ClassificationService, DuplicateDetector, PriorityService as PriorityScorer
from database import SessionLocal, Complaint, Incident, PriorityHistory
from models import ClassifyRequest, PriorityRequest
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session


JOB_TTL = 3600  # 1 hour expiry for status keys


def _format_existing(c):
    return {
        'title': c.title, 'description': c.description,
        'lat': getattr(c, 'latitude', 0) or 0,
        'lon': getattr(c, 'longitude', 0) or 0,
        'category': c.predicted_category, 'ward': c.ward,
        'incident_id': c.incident_id,
    }


async def process_complaint(ctx: Dict, complaint_id: str, user_id: Optional[str]) -> Dict[str, Any]:
    redis = ctx.get("redis")
    job_key = f"complaint:status:{complaint_id}"

    await _set_status(redis, job_key, "processing", detail="Starting ML pipeline")

    db: Session = SessionLocal()
    try:
        complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if not complaint:
            await _set_status(redis, job_key, "failed", detail="Complaint not found")
            return {"error": "not_found"}

        data = {
            "title": complaint.title,
            "description": complaint.description,
            "location": complaint.location or "",
            "ward": complaint.ward or "",
            "lat": getattr(complaint, "latitude", 0) or 0,
            "lon": getattr(complaint, "longitude", 0) or 0,
        }

        await _set_status(redis, job_key, "processing", detail="Classifying complaint")
        classifier = ClassificationService()
        classify_res = await classifier.classify(ClassifyRequest(text=data["title"], detail=data["description"]))
        category = classify_res.predicted_category
        confidence = classify_res.confidence

        incident_id = None
        dup_conf = 0.0
        is_duplicate = False
        duplicate_detector = None
        try:
            duplicate_detector = DuplicateDetector()
        except Exception:
            logger.warning("DuplicateDetector init failed, skipping")

        if duplicate_detector is not None:
            try:
                ninety_days_ago = datetime.utcnow() - timedelta(days=90)
                existing = (
                    db.query(Complaint)
                    .filter(
                        and_(
                            Complaint.created_at >= ninety_days_ago,
                            or_(
                                Complaint.ward == data.get("ward"),
                                Complaint.predicted_category == category,
                            ),
                        )
                    )
                    .order_by(Complaint.created_at.desc())
                    .limit(1000)
                    .all()
                )
                formatted = [_format_existing(c) for c in existing]
                incident_id, dup_conf = duplicate_detector.detect_duplicates(data, formatted)
                is_duplicate = dup_conf > 0.8
            except Exception as exc:
                logger.warning("Duplicate detection failed: %s", exc)

        await _set_status(redis, job_key, "processing", detail="Updating incident")

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
                ward=data["ward"],
                cluster_size=1,
                priority_score=0.0,
                priority_label="Low",
                summary=data["title"],
            )
            db.add(incident)
            merge_reason = "New incident created."

        priority_scorer = PriorityScorer()
        priority_res = await priority_scorer.calculate(
            PriorityRequest(
                incident_id=incident.id,
                cluster_size=incident.cluster_size,
                first_complaint_date=datetime.utcnow().isoformat(),
                last_complaint_date=datetime.utcnow().isoformat(),
                category=category,
                location_hints=[data.get("location", "")],
            )
        )

        if incident.priority_score != priority_res.priority_score:
            db.add(
                PriorityHistory(
                    id=str(uuid.uuid4()),
                    incident_id=incident.id,
                    old_score=incident.priority_score,
                    new_score=priority_res.priority_score,
                    reason="Automatic update in worker",
                )
            )
        incident.priority_score = priority_res.priority_score
        incident.priority_label = priority_res.priority_label

        complaint.predicted_category = category
        complaint.confidence = confidence
        complaint.incident_id = incident.id
        complaint.priority = incident.priority_label
        complaint.merge_reason = merge_reason if is_duplicate else None
        complaint.user_id = user_id

        db.commit()
        db.refresh(complaint)
        db.refresh(incident)

        result = {
            "complaintId": complaint.id,
            "incidentId": incident.id,
            "predictedCategory": category,
            "priority": incident.priority_label,
            "confidence": dup_conf if is_duplicate else confidence,
            "duplicate": is_duplicate,
            "message": "Complaint processed successfully.",
        }

        await _set_status(redis, job_key, "completed", detail="ML pipeline finished", result=result)
        logger.info("Processed complaint %s -> incident %s", complaint.id, incident.id)
        return result

    except Exception as exc:
        logger.exception("ML pipeline failed for complaint %s", complaint_id)
        await _set_status(redis, job_key, "failed", detail=str(exc))
        return {"error": str(exc)}

    finally:
        db.close()


async def _set_status(redis, key: str, status: str, detail: str = "", result: dict = None):
    payload = {"status": status, "detail": detail, "updated_at": datetime.utcnow().isoformat()}
    if result:
        payload["result"] = result
    try:
        await redis.set(key, json.dumps(payload))
        await redis.expire(key, JOB_TTL)
    except Exception:
        pass


class WorkerSettings:
    functions = [process_complaint]
    poll_delay = 0.5
    max_jobs = 10
    burst = False
