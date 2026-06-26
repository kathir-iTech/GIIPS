"""
Utility functions for priority calculation.
"""

from datetime import datetime
from typing import Dict, List, Optional
import re


def calculate_days_open(first_complaint_date: str) -> int:
    """
    Calculate number of days since first complaint.

    Args:
        first_complaint_date: ISO format date string

    Returns:
        Number of days open
    """
    try:
        # Handle various date formats
        date_str = first_complaint_date.split('T')[0] if 'T' in first_complaint_date else first_complaint_date
        first_date = datetime.fromisoformat(date_str)
        return max(0, (datetime.now() - first_date).days)
    except (ValueError, TypeError, AttributeError):
        return 0


def extract_urgency_keywords(text: str) -> List[str]:
    """
    Extract urgency-related keywords from complaint text.

    Args:
        text: Complaint text

    Returns:
        List of urgency keywords found
    """
    urgency_patterns = [
        r'\b(?:emergency|urgent|immediate|dangerous|hazardous|critical|severe|serious)\b',
        r'\b(?:accident|injury|hurt|death|trapped|collapsed)\b',
        r'\b(?:flooding|burst|explosion|fire)\b',
        r'\b(?:children|kids|elderly|disabled)\b'
    ]

    keywords = []
    text_lower = text.lower()

    for pattern in urgency_patterns:
        matches = re.findall(pattern, text_lower)
        keywords.extend(matches)

    return list(set(keywords))


def calculate_complaint_frequency(
    complaints: List[Dict],
    date_key: str = 'date_received'
) -> float:
    """
    Calculate complaints per day for a cluster.

    Args:
        complaints: List of complaint dictionaries
        date_key: Key for date field

    Returns:
        Average complaints per day
    """
    if not complaints:
        return 0.0

    dates = []
    for c in complaints:
        date_str = c.get(date_key, '')
        try:
            if 'T' in date_str:
                date_str = date_str.split('T')[0]
            dates.append(datetime.fromisoformat(date_str))
        except (ValueError, TypeError):
            continue

    if len(dates) < 2:
        return 1.0

    dates.sort()
    date_range = (dates[-1] - dates[0]).days + 1

    return len(dates) / max(date_range, 1)


def get_impact_severity(
    category: str,
    location_hints: List[str],
    text: str
) -> str:
    """
    Determine impact severity level.

    Args:
        category: Incident category
        location_hints: List of location keywords
        text: Combined complaint text

    Returns:
        Severity level: 'high', 'medium', or 'low'
    """
    score = 0

    # Category impact
    high_impact_categories = {
        'Water Supply', 'Sanitation', 'Road Infrastructure'
    }
    if category in high_impact_categories:
        score += 2

    # Location impact
    high_impact_locations = {
        'school', 'hospital', 'emergency', 'transit', 'market'
    }
    location_text = ' '.join(location_hints).lower()
    for loc in high_impact_locations:
        if loc in location_text:
            score += 1

    # Urgency keywords
    urgency_keywords = extract_urgency_keywords(text)
    score += min(len(urgency_keywords), 3)

    if score >= 4:
        return 'high'
    elif score >= 2:
        return 'medium'
    else:
        return 'low'


def estimate_affected_population(
    location_hints: List[str],
    time_of_day: Optional[str] = None
) -> int:
    """
    Estimate rough affected population based on location type.

    Args:
        location_hints: List of location keywords
        time_of_day: Optional time context

    Returns:
        Estimated affected population (rough estimate)
    """
    location_text = ' '.join(location_hints).lower()

    # Rough estimates based on location type
    estimates = {
        'school': 500,
        'hospital': 200,
        'market': 1000,
        'transit': 2000,
        'metro': 5000,
        'bus stop': 200,
        'intersection': 500,
        'main road': 1000,
        'residential': 100,
        'park': 50
    }

    max_estimate = 50  # Default
    for keyword, estimate in estimates.items():
        if keyword in location_text:
            if estimate > max_estimate:
                max_estimate = estimate

    return max_estimate


def get_resource_requirement(
    category: str,
    priority_score: float
) -> Dict:
    """
    Estimate resource requirements for an incident.

    Args:
        category: Incident category
        priority_score: Priority score

    Returns:
        Dictionary with resource estimates
    """
    base_resources = {
        'Water Supply': {
            'personnel': 3,
            'vehicles': 2,
            'estimated_hours': 8
        },
        'Road Infrastructure': {
            'personnel': 4,
            'vehicles': 2,
            'estimated_hours': 6
        },
        'Sanitation': {
            'personnel': 2,
            'vehicles': 1,
            'estimated_hours': 4
        },
        'Street Lighting': {
            'personnel': 2,
            'vehicles': 1,
            'estimated_hours': 2
        },
        'Waste Management': {
            'personnel': 2,
            'vehicles': 1,
            'estimated_hours': 2
        }
    }

    resources = base_resources.get(category, {
        'personnel': 1,
        'vehicles': 1,
        'estimated_hours': 2
    }).copy()

    # Scale by priority
    if priority_score >= 90:
        multiplier = 1.5
    elif priority_score >= 75:
        multiplier = 1.2
    else:
        multiplier = 1.0

    resources['personnel'] = int(resources['personnel'] * multiplier)
    resources['vehicles'] = max(1, int(resources['vehicles'] * multiplier))

    return resources


def compute_workload_impact(
    cluster_size: int,
    resolution_hours: int
) -> Dict:
    """
    Compute the workload impact of clustering.

    Shows the efficiency gain from processing clustered complaints together.

    Args:
        cluster_size: Number of complaints in cluster
        resolution_hours: Estimated resolution time

    Returns:
        Dictionary with workload metrics
    """
    # Without clustering: each complaint processed separately
    individual_processing_minutes = 15  # Per complaint
    total_individual_hours = (cluster_size * individual_processing_minutes) / 60

    # With clustering: one incident processing
    cluster_processing_hours = resolution_hours
    cluster_admin_hours = 0.5  # Minimal admin for merged complaints

    savings_hours = total_individual_hours - (cluster_processing_hours + cluster_admin_hours)
    efficiency_gain = (savings_hours / total_individual_hours * 100) if total_individual_hours > 0 else 0

    return {
        'complaints_processed_individually': cluster_size,
        'individual_processing_hours': total_individual_hours,
        'clustered_processing_hours': cluster_processing_hours + cluster_admin_hours,
        'saved_hours': max(0, savings_hours),
        'efficiency_gain_percent': round(efficiency_gain, 1)
    }


if __name__ == '__main__':
    # Demo utilities
    test_text = "Urgent: Major water pipe burst near City Hospital causing flooding"
    print(f"Urgency keywords: {extract_urgency_keywords(test_text)}")
    print(f"Impact severity: {get_impact_severity('Water Supply', ['hospital'], test_text)}")
    print(f"Affected population: {estimate_affected_population(['hospital', 'main road'])}")
    print(f"Workload impact: {compute_workload_impact(50, 8)}")
