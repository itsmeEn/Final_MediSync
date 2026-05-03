from django.test import TestCase
from rest_framework.test import APIClient

from backend.analytics.models import AnalyticsResult
from backend.users.models import User, PatientProfile
from datetime import date


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
        data = resp.data.get("data") or {}

        self.assertIsInstance(data.get("patient_demographics"), dict)
        self.assertIsInstance(data.get("health_trends"), dict)
        self.assertIsInstance(data.get("medication_analysis"), dict)

        meds = data.get("medication_analysis") or {}
        self.assertTrue(bool(meds.get("medication_pareto_data")))
