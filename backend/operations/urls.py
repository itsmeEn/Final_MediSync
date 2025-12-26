from django.urls import path
from . import views
from .archive_views import archive_list, archive_detail, archive_create, archive_export, archive_logs, archive_update, archive_unarchive
from . import secure_views
from . import monitoring_views
from .medical_request_views import (
    medical_requests, approve_medical_request, deliver_medical_request,
    reject_medical_request, upload_certificate, add_doctor_notes, mark_request_processing
)

urlpatterns = [
    # Dashboard statistics
    path('dashboard/stats/', views.doctor_dashboard_stats, name='doctor_dashboard_stats'),
    path('appointments/', views.doctor_appointments, name='doctor_appointments'),
    path('queue/patients/', views.doctor_queue_patients, name='doctor_queue_patients'),
    path('notifications/', views.doctor_notifications, name='doctor_notifications'),
    path('notifications/<int:notification_id>/mark-read/', views.mark_notification_as_read, name='mark_notification_as_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('patient-assessments/', views.patient_assessments, name='patient_assessments'),
    
    # Appointment management
    path('blocked-dates/', views.doctor_blocked_dates, name='doctor_blocked_dates'),
    path('block-date/', views.doctor_block_date, name='doctor_block_date'),
    path('create-appointment/', views.doctor_create_appointment, name='doctor_create_appointment'),
    path('appointments/schedule/', views.schedule_appointment, name='schedule_appointment'),
    path('appointments/<int:appointment_id>/reschedule/', views.reschedule_appointment, name='reschedule_appointment'),
    path('appointments/<int:appointment_id>/cancel/', views.cancel_appointment, name='cancel_appointment'),
    path('appointments/<int:appointment_id>/check-in/', views.check_in_appointment, name='check_in_appointment'),
    path('appointments/<int:appointment_id>/start/', views.start_consultation, name='start_consultation'),
    path('appointments/<int:appointment_id>/finish/', views.finish_consultation, name='finish_consultation'),
    path('appointments/<int:appointment_id>/notify-patient/', views.notify_patient_appointment, name='notify_patient_appointment'),
    path('patient/appointments/', views.patient_appointments, name='patient_appointments'),
    path('patient/dashboard/summary/', views.patient_dashboard_summary, name='patient_dashboard_summary'),
    
    # Messaging endpoints
    path('messaging/conversations/', views.get_conversations, name='get_conversations'),
    path('messaging/conversations/create/', views.create_conversation, name='create_conversation'),
    path('messaging/conversations/<int:conversation_id>/messages/', views.get_messages, name='get_messages'),
    path('messaging/conversations/<int:conversation_id>/send/', views.send_message, name='send_message'),
    path('messaging/messages/<int:message_id>/react/', views.add_reaction, name='add_reaction'),
    path('messaging/available-users/', views.get_available_users, name='get_available_users'),

    # Availability endpoints
    path('availability/doctors/free/', views.available_doctors_free, name='available_doctors_free'),
    path('availability/nurses/', views.available_nurses, name='available_nurses'),
    path('nurses/list/', views.nurses_list, name='nurses_list'),
    path('nurse/capacity/validate/', views.nurse_capacity_validate, name='nurse_capacity_validate'),
    
    # Message notification endpoints
    path('messaging/notifications/', views.get_message_notifications, name='get_message_notifications'),
    path('messaging/notifications/<int:notification_id>/mark-sent/', views.mark_notification_as_sent, name='mark_notification_as_sent'),
    path('messaging/messages/<int:message_id>/mark-read/', views.mark_message_as_read, name='mark_message_as_read'),
    
    # Medicine inventory endpoints
    path('medicine-inventory/', views.get_medicine_inventory, name='get_medicine_inventory'),
    path('medicine-inventory/add/', views.add_medicine, name='add_medicine'),
    path('medicine-inventory/<int:medicine_id>/update/', views.update_medicine, name='update_medicine'),
    path('medicine-inventory/<int:medicine_id>/dispense/', views.dispense_medicine, name='dispense_medicine'),
    path('medicine-inventory/<int:medicine_id>/delete/', views.delete_medicine, name='delete_medicine'),
    
    # Nurse queue endpoints
    path('nurse/queue/patients/', views.nurse_queue_patients, name='nurse_queue_patients'),
    path('nurse/queue/remove/', views.nurse_remove_from_queue, name='nurse_remove_from_queue'),
    path('nurse/queue/mark-served/', views.nurse_mark_served, name='nurse_mark_served'),
    
    # Doctor selection endpoints
    path('available-doctors/', views.get_available_doctors, name='get_available_doctors'),
    # Hospital-specific departments for patient scheduling
    path('hospital/departments/', views.hospital_departments, name='hospital_departments'),
    path('assign-patient/', views.assign_patient_to_doctor, name='assign_patient_to_doctor'),
    
    # Doctor assignment endpoints
    path('doctor/assignments/', views.get_doctor_assignments, name='get_doctor_assignments'),
    path('doctor/assignments/<int:assignment_id>/accept/', views.accept_assignment, name='accept_assignment'),
    path('doctor/assignments/<int:assignment_id>/consultation-notes/', views.consultation_notes, name='consultation_notes'),
    
    # Queue Management endpoints
    path('queue/schedules/', views.queue_schedules, name='queue_schedules'),
    path('queue/schedules/<int:schedule_id>/', views.queue_schedule_detail, name='queue_schedule_detail'),
    path('queue/status/', views.queue_status, name='queue_status'),
    path('queue/status/logs/', views.queue_status_logs, name='queue_status_logs'),
    path('queue/join/', views.join_queue, name='join_queue'),
    path('queue/availability/', views.check_queue_availability, name='check_queue_availability'),
    path('queue/start-processing/', views.start_queue_processing, name='start_queue_processing'),
    path('queue/notifications/confirm/', views.confirm_notification_delivery, name='confirm_notification_delivery'),

    # Archive endpoints
    path('archives/', archive_list, name='archive_list'),
    path('archives/create/', archive_create, name='archive_create'),
    path('archives/<int:archive_id>/', archive_detail, name='archive_detail'),
    path('archives/<int:archive_id>/update/', archive_update, name='archive_update'),
    path('archives/<int:archive_id>/unarchive/', archive_unarchive, name='archive_unarchive'),
    path('archives/<int:archive_id>/export/', archive_export, name='archive_export'),
    path('archives/logs/', archive_logs, name='archive_logs'),

    # Public UI config endpoint for connectivity probing
    path('ui-config/', views.ui_config, name='ui_config'),

    # Monitoring and verification endpoints
    path('client-log/', monitoring_views.client_log, name='client_log'),
    path('verification-status/', monitoring_views.verification_status, name='verification_status'),


]

urlpatterns += [
    path('secure/register-public-key/', secure_views.register_public_key),
    path('secure/doctor-public-key/<int:doctor_id>/', secure_views.get_doctor_public_key),
    path('secure/transmissions/', secure_views.create_secure_transmission),
    path('secure/transmissions/list/', secure_views.list_transmissions_for_doctor),
    path('secure/transmissions/<int:transmission_id>/', secure_views.get_transmission_detail),
    path('secure/transmissions/<int:transmission_id>/received/', secure_views.mark_transmission_accessed),
    path('secure/mfa/challenge/', secure_views.mfa_challenge),
    path('secure/mfa/verify/', secure_views.mfa_verify),
    path('secure/transmissions/<int:transmission_id>/breach/', secure_views.report_breach),
    path('secure/purge/medical-records/', secure_views.purge_medical_records),
]
