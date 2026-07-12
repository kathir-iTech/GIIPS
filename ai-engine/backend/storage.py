"""
S3-compatible storage for complaint photo evidence (Backblaze B2 / MinIO / AWS S3).
Uses a private bucket with presigned URLs — no public bucket or credit card needed.
"""

import os
import uuid
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
PRESIGNED_URL_EXPIRY = 3600  # 1 hour


def _config(key: str, default: str) -> str:
    return os.environ.get(key, default)


class S3Storage:
    def __init__(self):
        self.endpoint_url = _config("S3_ENDPOINT_URL", "http://localhost:9000")
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
