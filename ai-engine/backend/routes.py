"""
API route definitions for GIIPS backend.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel

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
    ComplaintService
)

# Create routers
classify_router = APIRouter(prefix="/classify", tags=["Classification"])
cluster_router = APIRouter(prefix="/cluster", tags=["Clustering"])
priority_router = APIRouter(prefix="/priority", tags=["Priority"])
dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
incident_router = APIRouter(prefix="/incidents", tags=["Incidents"])
complaint_router = APIRouter(prefix="/complaints", tags=["Complaints"])


# === Complaint Submission Routes ===

@complaint_router.post("", response_model=ComplaintSubmissionResponse)
async def submit_complaint(request: ComplaintCreate):
    """Submit a new citizen complaint through the pipeline."""
    service = ComplaintService()
    return await service.submit_complaint(request.dict())


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
async def get_dashboard():
    """Get dashboard summary data."""
    service = DashboardService()
    return await service.get_summary()


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

@incident_router.get("")
async def list_incidents(
    priority: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = Query(10, ge=1, le=100)
):
    """List incidents with optional filters."""
    service = DashboardService()
    incidents = await service.get_incidents(priority, category, limit)
    return {"incidents": incidents, "count": len(incidents)}


@incident_router.get("/{incident_id}")
async def get_incident(incident_id: str):
    """Get details for a specific incident."""
    service = DashboardService()
    incident = await service.get_incident_by_id(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident
