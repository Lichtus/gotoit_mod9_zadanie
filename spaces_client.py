"""Klient do Digital Ocean Spaces (S3-compatible), współdzielony przez skrypt
uploadu danych i przyszły notebook treningowy (odczyt danych)."""

from io import BytesIO
from pathlib import Path

import boto3
import pandas as pd
from botocore.config import Config
from dotenv import dotenv_values

env = dotenv_values(Path(__file__).resolve().parent / ".env")

# Endpoint musi być regionalny (np. https://fra1.digitaloceanspaces.com), a nie
# bucket-specific (https://<bucket>.fra1.digitaloceanspaces.com) jak podaje panel DO -
# ten drugi w połączeniu z path-style addressing dubluje nazwę bucketu w ścieżce.
REGION = env["DO_SPACES_REGION"]
ENDPOINT_URL = f"https://{REGION}.digitaloceanspaces.com"


def get_client():
    return boto3.client(
        "s3",
        region_name=REGION,
        endpoint_url=ENDPOINT_URL,
        aws_access_key_id=env["DO_SPACES_KEY"],
        aws_secret_access_key=env["DO_SPACES_SECRET"],
        config=Config(s3={"addressing_style": "path"}),
    )


def upload_file(local_path, spaces_key, bucket=None, public=False):
    client = get_client()
    bucket = bucket or env["DO_SPACES_BUCKET"]
    extra_args = {"ACL": "public-read"} if public else {}
    client.upload_file(str(local_path), bucket, spaces_key, ExtraArgs=extra_args)
    return f"{ENDPOINT_URL}/{bucket}/{spaces_key}"


def download_file(spaces_key, local_path, bucket=None):
    client = get_client()
    bucket = bucket or env["DO_SPACES_BUCKET"]
    Path(local_path).parent.mkdir(parents=True, exist_ok=True)
    client.download_file(bucket, spaces_key, str(local_path))


def read_csv_from_spaces(spaces_key, bucket=None, **read_csv_kwargs):
    client = get_client()
    bucket = bucket or env["DO_SPACES_BUCKET"]
    obj = client.get_object(Bucket=bucket, Key=spaces_key)
    return pd.read_csv(BytesIO(obj["Body"].read()), **read_csv_kwargs)
