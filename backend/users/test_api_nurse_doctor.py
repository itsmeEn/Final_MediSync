from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from backend.users.models import User, PatientProfile


class NurseDoctorAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Create users
        self.nurse = User.objects.create_user(
            email="nurse@example.com",
            password="Password123",
            role=User.Role.NURSE,
            full_name="Nurse Joy",
        )
        self.doctor = User.objects.create_user(
            email="doctor@example.com",
            password="Password123",
            role=User.Role.DOCTOR,
            full_name="Dr. Smith",
        )
        self.other_doctor = User.objects.create_user(
            email="other_doctor@example.com",
            password="Password123",
            role=User.Role.DOCTOR,
            full_name="Dr. Jones",
        )
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="Password123",
            role=User.Role.ADMIN,
            full_name="Admin User",
        )

        # Create patient and profile
        self.patient_user = User.objects.create_user(
            email="patient@example.com",
            password="Password123",
            role=User.Role.PATIENT,
            full_name="John Patient",
        )
        self.profile = PatientProfile.objects.create(user=self.patient_user)

        # Seed nursing intake
        intake = {
            "vitals": {"bp": "120/80", "hr": 72, "rr": 16, "temp_c": 36.8, "o2_sat": 98},
            "chief_complaint": "Headache",
            "pain_score": 5,
            "assessed_at": timezone.now().isoformat(),
        }
        self.profile.set_nursing_intake(intake)
        self.profile.save()

    def test_nurse_can_submit_intake_and_validation_errors(self):
        # Authenticate as nurse
        self.client.force_authenticate(user=self.nurse)
        # Valid PUT
        valid_payload = {
            "vitals": {"bp": "118/76", "hr": 70, "rr": 15, "temp_c": 36.7, "o2_sat": 99},
            "chief_complaint": "Dizziness",
            "pain_score": 3,
            "assessed_at": timezone.now().isoformat(),
        }
        resp = self.client.put(
            f"/users/nurse/patient/{self.profile.id}/intake/",
            data=valid_payload,
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data.get("success"))

        # Invalid PUT (pain_score out of range)
        invalid_payload = dict(valid_payload)
        invalid_payload["pain_score"] = 12
        resp_bad = self.client.put(
            f"/users/nurse/patient/{self.profile.id}/intake/",
            data=invalid_payload,
            format="json",
        )
        self.assertEqual(resp_bad.status_code, 400)
        self.assertFalse(resp_bad.data.get("success"))

    def test_doctor_get_nurse_intake_requires_authorization(self):
        # Other doctor (not assigned) should be forbidden
        self.client.force_authenticate(user=self.other_doctor)
        resp_forbidden = self.client.get(
            f"/users/doctor/patient/{self.profile.id}/nurse-intake/"
        )
        self.assertEqual(resp_forbidden.status_code, 403)

        # Assign patient to doctor and allow access
        self.profile.assigned_doctor_id = self.doctor.id
        self.profile.save(update_fields=["assigned_doctor"])
        self.client.force_authenticate(user=self.doctor)
        resp_ok = self.client.get(
            f"/users/doctor/patient/{self.profile.id}/nurse-intake/"
        )
        self.assertEqual(resp_ok.status_code, 200)
        self.assertTrue(resp_ok.data.get("success"))
        self.assertIsInstance(resp_ok.data.get("data"), dict)

        # Admin can access any patient
        self.client.force_authenticate(user=self.admin)
        resp_admin = self.client.get(
            f"/users/doctor/patient/{self.profile.id}/nurse-intake/"
        )
        self.assertEqual(resp_admin.status_code, 200)
        self.assertTrue(resp_admin.data.get("success"))
