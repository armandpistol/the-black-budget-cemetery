-- stg_forensic_intelligence.sql
-- Unpacks Sector Alpha/Beta/Gamma JSONB structures and forward-fills missing coordinates
-- across multi-page archival documents using PostgreSQL window functions.

with source as (
    select * from {{ source('raw', 'forensic_intelligence') }}
    where nara_id != 'NARA-595466-09204-001'
),

grouped as (
    select
        nara_id,
        -- Group multi-page scans (e.g. NARA-595466-09257-2005-001-A..004-A -> NARA-595466-09257-2005)
        -- so continuation pages inherit header metadata from Page 1 of the same document
        regexp_replace(nara_id, '-[0-9]{3}-[A-Z]$', '') as case_group_id,
        case
            when nara_id ~ '-[0-9]{3}-[A-Z]$' then 'MICROFILM_PAGE_JPG'
            else 'COMPILED_CASE_PDF'
        end as record_granularity,
        trim(document_title)        as document_title,
        trim(pristine_transcript)   as pristine_transcript,
        length(trim(pristine_transcript)) as transcript_char_length,

        -- Scalar & JSONB unpacked fields (Sector Alpha)
        nullif(lower(trim(craft_type)), 'unknown') as raw_craft_type,
        -- Clean human observer titles out of craft occupant_type
         case
            when lower(sector_alpha->>'occupant_type') in ('unknown', 'pilot', 'witness role', 'none', '')
            then 'none observed'
            else sector_alpha->>'occupant_type'
         end as occupant_type,
        sector_alpha->'telemetry_matrix'->>'speed_mph' as reported_speed_mph,
        coalesce(
            sector_alpha->'telemetry_matrix'->>'total_sighting_duration',
            sector_alpha->'telemetry_matrix'->>'duration'
        ) as sighting_duration,
        latitude,
        longitude,

        -- Sector Beta JSONB unpacking
        sector_beta->>'cognitive_target_coordinates' as cognitive_target_coordinates,
        sector_beta->'psychoactive_compounds'        as psychoactive_compounds_json,
        linguistic_stress_score,

        -- Sector Gamma JSONB unpacking
        sector_gamma->'bureaucratic_routing'         as bureaucratic_routing_json,
        lower(trim(redaction_fingerprint))           as redaction_fingerprint,
        trim(historical_era)                         as historical_era,

        embedding,
        ingested_at
    from source
),

healed as (
    select
        *,
        -- Heal 'unknown' craft_type on administrative continuation pages using the case group or fallback
        coalesce(
            raw_craft_type,
            max(raw_craft_type) over (partition by case_group_id),
            'radar / administrative memo'
        ) as craft_type,

       -- Window Forward-Fill: Continuation pages inherit Page 1 coordinates;
        -- National HQ assessments without a field city default to Pentagon/ODNI HQ (38.8719, -77.0563)
        coalesce(
            latitude,
            max(latitude) over (partition by case_group_id),
            38.8719
        ) as healed_latitude,
        coalesce(
            longitude,
            max(longitude) over (partition by case_group_id),
            -77.0563
        ) as healed_longitude
    from grouped
)

select * from healed