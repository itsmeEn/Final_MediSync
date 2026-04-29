from rest_framework import serializers
from .models import User, GeneralDoctorProfile, NurseProfile, PatientProfile
from django.utils import timezone
# Removed image processing imports; profile picture uploads are deprecated
import re


class GeneralDoctorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneralDoctorProfile
        fields = "__all__"


class NurseProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = NurseProfile
        fields = "__all__"


class PatientProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientProfile
        fields = "__all__"
        read_only_fields = ["user"]


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model - used for general user data representation
    """
    doctor_profile = GeneralDoctorProfileSerializer(read_only=True)
    nurse_profile = NurseProfileSerializer(read_only=True)
    patient_profile = PatientProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'full_name', 'role', 'date_of_birth', 'gender',
            'hospital_name', 'hospital_address', 'is_verified', 'verification_status', 
            'profile_picture', 'verification_document', 'doctor_profile', 'nurse_profile', 
            'patient_profile', 'two_factor_enabled', 'date_joined', 'updated_at'
        ]
        read_only_fields = ['id', 'date_joined', 'updated_at', 'two_factor_enabled']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new users. It handles passwords and role-based
    validation.
    """
    password2 = serializers.CharField(style={"input_type": "password"}, write_only=True)
    license_number = serializers.CharField(required=False, write_only=True)
    specialization = serializers.CharField(required=False, write_only=True)
    department = serializers.CharField(required=False, write_only=True)
    # New: hospital selection is required; accept hospital_id from admin_site
    hospital_id = serializers.IntegerField(required=True, write_only=True)

    class Meta:
        model = User
        fields = [
            "email", "full_name", "role", "date_of_birth", "gender", 
            "password", "password2", "license_number", "specialization", "department",
            "verification_document", "hospital_id"
        ]
        extra_kwargs = {"password": {"write_only": True}}

    def validate_password(self, value):
        """
        Validate password requirements:
        - At least 8 characters long
        - Contains at least one letter and one number
        """
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        if not re.search(r'[A-Za-z]', value):
            raise serializers.ValidationError("Password must contain at least one letter.")
        if not re.search(r'\d', value):
            raise serializers.ValidationError("Password must contain at least one number.")
        return value

    def validate_email(self, value):
        """
        Validate email uniqueness
        """
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Password fields didn't match."})

        # ⚠️ Enforce role-based field requirements
        role = attrs.get('role')
        if role == 'doctor' and not (attrs.get('license_number') and attrs.get('specialization')):
            raise serializers.ValidationError({"role_fields": "License number and specialization are required for doctors."})
        if role == 'nurse' and not attrs.get('license_number'):
            raise serializers.ValidationError({"role_fields": "License number is required for nurses."})
        if role == 'nurse' and not attrs.get('department'):
            raise serializers.ValidationError({"role_fields": "Department is required for nurses."})

        # Hospital validation: require an ACTIVE hospital
        hospital_id = attrs.get('hospital_id')
        if not hospital_id:
            raise serializers.ValidationError({"hospital": "Please select your hospital."})
        # Avoid import path issues by using Django app registry
        from django.apps import apps
        Hospital = apps.get_model('admin_site', 'Hospital')
        try:
            hospital = Hospital.objects.get(id=hospital_id, status__iexact=Hospital.Status.ACTIVE)
        except Hospital.DoesNotExist:
            raise serializers.ValidationError({"hospital": "Selected hospital is not active or does not exist."})
        # Propagate authoritative hospital details to the user
        attrs['hospital_name'] = hospital.official_name
        attrs['hospital_address'] = hospital.address

        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        validated_data.pop("license_number", None)
        validated_data.pop("specialization", None)
        validated_data.pop("department", None)
        validated_data.pop("hospital_id", None)
        user = User.objects.create_user(**validated_data)
        return user

# Removed: ProfilePictureSerializer (profile picture uploads are deprecated)

class VerificationDocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for updating verification document and verification status
    """
    class Meta:
        model = User
        fields = ["verification_document", "is_verified", "verification_status"]

    def validate_verification_document(self, value):
        """
        Validate verification document file type
        """
        if value:
            allowed_types = ['application/pdf', 'image/jpeg', 'image/png']
            if value.content_type not in allowed_types:
                raise serializers.ValidationError("Only PDF, JPG, and PNG files are allowed.")
            
            # Check file size (max 5MB)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("File size must be less than 5MB.")
        
        return value


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user profile information including hospital details
    """
    class Meta:
        model = User
        fields = [
            'email', 'full_name', 'date_of_birth', 'gender', 
            'hospital_name', 'hospital_address'
        ]
        read_only_fields = ['email']  # Email should not be updated through this endpoint

    def update(self, instance, validated_data):
        """Trim and persist hospital fields reliably."""
        # Basic fields
        instance.full_name = validated_data.get('full_name', instance.full_name)
        instance.date_of_birth = validated_data.get('date_of_birth', instance.date_of_birth)
        instance.gender = validated_data.get('gender', instance.gender)

        # Hospital fields: normalize whitespace
        hosp_name = validated_data.get('hospital_name', instance.hospital_name)
        hosp_addr = validated_data.get('hospital_address', instance.hospital_address)
        if isinstance(hosp_name, str):
            hosp_name = hosp_name.strip()
        if isinstance(hosp_addr, str):
            hosp_addr = hosp_addr.strip()
        instance.hospital_name = hosp_name or ''
        instance.hospital_address = hosp_addr or ''

        # Persist only changed fields when possible
        try:
            instance.save(update_fields=['full_name', 'date_of_birth', 'gender', 'hospital_name', 'hospital_address'])
        except Exception:
            # Fallback: save without update_fields to avoid edge cases
            instance.save()
        return instance


class TwoFactorEnableSerializer(serializers.Serializer):
    """
    Serializer for initiating 2FA setup
    """
    pass  # No input required for initial setup


class TwoFactorVerifySerializer(serializers.Serializer):
    """
    Serializer for verifying and activating 2FA
    """
    otp_code = serializers.CharField(
        max_length=6,
        min_length=6,
        required=True,
        help_text="6-digit OTP code from authenticator app"
    )

    def validate_otp_code(self, value):
        """Validate that OTP code is 6 digits"""
        if not value.isdigit():
            raise serializers.ValidationError("OTP code must contain only digits.")
        return value


class TwoFactorDisableSerializer(serializers.Serializer):
    """
    Serializer for disabling 2FA
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        help_text="User password for verification"
    )


class TwoFactorLoginSerializer(serializers.Serializer):
    """
    Serializer for 2FA login verification
    """
    email = serializers.EmailField(required=True)
    otp_code = serializers.CharField(
        max_length=6,
        min_length=6,
        required=True,
        help_text="6-digit OTP code from authenticator app"
    )

    def validate_otp_code(self, value):
        """Validate that OTP code is 6 digits"""
        if not value.isdigit():
            raise serializers.ValidationError("OTP code must contain only digits.")
        return value


# ---- Nurse-centric form serializers ----

class NursingIntakeAssessmentSerializer(serializers.Serializer):
    """
    Serializer for Nursing Intake & Assessment. Uses permissive JSON fields
    with minimal validation to mirror model-level checks.
    """
    vitals = serializers.JSONField(required=False)
    weight_kg = serializers.FloatField(required=False)
    height_cm = serializers.FloatField(required=False)
    registration = serializers.JSONField(required=False)
    registration_physical = serializers.JSONField(required=False)
    opd_assessment = serializers.JSONField(required=False)
    chief_complaint = serializers.CharField(required=False, allow_blank=True)
    pain_score = serializers.FloatField(required=False)
    affected_body_parts = serializers.JSONField(required=False)
    allergies = serializers.JSONField(required=False)
    current_medications = serializers.JSONField(required=False)
    medical_history = serializers.CharField(required=False, allow_blank=True)
    assessment_notes = serializers.CharField(required=False, allow_blank=True)
    mental_status = serializers.CharField(required=False, allow_blank=True)
    fall_risk_score = serializers.FloatField(required=False)
    assessed_at = serializers.CharField(required=False, allow_blank=True)
    consent_agreed = serializers.BooleanField(required=False)
    patient_signature = serializers.CharField(required=False, allow_blank=True)
    signature_date = serializers.CharField(required=False, allow_blank=True)

    def validate_pain_score(self, value):
        if value is None:
            return value
        if value < 0 or value > 10:
            raise serializers.ValidationError("pain_score must be between 0 and 10")
        return value

    def validate(self, attrs):
        registration = attrs.get("registration")
        if isinstance(registration, dict) and registration:
            missing = []
            if not str(registration.get("surname") or "").strip():
                missing.append("registration.surname")
            if not str(registration.get("first_name") or "").strip():
                missing.append("registration.first_name")
            if not str(registration.get("birthday") or "").strip():
                missing.append("registration.birthday")
            if missing:
                raise serializers.ValidationError({"registration": f"Missing required fields: {', '.join(missing)}"})

        registration_physical = attrs.get("registration_physical")
        if isinstance(registration_physical, dict) and registration_physical:
            missing = []
            if not str(registration_physical.get("surname") or "").strip():
                missing.append("registration_physical.surname")
            if not str(registration_physical.get("first_name") or "").strip():
                missing.append("registration_physical.first_name")
            if not str(registration_physical.get("birthday") or "").strip():
                missing.append("registration_physical.birthday")
            if not str(registration_physical.get("address") or "").strip():
                missing.append("registration_physical.address")
            if not str(registration_physical.get("contact_no") or "").strip():
                missing.append("registration_physical.contact_no")
            if missing:
                raise serializers.ValidationError({"registration_physical": f"Missing required fields: {', '.join(missing)}"})

        opd = attrs.get("opd_assessment")
        if isinstance(opd, dict) and opd:
            missing = []
            if not str(opd.get("date") or "").strip():
                missing.append("opd_assessment.date")
            if not str(opd.get("staff") or "").strip():
                missing.append("opd_assessment.staff")
            if not str(opd.get("complaints_pe_findings") or "").strip():
                missing.append("opd_assessment.complaints_pe_findings")
            if missing:
                raise serializers.ValidationError({"opd_assessment": f"Missing required fields: {', '.join(missing)}"})

        return attrs


class FlowSheetEntrySerializer(serializers.Serializer):
    """Single graphic flow sheet entry."""
    time_of_reading = serializers.CharField(required=True)
    repeated_vitals = serializers.JSONField(required=False)
    intake_ml = serializers.FloatField(required=False)
    output_ml = serializers.FloatField(required=False)
    site_checks = serializers.CharField(required=False, allow_blank=True)
    nursing_interventions = serializers.JSONField(required=False)


class MARRecordSerializer(serializers.Serializer):
    """Medication Administration Record entry."""
    datetime_administered = serializers.CharField(required=True)
    name = serializers.CharField(required=True)
    dose = serializers.CharField(required=True)
    route = serializers.CharField(required=True)
    nurse_initials = serializers.CharField(required=True)
    prn_reason = serializers.CharField(required=False, allow_blank=True)
    prn_response = serializers.CharField(required=False, allow_blank=True)
    withheld_reason = serializers.CharField(required=False, allow_blank=True)


class EducationEntrySerializer(serializers.Serializer):
    topics = serializers.JSONField(required=True)
    teaching_method = serializers.CharField(required=True)
    comprehension_level = serializers.CharField(required=False, allow_blank=True)
    return_demonstration = serializers.CharField(required=False, allow_blank=True)
    barriers_to_learning = serializers.JSONField(required=False)
    recorded_at = serializers.CharField(required=False, allow_blank=True)


class DischargeSummarySerializer(serializers.Serializer):
    discharge_vitals = serializers.JSONField(required=False)
    understanding_confirmed = serializers.BooleanField(required=False)
    written_instructions_provided = serializers.BooleanField(required=False)
    follow_up_appointments_made = serializers.BooleanField(required=False)
    equipment_needs = serializers.JSONField(required=False)
    transportation_status = serializers.CharField(required=False, allow_blank=True)
    nurse_signature = serializers.CharField(required=False, allow_blank=True)
    patient_acknowledgment = serializers.BooleanField(required=False)
    discharged_at = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs.get("understanding_confirmed") and not attrs.get("discharged_at"):
            raise serializers.ValidationError({"discharged_at": "Required when understanding_confirmed is true"})
        return attrs


# ---- Doctor-centric form serializers ----

class HPFormSerializer(serializers.Serializer):
    """History & Physical form entry serializer (permissive; model enforces minimal checks)."""
    patient_name = serializers.CharField(required=False, allow_blank=True)
    dob = serializers.CharField(required=False, allow_blank=True)
    mrn = serializers.CharField(required=False, allow_blank=True)
    provider_signature = serializers.CharField(required=False, allow_blank=True)
    provider_id = serializers.CharField(required=False, allow_blank=True)
    chief_complaint = serializers.CharField(required=False, allow_blank=True)
    history_present_illness = serializers.CharField(required=False, allow_blank=True)
    past_medical_history = serializers.CharField(required=False, allow_blank=True)
    social_history = serializers.CharField(required=False, allow_blank=True)
    review_of_systems = serializers.JSONField(required=False)
    physical_exam = serializers.CharField(required=False, allow_blank=True)
    assessment = serializers.CharField(required=False, allow_blank=True)
    diagnoses_icd_codes = serializers.JSONField(required=False)
    initial_plan = serializers.CharField(required=False, allow_blank=True)
    created_at = serializers.CharField(required=False, allow_blank=True)


class ProgressNoteSerializer(serializers.Serializer):
    """SOAP progress note serializer (accepts either date_time or date_time_note)."""
    date_time = serializers.CharField(required=False, allow_blank=True)
    date_time_note = serializers.CharField(required=False, allow_blank=True)
    subjective = serializers.CharField(required=False, allow_blank=True)
    objective = serializers.CharField(required=False, allow_blank=True)
    vitals = serializers.JSONField(required=False)
    lab_imaging_results = serializers.CharField(required=False, allow_blank=True)
    assessment = serializers.CharField(required=False, allow_blank=True)
    plan = serializers.CharField(required=False, allow_blank=True)
    follow_up_date = serializers.CharField(required=False, allow_blank=True)
    provider_signature = serializers.CharField(required=False, allow_blank=True)
    created_at = serializers.CharField(required=False, allow_blank=True)


class ProviderOrderSerializer(serializers.Serializer):
    """Provider order sheet serializer."""
    ordering_provider = serializers.CharField(required=False, allow_blank=True)
    date_time_placed = serializers.CharField(required=False, allow_blank=True)
    order_type = serializers.CharField(required=False, allow_blank=True)
    medication_orders = serializers.JSONField(required=False)
    diagnostic_orders = serializers.JSONField(required=False)
    consultation_orders = serializers.JSONField(required=False)
    general_orders = serializers.JSONField(required=False)
    order_status = serializers.CharField(required=False, allow_blank=True)
    created_at = serializers.CharField(required=False, allow_blank=True)


class OperativeReportSerializer(serializers.Serializer):
    """Operative/procedure report serializer."""
    patient_id = serializers.CharField(required=False, allow_blank=True)
    date_time_performed = serializers.CharField(required=False, allow_blank=True)
    procedure_name = serializers.CharField(required=False, allow_blank=True)
    indications = serializers.CharField(required=False, allow_blank=True)
    consent_status = serializers.CharField(required=False, allow_blank=True)
    anesthesia_type = serializers.CharField(required=False, allow_blank=True)
    anesthesia_dose = serializers.CharField(required=False, allow_blank=True)
    procedure_steps = serializers.CharField(required=False, allow_blank=True)
    findings = serializers.CharField(required=False, allow_blank=True)
    complications = serializers.CharField(required=False, allow_blank=True)
    disposition_plan = serializers.CharField(required=False, allow_blank=True)
    surgeon_signature = serializers.CharField(required=False, allow_blank=True)
    created_at = serializers.CharField(required=False, allow_blank=True)
