"""
Evaluation module for complaint classification models.

Provides detailed evaluation metrics and visualization capabilities.
"""

import json
import pickle
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
    top_k_accuracy_score
)

from .train import ComplaintClassifier
from .utils import prepare_complaint_text, validate_dataframe


def evaluate_model(
    classifier: ComplaintClassifier,
    test_texts: pd.Series,
    test_labels: pd.Series,
    output_path: Optional[Path] = None
) -> Dict:
    """
    Evaluate a trained classifier on test data.

    Args:
        classifier: Trained ComplaintClassifier instance
        test_texts: Test text data
        test_labels: True labels
        output_path: Optional path to save evaluation results

    Returns:
        Dictionary of evaluation metrics
    """
    print("[INFO] Running evaluation...")

    # Vectorize test data
    X_test = classifier.vectorizer.transform(test_texts.values)
    y_test = classifier.label_encoder.transform(test_labels)

    # Predictions
    y_pred = classifier.classifier.predict(X_test)
    y_proba = classifier.classifier.predict_proba(X_test)

    # Basic metrics
    metrics = {
        'accuracy': accuracy_score(y_test, y_pred),
        'precision_weighted': precision_score(y_test, y_pred, average='weighted'),
        'recall_weighted': recall_score(y_test, y_pred, average='weighted'),
        'f1_weighted': f1_score(y_test, y_pred, average='weighted'),
        'precision_macro': precision_score(y_test, y_pred, average='macro'),
        'recall_macro': recall_score(y_test, y_pred, average='macro'),
        'f1_macro': f1_score(y_test, y_pred, average='macro'),
    }

    # Top-k accuracy
    metrics['top_3_accuracy'] = top_k_accuracy_score(y_test, y_proba, k=3)
    metrics['top_5_accuracy'] = top_k_accuracy_score(y_test, y_proba, k=5)

    # Per-class metrics
    class_report = classification_report(
        y_test, y_pred,
        target_names=classifier.classes_,
        output_dict=True,
        zero_division=0
    )

    # Confusion matrix
    conf_matrix = confusion_matrix(y_test, y_pred)

    # Build results
    results = {
        'metrics': {k: float(v) for k, v in metrics.items()},
        'num_classes': len(classifier.classes_),
        'num_samples': len(test_labels),
        'evaluation_date': datetime.now().isoformat(),
        'class_metrics': {
            name: {
                'precision': float(class_report[name]['precision']),
                'recall': float(class_report[name]['recall']),
                'f1_score': float(class_report[name]['f1-score']),
                'support': int(class_report[name]['support'])
            }
            for name in classifier.classes_
        },
        'confusion_matrix_shape': list(conf_matrix.shape)
    }

    # Print summary
    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)
    print(f"\nAccuracy:      {metrics['accuracy'] * 100:.2f}%")
    print(f"Precision:    {metrics['precision_weighted'] * 100:.2f}% (weighted)")
    print(f"Recall:       {metrics['recall_weighted'] * 100:.2f}% (weighted)")
    print(f"F1 Score:     {metrics['f1_weighted'] * 100:.2f}% (weighted)")
    print(f"Top-3 Acc:    {metrics['top_3_accuracy'] * 100:.2f}%")
    print(f"Top-5 Acc:    {metrics['top_5_accuracy'] * 100:.2f}%")

    # Save if path provided
    if output_path:
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save metrics JSON
        with open(output_path / 'evaluation_metrics.json', 'w') as f:
            json.dump(results, f, indent=2)

        # Save confusion matrix
        np.save(output_path / 'confusion_matrix.npy', conf_matrix)

        print(f"\n[SAVED] Evaluation results saved to {output_path}")

    return results


def cross_validate_model(
    classifier: ComplaintClassifier,
    texts: pd.Series,
    labels: pd.Series,
    n_folds: int = 5
) -> Dict:
    """
    Perform cross-validation on the classifier.

    Args:
        classifier: Classifier instance (will be retrained)
        texts: Text data
        labels: Labels
        n_folds: Number of CV folds

    Returns:
        Dictionary of CV metrics
    """
    from sklearn.model_selection import StratifiedKFold

    print(f"[INFO] Running {n_folds}-fold cross-validation...")

    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)

    fold_metrics = []

    for fold_idx, (train_idx, val_idx) in enumerate(skf.split(texts, labels)):
        print(f"\n[INFO] Fold {fold_idx + 1}/{n_folds}")

        # Split data
        X_train_fold = texts.iloc[train_idx]
        y_train_fold = labels.iloc[train_idx]
        X_val_fold = texts.iloc[val_idx]
        y_val_fold = labels.iloc[val_idx]

        # Train new classifier
        fold_classifier = ComplaintClassifier(
            max_features=classifier.max_features,
            ngram_range=classifier.ngram_range,
            random_state=classifier.random_state,
            max_iter=classifier.max_iter
        )
        fold_classifier.train(X_train_fold, y_train_fold)

        # Evaluate
        fold_metrics.append(fold_classifier.metrics)

    # Aggregate results
    cv_results = {
        'mean_accuracy': np.mean([m['accuracy'] for m in fold_metrics]),
        'std_accuracy': np.std([m['accuracy'] for m in fold_metrics]),
        'mean_precision': np.mean([m['precision'] for m in fold_metrics]),
        'std_precision': np.std([m['precision'] for m in fold_metrics]),
        'mean_recall': np.mean([m['recall'] for m in fold_metrics]),
        'std_recall': np.std([m['recall'] for m in fold_metrics]),
        'mean_f1': np.mean([m['f1_score'] for m in fold_metrics]),
        'std_f1': np.std([m['f1_score'] for m in fold_metrics]),
        'fold_results': fold_metrics
    }

    print("\n" + "=" * 60)
    print("CROSS-VALIDATION RESULTS")
    print("=" * 60)
    print(f"\nMean Accuracy:  {cv_results['mean_accuracy'] * 100:.2f}% (±{cv_results['std_accuracy'] * 100:.2f}%)")
    print(f"Mean F1 Score:  {cv_results['mean_f1'] * 100:.2f}% (±{cv_results['std_f1'] * 100:.2f}%)")

    return cv_results


def analyze_errors(
    classifier: ComplaintClassifier,
    test_texts: pd.Series,
    test_labels: pd.Series,
    output_path: Optional[Path] = None
) -> pd.DataFrame:
    """
    Analyze classification errors to identify patterns.

    Args:
        classifier: Trained classifier
        test_texts: Test text data
        test_labels: True labels
        output_path: Path to save error analysis

    Returns:
        DataFrame of errors with analysis
    """
    # Predictions
    predictions = classifier.predict(test_texts.tolist())
    true_labels = test_labels.values

    # Create error DataFrame
    errors_df = pd.DataFrame({
        'text': test_texts.values,
        'true_label': true_labels,
        'predicted_label': predictions,
        'text_length': test_texts.str.len()
    })

    # Mark correct/incorrect
    errors_df['is_correct'] = errors_df['true_label'] == errors_df['predicted_label']
    errors_df['error_type'] = errors_df['is_correct'].map({True: 'correct', False: 'incorrect'})

    # Filter to errors only
    errors_only = errors_df[~errors_df['is_correct']].copy()

    print(f"\n[INFO] Total test samples: {len(test_labels)}")
    print(f"[INFO] Correct predictions: {errors_df['is_correct'].sum()}")
    print(f"[INFO] Incorrect predictions: {len(errors_only)}")

    # Most common error patterns
    if len(errors_only) > 0:
        error_patterns = errors_only.groupby(['true_label', 'predicted_label']).size().reset_index(name='count')
        error_patterns = error_patterns.sort_values('count', ascending=False)

        print("\nMost common error patterns:")
        print(error_patterns.head(10).to_string())

        if output_path:
            output_path = Path(output_path)
            output_path.mkdir(parents=True, exist_ok=True)
            errors_only.to_csv(output_path / 'classification_errors.csv', index=False)
            error_patterns.to_csv(output_path / 'error_patterns.csv', index=False)

    return errors_df


if __name__ == '__main__':
    import sys

    # Evaluate an existing model
    model_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / 'models' / 'classification'
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).parent.parent / 'outputs' / 'classification_eval'

    print(f"[INFO] Loading model from {model_dir}")
    classifier = ComplaintClassifier.load(model_dir)

    # Load test data
    dataset_path = Path(__file__).parent.parent.parent / 'nyc311_working.csv'
    if dataset_path.exists():
        df = pd.read_csv(dataset_path)
        texts = prepare_complaint_text(df, 'Problem', 'Problem Detail')
        labels = df.loc[texts.notna(), 'Problem']
        texts = texts.dropna()

        evaluate_model(classifier, texts.sample(min(1000, len(texts)), random_state=42),
                      labels.sample(min(1000, len(labels)), random_state=42),
                      output_dir)
    else:
        print(f"[WARNING] Dataset not found at {dataset_path}")
