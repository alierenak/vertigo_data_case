/*
  Mobile Game Analytics - Daily Metrics Model
  
  Aggregates user-level daily metrics by date, country, and platform
  Produces business KPIs for dashboard consumption
*/
{{
  config(
    materialized='table',
    description='Daily aggregated metrics for mobile game analytics by date, country, and platform'
  )
}}

with daily_aggregation as (
  select 
    event_date,
    country,
    platform,
    
    -- User metrics
    count(distinct user_id) as dau,
    
    -- Revenue metrics
    sum(iap_revenue) as total_iap_revenue,
    sum(ad_revenue) as total_ad_revenue,
    
    -- Game metrics
    sum(match_start_count) as matches_started,
    sum(match_end_count) as total_match_ends,
    sum(victory_count) as total_victories,
    sum(defeat_count) as total_defeats,
    
    -- Technical metrics
    sum(server_connection_error) as total_server_errors,
    
    -- Session metrics
    sum(total_session_count) as total_sessions,
    sum(total_session_duration) as total_session_duration
    
  from {{ ref('stg_raw_user_metrics') }}
  group by 1, 2, 3
),

final_metrics as (
  select 
    event_date,
    country,
    platform,
    dau,
    total_iap_revenue,
    total_ad_revenue,
    
    -- ARPDAU (Average Revenue Per Daily Active User)
    round(
      safe_divide(total_iap_revenue + total_ad_revenue, dau), 
      4
    ) as arpdau,
    
    matches_started,
    
    -- Match per DAU
    round(
      safe_divide(matches_started, dau), 
      2
    ) as match_per_dau,
    
    -- Win ratio (victories / total match ends)
    round(
      safe_divide(total_victories, nullif(total_match_ends, 0)), 
      4
    ) as win_ratio,
    
    -- Defeat ratio (defeats / total match ends)
    round(
      safe_divide(total_defeats, nullif(total_match_ends, 0)), 
      4
    ) as defeat_ratio,
    
    -- Server error per DAU
    round(
      safe_divide(total_server_errors, dau), 
      4
    ) as server_error_per_dau,
    
    -- Additional useful metrics
    -- Convert from seconds to minutes (duration is stored in seconds)
    round(
      safe_divide(total_session_duration / 60.0, nullif(total_sessions, 0)), 
      2
    ) as avg_session_duration_minutes,
    
    round(
      safe_divide(total_sessions, dau), 
      2
    ) as sessions_per_user

  from daily_aggregation
  where dau > 0  -- Only include days with active users
)

select 
  -- Dimensions (keep as is)
  event_date,
  country,
  platform,
  
  -- Explicitly cast all numeric fields as proper types for BI tools
  cast(dau as int64) as dau,
  cast(total_iap_revenue as float64) as total_iap_revenue,
  cast(total_ad_revenue as float64) as total_ad_revenue,
  cast(arpdau as float64) as arpdau,
  cast(matches_started as int64) as matches_started,
  cast(match_per_dau as float64) as match_per_dau,
  cast(win_ratio as float64) as win_ratio,
  cast(defeat_ratio as float64) as defeat_ratio,
  cast(server_error_per_dau as float64) as server_error_per_dau,
  cast(avg_session_duration_minutes as float64) as avg_session_duration_minutes,
  cast(sessions_per_user as float64) as sessions_per_user
from final_metrics
order by event_date, country, platform