#!/usr/bin/env python3
"""
Export sample data from BigQuery daily_metrics table for deliverable
"""
from google.cloud import bigquery
import pandas as pd
import os

def export_sample_data():
    """Export sample daily_metrics data to CSV"""
    
    # Initialize BigQuery client
    client = bigquery.Client()
    
    # Query to get representative sample
    query = """
    SELECT 
        event_date,
        country,
        platform,
        dau,
        total_iap_revenue,
        total_ad_revenue,
        arpdau,
        matches_started,
        match_per_dau,
        win_ratio,
        defeat_ratio,
        server_error_per_dau,
        avg_session_duration_minutes,
        sessions_per_user
    FROM `elated-badge-466312-p3.mobile_analytics_prod.daily_metrics`
    WHERE dau >= 1000  -- Focus on significant markets
    ORDER BY 
        event_date,
        total_iap_revenue + total_ad_revenue DESC
    LIMIT 50
    """
    
    print("Exporting sample data from BigQuery...")
    
    # Execute query and convert to DataFrame
    df = client.query(query).to_dataframe()
    
    # Export to CSV
    output_file = 'sample_daily_metrics_output.csv'
    df.to_csv(output_file, index=False)
    
    print(f"✅ Exported {len(df)} rows to {output_file}")
    
    # Show summary statistics
    print(f"\n📊 Sample Data Summary:")
    print(f"Date Range: {df['event_date'].min()} to {df['event_date'].max()}")
    print(f"Countries: {df['country'].nunique()} unique countries")
    print(f"Total Revenue: ${(df['total_iap_revenue'] + df['total_ad_revenue']).sum():,.2f}")
    print(f"Total DAU: {df['dau'].sum():,}")
    
    # Show first few rows
    print(f"\n📋 Sample Records:")
    print(df.head(10).to_string(index=False))
    
    return df

if __name__ == "__main__":
    # Set credentials if needed
    if 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ:
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './dbt-key.json'
    
    export_sample_data()