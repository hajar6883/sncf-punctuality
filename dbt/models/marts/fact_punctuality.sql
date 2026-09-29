select
    {{ dbt_utils.generate_surrogate_key(['s.month_start', 'r.route_key']) }} as punctuality_key,
    s.month_start,
    r.route_key,
    s.trains_planned,
    s.trains_cancelled,
    s.trains_ran,
    s.trains_late_arrival,
    s.trains_ran - s.trains_late_arrival as trains_on_time,
    s.trains_late_15,
    s.trains_late_30,
    s.trains_late_60,
    s.trains_late_departure,
    -- totals (average x trains) so averages can be recomputed as Sum / Sum
    s.avg_delay_all_arrival * s.trains_ran as delay_minutes_all_arrival,
    s.avg_delay_late_arrival * s.trains_late_arrival as delay_minutes_late_arrival,
    s.avg_journey_minutes * s.trains_ran as journey_minutes,
    s.cause_external_pct is not null as has_cause_data,
    s.arrival_comment
from {{ ref('stg_tgv_route_monthly') }} as s
inner join {{ ref('int_tgv_routes') }} as r using (service, origin_station, destination_station)
