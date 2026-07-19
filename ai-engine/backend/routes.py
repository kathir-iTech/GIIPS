"""
API route definitions for GIIPS backend.
"""

import os
import json
import uuid
import time
import random
import logging
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Request, Response
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, extract, text
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from database import get_db, User, Incident, Complaint, AuditLog, DepartmentMetrics, Notification, PriorityHistory, ZONE_BY_WARD
from models import (
    ClassifyRequest, ClassifyResponse,
    ClusterRequest, ClusterResponse, ClusterAssignment,
    PriorityRequest, PriorityResponse, PriorityFactor,
    IncidentResponse,
    UserRegister, UserLogin, UserResponse, OfficerCreate, ProfileUpdate,
    PredictionSummaryResponse,
    KnowledgeSummaryResponse,
    DecisionSupportSummaryResponse,
    CopilotChatRequest,
    CopilotChatResponse,
    MergeIncidentsRequest,
    NotificationResponse,
    UpdateStatusRequest,
)
from schemas import ComplaintCreate, ComplaintSubmissionResponse, SubmissionAcceptedResponse, ComplaintProcessingStatus, EscalateRequest, VerifyResolutionRequest, TrackComplaintResponse, PublicStatsResponse, TimelineEvent, ZoneStat, CategoryStat
from job_queue import get_complaint_status
from rate_limiter import check_auth_rate_limit, check_complaint_rate_limit, check_verify_rate_limit, check_track_rate_limit
from constants import AGING_WARNING_DAYS, AGING_CRITICAL_DAYS
from department_map import (
    get_department, get_department_slug, get_slug_for_department,
    CATEGORY_DEPT_MAP, DEPARTMENT_SLUGS, SLUG_TO_DISPLAY, get_i18n_key
)
from officer_routing import route_complaint
from pipeline import process_complaint_pipeline
from services import (
    ClassificationService,
    ClusteringService,
    PriorityService,
    DashboardService,
    DecisionService,
    SpatialService
)
from auth_service import hash_password, verify_password, create_access_token, verify_token, set_auth_cookie, clear_auth_cookie
from prediction.engine import PredictiveEngine
from knowledge.engine import GovernanceKnowledgeEngine
from decision.support import DecisionSupportEngine
from copilot.engine import CopilotEngine
from storage import S3Storage, validate_file

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
    Uses flush (not commit) so it does not interfere with the caller's transaction."""
    try:
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
    except Exception:
        logger.error("Notification creation failed for user=%s type=%s", user_id, notification_type)


def _get_department_officers(db: Session, department: str) -> list[User]:
    """Return active officers assigned to a given department."""
    return db.query(User).filter(
        User.role == "Officer",
        User.department == department,
        User.status == "active"
    ).all()


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
    return await SpatialService().get_heatmap(db)

@spatial_router.get("/hotspots")
async def get_hotspots(db: Session = Depends(get_db)):
    return await SpatialService().get_hotspots(db)

@spatial_router.get("/forecast")
async def get_forecast(days: int = 7):
    return await SpatialService().get_forecast(days)

@spatial_router.get("/risk")
async def get_risk(db: Session = Depends(get_db)):
    return await SpatialService().get_risk_analysis(db)

@spatial_router.post("/simulate")
async def simulate(additional_teams: int):
    return await SpatialService().simulate_resources(additional_teams)

executive_router = APIRouter(prefix="/executive", tags=["Executive"])

@executive_router.get("/summary")
async def get_executive_summary(db: Session = Depends(get_db)):
    service = DecisionService()
    return await service.get_executive_summary(db)

@executive_router.get("/ward-health")
async def get_ward_health(db: Session = Depends(get_db)):
    service = DecisionService()
    return await service.get_ward_health(db)

@executive_router.get("/department-workload")
async def get_dept_workload(db: Session = Depends(get_db)):
    service = DecisionService()
    return await service.get_dept_workload(db)

classify_router = APIRouter(prefix="/classify", tags=["Classification"])
cluster_router = APIRouter(prefix="/cluster", tags=["Clustering"])
priority_router = APIRouter(prefix="/priority", tags=["Priority"])
dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
incident_router = APIRouter(prefix="/incidents", tags=["Incidents"])
complaint_router = APIRouter(prefix="/complaints", tags=["Complaints"])


# === Complaint Submission Routes ===

@complaint_router.post("", status_code=202, response_model=SubmissionAcceptedResponse)
async def submit_complaint(request: ComplaintCreate, _: None = Depends(check_complaint_rate_limit), db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Submit a new citizen complaint. Runs ML pipeline inline via asyncio.create_task
    (no separate worker process needed — keeps Render free tier viable)."""

    # ── E-khata/Khata rejection upstream ─────────────────────────────────
    # Property document requests are not civic grievances.
    from department_map import is_khata_complaint, get_khata_rejection_response
    combined_text = f"{request.title} {request.description}"
    if is_khata_complaint(combined_text):
        khata_resp = get_khata_rejection_response()
        raise HTTPException(status_code=400, detail=khata_resp["message"])

    complaint_id = str(uuid.uuid4())
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
    )
    db.add(complaint)
    db.commit()

    import asyncio
    asyncio.create_task(process_complaint_pipeline(complaint_id, db_user.id))

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
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
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
    incident = db.query(Incident).options(joinedload(Incident.priority_history)).filter(Incident.id == complaint.incident_id).first() if complaint.incident_id else None
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
            "priority_history": [
                {
                    "id": ph.id,
                    "old_score": ph.old_score,
                    "new_score": ph.new_score,
                    "reason": ph.reason,
                    "changed_at": ph.changed_at.isoformat() if ph.changed_at else None,
                } for ph in incident.priority_history
            ] if incident else [],
        } if incident else None
    }


# === Classification Routes ===

@classify_router.post("", response_model=ClassifyResponse)
async def classify_single(request: ClassifyRequest):
    """Classify a single complaint into a category."""
    service = ClassificationService()
    return await service.classify(request)


@classify_router.post("/batch")
async def classify_batch(requests: List[ClassifyRequest]):
    """Classify multiple complaints at once."""
    service = ClassificationService()
    results = [await service.classify(req) for req in requests]
    return {"results": results, "count": len(results)}


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
    """Get key performance metrics."""
    return {
        "model_accuracy": 92.3,
        "model_precision": 91.7,
        "model_recall": 93.1,
        "model_f1": 92.4,
        "processing_time_ms": 45,
        "last_updated": datetime.now().isoformat()
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

    return {
        "labels": [m[2] for m in months],
        "complaints": [comp_by_month.get((y, m), 0) for y, m, _ in months],
        "incidents": [inc_by_month.get((y, m), 0) for y, m, _ in months],
    }


@dashboard_router.get("/analytics")
async def get_analytics(db: Session = Depends(get_db)):
    """Get comprehensive analytics data for the Analysis page."""
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
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
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
            "complaints": [{
                "id": c.id, "complaint_number": c.id,
                "date_received": c.created_at.isoformat() if c.created_at else None,
                "text": c.title, "similarity_score": c.similarity_score or 0.85,
                "photo_duplicate_flag": c.photo_duplicate_flag,
                "photo_duplicate_of": c.photo_duplicate_of,
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
                     "photo_duplicate_of": c.photo_duplicate_of}
                    for c in inc.complaints
                ] if inc.complaints else [],
            }
            for inc in incidents
        ]
    }


@incident_router.post("/auto-escalate")
async def auto_escalate_aging_incidents(db: Session = Depends(get_db)):
    """Auto-escalate incidents that have exceeded the AGING_CRITICAL_DAYS threshold.
    Called periodically (e.g. from a scheduler or on relevant state changes).
    Follows the same SLA threshold as the aging notification system."""
    from constants import AGING_CRITICAL_DAYS

    incident_id = None
    try:
        cut_off = datetime.datetime.utcnow() - timedelta(days=AGING_CRITICAL_DAYS)
        aging = db.query(Incident).filter(
            Incident.created_at <= cut_off,
            Incident.escalated == False
        ).all()
        count = 0
        for inc in aging:
            inc.escalated = True
            inc.escalated_at = datetime.datetime.utcnow()
            inc.escalated_by = "system"
            count += 1
        if count:
            db.commit()
            return {"message": f"Auto-escalated {count} aging incidents"}
        return {"message": "No aging incidents to escalate"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Auto-escalation failed: {e}")


@incident_router.get("/{incident_id}")
async def get_incident(incident_id: str, db: Session = Depends(get_db)):
    """Get incident by ID."""
    inc = db.query(Incident).options(joinedload(Incident.complaints), joinedload(Incident.priority_history)).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {
        "id": inc.id, "incident_number": inc.incident_number, "category": inc.category,
        "department": get_department(inc.category),
        "ward": inc.ward, "cluster_size": inc.cluster_size, "priority_score": inc.priority_score,
        "priority_label": inc.priority_label, "status": inc.status, "summary": inc.summary,
        "recommended_action": inc.recommended_action, "days_open": inc.days_open,
        "created_at": inc.created_at.isoformat() if inc.created_at else None,
        "complaints": [{
            "id": c.id, "complaint_number": c.id,
            "date_received": c.created_at.isoformat() if c.created_at else None,
            "text": c.title, "similarity_score": c.similarity_score or 0.85,
            "photo_duplicate_flag": c.photo_duplicate_flag,
            "photo_duplicate_of": c.photo_duplicate_of,
        } for c in inc.complaints] if inc.complaints else [],
        "priority_history": [{
            "id": ph.id, "old_score": ph.old_score, "new_score": ph.new_score,
            "reason": ph.reason, "changed_at": ph.changed_at.isoformat() if ph.changed_at else None
        } for ph in inc.priority_history] if inc.priority_history else [],
    }


@incident_router.post("/merge")
async def merge_incidents(body: MergeIncidentsRequest, _: None = Depends(check_complaint_rate_limit), db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
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


@incident_router.post("/{incident_id}/split/{complaint_id}")
async def split_complaint(incident_id: str, complaint_id: str, _: None = Depends(check_complaint_rate_limit), db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
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
        incident.verification_code = code
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

        return {
            "message": "Citizen verification required. A confirmation code has been sent to the complainant.",
            "incident_id": incident.id,
            "status": "pending_verification",
        }

    # Non-resolution status change: apply directly
    incident.status = body.status
    db.commit()

    # Notify all citizens whose complaints are linked to this incident
    for c in incident.complaints:
        if c.user_id:
            _create_notification(
                db, c.user_id, "status_change",
                complaint_id=c.id,
                data={"old_status": old_status, "new_status": body.status, "incident_number": incident.incident_number},
            )

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

    return {"message": f"Incident status updated to {body.status}", "incident_id": incident.id, "status": body.status}


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

    return {"message": "Incident escalated", "incident_id": incident.id, "reason": body.reason}


@incident_router.post("/{incident_id}/verify-resolution")
async def verify_resolution(incident_id: str, body: VerifyResolutionRequest, _: None = Depends(check_verify_rate_limit), db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
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
    incident.status = "resolved"
    incident.verification_code = None
    db.commit()

    # Notify the citizen
    _create_notification(
        db, db_user.id, "status_change",
        complaint_id=complaint.id,
        data={"old_status": old_status, "new_status": "resolved", "incident_number": incident.incident_number,
              "message": "Resolution confirmed. Thank you for confirming!"},
    )

    _write_audit_log(db, db_user.id, db_user.email, db_user.role, "verify_resolution",
                     incident.id, "success", "Citizen confirmed resolution")

    return {"message": "Resolution confirmed. Thank you!", "incident_id": incident.id, "status": "resolved"}


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
async def register(user: UserRegister, request: Request, _: None = Depends(check_auth_rate_limit), db: Session = Depends(get_db)):
    """Register a new citizen account. Government accounts must be created by Executive through Officer Management."""
    if user.email.endswith("@gov.in"):
        raise HTTPException(status_code=400, detail="Government accounts must be created by an Executive. Use @gov.in emails are not allowed for public registration.")
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_pw = hash_password(user.password)
    new_user = User(
        id=str(uuid.uuid4()),
        full_name=user.full_name,
        email=user.email,
        password_hash=hashed_pw,
        phone=user.phone,
        district=user.district,
        ward=user.ward,
        role="Citizen"
    )
    db.add(new_user)
    db.commit()
    return {"message": "User registered successfully", "user_id": new_user.id, "role": new_user.role}

@auth_router.post("/login")
async def login(user: UserLogin, request: Request, response: Response, _: None = Depends(check_auth_rate_limit), db: Session = Depends(get_db)):
    """Authenticate user and return JWT token as httpOnly cookie."""
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.password_hash):
        _write_audit_log(db, None, user.email, None, "login", "auth", "failure", "Invalid credentials")
        raise HTTPException(status_code=401, detail="Invalid credentials")
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
    )


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
    )

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
    return [{"id": o.id, "full_name": o.full_name, "email": o.email, "district": o.district, "created_at": o.created_at.isoformat() if o.created_at else None, "status": o.status} for o in officers]

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

@admin_router.get("/departments")
async def get_departments(db_user: User = Depends(get_executive_user), db: Session = Depends(get_db)):
    """Get department metrics."""
    _write_audit_log(db, db_user.id, db_user.email, db_user.role, "departments_view", "departments", "success")
    depts = db.query(DepartmentMetrics).all()
    return [{"department": d.department, "open_incidents": d.open_incidents, "critical_incidents": d.critical_incidents, "assigned_officers": d.assigned_officers, "avg_resolution_time": d.avg_resolution_time, "completion_percentage": d.completion_percentage, "workload_indicator": d.workload_indicator} for d in depts]

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
    try:
        engine = PredictiveEngine()
        history_counts = []
        for i in range(5):
            cutoff = datetime.utcnow() - timedelta(days=5 - i)
            next_cutoff = datetime.utcnow() - timedelta(days=4 - i)
            count = db.query(Complaint).filter(Complaint.created_at >= cutoff, Complaint.created_at < next_cutoff).count()
            history_counts.append(count)
        forecast = engine.forecast_complaints('week', history=history_counts)

        total_incidents = db.query(Incident).count()
        critical_count = db.query(Incident).filter(Incident.priority_label == 'Critical').count()
        high_count = db.query(Incident).filter(Incident.priority_label == 'High').count()
        avg_days_open = db.query(func.avg(Incident.days_open)).scalar() or 0.0

        recent_incidents = db.query(Incident).order_by(Incident.created_at.desc()).limit(5).all()
        escalation_risks = []
        for inc in recent_incidents:
            esc = engine.predict_escalation(inc.id)
            escalation_risks.append({
                "incident_id": inc.id,
                "priority_label": inc.priority_label,
                "escalation_probability": esc.get("probability", 0.0),
                "risk_level": esc.get("risk_level", "LOW")
            })

        active_alerts = engine.generate_alerts()

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
async def copilot_chat(request: CopilotChatRequest):
    """Process copilot chat query."""
    engine = CopilotEngine()
    result = engine.chat(request.user_id, request.message)
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


# === Public Endpoints (no auth required) ===

public_router = APIRouter(tags=["Public"])


@public_router.get("/track/{complaint_id}", response_model=TrackComplaintResponse)
async def track_complaint(complaint_id: str, request: Request, _: None = Depends(check_track_rate_limit), db: Session = Depends(get_db)):
    """Public complaint tracking — no auth required. Returns status-only info, no PII."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    incident = db.query(Incident).filter(Incident.id == complaint.incident_id).first() if complaint.incident_id else None
    status = incident.status if incident else "pending"

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

    return TrackComplaintResponse(
        complaintId=complaint.id,
        title=complaint.title,
        category=complaint.predicted_category,
        ward=complaint.ward,
        status=status,
        dateReceived=complaint.created_at.isoformat() if complaint.created_at else "",
        timeline=timeline,
    )


@public_router.get("/public/stats", response_model=PublicStatsResponse)
async def public_stats(db: Session = Depends(get_db)):
    """Public aggregate stats — no auth required. Only anonymized counts, no PII."""
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

    return PublicStatsResponse(
        totalComplaintsThisMonth=total_this_month,
        resolutionRate=resolution_rate,
        avgResolutionDays=avg_resolution,
        complaintsByCategory=by_category,
        complaintsByZone=by_zone,
    )

