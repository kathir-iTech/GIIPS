"""
Duplicate Detection Module for GIIPS.

Provides fast similarity-based duplicate detection for complaints using:
- SentenceTransformer embeddings (all-MiniLM-L6-v2)
- FAISS similarity search
- Union-Find clustering

Usage:
    # Step 1: Generate embeddings
    python -m ai-engine.duplicate_detection.train_embeddings

    # Step 2: Build FAISS index
    python -m ai-engine.duplicate_detection.build_faiss

    # Step 3: Detect duplicates
    python -m ai-engine.duplicate_detection.detect_duplicates

Outputs:
    - embeddings.npy
    - faiss.index
    - duplicate_clusters.json (saved to ai-engine/outputs/)
"""

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
