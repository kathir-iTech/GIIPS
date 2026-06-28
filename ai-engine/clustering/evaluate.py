"""
Evaluation module for clustering quality assessment.
"""

import json
from pathlib import Path
from typing import Dict, Optional, List, Tuple
import numpy as np
import pandas as pd
from collections import defaultdict
from sklearn.metrics import (
    silhouette_score,
    calinski_harabasz_score,
    davies_bouldin_score
)


def evaluate_clustering(
    clusterer,
    ground_truth_labels: Optional[np.ndarray] = None
) -> Dict:
    """
    Evaluate clustering quality using intrinsic and extrinsic metrics.

    Args:
        clusterer: ComplaintClusterer instance with clustering results
        ground_truth_labels: Optional true labels for supervised evaluation

    Returns:
        Dictionary of evaluation metrics
    """
    if clusterer.embeddings is None or clusterer.labels is None:
        raise ValueError("Clusterer must have clustering results")

    embeddings = clusterer.embeddings
    labels = clusterer.labels

    results = {
        'n_clusters': clusterer.cluster_info['n_clusters'],
        'n_noise_items': clusterer.cluster_info['n_noise'],
        'total_items': clusterer.cluster_info['n_total'],
        'noise_ratio': clusterer.cluster_info['noise_ratio']
    }

    # Only compute cluster quality metrics if we have valid clusters
    valid_labels = labels[labels >= 0]
    valid_embeddings = embeddings[labels >= 0]

    if len(np.unique(valid_labels)) > 1:
        print("[INFO] Computing clustering quality metrics...")

        # Silhouette score (higher is better, range [-1, 1])
        results['silhouette_score'] = float(
            silhouette_score(valid_embeddings, valid_labels)
        )

        # Calinski-Harabasz score (higher is better)
        results['calinski_harabasz_score'] = float(
            calinski_harabasz_score(valid_embeddings, valid_labels)
        )

        # Davies-Bouldin score (lower is better)
        results['davies_bouldin_score'] = float(
            davies_bouldin_score(valid_embeddings, valid_labels)
        )

        print(f"[METRIC] Silhouette Score: {results['silhouette_score']:.4f}")
        print(f"[METRIC] Calinski-Harabasz Score: {results['calinski_harabasz_score']:.2f}")
        print(f"[METRIC] Davies-Bouldin Score: {results['davies_bouldin_score']:.4f}")

    # Cluster size distribution
    cluster_sizes = defaultdict(int)
    for label in labels:
        if label >= 0:
            cluster_sizes[label] += 1

    if cluster_sizes:
        sizes = list(cluster_sizes.values())
        results['cluster_size_stats'] = {
            'min': int(min(sizes)),
            'max': int(max(sizes)),
            'mean': float(np.mean(sizes)),
            'median': float(np.median(sizes)),
            'std': float(np.std(sizes))
        }

    # If ground truth available, compute supervised metrics
    if ground_truth_labels is not None:
        print("[INFO] Computing supervised metrics...")

        # Adjusted Rand Index
        from sklearn.metrics import (
            adjusted_rand_score,
            normalized_mutual_info_score,
            adjusted_mutual_info_score
        )

        results['adjusted_rand_index'] = float(
            adjusted_rand_score(ground_truth_labels, labels)
        )
        results['normalized_mutual_info'] = float(
            normalized_mutual_info_score(ground_truth_labels, labels)
        )
        results['adjusted_mutual_info'] = float(
            adjusted_mutual_info_score(ground_truth_labels, labels)
        )

        print(f"[METRIC] Adjusted Rand Index: {results['adjusted_rand_index']:.4f}")
        print(f"[METRIC] Normalized Mutual Info: {results['normalized_mutual_info']:.4f}")

    return results


def analyze_cluster_cohesion(clusterer) -> Dict:
    """
    Analyze the semantic cohesion within each cluster.

    Args:
        clusterer: ComplaintClusterer instance

    Returns:
        Dictionary with per-cluster cohesion analysis
    """
    if clusterer.embeddings is None:
        raise ValueError("No embeddings available")

    cohesion_analysis = {}
    embeddings = clusterer.embeddings
    labels = clusterer.labels

    unique_labels = np.unique(labels[labels >= 0])

    for label in unique_labels:
        mask = labels == label
        cluster_embeddings = embeddings[mask]

        if len(cluster_embeddings) < 2:
            cohesion_analysis[int(label)] = {
                'size': len(cluster_embeddings),
                'cohesion': 1.0,
                'diameter': 0.0
            }
            continue

        # Compute centroid
        centroid = cluster_embeddings.mean(axis=0)

        # Distances from centroid
        distances = np.linalg.norm(cluster_embeddings - centroid, axis=1)

        # Pairwise distances
        from sklearn.metrics.pairwise import cosine_distances
        pairwise = cosine_distances(cluster_embeddings)

        cohesion_analysis[int(label)] = {
            'size': len(cluster_embeddings),
            'mean_distance_to_centroid': float(np.mean(distances)),
            'max_distance_to_centroid': float(np.max(distances)),
            'mean_pairwise_distance': float(np.mean(pairwise[np.triu_indices(len(cluster_embeddings), k=1)])),
            'cohesion': float(1 - np.mean(distances))  # Higher is better
        }

    return cohesion_analysis


def find_cluster_outliers(clusterer: 'ComplaintClusterer', threshold: float = 0.5) -> Dict[int, List[int]]:
    """
    Find items that may not belong in their assigned cluster.

    Args:
        clusterer: ComplaintClusterer instance
        threshold: Distance threshold for outlier detection

    Returns:
        Dictionary mapping cluster label to list of outlier indices
    """
    if clusterer.embeddings is None:
        raise ValueError("No embeddings available")

    outliers = {}
    embeddings = clusterer.embeddings
    labels = clusterer.labels

    unique_labels = np.unique(labels[labels >= 0])

    for label in unique_labels:
        mask = labels == label
        cluster_embeddings = embeddings[mask]
        cluster_indices = np.where(mask)[0]

        if len(cluster_embeddings) < 2:
            continue

        # Compute centroid
        centroid = cluster_embeddings.mean(axis=0)

        # Compute distances
        distances = np.linalg.norm(cluster_embeddings - centroid, axis=1)

        # Find outliers
        outlier_mask = distances > threshold
        if outlier_mask.any():
            outliers[int(label)] = cluster_indices[outlier_mask].tolist()

    return outliers


def suggest_optimal_parameters(clusterer: 'ComplaintClusterer') -> Dict:
    """
    Analyze embeddings to suggest optimal DBSCAN parameters.

    Args:
        clusterer: ComplaintClusterer instance with embeddings

    Returns:
        Dictionary with parameter suggestions
    """
    if clusterer.embeddings is None:
        raise ValueError("No embeddings available - run clustering first")

    from sklearn.neighbors import NearestNeighbors

    embeddings = clusterer.embeddings

    # Compute k-NN distances for eps estimation
    k = clusterer.min_samples
    neigh = NearestNeighbors(n_neighbors=k, metric='cosine')
    neigh.fit(embeddings)
    distances, _ = neigh.kneighbors(embeddings)
    distances = np.sort(distances[:, k-1])

    # Suggested eps: knee point in k-distance graph
    # Simple heuristic: use median or 90th percentile
    suggested_eps = {
        'p50': float(np.percentile(distances, 50)),
        'p70': float(np.percentile(distances, 70)),
        'p90': float(np.percentile(distances, 90)),
        'median': float(np.median(distances))
    }

    return {
        'suggested_eps': suggested_eps,
        'suggested_min_samples': k,
        'recommendation': f"Try eps={suggested_eps['p70']:.3f} with min_samples=2-3"
    }


def validate_duplicate_detection(
    clusterer: 'ComplaintClusterer',
    known_duplicates: List[Tuple[int, int]]
) -> Dict:
    """
    Validate clustering by checking if known duplicates are in the same cluster.

    Args:
        clusterer: ComplaintClusterer instance
        known_duplicates: List of tuples (id1, id2) known to be duplicates

    Returns:
        Dictionary with validation results
    """
    if clusterer.labels is None:
        raise ValueError("No clustering results available")

    labels = clusterer.labels
    total_pairs = len(known_duplicates)
    correct_pairs = 0

    for idx1, idx2 in known_duplicates:
        if labels[idx1] == labels[idx2] and labels[idx1] >= 0:
            correct_pairs += 1

    recall = correct_pairs / total_pairs if total_pairs > 0 else 0

    return {
        'total_known_pairs': total_pairs,
        'correctly_clustered': correct_pairs,
        'recall': recall
    }


def generate_clustering_report(
    clusterer: 'ComplaintClusterer',
    output_dir: Path
) -> None:
    """
    Generate a comprehensive clustering report.

    Args:
        clusterer: ComplaintClusterer instance
        output_dir: Directory to save report
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Evaluate clustering
    metrics = evaluate_clustering(clusterer)
    cohesion = analyze_cluster_cohesion(clusterer)
    params = suggest_optimal_parameters(clusterer)
    outliers = find_cluster_outliers(clusterer)

    report = {
        "summary": {
            "n_clusters": metrics['n_clusters'],
            "n_total": metrics['total_items'],
            "noise_ratio": metrics['noise_ratio'],
            "silhouette": metrics.get('silhouette_score', 'N/A')
        },
        "metrics": metrics,
        "parameter_suggestions": params,
        "cluster_cohesion": cohesion,
        "outlier_count": sum(len(v) for v in outliers.values()),
        "clusters_with_outliers": list(outliers.keys())
    }

    # Save report
    with open(output_dir / 'clustering_report.json', 'w') as f:
        json.dump(report, f, indent=2, default=str)

    # Save cluster details
    cluster_details = []
    for label, info in cohesion.items():
        cluster_details.append({
            'cluster_label': label,
            'size': info['size'],
            'cohesion': info.get('cohesion', 0),
            'mean_distance': info.get('mean_distance_to_centroid', 0)
        })

    cluster_df = pd.DataFrame(cluster_details)
    cluster_df.to_csv(output_dir / 'cluster_details.csv', index=False)

    print(f"[SAVED] Clustering report saved to {output_dir}")


if __name__ == '__main__':
    from pathlib import Path

    # Load sample results
    results_dir = Path(__file__).parent.parent / 'outputs' / 'clustering'

    if (results_dir / 'embeddings.npy').exists():
        from .cluster import ComplaintClusterer
        clusterer = ComplaintClusterer.load(results_dir)
        metrics = evaluate_clustering(clusterer)
        print("\nCluster Quality Metrics:")
        for k, v in metrics.items():
            if isinstance(v, float):
                print(f"  {k}: {v:.4f}")
            else:
                print(f"  {k}: {v}")
    else:
        print("[WARNING] No clustering results found. Run cluster.py first.")
