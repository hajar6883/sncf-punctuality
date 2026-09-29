select
    r.route_key,
    r.service,
    r.origin_station,
    r.destination_station,
    r.origin_station || ' → ' || r.destination_station as route_label,
    -- same pair in both directions, to combine outbound and return
    least(r.origin_station, r.destination_station) || ' ↔ ' || greatest(r.origin_station, r.destination_station) as route_pair,
    coalesce(fo.country, 'France') as origin_country,
    coalesce(fd.country, 'France') as destination_country,
    r.origin_station like 'PARIS %' or r.destination_station like 'PARIS %' as touches_paris,
    r.first_month,
    r.last_month,
    r.months_available
from {{ ref('int_tgv_routes') }} as r
left join {{ ref('foreign_stations') }} as fo on fo.station = r.origin_station
left join {{ ref('foreign_stations') }} as fd on fd.station = r.destination_station
