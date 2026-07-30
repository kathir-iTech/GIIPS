"""
API route definitions for GIIPS backend.
"""

import os
import asyncio
import json
import re
import uuid
import time
import random
import logging
from collections import Counter
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Request, Response, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, extract, text, or_, case
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from pydantic import BaseModel

from database import get_db, User, Incident, Complaint, AuditLog, DepartmentMetrics, Notification, PriorityHistory, IncidentUpdate, IncidentComment, KpiTarget, Geofence, ComplaintDraft, PushSubscription, ZONE_BY_WARD
from models import (
    ClassifyRequest, ClassifyResponse,
    ClusterRequest, ClusterResponse, ClusterAssignment,
    PriorityRequest, PriorityResponse, PriorityFactor,
    IncidentResponse,
    UserRegister, UserLogin, UserResponse, OfficerCreate, OfficerUpdate, ProfileUpdate,
    PredictionSummaryResponse,
    KnowledgeSummaryResponse,
    DecisionSupportSummaryResponse,
    CopilotChatRequest,
    CopilotChatResponse,
    MergeIncidentsRequest,
    MergeSingleRequest,
    NotificationResponse,
    UpdateStatusRequest,
    IncidentUpdateRequest,
    RateComplaintRequest,
    BulkUpdateRequest,
    UpdateComplaintRequest,
    NotificationPrefsRequest,
    NoteUpdateRequest,
    TagsUpdateRequest,
    AvailabilityUpdateRequest,
    SkillsUpdateRequest,
    VerifyEmailRequest,
    WithdrawRequest,
    CategoryCorrectRequest,
)
from schemas import ComplaintCreate, ComplaintSubmissionResponse, SubmissionAcceptedResponse, ComplaintProcessingStatus, EscalateRequest, AppealRequest, VerifyResolutionRequest, TrackComplaintResponse, PublicStatsResponse, TimelineEvent, ZoneStat, CategoryStat, HourStat, DayStat, FunnelStage
from job_queue import get_complaint_status, get_pool
from rate_limiter import check_auth_rate_limit, check_complaint_rate_limit, check_verify_rate_limit, check_track_rate_limit, check_appeal_rate_limit, check_reopen_rate_limit, check_search_rate_limit, check_copilot_rate_limit, check_public_stats_rate_limit, check_track_public_rate_limit
from constants import AGING_WARNING_DAYS, AGING_CRITICAL_DAYS, SLA_PRIORITY_BUMP
from department_map import (
    get_department, get_department_slug, get_slug_for_department,
    CATEGORY_DEPT_MAP, DEPARTMENT_SLUGS, SLUG_TO_DISPLAY, get_i18n_key
)
from officer_routing import route_complaint
from pipeline import process_complaint_pipeline
from vapid import get_vapid_keys
from services import (
    ClassificationService,
    ClusteringService,
    PriorityService,
    DashboardService,
    DecisionService,
    SpatialService
)
from auth_service import hash_password, verify_password, create_access_token, create_ws_token, verify_token, set_auth_cookie, clear_auth_cookie
from prediction.engine import PredictiveEngine
from knowledge.engine import GovernanceKnowledgeEngine
from decision.support import DecisionSupportEngine
from copilot.engine import CopilotEngine
from storage import S3Storage, validate_file
from ws_manager import manager

logger = logging.getLogger(__name__)

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Extract JWT from httpOnly cookie first, fall back to Authorization header."""
    token = request.cookies.get("access_token")
    if not token:
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization")
        token = authorization.split(" ")[1]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    db_user = db.query(User).filter(User.email == payload["sub"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


def _write_audit_log(db: Session, user_id: Optional[str], user_email: Optional[str], role: Optional[str], action: str, target: Optional[str], status: str = "success", details: Optional[str] = None):
    """Write an audit log entry to the database."""
    try:
        log = AuditLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            user_email=user_email,
            role=role,
            action=action,
            target=target,
            details=details,
            status=status,
        )
        db.add(log)
        db.commit()
    except Exception:
        logger.error("Audit log write failed for action=%s target=%s", action, target)
        db.rollback()


def _create_notification(db: Session, user_id: str, notification_type: str, complaint_id: Optional[str] = None, data: Optional[dict] = None):
    """Create an in-app notification for a user.
    Uses flush (not commit) so it does not interfere with the caller's transaction.
    Respects the user's notify_status_updates preference.
    
    Smart batching: if 2+ unread notifications exist for the same citizen within
    the last 5 minutes, merges into the most recent one instead of creating new."""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.notify_status_updates:
            return

        # Smart batching check — only for non-officer notifications (citizen-facing)
        five_min_ago = datetime.utcnow() - timedelta(minutes=5)
        recent_unread = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False,
            Notification.created_at >= five_min_ago,
        ).order_by(Notification.created_at.desc()).limit(5).all()

        if len(recent_unread) >= 2:
            # Merge into the most recent unread notification
            target = recent_unread[0]
            existing_data = {}
            if target.data:
                try:
                    existing_data = json.loads(target.data)
                except (json.JSONDecodeError, TypeError):
                    existing_data = {}
            if not isinstance(existing_data, dict):
                existing_data = {}
            batch_list = existing_data.get("batched_updates", [])
            new_entry = {
                "type": notification_type,
                "complaint_id": complaint_id,
                "data": data,
            }
            batch_list.append(new_entry)
            existing_data["batched_updates"] = batch_list
            existing_data["batch_count"] = len(batch_list) + 1
            target.data = json.dumps(existing_data)
            target.batched = True
            return

        notif = Notification(
            id=str(uuid.uuid4()),
            user_id=user_id,
            complaint_id=complaint_id,
            type=notification_type,
            data=json.dumps(data) if data else None,
            is_read=False,
        )
        db.add(notif)
        db.flush()
        try:
            asyncio.get_running_loop().create_task(
                manager.broadcast("notification_new", {
                    "user_id": user_id,
                    "notification_type": notification_type,
                    "complaint_id": complaint_id,
                    "notification_id": notif.id,
                })
            )
        except RuntimeError:
            pass
    except Exception:
        logger.error("Notification creation failed for user=%s type=%s", user_id, notification_type)


def _get_department_officers(db: Session, department: str) -> list[User]:
    """Return active officers assigned to a given department."""
    return db.query(User).filter(
        User.role == "Officer",
        User.department == department,
        User.status == "active"
    ).all()


def _label_for_score(score: float) -> str:
    """Map a priority score (0-100) to a label."""
    if score >= 80:
        return "Critical"
    if score >= 60:
        return "High"
    if score >= 40:
        return "Medium"
    return "Low"


def _notify_department_officers(db: Session, department: str, notification_type: str, data: Optional[dict] = None):
    """Create a notification for every active officer in a department."""
    for officer in _get_department_officers(db, department):
        _create_notification(db, officer.id, notification_type, data=data)


def _check_aging_notifications(db: Session, department: str):
    """Create aging-warning / aging-critical notifications for officers in a department."""
    dept_slug = get_slug_for_department(department)
    dept_categories = [cat for cat, slug in CATEGORY_DEPT_MAP.items() if slug == dept_slug]

    if not dept_categories:
        return

    incidents = db.query(Incident).filter(
        Incident.category.in_(dept_categories),
        Incident.status == "open"
    ).all()

    officers = _get_department_officers(db, department)
    if not officers or not incidents:
        return

    officer_ids = {o.id for o in officers}

    # Fetch ALL existing aging-type notifications for these officers at once
    # (avoids a slow per-incident LIKE query on JSON text)
    all_existing = db.query(Notification).filter(
        Notification.user_id.in_(officer_ids),
        Notification.type.in_(["aging_warning", "aging_critical"]),
    ).all()

    # Build a set of (officer_id, incident_id) already notified
    already_notified = set()
    for n in all_existing:
        if n.data:
            try:
                nd = json.loads(n.data)
                iid = nd.get("incident_id")
                if iid:
                    already_notified.add((n.user_id, iid))
            except (json.JSONDecodeError, TypeError):
                continue

    for incident in incidents:
        days = incident.days_open or 0
        if days < AGING_WARNING_DAYS:
            continue
        aging_type = "aging_critical" if days >= AGING_CRITICAL_DAYS else "aging_warning"

        for officer in officers:
            if (officer.id, incident.id) not in already_notified:
                _create_notification(
                    db, officer.id, aging_type,
                    data={
                        "incident_id": incident.id,
                        "incident_number": incident.incident_number,
                        "category": incident.category,
                        "ward": incident.ward,
                        "days_open": days,
                    },
                )

# ... (router definitions)
spatial_router = APIRouter(prefix="/spatial", tags=["Spatial"])

@spatial_router.get("/heatmap")
async def get_heatmap(db: Session = Depends(get_db)):
    # FEATURE 13: 60s Redis cache
    pool = get_pool()
    cache_key = "cache:/spatial/heatmap"
    if pool:
        cached = await pool.get(cache_key)
        if cached:
            return json.loads(cached)
    response = await SpatialService().get_heatmap(db)
    if pool:
        await pool.set(cache_key, json.dumps(response), ex=60)
    return response

@spatial_router.get("/hotspots")
async def get_hotspots(db: Session = Depends(get_db)):
    return await SpatialService().get_hotspots(db)

@spatial_router.get("/forecast")
async def get_forecast(days: int = 7, db: Session = Depends(get_db)):
    return await SpatialService().get_forecast(db, days)

@spatial_router.get("/risk")
async def get_risk(db: Session = Depends(get_db)):
    return await SpatialService().get_risk_analysis(db)

@spatial_router.post("/simulate")
async def simulate(additional_teams: int, db: Session = Depends(get_db)):
    return await SpatialService().simulate_resources(db, additional_teams)

executive_router = APIRouter(prefix="/executive", tags=["Executive"])

@executive_router.get("/summary")
async def get_executive_summary(db: Session = Depends(get_db)):
    service = DecisionService()
    return await service.get_executive_summary(db)

@executive_router.get("/ward-health")
async def get_ward_health(db: Session = Depends(get_db)):
    # FEATURE 13: 60s Redis cache
    pool = get_pool()
    cache_key = "cache:/executive/ward-health"
    if pool:
        cached = await pool.get(cache_key)
        if cached:
            return json.loads(cached)
    service = DecisionService()
    response = await service.get_ward_health(db)
    if pool:
        await pool.set(cache_key, json.dumps(response), ex=60)
    return response

@executive_router.get("/department-workload")
async def get_dept_workload(db: Session = Depends(get_db)):
    service = DecisionService()
    return await service.get_dept_workload(db)


@executive_router.post("/kpi-targets")
def set_kpi_target(body: KpiTargetCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != 'Executive':
        raise HTTPException(status_code=403, detail="Executive only")
    target = KpiTarget(metric_name=body.metric_name, target_value=body.target_value, current_value=body.current_value, set_by=current_user.full_name)
    db.add(target); db.commit(); db.refresh(target)
    return {"id": target.id, "metric_name": target.metric_name, "target_value": target.target_value, "current_value": target.current_value}

@executive_router.get("/kpi-targets")
def get_kpi_targets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != 'Executive':
        raise HTTPException(status_code=403, detail="Executive only")
    targets = db.query(KpiTarget).order_by(KpiTarget.set_at.desc()).all()
    return [{"id": t.id, "metric_name": t.metric_name, "target_value": t.target_value, "current_value": t.current_value, "set_by": t.set_by, "set_at": t.set_at.isoformat()} for t in targets]


@executive_router.get("/ward-trend")
async def get_ward_trend(db: Session = Depends(get_db)):
    """Get complaint volume per ward over the last 7 days, grouped by date."""
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    rows = db.query(
        Complaint.ward,
        func.date(Complaint.created_at).label("dt"),
        func.count(Complaint.id),
    ).filter(
        Complaint.ward.isnot(None), Complaint.ward != "",
        Complaint.created_at >= seven_days_ago,
    ).group_by(Complaint.ward, "dt").order_by(Complaint.ward, "dt").all()

    trend_by_ward: dict[str, list] = {}
    for ward, dt, cnt in rows:
        date_str = dt.isoformat() if hasattr(dt, 'isoformat') else str(dt)
        if ward not in trend_by_ward:
            trend_by_ward[ward] = []
        trend_by_ward[ward].append({"date": date_str, "count": cnt})
    return [{"ward": ward, "daily_counts": counts} for ward, counts in trend_by_ward.items()]


@executive_router.get("/anomalies")
async def get_anomalies(db: Session = Depends(get_db)):
    """Detect statistical anomalies in complaint volume by ward+category using mean+stddev."""
    from collections import defaultdict
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    rows = db.query(
        Complaint.ward,
        Complaint.predicted_category,
        func.date(Complaint.created_at).label("dt"),
        func.count(Complaint.id),
    ).filter(
        Complaint.ward.isnot(None), Complaint.ward != "",
        Complaint.predicted_category.isnot(None),
        Complaint.created_at >= thirty_days_ago,
    ).group_by(Complaint.ward, Complaint.predicted_category, "dt").all()

    data: dict = defaultdict(lambda: defaultdict(list))
    for ward, cat, dt, cnt in rows:
        data[(ward, cat)][str(dt)].append(cnt)

    anomalies = []
    for (ward, cat), daily_map in data.items():
        counts = [sum(v) for v in daily_map.values()]
        if len(counts) < 2:
            continue
        mean = sum(counts) / len(counts)
        variance = sum((x - mean) ** 2 for x in counts) / len(counts)
        stddev = variance ** 0.5
        today_counts = [c for d, c in daily_map.items() if d >= str(today_start.date())]
        today_count = sum(today_counts) if today_counts else 0
        if today_count > mean + 2 * stddev:
            severity = "high" if today_count > mean + 3 * stddev else "medium"
            anomalies.append({
                "ward": ward,
                "category": cat,
                "today_count": today_count,
                "mean": round(mean, 2),
                "stddev": round(stddev, 2),
                "severity": severity,
            })
    return anomalies


@executive_router.get("/hotspot-prediction")
async def get_hotspot_prediction(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Predict complaint hotspots per ward for next week using PredictiveEngine.
    Uses last 4 weeks of complaint data per ward, returns top 10 by predicted volume.
    Executive auth required."""
    if current_user.role != 'Executive':
        raise HTTPException(status_code=403, detail="Executive only")
    engine = PredictiveEngine()
    now = datetime.utcnow()
    predictions = []
    ward_numbers = db.query(Complaint.ward).filter(
        Complaint.ward.isnot(None), Complaint.ward != ""
    ).distinct().all()
    for (wn,) in ward_numbers:
        weeks = []
        for w in range(4):
            start = now - timedelta(weeks=w+1)
            end = now - timedelta(weeks=w)
            cnt = db.query(Complaint).filter(
                Complaint.ward == wn,
                Complaint.created_at >= start,
                Complaint.created_at < end,
            ).count()
            weeks.append(cnt)
        weeks.reverse()
        forecast = engine.forecast_complaints('week', history=weeks)
        predicted = forecast.get("predicted_volume", 0)
        confidence = forecast.get("confidence", 0)
        risk = "HIGH" if predicted > 50 else "MEDIUM" if predicted > 20 else "LOW"
        predictions.append({
            "ward": wn,
            "predicted_volume": round(predicted, 1),
            "confidence": round(confidence, 2),
            "risk_level": risk,
        })
    predictions.sort(key=lambda r: r["predicted_volume"], reverse=True)
    return predictions[:10]


class GeofenceCreate(BaseModel):
    lat: float
    lng: float
    radius_meters: float
    label: str


@executive_router.post("/geofence")
def create_geofence(body: GeofenceCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != 'Executive':
        raise HTTPException(status_code=403, detail="Executive only")
    gf = Geofence(
        id=str(uuid.uuid4()),
        lat=body.lat,
        lng=body.lng,
        radius_meters=body.radius_meters,
        label=body.label,
        created_by=current_user.id,
    )
    db.add(gf)
    db.commit()
    db.refresh(gf)
    return {
        "id": gf.id,
        "lat": gf.lat,
        "lng": gf.lng,
        "radius_meters": gf.radius_meters,
        "label": gf.label,
        "created_at": gf.created_at.isoformat() if gf.created_at else None,
    }


@executive_router.get("/geofences")
def list_geofences(db: Session = Depends(get_db)):
    fences = db.query(Geofence).order_by(Geofence.created_at.desc()).all()
    return [
        {
            "id": f.id,
            "lat": f.lat,
            "lng": f.lng,
            "radius_meters": f.radius_meters,
            "label": f.label,
            "created_by": f.created_by,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in fences
    ]


# FEATURE 19: daily briefing
@executive_router.get("/daily-briefing")
async def get_daily_briefing(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != 'Executive':
        raise HTTPException(status_code=403, detail="Executive only")
    from collections import defaultdict
    from prediction.engine import PredictiveEngine
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    new_complaints_today = db.query(func.count(Complaint.id)).filter(Complaint.created_at >= today_start).scalar() or 0

    resolved_today = db.query(func.count(Incident.id)).filter(
        Incident.status_changed_at >= today_start,
        Incident.status.in_(["resolved", "closed"]),
    ).scalar() or 0

    sla_breaches_today = db.query(func.count(Incident.id)).filter(
        Incident.days_open > 7,
        ~Incident.status.in_(["resolved", "closed"]),
    ).scalar() or 0

    pending_appeals = db.query(func.count(Incident.id)).filter(
        Incident.appealed == True,
        Incident.status != "resolved",
    ).scalar() or 0

    thirty_days_ago = now - timedelta(days=30)
    rows = db.query(
        Complaint.ward,
        Complaint.predicted_category,
        func.date(Complaint.created_at).label("dt"),
        func.count(Complaint.id),
    ).filter(
        Complaint.ward.isnot(None), Complaint.ward != "",
        Complaint.predicted_category.isnot(None),
        Complaint.created_at >= thirty_days_ago,
    ).group_by(Complaint.ward, Complaint.predicted_category, "dt").all()
    data = defaultdict(lambda: defaultdict(list))
    for ward, cat, dt, cnt in rows:
        data[(ward, cat)][str(dt)].append(cnt)
    top_anomaly = None
    for (ward, cat), daily_map in data.items():
        counts = [sum(v) for v in daily_map.values()]
        if len(counts) < 2:
            continue
        mean = sum(counts) / len(counts)
        variance = sum((x - mean) ** 2 for x in counts) / len(counts)
        stddev = variance ** 0.5
        today_counts = [c for d, c in daily_map.items() if d >= str(today_start.date())]
        today_count = sum(today_counts) if today_counts else 0
        if today_count > mean + 2 * stddev:
            severity = "high" if today_count > mean + 3 * stddev else "medium"
            if not top_anomaly or today_count > top_anomaly["today_count"]:
                top_anomaly = {"ward": ward, "category": cat, "today_count": today_count, "mean": round(mean, 2), "stddev": round(stddev, 2), "severity": severity}

    engine = PredictiveEngine()
    predictions = []
    ward_numbers = db.query(Complaint.ward).filter(Complaint.ward.isnot(None), Complaint.ward != "").distinct().all()
    for (wn,) in ward_numbers:
        weeks = []
        for w in range(4):
            start = now - timedelta(weeks=w+1)
            end = now - timedelta(weeks=w)
            cnt = db.query(Complaint).filter(Complaint.ward == wn, Complaint.created_at >= start, Complaint.created_at < end).count()
            weeks.append(cnt)
        weeks.reverse()
        forecast = engine.forecast_complaints('week', history=weeks)
        predicted = forecast.get("predicted_volume", 0)
        predictions.append({"ward": wn, "predicted_volume": round(predicted, 1)})
    predictions.sort(key=lambda r: r["predicted_volume"], reverse=True)
    hotspot_prediction = predictions[:5] if predictions else []

    return {
        "date": now.date().isoformat(),
        "new_complaints_today": new_complaints_today,
        "resolved_today": resolved_today,
        "sla_breaches_today": sla_breaches_today,
        "pending_appeals": pending_appeals,
        "top_anomaly": top_anomaly,
        "hotspot_prediction": hotspot_prediction,
    }


classify_router = APIRouter(prefix="/classify", tags=["Classification"])
cluster_router = APIRouter(prefix="/cluster", tags=["Clustering"])
priority_router = APIRouter(prefix="/priority", tags=["Priority"])
dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
incident_router = APIRouter(prefix="/incidents", tags=["Incidents"])
complaint_router = APIRouter(prefix="/complaints", tags=["Complaints"])
officer_router = APIRouter(prefix="/officer", tags=["Officer"])


# === Complaint Submission Routes ===

@complaint_router.post("", status_code=202, response_model=SubmissionAcceptedResponse)
async def submit_complaint(request: ComplaintCreate, _: None = Depends(check_complaint_rate_limit), db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):  # FEATURE 2: previously rate-limited
    """Submit a new citizen complaint. Runs ML pipeline inline via asyncio.create_task
    (no separate worker process needed — keeps Render free tier viable)."""

    # ── E-khata/Khata rejection upstream ─────────────────────────────────
    # Property document requests are not civic grievances.
    from department_map import is_khata_complaint, get_khata_rejection_response
    combined_text = f"{request.title} {request.description}"
    if is_khata_complaint(combined_text):
        khata_resp = get_khata_rejection_response()
        raise HTTPException(status_code=400, detail=khata_resp["message"])

    # FEATURE 14: email verification
    if not db_user.email_verified:
        raise HTTPException(status_code=403, detail="Please verify your email before submitting complaints.")

    # FEATURE 8: 10/day per citizen limit
    last_24h = datetime.utcnow() - timedelta(hours=24)
    count_today = db.query(func.count(Complaint.id)).filter(
        Complaint.user_id == db_user.id,
        Complaint.created_at >= last_24h,
    ).scalar() or 0
    if count_today >= 10:
        raise HTTPException(status_code=429, detail="Maximum 10 complaints per day. You have used all your submissions for today.")

    # FEATURE 12: HTML strip + spam detection
    request.title = re.sub(r'<[^>]+>', '', request.title)
    request.description = re.sub(r'<[^>]+>', '', request.description)
    for field in (request.title, request.description):
        if field:
            alnum_count = sum(c.isalnum() for c in field)
            total_count = len(field)
            if total_count > 0 and alnum_count / total_count < 0.4:
                raise HTTPException(status_code=400, detail="Complaint text appears to be spam or contains invalid characters.")

    complaint_id = str(uuid.uuid4())

    # FEATURE 14: compute location accuracy
    location_accuracy = None
    if request.latitude is not None and request.longitude is not None:
        location_accuracy = "gps"
    elif request.address:
        location_accuracy = "address"
    elif request.ward:
        location_accuracy = "ward_only"

    complaint = Complaint(
        id=complaint_id,
        title=request.title,
        description=request.description,
        location=request.location,
        ward=request.ward or "",
        address=request.address,
        latitude=request.latitude,
        longitude=request.longitude,
        image_path=request.image_path,
        user_id=db_user.id,
        location_accuracy=location_accuracy,
    )
    db.add(complaint)
    db.commit()

    import asyncio
    asyncio.create_task(process_complaint_pipeline(complaint_id, db_user.id))

    # FEATURE 13: cache invalidated
    pool = get_pool()
    if pool:
        for key in ["cache:/spatial/heatmap", "cache:/executive/ward-health"]:
            try:
                await pool.delete(key)
            except Exception:
                pass

    await manager.broadcast("complaint:new", {
        "complaint_id": complaint_id,
        "ward": complaint.ward,
        "category": None,
    })

    _write_audit_log(
        db,
        db_user.id,
        db_user.email,
        db_user.role,
        "complaint_create",
        complaint_id,
        "accepted",
        "inline_pipeline",
    )
    return SubmissionAcceptedResponse(
        complaintId=complaint_id,
        statusUrl=f"/complaints/{complaint_id}/status",
        message="Complaint accepted for processing. Check status via the status URL."
    )


@complaint_router.get("/{complaint_id}/status", response_model=ComplaintProcessingStatus)
async def get_complaint_processing_status(complaint_id: str, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get async ML processing status for a complaint. Falls back to DB if Redis is unavailable."""
    status_data = await get_complaint_status(complaint_id)
    if status_data is None:
        complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if not complaint:
            return ComplaintProcessingStatus(status="failed", detail="Complaint not found")
        if complaint.predicted_category is not None:
            return ComplaintProcessingStatus(
                status="completed",
                detail="ML pipeline finished",
                result={
                    "complaintId": complaint.id,
                    "incidentId": complaint.incident_id,
                    "predictedCategory": complaint.predicted_category,
                    "priority": complaint.priority,
                    "confidence": complaint.confidence,
                    "duplicate": complaint.merge_reason is not None,
                    "message": "Complaint processed successfully.",
                }
            )
        return ComplaintProcessingStatus(status="pending", detail="Pipeline not yet started")
    return ComplaintProcessingStatus(**status_data)


@complaint_router.post("/{complaint_id}/upload")
async def upload_complaint_photo(
    complaint_id: str,
    file: UploadFile = File(...),
    db_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a photo for complaint evidence (jpg/png, max 5MB).

    On upload, a perceptual hash (pHash) is computed and compared against
    all existing complaint photos. If a near-duplicate is found:
      - Same user → flagged 'possible_duplicate_submission' (spam guard)
      - Different user → flagged 'reused_image' (fraud guard)
    The complaint's auto-priority is lowered for same-user matches, but
    never auto-rejected — false positives are reviewed by officers/admins.
    """
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id, Complaint.user_id == db_user.id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    data = await file.read()

    # FEATURE 9: 5MB max, jpg/png/webp only
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Photo exceeds maximum size of 5MB.")
    ext = Path(file.filename or "").suffix.lower() if file.filename else ""
    allowed_exts = {".jpg", ".jpeg", ".png", ".webp"}
    allowed_mimes = {"image/jpeg", "image/png", "image/webp"}
    if ext not in allowed_exts or file.content_type not in allowed_mimes:
        raise HTTPException(status_code=400, detail="Invalid file type. Allowed types: jpg, png, webp.")

    err = validate_file(file.filename or "upload", file.content_type or "", len(data))
    if err:
        raise HTTPException(status_code=400, detail=err)

    # Compute perceptual hash for duplicate detection
    from storage import compute_phash, find_duplicate_photo
    phash_str = compute_phash(data)
    if phash_str:
        match_id, flag_type, _ = find_duplicate_photo(db, db_user.id, phash_str)
        if flag_type == "same_user":
            complaint.photo_duplicate_flag = "possible_duplicate_submission"
            complaint.photo_duplicate_of = match_id
            logger.info(
                "Photo duplicate (same user %s): complaint %s matches %s",
                db_user.id, complaint_id, match_id,
            )
            # Lower auto-priority for same-user duplicate photo submissions
            if complaint.priority not in (None, "Low"):
                complaint.priority = "Low"
        elif flag_type == "cross_user":
            complaint.photo_duplicate_flag = "reused_image"
            complaint.photo_duplicate_of = match_id
            logger.info(
                "Photo reused (cross-user): complaint %s (user %s) matches %s (different user)",
                complaint_id, db_user.id, match_id,
            )
        elif flag_type == "similar":
            complaint.photo_duplicate_flag = "similar"
            complaint.photo_duplicate_of = match_id
            logger.info(
                "Photo similar (hamming < 10): complaint %s (user %s) matches %s",
                complaint_id, db_user.id, match_id,
            )
    else:
        logger.info("No pHash computed for complaint %s — proceeding without duplicate check", complaint_id)

    complaint.photo_hash = phash_str

    storage = S3Storage()
    if not storage.available:
        logger.warning("S3 not configured — skipping photo upload for complaint %s", complaint_id)
        db.commit()
        return {
            "imageKey": None,
            "complaintId": complaint_id,
            "photoHash": phash_str,
            "photoDuplicateFlag": complaint.photo_duplicate_flag,
            "photoDuplicateOf": complaint.photo_duplicate_of,
            "message": "Photo hash stored but upload skipped (S3 not configured).",
        }

    try:
        object_key = storage.upload(data, file.filename, file.content_type)
    except Exception as e:
        logger.error("S3 upload failed for complaint %s: %s", complaint_id, e)
        # Hash and flags are already set — commit so they're not lost
        db.commit()
        raise HTTPException(status_code=502, detail=f"Storage upload failed: {e}")

    complaint.image_path = object_key
    db.commit()

    flag_msg = ""
    if complaint.photo_duplicate_flag == "possible_duplicate_submission":
        flag_msg = " Photo matches your earlier upload — marked as possible duplicate for review."
    elif complaint.photo_duplicate_flag == "reused_image":
        flag_msg = " Photo matches an existing complaint from another user — flagged for review."

    return {
        "imageKey": object_key,
        "complaintId": complaint_id,
        "photoHash": phash_str,
        "photoDuplicateFlag": complaint.photo_duplicate_flag,
        "photoDuplicateOf": complaint.photo_duplicate_of,
        "message": "Photo uploaded successfully." + flag_msg,
    }


@complaint_router.get("/{complaint_id}/photo")
async def get_complaint_photo(complaint_id: str, db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get a presigned photo URL for a complaint's uploaded image (private bucket)."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id, Complaint.user_id == db_user.id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    if not complaint.image_path:
        return {"imageUrl": None, "complaintId": complaint_id}

    storage = S3Storage()
    if not storage.available:
        return {"imageUrl": None, "complaintId": complaint_id, "message": "Storage not configured"}

    url = storage.get_presigned_url(complaint.image_path)
    if not url:
        raise HTTPException(status_code=502, detail="Failed to generate photo URL")
    return {"imageUrl": url, "complaintId": complaint_id}


@complaint_router.get("/debug/env")
async def debug_env(db_user: User = Depends(get_current_user)):
    """Check S3 environment variable status (auth-protected)."""
    from storage import S3Storage
    s3 = S3Storage()
    return {
        "S3_ENDPOINT_URL_set": bool(os.environ.get("S3_ENDPOINT_URL")),
        "S3_ACCESS_KEY_ID_set": bool(os.environ.get("S3_ACCESS_KEY_ID")),
        "S3_SECRET_ACCESS_KEY_set": bool(os.environ.get("S3_SECRET_ACCESS_KEY")),
        "S3_BUCKET_NAME_set": bool(os.environ.get("S3_BUCKET_NAME")),
        "S3Storage.available": s3.available,
        "endpoint_url": s3.endpoint_url,
        "bucket": s3.bucket,
    }


@complaint_router.get("/my")
async def get_my_complaints(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(50, ge=1, le=2000, description="Items per page"),
    db_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get complaints for the current authenticated user, paginated.

    Uses eager-loaded incident relation to avoid N+1 queries.
    Caches officer assignments per (ward, category) pair.
    """
    q = db.query(Complaint).options(joinedload(Complaint.incident)).filter(
        Complaint.user_id == db_user.id
    ).order_by(Complaint.created_at.desc())

    total = db.query(Complaint).filter(Complaint.user_id == db_user.id).count()

    # FEATURE 8: 10/day per citizen limit
    last_24h = datetime.utcnow() - timedelta(hours=24)
    count_today = db.query(func.count(Complaint.id)).filter(
        Complaint.user_id == db_user.id,
        Complaint.created_at >= last_24h,
    ).scalar() or 0
    offset_val = (page - 1) * limit
    complaints = q.offset(offset_val).limit(limit).all()

    _officer_cache: dict[tuple[str, str], dict] = {}

    result = []
    for c in complaints:
        incident = c.incident
        key = (c.ward or "", c.predicted_category or "")
        if key not in _officer_cache:
            _officer_cache[key] = route_complaint(*key)
        result.append({
            "id": c.id,
            "title": c.title,
            "description": c.description,
            "location": c.location,
            "ward": c.ward,
            "predicted_category": c.predicted_category,
            "confidence": c.confidence,
            "priority": c.priority,
            "similarity_score": c.similarity_score,
            "merge_reason": c.merge_reason,
            "photo_duplicate_flag": c.photo_duplicate_flag,
            "photo_duplicate_of": c.photo_duplicate_of,
            "date_received": c.created_at.isoformat() if c.created_at else None,
            "assigned_officer": _officer_cache[key],
            "incident": {
                "id": incident.id if incident else None,
                "incident_number": incident.incident_number if incident else None,
                "category": incident.category if incident else None,
                "priority_label": incident.priority_label if incident else None,
                "status": incident.status if incident else None,
                "cluster_size": incident.cluster_size if incident else None,
                "recommended_action": incident.recommended_action if incident else None,
                "resolution_note": incident.resolution_note if incident else None,
                "days_open": incident.days_open if incident else None,
            # FEATURE 17: Impact assessment
            "impact_score": incident.impact_score if incident else None,
            "economic_impact": incident.economic_impact if incident else None,
            "beneficiaries": incident.beneficiaries if incident else None,
            } if incident else None
        })
    return {
        "complaints": result,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@complaint_router.get("/coordinates")
async def get_complaint_coordinates(db: Session = Depends(get_db)):
    """Get all complaint coordinates for spatial map pin layer. No auth required for map rendering."""
    complaints = db.query(Complaint).filter(Complaint.latitude.isnot(None), Complaint.longitude.isnot(None)).order_by(Complaint.created_at.desc()).limit(500).all()
    return [
        {
            "id": c.id,
            "title": c.title,
            "latitude": c.latitude,
            "longitude": c.longitude,
            "address": c.address or c.location,
            "category": c.predicted_category,
            "priority": c.priority,
            "status": c.incident.status if c.incident else "pending",
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in complaints
    ]


@complaint_router.get("/{complaint_id}")
async def get_complaint_detail(complaint_id: str, db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get a single complaint detail for the current user."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id, Complaint.user_id == db_user.id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    incident = db.query(Incident).options(
        joinedload(Incident.priority_history),
        joinedload(Incident.updates),
        joinedload(Incident.complaints),
    ).filter(Incident.id == complaint.incident_id).first() if complaint.incident_id else None
    return {
        "id": complaint.id,
        "title": complaint.title,
        "description": complaint.description,
        "location": complaint.location,
        "ward": complaint.ward,
        "image_path": complaint.image_path,
        "predicted_category": complaint.predicted_category,
        "department": get_department(complaint.predicted_category),
        "confidence": complaint.confidence,
        "assigned_officer": route_complaint(complaint.ward or "", complaint.predicted_category or ""),
        "priority": complaint.priority,
        "similarity_score": complaint.similarity_score,
        "merge_reason": complaint.merge_reason,
        "photo_duplicate_flag": complaint.photo_duplicate_flag,
        "photo_duplicate_of": complaint.photo_duplicate_of,
        "citizen_rating": complaint.citizen_rating,
        "urgency_flag": getattr(complaint, "urgency_flag", "LOW"),
        "date_received": complaint.created_at.isoformat() if complaint.created_at else None,
        "incident": {
            "id": incident.id if incident else None,
            "incident_number": incident.incident_number if incident else None,
            "category": incident.category if incident else None,
            "priority_label": incident.priority_label if incident else None,
            "status": incident.status if incident else None,
            "cluster_size": incident.cluster_size if incident else None,
            "recommended_action": incident.recommended_action if incident else None,
            "summary": incident.summary if incident else None,
            "resolution_note": incident.resolution_note if incident else None,
            # FEATURE 17: Impact assessment
            "impact_score": incident.impact_score if incident else None,
            "economic_impact": incident.economic_impact if incident else None,
            "beneficiaries": incident.beneficiaries if incident else None,
            "priority_history": [
                {
                    "id": ph.id,
                    "old_score": ph.old_score,
                    "new_score": ph.new_score,
                    "reason": ph.reason,
                    "changed_at": ph.changed_at.isoformat() if ph.changed_at else None,
                } for ph in incident.priority_history
            ] if incident else [],
            "updates": [
                {
                    "id": u.id,
                    "user_name": u.user_name,
                    "message": u.message,
                    "created_at": u.created_at.isoformat() if u.created_at else None,
                } for u in incident.updates
            ] if incident else [],
            "complaints": [{
                "id": c.id,
                "complaint_number": c.id,
                "ward": c.ward,
                "date_received": c.created_at.isoformat() if c.created_at else None,
                "status": incident.status if incident else None,
                "urgency_flag": getattr(c, "urgency_flag", "LOW"),
                "image_path": c.image_path,
            } for c in incident.complaints] if incident else [],
        } if incident else None
    }


@complaint_router.patch("/{complaint_id}")
async def update_complaint(complaint_id: str, body: UpdateComplaintRequest, db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Edit complaint description/location within 15 minutes of submission."""
    if db_user.role != "Citizen":
        raise HTTPException(status_code=403, detail="Only citizens can edit complaints")
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id, Complaint.user_id == db_user.id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found or not owned by you")
    if not body.description and not body.location:
        raise HTTPException(status_code=400, detail="At least one of description or location is required")

    if complaint.created_at:
        elapsed = (datetime.utcnow() - complaint.created_at).total_seconds()
        if elapsed > 900:
            raise HTTPException(status_code=403, detail="Editing window expired (15 minutes since submission)")

    if body.description is not None:
        complaint.description = body.description
    if body.location is not None:
        complaint.location = body.location
    db.commit()
    db.refresh(complaint)
    return {"id": complaint.id, "description": complaint.description, "location": complaint.location}


@complaint_router.post("/{complaint_id}/rate")
async def rate_complaint(complaint_id: str, body: RateComplaintRequest, db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Submit a citizen satisfaction rating (1-5) for a resolved complaint.
    Only the complaint's original citizen can rate, once per complaint."""
    if db_user.role != "Citizen":
        raise HTTPException(status_code=403, detail="Only citizens can rate complaints")
    if body.rating not in (1, 2, 3, 4, 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id, Complaint.user_id == db_user.id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found or not owned by you")
    if complaint.citizen_rating is not None:
        raise HTTPException(status_code=400, detail="You have already rated this complaint")

    incident = db.query(Incident).filter(Incident.id == complaint.incident_id).first()
    if not incident or incident.status not in ("resolved", "closed"):
        raise HTTPException(status_code=400, detail="Complaint must be resolved before rating")

    complaint.citizen_rating = body.rating

    # FEATURE 9: recompute resolution quality score with citizen_rating factor
    if incident:
        quality = 0
        if incident.resolution_photo_path:
            quality += 30
        if incident.resolution_note:
            quality += min(len(incident.resolution_note) * 2, 40)
        if incident.days_open and incident.days_open <= 2:
            quality += 30
        elif incident.days_open and incident.days_open <= 5:
            quality += 15
        # 4th factor — citizen_rating
        if body.rating >= 4:
            quality += 20
        elif body.rating == 3:
            quality += 10
        else:
            quality -= 10
        incident.resolution_quality_score = max(0, quality)
    db.commit()

    _write_audit_log(db, db_user.id, db_user.email, db_user.role, "complaint_rated",
                     complaint.id, "success",
                     f"Rating: {body.rating}/5")

    return {"message": "Rating submitted", "rating": body.rating}


@complaint_router.post("/{complaint_id}/withdraw")
async def withdraw_complaint(complaint_id: str, db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Withdraw a complaint by its owner. Only possible within 24h and if incident is open/pending."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id, Complaint.user_id == db_user.id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found or not owned by you")
    if complaint.created_at and (datetime.utcnow() - complaint.created_at) > timedelta(hours=24):
        raise HTTPException(status_code=400, detail="Complaint can only be withdrawn within 24 hours of submission")
    incident = db.query(Incident).filter(Incident.id == complaint.incident_id).first() if complaint.incident_id else None
    if not incident or incident.status not in ("open", "pending"):
        raise HTTPException(status_code=400, detail="Incident must be in open or pending status to withdraw")
    incident.status = "withdrawn"
    incident.status_changed_at = datetime.utcnow()
    db.commit()
    _write_audit_log(db, db_user.id, db_user.email, db_user.role, "complaint_withdraw",
                     complaint.id, "success")
    return {"success": True}


@complaint_router.patch("/{complaint_id}/tags")
async def update_complaint_tags(complaint_id: str, body: TagsUpdateRequest, db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update tags on a complaint (Officer/Executive or complaint owner, max 3)."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    if db_user.role not in ("Officer", "Executive") and complaint.user_id != db_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update tags on this complaint")
    if len(body.tags) > 3:
        raise HTTPException(status_code=400, detail="Maximum of 3 tags allowed")
    complaint.tags = json.dumps(body.tags)
    db.commit()
    return {"tags": json.loads(complaint.tags)}


# FEATURE 16: drafts
class DraftCreate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    ward: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None

@complaint_router.post("/draft")
async def save_draft(body: DraftCreate, db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if db_user.role != 'Citizen':
        raise HTTPException(status_code=403, detail="Only citizens can save drafts")
    existing = db.query(ComplaintDraft).filter(ComplaintDraft.user_id == db_user.id).order_by(ComplaintDraft.updated_at.asc()).all()
    if len(existing) >= 3:
        draft = existing[0]
    else:
        draft = ComplaintDraft(id=str(uuid.uuid4()), user_id=db_user.id)
        db.add(draft)
    if body.title is not None: draft.title = body.title
    if body.description is not None: draft.description = body.description
    if body.location is not None: draft.location = body.location
    if body.ward is not None: draft.ward = body.ward
    if body.category is not None: draft.category = body.category
    if body.tags is not None: draft.tags = body.tags
    draft.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(draft)
    return {
        "id": draft.id,
        "title": draft.title,
        "description": draft.description,
        "location": draft.location,
        "ward": draft.ward,
        "category": draft.category,
        "tags": draft.tags,
        "created_at": draft.created_at.isoformat() if draft.created_at else None,
        "updated_at": draft.updated_at.isoformat() if draft.updated_at else None,
    }

@complaint_router.get("/drafts")
async def list_drafts(db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if db_user.role != 'Citizen':
        raise HTTPException(status_code=403, detail="Only citizens can view drafts")
    drafts = db.query(ComplaintDraft).filter(ComplaintDraft.user_id == db_user.id).order_by(ComplaintDraft.updated_at.desc()).limit(3).all()
    return [
        {
            "id": d.id,
            "title": d.title,
            "description": d.description,
            "location": d.location,
            "ward": d.ward,
            "category": d.category,
            "tags": d.tags,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "updated_at": d.updated_at.isoformat() if d.updated_at else None,
        }
        for d in drafts
    ]

@complaint_router.delete("/draft/{draft_id}")
async def delete_draft(draft_id: str, db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    draft = db.query(ComplaintDraft).filter(ComplaintDraft.id == draft_id, ComplaintDraft.user_id == db_user.id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    db.delete(draft)
    db.commit()
    return {"success": True}


# === Classification Routes ===

@classify_router.post("", response_model=ClassifyResponse)
async def classify_single(request: ClassifyRequest):
    """Classify a single complaint into a category with complexity and language detection."""
    import re
    from duplicate_detection.engine import _is_tanglish_text
    service = ClassificationService()
    result = await service.classify(request)
    description = request.text or ""

    desc_len_score = min(len(description) / 500, 1.0) * 0.3
    sent_count_score = min(len(re.split('[.!?]', description)) / 10, 1.0) * 0.25
    category_weights = {"Roads": 0.25, "Water Supply": 0.3, "Waste Management": 0.2, "Public Health": 0.35, "Street Lighting": 0.2, "Electricity": 0.3, "Sanitation": 0.25}
    total = desc_len_score + sent_count_score + category_weights.get(result.predicted_category, 0.2)
    result.complexity_label = "simple" if total < 0.4 else "moderate" if total < 0.7 else "complex"
    result.complexity_score = round(total, 4)

    if any('\u0B80' <= c <= '\u0BFF' for c in description):
        result.complaint_language = "tamil"
    elif _is_tanglish_text(description):
        result.complaint_language = "tamil"
    else:
        result.complaint_language = "english"

    return result


@classify_router.post("/batch")
async def classify_batch(requests: List[ClassifyRequest]):
    """Classify multiple complaints at once."""
    service = ClassificationService()
    results = [await service.classify(req) for req in requests]
    return {"results": results, "count": len(results)}


class CommentCreate(BaseModel):
    message: str

class ForwardRequest(BaseModel):
    new_department: str

class KpiTargetCreate(BaseModel):
    metric_name: str
    target_value: float
    current_value: Optional[float] = None

class PredictCategoryRequest(BaseModel):
    text: str


@classify_router.post("/predict", response_model=ClassifyResponse)
async def predict_category(request: PredictCategoryRequest):
    """Alias for classify endpoint."""
    service = ClassificationService()
    return await service.classify(ClassifyRequest(text=request.text))


# === Clustering Routes ===

@cluster_router.post("", response_model=ClusterResponse)
async def cluster_complaints(request: ClusterRequest):
    """Cluster complaints into incidents."""
    service = ClusteringService()
    return await service.cluster(request)


@cluster_router.post("/similar")
async def find_similar(
    text: str,
    existing_complaints: List[Dict[str, Any]],
    threshold: float = Query(0.8, ge=0.0, le=1.0)
):
    """Find complaints similar to the given text."""
    service = ClusteringService()
    similar = await service.find_similar(text, existing_complaints, threshold)
    return {"similar_complaints": similar}


@cluster_router.get("/config")
async def get_clustering_config():
    """Get current clustering configuration."""
    return {
        "eps": 0.3,
        "min_samples": 2,
        "model": "all-MiniLM-L6-v2"
    }


# === Priority Routes ===

@priority_router.post("", response_model=PriorityResponse)
async def calculate_priority(request: PriorityRequest):
    """Calculate priority score for an incident."""
    service = PriorityService()
    return await service.calculate(request)


@priority_router.post("/batch")
async def calculate_batch_priority(requests: List[PriorityRequest]):
    """Calculate priority for multiple incidents."""
    service = PriorityService()
    results = [await service.calculate(req) for req in requests]
    return {"results": results, "count": len(results)}


@priority_router.get("/rules")
async def get_priority_rules():
    """Get active priority adjustment rules."""
    return {
        "rules": [
            {"name": "safety_critical", "adjustment": 20, "reason": "Safety hazard detected"},
            {"name": "school_proximity", "adjustment": 15, "reason": "Issue near school/childcare"},
            {"name": "hospital_proximity", "adjustment": 12, "reason": "Issue near medical facility"},
            {"name": "water_public_health", "adjustment": 10, "reason": "Public health impact"},
            {"name": "long_standing", "adjustment": 8, "reason": "Issue unresolved for >3 weeks"},
            {"name": "large_cluster", "adjustment": 7, "reason": "High public interest"},
        ]
    }


# === Dashboard Routes ===

@dashboard_router.get("")
async def get_dashboard(db: Session = Depends(get_db)):
    """Get dashboard summary data."""
    service = DashboardService()
    return await service.get_summary(db)


@dashboard_router.get("/metrics")
async def get_metrics():
    """Get key performance metrics from the trained model metadata."""
    # FEATURE 7: real per-category metrics
    metadata_path = Path(__file__).parent.parent.parent / 'ai-engine' / 'models' / 'classification' / 'metadata.json'
    if metadata_path.exists():
        try:
            with open(metadata_path) as f:
                meta = json.load(f)
            accuracy_pct = round(meta.get('accuracy', 0) * 100, 2)
            return {
                "model_accuracy": accuracy_pct,
                "model_type": meta.get('model_type', 'unknown'),
                "num_classes": meta.get('num_classes', 0),
                "categories": meta.get('classes', []),
                "dataset_size": meta.get('total_samples', 0),
                "num_train_samples": meta.get('num_train_samples', 0),
                "num_test_samples": meta.get('num_test_samples', 0),
                "last_updated": meta.get('trained_at', datetime.now().isoformat()),
                "per_category_metrics": meta.get('per_category_metrics', {}),
            }
        except Exception as e:
            logger.warning(f"Failed to load model metadata: {e}")
    return {
        "model_accuracy": 0,
        "model_type": "not available",
        "num_classes": 0,
        "categories": [],
        "dataset_size": 0,
        "last_updated": datetime.now().isoformat(),
        "per_category_metrics": {},
    }


@dashboard_router.get("/trend")
async def get_trend_data(db: Session = Depends(get_db)):
    """Get trend data for charts (complaints & incidents per month, last 6mo)."""
    six_months_ago = datetime.now() - timedelta(days=180)
    months = []
    for i in range(5, -1, -1):
        d = datetime.now() - timedelta(days=30 * i)
        months.append((d.year, d.month, d.strftime("%b")))

    comp_by_month = {
        (r.year, r.month): r[2]
        for r in db.query(
            extract("year", Complaint.created_at).label("year"),
            extract("month", Complaint.created_at).label("month"),
            func.count(Complaint.id),
        ).filter(Complaint.created_at >= six_months_ago)
         .group_by("year", "month").all()
    }
    inc_by_month = {
        (r.year, r.month): r[2]
        for r in db.query(
            extract("year", Incident.created_at).label("year"),
            extract("month", Incident.created_at).label("month"),
            func.count(Incident.id),
        ).filter(Incident.created_at >= six_months_ago)
         .group_by("year", "month").all()
    }

    # Category trend: GROUP BY month + category
    cat_rows = db.query(
        extract("year", Complaint.created_at).label("year"),
        extract("month", Complaint.created_at).label("month"),
        Complaint.predicted_category,
        func.count(Complaint.id),
    ).filter(
        Complaint.created_at >= six_months_ago,
        Complaint.predicted_category.isnot(None),
    ).group_by("year", "month", Complaint.predicted_category).all()

    category_trend = []
    for yr, mo, cat, cnt in cat_rows:
        month_label = f"{yr}-{mo:02d}"
        category_trend.append({
            "month": month_label,
            "category": cat,
            "count": cnt,
        })

    return {
        "labels": [m[2] for m in months],
        "complaints": [comp_by_month.get((y, m), 0) for y, m, _ in months],
        "incidents": [inc_by_month.get((y, m), 0) for y, m, _ in months],
        "categoryTrend": category_trend,
    }


@dashboard_router.get("/today-tasks")
async def get_today_tasks(db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get today's task counts for the officer's department."""
    if db_user.role != "Officer":
        raise HTTPException(status_code=403, detail="Only officers can access today's tasks")
    department = db_user.department
    if not department:
        raise HTTPException(status_code=400, detail="Officer has no department assigned")

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    dept_slug = get_slug_for_department(department)
    dept_categories = [cat for cat, slug in CATEGORY_DEPT_MAP.items() if slug == dept_slug]

    open_today = 0
    resolved_today = 0
    new_today = 0

    if dept_categories:
        open_today = db.query(func.count(Incident.id)).filter(
            Incident.category.in_(dept_categories),
            Incident.status.in_(["open", "in-progress"]),
            Incident.created_at >= today_start,
            Incident.created_at < today_end,
        ).scalar() or 0

        resolved_today = db.query(func.count(Incident.id)).filter(
            Incident.category.in_(dept_categories),
            Incident.status.in_(["resolved", "closed"]),
            Incident.status_changed_at >= today_start,
            Incident.status_changed_at < today_end,
        ).scalar() or 0

        new_today = db.query(func.count(Complaint.id)).filter(
            Complaint.predicted_category.in_(dept_categories),
            Complaint.created_at >= today_start,
            Complaint.created_at < today_end,
            Complaint.incident_id.isnot(None),
        ).scalar() or 0

    return {
        "open_today": open_today,
        "resolved_today": resolved_today,
        "new_today": new_today,
    }


@dashboard_router.get("/analytics")
async def get_analytics(db: Session = Depends(get_db)):
    """Get comprehensive analytics data for the Analysis page."""
    six_months_ago = datetime.now() - timedelta(days=180)

    # Overview
    total_complaints = db.query(Complaint).count()
    total_incidents = db.query(Incident).count()
    open_incidents = db.query(Incident).filter(Incident.status == "open").count()

    # Category breakdown (complaints by category)
    cat_raw = db.query(
        Complaint.predicted_category, func.count(Complaint.id)
    ).filter(
        Complaint.predicted_category.isnot(None),
    ).group_by(Complaint.predicted_category).order_by(func.count(Complaint.id).desc()).all()

    # Department workload (open incidents, mapped to departments)
    dept_raw = db.query(
        Incident.category, func.count(Incident.id)
    ).filter(Incident.status == "open").group_by(Incident.category).all()
    dept_merged: Dict[str, int] = {}
    for cat, cnt in dept_raw:
        dept = get_department(cat)
        dept_merged[dept] = dept_merged.get(dept, 0) + cnt

    # Volume trend (last 6 months)
    months: list = []
    for i in range(5, -1, -1):
        d = datetime.now() - timedelta(days=30 * i)
        months.append((d.year, d.month, d.strftime("%b")))

    yr = extract("year", Complaint.created_at)
    mo = extract("month", Complaint.created_at)
    comp_by_month = {
        (r[0], r[1]): r[2]
        for r in db.query(
            yr, mo, func.count(Complaint.id),
        ).filter(Complaint.created_at >= six_months_ago)
         .group_by(yr, mo).all()
    }
    inc_by_month = {
        (r[0], r[1]): r[2]
        for r in db.query(
            extract("year", Incident.created_at).label("y"),
            extract("month", Incident.created_at).label("m"),
            func.count(Incident.id),
        ).filter(Incident.created_at >= six_months_ago)
         .group_by("y", "m").all()
    }

    # Resolution time trend (avg days_open for closed/resolved incidents per month)
    yr2 = extract("year", Incident.created_at)
    mo2 = extract("month", Incident.created_at)
    res_raw = db.query(
        yr2, mo2, func.avg(Incident.days_open),
    ).filter(
        Incident.status.in_(["resolved", "closed"]),
        Incident.created_at >= six_months_ago,
    ).group_by(yr2, mo2).all()
    res_by_month = {(r[0], r[1]): round(float(r[2]), 1) for r in res_raw if r[2] is not None}

    # Ward hotspots (top 10 by complaint count)
    ward_raw = db.query(
        Complaint.ward, func.count(Complaint.id)
    ).filter(
        Complaint.ward.isnot(None), Complaint.ward != "",
    ).group_by(Complaint.ward).order_by(func.count(Complaint.id).desc()).limit(10).all()

    return {
        "overview": {
            "totalComplaints": total_complaints,
            "totalIncidents": total_incidents,
            "openIncidents": open_incidents,
        },
        "categoryBreakdown": [
            {"category": cat or "Uncategorized", "count": cnt}
            for cat, cnt in cat_raw
        ],
        "departmentWorkload": [
            {"department": dept, "activeIncidents": cnt}
            for dept, cnt in sorted(dept_merged.items(), key=lambda x: -x[1])
        ],
        "volumeTrend": {
            "labels": [m[2] for m in months],
            "complaints": [comp_by_month.get((y, m), 0) for y, m, _ in months],
            "incidents": [inc_by_month.get((y, m), 0) for y, m, _ in months],
        },
        "resolutionTrend": {
            "labels": [m[2] for m in months],
            "avgDays": [res_by_month.get((y, m)) for y, m, _ in months],
        },
        "wardHotspots": [
            {"ward": w, "complaintCount": cnt}
            for w, cnt in ward_raw
        ],
    }


@incident_router.get("")
async def get_incidents(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(50, ge=1, le=2000, description="Items per page"),
    db: Session = Depends(get_db),
):
    """Get all incidents, paginated.

    Uses eager-loaded complaints relation to avoid N+1 queries.
    """
    total = db.query(Incident).count()
    offset_val = (page - 1) * limit
    incidents = db.query(Incident).options(joinedload(Incident.complaints)).order_by(
        Incident.priority_score.desc().nullslast(),
        Incident.created_at.desc().nullslast(),
    ).offset(offset_val).limit(limit).all()

    _dept_cache: dict[str, str] = {}

    result = []
    for inc in incidents:
        cat = inc.category or ""
        if cat not in _dept_cache:
            _dept_cache[cat] = get_department(cat)
        inc_dict = {
            "id": inc.id, "incident_number": inc.incident_number, "category": inc.category,
            "department": _dept_cache[cat],
            "ward": inc.ward, "cluster_size": inc.cluster_size, "priority_score": inc.priority_score,
            "priority_label": inc.priority_label, "status": inc.status, "summary": inc.summary,
            "recommended_action": inc.recommended_action, "days_open": inc.days_open,
            "affected_wards": json.loads(inc.affected_wards) if inc.affected_wards else [],
            "accepted_by": inc.accepted_by,
            "accepted_at": inc.accepted_at.isoformat() if inc.accepted_at else None,
            "impact_score": inc.impact_score,
            "economic_impact": inc.economic_impact,
            "beneficiaries": inc.beneficiaries,
            "complaints": [{
                "id": c.id, "complaint_number": c.id,
                "date_received": c.created_at.isoformat() if c.created_at else None,
                "text": c.title, "similarity_score": c.similarity_score or 0.85,
                "photo_duplicate_flag": c.photo_duplicate_flag,
                "photo_duplicate_of": c.photo_duplicate_of,
                "urgency_flag": getattr(c, "urgency_flag", "LOW"),
                "image_path": c.image_path,
                "complexity_label": getattr(c, "complexity_label", None),
                "complaint_language": getattr(c, "complaint_language", None),
            } for c in inc.complaints] if inc.complaints else []
        }
        result.append(inc_dict)
    return {
        "incidents": result,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@incident_router.get("/escalated")
async def get_escalated_incidents(db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List escalated incidents for MLA/Collector oversight dashboards.
    Collector sees only incidents in their district; MLA sees all escalated."""
    if db_user.role not in ("MLA", "Collector", "Councillor", "Commissioner", "Executive"):
        raise HTTPException(status_code=403, detail="Access denied")

    query = db.query(Incident).options(joinedload(Incident.complaints)).filter(Incident.escalated == True)

    if db_user.role == "Collector" and db_user.district:
        collector_wards = db.query(Complaint.ward).filter(
            Complaint.ward.isnot(None), Complaint.ward != ""
        ).distinct().all()
        query = query.filter(Incident.ward.in_([w[0] for w in collector_wards]))

    incidents = query.order_by(Incident.escalated_at.desc().nullslast()).all()
    return {
        "incidents": [
            {
                "id": inc.id, "incident_number": inc.incident_number, "category": inc.category,
                "ward": inc.ward, "cluster_size": inc.cluster_size, "priority_score": inc.priority_score,
                "priority_label": inc.priority_label, "status": inc.status, "summary": inc.summary,
                "recommended_action": inc.recommended_action, "days_open": inc.days_open,
                "escalated": inc.escalated, "escalated_at": inc.escalated_at.isoformat() if inc.escalated_at else None,
                "escalated_by": inc.escalated_by, "escalation_reason": inc.escalation_reason,
                "complaints": [
                    {"id": c.id, "complaint_number": c.id, "text": c.title,
                     "date_received": c.created_at.isoformat() if c.created_at else None,
                     "photo_duplicate_flag": c.photo_duplicate_flag,
                     "photo_duplicate_of": c.photo_duplicate_of,
                     "urgency_flag": getattr(c, "urgency_flag", "LOW"),
                     "image_path": c.image_path}
                    for c in inc.complaints
                ] if inc.complaints else [],
            }
            for inc in incidents
        ]
    }


@incident_router.post("/auto-escalate")
async def auto_escalate_aging_incidents(db: Session = Depends(get_db)):
    """Auto-escalate incidents that have exceeded SLA thresholds.
    
    Tiered logic:
      - Ward-level (first escalation): incident.status_changed_at > 48 hours ago,
        sets escalated=True, bumps priority by SLA_PRIORITY_BUMP points.
      - Zonal-level (second escalation): already escalated AND
        status_changed_at > 120 hours (5 working days) ago, further priority bump
        and updates escalation_reason.
    
    Writes audit log entries and creates notifications for relevant officers.
    Call periodically (e.g. from a scheduler or as an on-demand trigger).
    """
    from constants import SLA_WARD_HOURS, SLA_ZONE_HOURS, SLA_PRIORITY_BUMP

    from coimbatore_wards import ZONE_BY_WARD

    now = datetime.utcnow()
    ward_cutoff = now - timedelta(hours=SLA_WARD_HOURS)
    zone_cutoff = now - timedelta(hours=SLA_ZONE_HOURS)

    results = {"ward_escalated": 0, "zone_escalated": 0, "errors": []}

    try:
        # ── Ward-level escalations (not yet escalated, status stale > 48h) ──
        ward_targets = db.query(Incident).filter(
            Incident.status.in_(["open", "in-progress"]),
            Incident.escalated == False,
            Incident.status_changed_at.isnot(None),
            Incident.status_changed_at <= ward_cutoff,
        ).all()

        for inc in ward_targets:
            try:
                inc.escalated = True
                inc.escalated_at = now
                inc.escalated_by = "system"
                inc.escalation_reason = (
                    f"Auto-escalated: no status change in {SLA_WARD_HOURS}h "
                    f"(ward-level SLA breach)"
                )
                # Bump priority
                old_score = inc.priority_score or 0.0
                inc.priority_score = min(100.0, old_score + SLA_PRIORITY_BUMP)
                inc.priority_label = _label_for_score(inc.priority_score)

                _write_audit_log(
                    db, None, "system", "system",
                    "incident_auto_escalate", inc.id, "success",
                    f"Ward-level SLA: {SLA_WARD_HOURS}h exceeded. "
                    f"Priority bumped {old_score} -> {inc.priority_score}. "
                    f"Escalation reason: {inc.escalation_reason}"
                )

                # Notify department officers
                dept = get_department(inc.category or "")
                _notify_department_officers(
                    db, dept, "escalated",
                    data={
                        "incident_id": inc.id,
                        "incident_number": inc.incident_number,
                        "category": inc.category,
                        "ward": inc.ward,
                        "reason": inc.escalation_reason,
                        "auto_escalated": True,
                    },
                )

                results["ward_escalated"] += 1
            except Exception as e:
                results["errors"].append(f"incident {inc.id}: {e}")

        # ── Zone-level escalations (already escalated, status stale > 5 days) ──
        zone_targets = db.query(Incident).filter(
            Incident.status.in_(["open", "in-progress"]),
            Incident.escalated == True,
            Incident.status_changed_at.isnot(None),
            Incident.status_changed_at <= zone_cutoff,
        ).all()

        for inc in zone_targets:
            try:
                ward_num = int(inc.ward) if inc.ward and inc.ward.isdigit() else None
                zone = ZONE_BY_WARD.get(ward_num, "Unknown") if ward_num else "Unknown"

                old_score = inc.priority_score or 0.0
                inc.priority_score = min(100.0, old_score + SLA_PRIORITY_BUMP)
                inc.priority_label = _label_for_score(inc.priority_score)
                inc.escalation_reason = (
                    f"Zone-level escalation: no status change in {SLA_ZONE_HOURS}h "
                    f"(zone: {zone}, ward: {inc.ward}). "
                    f"Previous reason: {inc.escalation_reason or 'none'}"
                )

                _write_audit_log(
                    db, None, "system", "system",
                    "incident_auto_escalate_zone", inc.id, "success",
                    f"Zone-level SLA ({zone}): {SLA_ZONE_HOURS}h exceeded. "
                    f"Priority bumped {old_score} -> {inc.priority_score}."
                )

                # Notify department officers
                dept = get_department(inc.category or "")
                _notify_department_officers(
                    db, dept, "escalated",
                    data={
                        "incident_id": inc.id,
                        "incident_number": inc.incident_number,
                        "category": inc.category,
                        "ward": inc.ward,
                        "zone": zone,
                        "reason": inc.escalation_reason,
                        "auto_escalated": True,
                    },
                )

                results["zone_escalated"] += 1
            except Exception as e:
                results["errors"].append(f"incident {inc.id}: {e}")

        db.commit()

        total = results["ward_escalated"] + results["zone_escalated"]
        if total:
            return {
                "message": f"Auto-escalated {total} incidents "
                           f"({results['ward_escalated']} ward-level, "
                           f"{results['zone_escalated']} zone-level)",
                **results,
            }
        return {"message": "No incidents exceed SLA thresholds", **results}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Auto-escalation failed: {e}")


@incident_router.post("/bulk-update")
async def bulk_update_incidents(body: BulkUpdateRequest, db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Bulk-update incidents: bump priority or post a status update for each selected incident."""
    if db_user.role not in ("Officer", "Executive"):
        raise HTTPException(status_code=403, detail="Only officers and executives can perform bulk updates")
    if body.action == "post_update" and not body.message:
        raise HTTPException(status_code=400, detail="Message is required for post_update action")

    incidents = db.query(Incident).filter(Incident.id.in_(body.incident_ids)).all()
    if not incidents:
        raise HTTPException(status_code=404, detail="No incidents found")
    if len(incidents) != len(body.incident_ids):
        found_ids = {i.id for i in incidents}
        missing = [i for i in body.incident_ids if i not in found_ids]
        raise HTTPException(status_code=404, detail=f"Incidents not found: {missing}")

    updated_count = 0
    now = datetime.utcnow()

    if body.action == "priority_bump":
        for inc in incidents:
            old_score = inc.priority_score
            new_score = min(int(old_score) + SLA_PRIORITY_BUMP, 100)
            if new_score == old_score:
                continue
            inc.priority_score = new_score
            inc.priority_label = _label_for_score(new_score)

            ph = PriorityHistory(
                incident_id=inc.id, old_score=old_score, new_score=new_score,
                reason=f"Bulk priority bump (+{SLA_PRIORITY_BUMP})", changed_at=now
            )
            db.add(ph)

            _write_audit_log(db, db_user.id, db_user.email, db_user.role,
                              "priority_bump", inc.id, "success",
                              f"Priority bumped {old_score} -> {new_score} (bulk update)")
            updated_count += 1

    elif body.action == "post_update":
        for inc in incidents:
            update = IncidentUpdate(id=str(uuid.uuid4()), incident_id=inc.id, message=body.message, user_id=db_user.id, user_name=db_user.full_name, created_at=now)
            db.add(update)
            db.flush()

            for comp in inc.complaints or []:
                notif = Notification(
                    id=str(uuid.uuid4()),
                    user_id=comp.user_id, complaint_id=comp.id,
                    type="status_update",
                    data=json.dumps({
                        "incident_id": inc.id, "incident_number": inc.incident_number,
                        "message": body.message, "update_id": update.id
                    }),
                    is_read=False,
                )
                db.add(notif)

            _write_audit_log(db, db_user.id, db_user.email, db_user.role,
                              "status_update", inc.id, "success",
                              f"Bulk update posted: {body.message[:100]}")
            updated_count += 1

    db.commit()
    return {"updated": updated_count, "total": len(body.incident_ids)}


@incident_router.get("/{incident_id}")
async def get_incident(incident_id: str, db: Session = Depends(get_db)):
    """Get incident by ID."""
    inc = db.query(Incident).options(joinedload(Incident.complaints), joinedload(Incident.priority_history)).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    affected = []
    if inc.affected_wards:
        try: affected = json.loads(inc.affected_wards)
        except: pass
    return {
        "id": inc.id, "incident_number": inc.incident_number, "category": inc.category,
        "department": get_department(inc.category),
        "ward": inc.ward, "cluster_size": inc.cluster_size, "priority_score": inc.priority_score,
        "priority_label": inc.priority_label, "status": inc.status, "summary": inc.summary,
        "recommended_action": inc.recommended_action, "days_open": inc.days_open,
        "resolution_note": inc.resolution_note,
        "verification_code": inc.verification_code,
        "created_at": inc.created_at.isoformat() if inc.created_at else None,
        "affected_wards": affected,
        "accepted_by": inc.accepted_by,
        "accepted_at": inc.accepted_at.isoformat() if inc.accepted_at else None,
        "impact_score": inc.impact_score,
        "economic_impact": inc.economic_impact,
        "beneficiaries": inc.beneficiaries,
        "complaints": [{
            "id": c.id, "complaint_number": c.id,
            "date_received": c.created_at.isoformat() if c.created_at else None,
            "text": c.title, "similarity_score": c.similarity_score or 0.85,
            "photo_duplicate_flag": c.photo_duplicate_flag,
            "photo_duplicate_of": c.photo_duplicate_of,
            "urgency_flag": getattr(c, "urgency_flag", "LOW"),
            "image_path": c.image_path,
            "complexity_label": getattr(c, "complexity_label", None),
            "complaint_language": getattr(c, "complaint_language", None),
        } for c in inc.complaints] if inc.complaints else [],
        "priority_history": [{
            "id": ph.id, "old_score": ph.old_score, "new_score": ph.new_score,
            "reason": ph.reason, "changed_at": ph.changed_at.isoformat() if ph.changed_at else None
        } for ph in inc.priority_history] if inc.priority_history else [],
    }


@incident_router.post("/merge")
async def merge_incidents(body: MergeIncidentsRequest, _: None = Depends(check_complaint_rate_limit), db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):  # FEATURE 2: previously rate-limited
    """Merge multiple incidents into one. Moves all complaints to the target and recalculates priority."""
    if db_user.role not in ("Officer", "Executive", "Commissioner"):
        raise HTTPException(status_code=403, detail="Only officers, executives, and commissioners can merge incidents")
    if len(body.incident_ids) < 2:
        raise HTTPException(status_code=400, detail="At least two incident IDs are required")

    incidents = db.query(Incident).options(joinedload(Incident.complaints)).filter(Incident.id.in_(body.incident_ids)).all()
    if len(incidents) != len(body.incident_ids):
        found = {i.id for i in incidents}
        missing = set(body.incident_ids) - found
        raise HTTPException(status_code=404, detail=f"Incidents not found: {', '.join(missing)}")

    # Pick the largest incident as target (most complaints), fallback to first
    target = max(incidents, key=lambda i: len(i.complaints) or 0)
    sources = [i for i in incidents if i.id != target.id]

    for src in sources:
        for c in src.complaints:
            c.incident_id = target.id
            c.merge_reason = f"Merged from {src.incident_number} by officer action"
            if c.user_id:
                _create_notification(
                    db, c.user_id, "merged",
                    complaint_id=c.id,
                    data={"incident_number": target.incident_number, "src_incident_number": src.incident_number},
                )
        db.query(PriorityHistory).filter(PriorityHistory.incident_id == src.id).delete()
        db.delete(src)

    db.flush()

    # Recalculate cluster size and summary
    target.cluster_size = db.query(Complaint).filter(Complaint.incident_id == target.id).count()

    # Build merged summary
    all_titles = [c.title for c in target.complaints][:5]
    target.summary = "; ".join(all_titles) if all_titles else target.summary

    # Recalculate priority
    from priority.utils import calculate_days_open
    from priority.priority import PriorityEngine
    dates = [c.created_at for c in target.complaints if c.created_at]
    first_date = min(dates).isoformat() if dates else datetime.utcnow().isoformat()
    last_date = max(dates).isoformat() if dates else datetime.utcnow().isoformat()
    location_hints = list({c.location for c in target.complaints if c.location})

    try:
        engine = PriorityEngine()
        result = engine.compute(
            incident_id=target.id,
            cluster_size=target.cluster_size,
            first_complaint_date=first_date,
            last_complaint_date=last_date,
            category=target.category,
            location_hints=location_hints,
        )
        old_score = target.priority_score
        if abs(target.priority_score - result.priority_score) > 0.01:
            db.add(PriorityHistory(
                id=str(uuid.uuid4()), incident_id=target.id,
                old_score=old_score, new_score=result.priority_score,
                reason=f"Merged {len(sources)} incident(s) into {target.incident_number}"
            ))
        target.priority_score = result.priority_score
        target.priority_label = result.priority_label
        target.days_open = calculate_days_open(first_date)
    except Exception as e:
        logger.warning("Priority recalculation failed after merge: %s", e)

    db.commit()

    _write_audit_log(db, db_user.id, db_user.email, db_user.role, "incident_merge",
                     target.id, "success",
                     f"Merged incidents {', '.join(src.incident_number for src in sources)} into {target.incident_number}")

    # Notify officers in the department
    department = get_department(target.category)
    _notify_department_officers(
        db, department, "officer_merged",
        data={"incident_number": target.incident_number, "incident_id": target.id, "category": target.category}
    )
    _check_aging_notifications(db, department)

    return {"message": f"Incidents merged into {target.incident_number}", "incident_id": target.id}


@incident_router.post("/{incident_id}/merge")
async def merge_single_incident(incident_id: str, body: MergeSingleRequest, db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Merge a source incident into a target incident (Officer/Executive only)."""
    if db_user.role not in ("Officer", "Executive"):
        raise HTTPException(status_code=403, detail="Only officers and executives can merge incidents")

    source = db.query(Incident).options(joinedload(Incident.complaints)).filter(Incident.id == incident_id).first()
    target = db.query(Incident).options(joinedload(Incident.complaints)).filter(Incident.id == body.target_incident_id).first()
    if not source or not target:
        raise HTTPException(status_code=404, detail="Source or target incident not found")
    if source.category != target.category:
        raise HTTPException(status_code=400, detail="Incidents must belong to the same category to merge")
    if source.id == target.id:
        raise HTTPException(status_code=400, detail="Cannot merge an incident into itself")

    for c in source.complaints:
        c.incident_id = target.id
        c.merge_reason = f"Merged from {source.incident_number} into {target.incident_number} by officer action"

    db.query(PriorityHistory).filter(PriorityHistory.incident_id == source.id).delete()
    db.delete(source)
    db.flush()

    target.cluster_size = db.query(Complaint).filter(Complaint.incident_id == target.id).count()

    db.commit()

    _write_audit_log(db, db_user.id, db_user.email, db_user.role, "incident_merge",
                     target.id, "success",
                     f"Merged {source.incident_number} into {target.incident_number}")

    return {
        "id": target.id, "incident_number": target.incident_number, "category": target.category,
        "cluster_size": target.cluster_size, "status": target.status
    }


@incident_router.post("/{incident_id}/split/{complaint_id}")
async def split_complaint(incident_id: str, complaint_id: str, _: None = Depends(check_complaint_rate_limit), db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):  # FEATURE 2: previously rate-limited
    """Remove a complaint from an incident and create a new standalone incident for it."""
    if db_user.role not in ("Officer", "Executive", "Commissioner"):
        raise HTTPException(status_code=403, detail="Only officers, executives, and commissioners can split complaints")

    incident = db.query(Incident).options(joinedload(Incident.complaints)).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    complaint = db.query(Complaint).filter(Complaint.id == complaint_id, Complaint.incident_id == incident_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found in this incident")

    if incident.cluster_size <= 1:
        raise HTTPException(status_code=400, detail="Cannot split the last complaint from an incident. Delete the incident instead.")

    # Create new incident for the split complaint
    new_incident = Incident(
        id=str(uuid.uuid4()),
        incident_number=f"INC-{uuid.uuid4().hex[:6].upper()}",
        category=complaint.predicted_category or incident.category,
        ward=complaint.ward or incident.ward,
        cluster_size=1,
        priority_score=0.0,
        priority_label="Low",
        summary=complaint.title,
    )
    db.add(new_incident)
    db.flush()

    # Move the complaint
    old_merge_reason = complaint.merge_reason
    complaint.incident_id = new_incident.id
    complaint.merge_reason = f"Split from {incident.incident_number} by officer action"

    if complaint.user_id:
        _create_notification(
            db, complaint.user_id, "split",
            complaint_id=complaint.id,
            data={"incident_number": new_incident.incident_number, "src_incident_number": incident.incident_number},
        )

    # Update original incident
    incident.cluster_size = db.query(Complaint).filter(Complaint.incident_id == incident.id).count()

    # Recalculate priority for original incident
    from priority.utils import calculate_days_open
    from priority.priority import PriorityEngine
    orig_dates = [c.created_at for c in incident.complaints if c.created_at and c.id != complaint_id]
    if orig_dates:
        first_date = min(orig_dates).isoformat()
        last_date = max(orig_dates).isoformat()
        orig_location_hints = list({c.location for c in incident.complaints if c.location and c.id != complaint_id})
        try:
            engine = PriorityEngine()
            result = engine.compute(
                incident_id=incident.id, cluster_size=incident.cluster_size,
                first_complaint_date=first_date, last_complaint_date=last_date,
                category=incident.category, location_hints=orig_location_hints,
            )
            old_score = incident.priority_score
            if abs(incident.priority_score - result.priority_score) > 0.01:
                db.add(PriorityHistory(
                    id=str(uuid.uuid4()), incident_id=incident.id,
                    old_score=old_score, new_score=result.priority_score,
                    reason=f"Complaint {complaint_id[:8]} split out to {new_incident.incident_number}"
                ))
            incident.priority_score = result.priority_score
            incident.priority_label = result.priority_label
            incident.days_open = calculate_days_open(first_date)
        except Exception as e:
            logger.warning("Priority recalculation failed after split (original): %s", e)

    # Recalculate priority for new incident
    new_dates = [complaint.created_at] if complaint.created_at else []
    if new_dates:
        try:
            engine = PriorityEngine()
            result = engine.compute(
                incident_id=new_incident.id, cluster_size=1,
                first_complaint_date=new_dates[0].isoformat(),
                last_complaint_date=new_dates[0].isoformat(),
                category=new_incident.category,
                location_hints=[complaint.location] if complaint.location else [],
            )
            new_incident.priority_score = result.priority_score
            new_incident.priority_label = result.priority_label
            new_incident.days_open = calculate_days_open(new_dates[0].isoformat())
        except Exception as e:
            logger.warning("Priority recalculation failed after split (new): %s", e)

    # Record priority history for the change
    db.add(PriorityHistory(
        id=str(uuid.uuid4()), incident_id=incident.id,
        old_score=incident.priority_score, new_score=incident.priority_score,
        reason=f"Cluster size changed after split: {incident.cluster_size + 1} -> {incident.cluster_size}"
    ))

    db.commit()

    _write_audit_log(db, db_user.id, db_user.email, db_user.role, "incident_split",
                     incident.id, "success",
                     f"Complaint {complaint_id[:8]} split from {incident.incident_number} to new {new_incident.incident_number}")

    # Notify officers in both departments
    dept_orig = get_department(incident.category)
    dept_new = get_department(new_incident.category)
    for dept in {dept_orig, dept_new}:
        _notify_department_officers(
            db, dept, "officer_split",
            data={
                "incident_number_orig": incident.incident_number,
                "incident_number_new": new_incident.incident_number,
                "complaint_id": complaint.id,
            }
        )
        _check_aging_notifications(db, dept)

    return {
        "message": f"Complaint split to new incident {new_incident.incident_number}",
        "original_incident_id": incident.id,
        "new_incident_id": new_incident.id,
        "new_incident_number": new_incident.incident_number,
    }


@incident_router.patch("/{incident_id}/status")
async def update_incident_status(incident_id: str, body: UpdateStatusRequest, db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update an incident's status. Creates notifications for all linked complaint owners.
    If the requested status is 'resolved', the incident goes to 'pending_verification'
    instead, and the citizen must confirm via POST /incidents/{id}/verify-resolution."""
    if db_user.role not in ("Officer", "Executive", "Commissioner"):
        raise HTTPException(status_code=403, detail="Only officers, executives, and commissioners can update incident status")
    if body.status not in ("open", "in-progress", "resolved", "pending_verification"):
        raise HTTPException(status_code=400, detail="Status must be one of: open, in-progress, resolved, pending_verification")

    incident = db.query(Incident).options(joinedload(Incident.complaints)).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    old_status = incident.status
    if old_status == body.status:
        raise HTTPException(status_code=400, detail="Incident already has this status")

    # Intercept 'resolved' — set to pending_verification and notify citizen
    if body.status == "resolved":
        code = f"{random.randint(100000, 999999)}"
        incident.status = "pending_verification"
        incident.status_changed_at = datetime.utcnow()
        incident.verification_code = code
        incident.resolution_note = body.resolution_note
        db.commit()

        # Notify citizens with the verification code
        for c in incident.complaints:
            if c.user_id:
                _create_notification(
                    db, c.user_id, "pending_verification",
                    complaint_id=c.id,
                    data={
                        "incident_number": incident.incident_number,
                        "verification_code": code,
                        "message": "Your issue has been marked as fixed. Please confirm with the verification code.",
                    },
                )
                _send_push_notification(c.user_id, "Pending Verification",
                                        f"Incident {incident.incident_number} has been marked as fixed. Please confirm.",
                                        db=db)

        _write_audit_log(db, db_user.id, db_user.email, db_user.role, "incident_status_update",
                         incident.id, "success",
                         f"Status set to pending_verification (awaiting citizen confirmation)")

        # Notify officers
        department = get_department(incident.category)
        _notify_department_officers(
            db, department, "officer_status_change",
            data={
                "incident_number": incident.incident_number,
                "incident_id": incident.id,
                "old_status": old_status,
                "new_status": "pending_verification",
            }
        )

        await manager.broadcast("incident:update", {
            "incident_id": incident.id,
            "old_status": old_status,
            "new_status": "pending_verification",
        })
        return {
            "message": "Citizen verification required. A confirmation code has been sent to the complainant.",
            "incident_id": incident.id,
            "status": "pending_verification",
        }

    # Non-resolution status change: apply directly
    incident.status = body.status
    incident.status_changed_at = datetime.utcnow()
    db.commit()

    # Notify all citizens whose complaints are linked to this incident
    for c in incident.complaints:
        if c.user_id:
            _create_notification(
                db, c.user_id, "status_change",
                complaint_id=c.id,
                data={"old_status": old_status, "new_status": body.status, "incident_number": incident.incident_number},
            )
            _send_push_notification(c.user_id, "Status Update",
                                    f"Incident {incident.incident_number} changed from {old_status} to {body.status}",
                                    db=db)

    _write_audit_log(db, db_user.id, db_user.email, db_user.role, "incident_status_update",
                     incident.id, "success",
                     f"Status changed from {old_status} to {body.status}")

    # Notify officers in the department
    department = get_department(incident.category)
    _notify_department_officers(
        db, department, "officer_status_change",
        data={
            "incident_number": incident.incident_number,
            "incident_id": incident.id,
            "old_status": old_status,
            "new_status": body.status,
        }
    )
    _check_aging_notifications(db, department)

    await manager.broadcast("incident:update", {
        "incident_id": incident.id,
        "old_status": old_status,
        "new_status": body.status,
    })
    return {"message": f"Incident status updated to {body.status}", "incident_id": incident.id, "status": body.status}


@incident_router.patch("/{incident_id}/forward")
async def forward_incident(incident_id: str, body: ForwardRequest, db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Forward an incident to a different department."""
    if db_user.role != "Officer":
        raise HTTPException(status_code=403, detail="Only officers can forward incidents")

    incident = db.query(Incident).options(joinedload(Incident.complaints)).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    old_dept = get_department(incident.category)
    new_dept = body.new_department

    if old_dept == new_dept:
        raise HTTPException(status_code=400, detail="Incident is already assigned to this department")

    new_dept_slug = get_slug_for_department(new_dept)
    old_categories = [cat for cat, slug in CATEGORY_DEPT_MAP.items() if slug == new_dept_slug]
    if not old_categories:
        raise HTTPException(status_code=400, detail="No categories found for the target department")

    new_category = old_categories[0]
    old_category = incident.category
    incident.category = new_category

    db.commit()

    _write_audit_log(db, db_user.id, db_user.email, db_user.role, "incident_forward",
                     incident.id, "success",
                     f"Forwarded from {old_dept} ({old_category}) to {new_dept} ({new_category})")

    _notify_department_officers(
        db, new_dept, "incident_forwarded",
        data={
            "incident_id": incident.id,
            "incident_number": incident.incident_number,
            "category": new_category,
            "old_department": old_dept,
            "new_department": new_dept,
            "forwarded_by": db_user.full_name,
        }
    )

    return {
        "id": incident.id,
        "incident_number": incident.incident_number,
        "old_department": old_dept,
        "new_department": new_dept,
        "old_category": old_category,
        "new_category": new_category,
    }


@incident_router.patch("/{incident_id}/category")
def correct_incident_category(incident_id: str, body: CategoryCorrectRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in ('Officer', 'Executive'):
        raise HTTPException(status_code=403, detail="Only officers and executives can correct category")
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    old_cat = incident.category
    if not incident.original_category:
        incident.original_category = old_cat
    incident.category = body.category
    db.commit()
    _write_audit_log(db, current_user.id, current_user.email, current_user.role, 'category_correct', incident_id, 'success', f"Category corrected from {old_cat} to {body.category}")
    return {"incident_id": incident_id, "old_category": old_cat, "new_category": body.category}


@incident_router.post("/{incident_id}/updates")
async def post_incident_update(incident_id: str, body: IncidentUpdateRequest, db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Post a free-text progress update visible to citizens in the tracking timeline.
    Does not change the incident's formal status."""
    if db_user.role not in ("Officer", "Executive"):
        raise HTTPException(status_code=403, detail="Only officers and executives can post updates")
    incident = db.query(Incident).options(joinedload(Incident.complaints)).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    update = IncidentUpdate(
        id=str(uuid.uuid4()),
        incident_id=incident.id,
        user_id=db_user.id,
        user_name=db_user.full_name,
        message=body.message.strip(),
        created_at=datetime.utcnow(),
    )
    db.add(update)
    db.flush()

    _write_audit_log(db, db_user.id, db_user.email, db_user.role, "incident_update_posted",
                     incident.id, "success",
                     f"Update: {body.message[:200]}")

    for c in incident.complaints:
        if c.user_id:
            _create_notification(
                db, c.user_id, "incident_update",
                complaint_id=c.id,
                data={
                    "incident_number": incident.incident_number,
                    "incident_id": incident.id,
                    "message": body.message,
                    "officer_name": db_user.full_name,
                },
            )

    db.commit()
    return {
        "message": "Update posted",
        "update_id": update.id,
        "created_at": update.created_at.isoformat(),
    }


@incident_router.post("/{incident_id}/comments")
def post_comment(incident_id: str, body: CommentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in ('Officer', 'Executive'):
        raise HTTPException(status_code=403, detail="Only officers and executives can comment")
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    comment = IncidentComment(
        incident_id=incident_id,
        user_id=current_user.id,
        user_name=current_user.full_name,
        role=current_user.role,
        message=body.message
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return {"id": comment.id, "message": comment.message, "user_name": comment.user_name, "role": comment.role, "created_at": comment.created_at.isoformat()}

@incident_router.get("/{incident_id}/comments")
def get_comments(incident_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in ('Officer', 'Executive'):
        raise HTTPException(status_code=403, detail="Only officers and executives can view comments")
    comments = db.query(IncidentComment).filter(IncidentComment.incident_id == incident_id).order_by(IncidentComment.created_at.asc()).all()
    return [{"id": c.id, "message": c.message, "user_name": c.user_name, "role": c.role, "created_at": c.created_at.isoformat()} for c in comments]


@incident_router.patch("/{incident_id}/note")
async def update_private_note(incident_id: str, body: NoteUpdateRequest, db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update the private note on an incident (Officer/Executive only)."""
    if db_user.role not in ("Officer", "Executive"):
        raise HTTPException(status_code=403, detail="Only officers and executives can add private notes")
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    incident.private_note = body.note
    incident.private_note_updated_at = datetime.utcnow()
    # Recompute resolution quality score when note changes
    quality = 0
    if incident.resolution_photo_path: quality += 30
    if incident.resolution_note: quality += min(len(incident.resolution_note) * 2, 40)
    if incident.days_open and incident.days_open <= 2: quality += 30
    elif incident.days_open and incident.days_open <= 5: quality += 15
    # FEATURE 9: citizen_rating factor
    if incident.id:
        rating = db.query(func.avg(Complaint.citizen_rating)).filter(
            Complaint.incident_id == incident.id,
            Complaint.citizen_rating.isnot(None),
        ).scalar()
        if rating:
            if rating >= 4: quality += 20
            elif rating >= 3: quality += 10
            else: quality -= 10
    incident.resolution_quality_score = max(0, quality)
    db.commit()
    _write_audit_log(db, db_user.id, db_user.email, db_user.role, "private_note_update",
                     incident.id, "success")
    return {"success": True}


@incident_router.post("/{incident_id}/resolution-photo")
async def upload_resolution_photo(incident_id: str, file: UploadFile = File(...), db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Upload a resolution photo for an incident (Officer/Executive only)."""
    if db_user.role not in ("Officer", "Executive"):
        raise HTTPException(status_code=403, detail="Only officers and executives can upload resolution photos")
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    data = await file.read()
    err = validate_file(file.filename or "upload", file.content_type or "", len(data))
    if err:
        raise HTTPException(status_code=400, detail=err)
    uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "photo.jpg")[1] or ".jpg"
    saved_name = f"resolution_{incident_id}_{uuid.uuid4().hex[:8]}{ext}"
    saved_path = os.path.join(uploads_dir, saved_name)
    with open(saved_path, "wb") as f:
        f.write(data)
    incident.resolution_photo_path = saved_path
    # Compute resolution quality score
    quality = 0
    if incident.resolution_photo_path: quality += 30
    if incident.resolution_note: quality += min(len(incident.resolution_note) * 2, 40)
    if incident.days_open and incident.days_open <= 2: quality += 30
    elif incident.days_open and incident.days_open <= 5: quality += 15
    # FEATURE 9: citizen_rating factor
    if incident.id:
        rating = db.query(func.avg(Complaint.citizen_rating)).filter(
            Complaint.incident_id == incident.id,
            Complaint.citizen_rating.isnot(None),
        ).scalar()
        if rating:
            if rating >= 4: quality += 20
            elif rating >= 3: quality += 10
            else: quality -= 10
    incident.resolution_quality_score = max(0, quality)
    db.commit()
    _write_audit_log(db, db_user.id, db_user.email, db_user.role, "resolution_photo_upload",
                     incident.id, "success")
    return {"resolution_photo_url": f"/incidents/{incident_id}/resolution-photo"}


# === Escalation & Ward-Level Routes ===


@incident_router.post("/{incident_id}/escalate")
async def escalate_incident(incident_id: str, body: EscalateRequest, db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Flag an incident for escalation. Councillors and commissioners can escalate.
    Once escalated, the incident appears in MLA/Collector oversight dashboards."""
    if db_user.role not in ("Councillor", "Commissioner", "Executive"):
        raise HTTPException(status_code=403, detail="Only councillors, commissioners, and executives can escalate incidents")

    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    if incident.escalated:
        raise HTTPException(status_code=400, detail="Incident is already escalated")

    incident.escalated = True
    incident.escalated_at = datetime.utcnow()
    incident.escalated_by = db_user.email
    incident.escalation_reason = body.reason
    db.commit()

    # Notify linked complaint owners
    for c in incident.complaints:
        if c.user_id:
            _create_notification(
                db, c.user_id, "escalated",
                complaint_id=c.id,
                data={
                    "incident_number": incident.incident_number,
                    "reason": body.reason,
                    "escalated_by": db_user.email,
                },
            )

    _write_audit_log(db, db_user.id, db_user.email, db_user.role, "incident_escalate",
                     incident.id, "success", f"Reason: {body.reason}")

    await manager.broadcast("incident:update", {
        "incident_id": incident.id,
        "escalated": True,
    })
    return {"message": "Incident escalated", "incident_id": incident.id, "reason": body.reason}


@incident_router.post("/{incident_id}/verify-resolution")
async def verify_resolution(incident_id: str, body: VerifyResolutionRequest, _: None = Depends(check_verify_rate_limit), db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):  # FEATURE 2: previously rate-limited
    """Verify resolution as the citizen who filed the original complaint.
    Only the citizen who owns a complaint linked to this incident can confirm.
    Rate-limited to 3 attempts/min to prevent code-guessing."""
    if db_user.role != "Citizen":
        raise HTTPException(status_code=403, detail="Only citizens can verify resolution")

    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    if incident.status != "pending_verification":
        raise HTTPException(status_code=400, detail="Incident is not awaiting citizen verification")

    # Verify the citizen owns at least one complaint linked to this incident
    complaint = db.query(Complaint).filter(
        Complaint.incident_id == incident_id,
        Complaint.user_id == db_user.id
    ).first()
    if not complaint:
        raise HTTPException(status_code=403, detail="You are not authorized to verify this incident")

    if incident.verification_code != body.code:
        _write_audit_log(db, db_user.id, db_user.email, db_user.role, "verify_resolution",
                         incident.id, "failure", "Invalid verification code")
        raise HTTPException(status_code=400, detail="Invalid verification code. Please check the code sent to you.")

    # Code matches — mark as truly resolved
    old_status = incident.status

    # FEATURE 17: Impact assessment
    severity_weights = {"Roads": 3, "Water Supply": 4, "Waste Management": 2, "Sanitation": 3, "Street Lighting": 1, "Electricity": 4, "Public Health": 5}
    cat = incident.category or ""
    weight = severity_weights.get(cat, 1)
    days = incident.days_open or 1
    incident.impact_score = incident.cluster_size * 4
    incident.economic_impact = weight * days * 100
    incident.beneficiaries = incident.cluster_size * 3

    incident.status = "resolved"
    incident.verification_code = None

    # FEATURE 15: auto-close follow-up complaints linked to this incident
    follow_up_complaints = db.query(Complaint).filter(
        Complaint.incident_id == incident.id,
        or_(
            Complaint.merge_reason.ilike("%follow_up%"),
            Complaint.tags.ilike("%follow-up%"),
        ),
    ).all()
    for fc in follow_up_complaints:
        fc_incident = db.query(Incident).filter(Incident.id == fc.incident_id).first()
        if fc_incident and fc_incident.status not in ("resolved", "closed"):
            fc_incident.status = "closed"
            fc_incident.status_changed_at = datetime.utcnow()
            fc_incident.resolution_note = "Auto-closed: parent incident resolved"
            _write_audit_log(
                db, "system", "system", "System",
                "auto_close_follow_up", fc_incident.id, "success",
                f"Auto-closed follow-up complaint {fc.id} linked to resolved incident {incident.incident_number}",
            )

    db.commit()

    # Notify the citizen
    _create_notification(
        db, db_user.id, "status_change",
        complaint_id=complaint.id,
        data={"old_status": old_status, "new_status": "resolved", "incident_number": incident.incident_number,
              "message": "Resolution confirmed. Thank you for confirming!"},
    )
    _send_push_notification(db_user.id, "Resolution Confirmed",
                            f"Incident {incident.incident_number} resolved. Thank you!",
                            db=db)

    _write_audit_log(db, db_user.id, db_user.email, db_user.role, "verify_resolution",
                     incident.id, "success", "Citizen confirmed resolution")

    await manager.broadcast("incident:update", {
        "incident_id": incident.id,
        "old_status": old_status,
        "new_status": "resolved",
    })
    return {"message": "Resolution confirmed. Thank you!", "incident_id": incident.id, "status": "resolved"}


@incident_router.post("/{incident_id}/reopen")
async def reopen_incident(incident_id: str, request: Request, _: None = Depends(check_reopen_rate_limit), db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):  # FEATURE 2: newly rate-limited
    """Reopen a resolved/pending_verification incident. Only the complaint submitter can reopen."""
    incident = db.query(Incident).options(joinedload(Incident.complaints)).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    if incident.status not in ("resolved", "pending_verification", "closed"):
        raise HTTPException(status_code=400, detail="Only resolved or closed incidents can be reopened")

    # Verify the citizen owns at least one complaint linked to this incident
    complaint = db.query(Complaint).filter(
        Complaint.incident_id == incident_id,
        Complaint.user_id == db_user.id
    ).first()
    if not complaint:
        raise HTTPException(status_code=403, detail="You are not authorized to reopen this incident")

    old_status = incident.status
    incident.status = "open"
    incident.verification_code = None
    incident.resolution_note = None
    db.commit()

    _create_notification(
        db, db_user.id, "status_change",
        complaint_id=complaint.id,
        data={"old_status": old_status, "new_status": "open", "incident_number": incident.incident_number,
              "message": "Your complaint has been reopened."},
    )
    _send_push_notification(db_user.id, "Incident Reopened",
                            f"Incident {incident.incident_number} has been reopened.",
                            db=db)

    _write_audit_log(db, db_user.id, db_user.email, db_user.role, "incident_reopen",
                     incident.id, "success", f"Citizen reopened incident from {old_status} to open")

    await manager.broadcast("incident:update", {
        "incident_id": incident.id,
        "old_status": old_status,
        "new_status": "open",
    })
    return {"message": "Incident reopened", "incident_id": incident.id, "status": "open"}


@incident_router.post("/{incident_id}/appeal")
async def appeal_incident(incident_id: str, body: AppealRequest, request: Request, _: None = Depends(check_appeal_rate_limit), db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):  # FEATURE 2: newly rate-limited
    """Citizen appeal — formal escalation with reason when resolution is unsatisfactory.
    Sets appealed flag, bumps priority, notifies department officers, and writes audit log.
    Distinct from reopen (which is a simple retry with no escalation)."""
    if db_user.role != "Citizen":
        raise HTTPException(status_code=403, detail="Only citizens can appeal")

    incident = db.query(Incident).options(joinedload(Incident.complaints)).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    if incident.status not in ("resolved", "closed", "pending_verification"):
        raise HTTPException(status_code=400, detail="Only resolved or closed incidents can be appealed")

    complaint = db.query(Complaint).filter(
        Complaint.incident_id == incident_id,
        Complaint.user_id == db_user.id
    ).first()
    if not complaint:
        raise HTTPException(status_code=403, detail="You are not authorized to appeal this incident")

    old_status = incident.status
    incident.status = "open"
    incident.appealed = True
    incident.appeal_reason = body.reason
    incident.appealed_at = datetime.utcnow()
    incident.verification_code = None

    # Bump priority — increase by 25% or at least 5 points
    old_score = incident.priority_score
    incident.priority_score = max(old_score + 5, old_score * 1.25)
    if incident.priority_score > 100:
        incident.priority_score = 100.0

    # Re-label priority
    incident.priority_label = "Critical" if incident.priority_score >= 75 else "High" if incident.priority_score >= 50 else "Medium" if incident.priority_score >= 25 else "Low"

    db.commit()

    # Notify the citizen
    await manager.broadcast("incident:appealed", {
        "incident_id": incident.id,
        "old_status": old_status,
        "new_status": "open",
    })
    _create_notification(
        db, db_user.id, "status_change",
        complaint_id=complaint.id,
        data={"old_status": old_status, "new_status": "open", "incident_number": incident.incident_number,
              "message": "Your appeal has been filed. Your complaint has been reopened and escalated."},
    )
    _send_push_notification(db_user.id, "Appeal Filed",
                            f"Your appeal for incident {incident.incident_number} has been filed.",
                            db=db)

    # Notify department officers
    dept = get_department(incident.category or "")
    _notify_department_officers(
        db, dept, "appeal_filed",
        data={"incident_number": incident.incident_number, "incident_id": incident.id,
              "appeal_reason": body.reason, "priority": incident.priority_label},
    )

    _write_audit_log(db, db_user.id, db_user.email, db_user.role, "incident_appeal",
                     incident.id, "success",
                     f"Citizen appealed incident from {old_status}. Reason: {body.reason[:200]}")

    return {"message": "Appeal filed successfully. Your complaint has been reopened and escalated.", "incident_id": incident.id, "status": "open", "appealed": True}


@complaint_router.get("/ward/{ward}")
async def get_ward_complaints(ward: str, db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get complaints for a specific ward. Councillor sees only their assigned ward;
    Commissioner and Executive can view any ward."""
    if db_user.role == "Councillor":
        if db_user.ward and db_user.ward != ward:
            raise HTTPException(status_code=403, detail="Councillors can only view their assigned ward")
    elif db_user.role not in ("Commissioner", "Executive", "Officer"):
        raise HTTPException(status_code=403, detail="Access denied")

    complaints = db.query(Complaint).options(joinedload(Complaint.incident)).filter(
        Complaint.ward == ward
    ).order_by(Complaint.created_at.desc()).all()

    result = []
    for c in complaints:
        incident = c.incident
        result.append({
            "id": c.id, "title": c.title, "description": c.description,
            "location": c.location, "ward": c.ward,
            "predicted_category": c.predicted_category, "confidence": c.confidence,
            "priority": c.priority, "similarity_score": c.similarity_score,
            "merge_reason": c.merge_reason,
            "date_received": c.created_at.isoformat() if c.created_at else None,
            "incident": {
                "id": incident.id, "incident_number": incident.incident_number,
                "category": incident.category, "status": incident.status,
                "priority_label": incident.priority_label, "cluster_size": incident.cluster_size,
                "escalated": incident.escalated, "days_open": incident.days_open,
            } if incident else None,
        })
    return {"complaints": result, "ward": ward, "count": len(result)}


search_router = APIRouter(prefix="/search", tags=["Search"])

@search_router.get("")
def search_complaints(
    q: str = Query(..., min_length=1),
    category: Optional[str] = Query(None, description="Exact match on predicted_category"),
    ward: Optional[str] = Query(None, description="Exact match on ward"),
    status: Optional[str] = Query(None, description="Exact match on incident status"),
    priority: Optional[str] = Query(None, description="Exact match on priority"),
    date_from: Optional[str] = Query(None, description="Filter created_at >= date_from (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter created_at <= date_to (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(20, ge=1, le=200, description="Items per page"),
    request: Request = None,
    _: None = Depends(check_search_rate_limit),
    db: Session = Depends(get_db),
):  # FEATURE 4: advanced search filters
    pattern = f"%{q}%"
    query = db.query(Complaint).options(joinedload(Complaint.incident)).filter(
        or_(Complaint.title.ilike(pattern), Complaint.description.ilike(pattern))
    )
    if category:
        query = query.filter(Complaint.predicted_category == category)
    if ward:
        query = query.filter(Complaint.ward == ward)
    if status:
        query = query.filter(Complaint.incident.has(Incident.status == status))
    if priority:
        query = query.filter(Complaint.priority == priority)
    if date_from:
        try:
            dt_from = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(Complaint.created_at >= dt_from)
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(Complaint.created_at <= dt_to)
        except ValueError:
            pass

    total = query.count()
    offset_val = (page - 1) * limit
    results = query.order_by(Complaint.created_at.desc()).offset(offset_val).limit(limit).all()
    return {
        "results": [{
            "id": c.id, "title": c.title, "description": c.description[:100],
            "ward": c.ward, "predicted_category": c.predicted_category,
            "priority": c.priority,
            "status": c.incident.status if c.incident else None,
            "date_received": c.created_at.isoformat() if c.created_at else None,
        } for c in results],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


notifications_router = APIRouter(prefix="/notifications", tags=["Notifications"])


@notifications_router.get("")
async def get_notifications(db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current user's notifications, most recent first."""
    notifs = db.query(Notification).filter(Notification.user_id == db_user.id).order_by(Notification.created_at.desc()).limit(50).all()
    return [
        NotificationResponse(
            id=n.id,
            user_id=n.user_id,
            complaint_id=n.complaint_id,
            type=n.type,
            data=json.loads(n.data) if n.data else None,
            is_read=n.is_read,
            created_at=n.created_at.isoformat() if n.created_at else "",
        )
        for n in notifs
    ]


@notifications_router.post("/{notification_id}/read")
async def mark_notification_read(notification_id: str, db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Mark a single notification as read."""
    notif = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == db_user.id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    db.commit()
    return {"message": "Notification marked as read"}


@notifications_router.post("/read-all")
async def mark_all_notifications_read(db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Mark all of the current user's notifications as read."""
    db.query(Notification).filter(Notification.user_id == db_user.id, Notification.is_read == False).update({"is_read": True})
    db.commit()
    return {"message": "All notifications marked as read"}


# FEATURE 3: push notification structure
class PushSubscribeRequest(BaseModel):
    endpoint: str
    keys: dict


@notifications_router.post("/subscribe")
async def subscribe_push(body: PushSubscribeRequest, db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.query(PushSubscription).filter(PushSubscription.user_id == db_user.id).first()
    if existing:
        existing.endpoint = body.endpoint
        existing.p256dh = body.keys.get("p256dh", "")
        existing.auth = body.keys.get("auth", "")
    else:
        sub = PushSubscription(
            id=str(uuid.uuid4()),
            user_id=db_user.id,
            endpoint=body.endpoint,
            p256dh=body.keys.get("p256dh", ""),
            auth=body.keys.get("auth", ""),
        )
        db.add(sub)
    db.commit()
    return {"status": "subscribed"}


@notifications_router.delete("/unsubscribe")
async def unsubscribe_push(db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(PushSubscription).filter(PushSubscription.user_id == db_user.id).delete()
    db.commit()
    return {"status": "unsubscribed"}


def _send_push_notification(user_id: str, title: str, body: str, url: str = "/", db: Optional[Session] = None):
    """Send a Web Push notification to the user's subscribed device.
    Uses pywebpush if available; silently falls back to logging.
    On failure (expired subscription), deletes the subscription."""
    if db is None:
        return
    try:
        sub = db.query(PushSubscription).filter(PushSubscription.user_id == user_id).first()
        if not sub:
            return
        vapid = get_vapid_keys()
        if not vapid["public_key"] or not vapid["private_key"]:
            logger.info("VAPID keys not configured — skipping push for user %s", user_id)
            return
        try:
            from pywebpush import webpush
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=json.dumps({"title": title, "body": body, "url": url}),
                vapid_private_key=vapid["private_key"],
                vapid_claims={"sub": f"mailto:{vapid['claim_email']}"},
            )
        except ImportError:
            logger.info("pywebpush not installed — push notification logged for user %s: %s — %s", user_id, title, body)
        except Exception as push_err:
            err_str = str(push_err).lower()
            if "expired" in err_str or "410" in err_str or "gone" in err_str:
                db.query(PushSubscription).filter(PushSubscription.user_id == user_id).delete()
                db.flush()
                logger.info("Removed expired push subscription for user %s", user_id)
            else:
                logger.warning("Push notification failed for user %s: %s", user_id, push_err)
    except Exception:
        logger.warning("Push notification lookup failed for user %s", user_id)


# === Incident Intelligence Routes ===
# ... (existing intelligence_router)

# === Predictive Analytics Routes ===
# ... (existing prediction_router)

# === Decision Support Routes ===
# ... (existing decision_router)

# === Governance Copilot Routes ===
# ... (existing copilot_router)

# === Governance Knowledge Routes ===
# ... (existing knowledge_router)

# === Auth Routes ===

auth_router = APIRouter(prefix="/auth", tags=["Auth"])

@auth_router.post("/register")
async def register(user: UserRegister, request: Request, _: None = Depends(check_auth_rate_limit), db: Session = Depends(get_db)):  # FEATURE 2: previously rate-limited
    """Register a new citizen account. Government accounts must be created by Executive through Officer Management."""
    if user.email.endswith("@gov.in"):
        raise HTTPException(status_code=400, detail="Government accounts must be created by an Executive. Use @gov.in emails are not allowed for public registration.")
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_pw = hash_password(user.password)
    # FEATURE 14: email verification
    verification_code = f"{random.randint(100000, 999999)}"
    new_user = User(
        id=str(uuid.uuid4()),
        full_name=user.full_name,
        email=user.email,
        password_hash=hashed_pw,
        phone=user.phone,
        district=user.district,
        ward=user.ward,
        role="Citizen",
        verification_code=verification_code,
        email_verified=False,
    )
    db.add(new_user)
    db.commit()
    return {"message": "User registered successfully", "user_id": new_user.id, "role": new_user.role, "verification_code": verification_code}

@auth_router.post("/verify-email")
async def verify_email(body: VerifyEmailRequest, db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Verify email with 6-digit code."""
    # FEATURE 14: email verification
    if db_user.email_verified:
        raise HTTPException(status_code=400, detail="Email already verified")
    if db_user.verification_code != body.code:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    db_user.email_verified = True
    db_user.verification_code = None
    db.commit()
    return {"message": "Email verified successfully"}

@auth_router.post("/login")
async def login(user: UserLogin, request: Request, response: Response, _: None = Depends(check_auth_rate_limit), db: Session = Depends(get_db)):  # FEATURE 2: previously rate-limited
    """Authenticate user and return JWT token as httpOnly cookie."""
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.password_hash):
        _write_audit_log(db, None, user.email, None, "login", "auth", "failure", "Invalid credentials")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    db_user.last_login = datetime.utcnow()
    db.commit()
    token = create_access_token({"sub": db_user.email, "role": db_user.role})
    set_auth_cookie(response, token)
    _write_audit_log(db, db_user.id, db_user.email, db_user.role, "login", "auth", "success")
    return {
        "role": db_user.role,
        "user_id": db_user.id,
        "full_name": db_user.full_name,
        "ward": db_user.ward,
        "district": db_user.district,
        "department": db_user.department,
    }

@auth_router.post("/logout")
async def logout(response: Response):
    """Logout: clear the httpOnly auth cookie."""
    clear_auth_cookie(response)
    return {"message": "Logged out successfully"}

@auth_router.get("/me", response_model=UserResponse)
async def get_me(db_user: User = Depends(get_current_user)):
    """Get current user profile from token."""
    return UserResponse(
        user_id=db_user.id,
        full_name=db_user.full_name,
        email=db_user.email,
        role=db_user.role,
        ward=db_user.ward,
        district=db_user.district,
        department=db_user.department,
        notify_status_updates=db_user.notify_status_updates,
        skills=db_user.skills,
        availability=db_user.availability,
        current_shift=db_user.current_shift,
        email_verified=db_user.email_verified,
    )


@auth_router.patch("/profile/notifications")
async def update_notification_prefs(body: NotificationPrefsRequest, db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update notification preferences for the current user."""
    db_user.notify_status_updates = body.notify_status_updates
    db.commit()
    db.refresh(db_user)
    return {"notify_status_updates": db_user.notify_status_updates}


@auth_router.put("/profile", response_model=UserResponse)
async def update_profile(data: ProfileUpdate, db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update current user profile."""
    from auth_service import hash_password
    if data.full_name is not None: db_user.full_name = data.full_name
    if data.email is not None: db_user.email = data.email
    if data.phone is not None: db_user.phone = data.phone
    if data.district is not None: db_user.district = data.district
    if data.ward is not None: db_user.ward = data.ward
    if data.password: db_user.password_hash = hash_password(data.password)
    # FEATURE 15: shift schedule
    if data.current_shift is not None: db_user.current_shift = data.current_shift
    db.commit()
    db.refresh(db_user)
    return UserResponse(
        user_id=db_user.id,
        full_name=db_user.full_name,
        email=db_user.email,
        role=db_user.role,
        ward=db_user.ward,
        district=db_user.district,
        department=db_user.department,
        notify_status_updates=db_user.notify_status_updates,
        skills=db_user.skills,
        availability=db_user.availability,
        current_shift=db_user.current_shift,
        email_verified=db_user.email_verified,
    )

# === WebSocket endpoint for real-time dashboard updates ===

ws_router = APIRouter(tags=["WebSocket"])


@ws_router.websocket("/ws/dashboard")
async def dashboard_ws(websocket: WebSocket, token: str = Query(...)):
    """Real-time dashboard updates via WebSocket.

    Accepts a short-lived JWT (10 min expiry, scope='websocket') obtained
    from GET /auth/ws-token.  On any complaint submission or incident
    status change the server broadcasts a typed event so connected
    clients update instantly instead of waiting for the 30s poll cycle.
    """
    payload = verify_token(token)
    if not payload or payload.get("scope") != "websocket":
        await websocket.close(code=4001)
        return
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('"pong"')
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket)


# === Short-lived token for WebSocket auth ===

@auth_router.get("/ws-token")
async def get_ws_token(db_user: User = Depends(get_current_user)):
    """Issue a short-lived JWT (10 min) for WebSocket authentication.

    The returned token is consumed as ?token=... in the WebSocket
    connection URL.  A separate expiry from the main session cookie
    limits exposure if the token appears in server access logs.
    """
    ws_token = create_ws_token({"sub": db_user.email, "role": db_user.role})
    return {"token": ws_token, "expires_in_minutes": 10}


admin_router = APIRouter(prefix="/admin", tags=["Admin"])

def get_executive_user(db_user: User = Depends(get_current_user)):
    """Verify user is Executive role."""
    if db_user.role != "Executive":
        raise HTTPException(status_code=403, detail="Executive access required")
    return db_user

@admin_router.get("/officers")
async def get_officers(db_user: User = Depends(get_executive_user), db: Session = Depends(get_db)):
    """Get all officers."""
    officers = db.query(User).filter(User.role == "Officer").all()
    return [{"id": o.id, "full_name": o.full_name, "email": o.email, "district": o.district, "department": o.department, "zone": o.zone, "created_at": o.created_at.isoformat() if o.created_at else None, "status": o.status, "last_login": o.last_login.isoformat() if o.last_login else None, "current_shift": o.current_shift} for o in officers]

@admin_router.get("/zone-commanders")
async def get_zone_commanders(db_user: User = Depends(get_executive_user), db: Session = Depends(get_db)):
    """Get all Zone Commanders."""
    zcs = db.query(User).filter(User.role == "Zone Commander").all()
    return [{"id": z.id, "full_name": z.full_name, "email": z.email, "district": z.district, "zone": z.zone, "department": z.department, "created_at": z.created_at.isoformat() if z.created_at else None, "status": z.status} for z in zcs]

@admin_router.post("/officers")
async def create_officer(body: OfficerCreate, db_user: User = Depends(get_executive_user), db: Session = Depends(get_db)):
    """Create a new officer. Only @gov.in emails allowed."""
    if not body.email.endswith("@gov.in"):
        raise HTTPException(status_code=400, detail="Government accounts must use @gov.in email domain")
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    officer_id = f"TN-{body.district or 'UNK'}-{body.department or 'UNK'}-{str(len(db.query(User).filter(User.role == 'Officer').all()) + 1).zfill(3)}"
    new_officer = User(
        id=officer_id,
        full_name=body.full_name,
        email=body.email,
        password_hash=hash_password(body.password),
        district=body.district,
        department=body.department,
        role="Officer",
        status="active"
    )
    db.add(new_officer)
    db.commit()
    _write_audit_log(db, db_user.id, db_user.email, db_user.role, "officer_create", officer_id, "success", f"full_name={body.full_name} email={body.email} district={body.district}")
    return {"message": "Officer created", "officer_id": officer_id}

@admin_router.post("/zone-commanders")
async def create_zone_commander(body: OfficerCreate, db_user: User = Depends(get_executive_user), db: Session = Depends(get_db)):
    """Create a new Zone Commander (Executive only)."""
    if not body.email.endswith("@gov.in"):
        raise HTTPException(status_code=400, detail="Government accounts must use @gov.in email domain")
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    new_zc = User(
        id=str(uuid.uuid4()),
        full_name=body.full_name,
        email=body.email,
        password_hash=hash_password(body.password),
        district=body.district,
        department=body.department or "Zone Command",
        role="Zone Commander",
        zone=body.zone,
        status="active"
    )
    db.add(new_zc)
    db.commit()
    _write_audit_log(db, db_user.id, db_user.email, db_user.role, "zone_commander_create", new_zc.id, "success", f"full_name={body.full_name} zone={body.zone}")
    return {"message": "Zone Commander created", "user_id": new_zc.id}

@admin_router.patch("/officers/{officer_id}/disable")
async def disable_officer(officer_id: str, db_user: User = Depends(get_executive_user), db: Session = Depends(get_db)):
    """Disable an officer."""
    officer = db.query(User).filter(User.id == officer_id).first()
    if not officer:
        raise HTTPException(status_code=404, detail="Officer not found")
    officer.status = "disabled"
    db.commit()
    _write_audit_log(db, db_user.id, db_user.email, db_user.role, "officer_disable", officer_id, "success")
    return {"message": "Officer disabled"}

@admin_router.patch("/officers/{officer_id}/enable")
async def enable_officer(officer_id: str, db_user: User = Depends(get_executive_user), db: Session = Depends(get_db)):
    """Enable an officer."""
    officer = db.query(User).filter(User.id == officer_id).first()
    if not officer:
        raise HTTPException(status_code=404, detail="Officer not found")
    officer.status = "active"
    db.commit()
    _write_audit_log(db, db_user.id, db_user.email, db_user.role, "officer_enable", officer_id, "success")
    return {"message": "Officer enabled"}

@admin_router.patch("/officers/{officer_id}")
async def update_officer(officer_id: str, body: OfficerUpdate, db_user: User = Depends(get_executive_user), db: Session = Depends(get_db)):
    """Update officer details (department, district, full_name)."""
    officer = db.query(User).filter(User.id == officer_id).first()
    if not officer:
        raise HTTPException(status_code=404, detail="Officer not found")
    if officer.role != "Officer":
        raise HTTPException(status_code=400, detail="User is not an Officer")
    if body.department is not None:
        officer.department = body.department
    if body.district is not None:
        officer.district = body.district
    if body.full_name is not None:
        officer.full_name = body.full_name
    db.commit()
    _write_audit_log(db, db_user.id, db_user.email, db_user.role, "officer_update", officer_id, "success",
                     f"department={officer.department} district={officer.district}")
    return {"message": "Officer updated", "department": officer.department, "district": officer.district, "full_name": officer.full_name}

@admin_router.get("/zone-age-distribution")
def get_zone_age_distribution(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in ('Executive', 'Admin'):
        raise HTTPException(status_code=403, detail="Executive only")
    incidents = db.query(Incident.ward, Incident.days_open).filter(Incident.days_open.isnot(None)).all()
    zones = {}
    for ward, days in incidents:
        zone = ZONE_BY_WARD.get(ward, 'Unknown')
        if zone not in zones: zones[zone] = {"0-7d": 0, "7-30d": 0, "30-90d": 0, "90d+": 0}
        if days <= 7: zones[zone]["0-7d"] += 1
        elif days <= 30: zones[zone]["7-30d"] += 1
        elif days <= 90: zones[zone]["30-90d"] += 1
        else: zones[zone]["90d+"] += 1
    return [{"zone": z, **buckets} for z, buckets in zones.items()]

@admin_router.get("/departments")
async def get_departments(db_user: User = Depends(get_executive_user), db: Session = Depends(get_db)):
    """Get department metrics."""
    _write_audit_log(db, db_user.id, db_user.email, db_user.role, "departments_view", "departments", "success")
    depts = db.query(DepartmentMetrics).all()

    # FEATURE 4: department_metrics — found used, populated
    if not depts:
        from types import SimpleNamespace
        cat_to_dept = {}
        for cat, slug in CATEGORY_DEPT_MAP.items():
            cat_to_dept[cat] = SLUG_TO_DISPLAY.get(slug, slug)
        for slug in DEPARTMENT_SLUGS:
            dept_name = SLUG_TO_DISPLAY.get(slug, slug)
            cats_for_dept = [c for c, d in cat_to_dept.items() if d == dept_name]
            if not cats_for_dept:
                continue
            open_cnt = db.query(func.count(Incident.id)).filter(
                Incident.category.in_(cats_for_dept),
                Incident.status.in_(["open", "in_progress", "escalated"])
            ).scalar() or 0
            critical_cnt = db.query(func.count(Incident.id)).filter(
                Incident.category.in_(cats_for_dept),
                Incident.status.in_(["open", "in_progress", "escalated"]),
                Incident.priority_score >= 75
            ).scalar() or 0
            officer_cnt = db.query(func.count(User.id)).filter(
                User.role == "Officer",
                User.department == dept_name
            ).scalar() or 0
            avg_res = db.query(func.avg(Incident.days_open)).filter(
                Incident.status.in_(["resolved", "closed"]),
                Incident.category.in_(cats_for_dept)
            ).scalar() or 0.0
            total_inc = db.query(func.count(Incident.id)).filter(
                Incident.category.in_(cats_for_dept)
            ).scalar() or 1
            resolved_inc = db.query(func.count(Incident.id)).filter(
                Incident.status.in_(["resolved", "closed"]),
                Incident.category.in_(cats_for_dept)
            ).scalar() or 0
            comp_pct = round((resolved_inc / total_inc) * 100, 1) if total_inc > 0 else 0.0
            workload = round((open_cnt / max(officer_cnt, 1)) * 10, 1)
            depts.append(SimpleNamespace(
                department=dept_name,
                open_incidents=open_cnt,
                critical_incidents=critical_cnt,
                assigned_officers=officer_cnt,
                avg_resolution_time=round(float(avg_res), 1),
                completion_percentage=comp_pct,
                workload_indicator=min(workload, 100),
            ))

    avg_ratings = db.query(
        Complaint.predicted_category,
        func.avg(Complaint.citizen_rating).label("avg_rating"),
        func.count(Complaint.id).label("rating_count"),
    ).filter(
        Complaint.citizen_rating.isnot(None),
        Complaint.incident_id.isnot(None),
    ).group_by(Complaint.predicted_category).all()

    rating_by_dept = {}
    for cat, avg, cnt in avg_ratings:
        dept = get_department(cat or "")
        if dept:
            rating_by_dept[dept] = {"avg_citizen_rating": round(float(avg), 2), "rating_count": cnt}

    aging_counts = db.query(
        Incident.category,
        func.count(Incident.id).label("cnt"),
    ).filter(
        Incident.days_open >= 30,
        Incident.status.in_(["open", "in_progress", "escalated"]),
    ).group_by(Incident.category).all()

    aging_by_dept = {}
    for cat, cnt in aging_counts:
        dept = get_department(cat or "")
        if dept:
            aging_by_dept[dept] = aging_by_dept.get(dept, 0) + cnt

    result = []
    for d in depts:
        entry = {
            "department": d.department,
            "open_incidents": d.open_incidents,
            "critical_incidents": d.critical_incidents,
            "assigned_officers": d.assigned_officers,
            "avg_resolution_time": d.avg_resolution_time,
            "completion_percentage": d.completion_percentage,
            "workload_indicator": d.workload_indicator,
        }
        rating_data = rating_by_dept.get(d.department)
        if rating_data:
            entry["avg_citizen_rating"] = rating_data["avg_citizen_rating"]
            entry["rating_count"] = rating_data["rating_count"]
        else:
            entry["avg_citizen_rating"] = None
            entry["rating_count"] = 0
        entry["aging_count"] = aging_by_dept.get(d.department, 0)
        result.append(entry)

    return result

@admin_router.get("/complaint-quality")
async def get_complaint_quality(db_user: User = Depends(get_executive_user), db: Session = Depends(get_db)):
    """Get complaint description length distribution and avg resolution days per bucket."""
    rows = db.query(
        Complaint.description,
        Incident.days_open,
    ).outerjoin(Incident, Complaint.incident_id == Incident.id).filter(
        Complaint.description.isnot(None),
    ).all()

    buckets = {"<50": {"count": 0, "total_days": 0}, "50-150": {"count": 0, "total_days": 0},
               "150-300": {"count": 0, "total_days": 0}, "300+": {"count": 0, "total_days": 0}}

    for desc, days_open in rows:
        length = len(desc)
        if length < 50:
            key = "<50"
        elif length <= 150:
            key = "50-150"
        elif length <= 300:
            key = "150-300"
        else:
            key = "300+"
        buckets[key]["count"] += 1
        if days_open is not None:
            buckets[key]["total_days"] += days_open

    distribution = []
    for bucket, data in buckets.items():
        avg_days = round(data["total_days"] / data["count"], 1) if data["count"] > 0 else 0
        distribution.append({
            "bucket": bucket,
            "count": data["count"],
            "avg_resolution_days": avg_days,
        })

    return {"distribution": distribution}


@admin_router.get("/officer-performance")
async def get_officer_performance(db_user: User = Depends(get_executive_user), db: Session = Depends(get_db)):
    """Rank officers by avg resolution time (fastest first)."""
    from collections import defaultdict
    from officer_routing import route_complaint

    rows = (
        db.query(
            Complaint.ward,
            Complaint.predicted_category,
            Incident.days_open,
            Incident.status,
            Incident.resolution_quality_score,
        )
        .join(Incident, Complaint.incident_id == Incident.id)
        .filter(
            Incident.status.in_(["resolved", "closed"]),
            Incident.days_open.isnot(None),
            Complaint.predicted_category.isnot(None),
        )
        .all()
    )

    officer_stats: dict[str, dict] = {}
    for ward, category, days_open, status, quality_score in rows:
        officer = route_complaint(ward or "", category or "")
        name = officer.get("name")
        if not name:
            continue
        dept = get_department(category or "")
        if name not in officer_stats:
            officer_stats[name] = {
                "officer_name": name,
                "department": dept,
                "total_days": 0,
                "resolved_count": 0,
                "quality_scores": [],
            }
        officer_stats[name]["total_days"] += (days_open or 0)
        officer_stats[name]["resolved_count"] += 1
        if quality_score is not None:
            officer_stats[name]["quality_scores"].append(quality_score)

    escalated_rows = (
        db.query(Complaint.ward, Complaint.predicted_category)
        .join(Incident, Complaint.incident_id == Incident.id)
        .filter(Incident.escalated == True)
        .all()
    )
    escalation_counts: dict[str, int] = {}
    for ward, category in escalated_rows:
        officer = route_complaint(ward or "", category or "")
        name = officer.get("name")
        if name:
            escalation_counts[name] = escalation_counts.get(name, 0) + 1

    # Get skills for officers
    officers_db = db.query(User).filter(User.role == "Officer").all()
    officer_skills: dict[str, str] = {}
    for o in officers_db:
        officer_skills[o.full_name] = o.skills

    result = []
    for name, stats in officer_stats.items():
        count = stats["resolved_count"]
        esc_count = escalation_counts.get(name, 0)
        qs = stats["quality_scores"]
        avg_qs = round(sum(qs) / len(qs), 1) if qs else None
        result.append({
            "officer_name": stats["officer_name"],
            "department": stats["department"],
            "avg_days_to_resolve": round(stats["total_days"] / count, 1) if count > 0 else 0,
            "total_resolved": count,
            "escalation_count": esc_count,
            "esc_rate": round(esc_count / count * 100, 1) if count > 0 else 0,
            "skills": officer_skills.get(name),
            "avg_quality_score": avg_qs,
        })

    result.sort(key=lambda r: (r["avg_days_to_resolve"] if r["total_resolved"] > 0 else float("inf"), -r["total_resolved"]))
    return result


@admin_router.get("/departments/list")
async def get_department_list(db_user: User = Depends(get_executive_user)):
    """Get the authoritative list of all departments with slugs and i18n keys."""
    return [
        {
            "slug": slug,
            "name": SLUG_TO_DISPLAY[slug],
            "i18nKey": get_i18n_key(slug),
        }
        for slug in DEPARTMENT_SLUGS
    ]

@admin_router.get("/system-health")
async def get_system_health(db_user: User = Depends(get_executive_user), db: Session = Depends(get_db)):
    """Get system health status."""
    _write_audit_log(db, db_user.id, db_user.email, db_user.role, "system_health_view", "system", "success")
    return {"backend": "healthy", "database": "healthy", "ai_engine": "healthy", "jwt_auth": "healthy", "classification_model": "loaded", "prediction_engine": "loaded", "duplicate_detection": "loaded", "knowledge_engine": "loaded", "decision_engine": "loaded", "db_size": db.query(User).count() + db.query(Complaint).count(), "users": db.query(User).count(), "complaints": db.query(Complaint).count(), "incidents": db.query(Incident).count()}

@admin_router.get("/audit-logs")
async def get_audit_logs(db_user: User = Depends(get_executive_user), db: Session = Depends(get_db)):
    """Get audit logs."""
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100).all()
    return [{"id": l.id, "timestamp": l.timestamp.isoformat() if l.timestamp else None, "user": l.user_email, "role": l.role, "action": l.action, "target": l.target, "status": l.status} for l in logs]

prediction_router = APIRouter(prefix="/predictions", tags=["Predictions"])

@prediction_router.get("/summary", response_model=PredictionSummaryResponse)
async def get_predictions_summary(db: Session = Depends(get_db)):
    """Get AI predictions summary using live complaint and incident data."""
    # FEATURE 13: 60s Redis cache
    pool = get_pool()
    cache_key = "cache:/predictions/summary"
    if pool:
        cached = await pool.get(cache_key)
        if cached:
            return json.loads(cached)
    try:
        engine = PredictiveEngine()
        history_counts = []
        for i in range(5):
            cutoff = datetime.utcnow() - timedelta(days=5 - i)
            next_cutoff = datetime.utcnow() - timedelta(days=4 - i)
            count = db.query(Complaint).filter(Complaint.created_at >= cutoff, Complaint.created_at < next_cutoff).count()
            history_counts.append(count)

        loop = asyncio.get_event_loop()

        def _run_engine():
            forecast = engine.forecast_complaints('week', history=history_counts)
            total_incidents = db.query(Incident).count()
            critical_count = db.query(Incident).filter(Incident.priority_label == 'Critical').count()
            high_count = db.query(Incident).filter(Incident.priority_label == 'High').count()
            avg_days_open = db.query(func.avg(Incident.days_open)).scalar() or 0.0
            recent_incidents = db.query(Incident).order_by(Incident.created_at.desc()).limit(5).all()
            escalation_risks = []
            for inc in recent_incidents:
                esc = engine.predict_escalation(inc)
                escalation_risks.append({
                    "incident_id": inc.id,
                    "priority_label": inc.priority_label,
                    "escalation_probability": esc.get("probability", 0.0),
                    "risk_level": esc.get("risk_level", "LOW")
                })
            active_alerts = engine.generate_alerts(db)
            return PredictionSummaryResponse(
                timeframe=forecast.get("timeframe", "week"),
                predicted_volume=forecast.get("predicted_volume", 0.0),
                confidence=forecast.get("confidence", 0.0),
                model=forecast.get("model", "unknown"),
                total_incidents=total_incidents,
                critical_count=critical_count,
                high_priority_count=high_count,
                avg_days_open=round(float(avg_days_open), 1),
                recent_escalation_risks=escalation_risks,
                active_alerts=active_alerts
            )

        response = await asyncio.wait_for(
            loop.run_in_executor(None, _run_engine),
            timeout=10.0
        )
        if pool:
            await pool.set(cache_key, json.dumps(response.dict() if hasattr(response, 'dict') else response), ex=60)
        return response
    except asyncio.TimeoutError:
        logger.warning("/predictions/summary timed out after 10s")  # FEATURE 3: 10s timeout with fallback
        return PredictionSummaryResponse(
            predicted_volume=0, confidence=0, timeout=True,
            recent_escalation_risks=[], active_alerts=[]
        )
    except Exception:
        logger.exception("/predictions/summary failed")
        return PredictionSummaryResponse(
            timeframe="week",
            predicted_volume=0.0,
            confidence=0.0,
            model="error",
            total_incidents=0,
            critical_count=0,
            high_priority_count=0,
            avg_days_open=0.0,
            recent_escalation_risks=[],
            active_alerts=[]
        )


knowledge_router = APIRouter(prefix="/knowledge", tags=["Knowledge"])

@knowledge_router.get("/summary", response_model=KnowledgeSummaryResponse)
async def get_knowledge_summary(db: Session = Depends(get_db)):
    """Get AI knowledge summary using live ward and incident data."""
    try:
        engine = GovernanceKnowledgeEngine()
        risk_index = engine.get_risk_index()
        policy_recs = engine.get_policy_recommendations()

        worst_ward = db.query(Incident.ward, func.count(Incident.id)).group_by(Incident.ward).order_by(func.count(Incident.id).desc()).first()
        worst_ward_name = worst_ward[0] if worst_ward else None

        root_causes = []
        cascade_chains = []
        if worst_ward_name:
            worst_inc = db.query(Incident).filter(Incident.ward == worst_ward_name).order_by(Incident.created_at.desc()).first()
            if worst_inc:
                root_cause_result = engine.get_root_cause(worst_inc.id)
                root_causes = root_cause_result.get("top_root_causes", [])
                cascade_chains = engine.analyze_cascade_impact(worst_inc.id)

        return KnowledgeSummaryResponse(
            district_risk_index=risk_index.get("district_risk_index"),
            infrastructure_risk_index=risk_index.get("infrastructure_risk_index"),
            policy_recommendations=policy_recs,
            worst_performing_ward=worst_ward_name,
            root_causes=root_causes,
            cascade_chains=cascade_chains
        )
    except Exception:
        logger.exception("/knowledge/summary failed")
        return KnowledgeSummaryResponse(
            district_risk_index=None,
            infrastructure_risk_index=None,
            policy_recommendations=[],
            worst_performing_ward=None,
            root_causes=[],
            cascade_chains=[]
        )


decision_router = APIRouter(prefix="/decision-support", tags=["Decision Support"])
@decision_router.get("/summary", response_model=DecisionSupportSummaryResponse)
async def get_decision_support_summary(db: Session = Depends(get_db)):
    """Get decision support summary using live district rankings and critical incident data."""
    try:
        engine = DecisionSupportEngine()

        districts = engine.rank_districts()
        wards = engine.rank_wards()

        top_critical = db.query(Incident).filter(Incident.priority_label == 'Critical').order_by(Incident.created_at.desc()).first()
        recommendation = None
        if top_critical:
            rec = engine.get_recommendations({
                "id": top_critical.id,
                "category": top_critical.category,
                "ward": top_critical.ward
            })
            recommendation = {
                "incident_id": top_critical.id,
                "incident_number": top_critical.incident_number,
                "recommended_actions": rec.get("recommended_actions", []),
                "resource_plan": rec.get("resource_plan", {}),
                "estimated_cost": rec.get("estimated_cost"),
                "completion_hours": rec.get("completion_hours"),
                "confidence": rec.get("confidence", 0.0),
                "reason": rec.get("reason", "")
            }

        return DecisionSupportSummaryResponse(
            district_rankings=districts,
            ward_rankings=wards,
            top_critical_recommendation=recommendation,
            executive_report=engine.generate_report()
        )
    except Exception:
        logger.exception("/decision-support/summary failed")
        return DecisionSupportSummaryResponse(
            district_rankings=[],
            ward_rankings={},
            top_critical_recommendation=None,
            executive_report=""
        )


copilot_router = APIRouter(prefix="/copilot", tags=["Copilot"])

@copilot_router.post("/chat", response_model=CopilotChatResponse)
async def copilot_chat(body: CopilotChatRequest, request: Request, _: None = Depends(check_copilot_rate_limit)):  # FEATURE 2: newly rate-limited
    """Process copilot chat query."""
    engine = CopilotEngine()
    result = engine.chat(body.user_id, body.message)
    return CopilotChatResponse(
        response=result.get("response", ""),
        confidence=result.get("confidence", 0.0),
        data_sources=result.get("data_sources", []),
        reasoning=result.get("reasoning", "")
    )


# === Debug endpoints (not for production use) ===

from fastapi import APIRouter, Depends
from sqlalchemy import func

debug_router = APIRouter(prefix="/debug", tags=["Debug"])


@debug_router.post("/migrate")
async def debug_migrate(db: Session = Depends(get_db), db_user: User = Depends(get_current_user)):
    """One-time migration: add appeal columns to incidents table.
    Required Executive auth.
    """
    if db_user.role not in ("Executive", "Collector"):
        raise HTTPException(status_code=403, detail="Executive or Collector access required")
    try:
        from sqlalchemy import text
        db.execute(text("ALTER TABLE incidents ADD COLUMN IF NOT EXISTS appealed BOOLEAN NOT NULL DEFAULT FALSE"))
        db.execute(text("ALTER TABLE incidents ADD COLUMN IF NOT EXISTS appeal_reason TEXT"))
        db.execute(text("ALTER TABLE incidents ADD COLUMN IF NOT EXISTS appealed_at TIMESTAMP"))

        # Backfill null departments for existing officers based on name/email heuristics
        dept_map = {
            "Roads": "CCMC Engineering Wing",
            "Sanitation": "CCMC Health Department",
            "Water": "TWAD Board - Coimbatore Division",
            "TANGEDCO": "TANGEDCO - Coimbatore Region",
            "Engineering": "CCMC Engineering Wing",
            "Health": "CCMC Health Department",
        }
        null_dept_officers = db.query(User).filter(User.role == "Officer", User.department.is_(None)).all()
        backfilled = 0
        for off in null_dept_officers:
            assigned = False
            for keyword, dept in dept_map.items():
                if keyword.lower() in (off.full_name or "").lower() or keyword.lower() in (off.email or "").lower():
                    off.department = dept
                    assigned = True
                    backfilled += 1
                    break
            if not assigned:
                off.department = "CCMC Engineering Wing"
                backfilled += 1
        db.commit()
        return {"message": f"Migration complete — appeal columns added, {backfilled} officers backfilled with department"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@debug_router.post("/reseed")
async def debug_reseed(db: Session = Depends(get_db), db_user: User = Depends(get_current_user)):
    """Drop and re-seed complaints/incidents/users with Coimbatore CCMC data.

    Requires Executive authentication (collector@giips.gov.in).
    Seeds real CCMC ward structure with 10K synthetic civic complaints
    across all 100 wards and 5 zones.
    """
    import traceback
    if db_user.role not in ("Executive", "Collector"):
        raise HTTPException(status_code=403, detail="Executive or Collector access required")
    try:
        from database import seed_demo_users, seed_synthetic_data
        from sqlalchemy import text
        for tbl in ["priority_history", "notifications", "department_metrics", "complaints", "incidents"]:
            try:
                db.execute(text(f"DELETE FROM {tbl}"))
            except Exception:
                pass
        db.commit()
        seed_demo_users()
        seed_synthetic_data(num_complaints=10000, duplicate_rate=0.15)
        return {"message": "Database re-seeded with Coimbatore (CCMC) data"}
    except Exception as e:
        db.rollback()
        detail = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=detail)


@debug_router.post("/topup")
async def debug_topup(db: Session = Depends(get_db), db_user: User = Depends(get_current_user)):
    """Top up Coimbatore CCMC wards to ensure each has at least 50 complaints.
    Idempotent — safe to call multiple times.
    """
    if db_user.role not in ("Executive", "Collector"):
        raise HTTPException(status_code=403, detail="Executive or Collector access required")
    try:
        from database import topup_wards
        topup_wards(min_per_ward=50)
        return {"message": "Coimbatore wards topped up successfully"}
    except Exception as e:
        import traceback
        detail = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=detail)


@debug_router.get("/wards")
async def debug_wards(db: Session = Depends(get_db)):
    """Show ward distribution and incident linkage counts."""
    ward_counts = db.query(Complaint.ward, func.count(Complaint.id)).group_by(Complaint.ward).order_by(Complaint.ward).all()
    total_complaints = db.query(func.count(Complaint.id)).scalar()
    unlinked = db.query(func.count(Complaint.id)).filter(Complaint.incident_id.is_(None)).scalar()
    linked = total_complaints - unlinked
    incident_count = db.query(func.count(Incident.id)).scalar()
    return {
        "total_complaints": total_complaints,
        "linked_to_incident": linked,
        "unlinked": unlinked,
        "total_incidents": incident_count,
        "ward_distribution": {w: c for w, c in ward_counts},
    }


@debug_router.get("/sla-diagnostics")
async def debug_sla_diagnostics(db: Session = Depends(get_db)):
    """Diagnostic: check SLA escalation state in the database.
    
    Returns three counts to determine whether sla logic has a bug
    or the data state explains zero escalations.
    """
    now = datetime.utcnow()
    ward_cutoff = now - timedelta(hours=48)

    total_incidents = db.query(func.count(Incident.id)).scalar()

    escalated_true = db.query(func.count(Incident.id)).filter(
        Incident.escalated == True
    ).scalar()

    status_changed_at_null = db.query(func.count(Incident.id)).filter(
        Incident.status_changed_at.is_(None)
    ).scalar()

    eligible_for_ward = db.query(func.count(Incident.id)).filter(
        Incident.status.in_(["open", "in-progress"]),
        Incident.escalated == False,
        Incident.status_changed_at.isnot(None),
        Incident.status_changed_at <= ward_cutoff,
    ).scalar()

    open_in_progress_total = db.query(func.count(Incident.id)).filter(
        Incident.status.in_(["open", "in-progress"]),
    ).scalar()

    return {
        "total_incidents": total_incidents,
        "escalated_true": escalated_true,
        "status_changed_at_null": status_changed_at_null,
        "eligible_for_ward_escalation": eligible_for_ward,
        "open_or_in_progress_total": open_in_progress_total,
        "ward_cutoff_utc": ward_cutoff.isoformat(),
        "now_utc": now.isoformat(),
    }


@incident_router.get("/{incident_id}/resolution-photo")
async def get_resolution_photo(incident_id: str, db: Session = Depends(get_db)):
    """Get the resolution photo for an incident (public, no auth)."""
    from fastapi.responses import FileResponse
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident or not incident.resolution_photo_path:
        raise HTTPException(status_code=404, detail="Resolution photo not found")
    if not os.path.exists(incident.resolution_photo_path):
        raise HTTPException(status_code=404, detail="Resolution photo file not found")
    return FileResponse(incident.resolution_photo_path)


@admin_router.get("/resolution-histogram")
def get_resolution_histogram(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in ('Executive', 'Admin'):
        raise HTTPException(status_code=403, detail="Executive only")
    incidents = db.query(Incident.days_open).filter(Incident.status.in_(['resolved','closed']), Incident.days_open.isnot(None)).all()
    buckets = {"0-5": 0, "5-15": 0, "15-30": 0, "30+": 0}
    for (days,) in incidents:
        if days <= 5: buckets["0-5"] += 1
        elif days <= 15: buckets["5-15"] += 1
        elif days <= 30: buckets["15-30"] += 1
        else: buckets["30+"] += 1
    return [{"range": k, "count": v} for k, v in buckets.items()]


@admin_router.get("/active-users")
async def get_active_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in ('Executive', 'Admin'):
        raise HTTPException(status_code=403, detail="Executive only")
    return {"active_users": manager.active_count}


@admin_router.get("/department-sla-report")
async def get_department_sla_report(db_user: User = Depends(get_executive_user), db: Session = Depends(get_db)):
    """Get SLA report per department."""
    from collections import defaultdict
    incidents = db.query(Incident).filter(Incident.status.in_(["open", "in-progress"])).all()
    dept_data: dict = defaultdict(lambda: {"total_open": 0, "within_sla": 0, "breached_sla": 0, "breach_durations": []})
    for inc in incidents:
        dept = get_department(inc.category or "")
        if not dept:
            continue
        dept_data[dept]["total_open"] += 1
        days = inc.days_open or 0
        sla_limit = 2 if inc.ward and inc.ward != "" else 5
        if days <= sla_limit:
            dept_data[dept]["within_sla"] += 1
        else:
            dept_data[dept]["breached_sla"] += 1
            dept_data[dept]["breach_durations"].append(days)
    result = []
    for dept, data in dept_data.items():
        avg_breach = round(sum(data["breach_durations"]) / len(data["breach_durations"]), 2) if data["breach_durations"] else 0
        result.append({
            "department": dept,
            "total_open": data["total_open"],
            "within_sla": data["within_sla"],
            "breached_sla": data["breached_sla"],
            "avg_breach_duration_days": avg_breach,
        })
    return result


@admin_router.get("/department-heatmap")
def get_department_heatmap(department: str = Query(''), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in ('Executive', 'Admin'):
        raise HTTPException(status_code=403, detail="Executive only")
    query = db.query(
        func.strftime('%w', Complaint.created_at).label('dow'),
        func.strftime('%H', Complaint.created_at).label('hour'),
        func.count(Complaint.id).label('count')
    )
    if department:
        dept_slug = get_slug_for_department(department)
        query = query.filter(Complaint.department == dept_slug)
    results = query.group_by('dow', 'hour').order_by('dow', 'hour').all()
    heatmap = [[0]*24 for _ in range(7)]
    for r in results:
        d = int(r.dow) % 7
        h = int(r.hour) % 24
        heatmap[d][h] = r.count
    return {"days": ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"], "hours": list(range(24)), "data": heatmap}


@auth_router.patch("/profile/skills")
def update_skills(body: SkillsUpdateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in ('Officer', 'Executive'):
        raise HTTPException(status_code=403, detail="Only officers and executives can set skills")
    current_user.skills = json.dumps(body.skills)
    db.commit()
    return {"skills": body.skills}


@auth_router.patch("/profile/availability")
async def update_availability(body: AvailabilityUpdateRequest, db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Toggle officer availability (Officer only)."""
    if db_user.role != "Officer":
        raise HTTPException(status_code=403, detail="Only officers can update availability")
    if body.availability not in ("available", "on_leave"):
        raise HTTPException(status_code=400, detail="Availability must be 'available' or 'on_leave'")
    db_user.availability = body.availability
    db.commit()
    db.refresh(db_user)
    return {"id": db_user.id, "full_name": db_user.full_name, "availability": db_user.availability}


# === Feature 17: Zone Commander auth dependency ===

def get_zone_commander_or_executive(current_user: User = Depends(get_current_user)):
    """Allow Zone Commander or Executive access."""
    if current_user.role not in ("Zone Commander", "Executive"):
        raise HTTPException(status_code=403, detail="Zone Commander or Executive access required")
    return current_user


# === Zone Commander: filtered incident overview ===

@admin_router.get("/zone-incidents")
async def get_zone_incidents(db_user: User = Depends(get_zone_commander_or_executive), db: Session = Depends(get_db)):
    """Get incidents filtered by the zone commander's zone (or all for exec)."""
    from sqlalchemy import case as sql_case
    if db_user.role == "Zone Commander":
        if not db_user.zone:
            raise HTTPException(status_code=400, detail="Zone Commander has no zone assigned")
        zone_wards = [w.strip() for w in db_user.zone.split(",")]
        incidents = db.query(Incident).filter(Incident.ward.in_(zone_wards)).order_by(Incident.created_at.desc()).limit(50).all()
    else:
        incidents = db.query(Incident).order_by(Incident.created_at.desc()).limit(50).all()
    result = []
    for inc in incidents:
        cat = inc.category or "unknown"
        result.append({
            "id": inc.id, "incident_number": inc.incident_number, "category": cat,
            "department": get_department(cat),
            "ward": inc.ward, "cluster_size": inc.cluster_size, "priority_score": inc.priority_score,
            "priority_label": inc.priority_label, "status": inc.status, "summary": inc.summary,
            "days_open": inc.days_open,
            "affected_wards": json.loads(inc.affected_wards) if inc.affected_wards else [],
            "accepted_by": inc.accepted_by,
            "created_at": inc.created_at.isoformat() if inc.created_at else None,
        })
    return result


# === Feature 8: Multi-ward incident linking ===

class AffectedWardsRequest(BaseModel):
    affected_wards: List[str]

@incident_router.patch("/{incident_id}/affected-wards")
async def update_affected_wards(incident_id: str, body: AffectedWardsRequest, db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update affected wards for an incident (Officer auth required)."""
    if db_user.role not in ("Officer", "Executive", "Zone Commander"):
        raise HTTPException(status_code=403, detail="Only officers, executives, and zone commanders can update affected wards")
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    incident.affected_wards = json.dumps(body.affected_wards)
    db.commit()
    return {"affected_wards": body.affected_wards}


# === Feature 13: Incident bulk close (executive only) ===

class BulkCloseRequest(BaseModel):
    incident_ids: List[str]
    close_reason: str

@incident_router.post("/bulk-close")
async def bulk_close_incidents(body: BulkCloseRequest, db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Bulk close incidents (Executive auth required)."""
    if db_user.role != "Executive":
        raise HTTPException(status_code=403, detail="Executive only")
    incidents = db.query(Incident).filter(Incident.id.in_(body.incident_ids)).all()
    now = datetime.utcnow()
    success_count = 0
    for inc in incidents:
        inc.status = "closed"
        inc.status_changed_at = now
        inc.resolution_note = body.close_reason
        # FEATURE 15: auto-close follow-up complaints
        follow_up_complaints = db.query(Complaint).filter(
            Complaint.incident_id == inc.id,
            or_(
                Complaint.merge_reason.ilike("%follow_up%"),
                Complaint.tags.ilike("%follow-up%"),
            ),
        ).all()
        for fc in follow_up_complaints:
            fc_inc = db.query(Incident).filter(Incident.id == fc.incident_id).first()
            if fc_inc and fc_inc.status not in ("resolved", "closed"):
                fc_inc.status = "closed"
                fc_inc.status_changed_at = now
                fc_inc.resolution_note = "Auto-closed: parent incident closed"
                _write_audit_log(
                    db, db_user.id, db_user.email, db_user.role,
                    "auto_close_follow_up", fc_inc.id, "success",
                    f"Auto-closed follow-up complaint {fc.id} linked to closed incident {inc.incident_number}",
                )
        _write_audit_log(db, db_user.id, db_user.email, db_user.role, "bulk_close", inc.id, "success", f"Bulk closed: {body.close_reason[:200]}")
        success_count += 1
    db.commit()
    return {"success_count": success_count, "total": len(body.incident_ids)}


# === Feature 15: Officer incident acceptance ===

@incident_router.patch("/{incident_id}/accept")
async def accept_incident(incident_id: str, db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Accept an incident (Officer auth required). Sets accepted_by and accepted_at."""
    if db_user.role != "Officer":
        raise HTTPException(status_code=403, detail="Only officers can accept incidents")
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if incident.accepted_by:
        raise HTTPException(status_code=400, detail="Incident already accepted")
    incident.accepted_by = db_user.full_name
    incident.accepted_at = datetime.utcnow()
    db.commit()
    _write_audit_log(db, db_user.id, db_user.email, db_user.role, "incident_accept", incident.id, "success")
    return {"accepted_by": incident.accepted_by, "accepted_at": incident.accepted_at.isoformat() if incident.accepted_at else None}


@officer_router.get("/my-performance")
async def officer_self_performance(db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Officer performance self-view. Returns key metrics for the authenticated officer.
    # FEATURE 6: Officer performance self-view"""
    if db_user.role != "Officer":
        raise HTTPException(status_code=403, detail="Only officers can view their performance")
    officer_name = db_user.full_name
    department = db_user.department
    if not department:
        raise HTTPException(status_code=400, detail="Officer has no department assigned")

    now = datetime.utcnow()
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Resolved incidents accepted_by this officer
    resolved_incs = db.query(Incident).filter(
        Incident.accepted_by == officer_name,
        Incident.status.in_(["resolved", "closed"]),
    ).all()
    resolved_count = len(resolved_incs)
    total_days = sum(inc.days_open or 0 for inc in resolved_incs)
    avg_resolution_time = round(total_days / resolved_count, 1) if resolved_count > 0 else 0.0

    # Total resolved this month
    total_resolved_this_month = db.query(Incident).filter(
        Incident.accepted_by == officer_name,
        Incident.status_changed_at.isnot(None),
        Incident.status_changed_at >= first_of_month,
        Incident.status.in_(["resolved", "closed"]),
    ).count()

    # Citizen ratings received — avg from complaints linked to incidents accepted_by this officer
    rating_result = db.query(func.avg(Complaint.citizen_rating)).join(
        Incident, Complaint.incident_id == Incident.id
    ).filter(
        Incident.accepted_by == officer_name,
        Complaint.citizen_rating.isnot(None),
    ).scalar()
    citizen_ratings_received = round(float(rating_result), 2) if rating_result else 0.0

    # SLA compliance rate — percentage resolved within 7 days
    sla_ok = db.query(Incident).filter(
        Incident.accepted_by == officer_name,
        Incident.status.in_(["resolved", "closed"]),
        Incident.days_open.isnot(None),
        Incident.days_open <= 7,
    ).count()
    sla_total = db.query(Incident).filter(
        Incident.accepted_by == officer_name,
        Incident.status.in_(["resolved", "closed"]),
        Incident.days_open.isnot(None),
    ).count()
    sla_compliance_rate = round((sla_ok / sla_total) * 100, 1) if sla_total > 0 else 0.0

    # Department averages
    dept_resolved = db.query(Incident).filter(
        Incident.accepted_by == officer_name,
        Incident.status.in_(["resolved", "closed"]),
    ).subquery()
    dept_resolved_incs = db.query(Incident).filter(
        Incident.status.in_(["resolved", "closed"]),
    ).all()
    dept_all_resolved = [i for i in dept_resolved_incs]
    dept_days = sum(i.days_open or 0 for i in dept_all_resolved)
    dept_res_count = len(dept_all_resolved)
    department_avg_resolution = round(dept_days / dept_res_count, 1) if dept_res_count > 0 else 0.0

    dept_this_month = db.query(Incident).filter(
        Incident.status_changed_at.isnot(None),
        Incident.status_changed_at >= first_of_month,
        Incident.status.in_(["resolved", "closed"]),
    ).count()

    dept_rating_result = db.query(func.avg(Complaint.citizen_rating)).join(
        Incident, Complaint.incident_id == Incident.id
    ).filter(
        Complaint.citizen_rating.isnot(None),
    ).scalar()
    dept_avg_rating = round(float(dept_rating_result), 2) if dept_rating_result else 0.0

    dept_sla_ok = db.query(Incident).filter(
        Incident.status.in_(["resolved", "closed"]),
        Incident.days_open.isnot(None),
        Incident.days_open <= 7,
    ).count()
    dept_sla_total = db.query(Incident).filter(
        Incident.status.in_(["resolved", "closed"]),
        Incident.days_open.isnot(None),
    ).count()
    dept_sla_rate = round((dept_sla_ok / dept_sla_total) * 100, 1) if dept_sla_total > 0 else 0.0

    return {
        "officer_name": officer_name,
        "department": department,
        "avg_resolution_time": avg_resolution_time,
        "total_resolved_this_month": total_resolved_this_month,
        "citizen_ratings_received": citizen_ratings_received,
        "sla_compliance_rate": sla_compliance_rate,
        "department_avg": {
            "avg_resolution_time": department_avg_resolution,
            "total_resolved_this_month": dept_this_month,
            "citizen_ratings_received": dept_avg_rating,
            "sla_compliance_rate": dept_sla_rate,
        },
    }


class ReassignRequest(BaseModel):
    new_department: Optional[str] = None
    new_officer: Optional[str] = None
    reason: str

@incident_router.patch("/{incident_id}/reassign")
async def reassign_incident(incident_id: str, body: ReassignRequest, db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Reassign an incident to a different officer and/or department. Executive only.
    # FEATURE 7: Incident reassignment"""
    if db_user.role != "Executive":
        raise HTTPException(status_code=403, detail="Executive only")
    incident = db.query(Incident).options(joinedload(Incident.complaints)).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if not body.reason:
        raise HTTPException(status_code=400, detail="Reason is required for reassignment")

    old_officer = incident.accepted_by
    old_category = incident.category

    if body.new_officer:
        incident.accepted_by = body.new_officer
        incident.accepted_at = datetime.utcnow()

    if body.new_department:
        new_slug = get_slug_for_department(body.new_department)
        dept_cats = [cat for cat, slug in CATEGORY_DEPT_MAP.items() if slug == new_slug]
        if dept_cats:
            incident.category = dept_cats[0]

    _write_audit_log(
        db, db_user.id, db_user.email, db_user.role,
        "incident_reassign", incident.id, "success",
        f"Reassigned by {db_user.full_name}. Reason: {body.reason}. "
        f"Old officer: {old_officer or 'none'}, New officer: {body.new_officer or 'unchanged'}. "
        f"Old category: {old_category}, New category: {incident.category}"
    )

    # Notify old officer
    if old_officer:
        old_user = db.query(User).filter(User.full_name == old_officer).first()
        if old_user:
            _create_notification(
                db, old_user.id, "incident_reassigned",
                data={
                    "incident_id": incident.id,
                    "incident_number": incident.incident_number,
                    "message": f"Incident {incident.incident_number} has been reassigned away from you. Reason: {body.reason}",
                }
            )
    # Notify new officer
    if body.new_officer:
        new_user = db.query(User).filter(User.full_name == body.new_officer).first()
        if new_user:
            _create_notification(
                db, new_user.id, "incident_assigned",
                data={
                    "incident_id": incident.id,
                    "incident_number": incident.incident_number,
                    "message": f"Incident {incident.incident_number} has been assigned to you. Reason: {body.reason}",
                }
            )

    db.commit()
    return {
        "id": incident.id,
        "incident_number": incident.incident_number,
        "accepted_by": incident.accepted_by,
        "category": incident.category,
        "status": incident.status,
    }


# === Feature 9: Confidence distribution (executive) ===

@admin_router.get("/confidence-distribution")
async def get_confidence_distribution(db_user: User = Depends(get_executive_user), db: Session = Depends(get_db)):
    """Get confidence distribution buckets for all classified complaints."""
    rows = db.query(Complaint.confidence).filter(Complaint.confidence.isnot(None)).all()
    buckets = {"0-20%": 0, "20-40%": 0, "40-60%": 0, "60-80%": 0, "80-100%": 0}
    for (c,) in rows:
        pct = c * 100
        if pct < 20: buckets["0-20%"] += 1
        elif pct < 40: buckets["20-40%"] += 1
        elif pct < 60: buckets["40-60%"] += 1
        elif pct < 80: buckets["60-80%"] += 1
        else: buckets["80-100%"] += 1
    return [{"bucket": k, "count": v} for k, v in buckets.items()]


# === Feature 12: Department capacity planning (executive) ===

@admin_router.get("/department-capacity")
async def get_department_capacity(db_user: User = Depends(get_executive_user), db: Session = Depends(get_db)):
    """Get department capacity planning data."""
    from department_map import CATEGORY_DEPT_MAP, get_slug_for_department, SLUG_TO_DISPLAY
    dept_data = {}
    for cat, slug in CATEGORY_DEPT_MAP.items():
        dept = SLUG_TO_DISPLAY.get(slug, slug)
        if dept not in dept_data:
            dept_data[dept] = {"open_incidents": 0, "officers_available": 0, "total_daily_resolved": 0, "days_measured": 0}
        open_cnt = db.query(Incident).filter(
            Incident.category == cat,
            Incident.status.in_(["open", "in-progress"])
        ).count()
        dept_data[dept]["open_incidents"] += open_cnt
    for dept in dept_data:
        available = db.query(User).filter(
            User.role == "Officer",
            User.department == dept,
            User.availability == "available"
        ).count()
        dept_data[dept]["officers_available"] = available
        # avg daily resolution rate over last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        resolved_30d = db.query(Incident).filter(
            Incident.department == dept,
            Incident.status.in_(["resolved", "closed"]),
            Incident.status_changed_at >= thirty_days_ago,
        ).count()
        avg_daily = resolved_30d / 30.0 if resolved_30d > 0 else 0.5
        backlog_days = round(dept_data[dept]["open_incidents"] / max(avg_daily, 0.5), 1)
        dept_data[dept]["avg_daily_resolution_rate"] = round(avg_daily, 2)
        dept_data[dept]["estimated_days_to_clear_backlog"] = backlog_days
    result = []
    for dept_name, data in sorted(dept_data.items(), key=lambda x: -x[1]["open_incidents"]):
        entry = {"department": dept_name, **data}
        utilization = round((data["open_incidents"] / max(data["officers_available"], 1)) * 10, 1)  # scaled
        entry["utilization_score"] = min(utilization, 100)
        result.append(entry)
    return result


# === Feature 6: Citizen trust score ===

@complaint_router.get("/trust-score")
async def get_citizen_trust_score(db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Compute trust score for the current citizen user."""
    if db_user.role != "Citizen":
        raise HTTPException(status_code=403, detail="Only citizens can view trust score")
    complaints = db.query(Complaint).filter(Complaint.user_id == db_user.id).all()
    total = len(complaints)
    if total == 0:
        return {"trust_score": 0, "verify_score": 0, "genuine_score": 0, "rating_accuracy": 0}
    resolved_verified = 0
    not_withdrawn = 0
    rating_diff_sum = 0
    rating_count = 0
    for c in complaints:
        inc = db.query(Incident).filter(Incident.id == c.incident_id).first() if c.incident_id else None
        if inc and inc.status in ("resolved", "closed") and not inc.appealed:
            resolved_verified += 1
        if inc and inc.status != "withdrawn":
            not_withdrawn += 1
        if c.citizen_rating is not None and c.predicted_category:
            avg_for_cat = db.query(func.avg(Complaint.citizen_rating)).filter(
                Complaint.predicted_category == c.predicted_category,
                Complaint.citizen_rating.isnot(None)
            ).scalar() or 3.0
            rating_diff_sum += abs(c.citizen_rating - float(avg_for_cat))
            rating_count += 1
    verify_score = round((resolved_verified / total) * 100, 1)
    genuine_score = round((not_withdrawn / total) * 100, 1)
    rating_accuracy = round(max(0, 100 - (rating_diff_sum / max(rating_count, 1)) * 20), 1) if rating_count > 0 else 0
    trust_score = round((verify_score + genuine_score + rating_accuracy) / 3, 1)
    return {"trust_score": trust_score, "verify_score": verify_score, "genuine_score": genuine_score, "rating_accuracy": rating_accuracy}


# === Feature 19: Public transparency score ===

public_router = APIRouter(tags=["Public"])

@public_router.get("/public/transparency-score")
def get_transparency_score(db: Session = Depends(get_db)):
    """Compute a 0-100 transparency score from:
    - % incidents with resolution_notes (0-20)
    - % incidents with resolution_photos (0-20)
    - % citizen-verified (0-20)
    - avg citizen rating (0-20)
    - avg resolution time vs SLA of 120h (0-20)
    """
    total_incidents = db.query(Incident).count()
    if total_incidents == 0:
        return {"transparency_score": 0, "sub_scores": {}}
    with_notes = db.query(Incident).filter(Incident.resolution_note.isnot(None), Incident.resolution_note != "").count()
    with_photos = db.query(Incident).filter(Incident.resolution_photo_path.isnot(None)).count()
    citizen_verified = db.query(Incident).filter(
        Incident.status == "resolved",
        Incident.verification_code.is_(None)
    ).count()
    avg_rating = db.query(func.avg(Complaint.citizen_rating)).filter(Complaint.citizen_rating.isnot(None)).scalar() or 0
    avg_res_days = db.query(func.avg(Incident.days_open)).filter(
        Incident.status.in_(["resolved", "closed"]),
        Incident.days_open.isnot(None)
    ).scalar() or 0
    sla_hours = 120
    avg_res_hours = float(avg_res_days) * 24 if avg_res_days else 0
    note_score = min(20, round((with_notes / total_incidents) * 20, 1))
    photo_score = min(20, round((with_photos / total_incidents) * 20, 1))
    verified_score = min(20, round((citizen_verified / total_incidents) * 20, 1))
    rating_score = min(20, round((float(avg_rating) / 5) * 20, 1))
    sla_score = min(20, round(max(0, 1 - (avg_res_hours / sla_hours)) * 20, 1))
    total_score = round(note_score + photo_score + verified_score + rating_score + sla_score, 1)
    return {
        "transparency_score": total_score,
        "sub_scores": {
            "resolution_notes": {"score": note_score, "max": 20},
            "resolution_photos": {"score": photo_score, "max": 20},
            "citizen_verified": {"score": verified_score, "max": 20},
            "citizen_rating": {"score": rating_score, "max": 20},
            "sla_adherence": {"score": sla_score, "max": 20},
        },
        "total_incidents": total_incidents,
        "avg_resolution_hours": round(avg_res_hours, 1),
        "avg_citizen_rating": round(float(avg_rating), 2),
    }


# FEATURE 18: ward improvement tracking
@public_router.get("/public/ward-improvement")
def get_ward_improvement(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    thirty_days_ago = now - timedelta(days=30)
    ward_numbers = db.query(Complaint.ward).filter(Complaint.ward.isnot(None), Complaint.ward != "").distinct().all()
    results = []
    for (wn,) in ward_numbers:
        current_open = db.query(func.count(Incident.id)).join(Complaint, Complaint.incident_id == Incident.id).filter(
            Complaint.ward == wn,
            ~Incident.status.in_(["resolved", "closed", "withdrawn"]),
        ).scalar() or 0
        past_open = db.query(func.count(Incident.id)).join(Complaint, Complaint.incident_id == Incident.id).filter(
            Complaint.ward == wn,
            Complaint.created_at < thirty_days_ago,
            ~Incident.status.in_(["resolved", "closed", "withdrawn"]),
        ).scalar() or 0
        improvement = past_open - current_open
        results.append({"ward": wn, "current_open_count": current_open, "past_count": past_open, "improvement": improvement})
    results.sort(key=lambda r: r["improvement"], reverse=True)
    return {
        "top_5_improved": results[:5],
        "bottom_5_deteriorated": results[-5:] if len(results) >= 5 else results,
    }


# === Public Endpoints (no auth required) ===

STOPWORDS = {"the","is","in","at","of","a","and","to","for","it","on","that","this","with","was","are","be","has","have","had","not","but","or","from","by","an","as","we","they","i","you","he","she","its","their","there","been","all","no","so","if","do","will","would","can","could","should","may","also","very","just","about","than","too","any","more","some","these","those","into","over","after","before","between","under","above","below","up","down","out","off","per","each","other","which","what","who","whom","when","where","why","how"}

@public_router.get("/public/ward-leaderboard")
def get_ward_leaderboard(db: Session = Depends(get_db)):
    """Public ward performance leaderboard — no auth required.
    Groups complaints by ward, computes resolved count, resolution rate,
    avg citizen rating, and avg resolution days. Sorted by resolution_rate desc.
    """
    from sqlalchemy import case as sql_case
    rows = db.query(
        Complaint.ward,
        func.count(Complaint.id).label("total"),
        func.sum(sql_case((Incident.status.in_(["resolved", "closed"]), 1), else_=0)).label("resolved"),
        func.avg(Complaint.citizen_rating).label("avg_rating"),
        func.avg(Incident.days_open).label("avg_days"),
    ).outerjoin(Incident, Complaint.incident_id == Incident.id
    ).filter(
        Complaint.ward.isnot(None), Complaint.ward != "",
    ).group_by(Complaint.ward).all()

    result = []
    for ward, total, resolved, avg_rating, avg_days in rows:
        total = total or 0
        resolved = resolved or 0
        resolution_rate = round((resolved / total) * 100, 1) if total > 0 else 0.0
        result.append({
            "ward": ward,
            "total_complaints": total,
            "resolved": resolved,
            "resolution_rate": resolution_rate,
            "avg_citizen_rating": round(float(avg_rating), 2) if avg_rating else None,
            "avg_resolution_days": round(float(avg_days), 1) if avg_days else None,
        })

    result.sort(key=lambda r: r["resolution_rate"], reverse=True)
    return result

@public_router.get("/public/satisfaction-trend")
def get_satisfaction_trend(db: Session = Depends(get_db)):
    eight_weeks_ago = datetime.utcnow() - timedelta(weeks=8)
    results = db.query(
        func.strftime('%Y-%W', Complaint.created_at).label('week'),
        func.avg(Complaint.citizen_rating).label('avg_rating'),
        func.count(Complaint.id).label('count')
    ).filter(Complaint.created_at >= eight_weeks_ago, Complaint.citizen_rating.isnot(None))\
     .group_by('week').order_by('week').all()
    return [{"week": r.week, "avg_rating": round(float(r.avg_rating), 2), "count": r.count} for r in results]


@public_router.get("/public/word-cloud")
def get_word_cloud(db: Session = Depends(get_db)):
    complaints = db.query(Complaint.description).filter(Complaint.description.isnot(None)).all()
    words = []
    for (desc,) in complaints:
        tokens = re.findall(r'[a-zA-Z]+', desc.lower())
        words.extend([w for w in tokens if w not in STOPWORDS and len(w) > 2])
    top = Counter(words).most_common(30)
    return [{"word": w, "count": c} for w, c in top]


@public_router.get("/public/councillor-briefing/{ward}")
async def councillor_briefing(ward: str, db: Session = Depends(get_db)):
    """Public ward councillor briefing — no auth required.
    # FEATURE 17: Ward councillor complaint briefing"""
    now = datetime.utcnow()
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Top 3 open issues by priority_score
    top_open = db.query(Incident).filter(
        Incident.ward == ward,
        ~Incident.status.in_(["resolved", "closed"]),
    ).order_by(Incident.priority_score.desc().nullslast()).limit(3).all()
    top_3_open_issues = [{
        "id": inc.id,
        "incident_number": inc.incident_number,
        "category": inc.category,
        "priority_score": inc.priority_score,
        "priority_label": inc.priority_label,
        "days_open": inc.days_open,
        "summary": inc.summary,
    } for inc in top_open]

    # Resolved count this month
    resolved_count_this_month = db.query(Incident).join(
        Complaint, Complaint.incident_id == Incident.id
    ).filter(
        Complaint.ward == ward,
        Incident.status.in_(["resolved", "closed"]),
        Incident.status_changed_at.isnot(None),
        Incident.status_changed_at >= first_of_month,
    ).count()

    # Most common category
    category_row = db.query(
        Complaint.predicted_category,
        func.count(Complaint.id).label("cnt"),
    ).filter(
        Complaint.ward == ward,
        Complaint.predicted_category.isnot(None),
    ).group_by(Complaint.predicted_category).order_by(func.count(Complaint.id).desc()).first()
    most_common_category = category_row[0] if category_row else None

    # SLA breach count: incidents where days_open > 7 and not resolved/closed
    sla_breach_count = db.query(Incident).join(
        Complaint, Complaint.incident_id == Incident.id
    ).filter(
        Complaint.ward == ward,
        ~Incident.status.in_(["resolved", "closed"]),
        Incident.days_open.isnot(None),
        Incident.days_open > 7,
    ).count()

    # Total open count
    total_open_count = db.query(Incident).join(
        Complaint, Complaint.incident_id == Incident.id
    ).filter(
        Complaint.ward == ward,
        ~Incident.status.in_(["resolved", "closed"]),
    ).count()

    return {
        "ward": ward,
        "top_3_open_issues": top_3_open_issues,
        "resolved_count_this_month": resolved_count_this_month,
        "most_common_category": most_common_category,
        "sla_breach_count": sla_breach_count,
        "total_open_count": total_open_count,
    }


@public_router.get("/track/{complaint_id}", response_model=TrackComplaintResponse)
async def track_complaint(complaint_id: str, request: Request, _: None = Depends(check_track_public_rate_limit), db: Session = Depends(get_db)):  # FEATURE 2: newly rate-limited
    """Public complaint tracking — no auth required. Returns status-only info, no PII."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    incident = db.query(Incident).filter(Incident.id == complaint.incident_id).first() if complaint.incident_id else None
    status = incident.status if incident else "pending"

    updates = []
    if incident:
        updates = db.query(IncidentUpdate).filter(
            IncidentUpdate.incident_id == incident.id
        ).order_by(IncidentUpdate.created_at.asc()).all()

    timeline = [
        TimelineEvent(label="Submitted", date=complaint.created_at.isoformat() if complaint.created_at else None),
    ]
    if complaint.predicted_category:
        timeline.append(TimelineEvent(
            label="Categorized",
            date=complaint.created_at.isoformat() if complaint.created_at else None,
            detail=complaint.predicted_category,
        ))
    if incident:
        timeline.append(TimelineEvent(
            label="Assigned",
            date=incident.created_at.isoformat() if incident.created_at else None,
            detail=incident.incident_number,
        ))
    if status in ("in-progress", "pending_verification", "resolved", "closed"):
        timeline.append(TimelineEvent(
            label="In Progress",
            date=None,
        ))
    if status in ("pending_verification", "resolved", "closed"):
        timeline.append(TimelineEvent(
            label="Resolved" if status == "resolved" else "Pending Verification",
            date=None,
        ))

    for u in updates:
        timeline.append(TimelineEvent(
            label="Status Update",
            date=u.created_at.isoformat() if u.created_at else None,
            detail=f"{u.user_name}: {u.message}",
        ))

    # Get officer info (name + designation only — no phone/email PII)
    officer_info = route_complaint(complaint.ward or "", complaint.predicted_category or "")
    officer_name = officer_info.get("name") if isinstance(officer_info, dict) else None
    officer_role = officer_info.get("designation") if isinstance(officer_info, dict) else None

    return TrackComplaintResponse(
        complaintId=complaint.id,
        title=complaint.title,
        category=complaint.predicted_category,
        ward=complaint.ward,
        status=status,
        dateReceived=complaint.created_at.isoformat() if complaint.created_at else "",
        timeline=timeline,
        department=get_department(complaint.predicted_category or ""),
        officer_name=officer_name,
        officer_role=officer_role,
        resolution_note=incident.resolution_note if incident and incident.resolution_note else None,
    )


@public_router.get("/public/success-stories")
async def public_success_stories(ward: Optional[str] = None, db: Session = Depends(get_db)):
    """Top-rated recently resolved complaints — anonymized, no PII.
    Returns up to 5 incidents whose linked complaints have citizen ratings of 4 or 5.
    If `ward` is provided, only incidents in that ward are returned.
    """
    q = db.query(
        Incident.category,
        Incident.ward,
        Incident.resolution_note,
        Complaint.citizen_rating,
        Incident.days_open,
    ).join(Complaint, Complaint.incident_id == Incident.id).filter(
        Incident.status.in_(["resolved", "closed"]),
        Complaint.citizen_rating.isnot(None),
        Complaint.citizen_rating >= 4,
    )
    if ward:
        ward_str = f"Ward {ward}"
        q = q.filter(Incident.ward.in_([ward_str, ward]))
    rows = q.order_by(Complaint.created_at.desc()).limit(5).all()

    seen = set()
    result = []
    for cat, ward, note, rating, days in rows:
        dept = get_department(cat or "")
        key = (cat, ward)
        if key not in seen:
            seen.add(key)
            result.append({
                "category": cat,
                "ward": ward,
                "department": dept,
                "resolution_note": note,
                "citizen_rating": rating,
                "days_to_resolve": days or 0,
            })
    return result


@public_router.get("/public/stats", response_model=PublicStatsResponse)
async def public_stats(request: Request, _: None = Depends(check_public_stats_rate_limit), db: Session = Depends(get_db)):  # FEATURE 2: newly rate-limited
    """Public aggregate stats — no auth required. Only anonymized counts, no PII."""
    # FEATURE 13: 60s Redis cache
    pool = get_pool()
    cache_key = "cache:/public/stats"
    if pool:
        cached = await pool.get(cache_key)
        if cached:
            return json.loads(cached)
    now = datetime.utcnow()
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Total complaints this month
    total_this_month = db.query(func.count(Complaint.id)).filter(
        Complaint.created_at >= first_of_month
    ).scalar() or 0

    # Resolution rate: resolved / (resolved + open + in-progress)
    resolved_count = db.query(func.count(Incident.id)).filter(
        Incident.status.in_(["resolved", "closed"])
    ).scalar() or 0
    open_count = db.query(func.count(Incident.id)).filter(
        Incident.status.in_(["open", "in-progress", "pending_verification"])
    ).scalar() or 0
    total_active = resolved_count + open_count
    resolution_rate = round((resolved_count / total_active) * 100, 1) if total_active > 0 else 0.0

    # Avg resolution time (days_open for resolved incidents)
    avg_days = db.query(func.avg(Incident.days_open)).filter(
        Incident.status.in_(["resolved", "closed"])
    ).scalar()
    avg_resolution = round(float(avg_days), 1) if avg_days else 0.0

    # Complaints by category (counts only)
    cat_raw = db.query(
        Complaint.predicted_category, func.count(Complaint.id)
    ).filter(
        Complaint.predicted_category.isnot(None),
    ).group_by(Complaint.predicted_category).order_by(func.count(Complaint.id).desc()).all()
    by_category = [CategoryStat(category=cat or "Uncategorized", count=cnt) for cat, cnt in cat_raw]

    # Complaints by zone (aggregated from ward data, not ward-level)
    ward_raw = db.query(
        Complaint.ward, func.count(Complaint.id)
    ).filter(
        Complaint.ward.isnot(None), Complaint.ward != "",
    ).group_by(Complaint.ward).all()

    zone_counts: dict[str, int] = {}
    for ward_str, cnt in ward_raw:
        try:
            ward_num = int(ward_str.split()[-1]) if " " in ward_str else int(ward_str)
        except ValueError:
            continue
        zone = ZONE_BY_WARD.get(ward_num)
        if zone:
            zone_counts[zone] = zone_counts.get(zone, 0) + cnt
    by_zone = [ZoneStat(zone=zone, count=cnt) for zone, cnt in sorted(zone_counts.items())]

    # Complaints by hour of day (0-23) — portable EXTRACT
    hour_raw = db.query(
        extract('hour', Complaint.created_at).label('hour'),
        func.count(Complaint.id)
    ).filter(
        Complaint.created_at.isnot(None),
    ).group_by('hour').order_by('hour').all()

    hour_map: dict[int, int] = {}
    for h, cnt in hour_raw:
        hour_map[int(h)] = cnt
    by_hour = [HourStat(hour=h, count=hour_map.get(h, 0)) for h in range(24)]

    # Complaints by day of week (0=Sunday … 6=Saturday) — portable EXTRACT
    DAY_NAMES = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    dow_raw = db.query(
        extract('dow', Complaint.created_at).label('dow'),
        func.count(Complaint.id)
    ).filter(
        Complaint.created_at.isnot(None),
    ).group_by('dow').order_by('dow').all()

    dow_map: dict[int, int] = {}
    for d, cnt in dow_raw:
        dow_map[int(d)] = cnt
    by_day = [DayStat(day=DAY_NAMES[d], count=dow_map.get(d, 0)) for d in range(7)]

    # Resolution funnel: complaints by their incident's current status
    STAGES = [
        ("open", "Routed"),
        ("in-progress", "In Progress"),
        ("pending_verification", "Pending Citizen Verification"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
    ]
    status_raw = db.query(
        Incident.status,
        func.count(Complaint.id)
    ).join(Complaint, Complaint.incident_id == Incident.id).group_by(Incident.status).all()
    status_map: dict[str, int] = dict(status_raw)

    # Unlinked complaints (submitted, not yet assigned to any incident)
    unlinked = db.query(func.count(Complaint.id)).filter(
        Complaint.incident_id.is_(None)
    ).scalar() or 0
    total_all = db.query(func.count(Complaint.id)).scalar() or 0

    by_status = [
        FunnelStage(label="Submitted", count=total_all),
        *[FunnelStage(label=display, count=status_map.get(db_status, 0)) for db_status, display in STAGES],
    ]

    response = PublicStatsResponse(
        totalComplaintsThisMonth=total_this_month,
        resolutionRate=resolution_rate,
        avgResolutionDays=avg_resolution,
        complaintsByCategory=by_category,
        complaintsByZone=by_zone,
        complaintsByHour=by_hour,
        complaintsByDay=by_day,
        complaintsByStatus=by_status,
    )
    if pool:
        await pool.set(cache_key, json.dumps(response.dict() if hasattr(response, 'dict') else response), ex=60)
    return response


@public_router.get("/public/ward-stats/{ward}")
async def public_ward_stats(ward: str, db: Session = Depends(get_db)):
    """Public aggregate stats for a single ward — no auth, no PII."""
    ward_str = f"Ward {ward}"
    match = db.query(
        func.count(Complaint.id),
        func.avg(Incident.days_open).filter(Incident.status.in_(["resolved", "closed"])),
        func.count(Incident.id).filter(Incident.status.in_(["resolved", "closed"])),
    ).outerjoin(Incident, Complaint.incident_id == Incident.id).filter(
        Complaint.ward.in_([ward_str, ward]),
    ).first()

    total = match[0] or 0
    avg_days = match[1]
    resolved = match[2] or 0

    resolved_pct = round((resolved / total) * 100, 1) if total > 0 else 0.0
    avg_resolution = round(float(avg_days), 1) if avg_days else 0.0

    category_raw = db.query(
        Complaint.predicted_category, func.count(Complaint.id)
    ).filter(
        Complaint.ward.in_([ward_str, ward]),
        Complaint.predicted_category.isnot(None),
    ).group_by(Complaint.predicted_category).order_by(func.count(Complaint.id).desc()).all()

    top_categories = [
        {"category": cat, "count": cnt}
        for cat, cnt in category_raw
    ]

    return {
        "ward": ward,
        "total_complaints": total,
        "resolved_percentage": resolved_pct,
        "avg_resolution_days": avg_resolution,
        "top_categories": top_categories,
    }


@public_router.get("/public/nearby-complaints")
async def public_nearby_complaints(
    ward: str,
    category: str,
    exclude: str = "",
    db: Session = Depends(get_db),
):
    """Anonymized nearby complaints in the same ward+category. No PII."""
    rows = (
        db.query(
            Complaint.id,
            Complaint.ward,
            Complaint.predicted_category,
            Complaint.priority,
            Complaint.created_at,
            Incident.status,
            Incident.days_open,
        )
        .outerjoin(Incident, Complaint.incident_id == Incident.id)
        .filter(
            Complaint.ward == ward,
            Complaint.predicted_category == category,
        )
    )
    if exclude:
        rows = rows.filter(Complaint.id != exclude)
    rows = rows.order_by(
        Incident.days_open.desc().nullslast(),
        Complaint.created_at.desc(),
    ).limit(5).all()

    return [
        {
            "complaint_id": r.id,
            "ward": r.ward,
            "category": r.predicted_category,
            "priority": r.priority,
            "status": r.status or "open",
            "days_open": r.days_open or 0,
            "date_received": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@public_router.get("/public/resolved-gallery")
async def public_resolved_gallery(db: Session = Depends(get_db)):
    """Public gallery of resolved incidents with high ratings and proof photos."""
    rows = db.query(
        Incident.id,
        Incident.category,
        Incident.ward,
        Incident.resolution_note,
        Incident.days_open,
        Incident.resolution_photo_path,
        Complaint.citizen_rating,
    ).join(Complaint, Complaint.incident_id == Incident.id).filter(
        Incident.status.in_(["closed", "resolved"]),
        Complaint.citizen_rating.isnot(None),
        Complaint.citizen_rating >= 4,
        Incident.resolution_photo_path.isnot(None),
    ).order_by(Complaint.created_at.desc()).limit(20).all()

    result = []
    seen_ids = set()
    for iid, cat, ward, note, days, photo_path, rating in rows:
        if iid in seen_ids:
            continue
        seen_ids.add(iid)
        presigned_url = None
        if photo_path and os.path.exists(photo_path):
            try:
                from storage import S3Storage
                s3 = S3Storage()
                if s3.available:
                    presigned_url = s3.get_presigned_url(photo_path)
            except Exception:
                presigned_url = f"/incidents/{iid}/resolution-photo"
        else:
            presigned_url = f"/incidents/{iid}/resolution-photo" if photo_path else None
        result.append({
            "id": iid,
            "category": cat,
            "ward": ward,
            "resolution_note": (note[:200] + "...") if note and len(note) > 200 else note,
            "days_open": days or 0,
            "rating": rating,
            "resolution_photo_url": presigned_url,
        })
    return result

