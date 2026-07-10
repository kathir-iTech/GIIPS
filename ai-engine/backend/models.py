"""
Pydantic models for API request/response validation.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ClassifyRequest(BaseModel):
    """Request for complaint classification."""
    text: str = Field(..., description="Complaint text to classify", min_length=1)
    detail: Optional[str] = Field(None, description="Additional detail text")


class ClassifyResponse(BaseModel):
    """Response for classification."""
    predicted_category: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    top_predictions: List[Dict[str, Any]]
    reason: str
    supporting_factors: List[str]


class ComplaintModel(BaseModel):
    """Model for a single complaint."""
    id: str
    text: str
    date_received: Optional[str] = None
    ward: Optional[str] = None
    similarity_score: Optional[float] = None


class ClusterRequest(BaseModel):
    """Request for clustering complaints."""
    complaints: List[Dict[str, Any]] = Field(..., min_length=1)
    text_key: str = Field("text", description="Key for text field in complaint objects")
    eps: Optional[float] = Field(0.3, ge=0.0, le=1.0, description="DBSCAN epsilon parameter")
    min_samples: Optional[int] = Field(2, ge=1, le=10, description="DBSCAN min samples")


class ClusterAssignment(BaseModel):
    """Cluster assignment for a single complaint."""
    complaint_id: Any
    cluster_label: int
    is_noise: bool


class ClusterResponse(BaseModel):
    """Response for clustering."""
    n_clusters: int
    n_noise: int
    cluster_assignments: List[ClusterAssignment]
    cluster_details: Dict[str, Any]


class PriorityRequest(BaseModel):
    """Request for priority calculation."""
    incident_id: str
    cluster_size: int = Field(..., ge=1)
    first_complaint_date: str
    last_complaint_date: str
    category: str
    location_hints: List[str] = []


class PriorityFactor(BaseModel):
    """A single factor in priority calculation."""
    name: str
    raw_value: float
    normalized_value: float
    weight: float
    contribution: float
    description: str


class PriorityResponse(BaseModel):
    """Response for priority calculation."""
    incident_id: str
    priority_score: float = Field(..., ge=0.0, le=100.0)
    priority_label: str
    factors: List[PriorityFactor]
    explanation: str


class IncidentResponse(BaseModel):
    """Response model for an incident."""
    id: str
    incident_number: str
    category: str
    ward: str
    cluster_size: int
    days_open: int
    priority_score: float
    priority_label: str
    summary: str
    recommended_action: str
    status: str
    complaints: List[ComplaintModel]


class ComplaintResponse(BaseModel):
    """Response model for a complaint."""
    id: str
    complaint_number: str
    incident_id: Optional[str] = None
    text: str
    similarity_score: Optional[float] = None
    date_received: str


class DashboardResponse(BaseModel):
    """Response for dashboard data."""
    total_complaints: int
    unique_incidents: int
    workload_reduction: float
    critical_incidents: int
    high_priority_incidents: int
    medium_priority_incidents: Optional[int] = None
    low_priority_incidents: Optional[int] = None
    category_distribution: List[Dict[str, Any]]
    priority_distribution: Dict[str, int]
    avg_days_open: Optional[float] = None
    avg_priority_score: Optional[float] = None


class HealthResponse(BaseModel):
    """Response for health check."""
    status: str
    models_loaded: Dict[str, bool]
    timestamp: str
    version: str = "1.0.0"


class ErrorResponse(BaseModel):
    """Error response model."""
    detail: str
    code: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class FindSimilarRequest(BaseModel):
    """Request to find similar complaints."""
    text: str
    existing_complaints: List[ComplaintModel]
    threshold: float = Field(0.8, ge=0.0, le=1.0)


class SimilarResult(BaseModel):
    """Result of similarity search."""
    complaint_id: str
    text: str
    similarity: float


class FindSimilarResponse(BaseModel):
    """Response for finding similar complaints."""
    similar_complaints: List[SimilarResult]

class UserRegister(BaseModel):
    full_name: str
    email: str
    password: str
    phone: Optional[str] = None
    district: Optional[str] = None
    ward: Optional[str] = None

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    district: Optional[str] = None
    ward: Optional[str] = None
    password: Optional[str] = None

class OfficerCreate(BaseModel):
    full_name: str
    email: str
    password: str
    district: Optional[str] = None
    department: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    user_id: str
    full_name: str
    email: str
    role: str


class PredictionSummaryResponse(BaseModel):
    timeframe: str
    predicted_volume: float = Field(..., ge=0.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    model: str
    total_incidents: int
    critical_count: int
    high_priority_count: int
    avg_days_open: float
    recent_escalation_risks: List[Dict[str, Any]]
    active_alerts: List[Dict[str, Any]]


class KnowledgeSummaryResponse(BaseModel):
    district_risk_index: Optional[int] = None
    infrastructure_risk_index: Optional[int] = None
    policy_recommendations: List[Dict[str, Any]]
    worst_performing_ward: Optional[str] = None
    root_causes: List[Dict[str, Any]]
    cascade_chains: List[Dict[str, Any]]


class DecisionSupportSummaryResponse(BaseModel):
    district_rankings: List[Dict[str, Any]]
    ward_rankings: Dict[str, Any]
    top_critical_recommendation: Optional[Dict[str, Any]]
    executive_report: str


class CopilotChatRequest(BaseModel):
    user_id: str
    message: str


class CopilotChatResponse(BaseModel):
    response: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    data_sources: List[str]
    reasoning: str
