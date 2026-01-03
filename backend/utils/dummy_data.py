import logging
import random
import string
from datetime import datetime, timedelta, time
from typing import Dict, Any, List

from django.db import transaction
from django.utils import timezone

from backend.users.models import (
    User,
    GeneralDoctorProfile,
    NurseProfile,
    PatientProfile,
)
from backend.operations.models import (
    AppointmentManagement,
    PatientAssignment,
    ConsultationNotes,
    QueueSchedule,
)


logger = logging.getLogger(__name__)


def _rand_email(prefix: str) -> str:
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"{prefix}.{suffix}@medisync.local"


def _dt(days_ahead: int = 0, minutes_ahead: int = 0) -> datetime:
    return timezone.now() + timedelta(days=days_ahead, minutes=minutes_ahead)


def _safe_time(dt: datetime) -> time:
    return time(dt.hour, dt.minute, dt.second)

def _rand_future_datetime_within_year(max_days_ahead: int = 60) -> datetime:
    """Generate a future datetime within the current year, up to max_days_ahead.
    Ensures appointment dates comply with model constraints for scheduled/rescheduled.
    """
    now = timezone.now()
    # Aim to keep within current year end; use 4 PM cutoff for realism
    year_end = now.replace(month=12, day=31, hour=16, minute=0, second=0, microsecond=0)
    days_remaining = max((year_end - now).days, 1)
    days_ahead = random.randint(1, min(max_days_ahead, days_remaining))
    minutes_ahead = random.randint(0, 8 * 60)  # within an 8-hour window
    return now + timedelta(days=days_ahead, minutes=minutes_ahead)


class DummyDataReport:
    """Structured report for verification and cleanup bookkeeping."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created: Dict[str, List[int]] = {
            'users': [],
            'patient_profiles': [],
            'doctor_profiles': [],
            'nurse_profiles': [],
            'appointments': [],
            'assignments': [],
            'consultation_notes': [],
        }
        self.metrics: Dict[str, Any] = {}
        self.errors: List[str] = []

    def add(self, key: str, pk: int):
        self.created.setdefault(key, []).append(pk)

    def summary(self) -> Dict[str, Any]:
        return {
            'session_id': self.session_id,
            'created_counts': {k: len(v) for k, v in self.created.items()},
            'metrics': self.metrics,
            'errors': self.errors,
        }


def _create_user_safe(**kwargs) -> User:
    password = kwargs.pop('password', None)
    try:
        # Preferred path if custom manager exists
        return User.objects.create_user(password=password, **kwargs)
    except AttributeError:
        # Fallback if create_user is not available
        user = User.objects.create(**kwargs)
        if password:
            user.set_password(password)
            user.save(update_fields=['password'])
        return user


FILIPINO_FIRST_NAMES = [
    'Juan', 'Maria', 'Jose', 'Ana', 'Liza', 'Mark', 'Grace', 'Rodel', 'Emmanuel',
    'Arlene', 'Cesar', 'Ramon', 'Noel', 'Glenda', 'Evelyn', 'Carmela', 'Allan',
    'Rhea', 'Alfred', 'Jessa', 'Arvin', 'Kristine', 'Jonas', 'Jocelyn', 'Mylene'
]
FILIPINO_LAST_NAMES = [
    'Dela Cruz', 'Santos', 'Reyes', 'Garcia', 'Mendoza', 'Aquino', 'Flores',
    'Ramos', 'Torres', 'Gonzales', 'Navarro', 'Fernandez', 'Domingo', 'Villanueva',
    'Castillo', 'Bautista', 'Villar', 'Trinidad', 'Valdez', 'Marquez'
]


def _filipino_name() -> str:
    return f"{random.choice(FILIPINO_FIRST_NAMES)} {random.choice(FILIPINO_LAST_NAMES)}"


def populate_dummy_data(
    *,
    hospital_name: str,
    hospital_address: str,
    hospital_phone: str = '+63 (52) 811-1234',
    hospital_email: str = 'info@catanduanesmedical.ph',
    num_patients: int = 50,
    appointments_per_patient: int = 2,
    nurses_count: int = 20,
    use_api: bool = False,  # reserved for future: invoke endpoints via test client
    cleanup: bool = False,
    dry_run: bool = False,
    verify: bool = True,
) -> Dict[str, Any]:
    """
    Populate realistic dummy data across the system:
    - Staff credentials (one doctor, one nurse)
    - Patient registrations
    - Appointment scheduling
    - Medical records: assignments, notes, record requests
    - Nurse/Doctor forms on PatientProfile JSON fields

    Isolation:
    - Operates within the provided hospital_name/address
    - Tracks all created objects for cleanup/rollback

    Verification:
    - Validates nurse and doctor form minimal checks
    - Confirms persistence for all entities
    - Returns coverage metrics and errors
    """

    session_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
    report = DummyDataReport(session_id)
    created_objects: Dict[str, List[int]] = report.created

    # Track nurse-to-patient assignments for verification
    nurse_assignments_count: Dict[int, int] = {}

    def _unique_email(prefix: str) -> str:
        for _ in range(5):
            email = _rand_email(prefix)
            if not User.objects.filter(email=email).exists():
                return email
        return _rand_email(prefix)

    def _approve_user(u: User) -> None:
        """Mark a user as verified/approved, respecting system constraints."""
        try:
            u.verification_status = 'approved'
        except Exception:
            # Older schemas may miss this field; ignore safely
            pass
        try:
            u.is_verified = True
        except Exception:
            pass
        # Persist any changed flags
        try:
            u.save(update_fields=['verification_status', 'is_verified'])
        except Exception:
            # Fallback if update_fields mismatch; persist full save
            u.save()

    def _rand_current_year_date(start_day_offset: int = 0, end_day_offset: int = 365) -> datetime:
        base = timezone.now().replace(month=1, day=1, hour=9, minute=0, second=0, microsecond=0)
        delta_days = random.randint(start_day_offset, end_day_offset)
        delta_minutes = random.randint(0, 9 * 60)
        return base + timedelta(days=delta_days, minutes=delta_minutes)

    @transaction.atomic
    def _run() -> None:
        # 1) Create staff: doctor and nurse
        doctor_user = _create_user_safe(
            email=_rand_email('doctor'),
            password='DummyPass123!@#',
            full_name=f"Dr. {_filipino_name()}",
            role=User.Role.DOCTOR,
        )
        doctor_user.hospital_name = hospital_name
        doctor_user.hospital_address = hospital_address
        doctor_user.save(update_fields=['hospital_name', 'hospital_address'])
        if verify:
            _approve_user(doctor_user)
        report.add('users', doctor_user.pk)

        doctor_profile = GeneralDoctorProfile.objects.create(
            user=doctor_user,
            license_number=f"LIC-{session_id[:6]}-DR",
            specialization='Internal Medicine'
        )
        report.add('doctor_profiles', doctor_profile.pk)

        # Create multiple nurses with departments and shift schedules
        nurse_profiles: List[NurseProfile] = []
        nurse_departments = ['OPD', 'Pharmacy', 'Appointment', 'ER', 'ICU', 'Pediatrics', 'Surgery']
        for n in range(nurses_count):
            nurse_user = _create_user_safe(
                email=_unique_email('nurse'),
                password='DummyPass123!@#',
                full_name=f"Nurse {_filipino_name()}",
                role=User.Role.NURSE,
            )
            nurse_user.hospital_name = hospital_name
            nurse_user.hospital_address = hospital_address
            nurse_user.save(update_fields=['hospital_name', 'hospital_address'])
            if verify:
                _approve_user(nurse_user)
            report.add('users', nurse_user.pk)

            dept = random.choice(nurse_departments)
            nurse_profile = NurseProfile.objects.create(
                user=nurse_user,
                license_number=f"LIC-{session_id[:6]}-RN-{n+1}",
                department=dept
            )
            nurse_profiles.append(nurse_profile)
            report.add('nurse_profiles', nurse_profile.pk)

            # Create QueueSchedule to represent shift schedule (morning or evening)
            start_t = time(7, 0) if random.choice([True, False]) else time(14, 0)
            end_t = time(15, 0) if start_t.hour == 7 else time(22, 0)
            days = sorted(random.sample(list(range(0, 7)), k=random.choice([5, 6])))
            try:
                QueueSchedule.objects.create(
                    department=(dept if dept in ['OPD', 'Pharmacy', 'Appointment'] else 'OPD'),
                    nurse=nurse_profile,
                    start_time=start_t,
                    end_time=end_t,
                    days_of_week=days,
                    is_active=True,
                    manual_override=False,
                    override_status='auto',
                )
                # No report bucket for schedules; record in metrics summary later
            except Exception:
                # If QueueSchedule fails due to department constraint, skip silently
                pass

        # 2) Create patients
        patients: List[PatientProfile] = []
        for i in range(num_patients):
            p_user = _create_user_safe(
                email=_unique_email('patient'),
                password='DummyPass123!@#',
                full_name=_filipino_name(),
                role=User.Role.PATIENT,
                gender=random.choice(['male', 'female']),
            )
            p_user.hospital_name = hospital_name
            p_user.hospital_address = hospital_address
            p_user.save(update_fields=['hospital_name', 'hospital_address'])
            if verify:
                _approve_user(p_user)
            report.add('users', p_user.pk)

            profile = PatientProfile.objects.create(
                user=p_user,
                blood_type=random.choice([bt for bt, _ in PatientProfile.BloodType.choices]),
                medical_condition=random.choice([
                    'Hypertension (Stage 1)', 'Type 2 Diabetes Mellitus', 'Dyslipidemia',
                    'Bronchial Asthma', 'Gastroesophageal Reflux Disease', 'Healthy'
                ]),
                medication=random.choice(['Lisinopril 10mg daily', 'Metformin 500mg BID', 'None']),
                test_results='CBC normal; Lipids borderline; A1c 6.8%',
                hospital=hospital_name,
                insurance_provider=random.choice(['Blue Shield', 'Medicare', 'Private']),
                room_number=str(100 + i),
                admission_type=random.choice(['scheduled', 'emergency']),
                assigned_doctor=doctor_user,
            )
            patients.append(profile)
            report.add('patient_profiles', profile.pk)

            # Admission/discharge across current year
            admit_dt = _rand_current_year_date(0, 330)
            profile.date_of_admission = admit_dt.date()
            if random.random() < 0.6:  # ~60% discharged
                profile.discharge_date = (admit_dt + timedelta(days=random.randint(1, 10))).date()

            # Nurse-centric forms
            profile.set_nursing_intake({
                'vitals': {'bp': '120/80', 'hr': 72, 'rr': 16, 'temp_c': 36.7, 'o2_sat': 98},
                'weight_kg': round(random.uniform(55, 90), 1),
                'height_cm': round(random.uniform(150, 190), 1),
                'chief_complaint': random.choice(['Routine checkup', 'Follow-up for hypertension', 'Diabetic control', 'Asthma monitoring']),
                'pain_score': random.choice([0, 2, 4]),
                'allergies': [{'substance': 'Penicillin', 'reaction': 'Rash'}],
                'current_medications': ['Vitamin D', 'Aspirin 81mg'],
                'mental_status': 'alert',
                'fall_risk_score': random.choice([0, 10, 20]),
                'assessed_at': timezone.now().isoformat(),
            })
            # Multiple vital monitoring entries throughout the year
            for k in range(random.randint(3, 6)):
                tdt = _rand_current_year_date(10, 360)
                profile.add_flow_sheet_entry({
                    'time_of_reading': tdt.isoformat(),
                    'repeated_vitals': {
                        'bp': random.choice(['118/76', '130/85', '140/90']),
                        'hr': random.choice([68, 72, 80]),
                        'rr': random.choice([16, 18, 20]),
                        'temp_c': round(random.uniform(36.4, 37.8), 1),
                        'o2_sat': random.choice([97, 98, 99]),
                        'pain': random.choice([0, 1, 2, 3]),
                    },
                    'intake_ml': random.choice([250, 500, 750]),
                    'output_ml': random.choice([200, 400, 600]),
                    'site_checks': random.choice(['IV site clean/dry/intact', 'No infiltration noted']),
                    'nursing_interventions': random.choice([
                        ['repositioned patient'], ['guided deep breathing'], ['assisted ambulation']
                    ]),
                    'handoff_note': random.choice(['Stable; continue monitoring', 'BP trending up; notify MD if >140/90']),
                })
            profile.add_mar_entry({
                'datetime_administered': timezone.now().isoformat(),
                'name': 'Acetaminophen',
                'dose': '500 mg',
                'route': 'PO',
                'nurse_initials': 'NT',
                'prn_reason': 'Headache 4/10',
                'prn_response': 'Improved to 2/10',
                'withheld_reason': None,
            })
            # Additional MAR entries
            for m in range(random.randint(1, 3)):
                profile.add_mar_entry({
                    'datetime_administered': _rand_current_year_date(5, 350).isoformat(),
                    'name': random.choice(['Lisinopril', 'Metformin', 'Salbutamol']),
                    'dose': random.choice(['10 mg', '500 mg', '2 puffs']),
                    'route': random.choice(['PO', 'IV', 'Inhalation']),
                    'nurse_initials': 'RN',
                    'prn_reason': random.choice(['Hypertension control', 'Blood sugar control', 'Asthma exacerbation']),
                    'prn_response': random.choice(['Stable', 'Improved']),
                    'withheld_reason': None,
                })
            profile.add_education_entry({
                'topics': ['wound care', 'medication adherence'],
                'teaching_method': 'verbal',
                'comprehension_level': 'good',
                'return_demonstration': 'successful',
                'barriers_to_learning': ['none'],
                'recorded_at': timezone.now().isoformat(),
            })
            profile.set_discharge_summary({
                'discharge_vitals': {'bp': '118/76', 'hr': 70},
                'understanding_confirmed': True,
                'written_instructions_provided': True,
                'follow_up_appointments_made': True,
                'equipment_needs': [],
                'transportation_status': 'self',
                'nurse_signature': nurse_user.full_name,
                'patient_acknowledgment': True,
                'discharged_at': timezone.now().isoformat(),
            })

            # Doctor-centric forms
            profile.add_hp_form({
                'patient_name': profile.user.full_name,
                'dob': (profile.user.date_of_birth.isoformat() if profile.user.date_of_birth else '1980-01-01'),
                'mrn': f"MRN-{session_id[:6]}-{i+1}",
                'provider_signature': doctor_user.full_name,
                'provider_id': str(doctor_user.id),
                'chief_complaint': random.choice(['Routine checkup', 'Elevated BP', 'DM follow-up', 'Asthmatic cough']),
                'history_present_illness': 'Patient presents for annual review.',
                'past_medical_history': profile.medical_condition,
                'social_history': 'Non-smoker; occasional alcohol',
                'review_of_systems': {'cardiovascular': 'negative', 'respiratory': 'negative'},
                'physical_exam': 'Well-appearing, normal exam',
                'assessment': 'Stable chronic conditions',
                'diagnoses_icd_codes': ['I10'],
                'initial_plan': 'Continue current regimen',
                'created_at': timezone.now().isoformat(),
            })
            profile.add_progress_note({
                # Use 'date_time' to satisfy validator; keep current-year distribution
                'date_time': _rand_current_year_date(1, 340).isoformat(),
                'subjective': 'Feels well',
                'objective': 'VS stable',
                'vitals': {'bp': '118/76', 'hr': '70', 'temp': '36.6'},
                'lab_imaging_results': 'CBC normal',
                'assessment': 'Hypertension stable',
                'plan': 'Maintain meds; lifestyle counseling',
                'follow_up_date': (_dt(days_ahead=30).date().isoformat()),
                'provider_signature': doctor_user.full_name,
                'created_at': timezone.now().isoformat(),
            })
            profile.add_provider_order({
                'ordering_provider': doctor_user.full_name,
                'date_time_placed': timezone.now().isoformat(),
                'order_type': 'medication',
                'medication_orders': [{'drug_name': 'Lisinopril', 'dose': '10mg', 'route': 'PO', 'frequency': 'daily'}],
                'diagnostic_orders': [{'test_name': 'CBC', 'priority': 'routine', 'reason': 'monitoring'}],
                'consultation_orders': [{'specialty': 'cardiology', 'question': 'evaluate hypertension'}],
                'general_orders': ['low sodium diet'],
                'order_status': 'new',
                'created_at': timezone.now().isoformat(),
            })
            profile.add_operative_report({
                'patient_id': str(profile.user.id),
                'date_time_performed': timezone.now().isoformat(),
                'procedure_name': 'Skin lesion excision',
                'indications': 'suspicious lesion',
                'consent_status': 'obtained',
                'anesthesia_type': 'local',
                'anesthesia_dose': 'lidocaine 10ml',
                'procedure_steps': 'prep, excision, closure',
                'findings': 'benign appearing',
                'complications': 'none',
                'disposition_plan': 'home',
                # Use 'surgeon_signature' to match validator/tests
                'surgeon_signature': doctor_user.full_name,
                'created_at': timezone.now().isoformat(),
            })

            # Validate JSON form minimal checks
            valid_nurse, nurse_errors = profile.validate_nurse_forms_minimal()
            if not valid_nurse:
                report.errors.extend([f"patient {profile.pk}: {e}" for e in nurse_errors])
            valid_doc, doc_errors = profile.validate_doctor_forms_minimal()
            if not valid_doc:
                report.errors.extend([f"patient {profile.pk}: {e}" for e in doc_errors])

            profile.save()

            # 3) Appointments per patient spanning current year (future dates)
            for j in range(appointments_per_patient):
                # Ensure appointment_date is in the future and within the current year
                dt_appt = _rand_future_datetime_within_year(60)
                # Ensure unique queue number with robust randomization
                attempts = 0
                base_q = random.randint(1000, 999999)
                while AppointmentManagement.objects.filter(queue_number=base_q).exists():
                    base_q = random.randint(1000, 999999)
                    attempts += 1
                    if attempts > 50:
                        # As a final fallback, monotonic increment from a high base
                        base_q = int(timezone.now().timestamp())
                        if not AppointmentManagement.objects.filter(queue_number=base_q).exists():
                            break
                appt = AppointmentManagement.objects.create(
                    patient=profile,
                    doctor=doctor_profile,
                    appointment_date=dt_appt,
                    appointment_type='consultation',
                    appointment_time=_safe_time(dt_appt),
                    queue_number=base_q,
                )
                report.add('appointments', appt.pk)

            # 4) PatientAssignment & ConsultationNotes
            # Assign a random nurse as assigning staff to reflect nurse-patient relationship
            assigned_nurse = random.choice(nurse_profiles) if nurse_profiles else None
            assign = PatientAssignment.objects.create(
                patient=profile,
                doctor=doctor_profile,
                assigned_by=(assigned_nurse.user if assigned_nurse else doctor_user),
                specialization_required='Internal Medicine',
                assignment_reason='Initial assessment',
                status='accepted',
                priority='medium',
            )
            report.add('assignments', assign.pk)
            if assigned_nurse:
                nurse_assignments_count[assigned_nurse.pk] = nurse_assignments_count.get(assigned_nurse.pk, 0) + 1
            notes = ConsultationNotes.objects.create(
                assignment=assign,
                doctor=doctor_profile,
                patient=profile,
                chief_complaint='Routine checkup',
                history_of_present_illness='Annual follow-up visit',
                physical_examination='Normal findings',
                diagnosis='Hypertension',
                treatment_plan='Continue meds; diet/exercise',
                medications_prescribed='Lisinopril 10mg daily',
                follow_up_instructions='Return in 1 month',
                additional_notes=random.choice(['No acute issues', 'Handoff received from night shift', 'Patient educated on medication adherence']),
                status='completed',
            )
            report.add('consultation_notes', notes.pk)



        # Metrics
        # Role distribution among created users
        role_counts: Dict[str, int] = {
            'doctor': User.objects.filter(pk__in=created_objects.get('users', []), role=User.Role.DOCTOR).count(),
            'nurse': User.objects.filter(pk__in=created_objects.get('users', []), role=User.Role.NURSE).count(),
            'patient': User.objects.filter(pk__in=created_objects.get('users', []), role=User.Role.PATIENT).count(),
        }

        # Verify flags confirmation across created users
        verified_count = User.objects.filter(
            pk__in=created_objects.get('users', []),
            verification_status='approved',
            is_verified=True,
        ).count()
        all_verified = verified_count == len(created_objects.get('users', [])) if created_objects.get('users') else True

        report.metrics = {
            'doctor_user_id': doctor_user.pk,
            'nurses_total': len(nurse_profiles),
            'patients_total': len(patients),
            'appointments_total': len(created_objects.get('appointments', [])),
            'assignments_total': len(created_objects.get('assignments', [])),
            'notes_total': len(created_objects.get('consultation_notes', [])),
            'hospital_contact': {'phone': hospital_phone, 'email': hospital_email},
            'nurse_patient_map': nurse_assignments_count,
            'role_counts': role_counts,
            'verified_users_total': verified_count,
            'all_users_verified': all_verified,
        }

        if dry_run:
            # Rollback everything for dry run
            logger.info("Dry run enabled; rolling back transaction.")
            raise transaction.TransactionManagementError("Dry run rollback")

    try:
        _run()
    except transaction.TransactionManagementError:
        # Expected rollback for dry_run
        logger.info("Dry run rollback completed.")
    except Exception as e:
        logger.exception("Dummy data population failed: %s", e)
        report.errors.append(str(e))

    # Optional cleanup (delete created records)
    if cleanup and not dry_run:
        # Delete child-first to satisfy FKs
        ConsultationNotes.objects.filter(pk__in=created_objects.get('consultation_notes', [])).delete()
        PatientAssignment.objects.filter(pk__in=created_objects.get('assignments', [])).delete()
        AppointmentManagement.objects.filter(pk__in=created_objects.get('appointments', [])).delete()
        PatientProfile.objects.filter(pk__in=created_objects.get('patient_profiles', [])).delete()
        GeneralDoctorProfile.objects.filter(pk__in=created_objects.get('doctor_profiles', [])).delete()
        NurseProfile.objects.filter(pk__in=created_objects.get('nurse_profiles', [])).delete()
        User.objects.filter(pk__in=created_objects.get('users', [])).delete()
        logger.info("Cleanup completed for session %s", session_id)

    return report.summary()