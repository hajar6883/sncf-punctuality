# Sheet plan

Measures refer to `master_measures.md`. Every sheet has, at the top, filter panes on
`Service` (*Always one selected value*, default **National**), `Année`, `[Année-Mois]`.

## Sheet 1 — Vue nationale

Question: *how punctual is TGV this month, and is it getting better?*

| Object | Content |
|---|---|
| KPI | Taux de régularité (mois), with Évolution sur 1 an (pts) as the second measure (green if ≥ 0) |
| KPI | Taux de régularité 12 mois glissants |
| KPI | Taux d'annulation (over the selection) |
| KPI | Retard moyen des trains en retard, min (over the selection) |
| Line chart | `[Année-Mois]` × Taux de régularité, plus the 12-month rolling line (`RangeSum(Above(...))`) |
| Text | Disrupted months: add a reference band or note for `Perturbation` (grève 2019-12, COVID 2020) |

Tip: a second line chart by `Mois` with `Année` as a second dimension shows seasonality (one line per year).

## Sheet 2 — Liaisons

Question: *which routes are worst, and is it structural or a bad month?*

| Object | Content |
|---|---|
| Filter panes | `[Liaison (2 sens)]`, `[Gare de départ]`, `[Gare d'arrivée]`, `[Dessert Paris]`, `[Pays d'arrivée]` |
| Bar chart | 10 worst routes this month: measure 5 (see its chart setup) |
| Table | `Liaison` · Trains ayant circulé · Taux de régularité (mois) · Évolution sur 1 an · 12 mois glissants · Retard moyen des trains en retard, sorted by rate |
| Line chart | `[Année-Mois]` × Taux de régularité for the selected route(s) |
| Table | `[Année-Mois]`, `Liaison`, `[Commentaire retards]` (SNCF's own explanation, where given) |

Demo in interview: click a route in the bar chart; everything filters. Show the grey (excluded) values in
the filter panes: that is the associative model.

## Sheet 3 — Causes de retard

Question: *what causes the delays, and does it depend on season or route?*

| Object | Content |
|---|---|
| Bar chart (100 % stacked) | `[Année-Mois]` or `Année` × Part des retards par cause, stacked by `Cause` |
| Bar chart | `Cause` × Part des retards par cause for the current selection |
| Heatmap (table with colour by expression) | `Saison` × `Cause`, measure Part des retards par cause |
| Text | "Estimation: SNCF does not publish the base of the cause percentages" |

## Sheet 4 — Prévision vs réalisé (after phase 4)

Question: *what punctuality should we expect next month, per route, and how reliable is that forecast?*

| Object | Content |
|---|---|
| Line chart | `[Année-Mois]` × actual rate and forecast rate, for one selected route |
| KPI | Forecast error (MAE) of the model vs the seasonal-naive baseline, on the test period |
| Table | Routes with the largest forecast drop for next month |

Data model for this sheet is designed in phase 4 (the forecast table must not create a synthetic key with
`Regularite`; see `model_notes.md`).
