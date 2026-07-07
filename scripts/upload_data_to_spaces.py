"""Wysyła surowe pliki CSV z danymi półmaratonu do Digital Ocean Spaces.

Użycie:
    python scripts/upload_data_to_spaces.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from spaces_client import upload_file

DATA_FILES = [
    "halfmarathon_wroclaw_2023__final.csv",
    "halfmarathon_wroclaw_2024__final.csv",
]

if __name__ == "__main__":
    for filename in DATA_FILES:
        local_path = project_root / filename
        url = upload_file(local_path, spaces_key=f"data/{filename}")
        print(f"OK: {filename} -> {url}")
