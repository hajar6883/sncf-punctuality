# Qlik interview drill (20 questions on this app)

Answer out loud first, then compare. Each answer points to something you can show in the app.

## Load script

**1. Walk me through your load script.**
Five sections. *Settings*: variables, month names, hidden `%` prefix. *Extract*: a loop loads each dbt
Parquet file and stores it as a QVD. *Model*: loads the QVDs, renames fields so only four keys are shared.
*Calendar*: generates a monthly master calendar. *Finalize*: AutoNumber on the hash keys.

**2. Why are the transformations in dbt and not in the Qlik script?**
One source of truth: the same cleaned tables feed Qlik and the forecast in Python, and they are tested in
dbt (51 tests). Qlik does what only Qlik does: associative model, calendar, set analysis, UI.

**3. What is a preceding load? Where do you use one?**
A `LOAD` with no `FROM` that reads the output of the load below it. In the calendar, the bottom load
generates one date per month; the preceding load derives year, month, quarter, season, index from it,
without repeating the date expression.

**4. What does `ApplyMap` do and why not a join?**
Looks up a value in a two-column mapping table. It adds one field (disruption label) without changing row
counts, which a join can do if the lookup key is not unique; the mapping table is dropped automatically.

## QVD

**5. What is a QVD and why store one?**
Qlik's native format: data stored the way Qlik holds it in memory. Reloading from QVD is much faster
than from the source, and the source is queried once for many apps.

**6. What is an optimized QVD load and what breaks it?**
Loading a QVD with only field renames or `WHERE Exists()` lets Qlik read it almost directly into memory.
Any transformation (`If`, a calculation, most `WHERE` clauses) makes it unoptimized. My `Liaisons` load is
unoptimized because of `If(touches_paris = 1, ...)`; at 146 rows it does not matter.

**7. How would this look in production?**
Two or three tiers: an extract app (source → raw QVDs), optionally a transform app (→ model QVDs), and
dashboard apps loading only QVDs, each reloaded on a schedule with task chaining.

## Associative model and data modelling

**8. How does Qlik know how tables are linked?**
By identical field names. No joins in charts. That is why I rename everything and share only
`%DateKey`, `%RouteKey`, `%PunctualityKey`, `%CauseKey`.

**9. What is a synthetic key? Could you get one here?**
Two tables sharing more than one field → Qlik builds a hidden `$Syn` table on the combination. It would
happen if the cause table kept month and route. dbt gives it one composite key, `punctuality_key`, instead.
It will come up again in phase 4 with the forecast table (fix: concatenate into the fact).

**10. What is a circular reference?**
A loop in the table graph, which makes the path between two tables ambiguous; Qlik loosens a link.
Mine is a tree. Example: linking `Liaisons` to the calendar through the route's first month would close
a loop with `Regularite`.

**11. Why a star schema with two facts?**
The route × month fact holds counts. Causes are six percentages per row; as rows they can be a
dimension (one chart, one filter). Different grain → separate table, attached by one key.

**12. What do white, green and grey mean?**
Green: selected. White: possible given the selection. Grey: excluded. Selecting a route and seeing grey
months shows months without data for that route: the model answers questions nobody asked.

**13. What is a master calendar and why build one?**
A calendar generated from the min and max date with no gaps, holding all time attributes. Charts don't
skip missing months, and time logic (year, season, index) is defined once. Mine is monthly because the
data is monthly; a daily calendar would imply precision the data doesn't have.

## Set analysis and expressions

**14. How do you compute the punctuality rate and why that way?**
`Sum(trains_on_time) / Sum(trains_ran)`. The ratio of sums gives each route its real weight; an average
of monthly rates would count a 21-train route like a 900-train one.

**15. Explain the year-on-year measure.**
The set `{<[%MoisIndex]={$(=Max([%MoisIndex]))}, $(vClearCalendar)>}` fixes the latest selected month;
the same with `−12` gives last year. `vClearCalendar` removes calendar selections so the expression can
reach last year even if the user selected 2026. The result is in percentage points, since it is the
difference of two rates.

**16. What is `$(=...)` and when is it evaluated?**
Dollar-sign expansion: evaluated once before the chart is computed, in the current selections, and
pasted into the expression as text. So `Max([%MoisIndex])` is a constant for the whole chart, not per row.

**17. Why doesn't the rolling-12 set work as a line over months?**
Set analysis is evaluated once per chart, not per dimension value. For a line, I use
`RangeSum(Above(Sum(x), 0, 12))` (chart inter-record function), or an *As-Of* table in the script
(each month linked to its previous 12), which also works with selections.

**18. What does `TOTAL` do in the cause-share measure?**
`Sum({<Cause=>} TOTAL est_late_trains)` ignores the chart dimension, so the denominator is all causes.
`{<Cause=>}` ignores a selection on `Cause`, so selecting one cause doesn't turn its share into 100 %.

**19. How do you show the 10 worst routes, and why the 50-train threshold?**
Dimension `Liaison`, measure = latest-month rate returning null below `vMinTrains` trains, limit to the
10 smallest values. Without a threshold, a 21-train route (one late train ≈ 5 points) tops the list by
chance. Alternative: `Aggr` with `Rank()` in a calculated dimension.

## Security

**20. What is section access? How would you use it here?**
Row-level security in the script: a `Section Access` table maps users to values of a reduction field; on
open, the data is reduced to their rows. Here: regional managers see only their `SERVICE`. Pitfalls:
field names and values in upper case, `*` means "all values listed in the table", and a mistake can lock
everyone out, so test on a copy. See `section_access_example.qvs`.
