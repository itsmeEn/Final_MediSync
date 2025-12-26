from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
import logging

from backend.users.models import GeneralDoctorProfile, PatientProfile, User
from .models import AppointmentManagement, PatientAssignment, Notification, PatientAssessmentArchive

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def client_log(request):
    """Accept client-side logs for correlation and troubleshooting.
    Payload suggestions:
      - message: string
      - level: 'info'|'warning'|'error'
      - route: frontend route or component name
      - context: dict of arbitrary info (ids, counts, timings)
      - network: dict (online, downlink, rtt) from navigator.connection if available
    """
    try:
        user = request.user
        level = str(request.data.get('level', 'info')).lower()
        message = request.data.get('message', '')
        route = request.data.get('route', '')
        context = request.data.get('context', {})
        network = request.data.get('network', {})

        log_msg = f"client_log user_id={getattr(user,'id',None)} role={getattr(user,'role',None)} route={route} level={level} message={message}"
        extras = { 'context': context, 'network': network, 'timestamp': timezone.now().isoformat() }
        if level == 'error':
            logger.error(log_msg + f" extras={extras}")
        elif level == 'warning':
            logger.warning(log_msg + f" extras={extras}")
        else:
            logger.info(log_msg + f" extras={extras}")

        return Response({ 'status': 'logged' }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception(f"client_log:error details={e}")
        return Response({ 'error': f'Failed to record client log: {str(e)}' }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verification_status(request):
    """Verify data transmission, persistence, and mapping for a patient/doctor pair.
    Query params:
      - patient_id: patient user id (preferred) or profile id
      - doctor_id: doctor user id
    Returns structured indicators for: transmission, persistence, mapping.
    """
    try:
        patient_id = request.query_params.get('patient_id')
        doctor_id = request.query_params.get('doctor_id')
        if not patient_id or not doctor_id:
            return Response({'error': 'patient_id and doctor_id are required'}, status=status.HTTP_400_BAD_REQUEST)

        # Resolve profiles
        patient_profile = PatientProfile.objects.filter(user_id=patient_id).first() or PatientProfile.objects.filter(id=patient_id).first()
        doctor_profile = GeneralDoctorProfile.objects.filter(user_id=doctor_id).first()
        if not patient_profile:
            return Response({'error': 'Patient profile not found'}, status=status.HTTP_404_NOT_FOUND)
        if not doctor_profile:
            return Response({'error': 'Doctor profile not found'}, status=status.HTTP_404_NOT_FOUND)

        # Persistence checks
        assignments_qs = PatientAssignment.objects.filter(patient=patient_profile, doctor=doctor_profile)
        appointments_qs = AppointmentManagement.objects.filter(patient=patient_profile, doctor=doctor_profile)
        notifications_qs = Notification.objects.filter(user=doctor_profile.user).order_by('-created_at')
        archives_qs = PatientAssessmentArchive.objects.filter(user_id=patient_profile.user.id)

        result = {
            'input': {
                'patient_user_id': patient_profile.user.id,
                'patient_profile_id': patient_profile.id,
                'doctor_user_id': doctor_profile.user.id,
                'doctor_profile_id': doctor_profile.id,
            },
            'persistence': {
                'assignments_count': assignments_qs.count(),
                'appointments_count': appointments_qs.count(),
                'archives_count': archives_qs.count(),
            },
            'transmission': {
                'recent_notification_present': notifications_qs.exists(),
                'recent_notification_message': notifications_qs.first().message if notifications_qs.exists() else None,
                'recent_notification_at': notifications_qs.first().created_at.isoformat() if notifications_qs.exists() else None,
            },
            'mapping': {
                'assignment_statuses': list(assignments_qs.values_list('status', flat=True)),
                'appointment_statuses': list(appointments_qs.values_list('status', flat=True)),
            }
        }

        logger.info(f"verification_status:result patient_profile_id={patient_profile.id} doctor_profile_id={doctor_profile.id} data={result}")
        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception(f"verification_status:error details={e}")
        return Response({'error': f'Failed to verify status: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

