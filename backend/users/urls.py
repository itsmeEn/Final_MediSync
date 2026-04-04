from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    # API endpoints for authentication
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # Public list of doctor specializations (for registration dropdown)
    path('specializations/', views.list_specializations, name='list_specializations'),

    # API endpoints for user profiles
    path('profile/', views.get_user_profile, name='get_user_profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    # Removed: deprecated profile picture upload endpoint
    
    # Verification endpoints
    path('verification/upload/', views.upload_verification_document, name='upload_verification_document'),
    path('verification/verify-now/', views.verify_now, name='verify_now'),
    
    # Password reset endpoints
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/<str:uidb64>/<str:token>/', views.reset_password, name='reset_password'),
    
    # Two-Factor Authentication endpoints
    path('2fa/enable/', views.enable_2fa, name='enable_2fa'),
    path('2fa/verify/', views.verify_2fa, name='verify_2fa'),
    path('2fa/disable/', views.disable_2fa, name='disable_2fa'),
    path('2fa/login/verify/', views.verify_2fa_login, name='verify_2fa_login'),
    
    # Patient management endpoints
    path('doctor/patients/', views.get_doctor_patients, name='get_doctor_patients'),
    path('nurse/patients/', views.get_nurse_patients, name='get_nurse_patients'),

    # Nurse-centric forms CRUD endpoints
    path('nurse/patient/<int:patient_id>/forms/', views.nurse_patient_forms_overview, name='nurse_patient_forms_overview'),
    path('nurse/patient/<int:patient_id>/intake/', views.nurse_intake, name='nurse_intake'),
    path('nurse/patient/<int:patient_id>/flow-sheets/', views.nurse_flow_sheets, name='nurse_flow_sheets'),
    path('nurse/patient/<int:patient_id>/flow-sheets/<int:index>/', views.nurse_flow_sheets_update, name='nurse_flow_sheets_update'),
    path('nurse/patient/<int:patient_id>/mar/', views.nurse_mar_records, name='nurse_mar_records'),
    path('nurse/patient/<int:patient_id>/mar/<int:index>/', views.nurse_mar_update, name='nurse_mar_update'),
    path('nurse/patient/<int:patient_id>/education/', views.nurse_education_records, name='nurse_education_records'),
    path('nurse/patient/<int:patient_id>/education/<int:index>/', views.nurse_education_update, name='nurse_education_update'),
    path('nurse/patient/<int:patient_id>/discharge/', views.nurse_discharge_summary, name='nurse_discharge_summary'),
    path('nurse/patient/<int:patient_id>/psychiatric-opd/', views.nurse_psychiatric_opd_questionnaire, name='nurse_psychiatric_opd_questionnaire'),
    path('nurse/patient/<int:patient_id>/psychiatric-opd/submit/', views.nurse_psychiatric_opd_questionnaire_submit, name='nurse_psychiatric_opd_questionnaire_submit'),

    # Doctor-centric forms CRUD endpoints
    path('doctor/patient/<int:patient_id>/forms/', views.doctor_patient_forms_overview, name='doctor_patient_forms_overview'),
    path('doctor/patient/<int:patient_id>/nurse-intake/', views.doctor_nurse_intake, name='doctor_nurse_intake'),
    path('doctor/patient/<int:patient_id>/hp/', views.doctor_hp_forms, name='doctor_hp_forms'),
    path('doctor/patient/<int:patient_id>/hp/<int:index>/', views.doctor_hp_forms_update, name='doctor_hp_forms_update'),
    path('doctor/patient/<int:patient_id>/progress-notes/', views.doctor_progress_notes, name='doctor_progress_notes'),
    path('doctor/patient/<int:patient_id>/progress-notes/<int:index>/', views.doctor_progress_notes_update, name='doctor_progress_notes_update'),
    path('doctor/patient/<int:patient_id>/orders/', views.doctor_provider_orders, name='doctor_provider_orders'),
    path('doctor/patient/<int:patient_id>/orders/<int:index>/', views.doctor_provider_orders_update, name='doctor_provider_orders_update'),
    path('doctor/patient/<int:patient_id>/operative-reports/', views.doctor_operative_reports, name='doctor_operative_reports'),
    path('doctor/patient/<int:patient_id>/operative-reports/<int:index>/', views.doctor_operative_reports_update, name='doctor_operative_reports_update'),

]
