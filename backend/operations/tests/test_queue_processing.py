from django.test import TestCase
from django.utils import timezone
from django.test import override_settings
from rest_framework.test import APIClient
from unittest.mock import patch

from backend.users.models import User, NurseProfile, PatientProfile
from backend.operations.models import QueueStatus, QueueManagement, Notification
from backend.operations.tasks import process_queue_no_show


class QueueProcessingTests(TestCase):
    def setUp(self):
        # Create users
        self.nurse_user = User.objects.create_user(
            email="nurse@example.com",
            password="Password123",
            role=User.Role.NURSE,
            full_name="Nurse Joy",
        )
        self.patient_user = User.objects.create_user(
            email="patient@example.com",
            password="Password123",
            role=User.Role.PATIENT,
            full_name="John Patient",
        )

        # Profiles
        self.nurse_profile = NurseProfile.objects.create(
            user=self.nurse_user, department="OPD"
        )
        self.patient_profile = PatientProfile.objects.create(
            user=self.patient_user
        )

        # Queue status (open)
        self.queue_status = QueueStatus.objects.create(
            department="OPD",
            is_open=True,
        )

        # Create a waiting queue entry using bulk_create to avoid model save overrides
        QueueManagement.objects.bulk_create([
            QueueManagement(
                patient=self.patient_profile,
                queue_number=1,
                department="OPD",
                status="waiting",
                position_in_queue=1,
                enqueue_time=timezone.now(),
            )
        ])

        self.client = APIClient()

    def test_start_queue_processing_updates_status_and_sends_notification(self):
        # Stub channel layer to avoid external Redis dependency
        class DummyChannelLayer:
            async def group_send(self, group, event):
                return None

        self.client.force_authenticate(user=self.nurse_user)
        with patch("backend.operations.views.get_channel_layer", return_value=DummyChannelLayer()):
            resp = self.client.post(
                "/operations/queue/start-processing/",
                {"department": "OPD"},
                format="json",
            )

        self.assertEqual(resp.status_code, 200, resp.content)

        data = resp.json()
        # Queue status should reflect current serving and zero waiting
        self.assertIn("queue_status", data)
        self.assertEqual(data["queue_status"].get("current_serving"), 1)
        self.assertEqual(data["queue_status"].get("total_waiting"), 0)

        # Queue entry should be in progress
        entry = QueueManagement.objects.get(queue_number=1)
        self.assertEqual(entry.status, "called")
        self.assertIsNotNone(entry.grace_expires_at)

        self.assertIn("notification_results", data)

    def test_confirm_notification_delivery_updates_fields(self):
        # Create a pending notification for patient
        notif = Notification.objects.create(
            user=self.patient_user,
            message="Test delivery",
            channel=Notification.CHANNEL_WEBSOCKET,
            delivery_status=Notification.DELIVERY_PENDING,
        )

        # Patient confirms delivery
        self.client.force_authenticate(user=self.patient_user)
        resp = self.client.post(
            "/operations/queue/notifications/confirm/",
            {"notification_id": notif.id},
            format="json",
        )

        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        self.assertIn("notification", data)
        updated = data["notification"]
        self.assertEqual(updated.get("delivery_status"), Notification.DELIVERY_DELIVERED)
        self.assertIsNotNone(updated.get("delivered_at"))

    def test_no_show_move_to_end_requeues_patient_and_broadcasts_consistent_updates(self):
        from datetime import timedelta

        class DummyChannelLayer:
            def __init__(self):
                self.sent = []

            async def group_send(self, group, event):
                self.sent.append((group, event))

        now = timezone.now()
        entry = QueueManagement.objects.get(queue_number=1)
        entry.status = "called"
        entry.called_at = now - timedelta(seconds=70)
        entry.grace_expires_at = now - timedelta(seconds=1)
        entry.save(update_fields=["status", "called_at", "grace_expires_at", "updated_at"])
        self.queue_status.current_serving = 1
        self.queue_status.save(update_fields=["current_serving", "last_updated_at"])

        patient2_user = User.objects.create_user(
            email="patient2@example.com",
            password="Password123",
            role=User.Role.PATIENT,
            full_name="Jane Patient",
        )
        patient2_profile = PatientProfile.objects.create(user=patient2_user)
        QueueManagement.objects.bulk_create([
            QueueManagement(
                patient=patient2_profile,
                queue_number=2,
                department="OPD",
                status="waiting",
                position_in_queue=2,
                enqueue_time=now - timedelta(minutes=5),
            )
        ])

        dummy_layer = DummyChannelLayer()
        with patch("backend.operations.tasks.get_channel_layer", return_value=dummy_layer):
            resp = process_queue_no_show(entry.id)

        self.assertTrue(resp.get("ok"), resp)
        entry.refresh_from_db()
        self.assertEqual(entry.status, "waiting")
        self.assertIsNone(entry.grace_expires_at)

        position_updates = [e for (g, e) in dummy_layer.sent if e.get("type") == "queue_position_update"]
        self.assertTrue(position_updates)
        mine = [
            e for e in position_updates
            if (e.get("position") or {}).get("patient_id") == self.patient_user.id and (e.get("position") or {}).get("queue_number") == 1
        ]
        self.assertTrue(mine)
        self.assertEqual((mine[0].get("position") or {}).get("status"), "waiting")
        self.assertIsNone((mine[0].get("position") or {}).get("grace_expires_at"))

        dept_notifications = [
            e for (g, e) in dummy_layer.sent
            if g == "queue_OPD" and e.get("type") == "queue_notification" and (e.get("notification") or {}).get("event") == "queue_no_show_requeued"
        ]
        self.assertTrue(dept_notifications)

        user_group_updates = [
            e for (g, e) in dummy_layer.sent
            if g == f"queue_user_{self.patient_user.id}" and e.get("type") == "queue_position_update"
        ]
        self.assertTrue(user_group_updates)

        self.queue_status.refresh_from_db()
        self.assertNotEqual(self.queue_status.current_serving, 1)

    @override_settings(QUEUE_NO_SHOW_POLICY="remove")
    def test_no_show_remove_marks_no_show_and_broadcasts_no_show_status(self):
        from datetime import timedelta

        class DummyChannelLayer:
            def __init__(self):
                self.sent = []

            async def group_send(self, group, event):
                self.sent.append((group, event))

        now = timezone.now()
        entry = QueueManagement.objects.get(queue_number=1)
        entry.status = "called"
        entry.called_at = now - timedelta(seconds=70)
        entry.grace_expires_at = now - timedelta(seconds=1)
        entry.save(update_fields=["status", "called_at", "grace_expires_at", "updated_at"])

        dummy_layer = DummyChannelLayer()
        with patch("backend.operations.tasks.get_channel_layer", return_value=dummy_layer):
            resp = process_queue_no_show(entry.id)

        self.assertTrue(resp.get("ok"), resp)
        entry.refresh_from_db()
        self.assertEqual(entry.status, "no_show")
        self.assertIsNone(entry.grace_expires_at)

        mine = [
            e for (g, e) in dummy_layer.sent
            if e.get("type") == "queue_position_update" and (e.get("position") or {}).get("patient_id") == self.patient_user.id
        ]
        self.assertTrue(mine)
        self.assertEqual((mine[0].get("position") or {}).get("status"), "no_show")

    def test_no_show_task_is_idempotent_under_duplicate_execution(self):
        from datetime import timedelta

        class DummyChannelLayer:
            def __init__(self):
                self.sent = []

            async def group_send(self, group, event):
                self.sent.append((group, event))

        now = timezone.now()
        entry = QueueManagement.objects.get(queue_number=1)
        entry.status = "called"
        entry.called_at = now - timedelta(seconds=70)
        entry.grace_expires_at = now - timedelta(seconds=1)
        entry.save(update_fields=["status", "called_at", "grace_expires_at", "updated_at"])

        patient2_user = User.objects.create_user(
            email="patient3@example.com",
            password="Password123",
            role=User.Role.PATIENT,
            full_name="Idempotent Patient",
        )
        patient2_profile = PatientProfile.objects.create(user=patient2_user)
        QueueManagement.objects.bulk_create([
            QueueManagement(
                patient=patient2_profile,
                queue_number=2,
                department="OPD",
                status="waiting",
                position_in_queue=2,
                enqueue_time=now - timedelta(minutes=5),
            )
        ])

        dummy_layer = DummyChannelLayer()
        with patch("backend.operations.tasks.get_channel_layer", return_value=dummy_layer):
            first = process_queue_no_show(entry.id)
            second = process_queue_no_show(entry.id)

        self.assertTrue(first.get("ok"), first)
        self.assertFalse(second.get("ok"), second)
        self.assertEqual(second.get("reason"), "not_called")
