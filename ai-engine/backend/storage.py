"""
S3-compatible storage for complaint photo evidence (Backblaze B2 / MinIO / AWS S3).
Uses a private bucket with presigned URLs — no public bucket or credit card needed.
Includes perceptual-hash-based duplicate/fraud detection for uploaded photos.
"""

import os
import uuid
import logging
import io
from pathlib import Path
from typing import Optional, List, Tuple

from imagehash import phash
from PIL import Image

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
PRESIGNED_URL_EXPIRY = 3600  # 1 hour

# ── Perceptual hash settings ────────────────────────────────────────────────
PHASH_HAMMING_THRESHOLD = 8  # max Hamming distance to consider a near-duplicate
PHASH_SIZE = 8               # 8×8 DCT-based pHash = 64-bit hash


def compute_phash(data: bytes) -> str:
    """Compute a perceptual hash (pHash) from raw image bytes.

    Returns a 16-character hex string representing the 64-bit hash.
    Catches resized, re-compressed, and slightly cropped duplicates.
    """
    try:
        img = Image.open(io.BytesIO(data))
        # Convert to RGB if paletted/RGBA so pHash is consistent
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        return str(phash(img, hash_size=PHASH_SIZE))
    except Exception as e:
        logger.warning("Failed to compute pHash: %s", e)
        return ""


def hamming_distance(hash_a: str, hash_b: str) -> int:
    """Compute Hamming distance between two hex-encoded pHash strings."""
    if len(hash_a) != len(hash_b):
        return 64  # max possible distance for 64-bit hash
    val = int(hash_a, 16) ^ int(hash_b, 16)
    return bin(val).count("1")


def find_duplicate_photo(
    db_session,
    current_user_id: str,
    phash_str: str,
    threshold: int = PHASH_HAMMING_THRESHOLD,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Search for near-duplicate photos in the database.

    Returns (match_complaint_id, flag_type, matched_user_id) where flag_type is:
      - "same_user"    — exact/near-exact match from the SAME user (possible spam)
      - "cross_user"   — match from a DIFFERENT user (reused image)
      - "similar"      — hamming distance < 10 against a recent pHash (last 30 days)
      - None           — no match found
    """
    if not phash_str:
        return None, None, None

    # Import here to avoid circular import at module level
    from database import Complaint
    from datetime import datetime, timedelta

    # FEATURE 18: check against pHashes from last 30 days for similarity
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_hashes: List[Complaint] = (
        db_session.query(Complaint)
        .filter(
            Complaint.photo_hash.isnot(None),
            Complaint.photo_hash != "",
            Complaint.created_at >= thirty_days_ago,
        )
        .all()
    )

    best_match_id = None
    best_match_user = None
    best_distance = threshold + 1
    similar_distance = 10  # threshold for 'similar' flag

    for c in recent_hashes:
        if not c.photo_hash:
            continue
        dist = hamming_distance(phash_str, c.photo_hash)
        if dist < similar_distance and dist < best_distance:
            best_distance = dist
            best_match_id = c.id
            best_match_user = c.user_id

    if best_match_id is None:
        return None, None, None

    if best_match_user == current_user_id:
        return best_match_id, "same_user", best_match_user
    elif best_distance <= threshold:
        return best_match_id, "cross_user", best_match_user
    else:
        # Hamming distance < 10 but above exact threshold — flag as similar
        return best_match_id, "similar", best_match_user


def _config(key: str, default: str) -> str:
    return os.environ.get(key, default)


class S3Storage:
    def __init__(self):
        raw = _config("S3_ENDPOINT_URL", "http://localhost:9000")
        if raw and not raw.startswith("http://") and not raw.startswith("https://"):
            raw = "https://" + raw
        self.endpoint_url = raw
        self.access_key = _config("S3_ACCESS_KEY_ID", "minioadmin")
        self.secret_key = _config("S3_SECRET_ACCESS_KEY", "minioadmin")
        self.bucket = _config("S3_BUCKET_NAME", "giips-complaints")
        self.region = _config("S3_REGION", "us-east-1")
        self._client = None

    @property
    def available(self) -> bool:
        return os.environ.get("S3_ENDPOINT_URL") is not None

    @property
    def client(self):
        if self._client is None:
            import boto3
            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
                config=boto3.session.Config(signature_version="s3v4"),
            )
            self._ensure_bucket()
        return self._client

    def _ensure_bucket(self):
        try:
            self._client.head_bucket(Bucket=self.bucket)
        except Exception:
            try:
                self._client.create_bucket(Bucket=self.bucket)
                logger.info("Created S3 bucket: %s", self.bucket)
            except Exception as e:
                logger.warning("Could not create bucket %s: %s", self.bucket, e)

    def upload(self, data: bytes, filename: str, content_type: str) -> str:
        """Upload a file and return the object key. Use get_presigned_url() to retrieve."""
        ext = Path(filename).suffix.lower()
        key = f"complaints/{uuid.uuid4().hex}{ext}"
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        logger.info("Uploaded %s (%d bytes)", key, len(data))
        return key

    def get_presigned_url(self, object_key: str, expiry: int = PRESIGNED_URL_EXPIRY) -> Optional[str]:
        """Generate a presigned GET URL for a private object."""
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": object_key},
                ExpiresIn=expiry,
            )
            return url
        except Exception as e:
            logger.warning("Failed to generate presigned URL for %s: %s", object_key, e)
            return None


def validate_file(filename: str, content_type: str, size: int) -> Optional[str]:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return f"File type '{ext}' not allowed. Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
    if content_type not in ALLOWED_MIME_TYPES:
        return f"Content type '{content_type}' not allowed. Supported: {', '.join(sorted(ALLOWED_MIME_TYPES))}"
    if size > MAX_FILE_SIZE:
        return f"File too large ({size / 1024 / 1024:.1f} MB). Maximum: {MAX_FILE_SIZE / 1024 / 1024:.0f} MB"
    return None
