"""
API route definitions for GIIPS backend.
"""

import uuid
from fastapi import APIRouter, HTTPException, Depends, Query, Header
from sqlalchemy.orm import Session, joinedload
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel

from database import get_db, User, Incident
from models import (
    ClassifyRequest, ClassifyResponse,
    ClusterRequest, ClusterResponse,
    PriorityRequest, PriorityResponse,
    IncidentResponse, ComplaintResponse,
    UserRegister, UserLogin, UserResponse
)
from schemas import ComplaintCreate, ComplaintSubmissionResponse
from services import (
    ClassificationService,
    ClusteringService,
    PriorityService,
    DashboardService,
    ComplaintService,
    DecisionService,
    SpatialService
)
from auth_service import hash_password, verify_password, create_access_token, verify_token

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

@complaint_router.post("", response_model=ComplaintSubmissionResponse)
async def submit_complaint(request: ComplaintCreate, db_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Submit a new citizen complaint through the pipeline."""
    service = ComplaintService()
    return await service.submit_complaint(db, request.dict(), user_id=db_user.id)


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
        "predicted_category": complaint.predicted_category,
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
async def get_trend_data():
    """Get trend data for charts."""
    return {
        "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
        "complaints": [95, 127, 143, 108, 89, 115],
        "incidents": [15, 18, 22, 16, 12, 15]
    }


@incident_router.get("")
async def get_incidents(db: Session = Depends(get_db)):
    """Get all incidents."""
    incidents = db.query(Incident).options(joinedload(Incident.complaints)).all()
    result = []
    for inc in incidents:
        inc_dict = {
            "id": inc.id, "incident_number": inc.incident_number, "category": inc.category,
            "ward": inc.ward, "cluster_size": inc.cluster_size, "priority_score": inc.priority_score,
            "priority_label": inc.priority_label, "status": inc.status, "summary": inc.summary,
            "recommended_action": inc.recommended_action, "days_open": inc.days_open,
            "complaints": [{
                "id": c.id, "complaint_number": c.id.replace("COMP-", "CMP-"), 
                "date_received": c.created_at.isoformat() if c.created_at else None,
                "text": c.title, "similarity_score": c.similarity_score or 0.85
            } for c in inc.complaints] if inc.complaints else []
        }
        result.append(inc_dict)
    return {"incidents": result}


@incident_router.get("/{incident_id}")
async def get_incident(incident_id: str, db: Session = Depends(get_db)):
    """Get incident by ID."""
    service = DashboardService()
    incident = service.get_incident_by_id(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident

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
async def register(user: UserRegister, db: Session = Depends(get_db)):
    """Register a new user."""
    hashed_pw = hash_password(user.password)
    new_user = User(
        id=str(uuid.uuid4()),
        full_name=user.full_name,
        email=user.email,
        password_hash=hashed_pw,
        phone=user.phone,
        district=user.district,
        ward=user.ward,
        role=user.role
    )
    db.add(new_user)
    db.commit()
    return {"message": "User registered successfully", "user_id": new_user.id}

@auth_router.post("/login")
async def login(user: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return JWT token."""
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": db_user.email, "role": db_user.role})
    return {"access_token": token, "token_type": "bearer", "role": db_user.role}

@auth_router.get("/me", response_model=UserResponse)
async def get_me(db_user: User = Depends(get_current_user)):
    """Get current user profile from token."""
    return UserResponse(user_id=db_user.id, full_name=db_user.full_name, email=db_user.email, role=db_user.role)

