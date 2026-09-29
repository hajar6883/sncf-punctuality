{% set months_fr = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'] %}

with months as (
    select unnest(generate_series(min(month_start), max(month_start), interval 1 month))::date as month_start
    from {{ ref('stg_tgv_route_monthly') }}
)

select
    m.month_start,
    year(m.month_start) as year,
    month(m.month_start) as month,
    strftime(m.month_start, '%Y-%m') as year_month,
    ['{{ months_fr | join("', '") }}'][month(m.month_start)] as month_name_fr,
    'T' || quarter(m.month_start) as quarter,
    case
        when month(m.month_start) in (12, 1, 2) then 'Hiver'
        when month(m.month_start) in (3, 4, 5) then 'Printemps'
        when month(m.month_start) in (6, 7, 8) then 'Été'
        else 'Automne'
    end as season,
    d.disruption,
    (d.disruption is not null)::integer as is_disrupted
from months as m
left join {{ ref('disrupted_months') }} as d using (month_start)
