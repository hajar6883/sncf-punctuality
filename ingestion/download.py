"""Download full CSV snapshots to data/raw/<dataset_id>/<YYYY-MM-DD>.csv."""

import hashlib
from datetime import date
from pathlib import Path

import requests

from ingestion.config import API_BASE, DATASETS, RAW_DIR


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def fetch_csv(dataset_id: str) -> bytes:
    # use_labels=false -> technical column names (nb_train_prevu, ...)
    url = f"{API_BASE}/{dataset_id}/exports/csv"
    response = requests.get(url, params={"delimiter": ";", "use_labels": "false"}, timeout=120)
    response.raise_for_status()
    return response.content


def save_snapshot(dataset_id: str, content: bytes, raw_dir: Path = RAW_DIR, today: date | None = None) -> Path | None:
    """Save the snapshot, or return None if identical to the latest one."""
    folder = raw_dir / dataset_id
    folder.mkdir(parents=True, exist_ok=True)
    existing = sorted(folder.glob("*.csv"))
    if existing and sha256(existing[-1].read_bytes()) == sha256(content):
        return None
    path = folder / f"{(today or date.today()).isoformat()}.csv"
    path.write_bytes(content)
    return path


def main() -> None:
    for dataset_id in DATASETS:
        path = save_snapshot(dataset_id, fetch_csv(dataset_id))
        print(f"{dataset_id}: {'saved ' + path.name if path else 'unchanged, skipped'}")


if __name__ == "__main__":
    main()
