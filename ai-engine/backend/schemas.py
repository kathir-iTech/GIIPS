"""
Pydantic schemas for data validation and serialization.

Contains schemas for request validation and response formatting
for both Complaints and Incidents, supporting both Pydantic v1 and v2.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# === New Submission Schemas ===

class ComplaintCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Short title of the complaint")
    description: str = Field(..., min_length=1, max_length=5000, description="Detailed description of the issue")
    location: str = Field(..., min_length=1, max_length=500, description="Specific physical location or address")
    ward: str = Field(..., min_length=1, max_length=100, description="Municipal ward identifier")
    image_path: Optional[str] = Field(None, description="Optional file path to uploaded image")

class ComplaintSubmissionResponse(BaseModel):
    complaintId: str
    incidentId: str
    predictedCategory: str
    priority: str
    confidence: float
    duplicate: bool
    message: str
    processing_time_ms: float = 0.0


class ComplaintBase(BaseModel):
    """Base fields shared across all Complaint schemas."""
    title: str = Field(..., description="Short title of the complaint", min_length=1)
    description: str = Field(..., description="Detailed description of the issue", min_length=1)
    location: str = Field(..., description="Specific physical location or address", min_length=1)
    ward: str = Field(..., description="Municipal ward identifier", min_length=1)
    image_path: Optional[str] = Field(None, description="Optional file path to uploaded image")
    predicted_category: Optional[str] = Field(None, description="AI-predicted category")
    confidence: Optional[float] = Field(None, description="AI classification confidence score", ge=0.0, le=1.0)
    priority: Optional[str] = Field(None, description="Priority classification (Critical, High, Medium, Low)")
    incident_id: Optional[str] = Field(None, description="Optional foreign key linking to an aggregated Incident")


class ComplaintResponse(ComplaintBase):
    """Schema returned in API responses for Complaint data."""
    id: str
    created_at: datetime
    similarity_score: Optional[float] = None
    merge_reason: Optional[str] = None

    class Config:
        # Pydantic v1 support
        orm_mode = True
        # Pydantic v2 support
        from_attributes = True

class PriorityHistoryResponse(BaseModel):
    id: str
    incident_id: str
    old_score: float
    new_score: float
    reason: str
    changed_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True

# === Incident Schemas ===

class IncidentBase(BaseModel):
    """Base fields shared across all Incident schemas."""
    incident_number: str = Field(..., description="Unique human-readable incident ID, e.g. INC-2024-0001")
    category: str = Field(..., description="Unified municipal category for the incident cluster")
    ward: str = Field(..., description="Municipal ward where the incident resides")
    cluster_size: int = Field(1, description="Number of grouped citizen complaints", ge=1)
    priority_score: float = Field(0.0, description="Calculated priority score (0-100)", ge=0.0, le=100.0)
    priority_label: str = Field("Low", description="Priority level (Critical, High, Medium, Low)")
    summary: Optional[str] = Field(None, description="AI-generated summary of the incident")
    status: str = Field("open", description="Resolution status (open, in-progress, closed)")


class IncidentCreate(IncidentBase):
    """Schema used when initializing a new aggregated Incident."""
    id: str = Field(..., description="Unique UUID identifier for the incident")


class IncidentResponse(IncidentBase):
    """Schema returned in API responses for Incident data (including linked complaints)."""
    id: str
    created_at: datetime
    complaints: List[ComplaintResponse] = []
    priority_history: List[PriorityHistoryResponse] = []

    class Config:
        # Pydantic v1 support
        orm_mode = True
        # Pydantic v2 support
        from_attributes = True
