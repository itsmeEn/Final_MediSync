from django.test import TestCase
from rest_framework.test import APIClient

from backend.users.models import User
from backend.operations.models import Conversation, Message, MessageNotification


class MessageNotificationsMarkAllTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.doctor = User.objects.create_user(
            email="doctor.msgnotif@example.com",
            password="StrongPass123",
            full_name="Dr MsgNotif",
            role=User.Role.DOCTOR,
            verification_status="approved",
        )
        self.patient = User.objects.create_user(
            email="patient.msgnotif@example.com",
            password="StrongPass123",
            full_name="Patient MsgNotif",
            role=User.Role.PATIENT,
            verification_status="approved",
        )

        conv = Conversation.objects.create()
        conv.participants.add(self.doctor, self.patient)

        msg = Message.objects.create(conversation=conv, sender=self.patient, content="Hello")
        self.n1 = MessageNotification.objects.create(
            recipient=self.doctor,
            message=msg,
            notification_type="new_message",
            is_sent=False,
        )

        self.client.force_authenticate(user=self.doctor)

    def test_mark_all_sent_resets_list(self):
        before = self.client.get("/operations/messaging/notifications/")
        self.assertEqual(before.status_code, 200)
        self.assertEqual(len(before.json()), 1)

        resp = self.client.post("/operations/messaging/notifications/mark-all-sent/", {}, format="json")
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("unread_count"), 0)

        self.n1.refresh_from_db()
        self.assertTrue(self.n1.is_sent)

        after = self.client.get("/operations/messaging/notifications/")
        self.assertEqual(after.status_code, 200)
        self.assertEqual(len(after.json()), 0)

