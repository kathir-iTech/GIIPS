"""
Duplicate Incident Detection and Clustering Module.

Uses SentenceTransformer embeddings and DBSCAN clustering to identify
complaints that describe the same underlying incident.
"""

import json
import pickle
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Union
from collections import defaultdict

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_distances

from .utils import (
    preprocess_for_clustering,
    group_by_location,
    validate_clustering_params,
    prepare_clustering_dataframe
)


class ComplaintClusterer:
    """
    SentenceTransformer-based clustering for duplicate complaint detection.
    """

    def __init__(
        self,
        model_name: str = 'all-MiniLM-L6-v2',
        eps: float = 0.3,
        min_samples: int = 2,
        batch_size: int = 32,
        device: Optional[str] = None
    ):
        """
        Initialize the complaint clusterer.

        Args:
            model_name: Name of SentenceTransformer model
            eps: DBSCAN epsilon parameter (neighborhood radius for cosine distance)
            min_samples: DBSCAN minimum samples parameter
            batch_size: Batch size for embedding generation
            device: Device to use ('cuda', 'cpu', or None for auto)
        """
        self.model_name = model_name
        self.eps = eps
        self.min_samples = min_samples
        self.batch_size = batch_size
        self.device = device

        self.model = None
        self.embeddings: Optional[np.ndarray] = None
        self.labels: Optional[np.ndarray] = None
        self.cluster_info: Dict = {}

    def _load_model(self):
        """Lazy-load the SentenceTransformer model."""
        if self.model is None:
            try:
                from sentence_transformers import SentenceTransformer
                print(f"[INFO] Loading SentenceTransformer model: {self.model_name}")
                self.model = SentenceTransformer(self.model_name, device=self.device)
                print(f"[INFO] Model loaded on device: {self.device or 'auto-detected'}")
            except ImportError:
                raise ImportError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )

    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of complaint texts

        Returns:
            Array of embeddings (n_samples, embedding_dim)
        """
        self._load_model()

        print(f"[INFO] Generating embeddings for {len(texts)} texts...")
        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        print(f"[INFO] Embedding shape: {embeddings.shape}")
        return embeddings

    def cluster(
        self,
        texts: List[str],
        ids: Optional[List] = None,
        ward_hints: Optional[List[str]] = None
    ) -> Dict:
        """
        Cluster complaints into incidents using DBSCAN.

        Args:
            texts: List of complaint texts
            ids: Optional list of complaint IDs
            ward_hints: Optional list of ward names for location-aware clustering

        Returns:
            Dictionary with clustering results
        """
        if ids is None:
            ids = list(range(len(texts)))

        # Generate embeddings
        self.embeddings = self.generate_embeddings(texts)

        # Compute cosine distance matrix
        print("[INFO] Computing distance matrix...")
        distance_matrix = cosine_distances(self.embeddings)

        # Run DBSCAN
        print(f"[INFO] Running DBSCAN (eps={self.eps}, min_samples={self.min_samples})...")

        dbscan = DBSCAN(
            eps=self.eps,
            min_samples=self.min_samples,
            metric='precomputed'
        )
        self.labels = dbscan.fit_predict(distance_matrix)

        # Process results
        self._process_clustering_results(ids, texts, ward_hints)

        return self.cluster_info

    def _process_clustering_results(
        self,
        ids: List,
        texts: List[str],
        ward_hints: Optional[List[str]]
    ):
        """Process and organize clustering results."""
        # Cluster assignments
        unique_labels = set(self.labels)

        # Count clusters
        n_clusters = len([l for l in unique_labels if l >= 0])
        n_noise = list(self.labels).count(-1)

        print(f"[RESULTS] Found {n_clusters} clusters, {n_noise} noise points")

        # Build cluster map
        clusters = defaultdict(list)
        for i, label in enumerate(self.labels):
            clusters[label].append({
                'id': ids[i],
                'text': texts[i],
                'index': i,
                'ward': ward_hints[i] if ward_hints else None
            })

        self.cluster_info = {
            'n_clusters': n_clusters,
            'n_noise': n_noise,
            'n_total': len(ids),
            'noise_ratio': n_noise / len(ids) if len(ids) > 0 else 0,
            'labels': self.labels.tolist(),
            'clusters': {k: v for k, v in clusters.items() if k >= 0},
            'noise_items': clusters.get(-1, [])
        }

        # Calculate cluster statistics
        cluster_sizes = [len(v) for k, v in clusters.items() if k >= 0]
        if cluster_sizes:
            self.cluster_info['avg_cluster_size'] = np.mean(cluster_sizes)
            self.cluster_info['max_cluster_size'] = max(cluster_sizes)
            self.cluster_info['min_cluster_size'] = min(cluster_sizes)

    def cluster_with_ward_separation(
        self,
        complaints: List[Dict],
        text_key: str = 'text',
        ward_key: str = 'ward'
    ) -> Dict:
        """
        Cluster complaints within each ward separately for better accuracy.

        Args:
            complaints: List of complaint dictionaries
            text_key: Key for text field
            ward_key: Key for ward field

        Returns:
            Combined clustering results
        """
        all_texts = []
        all_ids = []
        all_wards = []

        # Extract data
        for c in complaints:
            text = c.get(text_key, '')
            processed = preprocess_for_clustering(text)
            if processed:
                all_texts.append(processed)
                all_ids.append(c.get('id', len(all_texts)))
                all_wards.append(c.get(ward_key, 'Unknown'))

        # Cluster all together
        return self.cluster(all_texts, all_ids, all_wards)

    def get_cluster_members(self, cluster_label: int) -> List[Dict]:
        """
        Get all members of a specific cluster.

        Args:
            cluster_label: Cluster label

        Returns:
            List of cluster member dictionaries
        """
        if self.cluster_info is None:
            raise RuntimeError("No clustering results available")

        return self.cluster_info['clusters'].get(cluster_label, [])

    def get_representative_text(self, cluster_label: int) -> Optional[str]:
        """
        Get the most representative text from a cluster
        (the one closest to the cluster centroid).

        Args:
            cluster_label: Cluster label

        Returns:
            Representative text string
        """
        members = self.get_cluster_members(cluster_label)
        if not members:
            return None

        if len(members) == 1:
            return members[0]['text']

        # Find centroid index
        indices = [m['index'] for m in members]
        cluster_embeddings = self.embeddings[indices]
        centroid = cluster_embeddings.mean(axis=0)

        # Find closest to centroid
        distances = np.linalg.norm(cluster_embeddings - centroid, axis=1)
        best_idx = indices[np.argmin(distances)]

        return members[np.argmin(distances)]['text']

    def compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute semantic similarity between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score between 0 and 1
        """
        self._load_model()

        embeddings = self.model.encode([text1, text2], normalize_embeddings=True)
        similarity = np.dot(embeddings[0], embeddings[1])

        return float(similarity)

    def find_duplicates(
        self,
        new_complaint: str,
        existing_complaints: List[Dict],
        text_key: str = 'text',
        threshold: float = 0.8
    ) -> List[Dict]:
        """
        Find potential duplicates for a new complaint.

        Args:
            new_complaint: New complaint text
            existing_complaints: List of existing complaints
            text_key: Key for text field
            threshold: Similarity threshold

        Returns:
            List of potential duplicates with similarity scores
        """
        self._load_model()

        # Get embedding for new complaint
        new_embedding = self.model.encode(
            [preprocess_for_clustering(new_complaint)],
            normalize_embeddings=True
        )[0]

        # Get existing texts
        existing_texts = [
            preprocess_for_clustering(c.get(text_key, ''))
            for c in existing_complaints
        ]

        # Filter empty
        valid_indices = [i for i, t in enumerate(existing_texts) if t]
        valid_texts = [existing_texts[i] for i in valid_indices]

        if not valid_texts:
            return []

        # Get embeddings for existing
        existing_embeddings = self.model.encode(valid_texts, normalize_embeddings=True)

        # Compute similarities
        similarities = np.dot(existing_embeddings, new_embedding)

        # Find matches above threshold
        duplicates = []
        for i, sim in enumerate(similarities):
            if sim >= threshold:
                original_idx = valid_indices[i]
                duplicate = existing_complaints[original_idx].copy()
                duplicate['similarity'] = float(sim)
                duplicates.append(duplicate)

        # Sort by similarity
        duplicates.sort(key=lambda x: x['similarity'], reverse=True)

        return duplicates

    def save(self, output_dir: Path):
        """
        Save clustering results.

        Args:
            output_dir: Directory to save results
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save cluster info
        with open(output_dir / 'clustering_results.json', 'w') as f:
            json.dump({
                k: v for k, v in self.cluster_info.items()
                if k != 'labels'
            }, f, indent=2)

        # Save embeddings
        if self.embeddings is not None:
            np.save(output_dir / 'embeddings.npy', self.embeddings)

        # Save labels
        if self.labels is not None:
            np.save(output_dir / 'labels.npy', self.labels)

        print(f"[SAVED] Clustering results saved to {output_dir}")

    @classmethod
    def load(cls, input_dir: Path) -> 'ComplaintClusterer':
        """
        Load saved clustering results.

        Args:
            input_dir: Directory containing saved results

        Returns:
            ComplaintClusterer with loaded results
        """
        input_dir = Path(input_dir)

        instance = cls()

        with open(input_dir / 'clustering_results.json', 'r') as f:
            instance.cluster_info = json.load(f)

        instance.embeddings = np.load(input_dir / 'embeddings.npy')
        instance.labels = np.load(input_dir / 'labels.npy')

        print(f"[LOADED] Clustering results from {input_dir}")
        return instance


def cluster_complaints(
    complaints: List[Dict],
    output_dir: Path,
    text_key: str = 'text',
    eps: float = 0.3,
    min_samples: int = 2
) -> ComplaintClusterer:
    """
    Convenience function to cluster complaints and save results.

    Args:
        complaints: List of complaint dictionaries
        output_dir: Directory to save results
        text_key: Key for text field
        eps: DBSCAN epsilon parameter
        min_samples: DBSCAN min samples parameter

    Returns:
        Trained ComplaintClusterer instance
    """
    clusterer = ComplaintClusterer(eps=eps, min_samples=min_samples)
    clusterer.cluster_with_ward_separation(complaints, text_key)
    clusterer.save(output_dir)
    return clusterer


if __name__ == '__main__':
    import sys

    # Demo with sample data
    sample_complaints = [
        {'id': 1, 'text': 'Large pothole on Main Street near the traffic light, causing accidents', 'ward': 'W1'},
        {'id': 2, 'text': 'Big hole in the road on Main Street by the signal, dangerous for vehicles', 'ward': 'W1'},
        {'id': 3, 'text': 'Water pipe burst on Oak Avenue, flooding the street', 'ward': 'W2'},
        {'id': 4, 'text': 'Broken water main on Oak Ave causing severe flooding', 'ward': 'W2'},
        {'id': 5, 'text': 'Garbage not collected for two weeks on Pine Street', 'ward': 'W3'},
        {'id': 6, 'text': 'Main Street pothole is very deep and damaged my tire', 'ward': 'W1'},
        {'id': 7, 'text': 'Street light not working on the corner of Elm Street', 'ward': 'W4'},
        {'id': 8, 'text': 'The lamp post at Elm Street intersection is out', 'ward': 'W4'},
    ]

    output_dir = Path(__file__).parent.parent / 'outputs' / 'clustering'

    clusterer = ComplaintClusterer(eps=0.35, min_samples=2)
    results = clusterer.cluster_with_ward_separation(sample_complaints)
    clusterer.save(output_dir)

    print(f"\n[INFO] Found {results['n_clusters']} clusters from {results['n_total']} complaints")
    print(f"[INFO] Noise items (no cluster): {results['n_noise']}")

    # Show sample cluster
    for label, members in results['clusters'].items():
        print(f"\nCluster {label}:")
        for m in members[:3]:
            print(f"  - {m['text'][:60]}...")
