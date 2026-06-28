# Project Structure

This project is divided into a frontend React application and a Python-based AI backend.

## 💻 Frontend (`/`)
- `src/`: Application source code.
    - `components/`: Reusable UI components (Header, KPI cards, Sidebar).
    - `pages/`: Main views of the application.
        - `Overview.tsx`: Executive dashboard.
        - `IncidentFeed.tsx`: Prioritized list of issues.
        - `Clusters.tsx`: Deep-dive cluster explorer.
        - `Analysis.tsx`: Model performance metrics.
        - `Methodology.tsx`: Documentation of the AI pipeline.
    - `services/`: API communication layer (`api.ts`).
    - `types/`: TypeScript interfaces for API responses.
    - `data/`: Local fallback data (legacy).
- `public/`: Static assets.

## 🧠 AI Engine (`/ai-engine`)
- `backend/`: FastAPI implementation.
    - `app.py`: Main entry point, server configuration, and app initialization.
    - `routes.py`: Definition of REST endpoints and API routing.
    - `services.py`: Business logic layer and model orchestration.
    - `models.py`: Pydantic schemas for request/response validation.
- `models/`: Storage for trained ML artifacts.
    - `classification/`: Contains `classifier.pkl`, `vectorizer.pkl`, and `label_encoder.pkl`.
- `data/`: Raw and processed datasets (e.g., NYC311 data).
- `priority/`: Logic for the priority scoring engine.
- `clustering/`: Logic for semantic similarity and duplicate detection.
- `classification/`: Logic for category prediction.
- `outputs/`: Generated reports and dashboard JSON summaries.
