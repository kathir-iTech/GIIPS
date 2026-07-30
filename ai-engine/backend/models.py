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
    method: str = Field("ml_model", description="Classification method used (ml_model, heuristic_fallback, tamil_keyword_fallback)")
    complexity_score: Optional[float] = Field(None, description="Computed complexity score")
    complexity_label: Optional[str] = Field(None, description="Complexity level (simple/moderate/complex)")
    complaint_language: Optional[str] = Field(None, description="Detected language (english/tamil)")


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
    incident_latitude: Optional[float] = None
    incident_longitude: Optional[float] = None
    trust_score: Optional[float] = None


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
    current_shift: Optional[str] = None  # FEATURE 15: shift schedule

class OfficerCreate(BaseModel):
    full_name: str
    email: str
    password: str
    district: Optional[str] = None
    department: Optional[str] = None
    zone: Optional[str] = None

class OfficerUpdate(BaseModel):
    full_name: Optional[str] = None
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
    ward: Optional[str] = None
    district: Optional[str] = None
    department: Optional[str] = None
    zone: Optional[str] = None
    notify_status_updates: Optional[bool] = True
    skills: Optional[str] = None
    availability: Optional[str] = None
    current_shift: Optional[str] = None  # FEATURE 15: shift schedule
    email_verified: Optional[bool] = False  # FEATURE 14: email verification


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
    timeout: bool = False


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


class MergeIncidentsRequest(BaseModel):
    incident_ids: List[str] = Field(..., min_length=2)

class NotificationResponse(BaseModel):
    id: str
    user_id: str
    complaint_id: Optional[str] = None
    type: str
    data: Optional[Dict[str, Any]] = None
    is_read: bool
    created_at: str

class UpdateStatusRequest(BaseModel):
    status: str
    resolution_note: Optional[str] = None

class IncidentUpdateRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="Free-text progress update visible to citizens")

class RateComplaintRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Citizen satisfaction rating (1-5)")

class BulkUpdateRequest(BaseModel):
    incident_ids: List[str] = Field(..., min_length=1, description="List of incident IDs to update")
    action: str = Field(..., pattern="^(priority_bump|post_update)$", description="Action: priority_bump or post_update")
    message: Optional[str] = Field(None, max_length=2000, description="Message for post_update action")

class UpdateComplaintRequest(BaseModel):
    description: Optional[str] = Field(None, max_length=5000, description="Updated complaint description")
    location: Optional[str] = Field(None, max_length=500, description="Updated complaint location")

class NotificationPrefsRequest(BaseModel):
    notify_status_updates: bool = Field(..., description="Opt in/out of status update notifications")

class MergeSingleRequest(BaseModel):
    target_incident_id: str = Field(..., description="Target incident ID to merge into")

class NoteUpdateRequest(BaseModel):
    note: str = Field(..., min_length=1, max_length=5000, description="Private note")

class TagsUpdateRequest(BaseModel):
    tags: List[str] = Field(..., description="List of tags")

class SkillsUpdateRequest(BaseModel):
    skills: List[str] = Field(..., description="List of skill tags")

class AvailabilityUpdateRequest(BaseModel):
    availability: str = Field(..., description="Availability status")

class VerifyEmailRequest(BaseModel):
    code: str

class WithdrawRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=2000, description="Withdrawal reason")

class CategoryCorrectRequest(BaseModel):
    category: str = Field(..., min_length=1)

class WebhookRegister(BaseModel):
    url: str
    events: List[str]

# FEATURE 2: peer review
class PeerReviewRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Peer rating 1-5")
    comment: Optional[str] = Field(None, max_length=2000)

class PeerReviewResponse(BaseModel):
    id: str
    incident_id: str
    reviewer_name: str
    rating: int
    comment: Optional[str]
    created_at: str

class PeerReviewSummaryItem(BaseModel):
    officer_id: str
    officer_name: str
    avg_peer_rating: float
    review_count: int
    citizen_avg_rating: Optional[float]

# FEATURE 5: geo heat trend
class GeoHeatTrendItem(BaseModel):
    week: int
    label: str
    hotspots: List[dict]

# FEATURE 6: FAQ chatbot
class ChatbotMessage(BaseModel):
    question: str

class ChatbotAnswer(BaseModel):
    question: str
    answer: str

# FEATURE 7: incident cost
class CostEstimate(BaseModel):
    category: str
    base_cost: float
    per_complaint_cost: float
    cluster_size: int
    estimated_total: float

# FEATURE 8: batch import
class BatchImportResult(BaseModel):
    imported: int
    duplicates: int
    failed: int
    errors: List[str]

# FEATURE 10: zone transfer
class ZoneTransferRequest(BaseModel):
    new_zone: str = Field(..., min_length=1)

# FEATURE 11: response time prediction
class ResolutionEstimate(BaseModel):
    category: str
    avg_resolution_days: float
    department_backlog: int
    estimated_days: float

# FEATURE 13: alert config
class AlertConfigItem(BaseModel):
    id: str
    exec_user_id: str
    alert_type: str
    enabled: bool
    threshold: Optional[float]
    created_at: str

class AlertConfigRequest(BaseModel):
    alert_type: str
    enabled: bool = True
    threshold: Optional[float] = None

# FEATURE 14: language stats
class LanguageStatItem(BaseModel):
    week: str
    english: int
    tamil: int
    tanglish: int
    unknown: int

# FEATURE 15: response template
class ResponseTemplateItem(BaseModel):
    id: str
    officer_id: str
    title: str
    message: str
    created_at: str

class ResponseTemplateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1, max_length=2000)

# FEATURE 18: councillor performance
class CouncillorPerformanceItem(BaseModel):
    councillor_name: str
    ward: str
    open_incidents: int
    resolved_incidents: int
    resolution_rate: float
    avg_citizen_rating: float
    sla_compliance: float

# F6: watchlist
class WatchlistRequest(BaseModel):
    incident_id: str

class WatchlistResponse(BaseModel):
    id: str
    exec_user_id: str
    incident_id: str
    created_at: str

# F9: resolution time by category
class ResolutionTimeByCategory(BaseModel):
    category: str
    avg_resolution_days: float

# F13: reassignment request
class ReassignmentRequestResponse(BaseModel):
    id: str
    incident_id: str
    requesting_officer_id: str
    requesting_officer_name: str
    reason: str
    status: str
    created_at: str

# F14: complaint subscription
class ComplaintSubscriptionRequest(BaseModel):
    complaint_id: str
    user_id: str
    created_at: str

# F19: system metrics
class SystemMetrics(BaseModel):
    active_connections: int
    redis_status: str
    redis_latency_ms: float
    db_latency_ms: float
    queue_depth: int
