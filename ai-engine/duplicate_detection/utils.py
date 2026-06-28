"""
utils.py

Utility functions for the duplicate detection module.

Provides:
- Union-Find data structure for cluster building
- File loading utilities
- Text preprocessing helpers
- Output formatting

Author: GIIPS AI Engine
Version: 1.0.0
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class UnionFind:
    """
    Union-Find (Disjoint Set Union) data structure.

    Used for efficiently grouping duplicate complaints into clusters.
    Path compression and union by rank for optimal performance.

    Example:
        >>> uf = UnionFind(10)
        >>> uf.union(0, 1)
        >>> uf.union(1, 2)
        >>> uf.find(0) == uf.find(2)  # True - same cluster
    """

    def __init__(self, n: int):
        """
        Initialize Union-Find with n elements.

        Args:
            n: Number of elements
        """
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        """
        Find the root of element x with path compression.

        Args:
            x: Element to find root for

        Returns:
            Root of the set containing x
        """
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x: int, y: int) -> None:
        """
        Union the sets containing x and y.

        Uses union by rank for balanced trees.

        Args:
            x: First element
            y: Second element
        """
        px, py = self.find(x), self.find(y)

        if px == py:
            return  # Already in same set

        # Union by rank
        if self.rank[px] < self.rank[py]:
            px, py = py, px

        self.parent[py] = px

        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1


def load_metadata_file(metadata_path: Path) -> Optional[Dict]:
    """
    Load metadata JSON file with error handling.

    Args:
        metadata_path: Path to metadata JSON file

    Returns:
        Dictionary with metadata or None if file doesn't exist
    """
    metadata_path = Path(metadata_path)

    if not metadata_path.exists():
        logger.warning(f"Metadata file not found: {metadata_path}")
        return None

    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in metadata file: {e}")
        return None
    except Exception as e:
        logger.error(f"Error loading metadata: {e}")
        return None


def save_json_output(
    data: Dict,
    output_path: Path,
    description: str = "output"
) -> bool:
    """
    Save data to JSON file with error handling.

    Args:
        data: Dictionary to save
        output_path: Path to save to
        description: Description for logging

    Returns:
        True if successful, False otherwise
    """
    output_path = Path(output_path)

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Saved {description}: {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving {description}: {e}")
        return False


def preprocess_complaint_text(text: str) -> str:
    """
    Preprocess complaint text for embedding.

    Operations:
    - Strip leading/trailing whitespace
    - Normalize internal whitespace
    - Remove control characters
    - Convert to proper case (keep original casing)

    Args:
        text: Raw complaint text

    Returns:
        Cleaned text
    """
    if not text or not isinstance(text, str):
        return ""

    # Remove control characters
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)

    # Strip
    text = text.strip()

    return text


def extract_complaint_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """
    Extract important keywords from complaint text.

    Args:
        text: Complaint text
        max_keywords: Maximum keywords to return

    Returns:
        List of keywords
    """
    if not text:
        return []

    # Simple keyword extraction (can be enhanced with NLP libraries)
    # Remove common stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'been',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'must', 'shall', 'can', 'this', 'that',
        'these', 'those', 'it', 'its', 'very', 'too', 'also', 'not', 'no'
    }

    # Tokenize
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())

    # Filter stop words and get unique keywords
    keywords = []
    seen = set()
    for word in words:
        if word not in stop_words and word not in seen:
            keywords.append(word)
            seen.add(word)
            if len(keywords) >= max_keywords:
                break

    return keywords


def format_duplicate_report(
    clusters: List[Dict],
    total_complaints: int,
    similarity_threshold: float
) -> str:
    """
    Format duplicate detection results as human-readable report.

    Args:
        clusters: List of cluster dictionaries
        total_complaints: Total number of complaints processed
        similarity_threshold: Threshold used for detection

    Returns:
        Formatted report string
    """
    lines = []
    lines.append("=" * 60)
    lines.append("DUPLICATE DETECTION REPORT")
    lines.append("=" * 60)
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Similarity threshold: {similarity_threshold:.0%}")
    lines.append(f"Total complaints analyzed: {total_complaints}")
    lines.append("")

    if not clusters:
        lines.append("No duplicate clusters found.")
        return "\n".join(lines)

    duplicates_count = sum(c['size'] for c in clusters)
    lines.append(f"Duplicate clusters found: {len(clusters)}")
    lines.append(f"Total complaints in clusters: {duplicates_count}")
    lines.append("")

    # Top clusters
    lines.append("TOP 10 DUPLICATE CLUSTERS:")
    lines.append("-" * 40)

    for i, cluster in enumerate(clusters[:10]):
        lines.append(f"\nCluster {i + 1}:")
        lines.append(f"  Size: {cluster['size']} complaints")
        lines.append(f"  Avg similarity: {cluster.get('avg_similarity', 0):.1%}")

        # Show sample members
        if 'members' in cluster:
            lines.append("  Sample complaints:")
            for member in cluster['members'][:3]:
                if 'id' in member:
                    lines.append(f"    - ID: {member['id']}")

    return "\n".join(lines)


def validate_embeddings(embeddings_path: Path) -> Dict[str, Any]:
    """
    Validate embeddings file format and content.

    Args:
        embeddings_path: Path to embeddings.npy

    Returns:
        Dictionary with validation results
    """
    import numpy as np

    results = {
        'valid': False,
        'shape': None,
        'dtype': None,
        'normalized': False,
        'error': None
    }

    try:
        embeddings = np.load(embeddings_path)

        results['shape'] = embeddings.shape
        results['dtype'] = str(embeddings.dtype)

        if len(embeddings.shape) != 2:
            results['error'] = f"Expected 2D array, got {len(embeddings.shape)}D"
            return results

        if embeddings.shape[0] == 0:
            results['error'] = "No embeddings in file"
            return results

        # Check if normalized (L2 norm should be ~1 for each row)
        norms = np.linalg.norm(embeddings, axis=1)
        avg_norm = np.mean(norms)
        results['normalized'] = 0.99 < avg_norm < 1.01

        results['valid'] = True

    except Exception as e:
        results['error'] = str(e)

    return results


def validate_faiss_index(index_path: Path) -> Dict[str, Any]:
    """
    Validate FAISS index file.

    Args:
        index_path: Path to faiss.index

    Returns:
        Dictionary with validation results
    """
    results = {
        'valid': False,
        'n_vectors': None,
        'dimension': None,
        'error': None
    }

    try:
        import faiss
        index = faiss.read_index(str(index_path))

        results['n_vectors'] = index.ntotal
        results['dimension'] = index.d
        results['valid'] = True

    except ImportError:
        results['error'] = "FAISS not installed"
    except Exception as e:
        results['error'] = str(e)

    return results


def get_statistics_summary(
    clusters: List[Dict],
    total_complaints: int
) -> Dict:
    """
    Compute summary statistics from clusters.

    Args:
        clusters: List of cluster dictionaries
        total_complaints: Total complaints analyzed

    Returns:
        Dictionary of statistics
    """
    if not clusters:
        return {
            'n_clusters': 0,
            'total_duplicates': 0,
            'unique_incidents': total_complaints,
            'avg_cluster_size': 0,
            'max_cluster_size': 0,
            'deduplication_rate': 0
        }

    sizes = [c['size'] for c in clusters]
    total_duplicates = sum(sizes)
    unique_incidents = (total_complaints - total_duplicates) + len(clusters)

    return {
        'n_clusters': len(clusters),
        'total_duplicates': total_duplicates,
        'unique_incidents': unique_incidents,
        'avg_cluster_size': sum(sizes) / len(sizes) if sizes else 0,
        'max_cluster_size': max(sizes) if sizes else 0,
        'min_cluster_size': min(sizes) if sizes else 0,
        'deduplication_rate': (
            (1 - unique_incidents / total_complaints) * 100
            if total_complaints > 0 else 0
        )
    }


if __name__ == '__main__':
    # Quick test
    print("Testing UnionFind...")
    uf = UnionFind(10)
    uf.union(0, 1)
    uf.union(1, 2)
    uf.union(3, 4)

    assert uf.find(0) == uf.find(2), "UnionFind test failed"
    assert uf.find(0) != uf.find(3), "UnionFind test failed"
    print("UnionFind tests passed!")

    print("\nTesting text processing...")
    text = "Large   pothole on  Main Street   causing accidents"
    processed = preprocess_complaint_text(text)
    print(f"Processed: '{processed}'")

    keywords = extract_complaint_keywords(text)
    print(f"Keywords: {keywords}")

    print("\nAll tests passed!")
