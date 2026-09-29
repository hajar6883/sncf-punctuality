"""Load raw CSV snapshots into DuckDB, idempotently, with a load log.

Re-running never duplicates rows, at two levels:
  1. file level: a file whose SHA-256 is already in raw._load_log is skipped;
  2. row level: each row carries _row_hash (md5 of all its values) and is inserted only
     if that hash is not already in the table. A corrected row published later by SNCF
     has a new hash, so it is appended next to the old version; staging keeps the latest.

Raw tables keep every column as VARCHAR, exactly as published. Typing happens in dbt staging.
"""

import hashlib
import uuid
from pathlib import Path

import duckdb

from ingestion.config import DATASETS, RAW_DIR, WAREHOUSE_PATH

LOAD_LOG_DDL = """
create table if not exists raw._load_log (
    load_id        varchar,
    dataset_id     varchar,
    table_name     varchar,
    file_name      varchar,
    file_sha256    varchar,
    rows_in_file   bigint,
    rows_inserted  bigint,
    status         varchar,   -- 'loaded' or 'skipped_known_file'
    loaded_at      timestamp default current_timestamp
)
"""


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_file(con: duckdb.DuckDBPyConnection, dataset_id: str, table: str, path: Path, load_id: str) -> int:
    """Load one snapshot into raw.<table>. Returns the number of rows inserted."""
    con.execute("create schema if not exists raw")
    con.execute(LOAD_LOG_DDL)
    digest = file_sha256(path)

    already_loaded = con.execute(
        "select count(*) from raw._load_log where dataset_id = ? and file_sha256 = ? and status = 'loaded'",
        [dataset_id, digest],
    ).fetchone()[0]
    if already_loaded:
        con.execute(
            "insert into raw._load_log values (?, ?, ?, ?, ?, null, 0, 'skipped_known_file', current_timestamp)",
            [load_id, dataset_id, table, path.name, digest],
        )
        return 0

    con.execute("begin transaction")
    try:
        # `src::varchar` renders the whole row as a struct string ({'date': 2026-06, ...}),
        # so the hash covers every column name and value.
        con.execute(
            """
            create or replace temp table _incoming as
            select src.*, md5(src::varchar) as _row_hash
            from read_csv(?, delim = ';', header = true, quote = '"', all_varchar = true) as src
            """,
            [str(path)],
        )
        rows_in_file = con.execute("select count(*) from _incoming").fetchone()[0]

        # First load creates the table with the file's columns plus audit columns.
        con.execute(
            f"""
            create table if not exists raw.{table} as
            select *, null::varchar as _load_id, null::varchar as _source_file, null::timestamp as _loaded_at
            from _incoming limit 0
            """
        )
        # BY NAME matches columns by name, not position. If SNCF adds or renames a column,
        # this fails loudly instead of shifting values into the wrong columns.
        # QUALIFY also drops exact duplicate rows inside the same file (none found in profiling).
        inserted = con.execute(
            f"""
            insert into raw.{table} by name
            select *, ? as _load_id, ? as _source_file, current_timestamp as _loaded_at
            from _incoming
            where _row_hash not in (select _row_hash from raw.{table})
            qualify row_number() over (partition by _row_hash) = 1
            """,
            [load_id, f"{dataset_id}/{path.name}"],
        ).fetchone()[0]

        con.execute(
            "insert into raw._load_log values (?, ?, ?, ?, ?, ?, ?, 'loaded', current_timestamp)",
            [load_id, dataset_id, table, path.name, digest, rows_in_file, inserted],
        )
        con.execute("commit")
    except Exception:
        con.execute("rollback")
        raise
    return inserted


def load_all(con: duckdb.DuckDBPyConnection, raw_dir: Path = RAW_DIR) -> dict[str, int]:
    """Load every snapshot of every dataset, oldest first. Returns rows inserted per table."""
    load_id = str(uuid.uuid4())
    inserted = {}
    for dataset_id, table in DATASETS.items():
        inserted[table] = 0
        for path in sorted((raw_dir / dataset_id).glob("*.csv")):
            inserted[table] += load_file(con, dataset_id, table, path, load_id)
    return inserted


def main() -> None:
    WAREHOUSE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(WAREHOUSE_PATH)) as con:
        for table, n in load_all(con).items():
            total = con.execute(f"select count(*) from raw.{table}").fetchone()[0]
            print(f"raw.{table}: +{n} rows (total {total})")


if __name__ == "__main__":
    main()
