from django.test import TestCase
from rest_framework.test import APIClient

from backend.analytics.models import AnalyticsResult
from backend.users.models import User, PatientProfile
from datetime import date
from backend.analytics.tasks import process_data_update_analytics
from backend.users.models import GeneralDoctorProfile
from backend.operations.models import PatientAssignment, ConsultationNotes, PsychiatricOpdQuestionnaire
import unittest

try:
    from backend.analytics.predictive_analytics import build_clinical_analytics_dataframe
    _PANDAS_AVAILABLE = True
except Exception:
    build_clinical_analytics_dataframe = None
    _PANDAS_AVAILABLE = False


class PatientVolumeAnalyticsParityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.nurse = User.objects.create_user(
            email="nurse_volume@example.com",
            password="Password123",
            role=User.Role.NURSE,
            full_name="Nurse Volume",
        )
        self.doctor = User.objects.create_user(
            email="doctor_volume@example.com",
            password="Password123",
            role=User.Role.DOCTOR,
            full_name="Doctor Volume",
        )

        AnalyticsResult.objects.create(
            analysis_type="patient_volume_prediction",
            status="completed",
            results={
                "evaluation_metrics": {"mae": 1.0, "rmse": 2.0},
                "comparison_data": [
                    {"date": "2024-01", "Forecasted": 45, "Actual": 42},
                    {"date": "2024-02", "Forecasted": 52, "Actual": 50},
                ],
            },
        )

    def test_nurse_analytics_endpoint_no_500(self):
        self.client.force_authenticate(user=self.nurse)
        resp = self.client.get("/analytics/nurse/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data.get("success"))

    def test_patient_volume_endpoint_returns_normalized_schema(self):
        self.client.force_authenticate(user=self.nurse)
        resp = self.client.get("/analytics/patient-volume/")
        self.assertEqual(resp.status_code, 200)
        payload = resp.data.get("data") or {}
        vp = payload.get("volume_prediction") or {}
        self.assertIsInstance(vp, dict)
        self.assertIn("forecasted_data", vp)
        self.assertIsInstance(vp["forecasted_data"], list)
        self.assertEqual(vp["forecasted_data"][0]["date"], "2024-01")
        self.assertIn("predicted_volume", vp["forecasted_data"][0])
        self.assertIn("actual_volume", vp["forecasted_data"][0])

    def test_patient_volume_endpoint_is_identical_for_doctor_and_nurse(self):
        self.client.force_authenticate(user=self.nurse)
        nurse_resp = self.client.get("/analytics/patient-volume/")
        self.assertEqual(nurse_resp.status_code, 200)
        nurse_vp = (nurse_resp.data.get("data") or {}).get("volume_prediction")

        self.client.force_authenticate(user=self.doctor)
        doctor_resp = self.client.get("/analytics/patient-volume/")
        self.assertEqual(doctor_resp.status_code, 200)
        doctor_vp = (doctor_resp.data.get("data") or {}).get("volume_prediction")

        self.assertEqual(nurse_vp, doctor_vp)

    def test_patient_volume_endpoint_allows_mixed_case_roles(self):
        mixed_doctor = User.objects.create_user(
            email="doctor_mixedcase@example.com",
            password="Password123",
            role="Doctor",
            full_name="Doctor Mixed",
        )
        self.client.force_authenticate(user=mixed_doctor)
        resp = self.client.get("/analytics/patient-volume/")
        self.assertEqual(resp.status_code, 200)


class NurseAnalyticsDataAvailabilityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.nurse = User.objects.create_user(
            email="nurse_analytics_access@example.com",
            password="Password123",
            role=User.Role.NURSE,
            full_name="Nurse Analytics",
        )

        self.patient = User.objects.create_user(
            email="patient_analytics_access@example.com",
            password="Password123",
            role=User.Role.PATIENT,
            full_name="Patient Analytics",
            gender="Female",
            date_of_birth=date(1995, 1, 1),
        )
        PatientProfile.objects.create(
            user=self.patient,
            medical_condition="Hypertension",
            medication="Metformin, Aspirin",
        )

        AnalyticsResult.objects.all().delete()

    def test_nurse_analytics_returns_core_sections_when_patient_profiles_exist(self):
        self.client.force_authenticate(user=self.nurse)
        resp = self.client.get("/analytics/nurse/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn((resp.data or {}).get("data_source"), ["database", "mixed", "seed"])
        data = resp.data.get("data") or {}

        self.assertIsInstance(data.get("patient_demographics"), dict)
        self.assertIsInstance(data.get("health_trends"), dict)
        self.assertIsInstance(data.get("medication_analysis"), dict)

        meds = data.get("medication_analysis") or {}
        self.assertTrue(bool(meds.get("medication_pareto_data")))


class DoctorAnalyticsFallbackTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.doctor = User.objects.create_user(
            email="doctor_analytics_fetch@example.com",
            password="Password123",
            role=User.Role.DOCTOR,
            full_name="Doctor Analytics Fetch",
        )

    def test_doctor_analytics_falls_back_to_seed_or_mixed_when_empty(self):
        self.client.force_authenticate(user=self.doctor)
        resp = self.client.get("/analytics/doctor/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data.get("success"))
        self.assertIn(resp.data.get("data_source"), ["seed", "mixed", "database"])
        data = resp.data.get("data") or {}
        self.assertIsInstance(data.get("patient_demographics"), dict)
        self.assertIsInstance(data.get("health_trends"), dict)


@unittest.skipUnless(_PANDAS_AVAILABLE, "pandas is required for clinical analytics dataframe tests")
class ClinicalAnalyticsFormIngestionTests(TestCase):
    def setUp(self):
        self.patient_user = User.objects.create_user(
            email="patient_forms_ingest@example.com",
            password="Password123",
            role=User.Role.PATIENT,
            full_name="Patient Ingest",
            gender="Female",
            date_of_birth=date(1990, 1, 1),
        )
        self.patient_profile = PatientProfile.objects.create(user=self.patient_user)

        self.nurse_user = User.objects.create_user(
            email="nurse_forms_ingest@example.com",
            password="Password123",
            role=User.Role.NURSE,
            full_name="Nurse Ingest",
        )

        self.doctor_user = User.objects.create_user(
            email="doctor_forms_ingest@example.com",
            password="Password123",
            role=User.Role.DOCTOR,
            full_name="Doctor Ingest",
        )
        self.doctor_profile = GeneralDoctorProfile.objects.create(user=self.doctor_user, specialization="General")

        AnalyticsResult.objects.all().delete()

    def test_build_dataframe_includes_flat_nurse_intake(self):
        self.patient_profile.nursing_intake_assessment = {
            "chief_complaint": "Headache",
            "current_medications": "Paracetamol 500mg",
            "assessed_at": "2026-03-27T10:00:00Z",
        }
        self.patient_profile.save(update_fields=["nursing_intake_assessment"])

        df = build_clinical_analytics_dataframe()
        self.assertFalse(df.empty)
        self.assertTrue(any((str(v).lower().startswith("headache") for v in df["medical_condition"].astype(str).tolist())))
        self.assertTrue(any(("paracetamol" in str(v).lower() for v in df["medication"].astype(str).tolist())))

    def test_build_dataframe_includes_consultation_notes(self):
        assignment = PatientAssignment.objects.create(
            specialization_required="General",
            assignment_reason="Reason",
            status="accepted",
            assigned_by=self.nurse_user,
            doctor=self.doctor_profile,
            patient=self.patient_profile,
        )
        ConsultationNotes.objects.create(
            chief_complaint="Headache",
            history_of_present_illness="2 days",
            physical_examination="Normal",
            diagnosis="Migraine",
            treatment_plan="Rest",
            medications_prescribed="Paracetamol",
            follow_up_instructions="Return if worse",
            additional_notes="",
            status="completed",
            assignment=assignment,
            doctor=self.doctor_profile,
            patient=self.patient_profile,
        )

        df = build_clinical_analytics_dataframe()
        self.assertFalse(df.empty)
        self.assertTrue(any(("migraine" in str(v).lower() for v in df["medical_condition"].astype(str).tolist())))


class AnalyticsUpdateTriggerTests(TestCase):
    def setUp(self):
        self.patient_user = User.objects.create_user(
            email="patient_update_trigger@example.com",
            password="Password123",
            role=User.Role.PATIENT,
            full_name="Patient Trigger",
            gender="Female",
            date_of_birth=date(1990, 1, 1),
        )
        self.patient_profile = PatientProfile.objects.create(user=self.patient_user)
        AnalyticsResult.objects.all().delete()

    def test_process_data_update_creates_analytics_results(self):
        self.patient_profile.nursing_intake_assessment = {
            "chief_complaint": "Fever",
            "current_medications": "Ibuprofen",
            "assessed_at": "2026-03-27T10:00:00Z",
        }
        self.patient_profile.save(update_fields=["nursing_intake_assessment"])

        process_data_update_analytics.apply(args=("PatientProfile", self.patient_profile.id, "update"))

        self.assertTrue(AnalyticsResult.objects.filter(analysis_type="patient_demographics", status="completed").exists())
        self.assertTrue(AnalyticsResult.objects.filter(analysis_type="patient_health_trends", status="completed").exists())
        self.assertTrue(AnalyticsResult.objects.filter(analysis_type="medication_analysis", status="completed").exists())

    def test_completed_consultation_notes_triggers_analytics_results(self):
        nurse_user = User.objects.create_user(
            email="nurse_trigger_notes@example.com",
            password="Password123",
            role=User.Role.NURSE,
            full_name="Nurse Trigger Notes",
        )
        doctor_user = User.objects.create_user(
            email="doctor_trigger_notes@example.com",
            password="Password123",
            role=User.Role.DOCTOR,
            full_name="Doctor Trigger Notes",
        )
        doctor_profile = GeneralDoctorProfile.objects.create(user=doctor_user, specialization="General")

        assignment = PatientAssignment.objects.create(
            specialization_required="General",
            assignment_reason="Reason",
            status="accepted",
            assigned_by=nurse_user,
            doctor=doctor_profile,
            patient=self.patient_profile,
        )
        ConsultationNotes.objects.create(
            chief_complaint="Headache",
            history_of_present_illness="2 days",
            physical_examination="Normal",
            diagnosis="Migraine",
            treatment_plan="Rest",
            medications_prescribed="Paracetamol",
            follow_up_instructions="Return if worse",
            additional_notes="",
            status="completed",
            assignment=assignment,
            doctor=doctor_profile,
            patient=self.patient_profile,
        )

        self.assertTrue(AnalyticsResult.objects.filter(analysis_type="patient_demographics", status="completed").exists())
        self.assertTrue(AnalyticsResult.objects.filter(analysis_type="medication_analysis", status="completed").exists())

    def test_submitted_psych_opd_triggers_analytics_results(self):
        nurse_user = User.objects.create_user(
            email="nurse_trigger_psych@example.com",
            password="Password123",
            role=User.Role.NURSE,
            full_name="Nurse Trigger Psych",
        )
        q = PsychiatricOpdQuestionnaire(
            patient_profile=self.patient_profile,
            created_by=nurse_user,
            status="submitted",
        )
        q.set_payload({"problemChecklist": ["anxiety", "sleep_disturbance"], "problemOther": "panic attacks"})
        q.save()

        self.assertTrue(AnalyticsResult.objects.filter(analysis_type="patient_demographics", status="completed").exists())
        self.assertTrue(AnalyticsResult.objects.filter(analysis_type="problem_checklist", status="completed").exists())
