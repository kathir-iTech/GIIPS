"""
build_index.py

Build FAISS index for fast similarity search on complaint embeddings.

This script:
1. Loads pre-computed embeddings
2. Builds a FAISS index (IVF or IndexFlatIP for cosine similarity)
3. Saves the index for production use

Author: GIIPS AI Engine
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple

import numpy as np

# FAISS for similarity search
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("[WARNING] FAISS not installed. Install with: pip install faiss-cpu or faiss-gpu")


class FAISSIndexBuilder:
    """
    Build and manage FAISS indices for duplicate detection.
    """

    def __init__(
        self,
        index_type: str = 'flat',
        n_lists: int = 100,
        n_probe: int = 10,
        use_gpu: bool = False
    ):
        """
        Initialize the index builder.

        Args:
            index_type: Type of index ('flat', 'ivf', 'hnsw')
            n_lists: Number of Voronoi cells for IVF index
            n_probe: Number of cells to probe during search
            use_gpu: Whether to use GPU acceleration
        """
        self.index_type = index_type
        self.n_lists = n_lists
        self.n_probe = n_probe
        self.use_gpu = use_gpu
        self.index = None
        self.embedding_dim = None

        if not FAISS_AVAILABLE:
            raise ImportError("FAISS is required. Install with: pip install faiss-cpu")

    def load_embeddings(self, embeddings_path: Path) -> np.ndarray:
        """
        Load embeddings from numpy file.

        Args:
            embeddings_path: Path to embeddings.npy

        Returns:
            Numpy array of embeddings
        """
        print(f"[INFO] Loading embeddings from: {embeddings_path}")
        embeddings = np.load(embeddings_path)

        # Ensure float32 for FAISS
        if embeddings.dtype != np.float32:
            embeddings = embeddings.astype(np.float32)

        print(f"[INFO] Loaded embeddings. Shape: {embeddings.shape}")
        self.embedding_dim = embeddings.shape[1]

        return embeddings

    def build_flat_index(self, embeddings: np.ndarray) -> faiss.Index:
        """
        Build a flat (brute-force) index.

        Best for:
        - Small to medium datasets (< 1M vectors)
        - Exact search required
        - Highest accuracy

        Args:
            embeddings: Embedding matrix (n, d)

        Returns:
            FAISS IndexFlatIP index
        """
        print("[INFO] Building flat index (exact search)...")

        # IndexFlatIP for inner product (cosine similarity with normalized vectors)
        index = faiss.IndexFlatIP(self.embedding_dim)

        # Add vectors
        index.add(embeddings)

        print(f"[INFO] Flat index built. Total vectors: {index.ntotal}")
        return index

    def build_ivf_index(self, embeddings: np.ndarray) -> faiss.Index:
        """
        Build an IVF (Inverted File) index.

        Best for:
        - Large datasets (> 100K vectors)
        - Approximate search acceptable
        - Fast search required

        Args:
            embeddings: Embedding matrix (n, d)

        Returns:
            FAISS IndexIVFFlat index
        """
        n_vectors = embeddings.shape[0]

        # Adjust n_lists based on dataset size
        n_lists = min(self.n_lists, int(np.sqrt(n_vectors)))

        print(f"[INFO] Building IVF index with {n_lists} cells...")

        # Quantizer
        quantizer = faiss.IndexFlatIP(self.embedding_dim)

        # IVF index
        index = faiss.IndexIVFFlat(
            quantizer,
            self.embedding_dim,
            n_lists,
            faiss.METRIC_INNER_PRODUCT
        )

        # Train on subset if large dataset
        if n_vectors > 100000:
            print("[INFO] Training index on subset...")
            train_size = min(n_vectors, 100000)
            train_indices = np.random.choice(n_vectors, train_size, replace=False)
            train_vectors = embeddings[train_indices]
            index.train(train_vectors)
        else:
            print("[INFO] Training index...")
            index.train(embeddings)

        # Add vectors
        index.add(embeddings)

        # Set n_probe for search
        index.nprobe = min(self.n_probe, n_lists)

        print(f"[INFO] IVF index built. Total vectors: {index.ntotal}")
        print(f"[INFO] N lists: {n_lists}, N probe: {index.nprobe}")
        return index

    def build_hnsw_index(self, embeddings: np.ndarray) -> faiss.Index:
        """
        Build an HNSW (Hierarchical Navigable Small World) index.

        Best for:
        - Very fast approximate search
        - High recall required
        - Memory is available

        Args:
            embeddings: Embedding matrix (n, d)

        Returns:
            FAISS IndexHNSW index
        """
        print("[INFO] Building HNSW index...")

        # HNSW parameters
        M = 32  # Number of connections per layer
        efConstruction = 200  # Build time accuracy

        index = faiss.IndexHNSWFlat(
            self.embedding_dim,
            M,
            faiss.METRIC_INNER_PRODUCT
        )
        index.hnsw.efConstruction = efConstruction

        # Add vectors
        index.add(embeddings)

        print(f"[INFO] HNSW index built. Total vectors: {index.ntotal}")
        return index

    def build_index(self, embeddings: np.ndarray) -> faiss.Index:
        """
        Build the appropriate index based on configuration.

        Args:
            embeddings: Embedding matrix

        Returns:
            FAISS index
        """
        if self.index_type == 'flat':
            index = self.build_flat_index(embeddings)
        elif self.index_type == 'ivf':
            index = self.build_ivf_index(embeddings)
        elif self.index_type == 'hnsw':
            index = self.build_hnsw_index(embeddings)
        else:
            raise ValueError(f"Unknown index type: {self.index_type}")

        return index

    def save_index(self, output_path: Path) -> None:
        """
        Save FAISS index to disk.

        Args:
            output_path: Path to save index
        """
        if self.index is None:
            raise ValueError("No index to save")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        faiss.write_index(self.index, str(output_path))
        print(f"[SAVED] FAISS index: {output_path}")

    def build_and_save(
        self,
        embeddings_path: Path,
        output_path: Path,
        save_metadata: bool = True
    ) -> Dict:
        """
        Build index from embeddings and save to disk.

        Args:
            embeddings_path: Path to embeddings file
            output_path: Path to save index
            save_metadata: Whether to save index metadata

        Returns:
            Dictionary with index information
        """
        # Load embeddings
        embeddings = self.load_embeddings(embeddings_path)

        # Build index
        self.index = self.build_index(embeddings)

        # Save index
        self.save_index(output_path)

        # Save metadata
        metadata = {
            'index_type': self.index_type,
            'embedding_dim': self.embedding_dim,
            'n_vectors': int(self.index.ntotal),
            'created_at': datetime.now().isoformat(),
            'n_probe': self.n_probe if self.index_type == 'ivf' else None
        }

        if save_metadata:
            metadata_path = output_path.with_suffix('.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            print(f"[SAVED] Index metadata: {metadata_path}")

        return metadata


def test_index(
    index_path: Path,
    embeddings_path: Path,
    k: int = 5
) -> None:
    """
    Test the index with sample queries.

    Args:
        index_path: Path to saved index
        embeddings_path: Path to embeddings
        k: Number of neighbors to retrieve
    """
    print("\n" + "=" * 60)
    print("TESTING INDEX")
    print("=" * 60)

    # Load index
    index = faiss.read_index(str(index_path))
    print(f"[INFO] Loaded index. Total vectors: {index.ntotal}")

    # Load embeddings
    embeddings = np.load(embeddings_path).astype(np.float32)

    # Test with first 5 vectors
    query_vectors = embeddings[:5]
    distances, indices = index.search(query_vectors, k)

    print(f"\n[RESULTS] Top {k} neighbors for first 5 complaints:")
    for i in range(5):
        print(f"\nQuery {i}:")
        print(f"  Neighbors: {indices[i]}")
        print(f"  Distances: {distances[i]}")


def main():
    """Main entry point for index building."""
    parser = argparse.ArgumentParser(
        description='Build FAISS index for duplicate detection'
    )
    parser.add_argument(
        '--embeddings', '-e',
        type=str,
        default='ai-engine/duplicate_detection/embeddings.npy',
        help='Path to embeddings file'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='ai-engine/duplicate_detection/faiss.index',
        help='Path to save FAISS index'
    )
    parser.add_argument(
        '--type', '-t',
        type=str,
        choices=['flat', 'ivf', 'hnsw'],
        default='flat',
        help='Type of FAISS index to build'
    )
    parser.add_argument(
        '--n-lists',
        type=int,
        default=100,
        help='Number of Voronoi cells for IVF index'
    )
    parser.add_argument(
        '--n-probe',
        type=int,
        default=10,
        help='Number of cells to probe for IVF index'
    )
    parser.add_argument(
        '--gpu',
        action='store_true',
        help='Use GPU acceleration'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test the index after building'
    )

    args = parser.parse_args()

    # Resolve paths
    project_root = Path(__file__).parent.parent.parent
    embeddings_path = Path(args.embeddings)
    if not embeddings_path.is_absolute():
        embeddings_path = project_root / embeddings_path

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = project_root / output_path

    # Check embeddings exist
    if not embeddings_path.exists():
        print(f"[ERROR] Embeddings file not found: {embeddings_path}")
        print("[INFO] Run train_embeddings.py first")
        sys.exit(1)

    # Check FAISS is available
    if not FAISS_AVAILABLE:
        print("[ERROR] FAISS not installed")
        print("[INFO] Install with: pip install faiss-cpu")
        sys.exit(1)

    # Build index
    builder = FAISSIndexBuilder(
        index_type=args.type,
        n_lists=args.n_lists,
        n_probe=args.n_probe,
        use_gpu=args.gpu
    )

    metadata = builder.build_and_save(
        embeddings_path=embeddings_path,
        output_path=output_path
    )

    print("\n" + "=" * 60)
    print("INDEX BUILDING COMPLETE")
    print("=" * 60)
    print(f"Index type: {metadata['index_type']}")
    print(f"Vectors: {metadata['n_vectors']}")
    print(f"Dimensions: {metadata['embedding_dim']}")
    print(f"Output: {output_path}")

    # Test if requested
    if args.test:
        test_index(output_path, embeddings_path)


if __name__ == '__main__':
    main()
