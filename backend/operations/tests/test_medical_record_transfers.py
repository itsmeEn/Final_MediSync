from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from backend.users.models import User, PatientProfile, GeneralDoctorProfile
from backend.operations.models import PatientAssignment, ConsultationNotes, MedicalRecordTransfer


class MedicalRecordTransferFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.doctor_user = User.objects.create_user(
            email="doctor.transfer@example.com",
            password="Testpass123",
            full_name="Test Doctor",
            role=User.Role.DOCTOR,
            verification_status="approved",
        )
        self.doctor_profile = GeneralDoctorProfile.objects.create(
            user=self.doctor_user,
            specialization="Psychiatry",
            license_number="LIC-12345",
        )

        self.patient_user = User.objects.create_user(
            email="patient.transfer@example.com",
            password="Testpass123",
            full_name="Test Patient",
            role=User.Role.PATIENT,
            verification_status="approved",
        )
        self.patient_profile = PatientProfile.objects.create(user=self.patient_user)

        self.assignment = PatientAssignment.objects.create(
            assigned_by=self.doctor_user,
            doctor=self.doctor_profile,
            patient=self.patient_profile,
            specialization_required="Psychiatry",
            assignment_reason="UAT test",
            status="accepted",
            priority="medium",
        )

        self.notes = ConsultationNotes.objects.create(
            chief_complaint="Headache",
            history_of_present_illness="For 3 days",
            physical_examination="Normal",
            diagnosis="Migraine",
            treatment_plan="Rest and hydration",
            medications_prescribed="Paracetamol",
            follow_up_instructions="Follow up in 1 week",
            additional_notes="",
            status="completed",
            completed_at=timezone.now(),
            assignment=self.assignment,
            doctor=self.doctor_profile,
            patient=self.patient_profile,
        )

        self.client.force_authenticate(user=self.doctor_user)

    def test_preview_requires_diagnoses(self):
        resp = self.client.post(
            "/operations/doctor/medical-records/preview/",
            {"patient_id": self.patient_user.id},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data.get("success"))
        self.assertTrue(isinstance(resp.data.get("diagnoses"), list))
        self.assertGreaterEqual(len(resp.data["diagnoses"]), 1)

    def test_preview_returns_400_when_no_diagnoses(self):
        ConsultationNotes.objects.filter(id=self.notes.id).update(diagnosis="")
        resp = self.client.post(
            "/operations/doctor/medical-records/preview/",
            {"patient_id": self.patient_user.id},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data.get("code"), "ERR_MISSING_DIAGNOSES")

    def test_send_requires_confirm(self):
        resp = self.client.post(
            "/operations/doctor/medical-records/send/",
            {"patient_id": self.patient_user.id},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_send_creates_transfer_and_status_and_password(self):
        resp = self.client.post(
            "/operations/doctor/medical-records/send/",
            {"patient_id": self.patient_user.id, "confirm": True, "assignment_id": self.assignment.id},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data.get("success"))
        transfer_id = resp.data.get("transfer_id")
        self.assertTrue(transfer_id)

        transfer = MedicalRecordTransfer.objects.filter(id=transfer_id).first()
        self.assertIsNotNone(transfer)
        self.assertEqual(transfer.sender_id, self.doctor_user.id)
        self.assertEqual(transfer.receiver_id, self.patient_user.id)
        self.assertTrue(bool(transfer.document_number))
        self.assertTrue(bool(transfer.encrypted_password))

        status_resp = self.client.get(f"/operations/medical-record-transfers/{transfer_id}/status/")
        self.assertEqual(status_resp.status_code, 200)
        self.assertEqual(status_resp.data.get("id"), transfer_id)
        self.assertIn(status_resp.data.get("email_delivery_status"), ["pending", "sent", "failed"])

        pw_resp = self.client.get(f"/operations/medical-record-transfers/{transfer_id}/password/")
        self.assertEqual(pw_resp.status_code, 200)
        self.assertTrue(bool(pw_resp.data.get("password")))

        patient_client = APIClient()
        patient_client.force_authenticate(user=self.patient_user)
        pw_resp_patient = patient_client.get(f"/operations/medical-record-transfers/{transfer_id}/password/")
        self.assertEqual(pw_resp_patient.status_code, 200)

    def test_send_rate_limited_by_cooldown(self):
        first = self.client.post(
            "/operations/doctor/medical-records/send/",
            {"patient_id": self.patient_user.id, "confirm": True},
            format="json",
        )
        self.assertEqual(first.status_code, 200)
        second = self.client.post(
            "/operations/doctor/medical-records/send/",
            {"patient_id": self.patient_user.id, "confirm": True},
            format="json",
        )
        self.assertEqual(second.status_code, 429)

