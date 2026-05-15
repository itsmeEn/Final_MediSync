from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import json

User = get_user_model()

class PatientRecord(models.Model):
    """
    Stores patient medical records for analytics
    """
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='medical_records')
    date_of_admission = models.DateTimeField()
    medical_condition = models.CharField(max_length=200)
    age = models.IntegerField()
    gender = models.CharField(max_length=10, choices=[
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other')
    ])
    medication = models.CharField(max_length=200, blank=True, null=True)
    severity = models.CharField(max_length=50, choices=[
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Critical', 'Critical')
    ], default='Medium')
    treatment_outcome = models.CharField(max_length=50, choices=[
        ('Recovered', 'Recovered'),
        ('Ongoing', 'Ongoing'),
        ('Transferred', 'Transferred'),
        ('Deceased', 'Deceased')
    ], default='Ongoing')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date_of_admission']
        db_table = 'patient_records'
        verbose_name = 'Patient Record'
        verbose_name_plural = 'Patient Records'
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.medical_condition} ({self.date_of_admission.strftime('%Y-%m-%d')})"

class AnalyticsResult(models.Model):
    """
    Stores the results of predictive analytics runs
    """
    ANALYSIS_TYPES = [
        ('patient_health_trends', 'Patient Health Trends'),
        ('patient_demographics', 'Patient Demographics'),
        ('illness_prediction', 'Illness Prediction'),
        ('medication_analysis', 'Medication Analysis'),
        ('patient_volume_prediction', 'Patient Volume Prediction'),
        ('illness_surge_prediction', 'Illness Surge Prediction'),
        ('weekly_illness_forecast', 'Weekly Illness Forecast'),
        ('monthly_illness_forecast', 'Monthly Illness Forecast'),
        ('problem_checklist', 'Problem Checklist Analysis'),
        ('ai_insights', 'AI Insights'),
        ('full_analysis', 'Full Analysis'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    analysis_type = models.CharField(max_length=50, choices=ANALYSIS_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    results = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'analytics_results'
        verbose_name = 'Analytics Result'
        verbose_name_plural = 'Analytics Results'
    
    def __str__(self):
        return f"{self.get_analysis_type_display()} - {self.get_status_display()} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

class AnalyticsTask(models.Model):
    """
    Tracks background analytics tasks
    """
    task_id = models.CharField(max_length=255, unique=True)
    analysis_type = models.CharField(max_length=50, choices=AnalyticsResult.ANALYSIS_TYPES)
    status = models.CharField(max_length=20, choices=AnalyticsResult.STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    result = models.ForeignKey(AnalyticsResult, on_delete=models.CASCADE, null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'analytics_tasks'
        verbose_name = 'Analytics Task'
        verbose_name_plural = 'Analytics Tasks'
    
    def __str__(self):
        return f"Task {self.task_id} - {self.get_analysis_type_display()}"

class DataUpdateLog(models.Model):
    """
    Logs when data is updated to trigger analytics refresh
    """
    model_name = models.CharField(max_length=100)
    record_id = models.PositiveIntegerField()
    action = models.CharField(max_length=20, choices=[
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
    ])
    triggered_analytics = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'data_update_logs'
        verbose_name = 'Data Update Log'
        verbose_name_plural = 'Data Update Logs'
    
    def __str__(self):
        return f"{self.action} {self.model_name} #{self.record_id}"

class AnalyticsCache(models.Model):
    """
    Caches frequently accessed analytics results for performance
    """
    cache_key = models.CharField(max_length=255, unique=True)
    data = models.JSONField()
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'analytics_cache'
        verbose_name = 'Analytics Cache'
        verbose_name_plural = 'Analytics Cache'
    
    def __str__(self):
        return f"Cache: {self.cache_key}"
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at


class UsageEvent(models.Model):
    """
    Captures user and system usage events for analytics and telemetry.
    """
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    event_type = models.CharField(max_length=100)
    source = models.CharField(max_length=100, blank=True, null=True)
    session_id = models.CharField(max_length=255, blank=True, null=True)
    ip_address = models.CharField(max_length=64, blank=True, null=True)
    context = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'usage_events'
        indexes = [
            models.Index(fields=['event_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.event_type} by {getattr(self.user, 'username', 'anonymous')} at {self.created_at}"


class UptimePing(models.Model):
    """
    Stores uptime heartbeat pings for services, used to monitor availability.
    """
    STATUS_CHOICES = [
        ('up', 'Up'),
        ('down', 'Down'),
        ('degraded', 'Degraded'),
    ]

    service = models.CharField(max_length=100, default='web')
    region = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='up')
    latency_ms = models.IntegerField(blank=True, null=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'uptime_pings'
        indexes = [
            models.Index(fields=['service']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.service} {self.status} ({self.latency_ms}ms)"


class RiskAssessmentAuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=32)
    version = models.IntegerField()
    risk_assessment = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'risk_assessment_audit_logs'
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['role']),
            models.Index(fields=['version']),
        ]

    def __str__(self):
        return f"RiskAssessment v{self.version} by {self.role} at {self.created_at}"
