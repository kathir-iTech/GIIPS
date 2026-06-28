# API Documentation

All endpoints are prefixed with `http://localhost:8000`.

## 📊 Dashboard & Metrics

### `GET /dashboard`
Returns high-level summary statistics for the executive view.
- **Response**:
  - `totalComplaints`: Total raw reports.
  - `uniqueIncidents`: Total unique issues identified.
  - `workloadReduction`: Percentage reduction in reports.
  - `criticalIncidents`: Count of Critical priority issues.
  - `categoryDistribution`: List of category counts.

### `GET /dashboard/metrics`
Returns model performance data.
- **Response**: Accuracy, Precision, Recall, and F1 Score.

### `GET /dashboard/trend`
Returns historical trend data for visualization.
- **Response**: Monthly counts of complaints and incidents.

## 🤖 AI Processing

### `POST /classify`
Categorizes a complaint based on its text.
- **Payload**: `{ "text": "string", "detail": "string" }`
- **Response**: Predicted category and confidence score.

### `POST /cluster`
Groups a list of complaints into unique incidents.
- **Payload**: `{ "complaints": [...], "text_key": "text" }`
- **Response**: Mapping of complaint IDs to cluster labels.

### `POST /priority`
Calculates a priority score for a specific incident.
- **Payload**: `{ "incident_id": "string", "cluster_size": int, ... }`
- **Response**: Priority score, label (Critical/High/Medium/Low), and contributing factors.

### `POST /similar`
Finds similar complaints to a given text.
- **Payload**: `{ "text": "string", "complaints": [...], "threshold": float }`
- **Response**: List of similar complaints with similarity scores.

## 📋 Incident Management

### `GET /incidents`
Returns a list of all identified incidents.
- **Query Params**: `priority`, `category`, `limit`.
- **Response**: List of Incident objects including priority scores and summaries.

### `GET /incidents/{incident_id}`
Returns detailed information about a specific cluster.
- **Response**: Full incident details and the list of all linked complaints.

## 🛠 System

### `GET /health`
Check backend operational status.
- **Response**: Status and model loading confirmation.
