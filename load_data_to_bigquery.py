#!/usr/bin/env python3
"""
Load raw CSV data into BigQuery for DBT processing
"""
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
import pandas as pd
import glob
import os
from pathlib import Path

def setup_bigquery_client():
    """Initialize BigQuery client"""
    # You'll need to set GOOGLE_APPLICATION_CREDENTIALS environment variable
    # or pass the service account key file path
    client = bigquery.Client()
    return client

def create_dataset_if_not_exists(client, project_id, dataset_id):
    """Create BigQuery dataset if it doesn't exist"""
    dataset_ref = f"{project_id}.{dataset_id}"
    
    try:
        client.get_dataset(dataset_ref)
        print(f"Dataset {dataset_ref} already exists")
    except NotFound:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "US"  # Choose appropriate location
        dataset = client.create_dataset(dataset, timeout=30)
        print(f"Created dataset {dataset_ref}")

def load_raw_data_to_bigquery(project_id, dataset_id="mobile_analytics_dev"):
    """Load all CSV files into BigQuery"""
    
    client = setup_bigquery_client()
    
    # Create dataset if needed
    create_dataset_if_not_exists(client, project_id, dataset_id)
    
    # Get all CSV files
    data_path = "data/data_analyst_case_revised_april/"
    csv_files = glob.glob(os.path.join(data_path, "*.csv.gz"))
    
    print(f"Found {len(csv_files)} CSV files to load into BigQuery")
    
    # Define table schema
    schema = [
        bigquery.SchemaField("user_id", "STRING"),
        bigquery.SchemaField("event_date", "DATE"),
        bigquery.SchemaField("platform", "STRING"),
        bigquery.SchemaField("install_date", "DATE"),
        bigquery.SchemaField("country", "STRING"),
        bigquery.SchemaField("total_session_count", "INTEGER"),
        bigquery.SchemaField("total_session_duration", "FLOAT"),
        bigquery.SchemaField("match_start_count", "INTEGER"),
        bigquery.SchemaField("match_end_count", "INTEGER"),
        bigquery.SchemaField("victory_count", "INTEGER"),
        bigquery.SchemaField("defeat_count", "INTEGER"),
        bigquery.SchemaField("server_connection_error", "INTEGER"),
        bigquery.SchemaField("iap_revenue", "FLOAT"),
        bigquery.SchemaField("ad_revenue", "FLOAT"),
    ]
    
    table_id = f"{project_id}.{dataset_id}.raw_user_metrics"
    
    # Create or replace table
    table = bigquery.Table(table_id, schema=schema)
    
    # Configure job
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        skip_leading_rows=1,  # Skip header row
        source_format=bigquery.SourceFormat.CSV,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,  # Replace table
    )
    
    # Load data in batches
    all_dfs = []
    for i, file in enumerate(csv_files):
        print(f"Reading {file} ({i+1}/{len(csv_files)})")
        df = pd.read_csv(file, compression='gzip')
        
        # Clean data: handle missing countries
        df['country'] = df['country'].fillna('Unknown')
        
        # Ensure date columns are properly formatted
        df['event_date'] = pd.to_datetime(df['event_date']).dt.date
        df['install_date'] = pd.to_datetime(df['install_date']).dt.date
        
        all_dfs.append(df)
    
    # Combine all dataframes
    combined_df = pd.concat(all_dfs, ignore_index=True)
    print(f"Combined dataset shape: {combined_df.shape}")
    
    # Upload to BigQuery
    print(f"Uploading data to {table_id}...")
    job = client.load_table_from_dataframe(combined_df, table, job_config=job_config)
    job.result()  # Wait for job to complete
    
    # Verify upload
    table = client.get_table(table_id)
    print(f"Loaded {table.num_rows} rows to {table_id}")
    
    # Sample query to verify data
    query = f"""
    SELECT 
        event_date,
        platform,
        country,
        COUNT(*) as row_count,
        SUM(iap_revenue) as total_iap,
        SUM(ad_revenue) as total_ad
    FROM `{table_id}`
    WHERE event_date >= '2024-02-15'
    GROUP BY event_date, platform, country
    ORDER BY event_date, platform, country
    LIMIT 10
    """
    
    query_job = client.query(query)
    results = query_job.result()
    
    print("\nSample aggregated data from BigQuery:")
    for row in results:
        print(f"{row.event_date} | {row.platform} | {row.country} | {row.row_count} rows | IAP: ${row.total_iap:.2f} | Ad: ${row.total_ad:.2f}")

def main():
    """Main function with instructions"""
    print("BigQuery Data Loading Script")
    print("=" * 40)
    print()
    print("Before running this script, make sure you have:")
    print("1. A Google Cloud Project with BigQuery API enabled")
    print("2. Service account key file with BigQuery permissions")
    print("3. Set GOOGLE_APPLICATION_CREDENTIALS environment variable")
    print("4. Install required packages: pip install google-cloud-bigquery pandas")
    print()
    
    # Example usage - replace with your project ID
    project_id = input("Enter your GCP Project ID: ").strip()
    if project_id:
        try:
            load_raw_data_to_bigquery(project_id)
            print("\nData loading completed successfully!")
        except Exception as e:
            print(f"Error loading data: {e}")
            print("\nTroubleshooting tips:")
            print("- Ensure you have BigQuery permissions")
            print("- Check your service account key file path")
            print("- Verify GOOGLE_APPLICATION_CREDENTIALS is set")
    else:
        print("Project ID is required. Please run the script again.")

if __name__ == "__main__":
    main()