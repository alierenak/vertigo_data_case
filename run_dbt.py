#!/usr/bin/env python3
"""
Cloud Run service for running DBT models with monitoring and error handling
"""
import os
import json
import logging
import subprocess
from datetime import datetime
from flask import Flask, request, jsonify
from google.cloud import secretmanager
from google.cloud import monitoring_v3
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

app = Flask(__name__)

class DBTRunner:
    def __init__(self):
        self.project_id = os.getenv('GCP_PROJECT_ID', 'mobile-analytics-prod')
        self.dbt_project_dir = '/app/dbt_project'
        
    def run_dbt_command(self, command, target='prod'):
        """Execute DBT command with proper error handling and logging"""
        full_command = f"dbt {command} --target {target} --project-dir {self.dbt_project_dir}"
        
        logger.info("Starting DBT command", command=full_command, target=target)
        
        try:
            result = subprocess.run(
                full_command.split(),
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode == 0:
                logger.info("DBT command completed successfully", 
                          command=command, target=target, 
                          stdout=result.stdout[-500:])  # Last 500 chars
                return {
                    'status': 'success',
                    'command': command,
                    'target': target,
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }
            else:
                logger.error("DBT command failed", 
                           command=command, target=target,
                           returncode=result.returncode,
                           stderr=result.stderr)
                return {
                    'status': 'error',
                    'command': command,
                    'target': target,
                    'returncode': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }
                
        except subprocess.TimeoutExpired:
            logger.error("DBT command timed out", command=command, target=target)
            return {
                'status': 'timeout',
                'command': command,
                'target': target,
                'error': 'Command timed out after 1 hour'
            }
        except Exception as e:
            logger.error("Unexpected error running DBT command", 
                        command=command, target=target, error=str(e))
            return {
                'status': 'error',
                'command': command,
                'target': target,
                'error': str(e)
            }
    
    def run_full_pipeline(self, target='prod'):
        """Run complete DBT pipeline with dependency installation"""
        results = []
        
        # Install dependencies
        deps_result = self.run_dbt_command('deps', target)
        results.append(deps_result)
        
        if deps_result['status'] != 'success':
            return results
        
        # Run seeds (if any)
        seed_result = self.run_dbt_command('seed', target)
        results.append(seed_result)
        
        # Run models
        run_result = self.run_dbt_command('run', target)
        results.append(run_result)
        
        # Run tests
        if run_result['status'] == 'success':
            test_result = self.run_dbt_command('test', target)
            results.append(test_result)
        
        return results
    
    def send_monitoring_metric(self, metric_name, value, labels=None):
        """Send custom metric to Cloud Monitoring"""
        try:
            client = monitoring_v3.MetricServiceClient()
            project_name = f"projects/{self.project_id}"
            
            series = monitoring_v3.TimeSeries()
            series.metric.type = f"custom.googleapis.com/dbt/{metric_name}"
            
            if labels:
                for key, val in labels.items():
                    series.metric.labels[key] = val
            
            series.resource.type = "cloud_run_revision"
            series.resource.labels["service_name"] = "dbt-runner"
            series.resource.labels["revision_name"] = os.getenv('K_REVISION', 'unknown')
            series.resource.labels["location"] = os.getenv('K_SERVICE_LOCATION', 'us-central1')
            
            now = datetime.utcnow()
            seconds = int(now.timestamp())
            nanos = int((now.timestamp() - seconds) * 10**9)
            interval = monitoring_v3.TimeInterval({
                "end_time": {"seconds": seconds, "nanos": nanos}
            })
            
            point = monitoring_v3.Point({
                "interval": interval,
                "value": {"double_value": value}
            })
            
            series.points = [point]
            client.create_time_series(name=project_name, time_series=[series])
            
            logger.info("Sent monitoring metric", metric=metric_name, value=value, labels=labels)
            
        except Exception as e:
            logger.warning("Failed to send monitoring metric", error=str(e))

# Initialize DBT runner
dbt_runner = DBTRunner()

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

@app.route('/run/<target>', methods=['POST'])
def run_dbt_pipeline(target):
    """Run DBT pipeline for specified target environment"""
    
    if target not in ['dev', 'staging', 'prod']:
        return jsonify({'error': 'Invalid target. Must be dev, staging, or prod'}), 400
    
    logger.info("Starting DBT pipeline run", target=target)
    
    start_time = datetime.utcnow()
    results = dbt_runner.run_full_pipeline(target)
    end_time = datetime.utcnow()
    
    # Calculate metrics
    duration = (end_time - start_time).total_seconds()
    success_count = sum(1 for r in results if r['status'] == 'success')
    error_count = sum(1 for r in results if r['status'] == 'error')
    
    # Send monitoring metrics
    dbt_runner.send_monitoring_metric('pipeline_duration', duration, {'target': target})
    dbt_runner.send_monitoring_metric('pipeline_success_rate', success_count / len(results) if results else 0, {'target': target})
    
    overall_status = 'success' if all(r['status'] == 'success' for r in results) else 'failed'
    
    response = {
        'status': overall_status,
        'target': target,
        'start_time': start_time.isoformat(),
        'end_time': end_time.isoformat(),
        'duration_seconds': duration,
        'results': results,
        'summary': {
            'total_commands': len(results),
            'successful': success_count,
            'errors': error_count
        }
    }
    
    logger.info("DBT pipeline completed", 
               target=target, status=overall_status, 
               duration=duration, results_count=len(results))
    
    return jsonify(response)

@app.route('/run/models/<model_name>', methods=['POST'])
def run_specific_model(model_name):
    """Run specific DBT model"""
    target = request.json.get('target', 'dev') if request.json else 'dev'
    
    logger.info("Running specific model", model=model_name, target=target)
    
    result = dbt_runner.run_dbt_command(f'run --select {model_name}', target)
    
    if result['status'] == 'success':
        # Also run tests for this model
        test_result = dbt_runner.run_dbt_command(f'test --select {model_name}', target)
        result['test_result'] = test_result
    
    return jsonify(result)

@app.route('/test/<target>', methods=['POST'])
def run_tests(target):
    """Run DBT tests for specified target"""
    
    if target not in ['dev', 'staging', 'prod']:
        return jsonify({'error': 'Invalid target. Must be dev, staging, or prod'}), 400
    
    logger.info("Running DBT tests", target=target)
    
    result = dbt_runner.run_dbt_command('test', target)
    
    return jsonify(result)

@app.route('/docs/generate', methods=['POST'])
def generate_docs():
    """Generate and serve DBT documentation"""
    target = request.json.get('target', 'prod') if request.json else 'prod'
    
    logger.info("Generating DBT documentation", target=target)
    
    result = dbt_runner.run_dbt_command('docs generate', target)
    
    return jsonify(result)

if __name__ == '__main__':
    # For local development
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)