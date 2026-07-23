"""
Predictive Governance AI Engine.

Forecasts future incidents using statistical trend analysis.
All predictions are based on transparent formulas using real incident data.
"""

from typing import Dict, Any, List, Optional
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session

class PredictiveEngine:
    def __init__(self):
        pass

    def forecast_complaints(self, timeframe: str, history: Optional[List[int]] = None) -> Dict[str, Any]:
        """Forecast complaint volume using linear extrapolation of historical trend.
        
        Confidence is computed as the R² of the linear fit — measures how well
        the trend line explains observed variance. Returns 0.0 for poor fits.
        """
        if history is None:
            history = []
        history = np.array(history, dtype=float)
        if len(history) < 2:
            return {
                'timeframe': timeframe,
                'predicted_volume': float(history[-1]) if len(history) else 0.0,
                'confidence': 0.0,
                'model': 'linear_trend'
            }
        x = np.arange(len(history))
        coeffs = np.polyfit(x, history, 1)

        # R² confidence — how well the linear model explains observed variance
        residuals = history - np.polyval(coeffs, x)
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((history - np.mean(history)) ** 2)
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        confidence = max(0.0, min(1.0, r_squared))

        days_ahead = 1 if timeframe == 'tomorrow' else 3
        future_x = np.arange(len(history), len(history) + days_ahead)
        forecast = np.polyval(coeffs, future_x)

        return {
            'timeframe': timeframe,
            'predicted_volume': max(0, float(forecast[-1])),
            'confidence': round(confidence, 4),
            'model': 'linear_trend'
        }

    def predict_escalation(self, incident) -> Dict[str, Any]:
        """Predict escalation probability from real incident fields.
        
        Transparent weighted formula using the incident's own data:
          risk = 0.35 × norm(cluster_size) + 0.25 × norm(days_open) + 0.40 × norm(priority_score)
        
        Each component and its contribution is returned in 'factors' for auditability.
        """
        # Normalize cluster_size: cap at 20 so a single massive cluster doesn't saturate
        CLUSTER_CAP = 20
        cluster_factor = min(incident.cluster_size or 1, CLUSTER_CAP) / CLUSTER_CAP

        # Normalize days_open: linear up to 30 days
        DAYS_CAP = 30
        aging_factor = min(incident.days_open or 0, DAYS_CAP) / DAYS_CAP

        # Priority score: already 0-100 from the pipeline
        priority_factor = (incident.priority_score or 0.0) / 100.0

        # Weighted sum
        W_CLUSTER = 0.35
        W_AGING = 0.25
        W_PRIORITY = 0.40
        probability = min(1.0, W_CLUSTER * cluster_factor + W_AGING * aging_factor + W_PRIORITY * priority_factor)
        probability = round(probability, 4)

        # Risk level buckets
        if probability > 0.80:
            risk_level = 'CRITICAL'
        elif probability > 0.55:
            risk_level = 'HIGH'
        elif probability > 0.30:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'

        return {
            'incident_id': incident.id,
            'probability': probability,
            'risk_level': risk_level,
            'factors': [
                {'factor': 'Cluster Size (public impact)',     'weight': W_CLUSTER,  'value': round(cluster_factor, 4)},
                {'factor': 'Days Open (aging)',                'weight': W_AGING,    'value': round(aging_factor, 4)},
                {'factor': 'Priority Score (severity)',        'weight': W_PRIORITY, 'value': round(priority_factor, 4)},
            ]
        }

    # TODO: Stub — implement with real SLA/resource logic before wiring to any route
    def predict_sla_failure(self, incident_id: str) -> Dict[str, Any]:
        """Predict SLA failure probability. (STUB — not in use.)"""
        return {
            'incident_id': incident_id,
            'probability': 0.35,
            'estimated_delay_hours': 4,
            'risk_level': 'MEDIUM'
        }

    # TODO: Stub — implement with real resource allocation logic before wiring to any route
    def predict_resources(self, incident_id: str) -> Dict[str, Any]:
        """Predict required resources. (STUB — not in use.)"""
        return {
            'incident_id': incident_id,
            'engineers': 2,
            'field_workers': 3,
            'vehicles': 1,
            'estimated_hours': 12
        }

    def generate_alerts(self, db: Session) -> List[Dict[str, Any]]:
        """Generate early warning alerts from real complaint volume spikes.
        
        Compares complaint counts per (ward, category) in the last 7 days vs
        the previous 7 days. Returns alerts where volume increased >= 50%
        (and baseline >= 3 complaints to avoid noise from tiny numbers).
        Returns empty list if no genuine spikes are found.
        """
        now = datetime.utcnow()
        last_7_start = now - timedelta(days=7)
        prev_14_start = now - timedelta(days=14)

        # Import here to avoid circular import issues
        from backend.database import Complaint

        # Current 7-day window: group by (ward, predicted_category)
        curr_rows = db.query(
            Complaint.ward,
            Complaint.predicted_category,
            func.count(Complaint.id)
        ).filter(
            Complaint.created_at >= last_7_start
        ).group_by(Complaint.ward, Complaint.predicted_category).all()

        # Previous 7-day window
        prev_rows = db.query(
            Complaint.ward,
            Complaint.predicted_category,
            func.count(Complaint.id)
        ).filter(
            Complaint.created_at >= prev_14_start,
            Complaint.created_at < last_7_start
        ).group_by(Complaint.ward, Complaint.predicted_category).all()

        prev_map = {}
        for ward, cat, cnt in prev_rows:
            prev_map[(ward, cat)] = cnt

        alerts = []
        for ward, cat, curr_cnt in curr_rows:
            if not ward or not cat:
                continue
            prev_cnt = prev_map.get((ward, cat), 0)
            if prev_cnt < 3:
                continue  # noise floor: need meaningful baseline
            growth_pct = ((curr_cnt - prev_cnt) / prev_cnt) * 100
            if growth_pct >= 50:
                severity = 'HIGH' if growth_pct >= 100 else 'MEDIUM'
                alerts.append({
                    'alert': f"{cat} complaints in Ward {ward} increased {growth_pct:.0f}% in the last 7 days.",
                    'severity': severity
                })

        # Sort by growth severity descending, return top 5
        alerts.sort(key=lambda a: 1 if a['severity'] == 'HIGH' else 0, reverse=True)
        return alerts[:5]
