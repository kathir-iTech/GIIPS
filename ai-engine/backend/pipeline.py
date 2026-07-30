"""
Inline ML pipeline for complaint processing.
Runs as an asyncio.create_task inside the same uvicorn process,
avoiding the need for a separate arq worker service on Render's free tier.

Provides Redis-backed status updates so GET /complaints/{id}/status
continues to work exactly as before.

See worker.py for the original arq-based implementation (kept for reference
if a future scale-up needs a dedicated worker process).
"""

import json
import logging
import math
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session

from database import SessionLocal, Complaint, Incident, PriorityHistory, Geofence, User, AuditLog
from job_queue import get_pool
from models import ClassifyRequest, PriorityRequest
from services import ClassificationService, DuplicateDetector, PriorityService as PriorityScorer
from department_map import get_department

logger = logging.getLogger(__name__)

JOB_TTL = 3600  # 1 hour expiry for status keys


def _format_existing(c):
    return {
        'title': c.title, 'description': c.description,
        'lat': getattr(c, 'latitude', 0) or 0,
        'lon': getattr(c, 'longitude', 0) or 0,
        'category': c.predicted_category, 'ward': c.ward,
        'incident_id': c.incident_id,
    }


async def _set_status(complaint_id: str, status: str, detail: str = "", result: dict = None):
    """Write status to Redis with TTL. Used by both the route and the inline pipeline."""
    pool = get_pool()
    if pool is None:
        logger.warning("Redis pool not available — skipping status update for %s", complaint_id)
        return
    key = f"complaint:status:{complaint_id}"
    payload = {"status": status, "detail": detail, "updated_at": datetime.utcnow().isoformat()}
    if result:
        payload["result"] = result
    try:
        await pool.set(key, json.dumps(payload))
        await pool.expire(key, JOB_TTL)
    except Exception as e:
        logger.warning("Failed to update Redis status for %s: %s", complaint_id, e)


async def process_complaint_pipeline(complaint_id: str, user_id: Optional[str] = None):
    """Full ML pipeline: classify → duplicate detection → incident create/merge → priority scoring.
    Designed to run as asyncio.create_task() inside the same process as uvicorn."""
    await _set_status(complaint_id, "processing", detail="Starting ML pipeline")

    db: Session = SessionLocal()
    try:
        complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if not complaint:
            await _set_status(complaint_id, "failed", detail="Complaint not found")
            return

        data = {
            "title": complaint.title,
            "description": complaint.description,
            "location": complaint.location or "",
            "ward": complaint.ward or "",
            "lat": getattr(complaint, "latitude", 0) or 0,
            "lon": getattr(complaint, "longitude", 0) or 0,
        }

        await _set_status(complaint_id, "processing", detail="Classifying complaint")
        classifier = ClassificationService()
        classify_res = await classifier.classify(ClassifyRequest(text=data["title"], detail=data["description"]))
        category = classify_res.predicted_category
        confidence = classify_res.confidence
        department = get_department(category)

        # Urgency keyword detection
        urgency_keywords = ["fire", "flood", "collapse", "accident", "gas leak", "electrocution", "medical", "emergency", "blast", "building collapse"]
        complaint_full_text = f"{data['title']} {data.get('description', '')}"
        complaint.urgency_flag = "HIGH" if any(kw in complaint_full_text.lower() for kw in urgency_keywords) else "LOW"

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

        await _set_status(complaint_id, "processing", detail="Updating incident")

        incident = None
        if is_duplicate and incident_id:
            incident = db.query(Incident).filter(Incident.id == incident_id).first()
            if incident:
                # FEATURE 11: max 200 cluster cap
                if incident.cluster_size >= 200:
                    sibling = Incident(
                        id=str(uuid.uuid4()),
                        incident_number=f"INC-{uuid.uuid4().hex[:6].upper()}",
                        category=category,
                        ward=data["ward"],
                        cluster_size=1,
                        priority_score=0.0,
                        priority_label="Low",
                        summary=data["title"],
                        sibling_of=incident.id,
                    )
                    db.add(sibling)
                    incident = sibling
                    merge_reason = "Cluster size cap (200) hit, created sibling"
                    try:
                        audit = AuditLog(id=str(uuid.uuid4()), user_id=None, user_email=None, role="system", action="cluster_cap_sibling", target=incident.id, details=f"Cluster size cap (200) hit for incident {incident_id}, created sibling", status="success")
                        db.add(audit)
                    except Exception:
                        logger.warning("Failed to write cluster cap audit log")
                else:
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
        db_user = db.query(User).filter(User.id == user_id).first() if user_id else None
        trust_score = getattr(db_user, 'trust_score', None) if db_user else None
        priority_res = await priority_scorer.calculate(
            PriorityRequest(
                incident_id=incident.id,
                cluster_size=incident.cluster_size,
                first_complaint_date=datetime.utcnow().isoformat(),
                last_complaint_date=datetime.utcnow().isoformat(),
                category=category,
                location_hints=[data.get("location", "")],
                incident_latitude=data.get("lat"),
                incident_longitude=data.get("lon"),
                trust_score=trust_score,
            )
        )

        if incident.priority_score != priority_res.priority_score:
            db.add(
                PriorityHistory(
                    id=str(uuid.uuid4()),
                    incident_id=incident.id,
                    old_score=incident.priority_score,
                    new_score=priority_res.priority_score,
                    reason="Automatic update in pipeline",
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

        # Urgency priority boost
        if complaint.urgency_flag == "HIGH":
            incident.priority_score = min(100, (incident.priority_score or 0) + 5)
            if incident.priority_score >= 70:
                incident.priority_label = "CRITICAL"
            elif incident.priority_score >= 50:
                incident.priority_label = "HIGH"

        # F11: Predict resolution time based on category historical avg + department backlog
        cat_avg = db.query(func.avg(Incident.days_open)).filter(
            Incident.category == category,
            Incident.status == "resolved"
        ).scalar() or 30.0
        dept_backlog = db.query(Incident).filter(
            Incident.category == category,
            Incident.status.in_(["open", "in-progress"])
        ).count()
        complaint.predicted_resolution_days = round(cat_avg * (1 + dept_backlog * 0.05), 1)

        # F17: Auto-tag complaint based on content analysis
        auto_tags = set()
        full_text = f"{complaint.title} {complaint.description}".lower()
        flood_kw = ["flood", "rain", "water logging", "drainage", "sewage"]
        if any(k in full_text for k in flood_kw):
            auto_tags.add("monsoon")
        landmarks = ["school", "temple", "church", "mosque", "hospital", "market", "park", "bus stand", "railway station"]
        for lm in landmarks:
            if lm in full_text:
                auto_tags.add(f"near-{lm.replace(' ', '-')}")
        if incident.cluster_size > 10:
            auto_tags.add("high-impact")
        if incident.days_open > 30:
            auto_tags.add("chronic")
        existing_tags = set()
        if complaint.tags:
            try:
                existing_tags = set(json.loads(complaint.tags))
            except (json.JSONDecodeError, TypeError):
                existing_tags = set(t.strip() for t in complaint.tags.split(",") if t.strip())
        all_tags = list(existing_tags | auto_tags)[:5]
        complaint.tags = json.dumps(all_tags)

        # Create notification for the citizen when complaint is processed
        if user_id:
            from routes import _create_notification, _notify_department_officers, _check_aging_notifications
            notif_data = {"incident_number": incident.incident_number, "is_duplicate": is_duplicate}
            if is_duplicate:
                notif_data["merge_reason"] = merge_reason
            _create_notification(
                db, user_id, "created" if not is_duplicate else "merged",
                complaint_id=complaint.id,
                data=notif_data,
            )

            # Notify officers in the department about new complaint
            _notify_department_officers(
                db, department, "complaint_assigned",
                data={
                    "complaint_id": complaint.id,
                    "incident_number": incident.incident_number,
                    "incident_id": incident.id,
                    "category": category,
                    "ward": complaint.ward,
                    "title": complaint.title,
                }
            )
            _check_aging_notifications(db, department)

        # Geofence check: if complaint falls within any executive-defined geofence, notify
        comp_lat = getattr(complaint, "latitude", None)
        comp_lng = getattr(complaint, "longitude", None)
        if comp_lat is not None and comp_lng is not None:
            geofences = db.query(Geofence).all()
            for gf in geofences:
                dlat = math.radians(comp_lat - gf.lat)
                dlng = math.radians(comp_lng - gf.lng)
                a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(gf.lat)) * math.cos(math.radians(comp_lat)) * math.sin(dlng / 2) ** 2
                c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                distance_m = 6371000 * c
                if distance_m <= gf.radius_meters:
                    _create_notification(
                        db, gf.created_by, "geofence_alert",
                        complaint_id=complaint.id,
                        data={
                            "geofence_label": gf.label,
                            "complaint_id": complaint.id,
                            "title": complaint.title,
                            "category": category,
                            "distance_m": round(distance_m, 1),
                        },
                    )

        # FEATURE 10: auto-assigned
        # FEATURE 15: shift schedule
        available_officers = db.query(User).filter(
            User.role == "Officer",
            User.department == department,
            User.availability == "available",
            User.status == "active",
        ).all()
        if available_officers:
            current_hour = datetime.utcnow().hour
            if 6 <= current_hour < 14:
                current_shift_period = "morning"
            elif 14 <= current_hour < 22:
                current_shift_period = "afternoon"
            else:
                current_shift_period = "night"
            def officer_sort_key(o):
                on_shift = 0 if o.current_shift == current_shift_period else 1
                open_count = db.query(Incident).filter(Incident.accepted_by == o.id, Incident.status.in_(["open", "in-progress"])).count()
                return (on_shift, open_count)
            available_officers.sort(key=officer_sort_key)
            best = available_officers[0]
            incident.accepted_by = best.id
            incident.accepted_at = datetime.utcnow()
            try:
                audit = AuditLog(id=str(uuid.uuid4()), user_id=best.id, user_email=best.email, role="Officer", action="incident_auto_assigned", target=incident.id, details=f"Auto-assigned to {best.full_name} (department: {department})", status="success")
                db.add(audit)
            except Exception:
                logger.warning("Failed to write auto-assign audit log")
        else:
            logger.warning("No available officers for department: %s", department)

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
            "cluster_size": incident.cluster_size,
            "incident_status": incident.status,
        }

        await _set_status(complaint_id, "completed", detail="ML pipeline finished", result=result)
        logger.info("Processed complaint %s -> incident %s (department: %s)", complaint.id, incident.id, department)

    except Exception as exc:
        logger.exception("ML pipeline failed for complaint %s", complaint_id)
        await _set_status(complaint_id, "failed", detail=str(exc))

    finally:
        db.close()
