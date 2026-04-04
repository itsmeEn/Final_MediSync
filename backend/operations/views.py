from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.core.cache import cache
from django.db import DatabaseError, transaction, connection
from django.db.models import Q
from datetime import datetime, timedelta
import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import uuid
import time

from .models import QueueManagement, QueueStatus, Notification, PainAssessment, AppointmentManagement, PatientAssignment, ConsultationNotes, DailySequenceCounter
from backend.users.models import User, GeneralDoctorProfile, NurseProfile, PatientProfile
from .serializers import (
    DashboardStatsSerializer, 
    NotificationSerializer, 
    QueueSerializer, 
    PainAssessmentSerializer
)

logger = logging.getLogger(__name__)

QUEUE_SCHEDULES_STORE = []
QUEUE_STATUS_STORE = {}
NEXT_SCHEDULE_ID = 1

def _corr_id(request):
    req_id = request.META.get('HTTP_X_REQUEST_ID') or request.headers.get('X-Request-ID') if hasattr(request, 'headers') else None
    if not req_id:
        req_id = str(uuid.uuid4())
    return req_id

def _broadcast(group, event, attempts=3, base_delay=0.1):
    try:
        channel_layer = get_channel_layer()
    except Exception:
        return
    for i in range(attempts):
        try:
            async_to_sync(channel_layer.group_send)(group, event)
            return
        except Exception:
            if i == attempts - 1:
                return
            time.sleep(base_delay * (2 ** i))

def _safe_insert_queue_entry(patient_profile, department, queue_number, est_wait, waiting_count):
    try:
        obj = QueueManagement.objects.create(
            patient=patient_profile,
            department=department,
            queue_number=queue_number,
            status='waiting',
            estimated_wait_time=est_wait,
            total_patients=waiting_count + 1 
        )
        return obj
    except DatabaseError as e:
        msg = str(e)
        if 'daily_sequence_number' not in msg and 'queue_management.daily_sequence_number' not in msg:
            raise
        with connection.cursor() as cur:
            vendor = connection.vendor
            if vendor == 'postgresql':
                cur.execute(
                    """
                    INSERT INTO queue_management
                    (patient_id, queue_number, total_patients, estimated_wait_time, department, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                    RETURNING id
                    """,
                    [patient_profile.id, queue_number, waiting_count + 1, est_wait, department, 'waiting']
                )
                row = cur.fetchone()
                new_id = row[0] if row else None
            else:
                cur.execute(
                    """
                    INSERT INTO queue_management
                    (patient_id, queue_number, total_patients, estimated_wait_time, department, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                    [patient_profile.id, queue_number, waiting_count + 1, est_wait, department, 'waiting']
                )
                cur.execute("SELECT MAX(id) FROM queue_management")
                new_id = cur.fetchone()[0]
        return QueueManagement.objects.only('id').get(id=new_id)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def doctor_dashboard_stats(request):
    """
    Get dashboard statistics for a doctor
    """
    try:
        doctor = request.user
        today = timezone.now().date()
        
        # 1. Total Appointments (dummy for now)
        total_appointments = 0
        
        # 2. Patients in Queue
        normal_queue = QueueManagement.objects.filter(
            department='OPD',
            status='waiting',
            is_priority=False
        ).count()
        
        priority_queue = QueueManagement.objects.filter(
            department='OPD',
            status='waiting',
            is_priority=True
        ).count()
        
        total_patients = normal_queue + priority_queue
        
        # 3. Notifications
        notifications = Notification.objects.filter(
            user=doctor,
            is_read=False
        ).count()
        
        # 4. Monthly cancelled
        monthly_cancelled = 0
        
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
    return Response([], status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def doctor_queue_patients(request):
    """
    Get patients in queue for the current doctor
    """
    try:
        normal_queue = QueueManagement.objects.filter(
            department='OPD',
            status='waiting'
        ).order_by('created_at') # 'position_in_queue' might not exist, checking models... models.py said queue_number
        
        normal_serializer = QueueSerializer(normal_queue, many=True)
        
        return Response({
            'normal_queue': normal_serializer.data,
            'priority_queue': []
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
        ).order_by('-created_at')[:10]
        
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to fetch notifications: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def mark_notification_as_read(request, notification_id):
    try:
        doctor = request.user
        notification = Notification.objects.filter(
            id=notification_id,
            user=doctor
        ).first()
        
        if not notification:
            return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)
        
        notification.is_read = True
        notification.save()
        return Response({'message': 'Notification marked as read'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read(request):
    try:
        doctor = request.user
        Notification.objects.filter(user=doctor, is_read=False).update(is_read=True)
        return Response({'message': 'All notifications marked as read'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_patient_pain_history(request, patient_id):
    """
    Get pain assessment history for a specific patient.
    """
    try:
        # Check permissions - only doctors and nurses can view other patients' history
        if request.user.role not in ['doctor', 'nurse', 'admin']:
             return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        # Try to resolve patient
        try:
            # Check if patient_id is PatientProfile ID
            patient = PatientProfile.objects.get(id=patient_id)
        except PatientProfile.DoesNotExist:
            try:
                # Check if patient_id is User ID
                patient = PatientProfile.objects.get(user__id=patient_id)
            except PatientProfile.DoesNotExist:
                 return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)

        pain_assessments = PainAssessment.objects.filter(patient=patient).order_by('-created_at')
        serializer = PainAssessmentSerializer(pain_assessments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error fetching pain history: {str(e)}")
        return Response({'error': 'Failed to fetch pain history'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def record_pain_assessment(request, patient_id):
    """
    Record a new pain assessment for a patient.
    """
    try:
        # Check permissions
        if request.user.role not in ['doctor', 'nurse', 'admin']:
             return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        # Try to resolve patient
        try:
            patient = PatientProfile.objects.get(id=patient_id)
        except PatientProfile.DoesNotExist:
            try:
                patient = PatientProfile.objects.get(user__id=patient_id)
            except PatientProfile.DoesNotExist:
                 return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        data['patient'] = patient.id
        # performed_by is set in perform_create equivalent logic or explicitly here if needed
        # But since we are using functional views, we handle it manually or pass context
        
        serializer = PainAssessmentSerializer(data=data)
        if serializer.is_valid():
            serializer.save(performed_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error recording pain assessment: {str(e)}")
        return Response({'error': 'Failed to record assessment'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def patient_assessments(request):
    try:
        status_filter = str(request.query_params.get('status', '')).lower()
        results = []
        count = 0
        if status_filter == 'completed':
            from .models import PatientAssessmentArchive
            from .serializers import PatientAssessmentArchiveSerializer
            qs = PatientAssessmentArchive.objects.all()
            hospital = getattr(request.user, 'hospital_name', None)
            if hospital:
                qs = qs.filter(hospital_name__iexact=hospital)
            serializer = PatientAssessmentArchiveSerializer(qs.order_by('-last_assessed_at')[:50], many=True)
            results = serializer.data
            count = len(results)
        elif status_filter == 'in_progress':
            results = []
            count = 0
        else:
            results = []
            count = 0
        return Response({'results': results, 'count': count}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': f'Failed to fetch patient assessments: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def nurse_send_patient_records(request):
    try:
        corr = _corr_id(request)
        if request.user.role != 'nurse':
            return Response({'error': 'Only nurses can send patient records.'}, status=status.HTTP_403_FORBIDDEN)
        patient_id = request.data.get('patient_id')
        doctor_id = request.data.get('doctor_id')
        note = request.data.get('message') or ''
        if not patient_id or not doctor_id:
            return Response({'error': 'patient_id and doctor_id are required.'}, status=status.HTTP_400_BAD_REQUEST)

        patient_profile = PatientProfile.objects.filter(id=patient_id).first() or PatientProfile.objects.filter(user_id=patient_id).first()
        if not patient_profile:
            return Response({'error': 'Patient not found.'}, status=status.HTTP_404_NOT_FOUND)

        doctor_user = User.objects.filter(id=doctor_id, role=User.Role.DOCTOR).first()
        if not doctor_user:
            return Response({'error': 'Doctor not found.'}, status=status.HTTP_404_NOT_FOUND)

        patient_profile.assigned_doctor = doctor_user
        patient_profile.save(update_fields=['assigned_doctor'])

        msg = f"Nurse {request.user.full_name} sent patient records for {patient_profile.user.full_name} (PatientProfile ID: {patient_profile.id})."
        if isinstance(note, str) and note.strip():
            msg = msg + f" Note: {note.strip()}"

        try:
            doctor_profile = GeneralDoctorProfile.objects.filter(user=doctor_user).first()
            if doctor_profile:
                from backend.operations.models import PatientAssignment
                existing = PatientAssignment.objects.filter(
                    patient=patient_profile,
                    doctor=doctor_profile,
                    status__in=['pending', 'accepted', 'in_progress']
                ).order_by('-assigned_at').first()
                if not existing:
                    PatientAssignment.objects.create(
                        assigned_by=request.user,
                        doctor=doctor_profile,
                        patient=patient_profile,
                        specialization_required=doctor_profile.specialization or '',
                        assignment_reason=note.strip() if isinstance(note, str) else '',
                        status='pending',
                        priority='medium'
                    )
        except Exception:
            pass

        Notification.objects.create(
            user=doctor_user,
            message=msg,
            channel=Notification.CHANNEL_WEBSOCKET,
            delivery_status=Notification.DELIVERY_PENDING,
        )

        logger.info(f"[{corr}] nurse_send_patient_records nurse_id={request.user.id} patient_profile_id={patient_profile.id} doctor_id={doctor_user.id}")
        return Response({'success': True, 'message': 'Patient records sent to doctor.'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --- Stubs for missing views referenced in urls.py ---

@api_view(['GET', 'POST'])
def doctor_blocked_dates(request): return Response([], status=status.HTTP_200_OK)

@api_view(['POST'])
def doctor_block_date(request): return Response({}, status=status.HTTP_200_OK)

@api_view(['POST'])
def doctor_create_appointment(request): return Response({}, status=status.HTTP_200_OK)

@api_view(['POST'])
def schedule_appointment(request): return Response({}, status=status.HTTP_200_OK)

@api_view(['POST'])
def reschedule_appointment(request, appointment_id): return Response({}, status=status.HTTP_200_OK)

@api_view(['POST'])
def cancel_appointment(request, appointment_id): return Response({}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_in_appointment(request, appointment_id):
    if request.user.role not in ['doctor', 'nurse', 'admin']:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    appt = AppointmentManagement.objects.filter(appointment_id=appointment_id).first()
    if not appt:
        return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)
    appt.status = 'checked_in'
    appt.checked_in_at = timezone.now()
    appt.save(update_fields=['status', 'checked_in_at', 'updated_at'])
    return Response({'success': True}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_consultation(request, appointment_id):
    if request.user.role not in ['doctor', 'admin']:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    appt = AppointmentManagement.objects.filter(appointment_id=appointment_id).first()
    if not appt:
        return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)
    appt.status = 'in_progress'
    appt.consultation_started_at = timezone.now()
    appt.save(update_fields=['status', 'consultation_started_at', 'updated_at'])
    return Response({'success': True}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def finish_consultation(request, appointment_id):
    if request.user.role not in ['doctor', 'admin']:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    appt = AppointmentManagement.objects.filter(appointment_id=appointment_id).first()
    if not appt:
        return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)
    appt.status = 'completed'
    appt.consultation_finished_at = timezone.now()
    appt.save(update_fields=['status', 'consultation_finished_at', 'updated_at'])
    return Response({'success': True}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notify_patient_appointment(request, appointment_id):
    if request.user.role not in ['doctor', 'nurse', 'admin']:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    appt = AppointmentManagement.objects.filter(appointment_id=appointment_id).select_related('patient__user', 'doctor__user').first()
    if not appt:
        return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)
    try:
        dt = appt.appointment_date
        msg = f"Appointment reminder: {dt.strftime('%Y-%m-%d %H:%M')}."
    except Exception:
        msg = "Appointment reminder."
    notif = Notification.objects.create(
        user=appt.patient.user,
        message=msg,
        channel=Notification.CHANNEL_WEBSOCKET,
        delivery_status=Notification.DELIVERY_SENT,
        sent_at=timezone.now(),
    )
    payload = NotificationSerializer(notif).data
    return Response({'message': 'Notification queued', 'notification': payload}, status=status.HTTP_200_OK)

@api_view(['GET'])
def patient_appointments(request): return Response([], status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def patient_dashboard_summary(request):
    try:
        corr = _corr_id(request)
        user = request.user
        dept = request.query_params.get('department') or 'OPD'
        try:
            patient_profile = user.patient_profile
        except (AttributeError, PatientProfile.DoesNotExist):
            patient_profile = PatientProfile.objects.filter(user=user).first()
        my_entry = None
        if patient_profile:
            my_entry = (QueueManagement.objects
                        .only('queue_number', 'status', 'created_at')
                        .filter(patient=patient_profile, department=dept, status__in=['waiting', 'in_progress'])
                        .order_by('created_at')
                        .first())
        now_serving = (QueueManagement.objects
                       .only('queue_number', 'patient', 'created_at', 'is_priority', 'priority_position')
                       .filter(department=dept, status='in_progress')
                       .order_by('-is_priority', 'priority_position', 'created_at')
                       .first())
        waiting_count = QueueManagement.objects.filter(
            department=dept,
            status='waiting'
        ).count()
        estimated_wait = waiting_count * 15
        payload = {
            'department': dept,
            'nowServing': now_serving.queue_number if now_serving else '',
            'currentPatient': now_serving.patient.user.full_name if now_serving else '',
            'myPosition': 'Now Serving' if my_entry and my_entry.status == 'in_progress' else (str(my_entry.queue_number) if my_entry else ''),
            'estimatedWaitMins': estimated_wait,
            'progressValue': 0,
        }
        logger.debug(f"[{corr}] patient_dashboard_summary user={user.id} dept={dept} -> {payload}")
        return Response(payload, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_conversations(request): return Response([], status=status.HTTP_200_OK)

@api_view(['POST'])
def create_conversation(request): return Response({}, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_messages(request, conversation_id): return Response([], status=status.HTTP_200_OK)

@api_view(['POST'])
def send_message(request, conversation_id): return Response({}, status=status.HTTP_200_OK)

@api_view(['POST'])
def add_reaction(request, message_id): return Response({}, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_available_users(request): return Response([], status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def available_doctors_free(request):
    """
    Get list of available doctors for the nurse's hospital.
    """
    try:
        user = request.user
        hospital_name = user.hospital_name
        
        # Base query for doctors
        doctors_query = User.objects.filter(role=User.Role.DOCTOR, is_active=True)
        
        # Filter by hospital if nurse has one
        if hospital_name:
            doctors_query = doctors_query.filter(hospital_name__iexact=hospital_name)
            
        # Get doctors who are available
        # efficient way: filter users who have a related doctor_profile with available_for_consultation=True
        doctors_query = doctors_query.filter(doctor_profile__available_for_consultation=True)
        
        doctors_data = []
        for doctor in doctors_query:
            try:
                profile = doctor.doctor_profile
                doctors_data.append({
                    'id': doctor.id,
                    'full_name': doctor.full_name,
                    'specialization': profile.specialization,
                    'email': doctor.email if request.GET.get('include_email') == 'true' else None,
                    'availability': 'available', # Since we filtered for available ones
                    'hospital_name': doctor.hospital_name
                })
            except GeneralDoctorProfile.DoesNotExist:
                continue
                
        return Response({
            'doctors': doctors_data,
            'checked_at': timezone.now().isoformat()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error fetching available doctors: {str(e)}")
        return Response({
            'error': 'Failed to fetch available doctors',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def available_nurses(request): return Response([], status=status.HTTP_200_OK)

@api_view(['GET'])
def nurses_list(request): return Response([], status=status.HTTP_200_OK)

@api_view(['POST'])
def nurse_capacity_validate(request): return Response({}, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_message_notifications(request): return Response([], status=status.HTTP_200_OK)

@api_view(['POST'])
def mark_notification_as_sent(request, notification_id): return Response({}, status=status.HTTP_200_OK)

@api_view(['POST'])
def mark_message_as_read(request, message_id): return Response({}, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_medicine_inventory(request): return Response([], status=status.HTTP_200_OK)

@api_view(['POST'])
def add_medicine(request): return Response({}, status=status.HTTP_200_OK)

@api_view(['PUT'])
def update_medicine(request, medicine_id): return Response({}, status=status.HTTP_200_OK)

@api_view(['POST'])
def dispense_medicine(request, medicine_id): return Response({}, status=status.HTTP_200_OK)

@api_view(['DELETE'])
def delete_medicine(request, medicine_id): return Response({}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def nurse_queue_patients(request):
    try:
        corr = _corr_id(request)
        department = request.query_params.get('department') or 'OPD'
        priority_qs = QueueManagement.objects.only(
            'id', 'patient', 'queue_number', 'department', 'status', 'created_at', 'priority_level', 'priority_position', 'is_priority'
        ).filter(
            department=department,
            status='waiting',
            is_priority=True
        ).order_by('priority_position', 'created_at')
        normal_qs = QueueManagement.objects.only(
            'id', 'patient', 'queue_number', 'department', 'status', 'created_at', 'is_priority'
        ).filter(
            department=department,
            status='waiting',
            is_priority=False
        ).order_by('created_at')
        priority_serializer = QueueSerializer(priority_qs, many=True)
        normal_serializer = QueueSerializer(normal_qs, many=True)
        all_patients = []
        for obj in priority_qs:
            all_patients.append({
                'id': obj.id,
                'queue_number': obj.queue_number,
                'patient_name': obj.patient.user.full_name,
                'queue_type': 'priority',
                'department': obj.department,
                'status': obj.status,
                'enqueue_time': obj.created_at.isoformat(),
                'priority_level': obj.priority_level or None,
                'priority_position': obj.priority_position or 0,
            })
        for obj in normal_qs:
            all_patients.append({
                'id': obj.id,
                'queue_number': obj.queue_number,
                'patient_name': obj.patient.user.full_name,
                'queue_type': 'normal',
                'department': obj.department,
                'status': obj.status,
                'enqueue_time': obj.created_at.isoformat(),
            })
        logger.info(f"[{corr}] nurse_queue_patients dept={department} normal={normal_qs.count()} priority={priority_qs.count()}")
        return Response({
            'normal_queue': normal_serializer.data,
            'priority_queue': priority_serializer.data,
            'all_patients': all_patients
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def nurse_remove_from_queue(request): return Response({}, status=status.HTTP_200_OK)

@api_view(['POST'])
def nurse_mark_served(request): return Response({}, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_available_doctors(request): return Response([], status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hospital_departments(request):
    actor_role = str(getattr(request.user, 'role', '') or '').lower()
    actor_verification = str(getattr(request.user, 'verification_status', '') or '').lower()

    if actor_role != 'patient' and actor_verification != 'approved':
        return Response({'error': 'Account verification required.'}, status=status.HTTP_403_FORBIDDEN)

    requested_hospital = (request.query_params.get('hospital') or '').strip()
    hospital_name = requested_hospital

    if not hospital_name and actor_role == 'patient':
        profile = PatientProfile.objects.filter(user=request.user).first()
        hospital_name = (getattr(profile, 'hospital', None) or getattr(request.user, 'hospital_name', None) or '').strip()

    qs = GeneralDoctorProfile.objects.filter(
        available_for_consultation=True,
        user__verification_status='approved',
    ).select_related('user')

    if hospital_name:
        qs = qs.filter(user__hospital_name=hospital_name)

    values = []
    seen = set()
    for doc in qs:
        spec = (doc.specialization or '').strip()
        if not spec:
            continue
        if spec in seen:
            continue
        seen.add(spec)
        values.append({'label': spec.replace('-', ' ').title(), 'value': spec})

    if not values:
        values = [{'label': 'General Medicine', 'value': 'general-medicine'}]

    return Response({'departments': values, 'hospital': hospital_name or None}, status=status.HTTP_200_OK)

@api_view(['POST'])
def assign_patient_to_doctor(request): return Response({}, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_doctor_assignments(request): return Response([], status=status.HTTP_200_OK)

@api_view(['POST'])
def accept_assignment(request, assignment_id): return Response({}, status=status.HTTP_200_OK)

@api_view(['GET', 'POST'])
def consultation_notes(request, assignment_id): return Response({}, status=status.HTTP_200_OK)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def queue_schedules(request):
    try:
        corr = _corr_id(request)
        global NEXT_SCHEDULE_ID
        if request.method == 'GET':
            return Response(QUEUE_SCHEDULES_STORE, status=status.HTTP_200_OK)
        data = request.data
        department = data.get('department') or 'OPD'
        start_time = str(data.get('start_time') or '08:00')
        end_time = str(data.get('end_time') or '17:00')
        days = data.get('days_of_week') or [0, 1, 2, 3, 4]
        is_active = bool(data.get('is_active', True))
        schedule = {
            'id': NEXT_SCHEDULE_ID,
            'department': department,
            'start_time': start_time,
            'end_time': end_time,
            'days_of_week': [int(x) for x in days],
            'is_active': is_active,
            'is_open': bool(QUEUE_STATUS_STORE.get(department, {}).get('is_open', False)),
        }
        QUEUE_SCHEDULES_STORE.insert(0, schedule)
        NEXT_SCHEDULE_ID += 1
        logger.info(f"[{corr}] queue_schedule created dept={department} id={schedule['id']}")
        return Response(schedule, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def queue_schedule_detail(request, schedule_id):
    try:
        corr = _corr_id(request)
        idx = next((i for i, s in enumerate(QUEUE_SCHEDULES_STORE) if s['id'] == schedule_id), None)
        if idx is None:
            return Response({'error': 'Schedule not found'}, status=status.HTTP_404_NOT_FOUND)
        if request.method == 'GET':
            return Response(QUEUE_SCHEDULES_STORE[idx], status=status.HTTP_200_OK)
        if request.method == 'PUT':
            data = request.data
            schedule = QUEUE_SCHEDULES_STORE[idx]
            schedule.update({
                'department': data.get('department', schedule['department']),
                'start_time': data.get('start_time', schedule['start_time']),
                'end_time': data.get('end_time', schedule['end_time']),
                'days_of_week': [int(x) for x in data.get('days_of_week', schedule['days_of_week'])],
                'is_active': bool(data.get('is_active', schedule['is_active'])),
            })
            QUEUE_SCHEDULES_STORE[idx] = schedule
            logger.info(f"[{corr}] queue_schedule updated id={schedule_id}")
            return Response(schedule, status=status.HTTP_200_OK)
        QUEUE_SCHEDULES_STORE.pop(idx)
        logger.info(f"[{corr}] queue_schedule deleted id={schedule_id}")
        return Response(status=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def queue_status(request):
    try:
        corr = _corr_id(request)
        if request.method == 'GET':
            department = request.query_params.get('department')
            if department:
                status_obj = QUEUE_STATUS_STORE.get(department, {'is_open': True})
                start_time = None
                end_time = None
                for s in QUEUE_SCHEDULES_STORE:
                    if s['department'] == department:
                        start_time = s.get('start_time')
                        end_time = s.get('end_time')
                        break
                payload = {
                    'department': department,
                    'is_open': bool(status_obj.get('is_open', True)),
                    'status_message': 'Open' if status_obj.get('is_open', True) else 'Closed',
                    'current_schedule_start_time': start_time,
                    'current_schedule_end_time': end_time,
                }
                logger.debug(f"[{corr}] queue_status get dept={department} -> {payload}")
                return Response(payload, status=status.HTTP_200_OK)
            items = []
            for s in QUEUE_SCHEDULES_STORE:
                dep = s['department']
                st = QUEUE_STATUS_STORE.get(dep, {'is_open': True})
                items.append({
                    'department': dep,
                    'is_open': bool(st.get('is_open', True)),
                    'current_schedule_start_time': s.get('start_time'),
                    'current_schedule_end_time': s.get('end_time'),
                })
            return Response(items, status=status.HTTP_200_OK)
        department = request.data.get('department') or 'OPD'
        is_open = bool(request.data.get('is_open', False))
        QUEUE_STATUS_STORE[department] = {'is_open': is_open}
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'queue_{department}',
                {
                    'type': 'queue_status_update',
                    'status': {
                        'department': department,
                        'is_open': is_open
                    }
                }
            )
            async_to_sync(channel_layer.group_send)(
                f'queue_{department}',
                {
                    'type': 'queue_notification',
                    'notification': {
                        'event': 'queue_opened' if is_open else 'queue_closed',
                        'department': department,
                        'message': f"Queue is now {'open' if is_open else 'closed'} for {department}.",
                        'timestamp': timezone.now().isoformat(),
                    }
                }
            )
        except Exception:
            pass
        logger.info(f"[{corr}] queue_status updated dept={department} is_open={is_open}")
        return Response({'message': 'Queue status updated', 'department': department, 'is_open': is_open}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def queue_status_logs(request):
    return Response([], status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def queue_daily_reset(request):
    if request.user.role not in ['nurse', 'doctor', 'admin']:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

    department = request.data.get('department') or 'OPD'
    today = timezone.now().date()

    try:
        with transaction.atomic():
            counter, _ = DailySequenceCounter.objects.select_for_update().get_or_create(
                department=department, date=today, defaults={'current_value': 0}
            )
            counter.current_value = 0
            counter.save()

        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'queue_{department}',
                {
                    'type': 'queue_notification',
                    'notification': {
                        'event': 'queue_reset',
                        'department': department,
                        'message': f'Queue numbering has been reset for {department}.',
                        'timestamp': timezone.now().isoformat(),
                    }
                }
            )
            async_to_sync(channel_layer.group_send)(
                f'queue_{department}',
                {
                    'type': 'queue_notification',
                    'notification': {
                        'event': 'queue_opened',
                        'department': department,
                        'message': f'Queue is now open for {department}.',
                        'timestamp': timezone.now().isoformat(),
                    }
                }
            )
        except Exception:
            pass

        logger.info(f"[{_corr_id(request)}] queue_daily_reset dept={department} date={today}")
        return Response({'message': 'Queue daily reset completed', 'department': department}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Queue daily reset failed: {str(e)}", exc_info=True)
        return Response({'error': 'Queue daily reset failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_queue(request):
    try:
        corr = _corr_id(request)
        user = request.user
        department = request.data.get('department', 'OPD')
        priority_level = request.data.get('priority_level')
        
        # Check if patient profile exists
        try:
            patient_profile = user.patient_profile
        except (AttributeError, PatientProfile.DoesNotExist):
            # Try to find by user id manually if related name issue
            patient_profile = PatientProfile.objects.filter(user=user).first()
            if not patient_profile:
                return Response({'error': 'Patient profile not found'}, status=status.HTTP_404_NOT_FOUND)

        # Check if already in queue (waiting or in_progress)
        existing_queue = QueueManagement.objects.filter(
            patient=patient_profile,
            status__in=['waiting', 'in_progress']
        ).first()

        if existing_queue:
             return Response({
                'message': 'Already in queue',
                'queue_number': existing_queue.queue_number,
                'status': existing_queue.status,
                'department': existing_queue.department,
                'estimated_wait_time': str(existing_queue.estimated_wait_time) if existing_queue.estimated_wait_time else None
            }, status=status.HTTP_200_OK)

        with transaction.atomic():
            today = timezone.now().date()
            # Lock the counter row
            counter, created = DailySequenceCounter.objects.select_for_update().get_or_create(
                department=department,
                date=today,
                defaults={'current_value': 0}
            )
            counter.current_value += 1
            counter.save()
            
            queue_number = counter.current_value
            
            # Calculate estimated wait time (e.g., 15 mins * people in waiting)
            waiting_count = QueueManagement.objects.filter(department=department, status='waiting').count()
            est_wait = timedelta(minutes=15 * waiting_count)

            queue_entry = _safe_insert_queue_entry(
                patient_profile=patient_profile,
                department=department,
                queue_number=queue_number,
                est_wait=est_wait,
                waiting_count=waiting_count
            )
            if priority_level:
                prio_waiting = QueueManagement.objects.filter(department=department, status='waiting', is_priority=True).count()
                queue_entry.is_priority = True
                queue_entry.priority_level = str(priority_level)
                queue_entry.priority_position = prio_waiting + 1
                queue_entry.save()
            
        # Broadcast update via WebSocket
        _broadcast(f'queue_{department}', {
            'type': 'queue_status_update',
            'status': {
                'department': department,
                'is_open': True
            }
        })
        _broadcast(f'queue_{department}', {
            'type': 'queue_position_update',
            'position': {
                'current_queue_number': queue_entry.queue_number,
                'status': queue_entry.status,
                'patient_id': patient_profile.user.id,
                'patient_name': patient_profile.user.full_name
            }
        })

        logger.info(f"[{corr}] patient {patient_profile.user.id} joined queue {department} #{counter.current_value}")
        return Response(QueueSerializer(queue_entry).data, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error joining queue: {str(e)}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def check_queue_availability(request):
    # 24/7 Operation: Always return open
    return Response({
        'is_open': True,
        'status_message': 'Queue is open 24/7',
        'current_schedule_start_time': '00:00:00',
        'current_schedule_end_time': '23:59:59'
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_queue_processing(request):
    if request.user.role not in ['nurse', 'doctor', 'admin']:
         return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
         
    department = request.data.get('department', 'OPD')
    
    try:
        with transaction.atomic():
            # Finish current in_progress patients
            current_patients = QueueManagement.objects.filter(
                department=department,
                status='in_progress'
            )
            for current in current_patients:
                current.status = 'completed'
                current.finished_at = timezone.now()
                current.save()
            
            # Get next patient
            next_priority = QueueManagement.objects.filter(
                department=department,
                status='waiting',
                is_priority=True
            ).order_by('priority_position', 'created_at').first()
            next_normal = QueueManagement.objects.filter(
                department=department,
                status='waiting',
                is_priority=False
            ).order_by('created_at').first() if not next_priority else None
            next_patient = next_priority or next_normal
            
            if next_patient:
                next_patient.status = 'in_progress'
                try:
                    next_patient.started_at = timezone.now()
                except Exception:
                    pass
                next_patient.save()

                try:
                    qs, _ = QueueStatus.objects.get_or_create(department=department)
                    qs.is_open = True
                    qs.current_serving = next_patient.queue_number
                    qs.total_waiting = QueueManagement.objects.filter(department=department, status='waiting').count()
                    qs.status_message = 'Open'
                    qs.last_updated_by = request.user
                    qs.save()
                except Exception as e:
                    logger.warning(f"Failed to update QueueStatus: {e}")

                notif_obj = None
                try:
                    notif_obj = Notification.objects.create(
                        user=next_patient.patient.user,
                        message=f"You are now being served. Queue #{next_patient.queue_number}. Please proceed to triage room ({department}).",
                        channel=Notification.CHANNEL_WEBSOCKET,
                        delivery_status=Notification.DELIVERY_SENT,
                        sent_at=timezone.now(),
                    )
                except Exception as e:
                    logger.warning(f"Failed to create notification: {e}")
                
                # Broadcast "Calling"
                try:
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f'queue_{department}',
                        {
                            'type': 'queue_position_update',
                            'position': {
                                'current_queue_number': next_patient.queue_number,
                                'status': 'in_progress',
                                'patient_id': next_patient.patient.user.id,
                                'patient_name': next_patient.patient.user.full_name
                            }
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to broadcast queue update: {e}")

                logger.info(f"User {request.user.id} started processing queue {department} - Patient {next_patient.id} (Queue #{next_patient.queue_number})")
                
                queue_status_payload = None
                try:
                    qs = QueueStatus.objects.filter(department=department).first()
                    if qs:
                        queue_status_payload = {
                            'department': qs.department,
                            'is_open': qs.is_open,
                            'current_serving': qs.current_serving,
                            'total_waiting': qs.total_waiting,
                            'status_message': qs.status_message,
                        }
                except Exception:
                    queue_status_payload = None

                notification_payload = None
                if notif_obj:
                    try:
                        notification_payload = NotificationSerializer(notif_obj).data
                    except Exception:
                        notification_payload = None

                return Response({
                    'success': True,
                    'message': f'Started processing patient #{next_patient.queue_number}',
                    'current_serving': next_patient.queue_number,
                    'department': department,
                    'queue_status': queue_status_payload,
                    'notification': notification_payload,
                    'patient_profile': {
                        'id': next_patient.patient.id,
                        'full_name': next_patient.patient.user.full_name,
                        'queue_number': next_patient.queue_number,
                        'department': department
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({'message': 'Queue is empty', 'success': False}, status=status.HTTP_200_OK)
                
    except Exception as e:
        logger.error(f"Error starting queue processing: {str(e)}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirm_notification_delivery(request):
    notification_id = request.data.get('notification_id')
    if not notification_id:
        return Response({'error': 'notification_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    notif = Notification.objects.filter(id=notification_id, user=request.user).first()
    if not notif:
        return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

    notif.delivery_status = Notification.DELIVERY_DELIVERED
    notif.delivered_at = timezone.now()
    notif.save(update_fields=['delivery_status', 'delivered_at', 'updated_at'])
    payload = None
    try:
        payload = NotificationSerializer(notif).data
    except Exception:
        payload = None
    return Response({'message': 'Notification confirmed', 'notification': payload}, status=status.HTTP_200_OK)

@api_view(['GET'])
def ui_config(request): return Response({}, status=status.HTTP_200_OK)
