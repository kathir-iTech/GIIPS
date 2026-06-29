# DATABASE_SCHEMA.md

GIIPS uses SQLite for lightweight, reliable data persistence.

## 1. Table: `complaints`
Stores individual raw citizen complaints.

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | String (PK) | Unique complaint identifier |
| `title` | String | Short title |
| `description` | Text | Detailed description |
| `ward` | String | Municipal ward |
| `incident_id` | FK | Foreign key to `incidents` table |
| `predicted_category`| String | AI-predicted category |
| `created_at` | DateTime | Timestamp of ingestion |

## 2. Table: `incidents`
Stores aggregated clusters of similar complaints.

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | String (PK) | Unique incident identifier |
| `category` | String | Unified category |
| `cluster_size` | Integer | Number of complaints grouped |
| `priority_score` | Float | Calculated priority (0-100) |
| `priority_label` | String | Critical/High/Medium/Low |
| `status` | String | open/in-progress/resolved |

## 3. Table: `priority_history`
Stores the evolution of an incident's priority score.

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | String (PK) | Unique record identifier |
| `incident_id` | FK | Foreign key to `incidents` |
| `old_score` | Float | Score before change |
| `new_score` | Float | Score after change |
| `reason` | Text | Justification for change |
