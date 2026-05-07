from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_overview, name='admin_overview'),
    path('config/', views.admin_config, name='admin_config'),
    path('login/', views.admin_login, name='admin_login'),
    path('register/', views.admin_register, name='admin_register'),
    path('token/refresh/', views.admin_token_refresh, name='admin_token_refresh'),
    path('csrf-token/', views.get_csrf_token, name='get_csrf_token'),
    path('verify-email/', views.verify_admin_email, name='verify_admin_email'),
    path('resend-verification/', views.resend_verification_email, name='resend_verification_email'),
    path('password-reset/request/', views.admin_password_reset_request, name='admin_password_reset_request'),
    path('password-reset/confirm/', views.admin_password_reset_confirm, name='admin_password_reset_confirm'),

    # Dashboard & Verifications
    path('dashboard/stats/', views.admin_dashboard_stats, name='admin_dashboard_stats'),
    path('verifications/', views.verification_requests_list, name='verification_requests_list'),
    path('verifications/<int:verification_id>/accept/', views.accept_verification, name='accept_verification'),
    path('verifications/<int:verification_id>/decline/', views.decline_verification, name='decline_verification'),
    path('verifications/<int:verification_id>/update/', views.update_verification, name='update_verification'),
    path('verifications/<int:verification_id>/document/', views.serve_verification_document, name='serve_verification_document'),
    
    # System Logs (Super Admin Only)
    path('logs/', views.system_logs, name='system_logs'),
    
    # Hospital Registration
    path('hospital/register/', views.hospital_registration, name='hospital_registration'),
    path('hospital/activate/', views.hospital_activation, name='hospital_activation'),
    path('hospital/status/', views.hospital_status, name='hospital_status'),
    # Hospitals list for frontend dropdown (public)
    path('hospitals/', views.hospitals_list, name='hospitals_list'),
    # Admin-scoped hospital endpoints
    path('my/hospitals/', views.admin_my_hospitals, name='admin_my_hospitals'),
    path('hospital/verify-selection/', views.verify_hospital_selection, name='verify_hospital_selection'),

    # Admin Settings & Export
    path('settings/profile/', views.admin_settings_profile, name='admin_settings_profile'),
    path('settings/password/', views.admin_change_password, name='admin_change_password'),
    path('users/export/', views.export_all_users, name='export_all_users'),
    path('users/hospital/', views.hospital_users, name='hospital_users'),
]
