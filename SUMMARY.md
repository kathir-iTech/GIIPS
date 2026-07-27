# GIIPS — Governance Incident Intelligence & Prioritization System
2: 
3: **A civic-complaint triage platform for Coimbatore, Tamil Nadu.**
4: 
5: Live: `https://giips.vercel.app` · Backend: `https://giips-backend.onrender.com`  
6: Tech: React 19 + FastAPI + PostgreSQL + TF-IDF/Logistic Regression
7: 
8: ---
9: 
10: ## What GIIPS Does
11: 
12: Citizens file complaints (road damage, water supply failure, garbage accumulation, etc.) through a web portal. GIIPS automatically classifies each complaint by category, detects near-duplicates, groups related complaints into incidents, assigns a priority score, and routes the result to the responsible municipal department. Citizens track resolution, receive notifications, verify outcomes, rate satisfaction, and can appeal unsatisfactory resolutions.
13: 
14: The system targets **Coimbatore City Municipal Corporation (CCMC)** — 100 wards across 5 zones — with department mappings to real bodies: CCMC Engineering Wing, TWAD Board (water), TANGEDCO (electricity), CCMC Health Department (sanitation), and others.
15: 
16: ---
17: 
18: ## The AI Pipeline — What Actually Runs
19: 
20: When a citizen submits a complaint, the following executes in a single async task (no external worker):
21: 
22: ### 1. Classification (TF-IDF + Logistic Regression)
23: A trained model (`classifier.pkl`) predicts the category from complaint text + title. The model was trained on an expanded synthetic dataset of ~700 Coimbatore-style complaints across 7 categories (100 per class) with `min_df=1`. **Measured accuracy: 79.56%** (up from 57.1% with the old 32-sample dataset). When confidence is low or the ML model errors, a keyword-overlap fallback uses the same 7 canonical categories. Tamil text is handled by a separate keyword matcher (`tamil_fallback.py`). The method used (`ml_model`, `tamil_keyword_fallback`, or `heuristic_fallback`) is returned in every response.
24: 
25: ### 2. Duplicate Detection (Jaccard Keyword Overlap / Sentence Embedding Cosine)
26: New complaints are compared against the last 90 days of existing complaints (up to 1000) using the `DuplicateDetector` from `ai-engine/duplicate_detection/engine.py`. Two backends exist:
27: 
28: - **ML path** (when `sentence-transformers` is available): `all-MiniLM-L6-v2` embeddings + `NearestNeighbors(metric='cosine')`. Confidence is a weighted blend of text similarity (60%), geographic proximity (30%), and category match (10%).
29: - **Fallback path** (what actually runs on Render's 512 MB tier — `sentence-transformers` is commented out in `requirements.txt`): **Jaccard similarity** on word sets: `|new_words ∩ comp_words| / |new_words ∪ comp_words|`.
30: 
31: If confidence exceeds 0.8, the complaint is merged into the existing incident. A merge reason is stored, and the citizen is notified.
32: 
33: ### 3. Incident Grouping
34: Non-duplicate complaints become new incidents. Complaints in the same `(category, ward)` bucket are clustered together (prefix-overlap fallback — no embedding model; SBERT/DBSCAN exists but is not wired in due to memory constraints on Render's free tier).
35: 
36: ### 4. Priority Scoring (Rule-Based)
37: Priority is calculated from: cluster size, days since first complaint, category weight, and keyword severity signals. Scores range 0–100 mapping to Critical (90+), High (75–89), Medium (50–74), Low (0–49). An additional 8 situational rules adjust scores (e.g., monsoon keywords, school proximity).
38: 
39: ### 5. Routing + Notification
40: The incident is assigned a department via a lookup table (`category → CCMC body`). Notifications are created for the citizen and for all active officers in the responsible department. Aging notifications fire at 4 days (warning) and 8 days (critical).
41: 
42: ---
43: 
44: ## What's Verified with Real Coimbatore Data
45: 
46: The following operate against actual CCMC ward geography and department structure, not placeholders:
47: 
48: - **100 wards across 5 zones** (North, East, Central, West, South) with area-level locality names — exact per CCMC delimitation notifications.
49: - **Department routing** maps each complaint category to the real responsible body: CCMC Engineering Wing (roads, drainage), TWAD Board (water), TANGEDCO (electricity), CCMC Health Department (sanitation/public health), and others.
50: - **10,000 synthetic complaints** seeded with Coimbatore-specific locations, ward numbers, zone references, and realistic civic descriptions (full Tamil-English text sample below). These populate all dashboards, charts, leaderboards, and auto-escalation triggers with production-like data.
51: 
52: > *Sample seeded complaint:* "Road damage near Mettupalayam Road junction causing accidents daily [COMP-000042 | Ward 34 | Central Zone | Coimbatore]"
53: 
54: - **43 Tamil Nadu government departments** mapped in a separate lookup (used for executive-level oversight views).
55: - **Citizen verification codes** (6-digit) are real — generated on resolution, sent via notification, and confirmed by the citizen before status changes to "resolved."
56: - **Appeal flow** — citizens can appeal resolved/closed incidents with a reason; the incident reopens, priority is bumped, and department officers receive a notification. Verified live on production.
57: - **Notifications** — 11 notification types delivered to both citizens and department officers. Verified live that officers receive department-targeted alerts (e.g., "appeal_filed" reaches CCMC Engineering Wing officers).
- **Priority scoring enhancements** — Seasonal monsoon weighting boosts category severity by +0.05 for Water Supply, Sanitation, and Road Infrastructure complaints during October–December. Landmark proximity detection applies a +8-point boost to complaints within 300m of five verified Coimbatore landmarks (Coimbatore Medical College Hospital, Gandhipuram Bus Stand, Coimbatore Railway Station, TIDEL Park, PSG College of Technology). Both adjustments appear as named factors in the priority explanation output.
58: 
59: ---
60: 
61: ## Current Limitations & Roadmap
62: 
63: ### ML Model Quality
64: | Issue | Status |
65: |-------|--------|
66: | Classification accuracy 79.56% (was 57.1%) | **Phase 2 improvement.** Expanded synthetic dataset (~700 Coimbatore-style complaints, 7 categories, `min_df=1`). New model covers all 7 categories with minimum per-class recall of 65%. |
67: | No Tamil NLP model deployed | Keyword fallback only. IndicBERT/LaBSE reverted during Phase 1.5 for 512MB RAM limit. |
68: | No embedding-based clustering | SBERT + DBSCAN code exists but is not wired in (memory). Current clustering uses text-prefix overlap. |
69: 
70: **Planned (Phase 3):** Fine-tune a lightweight IndicBERT on a curated TN complaint corpus. Replace synthetic training data with real TN complaint dataset when available. Deploy sentence-transformers if the hosting tier allows.
71: 
72: ### Infrastructure
73: | Issue | Status |
74: |-------|--------|
75: | Render free tier (512MB RAM, cold starts) | Constraints the ML stack. No PyTorch/TensorFlow runtime. |
76: | No message queue | Pipeline runs inline via `asyncio.create_task`. Not durable across restarts. |
77: | No database migrations | Schema changes via `ALTER TABLE` in startup code. Alembic deferred. |
78: | No test suite | Zero automated tests (backend or frontend). |
79: | No CI/CD pipeline | Both Vercel and Render auto-deploy from `main`; no GitHub Actions. |
80: 
81: **Planned (Phase 3):** Migrate to a paid hosting tier, add a durable job queue (Redis + arq or Celery), set up Alembic for migrations, and establish a CI pipeline with integration tests against the live API.
82: 
83: ### Frontend
84: | Issue | Status |
85: |-------|--------|
86: | No loading skeletons | Spinner-only during data fetches. |
87: | No error toast system | Errors appear inline, not in a centralized snackbar. |
88: | Real-time notifications | WebSocket push for near-instant updates (auth-scoped with short-lived tokens, exponential backoff reconnection), with 30s polling as fallback. |
89: | Address geocoder | Free Nominatim API — rate-limited, 500ms debounce. |
90: 
91: ### Feature Gaps (Phase 3+)
92: - Real Tamil Nadu complaint dataset (replace NYC 311 training data)
93: - Full-text search across complaints (PostgreSQL tsvector or Elasticsearch)
94: - Real-time notifications via WebSocket/SSE
95: - Mobile application (React Native)
96: - SMS / WhatsApp notification channel
97: - GIS shapefile import for precise ward boundary overlays
98: - Data export (CSV, PDF reports)
99: - Multi-language beyond English and Tamil (Telugu, Kannada, Malayalam, Hindi)
100: 
101: ---
102: 
103: ## System Metrics (Live, Post-Deploy)
104: 
105: | Metric | Value |
106: |--------|-------|
107: | Backend API endpoints | 77 |
108: | Database tables | 7 |
109: | User roles | 7 (Citizen, Officer, Executive, Commissioner, Councillor, MLA, Collector) |
110: | Frontend routes | 24 |
111: | ML classification categories | 7 model-based + 2 heuristic-fallback (Pollution, Traffic — legacy, unmapped) |
112: | Duplicate detection threshold | 0.8 cosine similarity |
113: | Aging notification thresholds | 4 days (warning), 8 days (critical) |
114: | Notification types | 11 |
115: | i18n keys per language | ~916 |
116: | Rate limits | 5/min (auth), 10/min (complaints) |
117: | Token expiry | 60 minutes |
118: | Photo upload limit | 5 MB (jpg/png) |
119: | Seed data | 10,000 complaints, ~150 incidents, 9 demo users |
120: | Deployed | Vercel (frontend) + Render (backend) + Backblaze B2 (photo storage) |
