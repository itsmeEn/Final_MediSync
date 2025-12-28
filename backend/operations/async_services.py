"""
Async services for operations module.
This module provides async implementations of core operations functionality.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async

from .models import (
    AppointmentManagement, QueueManagement, PriorityQueue,
    Notification, Conversation, Message,
    MessageNotification, MedicineInventory
)
from backend.users.models import PatientProfile
from backend.utils.async_db import AsyncModelManager, async_safe

User = get_user_model()
logger = logging.getLogger(__name__)

class AsyncAppointmentService:
    """Async service for appointment management."""
    
    @staticmethod
    @async_safe(timeout=30)
    async def get_user_appointments(user_id: int, filters: Dict[str, Any] = None) -> List[Dict]:
        """Get appointments for a user asynchronously."""
        try:
            filter_kwargs = {'doctor_id': user_id}
            if filters:
                filter_kwargs.update(filters)
            
            appointments = await AsyncModelManager.filter_objects(
                AppointmentManagement, **filter_kwargs
            )
            
            # Convert to serializable format
            result = []
            for appointment in appointments:
                patient = await AsyncModelManager.get_object_or_none(
                    User, id=appointment.patient_id
                )
                patient_profile = await AsyncModelManager.get_object_or_none(
                    PatientProfile, user=patient
                ) if patient else None
                
                result.append({
                    'id': appointment.id,
                    'patient_name': f"{patient.first_name} {patient.last_name}" if patient else "Unknown",
                    'patient_email': patient.email if patient else "",
                    'appointment_date': appointment.appointment_date.isoformat(),
                    'appointment_time': appointment.appointment_time.strftime('%H:%M'),
                    'status': appointment.status,
                    'blood_type': patient_profile.blood_type if patient_profile else "",
                    'medical_condition': patient_profile.medical_condition if patient_profile else "",
                })
            
            return result
        except Exception as e:
            logger.error(f"Error getting user appointments: {str(e)}")
            raise

    @staticmethod
    @async_safe(timeout=30)
    async def create_appointment(appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new appointment asynchronously."""
        try:
            # Validate patient exists
            patient = await AsyncModelManager.get_object_or_none(
                User, id=appointment_data['patient_id']
            )
            if not patient:
                raise ValueError("Patient not found")
            
            # Create appointment
            appointment = await AsyncModelManager.create_object(
                AppointmentManagement,
                doctor_id=appointment_data['doctor_id'],
                patient_id=appointment_data['patient_id'],
                appointment_date=appointment_data['appointment_date'],
                appointment_time=appointment_data['appointment_time'],
                status='scheduled'
            )
            
            # Create notification
            await AsyncModelManager.create_object(
                Notification,
                user_id=appointment_data['patient_id'],
                title="Appointment Scheduled",
                message=f"Your appointment has been scheduled for {appointment_data['appointment_date']} at {appointment_data['appointment_time']}",
                notification_type='appointment'
            )
            
            return {
                'id': appointment.id,
                'patient_name': f"{patient.first_name} {patient.last_name}",
                'appointment_date': appointment.appointment_date.isoformat(),
                'appointment_time': appointment.appointment_time.strftime('%H:%M'),
                'status': appointment.status
            }
        except Exception as e:
            logger.error(f"Error creating appointment: {str(e)}")
            raise

class AsyncQueueService:
    """Async service for queue management."""
    
    @staticmethod
    @async_safe(timeout=30)
    async def get_queue_patients(department: str = None) -> Dict[str, List]:
        """Get queue patients asynchronously."""
        try:
            filter_kwargs = {'status': 'waiting'}
            if department:
                filter_kwargs['department'] = department
            
            # Get normal queue
            normal_queue = await AsyncModelManager.filter_objects(
                QueueManagement, **filter_kwargs
            )
            
            # Get priority queue
            priority_queue = await AsyncModelManager.filter_objects(
                PriorityQueue, **filter_kwargs
            )
            
            # Process normal queue
            normal_patients = []
            for queue_item in normal_queue:
                patient = await AsyncModelManager.get_object_or_none(
                    User, id=queue_item.patient_id
                )
                if patient:
                    normal_patients.append({
                        'id': queue_item.id,
                        'patient_name': f"{patient.first_name} {patient.last_name}",
                        'patient_email': patient.email,
                        'position': queue_item.position_in_queue,
                        'queue_number': queue_item.queue_number,
                        'estimated_wait': queue_item.estimated_wait_time
                    })
            
            # Process priority queue
            priority_patients = []
            for queue_item in priority_queue:
                patient = await AsyncModelManager.get_object_or_none(
                    User, id=queue_item.patient_id
                )
                if patient:
                    priority_patients.append({
                        'id': queue_item.id,
                        'patient_name': f"{patient.first_name} {patient.last_name}",
                        'patient_email': patient.email,
                        'priority_level': queue_item.priority_level,
                        'queue_number': queue_item.queue_number,
                        'estimated_wait': queue_item.estimated_wait_time
                    })
            
            return {
                'normal_queue': normal_patients,
                'priority_queue': priority_patients
            }
        except Exception as e:
            logger.error(f"Error getting queue patients: {str(e)}")
            raise

class AsyncMessagingService:
    """Async service for messaging functionality."""
    
    @staticmethod
    @async_safe(timeout=30)
    async def get_user_conversations(user_id: int) -> List[Dict]:
        """Get user conversations asynchronously."""
        try:
            conversations = await sync_to_async(list)(
                Conversation.objects.filter(participants__id=user_id)
            )
            
            result = []
            for conversation in conversations:
                # Get other participant
                participants = await sync_to_async(list)(
                    conversation.participants.exclude(id=user_id)
                )
                other_user = participants[0] if participants else None
                
                # Get last message
                last_message = await sync_to_async(
                    lambda: conversation.messages.order_by('-timestamp').first()
                )()
                
                result.append({
                    'id': conversation.id,
                    'other_user': {
                        'id': other_user.id,
                        'name': f"{other_user.first_name} {other_user.last_name}",
                        'email': other_user.email
                    } if other_user else None,
                    'last_message': {
                        'content': last_message.content,
                        'timestamp': last_message.timestamp.isoformat(),
                        'sender_id': last_message.sender_id
                    } if last_message else None,
                    'updated_at': conversation.updated_at.isoformat()
                })
            
            return result
        except Exception as e:
            logger.error(f"Error getting user conversations: {str(e)}")
            raise

    @staticmethod
    @async_safe(timeout=30)
    async def send_message(conversation_id: int, sender_id: int, content: str) -> Dict[str, Any]:
        """Send a message asynchronously."""
        try:
            # Get conversation
            conversation = await AsyncModelManager.get_object_or_none(
                Conversation, id=conversation_id
            )
            if not conversation:
                raise ValueError("Conversation not found")
            
            # Create message
            message = await AsyncModelManager.create_object(
                Message,
                conversation=conversation,
                sender_id=sender_id,
                content=content
            )
            
            # Update conversation timestamp
            await AsyncModelManager.update_object(
                conversation,
                updated_at=datetime.now()
            )
            
            # Create notifications for other participants
            participants = await sync_to_async(list)(
                conversation.participants.exclude(id=sender_id)
            )
            
            for participant in participants:
                await AsyncModelManager.create_object(
                    MessageNotification,
                    user=participant,
                    message=message,
                    is_sent=False
                )
            
            return {
                'id': message.id,
                'content': message.content,
                'timestamp': message.timestamp.isoformat(),
                'sender_id': message.sender_id
            }
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            raise

class AsyncMedicineService:
    """Async service for medicine inventory management."""
    
    @staticmethod
    @async_safe(timeout=30)
    async def get_medicine_inventory(search: str = None) -> List[Dict]:
        """Get medicine inventory asynchronously."""
        try:
            filter_kwargs = {}
            if search:
                filter_kwargs['medicine_name__icontains'] = search
            
            medicines = await AsyncModelManager.filter_objects(
                MedicineInventory, **filter_kwargs
            )
            
            result = []
            for medicine in medicines:
                result.append({
                    'id': medicine.id,
                    'medicine_name': medicine.medicine_name,
                    'quantity': medicine.quantity,
                    'unit': medicine.unit,
                    'expiry_date': medicine.expiry_date.isoformat() if medicine.expiry_date else None,
                    'supplier': medicine.supplier,
                    'batch_number': medicine.batch_number,
                    'cost_per_unit': str(medicine.cost_per_unit),
                    'total_cost': str(medicine.total_cost),
                    'date_added': medicine.date_added.isoformat()
                })
            
            return result
        except Exception as e:
            logger.error(f"Error getting medicine inventory: {str(e)}")
            raise

    @staticmethod
    @async_safe(timeout=30)
    async def add_medicine(medicine_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add medicine to inventory asynchronously."""
        try:
            medicine = await AsyncModelManager.create_object(
                MedicineInventory,
                **medicine_data
            )
            
            return {
                'id': medicine.id,
                'medicine_name': medicine.medicine_name,
                'quantity': medicine.quantity,
                'unit': medicine.unit,
                'expiry_date': medicine.expiry_date.isoformat() if medicine.expiry_date else None,
                'supplier': medicine.supplier,
                'batch_number': medicine.batch_number,
                'cost_per_unit': str(medicine.cost_per_unit),
                'total_cost': str(medicine.total_cost)
            }
        except Exception as e:
            logger.error(f"Error adding medicine: {str(e)}")
            raise

class AsyncNotificationService:
    """Async service for notification management."""
    
    @staticmethod
    @async_safe(timeout=30)
    async def get_user_notifications(user_id: int, limit: int = 50) -> List[Dict]:
        """Get user notifications asynchronously."""
        try:
            notifications = await sync_to_async(list)(
                Notification.objects.filter(user_id=user_id)
                .order_by('-created_at')[:limit]
            )
            
            result = []
            for notification in notifications:
                result.append({
                    'id': notification.id,
                    'message': notification.message,
                    'channel': notification.channel,
                    'delivery_status': notification.delivery_status,
                    'is_read': notification.is_read,
                    'created_at': notification.created_at.isoformat()
                })
            
            return result
        except Exception as e:
            logger.error(f"Error getting user notifications: {str(e)}")
            raise

    @staticmethod
    @async_safe(timeout=30)
    async def mark_notifications_read(user_id: int, notification_ids: List[int] = None) -> int:
        """Mark notifications as read asynchronously."""
        try:
            filter_kwargs = {'user_id': user_id, 'is_read': False}
            if notification_ids:
                filter_kwargs['id__in'] = notification_ids
            
            # Get notifications to update
            notifications = await AsyncModelManager.filter_objects(
                Notification, **filter_kwargs
            )
            
            # Update each notification
            updated_count = 0
            for notification in notifications:
                await AsyncModelManager.update_object(notification, is_read=True)
                updated_count += 1
            
            return updated_count
        except Exception as e:
            logger.error(f"Error marking notifications as read: {str(e)}")
            raise
    
    @staticmethod
    @async_safe(timeout=60)
    async def send_notification_to_all_patients(message: str, department: str = None) -> Dict[str, Any]:
        """
        Send notification to all patients.
        If department is specified, only notify patients in that department's queue.
        
        Args:
            message: The notification message to send
            department: Optional department filter
            
        Returns:
            Dictionary with notification statistics
        """
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            # Get all patient users
            patients = await sync_to_async(list)(
                User.objects.filter(role='patient').select_related('patient_profile')
            )
            
            notifications_created = []
            notifications_failed = []
            
            for patient in patients:
                try:
                    # Create notification record
                    notification = await AsyncModelManager.create_object(
                        Notification,
                        user=patient,
                        message=message,
                        channel=Notification.CHANNEL_WEBSOCKET,
                        delivery_status=Notification.DELIVERY_PENDING,
                        delivery_attempts=0
                    )
                    notifications_created.append(notification)
                    
                except Exception as e:
                    logger.error(f"Failed to create notification for patient {patient.id}: {str(e)}")
                    notifications_failed.append({
                        'patient_id': patient.id,
                        'error': str(e)
                    })
            
            logger.info(f"Created {len(notifications_created)} notifications for queue opening. Failed: {len(notifications_failed)}")
            
            return {
                'success': True,
                'total_patients': len(patients),
                'notifications_created': len(notifications_created),
                'notifications_failed': len(notifications_failed),
                'notification_ids': [n.id for n in notifications_created]
            }
            
        except Exception as e:
            logger.error(f"Error sending notifications to all patients: {str(e)}")
            raise
    
    @staticmethod
    @async_safe(timeout=30)
    async def mark_notification_delivered(notification_id: int) -> bool:
        """Mark a notification as delivered."""
        try:
            notification = await AsyncModelManager.get_object_or_none(
                Notification, id=notification_id
            )
            
            if notification:
                from django.utils import timezone
                await AsyncModelManager.update_object(
                    notification,
                    delivery_status=Notification.DELIVERY_DELIVERED,
                    delivered_at=timezone.now()
                )
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error marking notification as delivered: {str(e)}")
            return False
    
    @staticmethod
    @async_safe(timeout=30)
    async def retry_failed_notifications(max_attempts: int = 3) -> int:
        """Retry sending failed notifications."""
        try:
            # Get notifications that failed but haven't exceeded max attempts
            notifications = await sync_to_async(list)(
                Notification.objects.filter(
                    delivery_status=Notification.DELIVERY_FAILED,
                    delivery_attempts__lt=max_attempts
                )
            )
            
            retry_count = 0
            for notification in notifications:
                await AsyncModelManager.update_object(
                    notification,
                    delivery_status=Notification.DELIVERY_PENDING,
                    delivery_attempts=notification.delivery_attempts + 1
                )
                retry_count += 1
            
            return retry_count
            
        except Exception as e:
            logger.error(f"Error retrying failed notifications: {str(e)}")
            raise