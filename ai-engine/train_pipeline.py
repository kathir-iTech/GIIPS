"""
train_models.py

Train and save classification model artifacts for GIIPS.
This script creates the classifier.pkl, vectorizer.pkl, and label_encoder.pkl files.

Author: GIIPS AI Engine
"""

import argparse
import pickle
import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """Clean and normalize text for classification."""
    import re
    import string

    if not isinstance(text, str):
        return ""

    text = text.lower()
    text = re.sub(r'http\S+|www\.\S+', '', text)
    text = text.translate(str.maketrans('', '', string.punctuation))
    text = ' '.join(text.split())

    return text.strip()


def prepare_dataset(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    """Prepare the dataset for training."""
    # Find text columns
    text_cols = []
    for col in ['text', 'Problem', 'Problem Detail', 'Descriptor', 'description']:
        if col in df.columns:
            text_cols.append(col)

    if not text_cols:
        raise ValueError(f"No text columns found. Available: {list(df.columns)}")

    logger.info(f"Using text columns: {text_cols}")

    # Combine text columns
    df['combined_text'] = df[text_cols].fillna('').agg(' '.join, axis=1)
    df['combined_text'] = df['combined_text'].apply(clean_text)

    # Remove empty texts
    df = df[df['combined_text'].str.len() > 0]

    # Find label column
    label_col = None
    for col in ['category', 'Problem', 'complaint_type', 'label']:
        if col in df.columns:
            label_col = col
            break

    if label_col is None:
        raise ValueError(f"No label column found. Available: {list(df.columns)}")

    logger.info(f"Using label column: {label_col}")

    return df['combined_text'], df[label_col]


def train_classifier(
    texts: np.ndarray,
    labels: np.ndarray,
    max_features: int = 10000,
    ngram_range: Tuple[int, int] = (1, 2),
    random_state: int = 42
) -> Dict:
    """Train the TF-IDF + Logistic Regression classifier."""

    # Encode labels
    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(labels)

    logger.info(f"Found {len(label_encoder.classes_)} unique categories")

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        texts, y, test_size=0.2, random_state=random_state, stratify=y
    )

    logger.info(f"Train: {len(X_train)}, Test: {len(X_test)}")

    # Vectorize
    vectorizer = TfidfVectorizer(
        max_features=max_features,
        ngram_range=ngram_range,
        min_df=2,
        max_df=0.95,
        stop_words='english',
        lowercase=True,
        strip_accents='unicode'
    )

    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    logger.info(f"Feature matrix: {X_train_vec.shape}")

    # Train classifier
    classifier = LogisticRegression(
        max_iter=1000,
        random_state=random_state,
        solver='lbfgs',
        n_jobs=-1
    )

    classifier.fit(X_train_vec, y_train)

    # Evaluate
    y_pred = classifier.predict(X_test_vec)
    accuracy = accuracy_score(y_test, y_pred)

    logger.info(f"\nClassification Report:")
    print(classification_report(
        y_test, y_pred,
        target_names=label_encoder.classes_,
        zero_division=0
    ))

    logger.info(f"Accuracy: {accuracy * 100:.2f}%")

    return {
        'vectorizer': vectorizer,
        'classifier': classifier,
        'label_encoder': label_encoder,
        'accuracy': accuracy,
        'classes': list(label_encoder.classes_)
    }


def save_models(models: Dict, output_dir: Path) -> None:
    """Save trained models to disk."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / 'vectorizer.pkl', 'wb') as f:
        pickle.dump(models['vectorizer'], f)
    logger.info(f"Saved vectorizer.pkl")

    with open(output_dir / 'classifier.pkl', 'wb') as f:
        pickle.dump(models['classifier'], f)
    logger.info(f"Saved classifier.pkl")

    with open(output_dir / 'label_encoder.pkl', 'wb') as f:
        pickle.dump(models['label_encoder'], f)
    logger.info(f"Saved label_encoder.pkl")

    # Save metadata
    metadata = {
        'accuracy': models['accuracy'],
        'num_classes': len(models['classes']),
        'classes': models['classes'],
        'created_at': datetime.now().isoformat(),
        'model_type': 'TF-IDF + Logistic Regression'
    }

    with open(output_dir / 'metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"Saved metadata.json")


def create_sample_dataset() -> pd.DataFrame:
    """Create a sample dataset if none exists."""
    data = [
        # Road Infrastructure
        {"text": "Large pothole on Main Street causing accidents", "category": "Road Infrastructure"},
        {"text": "Road surface damaged near the market area", "category": "Road Infrastructure"},
        {"text": "Speed breaker too high on Hospital Road", "category": "Road Infrastructure"},
        {"text": "Footpath tiles broken on Gandhi Road", "category": "Road Infrastructure"},
        {"text": "Manhole cover missing on MG Road", "category": "Road Infrastructure"},
        {"text": "Street has many cracks and potholes", "category": "Road Infrastructure"},

        # Water Supply
        {"text": "No water supply in Lakshmipuram for 3 days", "category": "Water Supply"},
        {"text": "Water pipe burst near the temple area", "category": "Water Supply"},
        {"text": "Dirty brown water coming from taps", "category": "Water Supply"},
        {"text": "Water contamination in residential area", "category": "Water Supply"},
        {"text": "Low water pressure in apartments", "category": "Water Supply"},

        # Waste Management
        {"text": "Garbage not collected for 2 weeks", "category": "Waste Management"},
        {"text": "Garbage bins overflowing near park", "category": "Waste Management"},
        {"text": "Illegal dumping of construction debris", "category": "Waste Management"},
        {"text": "Waste collection missed again", "category": "Waste Management"},

        # Street Lighting
        {"text": "Street lights not working near Shivaji Park", "category": "Street Lighting"},
        {"text": "Multiple street lamps out of order", "category": "Street Lighting"},
        {"text": "Dark area due to faulty street lights", "category": "Street Lighting"},
        {"text": "Street pole sparking dangerously", "category": "Street Lighting"},

        # Sanitation
        {"text": "Open drain overflow flooding the streets", "category": "Sanitation"},
        {"text": "Sewage on Subhash Nagar streets", "category": "Sanitation"},
        {"text": "Drainage blocked causing health hazard", "category": "Sanitation"},
        {"text": "Open sewage near residential area", "category": "Sanitation"},

        # More Road Infrastructure
        {"text": "Pothole causing vehicle damage on highway", "category": "Road Infrastructure"},
        {"text": "Road broken near school junction", "category": "Road Infrastructure"},
        {"text": "Dangerous speed bump needs fixing", "category": "Road Infrastructure"},

        # More Water Supply
        {"text": "Pipeline leakage wasting water", "category": "Water Supply"},
        {"text": "No water since Monday in our area", "category": "Water Supply"},

        # More Waste Management
        {"text": "Trash piling up near bus stop", "category": "Waste Management"},
        {"text": "Garbage truck not coming regularly", "category": "Waste Management"},

        # Sanitation
        {"text": "Blocked drain causing overflow", "category": "Sanitation"},
        {"text": "Mosquito breeding in stagnant water", "category": "Sanitation"},
    ]

    df = pd.DataFrame(data)
    logger.info(f"Created sample dataset with {len(df)} records")
    return df


def main():
    parser = argparse.ArgumentParser(description='Train GIIPS classification models')
    parser.add_argument('--input', '-i', type=str,
                       default='ai-engine/data/nyc311_filtered.csv',
                       help='Input CSV file')
    parser.add_argument('--output', '-o', type=str,
                       default='ai-engine/models/classification',
                       help='Output directory for models')
    parser.add_argument('--use-sample', action='store_true',
                       help='Use sample dataset')

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    input_path = project_root / args.input
    output_dir = project_root / args.output

    try:
        if args.use_sample or not input_path.exists():
            logger.warning(f"Dataset not found at {input_path}, using sample data")
            df = create_sample_dataset()
        else:
            logger.info(f"Loading dataset from {input_path}")
            df = pd.read_csv(input_path)
            logger.info(f"Loaded {len(df)} records")

        # Prepare dataset
        texts, labels = prepare_dataset(df)

        # Train classifier
        models = train_classifier(texts.values, labels.values)

        # Save models
        save_models(models, output_dir)

        print("\n" + "=" * 60)
        print("MODEL TRAINING COMPLETE")
        print("=" * 60)
        print(f"Accuracy: {models['accuracy'] * 100:.2f}%")
        print(f"Classes: {len(models['classes'])}")
        print(f"Output: {output_dir}")

    except Exception as e:
        logger.error(f"Training failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
