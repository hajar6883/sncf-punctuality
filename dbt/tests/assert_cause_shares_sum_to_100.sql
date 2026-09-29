-- 5 known rows (2026-06) sum to 84-99: warn on those, fail if more appear
{{ config(warn_if='>0', error_if='>5') }}

select punctuality_key, sum(cause_share_pct) as total
from {{ ref('fact_delay_cause') }}
group by 1
having abs(total - 100) > 0.5
