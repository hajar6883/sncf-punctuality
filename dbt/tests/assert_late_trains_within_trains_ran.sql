-- Rate = 1 - Sum(late) / Sum(ran): a late train must never exist without a matching trains_ran
select *
from {{ ref('stg_tgv_route_monthly') }}
where trains_late_arrival > coalesce(trains_ran, 0)
