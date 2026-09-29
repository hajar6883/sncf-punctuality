-- one row per (route, month, cause); rows without cause data are dropped
with unpivoted as (
    unpivot {{ ref('stg_tgv_route_monthly') }}
    on cause_external_pct, cause_infrastructure_pct, cause_traffic_management_pct,
       cause_rolling_stock_pct, cause_station_management_pct, cause_passenger_handling_pct
    into name source_column value cause_share_pct
)

select
    u.month_start,
    u.service,
    u.origin_station,
    u.destination_station,
    c.cause_key,
    u.cause_share_pct,
    u.trains_late_arrival
from unpivoted as u
inner join {{ ref('delay_causes') }} as c using (source_column)
