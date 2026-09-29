# Master measures

Create each one under **Master items → Measures**, with the label and number format given.
`[%MoisIndex]` = year × 12 + month, so the same month last year is always `index − 12`, across year boundaries.
`$(vClearCalendar)` (set in the script) removes calendar selections, so a measure can reach months outside
the user's selection (last year, the previous 11 months) while still reacting to every other filter.

**Service.** Always analyse one service at a time (sheet plan: Service filter set to *always one selected value*).

## Required measures

### 1. Taux de régularité
Punctuality rate over whatever is selected. Format: number, `0.0%`.
```
Sum(trains_on_time) / Sum(trains_ran)
```
Sum/Sum, never Avg of rates: large routes weigh more, as they should.

### 2. Taux de régularité (mois)
Rate for the latest selected month; the KPI shown on sheet 1. Format `0.0%`.
```
Sum({<[%MoisIndex]={$(=Max([%MoisIndex]))}, $(vClearCalendar)>} trains_on_time)
/ Sum({<[%MoisIndex]={$(=Max([%MoisIndex]))}, $(vClearCalendar)>} trains_ran)
```
`$(=Max([%MoisIndex]))` is evaluated once, before the chart, in the current selections.

### 3. Évolution sur 1 an (pts)
Same month this year minus same month last year, in percentage points (not %: the difference of two rates).
Format: number, `+0.0;-0.0`, label suffix "pts".
```
100 * (
  Sum({<[%MoisIndex]={$(=Max([%MoisIndex]))}, $(vClearCalendar)>} trains_on_time)
  / Sum({<[%MoisIndex]={$(=Max([%MoisIndex]))}, $(vClearCalendar)>} trains_ran)
  -
  Sum({<[%MoisIndex]={$(=Max([%MoisIndex]) - 12)}, $(vClearCalendar)>} trains_on_time)
  / Sum({<[%MoisIndex]={$(=Max([%MoisIndex]) - 12)}, $(vClearCalendar)>} trains_ran)
)
```

### 4. Taux de régularité 12 mois glissants
The 12 months ending at the latest selected month. Format `0.0%`.
```
Sum({<[%MoisIndex]={">=$(=Max([%MoisIndex]) - 11)<=$(=Max([%MoisIndex]))"}, $(vClearCalendar)>} trains_on_time)
/ Sum({<[%MoisIndex]={">=$(=Max([%MoisIndex]) - 11)<=$(=Max([%MoisIndex]))"}, $(vClearCalendar)>} trains_ran)
```
Set analysis is computed once per chart, not per row, so this works for a KPI but not as a line over months.
For a rolling line, use this in a line chart by `[Année-Mois]` (sorted by date):
```
RangeSum(Above(Sum(trains_on_time), 0, 12)) / RangeSum(Above(Sum(trains_ran), 0, 12))
```
Limit: the first 11 points use fewer than 12 months, and `Above` only sees months present in the chart.

### 5. Taux (mois, liaisons ≥ seuil)
Used by the "10 worst routes" chart: the latest-month rate, but only for routes with at least
`vMinTrains` (50) trains that month. Smaller routes return null and disappear from the ranking. Format `0.0%`.
```
If(Sum({<[%MoisIndex]={$(=Max([%MoisIndex]))}, $(vClearCalendar)>} trains_ran) >= $(vMinTrains),
   Sum({<[%MoisIndex]={$(=Max([%MoisIndex]))}, $(vClearCalendar)>} trains_on_time)
   / Sum({<[%MoisIndex]={$(=Max([%MoisIndex]))}, $(vClearCalendar)>} trains_ran))
```
Chart setup: bar chart, dimension `Liaison`, limit **Fixed number → Smallest → 10**, sort by this measure
ascending, "Include null values" off.

### 6. Part des retards par cause
Each cause's share of (estimated) late trains. Dimension: `Cause`. Format `0.0%`.
```
Sum(est_late_trains) / Sum({<Cause=>} TOTAL est_late_trains)
```
`TOTAL` ignores the chart's dimension (denominator = all causes); `{<Cause=>}` keeps the denominator whole
when the user selects one cause. Label the chart "estimation": the shares' base is not published.

## Supporting measures

| Label | Expression | Format |
|---|---|---|
| Trains ayant circulé | `Sum(trains_ran)` | `#,##0` |
| Taux d'annulation | `Sum({<trains_ran={"*"}>} trains_cancelled) / Sum({<trains_ran={"*"}>} trains_planned)` | `0.0%` |
| Retard moyen à l'arrivée (min, tous trains) | `Sum(delay_minutes_all_arrival) / Sum({<delay_minutes_all_arrival={"*"}>} trains_ran)` | `0.0` |
| Retard moyen des trains en retard (min) | `Sum(delay_minutes_late_arrival) / Sum({<delay_minutes_late_arrival={"*"}>} trains_late_arrival)` | `0.0` |
| Part des trains > 30 min | `Sum(trains_late_30) / Sum({<trains_late_30={"*"}>} trains_ran)` | `0.0%` |

`{<field={"*"}>}` keeps only rows where that field is not null, so numerator and denominator cover the
same rows (cleaned values are null in staging, see `docs/data_model.md`).

## Titles

Latest month, for sheet and KPI titles:
```
='Mois : ' & Date(Max([%DateKey]), 'MMMM YYYY')
```
