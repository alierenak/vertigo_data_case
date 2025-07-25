# Mobile Game Analytics - DBT Project

## Overview

This project creates a comprehensive data pipeline for mobile game analytics using DBT and Google BigQuery. It transforms raw user-level daily metrics into aggregated business intelligence suitable for reporting and decision-making.

## Dataset Description

**Source Data**: 7.3M rows of user-level daily metrics across 30 days (Feb 15 - Mar 15, 2024)
- **Platforms**: Android (~65%) and iOS (~35%)
- **Geographic Coverage**: 240+ countries, with Turkey, Brazil, and Russia as top markets
- **Metrics**: Sessions, gameplay, monetization, and technical performance indicators

### **Data Quality Assessment**
- **Completeness**: 99.75% country coverage (17,998 missing values filled with 'Unknown')
- **Reliability**: Server error rate 2.5% of sessions (~21K affected users daily)
- **Coverage**: All 17 data files successfully processed with consistent schema

## Architecture

```
Raw CSV Files (17 files, ~7.3M rows)
    ↓
Google BigQuery (raw_user_metrics table)
    ↓
DBT Staging Layer (data cleaning & quality checks)
    ↓
DBT Marts Layer (daily_metrics aggregation)
    ↓
Visualization Dashboard (Looker Studio)
```

## DBT Project Structure

```
dbt_project/
├── dbt_project.yml          # Project configuration
├── profiles.yml             # BigQuery connection settings
├── packages.yml            # dbt-utils dependency
├── models/
│   ├── sources.yml         # Raw data source definitions
│   ├── schema.yml         # Model documentation & tests
│   ├── staging/
│   │   └── stg_raw_user_metrics.sql  # Data cleaning & preparation
│   └── marts/
│       └── daily_metrics.sql         # Core business metrics aggregation
```

## Key Models

### 1. `stg_raw_user_metrics`
- **Purpose**: Data cleaning and quality preparation
- **Features**:
  - Handles missing country values (fills with 'Unknown')
  - Adds data quality flags for anomalies
  - Calculates user age and revenue categorization
  - Filters data to specified date range

### 2. `daily_metrics`
- **Purpose**: Core business metrics aggregated by date, country, platform
- **Key Fields**:
  - `dau`: Daily Active Users
  - `total_iap_revenue`: In-app purchase revenue
  - `total_ad_revenue`: Advertisement revenue  
  - `arpdau`: Average Revenue Per Daily Active User
  - `matches_started`: Total matches initiated
  - `match_per_dau`: Average matches per user
  - `win_ratio` / `defeat_ratio`: Game outcome ratios
  - `server_error_per_dau`: Technical performance metric

## Key Business Insights

### Revenue & Monetization
- **Total Revenue**: $1.08M over 30 days ($933K IAP, $146K Ad revenue)
- **Platform Economics**: iOS generates 2.4x higher ARPDAU ($0.24 vs $0.10) despite having 35% fewer users
- **Geographic Revenue Leaders**: USA dominates with 19.2% revenue share and $0.91 ARPDAU
- **Monetization Strategy**: IAP-focused (86% of revenue) with significant platform differences

### Market Segmentation 
- **Volume vs Premium Markets**: Turkey leads DAU (665K) but low monetization; USA/Germany show premium potential
- **Platform Distribution**: Android dominates user base (65%) but iOS drives premium revenue
- **Geographic Concentration**: Top 10 countries generate 85%+ of total revenue
- **Market Opportunities**: Clear premium markets (US, Germany) vs volume plays (Turkey, Brazil)

### User Engagement & Performance
- **Game Balance**: 61% win rate indicates healthy gameplay difficulty
- **Engagement Rate**: 4.7 matches per user on average
- **Technical Health**: 2.5% session error rate (~21K affected users daily)
- **Platform Engagement**: iOS users slightly more engaged (5.1 vs 4.5 matches/user)

### Strategic Implications
- **iOS Monetization**: Focus premium features and pricing on iOS markets
- **Geographic Strategy**: Scale volume in emerging markets, maximize revenue in premium markets  
- **Revenue Optimization**: Significant opportunity to improve Android monetization
- **Market Prioritization**: USA and Germany show highest revenue efficiency potential

## Setup Instructions

### Prerequisites
- Google Cloud Platform account with BigQuery enabled
- Service account key with BigQuery permissions
- Python environment with required packages

### 1. Data Loading
```bash
# Install dependencies
pip install google-cloud-bigquery pandas

# Set up authentication
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account-key.json"

# Load data to BigQuery
python load_data_to_bigquery.py
```

### 2. DBT Setup
```bash
# Install DBT
pip install dbt-bigquery

# Configure profiles.yml with your project details
# Update dbt_project/profiles.yml with your GCP project ID

cd dbt_project

# Install dependencies
dbt deps

# Run models
dbt run

# Run tests
dbt test
```

### 3. Dashboard Creation
Follow the `dashboard_setup_guide.md` to create visualizations in Looker Studio.

## Sample Output

Sample data is available in:
- `sample_daily_metrics_output.csv` (50 sample sorted by dau)

Example record:
```
event_date: 2024-02-15
country: Turkey  
platform: android
dau: 5420
total_iap_revenue: 1250.50
arpdau: 0.231
matches_started: 28750
win_ratio: 0.582
```

## Performance Considerations

### Optimization Opportunities
1. **Partitioning**: Partition `daily_metrics` by `event_date` for query performance
2. **Clustering**: Cluster by `country` and `platform` for regional analysis
3. **Incremental Models**: Convert to incremental refresh for production scale
4. **Cost Management**: Use `LIMIT` clauses during development

### Cost-Saving Strategies
- **Data Retention**: Archive raw data older than 90 days
- **Query Optimization**: Use column pruning and appropriate filters
- **Scheduled Runs**: Batch processing during off-peak hours
- **Materialization**: Balance between view and table materializations

## Incremental Modeling Ideas

For production deployment:
```sql
{{ config(
    materialized='incremental',
    unique_key=['event_date', 'country', 'platform'],
    on_schema_change='fail'
) }}

-- Add incremental logic
{% if is_incremental() %}
  WHERE event_date > (SELECT MAX(event_date) FROM {{ this }})
{% endif %}
```