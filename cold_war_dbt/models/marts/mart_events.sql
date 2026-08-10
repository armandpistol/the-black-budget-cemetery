with events as (
    select * from {{ ref('stg_documents') }}
),

programs as (
    select * from {{ ref('stg_programs') }}
),

raw_events as (
    select * from {{ source('raw', 'events') }}
),

final as (
    select
        e.event_id,
        e.event_type,
        e.event_date,
        e.location_name,
        e.latitude,
        e.longitude,
        e.location_type,
        e.observer_type,
        e.summary,
        p.program_name,
        p.lead_agency,
        d.source_file,
        d.source_agency,
        d.document_type,
        e.created_at
    from raw_events e
    left join programs p on e.program_id = p.program_id
    left join events d on e.document_id = d.document_id
)

select * from final