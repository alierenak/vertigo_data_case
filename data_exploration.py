#!/usr/bin/env python3
"""
Data exploration script for mobile gaming metrics dataset
"""
import pandas as pd
import numpy as np
import glob
import gzip
import os
from pathlib import Path

def load_all_data():
    """Load and combine all CSV.gz files from the data directory"""
    data_path = "data/data_analyst_case_revised_april/"
    csv_files = glob.glob(os.path.join(data_path, "*.csv.gz"))
    
    print(f"Found {len(csv_files)} CSV files to process")
    
    dfs = []
    for file in csv_files:
        print(f"Loading {file}...")
        df = pd.read_csv(file, compression='gzip')
        dfs.append(df)
    
    combined_df = pd.concat(dfs, ignore_index=True)
    print(f"Combined dataset shape: {combined_df.shape}")
    return combined_df

def explore_data(df):
    """Perform comprehensive data exploration"""
    print("\n=== DATA EXPLORATION REPORT ===")
    
    # Basic info
    print(f"\nDataset shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    
    # Data types
    print(f"\nData types:")
    print(df.dtypes)
    
    # Missing values
    print(f"\nMissing values:")
    missing_counts = df.isnull().sum()
    missing_pct = (missing_counts / len(df) * 100).round(2)
    missing_df = pd.DataFrame({
        'missing_count': missing_counts,
        'missing_pct': missing_pct
    })
    print(missing_df[missing_df.missing_count > 0])
    
    # Date range
    df['event_date'] = pd.to_datetime(df['event_date'])
    df['install_date'] = pd.to_datetime(df['install_date'])
    print(f"\nDate range:")
    print(f"Event dates: {df['event_date'].min()} to {df['event_date'].max()}")
    print(f"Install dates: {df['install_date'].min()} to {df['install_date'].max()}")
    
    # Platform and country distribution
    print(f"\nPlatform distribution:")
    print(df['platform'].value_counts())
    
    print(f"\nCountry distribution (top 10):")
    print(df['country'].value_counts().head(10))
    
    # Revenue statistics
    print(f"\nRevenue statistics:")
    print(f"IAP Revenue - Mean: {df['iap_revenue'].mean():.2f}, Max: {df['iap_revenue'].max():.2f}")
    print(f"Ad Revenue - Mean: {df['ad_revenue'].mean():.2f}, Max: {df['ad_revenue'].max():.2f}")
    
    # Game metrics
    print(f"\nGame metrics summary:")
    game_cols = ['total_session_count', 'total_session_duration', 'match_start_count', 
                 'match_end_count', 'victory_count', 'defeat_count', 'server_connection_error']
    print(df[game_cols].describe())
    
    return df

def create_sample_daily_metrics(df):
    """Create sample aggregated daily metrics"""
    print("\n=== CREATING SAMPLE DAILY METRICS ===")
    
    # Group by event_date, country, platform
    daily_metrics = df.groupby(['event_date', 'country', 'platform']).agg({
        'user_id': 'nunique',  # DAU
        'iap_revenue': 'sum',
        'ad_revenue': 'sum',
        'match_start_count': 'sum',
        'match_end_count': 'sum',
        'victory_count': 'sum',
        'defeat_count': 'sum',
        'server_connection_error': 'sum'
    }).reset_index()
    
    # Rename columns
    daily_metrics.rename(columns={
        'user_id': 'dau'
    }, inplace=True)
    
    # Calculate derived metrics
    daily_metrics['total_iap_revenue'] = daily_metrics['iap_revenue']
    daily_metrics['total_ad_revenue'] = daily_metrics['ad_revenue']
    daily_metrics['arpdau'] = (daily_metrics['iap_revenue'] + daily_metrics['ad_revenue']) / daily_metrics['dau']
    daily_metrics['matches_started'] = daily_metrics['match_start_count']
    daily_metrics['match_per_dau'] = daily_metrics['match_start_count'] / daily_metrics['dau']
    daily_metrics['win_ratio'] = np.where(daily_metrics['match_end_count'] > 0, 
                                         daily_metrics['victory_count'] / daily_metrics['match_end_count'], 0)
    daily_metrics['defeat_ratio'] = np.where(daily_metrics['match_end_count'] > 0,
                                           daily_metrics['defeat_count'] / daily_metrics['match_end_count'], 0)
    daily_metrics['server_error_per_dau'] = daily_metrics['server_connection_error'] / daily_metrics['dau']
    
    # Select final columns
    final_cols = ['event_date', 'country', 'platform', 'dau', 'total_iap_revenue', 'total_ad_revenue',
                  'arpdau', 'matches_started', 'match_per_dau', 'win_ratio', 'defeat_ratio', 'server_error_per_dau']
    daily_metrics_final = daily_metrics[final_cols]
    
    print(f"Daily metrics shape: {daily_metrics_final.shape}")
    print(f"Sample data:")
    print(daily_metrics_final.head(10))
    
    # Save sample output
    daily_metrics_final.to_csv('sample_daily_metrics.csv', index=False)
    print(f"\nSaved sample data to sample_daily_metrics.csv")
    
    return daily_metrics_final

if __name__ == "__main__":
    # Load and explore data
    df = load_all_data()
    df_clean = explore_data(df)
    
    # Create sample daily metrics
    daily_metrics = create_sample_daily_metrics(df_clean)