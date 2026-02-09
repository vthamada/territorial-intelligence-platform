with ranked as (
    select
        fi.territory_id,
        fi.source,
        fi.dataset,
        fi.indicator_code,
        fi.indicator_name,
        fi.unit,
        fi.category,
        fi.reference_period,
        fi.value,
        row_number() over (
            partition by fi.territory_id, fi.source, fi.dataset, fi.indicator_code, coalesce(fi.category, '')
            order by fi.reference_period desc
        ) as rn
    from silver.fact_indicator fi
)
select
    territory_id,
    source,
    dataset,
    indicator_code,
    indicator_name,
    unit,
    category,
    reference_period,
    value
from ranked
where rn = 1
