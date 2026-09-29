-- linked to fact_punctuality by punctuality_key only (no month/route key: avoids a Qlik synthetic key)
select
    {{ dbt_utils.generate_surrogate_key(['c.month_start', 'r.route_key']) }} as punctuality_key,
    c.cause_key,
    c.cause_share_pct,
    -- approximation: the shares' denominator is not published (docs/data_model.md)
    c.cause_share_pct / 100 * c.trains_late_arrival as est_late_trains
from {{ ref('int_tgv_delay_causes_unpivoted') }} as c
inner join {{ ref('int_tgv_routes') }} as r using (service, origin_station, destination_station)
