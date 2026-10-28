-- mart_forensic_matrix.sql
-- Production intelligence mart joining healed forensic records with manifest lineage
-- and reconstructing PostGIS GEOGRAPHY(POINT, 4326) pins for every healed row.

with intel as (
    select * from {{ ref('stg_forensic_intelligence') }}
),

manifest as (
    select * from {{ ref('stg_ingestion_manifest') }}
),

final as (
    select
        i.nara_id,
        i.case_group_id,
        i.record_granularity,
        m.source_archive,
        i.document_title,
        i.historical_era,
        i.craft_type,
        i.occupant_type,
        i.reported_speed_mph,
        i.sighting_duration,
        i.linguistic_stress_score,
        i.redaction_fingerprint,
        i.bureaucratic_routing_json,
        i.psychoactive_compounds_json,
        i.cognitive_target_coordinates,
        i.healed_latitude   as latitude,
        i.healed_longitude  as longitude,

        -- Reconstruct PostGIS Geography point using the window-healed coordinates
        case
            when i.healed_latitude is not null and i.healed_longitude is not null
            then st_setsrid(st_makepoint(i.healed_longitude, i.healed_latitude), 4326)::geography
        end as geom,

        i.transcript_char_length,
        i.pristine_transcript,
        i.embedding,
        m.processing_seconds,
        i.ingested_at
    from intel i
    left join manifest m on i.nara_id = m.nara_id
)

select * from final