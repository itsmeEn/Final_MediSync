from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from backend.users.models import User
from backend.operations.models import PatientAssessmentArchive


class PatientAssessmentsEndpointTests(TestCase):
    def setUp(self):
        self.doctor_user = User.objects.create_user(
            email="doctor2@example.com",
            password="StrongPass123",
            full_name="Dr. Assess",
            role=User.Role.DOCTOR,
        )
        self.doctor_user.hospital_name = "City Hospital"
        self.doctor_user.save()

        self.patient_user = User.objects.create_user(
            email="patient2@example.com",
            password="StrongPass123",
            full_name="Patient Two",
            role=User.Role.PATIENT,
        )

        PatientAssessmentArchive.objects.create(
            user=self.patient_user,
            archived_by=self.doctor_user,
            assessment_type="Nurse Intake",
            medical_condition="Hypertension",
            medical_history_summary="No known allergies",
            assessment_data={"bp": "130/85"},
            diagnostics={"notes": "Stable"},
            last_assessed_at=timezone.now(),
            hospital_name="City Hospital",
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.doctor_user)

    def test_completed_status_returns_archives(self):
        url = "/api/operations/patient-assessments/?status=completed"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("results", data)
        self.assertIn("count", data)
        self.assertEqual(data["count"], 1)
        rec = data["results"][0]
        for key in [
            "assessment_type",
            "medical_condition",
            "medical_history_summary",
            "assessment_data",
            "diagnostics",
            "last_assessed_at",
            "hospital_name",
        ]:
            self.assertIn(key, rec)

    def test_in_progress_status_returns_empty(self):
        url = "/api/operations/patient-assessments/?status=in_progress"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["results"], [])
