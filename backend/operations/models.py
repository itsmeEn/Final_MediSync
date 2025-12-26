from django.db import models
from django.contrib.auth import get_user_model
from backend.users.models import GeneralDoctorProfile, NurseProfile, PatientProfile
from backend.admin_site.models import Hospital
from django.utils import timezone
from datetime import timedelta
from cryptography.fernet import Fernet
from django.conf import settings
import base64
import json
from django.db import transaction


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

#queueing system for operations normal queues
class QueueManagement(models.Model):
    """Queue management model for handling patient queues in operations.
    - Each queue is associated with a patient.
    - Tracks the queue number, status, and timestamps for creation and updates.
    - FIFO
    """
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name="queue_management")
    queue_number = models.PositiveIntegerField(unique=True)
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
    ], default="waiting")
    
    #implementation of FIFO 
    position_in_queue = models.PositiveIntegerField(default=0, help_text="Position in the queue.")
    enqueue_time = models.DateTimeField(help_text="Timestamp when the patient was added to the queue."
                                        ,default=timezone.now)
    dequeue_time = models.DateTimeField(null=True, blank=True, help_text="Timestamp when the patient was removed from the queue.")
    started_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when the queue started.")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["department", "position_in_queue", "enqueue_time"]
        db_table = "queue_management"
        verbose_name = "Queue Management"
        verbose_name_plural = "Queue Management"
        unique_together = ["department", "queue_number", "patient"] #each patient should have unique queue number when queueing in different departments
        
    #fifo implementtion
    def save(self, *args, **kwargs):
        """
        Assign a globally unique queue_number and per-department FIFO position_on_queue
        in a safe way, then persist and normalize positions.
        """
        creating = self.pk is None
        with transaction.atomic():
            # Assign queue number globally unique across all departments
            if creating and not self.queue_number:
                last_queue_number = QueueManagement.objects.aggregate(
                    maximum_queue_number=models.Max("queue_number")
                )["maximum_queue_number"] or 0
                self.queue_number = last_queue_number + 1

            # Assign FIFO position per department for waiting/in_progress entries
            if creating and not self.position_in_queue:
                last_position = QueueManagement.objects.filter(
                    department=self.department,
                    status__in=["waiting", "in_progress"]
                ).aggregate(
                    maximum_position=models.Max("position_in_queue")
                )["maximum_position"] or 0
                self.position_in_queue = last_position + 1

            super().save(*args, **kwargs)
            # Normalize positions of waiting patients by enqueue_time (FIFO)
            self.update_queue_positions()

    #update the queueu 
    def update_queue_positions(self):
        """
        Update the positions for all waiting patients in the queue.
        """
        waiting_patients = QueueManagement.objects.filter(
            department=self.department, status="waiting"
            ).order_by("enqueue_time")
        
        #ensures that each patient has a position in queueu
        for index, patient in enumerate(waiting_patients, start=1):
            if patient.position_in_queue != index:
                patient.position_in_queue = index
                QueueManagement.objects.filter(id=patient.id).update(position_in_queue=index)
        
        
        #get the patient estimated waiting time
        """
        calculate the estimated waiting time for each patient in the queue.
        """

    @classmethod
    def update_queue_positions_for_department(cls, department: str):
        """
        Recalculate FIFO positions for all waiting normal-queue entries in a department.
        Safe for use after deletions, cancellations, or bulk updates.
        """
        waiting_patients = cls.objects.filter(
            department=department, status="waiting"
        ).order_by("enqueue_time")
        for index, patient in enumerate(waiting_patients, start=1):
            if patient.position_in_queue != index:
                cls.objects.filter(id=patient.id).update(position_in_queue=index)

    def get_estimated_wait_time(self):
        if self.status != "waiting":
            return None
        
        # Calculate average service time
        completed_queues = QueueManagement.objects.filter(
            department=self.department, status="completed",
            started_at__isnull=False, finished_at__isnull=False
        )
        total_service_time = sum([q.finished_at - q.started_at for q in completed_queues], timedelta())
        
        if completed_queues.count() > 0:
            avg_service_time = total_service_time / completed_queues.count()
        else:
            # Use a default value if no one has completed yet
            avg_service_time = timedelta(minutes=15) 

        # Count patients ahead
        patients_ahead_count = QueueManagement.objects.filter(
            department=self.department,
            status__in=["waiting", "in_progress"],
            position_in_queue__lt=self.position_in_queue
        ).count()
        
        return avg_service_time * patients_ahead_count
    
    def mark_started(self):
        """
        Mark this queue entry as started and set timestamp.
        """
        self.status = "in_progress"
        self.started_at = timezone.now()
        self.save()

    def mark_completed(self):
        """
        Mark this queue entry as completed and set completion timestamp.
        Also updates actual_wait_time if start time was recorded.
        """
        self.status = "completed"
        # Use finished_at as the completion timestamp field
        self.finished_at = timezone.now()
        if self.started_at:
            self.actual_wait_time = self.finished_at - self.enqueue_time
        self.save()
        # Update subsequent queue positions after completion
        self.update_queue_positions()
        
    def get_next_in_queue(self):
        """
        Get the next patient in the queue.
        """
        next_patient = QueueManagement.objects.filter(
            department=self.department, status="waiting"
        ).order_by("position_in_queue").first()
        return next_patient
    @classmethod
    def get_queue_by_dept(cls, department):
        """
        Get the queue for a specific department.
        """
        queue = cls.objects.filter(department=department).order_by("position_in_queue")
        return queue
        
    def __str__(self):
        return f"Queue {self.queue_number} - Patient: {self.patient.full_name}"
    
#medicine inventory management
class MedicineInventory(models.Model):
    """Medicine inventory management model.Tracks the available stock of medicines."""
    inventory = models.ForeignKey(
        NurseProfile, on_delete=models.CASCADE, related_name="medicine_inventory", limit_choices_to={"user__role": "nurse"}
        # This ensures that only nurses or a pharmacist can manage the inventory.
    )
    medicine_name = models.CharField(max_length=100, help_text="Name of the medicine.")
    stock_number = models.PositiveIntegerField(default=0, help_text="Current stock of the medicine.")
    current_stock = models.PositiveIntegerField(default=0, help_text="Current available stock of the medicine.")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price per unit of the medicine.")
    minimum_stock_level = models.PositiveIntegerField(default=0, help_text="Minimum stock level before reordering.")
    expiry_date = models.DateField(null=True, blank=True, help_text="Expiry date of the medicine.")
    batch_number = models.CharField(max_length=50, unique=True, help_text="Batch number of the medicine.")
    last_restocked = models.DateTimeField(auto_now=True, help_text="Last time the medicine was restocked.")
    usage_pattern = models.TextField(
        blank=True, help_text="Description of the usage pattern for the medicine."
    ) #this can be used when the medicine is used frequently or has a specific usage pattern for predicting future stock needs or analytic basta yan siya.
    #notified the nurses about medicine stock, expiration
    notification = models.ForeignKey(Notification, on_delete=models.SET_NULL, null=True, blank=True, related_name="medicine_inventory")
    class Meta:
        ordering = ["medicine_name"]
        db_table = "medicine_inventory"
        verbose_name = "Medicine Inventory"
        verbose_name_plural = "Medicine Inventory"

    @property
    def is_expired(self):
        return self.expiry_date and self.expiry_date < timezone.now().date()#this can be used to check if the medicine is expired or not.

    @property
    def is_available(self):
        return self.current_stock > 0 and not self.is_expired

    @property
    def total_value(self):
        return self.current_stock * self.unit_price if self.current_stock else 0.0

    def save(self, *args, **kwargs):
        if self.current_stock < 0:
            raise ValueError("Current stock cannot be negative.")
        if self.unit_price < 0:
            raise ValueError("Unit price cannot be negative.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.medicine_name} - Stock: {self.current_stock}"
    
    #appointment management 
class AppointmentManagement(models.Model):
    """Appointment management model for handling patient appointments."""
    appointment_id = models.AutoField(primary_key=True, help_text="Unique identifier for the appointment.")
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name="appointments")
    doctor = models.ForeignKey(GeneralDoctorProfile, on_delete=models.CASCADE, related_name="appointments")
    # [2025-10-31] Reintroduced structured time slot reference to match prior migrations
    # (kept nullable to preserve backward compatibility with existing records)
    time_slot = models.ForeignKey('DoctorTimeSlot', on_delete=models.SET_NULL, null=True, blank=True, related_name='appointments', help_text="Structured time slot for the appointment (nullable for backward compatibility)")
    # [2025-10-31] Added flexible department association to prevent NULL errors
    # and support hospital-specific department labels/slugs (default to OPD)
    department = models.CharField(max_length=100, help_text="Department for the appointment.", default="OPD")
    appointment_date = models.DateTimeField(help_text="Date and time of the appointment.")
    appointment_type = models.CharField(
        max_length=50, choices=[
            ("consultation", "Consultation"),
            ("follow_up", "Follow Up"),
            ("emergency", "Emergency"),
        ], default="consultation"
    )
    appointment_time = models.TimeField(help_text="Time of the appointment.")
    queue_number = models.PositiveIntegerField(unique=True, help_text="Queue number for the appointment.")
    # Lifecycle timestamps for analytics and operational tracking
    checked_in_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when the patient checked in for the appointment.")
    consultation_started_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when the consultation started.")
    consultation_finished_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when the consultation finished.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    #status of the appointment like scheduled, completed, cancelled, no show
    status = models.CharField(max_length=50, choices=[
        ("scheduled", "Scheduled"),
        ("rescheduled", "Rescheduled"),
        ("checked_in", "Checked In"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("no_show", "No Show"),
    ], default="scheduled")
    cancellation_reason = models.TextField(blank=True, null=True, help_text="Reason for cancellation.")
    reschedule_reason = models.TextField(blank=True, null=True, help_text="Reason for rescheduling.")

    class Meta:
        ordering = ["appointment_date"]
        db_table = "appointment_management"
        verbose_name = "Appointment Management"
        verbose_name_plural = "Appointment Management"

    def __str__(self):
        return f"Appointment {self.id} - Patient: {self.patient.user.full_name} with Dr. {self.doctor.user.full_name}"

class Department(models.Model):
    """Hospital departments (e.g., Cardiology, OPD)."""
    # [2025-10-31] Restored Department model to align with migrations
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Department"
        verbose_name_plural = "Departments"
        db_table = "department"
        ordering = ["name"]

    def __str__(self):
        return self.name

class HospitalDepartmentDoctor(models.Model):
    """Mapping between Hospital, Department, and Doctor with status and capacity."""
    # [2025-10-31] Restored mapping model to prevent destructive migration operations
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='department_doctors')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='hospital_doctors')
    doctor = models.ForeignKey(GeneralDoctorProfile, on_delete=models.CASCADE, related_name='hospital_departments')
    status = models.CharField(max_length=20, choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active')
    capacity_limit = models.PositiveIntegerField(null=True, blank=True, help_text="Optional max concurrent appointments for this mapping.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Hospital Department Doctor"
        verbose_name_plural = "Hospital Department Doctors"
        db_table = "hospital_department_doctor"
        unique_together = ("hospital", "department", "doctor")

    def __str__(self):
        return f"{self.hospital} - {self.department} - {self.doctor}"

class DoctorTimeSlot(models.Model):
    """Doctor time slots within a hospital department mapping."""
    # [2025-10-31] Restored time slot model for structured scheduling compatibility
    hospital_department_doctor = models.ForeignKey(HospitalDepartmentDoctor, on_delete=models.CASCADE, related_name='time_slots')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    capacity = models.PositiveIntegerField(default=1, help_text="Max number of bookings allowed in this slot")
    booked_count = models.PositiveIntegerField(default=0, help_text="Number of bookings confirmed in this slot")
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Doctor Time Slot"
        verbose_name_plural = "Doctor Time Slots"
        db_table = "doctor_time_slot"
        unique_together = ("hospital_department_doctor", "date", "start_time", "end_time")

    def __str__(self):
        return f"{self.hospital_department_doctor} @ {self.date} {self.start_time}-{self.end_time}"
    
    def save(self, *args, **kwargs):
        """Validate slot time ranges and availability constraints before saving."""
        # Validate time range
        if self.start_time >= self.end_time:
            raise ValueError("Start time must be before end time.")

        # Disable availability if slot date is in the past
        try:
            if self.date < timezone.now().date():
                self.is_available = False
        except Exception:
            # If timezone comparison fails, proceed safely
            pass

        # Enforce capacity constraints
        if self.booked_count is not None and self.capacity is not None:
            if self.booked_count >= self.capacity:
                self.is_available = False

        super().save(*args, **kwargs)

#queue for priority patients
# no show.
class PriorityQueue(models.Model):
    """Priority queue model for handling patients with special needs or conditions or age. """
    appointment_id = models.ForeignKey(AppointmentManagement, on_delete=models.CASCADE, related_name="priority_queue", null=True, blank=True)
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name="priority_queue")
    notification = models.ForeignKey(Notification, on_delete=models.SET_NULL, null=True, blank=True, related_name="priority_queue")
    #prioritty level based on age, condition, or other factors
    priority_level = models.CharField(
        max_length=50, choices=[
            ("pwd", "Person With Disability"),
            ("pregnant", "Pregnant"),
            ("senior", "Senior Citizen"),
            ("with_child", "Accompanying a Child"),
        ], default="senior", help_text="Priority level of the patient in the queue."
    )
    department = models.CharField(max_length=100, help_text="Department for which the queue is managed.", default="OPD")
    
    # Status and timestamps for queue lifecycle
    status = models.CharField(max_length=50, choices=[
        ("waiting", "Waiting"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ], default="waiting")
    enqueue_time = models.DateTimeField(default=timezone.now, help_text="Timestamp when the patient was added to the priority queue.")
    started_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when the priority processing started.")
    finished_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when the priority processing finished.")
    
    actual_wait_time = models.DurationField(null=True, blank=True, help_text="Actual wait time for the patient.")
    estimated_wait_time = models.DurationField(null=True, blank=True, help_text="Estimated wait time for the patient.")
    created_at = models.DateTimeField(auto_now_add=True)
    queue_number = models.PositiveIntegerField(unique=True, help_text="Queue number for the priority patient.")
    
    #priority queue specific fields since priority siya di siya mag-undergo sa fifo
    priority_position = models.PositiveIntegerField(default=0, help_text="Position in the priority queue.")
    skip_normal_queues = models.BooleanField(default=False, help_text="Indicates if the patient should be skipped from the FIFO queue.")

    class Meta:
        ordering = ["enqueue_time", "priority_position", "created_at"]
        db_table = "priority_queue"
        verbose_name = "Priority Queue"
        verbose_name_plural = "Priority Queues"
        
    def save(self, *args, **kwargs):
        #auto assign queue number per department
        if not self.queue_number:
            self.queue_number = PriorityQueue.objects.filter(
                department=self.department
            ).aggregate(
                maximum_queue_number = models.Max("queue_number")
            )['maximum_queue_number'] or 0
            self.queue_number += 1
            
        #auto assign priority positions (FIFO within priority queue)
        if not self.priority_position:
            last_position = PriorityQueue.objects.filter(
                department=self.department,
                status__in=["waiting", "in_progress"]
            ).aggregate(
                maximum_position=models.Max("priority_position")
            )["maximum_position"] or 0
            self.priority_position = last_position + 1
        super().save(*args, **kwargs)
       
    """
    Calculate the estimated waiting time for priority lists
    """ 
    def get_estimated_wait_time(self):
        if self.status != "waiting":
            return None
        
        # Calculate average service time based on completed normal queues
        completed_queues = QueueManagement.objects.filter(
            department=self.department, status="completed",
            started_at__isnull=False, finished_at__isnull=False
        )
        total_service_time = sum([q.finished_at - q.started_at for q in completed_queues], timedelta())
        
        if completed_queues.count() > 0:
            avg_service_time = total_service_time / completed_queues.count()
        else:
            # Use a default value if no one has completed yet
            avg_service_time = timedelta(minutes=15)
            
        # Count priority patients ahead in the same department
        patients_ahead_count = PriorityQueue.objects.filter(
            department=self.department,
            status__in=["waiting", "in_progress"],
            enqueue_time__lt=self.enqueue_time
        ).count()
        
        return avg_service_time * patients_ahead_count

    def mark_started(self):
        self.status = "in_progress"
        self.started_at = timezone.now()
        self.save()

    def mark_completed(self):
        self.status = "completed"
        self.finished_at = timezone.now()
        if self.started_at:
            self.actual_wait_time = self.finished_at - self.enqueue_time
        self.save()

    def __str__(self):
        return f"Priority Queue - Patient: {self.patient.user.full_name} ({self.priority_level})"
    
#exchanging communications via messaging app
class Conversation(models.Model):
    """
    Conversation model for grouping messages between users.
    """
    participants = models.ManyToManyField(Users, related_name="conversations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ["-updated_at"]
        db_table = "conversations"
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"

    def __str__(self):
        participant_names = [p.full_name for p in self.participants.all()]
        return f"Conversation: {', '.join(participant_names)}"

    def get_other_participant(self, user):
        """Get the other participant in a 1-on-1 conversation"""
        return self.participants.exclude(id=user.id).first()
    
    def get_unread_count(self, user):
        """Get unread message count for a specific user"""
        return self.messages.filter(is_read=False).exclude(sender=user).count()
    
    def mark_messages_as_delivered(self, user):
        """Mark messages as delivered for a specific user"""
        undelivered_messages = self.messages.filter(
            is_delivered=False
        ).exclude(sender=user)
        
        for message in undelivered_messages:
            message.is_delivered = True
            message.delivered_at = timezone.now()
            message.save()
    
    def mark_messages_as_read(self, user):
        """Mark messages as read for a specific user"""
        unread_messages = self.messages.filter(
            is_read=False
        ).exclude(sender=user)
        
        for message in unread_messages:
            message.is_read = True
            message.read_at = timezone.now()
            message.save()

class Message(models.Model):
    """
    Enhanced messaging model with file support, reactions, and encryption.
    """ 
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="sent_messages")
    content = models.TextField(help_text="Encrypted message content.")
    encrypted_content = models.TextField(blank=True, help_text="Base64 encoded encrypted content")
    file_attachment = models.FileField(
        upload_to='message_attachments/', 
        blank=True, 
        null=True,
        help_text="Optional file attachment"
    )
    file_name = models.CharField(max_length=255, blank=True, help_text="Original file name")
    file_size = models.PositiveIntegerField(null=True, blank=True, help_text="File size in bytes")
    is_read = models.BooleanField(default=False, help_text="Whether the message has been read")
    is_delivered = models.BooleanField(default=False, help_text="Whether the message has been delivered")
    read_at = models.DateTimeField(null=True, blank=True, help_text="When the message was read")
    delivered_at = models.DateTimeField(null=True, blank=True, help_text="When the message was delivered")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the message was sent.")
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:        
        ordering = ["created_at"]
        db_table = "messages"
        verbose_name = "Message"
        verbose_name_plural = "Messages"

    def __str__(self):
        return f"Message from {self.sender.full_name}: {self.content[:50]}..."

    @property
    def has_attachment(self):
        return bool(self.file_attachment)
    
    def encrypt_content(self, plaintext):
        """Encrypt message content using Fernet encryption"""
        try:
            # Get encryption key from settings or generate one
            key = getattr(settings, 'MESSAGE_ENCRYPTION_KEY', None)
            if not key:
                # Generate a new key if none exists (for development)
                key = Fernet.generate_key()
                print(f"Generated new encryption key: {key.decode()}")
            
            if isinstance(key, str):
                key = key.encode()
            
            f = Fernet(key)
            encrypted_data = f.encrypt(plaintext.encode())
            return base64.b64encode(encrypted_data).decode()
        except Exception as e:
            print(f"Encryption error: {e}")
            return plaintext  # Fallback to plaintext
    
    def decrypt_content(self):
        """Decrypt message content"""
        try:
            if not self.encrypted_content:
                return self.content
            
            key = getattr(settings, 'MESSAGE_ENCRYPTION_KEY', None)
            if not key:
                return self.content
            
            if isinstance(key, str):
                key = key.encode()
            
            f = Fernet(key)
            encrypted_data = base64.b64decode(self.encrypted_content.encode())
            decrypted_data = f.decrypt(encrypted_data)
            return decrypted_data.decode()
        except Exception as e:
            print(f"Decryption error: {e}")
            return self.content  # Fallback to stored content
    
    def save(self, *args, **kwargs):
        """Override save to encrypt content before saving"""
        if self.content and not self.encrypted_content:
            self.encrypted_content = self.encrypt_content(self.content)
        super().save(*args, **kwargs)
    
    def create_notifications(self):
        """Create notifications for all participants except sender"""
        # Get all participants except sender
        recipients = self.conversation.participants.exclude(id=self.sender.id)
        
        for recipient in recipients:
            MessageNotification.objects.create(
                message=self,
                recipient=recipient,
                notification_type='new_message'
            )

class MessageNotification(models.Model):
    """
    Model for tracking message notifications and delivery status
    """
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="notifications")
    recipient = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="message_notifications")
    notification_type = models.CharField(
        max_length=20,
        choices=[
            ('new_message', 'New Message'),
            ('message_delivered', 'Message Delivered'),
            ('message_read', 'Message Read'),
        ],
        default='new_message'
    )
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-created_at"]
        db_table = "message_notifications"
        verbose_name = "Message Notification"
        verbose_name_plural = "Message Notifications"
    
    def __str__(self):
        return f"Notification for {self.recipient.full_name}: {self.notification_type}"

class MessageReaction(models.Model):
    """
    Model for message reactions (like, love, etc.)
    """
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="message_reactions")
    reaction_type = models.CharField(
        max_length=20,
        choices=[
            ('like', '👍'),
            ('love', '❤️'),
            ('laugh', '😂'),
            ('wow', '😮'),
            ('sad', '😢'),
            ('angry', '😠'),
        ],
        default='like'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['message', 'user', 'reaction_type']
        db_table = "message_reactions"
        verbose_name = "Message Reaction"
        verbose_name_plural = "Message Reactions"

    def __str__(self):
        return f"{self.user.full_name} reacted {self.reaction_type} to message"

# Keep the old Messaging model for backward compatibility
class Messaging(models.Model):
    """
    Legacy messaging model - kept for backward compatibility.
    """ 
    sender = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="legacy_sent_messages")
    receiver = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="legacy_received_messages")
    message = models.TextField(help_text="Message content.")    
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the message was sent.")  
    
    class Meta:        
        ordering = ["-created_at"]
        db_table = "messaging"
        verbose_name = "Legacy Messaging"
        verbose_name_plural = "Legacy Messaging"

    def __str__(self):
        return f"From {self.sender.full_name} to {self.receiver.full_name}: {self.message[:50]}..."

#doctor availability management
class DoctorAvailability(models.Model):
    """Doctor availability management for blocking dates and setting schedules."""
    doctor = models.ForeignKey(GeneralDoctorProfile, on_delete=models.CASCADE, related_name="availability")
    date = models.DateField(help_text="Date when doctor is unavailable")
    reason = models.CharField(max_length=255, blank=True, help_text="Reason for unavailability")
    is_blocked = models.BooleanField(default=True, help_text="Whether the date is blocked")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date"]
        db_table = "doctor_availability"
        verbose_name = "Doctor Availability"
        verbose_name_plural = "Doctor Availability"
        unique_together = ["doctor", "date"]

    def __str__(self):
        return f"Dr. {self.doctor.user.full_name} - {self.date} ({'Blocked' if self.is_blocked else 'Available'})"


class PatientAssignment(models.Model):
    """
    Model for assigning patients to doctors with specific specializations
    """
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name="assignments")
    doctor = models.ForeignKey(GeneralDoctorProfile, on_delete=models.CASCADE, related_name="assigned_patients")
    assigned_by = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="patient_assignments", help_text="Nurse who assigned the patient")
    specialization_required = models.CharField(max_length=100, help_text="Required specialization for this assignment")
    assignment_reason = models.TextField(blank=True, help_text="Reason for assignment")
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('accepted', 'Accepted'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('rejected', 'Rejected'),
        ],
        default='pending',
        help_text="Assignment status"
    )
    assigned_at = models.DateTimeField(auto_now_add=True, help_text="When the patient was assigned")
    accepted_at = models.DateTimeField(null=True, blank=True, help_text="When the doctor accepted the assignment")
    completed_at = models.DateTimeField(null=True, blank=True, help_text="When the consultation was completed")
    priority = models.CharField(
        max_length=10,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('urgent', 'Urgent'),
        ],
        default='medium',
        help_text="Assignment priority"
    )

    class Meta:
        ordering = ["-assigned_at"]
        db_table = "patient_assignments"
        verbose_name = "Patient Assignment"
        verbose_name_plural = "Patient Assignments"
        unique_together = ['patient', 'doctor', 'assigned_at']

    def __str__(self):
        return f"{self.patient.user.full_name} assigned to Dr. {self.doctor.user.full_name} ({self.specialization_required})"


class ConsultationNotes(models.Model):
    """
    Model for doctor consultation notes
    """
    assignment = models.ForeignKey(PatientAssignment, on_delete=models.CASCADE, related_name="consultation_notes")
    doctor = models.ForeignKey(GeneralDoctorProfile, on_delete=models.CASCADE, related_name="consultation_notes")
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name="consultation_notes")
    
    # Consultation details
    chief_complaint = models.TextField(help_text="Patient's main complaint")
    history_of_present_illness = models.TextField(help_text="Detailed history of the current illness")
    physical_examination = models.TextField(help_text="Physical examination findings")
    diagnosis = models.TextField(help_text="Doctor's diagnosis")
    treatment_plan = models.TextField(help_text="Recommended treatment plan")
    medications_prescribed = models.TextField(blank=True, help_text="Medications prescribed")
    follow_up_instructions = models.TextField(blank=True, help_text="Follow-up instructions for the patient")
    additional_notes = models.TextField(blank=True, help_text="Any additional notes")
    
    # Status and timestamps
    status = models.CharField(
        max_length=20,
        choices=[
            ('draft', 'Draft'),
            ('completed', 'Completed'),
            ('reviewed', 'Reviewed'),
        ],
        default='draft',
        help_text="Status of the consultation notes"
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="When the notes were created")
    updated_at = models.DateTimeField(auto_now=True, help_text="When the notes were last updated")
    completed_at = models.DateTimeField(null=True, blank=True, help_text="When the consultation was completed")

    class Meta:
        ordering = ["-created_at"]
        db_table = "consultation_notes"
        verbose_name = "Consultation Notes"
        verbose_name_plural = "Consultation Notes"

    def __str__(self):
        return f"Consultation notes for {self.patient.user.full_name} by Dr. {self.doctor.user.full_name}"


class QueueSchedule(models.Model):
    """
    Model for managing queue activation schedules set by nurses
    """
    department = models.CharField(
        max_length=100,
        help_text="Department for which the schedule is set"
    )
    nurse = models.ForeignKey(
        NurseProfile, 
        on_delete=models.CASCADE, 
        related_name="queue_schedules",
        help_text="Nurse who set the schedule"
    )
    
    # Schedule settings
    start_time = models.TimeField(help_text="Time when queue should open")
    end_time = models.TimeField(help_text="Time when queue should close")
    days_of_week = models.JSONField(
        default=list,
        help_text="List of days when queue is active (0=Monday, 6=Sunday)"
    )
    
    # Status and control
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this schedule is currently active"
    )
    manual_override = models.BooleanField(
        default=False,
        help_text="Manual override by nurse (overrides time-based activation)"
    )
    override_status = models.CharField(
        max_length=20,
        choices=[
            ('enabled', 'Manually Enabled'),
            ('disabled', 'Manually Disabled'),
            ('auto', 'Automatic'),
        ],
        default='auto',
        help_text="Current override status"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["-updated_at"]
        db_table = "queue_schedules"
        verbose_name = "Queue Schedule"
        verbose_name_plural = "Queue Schedules"
        unique_together = ['department', 'nurse']
    
    def is_queue_open(self):
        """
        Check if queue should be open based on schedule and manual override
        """
        if self.manual_override:
            return self.override_status == 'enabled'
        
        if not self.is_active:
            return False
        
        now = timezone.now()
        current_time = now.time()
        current_day = now.weekday()  # 0=Monday, 6=Sunday
        
        # Check if today is in the scheduled days
        if current_day not in self.days_of_week:
            return False
        
        # Check if current time is within schedule
        return self.start_time <= current_time <= self.end_time
    
    def __str__(self):
        return f"{self.department} Queue Schedule by {self.nurse.user.full_name}"


class PurgeAuditLog(models.Model):
    """
    Audit log for medical records purges.
    Stores only non-PHI metadata and counts for compliance.
    """
    ACTION_CHOICES = [
        ("PURGE_MEDICAL_RECORDS", "Purge Medical Records"),
    ]

    STATUS_CHOICES = [
        ("started", "Started"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    actor = models.ForeignKey(
        Users,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purge_actions",
        help_text="User who initiated the purge"
    )
    action = models.CharField(max_length=64, choices=ACTION_CHOICES, default="PURGE_MEDICAL_RECORDS")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="started")

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Counts only; do not store PHI or raw data
    patient_profiles_cleared = models.PositiveIntegerField(default=0)
    analytics_records_deleted = models.PositiveIntegerField(default=0)
    assessment_archives_deleted = models.PositiveIntegerField(default=0)

    details = models.JSONField(default=dict, blank=True, help_text="Additional non-sensitive metadata, e.g., field list, durations")
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "purge_audit_logs"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["action", "status"]),
            models.Index(fields=["started_at"]),
        ]

    def mark_success(self, counts: dict | None = None, extra: dict | None = None):
        self.status = "success"
        self.completed_at = timezone.now()
        if counts:
            self.patient_profiles_cleared = int(counts.get("patient_profiles_cleared", self.patient_profiles_cleared))
            self.analytics_records_deleted = int(counts.get("analytics_records_deleted", self.analytics_records_deleted))
            self.assessment_archives_deleted = int(counts.get("assessment_archives_deleted", self.assessment_archives_deleted))
        if extra:
            self.details = {**(self.details or {}), **extra}
        self.save(update_fields=[
            "status",
            "completed_at",
            "patient_profiles_cleared",
            "analytics_records_deleted",
            "assessment_archives_deleted",
            "details",
        ])

    def mark_failed(self, message: str):
        self.status = "failed"
        self.completed_at = timezone.now()
        self.error_message = message[:4000]
        self.save(update_fields=["status", "completed_at", "error_message"])


class QueueStatus(models.Model):
    """
    Model for tracking real-time queue status and broadcasting changes
    """
    department = models.CharField(
        max_length=100,
        unique=True,
        help_text="Department for which status is tracked"
    )
    
    # Current status
    current_schedule = models.ForeignKey(
        'QueueSchedule',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Currently active schedule for this department"
    )
    is_open = models.BooleanField(
        default=False,
        help_text="Whether the queue is currently open for new patients"
    )
    current_serving = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Queue number currently being served"
    )
    total_waiting = models.PositiveIntegerField(
        default=0,
        help_text="Total number of patients currently waiting"
    )
    estimated_wait_time = models.DurationField(
        null=True,
        blank=True,
        help_text="Estimated wait time for new patients"
    )
    
    # Status message for patients
    status_message = models.CharField(
        max_length=200,
        default="Queue Closed",
        help_text="Current status message displayed to patients"
    )
    
    # Last update info
    last_updated_by = models.ForeignKey(
        Users,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who last updated the status"
    )
    last_updated_at = models.DateTimeField(auto_now=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "queue_status"
        verbose_name = "Queue Status"
        verbose_name_plural = "Queue Statuses"
    
    def update_status_message(self):
        """
        Update status message based on current queue state
        """
        if self.is_open:
            if self.total_waiting == 0:
                self.status_message = "Queue Open - No Wait"
            else:
                wait_msg = f"Estimated wait: {self.estimated_wait_time}" if self.estimated_wait_time else ""
                self.status_message = f"Queue Open - {self.total_waiting} waiting {wait_msg}".strip()
        else:
            self.status_message = "Queue Closed"
    
    def should_auto_close(self):
        """
        Check if queue should be automatically closed based on schedule.
        Returns True if current time is past the scheduled end time.
        """
        if not self.current_schedule or not self.is_open:
            return False
        
        current_time = timezone.now().time()
        schedule = self.current_schedule
        
        # Check if we're past the end time
        if current_time > schedule.end_time:
            return True
        
        # Check if manual override is preventing auto-close
        if schedule.manual_override and schedule.override_status == 'enabled':
            return False
        
        return False
    
    def auto_close_if_needed(self):
        """
        Automatically close the queue if past scheduled time.
        Returns True if queue was closed, False otherwise.
        """
        if self.should_auto_close():
            self.is_open = False
            self.update_status_message()
            self.save()
            return True
        return False
    
    def __str__(self):
        return f"{self.department} Queue Status: {'Open' if self.is_open else 'Closed'}"


class QueueStatusLog(models.Model):
    """
    Model for logging queue status changes for audit and analytics
    """
    department = models.CharField(
        max_length=100,
        help_text="Department for which status changed"
    )
    
    # Status change details
    previous_status = models.BooleanField(help_text="Previous queue open/closed status")
    new_status = models.BooleanField(help_text="New queue open/closed status")
    change_reason = models.CharField(
        max_length=50,
        choices=[
            ('schedule', 'Scheduled Time'),
            ('manual', 'Manual Override'),
            ('system', 'System Update'),
        ],
        help_text="Reason for status change"
    )
    
    # Change metadata
    changed_by = models.ForeignKey(
        Users,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who triggered the change"
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    additional_notes = models.TextField(
        blank=True,
        help_text="Additional notes about the status change"
    )
    
    class Meta:
        ordering = ["-changed_at"]
        db_table = "queue_status_logs"
        verbose_name = "Queue Status Log"
        verbose_name_plural = "Queue Status Logs"
    
    def __str__(self):
        status_change = "Opened" if self.new_status else "Closed"
        return f"{self.department} Queue {status_change} at {self.changed_at}"


class PatientAssessmentArchive(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="patient_archives")
    patient_profile = models.ForeignKey(PatientProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="archives")
    assessment_type = models.CharField(max_length=100, blank=True)
    medical_condition = models.CharField(max_length=200, blank=True)
    medical_history_summary = models.TextField(blank=True)
    assessment_data = models.JSONField(default=dict, help_text="Complete patient assessment data (unencrypted copy for development)")
    encrypted_assessment_data = models.TextField(blank=True, help_text="Base64 encoded encrypted assessment data")
    diagnostics = models.JSONField(default=dict, blank=True, help_text="Relevant diagnostic information")
    last_assessed_at = models.DateTimeField(null=True, blank=True)
    hospital_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_assessed_at", "-updated_at"]
        db_table = "patient_assessment_archives"
        verbose_name = "Patient Assessment Archive"
        verbose_name_plural = "Patient Assessment Archives"

    def __str__(self):
        name = getattr(self.user, 'full_name', '') or str(self.user_id)
        return f"Archive for {name} - {self.medical_condition or self.assessment_type}"

    def _get_encryption_key(self):
        key = getattr(settings, 'ARCHIVE_ENCRYPTION_KEY', None) or getattr(settings, 'MESSAGE_ENCRYPTION_KEY', None)
        if isinstance(key, str):
            key = key.encode()
        return key

    def encrypt_payload(self, payload: dict) -> str:
        try:
            key = self._get_encryption_key()
            if not key:
                # Fallback for development when key is missing
                key = Fernet.generate_key()
            f = Fernet(key)
            raw = json.dumps(payload or {}, ensure_ascii=False)
            encrypted = f.encrypt(raw.encode())
            return base64.b64encode(encrypted).decode()
        except Exception:
            # Fallback to plain JSON to avoid data loss in development
            return json.dumps(payload or {}, ensure_ascii=False)

    def decrypt_payload(self) -> dict:
        try:
            if not self.encrypted_assessment_data:
                return self.assessment_data or {}
            key = self._get_encryption_key()
            if not key:
                return self.assessment_data or {}
            f = Fernet(key)
            encrypted_data = base64.b64decode(self.encrypted_assessment_data.encode())
            decrypted = f.decrypt(encrypted_data).decode()
            return json.loads(decrypted)
        except Exception:
            return self.assessment_data or {}

    def save(self, *args, **kwargs):
        # Ensure encrypted payload is populated
        if (self.assessment_data or {}) and not self.encrypted_assessment_data:
            self.encrypted_assessment_data = self.encrypt_payload(self.assessment_data)
        # Normalize hospital name from related profile or user
        if not self.hospital_name:
            self.hospital_name = getattr(self.user, 'hospital_name', '') or (getattr(getattr(self.patient_profile, 'user', None), 'hospital_name', '') if self.patient_profile else '')
        super().save(*args, **kwargs)


class ArchiveAccessLog(models.Model):
    ACTION_CHOICES = [
        ('view', 'View'),
        ('export', 'Export'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('search', 'Search'),
    ]

    user = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, related_name="archive_access_logs")
    record = models.ForeignKey(PatientAssessmentArchive, on_delete=models.CASCADE, related_name="access_logs", null=True, blank=True)
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

    def __str__(self):
        rid = getattr(self.record, 'id', None)
        return f"Archive access: {self.action} by {getattr(self.user, 'email', 'system')} on {rid}"




class SecureKey(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='secure_keys')
    public_key_pem = models.TextField()
    algorithm = models.CharField(max_length=64, default='RSA-OAEP-2048-SHA256')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class SecureTransmission(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='sent_secure_transmissions')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='received_secure_transmissions')
    patient = models.ForeignKey(PatientProfile, on_delete=models.PROTECT, related_name='secure_transmissions')
    ciphertext_b64 = models.TextField()
    iv_b64 = models.CharField(max_length=64)
    encrypted_key_b64 = models.TextField()
    signature_b64 = models.TextField()
    signing_public_key_pem = models.TextField()
    checksum_hex = models.CharField(max_length=128)
    encryption_alg = models.CharField(max_length=64, default='AES-256-GCM')
    signature_alg = models.CharField(max_length=64, default='ECDSA-P256-SHA256')
    status = models.CharField(max_length=32, default='pending', choices=[('pending','pending'),('received','received'),('decrypted','decrypted'),('failed','failed')])
    created_at = models.DateTimeField(auto_now_add=True)
    accessed_at = models.DateTimeField(null=True, blank=True)
    breach_flag = models.BooleanField(default=False)
    breach_notified_at = models.DateTimeField(null=True, blank=True)


class TransmissionAudit(models.Model):
    transmission = models.ForeignKey('SecureTransmission', on_delete=models.CASCADE, related_name='audits')
    event = models.CharField(max_length=64)
    detail = models.TextField(blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class MFAChallenge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mfa_challenges')
    code = models.CharField(max_length=12)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
