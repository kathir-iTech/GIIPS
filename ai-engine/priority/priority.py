"""
Priority Engine for GIIPS.

Computes explainable priority scores for identified incidents using
multiple weighted factors: cluster size, complaint age, category severity,
and location importance.
"""

import json
import pickle
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd


@dataclass
class PriorityFactor:
    """Represents a single factor contributing to priority score."""
    name: str
    raw_value: float
    normalized_value: float
    weight: float
    contribution: float
    description: str


@dataclass
class PriorityResult:
    """Complete priority calculation result."""
    incident_id: str
    priority_score: float
    priority_label: str
    factors: List[PriorityFactor]
    explanation: str
    timestamp: str


    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'incident_id': self.incident_id,
            'priority_score': round(self.priority_score, 1),
            'priority_label': self.priority_label,
            'factors': [
                {
                    'name': f.name,
                    'raw_value': round(f.raw_value, 2),
                    'normalized_value': round(f.normalized_value, 3),
                    'weight': round(f.weight, 3),
                    'contribution': round(f.contribution, 2),
                    'description': f.description
                }
                for f in self.factors
            ],
            'explanation': self.explanation,
            'timestamp': self.timestamp
        }


class PriorityEngine:
    """
    Engine for computing explainable priority scores for incidents.

    The priority score is calculated as a weighted sum of factors:
    - Cluster size (30%): More complaints = higher visibility/impact
    - Complaint age (25%): Older unresolved issues = higher urgency
    - Category severity (25%): Some issue types are inherently more severe
    - Location importance (20%): Public spaces/sensitive areas = higher priority

    The final score is normalized to 0-100 scale.
    """

    # Category severity weights (higher = more severe)
    CATEGORY_WEIGHTS = {
        'Water Supply': 0.90,
        'Road Infrastructure': 0.85,
        'Sanitation': 0.80,
        'Street Lighting': 0.60,
        'Waste Management': 0.65,
        'Public Works': 0.55,
        'Noise nuisance': 0.40,
        'Illegal Parking': 0.35,
        'Blocked Driveway': 0.45,
        'Damaged Tree': 0.30,
        'Street Sign Missing': 0.25,
        'General Construction': 0.50,
    }

    # Location importance weights
    LOCATION_WEIGHTS = {
        'near school': 1.0,
        'school zone': 1.0,
        'near hospital': 0.95,
        'hospital': 0.95,
        'market': 0.85,
        'bus stop': 0.80,
        'transit': 0.80,
        'metro': 0.80,
        'intersection': 0.75,
        'main road': 0.70,
        'highway': 0.70,
        'residential': 0.60,
        'park': 0.55,
        'commercial': 0.65,
    }

    # MONSOON SEASON WEIGHTING (Oct–Dec)
    MONSOON_MONTHS = [10, 11, 12]
    MONSOON_BOOST = 0.05
    MONSOON_TRIGGER_CATEGORIES = {
        'Water Supply', 'Water Supply Issues', 'Potholes - Water logged',
        'Water Contamination', 'Drainage Blockage', 'Overflowing Sewer',
        'Sanitation', 'Garbage Accumulation', 'Mosquito Breeding',
        'Public Health', 'Street Cleaning', 'Unsanitary Conditions',
        'Road Infrastructure', 'Potholes', 'Road Damage', 'Damaged Road',
    }

    # LANDMARK PROXIMITY BOOST
    COIMBATORE_LANDMARKS = {
        "Coimbatore Medical College Hospital": (11.0005, 76.9632),
        "Gandhipuram Bus Stand": (11.0072, 76.9635),
        "Coimbatore Railway Station": (10.9995, 76.9645),
        "TIDEL Park Coimbatore": (11.0179, 76.9405),
        "PSG College of Technology": (10.9750, 76.9650),
    }
    PROXIMITY_RADIUS_METERS = 300
    LANDMARK_BOOST_POINTS = 8.0

    def __init__(
        self,
        cluster_size_weight: float = 0.30,
        age_weight: float = 0.25,
        category_weight: float = 0.25,
        location_weight: float = 0.20,
        max_age_days: int = 30
    ):
        """
        Initialize the priority engine.

        Args:
            cluster_size_weight: Weight for cluster size factor
            age_weight: Weight for complaint age factor
            category_weight: Weight for category severity factor
            location_weight: Weight for location importance factor
            max_age_days: Maximum age to consider (for normalization)
        """
        self.weights = {
            'cluster_size': cluster_size_weight,
            'age': age_weight,
            'category': category_weight,
            'location': location_weight
        }
        self.max_age_days = max_age_days

        # Normalize weights to sum to 1
        total = sum(self.weights.values())
        self.weights = {k: v / total for k, v in self.weights.items()}

    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371e3
        phi1, phi2 = np.radians(lat1), np.radians(lat2)
        dphi = np.radians(lat2 - lat1)
        dlambda = np.radians(lon2 - lon1)
        a = np.sin(dphi / 2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2)**2
        return float(R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a)))

    def compute(
        self,
        incident_id: str,
        cluster_size: int,
        first_complaint_date: str,
        last_complaint_date: str,
        category: str,
        location_hints: List[str],
        incident_latitude: Optional[float] = None,
        incident_longitude: Optional[float] = None,
        max_cluster_size: int = 100
    ) -> PriorityResult:
        factors = []

        # Factor 1: Cluster Size
        cluster_factor = self._compute_cluster_size_factor(
            cluster_size, max_cluster_size
        )
        factors.append(cluster_factor)

        # Factor 2: Complaint Age
        age_factor = self._compute_age_factor(
            first_complaint_date, last_complaint_date
        )
        factors.append(age_factor)

        # Factor 3: Category Severity (with seasonal monsoon boost)
        category_factor = self._compute_category_factor(category)
        factors.append(category_factor)

        # Factor 4: Location Importance (keyword-based)
        location_factor = self._compute_location_factor(location_hints)
        factors.append(location_factor)

        # Factor 5: Landmark Proximity Boost (if coordinates available)
        landmark_factor = self._check_landmark_proximity(
            incident_latitude, incident_longitude
        )
        if landmark_factor is not None:
            factors.append(landmark_factor)

        # Compute weighted score
        total_score = sum(f.contribution for f in factors)
        normalized_score = min(max(total_score * 100, 0), 100)

        # Determine label
        label = self._get_priority_label(normalized_score)

        # Generate explanation
        explanation = self._generate_explanation(factors, label, cluster_size)

        return PriorityResult(
            incident_id=incident_id,
            priority_score=normalized_score,
            priority_label=label,
            factors=factors,
            explanation=explanation,
            timestamp=datetime.now().isoformat()
        )

    def _compute_cluster_size_factor(
        self,
        cluster_size: int,
        max_cluster_size: int
    ) -> PriorityFactor:
        """Compute the cluster size contribution to priority."""
        # Normalize cluster size (larger = higher priority)
        raw = cluster_size
        normalized = min(cluster_size / max_cluster_size, 1.0)

        # Apply sigmoid for diminishing returns on very large clusters
        adjusted = (1 / (1 + np.exp(-0.1 * (cluster_size - 10)))) * 0.7 + normalized * 0.3

        contribution = adjusted * self.weights['cluster_size'] * 100

        if cluster_size <= 3:
            desc = "Small cluster (low public attention)"
        elif cluster_size <= 10:
            desc = "Medium cluster (moderate public attention)"
        else:
            desc = "Large cluster (high public attention)"

        return PriorityFactor(
            name='cluster_size',
            raw_value=raw,
            normalized_value=adjusted,
            weight=self.weights['cluster_size'],
            contribution=contribution,
            description=desc
        )

    def _compute_age_factor(
        self,
        first_complaint_date: str,
        last_complaint_date: str
    ) -> PriorityFactor:
        """Compute the complaint age contribution to priority."""
        try:
            first_date = datetime.fromisoformat(first_complaint_date.split('T')[0])
            last_date = datetime.fromisoformat(last_complaint_date.split('T')[0])
        except (ValueError, AttributeError):
            first_date = datetime.now()
            last_date = datetime.now()

        days_open = (datetime.now() - first_date).days
        raw = days_open

        # Normalize age (older = higher priority)
        normalized = min(days_open / self.max_age_days, 1.0)

        # Apply exponential increase for aging issues
        adjusted = 1 - np.exp(-days_open / 10)

        contribution = adjusted * self.weights['age'] * 100

        if days_open <= 3:
            desc = "Recent issue (within 3 days)"
        elif days_open <= 7:
            desc = "Moderate age (1 week old)"
        elif days_open <= 14:
            desc = "Older issue (2 weeks old)"
        else:
            desc = f"Long-standing issue ({days_open} days)"

        return PriorityFactor(
            name='age',
            raw_value=raw,
            normalized_value=adjusted,
            weight=self.weights['age'],
            contribution=contribution,
            description=desc
        )

    def _compute_category_factor(self, category: str) -> PriorityFactor:
        weight = self.CATEGORY_WEIGHTS.get(category, 0.5)

        monsoon_active = (
            datetime.now().month in self.MONSOON_MONTHS
            and category in self.MONSOON_TRIGGER_CATEGORIES
        )
        effective_weight = weight + (self.MONSOON_BOOST if monsoon_active else 0.0)
        effective_weight = min(effective_weight, 1.0)

        raw = effective_weight * 100
        contribution = effective_weight * self.weights['category'] * 100

        if monsoon_active:
            desc = f"Critical category ({category}) — Monsoon season boost +{self.MONSOON_BOOST}"
        elif effective_weight >= 0.80:
            desc = f"Critical category ({category})"
        elif effective_weight >= 0.60:
            desc = f"Important category ({category})"
        else:
            desc = f"Standard category ({category})"

        return PriorityFactor(
            name='category',
            raw_value=raw,
            normalized_value=effective_weight,
            weight=self.weights['category'],
            contribution=contribution,
            description=desc
        )

    def _compute_location_factor(self, location_hints: List[str]) -> PriorityFactor:
        """Compute the location importance contribution to priority."""
        # Find best matching location importance
        max_importance = 0.5  # Default
        matched_hint = 'general area'

        hints_lower = [h.lower() for h in location_hints if h]
        all_hints = ' '.join(hints_lower)

        for keyword, importance in self.LOCATION_WEIGHTS.items():
            if keyword in all_hints:
                if importance > max_importance:
                    max_importance = importance
                    matched_hint = keyword

        raw = max_importance * 100
        contribution = max_importance * self.weights['location'] * 100

        if max_importance >= 0.9:
            desc = f"High-importance location ({matched_hint})"
        elif max_importance >= 0.7:
            desc = f"Medium-importance location ({matched_hint})"
        else:
            desc = "Standard location"

        return PriorityFactor(
            name='location',
            raw_value=raw,
            normalized_value=max_importance,
            weight=self.weights['location'],
            contribution=contribution,
            description=desc
        )

    def _check_landmark_proximity(
        self,
        lat: Optional[float],
        lng: Optional[float]
    ) -> Optional[PriorityFactor]:
        if lat is None or lng is None:
            return None
        closest_name = None
        closest_dist = float('inf')
        for name, (lm_lat, lm_lng) in self.COIMBATORE_LANDMARKS.items():
            d = self._haversine_distance(lat, lng, lm_lat, lm_lng)
            if d < closest_dist:
                closest_dist = d
                closest_name = name
        if closest_dist <= self.PROXIMITY_RADIUS_METERS:
            return PriorityFactor(
                name='landmark_proximity',
                raw_value=round(closest_dist, 0),
                normalized_value=1.0,
                weight=1.0,
                contribution=self.LANDMARK_BOOST_POINTS,
                description=f"Within {closest_dist:.0f}m of {closest_name} (+{self.LANDMARK_BOOST_POINTS} pts)"
            )
        return None

    def _get_priority_label(self, score: float) -> str:
        """Convert numeric score to priority label."""
        if score >= 90:
            return 'Critical'
        elif score >= 75:
            return 'High'
        elif score >= 50:
            return 'Medium'
        else:
            return 'Low'

    def _generate_explanation(
        self,
        factors: List[PriorityFactor],
        label: str,
        cluster_size: int
    ) -> str:
        """Generate human-readable explanation for the priority."""
        explanations = []

        # Cluster size explanation
        for f in factors:
            if f.name == 'cluster_size':
                if cluster_size >= 10:
                    explanations.append(f"High visibility: {cluster_size} complaints received")
                else:
                    explanations.append(f"Based on {cluster_size} reported complaints")

            elif f.name == 'age':
                days = int(f.raw_value)
                if days > 7:
                    explanations.append(f"Issue pending for {days} days")
                else:
                    explanations.append("Recently reported")

            elif f.name == 'category':
                if f.normalized_value >= 0.80:
                    explanations.append("Critical issue type requiring urgent attention")
                elif f.normalized_value >= 0.6:
                    explanations.append("Important infrastructure/service issue")

            elif f.name == 'location':
                if f.normalized_value >= 0.75:
                    explanations.append("Located in high-impact public area")

            elif f.name == 'landmark_proximity':
                explanations.append(f.description)

        return ". ".join(explanations) + "."

    def batch_compute(
        self,
        incidents: List[Dict],
        max_cluster_size: Optional[int] = None
    ) -> List[PriorityResult]:
        """
        Compute priority for multiple incidents.

        Args:
            incidents: List of incident dictionaries
            max_cluster_size: Optional override for max cluster size

        Returns:
            List of PriorityResult objects
        """
        if max_cluster_size is None:
            # Auto-detect from data
            max_cluster_size = max(
                i.get('cluster_size', 1) for i in incidents
            )
            max_cluster_size = max(max_cluster_size, 10)

        results = []
        for incident in incidents:
            result = self.compute(
                incident_id=incident.get('id', 'unknown'),
                cluster_size=incident.get('cluster_size', 1),
                first_complaint_date=incident.get('first_complaint_date', datetime.now().isoformat()),
                last_complaint_date=incident.get('last_complaint_date', datetime.now().isoformat()),
                category=incident.get('category', 'General'),
                location_hints=incident.get('location_hints', []),
                incident_latitude=incident.get('latitude'),
                incident_longitude=incident.get('longitude'),
                max_cluster_size=max_cluster_size
            )
            results.append(result)

        return results

    def save(self, output_dir: Path):
        """Save priority engine configuration."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        config = {
            'weights': self.weights,
            'max_age_days': self.max_age_days,
            'category_weights': self.CATEGORY_WEIGHTS,
            'location_weights': self.LOCATION_WEIGHTS
        }

        with open(output_dir / 'priority_engine_config.json', 'w') as f:
            json.dump(config, f, indent=2)

        print(f"[SAVED] Priority engine config saved to {output_dir}")

    @classmethod
    def load(cls, config_path: Path) -> 'PriorityEngine':
        """Load priority engine from configuration."""
        config_path = Path(config_path)

        with open(config_path / 'priority_engine_config.json', 'r') as f:
            config = json.load(f)

        engine = cls(
            cluster_size_weight=config['weights']['cluster_size'],
            age_weight=config['weights']['age'],
            category_weight=config['weights']['category'],
            location_weight=config['weights']['location'],
            max_age_days=config['max_age_days']
        )

        # Override weights if provided
        if 'category_weights' in config:
            engine.CATEGORY_WEIGHTS = config['category_weights']
        if 'location_weights' in config:
            engine.LOCATION_WEIGHTS = config['location_weights']

        return engine


if __name__ == '__main__':
    # Demo the priority engine
    engine = PriorityEngine()

    # Sample incidents
    test_incidents = [
        {
            'id': 'INC-001',
            'cluster_size': 15,
            'first_complaint_date': '2024-01-01',
            'last_complaint_date': '2024-01-15',
            'category': 'Water Supply',
            'location_hints': ['near hospital', 'main road']
        },
        {
            'id': 'INC-002',
            'cluster_size': 5,
            'first_complaint_date': '2024-01-10',
            'last_complaint_date': '2024-01-12',
            'category': 'Street Lighting',
            'location_hints': ['residential']
        },
        {
            'id': 'INC-003',
            'cluster_size': 25,
            'first_complaint_date': '2023-12-15',
            'last_complaint_date': '2024-01-15',
            'category': 'Road Infrastructure',
            'location_hints': ['near school', 'intersection']
        }
    ]

    results = engine.batch_compute(test_incidents)

    print("\n" + "=" * 60)
    print("PRIORITY SCORES")
    print("=" * 60)

    for result in results:
        print(f"\n{result.incident_id}: {result.priority_label} ({result.priority_score:.1f}/100)")
        print(f"  {result.explanation}")
        for factor in result.factors:
            print(f"  - {factor.name}: {factor.contribution:.1f} points ({factor.description})")

    # Save results
    output_dir = Path(__file__).parent.parent / 'outputs' / 'priority'
    engine.save(output_dir)

    # Save sample results
    with open(output_dir / 'sample_priority_results.json', 'w') as f:
        json.dump([r.to_dict() for r in results], f, indent=2)
