from rest_framework import serializers
from django.utils import timezone
from .models import AppointmentManagement, QueueManagement, PriorityQueue, Notification, Messaging, Conversation, Message, MessageReaction, MessageNotification, MedicineInventory, PatientAssignment, ConsultationNotes, QueueSchedule, QueueStatus, QueueStatusLog, PatientAssessmentArchive, ArchiveAccessLog
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

class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.user.full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.user.full_name', read_only=True)
    doctor_id = serializers.IntegerField(source='doctor.user.id', read_only=True)
    department = serializers.CharField(source='doctor.specialization', read_only=True)
    type = serializers.CharField(source='appointment_type', read_only=True)
    reason = serializers.SerializerMethodField()
    
    class Meta:
        model = AppointmentManagement
        fields = ['appointment_id', 'patient_name', 'doctor_name', 'doctor_id', 'department', 
                  'appointment_date', 'appointment_time', 'status', 'appointment_type', 'type', 'reason',
                  'checked_in_at', 'consultation_started_at', 'consultation_finished_at',
                  'cancellation_reason', 'reschedule_reason']
    
    def get_reason(self, obj):
        """Return a default reason for display purposes"""
        return "Medical consultation"

class QueueSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.user.full_name', read_only=True)
    
    class Meta:
        model = QueueManagement
        fields = ['id', 'queue_number', 'patient_name', 'department', 'status', 'position_in_queue', 'enqueue_time']

class PriorityQueueSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.user.full_name', read_only=True)
    
    class Meta:
        model = PriorityQueue
        fields = ['id', 'queue_number', 'patient_name', 'priority_level', 'department', 'priority_position', 'status', 'enqueue_time', 'started_at', 'finished_at']

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

# NurseChartSerializer commented out until NurseChart model is fully implemented
# class NurseChartSerializer(serializers.ModelSerializer):
#     patient_name = serializers.CharField(source='patient.user.full_name', read_only=True)
#     nurse_name = serializers.CharField(source='nurse.user.full_name', read_only=True)
#     
#     class Meta:
#         model = NurseChart
#         fields = ['id', 'patient_name', 'nurse_name', 'chief_complaint', 'status', 'priority', 'created_at']

# Messaging Serializers
class UserSerializer(serializers.ModelSerializer):
    """Serializer for user information in conversations"""
    class Meta:
        model = User
        fields = ['id', 'full_name', 'role', 'profile_picture']

class MessageReactionSerializer(serializers.ModelSerializer):
    """Serializer for message reactions"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = MessageReaction
        fields = ['id', 'user', 'reaction_type', 'created_at']

class MessageSerializer(serializers.ModelSerializer):
    """Serializer for messages"""
    sender = UserSerializer(read_only=True)
    reactions = MessageReactionSerializer(many=True, read_only=True)
    has_attachment = serializers.ReadOnlyField()
    decrypted_content = serializers.SerializerMethodField()
    is_delivered = serializers.ReadOnlyField()
    read_at = serializers.ReadOnlyField()
    delivered_at = serializers.ReadOnlyField()
    
    class Meta:
        model = Message
        fields = ['id', 'sender', 'content', 'decrypted_content', 'file_attachment', 'file_name', 'file_size', 
                 'has_attachment', 'is_read', 'is_delivered', 'read_at', 'delivered_at', 
                 'created_at', 'updated_at', 'reactions']
    
    def get_decrypted_content(self, obj):
        """Return decrypted content for the message"""
        return obj.decrypt_content()

class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for conversations"""
    participants = UserSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    other_participant = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = ['id', 'participants', 'other_participant', 'last_message', 
                 'unread_count', 'created_at', 'updated_at', 'is_active']
    
    def get_last_message(self, obj):
        """Get the last message in the conversation"""
        last_msg = obj.messages.last()
        if last_msg:
            return MessageSerializer(last_msg).data
        return None
    
    def get_unread_count(self, obj):
        """Get unread message count for the current user"""
        request = self.context.get('request')
        if request and request.user:
            return obj.messages.filter(is_read=False).exclude(sender=request.user).count()
        return 0
    
    def get_other_participant(self, obj):
        """Get the other participant in a 1-on-1 conversation"""
        request = self.context.get('request')
        if request and request.user:
            other = obj.get_other_participant(request.user)
            if other:
                return UserSerializer(other).data
        return None

class CreateMessageSerializer(serializers.ModelSerializer):
    """Serializer for creating new messages"""
    class Meta:
        model = Message
        fields = ['content', 'file_attachment']
    
    def validate_file_attachment(self, value):
        """Validate file attachment"""
        if value:
            # Check file size (max 10MB)
            if value.size > 10 * 1024 * 1024:
                raise serializers.ValidationError("File size cannot exceed 10MB")
            
            # Check file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'application/pdf', 
                           'text/plain', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
            if value.content_type not in allowed_types:
                raise serializers.ValidationError("File type not allowed")
        
        return value

class CreateReactionSerializer(serializers.ModelSerializer):
    """Serializer for creating message reactions"""
    class Meta:
        model = MessageReaction
        fields = ['reaction_type']

class MessageNotificationSerializer(serializers.ModelSerializer):
    """Serializer for message notifications"""
    message = MessageSerializer(read_only=True)
    recipient = UserSerializer(read_only=True)
    
    class Meta:
        model = MessageNotification
        fields = ['id', 'message', 'recipient', 'notification_type', 'is_sent', 'sent_at', 'created_at']

class MedicineInventorySerializer(serializers.ModelSerializer):
    """Serializer for medicine inventory"""
    stock_level = serializers.SerializerMethodField()

    class Meta:
        model = MedicineInventory
        fields = ['id', 'medicine_name', 'stock_number', 'current_stock', 'unit_price',
                  'minimum_stock_level', 'expiry_date', 'batch_number', 'last_restocked',
                  'usage_pattern', 'stock_level']

    def get_stock_level(self, obj):
        """Calculate stock level based on current stock and minimum level"""
        if obj.current_stock == 0:
            return 'out_of_stock'
        elif obj.current_stock <= obj.minimum_stock_level:
            return 'low_stock'
        else:
            return 'in_stock'


class PatientAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for patient assignments"""
    patient_name = serializers.CharField(source='patient.user.full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.user.full_name', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.full_name', read_only=True)
    patient_id = serializers.IntegerField(source='patient.id', read_only=True)
    doctor_id = serializers.IntegerField(source='doctor.id', read_only=True)

    class Meta:
        model = PatientAssignment
        fields = ['id', 'patient', 'patient_id', 'patient_name', 'doctor', 'doctor_id', 'doctor_name',
                  'assigned_by', 'assigned_by_name', 'specialization_required', 'assignment_reason',
                  'status', 'assigned_at', 'accepted_at', 'completed_at', 'priority']

    def create(self, validated_data):
        """Create a new patient assignment"""
        return PatientAssignment.objects.create(**validated_data)


class ConsultationNotesSerializer(serializers.ModelSerializer):
    """Serializer for consultation notes"""
    patient_name = serializers.CharField(source='patient.user.full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.user.full_name', read_only=True)
    assignment_id = serializers.IntegerField(source='assignment.id', read_only=True)

    class Meta:
        model = ConsultationNotes
        fields = ['id', 'assignment', 'assignment_id', 'doctor', 'patient', 'patient_name', 'doctor_name',
                  'chief_complaint', 'history_of_present_illness', 'physical_examination', 'diagnosis',
                  'treatment_plan', 'medications_prescribed', 'follow_up_instructions', 'additional_notes',
                  'status', 'created_at', 'updated_at', 'completed_at']

    def create(self, validated_data):
        """Create new consultation notes"""
        return ConsultationNotes.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """Update consultation notes"""
        if validated_data.get('status') == 'completed' and not instance.completed_at:
            validated_data['completed_at'] = timezone.now()
        return super().update(instance, validated_data)


class QueueScheduleSerializer(serializers.ModelSerializer):
    """Serializer for queue schedules"""
    nurse_name = serializers.CharField(source='nurse.user.full_name', read_only=True)
    is_currently_open = serializers.SerializerMethodField()
    
    class Meta:
        model = QueueSchedule
        fields = ['id', 'department', 'nurse', 'nurse_name', 'start_time', 'end_time', 
                 'days_of_week', 'is_active', 'manual_override', 'override_status',
                 'is_currently_open', 'created_at', 'updated_at']

    def get_is_currently_open(self, obj):
        """Determine if the queue is currently open based on schedule and override"""
        now = timezone.localtime()
        current_day = now.weekday()  # 0=Monday, 6=Sunday
        # Normalize days_of_week to numeric list if strings are present
        days = obj.days_of_week or []
        if days and isinstance(days[0], str):
            name_to_num = {
                'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
                'Friday': 4, 'Saturday': 5, 'Sunday': 6
            }
            def to_num(d: str) -> int:
                if d.isdigit():
                    n = int(d)
                    return n if 0 <= n <= 6 else -1
                return name_to_num.get(d, -1)
            days = [to_num(d) for d in days]
        in_schedule = bool(obj.is_active) and (current_day in days) and (obj.start_time <= now.time() <= obj.end_time)
        if obj.manual_override and obj.override_status is not None:
            # Treat 'enabled' as open, otherwise use in_schedule
            return obj.override_status == 'enabled'
        return in_schedule

class QueueStatusSerializer(serializers.ModelSerializer):
    """Serializer for real-time queue status"""
    last_updated_by_name = serializers.CharField(source='last_updated_by.full_name', read_only=True)
    current_schedule_start_time = serializers.SerializerMethodField()
    current_schedule_end_time = serializers.SerializerMethodField()
    current_schedule_days_of_week = serializers.SerializerMethodField()
    
    class Meta:
        model = QueueStatus
        fields = ['id', 'department', 'is_open', 'current_serving', 'total_waiting',
                 'estimated_wait_time', 'status_message', 'last_updated_by', 
                 'last_updated_by_name', 'last_updated_at', 'created_at',
                 'current_schedule_start_time', 'current_schedule_end_time', 'current_schedule_days_of_week']

    def get_current_schedule_start_time(self, obj):
        schedule = QueueSchedule.objects.filter(department=obj.department, is_active=True).first()
        return schedule.start_time.isoformat() if schedule and schedule.start_time else None

    def get_current_schedule_end_time(self, obj):
        schedule = QueueSchedule.objects.filter(department=obj.department, is_active=True).first()
        return schedule.end_time.isoformat() if schedule and schedule.end_time else None

    def get_current_schedule_days_of_week(self, obj):
        schedule = QueueSchedule.objects.filter(department=obj.department, is_active=True).first()
        return schedule.days_of_week if schedule else []

class QueueStatusLogSerializer(serializers.ModelSerializer):
    """Serializer for queue status change logs"""
    changed_by_name = serializers.CharField(source='changed_by.full_name', read_only=True)
    status_change_text = serializers.SerializerMethodField()
    
    class Meta:
        model = QueueStatusLog
        fields = ['id', 'department', 'previous_status', 'new_status', 'change_reason',
                 'changed_by', 'changed_by_name', 'changed_at', 'additional_notes',
                 'status_change_text']
    
    def get_status_change_text(self, obj):
        status_change = "Opened" if obj.new_status else "Closed"
        return f"Queue {status_change}: {obj.department} - {obj.change_reason}"

class CreateQueueScheduleSerializer(serializers.ModelSerializer):
    """Serializer for creating queue schedules"""
    class Meta:
        model = QueueSchedule
        fields = ['department', 'start_time', 'end_time', 'days_of_week', 'is_active']
    
    def validate_days_of_week(self, value):
        # Accept numeric days (0=Mon..6=Sun), numeric strings, or day names; normalize to numeric
        valid_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        name_to_num = {
            'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
            'Friday': 4, 'Saturday': 5, 'Sunday': 6
        }
        normalized: list[int] = []
        for day in value:
            if isinstance(day, int):
                if day < 0 or day > 6:
                    raise serializers.ValidationError(f"Invalid day: {day}")
                normalized.append(day)
            elif isinstance(day, str):
                d = day.strip()
                if d.isdigit():
                    num = int(d)
                    if num < 0 or num > 6:
                        raise serializers.ValidationError(f"Invalid day: {day}")
                    normalized.append(num)
                else:
                    if d not in valid_names:
                        raise serializers.ValidationError(f"Invalid day: {day}")
                    normalized.append(name_to_num[d])
            else:
                raise serializers.ValidationError(f"Invalid day type: {type(day).__name__}")
        return normalized

    def validate(self, data):
        if data['start_time'] >= data['end_time']:
            raise serializers.ValidationError("Start time must be before end time")
        return data

class UpdateQueueStatusSerializer(serializers.ModelSerializer):
    """Serializer for updating real-time queue status"""
    class Meta:
        model = QueueStatus
        fields = ['department', 'is_open']
    
    def validate_department(self, value):
        if not value:
            raise serializers.ValidationError("Department is required")
        return value

# Archive Serializers
class PatientAssessmentArchiveSerializer(serializers.ModelSerializer):
    patient_id = serializers.IntegerField(source='user.id', read_only=True)
    patient_name = serializers.CharField(source='user.full_name', read_only=True)
    decrypted_assessment_data = serializers.SerializerMethodField()

    class Meta:
        model = PatientAssessmentArchive
        fields = ['id', 'patient_id', 'patient_name', 'assessment_type', 'medical_condition',
                  'medical_history_summary', 'diagnostics', 'last_assessed_at', 'hospital_name',
                  'decrypted_assessment_data', 'created_at', 'updated_at']

    def get_decrypted_assessment_data(self, obj):
        return obj.decrypt_payload()

class ArchiveAccessLogSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    record_id = serializers.IntegerField(source='record.id', read_only=True)

    class Meta:
        model = ArchiveAccessLog
        fields = ['id', 'record_id', 'user', 'action', 'accessed_at', 'ip_address', 'query_params', 'duration_ms']


