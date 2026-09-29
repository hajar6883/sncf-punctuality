"""Data-quality checks on raw tables; writes docs/data_quality.md."""

from datetime import date

import duckdb

from ingestion.config import PROJECT_ROOT, WAREHOUSE_PATH

REPORT_PATH = PROJECT_ROOT / "docs" / "data_quality.md"

TGV_CAUSES = [
    "prct_cause_externe", "prct_cause_infra", "prct_cause_gestion_trafic",
    "prct_cause_materiel_roulant", "prct_cause_gestion_gare", "prct_cause_prise_en_charge_voyageurs",
]
TGV_COUNTS = [
    "nb_train_prevu", "nb_annulation", "nb_train_depart_retard", "nb_train_retard_arrivee",
    "nb_train_retard_sup_15", "nb_train_retard_sup_30", "nb_train_retard_sup_60",
]
cause_sum = " + ".join(f"n({c})" for c in TGV_CAUSES)
any_negative = " or ".join(f"n({c}) < 0" for c in TGV_COUNTS)


def missing_months(table: str, where: str = "true") -> str:
    """Months between the table's first and last month with no row matching `where`."""
    return f"""
        with bounds as (select min(date) lo, max(date) hi from raw.{table}),
        months as (
            select strftime(unnest(generate_series(strptime(lo, '%Y-%m'), strptime(hi, '%Y-%m'), interval 1 month)), '%Y-%m') m
            from bounds)
        select m from months where m not in (select date from raw.{table} where {where}) order by m"""


# (table, check, SQL returning the affected rows, action)
CHECKS = [
    ("tgv_route_monthly", "Duplicate key (date, service, gare_depart, gare_arrivee)",
     "select date, service, gare_depart, gare_arrivee from raw.tgv_route_monthly group by all having count(*) > 1",
     "Test: expect 0 (dbt unique)"),
    ("tgv_route_monthly", "Missing months", missing_months("tgv_route_monthly"), "Document"),
    ("tgv_route_monthly", "Cancellations > planned trains",
     "select * from raw.tgv_route_monthly where n(nb_annulation) > n(nb_train_prevu)",
     "Fix: flag as COVID month, exclude from rates"),
    ("tgv_route_monthly", "Zero planned trains (rate undefined)",
     "select * from raw.tgv_route_monthly where n(nb_train_prevu) = 0",
     "Fix: rates set to null"),
    ("tgv_route_monthly", "Negative train count",
     f"select * from raw.tgv_route_monthly where {any_negative}", "Fix: null the negative value"),
    ("tgv_route_monthly", "Delay buckets not nested (>60 > >30 or >30 > >15)",
     "select * from raw.tgv_route_monthly where n(nb_train_retard_sup_60) > n(nb_train_retard_sup_30) "
     "or n(nb_train_retard_sup_30) > n(nb_train_retard_sup_15)",
     "Fix: null the >30 and >60 buckets on those rows"),
    ("tgv_route_monthly", "Negative average delay of late trains",
     "select * from raw.tgv_route_monthly where n(retard_moyen_arrivee) < 0 or n(retard_moyen_depart) < 0",
     "Fix: null (a late train cannot be early)"),
    ("tgv_route_monthly", "Negative average delay of all trains",
     "select * from raw.tgv_route_monthly where n(retard_moyen_tous_trains_arrivee) < 0",
     "Document: small negatives = early arrivals; large ones are errors"),
    ("tgv_route_monthly", "retard_moyen_trains_retard_sup15 equals the all-trains average",
     "select * from raw.tgv_route_monthly where retard_moyen_trains_retard_sup15 = retard_moyen_tous_trains_arrivee",
     "Fix: column dropped in staging (unreliable)"),
    ("tgv_route_monthly", "All cause shares = 0 while trains were late",
     f"select * from raw.tgv_route_monthly where {cause_sum} < 0.01 and n(nb_train_retard_arrivee) > 0",
     "Fix: causes set to null (missing, not zero)"),
    ("tgv_route_monthly", "Cause shares sum neither ~100 nor 0",
     f"select * from raw.tgv_route_monthly where abs({cause_sum} - 100) >= 0.5 and {cause_sum} >= 0.01",
     "Document"),
    ("tgv_route_monthly", "Domestic route also reported under 'International'",
     "select i.* from raw.tgv_route_monthly i join raw.tgv_route_monthly d "
     "using (date, gare_depart, gare_arrivee) where i.service = 'International' and d.service = 'National'",
     "Document: never sum National + International"),
    ("tgv_route_monthly", "Route with incomplete history (fewer months than the dataset)",
     "select gare_depart, gare_arrivee, service from raw.tgv_route_monthly group by all "
     "having count(*) < (select count(distinct date) from raw.tgv_route_monthly)",
     "Document: forecast must handle short series"),
    ("ter_region_monthly", "All-null measures (Lorraine 2013-2015, publication refused)",
     "select * from raw.ter_region_monthly where taux_de_regularite is null", "Document"),
    ("ter_region_monthly", "Circulated != planned - cancelled",
     "select * from raw.ter_region_monthly where n(nombre_de_trains_programmes) - n(nombre_de_trains_annules) "
     "<> n(nombre_de_trains_ayant_circule)", "Document"),
    ("ter_region_monthly", "Region without full history (2016 region reform, 2025 renames)",
     "select region from raw.ter_region_monthly group by 1 "
     "having count(*) < (select count(distinct date) from raw.ter_region_monthly)",
     "Document: region mapping needed for long trends"),
    ("transilien_line_monthly", "Months missing for all lines", missing_months("transilien_line_monthly"), "Document"),
    ("transilien_line_monthly", "Months missing for line U",
     missing_months("transilien_line_monthly", "ligne = 'U'"), "Document"),
    ("transilien_line_monthly", "Null punctuality rate",
     "select * from raw.transilien_line_monthly where n(taux_de_ponctualite) is null or isnan(n(taux_de_ponctualite))",
     "Document"),
    ("tgv_axis_monthly", "Null regularity",
     "select * from raw.tgv_axis_monthly where regularite_composite is null", "Document"),
    ("intercites_route_monthly", "Duplicate key (date, depart, arrivee) with different values",
     "select date, depart, arrivee from raw.intercites_route_monthly group by all having count(*) > 1",
     "Document: no field to tell the two series apart"),
    ("intercites_route_monthly", "Zero trains circulated but regularity = 0",
     "select * from raw.intercites_route_monthly where n(nombre_de_trains_ayant_circule) = 0",
     "Fix: rate set to null"),
    ("intercites_route_monthly", "Station renamed (LYON-PART-DIEU until 2017, LYON after)",
     "select * from raw.intercites_route_monthly where 'LYON-PART-DIEU' in (depart, arrivee)",
     "Fix: map to one name"),
]

# Rates must lie in [0, 100] everywhere
RATE_COLUMNS = {
    "tgv_route_monthly": TGV_CAUSES,
    "ter_region_monthly": ["taux_de_regularite"],
    "transilien_line_monthly": ["taux_de_ponctualite"],
    "intercites_route_monthly": ["taux_de_regularite"],
    "tgv_axis_monthly": ["regularite_composite", "ponctualite_origine"],
    "tgv_national_monthly": ["regularite_composite", "ponctualite_origine"],
}
for table, cols in RATE_COLUMNS.items():
    out_of_range = " or ".join(f"n({c}) not between 0 and 100" for c in cols)
    CHECKS.append((table, "Rate outside [0, 100]", f"select * from raw.{table} where {out_of_range}", "Test: expect 0 (dbt range)"))


def run(con: duckdb.DuckDBPyConnection) -> str:
    con.execute("create or replace temp macro n(x) as try_cast(x as double)")
    lines = [
        "# Data quality report (raw layer)",
        "",
        f"Generated by `ingestion/data_quality.py` on {date.today().isoformat()}. Do not edit by hand.",
        "",
        "## Tables",
        "",
        "| Table | Rows | First month | Last month | Months |",
        "|---|---:|---|---|---:|",
    ]
    for table in RATE_COLUMNS:
        rows, lo, hi, months = con.execute(
            f"select count(*), min(date), max(date), count(distinct date) from raw.{table}"
        ).fetchone()
        lines.append(f"| `{table}` | {rows:,} | {lo} | {hi} | {months} |")

    lines += ["", "## Checks", "", "| Table | Check | Affected | Action | Examples |", "|---|---|---:|---|---|"]
    for table, check, sql, action in CHECKS:
        affected = con.execute(f"select count(*) from ({sql})").fetchone()[0]
        examples = ""
        if 0 < affected and "missing" in check.lower():
            examples = ", ".join(r[0] for r in con.execute(sql).fetchall())
        lines.append(f"| `{table}` | {check} | {affected:,} | {action} | {examples} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    with duckdb.connect(str(WAREHOUSE_PATH), read_only=True) as con:
        REPORT_PATH.write_text(run(con))
    print(f"wrote {REPORT_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
