{{
  config(
    materialized='view'
  )
}}

with source_data as (
  select 
    user_id,
    event_date,
    platform,
    install_date,
    coalesce(country, 'Unknown') as country,
    total_session_count,
    total_session_duration,
    match_start_count,
    match_end_count,
    victory_count,
    defeat_count,
    server_connection_error,
    iap_revenue,
    ad_revenue
  from {{ source('raw', 'raw_user_metrics') }}
),

cleaned_data as (
  select 
    *,
    -- Data quality flags
    case 
      when total_session_count = 0 and total_session_duration > 0 then 'session_duration_without_sessions'
      when match_start_count < match_end_count then 'more_ends_than_starts'
      when victory_count + defeat_count > match_end_count then 'outcome_count_mismatch'
      else null
    end as data_quality_flag,
    
    -- Calculate user age in days
    date_diff(event_date, install_date, day) as user_age_days,
    
    -- Revenue categories
    case 
      when iap_revenue > 0 and ad_revenue > 0 then 'both'
      when iap_revenue > 0 then 'iap_only'
      when ad_revenue > 0 then 'ad_only'
      else 'no_revenue'
    end as revenue_type

  from source_data
  where event_date >= '{{ var("start_date") }}'
    and event_date <= '{{ var("end_date") }}'
)

select * from cleaned_data