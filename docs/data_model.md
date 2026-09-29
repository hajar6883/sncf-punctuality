# Data model (TGV star schema)

Source: `regularite-mensuelle-tgv-aqst` (TGV punctuality by route, monthly, 2018-01 onward).
Built with dbt in `dbt/`; marts are written to `data/marts/*.parquet` for Qlik.

```mermaid
erDiagram
    dim_date ||--o{ fact_punctuality : month_start
    dim_route ||--o{ fact_punctuality : route_key
    fact_punctuality ||--o{ fact_delay_cause : punctuality_key
    dim_delay_cause ||--o{ fact_delay_cause : cause_key
```

## Tables

| Table | Grain | Rows (approx.) |
|---|---|---:|
| `fact_punctuality` | month × route × service | 12,500 |
| `fact_delay_cause` | punctuality row × delay cause | 6 per row with cause data |
| `dim_route` | service × origin × destination | 146 |
| `dim_date` | month | 102 |
| `dim_delay_cause` | delay cause | 6 |

## Design decisions

**Service is part of the grain.** In 2025-07 to 2025-09 the same origin-destination pair (e.g. Dijon → Paris Lyon)
is reported under both `National` and `International` with different counts. Service is therefore part of the
route key, not a label on the route. National and International rows must never be summed together.

**Only additive measures are stored.** Rates and averages cannot be summed or averaged across routes or months
(a monthly average of rates gives a small route the same weight as Paris–Marseille). The fact stores counts and
total delay minutes (`average × number of trains`); every rate and average is computed as `Sum(...) / Sum(...)`.

**Monthly calendar.** The source is monthly; a daily calendar would suggest a precision the data does not have.

**Causes as a separate fact.** The six cause columns are unpivoted so "cause" can be used as a dimension
(one chart, one filter). `fact_delay_cause` links to `fact_punctuality` through a single key and carries no
month or route key itself: two tables sharing two keys would create a synthetic key in Qlik.

## Definitions and known limits

- **Punctuality rate** = 1 − trains late at arrival / trains that ran. The lateness threshold used by SNCF is
  not published in the dataset, so the KPI is named "taux de régularité à l'arrivée (seuil SNCF)".
  It tracks the official *régularité composite* (`tgv_national_monthly`) but is lower by a few points
  (June 2024: 86.1 vs 88.0), because that indicator is defined differently.
- **Cause shares** are a mix within one row; their denominator is not published. The implied denominator
  matches "trains late at arrival" in only 36–73 % of rows depending on the year. Across rows, causes are weighted by trains
  late at arrival (`est_late_trains`); this is an approximation and is labelled as such.
- **COVID period** (`is_covid_period`): 2020-03 to 2020-06 and 2020-10 to 2020-12, the months when planned
  National TGV trains fell below 75 % of the February 2020 level.

## Cleaning rules (staging)

From `docs/data_quality.md`:

| Problem | Rule |
|---|---|
| Revised rows (same key, loaded twice) | keep the latest `_loaded_at` |
| Negative train counts | null |
| Buckets not nested (>60 > >30 or >30 > >15) | null the >30 and >60 buckets |
| Negative average delay of late trains | null |
| Zero trains ran | rates undefined (division guarded in Qlik) |
| All cause shares = 0 | causes null (missing, not zero) |
| `retard_moyen_trains_retard_sup15` | dropped (mirrors another column in 2018–2019) |
| Empty comment columns | dropped |
