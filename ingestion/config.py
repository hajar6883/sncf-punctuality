"""Datasets to ingest and file locations."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
WAREHOUSE_PATH = PROJECT_ROOT / "data" / "warehouse.duckdb"

API_BASE = "https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets"

# SNCF dataset id -> raw table name
DATASETS = {
    "regularite-mensuelle-tgv-aqst": "tgv_route_monthly",
    "regularite-mensuelle-ter": "ter_region_monthly",
    "ponctualite-mensuelle-transilien": "transilien_line_monthly",
    "regularite-mensuelle-intercites": "intercites_route_monthly",
    "regularite-mensuelle-tgv-axes": "tgv_axis_monthly",
    "reglarite-mensuelle-tgv-nationale": "tgv_national_monthly",  # typo is SNCF's
}
