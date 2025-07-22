# Dashboard Setup Guide

## Overview
This guide helps you create a visualization dashboard for the mobile game analytics data using free BI tools.

## Recommended Tools
1. **Google Looker Studio** (Free, integrates well with BigQuery)
2. **Tableau Public** (Free, powerful visualizations)
3. **Metabase** (Open source, self-hosted)

## Dashboard Setup with Google Looker Studio

### Prerequisites
- BigQuery dataset loaded with daily_metrics table
- Google account with access to Looker Studio

### Steps

1. **Connect to BigQuery**
   - Go to [datastudio.google.com](https://datastudio.google.com)
   - Create new report
   - Add data source → BigQuery
   - Select your project → dataset → daily_metrics table

2. **Key Charts to Create**

   **Chart 1: Daily Active Users Trend**
   - Type: Time Series Line Chart
   - Date Dimension: event_date
   - Metric: SUM(dau)
   - Breakdown: platform

   **Chart 2: Revenue Overview**
   - Type: Combo Chart
   - Date Dimension: event_date  
   - Metrics: SUM(total_iap_revenue), SUM(total_ad_revenue)
   - Right Y-axis: AVG(arpdau)

   **Chart 3: Platform Comparison**
   - Type: Bar Chart
   - Dimension: platform
   - Metrics: SUM(dau), SUM(total_iap_revenue + total_ad_revenue)

   **Chart 4: Top Countries**
   - Type: Geo Map or Table
   - Dimension: country
   - Metric: SUM(dau)
   - Sort: Descending by DAU

   **Chart 5: Game Engagement**
   - Type: Scatter Plot
   - X-axis: match_per_dau
   - Y-axis: avg_session_duration_minutes
   - Size: dau
   - Color: platform

   **Chart 6: Win/Loss Ratios**
   - Type: Stacked Bar Chart
   - Dimension: country (top 10)
   - Metrics: AVG(win_ratio), AVG(defeat_ratio)

3. **Key Filters**
   - Date range picker
   - Platform selector (android/ios)
   - Country multi-select

4. **Key Performance Indicators (Cards)**
   - Total DAU: SUM(dau)
   - Total Revenue: SUM(total_iap_revenue + total_ad_revenue)
   - Average ARPDAU: AVG(arpdau)
   - Total Matches: SUM(matches_started)

## Sample Dashboard Data

Use the file `sample_daily_metrics_for_dashboard.csv` for initial dashboard creation if BigQuery is not yet set up.

## Dashboard URL Template

Once created, your Looker Studio dashboard URL will look like:
```
https://datastudio.google.com/reporting/[REPORT_ID]/page/[PAGE_ID]
```

Make sure to set sharing permissions to "Anyone with the link can view" for demo purposes.

## Expected Insights

Your dashboard should reveal:
- **Platform Performance**: Android has higher DAU but iOS generates more revenue per user
- **Geographic Distribution**: Turkey is the top market by DAU, followed by Brazil and Russia
- **Revenue Patterns**: Weekend vs weekday performance differences
- **Engagement Metrics**: Correlation between matches played and session duration
- **Technical Issues**: Server error patterns by region/platform

## Next Steps

1. Set up BigQuery connection
2. Load data using `load_data_to_bigquery.py`
3. Create Looker Studio dashboard
4. Share dashboard link for review