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
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import asynccontextmanager
from collections import defaultdict

import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import text

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
    # schema creation and migration/backfill.
    try:
        from database import Base, engine
        logger.info("[STARTUP] Initializing database and auto-creating tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("[STARTUP] Database tables created/verified successfully")

        # Run Alembic migrations
        try:
            import subprocess
            result = subprocess.run(
                ["alembic", "upgrade", "head"],
                capture_output=True, text=True, check=False
            )
            if result.returncode == 0:
                logger.info("[MIGRATION] Alembic upgrade succeeded:\n%s", result.stdout)
            else:
                logger.warning("[MIGRATION] Alembic upgrade had issues (exit %d):\n%s\n%s",
                               result.returncode, result.stdout, result.stderr)
        except Exception as exc:
            logger.warning("[MIGRATION] Alembic upgrade skipped: %s", exc)

        # Migration: fix district for government users from old Chennai data
        try:
            from database import User, Base
            from sqlalchemy.orm import sessionmaker
            FixSession = sessionmaker(bind=engine)
            with FixSession() as fix_db:
                fix_db.query(User).filter(
                    User.email.in_(["mla1@giips.gov.in", "collector1@giips.gov.in",
                                    "councillor1@giips.gov.in", "councillor2@giips.gov.in",
                                    "councillor3@giips.gov.in", "councillor4@giips.gov.in",
                                    "councillor5@giips.gov.in", "councillor6@giips.gov.in",
                                    "councillor7@giips.gov.in", "councillor8@giips.gov.in",
                                    "commr-north@giips.gov.in", "commr-south@giips.gov.in",
                                    "commr-east@giips.gov.in", "commr-west@giips.gov.in",
                                    "commr-central@giips.gov.in"]),
                    User.district != "Coimbatore"
                ).update({"district": "Coimbatore"}, synchronize_session=False)
                fix_db.commit()
                logger.info("[MIGRATION] Corrected district to Coimbatore for government users")
        except Exception as exc:
            logger.warning("[MIGRATION] District fix skipped: %s", exc)

        # Seed demo users (idempotent: skips users whose email already exists)
        try:
            from database import seed_demo_users
            seed_demo_users()
        except Exception as exc:
            logger.warning("[STARTUP] Demo user seeding skipped: %s", exc)

        # Backfill ward distribution and incident linkage for existing complaints
        try:
            from database import backfill_wards_and_incidents
            backfill_wards_and_incidents()
        except Exception as exc:
            logger.warning("[STARTUP] Backfill skipped: %s", exc)

        # Top-up wards: ensure every ward has at least 50 complaints
        try:
            from database import topup_wards
            topup_wards(min_per_ward=50)
        except Exception as exc:
            logger.warning("[STARTUP] Ward top-up skipped: %s", exc)

        # Seed default executive account
        try:
            from database import seed_default_executive
            seed_default_executive()
        except Exception as exc:
            logger.warning("[STARTUP] Default executive seeding skipped: %s", exc)

        # Backfill any complaints missing user_id
        try:
            from database import backfill_complaint_user_ids
            backfill_complaint_user_ids()
        except Exception as exc:
            logger.warning("[STARTUP] Complaint backfill skipped: %s", exc)

        # Migrate old department names to new standardised names
        try:
            from database import migrate_old_departments
            migrate_old_departments()
        except Exception as exc:
            logger.warning("[STARTUP] Department migration skipped: %s", exc)

        # Backfill officer departments — ensures _notify_department_officers works
        try:
            from database import backfill_officer_departments
            backfill_officer_departments()
        except Exception as exc:
            logger.warning("[STARTUP] Officer department backfill skipped: %s", exc)

        # Backfill status_changed_at for existing incidents (set to created_at)
        try:
            from database import SessionLocal, Incident
            with SessionLocal() as backfill_db:
                count = backfill_db.query(Incident).filter(Incident.status_changed_at.is_(None)).update(
                    {Incident.status_changed_at: Incident.created_at},
                    synchronize_session=False
                )
                if count:
                    backfill_db.commit()
                    logger.info("[BACKFILL] Set status_changed_at = created_at for %d incidents", count)
        except Exception as exc:
            logger.warning("[BACKFILL] status_changed_at backfill skipped: %s", exc)

    except Exception as e:
        logger.error("[STARTUP] Database initialization failed: %s", e)

    # Ensure outputs directory exists
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    # Log S3 storage availability
    try:
        from storage import S3Storage
        s3 = S3Storage()
        logger.info("[STARTUP] S3 storage available=%s (endpoint=%s, bucket=%s, key_id_set=%s)",
                    s3.available, s3.endpoint_url, s3.bucket,
                    bool(os.environ.get("S3_ACCESS_KEY_ID")))
    except Exception as e:
        logger.warning("[STARTUP] S3 storage check failed: %s", e)

    # Initialize Redis pool for arq job queue
    try:
        from job_queue import init_redis_pool, close_redis_pool
        await init_redis_pool()
        logger.info("[STARTUP] Redis pool initialized for job queue")
    except Exception as e:
        logger.warning("[STARTUP] Redis pool init skipped: %s", e)

    # Start background SLA auto-escalation task (runs every 6 hours)
    async def _auto_escalate_loop():
        """Periodically check and auto-escalate stale incidents."""
        while True:
            try:
                from database import SessionLocal
                from routes import auto_escalate_aging_incidents
                from fastapi import Request
                # Create a minimal request stub — auto-escalate doesn't use request fields
                db = SessionLocal()
                try:
                    result = await auto_escalate_aging_incidents(db)
                    msg = result.get("message", "")
                    if "No incidents" not in msg:
                        logger.info("[SLA-AUTO-ESCALATE] %s", msg)
                finally:
                    db.close()
            except Exception as exc:
                logger.warning("[SLA-AUTO-ESCALATE] Cycle failed: %s", exc)
            await asyncio.sleep(21600)  # 6 hours

    task = asyncio.create_task(_auto_escalate_loop())
    logger.info("[STARTUP] SLA auto-escalation background task started (interval: 6h)")

    async def send_verification_reminders():
        while True:
            try:
                from database import SessionLocal, Incident, Complaint, Notification
                db = SessionLocal()
                now = datetime.utcnow()
                three_days_ago = now - timedelta(days=6)
                six_days_ago = now - timedelta(days=3)
                reminders = db.query(Incident).filter(
                    Incident.status == 'pending_verification',
                    Incident.status_changed_at >= three_days_ago,
                    Incident.status_changed_at <= six_days_ago
                ).all()
                for inc in reminders:
                    days_left = 7 - (now - inc.status_changed_at).days
                    complaint = db.query(Complaint).filter(Complaint.incident_id == inc.id).first()
                    if complaint and complaint.user_id:
                        existing = db.query(Notification).filter(
                            Notification.user_id == complaint.user_id,
                            Notification.type == 'verification_reminder',
                            Notification.complaint_id == complaint.id
                        ).first()
                        if not existing:
                            notif = Notification(
                                id=str(uuid.uuid4()),
                                user_id=complaint.user_id, complaint_id=complaint.id,
                                type='verification_reminder',
                                data=json.dumps({"incident_id": inc.id, "days_left": days_left, "message": f"Please verify your resolved complaint — it will auto-close in {days_left} days."})
                            )
                            db.add(notif)
                db.commit()
                db.close()
            except Exception as e:
                logger.error(f"Verification reminder task error: {e}")
            await asyncio.sleep(43200)

    task2 = asyncio.create_task(send_verification_reminders())
    logger.info("[STARTUP] Verification reminder background task started (interval: 12h)")

    # Start background auto-close task for stale pending_verification incidents (runs daily)
    async def _auto_close_loop():
        while True:
            try:
                from database import SessionLocal, Incident, AuditLog
                from datetime import timedelta
                db = SessionLocal()
                try:
                    seven_days_ago = datetime.utcnow() - timedelta(days=7)
                    stale = db.query(Incident).filter(
                        Incident.status == 'pending_verification',
                        Incident.status_changed_at <= seven_days_ago
                    ).all()
                    for inc in stale:
                        inc.status = 'closed'
                        inc.status_changed_at = datetime.utcnow()
                        audit = AuditLog(
                            id=str(uuid.uuid4()),
                            user_id='system',
                            user_email='system',
                            role='System',
                            action='auto_close',
                            target=inc.id,
                            details="Auto-closed after 7 days in pending_verification (citizen did not verify)",
                            status='success'
                        )
                        db.add(audit)
                    db.commit()
                    if stale:
                        logger.info("[AUTO-CLOSE] Closed %d stale pending_verification incidents", len(stale))
                finally:
                    db.close()
            except Exception as exc:
                logger.warning("[AUTO-CLOSE] Cycle failed: %s", exc)
            await asyncio.sleep(86400)

    task3 = asyncio.create_task(_auto_close_loop())
    logger.info("[STARTUP] Auto-close background task started (interval: 24h)")

    yield

    # Cleanup: cancel the background tasks on shutdown
    task.cancel()
    task2.cancel()
    task3.cancel()
    try:
        await task
        await task2
        await task3
    except asyncio.CancelledError:
        pass

    # Cleanup
    _models.clear()
    logger.info("[SHUTDOWN] Models unloaded")
    try:
        await close_redis_pool()
        logger.info("[SHUTDOWN] Redis pool closed")
    except Exception:
        pass


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
    logging.warning("GIIPS_ALLOWED_ORIGINS not set — defaulting to https://giips.vercel.app. Set this env var in production.")
    ALLOWED_ORIGINS = "https://giips.vercel.app"
allowed_origins_list = [o.strip() for o in ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === CSRF Protection: Origin/Referer header check ===
# With SameSite=None, the auth cookie is sent on all cross-origin POSTs.
# The Origin header is set by the browser and cannot be spoofed from JS,
# making this a simple and effective CSRF defense. No frontend changes needed.
# Also allows same-origin requests (e.g. Swagger UI at the backend's own URL).

@app.middleware("http")
async def csrf_origin_check(request: Request, call_next):
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        path = request.url.path
        exempt_prefixes = ("/docs", "/redoc", "/openapi.json", "/health", "/", "/track/", "/public/")
        if path.startswith(exempt_prefixes):
            return await call_next(request)

        origin = request.headers.get("origin")
        referer = request.headers.get("referer")

        # Same-origin check — allow requests from the backend itself (Swagger UI, etc.)
        host = request.headers.get("host", "")
        protocol = request.url.scheme
        backend_origin = f"{protocol}://{host}"

        origin_valid = False
        if origin:
            origin_stripped = origin.rstrip("/")
            if origin_stripped == backend_origin.rstrip("/"):
                origin_valid = True
            else:
                for ao in allowed_origins_list:
                    if origin_stripped == ao.rstrip("/"):
                        origin_valid = True
                        break
        elif referer:
            for ao in allowed_origins_list:
                if referer.startswith(ao.rstrip("/")):
                    origin_valid = True
                    break
        else:
            # No Origin AND no Referer — non-browser client (curl/Postman/etc.)
            logger.warning("CSRF origin check: no Origin or Referer header (non-browser client), allowing request: method=%s path=%s",
                           request.method, path)
            origin_valid = True

        if not origin_valid:
            logger.warning("CSRF origin check failed: method=%s path=%s origin=%s referer=%s",
                           request.method, path, origin, referer)
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF check failed: request must include a valid Origin or Referer header"}
            )

    return await call_next(request)


from routes import classify_router, cluster_router, priority_router, dashboard_router, incident_router, complaint_router, executive_router, spatial_router, auth_router, admin_router, prediction_router, knowledge_router, decision_router, copilot_router, notifications_router, debug_router, public_router, ws_router, search_router

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
app.include_router(notifications_router)
app.include_router(debug_router)
app.include_router(public_router)
app.include_router(ws_router)
app.include_router(search_router)


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
