# GCP Deployment Guide for Mobile Analytics DBT Project

## Overview
This guide walks you through deploying the mobile analytics DBT project to Google Cloud Platform with production-ready configurations.

## Prerequisites
- Google Cloud Platform account
- `gcloud` CLI installed and configured
- Docker installed (for Cloud Run deployment)
- Git repository set up

## Step 1: GCP Project Setup

### 1.1 Create and Configure GCP Project
```bash
# Create new project
gcloud projects create mobile-analytics-prod --name="Mobile Analytics"

# Set as default project
gcloud config set project mobile-analytics-prod

# Enable required APIs
gcloud services enable bigquery.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable scheduler.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

### 1.2 Set Up Service Account
```bash
# Create service account for DBT
gcloud iam service-accounts create dbt-runner \
    --display-name="DBT Runner Service Account"

# Grant necessary permissions
gcloud projects add-iam-policy-binding mobile-analytics-prod \
    --member="serviceAccount:dbt-runner@mobile-analytics-prod.iam.gserviceaccount.com" \
    --role="roles/bigquery.admin"

gcloud projects add-iam-policy-binding mobile-analytics-prod \
    --member="serviceAccount:dbt-runner@mobile-analytics-prod.iam.gserviceaccount.com" \
    --role="roles/bigquery.dataEditor"

gcloud projects add-iam-policy-binding mobile-analytics-prod \
    --member="serviceAccount:dbt-runner@mobile-analytics-prod.iam.gserviceaccount.com" \
    --role="roles/bigquery.jobUser"

# Create and download service account key
gcloud iam service-accounts keys create dbt-service-account-key.json \
    --iam-account=dbt-runner@mobile-analytics-prod.iam.gserviceaccount.com
```

## Step 2: BigQuery Setup

### 2.1 Create Datasets
```bash
# Create datasets for different environments
bq mk --location=US mobile_analytics_dev
bq mk --location=US mobile_analytics_staging  
bq mk --location=US mobile_analytics_prod
```

### 2.2 Load Raw Data
```bash
# Upload your service account key
export GOOGLE_APPLICATION_CREDENTIALS="./dbt-service-account-key.json"

# Run data loading script
python load_data_to_bigquery.py
```

## Step 3: DBT Configuration Updates

### 3.1 Update profiles.yml for Production
```yaml
mobile_game_analytics:
  outputs:
    dev:
      type: bigquery
      method: service-account
      project: mobile-analytics-prod
      dataset: mobile_analytics_dev
      threads: 4
      timeout_seconds: 300
      location: US
      keyfile: "{{ env_var('DBT_BIGQUERY_KEYFILE') }}"
    staging:
      type: bigquery
      method: service-account
      project: mobile-analytics-prod
      dataset: mobile_analytics_staging
      threads: 4
      timeout_seconds: 300
      location: US
      keyfile: "{{ env_var('DBT_BIGQUERY_KEYFILE') }}"
    prod:
      type: bigquery
      method: service-account
      project: mobile-analytics-prod
      dataset: mobile_analytics_prod
      threads: 8
      timeout_seconds: 600
      location: US
      keyfile: "{{ env_var('DBT_BIGQUERY_KEYFILE') }}"
  target: dev
```

## Step 4: Containerized DBT Deployment

### 4.1 Create Dockerfile
See `Dockerfile` in project root.

### 4.2 Build and Deploy to Cloud Run
```bash
# Build container
gcloud builds submit --tag gcr.io/mobile-analytics-prod/dbt-runner

# Deploy to Cloud Run
gcloud run deploy dbt-runner \
    --image gcr.io/mobile-analytics-prod/dbt-runner \
    --platform managed \
    --region us-central1 \
    --memory 2Gi \
    --cpu 2 \
    --timeout 3600 \
    --service-account dbt-runner@mobile-analytics-prod.iam.gserviceaccount.com \
    --set-env-vars DBT_PROFILES_DIR=/app/dbt_project \
    --no-allow-unauthenticated
```

## Step 5: Automated Scheduling

### 5.1 Create Cloud Scheduler Jobs
```bash
# Daily production run at 6 AM UTC
gcloud scheduler jobs create http daily-dbt-run \
    --schedule="0 6 * * *" \
    --uri="https://dbt-runner-[HASH]-uc.a.run.app/run/prod" \
    --http-method=POST \
    --oidc-service-account-email=dbt-runner@mobile-analytics-prod.iam.gserviceaccount.com

# Hourly staging runs during business hours  
gcloud scheduler jobs create http hourly-dbt-staging \
    --schedule="0 9-17 * * 1-5" \
    --uri="https://dbt-runner-[HASH]-uc.a.run.app/run/staging" \
    --http-method=POST \
    --oidc-service-account-email=dbt-runner@mobile-analytics-prod.iam.gserviceaccount.com
```

## Step 6: Monitoring and Alerting

### 6.1 Set up Cloud Monitoring
```bash
# Create notification channel (Slack/Email)
gcloud alpha monitoring channels create \
    --display-name="DBT Alerts" \
    --type=slack \
    --channel-labels=url=YOUR_SLACK_WEBHOOK

# Create alerting policy for DBT failures
# See monitoring-config.yaml for details
```

## Step 7: GitHub Actions CI/CD

### 7.1 Set up Repository Secrets
In GitHub repository settings, add these secrets:
- `GCP_PROJECT_ID`: mobile-analytics-prod
- `GCP_SA_KEY`: Contents of dbt-service-account-key.json
- `DBT_PROFILES_DIR`: /github/workspace/dbt_project

### 7.2 GitHub Actions Workflow
See `.github/workflows/dbt-deploy.yml`

## Step 8: Environment Management

### 8.1 Development Workflow
```bash
# Local development
export DBT_PROFILES_DIR="./dbt_project"
export GOOGLE_APPLICATION_CREDENTIALS="./dbt-service-account-key.json"
cd dbt_project

# Run against dev environment
dbt run --target dev
dbt test --target dev
```

### 8.2 Staging Deployment
```bash
# Deploy to staging on feature branch
git push origin feature-branch
# GitHub Actions automatically runs DBT against staging
```

### 8.3 Production Deployment  
```bash
# Deploy to production on main branch
git push origin main
# GitHub Actions runs full test suite then deploys to prod
```

## Step 9: Data Quality Monitoring

### 9.1 DBT Test Results to BigQuery
Set up automated test result logging for monitoring dashboard.

### 9.2 Alerting on Data Issues
Configure alerts for:
- DBT test failures
- Data freshness issues  
- Unexpected data volume changes
- Query performance degradation

## Cost Optimization Tips

1. **Query Optimization**
   - Use partitioned tables for time-series data
   - Implement column pruning
   - Add appropriate clustering

2. **Scheduling**
   - Run heavy transformations during off-peak hours
   - Use incremental models for large tables
   - Implement smart refresh logic

3. **Resource Management**
   - Right-size Cloud Run instances
   - Use preemptible instances where possible
   - Monitor BigQuery slot usage

## Security Considerations

1. **Service Account Permissions**
   - Follow principle of least privilege
   - Rotate service account keys regularly
   - Use Workload Identity where possible

2. **Data Access**
   - Implement row-level security in BigQuery
   - Use authorized views for sensitive data
   - Set up audit logging

3. **Secrets Management**
   - Store credentials in Secret Manager
   - Never commit keys to version control
   - Use environment-specific configurations

## Disaster Recovery

1. **Backup Strategy**
   - BigQuery automatic backups (7 days)
   - Export critical datasets to Cloud Storage
   - Document recovery procedures

2. **Multi-region Setup**
   - Consider cross-region dataset replication
   - Set up failover mechanisms
   - Test recovery procedures regularly

## Next Steps

1. Deploy using this guide
2. Set up monitoring dashboards  
3. Configure alerting rules
4. Test disaster recovery procedures
5. Optimize performance and costs
6. Scale to additional data sources

## Troubleshooting

Common issues and solutions:
- **Permission errors**: Check service account roles
- **Timeout issues**: Increase Cloud Run timeout/memory
- **DBT failures**: Check logs in Cloud Run console
- **Data quality**: Review DBT test results in BigQuery