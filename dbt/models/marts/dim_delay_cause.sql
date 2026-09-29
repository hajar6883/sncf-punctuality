select cause_key, cause_label_fr, cause_label_en, sort_order
from {{ ref('delay_causes') }}
