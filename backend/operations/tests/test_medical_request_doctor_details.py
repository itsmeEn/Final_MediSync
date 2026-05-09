from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from backend.users.models import User, PatientProfile, GeneralDoctorProfile
from backend.operations.models import MedicalRequest, PatientAssignment, ConsultationNotes


class MedicalRequestDoctorDetailsTests(TestCase):
    def setUp(self):
        self.patient_user = User.objects.create_user(
            email="patient.mr.details@example.com",
            password="StrongPass123",
            full_name="Patient MR",
            role=User.Role.PATIENT,
        )
        self.patient_profile = PatientProfile.objects.create(user=self.patient_user, blood_type="O+", medical_condition="None")

        self.doctor_user = User.objects.create_user(
            email="doctor.mr.details@example.com",
            password="StrongPass123",
            full_name="Dr Details",
            role=User.Role.DOCTOR,
            hospital_name="MediSync Hospital",
            hospital_address="123 Health St",
        )
        self.doctor_profile = GeneralDoctorProfile.objects.create(
            user=self.doctor_user,
            specialization="Internal Medicine",
            available_for_consultation=True,
            license_number="LIC-DET-001",
        )

        self.client = APIClient()
        self.client.force_authenticate(self.patient_user)

    def test_patient_medical_requests_includes_doctor_details_when_assigned(self):
        MedicalRequest.objects.create(
            requested_by=self.patient_user,
            patient=self.patient_profile,
            doctor=self.doctor_profile,
            request_medical_certificate=True,
            request_prescription=False,
            status="pending",
        )
        with self.assertLogs("backend.operations.views", level="INFO") as logs:
            resp = self.client.get("/operations/medical-requests/patient/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(len(data.get("results", [])) >= 1)
        item = data["results"][0]
        self.assertEqual(item.get("doctor_status"), "assigned")
        doctor = item.get("doctor")
        self.assertTrue(isinstance(doctor, dict))
        self.assertEqual(doctor.get("name"), "Dr Details")
        self.assertEqual(doctor.get("specialty"), "Internal Medicine")
        self.assertEqual(doctor.get("contact", {}).get("email"), "doctor.mr.details@example.com")
        self.assertEqual(doctor.get("availability", {}).get("available_for_consultation"), True)
        self.assertTrue(any("patient_medical_requests doctor_details_resolved" in m for m in logs.output))

    def test_patient_medical_requests_handles_unassigned_doctor(self):
        MedicalRequest.objects.create(
            requested_by=self.patient_user,
            patient=self.patient_profile,
            doctor=None,
            request_medical_certificate=False,
            request_prescription=True,
            status="pending",
        )
        resp = self.client.get("/operations/medical-requests/patient/")
        self.assertEqual(resp.status_code, 200)
        item = resp.json()["results"][0]
        self.assertEqual(item.get("doctor_status"), "unassigned")
        self.assertIsNone(item.get("doctor"))

    def test_patient_medical_requests_returns_500_on_db_failure(self):
        with patch("backend.operations.views.MedicalRequest.objects.select_related", side_effect=Exception("db down")):
            with self.assertLogs("backend.operations.views", level="ERROR") as logs:
                resp = self.client.get("/operations/medical-requests/patient/")
        self.assertEqual(resp.status_code, 500)
        self.assertTrue(any("patient_medical_requests failed to fetch doctor details" in m for m in logs.output))

    def test_doctor_medical_requests_includes_consultation_notes(self):
        nurse_user = User.objects.create_user(
            email="nurse.mr.details@example.com",
            password="StrongPass123",
            full_name="Nurse MR",
            role=User.Role.NURSE,
        )
        assignment = PatientAssignment.objects.create(
            specialization_required="Internal Medicine",
            assignment_reason="Reason",
            status="accepted",
            assigned_by=nurse_user,
            doctor=self.doctor_profile,
            patient=self.patient_profile,
        )
        notes = ConsultationNotes.objects.create(
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
        MedicalRequest.objects.create(
            requested_by=self.patient_user,
            patient=self.patient_profile,
            doctor=self.doctor_profile,
            assignment=assignment,
            consultation_notes=notes,
            request_medical_certificate=True,
            request_prescription=False,
            status="pending",
        )

        client = APIClient()
        client.force_authenticate(self.doctor_user)
        resp = client.get("/operations/medical-requests/doctor/")
        self.assertEqual(resp.status_code, 200)
        item = resp.json()["results"][0]
        returned_notes = item.get("consultation_notes")
        self.assertTrue(isinstance(returned_notes, dict))
        self.assertEqual(returned_notes.get("id"), notes.id)
        self.assertEqual(returned_notes.get("diagnosis"), "Migraine")

    def test_create_medical_request_succeeds_when_notifications_fail(self):
        nurse_user = User.objects.create_user(
            email="nurse.mr.create@example.com",
            password="StrongPass123",
            full_name="Nurse Create MR",
            role=User.Role.NURSE,
        )
        PatientAssignment.objects.create(
            specialization_required="Internal Medicine",
            assignment_reason="Reason",
            status="accepted",
            assigned_by=nurse_user,
            doctor=self.doctor_profile,
            patient=self.patient_profile,
        )

        with patch(
            "backend.operations.views.Notification.objects.create",
            side_effect=Exception('column "extra_data" of relation "notifications" does not exist'),
        ):
            resp = self.client.post(
                "/operations/medical-requests/create/",
                {"medical_certificate": True, "prescription": True, "message": "Need docs"},
                format="json",
            )
        self.assertEqual(resp.status_code, 201)
        payload = resp.json()
        self.assertTrue(payload.get("success"))
        self.assertTrue(MedicalRequest.objects.filter(id=payload.get("id")).exists())
