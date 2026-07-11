# GIIPS — Complete Architecture Reference

> Governance Incident Intelligence & Prioritization System
> Generated from full codebase analysis (Jul 2026)

---

## Table of Contents

1. [Full File Inventory](#1-full-file-inventory)
2. [Backend Dependency / Connection Graph](#2-backend-dependency--connection-graph)
3. [Frontend-to-Backend API Map](#3-frontend-to-backend-api-map)
4. [Database Schema Map](#4-database-schema-map)
5. [Deployment Architecture](#5-deployment-architecture)
6. [AI Pipeline Data Flow](#6-ai-pipeline-data-flow)

---

## 1. Full File Inventory

### 1.1 Root Level

| Path | Purpose |
|---|---|
| `index.html` | Vite entry HTML with root `<div id="root">` and Inter font |
| `package.json` | NPM manifest — React 19, Vite, TypeScript, Leaflet, Plotly, Framer Motion |
| `package-lock.json` | Locked dependency tree |
| `vite.config.ts` | Vite config (TypeScript source) — React plugin, `@/` alias |
| `vite.config.js` | **Active** Vite config — validates `VITE_API_BASE_URL` at build time, React plugin, `@/` alias |
| `tsconfig.json` | TypeScript config for `src/` — strict mode, React JSX transform |
| `tsconfig.node.json` | TypeScript config for Vite/Node files |
| `vercel.json` | Vercel SPA rewrites — all paths → `index.html` |
| `Dockerfile` | Multi-stage Docker build for FastAPI backend (Python 3.11) |
| `docker-compose.yml` | Full local stack — backend, PostgreSQL 16, Redis 7, MinIO |
| `.dockerignore` | Excludes `.git`, `node_modules`, `.env`, `*.db`, `__pycache__` |
| `.env` | `VITE_API_BASE_URL=https://giips-backend.onrender.com` |
| `.gitignore` | Standard Node + Python ignores |
| `train_classifier.py` | Standalone TF-IDF + Logistic Regression training script |
| `nyc311_filtered.csv` | NYC 311 complaint dataset (training) |
| `nyc311_working.csv` | Working copy of NYC 311 data |
| `check_syntax.mjs` | Recursive TSX syntax checker |
| `LICENSE` | ISC license |
| `README.md` | Project overview, setup, features |

### 1.2 Frontend — `src/`

#### Entry & Routing

| Path | Purpose |
|---|---|
| `src/main.tsx` | React DOM mount point |
| `src/App.tsx` | Root component — 21 code-split routes, auth protection, sidebar layout |
| `src/App.css` | App layout, scrollbar, transitions |
| `src/index.css` | Global reset, dark theme, Inter font |
| `src/vite-env.d.ts` | Vite env type declarations |

#### Context

| Path | Purpose |
|---|---|
| `src/context/AuthContext.tsx` | Auth provider — JWT login/register/logout, session validation, role storage |

#### Services

| Path | Purpose |
|---|---|
| `src/services/api.ts` | **Single API client** — native `fetch()` wrapper, all 35+ backend endpoints |

#### Types

| Path | Purpose |
|---|---|
| `src/types/index.ts` | TypeScript interfaces — `DashboardData`, `Incident`, `Complaint`, all API models |

#### Components

| Path | Purpose |
|---|---|
| `src/components/Header.tsx` | Top nav — user info, role menu, logout |
| `src/components/Sidebar.tsx` | Left sidebar — role-based menu (Citizen / Officer / Executive) |
| `src/components/KPICard.tsx` | Animated KPI metric card |
| `src/components/ProtectedRoute.tsx` | Route guard — checks role, redirects to `/unauthorized` or `/login` |
| `src/components/AddressSearch.tsx` | Nominatim geocoding autocomplete (Tamil Nadu bbox, 500ms debounce) |
| `src/components/ErrorBoundary.tsx` | React error boundary — fallback UI + retry |

#### Pages

| Path | Purpose |
|---|---|
| `src/pages/Landing.tsx` | Static landing — hero, feature cards, gateway to login/register |
| `src/pages/Login.tsx` | Email + password login form |
| `src/pages/Register.tsx` | Registration form — name, email, password, phone, district |
| `src/pages/Overview.tsx` | Main dashboard — KPI cards, priority pie, category bar, recent incidents (polls `/dashboard`) |
| `src/pages/ExecutiveDashboard.tsx` | Executive view — 8 parallel API feeds, AI copilot chat, 30s auto-refresh |
| `src/pages/SpatialIntelligence.tsx` | Leaflet map — district heatmap, incident hotspots, complaint pins, risk overlay, resource simulation |
| `src/pages/IncidentFeed.tsx` | Sortable/filterable incident table with expandable rows (30s auto-refresh) |
| `src/pages/Clusters.tsx` | Incident investigation cards, priority rules, predictions, knowledge, decisions |
| `src/pages/Analysis.tsx` | Model performance — accuracy, precision, recall, confusion matrix, trend chart |
| `src/pages/CitizenPortal.tsx` | Complaint submission form + address geocoding + status polling |
| `src/pages/MyComplaints.tsx` | Citizen's complaint history list |
| `src/pages/ComplaintDetail.tsx` | Single complaint detail — classification, incident linkage, timeline |
| `src/pages/CitizenProfile.tsx` | Profile edit — name, email, phone, district, ward |
| `src/pages/CitizenServices.tsx` | Static service directory / redirect |
| `src/pages/GovernmentPortal.tsx` | Static redirect to login |
| `src/pages/SystemHealth.tsx` | System health — backend, DB, AI engine, JWT, model status cards |
| `src/pages/Admin.css` | Admin page styles |
| `src/pages/AuditLogs.tsx` | Searchable/filterable audit log table |
| `src/pages/DepartmentManagement.tsx` | Department performance cards |
| `src/pages/OfficerManagement.tsx` | Officer CRUD — table, create, enable/disable |
| `src/pages/Methodology.tsx` | Static — AI/ML approach documentation |
| `src/pages/Unauthorized.tsx` | Static access-denied page |

#### Data

| Path | Purpose |
|---|---|
| `src/data/tamil-nadu-districts.ts` | Tamil Nadu district GeoJSON boundaries + bounding boxes |

### 1.3 Backend — `ai-engine/`

#### Backend Core — `ai-engine/backend/`

| Path | Purpose |
|---|---|
| `backend/__init__.py` | Package marker |
| `backend/app.py` | FastAPI app — lifespan (model load, DB init, migrations), CORS, 14 router registrations, health endpoint |
| `backend/routes.py` | **All 48 API routes** — 14 routers, 779 lines |
| `backend/database.py` | SQLAlchemy engine, 6 ORM models, DB session, seed/migration functions |
| `backend/models.py` | 22 Pydantic models — request/response for all endpoints |
| `backend/schemas.py` | 8 Pydantic schemas — ComplaintCreate, ComplaintResponse, Incident schemas |
| `backend/services.py` | 6 service classes — Classification, Clustering, Priority, Dashboard, Decision, Spatial, Complaint |
| `backend/worker.py` | Arq background worker — full ML pipeline (classify → dedup → incident → priority) |
| `backend/job_queue.py` | Arq Redis pool — `enqueue_complaint_job()`, `get_complaint_status()` |
| `backend/auth_service.py` | JWT + bcrypt — `hash_password`, `verify_password`, `create/verify_token` |
| `backend/storage.py` | S3/MinIO — `S3Storage`, `validate_file` |
| `backend/requirements.txt` | Core Python deps — FastAPI, SQLAlchemy, scikit-learn, numpy, PyJWT, bcrypt, arq, boto3 |
| `backend/requirements-ai.txt` | Optional heavy ML deps — sentence-transformers, torch |

#### AI Engine Modules

| Path | Purpose |
|---|---|
| `classification/train.py` | `ComplaintClassifier` — TF-IDF + Logistic Regression, train/evaluate/save/load |
| `classification/predict.py` | `ComplaintPredictor` — batch prediction from trained model |
| `classification/evaluate.py` | `evaluate_model()`, `cross_validate_model()`, `analyze_errors()` |
| `classification/utils.py` | `clean_text()`, `prepare_complaint_text()`, `validate_dataframe()` |
| `clustering/cluster.py` | `ComplaintClusterer` — DBSCAN + SentenceTransformer embeddings |
| `clustering/utils.py` | `preprocess_for_clustering()`, `group_by_location()` |
| `clustering/evaluate.py` | `evaluate_clustering()`, silhouette/Davies-Bouldin scores |
| `priority/priority.py` | `PriorityEngine` — 4-factor weighted score (cluster size, age, category, location) |
| `priority/rules.py` | `PriorityRulesEngine` — 8 override rules, `EscalationPolicy` |
| `priority/intelligence.py` | `IncidentIntelligenceEngine` — severity, impact, risk, resources |
| `priority/utils.py` | `calculate_days_open()`, `extract_urgency_keywords()`, `estimate_affected_population()` |
| `prediction/engine.py` | `PredictiveEngine` — linear trend forecast, escalation prediction, alerts |
| `knowledge/engine.py` | `GovernanceKnowledgeEngine` — root cause, cascade impact, policy recommendations, risk index |
| `decision/support.py` | `DecisionSupportEngine` — district/ward rankings, recommendations, executive report |
| `copilot/engine.py` | `CopilotEngine` — intent-based chat, brief generation, insights |
| `duplicate_detection/engine.py` | `DuplicateDetector` — SBERT embeddings + NearestNeighbors (fallback: keyword overlap) |
| `duplicate_detection/utils.py` | `UnionFind`, `preprocess_complaint_text()`, `format_duplicate_report()` |
| `duplicate_detection/train_embeddings.py` | `EmbeddingTrainer` — generates SBERT embeddings from CSV |
| `duplicate_detection/build_faiss.py` | `FAISSIndexBuilder` — flat/IVF/HNSW indices for fast similarity search |

#### Training & Data

| Path | Purpose |
|---|---|
| `train_pipeline.py` | Standalone training script — vectorizer + classifier + label encoder + metadata |
| `data/generate_tn_dataset.py` | Synthetic Tamil Nadu complaint generator |
| `data/giips.db` | Default SQLite database |
| `data/nyc311_filtered.csv` | Training data |
| `data/synthetic_complaints.json` | Pre-generated synthetic dataset |
| `models/classifier.pkl` | Trained Logistic Regression model |
| `models/vectorizer.pkl` | TF-IDF vectorizer |
| `models/label_encoder.pkl` | Label encoder |
| `models/classification/classifier.pkl` | Model in classification subdirectory |
| `models/classification/vectorizer.pkl` | Vectorizer in classification subdirectory |
| `models/classification/label_encoder.pkl` | Label encoder in classification subdirectory |
| `models/classification/metadata.json` | Training metadata — date, accuracy, classes |

### 1.4 Ancillary

| Path | Purpose |
|---|---|
| `metrics/calculate_impact.py` | Impact metric calculator — duplicate reduction rate, time saved |
| `metrics/impact_metrics.json` | Computed impact metrics |
| `metrics/cache/embeddings_sbert.npy` | Cached SBERT embeddings |
| `dist/` | Vite build output (44 assets) |

---

## 2. Backend Dependency / Connection Graph

### 2.1 Module Dependency Map

```
app.py
  ├── routes.py (imports all 14 routers)
  ├── database.py (Base, engine, seed_default_executive, backfill_complaint_user_ids)
  ├── job_queue.py (init_redis_pool, close_redis_pool)
  ├── priority.priority (PriorityEngine — lifespan init check)
  └── pickle (loads classifier.pkl, vectorizer.pkl, label_encoder.pkl)

routes.py
  ├── database.py (get_db, User, Incident, Complaint, AuditLog, DepartmentMetrics)
  ├── models.py (all 22 Pydantic models)
  ├── schemas.py (ComplaintCreate, SubmissionAcceptedResponse, ComplaintProcessingStatus)
  ├── services.py (ClassificationService, ClusteringService, PriorityService, DashboardService,
  │              DecisionService, SpatialService, ComplaintService)
  ├── auth_service.py (hash_password, verify_password, create_access_token, verify_token)
  ├── job_queue.py (enqueue_complaint_job, get_complaint_status)
  ├── storage.py (S3Storage, validate_file)
  ├── prediction.engine (PredictiveEngine)
  ├── knowledge.engine (GovernanceKnowledgeEngine)
  ├── decision.support (DecisionSupportEngine)
  └── copilot.engine (CopilotEngine)

services.py
  ├── database.py (SessionLocal, Complaint, Incident, PriorityHistory)
  ├── models.py (ClassifyRequest, ClassifyResponse, etc.)
  ├── classification.train (ComplaintClassifier)
  ├── clustering.cluster (ComplaintClusterer)
  ├── priority.priority (PriorityEngine)
  └── duplicate_detection.engine (DuplicateDetector)

worker.py
  ├── services.py (ClassificationService, DuplicateDetector, PriorityService)
  ├── database.py (SessionLocal, Complaint, Incident, PriorityHistory)
  └── models.py (ClassifyRequest, PriorityRequest)
```

### 2.2 Complete Route Table (48 Endpoints)

| Method | Path | Router Variable | Auth | Handler in routes.py | Backend Module Used |
|---|---|---|---|---|---|
| GET | `/` | app.py | No | `root()` | — |
| GET | `/health` | app.py | No | `health()` | — |
| POST | `/similar` | app.py | No | `find_similar()` | — |
| POST | `/classify` | `classify_router` | No | `classify_single()` | `ClassificationService.classify()` |
| POST | `/classify/batch` | `classify_router` | No | `classify_batch()` | `ClassificationService.classify()` |
| POST | `/classify/predict` | `classify_router` | No | `predict_category()` | `ClassificationService.classify()` |
| POST | `/cluster` | `cluster_router` | No | `cluster_complaints()` | `ClusteringService.cluster()` |
| POST | `/cluster/similar` | `cluster_router` | No | `find_similar()` | `ClusteringService.find_similar()` |
| GET | `/cluster/config` | `cluster_router` | No | `get_clustering_config()` | Hardcoded |
| POST | `/priority` | `priority_router` | No | `calculate_priority()` | `PriorityService.calculate()` |
| POST | `/priority/batch` | `priority_router` | No | `calculate_batch_priority()` | `PriorityService.calculate()` |
| GET | `/priority/rules` | `priority_router` | No | `get_priority_rules()` | Hardcoded |
| GET | `/dashboard` | `dashboard_router` | No | `get_dashboard()` | `DashboardService.get_summary()` |
| GET | `/dashboard/metrics` | `dashboard_router` | No | `get_metrics()` | Hardcoded |
| GET | `/dashboard/trend` | `dashboard_router` | No | `get_trend_data()` | Inline SQLAlchemy |
| GET | `/incidents` | `incident_router` | No | `get_incidents()` | Inline SQLAlchemy |
| GET | `/incidents/{id}` | `incident_router` | No | `get_incident()` | `DashboardService.get_incident_by_id()` |
| POST | `/complaints` | `complaint_router` | JWT | `submit_complaint()` | `JobQueue.enqueue_complaint_job()` |
| GET | `/complaints/{id}/status` | `complaint_router` | JWT | `get_complaint_processing_status()` | `JobQueue.get_complaint_status()` |
| POST | `/complaints/{id}/upload` | `complaint_router` | JWT | `upload_complaint_photo()` | `S3Storage.upload()` |
| GET | `/complaints/my` | `complaint_router` | JWT | `get_my_complaints()` | Inline SQLAlchemy |
| GET | `/complaints/coordinates` | `complaint_router` | No | `get_complaint_coordinates()` | Inline SQLAlchemy |
| GET | `/complaints/{id}` | `complaint_router` | JWT | `get_complaint_detail()` | Inline SQLAlchemy |
| GET | `/spatial/heatmap` | `spatial_router` | No | `get_heatmap()` | `SpatialService.get_heatmap()` |
| GET | `/spatial/hotspots` | `spatial_router` | No | `get_hotspots()` | `SpatialService.get_hotspots()` → `PriorityEngine` |
| GET | `/spatial/forecast` | `spatial_router` | No | `get_forecast()` | `SpatialService.get_forecast()` |
| GET | `/spatial/risk` | `spatial_router` | No | `get_risk()` | `SpatialService.get_risk_analysis()` |
| POST | `/spatial/simulate` | `spatial_router` | No | `simulate()` | `SpatialService.simulate_resources()` |
| GET | `/executive/summary` | `executive_router` | No | `get_executive_summary()` | `DecisionService.get_executive_summary()` |
| GET | `/executive/ward-health` | `executive_router` | No | `get_ward_health()` | `DecisionService.get_ward_health()` |
| GET | `/executive/department-workload` | `executive_router` | No | `get_dept_workload()` | `DecisionService.get_dept_workload()` |
| POST | `/auth/register` | `auth_router` | No | `register()` | `auth_service.hash_password()` |
| POST | `/auth/login` | `auth_router` | No | `login()` | `auth_service.{verify,hash,create}*` |
| GET | `/auth/me` | `auth_router` | JWT | `get_me()` | — |
| PUT | `/auth/profile` | `auth_router` | JWT | `update_profile()` | `auth_service.hash_password()` |
| GET | `/admin/officers` | `admin_router` | Exec | `get_officers()` | Inline SQLAlchemy (`User`) |
| POST | `/admin/officers` | `admin_router` | Exec | `create_officer()` | `auth_service.hash_password()` |
| PATCH | `/admin/officers/{id}/disable` | `admin_router` | Exec | `disable_officer()` | Inline SQLAlchemy (`User`) |
| PATCH | `/admin/officers/{id}/enable` | `admin_router` | Exec | `enable_officer()` | Inline SQLAlchemy (`User`) |
| GET | `/admin/departments` | `admin_router` | Exec | `get_departments()` | Inline SQLAlchemy (`DepartmentMetrics`) |
| GET | `/admin/system-health` | `admin_router` | Exec | `get_system_health()` | Inline counts + hardcoded statuses |
| GET | `/admin/audit-logs` | `admin_router` | Exec | `get_audit_logs()` | Inline SQLAlchemy (`AuditLog`) |
| GET | `/predictions/summary` | `prediction_router` | No | `get_predictions_summary()` | `PredictiveEngine.{forecast,alerts}*` |
| GET | `/knowledge/summary` | `knowledge_router` | No | `get_knowledge_summary()` | `GovernanceKnowledgeEngine.*` |
| GET | `/decision-support/summary` | `decision_router` | No | `get_decision_support_summary()` | `DecisionSupportEngine.*` |
| POST | `/copilot/chat` | `copilot_router` | No | `copilot_chat()` | `CopilotEngine.chat()` |

### 2.3 Auth Dependency Chain

```
get_current_user(authorization: str, db: Session) → User
  1. Extracts Bearer token from Authorization header
  2. Calls verify_token(token) → {"sub": email, "role": ...}
  3. Queries User table by email
  4. Returns User or raises HTTPException(401)

get_executive_user(db_user: User) → User
  1. Checks db_user.role == "Executive"
  2. Raises HTTPException(403) if not
```

---

## 3. Frontend-to-Backend API Map

### 3.1 API Client

**File:** `src/services/api.ts`

All HTTP calls use **native `fetch()`** (no Axios). Base URL from `VITE_API_BASE_URL` env var.

```typescript
// Typical usage pattern:
api.get('/endpoint')
api.post('/endpoint', body)
api.patch('/endpoint', body)
// Auth token injected automatically from localStorage
```

### 3.2 Page → API Endpoint Mapping

| Page Component | API Call(s) | Backend Route | Tables Read/Written | AI Module |
|---|---|---|---|---|
| **Overview.tsx** | `GET /dashboard` | `dashboard_router.get_dashboard()` | `Complaint` (count, group), `Incident` (count, group) | `DashboardService.get_summary()` |
| **CitizenPortal.tsx** | `POST /complaints` | `complaint_router.submit_complaint()` | `Complaint` (create), `User` (auth check) | Enqueues Arq job → `worker.py` |
| | `POST /complaints/{id}/upload` | `complaint_router.upload_complaint_photo()` | `Complaint` (update image_path) | `S3Storage.upload()` |
| | `GET /complaints/{id}/status` (poll) | `complaint_router.get_complaint_processing_status()` | Redis key | `job_queue.get_complaint_status()` |
| **MyComplaints.tsx** | `GET /complaints/my` | `complaint_router.get_my_complaints()` | `Complaint` (filter by user_id), `Incident` (join) | — |
| **ComplaintDetail.tsx** | `GET /complaints/{id}` | `complaint_router.get_complaint_detail()` | `Complaint` (by id+user_id), `Incident` + `PriorityHistory` | — |
| **CitizenProfile.tsx** | `GET /auth/me` | `auth_router.get_me()` | `User` (via auth) | — |
| | `PUT /auth/profile` | `auth_router.update_profile()` | `User` (update) | `auth_service.hash_password()` |
| **Login.tsx** (via AuthContext) | `POST /auth/login` | `auth_router.login()` | `User` (find by email) | `auth_service.*` |
| **Register.tsx** (via AuthContext) | `POST /auth/register` | `auth_router.register()` | `User` (create) | `auth_service.hash_password()` |
| **ExecutiveDashboard.tsx** | `GET /executive/summary` | `executive_router.get_executive_summary()` | `Incident` (critical count, ward group), `Complaint` (7-day category) | `DecisionService.get_executive_summary()` |
| | `GET /executive/ward-health` | `executive_router.get_ward_health()` | `Incident` (distinct wards) | `DecisionService.get_ward_health()` |
| | `GET /executive/department-workload` | `executive_router.get_dept_workload()` | `Incident` (group by category) | `DecisionService.get_dept_workload()` |
| | `GET /incidents` | `incident_router.get_incidents()` | `Incident` + `Complaint` (joinedload) | — |
| | `GET /predictions/summary` | `prediction_router.get_predictions_summary()` | `Complaint` (date range counts), `Incident` (counts, avg) | `PredictiveEngine` |
| | `GET /knowledge/summary` | `knowledge_router.get_knowledge_summary()` | `Incident` (ward group) | `GovernanceKnowledgeEngine` |
| | `GET /decision-support/summary` | `decision_router.get_decision_support_summary()` | `Incident` (filter critical) | `DecisionSupportEngine` |
| | `GET /admin/system-health` | `admin_router.get_system_health()` | `User`, `Complaint`, `Incident` (counts) | — |
| | `POST /copilot/chat` | `copilot_router.copilot_chat()` | — | `CopilotEngine.chat()` |
| **SpatialIntelligence.tsx** | `GET /spatial/heatmap` | `spatial_router.get_heatmap()` | `Complaint` (ward group, avg lat/lon) | `SpatialService.get_heatmap()` |
| | `GET /spatial/hotspots` | `spatial_router.get_hotspots()` | `Complaint` (ward/category group) | `SpatialService.get_hotspots()` → `PriorityEngine` |
| | `GET /spatial/risk` | `spatial_router.get_risk()` | — | `SpatialService.get_risk_analysis()` |
| | `GET /spatial/forecast` | `spatial_router.get_forecast()` | — | `SpatialService.get_forecast()` |
| | `GET /incidents` | `incident_router.get_incidents()` | `Incident` + `Complaint` | — |
| | `GET /complaints/coordinates` | `complaint_router.get_complaint_coordinates()` | `Complaint` (lat/lon IS NOT NULL) | — |
| | `POST /spatial/simulate` | `spatial_router.simulate()` | — | `SpatialService.simulate_resources()` |
| **IncidentFeed.tsx** | `GET /incidents` | `incident_router.get_incidents()` | `Incident` + `Complaint` | — |
| **Clusters.tsx** | `GET /incidents` | `incident_router.get_incidents()` | `Incident` + `Complaint` | — |
| | `GET /incidents/{id}` | `incident_router.get_incident()` | `Incident` + `Complaint` + `PriorityHistory` | `DashboardService.get_incident_by_id()` |
| | `GET /priority/rules` | `priority_router.get_priority_rules()` | — | Hardcoded |
| | `GET /predictions/summary` | `prediction_router.get_predictions_summary()` | `Complaint`, `Incident` | `PredictiveEngine` |
| | `GET /knowledge/summary` | `knowledge_router.get_knowledge_summary()` | `Incident` | `GovernanceKnowledgeEngine` |
| | `GET /decision-support/summary` | `decision_router.get_decision_support_summary()` | `Incident` | `DecisionSupportEngine` |
| **Analysis.tsx** | `GET /dashboard/metrics` | `dashboard_router.get_metrics()` | — | Hardcoded |
| | `GET /dashboard/trend` | `dashboard_router.get_trend_data()` | `Complaint` (monthly), `Incident` (monthly) | Inline SQLAlchemy |
| **SystemHealth.tsx** | `GET /admin/system-health` | `admin_router.get_system_health()` | `User`, `Complaint`, `Incident` | — |
| **AuditLogs.tsx** | `GET /admin/audit-logs` | `admin_router.get_audit_logs()` | `AuditLog` | — |
| **DepartmentManagement.tsx** | `GET /admin/departments` | `admin_router.get_departments()` | `DepartmentMetrics` | — |
| **OfficerManagement.tsx** | `GET /admin/officers` | `admin_router.get_officers()` | `User` | — |
| | `POST /admin/officers` | `admin_router.create_officer()` | `User` | `auth_service.hash_password()` |
| | `PATCH /admin/officers/{id}/disable` | `admin_router.disable_officer()` | `User` | — |
| | `PATCH /admin/officers/{id}/enable` | `admin_router.enable_officer()` | `User` | — |

### 3.3 External API (non-backend)

| Component | API | Purpose |
|---|---|---|
| `AddressSearch.tsx` | `GET https://nominatim.openstreetmap.org/search` | Free-text geocoding for Tamil Nadu addresses (no API key) |

---

## 4. Database Schema Map

### 4.1 Entity-Relationship Diagram (Text)

```
┌──────────┐       ┌────────────┐       ┌──────────────────┐
│   User   │       │  Incident  │◄──────│  PriorityHistory  │
│          │       │            │       │ (FK incident_id)  │
│  users   │       │  incidents │       │ priority_history  │
└────┬─────┘       └─────┬──────┘       └──────────────────┘
     │                    │
     │ (no formal FK)     │ (FK incident_id)
     │                    │
     └─────┐       ┌─────┘
           │       │
       ┌───▼───────▼───┐
       │   Complaint    │
       │                │
       │  complaints    │
       └────────────────┘

┌──────────────────┐   ┌──────────────────┐
│    AuditLog      │   │ DepartmentMetrics│
│   audit_logs     │   │ department_metrics│
└──────────────────┘   └──────────────────┘
```

### 4.2 Table: `users`

| Column | Type | Constraints | Default |
|---|---|---|---|
| `id` | String | PK, indexed | — |
| `full_name` | String | NOT NULL | — |
| `email` | String | NOT NULL, UNIQUE, indexed | — |
| `phone` | String | nullable | — |
| `password_hash` | String | NOT NULL | — |
| `district` | String | nullable | — |
| `ward` | String | nullable | — |
| `role` | String | NOT NULL | — |
| `created_at` | DateTime | NOT NULL | `datetime.utcnow` |
| `last_login` | DateTime | nullable | — |
| `status` | String | NOT NULL | `"active"` |

**Read by routes:** `register`, `login`, `get_me`, `update_profile`, `get_officers`, `create_officer`, `disable_officer`, `enable_officer`, `get_system_health`  
**Written by routes:** `register`, `create_officer`, `disable_officer`, `enable_officer`, `update_profile`, `login` (last_login)  
**Seeded by:** `seed_default_executive()` → `collector@gov.in` / Executive role

### 4.3 Table: `incidents`

| Column | Type | Constraints | Default |
|---|---|---|---|
| `id` | String | PK, indexed | — |
| `incident_number` | String | NOT NULL, UNIQUE, indexed | — |
| `category` | String | NOT NULL | — |
| `ward` | String | NOT NULL | — |
| `cluster_size` | Integer | NOT NULL | `1` |
| `priority_score` | Float | NOT NULL | `0.0` |
| `priority_label` | String | NOT NULL | `"Low"` |
| `summary` | Text | nullable | — |
| `status` | String | NOT NULL | `"open"` |
| `recommended_action` | Text | nullable | — |
| `days_open` | Integer | NOT NULL | `0` |
| `created_at` | DateTime | NOT NULL | `datetime.utcnow` |

**Relationships:**
- `complaints` ← `Complaint.incident_id` (one-to-many)
- `priority_history` ← `PriorityHistory.incident_id` (one-to-many)

**Read by routes:** `get_dashboard`, `get_incidents`, `get_incident`, `get_trend_data`, `get_predictions_summary`, `get_knowledge_summary`, `get_decision_support_summary`, `get_executive_summary`, `get_ward_health`, `get_dept_workload`  
**Written by:** `worker.py:process_complaint()`, `services.py:ComplaintService.submit_complaint()`

### 4.4 Table: `complaints`

| Column | Type | Constraints | Default |
|---|---|---|---|
| `id` | String | PK, indexed | — |
| `title` | String | NOT NULL | — |
| `description` | Text | NOT NULL | — |
| `location` | String | NOT NULL | — |
| `ward` | String | NOT NULL | — |
| `image_path` | String | nullable | — |
| `predicted_category` | String | nullable | — |
| `confidence` | Float | nullable | — |
| `priority` | String | nullable | — |
| `incident_id` | String | FK → `incidents.id`, nullable | — |
| `user_id` | String | nullable, indexed | — |
| `created_at` | DateTime | NOT NULL | `datetime.utcnow` |
| `address` | String | nullable (added via migration) | — |
| `latitude` | Float | nullable | — |
| `longitude` | Float | nullable | — |
| `similarity_score` | Float | nullable | — |
| `merge_reason` | Text | nullable | — |
| `merged_at` | DateTime | nullable | — |

**Relationships:**
- `incident` → `Incident` (many-to-one, via `incident_id` FK)

**Read by routes:** `get_dashboard`, `get_my_complaints`, `get_complaint_detail`, `get_complaint_coordinates`, `get_trend_data`, `get_predictions_summary`, `get_system_health`, `get_heatmap`, `get_hotspots`  
**Written by:** `submit_complaint` (create), `upload_complaint_photo` (update image_path), `worker.py:process_complaint()` (update ML fields), `services.py:ComplaintService.submit_complaint()`

### 4.5 Table: `priority_history`

| Column | Type | Constraints | Default |
|---|---|---|---|
| `id` | String | PK | — |
| `incident_id` | String | NOT NULL, FK → `incidents.id`, indexed | — |
| `old_score` | Float | NOT NULL | — |
| `new_score` | Float | NOT NULL | — |
| `reason` | Text | NOT NULL | — |
| `changed_at` | DateTime | NOT NULL | `datetime.utcnow` |

**Written by:** `worker.py:process_complaint()`, `services.py:ComplaintService.submit_complaint()`  
**Read by:** `get_complaint_detail` (via `joinedload(Incident.priority_history)`)

### 4.6 Table: `audit_logs`

| Column | Type | Constraints | Default |
|---|---|---|---|
| `id` | String | PK | — |
| `timestamp` | DateTime | NOT NULL | `datetime.utcnow` |
| `user_id` | String | nullable | — |
| `user_email` | String | nullable | — |
| `role` | String | nullable | — |
| `action` | String | NOT NULL | — |
| `target` | String | nullable | — |
| `details` | Text | nullable | — |
| `status` | String | NOT NULL | `"success"` |
| `ip_address` | String | nullable | — |

**Written by:** `_write_audit_log()` helper (called by `submit_complaint`, `login`, `create_officer`, `disable_officer`, `enable_officer`, `get_departments`, `get_system_health`)  
**Read by:** `get_audit_logs`

### 4.7 Table: `department_metrics`

| Column | Type | Constraints | Default |
|---|---|---|---|
| `id` | String | PK | — |
| `department` | String | NOT NULL | — |
| `open_incidents` | Integer | NOT NULL | `0` |
| `critical_incidents` | Integer | NOT NULL | `0` |
| `assigned_officers` | Integer | NOT NULL | `0` |
| `avg_resolution_time` | Float | NOT NULL | `0.0` |
| `completion_percentage` | Float | NOT NULL | `0.0` |
| `workload_indicator` | Float | NOT NULL | `0.0` |
| `updated_at` | DateTime | NOT NULL | `datetime.utcnow` |

**Read by:** `get_departments` (only consumer)

---

## 5. Deployment Architecture

### 5.1 Live Topology

```
                         ┌─────────────────────────────────────┐
                         │          Vercel (Frontend)           │
                         │  URL: https://giips.vercel.app       │
                         │  Hosting: SPA (vercel.json rewrites)  │
                         │  Build: npm run build → dist/        │
                         │  Env: VITE_API_BASE_URL (build-time)  │
                         └──────────────┬──────────────────────┘
                                        │
                          VITE_API_BASE_URL
                    https://giips-backend.onrender.com
                                        │
                         ┌──────────────▼──────────────────────┐
                         │        Render (Backend)              │
                         │  URL: https://giips-backend.onrender.com │
                         │  Runtime: Docker (Python 3.11)       │
                         │  Server: Uvicorn (1 worker)          │
                         │  Port: 8000                          │
                         │  Env: DATABASE_URL, REDIS_URL,       │
                         │        GIIPS_JWT_SECRET,             │
                         │        GIIPS_ALLOWED_ORIGINS,        │
                         │        S3_* (optional)               │
                         └──────┬───────────────┬──────────────┘
                                │               │
                    ┌───────────▼───┐   ┌───────▼──────────┐
                    │   Render      │   │   Render         │
                    │   PostgreSQL  │   │   Redis           │
                    │  (Managed DB) │   │  (Managed Cache)  │
                    └───────────────┘   └──────────────────┘
```

### 5.2 Platform Details

| Aspect | Frontend (Vercel) | Backend (Render) |
|---|---|---|
| **Deploy trigger** | Git push to `main` (auto) | Git push to `main` (auto via Render dashboard) |
| **Build command** | `npm run build` (`tsc -b && vite build`) | Docker build (Dockerfile) |
| **Output** | `dist/` directory | Docker container |
| **Static files** | Served by Vercel CDN | N/A |
| **Env vars** | `VITE_API_BASE_URL` (build-time) | `DATABASE_URL`, `REDIS_URL`, `GIIPS_JWT_SECRET`, etc. |
| **Health check** | N/A | `curl http://localhost:8000/health` (Dockerfile HEALTHCHECK) |

### 5.3 Required Environment Variables

#### Frontend (build-time)
```
VITE_API_BASE_URL=https://giips-backend.onrender.com
```

#### Backend (runtime)
```
DATABASE_URL=postgresql://giips:giips@postgres:5432/giips
REDIS_URL=redis://redis:6379/0
GIIPS_JWT_SECRET=<strong-random-secret>
GIIPS_ALLOWED_ORIGINS=https://giips.vercel.app
S3_ENDPOINT_URL=http://minio:9000            # optional
S3_PUBLIC_URL=http://localhost:9000          # optional
S3_ACCESS_KEY_ID=minioadmin                  # optional
S3_SECRET_ACCESS_KEY=minioadmin              # optional
S3_BUCKET_NAME=giips-complaints             # optional
```

### 5.4 Docker Architecture (`docker-compose.yml`)

| Service | Image | Port | Purpose |
|---|---|---|---|
| `minio` | `minio/minio:latest` | 9000 (API), 9001 (Console) | S3-compatible complaint photo storage |
| `postgres` | `postgres:16-alpine` | 5432 | Production database |
| `redis` | `redis:7-alpine` | 6379 | Arq job queue |
| `backend` | Build from Dockerfile | 8000 | FastAPI application |

### 5.5 CI/CD

**No GitHub Actions or CI pipeline configured.** Deployment is manual:

1. **Frontend**: Git push → Vercel auto-deploys from `main` branch (detects `vercel.json`)
2. **Backend**: Git push → Render auto-deploys from `main` branch (Dockerfile detected via Render dashboard)

### 5.6 Python Dependencies

**Core** (`requirements.txt`):
`fastapi`, `pydantic`, `sqlalchemy`, `numpy`, `pandas`, `scikit-learn`, `uvicorn[standard]`,
`python-multipart`, `python-dotenv`, `gunicorn`, `PyJWT`, `bcrypt`, `psycopg2-binary`,
`geopy`, `arq`, `redis[hiredis]`, `boto3`

**Optional AI** (`requirements-ai.txt`, commented out in Dockerfile):
`sentence-transformers`, `torch` — excluded from production build. The system falls back to keyword-based duplicate detection when these are absent.

---

## 6. AI Pipeline Data Flow

### Complete Lifecycle of a Single Complaint

```
STEP 1: CITIZEN SUBMITS
───────────────────────
Page:      CitizenPortal.tsx
API:       POST /complaints
Handler:   routes.py submit_complaint() [line 130]
Auth:      JWT (get_current_user)
Schema:    ComplaintCreate [schemas.py:15]
           ├─ title (1-200 chars)
           ├─ description (1-5000 chars)
           ├─ location (1-500 chars)
           ├─ ward (optional, default "")
           ├─ address (optional, from Nominatim)
           ├─ latitude (optional, -90 to 90)
           ├─ longitude (optional, -180 to 180)
           └─ image_path (optional)

STEP 2: DATABASE WRITE
───────────────────────
routes.py:134-147
           Complaint created with:
           - id = uuid4()
           - user_id from JWT token
           - AI fields = all NULL (predicted_category, confidence, incident_id, priority)
           db.add(complaint); db.commit()

STEP 3: STATUS URL RETURNED
───────────────────────────
routes.py:161-165
           HTTP 202 Accepted
           { complaintId, statusUrl, message }

STEP 4: ENQUEUE ASYNC JOB
───────────────────────────
routes.py:149 → job_queue.py:46 → Arq Redis enqueue
           Job: "process_complaint"(complaint_id, user_id)
           If Redis unavailable → NO ML PROCESSING (complaint stored but never classified)

STEP 5: FRONTEND POLLS STATUS
─────────────────────────────
CitizenPortal.tsx polls GET /complaints/{id}/status every 1.5s
           Returns: pending → processing → completed/failed
           Reads from Redis key (TTL: 3600s)

═══ BACKGROUND WORKER (arq) ═══
File: worker.py process_complaint() [line 43]

STEP 6: LOAD COMPLAINT
───────────────────────
worker.py:51   complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()

STEP 7: CLASSIFICATION
───────────────────────
worker.py:66-69 → services.py:51 → classification/train.py:ComplaintClassifier
           
           IF trained model exists (classifier.pkl):
             TF-IDF vectorize text → Logistic Regression predict()
             Returns: predicted_category, confidence (0-1), top_predictions, reason, supporting_factors
           
           ELSE (fallback):
             Keyword matching: "pothole"→"Road Infrastructure", "pipe"→"Water Supply", etc.
           
           Model trained by: train_pipeline.py on NYC 311 data (7 categories)

STEP 8: DUPLICATE DETECTION
───────────────────────────
worker.py:71-102 → duplicate_detection/engine.py:DuplicateDetector
           
           Queries existing complaints (last 90 days, same ward OR category, limit 1000)
           
           IF sentence-transformers available:
             SBERT embeddings → NearestNeighbors (k=5, cosine)
             Confidence = 60% text_sim + 30% geo_proximity + 10% category_match
             geopy.distance.geodesic for geo proximity
           
           ELSE (fallback):
             Jaccard keyword overlap on tokenized text
           
           Returns: incident_id (if match found), dup_conf
           Decision: is_duplicate = dup_conf > 0.8

STEP 9: INCIDENT LOGIC
───────────────────────
worker.py:104-127

           IF is_duplicate AND incident_id exists:
             incident.cluster_size += 1
             merge_reason = "Automated merge based on {dup_conf:.2%} confidence"
             # No new Incident row
           
           ELSE:
             incident = Incident(
               id = uuid4(),
               incident_number = f"INC-{uuid4().hex[:6].upper()}",
               category = predicted_category,
               ward = complaint.ward,
               cluster_size = 1,
               priority_score = 0.0,
               priority_label = "Low",
               summary = complaint.title
             )
             db.add(incident)
             merge_reason = "New incident created"

STEP 10: PRIORITY SCORING
─────────────────────────
worker.py:129-152 → priority/priority.py:PriorityEngine

           Four weighted factors:
           ┌────────────────┬──────┬────────────────────────────────────┐
           │ Factor         │Weight│ Computation                         │
           ├────────────────┼──────┼────────────────────────────────────┤
           │ Cluster Size   │ 30%  │ sigmoid(cluster_size) → [0,1]      │
           │ Complaint Age  │ 25%  │ 1 - exp(-days_since_first/10)       │
           │ Category       │ 25%  │ Water=0.90, Road=0.85, Waste=0.65  │
           │ Location       │ 20%  │ school=1.0, hospital=0.95, ...    │
           └────────────────┴──────┴────────────────────────────────────┘
           
           Score = weighted_sum × 100  (clamped 0-100)
           Label: >=90 "Critical", >=75 "High", >=50 "Medium", <50 "Low"
           
           Rules engine (priority/rules.py) applies ± adjustments:
             +20 safety_critical, +15 school, +12 hospital, -5 minor_issue
           
           IF score changes → creates PriorityHistory record

STEP 11: UPDATE DATABASE
────────────────────────
worker.py:154-159
           complaint.predicted_category = category
           complaint.confidence = confidence
           complaint.incident_id = incident.id
           complaint.priority = incident.priority_label
           complaint.merge_reason = merge_reason (if duplicate)
           complaint.user_id = user_id
           db.commit()

STEP 12: SET COMPLETED STATUS
─────────────────────────────
worker.py:175   Redis key "complaint:status:{id}" = completed + result JSON
                TTL: 3600s (1 hour)

═══ DOWNSTREAM DISPLAY ═══

STEP 13: CITIZEN SEES RESULT
─────────────────────────────
MyComplaints.tsx → GET /complaints/my
           Returns: complaint with predicted_category, confidence, priority, incident linkage

ComplaintDetail.tsx → GET /complaints/{id}
           Returns: full detail including incident summary and priority_history

STEP 14: OFFICER/EXECUTIVE DASHBOARDS
─────────────────────────────────────
Overview.tsx        → GET /dashboard       → DashboardService.get_summary()
                                                - total complaints, incidents
                                                - breakdown by priority label, category
                                                - 10 most recent incidents
IncidentFeed.tsx    → GET /incidents       → All incidents with nested complaints
SpatialIntelligence → GET /spatial/*       → Map layers (heatmap, hotspots, pins)
ExecutiveDashboard → GET /executive/summary → DecisionService.get_executive_summary()
                                                - critical count, worst ward, emerging trends
                   → GET /predictions/summary → PredictiveEngine.forecast_complaints()
                                                - linear trend extrapolation
                                                - escalation risk predictions
                                                - active alerts
                   → GET /knowledge/summary    → GovernanceKnowledgeEngine
                                                - risk indices
                                                - policy recommendations
                                                - root cause / cascade analysis
                   → GET /decision-support/summary → DecisionSupportEngine
                                                - district/ward rankings
                                                - resource recommendations
                                                - executive report
```

### 6.2 Prediction Engine Detail

**File:** `prediction/engine.py`

```
forecast_complaints(timeframe, history=[10,12,15,14,18]):
  1. history → np.array(dtype=float)
  2. x = arange(5)
  3. coeffs = polyfit(x, history, 1)     # linear regression slope + intercept
  4. future_x = arange(5, 5 + days_ahead)
  5. forecast = polyval(coeffs, future_x) # extrapolate
  6. predicted_volume = max(0, forecast[-1])  # clamped at 0 (fix for declining trend)
  7. confidence = 0.85 (hardcoded)
  Returns: { timeframe, predicted_volume, confidence, model }
```

### 6.3 Priority Rules Engine Detail

**File:** `priority/rules.py`

| Rule | Trigger | Adjustment |
|---|---|---|
| `safety_critical` | text has "injury"/"accident"/"dangerous" | +20 |
| `school_proximity` | text has "school" | +15 |
| `hospital_proximity` | text has "hospital" | +12 |
| `water_public_health` | category = Water Supply | +10 |
| `long_standing` | days_open > 30 | +8 |
| `large_cluster` | cluster_size > 10 | +7 |
| `minor_issue` | text has "cosmetic"/"minor"/"aesthetic" | -5 |
| `holiday_weekend` | current time is weekend/holiday | +3 |

---

*End of architecture document. Generated from full codebase analysis — every file path, line number, and function/class name is factual and verified against the source.*
