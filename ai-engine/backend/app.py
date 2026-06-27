"""
GIIPS FastAPI Backend Application.

Exposes REST endpoints for complaint classification, clustering,
priority scoring, and dashboard data.

Author: GIIPS AI Engine
Version: 1.0.0
"""

import json
import pickle
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import asynccontextmanager
from collections import defaultdict

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# === Configuration ===
PROJECT_ROOT = Path(__file__).parent.parent.parent
MODELS_DIR = PROJECT_ROOT / 'ai-engine' / 'models' / 'classification'
OUTPUTS_DIR = PROJECT_ROOT / 'ai-engine' / 'outputs'
DATA_DIR = PROJECT_ROOT / 'ai-engine' / 'data'

# === Global State ===
_models: Dict[str, Any] = {}


# === Model Loading ===

def load_classifier():
    """Load the trained classifier models."""
    try:
        classifier_path = MODELS_DIR / 'classifier.pkl'
        vectorizer_path = MODELS_DIR / 'vectorizer.pkl'
        encoder_path = MODELS_DIR / 'label_encoder.pkl'

        if not all(p.exists() for p in [classifier_path, vectorizer_path, encoder_path]):
            logger.warning("Model files not found, classifier will use fallback")
            return None

        with open(vectorizer_path, 'rb') as f:
            vectorizer = pickle.load(f)

        with open(classifier_path, 'rb') as f:
            classifier = pickle.load(f)

        with open(encoder_path, 'rb') as f:
            label_encoder = pickle.load(f)

        logger.info("Classification models loaded successfully")
        return {
            'vectorizer': vectorizer,
            'classifier': classifier,
            'label_encoder': label_encoder
        }
    except Exception as e:
        logger.error(f"Failed to load classifier: {e}")
        return None


# === Lifespan Management ===

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - load models on startup."""
    logger.info("[STARTUP] Initializing GIIPS Backend...")

    # Load classifier
    _models['classifier'] = load_classifier()
    if _models['classifier']:
        logger.info("[STARTUP] Classification model loaded")
    else:
        logger.warning("[STARTUP] Using fallback classifier")

    # Initialize priority engine
    try:
        from priority.priority import PriorityEngine
        _models['priority_engine'] = PriorityEngine()
        logger.info("[STARTUP] Priority engine initialized")
    except ImportError:
        # Inline priority engine
        _models['priority_engine'] = None
        logger.info("[STARTUP] Using inline priority engine")

    # Ensure outputs directory exists
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    yield

    # Cleanup
    _models.clear()
    logger.info("[SHUTDOWN] Models unloaded")


# === FastAPI App ===

app = FastAPI(
    title="GIIPS API",
    description="Governance Incident Intelligence & Prioritization System API",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Request/Response Models ===

class ClassifyRequest(BaseModel):
    """Request for complaint classification."""
    text: str = Field(..., description="Complaint text to classify")
    detail: Optional[str] = Field(None, description="Additional detail text")


class ClassifyResponse(BaseModel):
    """Response for classification."""
    predicted_category: str
    confidence: float
    top_predictions: List[Dict[str, Any]]


class ClusterRequest(BaseModel):
    """Request for clustering."""
    complaints: List[Dict[str, Any]] = Field(..., description="List of complaints")
    text_key: str = Field("text", description="Key for text field")


class ClusterResponse(BaseModel):
    """Response for clustering."""
    n_clusters: int
    n_noise: int
    cluster_assignments: List[Dict[str, Any]]


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


# === Helper Functions ===

FALLBACK_CATEGORIES = {
    'pothole': 'Road Infrastructure',
    'road': 'Road Infrastructure',
    'street': 'Road Infrastructure',
    'water': 'Water Supply',
    'pipe': 'Water Supply',
    'leak': 'Water Supply',
    'garbage': 'Waste Management',
    'waste': 'Waste Management',
    'trash': 'Waste Management',
    'light': 'Street Lighting',
    'lamp': 'Street Lighting',
    'dark': 'Street Lighting',
    'drain': 'Sanitation',
    'sewage': 'Sanitation',
    'toilet': 'Sanitation',
}

def fallback_classify(text: str) -> tuple:
    """Simple keyword-based classification fallback."""
    text_lower = text.lower()
    for keyword, category in FALLBACK_CATEGORIES.items():
        if keyword in text_lower:
            return category, 0.75
    return 'Public Works', 0.5


def calculate_priority_score(
    cluster_size: int,
    days_open: int,
    category: str,
    location_hints: List[str]
) -> Dict:
    """Calculate priority score and explanation."""
    # Category weights
    category_weights = {
        'Water Supply': 0.90,
        'Road Infrastructure': 0.85,
        'Sanitation': 0.80,
        'Waste Management': 0.65,
        'Street Lighting': 0.60,
        'Public Works': 0.50,
    }

    # Location weights
    location_weight = 0.5
    for hint in location_hints:
        hint_lower = hint.lower()
        if any(kw in hint_lower for kw in ['school', 'hospital', 'emergency']):
            location_weight = 0.95
            break
        elif any(kw in hint_lower for kw in ['market', 'transit', 'bus']):
            location_weight = 0.80
            break

    # Calculate components
    size_score = min(cluster_size / 20, 1.0) * 30
    age_score = min(days_open / 30, 1.0) * 25
    cat_score = category_weights.get(category, 0.5) * 25
    loc_score = location_weight * 20

    total_score = size_score + age_score + cat_score + loc_score

    if total_score >= 90:
        label = 'Critical'
    elif total_score >= 75:
        label = 'High'
    elif total_score >= 50:
        label = 'Medium'
    else:
        label = 'Low'

    return {
        'score': round(total_score, 1),
        'label': label,
        'factors': [
            {'name': 'cluster_size', 'value': cluster_size, 'contribution': round(size_score, 1)},
            {'name': 'age', 'value': days_open, 'contribution': round(age_score, 1)},
            {'name': 'category', 'value': category, 'contribution': round(cat_score, 1)},
            {'name': 'location', 'value': location_weight, 'contribution': round(loc_score, 1)},
        ]
    }


def group_by_similarity(complaints: List[Dict], text_key: str) -> List[List[int]]:
    """Simple text-based grouping for clustering."""
    buckets = defaultdict(list)

    for i, c in enumerate(complaints):
        text = str(c.get(text_key, '') or c.get('text', ''))
        # Extract key words for matching
        words = text.lower().split()[:5]
        key = ' '.join(words)
        buckets[key].append(i)

    # Also check for similar texts
    n = len(complaints)
    used = set()

    for i in range(n):
        if i in used:
            continue
        text_i = str(complaints[i].get(text_key, '') or complaints[i].get('text', '')).lower()
        words_i = set(text_i.split())

        for j in range(i + 1, n):
            if j in used:
                continue
            text_j = str(complaints[j].get(text_key, '') or complaints[j].get('text', '')).lower()
            words_j = set(text_j.split())

            # Jaccard similarity
            intersection = len(words_i & words_j)
            union = len(words_i | words_j)
            if union > 0 and intersection / union > 0.3:
                # Combine into same bucket
                found_key = None
                for k, v in buckets.items():
                    if i in v or j in v:
                        found_key = k
                        break
                if found_key:
                    if i not in buckets[found_key]:
                        buckets[found_key].append(i)
                    if j not in buckets[found_key]:
                        buckets[found_key].append(j)
                else:
                    buckets[f'sim_{i}'] = [i, j]
                used.add(i)
                used.add(j)

    # Convert to clusters (only groups with 2+ items)
    clusters = [indices for indices in buckets.values() if len(indices) >= 2]
    return clusters


# === API Endpoints ===

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "GIIPS API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": ["/classify", "/cluster", "/priority", "/dashboard", "/health"]
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "models_loaded": {
            "classifier": _models.get('classifier') is not None
        },
        "timestamp": datetime.now().isoformat()
    }


@app.post("/classify", response_model=ClassifyResponse)
async def classify(request: ClassifyRequest):
    """Classify a complaint into a category."""
    combined_text = request.text
    if request.detail:
        combined_text += f" {request.detail}"

    classifier_data = _models.get('classifier')

    if classifier_data:
        try:
            vectorizer = classifier_data['vectorizer']
            classifier = classifier_data['classifier']
            label_encoder = classifier_data['label_encoder']

            # Vectorize
            X = vectorizer.transform([combined_text])

            # Predict
            y_pred = classifier.predict(X)[0]
            y_proba = classifier.predict_proba(X)[0]

            # Decode
            category = label_encoder.inverse_transform([y_pred])[0]
            confidence = float(y_proba[y_pred])

            # Top predictions
            top_indices = np.argsort(y_proba)[::-1][:5]
            top_predictions = [
                {
                    "category": label_encoder.inverse_transform([idx])[0],
                    "confidence": float(y_proba[idx])
                }
                for idx in top_indices
            ]

            return ClassifyResponse(
                predicted_category=category,
                confidence=confidence,
                top_predictions=top_predictions
            )
        except Exception as e:
            logger.error(f"Classification error: {e}")

    # Fallback
    category, confidence = fallback_classify(combined_text)
    return ClassifyResponse(
        predicted_category=category,
        confidence=confidence,
        top_predictions=[{"category": category, "confidence": confidence}]
    )


@app.post("/cluster", response_model=ClusterResponse)
async def cluster(request: ClusterRequest):
    """Cluster complaints into duplicate incidents."""
    if not request.complaints:
        raise HTTPException(status_code=400, detail="No complaints provided")

    clusters = group_by_similarity(request.complaints, request.text_key)

    # Build assignments
    all_indices = list(range(len(request.complaints)))
    assigned = set()
    for cluster in clusters:
        assigned.update(cluster)

    assignments = []
    cluster_id = 0
    for cluster in clusters:
        for idx in cluster:
            assignments.append({
                "complaint_id": request.complaints[idx].get('id', idx),
                "cluster_label": cluster_id,
                "is_noise": False
            })
        cluster_id += 1

    # Noise points
    for idx in all_indices:
        if idx not in assigned:
            assignments.append({
                "complaint_id": request.complaints[idx].get('id', idx),
                "cluster_label": -1,
                "is_noise": True
            })

    return ClusterResponse(
        n_clusters=len(clusters),
        n_noise=len(assigned) - sum(len(c) for c in clusters) + len(all_indices) - len(assigned),
        cluster_assignments=assignments
    )


@app.post("/priority", response_model=PriorityResponse)
async def calculate_priority(request: PriorityRequest):
    """Calculate priority score for an incident."""
    try:
        first_date = datetime.fromisoformat(request.first_complaint_date.split('T')[0])
        days_open = max(0, (datetime.now() - first_date).days)
    except (ValueError, TypeError):
        days_open = 0

    result = calculate_priority_score(
        cluster_size=request.cluster_size,
        days_open=days_open,
        category=request.category,
        location_hints=request.location_hints
    )

    # Build explanation
    explanation = f"Incident with {request.cluster_size} complaints, "
    explanation += f"open for {days_open} days. "
    explanation += f"Category: {request.category}. "
    if request.location_hints:
        explanation += f"Location: {', '.join(request.location_hints[:2])}."

    return PriorityResponse(
        incident_id=request.incident_id,
        priority_score=result['score'],
        priority_label=result['label'],
        factors=result['factors'],
        explanation=explanation
    )


@app.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard():
    """Get dashboard summary data."""
    # Try to load saved data
    data_file = OUTPUTS_DIR / 'dashboard_data.json'
    if data_file.exists():
        try:
            with open(data_file, 'r') as f:
                data = json.load(f)
            return DashboardResponse(**data)
        except Exception:
            pass

    # Default sample data
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
async def find_similar(text: str, complaints: List[Dict], threshold: float = 0.8):
    """Find similar complaints (simple keyword matching)."""
    text_words = set(text.lower().split()[:10])
    similar = []

    for c in complaints:
        ct = str(c.get('text', ''))
        ct_words = set(ct.lower().split()[:10])
        overlap = len(text_words & ct_words) / max(len(text_words), 1)

        if overlap >= threshold * 0.5:
            similar.append({
                "id": c.get('id'),
                "text": ct[:100],
                "similarity": round(overlap, 3)
            })

    return {"similar_complaints": similar[:5]}


# === Main Entry Point ===

if __name__ == '__main__':
    import uvicorn

    print("\n" + "=" * 60)
    print("GIIPS FastAPI Backend")
    print("=" * 60)
    print("\nStarting server at http://localhost:8000")
    print("API docs: http://localhost:8000/docs")

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
