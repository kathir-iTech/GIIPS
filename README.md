# GIIPS: Governance Incident Intelligence & Prioritization System

GIIPS is an advanced AI-powered intelligence layer designed to transform raw, high-volume citizen grievance data into actionable, prioritized municipal incidents. By utilizing Natural Language Processing (NLP) and semantic clustering, GIIPS eliminates administrative redundancy and ensures that critical public issues are addressed with data-driven urgency.

## 🚩 Problem Statement
Municipalities are routinely overwhelmed by thousands of individual complaints. Many of these reports describe the same underlying incident (e.g., 50 residents reporting the same burst water pipe), leading to:
- **Administrative Redundancy**: Massive duplication of effort in triage and processing.
- **Delayed Response Times**: High volume leads to critical issues getting buried.
- **Inconsistent Prioritization**: Lack of a standardized, objective scoring mechanism.
- **Resource Wastage**: Inefficient allocation of municipal field teams.

## ✨ Key Features
- **AI-Powered Semantic Clustering**: Automatically groups duplicate complaints into unique, actionable incidents.
- **Dynamic Priority Intelligence**: Calculates an objective priority score based on severity, urgency, and public impact (location/category/age).
- **Executive Intelligence Dashboard**: High-level overview of workload reduction metrics and city-wide health scores.
- **Spatial Intelligence**: Geospatial visualization of incident hotspots and future demand forecasting.
- **Decision Support**: Automated recommendation system for field team allocation.

## 🤖 AI Pipeline
1. **Ingestion**: Complaints enter via web/mobile/call-center APIs.
2. **Classification**: NLP models categorize issues (e.g., "Water Supply", "Sanitation").
3. **Clustering**: Semantic similarity matching groups duplicate reports into single incident objects.
4. **Scoring**: A weighted engine calculates incident priority based on cluster size, age, category, and infrastructure proximity.

## 🛠 Tech Stack
### Frontend
- **React (TypeScript + Vite)**: High-performance administrative UI.
- **Plotly.js**: Advanced data visualization (pie charts, bar charts, scatter plots).
- **Lucide React**: Modern iconography.

### Backend
- **FastAPI (Python)**: High-performance, asynchronous REST API.
- **Scikit-learn**: Machine Learning pipeline for classification & clustering.
- **SQLAlchemy (SQLite)**: Robust ORM for data persistence.
- **Pydantic**: Strict data validation & schema enforcement.

## 🚀 Installation

### Prerequisites
- Python 3.9+
- Node.js 18+

### Backend Setup
```bash
cd ai-engine/backend
pip install -r requirements.txt
python app.py
```
*(Backend runs at `http://localhost:8000`)*

### Frontend Setup
```bash
npm install
npm run dev
```
*(Frontend runs at `http://localhost:5173`)*

## 📸 Screenshots (Placeholders)
- *[Placeholder: Dashboard Overview with Workload Reduction Metric]*
- *[Placeholder: Incident Feed with Priority Scoring]*
- *[Placeholder: Spatial Intelligence Heatmap]*

## 🔮 Future Scope
- **Computer Vision Integration**: Automatic verification of complaint photos (e.g., verifying a pothole).
- **GIS Integration**: Deep integration with municipal GIS platforms.
- **Multi-lingual LLM support**: Support for regional dialects via fine-tuned LLMs.
