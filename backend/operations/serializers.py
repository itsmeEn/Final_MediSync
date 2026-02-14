from rest_framework import serializers
from django.utils import timezone
from .models import Notification, QueueManagement, PainAssessment
from backend.users.models import User

class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics"""
    total_appointments = serializers.IntegerField()
    total_patients = serializers.IntegerField()
    normal_queue = serializers.IntegerField()
    priority_queue = serializers.IntegerField()
    notifications = serializers.IntegerField()
    pending_assessment = serializers.IntegerField()
    monthly_cancelled = serializers.IntegerField(required=False, default=0)

class QueueSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.user.full_name', read_only=True)
    
    class Meta:
        model = QueueManagement
        fields = ['id', 'queue_number', 'patient_name', 'department', 'status', 'estimated_wait_time', 'created_at']

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id',
            'message',
            'is_read',
            'channel',
            'delivery_status',
            'sent_at',
            'delivered_at',
            'delivery_attempts',
            'created_at',
        ]

class UserSerializer(serializers.ModelSerializer):
    """Serializer for user information in conversations"""
    class Meta:
        model = User
        fields = ['id', 'full_name', 'role', 'profile_picture']

class PainAssessmentSerializer(serializers.ModelSerializer):
    """Serializer for patient pain assessment records"""
    performed_by_name = serializers.CharField(source='performed_by.full_name', read_only=True)
    pain_emoji = serializers.ReadOnlyField()
    pain_label = serializers.ReadOnlyField()

    class Meta:
        model = PainAssessment
        fields = [
            'id', 'patient', 'performed_by', 'performed_by_name',
            'pain_score', 'notes', 'pain_emoji', 'pain_label',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['performed_by', 'created_at', 'updated_at']

class PatientAssessmentArchiveSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    archived_by_name = serializers.CharField(source='archived_by.full_name', read_only=True)

    class Meta:
        from .models import PatientAssessmentArchive
        model = PatientAssessmentArchive
        fields = [
            'id', 'assessment_type', 'medical_condition', 
            'medical_history_summary', 'assessment_data', 'diagnostics',
            'last_assessed_at', 'hospital_name',
            'user', 'user_name',
            'archived_at', 'archived_by', 'archived_by_name'
        ]
        read_only_fields = ['archived_at', 'archived_by']

class ArchiveAccessLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        from .models import ArchiveAccessLog
        model = ArchiveAccessLog
        fields = [
            'id', 'user', 'user_name', 'action', 
            'accessed_at', 'ip_address', 'query_params', 'duration_ms'
        ]
        read_only_fields = ['accessed_at']

