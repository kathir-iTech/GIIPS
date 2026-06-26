"""
Prediction module for complaint classification.

Provides functions to load trained models and make predictions on new data.
"""

import pickle
from pathlib import Path
from typing import List, Dict, Union, Optional

import numpy as np
import pandas as pd

from .train import ComplaintClassifier


class ComplaintPredictor:
    """
    Wrapper class for making predictions with trained models.
    """

    def __init__(self, model_dir: Path):
        """
        Initialize predictor by loading trained model.

        Args:
            model_dir: Directory containing saved model artifacts
        """
        self.model_dir = Path(model_dir)
        self.classifier = ComplaintClassifier.load(self.model_dir)
        print(f"[INFO] Predictor ready with {len(self.classifier.classes_)} categories")

    def predict(self, texts: Union[str, List[str]]) -> Union[str, np.ndarray]:
        """
        Predict category for one or more texts.

        Args:
            texts: Single text or list of texts

        Returns:
            Predicted category label(s)
        """
        if isinstance(texts, str):
            texts = [texts]
            single = True
        else:
            single = False

        predictions = self.classifier.predict(texts)

        if single:
            return predictions[0]
        return predictions

    def predict_with_confidence(self, texts: Union[str, List[str]]) -> List[Dict]:
        """
        Predict category with confidence scores.

        Args:
            texts: Single text or list of texts

        Returns:
            List of dictionaries with prediction and confidence
        """
        if isinstance(texts, str):
            texts = [texts]

        predictions = self.classifier.predict(texts)
        probabilities = self.classifier.predict_proba(texts)

        results = []
        for i, text in enumerate(texts):
            # Get top predictions
            probs = probabilities[i]
            top_indices = np.argsort(probs)[::-1][:5]

            top_predictions = [
                {
                    'category': self.classifier.classes_[idx],
                    'confidence': float(probs[idx])
                }
                for idx in top_indices
            ]

            results.append({
                'text': text[:100] + '...' if len(text) > 100 else text,
                'predicted_category': predictions[i],
                'confidence': float(probs[predictions[i] == self.classifier.classes_][0]),
                'top_predictions': top_predictions
            })

        return results

    def batch_predict(
        self,
        df: pd.DataFrame,
        text_col: str = 'combined_text'
    ) -> pd.DataFrame:
        """
        Predict categories for a DataFrame of complaints.

        Args:
            df: DataFrame containing complaints
            text_col: Column name containing text

        Returns:
            DataFrame with predictions added
        """
        texts = df[text_col].fillna('').tolist()
        predictions = self.predict(texts)

        df = df.copy()
        df['predicted_category'] = predictions

        # Add confidence scores
        probabilities = self.classifier.predict_proba(texts)
        df['confidence'] = [probs[pred == self.classifier.classes_][0]
                          for probs, pred in zip(probabilities, predictions)]

        return df


def load_predictor(model_dir: Optional[Path] = None) -> ComplaintPredictor:
    """
    Convenience function to load a predictor.

    Args:
        model_dir: Optional path to model directory

    Returns:
        Loaded ComplaintPredictor instance
    """
    if model_dir is None:
        # Default model directory
        model_dir = Path(__file__).parent.parent / 'models' / 'classification'

    return ComplaintPredictor(model_dir)


if __name__ == '__main__':
    import sys
    from .utils import clean_text

    model_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    predictor = load_predictor(model_dir)

    # Test with sample texts
    sample_texts = [
        "Noise from construction work happening at 3am",
        "Water main break causing flooding on main street",
        "Garbage not collected for two weeks",
        "Street light not working on corner of 5th avenue",
        "Pothole causing damage to vehicles"
    ]

    print("\n" + "=" * 60)
    print("SAMPLE PREDICTIONS")
    print("=" * 60)

    for text in sample_texts:
        result = predictor.predict_with_confidence(text)[0]
        print(f"\nText: {text}")
        print(f"Predicted: {result['predicted_category']} (confidence: {result['confidence']:.2%})")
