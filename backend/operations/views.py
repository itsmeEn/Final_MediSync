from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.core.cache import cache
from django.db import DatabaseError
from django.db.models import Q
from datetime import datetime, timedelta

from .models import AppointmentManagement, QueueManagement, PriorityQueue, Notification, DoctorAvailability, Conversation, Message, MessageReaction, MessageNotification, QueueSchedule, QueueStatus, QueueStatusLog
from backend.users.models import User, GeneralDoctorProfile, NurseProfile
from .serializers import DashboardStatsSerializer, ConversationSerializer, MessageSerializer, CreateMessageSerializer, CreateReactionSerializer, UserSerializer, MessageNotificationSerializer, QueueScheduleSerializer, QueueStatusSerializer, QueueStatusLogSerializer, CreateQueueScheduleSerializer, NotificationSerializer
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def doctor_dashboard_stats(request):
    """
    Get dashboard statistics for a doctor
    - Total appointments (today and upcoming)
    - Patients in queue (normal and priority)
    - Notifications (unread messages from patients, nurses, other doctors)
    - Pending assessments (nurse charts awaiting doctor review)
    """
    try:
        # Get the current doctor
        doctor = request.user
        
        # Get today's date
        today = timezone.now().date()
        
        # 1. Total Appointments (today and upcoming)
        total_appointments = AppointmentManagement.objects.filter(
            doctor__user=doctor,
            appointment_date__date__gte=today,
            status__in=['scheduled', 'in_progress']
        ).count()
        
        # 2. Patients in Queue (normal and priority)
        # Normal queue - patients waiting in OPD
        normal_queue = QueueManagement.objects.filter(
            department='OPD',
            status='waiting'
        ).count()
        
        # Priority queue - patients with special needs
        priority_queue = PriorityQueue.objects.filter(
            department='OPD'
        ).count()
        
        total_patients = normal_queue + priority_queue
        
        # 3. Notifications (unread messages from patients, nurses, other doctors)
        notifications = Notification.objects.filter(
            user=doctor,
            is_read=False
        ).count()
        
        # 4. Monthly cancelled appointments for the current month
        # Determine month boundaries in local timezone
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Compute first day of next month
        if month_start.month == 12:
            next_month = month_start.replace(year=month_start.year + 1, month=1)
        else:
            next_month = month_start.replace(month=month_start.month + 1)

        monthly_cancelled = AppointmentManagement.objects.filter(
            doctor__user=doctor,
            status='cancelled',
            appointment_date__date__gte=month_start.date(),
            appointment_date__date__lt=next_month.date()
        ).count()

        # 5. Pending Assessments (nurse charts awaiting doctor review)
        # For now, set to 0 since NurseChart model is not implemented yet
        # Prepare response data
        stats_data = {
            'total_appointments': total_appointments,
            'total_patients': total_patients,
            'normal_queue': normal_queue,
            'priority_queue': priority_queue,
            'notifications': notifications,
            'pending_assessment': 0,
            'monthly_cancelled': monthly_cancelled
        }
        
        serializer = DashboardStatsSerializer(stats_data)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to fetch dashboard statistics: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def doctor_appointments(request):
    """
    Get appointments for the current doctor
    """
    try:
        doctor = request.user
        today = timezone.now().date()
        
        appointments = AppointmentManagement.objects.filter(
            doctor__user=doctor,
            appointment_date__date__gte=today
        ).order_by('appointment_date')
        
        from .serializers import AppointmentSerializer
        serializer = AppointmentSerializer(appointments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to fetch appointments: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def doctor_queue_patients(request):
    """
    Get patients in queue for the current doctor
    """
    try:
        # Get normal queue patients
        normal_queue = QueueManagement.objects.filter(
            department='OPD',
            status='waiting'
        ).order_by('position_in_queue')
        
        # Get priority queue patients
        priority_queue = PriorityQueue.objects.filter(
            department='OPD'
        ).order_by('priority_position')
        
        from .serializers import QueueSerializer, PriorityQueueSerializer
        
        normal_serializer = QueueSerializer(normal_queue, many=True)
        priority_serializer = PriorityQueueSerializer(priority_queue, many=True)
        
        return Response({
            'normal_queue': normal_serializer.data,
            'priority_queue': priority_serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to fetch queue patients: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def doctor_notifications(request):
    """
    Get notifications for the current doctor
    """
    try:
        doctor = request.user
        
        notifications = Notification.objects.filter(
            user=doctor
        ).order_by('-created_at')[:10]  # Get last 10 notifications
        
        from .serializers import NotificationSerializer
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to fetch notifications: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def mark_notification_as_read(request, notification_id):
    """
    Mark a specific notification as read
    """
    try:
        doctor = request.user
        
        notification = Notification.objects.filter(
            id=notification_id,
            user=doctor
        ).first()
        
        if not notification:
            return Response({
                'error': 'Notification not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        notification.is_read = True
        notification.save()
        
        return Response({
            'message': 'Notification marked as read'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to mark notification as read: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read(request):
    """
    Mark all notifications as read for the current doctor
    """
    try:
        doctor = request.user
        
        updated_count = Notification.objects.filter(
            user=doctor,
            is_read=False
        ).update(is_read=True)
        
        return Response({
            'message': f'{updated_count} notifications marked as read'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to mark notifications as read: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_in_appointment(request, appointment_id):
    """
    Mark an appointment as checked-in and create/ensure a queue entry.
    Aligns the appointment calendar with the operational queue lifecycle.
    """
    try:
        appt = AppointmentManagement.objects.filter(appointment_id=appointment_id).first()
        if not appt:
            return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)

        # Only allow patient, assigned doctor, or nurses to check-in
        user = request.user
        is_patient = hasattr(user, 'patient_profile') and appt.patient == getattr(user, 'patient_profile', None)
        is_doctor = hasattr(user, 'doctor_profile') or getattr(user, 'role', '') == 'doctor'
        is_nurse = getattr(user, 'role', '') == 'nurse'
        if not (is_patient or is_doctor or is_nurse):
            return Response({'error': 'Unauthorized to perform check-in'}, status=status.HTTP_403_FORBIDDEN)

        # Update appointment lifecycle
        appt.checked_in_at = timezone.now()
        appt.status = 'checked_in'
        appt.save()

        # Ensure queue entry exists in OPD
        department = 'OPD'
        queue_entry = QueueManagement.objects.filter(patient=appt.patient, department=department, status__in=['waiting', 'in_progress']).order_by('enqueue_time').first()
        if not queue_entry:
            queue_entry = QueueManagement.objects.create(
                patient=appt.patient,
                department=department,
                status='waiting'
            )

        # Refresh QueueStatus metrics
        queue_status, _ = QueueStatus.objects.get_or_create(department=department, defaults={'is_open': True})
        queue_status.total_waiting = (
            QueueManagement.objects.filter(department=department, status='waiting').count() +
            PriorityQueue.objects.filter(department=department, status='waiting').count()
        )
        queue_status.update_status_message()
        queue_status.last_updated_by = user
        queue_status.save()

        from .serializers import AppointmentSerializer, QueueSerializer
        return Response({
            'message': 'Checked in successfully',
            'appointment': AppointmentSerializer(appt).data,
            'queue_entry': QueueSerializer(queue_entry).data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': f'Failed to check in: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_consultation(request, appointment_id):
    """
    Mark an appointment as in progress and start consultation.
    Optionally updates related queue entry to in_progress.
    """
    try:
        appt = AppointmentManagement.objects.filter(appointment_id=appointment_id).first()
        if not appt:
            return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        is_doctor = hasattr(user, 'doctor_profile') or getattr(user, 'role', '') == 'doctor'
        is_nurse = getattr(user, 'role', '') == 'nurse'
        if not (is_doctor or is_nurse):
            return Response({'error': 'Only doctors or nurses can start consultation'}, status=status.HTTP_403_FORBIDDEN)

        appt.consultation_started_at = timezone.now()
        appt.status = 'in_progress'
        appt.save()

        # Update queue entry if present
        department = 'OPD'
        queue_entry = QueueManagement.objects.filter(patient=appt.patient, department=department, status__in=['waiting', 'in_progress']).order_by('position_in_queue', 'enqueue_time').first()
        if queue_entry and queue_entry.status == 'waiting':
            try:
                queue_entry.mark_started()
            except Exception:
                QueueManagement.objects.filter(pk=queue_entry.id).update(status='in_progress', started_at=timezone.now())

        # Refresh queue status current serving
        queue_status, _ = QueueStatus.objects.get_or_create(department=department, defaults={'is_open': True})
        if queue_entry:
            queue_status.current_serving = queue_entry.queue_number
        queue_status.last_updated_by = user
        queue_status.update_status_message()
        queue_status.save()

        from .serializers import AppointmentSerializer
        return Response({'message': 'Consultation started', 'appointment': AppointmentSerializer(appt).data}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': f'Failed to start consultation: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def finish_consultation(request, appointment_id):
    """
    Mark an appointment as completed and close consultation.
    Completes any related queue entry and updates queue status.
    """
    try:
        appt = AppointmentManagement.objects.filter(appointment_id=appointment_id).first()
        if not appt:
            return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        is_doctor = hasattr(user, 'doctor_profile') or getattr(user, 'role', '') == 'doctor'
        is_nurse = getattr(user, 'role', '') == 'nurse'
        if not (is_doctor or is_nurse):
            return Response({'error': 'Only doctors or nurses can finish consultation'}, status=status.HTTP_403_FORBIDDEN)

        appt.consultation_finished_at = timezone.now()
        appt.status = 'completed'
        appt.save()

        # Complete queue entry if present
        department = 'OPD'
        queue_entry = QueueManagement.objects.filter(patient=appt.patient, department=department, status__in=['in_progress', 'waiting']).order_by('started_at', 'enqueue_time').first()
        if queue_entry:
            try:
                queue_entry.mark_completed()
                if not queue_entry.dequeue_time:
                    queue_entry.dequeue_time = timezone.now()
                    queue_entry.save()
            except Exception:
                QueueManagement.objects.filter(pk=queue_entry.id).update(status='completed', finished_at=timezone.now(), dequeue_time=timezone.now())

        # Update queue status metrics
        queue_status, _ = QueueStatus.objects.get_or_create(department=department, defaults={'is_open': True})
        queue_status.total_waiting = (
            QueueManagement.objects.filter(department=department, status='waiting').count() +
            PriorityQueue.objects.filter(department=department, status='waiting').count()
        )
        # Clear current serving if it matches the completed entry
        if queue_entry and queue_status.current_serving == queue_entry.queue_number:
            queue_status.current_serving = None
        queue_status.last_updated_by = user
        queue_status.update_status_message()
        queue_status.save()

        from .serializers import AppointmentSerializer
        return Response({'message': 'Consultation finished', 'appointment': AppointmentSerializer(appt).data}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': f'Failed to finish consultation: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notify_patient_appointment(request, appointment_id):
    """
    Notify the patient that their appointment is imminent (within 15 minutes).
    Persists a Notification for audit and broadcasts via WebSocket.
    """
    try:
        appt = AppointmentManagement.objects.filter(appointment_id=appointment_id).select_related('patient', 'doctor').first()
        if not appt:
            return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        is_doctor = hasattr(user, 'doctor_profile') or getattr(user, 'role', '') == 'doctor'
        is_nurse = getattr(user, 'role', '') == 'nurse'
        if not (is_doctor or is_nurse):
            return Response({'error': 'Only doctors or nurses can send notifications'}, status=status.HTTP_403_FORBIDDEN)

        now = timezone.now()
        appt_dt = appt.appointment_date
        if not appt_dt:
            return Response({'error': 'Appointment date/time not set'}, status=status.HTTP_400_BAD_REQUEST)

        delta = appt_dt - now
        if delta.total_seconds() < 0 or delta > timedelta(minutes=15):
            return Response({'error': 'Notification allowed only within 15 minutes before start'}, status=status.HTTP_400_BAD_REQUEST)

        patient_user = getattr(appt.patient, 'user', None)
        doctor_user = getattr(appt.doctor, 'user', None)
        doctor_name = getattr(doctor_user, 'full_name', 'your doctor') if doctor_user else 'your doctor'
        try:
            display_time = appt_dt.astimezone(timezone.get_current_timezone()).strftime('%I:%M %p')
        except Exception:
            display_time = appt_dt.strftime('%I:%M %p')
        message = f"Your appointment with {doctor_name} starts soon at {display_time}."

        notif = Notification.objects.create(
            user=patient_user,
            message=message,
            channel=Notification.CHANNEL_PUSH,
            delivery_status=Notification.DELIVERY_PENDING,
        )

        # Broadcast via WebSocket to patient's messaging group
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'messaging_{patient_user.id}',
                {
                    'type': 'notification',
                    'notification': {
                        'event': 'appointment_imminent',
                        'appointment_id': appt.appointment_id,
                        'department': appt.department,
                        'timestamp': now.isoformat(),
                        'notification': NotificationSerializer(notif).data,
                    },
                },
            )
            notif.delivery_status = Notification.DELIVERY_SENT
            notif.sent_at = timezone.now()
            notif.save()
        except Exception:
            # Leave as pending for retry/background sender
            pass

        return Response({'message': 'Notification queued', 'notification': NotificationSerializer(notif).data}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': f'Failed to send notification: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def doctor_pending_assessments(request):
    """
    Get pending nurse charts for the current doctor
    """
    try:
        # For now, return empty list since NurseChart model is not implemented yet
        # In the future, this would fetch pending nurse charts
        return Response([], status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to fetch pending assessments: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def patient_assessments(request):
    """
    Return patient assessments filtered by status.
    - status=completed: return archived patient assessments (limited set)
    - status=in_progress: return empty list until nurse charts are implemented
    Response shape: { results: [...], count: N }
    """
    try:
        status_filter = str(request.query_params.get('status', '')).lower()
        results = []
        count = 0

        if status_filter == 'completed':
            # Use archives of patient assessments as "completed" assessments
            from .models import PatientAssessmentArchive
            from .serializers import PatientAssessmentArchiveSerializer

            qs = PatientAssessmentArchive.objects.all()
            # If doctor has hospital affiliation, scope results to that hospital
            hospital = getattr(request.user, 'hospital_name', None)
            if hospital:
                qs = qs.filter(hospital_name__iexact=hospital)

            serializer = PatientAssessmentArchiveSerializer(qs.order_by('-last_assessed_at')[:50], many=True)
            results = serializer.data
            count = len(results)
        elif status_filter == 'in_progress':
            # Placeholder until NurseChart model is implemented
            results = []
            count = 0
        else:
            # Unknown status: return empty list for now
            results = []
            count = 0

        return Response({ 'results': results, 'count': count }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({ 'error': f'Failed to fetch patient assessments: {str(e)}' }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def doctor_blocked_dates(request):
    """
    Get blocked dates for the current doctor
    """
    try:
        doctor = request.user

        # Safely resolve the doctor's profile; return empty list if none exists
        from backend.users.models import GeneralDoctorProfile
        doctor_profile = GeneralDoctorProfile.objects.filter(user=doctor).first()
        if not doctor_profile:
            return Response([], status=status.HTTP_200_OK)
        
        blocked_dates = DoctorAvailability.objects.filter(
            doctor=doctor_profile,
            is_blocked=True
        ).values_list('date', flat=True)
        
        return Response(list(blocked_dates), status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to fetch blocked dates: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def doctor_block_date(request):
    """
    Block a date for the current doctor
    """
    try:
        doctor = request.user
        date = request.data.get('date')
        reason = request.data.get('reason', '')
        
        if not date:
            return Response({
                'error': 'Date is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Resolve the doctor's profile safely
        from backend.users.models import GeneralDoctorProfile
        doctor_profile = GeneralDoctorProfile.objects.filter(user=doctor).first()
        if not doctor_profile:
            return Response({
                'error': 'Doctor profile not found for this user.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if date is already blocked
        existing_block = DoctorAvailability.objects.filter(
            doctor=doctor_profile,
            date=date
        ).first()
        
        if existing_block:
            return Response({
                'error': 'Date is already blocked'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create new blocked date
        DoctorAvailability.objects.create(
            doctor=doctor_profile,
            date=date,
            reason=reason,
            is_blocked=True
        )
        
        return Response({
            'message': 'Date blocked successfully'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': f'Failed to block date: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def doctor_create_appointment(request):
    """
    Create a new appointment for the current doctor
    """
    try:
        doctor = request.user
        
        # Get patient by name (in a real app, you'd have patient selection)
        patient_name = request.data.get('patient_name')
        appointment_date = request.data.get('appointment_date')
        appointment_type = request.data.get('appointment_type', 'consultation')
        
        if not all([patient_name, appointment_date]):
            return Response({
                'error': 'Patient name and appointment date are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # For now, create a mock patient or find existing one
        # In a real app, you'd have proper patient selection
        from backend.users.models import PatientProfile
        
        # Try to find existing patient or create a placeholder
        patient_profile = PatientProfile.objects.filter(
            user__full_name__icontains=patient_name
        ).first()
        
        if not patient_profile:
            return Response({
                'error': 'Patient not found. Please ensure the patient is registered.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Resolve doctor profile safely
        from backend.users.models import GeneralDoctorProfile
        doctor_profile = GeneralDoctorProfile.objects.filter(user=doctor).first()
        if not doctor_profile:
            return Response({
                'error': 'Doctor profile not found for this user.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Derive appointment_time from provided appointment_date if possible
        appt_time = None
        try:
            appt_time = datetime.fromisoformat(str(appointment_date)).time()
        except Exception:
            try:
                # If already a datetime, extract time
                appt_time = appointment_date.time()
            except Exception:
                appt_time = None

        # Determine next queue number
        from django.db.models import Max
        max_q = AppointmentManagement.objects.aggregate(maxq=Max('queue_number'))['maxq'] or 0
        next_queue = max_q + 1

        # [2025-10-31] Department resolution for AppointmentManagement
        # Prefer explicit department from request; fall back to doctor's specialization; default to OPD
        dept = (request.data.get('department') or getattr(doctor_profile, 'specialization', None) or 'OPD')

        # [2025-10-31] Create appointment including resolved department
        # Ensures the new AppointmentManagement.department field is consistently populated
        appointment = AppointmentManagement.objects.create(
            patient=patient_profile,
            doctor=doctor_profile,
            department=dept,
            appointment_date=appointment_date,
            appointment_type=appointment_type,
            appointment_time=appt_time or getattr(appointment_date, 'time', lambda: None)() or timezone.now().time(),
            queue_number=next_queue,
            status='scheduled'
        )
        
        # Create notification for the doctor about the new appointment
        Notification.objects.create(
            user=doctor,
            message=f"New appointment scheduled with {patient_name} on {appointment_date}"
        )
        
        return Response({
            'message': 'Appointment created successfully',
            'appointment_id': appointment.appointment_id,
            'queue_number': appointment.queue_number
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': f'Failed to create appointment: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def schedule_appointment(request):
    """
    Patient-facing endpoint to schedule an appointment.
    Expects payload with keys: type, department, date (ISO), time (HH:MM), reason.
    Uses patient's assigned doctor when available.
    """
    try:
        user = request.user

        # Resolve patient profile
        from backend.users.models import PatientProfile, GeneralDoctorProfile
        try:
            patient_profile = PatientProfile.objects.get(user=user)
        except PatientProfile.DoesNotExist:
            return Response({'error': 'Patient profile not found'}, status=status.HTTP_404_NOT_FOUND)

        # Extract payload
        # Normalize frontend appointment types to backend model choices
        raw_type = request.data.get('type', 'consultation')
        type_map = {
            'general-consultation': 'consultation',
            'consultation': 'consultation',
            'follow-up': 'follow_up',
            'follow_up': 'follow_up',
            'emergency': 'emergency',
            # Fallback mappings for additional frontend types
            'lab-test': 'consultation',
            'specialist-consultation': 'consultation',
            'vaccination': 'consultation',
            'physical-exam': 'consultation',
            'mental-health': 'consultation',
        }
        appointment_type = type_map.get(str(raw_type).strip().lower(), 'consultation')
        date_iso = request.data.get('date')
        time_str = request.data.get('time')
        # Optional fields
        department = request.data.get('department')  # now used in model
        # reason = request.data.get('reason')         # model has no notes field

        if not date_iso or not time_str:
            return Response({'error': 'Date and time are required'}, status=status.HTTP_400_BAD_REQUEST)

        # Parse date and time
        try:
            # Combine into a timezone-aware datetime
            # Accept both full ISO and MM/DD/YYYY provided by frontend converter
            from datetime import datetime
            # Parse date
            try:
                date_dt = datetime.fromisoformat(date_iso.replace('Z', '+00:00'))
            except Exception:
                # Fallback: try parsing as YYYY-MM-DD
                date_dt = datetime.strptime(date_iso[:10], '%Y-%m-%d')

            # Parse time HH:MM (24h)
            time_dt = datetime.strptime(time_str, '%H:%M')

            # Combine keeping date from date_dt and time from time_dt
            naive_dt = datetime(
                year=date_dt.year,
                month=date_dt.month,
                day=date_dt.day,
                hour=time_dt.hour,
                minute=time_dt.minute,
            )
            # Make timezone-aware using the current timezone to avoid DST/offset issues
            combined_dt = timezone.make_aware(naive_dt, timezone.get_current_timezone())
        except Exception:
            return Response({'error': 'Invalid date or time format'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Ensure the new appointment datetime is in the future
        try:
            from django.utils import timezone as dj_timezone
            if combined_dt < dj_timezone.now():
                return Response({'error': 'Appointment date and time must be in the future'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({'error': 'Invalid appointment datetime'}, status=status.HTTP_400_BAD_REQUEST)

        # Optional: explicit doctor selection from frontend
        selected_doctor_id = request.data.get('doctor_id')

        # Validate that the appointment datetime is in the future to avoid model save errors
        try:
            from django.utils import timezone as dj_timezone
            now = dj_timezone.now()
            # Ensure combined_dt exists in this scope; recompute if necessary
            # combined_dt was computed above and is timezone-aware
            if combined_dt < now:
                return Response({'error': 'Appointment date and time must be in the future'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            # If timezone comparison fails, fall back to a generic error
            return Response({'error': 'Invalid appointment datetime'}, status=status.HTTP_400_BAD_REQUEST)

        # Choose doctor: use explicit selection if provided; else prefer assigned doctor, else first available
        doctor_profile = None
        # If explicit doctor_id provided, try to use it (must be verified & active)
        if selected_doctor_id:
            doctor_profile = GeneralDoctorProfile.objects.filter(
                user_id=selected_doctor_id,
                user__verification_status='approved',
                user__is_active=True
            ).first()

        # Fallback to assigned doctor (must be verified & active)
        if doctor_profile is None and patient_profile.assigned_doctor:
            assigned = patient_profile.assigned_doctor
            if assigned.verification_status == 'approved' and assigned.is_active:
                doctor_profile = GeneralDoctorProfile.objects.filter(user=assigned).first()

        # Fallback to first available verified doctor
        if doctor_profile is None:
            doctor_profile = GeneralDoctorProfile.objects.filter(
                available_for_consultation=True,
                user__verification_status='approved',
                user__is_active=True
            ).first()
            if doctor_profile is None:
                return Response({'error': 'No available verified doctor found'}, status=status.HTTP_404_NOT_FOUND)

        # Determine next queue number
        from django.db.models import Max
        max_q = AppointmentManagement.objects.aggregate(maxq=Max('queue_number'))['maxq'] or 0
        next_queue = max_q + 1

        # [2025-10-31] Department resolution for patient scheduling
        # Prefer explicit department from payload; else use doctor specialization; default to OPD
        dept = (department or getattr(doctor_profile, 'specialization', None) or 'OPD')

        # [2025-10-31] Create appointment including resolved department
        appointment = AppointmentManagement.objects.create(
            patient=patient_profile,
            doctor=doctor_profile,
            department=dept,
            appointment_date=combined_dt,
            appointment_type=appointment_type,
            appointment_time=combined_dt.time(),
            queue_number=next_queue,
            status='scheduled'
        )

        # Notify doctor
        Notification.objects.create(
            user=doctor_profile.user,
            message=f"New appointment scheduled by {patient_profile.user.full_name} on {combined_dt}"
        )

        from .serializers import AppointmentSerializer
        data = AppointmentSerializer(appointment).data
        # Broadcast real-time notification to the doctor via WebSocket
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'messaging_{doctor_profile.user.id}',
                {
                    'type': 'notification',
                    'notification': {
                        'event': 'appointment_scheduled',
                        'appointment': data
                    }
                }
            )
        except Exception:
            # Non-blocking: if WS fails, proceed without raising
            pass
        return Response({'message': 'Appointment scheduled successfully', 'appointment': data}, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({'error': f'Failed to schedule appointment: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def reschedule_appointment(request, appointment_id):
    """
    Reschedule an existing appointment.
    Updates the date, time, and status to 'rescheduled'.
    """
    try:
        user = request.user
        
        # Get the appointment and verify it belongs to the user
        try:
            from backend.users.models import PatientProfile
            patient_profile = PatientProfile.objects.get(user=user)
            appointment = AppointmentManagement.objects.get(
                appointment_id=appointment_id,
                patient=patient_profile
            )
        except (PatientProfile.DoesNotExist, AppointmentManagement.DoesNotExist):
            return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Extract new date and time
        date_iso = request.data.get('date')
        time_str = request.data.get('time')
        reschedule_reason = request.data.get('reschedule_reason', 'Patient requested reschedule')
        
        if not date_iso or not time_str:
            return Response({'error': 'Date and time are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Parse date and time
        try:
            from datetime import datetime
            try:
                date_dt = datetime.fromisoformat(date_iso.replace('Z', '+00:00'))
            except Exception:
                date_dt = datetime.strptime(date_iso[:10], '%Y-%m-%d')
            
            time_dt = datetime.strptime(time_str, '%H:%M')
            
            naive_dt = datetime(
                year=date_dt.year,
                month=date_dt.month,
                day=date_dt.day,
                hour=time_dt.hour,
                minute=time_dt.minute,
            )
            combined_dt = timezone.make_aware(naive_dt, timezone.get_current_timezone())
        except Exception:
            return Response({'error': 'Invalid date or time format'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update the appointment
        appointment.appointment_date = combined_dt
        appointment.appointment_time = combined_dt.time()
        appointment.status = 'rescheduled'
        appointment.reschedule_reason = reschedule_reason
        
        # Update other fields if provided
        if 'type' in request.data:
            raw_type = request.data.get('type')
            type_map = {
                'general-consultation': 'consultation',
                'consultation': 'consultation',
                'follow-up': 'follow_up',
                'follow_up': 'follow_up',
                'emergency': 'emergency',
                'lab-test': 'consultation',
                'specialist-consultation': 'consultation',
                'vaccination': 'consultation',
                'physical-exam': 'consultation',
                'mental-health': 'consultation',
            }
            appointment.appointment_type = type_map.get(str(raw_type).strip().lower(), 'consultation')
        
        appointment.save()
        
        # Notify doctor about the reschedule
        Notification.objects.create(
            user=appointment.doctor.user,
            message=f"Appointment with {patient_profile.user.full_name} has been rescheduled to {combined_dt}"
        )
        
        from .serializers import AppointmentSerializer
        data = AppointmentSerializer(appointment).data
        
        return Response({
            'message': 'Appointment rescheduled successfully',
            'appointment': data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': f'Failed to reschedule appointment: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def cancel_appointment(request, appointment_id):
    """
    Cancel an existing appointment.
    Updates the status to 'cancelled'.
    """
    try:
        user = request.user
        
        # Get the appointment and verify it belongs to the user
        try:
            from backend.users.models import PatientProfile
            patient_profile = PatientProfile.objects.get(user=user)
            appointment = AppointmentManagement.objects.get(
                appointment_id=appointment_id,
                patient=patient_profile
            )
        except (PatientProfile.DoesNotExist, AppointmentManagement.DoesNotExist):
            return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get cancellation reason
        cancellation_reason = request.data.get('cancellation_reason', 'Patient cancelled')
        
        # Update the appointment
        appointment.status = 'cancelled'
        appointment.cancellation_reason = cancellation_reason
        appointment.save()
        
        # Notify doctor about the cancellation
        Notification.objects.create(
            user=appointment.doctor.user,
            message=f"Appointment with {patient_profile.user.full_name} on {appointment.appointment_date} has been cancelled"
        )
        
        from .serializers import AppointmentSerializer
        data = AppointmentSerializer(appointment).data
        
        return Response({
            'message': 'Appointment cancelled successfully',
            'appointment': data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': f'Failed to cancel appointment: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def patient_appointments(request):
    """
    Get all appointments for the current patient.
    Supports filtering by status.
    """
    try:
        user = request.user
        
        # Get patient profile
        from backend.users.models import PatientProfile
        try:
            patient_profile = PatientProfile.objects.get(user=user)
        except PatientProfile.DoesNotExist:
            return Response({'error': 'Patient profile not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get all appointments for this patient
        appointments = AppointmentManagement.objects.filter(
            patient=patient_profile
        ).order_by('-appointment_date')
        
        # Optional filtering by status
        status_filter = request.query_params.get('status')
        if status_filter:
            appointments = appointments.filter(status=status_filter)
        
        from .serializers import AppointmentSerializer
        serializer = AppointmentSerializer(appointments, many=True)
        
        return Response({
            'results': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': f'Failed to fetch appointments: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def patient_dashboard_summary(request):
    """
    Unified patient dashboard summary for a department.
    Returns string fields: nowServing, currentPatient, myPosition.
    - nowServing: unified index of the first patient (1 if any)
    - currentPatient: name of the patient currently at the top of the unified queue
    - myPosition: the authenticated patient's unified position in the queue
    Also returns:
    - estimatedWaitMins: integer minutes based on relative baseline calculation
    - progressValue: placeholder progress (0 for now)
    """
    try:
        department = request.query_params.get('department', 'OPD')

        # Collect priority and normal queue entries
        priority_qs = PriorityQueue.objects.filter(
            department=department,
            status__in=['in_progress', 'waiting']
        ).order_by('priority_position', 'enqueue_time')

        normal_qs = QueueManagement.objects.filter(
            department=department,
            status__in=['in_progress', 'waiting']
        ).order_by('position_in_queue', 'enqueue_time')

        items = []
        for p in priority_qs:
            items.append({
                'patient_user_id': getattr(getattr(p.patient, 'user', None), 'id', None),
                'patient_name': str(getattr(getattr(p.patient, 'user', None), 'full_name', '') or ''),
                'queue_type': 'priority',
                'status': p.status,
                'position': p.priority_position or 0,
                'enqueue_time': p.enqueue_time,
                'started_at': p.started_at,
            })
        for n in normal_qs:
            items.append({
                'patient_user_id': getattr(getattr(n.patient, 'user', None), 'id', None),
                'patient_name': str(getattr(getattr(n.patient, 'user', None), 'full_name', '') or ''),
                'queue_type': 'normal',
                'status': n.status,
                'position': n.position_in_queue or 0,
                'enqueue_time': n.enqueue_time,
                'started_at': n.started_at,
            })

        def status_rank(s: str) -> int:
            return 0 if s == 'in_progress' else (1 if s == 'waiting' else 2)

        def type_rank(t: str) -> int:
            return 0 if t == 'priority' else 1

        # Unified sorting across both queues
        items_sorted = sorted(
            items,
            key=lambda x: (
                status_rank(x['status']),
                type_rank(x['queue_type']),
                (x['position'] or 0),
                (x['enqueue_time'] or timezone.now())
            )
        )

        summary = {
            'nowServing': '',
            'currentPatient': '',
            'myPosition': ''
        }

        if items_sorted:
            summary['nowServing'] = '1'
            summary['currentPatient'] = items_sorted[0].get('patient_name', '')

            # Authenticated user's unified position
            my_user_id = request.user.id
            for idx, it in enumerate(items_sorted, start=1):
                if it.get('patient_user_id') == my_user_id:
                    summary['myPosition'] = str(idx)
                    break

        # Compute estimated wait minutes for the current patient (or department fallback)
        estimated_wait_minutes = 0
        try:
            queue_entry = PriorityQueue.objects.filter(
                patient__user=request.user,
                department=department,
                status__in=['waiting', 'in_progress']
            ).first()
            if not queue_entry:
                queue_entry = QueueManagement.objects.filter(
                    patient__user=request.user,
                    department=department,
                    status__in=['waiting', 'in_progress']
                ).first()
            if queue_entry:
                est_td = queue_entry.get_estimated_wait_time()
                if est_td:
                    estimated_wait_minutes = max(0, int(est_td.total_seconds() // 60))
            else:
                try:
                    qs = QueueStatus.objects.get(department=department)
                    if qs.estimated_wait_time:
                        estimated_wait_minutes = max(0, int(qs.estimated_wait_time.total_seconds() // 60))
                except QueueStatus.DoesNotExist:
                    pass
        except Exception:
            pass

        summary['estimatedWaitMins'] = estimated_wait_minutes
        summary['progressValue'] = 0

        return Response(summary, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': f'Failed to fetch dashboard summary: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Messaging Views
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_conversations(request):
    """
    Get all conversations for the current user
    """
    try:
        user = request.user
        
        # Get conversations where user is a participant
        conversations = Conversation.objects.filter(
            participants=user,
            is_active=True
        ).prefetch_related('participants', 'messages__sender', 'messages__reactions__user')
        
        serializer = ConversationSerializer(conversations, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to fetch conversations: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_conversation(request):
    """
    Create a new conversation with another user
    """
    try:
        user = request.user
        other_user_id = request.data.get('other_user_id')
        
        if not other_user_id:
            return Response({
                'error': 'other_user_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if other user exists and is a doctor or nurse
        try:
            other_user = User.objects.get(id=other_user_id)
            if other_user.role not in ['doctor', 'nurse']:
                return Response({
                    'error': 'Can only message doctors and nurses'
                }, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if conversation already exists
        existing_conversation = Conversation.objects.filter(
            participants=user
        ).filter(
            participants=other_user
        ).first()
        
        if existing_conversation:
            serializer = ConversationSerializer(existing_conversation, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        # Create new conversation
        conversation = Conversation.objects.create()
        conversation.participants.add(user, other_user)
        
        serializer = ConversationSerializer(conversation, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': f'Failed to create conversation: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_messages(request, conversation_id):
    """
    Get messages for a specific conversation
    """
    try:
        user = request.user
        
        # Check if user is participant in conversation
        conversation = Conversation.objects.filter(
            id=conversation_id,
            participants=user
        ).first()
        
        if not conversation:
            return Response({
                'error': 'Conversation not found or access denied'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get messages with reactions
        messages = conversation.messages.all().prefetch_related('reactions__user')
        serializer = MessageSerializer(messages, many=True)
        
        # Mark messages as read and delivered
        conversation.mark_messages_as_read(user)
        conversation.mark_messages_as_delivered(user)
        
        # Send delivery notifications for unread messages
        unread_messages = conversation.messages.filter(
            is_delivered=False
        ).exclude(sender=user)
        
        for message in unread_messages:
            send_delivery_notification(message, user.id)
        
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to fetch messages: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request, conversation_id):
    """
    Send a message to a conversation
    """
    try:
        user = request.user
        
        # Check if user is participant in conversation
        conversation = Conversation.objects.filter(
            id=conversation_id,
            participants=user
        ).first()
        
        if not conversation:
            return Response({
                'error': 'Conversation not found or access denied'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CreateMessageSerializer(data=request.data)
        if serializer.is_valid():
            message = serializer.save(
                conversation=conversation,
                sender=user
            )
            
            # Update file information if attachment exists
            if message.file_attachment:
                message.file_name = message.file_attachment.name.split('/')[-1]
                message.file_size = message.file_attachment.size
                message.save()
            
            # Update conversation timestamp
            conversation.save()
            
            # Create notifications for recipients
            message.create_notifications()
            
            # Send real-time notifications via WebSocket
            send_message_notification(message)
            
            response_serializer = MessageSerializer(message)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response({
            'error': f'Failed to send message: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_reaction(request, message_id):
    """
    Add a reaction to a message
    """
    try:
        user = request.user
        
        # Get message and check if user has access
        message = Message.objects.filter(
            id=message_id,
            conversation__participants=user
        ).first()
        
        if not message:
            return Response({
                'error': 'Message not found or access denied'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CreateReactionSerializer(data=request.data)
        if serializer.is_valid():
            reaction_type = serializer.validated_data['reaction_type']
            
            # Check if user already reacted with this type
            existing_reaction = MessageReaction.objects.filter(
                message=message,
                user=user,
                reaction_type=reaction_type
            ).first()
            
            if existing_reaction:
                # Remove existing reaction
                existing_reaction.delete()
                return Response({
                    'message': 'Reaction removed',
                    'action': 'removed'
                }, status=status.HTTP_200_OK)
            else:
                # Remove other reactions from this user
                MessageReaction.objects.filter(
                    message=message,
                    user=user
                ).exclude(reaction_type=reaction_type).delete()
                
                # Add new reaction
                reaction = MessageReaction.objects.create(
                    message=message,
                    user=user,
                    reaction_type=reaction_type
                )
                
                return Response({
                    'message': 'Reaction added',
                    'action': 'added',
                    'reaction': CreateReactionSerializer(reaction).data
                }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response({
            'error': f'Failed to add reaction: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_available_users(request):
    """
    Get list of verified doctors and nurses available for secure messaging.
    Only shows healthcare providers who have completed admin verification process.
    """
    try:
        user = request.user
        search_query = request.GET.get('search', '').strip()
        
        # Security: Only allow verified users to access messaging
        if user.verification_status != 'approved':
            return Response({
                'error': 'Account verification required to access messaging features.',
                'verification_status': user.verification_status
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get only admin-verified doctors and nurses in the SAME hospital (excluding current user)
        # Ensures secure communication between registered, verified providers within the same facility
        if not user.hospital_name:
            available_users = User.objects.none()
        else:
            available_users = User.objects.filter(
                role__in=['doctor', 'nurse'],
                is_active=True,
                verification_status='approved',  # Only admin-verified users for security
                hospital_name__iexact=(user.hospital_name or '').strip()
            ).filter(
                Q(doctor_profile__isnull=False) | Q(nurse_profile__isnull=False)
            ).exclude(id=user.id)
        
        # Apply search filter if search query is provided
        if search_query:
            available_users = available_users.filter(
                Q(full_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(role__icontains=search_query)
            )
        
        serializer = UserSerializer(available_users, many=True)
        # Debug: log counts and context to aid investigations
        try:
            logger.info(
                f"get_available_users: user_id={getattr(user,'id',None)} role={getattr(user,'role',None)} "
                f"hospital='{(getattr(user,'hospital_name', '') or '').strip()}' "
                f"search='{search_query}' count={available_users.count()} filter='approved_only'"
            )
        except Exception:
            pass
        return Response({
            'users': serializer.data,
            'total_count': available_users.count(),
            'message': f'Found {available_users.count()} verified providers in your hospital'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to fetch available users: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def available_doctors_free(request):
    """
    Return doctors in the same hospital who are verified and have no scheduled/ongoing
    appointments for today, and are not blocked by DoctorAvailability today.

    Optional query params:
    - specialization: filter by specialization substring (case-insensitive)
    - include_email: if 'true', include email in response

    Uses short-term caching to reduce DB load. Includes a 'checked_at' timestamp.
    """
    try:
        user = request.user

        # Security: require verified account and hospital context
        if user.verification_status != 'approved':
            return Response({'error': 'Account verification required.', 'verification_status': user.verification_status}, status=status.HTTP_403_FORBIDDEN)
        if not user.hospital_name:
            return Response({'error': 'Hospital context is required.'}, status=status.HTTP_400_BAD_REQUEST)

        specialization = request.GET.get('specialization', '').strip()
        include_email = str(request.GET.get('include_email', 'true')).lower() == 'true'

        cache_key = f"avail:free_doctors:{user.hospital_name}:{specialization.lower()}"
        cached = None
        try:
            cached = cache.get(cache_key)
        except Exception:
            cached = None
        if cached:
            return Response(cached, status=status.HTTP_200_OK)

        today = timezone.localdate()
        active_statuses = ['scheduled', 'rescheduled', 'checked_in', 'in_progress']

        # Base queryset: admin-approved doctors in same hospital (case-insensitive)
        # Note: rely on verification_status='approved' and avoid legacy is_verified flag
        doctors_qs = GeneralDoctorProfile.objects.select_related('user').filter(
            user__role='doctor',
            user__is_active=True,
            user__verification_status='approved',
            user__hospital_name__iexact=(user.hospital_name or ''),
        )

        if specialization:
            doctors_qs = doctors_qs.filter(specialization__icontains=specialization)

        # Exclude doctors blocked today
        blocked_doctors = DoctorAvailability.objects.filter(
            date=today,
            is_blocked=True,
        ).values_list('doctor_id', flat=True)
        doctors_qs = doctors_qs.exclude(id__in=list(blocked_doctors))

        # Exclude doctors with any active appointment today
        busy_doctors = AppointmentManagement.objects.filter(
            doctor__in=doctors_qs,
            status__in=active_statuses,
            appointment_date__date=today,
        ).values_list('doctor_id', flat=True)
        free_doctors_qs = doctors_qs.exclude(id__in=list(busy_doctors)).order_by('user__full_name')

        results = []
        for doc in free_doctors_qs:
            item = {
                'id': doc.user.id,
                'full_name': doc.user.full_name,
                'specialization': doc.specialization or '',
                'availability': 'available',
                'hospital_name': doc.user.hospital_name or '',
            }
            if include_email:
                item['email'] = doc.user.email
            results.append(item)

        payload = {
            'checked_at': timezone.now().isoformat(),
            'count': len(results),
            'doctors': results,
        }

        # Cache for 60 seconds
        try:
            cache.set(cache_key, payload, timeout=60)
        except Exception:
            pass
        return Response(payload, status=status.HTTP_200_OK)

    except DatabaseError as db_err:
        return Response({'error': 'Database error while fetching doctors.', 'detail': str(db_err)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        return Response({'error': 'Failed to fetch available doctors.', 'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def available_nurses(request):
    """
    Return available nurses in the same hospital with credentials, shift info, and department.
    'Available' means the nurse has an active QueueSchedule right now (or manual override enabled),
    otherwise marked as 'Off Duty'. Includes 'checked_at' timestamp and caches briefly.
    """
    try:
        user = request.user
        if user.verification_status != 'approved':
            return Response({'error': 'Account verification required.', 'verification_status': user.verification_status}, status=status.HTTP_403_FORBIDDEN)
        if not user.hospital_name:
            return Response({'error': 'Hospital context is required.'}, status=status.HTTP_400_BAD_REQUEST)

        search = request.GET.get('search', '').strip()
        cache_key = f"avail:nurses:{user.hospital_name}:{search.lower()}"
        cached = None
        try:
            cached = cache.get(cache_key)
        except Exception:
            cached = None
        if cached:
            return Response(cached, status=status.HTTP_200_OK)

        # Admin-approved nurses in same hospital (case-insensitive)
        nurses_qs = NurseProfile.objects.select_related('user').filter(
            user__role='nurse',
            user__is_active=True,
            user__verification_status='approved',
            user__hospital_name__iexact=(user.hospital_name or ''),
        )

        if search:
            nurses_qs = nurses_qs.filter(
                Q(user__full_name__icontains=search) | Q(user__email__icontains=search) | Q(department__icontains=search)
            )

        # Gather schedules for these nurses
        nurse_ids = list(nurses_qs.values_list('id', flat=True))
        schedules = list(QueueSchedule.objects.filter(nurse_id__in=nurse_ids, is_active=True))
        schedules_by_nurse = {}
        for s in schedules:
            schedules_by_nurse.setdefault(s.nurse_id, []).append(s)

        now_iso = timezone.now().isoformat()
        results = []
        for nurse in nurses_qs.order_by('user__full_name'):
            nurse_schedules = schedules_by_nurse.get(nurse.id, [])
            on_duty = False
            active_schedule = None
            for sched in nurse_schedules:
                try:
                    if hasattr(sched, 'is_queue_open') and sched.is_queue_open():
                        on_duty = True
                        active_schedule = sched
                        break
                except Exception:
                    # If schedule evaluation fails, treat as not active
                    continue

            shift = None
            if active_schedule:
                shift = {
                    'department': active_schedule.department,
                    'start_time': active_schedule.start_time.isoformat(),
                    'end_time': active_schedule.end_time.isoformat(),
                    'days_of_week': active_schedule.days_of_week,
                }

            results.append({
                'id': nurse.user.id,
                'full_name': nurse.user.full_name,
                'email': nurse.user.email,
                'credentials': nurse.license_number or '',
                'department': nurse.department or '',
                'availability': 'Available' if on_duty else 'Off Duty',
                'on_duty': on_duty,
                'shift': shift,
            })

        payload = {
            'checked_at': now_iso,
            'count': len(results),
            'nurses': results,
        }
        try:
            cache.set(cache_key, payload, timeout=60)
        except Exception:
            pass
        return Response(payload, status=status.HTTP_200_OK)

    except DatabaseError as db_err:
        return Response({'error': 'Database error while fetching nurses.', 'detail': str(db_err)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        return Response({'error': 'Failed to fetch available nurses.', 'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def nurse_capacity_validate(request):
    """
    Validate if a nurse has capacity to accept queue patients in a department.
    Params: nurse_id, department
    Returns: on_duty, has_active_schedule, department, nurse_name
    """
    try:
        nurse_id = int(request.GET.get('nurse_id', '0'))
    except Exception:
        return Response({'error': 'nurse_id is required and must be integer'}, status=status.HTTP_400_BAD_REQUEST)
    department = (request.GET.get('department') or '').strip() or 'OPD'

    nurse = NurseProfile.objects.select_related('user').filter(user_id=nurse_id).first()
    if not nurse:
        return Response({'error': 'Nurse not found'}, status=status.HTTP_404_NOT_FOUND)

    schedules = list(QueueSchedule.objects.filter(nurse_id=nurse.id, department=department, is_active=True))
    has_active_schedule = len(schedules) > 0
    on_duty = False
    active_schedule = None
    for sched in schedules:
        try:
            if hasattr(sched, 'is_queue_open') and sched.is_queue_open():
                on_duty = True
                active_schedule = sched
                break
        except Exception:
            continue

    payload = {
        'nurse_id': nurse.user.id,
        'nurse_name': nurse.user.full_name,
        'department': department,
        'has_active_schedule': has_active_schedule,
        'on_duty': on_duty,
        'schedule': None,
    }
    if active_schedule:
        payload['schedule'] = {
            'start_time': active_schedule.start_time.isoformat(),
            'end_time': active_schedule.end_time.isoformat(),
            'days_of_week': active_schedule.days_of_week,
            'manual_override': active_schedule.manual_override,
            'override_status': active_schedule.override_status,
        }
    return Response(payload, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def nurses_list(request):
    """
    Paginated nurses list in the same hospital, with sorting and search.
    Query: page, page_size, search, sort_by (full_name|department|email), order (asc|desc)
    """
    user = request.user
    if getattr(user, 'verification_status', 'pending') != 'approved':
        return Response({'error': 'Account verification required.', 'verification_status': user.verification_status}, status=status.HTTP_403_FORBIDDEN)
    if not user.hospital_name:
        return Response({'error': 'Hospital context is required.'}, status=status.HTTP_400_BAD_REQUEST)

    search = (request.GET.get('search') or '').strip()
    sort_by = (request.GET.get('sort_by') or 'full_name').strip()
    order = (request.GET.get('order') or 'asc').strip().lower()
    page = max(1, int(request.GET.get('page', '1')))
    page_size = max(1, min(50, int(request.GET.get('page_size', '10'))))

    qs = NurseProfile.objects.select_related('user').filter(
        user__role='nurse',
        user__is_active=True,
        user__verification_status='approved',
        user__hospital_name__iexact=(user.hospital_name or ''),
    )
    if search:
        qs = qs.filter(Q(user__full_name__icontains=search) | Q(user__email__icontains=search) | Q(department__icontains=search))

    sort_map = {
        'full_name': 'user__full_name',
        'department': 'department',
        'email': 'user__email',
    }
    sort_field = sort_map.get(sort_by, 'user__full_name')
    if order == 'desc':
        sort_field = f'-{sort_field}'
    qs = qs.order_by(sort_field)

    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    items = []
    now_iso = timezone.now().isoformat()
    for nurse in qs[start:end]:
        items.append({
            'id': nurse.user.id,
            'full_name': nurse.user.full_name,
            'email': nurse.user.email,
            'department': nurse.department,
            'is_active': nurse.user.is_active,
            'verification_status': nurse.user.verification_status,
            'checked_at': now_iso,
        })

    return Response({'items': items, 'total_count': total, 'page': page, 'page_size': page_size}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_message_notifications(request):
    """
    Get message notifications for the current user
    """
    try:
        user = request.user
        
        # Get unread message notifications
        notifications = MessageNotification.objects.filter(
            recipient=user,
            is_sent=False
        ).order_by('-created_at')[:20]
        
        serializer = MessageNotificationSerializer(notifications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to fetch notifications: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_as_sent(request, notification_id):
    """
    Mark a notification as sent
    """
    try:
        user = request.user
        
        notification = MessageNotification.objects.filter(
            id=notification_id,
            recipient=user
        ).first()
        
        if not notification:
            return Response({
                'error': 'Notification not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        notification.is_sent = True
        notification.sent_at = timezone.now()
        notification.save()
        
        return Response({
            'message': 'Notification marked as sent'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to mark notification as sent: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_message_as_read(request, message_id):
    """
    Mark a specific message as read
    """
    try:
        user = request.user
        
        message = Message.objects.filter(
            id=message_id,
            conversation__participants=user
        ).first()
        
        if not message:
            return Response({
                'error': 'Message not found or access denied'
            }, status=status.HTTP_404_NOT_FOUND)
        
        if not message.is_read and message.sender != user:
            message.is_read = True
            message.read_at = timezone.now()
            message.save()
            
            # Create read notification
            MessageNotification.objects.create(
                message=message,
                recipient=message.sender,
                notification_type='message_read'
            )
            
            # Send real-time read notification
            send_read_notification(message, user.id)
        
        return Response({
            'message': 'Message marked as read'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to mark message as read: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def _compute_medicine_alerts(medicine, days=21):
    """Return a list of alert dicts for a single medicine.
    Alert statuses: out_of_stock, low_stock, expiring_soon, expired.
    """
    alerts = []

    # Stock-based alerts
    try:
        current = int(medicine.current_stock or 0)
        minimum = int(medicine.minimum_stock_level or 0)
    except Exception:
        current = medicine.current_stock or 0
        minimum = medicine.minimum_stock_level or 0

    if current <= 0:
        alerts.append({
            'status': 'out_of_stock',
            'recommended_action': 'Reorder immediately',
        })
    elif minimum > 0 and current <= minimum:
        alerts.append({
            'status': 'low_stock',
            'recommended_action': 'Plan restock soon',
        })

    # Expiry-based alerts
    expiry = getattr(medicine, 'expiry_date', None)
    if expiry:
        today = timezone.now().date()
        if expiry < today:
            alerts.append({
                'status': 'expired',
                'expiry_date': expiry,
                'recommended_action': 'Discard per policy',
            })
        else:
            cutoff = today + timedelta(days=days)
            if expiry <= cutoff:
                alerts.append({
                    'status': 'expiring_soon',
                    'expiry_date': expiry,
                    'recommended_action': 'Prioritize usage or reorder',
                })

    return alerts


def _send_medicine_alert_email(nurse_user, medicine, alerts, days=21):
    """Compose and send a concise email for a single medicine's alerts."""
    if not alerts:
        return

    recipient = getattr(nurse_user, 'email', None)
    if not recipient:
        return

    status_labels = {
        'out_of_stock': 'Out of Stock',
        'low_stock': 'Low Stock',
        'expiring_soon': 'Expiring Soon',
        'expired': 'Expired',
    }

    lines = []
    for a in alerts:
        label = status_labels.get(a['status'], a['status'])
        expiry_info = ''
        if a.get('expiry_date'):
            expiry_info = f" — Expiry: {a['expiry_date']}"
        lines.append(
            f"• {medicine.medicine_name} — {label}{expiry_info} — Recommended: {a['recommended_action']}"
        )

    subject = f"MediSync Inventory Alert: {medicine.medicine_name}"
    message = (
        "Hello,\n\n"
        "The following inventory alert was detected in real-time:\n\n"
        + "\n".join(lines)
        + "\n\n"
        f"Expiry window considered: next {days} days.\n"
        "Please take the recommended action.\n\n"
        "— MediSync"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            recipient_list=[recipient],
            fail_silently=False,
        )
    except Exception as e:
        # Do not break the request flow; optionally log
        print(f"Email send failed for {recipient}: {e}")

# Medicine Inventory Views
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_medicine_inventory(request):
    """
    Get medicine inventory for the current nurse with optional search functionality
    """
    try:
        user = request.user
        logger.info(f"assign_patient_to_doctor:start user_id={getattr(user,'id',None)} role={getattr(user,'role',None)} patient_id={request.data.get('patient_id')} doctor_id={request.data.get('doctor_id')} specialization={request.data.get('specialization')}")
        
        # Check if user is a nurse
        if user.role != 'nurse':
            return Response({
                'error': 'Access denied. Only nurses can view medicine inventory.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get search parameter
        search_query = request.GET.get('search', '').strip()
        
        # Get medicine inventory for the current nurse
        from .models import MedicineInventory
        inventory = MedicineInventory.objects.filter(
            inventory__user=user
        )
        
        # Apply search filter if search query is provided
        if search_query:
            inventory = inventory.filter(
                Q(medicine_name__icontains=search_query) |
                Q(batch_number__icontains=search_query) |
                Q(manufacturer__icontains=search_query)
            )
        
        inventory = inventory.order_by('medicine_name')
        
        from .serializers import MedicineInventorySerializer
        serializer = MedicineInventorySerializer(inventory, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to fetch medicine inventory: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_medicine(request):
    """
    Add a new medicine to inventory
    """
    try:
        user = request.user
        
        # Check if user is a nurse
        if user.role != 'nurse':
            return Response({
                'error': 'Access denied. Only nurses can manage medicine inventory.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        from .models import MedicineInventory
        from backend.users.models import NurseProfile
        
        # Get nurse profile
        nurse_profile = NurseProfile.objects.get(user=user)
        
        # Create medicine inventory entry
        medicine = MedicineInventory.objects.create(
            inventory=nurse_profile,
            medicine_name=request.data.get('name'),
            stock_number=request.data.get('quantity', 0),
            current_stock=request.data.get('quantity', 0),
            unit_price=request.data.get('unit_price', 0),
            minimum_stock_level=request.data.get('min_stock_level', 0),
            expiry_date=request.data.get('expiry_date'),
            batch_number=request.data.get('batch_number', ''),
            usage_pattern=request.data.get('description', '')
        )

        # Real-time email alert for new entries that already meet thresholds
        try:
            days = int(request.data.get('expiry_days', 21))
        except Exception:
            days = 21
        alerts = _compute_medicine_alerts(medicine, days)
        if alerts:
            _send_medicine_alert_email(user, medicine, alerts, days)
        
        from .serializers import MedicineInventorySerializer
        serializer = MedicineInventorySerializer(medicine)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': f'Failed to add medicine: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_medicine(request, medicine_id):
    """
    Update medicine inventory
    """
    try:
        user = request.user
        
        # Check if user is a nurse
        if user.role != 'nurse':
            return Response({
                'error': 'Access denied. Only nurses can manage medicine inventory.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        from .models import MedicineInventory
        
        # Get medicine
        medicine = MedicineInventory.objects.get(
            id=medicine_id,
            inventory__user=user
        )
        
        # Compute alerts before update (to detect threshold crossings)
        try:
            days = int(request.data.get('expiry_days', 21))
        except Exception:
            days = 21
        before_alerts = _compute_medicine_alerts(medicine, days)
        before_statuses = {a['status'] for a in before_alerts}

        # Update fields
        medicine.medicine_name = request.data.get('name', medicine.medicine_name)
        medicine.current_stock = request.data.get('quantity', medicine.current_stock)
        medicine.unit_price = request.data.get('unit_price', medicine.unit_price)
        medicine.minimum_stock_level = request.data.get('min_stock_level', medicine.minimum_stock_level)
        medicine.expiry_date = request.data.get('expiry_date', medicine.expiry_date)
        medicine.usage_pattern = request.data.get('description', medicine.usage_pattern)
        medicine.save()

        # Compute alerts after update and send only newly reached statuses
        after_alerts = _compute_medicine_alerts(medicine, days)
        new_statuses = [a for a in after_alerts if a['status'] not in before_statuses]
        if new_statuses:
            _send_medicine_alert_email(user, medicine, new_statuses, days)
        
        from .serializers import MedicineInventorySerializer
        serializer = MedicineInventorySerializer(medicine)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except MedicineInventory.DoesNotExist:
        return Response({
            'error': 'Medicine not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Failed to update medicine: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dispense_medicine(request, medicine_id):
    """
    Dispense a quantity of medicine to a patient and update stock.
    Triggers real-time email alerts if thresholds are newly crossed.
    Also broadcasts a patient-specific WebSocket notification when `patient_id` is provided.
    """
    try:
        user = request.user

        # Check if user is a nurse
        if user.role != 'nurse':
            return Response({
                'error': 'Access denied. Only nurses can manage medicine inventory.'
            }, status=status.HTTP_403_FORBIDDEN)

        from .models import MedicineInventory

        # Get medicine owned by current nurse
        medicine = MedicineInventory.objects.get(
            id=medicine_id,
            inventory__user=user
        )

        # Validate quantity
        qty = request.data.get('quantity')
        try:
            qty = int(qty)
        except Exception:
            return Response({'error': 'Invalid quantity'}, status=status.HTTP_400_BAD_REQUEST)
        if qty is None or qty <= 0:
            return Response({'error': 'Quantity must be a positive integer'}, status=status.HTTP_400_BAD_REQUEST)
        if medicine.current_stock < qty:
            return Response({'error': 'Insufficient stock to dispense'}, status=status.HTTP_400_BAD_REQUEST)

        # Compute status before dispensing
        try:
            days = int(request.data.get('expiry_days', 21))
        except Exception:
            days = 21
        before_alerts = _compute_medicine_alerts(medicine, days)
        before_statuses = {a['status'] for a in before_alerts}

        # Apply dispense
        medicine.current_stock = medicine.current_stock - qty
        medicine.save()

        # Compute status after dispensing and notify only on newly reached statuses
        after_alerts = _compute_medicine_alerts(medicine, days)
        new_statuses = [a for a in after_alerts if a['status'] not in before_statuses]
        if new_statuses:
            _send_medicine_alert_email(user, medicine, new_statuses, days)

        from .serializers import MedicineInventorySerializer
        serializer = MedicineInventorySerializer(medicine)


        return Response({
            'message': 'Medicine dispensed successfully',
            'inventory': serializer.data
        }, status=status.HTTP_200_OK)

    except MedicineInventory.DoesNotExist:
        return Response({'error': 'Medicine not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': f'Failed to dispense medicine: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_medicine(request, medicine_id):
    """
    Delete medicine from inventory
    """
    try:
        user = request.user
        
        # Check if user is a nurse
        if user.role != 'nurse':
            return Response({
                'error': 'Access denied. Only nurses can manage medicine inventory.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        from .models import MedicineInventory
        
        # Get and delete medicine
        medicine = MedicineInventory.objects.get(
            id=medicine_id,
            inventory__user=user
        )
        medicine.delete()
        
        return Response({
            'message': 'Medicine deleted successfully'
        }, status=status.HTTP_200_OK)
        
    except MedicineInventory.DoesNotExist:
        return Response({
            'error': 'Medicine not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Failed to delete medicine: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Nurse Queue Views
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def nurse_queue_patients(request):
    """
    Get patients in queue for nurses with optional department filtering and
    a consolidated list including queue type indicators.
    """
    try:
        user = request.user

        # Check if user is a nurse
        if user.role != 'nurse':
            return Response({
                'error': 'Access denied. Only nurses can view patient queue.'
            }, status=status.HTTP_403_FORBIDDEN)

        # Department filter (default to nurse profile department or OPD)
        department = request.query_params.get('department') or getattr(getattr(user, 'nurse_profile', None), 'department', None) or 'OPD'

        # Get normal queue patients (waiting or in_progress)
        normal_queue = QueueManagement.objects.filter(
            department=department,
            status__in=['waiting', 'in_progress']
        ).order_by('position_in_queue', 'enqueue_time')

        # Get priority queue patients (waiting or in_progress)
        priority_queue = PriorityQueue.objects.filter(
            department=department,
            status__in=['waiting', 'in_progress']
        ).order_by('priority_position', 'enqueue_time')

        from .serializers import QueueSerializer, PriorityQueueSerializer

        normal_serializer = QueueSerializer(normal_queue, many=True)
        priority_serializer = PriorityQueueSerializer(priority_queue, many=True)

        # Build consolidated list with queue_type and normalized fields
        def normalize_normal(n):
            return {
                'id': n.get('id'),
                'queue_number': n.get('queue_number'),
                'patient_name': n.get('patient_name'),
                'department': n.get('department'),
                'status': n.get('status'),
                'position': n.get('position_in_queue'),
                'enqueue_time': n.get('enqueue_time'),
                'queue_type': 'normal',
            }

        def normalize_priority(p):
            return {
                'id': p.get('id'),
                'queue_number': p.get('queue_number'),
                'patient_name': p.get('patient_name'),
                'department': p.get('department'),
                'status': p.get('status'),
                'position': p.get('priority_position'),
                'enqueue_time': p.get('enqueue_time'),
                'queue_type': 'priority',
                'priority_level': p.get('priority_level'),
            }

        consolidated = [normalize_normal(n) for n in normal_serializer.data] + [normalize_priority(p) for p in priority_serializer.data]

        return Response({
            'department': department,
            'normal_queue': normal_serializer.data,
            'priority_queue': priority_serializer.data,
            'all_patients': consolidated
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': f'Failed to fetch queue patients: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Doctor Selection Views
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_available_doctors(request):
    """
    Get available verified doctors by specialization with optional search functionality.
    Only shows doctors who have completed admin verification process.
    For patients, filters doctors by the same hospital where the patient is registered.
    """
    try:
        user = request.user
        
        # Allow patients, nurses, and doctors who are verified to view available doctors.
        # This supports patient appointment scheduling with department-based filtering.
        # Patients can browse available doctors even if their account is not yet approved.
        # Other roles (nurse/doctor/admin) must be approved.
        if user.role != 'patient' and user.verification_status != 'approved':
            return Response({
                'error': 'Account verification required to access doctor information.',
                'verification_status': user.verification_status
            }, status=status.HTTP_403_FORBIDDEN)
        
        specialization = request.GET.get('specialization', '')
        department = request.GET.get('department', '')
        search_query = request.GET.get('search', '').strip()
        
        # Get only admin-verified doctors with the specified specialization
        from backend.users.models import GeneralDoctorProfile, PatientProfile
        
        doctors_query = GeneralDoctorProfile.objects.filter(
            user__verification_status='approved',  # Only admin-verified doctors for security
            user__is_active=True,
            available_for_consultation=True
        )
        
        # Filter doctors by patient's registered hospital if the user is a patient
        if user.role == 'patient':
            try:
                patient_profile = PatientProfile.objects.get(user=user)
                patient_hospital = patient_profile.hospital
                
                if patient_hospital:
                    # Filter doctors who work at the same hospital as the patient
                    doctors_query = doctors_query.filter(user__hospital_name=patient_hospital)
            except PatientProfile.DoesNotExist:
                # If patient profile doesn't exist, return empty list for security
                return Response({
                    'doctors': [],
                    'total_count': 0,
                    'message': 'Patient profile not found. Please complete your registration.',
                    'error': 'Patient profile required for appointment scheduling'
                }, status=status.HTTP_404_NOT_FOUND)
        
        if specialization:
            doctors_query = doctors_query.filter(specialization__icontains=specialization)
        if department:
            # Map frontend department slug to specialization keywords
            dept_slug = str(department).strip().lower()
            dept_map = {
                'general-medicine': ['general', 'internal medicine', 'primary care'],
                'cardiology': ['cardiology', 'cardiologist'],
                'dermatology': ['dermatology', 'dermatologist'],
                'orthopedics': ['orthopedics', 'orthopaedic', 'orthopedic'],
                'pediatrics': ['pediatrics', 'pediatrician'],
                'gynecology': ['gynecology', 'obstetrics', 'ob-gyn', 'obgyn'],
                'neurology': ['neurology', 'neurologist'],
                'oncology': ['oncology', 'oncologist'],
                'optometrist': ['optometry', 'optometrist', 'eye care', 'ophthalmology', 'ophthalmologist'],
                'emergency-medicine': ['emergency', 'emergency medicine']
            }
            keywords = dept_map.get(dept_slug, [])
            # Build combined filter: direct slug match OR keyword-based match
            q = Q(
                specialization__iexact=dept_slug
            ) | Q(
                specialization__icontains=dept_slug
            ) | Q(
                specialization__icontains=dept_slug.replace('-', ' ')
            ) | Q(
                specialization__icontains=dept_slug.replace('-', '_')
            )
            for kw in keywords:
                q |= Q(specialization__icontains=kw)
            # Include doctors with blank specialization for General Medicine
            if dept_slug == 'general-medicine':
                q |= Q(specialization__isnull=True) | Q(specialization='')
            doctors_query = doctors_query.filter(q)
        
        # Apply search filter if search query is provided
        if search_query:
            doctors_query = doctors_query.filter(
                Q(user__full_name__icontains=search_query) |
                Q(specialization__icontains=search_query)
            )
        
        doctors = doctors_query.select_related('user')
        
        # Get current patient count for each doctor
        doctor_data = []
        def derive_department_label(spec: str) -> str:
            s = (spec or '').lower()
            if 'cardio' in s:
                return 'Cardiology'
            if 'dermat' in s:
                return 'Dermatology'
            if 'ortho' in s:
                return 'Orthopedics'
            if 'pediatr' in s:
                return 'Pediatrics'
            if 'gynecol' in s or 'obstet' in s or 'ob-gyn' in s or 'obgyn' in s:
                return 'Gynecology'
            if 'neuro' in s:
                return 'Neurology'
            if 'oncolo' in s:
                return 'Oncology'
            if 'emergency' in s:
                return 'Emergency Medicine'
            return 'General Medicine'
        
        for doctor in doctors:
            try:
                current_patients = AppointmentManagement.objects.filter(
                    doctor=doctor,
                    appointment_date__date=timezone.now().date(),
                    status__in=['scheduled', 'in_progress']
                ).count()
                
                # Handle profile picture safely to avoid UnicodeDecodeError
                profile_picture_url = None
                if doctor.user.profile_picture:
                    try:
                        # Just return the URL string, don't try to decode the file
                        profile_picture_url = str(doctor.user.profile_picture.url) if hasattr(doctor.user.profile_picture, 'url') else str(doctor.user.profile_picture)
                    except (UnicodeDecodeError, ValueError, AttributeError):
                        # If there's any issue with the profile picture, set to None
                        profile_picture_url = None
                
                doctor_data.append({
                    'id': doctor.user.id,
                    'full_name': doctor.user.full_name,
                    'specialization': doctor.specialization,
                    'department': derive_department_label(doctor.specialization),
                    'hospital_name': getattr(doctor.user, 'hospital_name', None),
                    'is_available': current_patients < 10,  # Assume max 10 patients per doctor
                    'current_patients': current_patients,
                    'profile_picture': profile_picture_url,
                    'verification_status': doctor.user.verification_status,
                    'is_verified': True  # All returned doctors are verified
                })
            except Exception as e:
                # Skip this doctor if there's any issue processing their data
                print(f"Error processing doctor {doctor.user.id}: {e}")
                continue
        
        return Response({
            'doctors': doctor_data,
            'total_count': len(doctor_data),
            'message': f'Found {len(doctor_data)} verified doctors',
            'security_note': 'Only admin-verified doctors are shown for secure healthcare operations'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to fetch available doctors: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Departments per Hospital
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hospital_departments(request):
    """
    Return department options available in the user's hospital based on verified doctors.
    - For patients: uses their registered hospital automatically.
    - For other roles: optional `hospital` query parameter can scope departments.
    - Falls back to standard department list to avoid breaking existing flows.
    """
    try:
        user = request.user
        # Patients can see hospital departments even if not yet approved.
        # Other roles must be approved to access this data.
        if user.role != 'patient' and user.verification_status != 'approved':
            return Response({
                'error': 'Account verification required to access hospital departments.',
                'verification_status': user.verification_status
            }, status=status.HTTP_403_FORBIDDEN)

        from backend.users.models import GeneralDoctorProfile, PatientProfile

        # Determine hospital scope
        requested_hospital = request.GET.get('hospital')
        hospital_name = None
        if user.role == 'patient':
            try:
                patient_profile = PatientProfile.objects.get(user=user)
                hospital_name = getattr(patient_profile, 'hospital', None) or requested_hospital
            except PatientProfile.DoesNotExist:
                return Response({
                    'departments': [],
                    'total_count': 0,
                    'message': 'Patient profile not found. Please complete registration to view departments.'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            hospital_name = requested_hospital or getattr(user, 'hospital_name', None)

        # Base doctor query: only verified, active and available
        doctors_query = GeneralDoctorProfile.objects.filter(
            user__verification_status='approved',
            user__is_active=True,
            available_for_consultation=True
        )
        if hospital_name:
            doctors_query = doctors_query.filter(user__hospital_name=hospital_name)

        specializations = list(doctors_query.values_list('specialization', flat=True))

        # Map specialization keywords to department slugs
        dept_map = {
            'general-medicine': ['general', 'internal medicine', 'primary care'],
            'cardiology': ['cardiology', 'cardiologist', 'cardio'],
            'dermatology': ['dermatology', 'dermatologist', 'dermat'],
            'orthopedics': ['orthopedics', 'orthopaedic', 'orthopedic', 'ortho'],
            'pediatrics': ['pediatrics', 'pediatrician', 'pediatr'],
            'gynecology': ['gynecology', 'obstetrics', 'ob-gyn', 'obgyn', 'gynecol'],
            'neurology': ['neurology', 'neurologist', 'neuro'],
            'oncology': ['oncology', 'oncologist', 'oncolo'],
            'optometrist': ['optometry', 'optometrist', 'eye care', 'ophthalmology', 'ophthalmologist'],
            'emergency-medicine': ['emergency', 'emergency medicine']
        }

        slug_to_label = {
            'general-medicine': 'General Medicine',
            'cardiology': 'Cardiology',
            'dermatology': 'Dermatology',
            'orthopedics': 'Orthopedics',
            'pediatrics': 'Pediatrics',
            'gynecology': 'Gynecology',
            'neurology': 'Neurology',
            'oncology': 'Oncology',
            'optometrist': 'Optometrist',
            'emergency-medicine': 'Emergency Medicine',
            'other': 'Other'
        }

        def spec_to_slug(spec: str) -> str:
            s = (spec or '').lower()
            for slug, keywords in dept_map.items():
                if s == slug:
                    return slug
                if s.replace('-', ' ') == slug:
                    return slug
                for kw in keywords:
                    if kw in s:
                        return slug
            # Default bucket
            return 'general-medicine' if s.strip() == '' else 'other'

        slugs = set(spec_to_slug(spec) for spec in specializations)

        # Build options. If none detected, fall back to shared list
        if slugs:
            departments = [
                {'label': slug_to_label.get(slug, slug.title().replace('-', ' ')), 'value': slug}
                for slug in sorted(slugs)
            ]
        else:
            departments = [
                {'label': 'General Medicine', 'value': 'general-medicine'},
                {'label': 'Cardiology', 'value': 'cardiology'},
                {'label': 'Dermatology', 'value': 'dermatology'},
                {'label': 'Orthopedics', 'value': 'orthopedics'},
                {'label': 'Pediatrics', 'value': 'pediatrics'},
                {'label': 'Gynecology', 'value': 'gynecology'},
                {'label': 'Neurology', 'value': 'neurology'},
                {'label': 'Oncology', 'value': 'oncology'},
                {'label': 'Optometrist', 'value': 'optometrist'},
                {'label': 'Emergency Medicine', 'value': 'emergency-medicine'},
                {'label': 'Other', 'value': 'other'},
            ]

        return Response({
            'departments': departments,
            'total_count': len(departments),
            'hospital': hospital_name
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': f'Failed to fetch hospital departments: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_patient_to_doctor(request):
    """
    Assign a patient to a doctor
    """
    try:
        user = request.user
        # Audit: start of assignment flow with basic context
        try:
            logger.info(
                f"assign_patient_to_doctor:start nurse_user_id={getattr(user,'id',None)} payload_keys={list(getattr(request,'data',{}).keys())}"
            )
        except Exception:
            # non-blocking audit
            pass
        
        # Check if user is a nurse
        if user.role != 'nurse':
            return Response({
                'error': 'Access denied. Only nurses can assign patients.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        patient_id = request.data.get('patient_id')
        doctor_id = request.data.get('doctor_id')
        specialization = request.data.get('specialization')
        
        if not all([patient_id, doctor_id, specialization]):
            return Response({
                'error': 'Patient ID, Doctor ID, and specialization are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get doctor profile
        from backend.users.models import GeneralDoctorProfile
        try:
            doctor_profile = GeneralDoctorProfile.objects.get(user_id=doctor_id)
        except GeneralDoctorProfile.DoesNotExist:
            return Response({
                'error': 'Doctor not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Create appointment for the patient
        from backend.users.models import PatientProfile
        try:
            patient_profile = PatientProfile.objects.get(user_id=patient_id)
        except PatientProfile.DoesNotExist:
            return Response({
                'error': 'Patient not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Enforce specialization matching before creating any side effects
        requested_specialty = (specialization or '').strip()
        doctor_specialty = (getattr(doctor_profile, 'specialization', '') or '').strip()
        # Try to infer required specialty from latest provider orders (consultation_orders.specialty)
        inferred_specialty = requested_specialty
        try:
            orders = getattr(patient_profile, 'provider_order_sheets', []) or []
            for entry in reversed(orders):
                try:
                    cons = (entry or {}).get('consultation_orders') or {}
                    spec = (cons.get('specialty') or '').strip()
                    if spec:
                        inferred_specialty = spec
                        break
                except Exception:
                    continue
        except Exception:
            # If provider orders not accessible, stick to requested_specialty
            pass

        # Normalize specialties to avoid false mismatches due to case/spacing/synonyms
        def _normalize_specialty(s: str) -> str:
            s = (s or '').strip().lower()
            if not s:
                return ''
            synonyms = {
                'pulmonary medicine': 'pulmonology',
                'respiratory medicine': 'pulmonology',
                'cardiovascular medicine': 'cardiology',
                'ob-gyn': 'gynecology',
                'obgyn': 'gynecology',
            }
            canonical = synonyms.get(s, s)
            # Title-case the canonical value for consistent storage/display
            return ' '.join(w.capitalize() for w in canonical.split())

        def _spec_matches(a: str, b: str) -> bool:
            a = (a or '').strip().lower()
            b = (b or '').strip().lower()
            if not a or not b:
                return False
            return a in b or b in a

        if not doctor_specialty:
            logger.warning(
                f"assign_patient_to_doctor:specialization_missing doctor_user_id={getattr(doctor_profile.user,'id',None)}"
            )
            return Response({
                'error': 'Doctor specialization is not set. Assignment blocked.',
                'code': 'ERR_DOCTOR_SPECIALIZATION_MISSING',
                'doctor_specialization': doctor_specialty,
            }, status=status.HTTP_400_BAD_REQUEST)

        # Compare normalized values for robust matching
        normalized_doctor_specialty = _normalize_specialty(doctor_specialty)
        normalized_inferred_specialty = _normalize_specialty(inferred_specialty)
        normalized_requested_specialty = _normalize_specialty(requested_specialty)

        if not _spec_matches(normalized_doctor_specialty, normalized_inferred_specialty):
            logger.warning(
                (
                    "assign_patient_to_doctor:specialization_mismatch "
                    f"nurse_user_id={getattr(user,'id',None)} patient_id={patient_id} doctor_id={doctor_id} "
                    f"required='{normalized_inferred_specialty}' doctor_specialization='{normalized_doctor_specialty}' requested='{normalized_requested_specialty}'"
                )
            )
            return Response({
                'error': f"Specialization mismatch: patient requires {normalized_inferred_specialty or 'Unknown'}, you are {normalized_doctor_specialty or 'Unset'}.",
                'code': 'ERR_SPECIALIZATION_MISMATCH',
                'details': {
                    'required_specialty': normalized_inferred_specialty,
                    'doctor_specialization': normalized_doctor_specialty,
                    'requested_specialization': normalized_requested_specialty,
                },
                'resolution': 'Select a doctor with the matching specialty or adjust consultation order.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create appointment
        scheduled_time = timezone.now() + timedelta(minutes=15)
        # Allocate a unique queue number for the appointment
        last_queue_number = AppointmentManagement.objects.order_by('-queue_number').values_list('queue_number', flat=True).first() or 0
        next_queue_number = last_queue_number + 1
        appointment = AppointmentManagement.objects.create(
            patient=patient_profile,
            doctor=doctor_profile,
            appointment_date=scheduled_time,
            appointment_time=scheduled_time.time(),
            appointment_type='consultation',
            status='scheduled',
            queue_number=next_queue_number
        )
        logger.info(f"assign_patient_to_doctor:appointment_created appointment_id={getattr(appointment,'appointment_id',None)} patient_profile_id={getattr(patient_profile,'id',None)} doctor_profile_id={getattr(doctor_profile,'id',None)} queue_number={next_queue_number}")

        # Ensure doctor authorization for patient-specific endpoints
        try:
            patient_profile.assigned_doctor = doctor_profile.user
            patient_profile.save(update_fields=['assigned_doctor'])
            logger.info(f"assign_patient_to_doctor:assigned_doctor_set patient_profile_id={getattr(patient_profile,'id',None)} assigned_doctor_user_id={getattr(doctor_profile.user,'id',None)}")
        except Exception as e:
            logger.warning(f"assign_patient_to_doctor:assigned_doctor_set_failed patient_profile_id={getattr(patient_profile,'id',None)} doctor_user_id={getattr(doctor_profile.user,'id',None)} error={e}")
        
        # Remove patient from queue if they were in queue
        QueueManagement.objects.filter(
            patient=patient_profile,
            status='waiting'
        ).update(status='assigned')
        
        PriorityQueue.objects.filter(
            patient=patient_profile
        ).delete()
        
        # Create notification for doctor (include intake summary when available)
        try:
            intake = getattr(patient_profile, 'nursing_intake_assessment', {}) or {}
            chief_complaint = (intake.get('chief_complaint') or '').strip()
            vitals = intake.get('vitals') or {}
            vitals_str = \
                f"BP {vitals.get('bp') or ''}, HR {vitals.get('hr')}, RR {vitals.get('rr')}, Temp {vitals.get('temp_c')}, O2 {vitals.get('o2_sat')}".strip()
            message_text = (
                f"New patient {patient_profile.user.full_name} assigned for {normalized_inferred_specialty or normalized_requested_specialty} consultation. "
                f"Queue #{next_queue_number}. "
                f"Chief complaint: {chief_complaint or 'N/A'}. Vitals: {vitals_str}."
            )
        except Exception:
            message_text = (
                f"New patient {patient_profile.user.full_name} assigned for {normalized_inferred_specialty or normalized_requested_specialty} consultation. "
                f"Queue #{next_queue_number}."
            )
        Notification.objects.create(
            user=doctor_profile.user,
            message=message_text,
            is_read=False
        )

        # Create a PatientAssignment record for the doctor to view
        try:
            from .models import PatientAssignment
            assignment = PatientAssignment.objects.create(
                patient=patient_profile,
                doctor=doctor_profile,
                assigned_by=user,
                specialization_required=normalized_inferred_specialty or normalized_requested_specialty,
                assignment_reason=request.data.get('assignment_reason', ''),
                status='pending',
                priority=request.data.get('priority', 'medium')
            )
            logger.info(f"assign_patient_to_doctor:assignment_created assignment_id={getattr(assignment,'id',None)} patient_profile_id={getattr(patient_profile,'id',None)} doctor_profile_id={getattr(doctor_profile,'id',None)} status='pending' priority={request.data.get('priority','medium')}")
        except Exception:
            assignment = None

        # Broadcast real-time notification to the doctor via WebSocket
        try:
            channel_layer = get_channel_layer()
            intake = getattr(patient_profile, 'nursing_intake_assessment', {}) or {}
            notif_payload = {
                'event': 'patient_assigned',
                'patient': {
                    'id': patient_profile.id,
                    'user_id': patient_profile.user.id,
                    'full_name': patient_profile.user.full_name,
                    'hospital': patient_profile.hospital,
                    'medical_condition': patient_profile.medical_condition,
                },
                'specialization_required': normalized_inferred_specialty,
                'doctor_specialization': normalized_doctor_specialty,
                'queue_number': next_queue_number,
                'intake_summary': {
                    'chief_complaint': intake.get('chief_complaint'),
                    'vitals': intake.get('vitals'),
                    'assessed_at': intake.get('assessed_at'),
                },
            }
            # Include assignment data if created
            if assignment is not None:
                from .serializers import PatientAssignmentSerializer
                notif_payload['assignment'] = PatientAssignmentSerializer(assignment).data
            async_to_sync(channel_layer.group_send)(
                f'messaging_{doctor_profile.user.id}',
                {
                    'type': 'notification',
                    'notification': notif_payload
                }
            )
            logger.info(f"assign_patient_to_doctor:websocket_broadcasted doctor_user_id={getattr(doctor_profile.user,'id',None)} event='patient_assigned' payload_keys={list(notif_payload.keys())}")
        except Exception as ws_err:
            logger.warning(f"assign_patient_to_doctor:websocket_failed doctor_user_id={getattr(doctor_profile.user,'id',None)} error={ws_err}")
            # Non-blocking: if WS fails, proceed without raising
            pass
        
        return Response({
            'message': 'Patient assigned successfully',
            'appointment_id': appointment.appointment_id,
            'assignment_id': assignment.id if assignment is not None else None
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.exception(f"assign_patient_to_doctor:error user_id={getattr(getattr(request,'user',None),'id',None)} details={e}")
        return Response({
            'error': f'Failed to assign patient: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def send_message_notification(message):
    """Send real-time notification via WebSocket"""
    channel_layer = get_channel_layer()
    message_data = MessageSerializer(message).data
    
    # Send to all participants except sender
    for participant in message.conversation.participants.exclude(id=message.sender.id):
        group_name = f'messaging_{participant.id}'
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'new_message',
                'message': message_data
            }
        )

def send_delivery_notification(message, recipient_id):
    """Send delivery notification via WebSocket"""
    channel_layer = get_channel_layer()
    message_data = MessageSerializer(message).data
    
    group_name = f'messaging_{message.sender.id}'
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'message_delivered',
            'message': message_data
        }
    )

def send_read_notification(message, reader_id):
    """Send read notification via WebSocket"""
    channel_layer = get_channel_layer()
    message_data = MessageSerializer(message).data
    
    group_name = f'messaging_{message.sender.id}'
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'message_read',
            'message': message_data
        }
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_doctor_assignments(request):
    """
    Get patient assignments for the current doctor
    """
    try:
        user = request.user
        logger.info(f"get_doctor_assignments:start user_id={getattr(user,'id',None)} role={getattr(user,'role',None)}")

        # Check if user is a doctor
        if user.role != 'doctor':
            return Response({
                'error': 'Access denied. Only doctors can view their assignments.'
            }, status=status.HTTP_403_FORBIDDEN)

        # Get doctor profile
        from backend.users.models import GeneralDoctorProfile
        try:
            doctor_profile = GeneralDoctorProfile.objects.get(user=user)
        except GeneralDoctorProfile.DoesNotExist:
            return Response({
                'error': 'Doctor profile not found'
            }, status=status.HTTP_404_NOT_FOUND)

        # Get assignments for this doctor
        from .models import PatientAssignment
        assignments = PatientAssignment.objects.filter(
            doctor=doctor_profile
        ).select_related('patient__user', 'assigned_by')

        from .serializers import PatientAssignmentSerializer
        serializer = PatientAssignmentSerializer(assignments, many=True)
        logger.info(f"get_doctor_assignments:result count={len(serializer.data)} doctor_profile_id={getattr(doctor_profile,'id',None)}")
        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.exception(f"get_doctor_assignments:error user_id={getattr(getattr(request,'user',None),'id',None)} details={e}")
        return Response({
            'error': f'Failed to fetch assignments: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_assignment(request, assignment_id):
    """
    Accept a patient assignment
    """
    try:
        user = request.user

        # Check if user is a doctor
        if user.role != 'doctor':
            return Response({
                'error': 'Access denied. Only doctors can accept assignments.'
            }, status=status.HTTP_403_FORBIDDEN)

        # Get assignment
        from .models import PatientAssignment
        try:
            assignment = PatientAssignment.objects.get(
                id=assignment_id,
                doctor__user=user
            )
        except PatientAssignment.DoesNotExist:
            return Response({
                'error': 'Assignment not found or access denied'
            }, status=status.HTTP_404_NOT_FOUND)

        # Update assignment status
        assignment.status = 'accepted'
        assignment.accepted_at = timezone.now()
        assignment.save()

        from .serializers import PatientAssignmentSerializer
        serializer = PatientAssignmentSerializer(assignment)
        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': f'Failed to accept assignment: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def consultation_notes(request, assignment_id=None):
    """
    Get or create consultation notes for an assignment
    """
    try:
        user = request.user

        # Check if user is a doctor
        if user.role != 'doctor':
            return Response({
                'error': 'Access denied. Only doctors can manage consultation notes.'
            }, status=status.HTTP_403_FORBIDDEN)

        if request.method == 'GET':
            # Get consultation notes for assignment
            from .models import ConsultationNotes
            try:
                notes = ConsultationNotes.objects.get(
                    assignment_id=assignment_id,
                    doctor__user=user
                )
                from .serializers import ConsultationNotesSerializer
                serializer = ConsultationNotesSerializer(notes)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except ConsultationNotes.DoesNotExist:
                return Response({
                    'error': 'Consultation notes not found'
                }, status=status.HTTP_404_NOT_FOUND)

        elif request.method == 'POST':
            # Create or update consultation notes
            from .models import PatientAssignment, ConsultationNotes
            try:
                assignment = PatientAssignment.objects.get(
                    id=assignment_id,
                    doctor__user=user
                )
            except PatientAssignment.DoesNotExist:
                return Response({
                    'error': 'Assignment not found or access denied'
                }, status=status.HTTP_404_NOT_FOUND)

            # Create or update consultation notes
            notes, created = ConsultationNotes.objects.get_or_create(
                assignment=assignment,
                defaults={
                    'doctor': assignment.doctor,
                    'patient': assignment.patient,
                    'chief_complaint': request.data.get('chief_complaint', ''),
                    'history_of_present_illness': request.data.get('history_of_present_illness', ''),
                    'physical_examination': request.data.get('physical_examination', ''),
                    'diagnosis': request.data.get('diagnosis', ''),
                    'treatment_plan': request.data.get('treatment_plan', ''),
                    'medications_prescribed': request.data.get('medications_prescribed', ''),
                    'follow_up_instructions': request.data.get('follow_up_instructions', ''),
                    'additional_notes': request.data.get('additional_notes', ''),
                    'status': request.data.get('status', 'draft')
                }
            )

            if not created:
                # Update existing notes
                for field in ['chief_complaint', 'history_of_present_illness', 'physical_examination',
                             'diagnosis', 'treatment_plan', 'medications_prescribed', 'follow_up_instructions',
                             'additional_notes', 'status']:
                    if field in request.data:
                        setattr(notes, field, request.data[field])
                notes.save()

            from .serializers import ConsultationNotesSerializer
            serializer = ConsultationNotesSerializer(notes)
            return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': f'Failed to manage consultation notes: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Queue Management API Endpoints

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def queue_schedules(request):
    """
    GET: Retrieve all queue schedules for the current nurse
    POST: Create a new queue schedule
    """
    try:
        if request.method == 'GET':
            # Only nurses can view schedules
            if not hasattr(request.user, 'nurse_profile'):
                return Response({
                    'error': 'Only nurses can access queue schedules'
                }, status=status.HTTP_403_FORBIDDEN)
            
            schedules = QueueSchedule.objects.filter(
                nurse=request.user.nurse_profile
            ).order_by('-created_at')
            
            serializer = QueueScheduleSerializer(schedules, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        elif request.method == 'POST':
            # Only nurses can create schedules
            if not hasattr(request.user, 'nurse_profile'):
                return Response({
                    'error': 'Only nurses can create queue schedules'
                }, status=status.HTTP_403_FORBIDDEN)
            
            serializer = CreateQueueScheduleSerializer(data=request.data)
            if serializer.is_valid():
                # Check if schedule already exists for this nurse and department
                department = serializer.validated_data['department']
                existing_schedule = QueueSchedule.objects.filter(
                    nurse=request.user.nurse_profile,
                    department=department
                ).first()
                
                if existing_schedule:
                    return Response({
                        'error': f'A schedule already exists for {department}. Please edit the existing schedule instead.',
                        'existing_schedule_id': existing_schedule.id
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                schedule = serializer.save(nurse=request.user.nurse_profile)
                
                # Update queue status when schedule is created
                queue_status, created = QueueStatus.objects.get_or_create(
                    department=schedule.department,
                    defaults={
                        'is_open': False,
                        'current_schedule': schedule,
                        'last_updated_by': request.user
                    }
                )
                
                if not created:
                    queue_status.current_schedule = schedule
                    queue_status.last_updated_by = request.user
                    queue_status.save()
                
                # Log the schedule creation
                QueueStatusLog.objects.create(
                    department=schedule.department,
                    previous_status=False,
                    new_status=queue_status.is_open,
                    change_reason='schedule',
                    changed_by=request.user,
                    additional_notes=f'Schedule created from {schedule.start_time} to {schedule.end_time}'
                )
                
                # Broadcast schedule update via WebSocket (non-blocking)
                try:
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f'queue_{schedule.department}',
                        {
                            'type': 'queue_schedule_update',
                            'schedule': QueueScheduleSerializer(schedule).data,
                            'status': QueueStatusSerializer(queue_status).data
                        }
                    )
                except Exception:
                    pass
                
                return Response(QueueScheduleSerializer(schedule).data, status=status.HTTP_201_CREATED)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response({
            'error': f'Failed to manage queue schedules: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def queue_schedule_detail(request, schedule_id):
    """
    PUT: Update a queue schedule
    DELETE: Delete a queue schedule
    """
    try:
        # Only nurses can modify schedules
        if not hasattr(request.user, 'nurse_profile'):
            return Response({
                'error': 'Only nurses can modify queue schedules'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            schedule = QueueSchedule.objects.get(
                id=schedule_id,
                nurse=request.user.nurse_profile
            )
        except QueueSchedule.DoesNotExist:
            return Response({
                'error': 'Schedule not found or access denied'
            }, status=status.HTTP_404_NOT_FOUND)
        
        if request.method == 'PUT':
            serializer = CreateQueueScheduleSerializer(schedule, data=request.data, partial=True)
            if serializer.is_valid():
                updated_schedule = serializer.save()
                
                # Update related queue status
                try:
                    queue_status = QueueStatus.objects.get(current_schedule=schedule)
                    queue_status.last_updated_by = request.user
                    queue_status.save()
                    
                    # Log the schedule update
                    QueueStatusLog.objects.create(
                        department=updated_schedule.department,
                        previous_status=queue_status.is_open,
                        new_status=queue_status.is_open,
                        change_reason='schedule',
                        changed_by=request.user,
                        additional_notes='Schedule updated'
                    )
                    
                    # Broadcast update via WebSocket (non-blocking)
                    try:
                        channel_layer = get_channel_layer()
                        async_to_sync(channel_layer.group_send)(
                            f'queue_{updated_schedule.department}',
                            {
                                'type': 'queue_schedule_update',
                                'schedule': QueueScheduleSerializer(updated_schedule).data,
                                'status': QueueStatusSerializer(queue_status).data
                            }
                        )
                    except Exception:
                        pass
                except QueueStatus.DoesNotExist:
                    pass
                
                return Response(QueueScheduleSerializer(updated_schedule).data, status=status.HTTP_200_OK)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        elif request.method == 'DELETE':
            department = schedule.department
            
            # Update queue status to remove schedule reference
            try:
                queue_status = QueueStatus.objects.get(current_schedule=schedule)
                queue_status.current_schedule = None
                queue_status.is_open = False
                queue_status.last_updated_by = request.user
                queue_status.save()
                
                # Log the schedule deletion
                QueueStatusLog.objects.create(
                    department=department,
                    previous_status=queue_status.is_open,
                    new_status=False,
                    change_reason='schedule',
                    changed_by=request.user,
                    additional_notes='Schedule deleted'
                )
                
                # Broadcast update via WebSocket (non-blocking)
                try:
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f'queue_{department}',
                        {
                            'type': 'queue_schedule_update',
                            'schedule': None,
                            'status': QueueStatusSerializer(queue_status).data
                        }
                    )
                except Exception:
                    pass
            except QueueStatus.DoesNotExist:
                pass
            
            schedule.delete()
            return Response({'message': 'Schedule deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
    
    except Exception as e:
        return Response({
            'error': f'Failed to modify queue schedule: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def queue_status(request):
    """
    GET: Get current queue status for all departments or specific department
    POST: Update queue status (enable/disable queue)
    """
    try:
        if request.method == 'GET':
            department = request.query_params.get('department')
            
            if department:
                try:
                    status_obj = QueueStatus.objects.get(department=department)
                    serializer = QueueStatusSerializer(status_obj)
                    return Response(serializer.data, status=status.HTTP_200_OK)
                except QueueStatus.DoesNotExist:
                    return Response({
                        'error': f'Queue status not found for department: {department}'
                    }, status=status.HTTP_404_NOT_FOUND)
            else:
                statuses = QueueStatus.objects.all().order_by('department')
                serializer = QueueStatusSerializer(statuses, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
        
        elif request.method == 'POST':
            # Only nurses can update queue status
            if not hasattr(request.user, 'nurse_profile'):
                return Response({
                    'error': 'Only nurses can update queue status'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Validate the data manually
            department = request.data.get('department')
            is_open = request.data.get('is_open')
            
            if not department:
                return Response({
                    'error': 'Department is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if is_open is None:
                return Response({
                    'error': 'is_open field is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get or create queue status
            queue_status, created = QueueStatus.objects.get_or_create(
                department=department,
                defaults={
                    'is_open': is_open,
                    'last_updated_by': request.user
                }
            )
            
            # Track if we need to send notifications
            notification_stats = None
            
            if not created:
                old_status = queue_status.is_open
                queue_status.is_open = is_open
                queue_status.last_updated_by = request.user
                
                # Update status message
                queue_status.update_status_message()
                
                # Link to current schedule if available
                try:
                    current_schedule = QueueSchedule.objects.filter(
                        department=department,
                        is_active=True
                    ).first()
                    if current_schedule:
                        queue_status.current_schedule = current_schedule
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Could not link schedule: {str(e)}")
                
                queue_status.save()
                
                # Log the status change
                QueueStatusLog.objects.create(
                    department=department,
                    previous_status=old_status,
                    new_status=is_open,
                    change_reason='manual',
                    changed_by=request.user,
                    additional_notes=f'Queue {"enabled" if is_open else "disabled"} manually by {request.user.full_name}'
                )
                
                # If queue is being opened, send notifications to all patients
                if is_open and not old_status:
                    # Schedule patient notifications in background to avoid blocking the request
                    try:
                        import asyncio
                        import threading
                        from .async_services import AsyncNotificationService
                        
                        notification_message = f"The {department} queue is now OPEN! You can now join the queue."
                        
                        def _run_notify():
                            try:
                                asyncio.run(
                                    AsyncNotificationService.send_notification_to_all_patients(
                                        message=notification_message,
                                        department=department
                                    )
                                )
                            except Exception as e:
                                import logging
                                logging.getLogger(__name__).error(
                                    f"Error in background notifications: {str(e)}",
                                    exc_info=True
                                )
                        
                        threading.Thread(target=_run_notify, daemon=True).start()
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Error scheduling patient notifications: {str(e)}", exc_info=True)
                        # Continue even if scheduling fails
                
                # Broadcast status change via WebSocket (non-blocking)
                try:
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f'queue_{department}',
                        {
                            'type': 'queue_status_update',
                            'status': QueueStatusSerializer(queue_status).data,
                            'previous_status': old_status
                        }
                    )
                    
                    # Also notify department listeners of the new queue state
                    async_to_sync(channel_layer.group_send)(
                        f'queue_{department}',
                        {
                            'type': 'queue_notification',
                            'notification': {
                                'event': 'queue_opened' if is_open else 'queue_closed',
                                'department': department,
                                'message': f"Queue is now {'OPEN' if is_open else 'CLOSED'} for {department}.",
                                'timestamp': timezone.now().isoformat()
                            }
                        }
                    )
                    
                    # Mark WebSocket notifications as sent
                    if notification_stats and notification_stats.get('notification_ids'):
                        for notif_id in notification_stats['notification_ids']:
                            try:
                                notif = Notification.objects.get(id=notif_id)
                                notif.delivery_status = Notification.DELIVERY_SENT
                                notif.sent_at = timezone.now()
                                notif.delivery_attempts = 1
                                notif.save()
                            except Notification.DoesNotExist:
                                pass
                            except Exception as e:
                                import logging
                                logger = logging.getLogger(__name__)
                                logger.warning(f"Could not update notification {notif_id}: {str(e)}")
                                
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"WebSocket broadcast error: {str(e)}", exc_info=True)
                    # Non-blocking: continue even if WS fails
            
            response_data = {
                'message': f'Queue {"opened" if is_open else "closed"} successfully',
                'status': QueueStatusSerializer(queue_status).data
            }
            
            # Add notification stats if available
            if notification_stats:
                response_data['notification_stats'] = {
                    'total_patients_notified': notification_stats.get('notifications_created', 0),
                    'notification_failures': notification_stats.get('notifications_failed', 0)
                }
            
            return Response(response_data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': f'Failed to manage queue status: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def queue_status_logs(request):
    """
    Get queue status change logs for audit and analytics
    """
    try:
        department = request.query_params.get('department')
        limit = int(request.query_params.get('limit', 50))
        
        logs = QueueStatusLog.objects.all()
        
        if department:
            logs = logs.filter(queue_status__department=department)
        
        logs = logs.order_by('-timestamp')[:limit]
        
        serializer = QueueStatusLogSerializer(logs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': f'Failed to fetch queue status logs: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_queue(request):
    """
    Allow patients to join the queue if conditions are met
    """
    try:
        # Only patients can join queue
        if not hasattr(request.user, 'patient_profile'):
            return Response({
                'error': 'Only patients can join the queue'
            }, status=status.HTTP_403_FORBIDDEN)
        
        department = request.data.get('department', 'OPD')
        
        # Check if patient is already in queue (normal or priority)
        existing_normal = QueueManagement.objects.filter(
            patient=request.user.patient_profile,
            department=department,
            status='waiting'
        ).first()

        existing_priority = PriorityQueue.objects.filter(
            patient=request.user.patient_profile,
            status='waiting',
            department=department
        ).first()
        
        if existing_normal or existing_priority:
            eq = existing_priority or existing_normal
            position = getattr(eq, 'position_in_queue', None) or getattr(eq, 'priority_position', None)
            return Response({
                'error': 'You are already in the queue',
                'queue_info': {
                    'queue_number': eq.queue_number,
                    'position': position,
                    'estimated_wait_time': getattr(eq, 'estimated_wait_time', None)
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check queue status and schedule
        try:
            queue_status = QueueStatus.objects.get(department=department)
            
            # Check if queue is active
            if not queue_status.is_open:
                return Response({
                    'error': 'Queue is currently closed',
                    'queue_status': 'closed'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Queue is open; allow joining regardless of schedule time windows
            # Schedule windows still drive auto-close in other parts of the system
            if queue_status.current_schedule:
                schedule = queue_status.current_schedule
                # Intentionally skip time-based restriction here to respect manual toggles
        
        except QueueStatus.DoesNotExist:
            # Safety-net: auto-create QueueStatus using any active schedule for department
            schedule = QueueSchedule.objects.filter(department=department).first()
            is_open_now = False
            try:
                if schedule:
                    # Respect manual override if present; otherwise use schedule window
                    if schedule.manual_override and schedule.override_status is not None:
                        is_open_now = schedule.override_status == 'enabled'
                    else:
                        is_open_now = bool(schedule.is_active) and schedule.is_queue_open()
            except Exception:
                is_open_now = False

            queue_status = QueueStatus.objects.create(
                department=department,
                is_open=is_open_now,
                current_schedule=schedule if schedule else None,
                last_updated_by=request.user
            )

            # If queue was auto-created closed, inform the user clearly
            if not is_open_now:
                return Response({
                    'error': 'Queue is currently closed',
                    'queue_status': 'closed'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Determine if priority queue is requested
        priority_level = request.data.get('priority_level')
        allowed_levels = {'pwd', 'pregnant', 'senior', 'with_child'}
        
        if priority_level and priority_level in allowed_levels:
            queue_entry = PriorityQueue.objects.create(
                patient=request.user.patient_profile,
                department=department,
                priority_level=priority_level,
                status='waiting',
                skip_normal_queues=True
            )
            entry_type = 'priority'
            # Log queue join (as a system note; no status change)
            QueueStatusLog.objects.create(
                department=department,
                previous_status=queue_status.is_open,
                new_status=queue_status.is_open,
                change_reason='system',
                changed_by=request.user,
                additional_notes=f'Priority patient {request.user.get_full_name()} joined queue (#{queue_entry.queue_number})'
            )
            notif_message = f'You joined the priority queue. Your number is #{queue_entry.queue_number}. Position: {getattr(queue_entry, "priority_position", None)}'
        else:
            queue_entry = QueueManagement.objects.create(
                patient=request.user.patient_profile,
                department=department,
                status='waiting'
            )
            entry_type = 'normal'
            QueueStatusLog.objects.create(
                department=department,
                previous_status=queue_status.is_open,
                new_status=queue_status.is_open,
                change_reason='system',
                changed_by=request.user,
                additional_notes=f'Patient {request.user.get_full_name()} joined queue (#{queue_entry.queue_number})'
            )
            notif_message = f'You joined the queue. Your number is #{queue_entry.queue_number}. Position: {getattr(queue_entry, "position_in_queue", None)}'
        
        # Update queue status counts and broadcast updates
        waiting_normal = QueueManagement.objects.filter(
            department=department,
            status='waiting'
        ).count()
        waiting_priority = PriorityQueue.objects.filter(
            department=department,
            status='waiting'
        ).count()
        queue_status.total_waiting = waiting_normal + waiting_priority
        queue_status.last_updated_by = request.user
        queue_status.update_status_message()
        queue_status.save()

        # Create and mark notification as sent
        notif = Notification.objects.create(
            user=request.user,
            message=notif_message,
            channel=Notification.CHANNEL_WEBSOCKET,
            delivery_status=Notification.DELIVERY_SENT,
            sent_at=timezone.now()
        )

        # Broadcast updates via WebSocket (non-blocking)
        try:
            channel_layer = get_channel_layer()

            # Compute position and estimated wait for the user
            queue_entry.refresh_from_db()
            if entry_type == 'priority':
                position_value = queue_entry.priority_position
                est_td = queue_entry.get_estimated_wait_time()
            else:
                position_value = queue_entry.position_in_queue
                est_td = queue_entry.get_estimated_wait_time()
            estimated_wait_minutes = 0
            if est_td:
                try:
                    estimated_wait_minutes = int(est_td.total_seconds() // 60)
                except Exception:
                    estimated_wait_minutes = 0

            # Broadcast department-wide status
            async_to_sync(channel_layer.group_send)(
                f'queue_{department}',
                {
                    'type': 'queue_status_update',
                    'status': QueueStatusSerializer(queue_status).data
                }
            )

            # Notify user about successful join
            async_to_sync(channel_layer.group_send)(
                f'queue_user_{request.user.id}',
                {
                    'type': 'queue_notification',
                    'notification': {
                        'event': 'queue_joined',
                        'department': department,
                        'queue_number': queue_entry.queue_number,
                        'message': notif.message,
                        'notification': NotificationSerializer(notif).data,
                        'timestamp': timezone.now().isoformat()
                    }
                }
            )

            # Send the user's current position and estimated wait time
            async_to_sync(channel_layer.group_send)(
                f'queue_user_{request.user.id}',
                {
                    'type': 'queue_position_update',
                    'position': {
                        'position': str(position_value) if position_value is not None else '',
                        'estimated_wait_time': estimated_wait_minutes
                    }
                }
            )
        except Exception:
            pass
        
        from .serializers import QueueSerializer, PriorityQueueSerializer
        if entry_type == 'priority':
            return Response({'type': 'priority', 'entry': PriorityQueueSerializer(queue_entry).data}, status=status.HTTP_201_CREATED)
        else:
            return Response({'type': 'normal', 'entry': QueueSerializer(queue_entry).data}, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        return Response({
            'error': f'Failed to join queue: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_queue_availability(request):
    """
    Check if queue is available for joining (for frontend button state)
    """
    try:
        department = request.query_params.get('department', 'OPD')
        
        try:
            queue_status = QueueStatus.objects.get(department=department)
            
            # Check basic availability
            is_available = queue_status.is_open
            reason = None
            
            if not is_available:
                reason = 'Queue is currently closed'
            elif queue_status.current_schedule:
                # Intentionally ignore schedule time window when queue is manually open
                # Schedule windows still drive auto-close elsewhere
                # (No change to reason unless queue is closed)
                pass
            
            # Check if patient is already in queue (for patients only)
            already_in_queue = False
            if hasattr(request.user, 'patient_profile'):
                existing_normal = QueueManagement.objects.filter(
                    patient=request.user.patient_profile,
                    department=department,
                    status__in=['waiting', 'in_progress']
                ).exists()
                existing_priority = PriorityQueue.objects.filter(
                    patient=request.user.patient_profile,
                    department=department,
                    status__in=['waiting', 'in_progress']
                ).exists()
                
                if existing_normal or existing_priority:
                    already_in_queue = True
                    is_available = False
                    reason = 'You are already in the queue'
            
            return Response({
                'is_available': is_available,
                'reason': reason,
                'already_in_queue': already_in_queue,
                'queue_status': QueueStatusSerializer(queue_status).data
            }, status=status.HTTP_200_OK)
        
        except QueueStatus.DoesNotExist:
            return Response({
                'is_available': False,
                'reason': 'Queue system is not configured for this department',
                'already_in_queue': False,
                'queue_status': None
            }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': f'Failed to check queue availability: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Lightweight UI configuration endpoint for frontend styling
@api_view(['GET'])
@permission_classes([AllowAny])
def ui_config(request):
    """Return UI configuration values for patient-facing elements.

    Moving these values to the backend allows central control of visual
    constants without redeploying the app.
    """
    config = {
        'patient_bottom_nav_bg': '#f3f4f6',
        'patient_nav_pill_bg': '#f5f5f7',
    }
    return Response(config, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_queue_processing(request):
    """
    Nurses start processing the next patient in a department queue.
    Triggers real-time notification to the patient with timestamp tracking and delivery status.
    """
    try:
        # Only nurses can start processing
        if not hasattr(request.user, 'nurse_profile'):
            return Response({'error': 'Only nurses can start queue processing'}, status=status.HTTP_403_FORBIDDEN)

        department = request.data.get('department')
        if not department:
            return Response({'error': 'Department is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure queue status exists and is open
        try:
            queue_status = QueueStatus.objects.get(department=department)
        except QueueStatus.DoesNotExist:
            return Response({'error': 'Queue status not found for department'}, status=status.HTTP_404_NOT_FOUND)

        if not queue_status.is_open:
            return Response({'error': 'Queue is currently closed'}, status=status.HTTP_400_BAD_REQUEST)

        # First, complete any currently in-progress patient
        prev_priority = PriorityQueue.objects.filter(
            department=department,
            status='in_progress'
        ).order_by('started_at', 'enqueue_time').first()
        prev_normal = QueueManagement.objects.filter(
            department=department,
            status='in_progress'
        ).order_by('started_at', 'enqueue_time').first()
        previous_entry = prev_priority or prev_normal
        if previous_entry:
            try:
                previous_entry.mark_completed()
                # Ensure dequeue_time is set for normal queue completion
                if isinstance(previous_entry, QueueManagement) and not previous_entry.dequeue_time:
                    previous_entry.dequeue_time = timezone.now()
                    previous_entry.save()
            except Exception:
                # Fallback to direct update if model method is unavailable in this context
                if isinstance(previous_entry, PriorityQueue):
                    PriorityQueue.objects.filter(pk=previous_entry.id).update(
                        status='completed',
                        finished_at=timezone.now()
                    )
                else:
                    QueueManagement.objects.filter(pk=previous_entry.id).update(
                        status='completed',
                        finished_at=timezone.now(),
                        dequeue_time=timezone.now()
                    )
                    QueueManagement.update_queue_positions_for_department(department)
            # Clear current serving if it was the previous entry
            if queue_status.current_serving == previous_entry.queue_number:
                queue_status.current_serving = None

        # Get the next waiting patient, prioritizing priority queue
        next_priority = PriorityQueue.objects.filter(
            department=department,
            status='waiting'
        ).order_by('priority_position', 'enqueue_time').first()

        next_type = None
        if next_priority:
            PriorityQueue.objects.filter(pk=next_priority.id).update(
                status='in_progress',
                started_at=timezone.now()
            )
            next_entry = next_priority
            next_type = 'priority'
        else:
            next_normal = QueueManagement.objects.filter(
                department=department,
                status='waiting'
            ).order_by('position_in_queue', 'enqueue_time').first()

            if not next_normal:
                # Update status to reflect no waiting patients
                queue_status.current_serving = None
                queue_status.total_waiting = 0
                queue_status.update_status_message()
                queue_status.last_updated_by = request.user
                queue_status.save()
                return Response({'message': 'No patients waiting in the queue'}, status=status.HTTP_200_OK)

            QueueManagement.objects.filter(pk=next_normal.id).update(
                status='in_progress',
                started_at=timezone.now()
            )
            next_entry = next_normal
            next_type = 'normal'

        # Refresh from DB to get updated values
        next_entry.refresh_from_db()

        # Update queue status metrics across both queues
        remaining_waiting = (
            QueueManagement.objects.filter(department=department, status='waiting').count() +
            PriorityQueue.objects.filter(department=department, status='waiting').count()
        )

        queue_status.current_serving = next_entry.queue_number
        queue_status.total_waiting = remaining_waiting
        queue_status.last_updated_by = request.user
        queue_status.update_status_message()
        queue_status.save()

        # Log processing start (system note; no status change)
        try:
            QueueStatusLog.objects.create(
                department=department,
                previous_status=queue_status.is_open,
                new_status=queue_status.is_open,
                change_reason='system',
                changed_by=request.user,
                additional_notes=f'Started processing {"priority" if next_type == "priority" else "normal"} queue (#{next_entry.queue_number})'
            )
        except Exception:
            pass

        # Create and mark notification as sent
        notif = Notification.objects.create(
            user=next_entry.patient.user,
            message=f'Your turn at {department}. Please proceed to the triage room for {department} (Queue #{next_entry.queue_number}).',
            channel=Notification.CHANNEL_WEBSOCKET,
            delivery_status=Notification.DELIVERY_SENT,
            sent_at=timezone.now()
        )

        # Broadcast via WebSocket to department and specific patient
        try:
            channel_layer = get_channel_layer()
            # Department status update
            async_to_sync(channel_layer.group_send)(
                f'queue_{department}',
                {
                    'type': 'queue_status_update',
                    'status': QueueStatusSerializer(queue_status).data
                }
            )
            # Patient-specific notification
            async_to_sync(channel_layer.group_send)(
                f'queue_user_{next_entry.patient.user.id}',
                {
                    'type': 'queue_notification',
                    'notification': {
                        'event': 'queue_started',
                        'department': department,
                        'destination_department': department,
                        'instruction': 'Proceed to the triage room',
                        'queue_number': next_entry.queue_number,
                        'notification': NotificationSerializer(notif).data,
                        'timestamp': timezone.now().isoformat()
                    }
                }
            )
        except Exception:
            # Non-blocking: if WS fails, keep REST response
            pass

        # Build optional patient profile payload for nurse UI data transfer
        patient_profile_payload = None
        try:
            # Import here to avoid circular imports at module level
            from backend.users.models import PatientProfile
            patient_profile = PatientProfile.objects.select_related('user').filter(user=next_entry.patient.user).first()
            if patient_profile:
                # Minimal, backward-compatible profile fields
                patient_profile_payload = {
                    'id': patient_profile.id,
                    'user_id': patient_profile.user.id,
                    'full_name': patient_profile.user.full_name,
                    'email': patient_profile.user.email,
                    'age': (timezone.now().year - patient_profile.user.date_of_birth.year) if getattr(patient_profile.user, 'date_of_birth', None) else None,
                    'gender': getattr(patient_profile.user, 'gender', None),
                    'blood_type': getattr(patient_profile, 'blood_type', None),
                    'medical_condition': getattr(patient_profile, 'medical_condition', None),
                    'hospital': getattr(patient_profile, 'hospital', None),
                    'insurance_provider': getattr(patient_profile, 'insurance_provider', None),
                    'room_number': getattr(patient_profile, 'room_number', None),
                    'admission_type': getattr(patient_profile, 'admission_type', None),
                    'date_of_admission': getattr(patient_profile, 'date_of_admission', None),
                    'discharge_date': getattr(patient_profile, 'discharge_date', None),
                    'medication': getattr(patient_profile, 'medication', None),
                    'test_results': getattr(patient_profile, 'test_results', None),
                    'assigned_doctor': (getattr(patient_profile.assigned_doctor, 'full_name', None) if getattr(patient_profile, 'assigned_doctor', None) else None),
                    'department': department,
                }
        except Exception:
            # If profile building fails, continue with core payload only
            patient_profile_payload = None

        # Response payload
        return Response({
            'message': 'Queue processing started',
            'department': department,
            'current_serving': next_entry.queue_number,
            'total_waiting': remaining_waiting,
            'queue_status': QueueStatusSerializer(queue_status).data,
            'patient': {
                'id': next_entry.patient.user.id,
                'name': next_entry.patient.user.full_name
            },
            'patient_profile': patient_profile_payload,  # optional, backward-compatible
            'notification': NotificationSerializer(notif).data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': f'Failed to start queue processing: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirm_notification_delivery(request):
    """
    Patient confirms delivery of a notification.
    Sets delivered_at and delivery_status=delivered.
    """
    try:
        notif_id = request.data.get('notification_id')
        if not notif_id:
            return Response({'error': 'notification_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            notif = Notification.objects.get(id=notif_id)
        except Notification.DoesNotExist:
            return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

        # Only the recipient (or staff) can confirm delivery
        if notif.user != request.user and not request.user.is_staff:
            return Response({'error': 'Not authorized to confirm this notification'}, status=status.HTTP_403_FORBIDDEN)

        notif.delivery_status = Notification.DELIVERY_DELIVERED
        notif.delivered_at = timezone.now()
        notif.save()

        return Response({'message': 'Notification delivery confirmed', 'notification': NotificationSerializer(notif).data}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': f'Failed to confirm delivery: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def nurse_remove_from_queue(request):
    try:
        # Only nurses can modify queues
        if not hasattr(request.user, 'nurse_profile'):
            return Response({'error': 'Only nurses can modify queues'}, status=status.HTTP_403_FORBIDDEN)

        entry_id = request.data.get('entry_id')
        queue_type = request.data.get('queue_type', 'normal')
        department = request.data.get('department', 'OPD')

        if not entry_id:
            return Response({'error': 'entry_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Get queue status if exists
        try:
            queue_status = QueueStatus.objects.get(department=department)
        except QueueStatus.DoesNotExist:
            queue_status = None

        if queue_type == 'priority':
            # Accept both primary key and queue_number for robustness
            removed_entry = PriorityQueue.objects.filter(id=entry_id, department=department).first()
            if not removed_entry:
                removed_entry = PriorityQueue.objects.filter(queue_number=entry_id, department=department).first()
            if not removed_entry:
                return Response({'error': 'Priority queue entry not found'}, status=status.HTTP_404_NOT_FOUND)

            # If current serving matches, clear it
            if queue_status and queue_status.current_serving == removed_entry.queue_number:
                queue_status.current_serving = None

            # Delete the entry
            removed_entry.delete()
        else:
            # Accept both primary key and queue_number
            removed_entry = QueueManagement.objects.filter(id=entry_id, department=department).first()
            if not removed_entry:
                removed_entry = QueueManagement.objects.filter(queue_number=entry_id, department=department).first()
            if not removed_entry:
                return Response({'error': 'Queue entry not found'}, status=status.HTTP_404_NOT_FOUND)

            if queue_status and queue_status.current_serving == removed_entry.queue_number:
                queue_status.current_serving = None

            # Delete and recalculate positions for normal queue
            removed_entry.delete()
            QueueManagement.update_queue_positions_for_department(department)

        # Update QueueStatus counts and broadcast
        if queue_status:
            queue_status.total_waiting = (
                QueueManagement.objects.filter(department=department, status='waiting').count() +
                PriorityQueue.objects.filter(department=department, status='waiting').count()
            )
            queue_status.last_updated_by = request.user
            queue_status.update_status_message()
            queue_status.save()

            # Log removal
            try:
                QueueStatusLog.objects.create(
                    queue_status=queue_status,
                    action='entry_removed',
                    performed_by=request.user,
                    details=f'Removed {"priority" if queue_type == "priority" else "normal"} queue entry'
                )
            except Exception:
                pass

            # Broadcast via WebSocket
            try:
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f'queue_{department}',
                    {
                        'type': 'queue_status_update',
                        'status': QueueStatusSerializer(queue_status).data
                    }
                )
            except Exception:
                pass

        return Response({'message': 'Entry removed successfully'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': f'Failed to remove entry: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def nurse_mark_served(request):
    try:
        # Only nurses can modify queues
        if not hasattr(request.user, 'nurse_profile'):
            return Response({'error': 'Only nurses can modify queues'}, status=status.HTTP_403_FORBIDDEN)

        entry_id = request.data.get('entry_id')
        queue_type = request.data.get('queue_type', 'normal')
        department = request.data.get('department', 'OPD')

        if not entry_id:
            return Response({'error': 'entry_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Get queue status if exists
        try:
            queue_status = QueueStatus.objects.get(department=department)
        except QueueStatus.DoesNotExist:
            queue_status = None

        # Fetch and mark entry as completed (accept id or queue_number)
        if queue_type == 'priority':
            entry = PriorityQueue.objects.filter(id=entry_id, department=department).first()
            if not entry:
                entry = PriorityQueue.objects.filter(queue_number=entry_id, department=department).first()
            if not entry:
                return Response({'error': 'Priority queue entry not found'}, status=status.HTTP_404_NOT_FOUND)
            entry.mark_completed()
        else:
            entry = QueueManagement.objects.filter(id=entry_id, department=department).first()
            if not entry:
                entry = QueueManagement.objects.filter(queue_number=entry_id, department=department).first()
            if not entry:
                return Response({'error': 'Queue entry not found'}, status=status.HTTP_404_NOT_FOUND)
            entry.mark_completed()
            # Ensure dequeue_time is set for normal queue completion
            if hasattr(entry, 'dequeue_time') and not entry.dequeue_time:
                entry.dequeue_time = timezone.now()
                entry.save()

        # Update QueueStatus counts and broadcast
        if queue_status:
            queue_status.total_waiting = (
                QueueManagement.objects.filter(department=department, status='waiting').count() +
                PriorityQueue.objects.filter(department=department, status='waiting').count()
            )
            # Clear current serving if this was the current one
            if queue_status.current_serving == entry.queue_number:
                queue_status.current_serving = None
            queue_status.last_updated_by = request.user
            queue_status.update_status_message()
            queue_status.save()

            # Log completion
            try:
                QueueStatusLog.objects.create(
                    queue_status=queue_status,
                    action='entry_completed',
                    performed_by=request.user,
                    details=f'Served {"priority" if queue_type == "priority" else "normal"} queue (#{entry.queue_number})'
                )
            except Exception:
                pass

            # Notify patient
            try:
                Notification.objects.create(
                    user=entry.patient.user,
                    message=f'Your queue at {department} has been completed (#{entry.queue_number}).',
                    channel=Notification.CHANNEL_WEBSOCKET,
                    delivery_status=Notification.DELIVERY_SENT,
                    sent_at=timezone.now()
                )
            except Exception:
                pass

            # Broadcast via WebSocket
            try:
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f'queue_{department}',
                    {
                        'type': 'queue_status_update',
                        'status': QueueStatusSerializer(queue_status).data
                    }
                )
            except Exception:
                pass

        return Response({'message': 'Entry marked as served'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': f'Failed to mark as served: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
