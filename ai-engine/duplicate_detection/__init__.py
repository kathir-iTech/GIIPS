"""
Duplicate Detection Module for GIIPS.

Provides fast similarity-based duplicate detection for complaints using:
- SentenceTransformer embeddings (all-MiniLM-L6-v2)
- NearestNeighbors (sklearn) or keyword-overlap fallback

The runtime DuplicateDetector is in engine.py and is consumed by the
backend's ComplaintService (services.py).

Usage:
    from duplicate_detection import DuplicateDetector
"""

from .engine import DuplicateDetector
from .utils import (
    UnionFind,
    load_metadata_file,
    save_json_output,
    preprocess_complaint_text,
    extract_complaint_keywords,
    format_duplicate_report,
    validate_embeddings,
    validate_faiss_index,
    get_statistics_summary
)

__all__ = [
    # Main classes
    'DuplicateDetector',
    # Utilities
    'UnionFind',
    'load_metadata_file',
    'save_json_output',
    'preprocess_complaint_text',
    'extract_complaint_keywords',
    'format_duplicate_report',
    'validate_embeddings',
    'validate_faiss_index',
    'get_statistics_summary',
]

__version__ = '1.0.0'
