"""
GIIPS FastAPI Backend Application.

Exposes REST endpoints for complaint classification, clustering,
priority scoring, and dashboard data.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from classification.train import ComplaintClassifier
from clustering.cluster import ComplaintClusterer
from priority.priority import PriorityEngine, PriorityResult


# Global model instances
_models: Dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - load models on startup."""
    print("[STARTUP] Loading AI models...")

    models_dir = Path(__file__).parent.parent / 'models'

    # Try to load classification model
    classification_dir = models_dir / 'classification'
    if classification_dir.exists() and (classification_dir / 'classifier.pkl').exists():
        try:
            _models['classifier'] = ComplaintClassifier.load(classification_dir)
            print("[STARTUP] Classification model loaded")
        except Exception as e:
            print(f"[WARNING] Could not load classification model: {e}")

    # Initialize clusterer
    _models['clusterer'] = ComplaintClusterer(eps=0.3, min_samples=2)
    print("[STARTUP] Clustering model initialized")

    # Initialize priority engine
    _models['priority_engine'] = PriorityEngine()
    print("[STARTUP] Priority engine initialized")

    yield

    # Cleanup
    _models.clear()
    print("[SHUTDOWN] Models unloaded")


app = FastAPI(
    title="GIIPS API",
    description="Governance Incident Intelligence & Prioritization System API",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Request/Response Models ===

class ClassifyRequest(BaseModel):
    """Request for single complaint classification."""
    text: str = Field(..., description="Complaint text to classify")
    detail: Optional[str] = Field(None, description="Additional detail text")


class ClassifyResponse(BaseModel):
    """Response for classification request."""
    predicted_category: str
    confidence: float
    top_predictions: List[Dict[str, Any]]


class ClusterRequest(BaseModel):
    """Request for clustering complaints."""
    complaints: List[Dict[str, Any]] = Field(..., description="List of complaints to cluster")
    text_key: str = Field("text", description="Key for text field")
    eps: Optional[float] = Field(0.3, description="DBSCAN epsilon parameter")


class ClusterResponse(BaseModel):
    """Response for clustering request."""
    n_clusters: int
    n_noise: int
    cluster_assignments: List[Dict[str, Any]]
    cluster_details: Dict[str, Any]


class PriorityRequest(BaseModel):
    """Request for priority calculation."""
    incident_id: str
    cluster_size: int
    first_complaint_date: str
    last_complaint_date: str
    category: str
    location_hints: List[str] = []


class PriorityResponse(BaseModel):
    """Response for priority calculation."""
    incident_id: str
    priority_score: float
    priority_label: str
    factors: List[Dict[str, Any]]
    explanation: str


class DashboardResponse(BaseModel):
    """Response for dashboard data."""
    total_complaints: int
    unique_incidents: int
    workload_reduction: float
    critical_incidents: int
    high_priority_incidents: int
    category_distribution: List[Dict[str, Any]]
    priority_distribution: Dict[str, int]


# === API Endpoints ===

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "GIIPS API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": [
            "/classify",
            "/cluster",
            "/priority",
            "/dashboard",
            "/health"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    loaded = {
        "classifier": "classifier" in _models,
        "clusterer": "clusterer" in _models,
        "priority_engine": "priority_engine" in _models
    }

    return {
        "status": "healthy" if all(loaded.values()) else "degraded",
        "models_loaded": loaded,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/classify", response_model=ClassifyResponse)
async def classify_complaint(request: ClassifyRequest):
    """
    Classify a single complaint into a category.

    Uses the trained TF-IDF + Logistic Regression classifier.
    """
    classifier = _models.get('classifier')

    if classifier is None:
        # Fallback: simple keyword matching
        return await _fallback_classify(request)

    # Combine text fields
    combined_text = request.text
    if request.detail:
        combined_text += f" {request.detail}"

    try:
        prediction = classifier.predict([combined_text])[0]
        probabilities = classifier.predict_proba([combined_text])[0]

        # Get top 5 predictions
        import numpy as np
        top_indices = np.argsort(probabilities)[::-1][:5]
        top_predictions = [
            {
                "category": classifier.classes_[idx],
                "confidence": float(probabilities[idx])
            }
            for idx in top_indices
        ]

        confidence = float(probabilities[classifier.classes_.tolist().index(prediction)])

        return ClassifyResponse(
            predicted_category=prediction,
            confidence=confidence,
            top_predictions=top_predictions
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")


async def _fallback_classify(request: ClassifyRequest) -> ClassifyResponse:
    """Fallback classification when model not loaded."""
    # Simple keyword matching
    text_lower = request.text.lower()
    category_scores = {
        'Road Infrastructure': any(kw in text_lower for kw in ['pothole', 'road', 'street', 'pavement', 'speed breaker']),
        'Water Supply': any(kw in text_lower for kw in ['water', 'pipe', 'leak', 'supply', 'tap']),
        'Waste Management': any(kw in text_lower for kw in ['garbage', 'waste', 'trash', 'rubbish', 'bin']),
        'Sanitation': any(kw in text_lower for kw in ['drain', 'sewage', 'toilet', 'sanitation']),
        'Street Lighting': any(kw in text_lower for kw in ['light', 'lamp', 'street light', 'bulb']),
    }

    predicted = 'Public Works'
    max_conf = 0.5

    for cat, match in category_scores.items():
        if match:
            predicted = cat
            max_conf = 0.8
            break

    return ClassifyResponse(
        predicted_category=predicted,
        confidence=max_conf,
        top_predictions=[{"category": predicted, "confidence": max_conf}]
    )


@app.post("/cluster", response_model=ClusterResponse)
async def cluster_complaints(request: ClusterRequest):
    """
    Cluster complaints into incidents using semantic similarity.

    Uses SentenceTransformer embeddings and DBSCAN clustering.
    """
    clusterer = _models.get('clusterer')

    if not request.complaints:
        raise HTTPException(status_code=400, detail="No complaints provided")

    # Use fallback if clusterer not properly initialized
    if clusterer is None:
        return await _fallback_cluster(request)

    try:
        # Update clusterer params if specified
        if request.eps:
            clusterer.eps = request.eps

        # Run clustering
        result = clusterer.cluster_with_ward_separation(
            request.complaints,
            text_key=request.text_key
        )

        # Build cluster assignments
        assignments = []
        for i, label in enumerate(result.get('labels', [])):
            assignments.append({
                "complaint_id": request.complaints[i].get('id', i),
                "cluster_label": int(label),
                "is_noise": label == -1
            })

        # Build cluster details
        cluster_details = {}
        for label, members in result.get('clusters', {}).items():
            cluster_details[str(label)] = {
                "size": len(members),
                "sample_complaints": [m.get('text', '')[:100] for m in members[:3]]
            }

        return ClusterResponse(
            n_clusters=result['n_clusters'],
            n_noise=result['n_noise'],
            cluster_assignments=assignments,
            cluster_details=cluster_details
        )

    except Exception as e:
        # Return fallback on error
        return await _fallback_cluster(request)


async def _fallback_cluster(request: ClusterRequest) -> ClusterResponse:
    """Simple fallback clustering when model unavailable."""
    # Group by similar text (first 50 chars as simple bucketing)
    from collections import defaultdict

    buckets = defaultdict(list)
    assignments = []

    for i, complaint in enumerate(request.complaints):
        text = complaint.get(request.text_key, '') or complaint.get('text', '')
        bucket_key = text[:50].lower() if text else 'empty'
        buckets[bucket_key].append(i)

    # Convert to clusters
    cluster_labels = {}
    cluster_id = 0

    for key, indices in buckets.items():
        if len(indices) >= 2:  # Only create clusters for duplicates
            for idx in indices:
                cluster_labels[idx] = cluster_id
            cluster_id += 1
        else:
            for idx in indices:
                cluster_labels[idx] = -1  # Noise

    assignments = [
        {
            "complaint_id": request.complaints[i].get('id', i),
            "cluster_label": cluster_labels.get(i, -1),
            "is_noise": cluster_labels.get(i, -1) == -1
        }
        for i in range(len(request.complaints))
    ]

    return ClusterResponse(
        n_clusters=cluster_id,
        n_noise=sum(1 for a in assignments if a['is_noise']),
        cluster_assignments=assignments,
        cluster_details={}
    )


@app.post("/priority", response_model=PriorityResponse)
async def calculate_priority(request: PriorityRequest):
    """
    Calculate priority score for an incident.

    Uses explainable scoring based on cluster size, age,
    category severity, and location importance.
    """
    engine = _models.get('priority_engine')

    if engine is None:
        engine = PriorityEngine()

    try:
        result = engine.compute(
            incident_id=request.incident_id,
            cluster_size=request.cluster_size,
            first_complaint_date=request.first_complaint_date,
            last_complaint_date=request.last_complaint_date,
            category=request.category,
            location_hints=request.location_hints
        )

        return PriorityResponse(
            incident_id=result.incident_id,
            priority_score=result.priority_score,
            priority_label=result.priority_label,
            factors=[{
                "name": f.name,
                "raw_value": f.raw_value,
                "normalized_value": f.normalized_value,
                "weight": f.weight,
                "contribution": f.contribution,
                "description": f.description
            } for f in result.factors],
            explanation=result.explanation
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Priority calculation failed: {str(e)}")


@app.post("/batch_priority")
async def calculate_batch_priority(incidents: List[PriorityRequest]):
    """Calculate priority for multiple incidents."""
    engine = _models.get('priority_engine') or PriorityEngine()

    results = []
    for incident in incidents:
        result = engine.compute(
            incident_id=incident.incident_id,
            cluster_size=incident.cluster_size,
            first_complaint_date=incident.first_complaint_date,
            last_complaint_date=incident.last_complaint_date,
            category=incident.category,
            location_hints=incident.location_hints
        )
        results.append(result.to_dict())

    return {"results": results, "count": len(results)}


@app.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard_data():
    """
    Get dashboard summary statistics.

    Returns key metrics for the main dashboard view.
    """
    # Try to load saved data
    outputs_dir = Path(__file__).parent.parent / 'outputs'
    data_file = outputs_dir / 'dashboard_data.json'

    if data_file.exists():
        try:
            with open(data_file, 'r') as f:
                data = json.load(f)
            return DashboardResponse(**data)
        except Exception:
            pass

    # Return sample data if no saved data
    return DashboardResponse(
        total_complaints=100,
        unique_incidents=15,
        workload_reduction=85.0,
        critical_incidents=3,
        high_priority_incidents=5,
        category_distribution=[
            {"category": "Road Infrastructure", "count": 30},
            {"category": "Water Supply", "count": 25},
            {"category": "Waste Management", "count": 20},
            {"category": "Street Lighting", "count": 15},
            {"category": "Sanitation", "count": 10}
        ],
        priority_distribution={
            "Critical": 3,
            "High": 5,
            "Medium": 4,
            "Low": 3
        }
    )


@app.post("/similar")
async def find_similar_complaints(
    text: str,
    existing_complaints: List[Dict[str, Any]],
    threshold: float = 0.8
):
    """
    Find similar complaints for duplicate detection.

    Uses semantic similarity to find potential duplicates.
    """
    clusterer = _models.get('clusterer')

    if clusterer is None:
        # Simple keyword fallback
        text_keywords = set(text.lower().split()[:5])
        similar = []
        for complaint in existing_complaints:
            ct = complaint.get('text', '').lower()
            ct_keywords = set(ct.split()[:5])
            overlap = len(text_keywords & ct_keywords) / max(len(text_keywords), 1)
            if overlap >= threshold * 0.5:
                similar.append({**complaint, "similarity": overlap})
        return {"similar_complaints": similar[:5]}

    try:
        duplicates = clusterer.find_duplicates(text, existing_complaints, threshold=threshold)
        return {"similar_complaints": duplicates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Similarity search failed: {str(e)}")


if __name__ == '__main__':
    import uvicorn

    print("\n" + "=" * 60)
    print("GIIPS FastAPI Backend")
    print("=" * 60)
    print("\nStarting server at http://localhost:8000")
    print("API docs: http://localhost:8000/docs")
    print("\n")

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
