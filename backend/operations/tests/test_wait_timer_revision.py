from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from unittest.mock import patch

from backend.users.models import User, PatientProfile
from backend.operations.models import QueueManagement

class WaitTimerRevisionTests(TestCase):
    def setUp(self):
        self.patient1 = User.objects.create_user(
            email="p1@example.com", password="Pass", full_name="Patient 1", role=User.Role.PATIENT
        )
        self.prof1 = PatientProfile.objects.create(user=self.patient1)
        
        self.patient2 = User.objects.create_user(
            email="p2@example.com", password="Pass", full_name="Patient 2", role=User.Role.PATIENT
        )
        self.prof2 = PatientProfile.objects.create(user=self.patient2)

        self.doctor = User.objects.create_user(
            email="d1@example.com", password="Pass", full_name="Doctor 1", role=User.Role.DOCTOR
        )

    def test_first_uncalled_patient_has_incrementing_timer_even_when_someone_is_served(self):
        """
        Verify that the first waiting patient (Position 1) has an 'elapsed' timer
        and 0 estimated wait time, even if someone else is currently being served.
        """
        base_now = timezone.now()
        
        # Person currently being served
        QueueManagement.objects.create(
            patient=self.prof1,
            queue_number=100,
            department="OPD",
            status="in_progress",
            called_at=base_now - timedelta(minutes=5),
            enqueue_time=base_now - timedelta(minutes=15),
        )
        
        # Next person in queue (first uncalled)
        next_patient = QueueManagement.objects.create(
            patient=self.prof2,
            queue_number=101,
            department="OPD",
            status="waiting",
            enqueue_time=base_now - timedelta(minutes=2),
        )

        pclient = APIClient()
        pclient.force_authenticate(self.patient2)
        
        with patch("backend.operations.views.timezone.now", return_value=base_now):
            resp = pclient.get("/operations/patient/dashboard/summary/?department=OPD")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            
            # Position should be 1 (first uncalled)
            self.assertEqual(data.get("myPositionInQueue"), 1)
            
            # Mode should be 'elapsed'
            self.assertEqual(data.get("waitTimerMode"), "elapsed")
            
            # Estimated wait mins should be 0
            self.assertEqual(data.get("estimatedWaitMins"), 0)
            
            # Seconds should match time since enqueue (2 mins = 120s)
            self.assertEqual(data.get("waitTimerSeconds"), 120)

    def test_subsequent_patients_have_countdown_timers(self):
        """
        Verify that patients after the first uncalled one have 'countdown' timers.
        """
        base_now = timezone.now()
        
        # Next person in queue (first uncalled)
        QueueManagement.objects.create(
            patient=self.prof1,
            queue_number=100,
            department="OPD",
            status="waiting",
            enqueue_time=base_now - timedelta(minutes=2),
        )
        
        # Person after that
        QueueManagement.objects.create(
            patient=self.prof2,
            queue_number=101,
            department="OPD",
            status="waiting",
            enqueue_time=base_now - timedelta(minutes=1),
        )

        pclient = APIClient()
        pclient.force_authenticate(self.patient2)
        
        with patch("backend.operations.views.timezone.now", return_value=base_now), \
             patch("backend.operations.views._avg_service_seconds_for_department", return_value=600): # 10 mins
            resp = pclient.get("/operations/patient/dashboard/summary/?department=OPD")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            
            # Position should be 2
            self.assertEqual(data.get("myPositionInQueue"), 2)
            
            # Mode should be 'countdown'
            self.assertEqual(data.get("waitTimerMode"), "countdown")
            
            # Estimated wait should be > 0 (it should be roughly avg_service_seconds if first waiting is considered active or similar)
            self.assertGreater(data.get("estimatedWaitSeconds"), 0)

    def test_timer_resets_when_called(self):
        """
        Verify that waitTimerMode becomes 'none' when the patient is called.
        """
        base_now = timezone.now()
        entry = QueueManagement.objects.create(
            patient=self.prof2,
            queue_number=101,
            department="OPD",
            status="called",
            called_at=base_now,
            enqueue_time=base_now - timedelta(minutes=10),
        )

        pclient = APIClient()
        pclient.force_authenticate(self.patient2)
        
        with patch("backend.operations.views.timezone.now", return_value=base_now):
            resp = pclient.get("/operations/patient/dashboard/summary/?department=OPD")
            data = resp.json()
            self.assertEqual(data.get("waitTimerMode"), "none")
            self.assertEqual(data.get("waitTimerSeconds"), 0)
