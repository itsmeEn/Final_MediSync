from django.contrib import admin
from .models import (
    Notification,
    QueueManagement,
    PainAssessment
)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('user__full_name', 'message')

@admin.register(QueueManagement)
class QueueManagementAdmin(admin.ModelAdmin):
    list_display = ('queue_number', 'patient', 'department', 'status', 'created_at')
    list_filter = ('department', 'status')
    search_fields = ('patient__user__full_name', 'queue_number')

@admin.register(PainAssessment)
class PainAssessmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'performed_by', 'pain_score', 'pain_label', 'created_at')
    list_filter = ('pain_score', 'created_at')
    search_fields = ('patient__user__full_name', 'notes')
    readonly_fields = ('pain_emoji', 'pain_label', 'created_at', 'updated_at')
