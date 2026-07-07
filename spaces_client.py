"""Klient do Digital Ocean Spaces (S3-compatible), współdzielony przez skrypt
uploadu danych, notebook treningowy i aplikację Streamlit.

Zmienne DO_SPACES_* czytane są z os.environ — lokalnie trafiają tam z pliku
.env (load_dotenv), a na Digital Ocean App Platform są wstrzykiwane przez
platformę bezpośrednio do środowiska procesu (nie ma tam pliku .env)."""

import os
from io import BytesIO
from pathlib import Path

import boto3
import pandas as pd
from botocore.config import Config
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")


def _env(key):
    return os.environ[key]


# Endpoint musi być regionalny (np. https://fra1.digitaloceanspaces.com), a nie
# bucket-specific (https://<bucket>.fra1.digitaloceanspaces.com) jak podaje panel DO -
# ten drugi w połączeniu z path-style addressing dubluje nazwę bucketu w ścieżce.
def _endpoint_url():
    return f"https://{_env('DO_SPACES_REGION')}.digitaloceanspaces.com"


def get_client():
    return boto3.client(
        "s3",
        region_name=_env("DO_SPACES_REGION"),
        endpoint_url=_endpoint_url(),
        aws_access_key_id=_env("DO_SPACES_KEY"),
        aws_secret_access_key=_env("DO_SPACES_SECRET"),
        config=Config(s3={"addressing_style": "path"}),
    )


def upload_file(local_path, spaces_key, bucket=None, public=False):
    client = get_client()
    bucket = bucket or _env("DO_SPACES_BUCKET")
    extra_args = {"ACL": "public-read"} if public else {}
    client.upload_file(str(local_path), bucket, spaces_key, ExtraArgs=extra_args)
    return f"{_endpoint_url()}/{bucket}/{spaces_key}"


def download_file(spaces_key, local_path, bucket=None):
    client = get_client()
    bucket = bucket or _env("DO_SPACES_BUCKET")
    Path(local_path).parent.mkdir(parents=True, exist_ok=True)
    client.download_file(bucket, spaces_key, str(local_path))


def read_csv_from_spaces(spaces_key, bucket=None, **read_csv_kwargs):
    client = get_client()
    bucket = bucket or _env("DO_SPACES_BUCKET")
    obj = client.get_object(Bucket=bucket, Key=spaces_key)
    return pd.read_csv(BytesIO(obj["Body"].read()), **read_csv_kwargs)
