from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.conf import settings
from django.db import models
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
import os
import csv
import io

from .models import AdminUser, VerificationRequest, SystemLog, Hospital
from .serializers import (
    AdminUserSerializer, AdminLoginSerializer, AdminRegistrationSerializer, VerificationRequestSerializer,
    VerificationRequestUpdateSerializer, DeclineVerificationSerializer, SystemLogSerializer,
    HospitalSerializer, HospitalRegistrationSerializer, HospitalActivationSerializer
)
from .authentication import AdminJWTAuthentication
from backend.users.models import User


def log_admin_action(admin_user, action, target, target_id, details=""):
    """Helper function to log admin actions."""
    SystemLog.objects.create(
        admin_user=admin_user,
        action=action,
        target=target,
        target_id=target_id,
        details=details
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def admin_overview(request):
    """
    Admin API overview - provides information about available endpoints
    """
    return Response({
        'message': 'MediSync Admin API',
        'version': '1.0.0',
        'endpoints': {
            'login': '/api/admin/login/',
            'dashboard_stats': '/api/admin/dashboard/stats/',
            'verifications': '/api/admin/verifications/',
            'system_logs': '/api/admin/logs/',
            'settings_profile': '/api/admin/settings/profile/',
            'settings_password': '/api/admin/settings/password/',
            'export_users': '/api/admin/users/export/',
        },
        'description': 'Administrative interface for managing user verifications and system operations'
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_csrf_token(request):
    """
    Get CSRF token for admin frontend and set it as a cookie so
    subsequent POST/PUT/PATCH/DELETE requests can include the token header.
    """
    from django.middleware.csrf import get_token
    csrf_token = get_token(request)
    # Return token in body and set CSRFTOKEN cookie
    response = Response({'csrf_token': csrf_token}, status=status.HTTP_200_OK)
    # Django expects the CSRF cookie name to be 'csrftoken'
    # Set samesite to 'Lax' to allow standard navigation requests
    response.set_cookie(
        'csrftoken',
        csrf_token,
        secure=False,  # set True if serving over HTTPS
        httponly=False,  # allow frontend to read cookie for X-CSRFToken header
        samesite='Lax'
    )
    return response


@api_view(['GET'])
@permission_classes([AllowAny])
def admin_config(request):
    """Expose configuration relevant to the admin frontend."""
    # Production-only: no testing mode, only official domain
    testing_mode = False
    allowed_domains = ['*.gov.ph', '*.edu.ph', 'gmail.com']
    banner_text = "Allowed: *.gov.ph, *.edu.ph, gmail.com"
    return Response({
        'testing_mode_enabled': testing_mode,
        'allowed_domains': allowed_domains,
        'banner_text': banner_text
    }, status=status.HTTP_200_OK)


# Admin Settings: Profile (GET/PATCH)
@api_view(['GET', 'PATCH'])
@authentication_classes([AdminJWTAuthentication])
@permission_classes([IsAuthenticated])
def admin_settings_profile(request):
    """
    Get or update admin profile settings.
    GET: returns name, email, hospital name.
    PATCH: allows updating full_name, email, hospital_name, and hospital_address (if hospital exists).
    """
    if not isinstance(request.user, AdminUser):
        return Response({'error': 'Access denied. Admin privileges required.'}, status=status.HTTP_403_FORBIDDEN)

    admin_user = request.user

    if request.method == 'GET':
        hospital = admin_user.hospital
        return Response({
            'full_name': admin_user.full_name,
            'email': admin_user.email,
            'hospital': {
                'id': hospital.id if hospital else None,
                'official_name': hospital.official_name if hospital else None,
                'address': hospital.address if hospital else None,
            }
        }, status=status.HTTP_200_OK)

    # PATCH
    payload = request.data or {}
    updated = {}

    full_name = (payload.get('full_name') or '').strip()
    email = (payload.get('email') or '').strip()
    hospital_name = (payload.get('hospital_name') or '').strip()
    hospital_address = (payload.get('hospital_address') or '').strip()

    try:
        if full_name:
            admin_user.full_name = full_name
            updated['full_name'] = full_name

        if email:
            # basic validation: ensure unique
            if AdminUser.objects.exclude(id=admin_user.id).filter(email=email).exists():
                return Response({'error': 'Email already in use.'}, status=status.HTTP_400_BAD_REQUEST)
            admin_user.email = email
            updated['email'] = email

        if admin_user.hospital:
            if hospital_name:
                admin_user.hospital.official_name = hospital_name
                updated['hospital_name'] = hospital_name
            if hospital_address:
                admin_user.hospital.address = hospital_address
                updated['hospital_address'] = hospital_address
            if hospital_name or hospital_address:
                admin_user.hospital.save()

        admin_user.save()
        return Response({'message': 'Settings updated successfully', 'updated': updated}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': f'Failed to update settings: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Admin Settings: Password change
@api_view(['POST'])
@authentication_classes([AdminJWTAuthentication])
@permission_classes([IsAuthenticated])
def admin_change_password(request):
    """Change admin user password given current and new password."""
    if not isinstance(request.user, AdminUser):
        return Response({'error': 'Access denied. Admin privileges required.'}, status=status.HTTP_403_FORBIDDEN)

    current_password = request.data.get('current_password') or ''
    new_password = request.data.get('new_password') or ''

    if not current_password or not new_password:
        return Response({'error': 'current_password and new_password are required.'}, status=status.HTTP_400_BAD_REQUEST)

    if not request.user.check_password(current_password):
        return Response({'error': 'Current password is incorrect.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        request.user.set_password(new_password)
        request.user.save()
        return Response({'message': 'Password updated successfully.'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': f'Failed to update password: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Export all registered users (Super Admin only)
@api_view(['GET'])
@authentication_classes([AdminJWTAuthentication])
@permission_classes([IsAuthenticated])
def export_all_users(request):
    """
    Export all registered users as CSV. Super Admin only.
    Includes key profile fields for admin reporting.
    """
    if not isinstance(request.user, AdminUser):
        return Response({'error': 'Access denied. Admin privileges required.'}, status=status.HTTP_403_FORBIDDEN)
    if not request.user.is_super_admin:
        return Response({'error': 'Export permitted for Super Admin only.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        users = User.objects.all().order_by('date_joined')

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'email', 'full_name', 'role', 'date_of_birth', 'gender',
            'hospital_name', 'hospital_address', 'is_verified', 'verification_status',
            'date_joined', 'updated_at'
        ])

        for u in users:
            writer.writerow([
                u.email,
                getattr(u, 'full_name', ''),
                getattr(u, 'role', ''),
                getattr(u, 'date_of_birth', ''),
                getattr(u, 'gender', ''),
                getattr(u, 'hospital_name', ''),
                getattr(u, 'hospital_address', ''),
                getattr(u, 'is_verified', False),
                getattr(u, 'verification_status', ''),
                getattr(u, 'date_joined', ''),
                getattr(u, 'updated_at', ''),
            ])

        csv_bytes = output.getvalue().encode('utf-8')
        filename = f"users_export_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response = FileResponse(io.BytesIO(csv_bytes), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        return Response({'error': f'Failed to export users: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# List users registered in admin's hospital (Admin only)
@api_view(['GET'])
@authentication_classes([AdminJWTAuthentication])
@permission_classes([IsAuthenticated])
def hospital_users(request):
    """
    Return users registered in the admin's active hospital.
    Supports optional query params:
    - search: filter by name/email/role
    - verified_only: '1' or 'true' to include only admin-verified users
    """
    admin_user = request.user
    if not isinstance(admin_user, AdminUser):
        return Response({'error': 'Access denied. Admin privileges required.'}, status=status.HTTP_403_FORBIDDEN)

    # Ensure admin has an ACTIVE hospital
    if not admin_user.can_access_admin_functions():
        return Response({
            'error': 'Admin hospital missing or inactive.',
            'resolution': 'Complete hospital registration/activation to access hospital users.'
        }, status=status.HTTP_403_FORBIDDEN)

    try:
        search = (request.GET.get('search') or '').strip()
        verified_only = (request.GET.get('verified_only') or '').strip().lower() in ('1', 'true', 'yes')

        # Match by hospital official name AND address to align with user.hospital_* storage
        hospital_name = (getattr(admin_user.hospital, 'official_name', '') or '').strip()
        hospital_address = (getattr(admin_user.hospital, 'address', '') or '').strip()
        if not hospital_name or not hospital_address:
            return Response({'users': [], 'message': 'Hospital name/address missing on admin record.'}, status=status.HTTP_200_OK)

        # Use case-insensitive exact match on both fields to avoid stale name-only mismatches
        queryset = User.objects.filter(
            is_active=True,
            hospital_name__iexact=hospital_name,
            hospital_address__iexact=hospital_address
        )
        if verified_only:
            queryset = queryset.filter(is_verified=True, verification_status='approved')
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(full_name__icontains=search) |
                Q(email__icontains=search) |
                Q(role__icontains=search)
            )

        # Select fields to return
        users = list(queryset.order_by('full_name').values(
            'id', 'email', 'full_name', 'role', 'is_verified', 'verification_status', 'date_joined'
        ))

        # Log action (non-fatal on failure)
        try:
            log_admin_action(admin_user, 'FETCH_HOSPITAL_USERS', 'User', 0, f"count={len(users)} verified_only={verified_only}")
        except Exception:
            pass

        return Response({'users': users, 'total_count': len(users)}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': f'Failed to fetch hospital users: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def admin_login(request):
    """
    Admin login endpoint
    """
    serializer = AdminLoginSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        # Use the custom AdminUserBackend for authentication
        from .backends import AdminUserBackend
        backend = AdminUserBackend()
        user = backend.authenticate(request, email=email, password=password)
        
        if user and isinstance(user, AdminUser):
            if not user.is_active:
                return Response({
                    'error': 'Account is deactivated.'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Check if email is verified
            if not user.is_email_verified:
                return Response({
                    'error': 'Email not verified.',
                    'message': 'Please verify your email address before logging in.'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Check hospital registration status
            hospital_registration_required = not user.hospital_registration_completed
            hospital_data = None
            if user.hospital:
                hospital_data = HospitalSerializer(user.hospital).data
            
            response_data = {
                'message': 'Login successful',
                'admin_user': AdminUserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'hospital_registration_required': hospital_registration_required,
                'hospital': hospital_data
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Invalid credentials.',
                'message': 'Email or password is incorrect.'
            }, status=status.HTTP_401_UNAUTHORIZED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def admin_register(request):
    """
    Admin registration endpoint with email verification
    """
    serializer = AdminRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        try:
            # Create admin user
            admin_user = AdminUser.objects.create_user(
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password'],
                full_name=serializer.validated_data['full_name'],
                is_super_admin=serializer.validated_data.get('is_super_admin', False)
            )
            
            # Generate email verification token
            from django.utils import timezone
            import uuid
            
            verification_token = str(uuid.uuid4())
            admin_user.email_verification_token = verification_token
            admin_user.email_verification_sent_at = timezone.now()
            admin_user.save()
            
            # Send verification email
            send_verification_email(admin_user, verification_token)
            
            return Response({
                'message': 'Admin account created successfully. Please check your email for verification.',
                'admin_user': {
                    'id': admin_user.id,
                    'email': admin_user.email,
                    'full_name': admin_user.full_name,
                    'is_email_verified': admin_user.is_email_verified
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': f'Failed to create admin account: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_admin_email(request):
    """
    Verify admin email with token
    """
    token = request.data.get('token')
    if not token:
        return Response({
            'error': 'Verification token is required.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        admin_user = AdminUser.objects.get(email_verification_token=token)
        
        # Check if token is expired (24 hours)
        from django.utils import timezone
        from datetime import timedelta
        
        if admin_user.email_verification_sent_at:
            if timezone.now() - admin_user.email_verification_sent_at > timedelta(hours=24):
                return Response({
                    'error': 'Verification token has expired. Please request a new one.'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify email
        admin_user.is_email_verified = True
        admin_user.email_verification_token = None
        admin_user.email_verification_sent_at = None
        admin_user.save()
        
        return Response({
            'message': 'Email verified successfully. You can now login.',
            'admin_user': AdminUserSerializer(admin_user).data
        }, status=status.HTTP_200_OK)
        
    except AdminUser.DoesNotExist:
        return Response({
            'error': 'Invalid verification token.'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'error': f'Failed to verify email: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def resend_verification_email(request):
    """
    Resend verification email
    """
    email = request.data.get('email')
    if not email:
        return Response({
            'error': 'Email is required.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        admin_user = AdminUser.objects.get(email=email)
        
        if admin_user.is_email_verified:
            return Response({
                'error': 'Email is already verified.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate new verification token
        from django.utils import timezone
        import uuid
        
        verification_token = str(uuid.uuid4())
        admin_user.email_verification_token = verification_token
        admin_user.email_verification_sent_at = timezone.now()
        admin_user.save()
        
        # Send verification email
        send_verification_email(admin_user, verification_token)
        
        return Response({
            'message': 'Verification email sent successfully.'
        }, status=status.HTTP_200_OK)
        
    except AdminUser.DoesNotExist:
        return Response({
            'error': 'Admin user not found.'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Failed to resend verification email: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def admin_token_refresh(request):
    """
    Admin token refresh endpoint
    """
    try:
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({
                'error': 'Refresh token is required.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Decode and verify the refresh token
        refresh = RefreshToken(refresh_token)
        
        # Get the user from the token
        user_id = refresh.payload.get('user_id')
        try:
            user = AdminUser.objects.get(id=user_id)
        except AdminUser.DoesNotExist:
            return Response({
                'error': 'Invalid refresh token.'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Generate new access token
        new_access_token = refresh.access_token
        
        return Response({
            'access': str(new_access_token),
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': 'Invalid refresh token.'
        }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET'])
@authentication_classes([AdminJWTAuthentication])
@permission_classes([IsAuthenticated])
def admin_dashboard_stats(request):
    """
    Get dashboard statistics
    """
    if not isinstance(request.user, AdminUser):
        return Response({
            'error': 'Access denied. Admin privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    stats = {
        'pending': VerificationRequest.objects.filter(status='pending').count(),
        'approved': VerificationRequest.objects.filter(status='approved').count(),
        'declined': VerificationRequest.objects.filter(status='declined').count(),
        'archived': VerificationRequest.objects.filter(status='archived').count(),
        'total': VerificationRequest.objects.count(),
    }
    
    return Response(stats, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([AdminJWTAuthentication])
@permission_classes([IsAuthenticated])
def verification_requests_list(request):
    """
    Get all verification requests with filtering
    """
    if not isinstance(request.user, AdminUser):
        return Response({
            'error': 'Access denied. Admin privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Get query parameters for filtering
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    
    queryset = VerificationRequest.objects.all()
    
    # Filter by status
    if status_filter and status_filter != 'all':
        queryset = queryset.filter(status=status_filter)
    
    # Filter by search query
    if search_query:
        queryset = queryset.filter(
            models.Q(user_full_name__icontains=search_query) |
            models.Q(user_email__icontains=search_query)
        )
    
    # Order by submitted date (newest first)
    queryset = queryset.order_by('-submitted_at')
    
    serializer = VerificationRequestSerializer(queryset, many=True)
    
    return Response({
        'verifications': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@authentication_classes([AdminJWTAuthentication])
@permission_classes([IsAuthenticated])
def accept_verification(request, verification_id):
    """
    Accept a verification request
    """
    if not isinstance(request.user, AdminUser):
        return Response({
            'error': 'Access denied. Admin privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        verification = VerificationRequest.objects.get(id=verification_id)
        
        # Cross-check hospital details for medical staff
        if verification.user_role in ['doctor', 'nurse']:
            try:
                from backend.users.models import User
                user = User.objects.get(email=verification.user_email)
            except User.DoesNotExist:
                return Response({
                    'error': 'User not found for verification'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Ensure user has hospital info
            if not user.hospital_name or not user.hospital_address:
                return Response({
                    'error': 'User registration missing hospital information.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Find matching hospital record
            hospital_match = Hospital.objects.filter(
                official_name=user.hospital_name.strip(),
                address=user.hospital_address.strip(),
                status=Hospital.Status.ACTIVE
            ).first()
            if not hospital_match:
                # Log mismatch and return error
                log_admin_action(
                    request.user,
                    'approve_verification_failed',
                    'verification_request',
                    verification_id,
                    f"Hospital mismatch or inactive for {verification.user_email}: {user.hospital_name} / {user.hospital_address}"
                )
                return Response({
                    'error': 'Hospital mismatch: user hospital does not match an active hospital record.'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        verification.approve(request.user)
        
        # Log the action
        log_admin_action(
            request.user, 
            'approve_verification', 
            'verification_request', 
            verification_id,
            f"Approved verification for {verification.user_email}"
        )
        
        # Send email notification to user
        try:
            subject = 'Verification Approved - MediSync'
            message = f"""
            Dear {verification.user_full_name},
            
            Your verification request has been approved! You can now access all features of your MediSync account.
            
            Thank you for your patience.
            
            Best regards,
            MediSync Admin Team
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [verification.user_email],
                fail_silently=False,
            )
        except Exception:
            pass
        
        return Response({
            'message': 'Verification approved successfully'
        }, status=status.HTTP_200_OK)
        
    except VerificationRequest.DoesNotExist:
        return Response({
            'error': 'Verification request not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@authentication_classes([AdminJWTAuthentication])
@permission_classes([IsAuthenticated])
def decline_verification(request, verification_id):
    """
    Decline a verification request
    """
    if not isinstance(request.user, AdminUser):
        return Response({
            'error': 'Access denied. Admin privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    serializer = DeclineVerificationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    reason = serializer.validated_data['reason']
    send_email = serializer.validated_data['send_email']
    
    try:
        verification = VerificationRequest.objects.get(id=verification_id)
        verification.decline(request.user, reason)
        
        # Log the action
        log_admin_action(
            request.user, 
            'decline_verification', 
            'verification_request', 
            verification_id,
            f"Declined verification for {verification.user_email}. Reason: {reason}"
        )
        
        # Send email notification to user if requested
        if send_email:
            try:
                subject = 'Verification Declined - MediSync'
                message = f"""
                Dear {verification.user_full_name},
                
                Your verification request has been declined for the following reason:
                
                {reason}
                
                Please review the requirements and submit a new verification request with the correct documentation.
                
                If you have any questions, please contact our support team.
                
                Best regards,
                MediSync Admin Team
                """
                
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [verification.user_email],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Failed to send decline email: {e}")
        
        return Response({
            'message': 'Verification declined successfully'
        }, status=status.HTTP_200_OK)
        
    except VerificationRequest.DoesNotExist:
        return Response({
            'error': 'Verification request not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@authentication_classes([AdminJWTAuthentication])
@permission_classes([IsAuthenticated])
def archive_verification(request, verification_id):
    """
    Archive a verification request
    """
    if not isinstance(request.user, AdminUser):
        return Response({
            'error': 'Access denied. Admin privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        verification = VerificationRequest.objects.get(id=verification_id)
        verification.archive(request.user)
        
        # Log the action
        log_admin_action(
            request.user, 
            'archive_verification', 
            'verification_request', 
            verification_id,
            f"Archived verification for {verification.user_email}"
        )
        
        return Response({
            'message': 'Verification archived successfully'
        }, status=status.HTTP_200_OK)
        
    except VerificationRequest.DoesNotExist:
        return Response({
            'error': 'Verification request not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['PUT'])
@authentication_classes([AdminJWTAuthentication])
@permission_classes([IsAuthenticated])
def update_verification(request, verification_id):
    """
    Update verification request details
    """
    if not isinstance(request.user, AdminUser):
        return Response({
            'error': 'Access denied. Admin privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        verification = VerificationRequest.objects.get(id=verification_id)
        serializer = VerificationRequestUpdateSerializer(verification, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            
            # Log the action
            log_admin_action(
                request.user, 
                'update_verification', 
                'verification_request', 
                verification_id,
                f"Updated verification for {verification.user_email}"
            )
            
            return Response({
                'message': 'Verification updated successfully',
                'verification': VerificationRequestSerializer(verification).data
            }, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
    except VerificationRequest.DoesNotExist:
        return Response({
            'error': 'Verification request not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@authentication_classes([AdminJWTAuthentication])
@permission_classes([IsAuthenticated])
def admin_my_hospitals(request):
    admin_user = request.user
    try:
        # Ensure the user is an AdminUser
        if not isinstance(admin_user, AdminUser):
            return Response({'error': 'Access denied. Admin account required.'}, status=status.HTTP_403_FORBIDDEN)

        status_filter = (request.GET.get('status') or '').strip().lower()
        # Default to ACTIVE when no explicit filter is provided
        queryset = Hospital.objects.filter(admin_users__id=admin_user.id)
        if not status_filter:
            status_filter = 'active'
        if status_filter in ['pending', 'active', 'suspended']:
            queryset = queryset.filter(status=status_filter)
        else:
            return Response({'error': 'Invalid status filter. Use pending, active, or suspended.'}, status=status.HTTP_400_BAD_REQUEST)

        hospitals = list(
            queryset.order_by('official_name').values('id', 'official_name', 'address')
        )

        # Log the fetch operation with count
        try:
            log_admin_action(
                admin_user=admin_user,
                action='FETCH_ADMIN_HOSPITALS',
                target='Hospital',
                target_id=0,
                details=f"status={status_filter}, count={len(hospitals)}"
            )
        except Exception:
            # Avoid breaking the response if logging fails
            pass

        if not hospitals:
            return Response({'hospitals': [], 'message': 'No hospitals found for admin.'}, status=status.HTTP_200_OK)
        return Response({'hospitals': hospitals}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': f'Failed to fetch hospitals: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@authentication_classes([AdminJWTAuthentication])
@permission_classes([IsAuthenticated])
def verify_hospital_selection(request):
    try:
        admin_user = request.user
        hospital_id = int(request.data.get('hospital_id', 0))
        if not hospital_id:
            return Response({'error': 'hospital_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        # Ensure selected hospital belongs to current admin and is ACTIVE
        hospital = Hospital.objects.filter(id=hospital_id, admin_users__id=admin_user.id, status=Hospital.Status.ACTIVE).first()
        if not hospital:
            return Response({'authorized': False, 'error': 'Unauthorized hospital selection'}, status=status.HTTP_403_FORBIDDEN)
        return Response({'authorized': True, 'hospital': {
            'id': hospital.id,
            'official_name': hospital.official_name,
            'address': hospital.address
        }}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': f'Validation failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@authentication_classes([AdminJWTAuthentication])
@permission_classes([IsAuthenticated])
def system_logs(request):
    """
    Get system logs for audit purposes
    """
    if not isinstance(request.user, AdminUser):
        return Response({
            'error': 'Access denied. Admin privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Only super admins can view logs
    if not request.user.is_super_admin:
        return Response({
            'error': 'Access denied. Super admin privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    logs = SystemLog.objects.all()[:100]  # Limit to last 100 logs
    serializer = SystemLogSerializer(logs, many=True)
    
    return Response({
        'logs': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([AdminJWTAuthentication])
@permission_classes([IsAuthenticated])
def serve_verification_document(request, verification_id):
    """
    Serve verification document with appropriate headers for iframe embedding,
    enforcing admin access privileges and hospital linkage for medical staff.
    """
    try:
        import mimetypes
        from django.db import DatabaseError

        # Ensure caller is an AdminUser
        if not isinstance(request.user, AdminUser):
            return Response({
                'error': 'Access denied. Admin privileges required.',
                'resolution': 'Log in as an admin user to access verification documents.'
            }, status=status.HTTP_403_FORBIDDEN)

        # Verify admin is eligible to access admin functions
        if not (request.user.is_super_admin or request.user.can_access_admin_functions()):
            log_admin_action(
                request.user,
                'serve_document_failed',
                'verification_request',
                verification_id,
                'Admin does not have active hospital or registration completed.'
            )
            return Response({
                'error': 'Admin lacks required hospital registration or hospital is inactive.',
                'resolution': 'Complete hospital registration and ensure hospital status is ACTIVE.'
            }, status=status.HTTP_403_FORBIDDEN)

        verification = get_object_or_404(VerificationRequest, id=verification_id)

        # For doctor/nurse, enforce that user belongs to the admin’s active hospital
        if verification.user_role in ['doctor', 'nurse']:
            try:
                from backend.users.models import User
                user = User.objects.get(email=verification.user_email)
            except User.DoesNotExist:
                log_admin_action(
                    request.user,
                    'serve_document_failed',
                    'verification_request',
                    verification_id,
                    f"User not found for email {verification.user_email}"
                )
                return Response({
                    'error': 'User not found for verification.',
                    'resolution': 'Confirm the user exists in the main app and retry.'
                }, status=status.HTTP_404_NOT_FOUND)
            except DatabaseError as db_err:
                log_admin_action(
                    request.user,
                    'serve_document_failed',
                    'verification_request',
                    verification_id,
                    f"Database error retrieving user: {str(db_err)}"
                )
                return Response({
                    'error': 'Database connectivity issue while retrieving user record.',
                    'resolution': 'Check database availability and admin app DB connections.'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

            admin_hospital = request.user.hospital
            if not admin_hospital or admin_hospital.status != Hospital.Status.ACTIVE:
                log_admin_action(
                    request.user,
                    'serve_document_failed',
                    'verification_request',
                    verification_id,
                    'Admin hospital missing or inactive.'
                )
                return Response({
                    'error': 'Admin hospital is missing or inactive.',
                    'resolution': 'Assign an ACTIVE hospital to the admin and retry.'
                }, status=status.HTTP_403_FORBIDDEN)

            user_hospital_name = (user.hospital_name or '').strip()
            user_hospital_address = (user.hospital_address or '').strip()
            if not user_hospital_name or not user_hospital_address:
                log_admin_action(
                    request.user,
                    'serve_document_failed',
                    'verification_request',
                    verification_id,
                    'User registration missing hospital information.'
                )
                return Response({
                    'error': 'User registration missing hospital information.',
                    'resolution': 'Ensure user hospital name and address are provided during registration.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Require that the user’s hospital matches the admin’s active hospital
            if not (
                user_hospital_name == admin_hospital.official_name.strip() and
                user_hospital_address == admin_hospital.address.strip()
            ):
                log_admin_action(
                    request.user,
                    'serve_document_failed',
                    'verification_request',
                    verification_id,
                    f"Hospital mismatch for {verification.user_email}: user={user_hospital_name} | {user_hospital_address} vs admin={admin_hospital.official_name} | {admin_hospital.address}"
                )
                return Response({
                    'error': 'Hospital mismatch: admin hospital does not match user registration hospital.',
                    'resolution': 'Switch to the matching hospital or correct the user’s hospital details.'
                }, status=status.HTTP_403_FORBIDDEN)

        # Document existence validations
        file_field = verification.verification_document
        if not file_field or not getattr(file_field, 'name', None):
            log_admin_action(
                request.user,
                'serve_document_failed',
                'verification_request',
                verification_id,
                'Verification document not present on request.'
            )
            return Response({'error': 'Document not found', 'resolution': 'Ask the user to re-upload the document.'}, status=status.HTTP_404_NOT_FOUND)

        # Ensure the file exists in storage
        storage = file_field.storage
        file_name = file_field.name
        if not storage.exists(file_name):
            log_admin_action(
                request.user,
                'serve_document_failed',
                'verification_request',
                verification_id,
                f'File missing in storage: {file_name}'
            )
            return Response({'error': 'File not found on storage', 'resolution': 'Verify storage configuration and file paths.'}, status=status.HTTP_404_NOT_FOUND)

        # Guess content type based on file name; fallback to octet-stream
        guessed_type, _ = mimetypes.guess_type(file_name)
        content_type = guessed_type or 'application/octet-stream'

        # Open via storage to support non-local backends
        file_handle = storage.open(file_name, 'rb')
        response = FileResponse(file_handle, content_type=content_type)
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(file_name)}"'

        # Allow iframe embedding explicitly (in addition to global settings)
        response['X-Frame-Options'] = 'ALLOWALL'

        # CORS headers for admin frontend previews
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET'
        response['Access-Control-Allow-Headers'] = '*'

        # Log success
        log_admin_action(
            request.user,
            'serve_document',
            'verification_request',
            verification_id,
            f"Served document {os.path.basename(file_name)} with content-type {content_type}"
        )

        return response
        
    except Exception as e:
        print(f"Error serving document for verification {verification_id}: {str(e)}")
        # Attempt to log the error if user context is available
        try:
            if isinstance(request.user, AdminUser):
                log_admin_action(
                    request.user,
                    'serve_document_failed',
                    'verification_request',
                    verification_id,
                    f"Unhandled exception: {str(e)}"
                )
        except Exception:
            pass
        return Response({
            'error': 'Failed to serve document due to an unexpected error.',
            'resolution': 'Check server logs for details and verify storage/DB configurations.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def send_verification_email(admin_user, verification_token):
    """
    Send email verification email to admin user
    """
    try:
        # Create verification URL
        verification_url = f"{settings.FRONTEND_URL}/verify-email.html?token={verification_token}"
        
        # Email subject and content
        subject = 'MediSync Admin - Email Verification Required'
        
        # HTML email template
        html_message = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: #286660; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0;">
                    <h1 style="margin: 0; font-size: 24px;">MediSync Admin</h1>
                    <p style="margin: 10px 0 0 0; opacity: 0.9;">Healthcare Management System</p>
                </div>
                
                <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; border: 1px solid #e9ecef;">
                    <h2 style="color: #286660; margin-top: 0;">Email Verification Required</h2>
                    
                    <p>Hello {admin_user.full_name},</p>
                    
                    <p>Thank you for registering as an administrator for MediSync. To complete your account setup, please verify your email address by clicking the button below:</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{verification_url}" 
                           style="background: #286660; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: bold;">
                            Verify Email Address
                        </a>
                    </div>
                    
                    <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                    <p style="background: #e9ecef; padding: 10px; border-radius: 4px; word-break: break-all; font-family: monospace;">
                        {verification_url}
                    </p>
                    
                    <p><strong>Important:</strong> This verification link will expire in 24 hours for security reasons.</p>
                    
                    <p>If you didn't create this account, please ignore this email.</p>
                    
                    <hr style="border: none; border-top: 1px solid #e9ecef; margin: 30px 0;">
                    
                    <p style="font-size: 14px; color: #666; margin: 0;">
                        Best regards,<br>
                        The MediSync Team
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        plain_message = f"""
        MediSync Admin - Email Verification Required
        
        Hello {admin_user.full_name},
        
        Thank you for registering as an administrator for MediSync. To complete your account setup, please verify your email address by visiting the following link:
        
        {verification_url}
        
        Important: This verification link will expire in 24 hours for security reasons.
        
        If you didn't create this account, please ignore this email.
        
        Best regards,
        The MediSync Team
        """
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin_user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        print(f"Verification email sent to {admin_user.email}")
        
    except Exception as e:
        print(f"Failed to send verification email to {admin_user.email}: {e}")
        raise e


# Hospital Registration Views

@api_view(['POST'])
@authentication_classes([AdminJWTAuthentication])
@permission_classes([IsAuthenticated])
def hospital_registration(request):
    """
    Handle hospital registration form submission
    """
    admin_user = request.user
    
    # Check if user already has a hospital registered
    if admin_user.hospital_registration_completed:
        return Response({
            'error': 'Hospital registration already completed'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = HospitalRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        try:
            # Create hospital instance
            hospital = serializer.save()
            
            # Link hospital to admin user
            admin_user.hospital = hospital
            admin_user.save()
            
            # Log the action
            log_admin_action(
                admin_user=admin_user,
                action="HOSPITAL_REGISTRATION",
                target="Hospital",
                target_id=hospital.id,
                details=f"Hospital '{hospital.official_name}' registered"
            )
            
            return Response({
                'message': 'Hospital registration successful. Please proceed to activation.',
                'hospital': HospitalSerializer(hospital).data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': f'Hospital registration failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([AdminJWTAuthentication])
@permission_classes([IsAuthenticated])
def hospital_activation(request):
    """
    Handle hospital self-verification and activation
    """
    admin_user = request.user
    
    # Check if user has a hospital to activate
    if not admin_user.hospital:
        return Response({
            'error': 'No hospital found for activation'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if already activated
    if admin_user.hospital.status == Hospital.Status.ACTIVE:
        return Response({
            'error': 'Hospital is already active'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = HospitalActivationSerializer(data=request.data)
    if serializer.is_valid():
        try:
            # Activate hospital
            hospital = admin_user.hospital
            hospital.status = Hospital.Status.ACTIVE
            hospital.activated_at = timezone.now()
            hospital.save()

            # Mark registration as completed
            admin_user.hospital_registration_completed = True
            admin_user.save()

            # Log the action
            log_admin_action(
                admin_user=admin_user,
                action="HOSPITAL_ACTIVATION",
                target="Hospital",
                target_id=hospital.id,
                details=f"Hospital '{hospital.official_name}' activated"
            )

            # Re-fetch to ensure persistence
            persisted = Hospital.objects.get(id=hospital.id)
            if persisted.status != Hospital.Status.ACTIVE:
                print(f"[hospital_activation] Persistence check failed for hospital {hospital.id}")
                return Response({
                    'error': 'Activation did not persist. Please retry or contact support.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response({
                'message': 'Hospital activated successfully. You now have full admin access.',
                'hospital': HospitalSerializer(hospital).data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Hospital activation failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([AdminJWTAuthentication])
@permission_classes([IsAuthenticated])
def hospital_status(request):
    """
    Get current hospital registration and activation status
    """
    admin_user = request.user
    
    response_data = {
        'hospital_registration_completed': admin_user.hospital_registration_completed,
        'can_access_admin_functions': admin_user.can_access_admin_functions(),
        'hospital': None
    }
    
    if admin_user.hospital:
        response_data['hospital'] = HospitalSerializer(admin_user.hospital).data
    
    return Response(response_data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def hospitals_list(request):
    """
    List hospitals with optional status filter. Defaults to returning ACTIVE hospitals.
    Returns a distinct set of hospitals to avoid duplicates in dropdowns.
    """
    try:
        status_filter = (request.GET.get('status') or '').strip().lower()
        if not status_filter:
            status_filter = 'active'

        if status_filter not in ['pending', 'active', 'suspended']:
            return Response({'error': 'Invalid status filter. Use pending, active, or suspended.'}, status=status.HTTP_400_BAD_REQUEST)

        # Verify database connectivity by performing a count first
        total_count = Hospital.objects.count()

        queryset = Hospital.objects.filter(status__iexact=status_filter)
        # Use values + distinct to ensure unique rows by id/name/address
        rows = queryset.values('id', 'official_name', 'address').order_by('official_name', 'id').distinct()
        data = list(rows)

        # Lightweight server-side log for troubleshooting
        print(f"[hospitals_list] status={status_filter}, total={total_count}, returned={len(data)}")

        return Response({'hospitals': data}, status=status.HTTP_200_OK)
    except Exception as e:
        print(f"[hospitals_list] ERROR: {e}")
        return Response({'error': f'Failed to fetch hospitals: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
