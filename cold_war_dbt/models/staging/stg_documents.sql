with source as (
    select * from {{ source('raw', 'documents') }}
),

cleaned as (
    select
        document_id,
        program_id,
        source_file,
        source_agency,
        document_type,
        trim(raw_text)                    as raw_text,
        length(trim(raw_text))       as text_length,
        page_count,
        metadata,
        ingested_at
    from source
    where raw_text is not null
      and trim(raw_text) != ''
)

select * from cleaned