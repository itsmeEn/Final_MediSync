from datetime import timedelta
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from unittest.mock import patch

from backend.users.models import User, PatientProfile
from backend.operations.models import QueueManagement, QueueStatus, QueueNoShowAuditLog
from backend.operations.tasks import process_queue_no_show


class DummyChannelLayer:
    async def group_send(self, group, event):
        return None


@override_settings(QUEUE_NO_SHOW_GRACE_SECONDS=1, QUEUE_NO_SHOW_POLICY="move_to_end")
class NoShowHandlingTests(TestCase):
    def setUp(self):
        self.patient_user = User.objects.create_user(
            email="patient1@example.com",
            password="Password123",
            role=User.Role.PATIENT,
            full_name="Patient One",
        )
        self.patient_profile = PatientProfile.objects.create(user=self.patient_user)

        self.patient2_user = User.objects.create_user(
            email="patient2@example.com",
            password="Password123",
            role=User.Role.PATIENT,
            full_name="Patient Two",
        )
        self.patient2_profile = PatientProfile.objects.create(user=self.patient2_user)

        self.dept = "OPD"

    def test_grace_expiry_moves_called_patient_to_back_of_normal_queue_and_logs(self):
        now = timezone.now()
        waiting = QueueManagement.objects.create(
            patient=self.patient2_profile,
            queue_number=2,
            department=self.dept,
            status="waiting",
            is_priority=False,
            position_in_queue=1,
            enqueue_time=now,
        )
        called = QueueManagement.objects.create(
            patient=self.patient_profile,
            queue_number=1,
            department=self.dept,
            status="called",
            is_priority=False,
            position_in_queue=1,
            called_at=now,
            grace_expires_at=now - timedelta(seconds=5),
        )
        QueueStatus.objects.create(department=self.dept, is_open=True, current_serving=called.queue_number, total_waiting=1, status_message="Calling")

        with patch("backend.operations.tasks.get_channel_layer", return_value=DummyChannelLayer()):
            result = process_queue_no_show(called.id)

        self.assertTrue(result.get("ok"), result)
        called.refresh_from_db()
        waiting.refresh_from_db()

        self.assertEqual(called.status, "waiting")
        self.assertEqual(called.position_in_queue, 2)
        self.assertIsNotNone(called.last_no_show_at)
        self.assertEqual(called.no_show_action, "move_to_end")
        self.assertEqual(waiting.position_in_queue, 1)

        audit_events = list(QueueNoShowAuditLog.objects.filter(queue_entry=called).values_list("event", flat=True))
        self.assertIn("no_show_marked", audit_events)
        self.assertIn("no_show_moved_to_end", audit_events)

        qs = QueueStatus.objects.get(department=self.dept)
        self.assertIsNone(qs.current_serving)
        self.assertEqual(qs.status_message, "Ready")
        self.assertEqual(qs.total_waiting, 2)

    def test_grace_expiry_moves_called_patient_to_back_of_priority_queue_and_logs(self):
        now = timezone.now()
        waiting_prio = QueueManagement.objects.create(
            patient=self.patient2_profile,
            queue_number=12,
            department=self.dept,
            status="waiting",
            is_priority=True,
            priority_level="pwd",
            priority_position=2,
            enqueue_time=now,
        )
        called_prio = QueueManagement.objects.create(
            patient=self.patient_profile,
            queue_number=11,
            department=self.dept,
            status="called",
            is_priority=True,
            priority_level="pwd",
            priority_position=1,
            called_at=now,
            grace_expires_at=now - timedelta(seconds=5),
        )
        QueueStatus.objects.create(department=self.dept, is_open=True, current_serving=called_prio.queue_number, total_waiting=1, status_message="Calling")

        with patch("backend.operations.tasks.get_channel_layer", return_value=DummyChannelLayer()):
            result = process_queue_no_show(called_prio.id)

        self.assertTrue(result.get("ok"), result)
        called_prio.refresh_from_db()
        waiting_prio.refresh_from_db()

        self.assertEqual(called_prio.status, "waiting")
        self.assertEqual(called_prio.priority_position, 3)
        self.assertEqual(waiting_prio.priority_position, 2)

        audit_events = list(QueueNoShowAuditLog.objects.filter(queue_entry=called_prio).values_list("event", flat=True))
        self.assertIn("no_show_moved_to_end", audit_events)

    def test_check_in_after_grace_expiry_returns_clear_status(self):
        now = timezone.now()
        called = QueueManagement.objects.create(
            patient=self.patient_profile,
            queue_number=21,
            department=self.dept,
            status="called",
            is_priority=False,
            position_in_queue=1,
            called_at=now,
            grace_expires_at=now - timedelta(seconds=5),
        )
        QueueManagement.objects.create(
            patient=self.patient2_profile,
            queue_number=22,
            department=self.dept,
            status="waiting",
            is_priority=False,
            position_in_queue=1,
            enqueue_time=now,
        )
        QueueStatus.objects.create(department=self.dept, is_open=True, current_serving=called.queue_number, total_waiting=1, status_message="Calling")

        with patch("backend.operations.tasks.get_channel_layer", return_value=DummyChannelLayer()):
            process_queue_no_show(called.id)

        client = APIClient()
        client.force_authenticate(user=self.patient_user)
        resp = client.post("/operations/queue/check-in/", {"department": self.dept}, format="json")
        self.assertEqual(resp.status_code, 409, resp.content)
        data = resp.json()
        self.assertEqual(data.get("error"), "grace_period_expired")
        self.assertIn("moved to the back", (data.get("message") or "").lower())

    def test_requeue_is_reflected_in_patient_summary_immediately(self):
        now = timezone.now()
        QueueManagement.objects.create(
            patient=self.patient2_profile,
            queue_number=22,
            department=self.dept,
            status="waiting",
            is_priority=False,
            position_in_queue=1,
            enqueue_time=now,
        )
        called = QueueManagement.objects.create(
            patient=self.patient_profile,
            queue_number=21,
            department=self.dept,
            status="called",
            is_priority=False,
            position_in_queue=1,
            called_at=now,
            grace_expires_at=now - timedelta(seconds=5),
        )
        QueueStatus.objects.create(department=self.dept, is_open=True, current_serving=called.queue_number, total_waiting=1, status_message="Calling")

        with patch("backend.operations.tasks.get_channel_layer", return_value=DummyChannelLayer()):
            process_queue_no_show(called.id)

        client = APIClient()
        client.force_authenticate(user=self.patient_user)
        resp = client.get(f"/operations/patient/dashboard/summary/?department={self.dept}")
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        self.assertEqual(data.get("myQueueStatus"), "waiting")
        self.assertEqual(data.get("nowServing"), "")

    @override_settings(QUEUE_NO_SHOW_POLICY="remove")
    def test_grace_expiry_always_reenqueues_to_back_even_if_policy_is_remove(self):
        now = timezone.now()
        QueueManagement.objects.create(
            patient=self.patient2_profile,
            queue_number=2,
            department=self.dept,
            status="waiting",
            is_priority=False,
            position_in_queue=1,
            enqueue_time=now,
        )
        called = QueueManagement.objects.create(
            patient=self.patient_profile,
            queue_number=1,
            department=self.dept,
            status="called",
            is_priority=False,
            position_in_queue=1,
            called_at=now,
            grace_expires_at=now - timedelta(seconds=5),
        )
        QueueStatus.objects.create(department=self.dept, is_open=True, current_serving=called.queue_number, total_waiting=1, status_message="Calling")

        with patch("backend.operations.tasks.get_channel_layer", return_value=DummyChannelLayer()):
            result = process_queue_no_show(called.id)

        self.assertTrue(result.get("ok"), result)
        called.refresh_from_db()
        self.assertEqual(called.status, "waiting")
        self.assertEqual(called.no_show_action, "move_to_end")
