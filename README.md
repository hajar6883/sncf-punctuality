# Ponctualité SNCF — de l'open data au tableau de bord Qlik Sense

Work in progress. Pipeline: SNCF open data → DuckDB → dbt (star schema) → Qlik Sense, plus a next-month punctuality forecast.

## Quick start

```bash
uv sync                                  # install dependencies (Python 3.11)
uv run python -m ingestion.download      # snapshot the SNCF datasets into data/raw/
uv run python -m ingestion.load          # load snapshots into data/warehouse.duckdb (idempotent)
uv run pytest
```
