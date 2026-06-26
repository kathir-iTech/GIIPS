"""
build_faiss.py

Build FAISS index for fast similarity search on complaint embeddings.

This script:
1. Loads pre-computed embeddings
2. Builds a FAISS index for cosine similarity search
3. Saves the index for production use

Supports multiple index types:
- flat: Exact search, best for small datasets (< 100K)
- ivf: Approximate search, good for large datasets (> 100K)
- hnsw: Fast approximate search, good recall

Author: GIIPS AI Engine
Version: 1.0.0
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

import numpy as np
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# FAISS for similarity search
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.error("FAISS not installed. Install with: pip install faiss-cpu or faiss-gpu")


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
            raise ImportError(
                "FAISS is required. Install with: pip install faiss-cpu"
            )

    def load_embeddings(self, embeddings_path: Path) -> np.ndarray:
        """
        Load embeddings from numpy file.

        Args:
            embeddings_path: Path to embeddings.npy

        Returns:
            Numpy array of embeddings (float32)
        """
        logger.info(f"Loading embeddings from: {embeddings_path}")
        embeddings = np.load(embeddings_path)

        # Ensure float32 for FAISS
        if embeddings.dtype != np.float32:
            embeddings = embeddings.astype(np.float32)
            logger.info("Converted embeddings to float32")

        logger.info(f"Loaded embeddings. Shape: {embeddings.shape}")
        self.embedding_dim = embeddings.shape[1]

        return embeddings

    def build_flat_index(self, embeddings: np.ndarray) -> faiss.Index:
        """
        Build a flat (brute-force) index for exact search.

        Best for:
        - Small to medium datasets (< 1M vectors)
        - Exact search required
        - Highest accuracy

        Args:
            embeddings: Embedding matrix (n, d) - must be L2 normalized

        Returns:
            FAISS IndexFlatIP index (inner product = cosine similarity for normalized vectors)
        """
        logger.info("Building flat index (exact cosine similarity search)...")

        n_vectors = embeddings.shape[0]

        # IndexFlatIP for inner product (cosine similarity with normalized vectors)
        # Progress bar for adding vectors
        index = faiss.IndexFlatIP(self.embedding_dim)

        # Add vectors in batches for progress tracking
        batch_size = 10000
        with tqdm(total=n_vectors, desc="Adding vectors", unit="vectors") as pbar:
            for start in range(0, n_vectors, batch_size):
                end = min(start + batch_size, n_vectors)
                index.add(embeddings[start:end])
                pbar.update(end - start)

        logger.info(f"Flat index built. Total vectors: {index.ntotal}")
        return index

    def build_ivf_index(self, embeddings: np.ndarray) -> faiss.Index:
        """
        Build an IVF (Inverted File) index for approximate search.

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
        # Rule of thumb: sqrt(n_vectors)
        n_lists = min(self.n_lists, int(np.sqrt(n_vectors)))
        n_lists = max(n_lists, 1)  # At least 1 cluster

        logger.info(f"Building IVF index with {n_lists} cells...")

        # Quantizer (index for the centroids)
        quantizer = faiss.IndexFlatIP(self.embedding_dim)

        # IVF index
        index = faiss.IndexIVFFlat(
            quantizer,
            self.embedding_dim,
            n_lists,
            faiss.METRIC_INNER_PRODUCT
        )

        # Train on data
        # FAISS requires training IVF to learn centroids
        train_size = min(n_vectors, n_lists * 39)  # FAISS recommendation: 39 * n_lists

        logger.info(f"Training index on {train_size} vectors...")
        np.random.seed(42)
        train_indices = np.random.choice(n_vectors, train_size, replace=False)
        train_vectors = embeddings[train_indices]

        with tqdm(desc="Training IVF", total=1, unit="step"):
            index.train(train_vectors)

        # Add vectors with progress bar
        batch_size = 10000
        with tqdm(total=n_vectors, desc="Adding vectors", unit="vectors") as pbar:
            for start in range(0, n_vectors, batch_size):
                end = min(start + batch_size, n_vectors)
                index.add(embeddings[start:end])
                pbar.update(end - start)

        # Set n_probe for search
        index.nprobe = min(self.n_probe, n_lists)

        logger.info(f"IVF index built. Total vectors: {index.ntotal}")
        logger.info(f"N lists: {n_lists}, N probe: {index.nprobe}")
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
        logger.info("Building HNSW index...")

        n_vectors = embeddings.shape[0]

        # HNSW parameters
        M = 32  # Number of connections per layer
        efConstruction = 200  # Build time accuracy (higher = better quality, slower build)

        index = faiss.IndexHNSWFlat(
            self.embedding_dim,
            M,
            faiss.METRIC_INNER_PRODUCT
        )
        index.hnsw.efConstruction = efConstruction

        # Add vectors with progress bar
        batch_size = 10000
        with tqdm(total=n_vectors, desc="Adding vectors (HNSW)", unit="vectors") as pbar:
            for start in range(0, n_vectors, batch_size):
                end = min(start + batch_size, n_vectors)
                index.add(embeddings[start:end])
                pbar.update(end - start)

        logger.info(f"HNSW index built. Total vectors: {index.ntotal}")
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
        logger.info(f"Saved FAISS index: {output_path}")

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
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            logger.info(f"Saved index metadata: {metadata_path}")

        return metadata

    def test_search(
        self,
        embeddings_path: Path,
        k: int = 5
    ) -> None:
        """
        Test the index with sample queries.

        Args:
            embeddings_path: Path to embeddings for test queries
            k: Number of neighbors to retrieve
        """
        logger.info("\n" + "=" * 60)
        logger.info("TESTING INDEX")
        logger.info("=" * 60)

        # Load test embeddings
        embeddings = np.load(embeddings_path).astype(np.float32)

        # Test with first 5 vectors
        n_test = min(5, len(embeddings))
        query_vectors = embeddings[:n_test]

        distances, indices = self.index.search(query_vectors, k)

        logger.info(f"\nTest results - Top {k} neighbors for first {n_test} complaints:")
        for i in range(n_test):
            logger.info(f"\nQuery {i}:")
            logger.info(f"  Neighbor indices: {indices[i].tolist()}")
            logger.info(f"  Similarities: {distances[i].tolist()}")


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
        embeddings_path = project_root / args.embeddings

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = project_root / args.output

    # Check embeddings exist
    if not embeddings_path.exists():
        logger.error(f"Embeddings file not found: {embeddings_path}")
        logger.info("Run train_embeddings.py first to generate embeddings")
        sys.exit(1)

    # Check FAISS is available
    if not FAISS_AVAILABLE:
        logger.error("FAISS not installed")
        logger.info("Install with: pip install faiss-cpu")
        sys.exit(1)

    try:
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
            builder.test_search(embeddings_path)

    except Exception as e:
        logger.error(f"Error building index: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
