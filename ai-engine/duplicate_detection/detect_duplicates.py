"""
detect_duplicates.py

Detect duplicate complaints using FAISS similarity search.

This script:
1. Loads FAISS index and embeddings
2. Searches for similar complaints above threshold
3. Clusters duplicates together
4. Outputs duplicate clusters with similarity scores

Author: GIIPS AI Engine
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Set
from collections import defaultdict

import numpy as np

# FAISS for similarity search
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False


class DuplicateDetector:
    """
    Detect duplicate complaints using FAISS similarity search.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.85,
        max_neighbors: int = 50,
        min_cluster_size: int = 2
    ):
        """
        Initialize the duplicate detector.

        Args:
            similarity_threshold: Minimum similarity to consider as duplicate (0-1)
            max_neighbors: Maximum neighbors to retrieve per query
            min_cluster_size: Minimum size for a duplicate cluster
        """
        self.similarity_threshold = similarity_threshold
        self.max_neighbors = max_neighbors
        self.min_cluster_size = min_cluster_size
        self.index = None
        self.embeddings = None
        self.metadata = None

    def load_index(self, index_path: Path) -> None:
        """
        Load FAISS index from disk.

        Args:
            index_path: Path to FAISS index file
        """
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS is required. Install with: pip install faiss-cpu")

        print(f"[INFO] Loading FAISS index from: {index_path}")
        self.index = faiss.read_index(str(index_path))
        print(f"[INFO] Index loaded. Total vectors: {self.index.ntotal}")

    def load_embeddings(self, embeddings_path: Path) -> None:
        """
        Load embeddings from disk.

        Args:
            embeddings_path: Path to embeddings file
        """
        print(f"[INFO] Loading embeddings from: {embeddings_path}")
        self.embeddings = np.load(embeddings_path).astype(np.float32)
        print(f"[INFO] Embeddings shape: {self.embeddings.shape}")

    def load_metadata(self, metadata_path: Path) -> None:
        """
        Load embedding metadata.

        Args:
            metadata_path: Path to metadata JSON file
        """
        print(f"[INFO] Loading metadata from: {metadata_path}")
        with open(metadata_path, 'r') as f:
            self.metadata = json.load(f)
        print(f"[INFO] Loaded metadata for {len(self.metadata.get('metadata', []))} complaints")

    def search_similar(
        self,
        query_idx: int,
        k: Optional[int] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for similar complaints to a query.

        Args:
            query_idx: Index of query vector
            k: Number of neighbors to retrieve

        Returns:
            Tuple of (distances, indices)
        """
        if k is None:
            k = min(self.max_neighbors, self.index.ntotal)

        # Get query vector
        query_vector = self.embeddings[query_idx:query_idx + 1]

        # Search
        distances, indices = self.index.search(query_vector, k)

        return distances[0], indices[0]

    def find_all_duplicates(self) -> Dict[int, List[Dict]]:
        """
        Find all duplicate pairs above threshold.

        Returns:
            Dictionary mapping complaint index to list of duplicates
        """
        if self.index is None or self.embeddings is None:
            raise ValueError("Index and embeddings must be loaded first")

        print(f"[INFO] Searching for duplicates (threshold={self.similarity_threshold})...")

        n_vectors = len(self.embeddings)
        k = min(self.max_neighbors, n_vectors)

        # Batch search for efficiency
        batch_size = 1000
        all_duplicates = defaultdict(list)

        for start in range(0, n_vectors, batch_size):
            end = min(start + batch_size, n_vectors)
            batch = self.embeddings[start:end]

            distances, indices = self.index.search(batch, k)

            for i, (dists, idxs) in enumerate(zip(distances, indices)):
                query_idx = start + i
                for dist, idx in zip(dists, idxs):
                    # Skip self
                    if idx == query_idx:
                        continue
                    # Check threshold
                    if dist >= self.similarity_threshold:
                        all_duplicates[query_idx].append({
                            'index': int(idx),
                            'similarity': float(dist)
                        })

            if (start // batch_size) % 10 == 0:
                print(f"[INFO] Processed {end}/{n_vectors} vectors...")

        print(f"[INFO] Found {len(all_duplicates)} complaints with potential duplicates")
        return dict(all_duplicates)

    def build_clusters(self, duplicates: Dict[int, List[Dict]]) -> List[List[int]]:
        """
        Build duplicate clusters using Union-Find algorithm.

        Args:
            duplicates: Dictionary of complaint index -> duplicate list

        Returns:
            List of clusters (each cluster is a list of indices)
        """
        print("[INFO] Building duplicate clusters...")

        # Union-Find
        n_vectors = len(self.embeddings)
        parent = list(range(n_vectors))
        rank = [0] * n_vectors

        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x, y):
            px, py = find(x), find(y)
            if px == py:
                return
            if rank[px] < rank[py]:
                px, py = py, px
            parent[py] = px
            if rank[px] == rank[py]:
                rank[px] += 1

        # Union all duplicate pairs
        for idx, dup_list in duplicates.items():
            for dup in dup_list:
                union(idx, dup['index'])

        # Group by root
        clusters = defaultdict(list)
        for i in range(n_vectors):
            root = find(i)
            clusters[root].append(i)

        # Filter to clusters with min size
        valid_clusters = [
            sorted(cluster) for cluster in clusters.values()
            if len(cluster) >= self.min_cluster_size
        ]

        # Sort by cluster size (descending)
        valid_clusters.sort(key=len, reverse=True)

        print(f"[INFO] Built {len(valid_clusters)} duplicate clusters")
        return valid_clusters

    def format_cluster(
        self,
        cluster_indices: List[int],
        cluster_id: int
    ) -> Dict:
        """
        Format a cluster with metadata.

        Args:
            cluster_indices: List of complaint indices in cluster
            cluster_id: Cluster identifier

        Returns:
            Formatted cluster dictionary
        """
        # Get metadata for cluster members
        members = []
        if self.metadata and 'metadata' in self.metadata:
            meta_list = self.metadata['metadata']
            for idx in cluster_indices:
                if idx < len(meta_list):
                    member_meta = meta_list[idx].copy()
                    members.append(member_meta)
                else:
                    members.append({'index': idx})

        # Calculate cluster statistics
        # Get pairwise similarities within cluster
        cluster_embeddings = self.embeddings[cluster_indices]
        pairwise = np.dot(cluster_embeddings, cluster_embeddings.T)

        # Exclude diagonal and get average
        mask = ~np.eye(len(cluster_indices), dtype=bool)
        avg_similarity = np.mean(pairwise[mask]) if mask.any() else 1.0
        min_similarity = np.min(pairwise[mask]) if mask.any() else 1.0

        return {
            'cluster_id': cluster_id,
            'size': len(cluster_indices),
            'avg_similarity': float(avg_similarity),
            'min_similarity': float(min_similarity),
            'members': members,
            'indices': cluster_indices
        }

    def detect(
        self,
        output_path: Optional[Path] = None
    ) -> Dict:
        """
        Run full duplicate detection pipeline.

        Args:
            output_path: Optional path to save results

        Returns:
            Dictionary with detection results
        """
        # Find all duplicates
        duplicates = self.find_all_duplicates()

        # Build clusters
        clusters = self.build_clusters(duplicates)

        # Format clusters
        formatted_clusters = []
        for i, cluster_indices in enumerate(clusters):
            formatted = self.format_cluster(cluster_indices, i)
            formatted_clusters.append(formatted)

        # Build results
        total_duplicates = sum(len(c) for c in clusters)
        unique_complaints = self.index.ntotal - total_duplicates + len(clusters)
        deduplication_rate = (1 - unique_complaints / self.index.ntotal) * 100

        results = {
            'total_complaints': int(self.index.ntotal),
            'total_duplicates': total_duplicates,
            'unique_incidents': len(clusters) + (self.index.ntotal - total_duplicates),
            'duplicate_clusters': len(clusters),
            'deduplication_rate': round(deduplication_rate, 2),
            'similarity_threshold': self.similarity_threshold,
            'clusters': formatted_clusters,
            'created_at': datetime.now().isoformat()
        }

        # Save if output path
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"[SAVED] Results: {output_path}")

        return results

    def find_duplicates_for_complaint(
        self,
        complaint_text: str,
        model_name: str = 'all-MiniLM-L6-v2',
        k: int = 10
    ) -> List[Dict]:
        """
        Find duplicates for a new complaint text.

        Args:
            complaint_text: New complaint text
            model_name: Model for embedding
            k: Number of neighbors to check

        Returns:
            List of potential duplicates with similarity scores
        """
        from sentence_transformers import SentenceTransformer

        # Load model
        model = SentenceTransformer(model_name)

        # Generate embedding
        embedding = model.encode(
            [complaint_text],
            convert_to_numpy=True,
            normalize_embeddings=True
        ).astype(np.float32)

        # Search
        distances, indices = self.index.search(embedding, k)

        # Filter by threshold
        duplicates = []
        for dist, idx in zip(distances[0], indices[0]):
            if dist >= self.similarity_threshold:
                dup_info = {
                    'index': int(idx),
                    'similarity': float(dist)
                }
                if self.metadata and 'metadata' in self.metadata:
                    if idx < len(self.metadata['metadata']):
                        dup_info.update(self.metadata['metadata'][idx])
                duplicates.append(dup_info)

        return duplicates


def main():
    """Main entry point for duplicate detection."""
    parser = argparse.ArgumentParser(
        description='Detect duplicate complaints using FAISS'
    )
    parser.add_argument(
        '--index', '-i',
        type=str,
        default='ai-engine/duplicate_detection/faiss.index',
        help='Path to FAISS index'
    )
    parser.add_argument(
        '--embeddings', '-e',
        type=str,
        default='ai-engine/duplicate_detection/embeddings.npy',
        help='Path to embeddings file'
    )
    parser.add_argument(
        '--metadata', '-m',
        type=str,
        default='ai-engine/duplicate_detection/embedding_metadata.json',
        help='Path to metadata JSON'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='ai-engine/duplicate_detection/duplicate_clusters.json',
        help='Path to save results'
    )
    parser.add_argument(
        '--threshold', '-t',
        type=float,
        default=0.85,
        help='Similarity threshold for duplicates'
    )
    parser.add_argument(
        '--max-neighbors',
        type=int,
        default=50,
        help='Maximum neighbors to search per query'
    )
    parser.add_argument(
        '--min-cluster-size',
        type=int,
        default=2,
        help='Minimum cluster size'
    )
    parser.add_argument(
        '--query',
        type=str,
        default=None,
        help='Query text for single complaint search'
    )

    args = parser.parse_args()

    # Resolve paths
    project_root = Path(__file__).parent.parent.parent
    index_path = Path(args.index) if Path(args.index).is_absolute() else project_root / args.index
    embeddings_path = Path(args.embeddings) if Path(args.embeddings).is_absolute() else project_root / args.embeddings
    metadata_path = Path(args.metadata) if Path(args.metadata).is_absolute() else project_root / args.metadata
    output_path = Path(args.output) if Path(args.output).is_absolute() else project_root / args.output

    # Check files exist
    for p, name in [(index_path, 'index'), (embeddings_path, 'embeddings')]:
        if not p.exists():
            print(f"[ERROR] {name} file not found: {p}")
            print(f"[INFO] Run build_index.py first")
            sys.exit(1)

    metadata_path = Path(args.metadata) if Path(args.metadata).is_absolute() else project_root / args.metadata

    # Initialize detector
    detector = DuplicateDetector(
        similarity_threshold=args.threshold,
        max_neighbors=args.max_neighbors,
        min_cluster_size=args.min_cluster_size
    )

    # Load files
    detector.load_index(index_path)
    detector.load_embeddings(embeddings_path)
    if metadata_path.exists():
        detector.load_metadata(metadata_path)

    # Handle query mode
    if args.query:
        print(f"\n[INFO] Searching for duplicates to: {args.query}")
        duplicates = detector.find_duplicates_for_complaint(args.query)

        print(f"\n[RESULTS] Found {len(duplicates)} potential duplicates:")
        for dup in duplicates[:5]:
            print(f"  - Similarity: {dup['similarity']:.2%}")
            if 'text' in dup:
                print(f"    Text: {dup['text'][:80]}...")
        return

    # Run detection
    results = detector.detect(output_path)

    # Print summary
    print("\n" + "=" * 60)
    print("DUPLICATE DETECTION RESULTS")
    print("=" * 60)
    print(f"Total complaints: {results['total_complaints']}")
    print(f"Unique incidents: {results['unique_incidents']}")
    print(f"Duplicate clusters: {results['duplicate_clusters']}")
    print(f"Deduplication rate: {results['deduplication_rate']}%")
    print(f"Similarity threshold: {results['similarity_threshold']}")
    print(f"\nOutput: {output_path}")


if __name__ == '__main__':
    main()
