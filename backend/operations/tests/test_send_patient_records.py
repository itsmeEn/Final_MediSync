from django.test import TestCase
from rest_framework.test import APIClient

from backend.users.models import User, PatientProfile
from backend.operations.models import Notification


class SendPatientRecordsTests(TestCase):
    def setUp(self):
        self.nurse = User.objects.create_user(
            email="nurse.send@example.com",
            password="StrongPass123",
            full_name="Nurse Sender",
            role=User.Role.NURSE,
        )
        self.doctor = User.objects.create_user(
            email="doctor.send@example.com",
            password="StrongPass123",
            full_name="Dr Receiver",
            role=User.Role.DOCTOR,
        )
        self.patient_user = User.objects.create_user(
            email="patient.send@example.com",
            password="StrongPass123",
            full_name="Patient Send",
            role=User.Role.PATIENT,
        )
        self.patient_profile = PatientProfile.objects.create(user=self.patient_user, blood_type="O+", medical_condition="None")

        self.client = APIClient()
        self.client.force_authenticate(self.nurse)

    def test_send_records_assigns_doctor_and_creates_notification(self):
        resp = self.client.post(
            "/api/operations/nurse/send-records/",
            {"patient_id": self.patient_profile.id, "doctor_id": self.doctor.id, "message": "Please review."},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.patient_profile.refresh_from_db()
        self.assertEqual(self.patient_profile.assigned_doctor_id, self.doctor.id)
        self.assertTrue(Notification.objects.filter(user=self.doctor, message__icontains="sent patient records").exists())
