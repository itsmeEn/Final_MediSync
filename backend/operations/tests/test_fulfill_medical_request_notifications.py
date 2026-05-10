import tempfile

from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from backend.users.models import User, PatientProfile, GeneralDoctorProfile
from backend.operations.models import MedicalRequest, Notification


class FulfillMedicalRequestNotificationTests(TestCase):
    def setUp(self):
        self.doctor_user = User.objects.create_user(
            email="doctor.fulfill@example.com",
            password="StrongPass123",
            full_name="Dr Fulfill",
            role=User.Role.DOCTOR,
        )
        self.doctor_profile = GeneralDoctorProfile.objects.create(
            user=self.doctor_user,
            specialization="General Medicine",
            available_for_consultation=True,
            license_number="LIC-FUL-001",
        )

        self.patient_user = User.objects.create_user(
            email="patient.fulfill@example.com",
            password="StrongPass123",
            full_name="Patient Fulfill",
            role=User.Role.PATIENT,
        )
        self.patient_profile = PatientProfile.objects.create(user=self.patient_user, blood_type="O+", medical_condition="None")

        self.req = MedicalRequest.objects.create(
            requested_by=self.patient_user,
            patient=self.patient_profile,
            doctor=self.doctor_profile,
            request_medical_certificate=True,
            request_prescription=True,
            status="pending",
        )

        self.client = APIClient()
        self.client.force_authenticate(self.doctor_user)

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_fulfill_sends_patient_in_app_notice_when_email_sent(self):
        payload = {
            "doctor_message": "OK",
            "certificate": {
                "leave_start_date": "2026-04-30",
                "leave_end_date": "2026-05-02",
                "diagnosis": "Test Diagnosis",
            },
            "prescription": {
                "medications": [
                    {
                        "drug_name": "Drug A",
                        "dosage": "10 mg",
                        "frequency": "Once daily",
                        "duration": "3 days",
                        "instructions": "After meals",
                    }
                ]
            },
        }

        with patch("backend.operations.views.EmailMessage.send", return_value=1), override_settings(
            EMAIL_BACKEND="anymail.backends.sendgrid.EmailBackend"
        ):
            resp = self.client.post(f"/operations/medical-requests/{self.req.id}/fulfill/", payload, format="json")

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("success", False))
        self.assertEqual(resp.json().get("email_sent"), True)
        self.assertTrue(Notification.objects.filter(user=self.patient_user, message__icontains="sent to your email").exists())

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_fulfill_marks_email_not_sent_when_console_backend(self):
        payload = {
            "doctor_message": "OK",
            "certificate": {
                "leave_start_date": "2026-04-30",
                "leave_end_date": "2026-05-02",
                "diagnosis": "Test Diagnosis",
            },
            "prescription": {
                "medications": [
                    {
                        "drug_name": "Drug A",
                        "dosage": "10 mg",
                        "frequency": "Once daily",
                        "duration": "3 days",
                        "instructions": "After meals",
                    }
                ]
            },
        }

        with patch("backend.operations.views.EmailMessage.send", return_value=1), override_settings(
            EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend"
        ):
            resp = self.client.post(f"/operations/medical-requests/{self.req.id}/fulfill/", payload, format="json")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("email_sent"), False)
        self.assertEqual(resp.json().get("email_reason"), "email_backend_not_configured")
        self.assertTrue(Notification.objects.filter(user=self.patient_user, message__icontains="Email delivery is not configured").exists())

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_fulfill_requires_doctor_advice_for_medical_certificate(self):
        payload = {
            "doctor_message": "",
            "certificate": {
                "leave_start_date": "2026-04-30",
                "leave_end_date": "2026-05-02",
                "diagnosis": "Test Diagnosis",
            },
        }
        resp = self.client.post(f"/operations/medical-requests/{self.req.id}/fulfill/", payload, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("required", str(resp.json().get("error", "")).lower())
