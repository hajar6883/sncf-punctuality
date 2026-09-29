"""Shared settings: which SNCF datasets we ingest and where files live."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
WAREHOUSE_PATH = PROJECT_ROOT / "data" / "warehouse.duckdb"

# Opendatasoft "Explore v2.1" API behind ressources.data.sncf.com.
# The /exports/csv endpoint returns the full dataset (no 100-row paging limit).
API_BASE = "https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets"

# SNCF dataset id -> name of our raw table in DuckDB.
# The TGV route dataset is the core of the model; the others are kept raw for context.
DATASETS = {
    "regularite-mensuelle-tgv-aqst": "tgv_route_monthly",
    "regularite-mensuelle-ter": "ter_region_monthly",
    "ponctualite-mensuelle-transilien": "transilien_line_monthly",
    "regularite-mensuelle-intercites": "intercites_route_monthly",
    "regularite-mensuelle-tgv-axes": "tgv_axis_monthly",
    "reglarite-mensuelle-tgv-nationale": "tgv_national_monthly",  # sic: typo is in SNCF's id
}
