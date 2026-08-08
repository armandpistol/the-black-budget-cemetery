with source as (
    select * from {{ source('raw', 'programs') }}
),

cleaned as (
    select
        program_id,
        trim(program_name)              as program_name,
        trim(lead_agency)               as lead_agency,
        start_year,
        end_year,
        (end_year - start_year)         as program_duration_years,
        trim(description)               as description
    from source
)

select * from cleaned