"""Object storage for per-copy source files and corpus artifacts.

Uses S3 (MinIO locally) when S3_ENDPOINT is set; otherwise a repo-local
directory so tests and a first seed work without Docker.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from ingest.constants import ROOT

load_dotenv(ROOT / ".env")

FILE_ROOT = ROOT / "data" / "blobs"


def copy_key(copy_id: str, name: str) -> str:
    return f"copies/{copy_id}/{name}"


def uses_s3() -> bool:
    return bool(os.environ.get("S3_ENDPOINT"))


def _bucket() -> str:
    return os.environ.get("S3_BUCKET", "ken")


def _s3():
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("S3_ENDPOINT"),
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY", "minio"),
        aws_secret_access_key=os.environ.get("S3_SECRET_KEY", "minio-password"),
        region_name=os.environ.get("S3_REGION", "us-east-1"),
        config=Config(s3={"addressing_style": "path"}),
    )


def ensure_bucket() -> None:
    if not uses_s3():
        FILE_ROOT.mkdir(parents=True, exist_ok=True)
        return
    client = _s3()
    name = _bucket()
    try:
        client.head_bucket(Bucket=name)
    except Exception:
        client.create_bucket(Bucket=name)


def put_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    ensure_bucket()
    if uses_s3():
        _s3().put_object(Bucket=_bucket(), Key=key, Body=data, ContentType=content_type)
        return
    path = FILE_ROOT / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def get_bytes(key: str) -> bytes:
    if uses_s3():
        return _s3().get_object(Bucket=_bucket(), Key=key)["Body"].read()
    path = FILE_ROOT / key
    if not path.exists():
        raise FileNotFoundError(key)
    return path.read_bytes()


def exists(key: str) -> bool:
    if uses_s3():
        from botocore.exceptions import ClientError

        try:
            _s3().head_object(Bucket=_bucket(), Key=key)
            return True
        except ClientError:
            return False
    return (FILE_ROOT / key).exists()
