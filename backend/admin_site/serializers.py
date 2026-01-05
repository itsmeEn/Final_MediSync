from rest_framework import serializers
from django.core.validators import RegexValidator
import re
from django.conf import settings
from .models import AdminUser, VerificationRequest, SystemLog, Hospital


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminUser
        fields = ['id', 'email', 'full_name', 'is_super_admin', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class AdminRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = AdminUser
        fields = ['email', 'password', 'password_confirm', 'full_name']
        extra_kwargs = {
            'email': {'required': True},
            'full_name': {'required': True}
        }

    def validate_email(self, value):
        """Allow @*.gov.ph or @gmail.com; enforce uniqueness."""
        email = (value or '').strip().lower()
        if AdminUser.objects.filter(email=email).exists():
            raise serializers.ValidationError("An admin with this email already exists.")
        
        gov_ph_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]*\.gov\.ph$'
        gmail_pattern = r'^[a-zA-Z0-9._%+-]+@gmail\.com$'
        
        if not (re.match(gov_ph_pattern, email) or re.match(gmail_pattern, email)):
            raise serializers.ValidationError("Email must be @*.gov.ph or @gmail.com.")
        
        return email

    def validate(self, attrs):
        """Validate password confirmation"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords do not match.")
        return attrs
    
    def create(self, validated_data):
        """Create admin user"""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        admin_user = AdminUser.objects.create_user(
            password=password,
            is_super_admin=False,  # Set to False by default
            **validated_data
        )
        return admin_user


class VerificationRequestSerializer(serializers.ModelSerializer):
    reviewed_by = AdminUserSerializer(read_only=True)
    
    class Meta:
        model = VerificationRequest
        fields = [
            'id', 'user_email', 'user_full_name', 'user_role', 'status',
            'verification_document', 'submitted_at', 'reviewed_at',
            'reviewed_by', 'decline_reason', 'notes'
        ]
        read_only_fields = ['id', 'submitted_at', 'reviewed_at', 'reviewed_by']


class VerificationRequestUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationRequest
        fields = ['status', 'decline_reason', 'notes']


class DeclineVerificationSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True)
    send_email = serializers.BooleanField(default=True)


class SystemLogSerializer(serializers.ModelSerializer):
    admin_user = AdminUserSerializer(read_only=True)
    
    class Meta:
        model = SystemLog
        fields = ['id', 'admin_user', 'action', 'target', 'target_id', 'details', 'timestamp']
        read_only_fields = ['id', 'timestamp']


class HospitalSerializer(serializers.ModelSerializer):
    """Serializer for Hospital model"""
    
    class Meta:
        model = Hospital
        fields = [
            'id', 'official_name', 'address', 'license_id', 
            'license_document', 'status', 'created_at', 'activated_at'
        ]
        read_only_fields = ['id', 'status', 'created_at', 'activated_at']


class HospitalRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for hospital registration form"""
    
    class Meta:
        model = Hospital
        fields = ['official_name', 'address', 'license_id', 'license_document', 'logo']
        extra_kwargs = {
            'official_name': {'required': True},
            'address': {'required': True},
            'license_id': {'required': True},
            'license_document': {'required': True},
            'logo': {'required': True}
        }

    def validate_logo(self, value):
        """Validate logo file (size, type, and dimensions for raster images)"""
        if not value:
            raise serializers.ValidationError("Hospital logo is required.")
            
        # Check file size (max 2MB)
        if value.size > 2 * 1024 * 1024:
            raise serializers.ValidationError("Logo must be smaller than 2MB.")
            
        # Check file extension
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.svg']
        file_extension = value.name.lower().split('.')[-1]
        if f'.{file_extension}' not in allowed_extensions:
            raise serializers.ValidationError(
                "Logo must be a JPG, PNG, or SVG file."
            )
            
        # Image processing/validation for raster images
        if file_extension in ['jpg', 'jpeg', 'png']:
            try:
                from PIL import Image
                img = Image.open(value)
                img.verify()  # Verify it's an image
                
                # Check dimensions (optional recommendation enforcement, or just logging)
                # For now, we'll just ensure it's a valid image.
                # Actual resizing/cropping can happen in the save method or pre-save signal
                # but since this is a serializer, we can also modify the image here if needed,
                # though usually better to do it in a utility or model method.
                
                # Reset file pointer for subsequent reads
                value.seek(0)
            except Exception:
                raise serializers.ValidationError("Invalid image file.")
                
        return value

    def validate_license_id(self, value):
        """Validate license ID uniqueness"""
        if Hospital.objects.filter(license_id=value).exists():
            raise serializers.ValidationError("A hospital with this license ID already exists.")
        return value
    
    def validate_license_document(self, value):
        """Validate license document file"""
        if not value:
            raise serializers.ValidationError("License document is required.")
        
        # Check file size (max 10MB)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("License document must be smaller than 10MB.")
        
        # Check file extension
        allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx']
        file_extension = value.name.lower().split('.')[-1]
        if f'.{file_extension}' not in allowed_extensions:
            raise serializers.ValidationError(
                "License document must be a PDF, image, or document file."
            )
        
        return value


class HospitalActivationSerializer(serializers.Serializer):
    """Serializer for hospital self-verification and activation"""
    terms_accepted = serializers.BooleanField(required=True)
    data_verified = serializers.BooleanField(required=True)
    
    def validate_terms_accepted(self, value):
        """Ensure terms are accepted"""
        if not value:
            raise serializers.ValidationError("You must accept the terms to activate the hospital.")
        return value
    
    def validate_data_verified(self, value):
        """Ensure data is verified"""
        if not value:
            raise serializers.ValidationError("You must verify the data accuracy to activate the hospital.")
        return value
