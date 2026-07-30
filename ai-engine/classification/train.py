"""
Complaint Classification Training Module.

Trains a TF-IDF + Logistic Regression classifier for categorizing complaints.
"""

import pickle
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, Optional

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report
)

from .utils import (
    prepare_complaint_text,
    validate_dataframe,
    get_category_distribution
)


class ComplaintClassifier:
    """
    TF-IDF + Logistic Regression classifier for complaint categorization.
    """

    def __init__(
        self,
        max_features: int = 10000,
        ngram_range: Tuple[int, int] = (1, 2),
        min_df: int = 2,
        max_df: float = 0.95,
        random_state: int = 42,
        max_iter: int = 1000
    ):
        """
        Initialize the classifier.

        Args:
            max_features: Maximum vocabulary size
            ngram_range: Range of n-grams to include
            min_df: Minimum document frequency
            max_df: Maximum document frequency (as proportion)
            random_state: Random seed for reproducibility
            max_iter: Maximum iterations for Logistic Regression
        """
        self.max_features = max_features
        self.ngram_range = ngram_range
        self.min_df = min_df
        self.max_df = max_df
        self.random_state = random_state
        self.max_iter = max_iter

        self.vectorizer: Optional[TfidfVectorizer] = None
        self.classifier: Optional[LogisticRegression] = None
        self.label_encoder: Optional[LabelEncoder] = None
        self.classes_: Optional[np.ndarray] = None
        self.metrics: Dict = {}

    def _create_vectorizer(self) -> TfidfVectorizer:
        """Create and return a configured TF-IDF vectorizer."""
        return TfidfVectorizer(
            max_features=self.max_features,
            ngram_range=self.ngram_range,
            min_df=self.min_df,
            max_df=self.max_df,
            stop_words='english',
            lowercase=True,
            strip_accents='unicode'
        )

    def train(
        self,
        texts: pd.Series,
        labels: pd.Series,
        test_size: float = 0.2
    ) -> Dict:
        """
        Train the complaint classifier.

        Args:
            texts: Series of complaint text
            labels: Series of category labels
            test_size: Proportion of data for testing

        Returns:
            Dictionary of training metrics
        """
        print(f"[INFO] Training classifier on {len(texts)} samples...")

        # Encode labels
        self.label_encoder = LabelEncoder()
        y = self.label_encoder.fit_transform(labels)
        self.classes_ = self.label_encoder.classes_

        print(f"[INFO] Found {len(self.classes_)} unique categories")

        # Split data
        X_train_text, X_test_text, y_train, y_test = train_test_split(
            texts.values,
            y,
            test_size=test_size,
            random_state=self.random_state,
            stratify=y
        )

        print(f"[INFO] Train samples: {len(X_train_text)}, Test samples: {len(X_test_text)}")

        # Vectorize text
        print("[INFO] Vectorizing text data...")
        self.vectorizer = self._create_vectorizer()
        X_train = self.vectorizer.fit_transform(X_train_text)
        X_test = self.vectorizer.transform(X_test_text)

        print(f"[INFO] Feature matrix shape: {X_train.shape}")
        print(f"[INFO] Vocabulary size: {len(self.vectorizer.vocabulary_)}")

        # Train classifier
        print("[INFO] Training Logistic Regression model...")
        self.classifier = LogisticRegression(
            max_iter=self.max_iter,
            random_state=self.random_state,
            multi_class='multinomial',
            solver='lbfgs',
            n_jobs=-1
        )
        self.classifier.fit(X_train, y_train)

        # Evaluate
        self._evaluate(X_test, y_test)

        return self.metrics

    def _evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> None:
        """Evaluate the trained model."""
        print("[INFO] Evaluating model...")

        y_pred = self.classifier.predict(X_test)

        self.metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, average='weighted'),
            'recall': recall_score(y_test, y_pred, average='weighted'),
            'f1_score': f1_score(y_test, y_pred, average='weighted'),
            'num_classes': len(self.classes_),
            'num_samples': len(y_test)
        }

        print(f"[RESULTS] Accuracy:  {self.metrics['accuracy'] * 100:.2f}%")
        print(f"[RESULTS] Precision: {self.metrics['precision'] * 100:.2f}%")
        print(f"[RESULTS] Recall:    {self.metrics['recall'] * 100:.2f}%")
        print(f"[RESULTS] F1 Score:  {self.metrics['f1_score'] * 100:.2f}%")

        # Store confusion matrix
        self.metrics['confusion_matrix'] = confusion_matrix(y_test, y_pred).tolist()

        # FEATURE 7: real per-category metrics
        report = classification_report(y_test, y_pred, target_names=self.classes_, output_dict=True)
        per_cat = {}
        for label, metrics_dict in report.items():
            if label in ('accuracy', 'macro avg', 'weighted avg'):
                continue
            per_cat[label] = {
                'precision': round(metrics_dict['precision'], 4),
                'recall': round(metrics_dict['recall'], 4),
                'f1_score': round(metrics_dict['f1-score'], 4),
                'support': metrics_dict['support'],
            }
        self.metrics['per_category_metrics'] = per_cat

    def predict(self, texts: list) -> np.ndarray:
        """
        Predict categories for new texts.

        Args:
            texts: List of text strings

        Returns:
            Array of predicted category labels
        """
        if self.vectorizer is None or self.classifier is None:
            raise RuntimeError("Model not trained. Call train() first or load a saved model.")

        X = self.vectorizer.transform(texts)
        y_pred = self.classifier.predict(X)
        return self.label_encoder.inverse_transform(y_pred)

    def predict_proba(self, texts: list) -> np.ndarray:
        """
        Get prediction probabilities for new texts.

        Args:
            texts: List of text strings

        Returns:
            Array of probability distributions
        """
        if self.vectorizer is None or self.classifier is None:
            raise RuntimeError("Model not trained. Call train() first or load a saved model.")

        X = self.vectorizer.transform(texts)
        return self.classifier.predict_proba(X)

    def save(self, output_dir: Path) -> None:
        """
        Save trained model artifacts.

        Args:
            output_dir: Directory to save models
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save vectorizer
        with open(output_dir / 'vectorizer.pkl', 'wb') as f:
            pickle.dump(self.vectorizer, f)

        # Save classifier
        with open(output_dir / 'classifier.pkl', 'wb') as f:
            pickle.dump(self.classifier, f)

        # Save label encoder
        with open(output_dir / 'label_encoder.pkl', 'wb') as f:
            pickle.dump(self.label_encoder, f)

        # Save metrics
        with open(output_dir / 'metrics.json', 'w') as f:
            json.dump({k: v for k, v in self.metrics.items() if k != 'confusion_matrix'}, f, indent=2)

        # FEATURE 7: update metadata.json with per_category_metrics
        metadata_path = output_dir / 'metadata.json'
        if metadata_path.exists():
            try:
                with open(metadata_path) as f:
                    meta = json.load(f)
            except Exception:
                meta = {}
            meta['per_category_metrics'] = self.metrics.get('per_category_metrics', {})
            with open(metadata_path, 'w') as f:
                json.dump(meta, f, indent=2)
            print(f"[SAVED] Updated metadata.json with per-category metrics")

        print(f"[SAVED] Model artifacts saved to {output_dir}")

    @classmethod
    def load(cls, model_dir: Path) -> 'ComplaintClassifier':
        """
        Load a trained model from disk.

        Args:
            model_dir: Directory containing saved model

        Returns:
            Loaded ComplaintClassifier instance
        """
        model_dir = Path(model_dir)

        instance = cls()

        with open(model_dir / 'vectorizer.pkl', 'rb') as f:
            instance.vectorizer = pickle.load(f)

        with open(model_dir / 'classifier.pkl', 'rb') as f:
            instance.classifier = pickle.load(f)

        with open(model_dir / 'label_encoder.pkl', 'rb') as f:
            instance.label_encoder = pickle.load(f)

        instance.classes_ = instance.label_encoder.classes_

        print(f"[LOADED] Model loaded from {model_dir}")
        return instance


def train_from_dataset(
    dataset_path: Path,
    output_dir: Path,
    problem_col: str = 'Problem',
    detail_col: str = 'Problem Detail',
    sample_size: Optional[int] = None
) -> ComplaintClassifier:
    """
    Train a classifier from a dataset file.

    Args:
        dataset_path: Path to CSV dataset
        output_dir: Directory to save trained model
        problem_col: Name of problem column
        detail_col: Name of detail column
        sample_size: Optional sample size for development

    Returns:
        Trained ComplaintClassifier instance
    """
    print(f"[INFO] Loading dataset from {dataset_path}")
    df = pd.read_csv(dataset_path)
    print(f"[INFO] Loaded {len(df)} records")

    # Validate columns
    required = [problem_col, detail_col]
    validate_dataframe(df, required)

    # Rename columns if needed
    rename_map = {}
    if problem_col == 'Complaint Type':
        rename_map['Complaint Type'] = 'Problem'
    if detail_col == 'Descriptor':
        rename_map['Descriptor'] = 'Problem Detail'
    if rename_map:
        df = df.rename(columns=rename_map)
        problem_col = rename_map.get(problem_col, problem_col)
        detail_col = rename_map.get(detail_col, detail_col)

    # Sample if requested
    if sample_size and len(df) > sample_size:
        df = df.sample(n=sample_size, random_state=42)
        print(f"[INFO] Sampled {len(df)} records for training")

    # Prepare text
    texts = prepare_complaint_text(df, problem_col, detail_col)

    # Remove nulls
    valid_mask = texts.notna() & texts.str.strip().str.len() > 0
    texts = texts[valid_mask]
    labels = df.loc[valid_mask, problem_col]

    # Train
    classifier = ComplaintClassifier()
    classifier.train(texts, labels)

    # Save
    classifier.save(output_dir)

    return classifier


if __name__ == '__main__':
    import sys

    # Default paths
    project_root = Path(__file__).parent.parent.parent
    dataset_path = project_root / 'nyc311_working.csv'
    output_dir = Path(__file__).parent.parent / 'models' / 'classification'

    # Allow command line override
    if len(sys.argv) > 1:
        dataset_path = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output_dir = Path(sys.argv[2])

    train_from_dataset(dataset_path, output_dir)
