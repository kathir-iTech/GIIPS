"""
train_embeddings.py

Generate sentence embeddings for NYC 311 complaints using SentenceTransformers.

This script:
1. Loads complaint data from CSV
2. Preprocesses text for embedding
3. Generates embeddings using all-MiniLM-L6-v2
4. Saves embeddings and metadata for indexing

Author: GIIPS AI Engine
Version: 1.0.0
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

import numpy as np
import pandas as pd
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

# Sentence Transformers for embeddings
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.error("sentence-transformers not installed. Install with: pip install sentence-transformers")


class EmbeddingTrainer:
    """
    Generate and manage sentence embeddings for complaint deduplication.
    """

    def __init__(
        self,
        model_name: str = 'all-MiniLM-L6-v2',
        batch_size: int = 64,
        device: Optional[str] = None,
        normalize: bool = True
    ):
        """
        Initialize the embedding trainer.

        Args:
            model_name: SentenceTransformer model name
            batch_size: Batch size for embedding generation
            device: Device to use ('cuda', 'cpu', or None for auto)
            normalize: Whether to L2-normalize embeddings
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.device = device
        self.normalize = normalize
        self.model = None
        self.embedding_dim = None

        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers is required. "
                "Install with: pip install sentence-transformers"
            )

    def load_model(self) -> None:
        """Load the SentenceTransformer model."""
        if self.model is None:
            logger.info(f"Loading SentenceTransformer model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name, device=self.device)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            device_info = self.device or "auto-detected"
            logger.info(f"Model loaded. Embedding dimension: {self.embedding_dim}")
            logger.info(f"Device: {device_info}")

    def preprocess_text(self, text: str) -> str:
        """
        Preprocess complaint text for embedding.

        Preserves semantic meaning while cleaning noise.

        Args:
            text: Raw complaint text

        Returns:
            Cleaned text
        """
        if not isinstance(text, str):
            return ""

        # Basic cleaning
        text = text.strip()

        # Remove excessive whitespace
        import re
        text = re.sub(r'\s+', ' ', text)

        return text

    def prepare_complaints(
        self,
        df: pd.DataFrame,
        text_columns: Optional[List[str]] = None,
        id_column: str = 'complaint_id'
    ) -> Tuple[List[str], List[Dict]]:
        """
        Prepare complaint texts and metadata for embedding.

        Args:
            df: DataFrame with complaints
            text_columns: Columns to combine for embedding
            id_column: Column containing unique IDs

        Returns:
            Tuple of (texts, metadata_list)
        """
        if text_columns is None:
            # Default columns to use - check common column names
            text_columns = []
            candidates = ['text', 'complaint_text', 'description', 'Problem', 'Problem Detail', 'Descriptor']
            for col in candidates:
                if col in df.columns:
                    text_columns.append(col)

        if not text_columns:
            raise ValueError(
                "No valid text columns found in DataFrame. "
                f"Available columns: {list(df.columns)}"
            )

        logger.info(f"Using text columns: {text_columns}")

        texts = []
        metadata = []

        # Use tqdm for progress bar
        for idx, row in tqdm(
            df.iterrows(),
            total=len(df),
            desc="Preparing complaints",
            unit="rows"
        ):
            # Combine text columns, handling missing values
            combined_parts = []
            for col in text_columns:
                val = row.get(col)
                if pd.notna(val) and str(val).strip():
                    combined_parts.append(str(val))

            combined_text = ' '.join(combined_parts)

            # Preprocess
            cleaned_text = self.preprocess_text(combined_text)

            if cleaned_text:
                texts.append(cleaned_text)

                # Store metadata
                meta = {
                    'id': row.get(id_column, idx) if pd.notna(row.get(id_column)) else f"cmp-{idx}",
                    'index': len(texts) - 1,
                }

                # Add additional useful fields with missing value handling
                for col in ['date_received', 'ward', 'category', 'Problem']:
                    val = row.get(col)
                    if pd.notna(val):
                        meta[col] = str(val)

                metadata.append(meta)

        logger.info(f"Prepared {len(texts)} complaints for embedding")
        return texts, metadata

    def generate_embeddings(
        self,
        texts: List[str],
        show_progress: bool = True
    ) -> np.ndarray:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of complaint texts
            show_progress: Whether to show progress bar

        Returns:
            Numpy array of embeddings (n_texts, embedding_dim)
        """
        self.load_model()

        logger.info(f"Generating embeddings for {len(texts)} texts...")

        # Generate embeddings with progress bar
        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
            normalize_embeddings=self.normalize
        )

        logger.info(f"Embeddings generated. Shape: {embeddings.shape}")

        return embeddings

    def process_dataset(
        self,
        input_path: Path,
        output_dir: Path,
        text_columns: Optional[List[str]] = None,
        id_column: str = 'complaint_id',
        sample_size: Optional[int] = None
    ) -> Dict:
        """
        Process a dataset and generate embeddings.

        Args:
            input_path: Path to input CSV
            output_dir: Directory to save outputs
            text_columns: Columns to use for text
            id_column: Column for IDs
            sample_size: Optional sample size for testing

        Returns:
            Processing statistics
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Load dataset
        logger.info(f"Loading dataset from: {input_path}")
        df = pd.read_csv(input_path)
        logger.info(f"Loaded {len(df)} records")

        # Handle missing values in text columns
        text_cols_to_check = text_columns if text_columns else ['text', 'Problem', 'Problem Detail', 'Descriptor']
        for col in text_cols_to_check:
            if col in df.columns:
                missing_count = df[col].isna().sum()
                if missing_count > 0:
                    logger.warning(f"Column '{col}' has {missing_count} missing values - will be handled")
                    df[col] = df[col].fillna('')

        # Sample if requested
        if sample_size and len(df) > sample_size:
            df = df.sample(n=sample_size, random_state=42)
            logger.info(f"Sampled {sample_size} records")

        # Prepare texts
        texts, metadata = self.prepare_complaints(df, text_columns, id_column)

        if not texts:
            raise ValueError("No valid texts found after preprocessing")

        # Generate embeddings
        embeddings = self.generate_embeddings(texts)

        # Save embeddings
        embeddings_path = output_dir / 'embeddings.npy'
        np.save(embeddings_path, embeddings)
        logger.info(f"Saved embeddings: {embeddings_path}")

        # Save metadata
        metadata_path = output_dir / 'embedding_metadata.json'
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump({
                'num_embeddings': len(texts),
                'embedding_dim': self.embedding_dim,
                'model_name': self.model_name,
                'normalized': self.normalize,
                'created_at': datetime.now().isoformat(),
                'metadata': metadata
            }, f, indent=2)
        logger.info(f"Saved metadata: {metadata_path}")

        # Save texts for reference
        texts_path = output_dir / 'complaint_texts.json'
        with open(texts_path, 'w', encoding='utf-8') as f:
            json.dump(texts, f, indent=2)
        logger.info(f"Saved texts: {texts_path}")

        return {
            'num_embeddings': len(texts),
            'embedding_dim': self.embedding_dim,
            'output_dir': str(output_dir)
        }


def main():
    """Main entry point for embedding training."""
    parser = argparse.ArgumentParser(
        description='Train embeddings for duplicate detection'
    )
    parser.add_argument(
        '--input', '-i',
        type=str,
        default='ai-engine/data/nyc311_filtered.csv',
        help='Input CSV file path'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='ai-engine/duplicate_detection',
        help='Output directory for embeddings'
    )
    parser.add_argument(
        '--model', '-m',
        type=str,
        default='all-MiniLM-L6-v2',
        help='SentenceTransformer model name'
    )
    parser.add_argument(
        '--batch-size', '-b',
        type=int,
        default=64,
        help='Batch size for embedding generation'
    )
    parser.add_argument(
        '--device', '-d',
        type=str,
        default=None,
        help='Device to use (cuda/cpu)'
    )
    parser.add_argument(
        '--sample', '-s',
        type=int,
        default=None,
        help='Sample size for testing'
    )
    parser.add_argument(
        '--text-columns', '-t',
        type=str,
        nargs='+',
        default=None,
        help='Columns to combine for text'
    )

    args = parser.parse_args()

    # Resolve paths
    project_root = Path(__file__).parent.parent.parent
    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = project_root / input_path

    output_dir = Path(args.output)
    if not output_dir.is_absolute():
        output_dir = project_root / args.output

    # Check input exists
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        logger.info("Please place nyc311_filtered.csv in ai-engine/data/")
        sys.exit(1)

    try:
        # Initialize trainer
        trainer = EmbeddingTrainer(
            model_name=args.model,
            batch_size=args.batch_size,
            device=args.device
        )

        # Process dataset
        stats = trainer.process_dataset(
            input_path=input_path,
            output_dir=output_dir,
            text_columns=args.text_columns,
            sample_size=args.sample
        )

        print("\n" + "=" * 60)
        print("EMBEDDING TRAINING COMPLETE")
        print("=" * 60)
        print(f"Embeddings: {stats['num_embeddings']}")
        print(f"Dimensions: {stats['embedding_dim']}")
        print(f"Output: {stats['output_dir']}")

    except Exception as e:
        logger.error(f"Error during embedding training: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
