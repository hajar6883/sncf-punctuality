# Qlik data model notes

## Setup in Qlik Cloud

1. `make all` locally → 5 files in `data/marts/`.
2. Qlik Cloud → *Analytics* → *Data files* (personal space) → upload the 5 `.parquet` files.
3. Create an app → *Data load editor* → one section per `///$tab` block of `load_script.qvs` → *Load data*.
4. *Data model viewer*: you should see 5 tables in a chain, no `$Syn` table, no dotted (loop) lines.
   Save a screenshot to `qlik/screenshots/data_model.png`.
5. Create the master measures (`master_measures.md`), then the sheets (`sheet_plan.md`).

## The model

```
Calendrier ──%DateKey── Regularite ──%RouteKey── Liaisons
                            │
                     %PunctualityKey
                            │
                      CausesRetard ──%CauseKey── Causes
```

5 tables, 4 key fields, each key shared by exactly two tables.

## Concepts, applied to this app

**Associative model.** Qlik links tables automatically on identical field names; there are no joins in
charts. Selecting a route in `Liaisons` propagates through `%RouteKey` to `Regularite`, then to
`Calendrier` and `CausesRetard`. Values compatible with the selection are white, excluded values grey:
the grey values are an answer too ("which months had no data for this route?").

**Why only key fields are shared.** Because association is by name, the script renames every field and
keeps only the four `%` keys common. `HidePrefix = '%'` hides the keys from users.

**Synthetic key.** If two tables share *more than one* field, Qlik builds a hidden `$Syn` table on the
combination. Here it would happen if `CausesRetard` kept `month_start` and `route_key`: it would share
two fields with `Regularite`. It does not: dbt gives it one composite key, `%PunctualityKey`
(hash of month + route). Same fix in general: one composite key, or drop/rename the extra fields.

**Circular reference.** A loop in the table graph (A–B, B–C, C–A) makes the path between two tables
ambiguous; Qlik loosens one link. This model is a tree, so there is no loop. Example of how one could
appear: loading `first_month` from `dim_route` as `%DateKey` would link `Liaisons` directly to
`Calendrier`, closing the loop Liaisons–Regularite–Calendrier.

**QVD.** Qlik's native file format: a table as stored in memory, very fast to reload. The script has two
layers: *Extract* (Parquet → QVD) and *Model* (QVD → tables). In production they are separate apps: one
extract app writes QVDs on a schedule, many dashboard apps read them. A QVD load with only renames stays
*optimized* (read almost directly into memory); a transformation like `If()` or a `WHERE` other than
`Exists()` makes it unoptimized. At our data volumes this does not matter.

**Master calendar.** The calendar is generated in the script, not taken from the fact, so every month
exists even when no train data does (no gaps in time charts). Pattern: min/max from the field's distinct
values (`FieldValue`, fast on big facts), then `AUTOGENERATE` + `WHILE IterNo()` to create one row per
month, and a *preceding load* on top to derive the attributes. It is monthly because the data is monthly.
`%MoisIndex` (year × 12 + month) makes "last year" `−12` and "last 12 months" a range, which set
analysis needs.

**Mapping load / ApplyMap.** `MapPerturbation` is a two-column lookup table used by `ApplyMap()` and
dropped automatically at the end of the script: it adds the disrupted-month label from dbt without a join.

**Dual.** A value with a text and a number. `Cause` shows the French label and sorts by `sort_order`;
`Mois` shows "janv." and sorts by 1..12.

**AutoNumber.** Replaces the 32-character hash keys with 1, 2, 3… (less memory, faster links). Done after
the QVD stores, because the numbers are not stable between reloads.

**Why the rates are Sum/Sum.** The fact stores counts; `Sum(trains_on_time) / Sum(trains_ran)` gives each
route its real weight. Averaging monthly route rates would count a 21-train route like a 900-train one.

**Why `vMinTrains = 50`.** In the latest month, 3 National routes ran 21–24 trains (one at 52.4 %,
where one late train moves the rate about 5 points); the next smallest ran 53. The threshold removes exactly
those three from the "worst 10" ranking.

## Phase 4: loading forecasts without a synthetic key

The forecast table will have a month and a route. Loaded as-is, it would share `%DateKey` and
`%RouteKey` with `Regularite` → synthetic key. Options:
1. **Concatenate** it into `Regularite` with a `[Type]` field (`Réalisé` / `Prévision`): one fact, no new link.
2. Give it one composite key (month + route) and remove the separate keys: it hangs off `Regularite`
   like `CausesRetard`, but then forecast months with no actuals would have no calendar link.

Option 1 is the usual Qlik answer and keeps the calendar working for future months.
