from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator

import secrets
import string

from .managers import CustomUserManager


def _generate_patient_id() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "PAT-" + "".join(secrets.choice(alphabet) for _ in range(8))

class User(AbstractUser):
    """
    Custom user model.
    - Uses email as the unique identifier.
    - Adds role, full_name, and other profile fields.
    - Inherits fields like password, last_login, is_superuser from AbstractUser.
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        NURSE = "nurse", "Nurse"
        DOCTOR = "doctor", "Doctor"
        PATIENT = "patient", "Patient"
        
    # Keep a simple string field for optional URL or identifier.
    profile_picture = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Deprecated: optional URL or identifier for profile picture"
    )
    verification_document = models.FileField(
        upload_to='verification_documents/%Y/%m/%d/',
        blank=True,
        null=True,
        help_text="Upload a PDF, JPG, or PNG file for identity verification"
    )
    # AbstractUser has a 'username' field. We set it to None to indicate
    username = None
    email = models.EmailField("email address", unique=True)

    # Custom fields
    role = models.CharField(max_length=10, choices=Role.choices)
    full_name = models.CharField(max_length=255, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    hospital_name = models.CharField(max_length=255, blank=True, help_text="Hospital or medical facility name")
    hospital_address = models.TextField(blank=True, help_text="Hospital address")
    is_verified = models.BooleanField(default=False)
    verification_status = models.CharField(
        max_length=20,
        choices=[
            ('not_submitted', 'Not Submitted'),
            ('pending', 'Pending Admin Review'),
            ('approved', 'Approved'),
            ('declined', 'Declined'),
        ],
        default='not_submitted'
    )
    
    # Two-Factor Authentication fields
    two_factor_enabled = models.BooleanField(default=False, help_text="Enable/disable two-factor authentication")
    two_factor_secret = models.CharField(max_length=32, blank=True, null=True, help_text="Secret key for 2FA")
    
    updated_at = models.DateTimeField(auto_now=True)  # `date_joined` from AbstractUser serves as `created_at`

    USERNAME_FIELD = "email"
    # 'email' and 'password' are required by default.
    # These fields will be prompted for when using the `createsuperuser` command.
    REQUIRED_FIELDS = ["full_name", "role"]

    objects = CustomUserManager()

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return self.email

    def clean(self):
        from django.core.exceptions import ValidationError
        import re
        
        # Password validation for alphanumeric combination with at least 8 characters
        if self.password and len(self.password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        
        if self.password and not re.match(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d@$!%*?&]{8,}$', self.password):
            raise ValidationError("Password must contain at least one letter and one number.")


class GeneralDoctorProfile(models.Model):
    """Profile model for users with the 'doctor' role."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="doctor_profile")
    license_number = models.CharField(max_length=100, unique=True, blank=True, null=True)
    specialization = models.CharField(max_length=255, blank=True)
    available_for_consultation = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "general_doctor_profiles"
        verbose_name = "General Doctor Profile"
        verbose_name_plural = "General Doctor Profiles"

    def __str__(self):
        return f"Dr. {self.user.full_name} - {self.specialization}"


class NurseProfile(models.Model):
    """Profile model for users with the 'nurse' role."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="nurse_profile")
    license_number = models.CharField(max_length=100, unique=True, blank=True, null=True)
    department = models.CharField(max_length=255, blank=True, help_text="Department where the nurse works")

    class Meta:
        db_table = "nurse_profiles"
        verbose_name = "Nurse Profile"
        verbose_name_plural = "Nurse Profiles"

    def __str__(self):
        return f"Nurse {self.user.full_name}"
    
    #patient profile
class PatientProfile(models.Model): #can be the content of medical history
    """Profile model for users with the 'patient' role."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="patient_profile")
    
    patient_id = models.CharField(max_length=20, unique=True, db_index=True, editable=False)

    # Note: Name, Age, and Gender are sourced from the related User model.
    # Age can be calculated from user.date_of_birth.
    #this is for patient demographics for predictive analytics
    class BloodType(models.TextChoices):
        A_POSITIVE = "A+", "A+"
        A_NEGATIVE = "A-", "A-"
        B_POSITIVE = "B+", "B+"
        B_NEGATIVE = "B-", "B-"
        AB_POSITIVE = "AB+", "AB+"
        AB_NEGATIVE = "AB-", "AB-"
        O_POSITIVE = "O+", "O+"
        O_NEGATIVE = "O-", "O-"
        UNKNOWN = "UNK", "Unknown"

    blood_type = models.CharField(
        max_length=3, choices=BloodType.choices, default=BloodType.UNKNOWN, blank=True
    )
    medical_condition = models.TextField(
        blank=True, help_text="A summary of the patient's current medical condition."
    )
    date_of_admission = models.DateField(null=True, blank=True)
    discharge_date = models.DateField(null=True, blank=True)
    assigned_doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patients",
        limit_choices_to={"role": User.Role.DOCTOR},
        help_text="The primary doctor assigned to this patient.",
    )
    medication = models.TextField(blank=True, help_text="List of prescribed medications.")
    test_results = models.TextField(blank=True, help_text="Summary of recent test results.")
    
    # Additional fields from CSV data
    hospital = models.CharField(max_length=255, blank=True, help_text="Hospital or medical facility name.")
    insurance_provider = models.CharField(max_length=255, blank=True, help_text="Patient's insurance provider.")
    billing_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Billing amount for treatment.")
    room_number = models.CharField(max_length=20, blank=True, help_text="Hospital room number.")
    admission_type = models.CharField(max_length=50, blank=True, help_text="Type of admission (emergency, scheduled, etc.).")

    # Nurse-centric forms storage (JSON fields)
    nursing_intake_assessment = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Structured intake fields: vitals, anthropometrics, chief complaint, pain score, "
            "allergies with reactions, current medications, mental status, fall risk score, assessed_at."
        ),
    )

    graphic_flow_sheets = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "List of chronological entries with time_of_reading, repeated_vitals, intake_ml, output_ml, "
            "site_checks, and nursing_interventions."
        ),
    )

    # 3) Medication Administration Record (MAR)
    medication_administration_records = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "List of medication events: datetime_administered, name, dose, route, nurse_initials, "
            "optional prn_reason, prn_response, withheld_reason."
        ),
    )

    # 4) Patient Education Record
    patient_education_record = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "List of education interactions: topics, teaching_method, comprehension_level, "
            "return_demonstration, barriers_to_learning, recorded_at."
        ),
    )

    # 5) Discharge Checklist & Summary (Nursing Section)
    discharge_checklist_summary = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Final discharge verification: discharge_vitals, understanding_confirmed, written_instructions_provided, "
            "follow_up_appointments_made, equipment_needs, transportation_status, nurse_signature, "
            "patient_acknowledgment, discharged_at."
        ),
    )

    # Doctor-centric forms (restricted to doctors only)
    history_physical_forms = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "List of H&P forms: patient_name, dob, mrn, provider_signature, provider_id, chief_complaint, "
            "history_present_illness, past_medical_history, social_history, review_of_systems, "
            "physical_exam, assessment, diagnoses_icd_codes, initial_plan, created_at."
        ),
    )

    progress_notes = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "List of SOAP progress notes: date_time_note, subjective, objective, vitals, "
            "lab_imaging_results, assessment, plan, follow_up_date, provider_signature, created_at."
        ),
    )

    provider_order_sheets = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "List of provider orders: ordering_provider, date_time_placed, order_type, "
            "medication_orders (drug_name, dose, route, frequency), diagnostic_orders (test_name, priority, reason), "
            "consultation_orders (specialty, question), general_orders, order_status, created_at."
        ),
    )

    operative_procedure_reports = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "List of operative/procedure reports: patient_id, date_time_performed, procedure_name, "
            "indications, consent_status, anesthesia_type, anesthesia_dose, procedure_steps, "
            "findings, complications, disposition_plan, surgeon_provider_signature, created_at."
        ),
    )

    def save(self, *args, **kwargs):
        if not self.patient_id:
            candidate = _generate_patient_id()
            while PatientProfile.objects.filter(patient_id=candidate).exists():
                candidate = _generate_patient_id()
            self.patient_id = candidate
        return super().save(*args, **kwargs)

    class Meta:
        db_table = "patient_profiles"
        verbose_name = "Patient Profile"
        verbose_name_plural = "Patient Profiles"

    def __str__(self):
        return f"Patient {self.user.full_name}"

    # ---- Nurse-centric helpers ----
    def add_flow_sheet_entry(self, entry):
        """
        Append a single flow sheet entry.
        Expected shape:
        {
            "time_of_reading": ISO8601 string,
            "repeated_vitals": {"bp": "120/80", "hr": 70, "rr": 16, "temp_c": 36.6, "o2_sat": 98, "pain": 3},
            "intake_ml": 250,
            "output_ml": 200,
            "site_checks": "IV site clean/dry/intact",
            "nursing_interventions": ["administered analgesic", "repositioned patient"]
        }
        """
        entries = list(self.graphic_flow_sheets or [])
        entries.append(entry)
        self.graphic_flow_sheets = entries

    def add_mar_entry(self, entry):
        """
        Append a single MAR entry.
        Expected shape:
        {
            "datetime_administered": ISO8601 string,
            "name": "Acetaminophen",
            "dose": "500 mg",
            "route": "PO",
            "nurse_initials": "AB",
            "prn_reason": "Pain 6/10",
            "prn_response": "Pain improved to 3/10",
            "withheld_reason": null
        }
        """
        entries = list(self.medication_administration_records or [])
        entries.append(entry)
        self.medication_administration_records = entries

    def add_education_entry(self, entry):
        """
        Append a single Patient Education entry.
        Expected shape:
        {
            "topics": ["wound care", "new medication use"],
            "teaching_method": "verbal",
            "comprehension_level": "good",  # e.g., poor/fair/good/excellent
            "return_demonstration": "successful",
            "barriers_to_learning": ["language"],
            "recorded_at": ISO8601 string
        }
        """
        entries = list(self.patient_education_record or [])
        entries.append(entry)
        self.patient_education_record = entries

    def set_nursing_intake(self, data):
        """
        Set the Nursing Intake & Assessment payload (dict). Minimal validation applied.
        Keys suggested: vitals, weight_kg, height_cm, chief_complaint, pain_score,
        allergies, current_medications, mental_status, fall_risk_score, assessed_at.
        """
        self.nursing_intake_assessment = data or {}

    def set_discharge_summary(self, data):
        """
        Set the Discharge Checklist & Summary payload (dict). Minimal validation applied.
        Keys suggested: discharge_vitals, understanding_confirmed, written_instructions_provided,
        follow_up_appointments_made, equipment_needs, transportation_status, nurse_signature,
        patient_acknowledgment, discharged_at.
        """
        self.discharge_checklist_summary = data or {}

    def validate_nurse_forms_minimal(self):
        """
        Perform minimal schema checks for nurse-centric JSON fields.
        Returns a tuple (is_valid: bool, errors: list[str]).
        """
        errors = []

        # Nursing intake: ensure pain_score 0-10 if present
        intake = self.nursing_intake_assessment or {}
        pain = intake.get("pain_score")
        if pain is not None:
            try:
                pain_val = float(pain)
                if pain_val < 0 or pain_val > 10:
                    errors.append("nursing_intake_assessment.pain_score must be between 0 and 10")
            except Exception:
                errors.append("nursing_intake_assessment.pain_score must be numeric")

        # Flow sheet entries: ensure time_of_reading present
        for idx, e in enumerate(self.graphic_flow_sheets or []):
            if "time_of_reading" not in e:
                errors.append(f"graphic_flow_sheets[{idx}].time_of_reading is required")

        # MAR entries: ensure required keys
        for idx, e in enumerate(self.medication_administration_records or []):
            for key in ("datetime_administered", "name", "dose", "route", "nurse_initials"):
                if key not in e:
                    errors.append(f"medication_administration_records[{idx}].{key} is required")

        # Education entries: ensure topics and teaching_method
        for idx, e in enumerate(self.patient_education_record or []):
            if not e.get("topics"):
                errors.append(f"patient_education_record[{idx}].topics is required")
            if not e.get("teaching_method"):
                errors.append(f"patient_education_record[{idx}].teaching_method is required")

        # Discharge summary: ensure discharged_at if understanding_confirmed
        ds = self.discharge_checklist_summary or {}
        if ds.get("understanding_confirmed") and not ds.get("discharged_at"):
            errors.append("discharge_checklist_summary.discharged_at is required when understanding_confirmed=true")

        return (len(errors) == 0, errors)

    # Doctor-centric form helper methods
    def add_hp_form(self, entry):
        """
        Append a single History & Physical form entry.
        Expected shape:
        {
            "patient_name": "John Doe",
            "dob": "1980-01-01",
            "mrn": "MRN123456",
            "provider_signature": "Dr. Smith",
            "provider_id": "DOC001",
            "chief_complaint": "Chest pain",
            "history_present_illness": "Patient presents with...",
            "past_medical_history": "Hypertension, diabetes",
            "social_history": "Non-smoker, occasional alcohol",
            "review_of_systems": {"cardiovascular": "positive", "respiratory": "negative"},
            "physical_exam": "Well-appearing patient...",
            "assessment": "Chest pain, rule out MI",
            "diagnoses_icd_codes": ["R06.02", "Z87.891"],
            "initial_plan": "EKG, troponins, chest X-ray",
            "created_at": ISO8601 string
        }
        """
        entries = list(self.history_physical_forms or [])
        entries.append(entry)
        self.history_physical_forms = entries

    def add_progress_note(self, entry):
        """
        Append a single SOAP progress note entry.
        Expected shape:
        {
            "date_time_note": ISO8601 string,
            "subjective": "Patient reports feeling better...",
            "objective": "Vital signs stable...",
            "vitals": {"bp": "120/80", "hr": "72", "temp": "98.6"},
            "lab_imaging_results": "CBC normal, chest X-ray clear",
            "assessment": "Improving chest pain...",
            "plan": "Continue current medications...",
            "follow_up_date": "2024-02-01",
            "provider_signature": "Dr. Smith",
            "created_at": ISO8601 string
        }
        """
        entries = list(self.progress_notes or [])
        entries.append(entry)
        self.progress_notes = entries

    def add_provider_order(self, entry):
        """
        Append a single provider order entry.
        Expected shape:
        {
            "ordering_provider": "Dr. Smith",
            "date_time_placed": ISO8601 string,
            "order_type": "medication|diagnostic|consultation|general",
            "medication_orders": [{"drug_name": "Lisinopril", "dose": "10mg", "route": "PO", "frequency": "daily"}],
            "diagnostic_orders": [{"test_name": "CBC", "priority": "routine", "reason": "monitoring"}],
            "consultation_orders": [{"specialty": "cardiology", "question": "evaluate chest pain"}],
            "general_orders": ["NPO after midnight", "bed rest"],
            "order_status": "new|held|discontinued",
            "created_at": ISO8601 string
        }
        """
        entries = list(self.provider_order_sheets or [])
        entries.append(entry)
        self.provider_order_sheets = entries

    def add_operative_report(self, entry):
        """
        Append a single operative/procedure report entry.
        Expected shape:
        {
            "patient_id": "PAT123456",
            "date_time_performed": ISO8601 string,
            "procedure_name": "Appendectomy",
            "indications": "Acute appendicitis",
            "consent_status": "obtained",
            "anesthesia_type": "general",
            "anesthesia_dose": "propofol 200mg",
            "procedure_steps": "Patient positioned supine...",
            "findings": "Inflamed appendix with perforation...",
            "complications": "none",
            "disposition_plan": "Recovery room, NPO until bowel sounds return",
            "surgeon_provider_signature": "Dr. Johnson",
            "created_at": ISO8601 string
        }
        """
        entries = list(self.operative_procedure_reports or [])
        entries.append(entry)
        self.operative_procedure_reports = entries

    def validate_doctor_forms_minimal(self):
        """
        Perform minimal schema checks for doctor-centric JSON fields.
        Returns a tuple (is_valid: bool, errors: list[str]).
        """
        errors = []

        # H&P forms: ensure required header fields
        for idx, e in enumerate(self.history_physical_forms or []):
            for key in ("patient_name", "dob", "mrn", "provider_signature", "chief_complaint"):
                if not e.get(key):
                    errors.append(f"history_physical_forms[{idx}].{key} is required")

        # Progress notes: ensure SOAP structure
        for idx, e in enumerate(self.progress_notes or []):
            for key in ("date_time", "subjective", "provider_signature"):
                if not e.get(key):
                    errors.append(f"progress_notes[{idx}].{key} is required")

        # Provider orders: ensure ordering provider and date/time
        for idx, e in enumerate(self.provider_order_sheets or []):
            for key in ("ordering_provider", "date_time_placed"):
                if not e.get(key):
                    errors.append(f"provider_order_sheets[{idx}].{key} is required")

        # Operative reports: ensure procedure details
        for idx, e in enumerate(self.operative_procedure_reports or []):
            for key in ("procedure_name", "surgeon_signature", "date_time_performed"):
                if not e.get(key):
                    errors.append(f"operative_procedure_reports[{idx}].{key} is required")

        return (len(errors) == 0, errors)

    def get_form_fields_context(self, for_role=None):
        """
        Structured form context describing fields, types, and defaults for frontend forms.
        Includes demographics, medical/admin, and nurse-centric forms.
        """
        def iso(dt):
            try:
                return dt.isoformat() if dt else None
            except Exception:
                return None

        context = {
            "model": "patient_profiles",
            "version": "2",
            "role": for_role,
            "groups": [
                "demographics",
                "medical",
                "administrative",
                "nursing_admin",
                "nursing_intake",
                "flow_sheets",
                "mar",
                "education",
                "discharge",
                "history_physical",
                "progress_notes",
                "provider_orders",
                "operative_reports",
            ],
            "demographics": {
                "full_name": {"label": "Full Name", "type": "text", "readonly": True, "default": self.user.full_name},
                "date_of_birth": {"label": "Date of Birth", "type": "date", "readonly": True, "default": iso(self.user.date_of_birth)},
                "gender": {"label": "Gender", "type": "text", "readonly": True, "default": self.user.gender},
                "hospital_address": {"label": "Hospital Address", "type": "textarea", "readonly": True, "default": self.user.hospital_address},
            },
            "medical": {
                "blood_type": {"label": "Blood Type", "type": "select", "choices": list(self.BloodType.choices), "required": False, "default": self.blood_type},
                "medical_condition": {"label": "Medical Condition", "type": "textarea", "required": False, "default": self.medical_condition},
                "date_of_admission": {"label": "Date of Admission", "type": "date", "required": False, "default": iso(self.date_of_admission)},
                "discharge_date": {"label": "Discharge Date", "type": "date", "required": False, "default": iso(self.discharge_date)},
                "assigned_doctor": {"label": "Assigned Doctor", "type": "relation", "required": False, "default": getattr(self.assigned_doctor, "id", None), "relation": {"model": "users.User", "filter": {"role": "doctor"}}},
                "medication": {"label": "Current Medications", "type": "textarea", "required": False, "default": self.medication},
                "test_results": {"label": "Test Results", "type": "textarea", "required": False, "default": self.test_results},
            },
            "administrative": {
                "hospital": {"label": "Hospital", "type": "text", "required": False, "default": self.hospital or self.user.hospital_name},
                "insurance_provider": {"label": "Insurance Provider", "type": "text", "required": False, "default": self.insurance_provider},
                "billing_amount": {"label": "Billing Amount", "type": "decimal", "required": False, "default": float(self.billing_amount) if self.billing_amount is not None else None, "attrs": {"max_digits": 10, "decimal_places": 2}},
                "room_number": {"label": "Room Number", "type": "text", "required": False, "default": self.room_number, "attrs": {"max_length": 20}},
                "admission_type": {"label": "Admission Type", "type": "text", "required": False, "default": self.admission_type, "attrs": {"max_length": 50}},
            },
            # Nurse-centric grouping of core medical/admin fields
            "nursing_admin": {
                "blood_type": {"label": "Blood Type", "type": "select", "choices": list(self.BloodType.choices), "required": False, "default": self.blood_type},
                "medical_condition": {"label": "Medical Condition", "type": "textarea", "required": False, "default": self.medical_condition},
                "date_of_admission": {"label": "Date of Admission", "type": "date", "required": False, "default": iso(self.date_of_admission)},
                "discharge_date": {"label": "Discharge Date", "type": "date", "required": False, "default": iso(self.discharge_date)},
                "assigned_doctor": {"label": "Assigned Doctor", "type": "relation", "required": False, "default": getattr(self.assigned_doctor, "id", None), "relation": {"model": "users.User", "filter": {"role": "doctor"}}},
                "medication": {"label": "Current Medications", "type": "textarea", "required": False, "default": self.medication},
                "test_results": {"label": "Test Results", "type": "textarea", "required": False, "default": self.test_results},
                "hospital": {"label": "Hospital", "type": "text", "required": False, "default": self.hospital or self.user.hospital_name},
                "insurance_provider": {"label": "Insurance Provider", "type": "text", "required": False, "default": self.insurance_provider},
                "billing_amount": {"label": "Billing Amount", "type": "decimal", "required": False, "default": float(self.billing_amount) if self.billing_amount is not None else None, "attrs": {"max_digits": 10, "decimal_places": 2}},
                "room_number": {"label": "Room Number", "type": "text", "required": False, "default": self.room_number, "attrs": {"max_length": 20}},
                "admission_type": {"label": "Admission Type", "type": "text", "required": False, "default": self.admission_type, "attrs": {"max_length": 50}},
            },
            "nursing_intake": {
                "schema": {
                    "vitals": {"bp": "", "hr": None, "rr": None, "temp_c": None, "o2_sat": None},
                    "weight_kg": None,
                    "height_cm": None,
                    "chief_complaint": "",
                    "pain_score": None,
                    "allergies": [],  # [{substance, reaction}]
                    "current_medications": [],
                    "mental_status": "",
                    "fall_risk_score": None,
                    "assessed_at": None,
                },
                "default": self.nursing_intake_assessment or {},
            },
            "flow_sheets": {
                "schema": {
                    "time_of_reading": None,
                    "repeated_vitals": {"bp": "", "hr": None, "rr": None, "temp_c": None, "o2_sat": None, "pain": None},
                    "intake_ml": None,
                    "output_ml": None,
                    "site_checks": "",
                    "nursing_interventions": [],
                },
                "default": list(self.graphic_flow_sheets or []),
            },
            "mar": {
                "schema": {
                    "datetime_administered": None,
                    "name": "",
                    "dose": "",
                    "route": "",
                    "nurse_initials": "",
                    "prn_reason": None,
                    "prn_response": None,
                    "withheld_reason": None,
                },
                "default": list(self.medication_administration_records or []),
            },
            "education": {
                "schema": {
                    "topics": [],
                    "teaching_method": "",
                    "comprehension_level": "",
                    "return_demonstration": "",
                    "barriers_to_learning": [],
                    "recorded_at": None,
                },
                "default": list(self.patient_education_record or []),
            },
            "discharge": {
                "schema": {
                    "discharge_vitals": {"bp": "", "hr": None, "rr": None, "temp_c": None, "o2_sat": None, "pain": None},
                    "understanding_confirmed": False,
                    "written_instructions_provided": False,
                    "follow_up_appointments_made": False,
                    "equipment_needs": [],
                    "transportation_status": "",
                    "nurse_signature": "",
                    "patient_acknowledgment": False,
                    "discharged_at": None,
                },
                "default": {},
            },
            # Doctor-centric forms
            "history_physical": {
                "schema": {
                    "patient_name": "",
                    "dob": None,
                    "mrn": "",
                    "provider_signature": "",
                    "provider_id": "",
                    "chief_complaint": "",
                    "history_present_illness": "",
                    "past_medical_history": "",
                    "social_history": "",
                    "review_of_systems": [],
                    "physical_exam": "",
                    "assessment": "",
                    "diagnoses_icd_codes": [],
                    "initial_plan": "",
                    "created_at": None,
                },
                "default": [],
            },
            "progress_notes": {
                "schema": {
                    "date_time_note": None,
                    "subjective": "",
                    "objective": "",
                    "vitals": {"bp": "", "hr": None, "rr": None, "temp_c": None, "o2_sat": None},
                    "lab_imaging_results": "",
                    "assessment": "",
                    "plan": "",
                    "follow_up_date": None,
                    "provider_signature": "",
                    "created_at": None,
                },
                "default": [],
            },
            "provider_orders": {
                "schema": {
                    "ordering_provider": "",
                    "date_time_placed": None,
                    "order_type": "",
                    "medication_orders": {
                        "drug_name": "",
                        "dose": "",
                        "route": "",
                        "frequency": "",
                    },
                    "diagnostic_orders": {
                        "test_name": "",
                        "priority": "",
                        "reason": "",
                    },
                    "consultation_orders": {
                        "specialty": "",
                        "question": "",
                    },
                    "general_orders": "",
                    "order_status": "",
                    "created_at": None,
                },
                "default": [],
            },
            "operative_reports": {
                "schema": {
                    "patient_id": "",
                    "date_time_performed": None,
                    "procedure_name": "",
                    "indications": "",
                    "consent_status": "",
                    "anesthesia_type": "",
                    "anesthesia_dose": "",
                    "procedure_steps": "",
                    "findings": "",
                    "complications": "",
                    "disposition_plan": "",
                    "surgeon_provider_signature": "",
                    "created_at": None,
                },
                "default": [],
            },
        }
        return context

    @classmethod
    def get_blank_form_fields_context(cls, for_role=None):
        """
        Blank/creation context with model defaults only.
        """
        context = {
            "model": "patient_profiles",
            "version": "2",
            "role": for_role,
            "groups": [
                "demographics",
                "medical",
                "administrative",
                "nursing_admin",
                "nursing_intake",
                "flow_sheets",
                "mar",
                "education",
                "discharge",
                "history_physical",
                "progress_notes",
                "provider_orders",
                "operative_reports",
            ],
            "demographics": {
                "full_name": {"label": "Full Name", "type": "text", "readonly": True, "default": ""},
                "date_of_birth": {"label": "Date of Birth", "type": "date", "readonly": True, "default": None},
                "gender": {"label": "Gender", "type": "text", "readonly": True, "default": None},
                "hospital_address": {"label": "Hospital Address", "type": "textarea", "readonly": True, "default": ""},
            },
            "medical": {
                "blood_type": {"label": "Blood Type", "type": "select", "choices": list(cls.BloodType.choices), "required": False, "default": cls.BloodType.UNKNOWN},
                "medical_condition": {"label": "Medical Condition", "type": "textarea", "required": False, "default": ""},
                "date_of_admission": {"label": "Date of Admission", "type": "date", "required": False, "default": None},
                "discharge_date": {"label": "Discharge Date", "type": "date", "required": False, "default": None},
                "assigned_doctor": {"label": "Assigned Doctor", "type": "relation", "required": False, "default": None, "relation": {"model": "users.User", "filter": {"role": "doctor"}}},
                "medication": {"label": "Current Medications", "type": "textarea", "required": False, "default": ""},
                "test_results": {"label": "Test Results", "type": "textarea", "required": False, "default": ""},
            },
            "administrative": {
                "hospital": {"label": "Hospital", "type": "text", "required": False, "default": ""},
                "insurance_provider": {"label": "Insurance Provider", "type": "text", "required": False, "default": ""},
                "billing_amount": {"label": "Billing Amount", "type": "decimal", "required": False, "default": None, "attrs": {"max_digits": 10, "decimal_places": 2}},
                "room_number": {"label": "Room Number", "type": "text", "required": False, "default": "", "attrs": {"max_length": 20}},
                "admission_type": {"label": "Admission Type", "type": "text", "required": False, "default": "", "attrs": {"max_length": 50}},
            },
            # Nurse-centric grouping of core medical/admin fields
            "nursing_admin": {
                "blood_type": {"label": "Blood Type", "type": "select", "choices": list(cls.BloodType.choices), "required": False, "default": cls.BloodType.UNKNOWN},
                "medical_condition": {"label": "Medical Condition", "type": "textarea", "required": False, "default": ""},
                "date_of_admission": {"label": "Date of Admission", "type": "date", "required": False, "default": None},
                "discharge_date": {"label": "Discharge Date", "type": "date", "required": False, "default": None},
                "assigned_doctor": {"label": "Assigned Doctor", "type": "relation", "required": False, "default": None, "relation": {"model": "users.User", "filter": {"role": "doctor"}}},
                "medication": {"label": "Current Medications", "type": "textarea", "required": False, "default": ""},
                "test_results": {"label": "Test Results", "type": "textarea", "required": False, "default": ""},
                "hospital": {"label": "Hospital", "type": "text", "required": False, "default": ""},
                "insurance_provider": {"label": "Insurance Provider", "type": "text", "required": False, "default": ""},
                "billing_amount": {"label": "Billing Amount", "type": "decimal", "required": False, "default": None, "attrs": {"max_digits": 10, "decimal_places": 2}},
                "room_number": {"label": "Room Number", "type": "text", "required": False, "default": "", "attrs": {"max_length": 20}},
                "admission_type": {"label": "Admission Type", "type": "text", "required": False, "default": "", "attrs": {"max_length": 50}},
            },
            "nursing_intake": {
                "schema": {
                    "vitals": {"bp": "", "hr": None, "rr": None, "temp_c": None, "o2_sat": None},
                    "weight_kg": None,
                    "height_cm": None,
                    "chief_complaint": "",
                    "pain_score": None,
                    "allergies": [],
                    "current_medications": [],
                    "mental_status": "",
                    "fall_risk_score": None,
                    "assessed_at": None,
                },
                "default": {},
            },
            "flow_sheets": {
                "schema": {
                    "time_of_reading": None,
                    "repeated_vitals": {"bp": "", "hr": None, "rr": None, "temp_c": None, "o2_sat": None, "pain": None},
                    "intake_ml": None,
                    "output_ml": None,
                    "site_checks": "",
                    "nursing_interventions": [],
                },
                "default": [],
            },
            "mar": {
                "schema": {
                    "datetime_administered": None,
                    "name": "",
                    "dose": "",
                    "route": "",
                    "nurse_initials": "",
                    "prn_reason": None,
                    "prn_response": None,
                    "withheld_reason": None,
                },
                "default": [],
            },
            "education": {
                "schema": {
                    "topics": [],
                    "teaching_method": "",
                    "comprehension_level": "",
                    "return_demonstration": "",
                    "barriers_to_learning": [],
                    "recorded_at": None,
                },
                "default": [],
            },
            "discharge": {
                "schema": {
                    "discharge_vitals": {"bp": "", "hr": None, "rr": None, "temp_c": None, "o2_sat": None, "pain": None},
                    "understanding_confirmed": False,
                    "written_instructions_provided": False,
                    "follow_up_appointments_made": False,
                    "equipment_needs": [],
                    "transportation_status": "",
                    "nurse_signature": "",
                    "patient_acknowledgment": False,
                    "discharged_at": None,
                },
                "default": {},
            },
            # Doctor-centric forms
            "history_physical": {
                "schema": {
                    "patient_name": "",
                    "dob": None,
                    "mrn": "",
                    "provider_signature": "",
                    "provider_id": "",
                    "chief_complaint": "",
                    "history_present_illness": "",
                    "past_medical_history": "",
                    "social_history": "",
                    "review_of_systems": [],
                    "physical_exam": "",
                    "assessment": "",
                    "diagnoses_icd_codes": [],
                    "initial_plan": "",
                    "created_at": None,
                },
                "default": [],
            },
            "progress_notes": {
                "schema": {
                    "date_time_note": None,
                    "subjective": "",
                    "objective": "",
                    "vitals": {"bp": "", "hr": None, "rr": None, "temp_c": None, "o2_sat": None},
                    "lab_imaging_results": "",
                    "assessment": "",
                    "plan": "",
                    "follow_up_date": None,
                    "provider_signature": "",
                    "created_at": None,
                },
                "default": [],
            },
            "provider_orders": {
                "schema": {
                    "ordering_provider": "",
                    "date_time_placed": None,
                    "order_type": "",
                    "medication_orders": {
                        "drug_name": "",
                        "dose": "",
                        "route": "",
                        "frequency": "",
                    },
                    "diagnostic_orders": {
                        "test_name": "",
                        "priority": "",
                        "reason": "",
                    },
                    "consultation_orders": {
                        "specialty": "",
                        "question": "",
                    },
                    "general_orders": "",
                    "order_status": "",
                    "created_at": None,
                },
                "default": [],
            },
            "operative_reports": {
                "schema": {
                    "patient_id": "",
                    "date_time_performed": None,
                    "procedure_name": "",
                    "indications": "",
                    "consent_status": "",
                    "anesthesia_type": "",
                    "anesthesia_dose": "",
                    "procedure_steps": "",
                    "findings": "",
                    "complications": "",
                    "disposition_plan": "",
                    "surgeon_provider_signature": "",
                    "created_at": None,
                },
                "default": [],
            },
        }
        return context
