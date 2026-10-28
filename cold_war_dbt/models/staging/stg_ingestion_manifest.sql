-- stg_ingestion_manifest.sql
-- Cleans and standardizes pipeline lineage tracking from raw.ingestion_manifest

with source as (
    select * from {{ source('raw', 'ingestion_manifest') }}
),

cleaned as (
    select
        nara_id,
        trim(source_archive)        as source_archive,
        trim(source_path_or_url)    as source_path_or_url,
        upper(ingestion_status)     as ingestion_status,
        discovered_at,
        processed_at,
        -- Calculate extraction turnaround duration in seconds for pipeline monitoring
        extract(epoch from (processed_at - discovered_at))::numeric(10, 2) as processing_seconds,
        error_log
    from source
    -- Exclude our initial single-file smoke test ID that was superseded by the 8-file batch
    where nara_id != 'NARA-595466-09204-001'
)

select * from cleaned