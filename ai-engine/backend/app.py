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
import os
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

    # Initialize database and create tables automatically on startup.
    # This runs once per worker and is the single source of truth for
    # schema creation, demo-user seeding, and migration/backfill.
    try:
        from database import Base, engine, seed_demo_users, seed_synthetic_data
        logger.info("[STARTUP] Initializing database and auto-creating tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("[STARTUP] Database tables created/verified successfully")

        # Seed demo users idempotently
        try:
            seed_demo_users()
            logger.info("[STARTUP] Demo users ensured")
        except Exception as exc:
            logger.warning("[STARTUP] Demo users seeding skipped: %s", exc)

        # Seed synthetic data idempotently
        try:
            seed_synthetic_data()
            logger.info("[STARTUP] Synthetic data seeding completed")
        except Exception as exc:
            logger.warning("[STARTUP] Synthetic data seeding skipped: %s", exc)

        # Backfill any complaints missing user_id
        try:
            from database import backfill_complaint_user_ids
            backfill_complaint_user_ids()
        except Exception as exc:
            logger.warning("[STARTUP] Complaint backfill skipped: %s", exc)

    except Exception as e:
        logger.error("[STARTUP] Database initialization failed: %s", e)

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

# Enable CORS - restrict to configured frontend origins
ALLOWED_ORIGINS = os.environ.get("GIIPS_ALLOWED_ORIGINS", "")
if not ALLOWED_ORIGINS:
    raise RuntimeError("GIIPS_ALLOWED_ORIGINS environment variable is not set. Backend startup aborted.")
allowed_origins_list = [o.strip() for o in ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routes import classify_router, cluster_router, priority_router, dashboard_router, incident_router, complaint_router, executive_router, spatial_router, auth_router, admin_router, prediction_router, knowledge_router, decision_router, copilot_router

app.include_router(classify_router)
app.include_router(cluster_router)
app.include_router(priority_router)
app.include_router(dashboard_router)
app.include_router(incident_router)
app.include_router(complaint_router)
app.include_router(executive_router)
app.include_router(spatial_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(prediction_router)
app.include_router(knowledge_router)
app.include_router(decision_router)
app.include_router(copilot_router)


# === Request/Response Models removed: now centralized in models.py and routes.py ===


# === Helper Functions removed: duplicate logic moved to routes.py services ===


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


class FindSimilarBody(BaseModel):
    text: str
    complaints: List[Dict] = []
    threshold: float = 0.8


@app.post("/similar")
async def find_similar(body: FindSimilarBody):
    """Find similar complaints (simple keyword matching)."""
    text_words = set(body.text.lower().split()[:10])
    similar = []

    for c in body.complaints:
        ct = str(c.get('text', ''))
        ct_words = set(ct.lower().split()[:10])
        overlap = len(text_words & ct_words) / max(len(text_words), 1)

        if overlap >= body.threshold * 0.5:
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
