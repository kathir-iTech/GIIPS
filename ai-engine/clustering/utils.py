"""
Clustering utilities for duplicate detection and incident grouping.
"""

import re
import string
from typing import List, Dict, Optional, Tuple
import numpy as np
import pandas as pd
from collections import defaultdict


def preprocess_for_clustering(text: str) -> str:
    """
    Preprocess text specifically for clustering/embedding generation.

    Different from classification preprocessing - we want to preserve
    semantic meaning for sentence embeddings.

    Args:
        text: Raw text string

    Returns:
        Preprocessed text
    """
    if not isinstance(text, str):
        return ""

    # Convert to lowercase
    text = text.lower()

    # Remove URLs
    text = re.sub(r'http\S+|www\.\S+', '', text)

    # Remove email addresses
    text = re.sub(r'\S+@\S+', '', text)

    # Normalize whitespace
    text = ' '.join(text.split())

    return text.strip()


def extract_location_hints(text: str) -> Dict[str, str]:
    """
    Extract location-related information from text.

    Args:
        text: Complaint text

    Returns:
        Dictionary with location hints
    """
    hints = {
        'street_number': '',
        'street_name': '',
        'intersection': False,
        'landmark': ''
    }

    # Pattern for street addresses
    address_pattern = r'\d+\s+[a-zA-Z\s]+(?:street|st|avenue|ave|road|rd|boulevard|blvd|drive|dr|place|pl|lane|ln)'
    match = re.search(address_pattern, text, re.IGNORECASE)
    if match:
        hints['street_name'] = match.group()

    # Pattern for intersections
    intersection_pattern = r'(?:corner of|at the intersection of|near|between)\s+[a-zA-Z\s]+(?:and|&|\s)\s+[a-zA-Z\s]+'
    match = re.search(intersection_pattern, text, re.IGNORECASE)
    if match:
        hints['intersection'] = True

    return hints


def normalize_complaint(complaint_dict: Dict, text_key: str = 'text') -> Dict:
    """
    Normalize a complaint dictionary for clustering.

    Args:
        complaint_dict: Dictionary containing complaint data
        text_key: Key for the text field

    Returns:
        Normalized complaint dictionary
    """
    normalized = complaint_dict.copy()

    if text_key in normalized:
        normalized['processed_text'] = preprocess_for_clustering(normalized[text_key])

    normalized['location_hints'] = extract_location_hints(normalized.get(text_key, ''))

    return normalized


def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    Calculate simple text similarity using token overlap.

    This is a fallback when embeddings are not available.

    Args:
        text1: First text
        text2: Second text

    Returns:
        Similiary score between 0 and 1
    """
    tokens1 = set(text1.lower().split())
    tokens2 = set(text2.lower().split())

    if not tokens1 or not tokens2:
        return 0.0

    intersection = tokens1 & tokens2
    union = tokens1 | tokens2

    return len(intersection) / len(union)


def group_by_location(complaints: List[Dict],
                      ward_key: str = 'ward') -> Dict[str, List[int]]:
    """
    Group complaints by ward for more efficient clustering.

    Args:
        complaints: List of complaint dictionaries
        ward_key: Key for ward field

    Returns:
        Dictionary mapping ward to list of indices
    """
    ward_groups = defaultdict(list)

    for i, complaint in enumerate(complaints):
        ward = complaint.get(ward_key, 'Unknown')
        ward_groups[ward].append(i)

    return dict(ward_groups)


def validate_clustering_params(eps: float, min_samples: int) -> Dict:
    """
    Validate and provide recommendations for DBSCAN parameters.

    Args:
        eps: Epsilon parameter (neighborhood radius)
        min_samples: Minimum samples parameter

    Returns:
        Dictionary with validation results
    """
    issues = []
    recommendations = []

    if eps <= 0:
        issues.append("eps must be positive")
    elif eps > 1:
        issues.append("eps typically should be in range (0, 1) for cosine distance")
        recommendations.append("Consider using eps between 0.1 and 0.5 for sentence embeddings")

    if min_samples < 2:
        issues.append("min_samples must be at least 2")
        recommendations.append("min_samples=2-5 is typical for duplicate detection")

    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'recommendations': recommendations
    }


def prepare_clustering_dataframe(complaints: List[Dict]) -> pd.DataFrame:
    """
    Prepare complaints for clustering by creating a DataFrame.

    Args:
        complaints: List of complaint dictionaries

    Returns:
        DataFrame with complaints ready for clustering
    """
    df = pd.DataFrame(complaints)

    # Ensure required columns
    if 'processed_text' not in df.columns and 'text' in df.columns:
        df['processed_text'] = df['text'].apply(preprocess_for_clustering)

    # Add index for tracking
    if 'id' not in df.columns:
        df['id'] = range(len(df))

    return df
