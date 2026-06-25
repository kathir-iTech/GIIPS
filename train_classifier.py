"""
train_classifier.py

A machine learning pipeline for classifying NYC 311 complaints.

This script:
1. Loads complaint data from CSV
2. Preprocesses text by combining Problem and Problem Detail columns
3. Trains a TF-IDF + Logistic Regression classifier
4. Evaluates model performance
5. Saves trained model artifacts for deployment

Compatible with Python 3.12+
"""

# Standard library imports
import pickle
from pathlib import Path

# Third-party imports
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


def create_models_directory(models_dir: str = "models") -> Path:
    """
    Create the models directory if it does not exist.

    Args:
        models_dir: Path to the models directory

    Returns:
        Path object for the models directory
    """
    models_path = Path(models_dir)
    models_path.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Models directory ready: {models_path.absolute()}")
    return models_path


def load_dataset(filepath: str) -> pd.DataFrame:
    """
    Load the NYC 311 complaints dataset from CSV.

    Args:
        filepath: Path to the CSV file

    Returns:
        DataFrame containing the complaint data
    """
    print(f"[INFO] Loading dataset from: {filepath}")
    df = pd.read_csv(filepath)
    print(f"[INFO] Loaded {len(df)} records")
    print(f"[INFO] Columns available: {list(df.columns)}")
    return df


def preprocess_data(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """
    Preprocess the complaint data for classification.

    Steps:
    1. Rename columns if needed (Complaint Type -> Problem, Descriptor -> Problem Detail)
    2. Combine Problem and Problem Detail into a single text column
    3. Remove rows with missing values
    4. Return features (text) and labels (category)

    Args:
        df: Raw DataFrame with complaint data

    Returns:
        Tuple of (text_series, category_series)
    """
    print("[INFO] Preprocessing data...")

    # Create a copy to avoid modifying the original DataFrame
    df = df.copy()

    # Rename columns if they have the old names
    column_mapping = {}
    if 'Complaint Type' in df.columns and 'Problem' not in df.columns:
        column_mapping['Complaint Type'] = 'Problem'
    if 'Descriptor' in df.columns and 'Problem Detail' not in df.columns:
        column_mapping['Descriptor'] = 'Problem Detail'

    if column_mapping:
        df = df.rename(columns=column_mapping)
        print(f"[INFO] Renamed columns: {column_mapping}")

    # Verify required columns exist
    required_columns = ['Problem', 'Problem Detail']
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Required column '{col}' not found in dataset. Available columns: {list(df.columns)}")

    # Combine Problem and Problem Detail into a single text column
    # This gives more context for classification
    df['combined_text'] = df['Problem'].astype(str) + ' ' + df['Problem Detail'].astype(str)

    # Remove rows where either column had missing values
    # Check for 'nan' strings which can occur from astype(str) on NaN values
    initial_count = len(df)
    df = df[
        (df['Problem'].notna()) &
        (df['Problem Detail'].notna()) &
        (df['Problem'] != 'nan') &
        (df['Problem Detail'] != 'nan')
    ]
    removed_count = initial_count - len(df)
    print(f"[INFO] Removed {removed_count} rows with missing values")
    print(f"[INFO] Remaining records: {len(df)}")

    # Return the combined text and the category (using Problem as the category label)
    return df['combined_text'], df['Problem']


def encode_labels(labels: pd.Series) -> tuple[np.ndarray, LabelEncoder]:
    """
    Encode categorical labels as numeric values.

    Args:
        labels: Series of categorical label strings

    Returns:
        Tuple of (encoded_labels, fitted_label_encoder)
    """
    print("[INFO] Encoding labels...")
    label_encoder = LabelEncoder()
    encoded_labels = label_encoder.fit_transform(labels)
    num_classes = len(label_encoder.classes_)
    print(f"[INFO] Found {num_classes} unique categories")
    print(f"[INFO] Sample categories: {list(label_encoder.classes_[:10])}")
    return encoded_labels, label_encoder


def create_vectorizer() -> TfidfVectorizer:
    """
    Create a TF-IDF vectorizer with optimized parameters.

    The vectorizer converts text into numerical feature vectors:
    - max_features: Limits vocabulary size for memory efficiency
    - ngram_range: Includes both unigrams and bigrams for better context
    - min_df: Ignores very rare terms (appear in less than 2 documents)
    - max_df: Ignores very common terms (appear in more than 95% of documents)
    - stop_words: Removes common English stop words

    Returns:
        Configured TfidfVectorizer instance
    """
    return TfidfVectorizer(
        max_features=10000,
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.95,
        stop_words='english',
        lowercase=True,
        strip_accents='unicode'
    )


def train_classifier(
    X_train: np.ndarray,
    y_train: np.ndarray,
    max_iter: int = 1000,
    random_state: int = 42
) -> LogisticRegression:
    """
    Train a Logistic Regression classifier.

    Logistic Regression is chosen for:
    - Fast training and prediction
    - Good performance on text classification
    - Interpretable results
    - Works well with TF-IDF features

    Args:
        X_train: Training features (TF-IDF matrix)
        y_train: Training labels
        max_iter: Maximum iterations for convergence
        random_state: Random seed for reproducibility

    Returns:
        Trained LogisticRegression model
    """
    print("[INFO] Training Logistic Regression classifier...")
    classifier = LogisticRegression(
        max_iter=max_iter,
        random_state=random_state,
        multi_class='multinomial',
        solver='lbfgs'
    )
    classifier.fit(X_train, y_train)
    print("[INFO] Training complete")
    return classifier


def evaluate_model(
    classifier: LogisticRegression,
    X_test: np.ndarray,
    y_test: np.ndarray,
    label_encoder: LabelEncoder
) -> dict:
    """
    Evaluate the trained classifier on test data.

    Computes and prints:
    - Accuracy: Overall correct predictions
    - Precision: True positives / (True positives + False positives)
    - Recall: True positives / (True positives + False negatives)
    - F1 Score: Harmonic mean of precision and recall
    - Confusion Matrix: Breakdown of predictions by class

    Args:
        classifier: Trained classifier
        X_test: Test features
        y_test: Test labels
        label_encoder: Fitted label encoder for class names

    Returns:
        Dictionary containing all metrics
    """
    print("\n" + "=" * 60)
    print("MODEL EVALUATION RESULTS")
    print("=" * 60)

    # Generate predictions
    y_pred = classifier.predict(X_test)

    # Calculate metrics
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, average='weighted')
    recall = recall_score(y_test, y_pred, average='weighted')
    f1 = f1_score(y_test, y_pred, average='weighted')
    cm = confusion_matrix(y_test, y_pred)

    # Print metrics
    print(f"\nAccuracy:  {accuracy * 100:.2f}%")
    print(f"Precision: {precision * 100:.2f}%")
    print(f"Recall:    {recall * 100:.2f}%")
    print(f"F1 Score:  {f1 * 100:.2f}%")

    # Print confusion matrix (limited to avoid overwhelming output)
    print(f"\nConfusion Matrix (shape: {cm.shape}):")
    if cm.shape[0] <= 15:
        print(cm)
    else:
        print(f"[Matrix too large to display ({cm.shape[0]} classes)]")
        print(f"Total predictions: {cm.sum()}")

    # Print detailed classification report for smaller datasets
    if len(label_encoder.classes_) <= 20:
        print("\nClassification Report:")
        print(classification_report(
            y_test, y_pred,
            target_names=label_encoder.classes_,
            zero_division=0
        ))

    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'confusion_matrix': cm
    }


def save_artifacts(
    models_dir: Path,
    classifier: LogisticRegression,
    vectorizer: TfidfVectorizer,
    label_encoder: LabelEncoder
) -> None:
    """
    Save trained model artifacts to disk.

    Saves three pickle files:
    - classifier.pkl: Trained Logistic Regression model
    - vectorizer.pkl: Fitted TF-IDF vectorizer
    - label_encoder.pkl: Fitted label encoder for decoding predictions

    Args:
        models_dir: Directory to save models
        classifier: Trained classifier
        vectorizer: Fitted vectorizer
        label_encoder: Fitted label encoder
    """
    print("\n[INFO] Saving model artifacts...")

    # Define file paths
    classifier_path = models_dir / 'classifier.pkl'
    vectorizer_path = models_dir / 'vectorizer.pkl'
    encoder_path = models_dir / 'label_encoder.pkl'

    # Save classifier
    with open(classifier_path, 'wb') as f:
        pickle.dump(classifier, f)
    print(f"[SAVED] Classifier: {classifier_path}")

    # Save vectorizer
    with open(vectorizer_path, 'wb') as f:
        pickle.dump(vectorizer, f)
    print(f"[SAVED] Vectorizer: {vectorizer_path}")

    # Save label encoder
    with open(encoder_path, 'wb') as f:
        pickle.dump(label_encoder, f)
    print(f"[SAVED] Label Encoder: {encoder_path}")


def main():
    """
    Main execution function.

    Orchestrates the complete ML pipeline:
    1. Create output directory
    2. Load and preprocess data
    3. Encode labels
    4. Split into train/test sets
    5. Vectorize text data
    6. Train classifier
    7. Evaluate performance
    8. Save artifacts
    """
    print("=" * 60)
    print("NYC 311 COMPLAINT CLASSIFIER TRAINING PIPELINE")
    print("=" * 60)
    print()

    # Configuration
    DATA_FILE = 'nyc311_working.csv'
    MODELS_DIR = 'models'
    TEST_SIZE = 0.2  # 20% for testing
    RANDOM_STATE = 42

    # Step 1: Create models directory
    models_path = create_models_directory(MODELS_DIR)

    # Step 2: Load dataset
    df = load_dataset(DATA_FILE)

    # Step 3: Preprocess data
    texts, labels = preprocess_data(df)

    # Step 4: Encode labels
    encoded_labels, label_encoder = encode_labels(labels)

    # Step 5: Split into train/test sets (80/20 split)
    print(f"\n[INFO] Splitting data (80% train, 20% test)...")
    X_train_text, X_test_text, y_train, y_test = train_test_split(
        texts,
        encoded_labels,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=encoded_labels  # Ensure balanced split across classes
    )
    print(f"[INFO] Training samples: {len(X_train_text)}")
    print(f"[INFO] Test samples: {len(X_test_text)}")

    # Step 6: Create and fit TF-IDF vectorizer
    print("\n[INFO] Vectorizing text data...")
    vectorizer = create_vectorizer()
    X_train = vectorizer.fit_transform(X_train_text)
    X_test = vectorizer.transform(X_test_text)
    print(f"[INFO] Feature matrix shape (train): {X_train.shape}")
    print(f"[INFO] Feature matrix shape (test): {X_test.shape}")
    print(f"[INFO] Vocabulary size: {len(vectorizer.vocabulary_)}")

    # Step 7: Train classifier
    classifier = train_classifier(X_train, y_train, max_iter=1000, random_state=RANDOM_STATE)

    # Step 8: Evaluate model
    metrics = evaluate_model(classifier, X_test, y_test, label_encoder)

    # Step 9: Save artifacts
    save_artifacts(models_path, classifier, vectorizer, label_encoder)

    # Final summary
    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"Final F1 Score: {metrics['f1_score'] * 100:.2f}%")
    print(f"Model artifacts saved to: {models_path.absolute()}")
    print()


if __name__ == '__main__':
    main()
