{% set counts = {
    'nb_train_prevu': 'trains_planned',
    'nb_annulation': 'trains_cancelled',
    'nb_train_depart_retard': 'trains_late_departure',
    'nb_train_retard_arrivee': 'trains_late_arrival',
} %}
{% set causes = {
    'prct_cause_externe': 'cause_external_pct',
    'prct_cause_infra': 'cause_infrastructure_pct',
    'prct_cause_gestion_trafic': 'cause_traffic_management_pct',
    'prct_cause_materiel_roulant': 'cause_rolling_stock_pct',
    'prct_cause_gestion_gare': 'cause_station_management_pct',
    'prct_cause_prise_en_charge_voyageurs': 'cause_passenger_handling_pct',
} %}

with latest as (
    -- keep the latest version of each row if SNCF revised it
    select *
    from {{ source('raw', 'tgv_route_monthly') }}
    qualify row_number() over (
        partition by date, service, gare_depart, gare_arrivee order by _loaded_at desc
    ) = 1
),

typed as (
    select
        strptime(date || '-01', '%Y-%m-%d')::date as month_start,
        service,
        trim(gare_depart) as origin_station,
        trim(gare_arrivee) as destination_station,
        try_cast(duree_moyenne as double) as avg_journey_minutes,
        {% for src, col in counts.items() %}
        try_cast({{ src }} as integer) as {{ col }},
        {% endfor %}
        try_cast(nb_train_retard_sup_15 as integer) as late_15,
        try_cast(nb_train_retard_sup_30 as integer) as late_30,
        try_cast(nb_train_retard_sup_60 as integer) as late_60,
        try_cast(retard_moyen_depart as double) as avg_delay_late_departure,
        try_cast(retard_moyen_tous_trains_depart as double) as avg_delay_all_departure,
        try_cast(retard_moyen_arrivee as double) as avg_delay_late_arrival,
        try_cast(retard_moyen_tous_trains_arrivee as double) as avg_delay_all_arrival,
        {% for src, col in causes.items() %}
        try_cast({{ src }} as double) as {{ col }},
        {% endfor %}
        nullif(trim(commentaires_retard_arrivee), '') as arrival_comment
    from latest
),

cleaned as (
    select
        month_start,
        service,
        origin_station,
        destination_station,
        avg_journey_minutes,
        {% for col in counts.values() %}
        case when {{ col }} >= 0 then {{ col }} end as {{ col }},
        {% endfor %}
        -- ran is unknown when cancellations exceed planned trains (COVID months)
        case when trains_cancelled <= trains_planned then trains_planned - trains_cancelled end as trains_ran,
        -- buckets are kept only if late >= >15 >= >30 >= >60 >= 0
        {% for b in ['late_15', 'late_30', 'late_60'] %}
        case when trains_late_arrival >= late_15 and late_15 >= late_30 and late_30 >= late_60 and late_60 >= 0
             then {{ b }} end as trains_{{ b }},
        {% endfor %}
        case when avg_delay_late_departure >= 0 then avg_delay_late_departure end as avg_delay_late_departure,
        avg_delay_all_departure,
        case when avg_delay_late_arrival >= 0 then avg_delay_late_arrival end as avg_delay_late_arrival,
        -- below -15 min the values are corrupt (all in 2019-10..2020-02, down to -472)
        case when avg_delay_all_arrival >= -15 then avg_delay_all_arrival end as avg_delay_all_arrival,
        {% for col in causes.values() %}
        -- all-zero causes mean missing, not zero
        case when {{ causes.values() | join(' + ') }} > 0 then {{ col }} end as {{ col }},
        {% endfor %}
        arrival_comment
    from typed
)

select * from cleaned
