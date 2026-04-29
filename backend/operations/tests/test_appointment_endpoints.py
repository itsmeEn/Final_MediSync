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

    def test_patient_can_list_own_appointments(self):
        self.client.force_authenticate(user=self.patient_user)
        resp = self.client.get("/operations/patient/appointments/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        results = data.get("results") or []
        self.assertTrue(isinstance(results, list))
        self.assertTrue(any((a.get("appointment_id") == self.appointment.appointment_id) for a in results))

    def test_get_available_doctors_for_patient(self):
        # Mark doctor as available + verified
        self.doctor_profile.available_for_consultation = True
        self.doctor_profile.specialization = "General"
        self.doctor_profile.save()
        self.doctor_user.verification_status = "approved"
        self.doctor_user.save()

        self.client.force_authenticate(user=self.patient_user)
        resp = self.client.get("/operations/available-doctors/", {"department": "General"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        doctors = data.get("doctors") or []
        self.assertTrue(isinstance(doctors, list))
        self.assertTrue(any((d.get("id") == self.doctor_user.id) for d in doctors))

    def test_patient_can_schedule_and_reschedule_appointment(self):
        # Make doctor selectable
        self.doctor_profile.available_for_consultation = True
        self.doctor_profile.specialization = "General"
        self.doctor_profile.save()
        self.doctor_user.verification_status = "approved"
        self.doctor_user.save()

        self.client.force_authenticate(user=self.patient_user)

        date_str = timezone.localdate().strftime("%Y-%m-%d")
        resp = self.client.post(
            "/operations/appointments/schedule/",
            {
                "department": "General",
                "date": date_str,
                "time": "09:00",
                "type": "general-consultation",
                "doctor_id": self.doctor_user.id,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        created = resp.json()
        appt_id = created.get("appointment_id")
        self.assertTrue(isinstance(appt_id, int))
        self.assertTrue(AppointmentManagement.objects.filter(appointment_id=appt_id).exists())

        resp2 = self.client.post(
            f"/operations/appointments/{appt_id}/reschedule/",
            {"date": date_str, "time": "09:30"},
            format="json",
        )
        self.assertEqual(resp2.status_code, 200)
        updated = resp2.json()
        self.assertEqual(updated.get("status"), "rescheduled")

    def test_doctor_occupied_slots_endpoint(self):
        self.client.force_authenticate(user=self.patient_user)
        date_str = timezone.localdate().strftime("%Y-%m-%d")
        resp = self.client.get("/operations/appointments/doctor-slots/", {"doctor_id": self.doctor_user.id, "date": date_str})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        occupied = data.get("occupied_times") or []
        self.assertTrue(isinstance(occupied, list))
        expected = self.appointment.appointment_time.strftime("%H:%M")
        self.assertIn(expected, occupied)

    def test_doctor_can_see_patient_scheduled_appointment(self):
        self.client.force_authenticate(user=self.doctor_user)
        resp = self.client.get("/operations/appointments/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        results = data.get("results") or []
        self.assertTrue(any((a.get("appointment_id") == self.appointment.appointment_id) for a in results))
