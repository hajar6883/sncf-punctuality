# Ponctualité SNCF — de l'open data au tableau de bord Qlik Sense

Pipeline: SNCF open data → DuckDB → dbt (star schema) → Qlik Sense, plus a next-month punctuality forecast.

## Quick start

```bash
uv sync      # install dependencies (Python 3.11)
make all     # download -> load -> data-quality report -> dbt build (+ tests) -> pytest
```

Steps can be run one by one: `make download`, `make load`, `make quality`, `make dbt`, `make test`.
Marts are written to `data/marts/*.parquet` (loaded by Qlik).

## Docs

- [Data quality report](docs/data_quality.md)
- [Data model](docs/data_model.md)
