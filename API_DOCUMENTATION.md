# API_DOCUMENTATION.md

GIIPS exposes a RESTful API built with FastAPI for intelligence processing and data retrieval.

| Endpoint | Method | Purpose |
| :--- | :--- | :--- |
| `/dashboard` | GET | Returns summary metrics for the executive dashboard. |
| `/classify` | POST | Classifies a new complaint text into a category. |
| `/cluster` | POST | Groups a list of complaints into incident clusters. |
| `/priority` | POST | Calculates priority score for an incident object. |
| `/incidents` | GET | Retrieves a list of prioritized incidents. |
| `/incidents/{id}` | GET | Returns detailed view of a specific incident cluster. |
| `/spatial/heatmap` | GET | Returns ward-wise incident distribution for spatial visualization. |
| `/spatial/forecast` | GET | Returns forecasted incident volumes (time-series). |
| `/complaints` | POST | Submits a new citizen complaint for processing. |

## Detailed Endpoint Specifications

### 1. Submit Complaint
- **URL**: `/complaints`
- **Method**: `POST`
- **Request Body**: `{ "title": "string", "description": "string", "location": "string", "ward": "string" }`
- **Response**: `{ "complaintId": "uuid", "incidentId": "uuid", "predictedCategory": "string", "priority": "string", "duplicate": boolean }`
- **Purpose**: Ingests new complaints and triggers the automated AI processing pipeline.

### 2. Dashboard Metrics
- **URL**: `/dashboard`
- **Method**: `GET`
- **Response**: `{ "totalComplaints": int, "uniqueIncidents": int, "workloadReduction": float, ... }`
- **Purpose**: Provides high-level metrics for dashboard visualization.
