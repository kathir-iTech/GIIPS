"""
Priority Rules Engine for handling special cases and overrides.

Provides rule-based adjustments to the ML-computed priority scores.
"""

from typing import Dict, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass


@dataclass
class PriorityRule:
    """Represents a priority adjustment rule."""
    name: str
    condition: Callable[[Dict], bool]
    adjustment: float
    reason: str
    priority: int = 0  # Higher = evaluated first


class PriorityRulesEngine:
    """
    Rule-based engine for priority adjustments.

    Rules can boost or reduce priority scores based on:
    - Safety implications
    - Legal requirements
    - Public health concerns
    - Media attention
    - Recurring issues
    """

    def __init__(self):
        """Initialize with default rules."""
        self.rules: List[PriorityRule] = []
        self._register_default_rules()

    def _register_default_rules(self):
        """Register built-in priority adjustment rules."""

        # Safety-critical issues
        self.add_rule(PriorityRule(
            name='safety_critical',
            condition=lambda i: any(kw in str(i).lower() for kw in
                ['injury', 'accident', 'hazardous', 'dangerous', 'collapsed', 'electric shock']),
            adjustment=20,
            reason='Safety hazard detected',
            priority=100
        ))

        # Near schools
        self.add_rule(PriorityRule(
            name='school_proximity',
            condition=lambda i: any(kw in str(i.get('location_hints', [])).lower()
                for kw in ['school', 'playground', 'daycare']),
            adjustment=15,
            reason='Issue near school/childcare',
            priority=90
        ))

        # Near hospitals
        self.add_rule(PriorityRule(
            name='hospital_proximity',
            condition=lambda i: any(kw in str(i.get('location_hints', [])).lower()
                for kw in ['hospital', 'clinic', 'medical', 'emergency']),
            adjustment=12,
            reason='Issue near medical facility',
            priority=85
        ))

        # Water-related (public health)
        self.add_rule(PriorityRule(
            name='water_public_health',
            condition=lambda i: any(kw in str(i.get('category', '')).lower()
                for kw in ['water', 'sewage', 'contamination']),
            adjustment=10,
            reason='Public health impact',
            priority=80
        ))

        # Long-standing issues
        self.add_rule(PriorityRule(
            name='long_standing',
            condition=lambda i: _get_days_open(i) > 21,
            adjustment=8,
            reason='Issue unresolved for >3 weeks',
            priority=70
        ))

        # Very large clusters (media attention risk)
        self.add_rule(PriorityRule(
            name='large_cluster',
            condition=lambda i: i.get('cluster_size', 0) > 20,
            adjustment=7,
            reason='High public interest',
            priority=60
        ))

        # Recurring issue (same location had previous complaints)
        self.add_rule(PriorityRule(
            name='recurring',
            condition=lambda i: i.get('is_recurring', False),
            adjustment=5,
            reason='Recurring issue pattern detected',
            priority=50
        ))

        # Low priority adjustment for minor issues
        self.add_rule(PriorityRule(
            name='minor_issue',
            condition=lambda i: any(kw in str(i.get('category', '')).lower()
                for kw in ['sign', 'painting', 'cosmetic']),
            adjustment=-5,
            reason='Low-impact cosmetic issue',
            priority=10
        ))

    def add_rule(self, rule: PriorityRule):
        """Add a priority rule."""
        self.rules.append(rule)
        # Sort by priority
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def apply_rules(
        self,
        incident: Dict,
        base_score: float
    ) -> Dict:
        """
        Apply rules to adjust the base priority score.

        Args:
            incident: Incident dictionary
            base_score: Base priority score from the ML engine

        Returns:
            Dictionary with adjusted score and applied rules
        """
        applied_rules = []
        total_adjustment = 0

        for rule in self.rules:
            try:
                if rule.condition(incident):
                    applied_rules.append({
                        'rule': rule.name,
                        'adjustment': rule.adjustment,
                        'reason': rule.reason
                    })
                    total_adjustment += rule.adjustment
            except Exception:
                # Skip rules that fail to evaluate
                continue

        # Apply adjustment (capped at 0-100)
        adjusted_score = max(0, min(100, base_score + total_adjustment))

        return {
            'base_score': base_score,
            'adjusted_score': adjusted_score,
            'total_adjustment': total_adjustment,
            'applied_rules': applied_rules
        }


def _get_days_open(incident: Dict) -> int:
    """Calculate days open for an incident."""
    try:
        first_date_str = incident.get('first_complaint_date', '')
        if 'T' in first_date_str:
            first_date = datetime.fromisoformat(first_date_str.split('T')[0])
        else:
            first_date = datetime.fromisoformat(first_date_str)
        return (datetime.now() - first_date).days
    except (ValueError, TypeError):
        return 0


def apply_priority_rules(
    incidents: List[Dict],
    base_scores: List[float]
) -> List[Dict]:
    """
    Apply priority rules to multiple incidents.

    Args:
        incidents: List of incident dictionaries
        base_scores: Corresponding base priority scores

    Returns:
        List of adjusted priority results
    """
    engine = PriorityRulesEngine()
    results = []

    for incident, base_score in zip(incidents, base_scores):
        result = engine.apply_rules(incident, base_score)
        results.append(result)

    return results


class EscalationPolicy:
    """
    Define escalation policies based on priority scores and thresholds.
    """

    # Priority thresholds for escalation levels
    ESCALATION_LEVELS = {
        'immediate': 90,  # Critical - immediate action
        'urgent': 75,     # High - within 24 hours
        'standard': 50,   # Medium - within 7 days
        'routine': 0      # Low - standard timeline
    }

    # Response time requirements by level
    RESPONSE_TIMES = {
        'immediate': '2 hours',
        'urgent': '24 hours',
        'standard': '7 days',
        'routine': '30 days'
    }

    @classmethod
    def get_escalation_level(cls, priority_score: float) -> str:
        """Determine escalation level for a priority score."""
        for level, threshold in sorted(
            cls.ESCALATION_LEVELS.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            if priority_score >= threshold:
                return level
        return 'routine'

    @classmethod
    def get_response_time(cls, priority_score: float) -> str:
        """Get required response time for a priority score."""
        level = cls.get_escalation_level(priority_score)
        return cls.RESPONSE_TIMES.get(level, '30 days')

    @classmethod
    def requires_notification(cls, priority_score: float) -> bool:
        """Check if an incident requires management notification."""
        return priority_score >= cls.ESCALATION_LEVELS['urgent']

    @classmethod
    def get_recommended_action(cls, category: str, priority_score: float) -> str:
        """Get recommended action based on category and priority."""
        level = cls.get_escalation_level(priority_score)

        actions = {
            'Water Supply': {
                'immediate': 'Emergency water supply deployment and repair crew dispatch',
                'urgent': 'Priority repair with water tanker support',
                'standard': 'Scheduled pipeline maintenance',
                'routine': 'Routine inspection and repair'
            },
            'Road Infrastructure': {
                'immediate': 'Emergency road closure and repair',
                'urgent': 'Priority patching with safety barriers',
                'standard': 'Scheduled resurfacing',
                'routine': 'Include in quarterly maintenance'
            },
            'Sanitation': {
                'immediate': 'Emergency cleaning and containment',
                'urgent': 'Priority drain clearing',
                'standard': 'Scheduled cleaning',
                'routine': 'Routine maintenance'
            }
        }

        return actions.get(category, {}).get(level, 'Standard procedure')


if __name__ == '__main__':
    # Demo rule application
    engine = PriorityRulesEngine()

    test_incidents = [
        {
            'id': 'TEST-001',
            'category': 'Water Supply',
            'cluster_size': 15,
            'location_hints': ['near hospital'],
            'first_complaint_date': '2024-01-01'
        },
        {
            'id': 'TEST-002',
            'category': 'Road Infrastructure',
            'cluster_size': 8,
            'location_hints': ['near school'],
            'first_complaint_date': '2024-01-05'
        },
        {
            'id': 'TEST-003',
            'text': 'Dangerous pothole causing accidents on main road',
            'category': 'Road Infrastructure',
            'cluster_size': 5,
            'location_hints': ['intersection'],
            'first_complaint_date': '2024-01-10'
        }
    ]

    print("\n" + "=" * 60)
    print("RULE-BASED PRIORITY ADJUSTMENTS")
    print("=" * 60)

    for incident in test_incidents[:3]:
        result = engine.apply_rules(incident, 50.0)
        print(f"\n{incident.get('id', 'unknown')}:")
        print(f"  Base score: {result['base_score']:.1f}")
        print(f"  Adjusted score: {result['adjusted_score']:.1f}")
        print(f"  Applied rules:")
        for rule in result['applied_rules']:
            print(f"    - {rule['reason']}: +{rule['adjustment']}")
