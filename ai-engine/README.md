# GIIPS AI Engine

Governance Incident Intelligence & Prioritization System - AI Backend

## Overview

The GIIPS AI Engine provides machine learning capabilities for:

1. **Complaint Classification** - Categorize incoming complaints using TF-IDF + Logistic Regression
2. **Duplicate Detection** - Cluster similar complaints using SentenceTransformer embeddings + DBSCAN
3. **Priority Scoring** - Calculate explainable priority scores for incidents

## Installation

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

### 1. Train the Classifier

```bash
cd ai-engine
python -m classification.train --data ../nyc311_working.csv --output ./models/classification
```

### 2. Run the FastAPI Backend

```bash
cd ai-engine/backend
python app.py
```

The API will be available at `http://localhost:8000`

API Documentation: `http://localhost:8000/docs`

## Directory Structure

```
ai-engine/
├── datasets/           # Data files (place nyc311_working.csv here)
├── models/             # Trained model artifacts
│   ├── classification/
│   └── clustering/
├── outputs/            # Generated outputs and logs
├── notebooks/          # Jupyter notebooks for analysis
├── classification/     # Classification module
│   ├── train.py       # Model training
│   ├── predict.py     # Inference
│   ├── evaluate.py    # Evaluation metrics
│   └── utils.py       # Utilities
├── clustering/         # Clustering module
│   ├── cluster.py     # DBSCAN clustering
│   ├── evaluate.py    # Cluster evaluation
│   └── utils.py       # Utilities
├── priority/           # Priority engine
│   ├── priority.py    # Priority calculation
│   ├── rules.py       # Rule-based adjustments
│   └── utils.py       # Utilities
├── backend/            # FastAPI backend
│   ├── app.py         # Main application
│   ├── routes.py      # API routes
│   ├── models.py      # Pydantic models
│   └── services.py    # Business logic
└── requirements.txt   # Python dependencies
```

## API Endpoints

### Classification

**POST /classify**

Classify a complaint into a category.

```json
{
  "text": "Large pothole on Main Street near the traffic signal",
  "detail": "Causing damage to vehicles"
}
```

Response:
```json
{
  "predicted_category": "Road Infrastructure",
  "confidence": 0.92,
  "top_predictions": [...]
}
```

### Clustering

**POST /cluster**

Cluster complaints into duplicate incidents.

```json
{
  "complaints": [
    {"id": "1", "text": "Pothole on Main Street"},
    {"id": "2", "text": "Big hole on Main St"}
  ],
  "eps": 0.3
}
```

Response:
```json
{
  "n_clusters": 1,
  "n_noise": 0,
  "cluster_assignments": [...]
}
```

### Priority

**POST /priority**

Calculate priority score for an incident.

```json
{
  "incident_id": "INC-001",
  "cluster_size": 15,
  "first_complaint_date": "2024-01-01",
  "last_complaint_date": "2024-01-15",
  "category": "Water Supply",
  "location_hints": ["near hospital"]
}
```

Response:
```json
{
  "incident_id": "INC-001",
  "priority_score": 92.5,
  "priority_label": "Critical",
  "factors": [...],
  "explanation": "Large cluster with 15 complaints near hospital..."
}
```

### Dashboard

**GET /dashboard**

Get summary statistics for the dashboard.

## Model Training

### Classification Model

```python
from classification.train import ComplaintClassifier

# Initialize
classifier = ComplaintClassifier(
    max_features=10000,
    ngram_range=(1, 2)
)

# Train
classifier.train(texts, labels)

# Save
classifier.save(Path('./models/classification'))

# Load
classifier = ComplaintClassifier.load(Path('./models/classification'))
```

### Clustering Model

```python
from clustering.cluster import ComplaintClusterer

# Initialize
clusterer = ComplaintClusterer(
    model_name='all-MiniLM-L6-v2',
    eps=0.3,
    min_samples=2
)

# Cluster
results = clusterer.cluster_with_ward_separation(complaints)

# Save
clusterer.save(Path('./outputs/clustering'))
```

### Priority Engine

```python
from priority.priority import PriorityEngine

# Initialize with custom weights
engine = PriorityEngine(
    cluster_size_weight=0.30,
    age_weight=0.25,
    category_weight=0.25,
    location_weight=0.20
)

# Calculate priority for single incident
result = engine.compute(
    incident_id='INC-001',
    cluster_size=15,
    first_complaint_date='2024-01-01',
    last_complaint_date='2024-01-15',
    category='Water Supply',
    location_hints=['near hospital']
)

# Save config
engine.save(Path('./outputs/priority'))
```

## Priority Scoring

The priority score (0-100) is calculated as:

| Factor | Weight | Description |
|--------|--------|-------------|
| Cluster Size | 30% | Number of complaints (higher = more visibility) |
| Complaint Age | 25% | Days since first complaint (older = more urgent) |
| Category Severity | 25% | Issue type severity (Water = critical) |
| Location Importance | 20% | Proximity to schools, hospitals, etc. |

**Priority Labels:**
- Critical: 90-100
- High: 75-89
- Medium: 50-74
- Low: 0-49

## Rule-Based Adjustments

The system applies additional rules:

| Rule | Adjustment | Condition |
|------|------------|-----------|
| Safety Critical | +20 | Injury/danger keywords detected |
| School Proximity | +15 | Near school/playground |
| Hospital Proximity | +12 | Near medical facility |
| Public Health | +10 | Water/sewage issues |
| Long Standing | +8 | Unresolved > 21 days |
| Large Cluster | +7 | > 20 complaints |

## Development

### Running Tests

```bash
pytest tests/
```

### Jupyter Notebooks

```bash
jupyter notebook notebooks/
```

## Production Deployment

### Using Gunicorn

```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.app:app --bind 0.0.0.0:8000
```

### Using Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY ai-engine/ /app/
RUN pip install -r requirements.txt

CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "backend.app:app", "--bind", "0.0.0.0:8000"]
```

## Integration with Frontend

The FastAPI backend exposes CORS-enabled endpoints that can be consumed by the React frontend. Update the frontend's API service to point to the backend URL:

```typescript
// src/services/api.ts
const API_BASE = 'http://localhost:8000';

export const api = {
  classify: (text: string) => fetch(`${API_BASE}/classify`, {...}),
  cluster: (complaints: any[]) => fetch(`${API_BASE}/cluster`, {...}),
  priority: (incident: any) => fetch(`${API_BASE}/priority`, {...}),
  dashboard: () => fetch(`${API_BASE}/dashboard`)
};
```

## License

MIT License
