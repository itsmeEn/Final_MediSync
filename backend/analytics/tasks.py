import asyncio
import json
import uuid
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from celery import shared_task
from celery.utils.log import get_task_logger

from .models import AnalyticsResult, AnalyticsTask, DataUpdateLog, AnalyticsCache, PatientRecord

# Import analytics functions with error handling
try:
    import pandas as pd
    from .predictive_analytics import (
        get_data_from_queryset,
        perform_patient_health_trends,
        analyze_patient_demographics,
        analyze_illness_prediction_chi_square,
        analyze_common_medications,
        predict_patient_volume,
        predict_illness_surge,
        predict_weekly_illness_forecast,
        predict_monthly_illness_forecast,
        analyze_performance_factors,
        run_full_analysis
    )
    ANALYTICS_AVAILABLE = True
except ImportError as e:
    logger = get_task_logger(__name__)
    logger.warning(f"Analytics modules not available: {e}")
    ANALYTICS_AVAILABLE = False

logger = get_task_logger(__name__)

@shared_task(bind=True, max_retries=3)
def run_analytics_task_async(self, task_id, analysis_type):
    """
    Async task to run analytics analysis
    """
    try:
        # Check if analytics modules are available
        if not ANALYTICS_AVAILABLE:
            raise Exception("Analytics modules not available. Please install required dependencies.")
        
        # Update task status
        task = AnalyticsTask.objects.get(task_id=task_id)
        task.status = 'processing'
        task.started_at = timezone.now()
        task.save()
        
        logger.info(f"Starting analytics task {task_id} for {analysis_type}")
        
        # Get patient data (exclude dummy data for real analytics)
        patient_queryset = PatientRecord.objects.select_related('patient').filter(is_dummy_data=False)
        
        if not patient_queryset.exists():
            raise Exception("No patient data available for analysis")
        
        # Convert to DataFrame
        df = get_data_from_queryset(patient_queryset)
        
        if df.empty:
            raise Exception("No data available for analysis")
        
        # Clean and prepare data
        df.columns = df.columns.str.lower().str.replace(' ', '_')
        
        # Run specific analysis based on type
        results = {}
        
        if analysis_type == 'patient_health_trends':
            results = perform_patient_health_trends(df)
        elif analysis_type == 'patient_demographics':
            results = analyze_patient_demographics(df)
        elif analysis_type == 'illness_prediction':
            results = analyze_illness_prediction_chi_square(df)
        elif analysis_type == 'medication_analysis':
            results = analyze_common_medications(df)
        elif analysis_type == 'patient_volume_prediction':
            results = predict_patient_volume(df)
        elif analysis_type == 'illness_surge_prediction':
            results = predict_illness_surge(df)
        elif analysis_type == 'weekly_illness_forecast':
            results = predict_weekly_illness_forecast(df)
        elif analysis_type == 'monthly_illness_forecast':
            results = predict_monthly_illness_forecast(df)
        elif analysis_type == 'performance_factors':
            results = analyze_performance_factors(df)
        elif analysis_type == 'full_analysis':
            results = run_full_analysis()
        else:
            raise Exception(f"Unknown analysis type: {analysis_type}")
        
        # Create analytics result
        with transaction.atomic():
            analytics_result = AnalyticsResult.objects.create(
                analysis_type=analysis_type,
                status='completed',
                results=results,
                processed_by_id=1  # You might want to pass user ID
            )
            
            # Update task
            task.status = 'completed'
            task.completed_at = timezone.now()
            task.result = analytics_result
            task.save()
        
        logger.info(f"Analytics task {task_id} completed successfully")
        return {
            'task_id': task_id,
            'status': 'completed',
            'results': results
        }
        
    except Exception as exc:
        logger.error(f"Analytics task {task_id} failed: {str(exc)}")
        
        # Update task status
        try:
            task = AnalyticsTask.objects.get(task_id=task_id)
            task.status = 'failed'
            task.error_message = str(exc)
            task.completed_at = timezone.now()
            task.save()
        except:
            pass
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying analytics task {task_id} (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        
        return {
            'task_id': task_id,
            'status': 'failed',
            'error': str(exc)
        }

@shared_task
def process_data_update_analytics(model_name, record_id, action):
    """
    Process analytics when data is updated
    """
    try:
        logger.info(f"Processing data update: {model_name} #{record_id} - {action}")
        
        # Log the data update
        DataUpdateLog.objects.create(
            model_name=model_name,
            record_id=record_id,
            action=action,
            triggered_analytics=True
        )
        
        # Trigger relevant analytics based on the model
        if model_name == 'PatientProfile':
            # Trigger patient-related analytics
            run_analytics_task_async.apply(args=(str(uuid.uuid4()), 'patient_demographics'))
            run_analytics_task_async.apply(args=(str(uuid.uuid4()), 'patient_health_trends'))
        
        logger.info(f"Analytics triggered for {model_name} #{record_id}")
        
    except Exception as exc:
        logger.error(f"Error processing data update analytics: {str(exc)}")

@shared_task
def cleanup_old_analytics():
    """
    Clean up old analytics results and cache
    """
    try:
        # Delete analytics results older than 30 days
        cutoff_date = timezone.now() - timedelta(days=30)
        old_results = AnalyticsResult.objects.filter(created_at__lt=cutoff_date)
        deleted_count = old_results.count()
        old_results.delete()
        
        # Delete expired cache entries
        expired_cache = AnalyticsCache.objects.filter(expires_at__lt=timezone.now())
        expired_count = expired_cache.count()
        expired_cache.delete()
        
        logger.info(f"Cleanup completed: {deleted_count} old results, {expired_count} expired cache entries deleted")
        
    except Exception as exc:
        logger.error(f"Error during cleanup: {str(exc)}")

@shared_task
def refresh_analytics_cache():
    """
    Refresh analytics cache with latest results
    """
    try:
        analysis_types = [
            'patient_health_trends',
            'patient_demographics',
            'illness_prediction',
            'medication_analysis',
            'patient_volume_prediction',
            'illness_surge_prediction',
            'performance_factors',
            'ai_insights'
        ]
        
        for analysis_type in analysis_types:
            # Get latest result
            latest_result = AnalyticsResult.objects.filter(
                analysis_type=analysis_type,
                status='completed'
            ).order_by('-created_at').first()
            
            if latest_result:
                # Cache the result
                cache_key = f"analytics_{analysis_type}"
                cache_data = {
                    'results': latest_result.results,
                    'updated_at': latest_result.updated_at.isoformat(),
                    'analysis_type': analysis_type
                }
                
                # Store in database cache
                AnalyticsCache.objects.update_or_create(
                    cache_key=cache_key,
                    defaults={
                        'data': cache_data,
                        'expires_at': timezone.now() + timedelta(hours=1)
                    }
                )
        
        logger.info("Analytics cache refreshed successfully")
        
    except Exception as exc:
        logger.error(f"Error refreshing analytics cache: {str(exc)}")

@shared_task
def run_scheduled_analytics():
    """
    Run scheduled analytics (can be called by Celery Beat)
    """
    try:
        logger.info("Running scheduled analytics")
        
        # Run full analysis
        task_id = str(uuid.uuid4())
        run_analytics_task_async.apply(args=(task_id, 'full_analysis'))
        
        # Refresh cache
        refresh_analytics_cache.apply()
        
        # Cleanup old data
        cleanup_old_analytics.apply()
        
        logger.info("Scheduled analytics completed")
        
    except Exception as exc:
        logger.error(f"Error in scheduled analytics: {str(exc)}")
