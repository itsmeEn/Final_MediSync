from django.test import TestCase
from rest_framework.test import APIClient

from backend.analytics.models import AnalyticsResult, PatientRecord
from backend.users.models import User, PatientProfile
from datetime import date, timedelta
from django.utils import timezone
from backend.analytics.tasks import process_data_update_analytics
from backend.users.models import GeneralDoctorProfile
from backend.operations.models import PatientAssignment, ConsultationNotes, PsychiatricOpdQuestionnaire
import unittest
from backend.analytics.views import compute_patient_demographics_from_records

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


class PatientDemographicsComputationTests(TestCase):
    def test_compute_patient_demographics_uses_unique_patients_and_whole_number_age(self):
        p1 = User.objects.create_user(
            email="demo_p1@example.com",
            password="Password123",
            role=User.Role.PATIENT,
            full_name="Demo P1",
            gender="Male",
            date_of_birth=date(2000, 1, 1),
        )
        p2 = User.objects.create_user(
            email="demo_p2@example.com",
            password="Password123",
            role=User.Role.PATIENT,
            full_name="Demo P2",
            gender="Female",
            date_of_birth=date(1990, 1, 1),
        )
        PatientProfile.objects.create(user=p1)
        PatientProfile.objects.create(user=p2)

        now = timezone.now()
        PatientRecord.objects.create(
            patient=p1,
            date_of_admission=now,
            medical_condition="Hypertension",
            age=25,
            gender="Male",
            medication="Aspirin",
        )
        PatientRecord.objects.create(
            patient=p1,
            date_of_admission=now - timedelta(days=10),
            medical_condition="Hypertension",
            age=25,
            gender="Male",
            medication="Aspirin",
        )
        PatientRecord.objects.create(
            patient=p2,
            date_of_admission=now,
            medical_condition="Diabetes",
            age=35,
            gender="Female",
            medication="Metformin",
        )

        out = compute_patient_demographics_from_records()
        self.assertIsInstance(out, dict)
        self.assertEqual(out.get("total_patients"), 2)
        self.assertIsInstance(out.get("average_age"), int)

        today = timezone.now().date()
        a1 = int((today - p1.date_of_birth).days // 365)
        a2 = int((today - p2.date_of_birth).days // 365)
        expected_avg = int(round((a1 + a2) / 2))
        self.assertEqual(out.get("average_age"), expected_avg)


class DoctorAnalyticsDoctorFacingFilteringTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.doctor = User.objects.create_user(
            email="doctor_filtering@example.com",
            password="Password123",
            role=User.Role.DOCTOR,
            full_name="Doctor Filtering",
        )

        AnalyticsResult.objects.create(
            analysis_type="patient_demographics",
            status="completed",
            results={"total_patients": 10, "average_age": 40, "age_distribution": {"19-35": 5}, "gender_proportions": {"Male": 50, "Female": 50}},
        )
        AnalyticsResult.objects.create(
            analysis_type="patient_health_trends",
            status="completed",
            results={"top_illnesses_by_week": [{"medical_condition": "URI", "count": 3, "date_of_admission": "2026-05-01"}]},
        )
        AnalyticsResult.objects.create(
            analysis_type="illness_surge_prediction",
            status="completed",
            results={"forecasted_monthly_cases": [{"date": "2026-06", "total_cases": 12}], "evaluation_metrics": {}},
        )
        AnalyticsResult.objects.create(
            analysis_type="monthly_illness_forecast",
            status="completed",
            results={"monthly_illness_forecast": [{"illness": "URI", "month": "2026-06", "predicted_cases": 5}], "evaluation_metrics": {}},
        )
        AnalyticsResult.objects.create(
            analysis_type="patient_volume_prediction",
            status="completed",
            results={"forecasted_data": [{"date": "2026-06", "predicted_volume": 10, "actual_volume": 9}]},
        )
        AnalyticsResult.objects.create(
            analysis_type="performance_factors",
            status="completed",
            results={"significant_factors": []},
        )
        AnalyticsResult.objects.create(
            analysis_type="ai_insights",
            status="completed",
            results={"recommendations": {"doctors": ["Increase staffing"]}},
        )
        AnalyticsResult.objects.create(
            analysis_type="illness_prediction",
            status="completed",
            results={
                "chi_square_statistic": 6.21,
                "p_value": 0.044,
                "association_result": "Statistically significant association detected (p=0.044).",
                "significant_factors": ["Age group → URI (p<0.05)"],
            },
        )

    def test_doctor_analytics_strips_statistical_test_fields(self):
        self.client.force_authenticate(user=self.doctor)
        resp = self.client.get("/analytics/doctor/")
        self.assertEqual(resp.status_code, 200)
        data = (resp.data or {}).get("data") or {}
        ip = data.get("illness_prediction") or {}
        self.assertIsInstance(ip, dict)
        self.assertNotIn("chi_square_statistic", ip)
        self.assertNotIn("p_value", ip)
        self.assertNotIn("association_result", ip)

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

    def test_time_range_filter_includes_completed_notes_by_completed_at(self):
        assignment = PatientAssignment.objects.create(
            specialization_required="General",
            assignment_reason="Reason",
            status="accepted",
            assigned_by=self.nurse_user,
            doctor=self.doctor_profile,
            patient=self.patient_profile,
        )
        completed_at = timezone.now() - timedelta(days=90)
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
            completed_at=completed_at,
            assignment=assignment,
            doctor=self.doctor_profile,
            patient=self.patient_profile,
        )

        start = (completed_at - timedelta(days=1)).date().isoformat()
        end = (completed_at + timedelta(days=1)).date().isoformat()
        df = build_clinical_analytics_dataframe(start=start, end=end)
        self.assertFalse(df.empty)
        self.assertTrue(any(("migraine" in str(v).lower() for v in df["medical_condition"].astype(str).tolist())))

    def test_time_range_filter_includes_psych_by_submitted_at(self):
        submitted_at = timezone.now() - timedelta(days=120)
        q = PsychiatricOpdQuestionnaire(
            patient_profile=self.patient_profile,
            created_by=self.nurse_user,
            status="submitted",
            submitted_at=submitted_at,
        )
        q.set_payload({"problemChecklist": ["anxiety"], "problemOther": ""})
        q.save()

        start = (submitted_at - timedelta(days=1)).date().isoformat()
        end = (submitted_at + timedelta(days=1)).date().isoformat()
        df = build_clinical_analytics_dataframe(start=start, end=end)
        self.assertFalse(df.empty)
        self.assertTrue(any(("anxiety" in str(v).lower() for v in df["medical_condition"].astype(str).tolist())))


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
