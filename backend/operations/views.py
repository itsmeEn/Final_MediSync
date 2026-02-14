from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.core.cache import cache
from django.db import DatabaseError, transaction
from django.db.models import Q
from datetime import datetime, timedelta
import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import QueueManagement, Notification, PainAssessment, AppointmentManagement, PatientAssignment, ConsultationNotes, DailySequenceCounter
from backend.users.models import User, GeneralDoctorProfile, NurseProfile, PatientProfile
from .serializers import (
    DashboardStatsSerializer, 
    NotificationSerializer, 
    QueueSerializer, 
    PainAssessmentSerializer
)

logger = logging.getLogger(__name__)

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
            status='waiting'
        ).count()
        
        priority_queue = 0 # PriorityQueue model missing
        
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
def check_in_appointment(request, appointment_id): return Response({}, status=status.HTTP_200_OK)

@api_view(['POST'])
def start_consultation(request, appointment_id): return Response({}, status=status.HTTP_200_OK)

@api_view(['POST'])
def finish_consultation(request, appointment_id): return Response({}, status=status.HTTP_200_OK)

@api_view(['POST'])
def notify_patient_appointment(request, appointment_id): return Response({}, status=status.HTTP_200_OK)

@api_view(['GET'])
def patient_appointments(request): return Response([], status=status.HTTP_200_OK)

@api_view(['GET'])
def patient_dashboard_summary(request): return Response({}, status=status.HTTP_200_OK)

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
def nurse_queue_patients(request): return Response([], status=status.HTTP_200_OK)

@api_view(['POST'])
def nurse_remove_from_queue(request): return Response({}, status=status.HTTP_200_OK)

@api_view(['POST'])
def nurse_mark_served(request): return Response({}, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_available_doctors(request): return Response([], status=status.HTTP_200_OK)

@api_view(['GET'])
def hospital_departments(request): return Response([], status=status.HTTP_200_OK)

@api_view(['POST'])
def assign_patient_to_doctor(request): return Response({}, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_doctor_assignments(request): return Response([], status=status.HTTP_200_OK)

@api_view(['POST'])
def accept_assignment(request, assignment_id): return Response({}, status=status.HTTP_200_OK)

@api_view(['GET', 'POST'])
def consultation_notes(request, assignment_id): return Response({}, status=status.HTTP_200_OK)

@api_view(['GET'])
def queue_schedules(request): return Response([], status=status.HTTP_200_OK)

@api_view(['GET'])
def queue_schedule_detail(request, schedule_id): return Response({}, status=status.HTTP_200_OK)

@api_view(['GET'])
def queue_status(request): return Response({}, status=status.HTTP_200_OK)

@api_view(['GET'])
def queue_status_logs(request): return Response([], status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_queue(request):
    try:
        user = request.user
        department = request.data.get('department', 'OPD')
        
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

            queue_entry = QueueManagement.objects.create(
                patient=patient_profile,
                department=department,
                queue_number=queue_number,
                status='waiting',
                estimated_wait_time=est_wait,
                total_patients=waiting_count + 1 
            )
            
        # Broadcast update via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'queue_{department}',
            {
                'type': 'queue_status_update',
                'status': {
                    'department': department,
                    'is_open': True
                }
            }
        )

        logger.info(f"Patient {patient_profile.user.id} joined queue {department} with number {counter.current_value}")
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
            # We want the one with the lowest queue_number for today, OR just oldest created_at
            # Assuming queue_number is sequential per day, ordering by created_at is safe.
            # But we must only pick from ACTIVE waiting list (status='waiting')
            next_patient = QueueManagement.objects.filter(
                department=department,
                status='waiting'
            ).order_by('created_at').first()
            
            if next_patient:
                next_patient.status = 'in_progress'
                next_patient.save()
                
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
                
                return Response({
                    'success': True,
                    'message': f'Started processing patient #{next_patient.queue_number}',
                    'current_serving': next_patient.queue_number,
                    'department': department,
                    'patient_profile': {
                        'id': next_patient.patient.id,
                        'full_name': next_patient.patient.user.full_name,
                        'queue_number': next_patient.queue_number
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({'message': 'Queue is empty', 'success': False}, status=status.HTTP_200_OK)
                
    except Exception as e:
        logger.error(f"Error starting queue processing: {str(e)}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def confirm_notification_delivery(request): return Response({}, status=status.HTTP_200_OK)

@api_view(['GET'])
def ui_config(request): return Response({}, status=status.HTTP_200_OK)
