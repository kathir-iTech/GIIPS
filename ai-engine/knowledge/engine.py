"""
AI Governance Knowledge Engine.

Handles Root Cause Analysis, Cascade Impact, and Policy Recommendations.
"""

from typing import Dict, Any, List, Optional

class GovernanceKnowledgeEngine:
    def __init__(self):
        pass

    # F11: Rule-based root cause analysis. Category -> likely root cause
    # mapping, keyed on recurrence of similar complaints (same ward + category).
    _ROOT_CAUSE_MAP = {
        "Roads": "Infrastructure aging or insufficient maintenance budget",
        "Water Supply": "Aging pipeline network or inadequate supply capacity",
        "Waste Management": "Contractor inefficiency or insufficient collection frequency",
        "Sanitation": "Inadequate desilting schedule before monsoon",
        "Street Lighting": "Lack of preventive maintenance contracts",
        "Electricity": "Aging transformers or overloaded feeders",
        "Public Health": "Poor waste disposal practices or sanitation gaps",
    }

    def get_root_cause(self, incident_id: str, db=None) -> Dict[str, Any]:
        """Infers root causes from incident + complaint recurrence data.

        db is an optional SQLAlchemy Session. When omitted, a short-lived
        session is opened to the default database; if that also fails, a
        static cause is returned.
        """
        incident = None
        category = None
        ward = None
        recurrence_count = 0
        owned_session = None

        try:
            if db is None:
                from database import SessionLocal
                owned_session = SessionLocal()
                db = owned_session

            from database import Incident, Complaint
            from datetime import datetime, timedelta
            incident = db.query(Incident).filter(Incident.id == incident_id).first()

            if incident is not None:
                category = incident.category
                ward = incident.ward
                ninety_days_ago = datetime.utcnow() - timedelta(days=90)
                recurrence_count = db.query(Complaint).filter(
                    Complaint.ward == ward,
                    Complaint.predicted_category == category,
                    Complaint.created_at >= ninety_days_ago,
                ).count()
        except Exception:
            incident = None
        finally:
            if owned_session is not None:
                try:
                    owned_session.close()
                except Exception:
                    pass

        if category is not None and ward is not None and recurrence_count >= 3:
            cause = self._ROOT_CAUSE_MAP.get(category, "Isolated incident, no clear pattern yet")
            return {
                'incident_id': incident_id,
                'top_root_causes': [
                    {
                        'cause': cause,
                        'confidence': 0.8,
                        'evidence': f"{recurrence_count} similar complaints in Ward {ward} in last 90 days",
                    }
                ]
            }

        return {
            'incident_id': incident_id,
            'top_root_causes': [
                {
                    'cause': 'Isolated incident, no clear pattern yet',
                    'confidence': 0.8,
                    'evidence': f"{recurrence_count} similar complaints in Ward {ward or 'Unknown'} in last 90 days",
                }
            ]
        }

    def analyze_cascade_impact(self, incident_id: str) -> List[Dict[str, Any]]:
        """Predicts cascade impact chain."""
        return [
            {'stage': 'Road damage', 'impact': 'Severe'},
            {'stage': 'Water stagnation', 'impact': 'High'},
            {'stage': 'Traffic congestion', 'impact': 'Moderate'}
        ]

    def simulate_scenario(self, query: str) -> Dict[str, Any]:
        """Simulates government actions."""
        return {
            'query': query,
            'expected_outcome': '20% reduction in backlog',
            'sla_improvement': '15%',
            'budget_impact': 10000
        }

    def get_policy_recommendations(self) -> List[Dict[str, Any]]:
        """Generates policy recommendations."""
        return [
            {'recommendation': 'Increase road maintenance budget', 'expected_benefit': '25% risk reduction', 'confidence': 0.9}
        ]

    def get_risk_index(self) -> Dict[str, Any]:
        """Returns governance risk indices."""
        return {'district_risk_index': 65, 'infrastructure_risk_index': 45}
