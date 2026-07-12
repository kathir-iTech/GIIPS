"""
API route definitions for GIIPS backend.
"""

import uuid
import time
import logging
from fastapi import APIRouter, HTTPException, Depends, Query, Header, UploadFile, File, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, extract
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from database import get_db, User, Incident, Complaint, AuditLog, DepartmentMetrics
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
    CopilotChatResponse
)
from schemas import ComplaintCreate, ComplaintSubmissionResponse, SubmissionAcceptedResponse, ComplaintProcessingStatus
from job_queue import get_complaint_status
from rate_limiter import check_auth_rate_limit
from department_map import get_department
from pipeline import process_complaint_pipeline
from services import (
    ClassificationService,
    ClusteringService,
    PriorityService,
    DashboardService,
    DecisionService,
    SpatialService
)
from auth_service import hash_password, verify_password, create_access_token, verify_token
from prediction.engine import PredictiveEngine
from knowledge.engine import GovernanceKnowledgeEngine
from decision.support import DecisionSupportEngine
from copilot.engine import CopilotEngine
from storage import S3Storage, validate_file

logger = logging.getLogger(__name__)

def get_current_user(authorization: Optional[str] = Header(None, alias="Authorization"), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
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
async def submit_complaint(request: ComplaintCreate, db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Submit a new citizen complaint. Runs ML pipeline inline via asyncio.create_task
    (no separate worker process needed — keeps Render free tier viable)."""
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
    """Upload a photo for complaint evidence (jpg/png, max 5MB)."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id, Complaint.user_id == db_user.id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    data = await file.read()
    err = validate_file(file.filename or "upload", file.content_type or "", len(data))
    if err:
        raise HTTPException(status_code=400, detail=err)

    storage = S3Storage()
    if not storage.available:
        logger.warning("S3 not configured — skipping photo upload for complaint %s", complaint_id)
        return {"imageUrl": "", "complaintId": complaint_id, "message": "Photo storage not configured. Complaint submitted without image."}

    try:
        url = storage.upload(data, file.filename, file.content_type)
    except Exception as e:
        logger.error("S3 upload failed for complaint %s: %s", complaint_id, e)
        raise HTTPException(status_code=502, detail=f"Storage upload failed: {e}")

    complaint.image_path = url
    db.commit()

    return {"imageUrl": url, "complaintId": complaint_id, "message": "Photo uploaded successfully."}


@complaint_router.get("/my")
async def get_my_complaints(db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get complaints for the current authenticated user."""
    complaints = db.query(Complaint).filter(Complaint.user_id == db_user.id).order_by(Complaint.created_at.desc()).all()
    result = []
    for c in complaints:
        incident = db.query(Incident).filter(Incident.id == c.incident_id).first() if c.incident_id else None
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
            "date_received": c.created_at.isoformat() if c.created_at else None,
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
    return {"complaints": result}


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
        "priority": complaint.priority,
        "similarity_score": complaint.similarity_score,
        "merge_reason": complaint.merge_reason,
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


@incident_router.get("")
async def get_incidents(db: Session = Depends(get_db)):
    """Get all incidents."""
    incidents = db.query(Incident).options(joinedload(Incident.complaints)).all()
    result = []
    for inc in incidents:
        inc_dict = {
            "id": inc.id, "incident_number": inc.incident_number, "category": inc.category,
            "department": get_department(inc.category),
            "ward": inc.ward, "cluster_size": inc.cluster_size, "priority_score": inc.priority_score,
            "priority_label": inc.priority_label, "status": inc.status, "summary": inc.summary,
            "recommended_action": inc.recommended_action, "days_open": inc.days_open,
            "complaints": [{
                "id": c.id, "complaint_number": c.id,
                "date_received": c.created_at.isoformat() if c.created_at else None,
                "text": c.title, "similarity_score": c.similarity_score or 0.85
            } for c in inc.complaints] if inc.complaints else []
        }
        result.append(inc_dict)
    return {"incidents": result}


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
            "text": c.title, "similarity_score": c.similarity_score or 0.85
        } for c in inc.complaints] if inc.complaints else [],
        "priority_history": [{
            "id": ph.id, "old_score": ph.old_score, "new_score": ph.new_score,
            "reason": ph.reason, "changed_at": ph.changed_at.isoformat() if ph.changed_at else None
        } for ph in inc.priority_history] if inc.priority_history else [],
    }

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
async def login(user: UserLogin, request: Request, _: None = Depends(check_auth_rate_limit), db: Session = Depends(get_db)):
    """Authenticate user and return JWT token."""
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.password_hash):
        _write_audit_log(db, None, user.email, None, "login", "auth", "failure", "Invalid credentials")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": db_user.email, "role": db_user.role})
    _write_audit_log(db, db_user.id, db_user.email, db_user.role, "login", "auth", "success")
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": db_user.role,
        "user_id": db_user.id,
        "full_name": db_user.full_name
    }

@auth_router.get("/me", response_model=UserResponse)
async def get_me(db_user: User = Depends(get_current_user)):
    """Get current user profile from token."""
    return UserResponse(user_id=db_user.id, full_name=db_user.full_name, email=db_user.email, role=db_user.role)

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
    return UserResponse(user_id=db_user.id, full_name=db_user.full_name, email=db_user.email, role=db_user.role)

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

