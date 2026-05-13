import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class MessageConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.user_group_name = f'messaging_{self.user_id}'
        
        # Join user group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        await self.accept()

    async def disconnect(self, close_code):
        # Leave user group
        await self.channel_layer.group_discard(
            self.user_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            if message_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))

    async def new_message(self, event):
        """Send new message to WebSocket"""
        message_data = event['message']
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'message': message_data
        }))

    async def message_delivered(self, event):
        """Send message delivered notification to WebSocket"""
        message_data = event['message']
        await self.send(text_data=json.dumps({
            'type': 'message_delivered',
            'message': message_data
        }))

    async def message_read(self, event):
        """Send message read notification to WebSocket"""
        message_data = event['message']
        await self.send(text_data=json.dumps({
            'type': 'message_read',
            'message': message_data
        }))

    async def notification(self, event):
        """Send notification to WebSocket"""
        notification_data = event['notification']
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': notification_data
        }))


class QueueStatusConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time queue status updates
    """
    
    async def connect(self):
        self.department = self.scope['url_route']['kwargs'].get('department', 'general')
        self.user_id = self.scope['url_route']['kwargs'].get('user_id')
        
        # Join department-specific group for queue updates
        self.queue_group_name = f'queue_{self.department}'
        await self.channel_layer.group_add(
            self.queue_group_name,
            self.channel_name
        )
        
        # Join user-specific group for personal notifications
        if self.user_id:
            self.user_group_name = f'queue_user_{self.user_id}'
            await self.channel_layer.group_add(
                self.user_group_name,
                self.channel_name
            )
        
        await self.accept()
        
        # Send current queue status
        await self.send_current_queue_status()

    async def disconnect(self, close_code):
        # Leave groups
        await self.channel_layer.group_discard(
            self.queue_group_name,
            self.channel_name
        )
        
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'get_queue_status':
                await self.send_current_queue_status()
            elif message_type == 'get_queue_schedule':
                await self.send_current_queue_schedule()
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))

    async def queue_status_update(self, event):
        """Send queue status update to WebSocket"""
        status_data = event['status']
        await self.send(text_data=json.dumps({
            'type': 'queue_status_update',
            'status': status_data
        }))

    async def queue_schedule_update(self, event):
        """Send queue schedule update to WebSocket"""
        schedule_data = event['schedule']
        await self.send(text_data=json.dumps({
            'type': 'queue_schedule_update',
            'schedule': schedule_data
        }))

    async def queue_notification(self, event):
        """Send queue notification to WebSocket"""
        notification_data = event['notification']
        await self.send(text_data=json.dumps({
            'type': 'queue_notification',
            'notification': notification_data
        }))
        
        # Mark notification as delivered if notification_id is provided
        notification_id = notification_data.get('notification_id')
        if notification_id:
            await self.mark_notification_delivered(notification_id)

    async def queue_position_update(self, event):
        """Send queue position update to WebSocket"""
        position_data = event['position']
        await self.send(text_data=json.dumps({
            'type': 'queue_position_update',
            'position': position_data
        }))

    @database_sync_to_async
    def mark_notification_delivered(self, notification_id):
        """Mark a notification as delivered"""
        try:
            from .models import Notification
            from django.utils import timezone
            
            notification = Notification.objects.get(id=notification_id)
            notification.delivery_status = Notification.DELIVERY_DELIVERED
            notification.delivered_at = timezone.now()
            notification.save()
            return True
        except Notification.DoesNotExist:
            return False
        except Exception:
            return False
    
    @database_sync_to_async
    def get_current_queue_status(self):
        try:
            from .models import QueueStatus
            qs = QueueStatus.objects.filter(department=self.department).first()
            if qs:
                return {
                    'department': qs.department,
                    'is_open': bool(qs.is_open),
                    'current_serving': qs.current_serving,
                    'total_waiting': qs.total_waiting,
                    'status_message': qs.status_message,
                    'last_updated_at': qs.last_updated_at.isoformat() if qs.last_updated_at else None,
                }
        except Exception:
            pass
        try:
            from .views import QUEUE_STATUS_STORE
            st = QUEUE_STATUS_STORE.get(self.department, {'is_open': False})
            return {
                'department': self.department,
                'is_open': bool(st.get('is_open', False)),
            }
        except Exception:
            return {'department': self.department, 'is_open': False}

    @database_sync_to_async
    def get_current_queue_schedule(self):
        from .views import QUEUE_SCHEDULES_STORE
        return [s for s in QUEUE_SCHEDULES_STORE if s.get('department') == self.department]

    async def send_current_queue_status(self):
        status_data = await self.get_current_queue_status()
        await self.send(text_data=json.dumps({
            'type': 'queue_status_update',
            'status': status_data
        }))

    async def send_current_queue_schedule(self):
        schedule_data = await self.get_current_queue_schedule()
        await self.send(text_data=json.dumps({
            'type': 'queue_schedule_update',
            'schedule': schedule_data
        }))


class MedicationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time medication dispense notifications to patients"""

    async def connect(self):
        self.patient_id = self.scope['url_route']['kwargs'].get('patient_id')
        self.group_name = f'medication_{self.patient_id}'

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        # Currently, we don't need to process incoming messages from clients
        try:
            data = json.loads(text_data)
            if data.get('type') == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
        except Exception:
            # Ignore malformed messages
            pass

    async def medication_notification(self, event):
        """Send medication notification to patient WebSocket"""
        payload = event.get('notification', {})
        await self.send(text_data=json.dumps({
            'type': 'medication_notification',
            'notification': payload
        }))
