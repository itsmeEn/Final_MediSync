from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from unittest.mock import patch

from backend.users.models import User, PatientProfile
from backend.operations.models import QueueManagement


class QueueSyncFlowTests(TestCase):
    def setUp(self):
        # Create a nurse for reading queue
        self.nurse = User.objects.create_user(
            email="nurse.sync@example.com",
            password="StrongPass123",
            full_name="Nurse Sync",
            role=User.Role.NURSE,
        )
        # Create a patient to join queue
        self.patient = User.objects.create_user(
            email="patient.sync@example.com",
            password="StrongPass123",
            full_name="Patient Sync",
            role=User.Role.PATIENT,
        )
        PatientProfile.objects.create(user=self.patient, blood_type="O+", medical_condition="None")

    def test_patient_join_updates_nurse_feed_and_patient_summary(self):
        # Patient joins queue
        pclient = APIClient()
        pclient.force_authenticate(self.patient)
        join_resp = pclient.post("/operations/queue/join/", {"department": "OPD"}, format="json")
        self.assertEqual(join_resp.status_code, 201)

        # Nurse sees queue
        nclient = APIClient()
        nclient.force_authenticate(self.nurse)
        nurse_resp = nclient.get("/operations/nurse/queue/patients/?department=OPD")
        self.assertEqual(nurse_resp.status_code, 200)
        data = nurse_resp.json()
        self.assertTrue(len(data.get("normal_queue", [])) >= 1)
        self.assertTrue(len(data.get("all_patients", [])) >= 1)

        # Patient summary reflects position
        summary_resp = pclient.get("/operations/patient/dashboard/summary/?department=OPD")
        self.assertEqual(summary_resp.status_code, 200)
        sdata = summary_resp.json()
        self.assertTrue(isinstance(sdata.get("myPosition", ""), str))
        # myPosition can be 'Now Serving' or a queue number string, but should not be empty
        self.assertNotEqual(sdata.get("myPosition", ""), "")

    def test_priority_join_appears_in_priority_queue(self):
        pclient = APIClient()
        pclient.force_authenticate(self.patient)
        join_resp = pclient.post("/operations/queue/join/", {"department": "OPD", "priority_level": "pwd"}, format="json")
        self.assertEqual(join_resp.status_code, 201)

        nclient = APIClient()
        nclient.force_authenticate(self.nurse)
        nurse_resp = nclient.get("/operations/nurse/queue/patients/?department=OPD")
        self.assertEqual(nurse_resp.status_code, 200)
        data = nurse_resp.json()
        self.assertTrue(len(data.get("priority_queue", [])) >= 1)

    def test_patient_can_leave_queue(self):
        pclient = APIClient()
        pclient.force_authenticate(self.patient)
        join_resp = pclient.post("/operations/queue/join/", {"department": "OPD"}, format="json")
        self.assertEqual(join_resp.status_code, 201)

        leave_resp = pclient.post("/operations/queue/leave/", {"department": "OPD"}, format="json")
        self.assertEqual(leave_resp.status_code, 200)
        self.assertTrue(leave_resp.json().get("success"))
        self.assertTrue(leave_resp.json().get("removed"))

        # Leaving again is idempotent
        leave_resp2 = pclient.post("/operations/queue/leave/", {"department": "OPD"}, format="json")
        self.assertEqual(leave_resp2.status_code, 200)
        self.assertTrue(leave_resp2.json().get("success"))
        self.assertFalse(leave_resp2.json().get("removed"))

    def test_patient_summary_falls_back_to_active_department(self):
        pclient = APIClient()
        pclient.force_authenticate(self.patient)
        join_resp = pclient.post("/operations/queue/join/", {"department": "OPD"}, format="json")
        self.assertEqual(join_resp.status_code, 201)

        summary_resp = pclient.get("/operations/patient/dashboard/summary/?department=Pharmacy")
        self.assertEqual(summary_resp.status_code, 200)
        sdata = summary_resp.json()
        self.assertEqual(sdata.get("activeDepartment"), "OPD")
        self.assertEqual(sdata.get("department"), "OPD")
        self.assertNotEqual(sdata.get("myPosition", ""), "")

    def test_patient_cannot_join_multiple_departments(self):
        pclient = APIClient()
        pclient.force_authenticate(self.patient)
        join_resp = pclient.post("/operations/queue/join/", {"department": "OPD"}, format="json")
        self.assertEqual(join_resp.status_code, 201)

        join_resp2 = pclient.post("/operations/queue/join/", {"department": "Pharmacy"}, format="json")
        self.assertEqual(join_resp2.status_code, 409)
        data = join_resp2.json()
        self.assertEqual(data.get("department"), "OPD")

    def test_patient_summary_includes_position_in_queue(self):
        patient2 = User.objects.create_user(
            email="patient2.sync@example.com",
            password="StrongPass123",
            full_name="Patient Two",
            role=User.Role.PATIENT,
        )
        PatientProfile.objects.create(user=patient2, blood_type="O+", medical_condition="None")

        pclient1 = APIClient()
        pclient1.force_authenticate(self.patient)
        join_resp1 = pclient1.post("/operations/queue/join/", {"department": "OPD"}, format="json")
        self.assertEqual(join_resp1.status_code, 201)

        pclient2 = APIClient()
        pclient2.force_authenticate(patient2)
        join_resp2 = pclient2.post("/operations/queue/join/", {"department": "OPD"}, format="json")
        self.assertEqual(join_resp2.status_code, 201)

        summary_resp = pclient2.get("/operations/patient/dashboard/summary/?department=OPD")
        self.assertEqual(summary_resp.status_code, 200)
        sdata = summary_resp.json()
        self.assertEqual(sdata.get("myQueueStatus"), "waiting")
        self.assertEqual(sdata.get("myPositionInQueue"), 2)
        self.assertTrue(isinstance(sdata.get("myQueueNumber"), int))

    def test_wait_estimate_runs_even_when_no_one_called_yet(self):
        pclient = APIClient()
        pclient.force_authenticate(self.patient)
        join_resp = pclient.post("/operations/queue/join/", {"department": "OPD"}, format="json")
        self.assertEqual(join_resp.status_code, 201, join_resp.content)

        my_entry = (
            QueueManagement.objects.filter(department="OPD", status="waiting")
            .order_by("-is_priority", "priority_position", "enqueue_time", "created_at")
            .first()
        )
        self.assertIsNotNone(my_entry)
        base_now = getattr(my_entry, "enqueue_time", None) or getattr(my_entry, "created_at", None) or timezone.now()

        with patch("backend.operations.views.timezone.now", return_value=base_now):
            s1_resp = pclient.get("/operations/patient/dashboard/summary/?department=OPD")
            self.assertEqual(s1_resp.status_code, 200, s1_resp.content)
            s1 = s1_resp.json()
        with patch("backend.operations.views.timezone.now", return_value=base_now + timedelta(seconds=10)):
            s2_resp = pclient.get("/operations/patient/dashboard/summary/?department=OPD")
            self.assertEqual(s2_resp.status_code, 200, s2_resp.content)
            s2 = s2_resp.json()

        self.assertEqual(s1.get("myQueueStatus"), "waiting")
        self.assertEqual(s1.get("estimatedWaitSeconds"), 0)
        self.assertEqual(s1.get("waitTimerMode"), "elapsed")
        self.assertEqual(int(s1.get("waitTimerSeconds") or 0), 0)

        self.assertEqual(s2.get("waitTimerMode"), "elapsed")
        self.assertEqual(int(s2.get("waitTimerSeconds") or 0), 10)

    def test_wait_estimate_does_not_reset_when_queue_is_idle(self):
        patient2 = User.objects.create_user(
            email="patient3.sync@example.com",
            password="StrongPass123",
            full_name="Patient Three",
            role=User.Role.PATIENT,
        )
        PatientProfile.objects.create(user=patient2, blood_type="O+", medical_condition="None")

        pclient1 = APIClient()
        pclient1.force_authenticate(self.patient)
        join1 = pclient1.post("/operations/queue/join/", {"department": "OPD"}, format="json")
        self.assertEqual(join1.status_code, 201, join1.content)

        pclient2 = APIClient()
        pclient2.force_authenticate(patient2)
        join2 = pclient2.post("/operations/queue/join/", {"department": "OPD"}, format="json")
        self.assertEqual(join2.status_code, 201, join2.content)

        first_waiting = QueueManagement.objects.filter(department="OPD", status="waiting").order_by("-is_priority", "priority_position", "enqueue_time", "created_at").first()
        self.assertIsNotNone(first_waiting)
        base_now = getattr(first_waiting, "enqueue_time", None) or getattr(first_waiting, "created_at", None) or timezone.now()

        with patch("backend.operations.views.timezone.now", return_value=base_now):
            s1 = pclient2.get("/operations/patient/dashboard/summary/?department=OPD").json()
        with patch("backend.operations.views.timezone.now", return_value=base_now + timedelta(seconds=10)):
            s2 = pclient2.get("/operations/patient/dashboard/summary/?department=OPD").json()

        self.assertEqual(s1.get("waitTimerMode"), "countdown")
        self.assertEqual(s2.get("waitTimerMode"), "countdown")
        self.assertEqual(s1.get("waitTimerEtaAt"), s2.get("waitTimerEtaAt"))

        e1 = int(s1.get("waitTimerSeconds") or 0)
        e2 = int(s2.get("waitTimerSeconds") or 0)
        self.assertGreater(e1, 0)
        self.assertLess(e2, e1)

    def test_wait_estimate_accounts_for_multiple_active_counters(self):
        patient_a = User.objects.create_user(
            email="patient.a.sync@example.com",
            password="StrongPass123",
            full_name="Patient A",
            role=User.Role.PATIENT,
        )
        patient_b = User.objects.create_user(
            email="patient.b.sync@example.com",
            password="StrongPass123",
            full_name="Patient B",
            role=User.Role.PATIENT,
        )
        patient_c = User.objects.create_user(
            email="patient.c.sync@example.com",
            password="StrongPass123",
            full_name="Patient C",
            role=User.Role.PATIENT,
        )
        prof_a = PatientProfile.objects.create(user=patient_a, blood_type="O+", medical_condition="None")
        prof_b = PatientProfile.objects.create(user=patient_b, blood_type="O+", medical_condition="None")
        prof_c = PatientProfile.objects.create(user=patient_c, blood_type="O+", medical_condition="None")

        base_now = timezone.now()
        QueueManagement.objects.create(
            patient=prof_a,
            queue_number=1,
            department="OPD",
            status="in_progress",
            enqueue_time=base_now - timedelta(minutes=10),
            called_at=base_now - timedelta(seconds=30),
        )
        QueueManagement.objects.create(
            patient=prof_b,
            queue_number=2,
            department="OPD",
            status="called",
            enqueue_time=base_now - timedelta(minutes=9),
            called_at=base_now - timedelta(seconds=10),
        )

        ahead = QueueManagement.objects.create(
            patient=prof_a,
            queue_number=3,
            department="OPD",
            status="waiting",
            enqueue_time=base_now - timedelta(seconds=5),
        )
        mine = QueueManagement.objects.create(
            patient=prof_c,
            queue_number=4,
            department="OPD",
            status="waiting",
            enqueue_time=base_now - timedelta(seconds=1),
        )
        self.assertLess(ahead.enqueue_time, mine.enqueue_time)

        pclient = APIClient()
        pclient.force_authenticate(patient_c)

        with patch("backend.operations.views.timezone.now", return_value=base_now), patch(
            "backend.operations.views._avg_service_seconds_for_department", return_value=60
        ):
            s = pclient.get("/operations/patient/dashboard/summary/?department=OPD").json()

        self.assertEqual(s.get("myQueueStatus"), "waiting")
        self.assertEqual(s.get("waitTimerMode"), "countdown")
        est = int(s.get("waitTimerSeconds") or 0)
        self.assertGreater(est, 0)
        self.assertLess(est, 90)
