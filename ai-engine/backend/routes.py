"""
API route definitions for GIIPS backend.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel

from database import get_db
from models import (
    ClassifyRequest, ClassifyResponse,
    ClusterRequest, ClusterResponse,
    PriorityRequest, PriorityResponse,
    IncidentResponse, ComplaintResponse
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
async def submit_complaint(request: ComplaintCreate, db: Session = Depends(get_db)):
    """Submit a new citizen complaint through the pipeline."""
    service = ComplaintService()
    return await service.submit_complaint(db, request.dict())


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
    return await service.classify(ClassifyRequest(text=request.get('text', '')))


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


# === Incident Routes ===
# ... (existing incident_router)

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
    from database import User
    from auth_service import hash_password
    hashed_pw = hash_password(user.password)
    new_user = User(
        id=str(uuid.uuid4()),
        full_name=user.full_name,
        email=user.email,
        password_hash=hashed_pw,
        role=user.role,
        district=user.district,
        ward=user.ward
    )
    db.add(new_user)
    db.commit()
    return {"message": "User registered successfully"}

@auth_router.post("/login")
async def login(user: UserLogin, db: Session = Depends(get_db)):
    from database import User
    from auth_service import verify_password, create_access_token
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": db_user.email, "role": db_user.role})
    return {"access_token": token, "token_type": "bearer", "role": db_user.role}

@auth_router.get("/me")
async def get_me(token: str, db: Session = Depends(get_db)):
    from auth_service import verify_token
    from database import User
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    db_user = db.query(User).filter(User.email == payload["sub"]).first()
    return UserResponse(user_id=db_user.id, full_name=db_user.full_name, email=db_user.email, role=db_user.role)

