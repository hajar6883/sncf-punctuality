DBT = cd dbt && DBT_PROFILES_DIR=. uv run dbt

.PHONY: all download load quality dbt test

all: download load quality dbt test

download:
	uv run python -m ingestion.download

load:
	uv run python -m ingestion.load

quality:
	uv run python -m ingestion.data_quality

dbt:
	mkdir -p data/marts
	$(DBT) deps
	$(DBT) build

test:
	uv run pytest
