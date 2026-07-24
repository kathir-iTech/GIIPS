# GIIPS — Governance Incident Intelligence & Prioritization System

**A civic-complaint triage platform for Coimbatore, Tamil Nadu.**

Live: `https://giips.vercel.app` · Backend: `https://giips-backend.onrender.com`  
Tech: React 19 + FastAPI + PostgreSQL + TF-IDF/Logistic Regression

---

## What GIIPS Does

Citizens file complaints (road damage, water supply failure, garbage accumulation, etc.) through a web portal. GIIPS automatically classifies each complaint by category, detects near-duplicates, groups related complaints into incidents, assigns a priority score, and routes the result to the responsible municipal department. Citizens track resolution, receive notifications, verify outcomes, rate satisfaction, and can appeal unsatisfactory resolutions.

The system targets **Coimbatore City Municipal Corporation (CCMC)** — 100 wards across 5 zones — with department mappings to real bodies: CCMC Engineering Wing, TWAD Board (water), TANGEDCO (electricity), CCMC Health Department (sanitation), and others.

---

## The AI Pipeline — What Actually Runs

When a citizen submits a complaint, the following executes in a single async task (no external worker):

### 1. Classification (TF-IDF + Logistic Regression)
A trained model (`classifier.pkl`) predicts the category from complaint text + title. The model was trained on ~30K NYC 311 records mapped to 5 Tamil Nadu categories. **Measured accuracy: 57.1%**. When confidence is low, a keyword-overlap fallback against 10 civic categories is used. Tamil text is handled by a separate keyword matcher (`tamil_fallback.py`). The method used (`ml_model`, `tamil_keyword_fallback`, or `heuristic_fallback`) is returned in every response.

### 2. Duplicate Detection (Jaccard Keyword Overlap / Sentence Embedding Cosine)
New complaints are compared against the last 90 days of existing complaints (up to 1000) using the `DuplicateDetector` from `ai-engine/duplicate_detection/engine.py`. Two backends exist:

- **ML path** (when `sentence-transformers` is available): `all-MiniLM-L6-v2` embeddings + `NearestNeighbors(metric='cosine')`. Confidence is a weighted blend of text similarity (60%), geographic proximity (30%), and category match (10%).
- **Fallback path** (what actually runs on Render's 512 MB tier — `sentence-transformers` is commented out in `requirements.txt`): **Jaccard similarity** on word sets: `|new_words ∩ comp_words| / |new_words ∪ comp_words|`.

If confidence exceeds 0.8, the complaint is merged into the existing incident. A merge reason is stored, and the citizen is notified.

### 3. Incident Grouping
Non-duplicate complaints become new incidents. Complaints in the same `(category, ward)` bucket are clustered together (prefix-overlap fallback — no embedding model; SBERT/DBSCAN exists but is not wired in due to memory constraints on Render's free tier).

### 4. Priority Scoring (Rule-Based)
Priority is calculated from: cluster size, days since first complaint, category weight, and keyword severity signals. Scores range 0–100 mapping to Critical (90+), High (75–89), Medium (50–74), Low (0–49). An additional 8 situational rules adjust scores (e.g., monsoon keywords, school proximity).

### 5. Routing + Notification
The incident is assigned a department via a lookup table (`category → CCMC body`). Notifications are created for the citizen and for all active officers in the responsible department. Aging notifications fire at 4 days (warning) and 8 days (critical).

---

## What's Verified with Real Coimbatore Data

The following operate against actual CCMC ward geography and department structure, not placeholders:

- **100 wards across 5 zones** (North, East, Central, West, South) with area-level locality names — exact per CCMC delimitation notifications.
- **Department routing** maps each complaint category to the real responsible body: CCMC Engineering Wing (roads, drainage), TWAD Board (water), TANGEDCO (electricity), CCMC Health Department (sanitation/public health), and others.
- **10,000 synthetic complaints** seeded with Coimbatore-specific locations, ward numbers, zone references, and realistic civic descriptions (full Tamil-English text sample below). These populate all dashboards, charts, leaderboards, and auto-escalation triggers with production-like data.

> *Sample seeded complaint:* "Road damage near Mettupalayam Road junction causing accidents daily [COMP-000042 | Ward 34 | Central Zone | Coimbatore]"

- **43 Tamil Nadu government departments** mapped in a separate lookup (used for executive-level oversight views).
- **Citizen verification codes** (6-digit) are real — generated on resolution, sent via notification, and confirmed by the citizen before status changes to "resolved."
- **Appeal flow** — citizens can appeal resolved/closed incidents with a reason; the incident reopens, priority is bumped, and department officers receive a notification. Verified live on production.
- **Notifications** — 11 notification types delivered to both citizens and department officers. Verified live that officers receive department-targeted alerts (e.g., "appeal_filed" reaches CCMC Engineering Wing officers).

---

## Current Limitations & Roadmap

### ML Model Quality
| Issue | Status |
|-------|--------|
| Classification accuracy 57.1% | **Phase 1 baseline.** Trained on NYC 311 data mapped to TN categories. No real TN complaint dataset exists publicly. |
| No Tamil NLP model deployed | Keyword fallback only. IndicBERT/LaBSE reverted during Phase 1.5 for 512MB RAM limit. |
| No embedding-based clustering | SBERT + DBSCAN code exists but is not wired in (memory). Current clustering uses text-prefix overlap. |

**Planned (Phase 3):** Fine-tune a lightweight IndicBERT on a curated TN complaint corpus. Replace NYC 311 source data when a real dataset becomes available. Deploy sentence-transformers if the hosting tier allows.

### Infrastructure
| Issue | Status |
|-------|--------|
| Render free tier (512MB RAM, cold starts) | Constraints the ML stack. No PyTorch/TensorFlow runtime. |
| No message queue | Pipeline runs inline via `asyncio.create_task`. Not durable across restarts. |
| No database migrations | Schema changes via `ALTER TABLE` in startup code. Alembic deferred. |
| No test suite | Zero automated tests (backend or frontend). |
| No CI/CD pipeline | Both Vercel and Render auto-deploy from `main`; no GitHub Actions. |

**Planned (Phase 3):** Migrate to a paid hosting tier, add a durable job queue (Redis + arq or Celery), set up Alembic for migrations, and establish a CI pipeline with integration tests against the live API.

### Frontend
| Issue | Status |
|-------|--------|
| No loading skeletons | Spinner-only during data fetches. |
| No error toast system | Errors appear inline, not in a centralized snackbar. |
| No real-time notifications | 45-second polling interval. No WebSocket/SSE. |
| Address geocoder | Free Nominatim API — rate-limited, 500ms debounce. |

### Feature Gaps (Phase 3+)
- Real Tamil Nadu complaint dataset (replace NYC 311 training data)
- Full-text search across complaints (PostgreSQL tsvector or Elasticsearch)
- Real-time notifications via WebSocket/SSE
- Mobile application (React Native)
- SMS / WhatsApp notification channel
- GIS shapefile import for precise ward boundary overlays
- Data export (CSV, PDF reports)
- Multi-language beyond English and Tamil (Telugu, Kannada, Malayalam, Hindi)

---

## System Metrics (Live, Post-Deploy)

| Metric | Value |
|--------|-------|
| Backend API endpoints | 77 |
| Database tables | 7 |
| User roles | 7 (Citizen, Officer, Executive, Commissioner, Councillor, MLA, Collector) |
| Frontend routes | 24 |
| ML classification categories | 5 model-based + 10 heuristic-fallback |
| Duplicate detection threshold | 0.8 cosine similarity |
| Aging notification thresholds | 4 days (warning), 8 days (critical) |
| Notification types | 11 |
| i18n keys per language | ~916 |
| Rate limits | 5/min (auth), 10/min (complaints) |
| Token expiry | 60 minutes |
| Photo upload limit | 5 MB (jpg/png) |
| Seed data | 10,000 complaints, ~150 incidents, 9 demo users |
| Deployed | Vercel (frontend) + Render (backend) + Backblaze B2 (photo storage) |
