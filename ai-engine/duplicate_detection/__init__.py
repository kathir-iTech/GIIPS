"""
Duplicate Detection Module for GIIPS.

Provides fast similarity-based duplicate detection for complaints.
"""

from .train_embeddings import EmbeddingTrainer
from .build_index import FAISSIndexBuilder
from .detect_duplicates import DuplicateDetector

__all__ = [
    'EmbeddingTrainer',
    'FAISSIndexBuilder',
    'DuplicateDetector'
]
