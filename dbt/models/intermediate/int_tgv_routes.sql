select
    {{ dbt_utils.generate_surrogate_key(['service', 'origin_station', 'destination_station']) }} as route_key,
    service,
    origin_station,
    destination_station,
    min(month_start) as first_month,
    max(month_start) as last_month,
    count(*) as months_available
from {{ ref('stg_tgv_route_monthly') }}
group by all
