"""
Classification utilities for text preprocessing and feature extraction.
"""

import re
import string
from typing import List, Optional
import pandas as pd


def clean_text(text: str) -> str:
    """
    Clean and normalize text for classification.

    Steps:
    1. Convert to lowercase
    2. Remove URLs
    3. Remove punctuation
    4. Remove extra whitespace
    5. Remove numbers (optional, can be toggled)

    Args:
        text: Raw text string

    Returns:
        Cleaned text string
    """
    if not isinstance(text, str):
        return ""

    # Convert to lowercase
    text = text.lower()

    # Remove URLs
    text = re.sub(r'http\S+|www\.\S+', '', text)

    # Remove email addresses
    text = re.sub(r'\S+@\S+', '', text)

    # Remove punctuation
    text = text.translate(str.maketrans('', '', string.punctuation))

    # Remove extra whitespace
    text = ' '.join(text.split())

    return text.strip()


def prepare_complaint_text(df: pd.DataFrame,
                           problem_col: str = 'Problem',
                           detail_col: str = 'Problem Detail') -> pd.Series:
    """
    Prepare complaint text for classification by combining Problem and Problem Detail.

    Args:
        df: DataFrame containing complaint data
        problem_col: Name of the problem/category column
        detail_col: Name of the detail/description column

    Returns:
        Series of cleaned combined text
    """
    # Combine problem and detail columns
    combined = df[problem_col].fillna('') + ' ' + df[detail_col].fillna('')

    # Clean the combined text
    cleaned = combined.apply(clean_text)

    # Remove empty strings
    cleaned = cleaned.replace('', None)

    return cleaned


def validate_dataframe(df: pd.DataFrame,
                       required_columns: List[str]) -> bool:
    """
    Validate that DataFrame has required columns.

    Args:
        df: DataFrame to validate
        required_columns: List of required column names

    Returns:
        True if all columns present, raises ValueError otherwise
    """
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return True


def get_category_distribution(labels: pd.Series) -> dict:
    """
    Get the distribution of categories in the dataset.

    Args:
        labels: Series of category labels

    Returns:
        Dictionary with category counts
    """
    return labels.value_counts().to_dict()


def sample_for_development(df: pd.DataFrame,
                           n_samples: int = 10000,
                           random_state: int = 42) -> pd.DataFrame:
    """
    Sample dataset for development/testing purposes.

    Args:
        df: Full DataFrame
        n_samples: Number of samples to take
        random_state: Random seed

    Returns:
        Sampled DataFrame
    """
    if len(df) <= n_samples:
        return df

    return df.sample(n=n_samples, random_state=random_state)
