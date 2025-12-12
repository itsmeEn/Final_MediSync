from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
import uuid
import logging

from backend.users.models import PatientProfile, User
from .models import AnalyticsResult

# Import tasks with error handling
try:
    from .tasks import process_data_update_analytics
    TASKS_AVAILABLE = True
except ImportError as e:
    print(f"Analytics tasks not available: {e}")
    TASKS_AVAILABLE = False

logger = logging.getLogger(__name__)

@receiver(post_save, sender=PatientProfile)
def patient_profile_saved(sender, instance, created, **kwargs):
    """
    Trigger analytics when a patient profile is created or updated
    """
    if not TASKS_AVAILABLE:
        return
        
    try:
        action = 'create' if created else 'update'
        process_data_update_analytics.apply(args=('PatientProfile', instance.id, action))
    except Exception as e:
        # Log error but don't break the save operation
        print(f"Error triggering analytics for patient profile {instance.id}: {str(e)}")

@receiver(post_delete, sender=PatientProfile)
def patient_profile_deleted(sender, instance, **kwargs):
    """
    Trigger analytics when a patient profile is deleted
    """
    if not TASKS_AVAILABLE:
        return
        
    try:
        process_data_update_analytics.apply(args=('PatientProfile', instance.id, 'delete'))
    except Exception as e:
        # Log error but don't break the delete operation
        print(f"Error triggering analytics for deleted patient profile {instance.id}: {str(e)}")

# You can add more signal handlers for other models that affect analytics
# For example, if you have appointment models, medicine inventory, etc.

from backend.operations.models import AppointmentManagement, Notification

@receiver(post_save, sender=AppointmentManagement)
def appointment_saved(sender, instance, created, **kwargs):
    """
    Signal to trigger analytics update when appointment data changes
    """
    try:
        if TASKS_AVAILABLE:
            process_data_update_analytics.apply(args=('AppointmentManagement', instance.appointment_id, 'created' if created else 'updated'))
        
        # Create notification for doctor about analytics update
        if instance.doctor:
            Notification.objects.create(
                user=instance.doctor.user,  # Use the User instance from the doctor profile
                message=f"New appointment data has triggered an analytics update for patient insights."
            )
            
    except Exception as e:
        logger.error(f"Error in appointment_saved signal: {str(e)}")


@receiver(post_save, sender=AnalyticsResult)
def analytics_result_completed(sender, instance, created, **kwargs):
    """
    Signal to notify doctors when analytics results are completed
    """
    try:
        # Only notify when analytics are completed (not when created or failed)
        if instance.status == 'completed':
            # Get all doctors to notify them about new analytics findings
            doctors = User.objects.filter(role='doctor', is_active=True)
            
            # Create a user-friendly message based on analysis type
            analysis_type_messages = {
                'patient_health_trends': 'New patient health trends analysis is available',
                'patient_demographics': 'Updated patient demographics analysis is ready',
                'illness_prediction': 'New illness prediction insights are available',
                'medication_analysis': 'Medication analysis results have been updated',
                'patient_volume_prediction': 'Patient volume predictions have been updated',
                'illness_surge_prediction': 'Illness surge predictions are now available',
                'weekly_illness_forecast': 'Weekly illness forecast has been updated',
                'monthly_illness_forecast': 'Monthly illness forecast is ready',
                'full_analysis': 'Complete analytics report is now available',
            }
            
            message = analysis_type_messages.get(
                instance.analysis_type, 
                f'New {instance.get_analysis_type_display()} results are available'
            )
            
            # Create notifications for all doctors
            for doctor in doctors:
                Notification.objects.create(
                    user=doctor,
                    message=message
                )
            
            logger.info(f"Created analytics notifications for {doctors.count()} doctors - {instance.analysis_type}")
            
    except Exception as e:
        logger.error(f"Error in analytics_result_completed signal: {str(e)}")
