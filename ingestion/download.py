"""Download full CSV snapshots of the SNCF punctuality datasets.

Each run writes data/raw/<dataset_id>/<YYYY-MM-DD>.csv. A snapshot is only kept if its
content differs from the most recent one, so re-running never accumulates identical files.
Loading into DuckDB is a separate step (ingestion.load), so it can be tested offline.
"""

import hashlib
from datetime import date
from pathlib import Path

import requests

from ingestion.config import API_BASE, DATASETS, RAW_DIR


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def fetch_csv(dataset_id: str) -> bytes:
    # delimiter=';' because free-text columns contain commas;
    # use_labels=false gives stable technical column names (e.g. nb_train_prevu).
    url = f"{API_BASE}/{dataset_id}/exports/csv"
    response = requests.get(url, params={"delimiter": ";", "use_labels": "false"}, timeout=120)
    response.raise_for_status()
    return response.content


def save_snapshot(dataset_id: str, content: bytes, raw_dir: Path = RAW_DIR, today: date | None = None) -> Path | None:
    """Write the snapshot; return its path, or None if identical to the latest one."""
    folder = raw_dir / dataset_id
    folder.mkdir(parents=True, exist_ok=True)
    existing = sorted(folder.glob("*.csv"))  # ISO dates sort chronologically
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
