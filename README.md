# GIIPS - Governance Incident Intelligence & Prioritization System

GIIPS is an advanced AI-powered intelligence layer designed to transform raw citizen grievance data into actionable, prioritized incidents. By utilizing Natural Language Processing (NLP) and semantic clustering, GIIPS eliminates administrative redundancy and ensures that critical public issues are addressed first.

## 🚩 Problem Statement
Municipalities are often overwhelmed by thousands of individual complaints. Many of these are duplicates describing the same incident (e.g., 50 people reporting the same burst pipe), leading to:
- Massive duplication of administrative effort.
- Delayed response times due to workload volume.
- Inconsistent prioritization of urgent issues.
- Resource wastage in triage.

## ✅ The Solution
GIIPS introduces an intelligence pipeline that:
1. **Ingests** raw complaints from multiple sources.
2. **Clusters** semantically similar complaints into a single "Incident" using AI embeddings.
3. **Scores** each incident based on severity, urgency, and public impact.
4. **Prioritizes** the workload for municipal officers through a high-signal dashboard.

## ✨ Key Features
- **AI-Powered Clustering**: Automatically groups duplicate complaints into unique incidents.
- **Priority Intelligence**: Calculates a priority score using a weighted multi-factor engine.
- **Incident Explorer**: Deep-dive into clusters to see linked complaints and similarity scores.
- **Executive Dashboard**: High-level overview of workload reduction and critical hotspots.
- **Real-time Classification**: Automatically categorizes complaints into infrastructure types.

## 🛠 Tech Stack
### Frontend
- **React (TypeScript)**: UI Framework
- **Plotly.js**: Data visualization and network graphs
- **Lucide React**: Iconography
- **CSS3**: Custom modern styling

### Backend
- **FastAPI (Python)**: High-performance REST API
- **Scikit-learn**: Machine Learning for classification
- **Pydantic**: Data validation and schema enforcement
- **Uvicorn**: ASGI server

## 🚀 Installation & Setup

### Prerequisites
- Python 3.9+
- Node.js 18+
- npm / yarn

### Backend Setup
```bash
cd ai-engine/backend
pip install -r requirements.txt
python app.py
```
The backend will start at `http://localhost:8000`.

### Frontend Setup
```bash
npm install
npm run dev
```
The dashboard will be available at `http://localhost:5173`.

## 📁 Project Structure
- `src/`: React frontend source code.
- `ai-engine/backend/`: FastAPI server and business logic.
- `ai-engine/models/`: Trained ML models and encoders.
- `ai-engine/data/`: Dataset and filtered CSVs.

## 📡 API Endpoints (Summary)
- `GET /dashboard`: Summary metrics and distribution.
- `POST /classify`: Categorize complaint text.
- `POST /cluster`: Group complaints into incidents.
- `POST /priority`: Calculate priority score.
- `GET /incidents`: List prioritized incidents.
- `GET /incidents/{id}`: Detailed cluster view.

## 🔮 Future Scope
- **Image Analysis**: Integration of computer vision to verify complaint photos.
- **Geo-spatial Mapping**: Integration with GIS for heat-map visualizations.
- **Automated Dispatch**: API hooks to notify field officers automatically.
- **Multi-lingual Support**: Support for local regional dialects using multilingual LLMs.
