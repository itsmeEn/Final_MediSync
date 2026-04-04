from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from backend.users.models import User, GeneralDoctorProfile, PatientProfile
from backend.operations.models import AppointmentManagement


class AppointmentEndpointTests(TestCase):
    def setUp(self):
        # Create doctor and patient users and profiles
        self.doctor_user = User.objects.create_user(
            email="doctor@example.com",
            password="StrongPass123",
            full_name="Dr. Test",
            role=User.Role.DOCTOR,
        )
        self.patient_user = User.objects.create_user(
            email="patient@example.com",
            password="StrongPass123",
            full_name="Patient One",
            role=User.Role.PATIENT,
        )
        self.doctor_profile = GeneralDoctorProfile.objects.create(user=self.doctor_user, specialization="General")
        self.patient_profile = PatientProfile.objects.create(user=self.patient_user)

        # Create an appointment scheduled 10 minutes from now (so notify is allowed)
        start_dt = timezone.now() + timezone.timedelta(minutes=10)
        self.appointment = AppointmentManagement.objects.create(
            patient=self.patient_profile,
            doctor=self.doctor_profile,
            appointment_date=start_dt,
            appointment_time=start_dt.time(),
            appointment_type="consultation",
            queue_number=1234,
            status="scheduled",
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.doctor_user)

    def test_notify_patient_appointment(self):
        url = f"/operations/appointments/{self.appointment.appointment_id}/notify-patient/"
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("message", data)
        self.assertEqual(data.get("message"), "Notification queued")
        self.assertIn("notification", data)

    def test_finish_consultation_marks_completed(self):
        url = f"/operations/appointments/{self.appointment.appointment_id}/finish/"
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)

        # Refresh from DB and verify state
        appt = AppointmentManagement.objects.get(pk=self.appointment.pk)
        self.assertEqual(appt.status, "completed")
        self.assertIsNotNone(appt.consultation_finished_at)
