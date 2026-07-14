# GIIPS — Governance Incident Intelligence & Prioritization System

## Overview

GIIPS is an AI-powered civic complaint management platform for the **Coimbatore City Municipal Corporation (CCMC)**. Citizens submit complaints about civic issues; the system classifies, clusters, prioritises, and routes them to the appropriate government department for resolution. It includes a full governance hierarchy for oversight, escalation, and citizen-verified resolution.

---

## Geography: Coimbatore Ward / Zone Data

The system models **all 100 real CCMC wards** across **5 zones**, sourced from the official delimitation notification on ccmc.gov.in:

| Zone     | Ward Numbers                         | Examples                      |
|----------|--------------------------------------|-------------------------------|
| North    | 1–4, 10–15, 18–21, 25–30            | Thudiyalur, Saravanampatti    |
| East     | 5–9, 22–24, 50–61                    | Kalapatti, Singanallur, Irugur|
| Central  | 31–32, 46–49, 62–70, 80–84          | Gandhipuram, RS Puram, Race Course |
| West     | 16–17, 33–45, 71–75                  | Vadavalli, Mettupalayam Road  |
| South    | 76–79, 85–100                        | Kuniyamuthur, Perur, Vellalore|

Lookup data is in `ai-engine/backend/coimbatore_wards.py` (exporting `WARDS`, `ZONE_BY_WARD`, `AREAS_BY_WARD`, `AREA_TO_WARD`, `ALL_WARD_NUMBERS`).

---

## Governance Hierarchy

The platform supports a full Coimbatore-specific governance chain:

```
Citizen ──────► Councillor (ward-level, 1 per ward)
                    │
                    ▼
            Commissioner (zone-level, 5 zones)
                    │
            ┌───────┴───────┐
            ▼               ▼
           MLA            Collector
    (constituency)    (district oversight)
```

### User Roles & Permissions

| Role          | Permissions |
|---------------|-------------|
| **Citizen**   | Register, submit complaints, upload photos, track status, verify resolution (with code) |
| **Officer**   | View incidents/complaints, update status (Open→In-Progress→Resolved), merge/split incidents, view dashboard |
| **Executive** | Platform administration: create/disable officers, view department metrics, system health, audit logs, re-seed database |
| **Councillor**| View complaints/incidents in their assigned ward only, escalate incidents |
| **Commissioner** | View all wards, update status, merge/split, escalate incidents, zone-level oversight |
| **MLA**       | View escalated incidents across the constituency |
| **Collector** | View escalated incidents in the district, district-level oversight |

> Note: "Executive" is the admin role (distinct from "Collector" governance role). Collector and MLA are oversight roles that can only view escalated incidents.

### Demo Accounts

| Email | Role | Password |
|-------|------|----------|
| `citizen@giips.gov.in` | Citizen | password123 |
| `officer1@giips.gov.in` | Officer (CCMC Roads) | password123 |
| `officer2@giips.gov.in` | Officer (TWAD Water) | password123 |
| `officer3@giips.gov.in` | Officer (CCMC Sanitation) | password123 |
| `officer4@giips.gov.in` | Officer (TANGEDCO) | password123 |
| `collector@giips.gov.in` | Executive (admin) | password123 |
| `councillor4@giips.gov.in` | Councillor (Ward 27, Peelamedu) | password123 |
| `commr-north@giips.gov.in` | Commissioner (North Zone) | password123 |
| `mla1@giips.gov.in` | MLA | password123 |
| `collector1@giips.gov.in` | Collector | password123 |

---

## Citizen Verification-Before-Resolution Flow

When an officer marks an incident as "resolved":

1. **Status becomes `pending_verification`** — not immediately "resolved"
2. A **random 6-digit verification code** is generated and stored on the incident
3. The citizen receives an in-app notification containing the code
4. The citizen calls `POST /incidents/{id}/verify-resolution` with the code (rate-limited to 3 attempts/min)
5. Only the citizen who owns a linked complaint can verify
6. On valid code: status changes to `resolved`, code is cleared
7. Invalid code: returns 400, audit-logged as "failure"

Status changes to any non-"resolved" value (e.g. `open` → `in-progress`) skip this flow entirely.

---

## Department Mapping

Complaint categories map to real Coimbatore-specific operational bodies:

| Category | Department |
|----------|------------|
| Roads | CCMC Engineering Wing |
| Water Supply | TWAD Board - Coimbatore Division |
| Waste Management | CCMC Health Department |
| Sanitation | CCMC Engineering Wing |
| Street Lighting | TANGEDCO - Coimbatore Region |
| Electricity | TANGEDCO - Coimbatore Region |
| Public Health | CCMC Health Department |

Full mapping in `ai-engine/backend/department_map.py`.

---

## API Endpoints

### Authentication

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | No | Register citizen account |
| POST | `/auth/login` | No | Login, returns httpOnly JWT cookie |
| POST | `/auth/logout` | Yes | Clear auth cookie |
| GET | `/auth/me` | Yes | Current user profile |
| PUT | `/auth/profile` | Yes | Update profile |

### Complaints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/complaints` | Citizen | Submit new complaint (triggers ML pipeline) |
| GET | `/complaints/{id}/status` | Yes | Check ML pipeline processing status |
| GET | `/complaints/{id}` | Citizen | Get complaint detail |
| GET | `/complaints/my` | Citizen | List my complaints |
| POST | `/complaints/{id}/upload` | Citizen | Upload photo evidence (jpg/png, max 5MB) |
| GET | `/complaints/{id}/photo` | Citizen | Get presigned photo URL |
| GET | `/complaints/coordinates` | No | All complaint coordinates for map |
| GET | `/complaints/ward/{ward}` | Councillor/Commr/Exec/Offr | Ward-specific complaints |

### Incidents

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/incidents` | Yes | List all incidents |
| GET | `/incidents/{id}` | Yes | Get incident detail |
| PATCH | `/incidents/{id}/status` | Officer/Exec/Commr | Update status |
| POST | `/incidents/merge` | Officer/Exec/Commr | Merge multiple incidents |
| POST | `/incidents/{id}/split/{complaint_id}` | Officer/Exec/Commr | Split complaint to new incident |
| POST | `/incidents/{id}/escalate` | Councillor/Commr/Exec | Escalate incident |
| POST | `/incidents/{id}/verify-resolution` | Citizen | Verify resolution (6-digit code) |
| GET | `/incidents/escalated` | MLA/Collector/Councillor/Commr/Exec | List escalated incidents |
| POST | `/incidents/auto-escalate` | System | Auto-escalate aging incidents |

### Classification & AI

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/classify` | Yes | Classify complaint text |
| POST | `/classify/batch` | Yes | Batch classification |
| POST | `/classify/predict` | Yes | Predict category (alias) |
| POST | `/cluster` | Yes | Cluster complaints |
| POST | `/cluster/similar` | Yes | Find similar complaints |
| GET | `/cluster/config` | No | Clustering configuration |
| POST | `/priority` | Yes | Calculate priority score |
| POST | `/priority/batch` | Yes | Batch priority |
| GET | `/priority/rules` | No | Active priority rules |

### Dashboard & Analytics

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/dashboard` | Yes | Summary data |
| GET | `/dashboard/metrics` | No | Model performance metrics |
| GET | `/dashboard/trend` | Yes | Trend data (last 6 months) |
| GET | `/dashboard/analytics` | Yes | Comprehensive analytics |

### Executive / Admin

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/executive/summary` | Yes | Executive summary |
| GET | `/executive/ward-health` | Yes | Ward health scores |
| GET | `/executive/department-workload` | Yes | Department workload |
| GET | `/admin/officers` | Executive | List officers |
| POST | `/admin/officers` | Executive | Create officer |
| PATCH | `/admin/officers/{id}/disable` | Executive | Disable officer |
| PATCH | `/admin/officers/{id}/enable` | Executive | Enable officer |
| GET | `/admin/departments` | Executive | Department metrics |
| GET | `/admin/departments/list` | Executive | All departments |
| GET | `/admin/system-health` | Executive | System health |
| GET | `/admin/audit-logs` | Executive | Audit logs |

### Spatial

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/spatial/heatmap` | Yes | Ward heatmap |
| GET | `/spatial/hotspots` | Yes | Crime/issue hotspots |
| GET | `/spatial/forecast` | Yes | Forecasting |
| GET | `/spatial/risk` | Yes | Risk analysis |
| POST | `/spatial/simulate` | Yes | Resource simulation |

### Predictive & Knowledge

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/predictions/summary` | Yes | Predictive analytics summary |
| GET | `/knowledge/summary` | Yes | Governance knowledge summary |
| GET | `/decision-support/summary` | Yes | Decision support summary |
| POST | `/copilot/chat` | Yes | Governance copilot chat |

### Notifications

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/notifications` | Yes | User's notifications |
| POST | `/notifications/{id}/read` | Yes | Mark as read |
| POST | `/notifications/read-all` | Yes | Mark all as read |

### System & Debug

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | Root info |
| GET | `/health` | No | Health check |
| POST | `/similar` | No | Keyword similarity |
| POST | `/debug/reseed` | Exec/Collector | Re-seed database |
| POST | `/debug/topup` | Exec/Collector | Top-up wards |
| GET | `/debug/wards` | Yes | Ward distribution |

---

## AI Pipeline

When a complaint is submitted (`POST /complaints`):

1. **Classification** — ML model (TF-IDF + Logistic Regression) predicts category from English text. Falls back to heuristic keyword matching if model unavailable.
2. **Tamil Fallback** — If text contains ≥20% Tamil Unicode characters, uses keyword-based classification (`tamil_fallback.py`). Returns `method: "tamil_keyword_fallback"`.
3. **Duplicate Detection** — Sentence-transformer embeddings + cosine similarity against recent (90-day) complaints in same ward/category. Threshold: 80% confidence. If duplicate, merges into existing incident.
4. **Incident Create/Merge** — New complaints get a new incident; duplicates merge into existing (increments `cluster_size`).
5. **Priority Scoring** — Multi-factor score (0–100) considering cluster size, age, category, location. Labels: Critical, High, Medium, Low.
6. **Notifications** — Citizen notified of created/merged status; department officers notified of new assignment.

Pipeline runs inline via `asyncio.create_task` (no separate worker needed for Render free tier). Status is tracked in Redis (falls back to DB query).

---

## Technology Stack

- **Backend**: Python 3.14, FastAPI, SQLAlchemy 2.0, Pydantic v2
- **Database**: SQLite (dev), PostgreSQL (prod via `DATABASE_URL`)
- **Auth**: JWT (httpOnly + SameSite=None cookie), bcrypt passwords
- **AI/ML**: scikit-learn (TF-IDF + Logistic Regression), sentence-transformers, NumPy
- **Storage**: S3-compatible (Backblaze B2 / MinIO) with presigned URLs
- **Queue**: Redis (arq) for status tracking; optional worker (currently using inline pipeline)
- **Rate Limiting**: Redis-backed per-IP limiting (falls open if Redis unavailable)
- **Classification Models**: Pre-trained `.pkl` files in `ai-engine/models/classification/`

---

## Known Limitations

1. **Multilingual embedding model deferred** — The Tamil keyword fallback (Phase 1.5) is a temporary stopgap. A proper multilingual embedding model (IndicBERT / LaBSE) was deferred for memory reasons (Render free tier: 512 MB RAM). The current TF-IDF model has zero vocabulary overlap with Tamil Unicode text.
2. **S3 storage optional** — Photo upload requires S3-compatible storage env vars. Falls back gracefully (returns 502 if not configured).
3. **Redis optional** — Rate limiting, job queue, and pipeline status tracking fall open/fall back gracefully when Redis is unavailable.
4. **Duplicate detection model download** — Sentence-transformers downloads `all-MiniLM-L6-v2` on first startup (≈90 MB). Can cause cold-start delays on free tier.
5. **SQLite in development** — Production deployments should use PostgreSQL (set `DATABASE_URL` env var).
6. **No real SMS/email** — Verification codes and notifications are in-app only. No SMS gateway or email service is integrated.
7. **Seed data is synthetic** — Complaint templates reference real Coimbatore areas but are procedurally generated for demo/testing.
