from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from django.core.management import call_command

from backend.analytics.models import AnalyticsResult, PatientRecord
from backend.users.models import User, PatientProfile
from datetime import date, timedelta, datetime
from django.utils import timezone
from backend.analytics.tasks import process_data_update_analytics
from backend.users.models import GeneralDoctorProfile
from backend.operations.models import PatientAssignment, ConsultationNotes, PsychiatricOpdQuestionnaire
import unittest
from backend.analytics.views import compute_patient_demographics_from_records, compute_medication_analysis_from_records
from django.core.cache import cache

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

    def test_patient_volume_endpoint_year_param_returns_12_months(self):
        self.client.force_authenticate(user=self.nurse)
        resp = self.client.get("/analytics/patient-volume/?year=2024")
        self.assertEqual(resp.status_code, 200)
        payload = resp.data.get("data") or {}
        vp = payload.get("volume_prediction") or {}
        self.assertIsInstance(vp, dict)
        fd = vp.get("forecasted_data")
        self.assertIsInstance(fd, list)
        self.assertEqual(len(fd), 12)
        self.assertEqual(fd[0]["date"], "2024-01")
        self.assertEqual(fd[-1]["date"], "2024-12")
        self.assertIn("predicted_volume", fd[0])
        self.assertIn("actual_volume", fd[0])

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


class MedicationAnalysisRecommendationSourceTests(TestCase):
    def test_medication_analysis_uses_doctor_consultation_notes_medications(self):
        nurse_user = User.objects.create_user(
            email="nurse_medrec@example.com",
            password="Password123",
            role=User.Role.NURSE,
            full_name="Nurse Med",
        )

        doctor_user = User.objects.create_user(
            email="doctor_medrec@example.com",
            password="Password123",
            role=User.Role.DOCTOR,
            full_name="Doctor Med",
        )
        doctor_profile = GeneralDoctorProfile.objects.create(user=doctor_user, specialization="General Practice")

        patient_user = User.objects.create_user(
            email="patient_medrec@example.com",
            password="Password123",
            role=User.Role.PATIENT,
            full_name="Patient Med",
        )
        patient_profile = PatientProfile.objects.create(user=patient_user)

        assignment = PatientAssignment.objects.create(
            specialization_required="General Practice",
            assignment_reason="Test",
            status="completed",
            priority="medium",
            assigned_by=nurse_user,
            doctor=doctor_profile,
            patient=patient_profile,
        )

        ConsultationNotes.objects.create(
            chief_complaint="Cough",
            history_of_present_illness="Test HPI",
            physical_examination="Normal",
            diagnosis="URI",
            treatment_plan="Supportive care",
            medications_prescribed="Lorazepam 1mg Tablet; Lorazepam 1mg Tablet",
            follow_up_instructions="Return if worse",
            additional_notes="",
            status="completed",
            completed_at=timezone.now(),
            assignment=assignment,
            doctor=doctor_profile,
            patient=patient_profile,
        )

        AnalyticsResult.objects.filter(analysis_type="medication_analysis").delete()
        PatientRecord.objects.all().delete()

        out = compute_medication_analysis_from_records()
        self.assertIsInstance(out, dict)
        self.assertEqual(out.get("source"), "consultation_notes")
        pareto = out.get("medication_pareto_data") or []
        self.assertTrue(pareto)
        top = pareto[0]
        self.assertEqual(top.get("medication"), "Lorazepam (Ativan)")
        self.assertEqual(int(top.get("frequency") or 0), 2)


class MedicationAnalysisOnlyEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.nurse = User.objects.create_user(
            email="nurse_medonly@example.com",
            password="Password123",
            role=User.Role.NURSE,
            full_name="Nurse Med Only",
        )
        self.patient = User.objects.create_user(
            email="patient_medonly@example.com",
            password="Password123",
            role=User.Role.PATIENT,
            full_name="Patient Med Only",
        )

    def test_medication_analysis_only_endpoint_returns_medication_fields_only(self):
        self.client.force_authenticate(user=self.nurse)
        resp = self.client.get("/analytics/medication-analysis/?top=5")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data.get("success"))
        data = resp.data.get("data") or {}
        self.assertEqual(
            set(data.keys()),
            {
                "medication_pareto_data",
                "total_prescriptions",
                "total_consultations",
                "unique_medications",
                "monthly_trends",
                "diagnosis_breakdown",
                "polypharmacy",
                "route_distribution",
                "safety_signals",
                "effectiveness_proxy",
                "source",
                "generated_at",
            },
        )
        self.assertIsInstance(data.get("medication_pareto_data"), list)
        self.assertLessEqual(len(data["medication_pareto_data"]), 5)

    def test_medication_analysis_only_endpoint_denies_patient(self):
        self.client.force_authenticate(user=self.patient)
        resp = self.client.get("/analytics/medication-analysis/")
        self.assertEqual(resp.status_code, 403)

class VolumeConfidenceEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.nurse = User.objects.create_user(
            email="nurse_volume_conf@example.com",
            password="Password123",
            role=User.Role.NURSE,
            full_name="Nurse Volume Conf",
        )
        patient = User.objects.create_user(
            email="patient_volume_conf@example.com",
            password="Password123",
            role=User.Role.PATIENT,
            full_name="Patient Volume Conf",
        )
        self.patient_profile = PatientProfile.objects.create(user=patient)

        from backend.operations.models import QueueManagement

        base = timezone.now().replace(day=15, hour=10, minute=0, second=0, microsecond=0)
        for i in range(10):
            dt = base - timedelta(days=30 * i)
            QueueManagement.objects.create(
                patient=self.patient_profile,
                queue_number=i + 1,
                department="OPD",
                enqueue_time=dt,
                daily_sequence_number=i + 1,
                position_in_queue=i + 1,
            )

    def test_volume_confidence_endpoint_returns_metrics_and_bounds(self):
        self.client.force_authenticate(user=self.nurse)
        resp = self.client.get("/analytics/volume-confidence/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data.get("success"))
        data = (resp.data.get("data") or {}).get("volume_prediction") or {}
        self.assertIn("evaluation_metrics", data)
        em = data.get("evaluation_metrics") or {}
        self.assertIn("mape", em)
        self.assertIn("rmse", em)
        self.assertIn("forecasted_data", data)
        self.assertIn("risk_assessment", data)
        self.assertIn("ai_summary", data)
        fd = data.get("forecasted_data") or []
        self.assertIsInstance(fd, list)
        if fd:
            row = fd[0]
            self.assertIn("date", row)
            self.assertIn("predicted_volume", row)
            self.assertIn("ci_lower", row)
            self.assertIn("ci_upper", row)
            if row.get("ci_lower") is not None and row.get("ci_upper") is not None:
                self.assertIn("point_confidence", row)
                self.assertIn("point_confidence_rating", row)


class NurseDemographicsFieldRestrictionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.nurse = User.objects.create_user(
            email="nurse_demo_fields@example.com",
            password="Password123",
            role=User.Role.NURSE,
            full_name="Nurse Demo Fields",
        )
        p = User.objects.create_user(
            email="patient_demo_fields@example.com",
            password="Password123",
            role=User.Role.PATIENT,
            full_name="Patient Demo Fields",
            gender="Male",
            date_of_birth=date(1990, 1, 1),
        )
        PatientProfile.objects.create(user=p)

    def test_nurse_analytics_includes_total_and_average_age(self):
        self.client.force_authenticate(user=self.nurse)
        resp = self.client.get("/analytics/nurse/")
        self.assertEqual(resp.status_code, 200)
        data = (resp.data.get("data") or {}).get("patient_demographics") or {}
        self.assertIsInstance(data, dict)
        self.assertIn("total_patients", data)
        self.assertIn("average_age", data)


class PatientVolumeHistorySeedRestorationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.nurse = User.objects.create_user(
            email="nurse_volume_history@example.com",
            password="Password123",
            role=User.Role.NURSE,
            full_name="Nurse Volume History",
        )

    def test_patient_volume_endpoint_refreshes_to_monthly_history(self):
        patient = User.objects.create_user(
            email="patient_volume_history@example.com",
            password="Password123",
            role=User.Role.PATIENT,
            full_name="Patient Volume History",
        )
        PatientProfile.objects.create(user=patient)

        AnalyticsResult.objects.create(
            analysis_type="patient_volume_prediction",
            status="completed",
            results={"comparison_data": [{"date": "2026-05-01", "predicted": 1, "actual": 1}]},
        )

        PatientRecord.objects.create(
            patient=patient,
            date_of_admission=timezone.make_aware(datetime(2026, 1, 15)),
            medical_condition="URI",
            age=30,
            gender="Male",
            medication="X",
        )
        PatientRecord.objects.create(
            patient=patient,
            date_of_admission=timezone.make_aware(datetime(2026, 3, 15)),
            medical_condition="URI",
            age=30,
            gender="Male",
            medication="X",
        )

        self.client.force_authenticate(user=self.nurse)
        resp = self.client.get("/analytics/patient-volume/")
        self.assertEqual(resp.status_code, 200)
        vp = ((resp.data.get("data") or {}).get("volume_prediction") or {})
        rows = vp.get("forecasted_data") or []
        self.assertIsInstance(rows, list)
        labels = [r.get("date") for r in rows if isinstance(r, dict)]
        self.assertIn("2026-01", labels)
        self.assertIn("2026-02", labels)
        self.assertIn("2026-03", labels)

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


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class RiskAssessmentStateTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.nurse = User.objects.create_user(
            email="nurse_risk_state@example.com",
            password="Password123",
            role=User.Role.NURSE,
            full_name="Nurse Risk",
        )
        self.client.force_authenticate(user=self.nurse)
        cache.delete("predictions:risk_assessment_state:v1")

    def test_get_seeds_state_on_empty_cache(self):
        resp = self.client.get("/analytics/risk-assessment/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data.get("success"))
        data = resp.data.get("data") or {}
        self.assertGreaterEqual(int(data.get("version") or 0), 1)
        ra = data.get("risk_assessment") or {}
        self.assertIsInstance(ra, dict)
        self.assertIn("confidence", ra)
        self.assertIn("confidence_label", ra)
        self.assertIn("risks", ra)
        self.assertIsInstance(ra.get("risks"), list)
        if ra.get("risks"):
            r0 = ra.get("risks")[0]
            self.assertIsInstance(r0, dict)
            self.assertIn("title", r0)
            self.assertIn("confidence", r0)
            self.assertIn("confidence_label", r0)
            self.assertNotIn("traceability", r0)

    def test_put_returns_conflict_on_version_mismatch(self):
        seed = self.client.get("/analytics/risk-assessment/")
        self.assertEqual(seed.status_code, 200)
        data = seed.data.get("data") or {}
        current_version = int(data.get("version") or 0)
        self.assertGreaterEqual(current_version, 1)

        resp = self.client.put(
            "/analytics/risk-assessment/",
            data={"version": current_version + 1, "risk_assessment": {"overall_risk": "low"}},
            format="json",
        )
        self.assertEqual(resp.status_code, 409)
        self.assertFalse(resp.data.get("success"))
        conflict = resp.data.get("data") or {}
        self.assertEqual(int(conflict.get("server_version") or 0), current_version)
        self.assertIsInstance(conflict.get("server_state") or {}, dict)

    def test_put_updates_state_and_increments_version(self):
        seed = self.client.get("/analytics/risk-assessment/")
        self.assertEqual(seed.status_code, 200)
        data = seed.data.get("data") or {}
        current_version = int(data.get("version") or 0)
        self.assertGreaterEqual(current_version, 1)

        resp = self.client.put(
            "/analytics/risk-assessment/",
            data={
                "version": current_version,
                "risk_assessment": {
                    "overall_risk": "high",
                    "confidence": 92.5,
                    "recommended_actions": [
                        {
                            "id": "a1",
                            "text": "Do something within 24 hours",
                            "priority": "High",
                            "owner": "Nurse Supervisor",
                            "due_by": timezone.now().isoformat(),
                            "review_by": (timezone.now() + timezone.timedelta(days=7)).isoformat(),
                            "success_metric": "Done within 24 hours",
                        }
                    ],
                    "risks": [
                        {
                            "id": "r1",
                            "title": "Test risk",
                            "impact": 5,
                            "likelihood": 4,
                            "business_criticality": 5,
                            "confidence": 88.0,
                        }
                    ],
                },
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        out = resp.data.get("data") or {}
        self.assertEqual(int(out.get("version") or 0), current_version + 1)
        ra = out.get("risk_assessment") or {}
        self.assertEqual(ra.get("overall_risk"), "high")
        self.assertEqual(ra.get("confidence_label"), "High")
        self.assertNotIn("data_sources", ra)
        self.assertNotIn("methodology", ra)
        self.assertNotIn("assumptions", ra)
        self.assertNotIn("traceability", ra)

    def test_confidence_recalculates_from_latest_analytics_for_seed_state(self):
        cache.delete("predictions:risk_assessment_state:v1")

        AnalyticsResult.objects.create(
            analysis_type="patient_volume_prediction",
            status="completed",
            results={
                "evaluation_metrics": {"mape": 35.0, "rmse": 18.0},
                "forecasted_data": [
                    {"date": "2026-01-01", "predicted_volume": 40, "actual_volume": 60, "ci_lower": 10, "ci_upper": 90},
                    {"date": "2026-02-01", "predicted_volume": 55, "actual_volume": 30, "ci_lower": 15, "ci_upper": 110},
                    {"date": "2026-03-01", "predicted_volume": 50, "actual_volume": 70, "ci_lower": 12, "ci_upper": 105},
                    {"date": "2026-04-01", "predicted_volume": 65, "actual_volume": 35, "ci_lower": 18, "ci_upper": 125},
                ],
            },
        )
        AnalyticsResult.objects.create(
            analysis_type="monthly_illness_forecast",
            status="completed",
            results={
                "monthly_illness_forecast": [
                    {"illness": "Condition A", "month": "2026-05", "predicted_cases": 100, "confidence_lower": 40, "confidence_upper": 170},
                    {"illness": "Condition B", "month": "2026-05", "predicted_cases": 80, "confidence_lower": 25, "confidence_upper": 140},
                ]
            },
        )

        r1 = self.client.get("/analytics/risk-assessment/")
        self.assertEqual(r1.status_code, 200)
        ra1 = (r1.data.get("data") or {}).get("risk_assessment") or {}
        c1 = ra1.get("confidence")
        self.assertIsInstance(c1, (int, float))

        AnalyticsResult.objects.create(
            analysis_type="patient_volume_prediction",
            status="completed",
            results={
                "evaluation_metrics": {"mape": 10.0, "rmse": 4.0},
                "forecasted_data": [
                    {"date": "2026-01-01", "predicted_volume": 40, "actual_volume": 41, "ci_lower": 36, "ci_upper": 44},
                    {"date": "2026-02-01", "predicted_volume": 42, "actual_volume": 41, "ci_lower": 38, "ci_upper": 46},
                    {"date": "2026-03-01", "predicted_volume": 41, "actual_volume": 42, "ci_lower": 37, "ci_upper": 45},
                    {"date": "2026-04-01", "predicted_volume": 43, "actual_volume": 42, "ci_lower": 39, "ci_upper": 47},
                ],
            },
        )
        AnalyticsResult.objects.create(
            analysis_type="monthly_illness_forecast",
            status="completed",
            results={
                "monthly_illness_forecast": [
                    {"illness": "Condition A", "month": "2026-05", "predicted_cases": 100, "confidence_lower": 92, "confidence_upper": 108},
                    {"illness": "Condition B", "month": "2026-05", "predicted_cases": 80, "confidence_lower": 74, "confidence_upper": 86},
                ]
            },
        )

        r2 = self.client.get("/analytics/risk-assessment/")
        self.assertEqual(r2.status_code, 200)
        ra2 = (r2.data.get("data") or {}).get("risk_assessment") or {}
        c2 = ra2.get("confidence")
        self.assertIsInstance(c2, (int, float))
        self.assertGreater(float(c2), float(c1))


class AnalyticsSeedGenerationTests(TestCase):
    def test_populate_demo_data_generates_non_empty_dashboard_data(self):
        call_command(
            "populate_demo_data",
            months=24,
            patients=15,
            daily_avg=1.0,
            seed=123,
            clear_analytics=True,
            clear_records=True,
        )

        self.assertGreater(PatientRecord.objects.count(), 0)

        for analysis_type in (
            "patient_demographics",
            "patient_health_trends",
            "patient_volume_prediction",
            "illness_surge_prediction",
            "weekly_illness_forecast",
            "monthly_illness_forecast",
            "medication_analysis",
        ):
            self.assertTrue(
                AnalyticsResult.objects.filter(analysis_type=analysis_type, status="completed").exists(),
                msg=f"Missing AnalyticsResult for {analysis_type}",
            )

        doctor = User.objects.create_user(
            email="seed_doctor@example.com",
            password="Password123",
            role=User.Role.DOCTOR,
            full_name="Seed Doctor",
        )
        nurse = User.objects.create_user(
            email="seed_nurse@example.com",
            password="Password123",
            role=User.Role.NURSE,
            full_name="Seed Nurse",
            verification_status="approved",
        )

        client = APIClient()

        client.force_authenticate(user=doctor)
        d = client.get("/analytics/doctor/")
        self.assertEqual(d.status_code, 200)
        self.assertTrue(d.data.get("success"))
        d_payload = d.data.get("data") or {}
        self.assertIsNotNone(d_payload.get("patient_demographics"))
        self.assertIsNotNone(d_payload.get("health_trends"))
        self.assertIsNotNone(d_payload.get("volume_prediction"))

        client.force_authenticate(user=nurse)
        n = client.get("/analytics/nurse/")
        self.assertEqual(n.status_code, 200)
        self.assertTrue(n.data.get("success"))
        n_payload = n.data.get("data") or {}
        self.assertIsNotNone(n_payload.get("patient_demographics"))
        self.assertIsNotNone(n_payload.get("health_trends"))
        self.assertIsNotNone(n_payload.get("volume_prediction"))
