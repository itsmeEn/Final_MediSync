from django.test import TestCase
from rest_framework.test import APIClient

from backend.users.models import User, PatientProfile


class NurseIntakeExtendedFieldsTests(TestCase):
    def setUp(self):
        self.nurse = User.objects.create_user(
            email="nurse.intake@example.com",
            password="StrongPass123",
            full_name="Nurse Intake",
            role=User.Role.NURSE,
        )
        self.doctor = User.objects.create_user(
            email="doctor.intake@example.com",
            password="StrongPass123",
            full_name="Dr Intake",
            role=User.Role.DOCTOR,
        )
        self.patient_user = User.objects.create_user(
            email="patient.intake@example.com",
            password="StrongPass123",
            full_name="Patient Intake",
            role=User.Role.PATIENT,
        )
        self.patient_profile = PatientProfile.objects.create(user=self.patient_user, blood_type="O+", medical_condition="None")

    def test_nurse_intake_saves_extended_fields_and_doctor_can_read(self):
        nclient = APIClient()
        nclient.force_authenticate(self.nurse)
        payload = {
            "chief_complaint": "Headache",
            "pain_score": 6,
            "allergies": ["Peanuts"],
            "current_medications": "Paracetamol 500mg",
            "medical_history": "No chronic illness",
            "assessment_notes": "Patient stable",
            "consent_agreed": True,
            "patient_signature": "Guardian Name",
            "signature_date": "2026-03-27",
            "assessed_at": "2026-03-27T10:00:00Z",
        }
        resp = nclient.put(f"/users/nurse/patient/{self.patient_profile.id}/intake/", payload, format="json")
        self.assertEqual(resp.status_code, 200)
        self.patient_profile.refresh_from_db()
        saved = self.patient_profile.nursing_intake_assessment or {}
        for key in ["medical_history", "assessment_notes", "consent_agreed", "patient_signature", "signature_date"]:
            self.assertIn(key, saved)

        self.patient_profile.assigned_doctor = self.doctor
        self.patient_profile.save(update_fields=["assigned_doctor"])

        dclient = APIClient()
        dclient.force_authenticate(self.doctor)
        read_resp = dclient.get(f"/users/doctor/patient/{self.patient_profile.id}/nurse-intake/")
        self.assertEqual(read_resp.status_code, 200)
        read_data = read_resp.json().get("data") or {}
        self.assertEqual(read_data.get("medical_history"), "No chronic illness")

        # Backward-compatible: allow calling doctor endpoints using patient user_id as well
        read_resp2 = dclient.get(f"/users/doctor/patient/{self.patient_user.id}/nurse-intake/")
        self.assertEqual(read_resp2.status_code, 200)
