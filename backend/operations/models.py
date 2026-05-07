from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from backend.users.models import GeneralDoctorProfile, NurseProfile, PatientProfile
from backend.admin_site.models import Hospital
from django.utils import timezone
from datetime import timedelta
from cryptography.fernet import Fernet
from django.conf import settings
import base64
import json
from django.db import transaction
import hashlib


# Custom User Model
# Ensure that the custom user model is used for all user-related operations.
# This is necessary for the queue management system to work with the custom user model.
# This allows us to reference the user model directly without hardcoding the model name.
# This is particularly useful for foreign key relationships and user management.

Users = get_user_model()

# [2025-10-31] Context note: today’s work added department handling to appointments
# and restored Department/HospitalDepartmentDoctor/DoctorTimeSlot models to align
# the ORM with existing migrations. Comments below mark areas changed today.
#
# notification management to notify patients about their queue status, appointment reminders, etc.
#notify doctors about the his appointments, patient status, etc.
#motify nurses about the medicine inventory, patient status, etc.
# a realtime notification system that can notify the patients
class Notification(models.Model):
    """
    Notifies the users about their queue status, appointment reminders, etc.
    Includes delivery tracking with timestamps and channels.
    """
    CHANNEL_WEBSOCKET = 'websocket'
    CHANNEL_EMAIL = 'email'
    CHANNEL_SMS = 'sms'
    CHANNEL_PUSH = 'push'

    CHANNEL_CHOICES = [
        (CHANNEL_WEBSOCKET, 'WebSocket'),
        (CHANNEL_EMAIL, 'Email'),
        (CHANNEL_SMS, 'SMS'),
        (CHANNEL_PUSH, 'Push Notification'),
    ]

    DELIVERY_PENDING = 'pending'
    DELIVERY_SENT = 'sent'
    DELIVERY_DELIVERED = 'delivered'
    DELIVERY_FAILED = 'failed'

    DELIVERY_STATUS_CHOICES = [
        (DELIVERY_PENDING, 'Pending'),
        (DELIVERY_SENT, 'Sent'),
        (DELIVERY_DELIVERED, 'Delivered'),
        (DELIVERY_FAILED, 'Failed'),
    ]

    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="notifications")
    message = models.TextField(help_text="Notification message.")
    is_read = models.BooleanField(default=False, help_text="Indicates if the notification has been read.")
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default=CHANNEL_WEBSOCKET)
    delivery_status = models.CharField(max_length=20, choices=DELIVERY_STATUS_CHOICES, default=DELIVERY_PENDING)
    sent_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when the notification was sent.")
    delivered_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when the notification was delivered.")
    delivery_attempts = models.PositiveIntegerField(default=0, help_text="Number of delivery attempts.")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the notification was created.")
    updated_at = models.DateTimeField(auto_now=True, help_text="Timestamp when the notification was last updated.")

    class Meta:
        ordering = ["-created_at"]
        db_table = "notifications"
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"Notification for {self.user.full_name}: {self.message[:50]}..."  # Display first 50 characters of the message


class WebPushSubscription(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="web_push_subscriptions")
    endpoint = models.TextField()
    subscription = models.JSONField()
    user_agent = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "endpoint")
        ordering = ["-updated_at"]
        db_table = "web_push_subscriptions"
        verbose_name = "Web Push Subscription"
        verbose_name_plural = "Web Push Subscriptions"

#queueing system for operations normal queues
class QueueManagement(models.Model):
    """Queue management model for handling patient queues in operations.
    - Each queue is associated with a patient.
    - Tracks the queue number, status, and timestamps for creation and updates.
    - FIFO
    """
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name="queue_management")
    queue_number = models.PositiveIntegerField(help_text="Queue number (resets daily)")
    notification = models.ForeignKey(Notification, on_delete=models.SET_NULL, null=True, blank=True, related_name="queue_management")
    total_patients = models.PositiveIntegerField(default=0, help_text="Total number of patients in the queue.")
    estimated_wait_time = models.DurationField(null=True, blank=True, help_text="Estimated wait time for the patient.")
    expected_patients = models.PositiveIntegerField(default=0, help_text="Expected number of patients in the queue.")   
    actual_wait_time = models.DurationField(null=True, blank=True, help_text="Actual wait time for the patient.")
    finished_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when the queue finished.")
    # Department identifier (slug or label). Accept any hospital-defined department.
    department = models.CharField(max_length=100, help_text="Department for which the queue is managed.")
    status = models.CharField(max_length=50, choices=[
        ("waiting", "Waiting"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ], default="waiting", help_text="Status of the patient in the queue.")
    is_priority = models.BooleanField(default=False)
    priority_level = models.CharField(max_length=50, blank=True, default="")
    priority_position = models.PositiveIntegerField(default=0)
    # Fields required by existing migrations and integrations
    daily_sequence_number = models.PositiveIntegerField(default=0, help_text="Sequential number for this patient for the day.")
    position_in_queue = models.PositiveIntegerField(default=0, help_text="Position in the queue.")
    enqueue_time = models.DateTimeField(default=timezone.now, help_text="Timestamp when the patient was added to the queue.")
    dequeue_time = models.DateTimeField(null=True, blank=True, help_text="Timestamp when the patient was removed from the queue.")
    started_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when the queue started.")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the queue was created.")
    updated_at = models.DateTimeField(auto_now=True, help_text="Timestamp when the queue was last updated.")

    class Meta:
        ordering = ["queue_number"]
        db_table = "queue_management"
        verbose_name = "Queue Management"
        verbose_name_plural = "Queue Managements"

    def __str__(self):
        return f"Queue {self.queue_number} for {self.patient.user.full_name}"


class QueueSchedule(models.Model):
    department = models.CharField(max_length=100, help_text="Department for which the schedule is set")
    start_time = models.TimeField(help_text="Time when queue should open")
    end_time = models.TimeField(help_text="Time when queue should close")
    days_of_week = models.JSONField(default=list, help_text="List of days when queue is active (0=Monday, 6=Sunday)")
    is_active = models.BooleanField(default=True, help_text="Whether this schedule is currently active")
    manual_override = models.BooleanField(default=False, help_text="Manual override by nurse (overrides time-based activation)")
    override_status = models.CharField(max_length=20, choices=[
        ("enabled", "Manually Enabled"),
        ("disabled", "Manually Disabled"),
        ("auto", "Automatic"),
    ], default="auto", help_text="Current override status")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Queue Schedule"
        verbose_name_plural = "Queue Schedules"
        ordering = ["-updated_at"]


class QueueStatus(models.Model):
    department = models.CharField(max_length=100, unique=True, help_text="Department for which status is tracked")
    is_open = models.BooleanField(default=False, help_text="Whether the queue is currently open for new patients")
    current_serving = models.PositiveIntegerField(null=True, blank=True, help_text="Queue number currently being served")
    total_waiting = models.PositiveIntegerField(default=0, help_text="Total number of patients currently waiting")
    estimated_wait_time = models.DurationField(null=True, blank=True, help_text="Estimated wait time for new patients")
    status_message = models.CharField(max_length=200, default="Queue Closed", help_text="Current status message displayed to patients")
    last_updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated_by = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True, related_name="queue_status_updates")

    class Meta:
        verbose_name = "Queue Status"
        verbose_name_plural = "Queue Statuses"


class QueueStatusLog(models.Model):
    change_reason = models.CharField(max_length=50, choices=[
        ("schedule", "Scheduled Time"),
        ("manual", "Manual Override"),
        ("system", "System Update"),
    ], help_text="Reason for status change")
    department = models.CharField(max_length=100, help_text="Department for which status changed")
    previous_status = models.BooleanField(help_text="Previous queue open/closed status")
    new_status = models.BooleanField(help_text="New queue open/closed status")
    changed_at = models.DateTimeField(auto_now_add=True)
    additional_notes = models.TextField(blank=True, help_text="Additional notes about the status change")

    class Meta:
        verbose_name = "Queue Status Log"
        verbose_name_plural = "Queue Status Logs"
        ordering = ["-changed_at"]


class Conversation(models.Model):
    participants = models.ManyToManyField(Users, related_name="conversations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"
        db_table = "conversations"
        ordering = ["-updated_at"]


class Message(models.Model):
    content = models.TextField(help_text="Encrypted message content.")
    encrypted_content = models.TextField(blank=True, help_text="Base64 encoded encrypted content")
    file_attachment = models.FileField(upload_to="message_attachments/", null=True, blank=True, help_text="Optional file attachment")
    file_name = models.CharField(max_length=255, blank=True, help_text="Original file name")
    file_size = models.PositiveIntegerField(null=True, blank=True, help_text="File size in bytes")
    is_read = models.BooleanField(default=False, help_text="Whether the message has been read")
    is_delivered = models.BooleanField(default=False, help_text="Whether the message has been delivered")
    delivered_at = models.DateTimeField(null=True, blank=True, help_text="When the message was delivered")
    read_at = models.DateTimeField(null=True, blank=True, help_text="When the message was read")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the message was sent.")
    updated_at = models.DateTimeField(auto_now=True)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="sent_messages")

    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        db_table = "messages"
        ordering = ["created_at"]


class MessageNotification(models.Model):
    notification_type = models.CharField(max_length=20, choices=[
        ("new_message", "New Message"),
        ("message_delivered", "Message Delivered"),
        ("message_read", "Message Read"),
    ], default="new_message")
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="notifications")
    recipient = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="message_notifications")

    class Meta:
        verbose_name = "Message Notification"
        verbose_name_plural = "Message Notifications"
        db_table = "message_notifications"
        ordering = ["-created_at"]


class MessageReaction(models.Model):
    reaction_type = models.CharField(max_length=20, choices=[
        ("like", "👍"),
        ("love", "❤️"),
        ("laugh", "😂"),
        ("wow", "😮"),
        ("sad", "😢"),
        ("angry", "😠"),
    ], default="like")
    created_at = models.DateTimeField(auto_now_add=True)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="message_reactions")

    class Meta:
        db_table = "message_reactions"

class AppointmentManagement(models.Model):
    appointment_id = models.AutoField(primary_key=True, help_text="Unique identifier for the appointment.")
    appointment_date = models.DateTimeField(help_text="Date and time of the appointment.")
    appointment_type = models.CharField(max_length=50, default="consultation", choices=[
        ("consultation", "Consultation"),
        ("follow_up", "Follow Up"),
        ("emergency", "Emergency"),
    ])
    appointment_time = models.TimeField(help_text="Time of the appointment.")
    queue_number = models.PositiveIntegerField(unique=True, help_text="Queue number for the appointment.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=50, default="scheduled", choices=[
        ("scheduled", "Scheduled"),
        ("rescheduled", "Rescheduled"),
        ("checked_in", "Checked In"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("no_show", "No Show"),
    ])
    doctor = models.ForeignKey(GeneralDoctorProfile, on_delete=models.CASCADE, related_name="appointments")
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name="appointments")
    
    checked_in_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when the patient checked in for the appointment.")
    consultation_started_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when the consultation started.")
    consultation_finished_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when the consultation finished.")

    class Meta:
        verbose_name = "Appointment Management"
        verbose_name_plural = "Appointment Management"
        db_table = "appointment_management"
        ordering = ["appointment_date"]

    def __str__(self):
        return f"Appointment {self.appointment_id} for {self.patient.user.full_name}"

class PatientAssignment(models.Model):
    specialization_required = models.CharField(max_length=100, help_text="Required specialization for this assignment")
    assignment_reason = models.TextField(blank=True, help_text="Reason for assignment")
    status = models.CharField(max_length=20, default="pending", choices=[
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("rejected", "Rejected"),
    ], help_text="Assignment status")
    
    assigned_at = models.DateTimeField(auto_now_add=True, help_text="When the patient was assigned")
    accepted_at = models.DateTimeField(null=True, blank=True, help_text="When the doctor accepted the assignment")
    completed_at = models.DateTimeField(null=True, blank=True, help_text="When the consultation was completed")
    
    priority = models.CharField(max_length=10, default="medium", choices=[
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ], help_text="Assignment priority")
    
    assigned_by = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="patient_assignments", help_text="Nurse who assigned the patient")
    doctor = models.ForeignKey(GeneralDoctorProfile, on_delete=models.CASCADE, related_name="assigned_patients")
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name="assignments")

    class Meta:
        verbose_name = "Patient Assignment"
        verbose_name_plural = "Patient Assignments"
        db_table = "patient_assignments"
        ordering = ["-assigned_at"]
        unique_together = [("patient", "doctor", "assigned_at")]

    def __str__(self):
        return f"Assignment for {self.patient.user.full_name} to {self.doctor.user.full_name}"

class ConsultationNotes(models.Model):
    chief_complaint = models.TextField(help_text="Patient's main complaint")
    history_of_present_illness = models.TextField(help_text="Detailed history of the current illness")
    physical_examination = models.TextField(help_text="Physical examination findings")
    diagnosis = models.TextField(help_text="Doctor's diagnosis")
    treatment_plan = models.TextField(help_text="Recommended treatment plan")
    medications_prescribed = models.TextField(blank=True, help_text="Medications prescribed")
    follow_up_instructions = models.TextField(blank=True, help_text="Follow-up instructions for the patient")
    additional_notes = models.TextField(blank=True, help_text="Any additional notes")
    
    status = models.CharField(max_length=20, default="draft", choices=[
        ("draft", "Draft"),
        ("completed", "Completed"),
        ("reviewed", "Reviewed"),
    ], help_text="Status of the consultation notes")
    
    created_at = models.DateTimeField(auto_now_add=True, help_text="When the notes were created")
    updated_at = models.DateTimeField(auto_now=True, help_text="When the notes were last updated")
    completed_at = models.DateTimeField(null=True, blank=True, help_text="When the consultation was completed")
    
    assignment = models.ForeignKey(PatientAssignment, on_delete=models.CASCADE, related_name="consultation_notes")
    doctor = models.ForeignKey(GeneralDoctorProfile, on_delete=models.CASCADE, related_name="consultation_notes")
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name="consultation_notes")

    class Meta:
        verbose_name = "Consultation Notes"
        verbose_name_plural = "Consultation Notes"
        db_table = "consultation_notes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Consultation Notes for {self.patient.user.full_name} by {self.doctor.user.full_name}"


class MedicalRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("fulfilled", "Fulfilled"),
        ("cancelled", "Cancelled"),
    ]

    requested_by = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True, related_name="medical_requests_requested")
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name="medical_requests")
    doctor = models.ForeignKey(GeneralDoctorProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="medical_requests")
    assignment = models.ForeignKey("PatientAssignment", on_delete=models.SET_NULL, null=True, blank=True, related_name="medical_requests")
    consultation_notes = models.ForeignKey("ConsultationNotes", on_delete=models.SET_NULL, null=True, blank=True, related_name="medical_requests")

    request_medical_certificate = models.BooleanField(default=False)
    request_prescription = models.BooleanField(default=False)
    patient_message = models.TextField(blank=True, default="")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    doctor_message = models.TextField(blank=True, default="")
    fulfilled_by = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True, related_name="medical_requests_fulfilled")
    fulfilled_at = models.DateTimeField(null=True, blank=True)

    certificate_details = models.JSONField(default=dict, blank=True)
    prescription_details = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "medical_requests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["patient", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"MedicalRequest #{self.id} for {self.patient.user.full_name}"


class GeneratedMedicalDocument(models.Model):
    DOC_TYPE_CHOICES = [
        ("medical_certificate", "Medical Certificate"),
        ("prescription", "Prescription"),
    ]

    EMAIL_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("failed", "Failed"),
    ]

    medical_request = models.ForeignKey(MedicalRequest, on_delete=models.CASCADE, related_name="documents")
    patient = models.ForeignKey(PatientProfile, on_delete=models.PROTECT, related_name="generated_medical_documents")
    doctor = models.ForeignKey(GeneralDoctorProfile, on_delete=models.PROTECT, related_name="generated_medical_documents")
    assignment = models.ForeignKey("PatientAssignment", on_delete=models.SET_NULL, null=True, blank=True, related_name="generated_medical_documents")
    consultation_notes = models.ForeignKey("ConsultationNotes", on_delete=models.SET_NULL, null=True, blank=True, related_name="generated_medical_documents")

    doc_type = models.CharField(max_length=32, choices=DOC_TYPE_CHOICES)
    document_number = models.CharField(max_length=64, db_index=True)
    file = models.FileField(upload_to="medical_documents/%Y/%m/")

    sha256_hex = models.CharField(max_length=64, blank=True, default="")
    signature_hmac_hex = models.CharField(max_length=128, blank=True, default="")

    encrypted_password = models.TextField(blank=True, default="")
    is_encrypted = models.BooleanField(default=True)

    email_delivery_status = models.CharField(max_length=16, choices=EMAIL_STATUS_CHOICES, default="pending")
    email_sent_at = models.DateTimeField(null=True, blank=True)

    metadata = models.JSONField(default=dict, blank=True)
    authenticated_at = models.DateTimeField(default=timezone.now)

    created_by = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True, related_name="generated_medical_documents")
    ip_address = models.CharField(max_length=64, blank=True, default="")
    user_agent = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "generated_medical_documents"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["doc_type", "created_at"]),
            models.Index(fields=["patient", "created_at"]),
            models.Index(fields=["doctor", "created_at"]),
            models.Index(fields=["document_number"]),
        ]

    def __str__(self):
        return f"{self.doc_type} {self.document_number}"


class MedicalRecordTransfer(models.Model):
    EMAIL_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("failed", "Failed"),
    ]

    sender = models.ForeignKey(Users, on_delete=models.PROTECT, related_name="sent_medical_record_transfers")
    receiver = models.ForeignKey(Users, on_delete=models.PROTECT, related_name="received_medical_record_transfers")
    patient = models.ForeignKey(PatientProfile, on_delete=models.PROTECT, related_name="medical_record_transfers")
    assignment = models.ForeignKey("PatientAssignment", on_delete=models.SET_NULL, null=True, blank=True, related_name="medical_record_transfers")

    document_number = models.CharField(max_length=64, db_index=True)
    file = models.FileField(upload_to="medical_record_transfers/%Y/%m/")

    sha256_hex = models.CharField(max_length=64, blank=True, default="")
    signature_hmac_hex = models.CharField(max_length=128, blank=True, default="")

    encrypted_password = models.TextField(blank=True, default="")
    is_encrypted = models.BooleanField(default=True)

    email_delivery_status = models.CharField(max_length=16, choices=EMAIL_STATUS_CHOICES, default="pending")
    email_sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")

    metadata = models.JSONField(default=dict, blank=True)
    authenticated_at = models.DateTimeField(default=timezone.now)

    created_by = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_medical_record_transfers")
    ip_address = models.CharField(max_length=64, blank=True, default="")
    user_agent = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "medical_record_transfers"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["patient", "created_at"]),
            models.Index(fields=["sender", "created_at"]),
            models.Index(fields=["receiver", "created_at"]),
            models.Index(fields=["document_number"]),
            models.Index(fields=["email_delivery_status", "created_at"]),
        ]

    def __str__(self):
        return f"medical_record_transfer {self.document_number}"


class MedicalRecordTransferLog(models.Model):
    transfer = models.ForeignKey(MedicalRecordTransfer, on_delete=models.CASCADE, related_name="logs")
    actor = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True, related_name="medical_record_transfer_logs")
    event = models.CharField(max_length=64)
    detail = models.TextField(blank=True, default="")
    ip_address = models.CharField(blank=True, max_length=64)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "medical_record_transfer_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["event", "created_at"]),
            models.Index(fields=["transfer", "created_at"]),
        ]


class FormAccessLog(models.Model):
    role = models.CharField(blank=True, max_length=32)
    form_key = models.CharField(max_length=64)
    endpoint = models.CharField(blank=True, max_length=255)
    method = models.CharField(blank=True, max_length=16)
    allowed = models.BooleanField(default=False)
    reason = models.TextField(blank=True)
    ip_address = models.CharField(blank=True, max_length=64)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    user = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True, related_name="form_access_logs")
    patient = models.ForeignKey(PatientProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="form_access_logs")
    assignment = models.ForeignKey(PatientAssignment, on_delete=models.SET_NULL, null=True, blank=True, related_name="form_access_logs")

    class Meta:
        db_table = "form_access_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["form_key", "created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["patient", "created_at"]),
        ]

class PatientAssignmentAuditLog(models.Model):
    actor = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True, related_name="patient_assignment_audit_logs")
    assignment = models.ForeignKey(PatientAssignment, on_delete=models.CASCADE, related_name="audit_logs")
    patient = models.ForeignKey(PatientProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="patient_assignment_audit_logs")
    doctor = models.ForeignKey(GeneralDoctorProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="patient_assignment_audit_logs")

    event = models.CharField(max_length=64)
    detail = models.TextField(blank=True)
    ip_address = models.CharField(blank=True, max_length=64)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "patient_assignment_audit_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["event", "created_at"]),
            models.Index(fields=["assignment", "created_at"]),
            models.Index(fields=["patient", "created_at"]),
            models.Index(fields=["doctor", "created_at"]),
        ]

class PainAssessment(models.Model):
    """
    Model for recording patient pain assessments.
    Utilizes a numerical scale from 1 to 10.
    """
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name="pain_assessments")
    performed_by = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, related_name="performed_pain_assessments")
    pain_score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Pain score from 1 (mild) to 10 (severe)"
    )
    notes = models.TextField(blank=True, null=True, help_text="Clinical notes regarding the pain assessment")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        db_table = "pain_assessments"
        verbose_name = "Pain Assessment"
        verbose_name_plural = "Pain Assessments"

    def __str__(self):
        return f"Pain Assessment for {self.patient.user.full_name}: {self.pain_score}/10"

    @property
    def pain_emoji(self):
        """Returns the emoji corresponding to the pain score."""
        emojis = {
            1: '😀', 2: '😀',
            3: '🙂', 4: '🙂',
            5: '😐', 6: '😐',
            7: '😟', 8: '😟',
            9: '😫', 10: '😫'
        }
        return emojis.get(self.pain_score, '❓')

    @property
    def pain_label(self):
        """Returns the label description for the pain score."""
        if self.pain_score <= 2: return 'Mild'
        if self.pain_score <= 4: return 'Moderate'
        if self.pain_score <= 6: return 'Distressing'
        if self.pain_score <= 8: return 'Intense'
        return 'Severe'

class PatientAssessmentArchive(models.Model):
    assessment_type = models.CharField(max_length=100, blank=True)
    medical_condition = models.CharField(max_length=200, blank=True)
    medical_history_summary = models.TextField(blank=True)
    assessment_data = models.JSONField(default=dict, help_text="Complete patient assessment data (unencrypted copy for development)")
    encrypted_assessment_data = models.TextField(blank=True, help_text="Base64 encoded encrypted assessment data")
    diagnostics = models.JSONField(default=dict, blank=True, help_text="Relevant diagnostic information")
    last_assessed_at = models.DateTimeField(null=True, blank=True)
    hospital_name = models.CharField(max_length=255, blank=True)
    
    user = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True, related_name="assessment_archives")
    archived_at = models.DateTimeField(auto_now_add=True)
    archived_by = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, related_name="archived_assessments")

    class Meta:
        ordering = ["-archived_at"]
        db_table = "patient_assessment_archives"
        verbose_name = "Patient Assessment Archive"
        verbose_name_plural = "Patient Assessment Archives"

    def __str__(self):
        return f"Archive for {self.user.full_name if self.user else 'Unknown'} - {self.assessment_type}"

class ArchiveAccessLog(models.Model):
    ACTION_CHOICES = [
        ('view', 'View'),
        ('export', 'Export'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('search', 'Search'),
    ]

    user = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, related_name="archive_access_logs")
    record = models.ForeignKey("PatientAssessmentArchive", on_delete=models.SET_NULL, null=True, blank=True, related_name="access_logs")
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    accessed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.CharField(max_length=64, blank=True)
    query_params = models.TextField(blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-accessed_at"]
        db_table = "archive_access_logs"
        verbose_name = "Archive Access Log"
        verbose_name_plural = "Archive Access Logs"

class MFAChallenge(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="mfa_challenges")
    code = models.CharField(max_length=12)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class SecureKey(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="secure_keys")
    public_key_pem = models.TextField()
    algorithm = models.CharField(max_length=64, default="RSA-OAEP-2048-SHA256")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class SecureTransmission(models.Model):
    sender = models.ForeignKey(Users, on_delete=models.PROTECT, related_name="sent_secure_transmissions")
    receiver = models.ForeignKey(Users, on_delete=models.PROTECT, related_name="received_secure_transmissions")
    patient = models.ForeignKey(PatientProfile, on_delete=models.PROTECT, related_name="secure_transmissions")
    
    ciphertext_b64 = models.TextField()
    iv_b64 = models.CharField(max_length=64)
    encrypted_key_b64 = models.TextField()
    signature_b64 = models.TextField()
    signing_public_key_pem = models.TextField()
    checksum_hex = models.CharField(max_length=128)
    
    encryption_alg = models.CharField(max_length=64, default="AES-256-GCM")
    signature_alg = models.CharField(max_length=64, default="ECDSA-P256-SHA256")
    
    status = models.CharField(max_length=32, default="pending", choices=[
        ("pending", "pending"),
        ("received", "received"),
        ("decrypted", "decrypted"),
        ("failed", "failed"),
    ])
    
    created_at = models.DateTimeField(auto_now_add=True)
    accessed_at = models.DateTimeField(blank=True, null=True)
    breach_flag = models.BooleanField(default=False)
    breach_notified_at = models.DateTimeField(blank=True, null=True)

class TransmissionAudit(models.Model):
    transmission = models.ForeignKey(SecureTransmission, on_delete=models.CASCADE, related_name="audits")
    actor = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True)
    event = models.CharField(max_length=64)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class PurgeAuditLog(models.Model):
    ACTION_CHOICES = [
        ("PURGE_MEDICAL_RECORDS", "Purge Medical Records"),
    ]
    STATUS_CHOICES = [
        ("started", "Started"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    action = models.CharField(max_length=64, choices=ACTION_CHOICES, default="PURGE_MEDICAL_RECORDS")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="started")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    patient_profiles_cleared = models.PositiveIntegerField(default=0)
    analytics_records_deleted = models.PositiveIntegerField(default=0)
    assessment_archives_deleted = models.PositiveIntegerField(default=0)
    
    details = models.JSONField(default=dict, blank=True, help_text="Additional non-sensitive metadata, e.g., field list, durations")
    error_message = models.TextField(blank=True)
    
    actor = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True, related_name="purge_actions", help_text="User who initiated the purge")

    class Meta:
        db_table = "purge_audit_logs"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["action", "status"]),
            models.Index(fields=["started_at"]),
        ]

class DailySequenceCounter(models.Model):
    department = models.CharField(
        max_length=100, 
        choices=[
            ('OPD', 'Out Patient Department'), 
            ('Pharmacy', 'Pharmacy'), 
            ('Appointment', 'Appointment')
        ], 
        help_text='Department for which the daily counter is tracked'
    )
    date = models.DateField(help_text='Date for the daily sequence counter')
    current_value = models.PositiveIntegerField(default=0, help_text='Last assigned daily sequence number for this date')

    class Meta:
        db_table = 'daily_sequence_counters'
        ordering = ['-date', 'department']
        unique_together = ('department', 'date')

    def __str__(self):
        return f"{self.department} - {self.date} - {self.current_value}"


def _fernet_from_settings() -> Fernet:
    raw = getattr(settings, "MESSAGE_ENCRYPTION_KEY", "") or ""
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_json_payload(payload: dict) -> str:
    f = _fernet_from_settings()
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    token = f.encrypt(raw)
    return token.decode("utf-8")


def decrypt_json_payload(token: str) -> dict:
    f = _fernet_from_settings()
    raw = f.decrypt(token.encode("utf-8"))
    return json.loads(raw.decode("utf-8"))


class PsychiatricOpdQuestionnaire(models.Model):
    STATUS_CHOICES = [
        ("draft", "draft"),
        ("submitted", "submitted"),
    ]

    patient_profile = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name="psychiatric_opd_questionnaires")
    created_by = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_psychiatric_opd_questionnaires")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="draft")
    encrypted_payload = models.TextField()
    payload_sha256 = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "psychiatric_opd_questionnaires"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["patient_profile", "status"]),
            models.Index(fields=["updated_at"]),
        ]

    def set_payload(self, payload: dict):
        self.encrypted_payload = encrypt_json_payload(payload)
        self.payload_sha256 = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

    def get_payload(self) -> dict:
        try:
            return decrypt_json_payload(self.encrypted_payload)
        except Exception:
            return {}
