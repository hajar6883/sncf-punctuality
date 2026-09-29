"""Idempotency tests for ingestion. Offline: they use a small TGV-shaped fixture, not the API."""

import shutil
from datetime import date
from pathlib import Path

import duckdb
import pytest

from ingestion.download import save_snapshot
from ingestion.load import load_all

FIXTURE = Path(__file__).parent / "fixtures" / "tgv_sample.csv"
DATASET_ID = "regularite-mensuelle-tgv-aqst"
TABLE = "raw.tgv_route_monthly"


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    folder = tmp_path / "raw" / DATASET_ID
    folder.mkdir(parents=True)
    shutil.copy(FIXTURE, folder / "2026-09-01.csv")
    return tmp_path / "raw"


@pytest.fixture
def con(tmp_path: Path):
    with duckdb.connect(str(tmp_path / "test.duckdb")) as connection:
        yield connection


def count(con, table: str = TABLE) -> int:
    return con.execute(f"select count(*) from {table}").fetchone()[0]


def test_first_run_loads_all_rows_including_multiline_comment(con, raw_dir):
    load_all(con, raw_dir)
    assert count(con) == 3  # 3 records even though the file has 4 data lines
    comment = con.execute(
        f"select commentaires_retard_arrivee from {TABLE} where gare_arrivee = 'LILLE'"
    ).fetchone()[0]
    assert comment == "Ligne 1 du commentaire;\nligne 2 du commentaire"


def test_second_run_inserts_zero_rows(con, raw_dir):
    load_all(con, raw_dir)
    rows_before = count(con)

    inserted = load_all(con, raw_dir)

    assert sum(inserted.values()) == 0
    assert count(con) == rows_before
    statuses = [r[0] for r in con.execute("select status from raw._load_log order by loaded_at").fetchall()]
    assert statuses == ["loaded", "skipped_known_file"]


def test_new_snapshot_only_adds_new_rows(con, raw_dir):
    load_all(con, raw_dir)
    # Next snapshot = same history + one new month (how SNCF publishes: full export each time).
    new_row = "2026-06;National;PARIS LYON;MARSEILLE ST CHARLES;910;1;\n"
    (raw_dir / DATASET_ID / "2026-10-01.csv").write_text(FIXTURE.read_text() + new_row)

    inserted = load_all(con, raw_dir)

    assert inserted["tgv_route_monthly"] == 1
    assert count(con) == 4


def test_revised_row_is_appended_not_overwritten(con, raw_dir):
    load_all(con, raw_dir)
    revised = FIXTURE.read_text().replace("PARIS LYON;MARSEILLE ST CHARLES;900;4", "PARIS LYON;MARSEILLE ST CHARLES;900;5")
    (raw_dir / DATASET_ID / "2026-10-01.csv").write_text(revised)

    load_all(con, raw_dir)

    versions = con.execute(
        f"select nb_annulation from {TABLE} where gare_arrivee = 'MARSEILLE ST CHARLES' order by _loaded_at"
    ).fetchall()
    assert versions == [("4",), ("5",)]  # both versions kept; staging will pick the latest


def test_identical_download_is_not_saved_twice(tmp_path):
    content = FIXTURE.read_bytes()
    first = save_snapshot(DATASET_ID, content, tmp_path, today=date(2026, 9, 1))
    second = save_snapshot(DATASET_ID, content, tmp_path, today=date(2026, 9, 2))
    assert first is not None and second is None
    assert len(list((tmp_path / DATASET_ID).glob("*.csv"))) == 1
