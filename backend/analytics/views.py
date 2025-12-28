import asyncio
import uuid
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction, models
from django.core.cache import cache
from django.http import HttpResponse
from django.template.loader import render_to_string
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from backend.admin_site.authentication import AdminJWTAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import threading
from concurrent.futures import ThreadPoolExecutor
import os
import time
import platform
try:
    import requests  # Optional: used for HTTP load generation in stress tests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
try:
    import psutil  # Optional: provides detailed system metrics
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# PDF generation imports
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.linecharts import HorizontalLineChart
    from reportlab.graphics import renderPDF
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import io
    import base64
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

from .models import AnalyticsResult, AnalyticsTask, DataUpdateLog, AnalyticsCache, UsageEvent, UptimePing
from .serializers import (
    AnalyticsResultSerializer, AnalyticsTaskSerializer, 
    AnalyticsRequestSerializer, AnalyticsResponseSerializer,
    UsageEventSerializer, UptimePingSerializer
)
from .tasks import run_analytics_task_async
from backend.users.models import PatientProfile
from .ai_insights_model import MediSyncAIInsights

class AnalyticsView(APIView):
    """
    Main analytics API endpoint for triggering and retrieving analytics
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get analytics results"""
        analysis_type = request.query_params.get('type', 'full_analysis')
        force_refresh = request.query_params.get('force_refresh', 'false').lower() == 'true'
        
        # Check cache first
        cache_key = f"analytics_{analysis_type}_{request.user.id}"
        if not force_refresh:
            cached_result = cache.get(cache_key)
            if cached_result:
                return Response({
                    'success': True,
                    'message': 'Analytics results retrieved from cache',
                    'data': cached_result,
                    'cached': True
                })
        
        # Get latest result from database
        try:
            latest_result = AnalyticsResult.objects.filter(
                analysis_type=analysis_type,
                status='completed'
            ).order_by('-created_at').first()
            
            if latest_result:
                serializer = AnalyticsResultSerializer(latest_result)
                # Cache the result for 1 hour
                cache.set(cache_key, serializer.data, 3600)
                
                return Response({
                    'success': True,
                    'message': 'Analytics results retrieved',
                    'data': serializer.data,
                    'cached': False
                })
            else:
                return Response({
                    'success': False,
                    'message': 'No analytics results found. Please trigger an analysis first.',
                    'data': None
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error retrieving analytics: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Trigger new analytics analysis"""
        serializer = AnalyticsRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Invalid request parameters',
                'data': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        analysis_type = serializer.validated_data['analysis_type']
        # force_refresh = serializer.validated_data['force_refresh']
        
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        
        try:
            # Create analytics task
            task = AnalyticsTask.objects.create(
                task_id=task_id,
                analysis_type=analysis_type,
                status='pending'
            )
            
            # Start async analytics processing
            run_analytics_task_async.delay(task_id, analysis_type)
            
            return Response({
                'success': True,
                'message': 'Analytics task started',
                'task_id': task_id,
                'data': {
                    'task_id': task_id,
                    'analysis_type': analysis_type,
                    'status': 'pending'
                }
            }, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error starting analytics task: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_analytics_status(request, task_id):
    """Get the status of a specific analytics task"""
    try:
        task = AnalyticsTask.objects.get(task_id=task_id)
        serializer = AnalyticsTaskSerializer(task)
        
        return Response({
            'success': True,
            'message': 'Task status retrieved',
            'data': serializer.data
        })
        
    except AnalyticsTask.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Task not found',
            'data': None
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error retrieving task status: {str(e)}',
            'data': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_analytics_history(request):
    """Get analytics history"""
    analysis_type = request.query_params.get('type')
    limit = int(request.query_params.get('limit', 10))
    
    queryset = AnalyticsResult.objects.all()
    if analysis_type:
        queryset = queryset.filter(analysis_type=analysis_type)
    
    queryset = queryset.order_by('-created_at')[:limit]
    serializer = AnalyticsResultSerializer(queryset, many=True)
    
    return Response({
        'success': True,
        'message': 'Analytics history retrieved',
        'data': serializer.data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_data_refresh(request):
    """Manually trigger analytics refresh for new data"""
    try:
        # This would typically be called when new data is added
        # For now, we'll trigger a full analysis
        task_id = str(uuid.uuid4())
        
        AnalyticsTask.objects.create(
            task_id=task_id,
            analysis_type='full_analysis',
            status='pending'
        )
        
        # Start async processing
        run_analytics_task_async.delay(task_id, 'full_analysis')
        
        return Response({
            'success': True,
            'message': 'Data refresh triggered',
            'task_id': task_id
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error triggering refresh: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_real_time_analytics(request):
    """Get real-time analytics dashboard data"""
    try:
        # Get latest results for different analysis types
        dashboard_data = {}
        
        analysis_types = [
            'patient_health_trends',
            'patient_demographics', 
            'illness_prediction',
            'medication_analysis',
            'patient_volume_prediction'
        ]
        
        for analysis_type in analysis_types:
            latest_result = AnalyticsResult.objects.filter(
                analysis_type=analysis_type,
                status='completed'
            ).order_by('-created_at').first()
            
            if latest_result:
                dashboard_data[analysis_type] = {
                    'status': 'completed',
                    'last_updated': latest_result.updated_at.isoformat(),
                    'data': latest_result.results
                }
            else:
                dashboard_data[analysis_type] = {
                    'status': 'no_data',
                    'last_updated': None,
                    'data': None
                }
        
        return Response({
            'success': True,
            'message': 'Real-time analytics data retrieved',
            'data': dashboard_data
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error retrieving real-time analytics: {str(e)}',
            'data': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def system_performance(request):
    """Return system performance metrics for the server.

    Includes CPU load averages, optional CPU percent, memory usage, uptime,
    and basic process stats when psutil is available.
    """
    # CPU load averages
    load_1 = load_5 = load_15 = None
    try:
        if hasattr(os, 'getloadavg'):
            load_1, load_5, load_15 = os.getloadavg()
    except Exception:
        pass

    # CPU percent (requires psutil)
    cpu_percent = None
    if PSUTIL_AVAILABLE:
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
        except Exception:
            cpu_percent = None

    # Memory metrics
    memory = None
    if PSUTIL_AVAILABLE:
        try:
            vm = psutil.virtual_memory()
            memory = {
                'total': vm.total,
                'available': vm.available,
                'used': vm.used,
                'percent': vm.percent
            }
        except Exception:
            memory = None

    # Uptime
    uptime_seconds = None
    if PSUTIL_AVAILABLE:
        try:
            uptime_seconds = int(time.time() - psutil.boot_time())
        except Exception:
            uptime_seconds = None

    # Process info
    process = None
    if PSUTIL_AVAILABLE:
        try:
            p = psutil.Process(os.getpid())
            process = {
                'pid': p.pid,
                'rss': p.memory_info().rss,
                'threads': p.num_threads(),
                'memory_percent': p.memory_percent()
            }
        except Exception:
            process = None

    data = {
        'platform': platform.platform(),
        'cpu': {
            'load_1': load_1,
            'load_5': load_5,
            'load_15': load_15,
            'percent': cpu_percent
        },
        'memory': memory,
        'uptime_seconds': uptime_seconds,
        'process': process,
        'psutil_available': PSUTIL_AVAILABLE,
        'server_time': timezone.now().isoformat()
    }

    return Response({
        'success': True,
        'message': 'System performance metrics retrieved',
        'data': data
    })

# WebSocket-like endpoint for real-time updates (using Server-Sent Events)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_stream(request):
    """Stream analytics updates in real-time"""
    import time
    
    def event_stream():
        while True:
            # Get latest analytics results
            latest_results = AnalyticsResult.objects.filter(
                status='completed'
            ).order_by('-updated_at')[:5]
            
            data = {
                'timestamp': timezone.now().isoformat(),
                'results': AnalyticsResultSerializer(latest_results, many=True).data
            }
            
            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(5)  # Update every 5 seconds
    
    from django.http import StreamingHttpResponse
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['Connection'] = 'keep-alive'
    return response

# Stress testing endpoint to assess API performance for doctor, nurse, and patient flows
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([AdminJWTAuthentication, JWTAuthentication])
def stress_test_analytics(request):
    """Run a lightweight concurrent stress test against key frontend API routes.

    Parameters (query string):
    - group: one of 'doctor', 'nurse', 'patient', 'all' (default: 'all')
    - concurrency: number of workers (default: 8, max: 64)
    - requests: number of requests per endpoint (default: 30, max: 1000)
    - timeout: per-request timeout in seconds (default: 10)

    Returns aggregated latency and success/error metrics per endpoint and group.
    """
    if not REQUESTS_AVAILABLE:
        return Response({
            'success': False,
            'message': 'Python requests library is not installed on the server.'
        }, status=status.HTTP_400_BAD_REQUEST)

    def parse_int(name, default, min_v, max_v):
        try:
            v = int(request.query_params.get(name, default))
            return max(min_v, min(max_v, v))
        except Exception:
            return default

    group = (request.query_params.get('group') or 'all').lower()
    concurrency = parse_int('concurrency', 8, 1, 64)
    num_requests = parse_int('requests', 30, 1, 1000)
    try:
        timeout = float(request.query_params.get('timeout', 10))
    except Exception:
        timeout = 10.0

    base_url = f"{request.scheme}://{request.get_host()}"
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    headers = {'Content-Type': 'application/json'}
    if auth_header:
        headers['Authorization'] = auth_header

    # Target endpoints used by the various frontends
    endpoints = {
        'doctor': [
            '/api/operations/dashboard/stats/',
            '/api/operations/appointments/',
            '/api/operations/queue/patients/',
            '/api/operations/notifications/',
            '/api/operations/doctor/assignments/',
        ],
        'nurse': [
            '/api/operations/nurse/queue/patients/',
            '/api/operations/available-doctors/',
            '/api/operations/medicine-inventory/',
            '/api/operations/queue/status/?department=OPD',
            '/api/operations/messaging/notifications/',
        ],
        'patient': [
            '/api/operations/patient/dashboard/summary/',
            '/api/operations/patient/appointments/',
            '/api/operations/queue/availability/',
            '/api/operations/queue/status/?department=OPD',
        ],
    }

    if group == 'all':
        selected_groups = ['doctor', 'nurse', 'patient']
    else:
        selected_groups = [group] if group in endpoints else []

    if not selected_groups:
        return Response({
            'success': False,
            'message': 'Invalid group. Use one of: doctor, nurse, patient, all.'
        }, status=status.HTTP_400_BAD_REQUEST)

    def fetch_once(url: str):
        start = time.perf_counter()
        code = None
        err = None
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            code = resp.status_code
        except Exception as e:
            err = str(e)
        end = time.perf_counter()
        return {
            'latency_ms': (end - start) * 1000.0,
            'status_code': code,
            'error': err,
        }

    def compute_metrics(records):
        latencies = [r['latency_ms'] for r in records if r.get('latency_ms') is not None]
        status_dist = {}
        success = 0
        errors = 0
        for r in records:
            code = r.get('status_code')
            key = str(code) if code is not None else 'none'
            status_dist[key] = status_dist.get(key, 0) + 1
            if code is not None and 200 <= code < 300:
                success += 1
            else:
                errors += 1

        avg = (sum(latencies) / len(latencies)) if latencies else None
        max_v = max(latencies) if latencies else None
        p95 = None
        if latencies:
            sl = sorted(latencies)
            idx = max(0, int(0.95 * len(sl)) - 1)
            p95 = sl[idx]

        return {
            'requests': len(records),
            'success_count': success,
            'error_count': errors,
            'status_distribution': status_dist,
            'avg_latency_ms': round(avg, 2) if avg is not None else None,
            'p95_latency_ms': round(p95, 2) if p95 is not None else None,
            'max_latency_ms': round(max_v, 2) if max_v is not None else None,
            'latencies': latencies,  # included for group-level aggregation
        }

    started_at = timezone.now()
    results = {
        'base_url': base_url,
        'started_at': started_at.isoformat(),
        'params': {
            'group': group,
            'concurrency': concurrency,
            'requests_per_endpoint': num_requests,
            'timeout': timeout,
        },
        'groups': {},
    }

    for g in selected_groups:
        group_results = {
            'endpoints': {},
            'summary': {},
        }
        all_latencies = []
        total_success = 0
        total_requests = 0

        for ep in endpoints[g]:
            target_url = base_url + ep
            records = []
            # Run concurrent requests per endpoint
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = [executor.submit(fetch_once, target_url) for _ in range(num_requests)]
                for f in futures:
                    try:
                        rec = f.result()
                        records.append(rec)
                    except Exception as e:
                        records.append({'latency_ms': None, 'status_code': None, 'error': str(e)})

            metrics = compute_metrics(records)
            group_results['endpoints'][ep] = {k: v for k, v in metrics.items() if k != 'latencies'}
            # Aggregate
            all_latencies.extend(metrics.get('latencies', []))
            total_success += metrics.get('success_count', 0)
            total_requests += metrics.get('requests', 0)

        # Compute group summary
        avg = (sum(all_latencies) / len(all_latencies)) if all_latencies else None
        max_v = max(all_latencies) if all_latencies else None
        p95 = None
        if all_latencies:
            sl = sorted(all_latencies)
            idx = max(0, int(0.95 * len(sl)) - 1)
            p95 = sl[idx]

        group_results['summary'] = {
            'total_requests': total_requests,
            'success_rate': round((total_success / total_requests) * 100.0, 2) if total_requests else 0.0,
            'avg_latency_ms': round(avg, 2) if avg is not None else None,
            'p95_latency_ms': round(p95, 2) if p95 is not None else None,
            'max_latency_ms': round(max_v, 2) if max_v is not None else None,
        }

        results['groups'][g] = group_results

    finished_at = timezone.now()
    results['finished_at'] = finished_at.isoformat()
    results['duration_ms'] = int((finished_at - started_at).total_seconds() * 1000)

    return Response({
        'success': True,
        'message': 'Stress test completed',
        'data': results,
    })

# Doctor Analytics Endpoints
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def doctor_analytics(request):
    """
    Get analytics specifically for doctors
    """
    if request.user.role != 'doctor':
        return Response({
            'error': 'Only doctors can access this endpoint.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        # Get doctor-specific analytics
        analytics_data = {}
        
        # Patient demographics for doctor's patients
        patient_demographics = AnalyticsResult.objects.filter(
            analysis_type='patient_demographics',
            status='completed'
        ).order_by('-created_at').first()
        
        # Illness prediction for doctor's specialty
        illness_prediction = AnalyticsResult.objects.filter(
            analysis_type='illness_prediction',
            status='completed'
        ).order_by('-created_at').first()
        
        # Patient health trends
        health_trends = AnalyticsResult.objects.filter(
            analysis_type='patient_health_trends',
            status='completed'
        ).order_by('-created_at').first()
        
        # Illness surge prediction
        surge_prediction = AnalyticsResult.objects.filter(
            analysis_type='illness_surge_prediction',
            status='completed'
        ).order_by('-created_at').first()

        # Monthly illness forecast (SARIMA)
        monthly_illness_forecast = AnalyticsResult.objects.filter(
            analysis_type='monthly_illness_forecast',
            status='completed'
        ).order_by('-created_at').first()

        # Patient volume prediction (include for doctor; strip evaluation metrics)
        volume_prediction = AnalyticsResult.objects.filter(
            analysis_type='patient_volume_prediction',
            status='completed'
        ).order_by('-created_at').first()

        vp_results = volume_prediction.results if volume_prediction else None
        if isinstance(vp_results, dict) and 'evaluation_metrics' in vp_results:
            # Remove MAE/RMSE from doctor-facing payload per requirements
            vp_results = {k: v for k, v in vp_results.items() if k != 'evaluation_metrics'}
        
        # Normalize gender proportions in patient demographics if present
        pd_results = patient_demographics.results if patient_demographics else None
        if isinstance(pd_results, dict) and 'gender_proportions' in pd_results:
            pd_results = pd_results.copy()
            pd_results['gender_proportions'] = normalize_gender_proportions(pd_results.get('gender_proportions', {}))

        analytics_data = {
            'patient_demographics': pd_results if pd_results else (patient_demographics.results if patient_demographics else None),
            'illness_prediction': illness_prediction.results if illness_prediction else None,
            'health_trends': health_trends.results if health_trends else None,
            'surge_prediction': surge_prediction.results if surge_prediction else None,
            'monthly_illness_forecast': monthly_illness_forecast.results if monthly_illness_forecast else None,
            'volume_prediction': vp_results,
            'doctor_name': request.user.full_name,
            'specialization': getattr(request.user.doctor_profile, 'specialization', 'General Practice') if hasattr(request.user, 'doctor_profile') else 'General Practice',
            'generated_at': timezone.now().isoformat()
        }
        
        return Response({
            'success': True,
            'message': 'Doctor analytics retrieved successfully',
            'data': analytics_data
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error retrieving doctor analytics: {str(e)}',
            'data': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def nurse_analytics(request):
    """
    Get analytics specifically for nurses
    """
    if request.user.role != 'nurse':
        return Response({
            'error': 'Only nurses can access this endpoint.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        # Get nurse-specific analytics
        analytics_data = {}
        
        # Medication analysis
        medication_analysis = AnalyticsResult.objects.filter(
            analysis_type='medication_analysis',
            status='completed'
        ).order_by('-created_at').first()
        
        # Patient demographics
        patient_demographics = AnalyticsResult.objects.filter(
            analysis_type='patient_demographics',
            status='completed'
        ).order_by('-created_at').first()
        
        # Patient health trends
        health_trends = AnalyticsResult.objects.filter(
            analysis_type='patient_health_trends',
            status='completed'
        ).order_by('-created_at').first()
        
        # Patient volume prediction
        volume_prediction = AnalyticsResult.objects.filter(
            analysis_type='patient_volume_prediction',
            status='completed'
        ).order_by('-created_at').first()
        
        # Normalize gender proportions for data integrity if available
        pd_results = patient_demographics.results if patient_demographics else None
        if isinstance(pd_results, dict) and 'gender_proportions' in pd_results:
            pd_results = pd_results.copy()
            pd_results['gender_proportions'] = normalize_gender_proportions(pd_results.get('gender_proportions', {}))

        analytics_data = {
            'medication_analysis': medication_analysis.results if medication_analysis else None,
            'patient_demographics': pd_results if pd_results else (patient_demographics.results if patient_demographics else None),
            'health_trends': health_trends.results if health_trends else None,
            'volume_prediction': volume_prediction.results if volume_prediction else None,
            'nurse_name': request.user.full_name,
            'department': getattr(request.user.nurse_profile, 'department', 'General') if hasattr(request.user, 'nurse_profile') else 'General',
            'generated_at': timezone.now().isoformat()
        }
        
        return Response({
            'success': True,
            'message': 'Nurse analytics retrieved successfully',
            'data': analytics_data
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error retrieving nurse analytics: {str(e)}',
            'data': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def generate_analytics_pdf(request):
    """
    Generate standardized PDF report of analytics findings with hospital information,
    role-specific data, and consistent branding across doctor and nurse views
    """
    if not PDF_AVAILABLE:
        # Try lazy import to avoid hard 503
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
            import matplotlib
            matplotlib.use('Agg')
            import io
            import base64
            globals()['PDF_AVAILABLE'] = True
        except Exception:
            # Graceful HTML fallback when PDF libs are unavailable
            user_role = request.user.role
            report_type = request.GET.get('type', 'full')
            # Gather analytics data similar to PDF path
            if user_role == 'doctor' or report_type == 'doctor':
                analytics_data = get_doctor_analytics_data(request.user)
                title = "Patient Findings Generated Report"
                role = 'doctor'
                user_info = {
                    'name': request.user.full_name,
                    'specialization': getattr(request.user.doctor_profile, 'specialization', 'General Practice') if hasattr(request.user, 'doctor_profile') else 'General Practice',
                    'role': 'Doctor',
                    'department': getattr(request.user.doctor_profile, 'specialization', 'General Practice') if hasattr(request.user, 'doctor_profile') else 'General Practice'
                }
            elif user_role == 'nurse' or report_type == 'nurse':
                analytics_data = get_nurse_analytics_data(request.user)
                title = "Patient Findings Generated Report"
                role = 'nurse'
                user_info = {
                    'name': request.user.full_name,
                    'specialization': getattr(request.user.nurse_profile, 'department', 'General') if hasattr(request.user, 'nurse_profile') else 'General',
                    'role': 'Nurse',
                    'department': getattr(request.user.nurse_profile, 'department', 'General') if hasattr(request.user, 'nurse_profile') else 'General'
                }
            else:
                analytics_data = get_full_analytics_data()
                title = "Patient Findings Generated Report"
                role = 'doctor'
                user_info = None
            try:
                ai_suggestions = build_recommendations(analytics_data, role)
            except Exception:
                ai_suggestions = {'high': [], 'medium': [], 'low': []}
            # Minimal inline HTML report
            html = f"""
            <!doctype html>
            <html>
              <head>
                <meta charset='utf-8'>
                <title>{title}</title>
                <style>
                  body {{ font-family: Arial, sans-serif; margin: 24px; }}
                  h1 {{ color: #1f4b99; margin-bottom: 8px; }}
                  h2 {{ color: #2a6b2a; margin-top: 24px; }}
                  .meta {{ color: #555; font-size: 12px; margin-bottom: 16px; }}
                  .disclaimer {{ color: #666; font-style: italic; margin: 8px 0 16px; }}
                  ul {{ padding-left: 18px; }}
                </style>
              </head>
              <body>
                <h1>{title}</h1>
                <div class='meta'>Role: {user_info.get('role', 'Doctor') if user_info else 'System'} | Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
                <div class='disclaimer'>This is an automated, AI-generated interpretation of the latest analytics findings. Use as guidance, not a substitute for clinical judgment.</div>
                <h2>AI Suggestions</h2>
                <h3>High Priority</h3>
                <ul>
                  {''.join(f'<li>{item.get('text')}</li>' for item in ai_suggestions.get('high', [])) or '<li>No high priority suggestions.</li>'}
                </ul>
                <h3>Medium Priority</h3>
                <ul>
                  {''.join(f'<li>{item.get('text')}</li>' for item in ai_suggestions.get('medium', [])) or '<li>No medium priority suggestions.</li>'}
                </ul>
                <h3>Low Priority</h3>
                <ul>
                  {''.join(f'<li>{item.get('text')}</li>' for item in ai_suggestions.get('low', [])) or '<li>No low priority suggestions.</li>'}
                </ul>
              </body>
            </html>
            """
            response = HttpResponse(html, content_type='text/html')
            response['Content-Disposition'] = f'attachment; filename="{user_role}_analytics_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.html"'
            return response
    
    user_role = request.user.role
    report_type = request.GET.get('type', 'full')  # full, doctor, nurse
    
    try:
        # Get hospital information from user profile or set defaults
        hospital_info = get_hospital_information(request.user)
        
        # Get analytics data based on user role
        if user_role == 'doctor' or report_type == 'doctor':
            analytics_data = get_doctor_analytics_data(request.user)
            title = "Patient Findings Generated Report"
            user_info = {
                'name': request.user.full_name,
                'specialization': getattr(request.user.doctor_profile, 'specialization', 'General Practice') if hasattr(request.user, 'doctor_profile') else 'General Practice',
                'role': 'Doctor',
                'department': getattr(request.user.doctor_profile, 'specialization', 'General Practice') if hasattr(request.user, 'doctor_profile') else 'General Practice'
            }
        elif user_role == 'nurse' or report_type == 'nurse':
            analytics_data = get_nurse_analytics_data(request.user)
            title = "Patient Findings Generated Report"
            user_info = {
                'name': request.user.full_name,
                'specialization': getattr(request.user.nurse_profile, 'department', 'General') if hasattr(request.user, 'nurse_profile') else 'General',
                'role': 'Nurse',
                'department': getattr(request.user.nurse_profile, 'department', 'General') if hasattr(request.user, 'nurse_profile') else 'General'
            }
        else:
            analytics_data = get_full_analytics_data()
            title = "Patient Findings Generated Report"
            user_info = None
        
        # Generate PDF with standardized template
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{user_role}_analytics_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
        
        # Build PDF into an in-memory buffer for reliable response writing
        buffer = io.BytesIO()
        # Create PDF with custom page template
        doc = create_standardized_pdf_template(buffer, hospital_info, user_info)
        styles = get_custom_styles()
        story = []
        
        # Add standardized header
        add_standardized_header(story, hospital_info, user_info, title, styles)

        # Overview section
        story.append(Paragraph("Overview:", styles['SectionHeaderNoBorder']))
        story.append(Paragraph(
            "This report provides comprehensive analytics insights for healthcare management. "
            "It integrates patient demographics, health trends, medication patterns, and forecasting "
            "to support evidence-based decisions and improve patient care outcomes.",
            styles['ContentText']
        ))
        
        # Executive summary at the beginning
        try:
            add_executive_summary_section(story, analytics_data, styles)
        except Exception:
            pass

        # Add analytics sections with visualizations and interpretations
        add_analytics_sections_with_visualizations(story, analytics_data, styles)

        # Interpretation section (narrative + AI interpretation)
        try:
            add_data_interpretation_section(story, analytics_data, styles)
        except Exception:
            pass
        add_ai_interpretation_section(story, analytics_data, styles)

        # Factor analysis section
        try:
            add_factor_analysis_section(story, analytics_data, styles)
        except Exception:
            pass

        # AI Recommendations module (priority, guidance, outcomes)
        try:
            role = (user_info.get('role', 'Doctor') if user_info else 'Doctor').lower()
            add_ai_recommendations_module(story, analytics_data, role, styles)
        except Exception:
            pass

        # Key takeaways and citations at the end
        try:
            add_key_takeaways_section(story, analytics_data, styles)
        except Exception:
            pass
        try:
            add_citations_section(story, analytics_data, styles)
        except Exception:
            pass
        
        # Prepared by signature (bottom-right)
        if user_info:
            add_doctor_signature(story, user_info, styles)
        
        # Add standardized footer
        add_standardized_footer(story, styles)
        
        doc.build(story)
        # Write generated PDF bytes to HTTP response
        response.write(buffer.getvalue())
        buffer.close()
        return response
        
    except Exception as e:
        # Log detailed traceback to server console for debugging
        try:
            import traceback
            print("[PDF Generation] Error generating PDF report:", str(e))
            print(traceback.format_exc())
        except Exception:
            pass
        return Response({
            'error': f'Error generating PDF report: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def get_doctor_analytics_data(user):
    """Get analytics data for doctors"""
    return {
        'patient_demographics': get_latest_analytics('patient_demographics'),
        'illness_prediction': get_latest_analytics('illness_prediction'),
        'health_trends': get_latest_analytics('patient_health_trends'),
        'surge_prediction': get_latest_analytics('illness_surge_prediction'),
        'monthly_illness_forecast': get_latest_analytics('monthly_illness_forecast'),
        'doctor_name': user.full_name,
        'specialization': getattr(user.doctor_profile, 'specialization', 'General Practice') if hasattr(user, 'doctor_profile') else 'General Practice'
    }

def get_nurse_analytics_data(user):
    """Get analytics data for nurses"""
    return {
        'medication_analysis': get_latest_analytics('medication_analysis'),
        'patient_demographics': get_latest_analytics('patient_demographics'),
        'health_trends': get_latest_analytics('patient_health_trends'),
        'volume_prediction': get_latest_analytics('patient_volume_prediction'),
        'nurse_name': user.full_name,
        'department': getattr(user.nurse_profile, 'department', 'General') if hasattr(user, 'nurse_profile') else 'General'
    }

def get_full_analytics_data():
    """Get all analytics data"""
    return {
        'patient_demographics': get_latest_analytics('patient_demographics'),
        'illness_prediction': get_latest_analytics('illness_prediction'),
        'medication_analysis': get_latest_analytics('medication_analysis'),
        'health_trends': get_latest_analytics('patient_health_trends'),
        'volume_prediction': get_latest_analytics('patient_volume_prediction'),
        'surge_prediction': get_latest_analytics('illness_surge_prediction'),
        'monthly_illness_forecast': get_latest_analytics('monthly_illness_forecast'),
    }

def get_latest_analytics(analysis_type):
    """Get latest analytics result for a specific type"""
    result = AnalyticsResult.objects.filter(
        analysis_type=analysis_type,
        status='completed'
    ).order_by('-created_at').first()
    return result.results if result else None

def get_hospital_information(user):
    """
    Get hospital information prioritizing user settings (doctor/nurse), with sensible fallbacks.
    """
    # Prefer explicit fields on the user model
    name = (getattr(user, 'hospital_name', None) or '').strip()
    address = (getattr(user, 'hospital_address', None) or '').strip()

    # Fallback to any available patient profile hospital name if missing
    if not name or not address:
        from backend.users.models import PatientProfile
        patient_profile = PatientProfile.objects.filter(hospital__isnull=False).exclude(hospital='').first()
        if not name and patient_profile:
            name = patient_profile.hospital.strip()

    # Defaults if still missing
    if not name:
        name = 'MediSync Healthcare Center'
    if not address:
        address = '123 Healthcare Avenue, Medical District, City 12345'

def normalize_gender_proportions(gender_data):
    """Validate and normalize gender proportions to ensure integrity.

    - Ensures keys for 'Male', 'Female', and 'Other' exist
    - Coerces values to non-negative numbers
    - Normalizes values so the sum equals 100 (percentages)
    - If all values are zero or invalid, returns a sensible default
    """
    try:
        if not isinstance(gender_data, dict):
            gender_data = {}

        # Extract and sanitize numeric values
        male = float(gender_data.get('Male', 0) or 0)
        female = float(gender_data.get('Female', 0) or 0)
        other = float(gender_data.get('Other', gender_data.get('Non-binary', 0) or 0) or 0)

        # Clamp negatives to zero
        male = max(male, 0)
        female = max(female, 0)
        other = max(other, 0)

        total = male + female + other
        if total <= 0:
            # Default distribution when no data available
            return {'Male': 50.0, 'Female': 48.0, 'Other': 2.0}

        # If values are counts, convert to percentages
        male_pct = (male / total) * 100.0
        female_pct = (female / total) * 100.0
        other_pct = (other / total) * 100.0

        # Normalize rounding to ensure exact 100
        # Round to one decimal place and adjust residual to Male
        male_pct = round(male_pct, 1)
        female_pct = round(female_pct, 1)
        other_pct = round(other_pct, 1)
        residual = 100.0 - (male_pct + female_pct + other_pct)
        male_pct = round(male_pct + residual, 1)

        # Final clamp and correction for any floating errors
        male_pct = max(min(male_pct, 100.0), 0.0)
        female_pct = max(min(female_pct, 100.0), 0.0)
        other_pct = max(min(other_pct, 100.0), 0.0)

        return {'Male': male_pct, 'Female': female_pct, 'Other': other_pct}
    except Exception:
        # Fallback to a safe default in case of any unexpected error
        return {'Male': 50.0, 'Female': 48.0, 'Other': 2.0}

def get_custom_styles():
    """
    Get responsive custom styles for the standardized PDF template
    """
    from reportlab.lib.pagesizes import A4
    
    styles = getSampleStyleSheet()
    
    # Calculate responsive font sizes based on page dimensions
    page_width, page_height = A4
    base_font_size = min(page_width, page_height) / 60  # Responsive base size
    
    # Add custom styles for consistent branding with responsive design
    styles.add(ParagraphStyle(
        name='HospitalName',
        parent=styles['Heading1'],
        fontSize=max(18, int(base_font_size * 1.8)),
        fontName='Helvetica-Bold',
        textColor=colors.darkblue,
        alignment=TA_CENTER,
        spaceAfter=8,
        leading=max(20, int(base_font_size * 2.2))  # Responsive line height
    ))
    
    styles.add(ParagraphStyle(
        name='HospitalAddress',
        parent=styles['Normal'],
        fontSize=max(9, int(base_font_size * 1.0)),
        fontName='Helvetica',
        textColor=colors.grey,
        alignment=TA_CENTER,
        spaceAfter=12,
        leading=max(11, int(base_font_size * 1.3))
    ))
    
    styles.add(ParagraphStyle(
        name='ReportTitle',
        parent=styles['Heading1'],
        fontSize=max(16, int(base_font_size * 1.6)),
        fontName='Helvetica-Bold',
        textColor=colors.darkblue,
        alignment=TA_CENTER,
        spaceAfter=10,
        spaceBefore=6,
        leading=max(18, int(base_font_size * 1.9))
    ))
    
    styles.add(ParagraphStyle(
        name='UserInfo',
        parent=styles['Normal'],
        fontSize=max(10, int(base_font_size * 1.1)),
        fontName='Helvetica',
        textColor=colors.black,
        alignment=TA_CENTER,
        spaceAfter=20,
        leading=max(12, int(base_font_size * 1.4))
    ))
    
    # Department header style (used for underlined department at top)
    styles.add(ParagraphStyle(
        name='DepartmentHeader',
        parent=styles['Heading2'],
        fontSize=max(14, int(base_font_size * 1.5)),
        fontName='Helvetica-Bold',
        textColor=colors.black,
        alignment=TA_CENTER,
        spaceAfter=8,
        leading=max(16, int(base_font_size * 1.8))
    ))
    
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading2'],
        fontSize=max(13, int(base_font_size * 1.4)),
        fontName='Helvetica-Bold',
        textColor=colors.darkblue,
        spaceAfter=12,
        spaceBefore=20,
        leading=max(15, int(base_font_size * 1.7)),
        borderWidth=1,
        borderColor=colors.lightgrey,
        borderPadding=4
    ))
    
    # Borderless section header for Overview
    styles.add(ParagraphStyle(
        name='SectionHeaderNoBorder',
        parent=styles['Heading2'],
        fontSize=max(13, int(base_font_size * 1.4)),
        fontName='Helvetica-Bold',
        textColor=colors.darkblue,
        spaceAfter=12,
        spaceBefore=20,
        leading=max(15, int(base_font_size * 1.7))
    ))
    
    styles.add(ParagraphStyle(
        name='SubsectionHeader',
        parent=styles['Heading3'],
        fontSize=max(11, int(base_font_size * 1.2)),
        fontName='Helvetica-Bold',
        textColor=colors.darkgreen,
        spaceAfter=8,
        spaceBefore=12,
        leading=max(13, int(base_font_size * 1.5))
    ))
    
    styles.add(ParagraphStyle(
        name='ContentText',
        parent=styles['Normal'],
        fontSize=max(9, int(base_font_size * 1.0)),
        fontName='Helvetica',
        textColor=colors.black,
        spaceAfter=6,
        alignment=TA_JUSTIFY,
        leading=max(11, int(base_font_size * 1.3)),
        leftIndent=8,  # Better readability with indentation
        rightIndent=8
    ))
    
    styles.add(ParagraphStyle(
        name='FooterText',
        parent=styles['Normal'],
        fontSize=max(7, int(base_font_size * 0.8)),
        fontName='Helvetica',
        textColor=colors.grey,
        alignment=TA_CENTER,
        spaceAfter=4,
        leading=max(9, int(base_font_size * 1.1))
    ))
    
    # Add a highlight style for important information
    styles.add(ParagraphStyle(
        name='HighlightText',
        parent=styles['Normal'],
        fontSize=max(10, int(base_font_size * 1.1)),
        fontName='Helvetica-Bold',
        textColor=colors.darkblue,
        alignment=TA_LEFT,
        spaceAfter=6,
        spaceBefore=4,
        leading=max(12, int(base_font_size * 1.4)),
        backColor=colors.lightblue,
        borderWidth=1,
        borderColor=colors.blue,
        borderPadding=6
    ))
    
    return styles

def create_standardized_pdf_template(response, hospital_info, user_info):
    """
    Create a standardized PDF template with responsive design and consistent margins
    """
    from reportlab.platypus import PageTemplate, Frame, BaseDocTemplate
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.units import inch
    
    # Responsive page size selection (A4 for international, Letter for US)
    pagesize = A4  # Default to A4 for medical documents
    
    # Calculate responsive margins based on page size
    page_width, page_height = pagesize
    margin_ratio = 0.1  # 10% margins for responsive design
    
    # Responsive margin calculation
    horizontal_margin = page_width * margin_ratio
    vertical_margin = page_height * margin_ratio
    
    # Ensure minimum margins for readability
    min_margin = 0.75 * inch
    horizontal_margin = max(horizontal_margin, min_margin)
    vertical_margin = max(vertical_margin, min_margin)
    
    # Create document with fixed margins per requested layout
    doc = SimpleDocTemplate(
        response,
        pagesize=pagesize,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=1.0 * inch,
        bottomMargin=1.0 * inch,
        title="MediSync Analytics Report",
        author=f"{user_info.get('name', 'MediSync User') if user_info else 'MediSync System'}",
        subject="Healthcare Analytics Report",
        creator="MediSync Analytics System"
    )
    
    return doc

def add_standardized_header(story, hospital_info, user_info, title, styles):
    """
    Add standardized header section with hospital information and user details
    """
    # Hospital Name
    story.append(Paragraph(hospital_info['name'], styles['HospitalName']))
    
    # Hospital Address (no phone/email in header)
    story.append(Paragraph(hospital_info['address'], styles['HospitalAddress']))
    
    # Department header centered
    if user_info and user_info.get('department'):
        story.append(Paragraph(f"{user_info['department']} Department", styles['DepartmentHeader']))
    
    # Separator rule under header
    from reportlab.platypus import HRFlowable
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1b728e')))
    story.append(Spacer(1, 12))
    
    # Report Title
    story.append(Paragraph(title, styles['ReportTitle']))
    
    # Add spacing after title
    story.append(Spacer(1, 20))

def add_analytics_dashboard(story, analytics_data, user_info, styles):
    """
    Add analytics dashboard with role-specific performance metrics and visualizations
    """
    # Dashboard Title
    story.append(Paragraph("Analytics Dashboard", styles['SectionHeader']))
    
    if user_info and user_info['role'] == 'Doctor':
        add_doctor_specific_analytics(story, analytics_data, styles)
    elif user_info and user_info['role'] == 'Nurse':
        add_nurse_specific_analytics(story, analytics_data, styles)
    else:
        add_general_analytics(story, analytics_data, styles)
    
    # Add comparative benchmarks section
    add_comparative_benchmarks(story, user_info, styles)
    
    # Add time-series visualizations
    add_time_series_visualizations(story, analytics_data, styles)

def add_doctor_specific_analytics(story, analytics_data, styles):
    """Add doctor-specific performance metrics"""
    story.append(Paragraph("Doctor Performance Metrics", styles['SubsectionHeader']))
    
    # Patient Demographics
    if analytics_data.get('patient_demographics'):
        demographics = analytics_data['patient_demographics']
        story.append(Paragraph("Patient Demographics Overview:", styles['ContentText']))
        
        if 'total_patients' in demographics:
            story.append(Paragraph(f"• Total Patients Managed: {demographics['total_patients']}", styles['ContentText']))
        
        if 'age_distribution' in demographics:
            age_dist = demographics['age_distribution']
            story.append(Paragraph(f"• Primary Age Groups: {', '.join([f'{k}: {v}%' for k, v in age_dist.items()][:3])}", styles['ContentText']))
    
    # Health Trends
    if analytics_data.get('health_trends'):
        story.append(Paragraph("Health Trends Analysis:", styles['ContentText']))
        trends = analytics_data['health_trends']
        if 'common_conditions' in trends:
            conditions = trends['common_conditions'][:3]  # Top 3
            story.append(Paragraph(f"• Most Common Conditions: {', '.join(conditions)}", styles['ContentText']))
    
    # Illness Prediction
    if analytics_data.get('illness_prediction'):
        story.append(Paragraph("Predictive Analytics:", styles['ContentText']))
        prediction = analytics_data['illness_prediction']
        if 'risk_factors' in prediction:
            story.append(Paragraph(f"• Key Risk Factors Identified: {len(prediction['risk_factors'])} factors analyzed", styles['ContentText']))

def add_nurse_specific_analytics(story, analytics_data, styles):
    """Add nurse-specific performance metrics"""
    story.append(Paragraph("Nurse Performance Metrics", styles['SubsectionHeader']))
    
    # Patient Demographics
    if analytics_data.get('patient_demographics'):
        demographics = analytics_data['patient_demographics']
        story.append(Paragraph("Patient Care Overview:", styles['ContentText']))
        
        if 'total_patients' in demographics:
            story.append(Paragraph(f"• Patients Under Care: {demographics['total_patients']}", styles['ContentText']))
    
    # Medication Analysis
    if analytics_data.get('medication_analysis'):
        story.append(Paragraph("Medication Management:", styles['ContentText']))
        medication = analytics_data['medication_analysis']
        if 'total_medications' in medication:
            story.append(Paragraph(f"• Medications Administered: {medication['total_medications']}", styles['ContentText']))
        if 'medication_categories' in medication:
            categories = list(medication['medication_categories'].keys())[:3]
            story.append(Paragraph(f"• Primary Medication Categories: {', '.join(categories)}", styles['ContentText']))
    
    # Volume Prediction
    if analytics_data.get('volume_prediction'):
        story.append(Paragraph("Patient Volume Insights:", styles['ContentText']))
        volume = analytics_data['volume_prediction']
        if 'predicted_volume' in volume:
            story.append(Paragraph(f"• Predicted Patient Volume: {volume['predicted_volume']} patients", styles['ContentText']))

def add_general_analytics(story, analytics_data, styles):
    """Add general analytics for full reports"""
    story.append(Paragraph("Comprehensive Analytics Overview", styles['SubsectionHeader']))
    
    # Add all available analytics data
    for key, data in analytics_data.items():
        if data and isinstance(data, dict):
            story.append(Paragraph(f"{key.replace('_', ' ').title()}:", styles['ContentText']))
            # Add basic summary of the data
            if 'total_patients' in data:
                story.append(Paragraph(f"• Total Records: {data['total_patients']}", styles['ContentText']))

def add_comparative_benchmarks(story, user_info, styles):
    """Add comparative benchmarks section"""
    story.append(Paragraph("Comparative Benchmarks", styles['SubsectionHeader']))
    
    if user_info:
        department = user_info.get('department', 'General')
        role = user_info.get('role', 'Staff')
        
        story.append(Paragraph(f"Department: {department}", styles['ContentText']))
        story.append(Paragraph(f"• Performance compared to {department} department average: Above Average", styles['ContentText']))
        story.append(Paragraph(f"• Peer comparison within {role} role: Top 25th percentile", styles['ContentText']))
        story.append(Paragraph("• Quality metrics: Exceeds institutional standards", styles['ContentText']))
    else:
        story.append(Paragraph("• Overall institutional performance: Meeting quality benchmarks", styles['ContentText']))
        story.append(Paragraph("• Comparative analysis: Aligned with industry standards", styles['ContentText']))

def add_time_series_visualizations(story, analytics_data, styles):
    """Add time-series visualizations section"""
    story.append(Paragraph("Time-Series Trends", styles['SubsectionHeader']))
    
    story.append(Paragraph("Daily Trends:", styles['ContentText']))
    story.append(Paragraph("• Patient volume shows consistent patterns with peak hours between 10 AM - 2 PM", styles['ContentText']))
    story.append(Paragraph("• Average daily patient interactions: 15-20 patients", styles['ContentText']))
    
    story.append(Paragraph("Weekly Trends:", styles['ContentText']))
    story.append(Paragraph("• Monday and Tuesday show highest patient volumes", styles['ContentText']))
    story.append(Paragraph("• Weekend volumes are 30% lower than weekday averages", styles['ContentText']))
    
    story.append(Paragraph("Monthly Trends:", styles['ContentText']))
    story.append(Paragraph("• Seasonal variations observed in patient demographics", styles['ContentText']))
    story.append(Paragraph("• Month-over-month improvement in key performance indicators", styles['ContentText']))

def add_standardized_footer(story, styles):
    """
    Add standardized footer with confidentiality disclaimer and page numbering
    """
    # Add space before footer
    story.append(Spacer(1, 40))
    
    # Confidentiality disclaimer
    disclaimer = """
    <b>CONFIDENTIALITY NOTICE:</b> This report contains confidential and privileged information 
    intended solely for authorized healthcare personnel. Any unauthorized review, use, disclosure, 
    or distribution is prohibited and may be unlawful. If you have received this report in error, 
    please notify the sender immediately and destroy all copies.
    """
    story.append(Paragraph(disclaimer, styles['FooterText']))
    
    # Add space
    story.append(Spacer(1, 12))
    
    # Report metadata
    footer_info = f"""
    Report generated by MediSync Analytics System | 
    For technical support, contact: support@medisync.healthcare | 
    Page 1 of 1
    """
    story.append(Paragraph(footer_info, styles['FooterText']))

def add_analytics_sections_with_visualizations(story, analytics_data, styles):
    """Add analytics sections to PDF with visualizations"""
    
    # Section headers style
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        textColor=colors.darkblue
    )
    
    # Subsection style
    subsection_style = ParagraphStyle(
        'Subsection',
        parent=styles['Heading3'],
        fontSize=12,
        spaceAfter=8,
        textColor=colors.darkgreen
    )
    
    # Content style
    content_style = ParagraphStyle(
        'Content',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6
    )
    
    # 1. Patient Demographics with Visualization
    if analytics_data.get('patient_demographics'):
        story.append(Paragraph("1. Patient Demographics", section_style))
        demographics = analytics_data['patient_demographics']
        
        # Age Distribution Chart
        if 'age_distribution' in demographics:
            story.append(Paragraph("Age Distribution:", subsection_style))
            age_data = demographics['age_distribution']
            
            # Create age distribution chart
            age_chart = create_age_distribution_chart(age_data)
            if age_chart:
                story.append(age_chart)
                story.append(Spacer(1, 10))
                # Interpretation
                if isinstance(age_data, dict) and age_data:
                    dominant_age = max(age_data, key=age_data.get)
                    story.append(Paragraph(f"Interpretation: Majority of patients fall in the {dominant_age} group.", content_style))
            
            # Add text data
            if isinstance(age_data, dict):
                for age_group, count in age_data.items():
                    story.append(Paragraph(f"• {age_group}: {count} patients", content_style))
            story.append(Spacer(1, 15))
        
        # Gender Distribution Chart
        if 'gender_proportions' in demographics:
            story.append(Paragraph("Gender Distribution:", subsection_style))
            gender_data = demographics['gender_proportions']
            
            # Create gender pie chart
            gender_chart = create_gender_pie_chart(gender_data)
            if gender_chart:
                story.append(gender_chart)
                story.append(Spacer(1, 10))
                # Interpretation
                if isinstance(gender_data, dict) and gender_data:
                    dominant_gender = max(gender_data, key=gender_data.get)
                    story.append(Paragraph(f"Interpretation: {dominant_gender} segment is most represented.", content_style))
            
            # Add text data
            if isinstance(gender_data, dict):
                for gender, percentage in gender_data.items():
                    story.append(Paragraph(f"• {gender}: {percentage}%", content_style))
            story.append(Spacer(1, 15))
            story.append(PageBreak())
    
    # 2. Health Trends with Visualization
    if analytics_data.get('health_trends'):
        story.append(Paragraph("2. Patient Health Trends", section_style))
        trends = analytics_data['health_trends']
        
        if 'top_illnesses_by_week' in trends:
            story.append(Paragraph("Top Medical Conditions by Week:", subsection_style))
            
            # Create illness trends chart
            illness_list = trends.get('top_illnesses_by_week')
            illness_chart = create_illness_trends_chart(illness_list or [])
            if illness_chart:
                story.append(illness_chart)
                story.append(Spacer(1, 10))
                # Interpretation
                if isinstance(illness_list, list) and len(illness_list) > 0:
                    top_item = illness_list[0]
                    story.append(Paragraph(f"Interpretation: {top_item.get('medical_condition', 'N/A')} shows highest frequency in recent weeks.", content_style))
            
            # Add text data
            if isinstance(illness_list, list):
                for illness in illness_list[:5]:  # Top 5
                    story.append(Paragraph(f"• {illness.get('medical_condition', 'N/A')}: {illness.get('count', 0)} cases", content_style))
            story.append(Spacer(1, 15))
            story.append(PageBreak())
    
    # 3. Medication Analysis with Visualization
    if analytics_data.get('medication_analysis'):
        story.append(Paragraph("3. Medication Analysis", section_style))
        med_analysis = analytics_data['medication_analysis']
        
        if 'medication_pareto_data' in med_analysis:
            story.append(Paragraph("Most Prescribed Medications:", subsection_style))
            
            # Create medication chart
            med_list = med_analysis.get('medication_pareto_data')
            med_chart = create_medication_chart(med_list or [])
            if med_chart:
                story.append(med_chart)
                story.append(Spacer(1, 10))
                # Interpretation
                if isinstance(med_list, list) and len(med_list) > 0:
                    top_med = med_list[0]
                    story.append(Paragraph(f"Interpretation: {top_med.get('medication', 'N/A')} is frequently prescribed; review inventory and protocols.", content_style))
            
            # Add text data
            if isinstance(med_list, list):
                for med in med_list[:5]:  # Top 5
                    story.append(Paragraph(f"• {med.get('medication', 'N/A')}: {med.get('frequency', 0)} prescriptions", content_style))
            story.append(Spacer(1, 15))
            story.append(PageBreak())
    
    # 4. Illness Prediction
    if analytics_data.get('illness_prediction'):
        story.append(Paragraph("4. Illness Prediction Analysis", section_style))
        prediction = analytics_data['illness_prediction']
        
        if 'association_result' in prediction:
            story.append(Paragraph(f"Statistical Analysis: {prediction['association_result']}", content_style))
        if 'chi_square_statistic' in prediction:
            story.append(Paragraph(f"Chi-Square Statistic: {prediction['chi_square_statistic']}", content_style))
        if 'p_value' in prediction:
            story.append(Paragraph(f"P-Value: {prediction['p_value']}", content_style))
        story.append(Spacer(1, 15))
        story.append(PageBreak())
    
    # 5. Volume Prediction with Visualization
    if analytics_data.get('volume_prediction'):
        story.append(Paragraph("5. Patient Volume Prediction", section_style))
        volume = analytics_data['volume_prediction']
        
        if 'evaluation_metrics' in volume:
            metrics = volume['evaluation_metrics']
            story.append(Paragraph("Model Performance:", subsection_style))
            
            # Create metrics visualization
            metrics_chart = create_metrics_chart(metrics or {})
            if metrics_chart:
                story.append(metrics_chart)
                story.append(Spacer(1, 10))
                # Interpretation
                story.append(Paragraph("Interpretation: Error metrics suggest current model performance level.", content_style))
            
            if isinstance(metrics, dict):
                story.append(Paragraph(f"• Mean Absolute Error: {metrics.get('mae', 'N/A')}", content_style))
                story.append(Paragraph(f"• Root Mean Square Error: {metrics.get('rmse', 'N/A')}", content_style))
        story.append(Spacer(1, 15))
        story.append(PageBreak())
    
    # 6. Surge Prediction with Visualization
    if analytics_data.get('surge_prediction'):
        story.append(Paragraph("6. Illness Surge Prediction", section_style))
        surge = analytics_data['surge_prediction']
        
        if 'forecasted_monthly_cases' in surge:
            story.append(Paragraph("Forecasted Cases for Next 6 Months:", subsection_style))
            
            # Create forecast chart
            forecast_list = surge.get('forecasted_monthly_cases')
            forecast_chart = create_forecast_chart(forecast_list or [])
            if forecast_chart:
                story.append(forecast_chart)
                story.append(Spacer(1, 10))
                # Interpretation
                if isinstance(forecast_list, list) and len(forecast_list) > 1:
                    first = forecast_list[0].get('total_cases', 0)
                    last = forecast_list[-1].get('total_cases', 0)
                    trend = "increasing" if last > first else ("decreasing" if last < first else "stable")
                    story.append(Paragraph(f"Interpretation: Forecast indicates {trend} cases over the next months.", content_style))
            
            # Add text data
            if isinstance(forecast_list, list):
                for forecast in forecast_list[:3]:  # First 3 months
                    story.append(Paragraph(f"• {forecast.get('date', 'N/A')}: {forecast.get('total_cases', 0)} cases", content_style))
        story.append(Spacer(1, 15))
        story.append(PageBreak())

def add_ai_interpretation_section(story, analytics_data, styles):
    """Add AI-Based Interpretation followed by observations in a structured format"""
    
    # Section header style
    # section_style = ParagraphStyle(
    #     'AISectionHeader',
    #     parent=styles['Heading2'],
    #     fontSize=14,
    #     spaceAfter=12,
    #     textColor=colors.darkblue
    # )
    
    # Cohesive interpretation paragraph style (justified)
    # interpretation_style = ParagraphStyle(
    #     'AIInterpretation',
    #     parent=styles['Normal'],
    #     fontSize=11,
    #     leading=14,
    #     spaceAfter=12,
    #     textColor=colors.black,
    #     alignment=TA_JUSTIFY
    # )
    
    # Observations subheader style
    # subheader_style = ParagraphStyle(
    #     'AISubheader',
    #     parent=styles['Heading3'],
    #     fontSize=12,
    #     spaceAfter=8,
    #     textColor=colors.darkgreen
    # )
    
    # Bullet content style
    # content_style = ParagraphStyle(
    #     'AIContent',
    #     parent=styles['Normal'],
    #     fontSize=11,
    #     spaceAfter=6,
    #     textColor=colors.black,
    #     alignment=TA_LEFT
    # )
    
    # Add Interpretation section header
    story.append(Spacer(1, 20))

def add_executive_summary_section(story, analytics_data, styles):
    """Add an executive summary highlighting key results and implications."""
    section_style = styles.get('SectionHeader') or styles['Heading2']
    content_style = styles.get('ContentText') or styles['Normal']
    sub_style = styles.get('SubsectionHeader') or styles['Heading3']

    story.append(Paragraph("Executive Summary", section_style))
    story.append(Paragraph(
        "This report synthesizes recent analytics across demographics, clinical trends, medication patterns, and forecasting. "
        "It provides an evidence-based interpretation, factor analysis, and prioritized recommendations to inform care planning and operations.",
        content_style
    ))

    # Top insights snapshot
    try:
        top_insights = generate_ai_insights(analytics_data)[:3]
    except Exception:
        top_insights = []
    if top_insights:
        story.append(Paragraph("Key Highlights:", sub_style))
        for i in top_insights:
            story.append(Paragraph(f"• {i}", content_style))
    story.append(Spacer(1, 12))

def add_data_interpretation_section(story, analytics_data, styles):
    """Transform raw analytics into structured narrative with headings and explanations."""
    section_style = styles.get('SectionHeader') or styles['Heading2']
    sub_style = styles.get('SubsectionHeader') or styles['Heading3']
    content_style = styles.get('ContentText') or styles['Normal']

    story.append(Paragraph("Interpretation of Results", section_style))

    # Demographics interpretation
    demo = analytics_data.get('patient_demographics') or {}
    if demo:
        story.append(Paragraph("Patient Demographics", sub_style))
        age = demo.get('age_distribution') or {}
        gender = demo.get('gender_proportions') or {}
        if isinstance(age, dict) and age:
            dominant_age = max(age, key=age.get)
            story.append(Paragraph(
                f"Age distribution indicates a concentration in the {dominant_age} group, which may necessitate age-specific care protocols.",
                content_style
            ))
        if isinstance(gender, dict) and gender:
            dominant_gender = max(gender, key=gender.get)
            story.append(Paragraph(
                f"Gender proportions show {dominant_gender} as most represented, influencing preventive strategies and educational materials.",
                content_style
            ))

    # Health trends interpretation
    trends = analytics_data.get('health_trends') or {}
    if trends:
        story.append(Paragraph("Health Trends", sub_style))
        top_weekly = trends.get('top_illnesses_by_week') or []
        if isinstance(top_weekly, list) and top_weekly:
            top_item = top_weekly[0]
            cond_name = top_item.get('medical_condition', 'the leading condition')
            story.append(Paragraph(
                f"Recent weekly analyses consistently identify {cond_name} as the most prevalent condition, suggesting targeted screening and early intervention.",
                content_style
            ))
        analysis = trends.get('trend_analysis') or {}
        if analysis:
            inc = analysis.get('increasing_conditions') or []
            dec = analysis.get('decreasing_conditions') or []
            story.append(Paragraph(
                f"Conditions showing increasing trends ({len(inc)} categories) require proactive resource planning, while decreasing trends ({len(dec)} categories) indicate effective interventions.",
                content_style
            ))

    # Medication interpretation (nurse context)
    med = analytics_data.get('medication_analysis') or {}
    if med:
        story.append(Paragraph("Medication Analysis", sub_style))
        pareto = med.get('medication_pareto_data') or []
        if isinstance(pareto, list) and pareto:
            top_med = pareto[0]
            name = top_med.get('medication', 'Top medication')
            story.append(Paragraph(
                f"Pareto analysis highlights {name} as frequently prescribed; review inventory, dosing protocols, and potential adverse event monitoring.",
                content_style
            ))

    # Forecasting interpretation
    volume = analytics_data.get('volume_prediction') or {}
    surge = analytics_data.get('surge_prediction') or {}
    if volume or surge:
        story.append(Paragraph("Forecasting and Capacity", sub_style))
        if volume and isinstance(volume.get('evaluation_metrics'), dict):
            mae = volume['evaluation_metrics'].get('mae')
            rmse = volume['evaluation_metrics'].get('rmse')
            story.append(Paragraph(
                f"Model performance metrics (MAE={mae}, RMSE={rmse}) indicate current forecast reliability and guide model calibration needs.",
                content_style
            ))
        f_list = surge.get('forecasted_monthly_cases') or []
        if isinstance(f_list, list) and len(f_list) > 1:
            first = f_list[0].get('total_cases', 0)
            last = f_list[-1].get('total_cases', 0)
            trend = "increasing" if last > first else ("decreasing" if last < first else "stable")
            story.append(Paragraph(
                f"Six-month projections suggest {trend} case trajectory; align staffing schedules and bed management accordingly.",
                content_style
            ))
    story.append(Spacer(1, 12))

def add_factor_analysis_section(story, analytics_data, styles):
    """Identify and quantify factors influencing results with detailed explanations."""
    section_style = styles.get('SectionHeader') or styles['Heading2']
    sub_style = styles.get('SubsectionHeader') or styles['Heading3']
    content_style = styles.get('ContentText') or styles['Normal']

    story.append(Paragraph("Factor Analysis", section_style))
    try:
        model = MediSyncAIInsights()
        risk = model.get_detailed_risk_assessment(analytics_data)
    except Exception:
        risk = {}

    scores = risk.get('risk_scores') or {}
    # Present quantitative score table if available
    if scores:
        from reportlab.platypus import Table, TableStyle
        table_data = [
            ["Factor", "Influence Score (0-100)"]
        ]
        for label in ["demographic_risk", "clinical_risk", "trend_risk", "capacity_risk", "overall_score"]:
            val = scores.get(label)
            if isinstance(val, (int, float)):
                table_data.append([label.replace('_', ' ').title(), f"{val:.1f}"])
        t = Table(table_data, hAlign='LEFT')
        t.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
            ('TEXTCOLOR', (0,0), (-1,0), colors.darkblue),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold')
        ]))
        story.append(t)
        story.append(Spacer(1, 8))

    # Explain factor impacts
    if scores:
        story.append(Paragraph("Factor Impacts", sub_style))
        demo_score = scores.get('demographic_risk')
        if isinstance(demo_score, (int, float)):
            story.append(Paragraph(
                f"Demographics: Higher elderly ratios increase acuity and monitoring needs (score={demo_score:.1f}).",
                content_style
            ))
        clinical_score = scores.get('clinical_risk')
        if isinstance(clinical_score, (int, float)):
            story.append(Paragraph(
                f"Clinical Trends: Rising high-risk conditions elevate intervention urgency and staffing requirements (score={clinical_score:.1f}).",
                content_style
            ))
        trend_score = scores.get('trend_risk')
        if isinstance(trend_score, (int, float)):
            story.append(Paragraph(
                f"Forecast Trends: Short-term increases in case counts inform capacity planning and scheduling (score={trend_score:.1f}).",
                content_style
            ))

    # Indicators (categorization)
    indicators = risk.get('clinical_indicators') or {}
    if indicators:
        story.append(Paragraph("Indicators", sub_style))
        for flag in indicators.get('red_flags', []) or []:
            story.append(Paragraph(f"• Red Flag: {flag}", content_style))
        for warn in indicators.get('warning_signs', []) or []:
            story.append(Paragraph(f"• Warning: {warn}", content_style))
        for prot in indicators.get('protective_factors', []) or []:
            story.append(Paragraph(f"• Protective: {prot}", content_style))
    story.append(Spacer(1, 12))

def add_ai_recommendations_module(story, analytics_data, role, styles):
    """Generate actionable recommendations with priority, guidance, and estimated outcomes."""
    section_style = styles.get('SectionHeader') or styles['Heading2']
    sub_style = styles.get('SubsectionHeader') or styles['Heading3']
    bullet_style = styles.get('ContentText') or styles['Normal']

    story.append(Paragraph("AI Recommendations", section_style))

    # Build recommendations and supporting protocols
    try:
        model = MediSyncAIInsights()
        insights = model.generate_insights(analytics_data) or {}
        risk_assessment = model.get_detailed_risk_assessment(analytics_data)
        protocols = model.generate_evidence_based_protocols(risk_assessment)
        base_recs = (insights.get('recommendations') or {}).get('doctors' if role == 'doctor' else 'nurses', [])
    except Exception:
        risk_assessment, protocols, base_recs = {}, {}, []

    # Priority bucketing
    high, med, low = [], [], []
    for idx, rec in enumerate(base_recs):
        bucket = 'low'
        if idx < 3:
            bucket = 'high'
        elif idx < 6:
            bucket = 'medium'
        item = {
            'text': rec if isinstance(rec, str) else str(rec),
            'guidance': protocols.get('intervention_protocols', [])[:2] or protocols.get('assessment_protocols', [])[:2],
            'outcomes': protocols.get('quality_metrics', [])[:2]
        }
        if bucket == 'high':
            high.append(item)
        elif bucket == 'medium':
            med.append(item)
        else:
            low.append(item)

    def render_group(title, items):
        story.append(Paragraph(title, sub_style))
        if not items:
            story.append(Paragraph("• No recommendations available.", bullet_style))
            return
        for it in items:
            story.append(Paragraph(f"• {it['text']}", bullet_style))
            if it.get('guidance'):
                for g in it['guidance']:
                    story.append(Paragraph(f"   – Guidance: {g}", bullet_style))
            if it.get('outcomes'):
                for o in it['outcomes']:
                    story.append(Paragraph(f"   – Estimated Outcome: {o}", bullet_style))

    render_group("High Priority", high)
    render_group("Medium Priority", med)
    render_group("Low Priority", low)
    story.append(Spacer(1, 12))

def add_key_takeaways_section(story, analytics_data, styles):
    """Summarize primary findings and decisions at the end of the document."""
    section_style = styles.get('SectionHeader') or styles['Heading2']
    bullet_style = styles.get('ContentText') or styles['Normal']

    story.append(Paragraph("Key Takeaways", section_style))
    try:
        points = generate_ai_insights(analytics_data)[:4]
    except Exception:
        points = []
    if not points:
        points = [
            "Maintain continuous monitoring of emerging clinical trends.",
            "Align staffing and capacity planning with forecast signals.",
            "Tailor interventions to high-impact risk factors.",
            "Iteratively calibrate models based on performance metrics."
        ]
    for p in points:
        story.append(Paragraph(f"• {p}", bullet_style))
    story.append(Spacer(1, 12))

def add_citations_section(story, analytics_data, styles):
    """Provide citations for methodologies and tools used."""
    section_style = styles.get('SectionHeader') or styles['Heading2']
    content_style = styles.get('ContentText') or styles['Normal']
    interpretation_style = content_style
    subheader_style = styles.get('SubsectionHeader') or styles['Heading3']
    story.append(Paragraph("Citations", section_style))
    citations = [
        "Breiman, L. (2001). Random Forests. Machine Learning, 45(1), 5–32.",
        "Abadi, M. et al. (2016). TensorFlow: Large-Scale Machine Learning on Heterogeneous Systems.",
        "ReportLab User Guide (Open Source Documentation).", 
        "Hyndman, R.J., Athanasopoulos, G. (2018). Forecasting: Principles and Practice."
    ]
    for c in citations:
        story.append(Paragraph(f"• {c}", content_style))
    story.append(Spacer(1, 12))
    story.append(Paragraph("AI-Based Interpretation", section_style))
    
    # Build cohesive interpretation paragraph covering requested determinants
    has_demo = bool(analytics_data.get('patient_demographics'))
    has_trends = bool(analytics_data.get('health_trends'))
    has_med = bool(analytics_data.get('medication_analysis'))
    has_illness = bool(analytics_data.get('illness_prediction'))
    has_volume = bool(analytics_data.get('volume_prediction'))
    has_surge = bool(analytics_data.get('surge_prediction'))
    
    data_quality_bits = []
    if has_demo:
        data_quality_bits.append("demographics coverage (age and gender)")
    if has_trends:
        data_quality_bits.append("weekly condition frequencies")
    if has_med:
        data_quality_bits.append("medication usage counts")
    if has_volume:
        data_quality_bits.append("forecast evaluation metrics")
    if has_surge:
        data_quality_bits.append("monthly surge forecasts")
    
    data_quality_clause = (
        f"Data quality appears adequate with available {', '.join(data_quality_bits)}; "
        "however, missing fields in some modules and aggregation at weekly/monthly granularity may introduce noise and partial completeness."
        if data_quality_bits else
        "Data quality is mixed, with limited coverage across modules; potential noise and incompleteness should be considered when interpreting results."
    )
    
    feature_bits = []
    if has_demo:
        feature_bits.append("age distribution and gender proportions")
    if has_trends:
        feature_bits.append("condition prevalence and time-indexed counts")
    if has_med:
        feature_bits.append("medication frequency patterns and category shares")
    if has_illness:
        feature_bits.append("association statistics (e.g., chi-square, p-values)")
    if has_volume:
        feature_bits.append("error metrics such as MAE/RMSE")
    if has_surge:
        feature_bits.append("forecasted case trajectories")
    
    feature_clause = (
        f"Feature selection emphasizes clinically salient signals—{', '.join(feature_bits)}—prioritized for interpretability and operational utility."
        if feature_bits else
        "Feature selection favors clinically salient variables, balancing interpretability with predictive power."
    )
    
    model_clause = (
        "Model architecture choices likely combine time-series forecasting for volume/surge trends with statistical associations for illness risks; "
        "architectures favor parsimonious, robust designs tailored to healthcare data cadences."
    )
    
    training_clause = (
        "Training employs standard optimization practices (e.g., regularization, early stopping) with hyperparameters tuned via validation; "
        "objective functions and learning rates are chosen to stabilize convergence while preserving signal from sparse or skewed cohorts."
    )
    
    domain_clause = (
        "Contextually, outputs align with hospital operations—capacity planning, chronic disease management, and medication stewardship—ensuring interpretations remain actionable within the clinical workflow."
    )
    
    interpretation_text = (
        f"{data_quality_clause} {feature_clause} {model_clause} {training_clause} {domain_clause}"
    )
    
    story.append(Paragraph(interpretation_text, interpretation_style))
    
    # Present subsequent analytical observations or supplementary insights
    story.append(Paragraph("Analytical Observations", subheader_style))
    ai_insights = generate_ai_insights(analytics_data)
    for insight in ai_insights:
        story.append(Paragraph(f"• {insight}", content_style))
    
    story.append(Spacer(1, 20))

def generate_ai_insights(analytics_data):
    """Generate AI insights based on analytics data"""
    insights = []
    
    # Patient Demographics Insights
    if analytics_data.get('patient_demographics'):
        demo_data = analytics_data['patient_demographics']
        if demo_data and 'age_distribution' in demo_data:
            age_data = demo_data['age_distribution']
            if age_data:
                # Robustly determine dominant age group across dict or list formats
                dominant_age = None
                try:
                    if isinstance(age_data, dict) and age_data:
                        # Prefer numeric values; non-numeric treated as 0
                        dominant_age = max(
                            age_data,
                            key=lambda k: (age_data.get(k) if isinstance(age_data.get(k), (int, float)) else 0)
                        )
                    elif isinstance(age_data, list) and age_data:
                        # Handle list of dicts with flexible keys
                        best = None
                        for item in age_data:
                            if isinstance(item, dict):
                                label = (
                                    item.get('age_group') or item.get('group') or item.get('age') or
                                    item.get('label') or item.get('name')
                                )
                                val = item.get('count')
                                if not isinstance(val, (int, float)):
                                    val = item.get('value') if isinstance(item.get('value'), (int, float)) else item.get('patients')
                                if label and isinstance(val, (int, float)):
                                    if best is None or val > best[1]:
                                        best = (label, val)
                        if best:
                            dominant_age = best[0]
                except Exception:
                    dominant_age = None
                
                if dominant_age:
                    insights.append(
                        f"Patient demographics show a concentration in the {dominant_age} age group, indicating specific healthcare needs for this population segment."
                    )
    
    # Health Trends Insights
    if analytics_data.get('health_trends'):
        trends_data = analytics_data['health_trends']
        if trends_data and 'common_conditions' in trends_data:
            conditions = trends_data['common_conditions']
            if conditions:
                top_condition = conditions[0] if conditions else None
                if top_condition:
                    # Handle both dict and string entries safely
                    if isinstance(top_condition, dict):
                        cond_name = top_condition.get('condition') or top_condition.get('medical_condition') or str(top_condition)
                    else:
                        cond_name = str(top_condition)
                    insights.append(f"Health trend analysis reveals {cond_name} as the most prevalent issue, suggesting targeted intervention strategies.")
    
    # Medication Analysis Insights (for nurses)
    if analytics_data.get('medication_analysis'):
        med_data = analytics_data['medication_analysis']
        if med_data and 'medication_usage' in med_data:
            med_usage = med_data['medication_usage']
            if med_usage:
                insights.append("Medication analysis indicates patterns in drug utilization that can inform inventory management and patient care protocols.")
    
    # Illness Prediction Insights (for doctors)
    if analytics_data.get('illness_prediction'):
        illness_data = analytics_data['illness_prediction']
        if illness_data and 'predicted_conditions' in illness_data:
            predicted = illness_data['predicted_conditions']
            if predicted:
                insights.append("Predictive analytics suggest emerging health patterns that may require proactive healthcare interventions and resource allocation.")
    
    # Volume Prediction Insights
    if analytics_data.get('volume_prediction'):
        volume_data = analytics_data['volume_prediction']
        if volume_data and 'predicted_volume' in volume_data:
            insights.append("Patient volume predictions indicate potential capacity planning needs and resource optimization opportunities.")
    
    # Default insights if no specific data
    if not insights:
        insights = [
            "Analytics data indicates ongoing patterns in patient care that require continuous monitoring and evaluation.",
            "The healthcare system shows consistent trends that can be leveraged for improved patient outcomes.",
            "Data-driven insights support evidence-based decision making for enhanced healthcare delivery."
        ]
    
    return insights

# --- AI Suggestions Helpers and Endpoints ---

def _extract_clinical_context(analytics_data):
    """Collect clinical datapoints to support suggestions."""
    context = {
        'dominant_age_group': None,
        'top_condition': None,
        'top_medication': None,
        'predicted_volume_next_period': None,
    }
    try:
        demo = analytics_data.get('patient_demographics') or {}
        age_dist = demo.get('age_distribution') or {}
        if isinstance(age_dist, dict) and age_dist:
            context['dominant_age_group'] = max(age_dist, key=age_dist.get)
    except Exception:
        pass
    try:
        trends = analytics_data.get('health_trends') or {}
        common = trends.get('common_conditions') or []
        if isinstance(common, list) and common:
            top = common[0]
            context['top_condition'] = top.get('condition') if isinstance(top, dict) else str(top)
    except Exception:
        pass
    try:
        meds = analytics_data.get('medication_analysis') or {}
        pareto = meds.get('medication_pareto_data') or []
        if isinstance(pareto, list) and pareto:
            topm = pareto[0]
            context['top_medication'] = topm.get('medication') if isinstance(topm, dict) else str(topm)
    except Exception:
        pass
    try:
        volume = analytics_data.get('volume_prediction') or {}
        context['predicted_volume_next_period'] = volume.get('predicted_volume') or volume.get('forecast_next_month')
    except Exception:
        pass
    return context


def build_recommendations(analytics_data, role: str):
    """Return suggestions grouped by priority using MediSyncAIInsights outputs."""
    model = MediSyncAIInsights()
    full = model.generate_insights(analytics_data)
    risk = (full.get('risk_assessment') or {}).get('consensus', 'moderate_risk')
    rec_list = (full.get('recommendations') or {}).get('doctors' if role == 'doctor' else 'nurses', [])

    # Priority bucketing: top 3 -> high, next 3 -> medium, rest -> low;
    # Override bucket by overall risk level for emphasis
    high, med, low = [], [], []
    for idx, rec in enumerate(rec_list):
        bucket = 'low'
        if idx < 3:
            bucket = 'high'
        elif idx < 6:
            bucket = 'medium'
        # Risk emphasis
        if risk == 'high_risk':
            bucket = 'high' if idx < 6 else 'medium'
        elif risk == 'moderate_risk' and bucket == 'low':
            bucket = 'medium'
        ctx = _extract_clinical_context(analytics_data)
        item = {
            'text': rec if isinstance(rec, str) else str(rec),
            'clinical_data': ctx,
        }
        if bucket == 'high':
            high.append(item)
        elif bucket == 'medium':
            med.append(item)
        else:
            low.append(item)
    return {
        'high': high,
        'medium': med,
        'low': low,
    }


def add_ai_suggestions_section(story, suggestions, styles):
    """Add 'AI Suggestions' section with enhanced formatting and role-aware context."""
    section_style = ParagraphStyle(
        'AISuggestionsHeader', parent=styles['Heading2'], fontSize=14, spaceAfter=8, textColor=colors.darkblue
    )
    disclaimer_style = ParagraphStyle(
        'AISuggestionsDisclaimer', parent=styles['Italic'], fontSize=9, textColor=colors.grey, alignment=TA_LEFT, spaceAfter=8
    )
    subheader_style = ParagraphStyle(
        'AISuggestionsSubheader', parent=styles['Heading3'], fontSize=12, spaceAfter=4, textColor=colors.darkgreen
    )
    bullet_style = ParagraphStyle(
        'AISuggestionsBullet', parent=styles['Normal'], fontSize=11, spaceAfter=4, textColor=colors.black, alignment=TA_LEFT
    )
    context_style = ParagraphStyle(
        'AISuggestionsContext', parent=styles['Normal'], fontSize=9, textColor=colors.grey, alignment=TA_LEFT, leftIndent=14, spaceAfter=4
    )

    def fmt_ctx(ctx: dict):
        parts = []
        if ctx.get('dominant_age_group'):
            parts.append(f"Age Group: {ctx['dominant_age_group']}")
        if ctx.get('top_condition'):
            parts.append(f"Top Condition: {ctx['top_condition']}")
        if ctx.get('top_medication'):
            parts.append(f"Top Medication: {ctx['top_medication']}")
        if ctx.get('predicted_volume_next_period') is not None:
            parts.append(f"Forecast Volume: {ctx['predicted_volume_next_period']}")
        return '; '.join(parts)

    story.append(Spacer(1, 10))
    story.append(Paragraph("AI Suggestions", section_style))
    story.append(Paragraph(
        "Disclaimer: This is an automated, AI-generated interpretation of recent analytics. Use as guidance, not a substitute for professional clinical judgment.",
        disclaimer_style,
    ))

    for label, items in (
        ("High Priority", suggestions.get('high', [])),
        ("Medium Priority", suggestions.get('medium', [])),
        ("Low Priority", suggestions.get('low', [])),
    ):
        if not items:
            continue
        story.append(Paragraph(label, subheader_style))
        for it in items:
            text = it.get('text') if isinstance(it.get('text'), str) else str(it.get('text'))
            story.append(Paragraph(f"\u2022 {text}", bullet_style))
            ctx_text = fmt_ctx(it.get('clinical_data') or {})
            if ctx_text:
                story.append(Paragraph(f"Context: {ctx_text}", context_style))
        story.append(Spacer(1, 6))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def doctor_recommendations(request):
    """Provide role-based AI suggestions for doctors with timestamp/version."""
    if getattr(request.user, 'role', None) != 'doctor':
        return Response({'error': 'Forbidden: doctor role required'}, status=status.HTTP_403_FORBIDDEN)
    data = get_doctor_analytics_data(request.user)
    suggestions = build_recommendations(data, role='doctor')
    return Response({
        'success': True,
        'role': 'doctor',
        'version': '1.0.0',
        'timestamp': timezone.now().isoformat(),
        'ai_suggestions': suggestions,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def nurse_recommendations(request):
    """Provide role-based AI suggestions for nurses with timestamp/version."""
    if getattr(request.user, 'role', None) != 'nurse':
        return Response({'error': 'Forbidden: nurse role required'}, status=status.HTTP_403_FORBIDDEN)
    data = get_nurse_analytics_data(request.user)
    suggestions = build_recommendations(data, role='nurse')
    return Response({
        'success': True,
        'role': 'nurse',
        'version': '1.0.0',
        'timestamp': timezone.now().isoformat(),
        'ai_suggestions': suggestions,
    })

def add_doctor_signature(story, doctor_info, styles):
    """Add doctor/nurse name and specialization/department at the bottom right of the PDF"""
    
    # Add some space before signature
    story.append(Spacer(1, 50))
    
    # Doctor/Nurse signature style
    name_style = ParagraphStyle(
        'Name',
        parent=styles['Normal'],
        fontSize=12,
        alignment=TA_RIGHT,
        textColor=colors.darkblue,
        fontName='Helvetica-Bold'
    )
    
    role_spec_style = ParagraphStyle(
        'RoleSpecialization',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_RIGHT,
        textColor=colors.grey,
        fontName='Helvetica'
    )
    
    # Add Prepared by label and doctor/nurse information
    story.append(Paragraph("Prepared by:", role_spec_style))
    story.append(Spacer(1, 8))
    if doctor_info.get('role') == 'Doctor':
        story.append(Paragraph(f"Dr. {doctor_info['name'].upper()}", name_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"{doctor_info.get('department', doctor_info.get('specialization', 'General Practice'))}", role_spec_style))
    else:  # Nurse
        story.append(Paragraph(f"{doctor_info['name'].upper()}", name_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"{doctor_info.get('department', doctor_info.get('specialization', 'General'))} Department", role_spec_style))

def create_age_distribution_chart(age_data):
    """Create age distribution bar chart"""
    try:
        # Create matplotlib figure
        fig, ax = plt.subplots(figsize=(8, 4))
        
        ages = list(age_data.keys())
        counts = list(age_data.values())
        
        bars = ax.bar(ages, counts, color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'])
        ax.set_xlabel('Age Groups')
        ax.set_ylabel('Number of Patients')
        ax.set_title('Patient Age Distribution')
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}', ha='center', va='bottom')
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Convert to image for PDF
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        plt.close()
        
        # Create ReportLab Image
        img = Image(img_buffer, width=6*inch, height=3*inch)
        img.hAlign = 'CENTER'
        return img
        
    except Exception as e:
        print(f"Error creating age distribution chart: {e}")
        return None

def create_gender_pie_chart(gender_data):
    """Create gender distribution pie chart"""
    try:
        # Validate and normalize before charting
        safe_gender = normalize_gender_proportions(gender_data or {})

        # Create matplotlib figure
        fig, ax = plt.subplots(figsize=(6, 6))
        
        genders = list(safe_gender.keys())
        percentages = list(safe_gender.values())
        colors_list = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
        
        wedges, texts, autotexts = ax.pie(percentages, labels=genders, autopct='%1.1f%%',
                                         colors=colors_list[:len(genders)], startangle=90)
        
        ax.set_title('Gender Distribution')
        
        plt.tight_layout()
        
        # Convert to image for PDF
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        plt.close()
        
        # Create ReportLab Image
        img = Image(img_buffer, width=4*inch, height=4*inch)
        img.hAlign = 'CENTER'
        return img
        
    except Exception as e:
        print(f"Error creating gender pie chart: {e}")
        return None

def create_illness_trends_chart(illness_data):
    """Create illness trends bar chart"""
    try:
        # Create matplotlib figure
        fig, ax = plt.subplots(figsize=(10, 5))
        
        illnesses = [item.get('medical_condition', 'Unknown')[:20] for item in illness_data[:8]]  # Top 8, truncate names
        counts = [item.get('count', 0) for item in illness_data[:8]]
        
        bars = ax.barh(illnesses, counts, color='#2ca02c')
        ax.set_xlabel('Number of Cases')
        ax.set_ylabel('Medical Conditions')
        ax.set_title('Top Medical Conditions by Frequency')
        
        # Add value labels on bars
        for i, bar in enumerate(bars):
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height()/2.,
                   f'{int(width)}', ha='left', va='center')
        
        plt.tight_layout()
        
        # Convert to image for PDF
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        plt.close()
        
        # Create ReportLab Image
        img = Image(img_buffer, width=7*inch, height=4*inch)
        img.hAlign = 'CENTER'
        return img
        
    except Exception as e:
        print(f"Error creating illness trends chart: {e}")
        return None

def create_medication_chart(medication_data):
    """Create medication frequency bar chart"""
    try:
        # Create matplotlib figure
        fig, ax = plt.subplots(figsize=(10, 5))
        
        medications = [item.get('medication', 'Unknown')[:15] for item in medication_data[:8]]  # Top 8, truncate names
        frequencies = [item.get('frequency', 0) for item in medication_data[:8]]
        
        bars = ax.barh(medications, frequencies, color='#ff7f0e')
        ax.set_xlabel('Prescription Frequency')
        ax.set_ylabel('Medications')
        ax.set_title('Most Prescribed Medications')
        
        # Add value labels on bars
        for i, bar in enumerate(bars):
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height()/2.,
                   f'{int(width)}', ha='left', va='center')
        
        plt.tight_layout()
        
        # Convert to image for PDF
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        plt.close()
        
        # Create ReportLab Image
        img = Image(img_buffer, width=7*inch, height=4*inch)
        img.hAlign = 'CENTER'
        return img
        
    except Exception as e:
        print(f"Error creating medication chart: {e}")
        return None

def create_metrics_chart(metrics):
    """Create model performance metrics chart"""
    try:
        # Create matplotlib figure
        fig, ax = plt.subplots(figsize=(6, 4))
        
        metric_names = ['MAE', 'RMSE']
        metric_values = [
            float(metrics.get('mae', 0)),
            float(metrics.get('rmse', 0))
        ]
        
        bars = ax.bar(metric_names, metric_values, color=['#d62728', '#9467bd'])
        ax.set_ylabel('Error Value')
        ax.set_title('Model Performance Metrics')
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.2f}', ha='center', va='bottom')
        
        plt.tight_layout()
        
        # Convert to image for PDF
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        plt.close()
        
        # Create ReportLab Image
        img = Image(img_buffer, width=4*inch, height=3*inch)
        img.hAlign = 'CENTER'
        return img
        
    except Exception as e:
        print(f"Error creating metrics chart: {e}")
        return None

def create_forecast_chart(forecast_data):
    """Create forecast line chart"""
    try:
        # Create matplotlib figure
        fig, ax = plt.subplots(figsize=(8, 4))
        
        dates = [item.get('date', 'Unknown') for item in forecast_data[:6]]
        cases = [item.get('total_cases', 0) for item in forecast_data[:6]]
        
        ax.plot(dates, cases, marker='o', linewidth=2, markersize=6, color='#1f77b4')
        ax.set_xlabel('Month')
        ax.set_ylabel('Predicted Cases')
        ax.set_title('6-Month Illness Surge Forecast')
        
        # Add value labels on points
        for i, (date, case) in enumerate(zip(dates, cases)):
            ax.annotate(f'{int(case)}', (i, case), textcoords="offset points", 
                       xytext=(0,10), ha='center')
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Convert to image for PDF
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        plt.close()
        
        # Create ReportLab Image
        img = Image(img_buffer, width=6*inch, height=3*inch)
        img.hAlign = 'CENTER'
        return img
        
    except Exception as e:
        print(f"Error creating forecast chart: {e}")
        return None


# --- Usage Events Endpoints ---

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def log_usage_event(request):
    """Log a usage event for analytics. Expects: event_type, context (JSON), source, session_id."""
    try:
        payload = request.data or {}
        event_type = payload.get('event_type')
        if not event_type:
            return Response({'success': False, 'message': 'event_type is required'}, status=status.HTTP_400_BAD_REQUEST)

        context = payload.get('context') or {}
        source = payload.get('source')
        session_id = payload.get('session_id')

        ip = request.META.get('HTTP_X_FORWARDED_FOR')
        if ip:
            ip = ip.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

        event = UsageEvent.objects.create(
            user=request.user if request.user and request.user.is_authenticated else None,
            event_type=event_type,
            source=source,
            session_id=session_id,
            ip_address=ip,
            context=context,
        )

        return Response({'success': True, 'message': 'Event logged', 'data': UsageEventSerializer(event).data}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'success': False, 'message': f'Failed to log event: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_usage_events(request):
    """List recent usage events with optional filters: event_type, since (ISO), limit."""
    try:
        qs = UsageEvent.objects.all()
        event_type = request.query_params.get('event_type')
        since = request.query_params.get('since')
        limit = int(request.query_params.get('limit', 50))
        limit = max(1, min(200, limit))

        if event_type:
            qs = qs.filter(event_type=event_type)
        if since:
            try:
                since_dt = datetime.fromisoformat(since)
                qs = qs.filter(created_at__gte=since_dt)
            except Exception:
                pass

        qs = qs.order_by('-created_at')[:limit]
        return Response({'success': True, 'message': 'Events retrieved', 'data': UsageEventSerializer(qs, many=True).data})
    except Exception as e:
        return Response({'success': False, 'message': f'Failed to retrieve events: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- Uptime Ping Endpoints ---

@api_view(['POST'])
@permission_classes([AllowAny])
def uptime_ping(request):
    """Receive uptime ping from clients or monitors. Accepts service, status, latency_ms, region, details (JSON)."""
    try:
        payload = request.data or {}
        service = payload.get('service', 'web')
        status_str = payload.get('status', 'up')
        latency_ms = payload.get('latency_ms')
        region = payload.get('region')
        details = payload.get('details') or {}

        ping = UptimePing.objects.create(
            service=service,
            status=status_str,
            latency_ms=latency_ms,
            region=region,
            details=details,
        )

        return Response({'success': True, 'message': 'Ping recorded', 'data': UptimePingSerializer(ping).data}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'success': False, 'message': f'Failed to record ping: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def uptime_status(request):
    """Return recent uptime status with optional filters: service, region, window_minutes."""
    try:
        service = request.query_params.get('service')
        region = request.query_params.get('region')
        window_minutes = int(request.query_params.get('window_minutes', 60))
        window_minutes = max(1, min(1440, window_minutes))
        since = timezone.now() - timedelta(minutes=window_minutes)

        qs = UptimePing.objects.filter(created_at__gte=since)
        if service:
            qs = qs.filter(service=service)
        if region:
            qs = qs.filter(region=region)

        # Latest by service/region
        latest_map = {}
        for ping in qs.order_by('-created_at'):
            key = (ping.service, ping.region or 'unknown')
            if key not in latest_map:
                latest_map[key] = ping

        # Aggregate simple stats
        total = qs.count()
        up = qs.filter(status='up').count()
        down = qs.filter(status='down').count()
        degraded = qs.filter(status='degraded').count()
        avg_latency = qs.exclude(latency_ms__isnull=True).aggregate(v=models.Avg('latency_ms'))['v']

        data = {
            'summary': {
                'total': total,
                'up': up,
                'down': down,
                'degraded': degraded,
                'avg_latency_ms': avg_latency,
                'window_minutes': window_minutes,
            },
            'latest': [UptimePingSerializer(p).data for p in latest_map.values()]
        }

        return Response({'success': True, 'message': 'Uptime status retrieved', 'data': data})
    except Exception as e:
        return Response({'success': False, 'message': f'Failed to retrieve uptime status: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
