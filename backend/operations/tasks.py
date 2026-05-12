"""
Celery tasks for operations module.
"""
import logging
from celery import shared_task
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


@shared_task(name='backend.operations.tasks.auto_close_queues')
def auto_close_queues():
    """
    Periodic task to automatically close queues that are past their scheduled end time.
    Runs every 5 minutes to check and close any queues that should be closed.
    """
    from .models import QueueStatus, QueueStatusLog
    from .serializers import QueueStatusSerializer
    
    logger.info(f"Running auto_close_queues task at {timezone.now()}")
    
    # Get all open queues
    open_queues = QueueStatus.objects.filter(is_open=True)
    
    closed_count = 0
    checked_count = 0
    
    for queue_status in open_queues:
        checked_count += 1
        
        # Check if queue should be auto-closed
        if queue_status.should_auto_close():
            try:
                old_status = queue_status.is_open
                queue_status.is_open = False
                queue_status.update_status_message()
                queue_status.save()
                
                # Log the automatic closure
                QueueStatusLog.objects.create(
                    department=queue_status.department,
                    previous_status=old_status,
                    new_status=False,
                    change_reason='schedule',
                    changed_by=queue_status.last_updated_by,
                    additional_notes=f'Queue automatically closed at scheduled time by system task'
                )
                
                # Broadcast closure via WebSocket
                try:
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f'queue_{queue_status.department}',
                        {
                            'type': 'queue_status_update',
                            'status': QueueStatusSerializer(queue_status).data,
                            'previous_status': old_status
                        }
                    )
                    async_to_sync(channel_layer.group_send)(
                        f'queue_{queue_status.department}',
                        {
                            'type': 'queue_notification',
                            'notification': {
                                'event': 'queue_closed',
                                'department': queue_status.department,
                                'message': f"The {queue_status.department} queue has been automatically closed at scheduled time.",
                                'timestamp': timezone.now().isoformat()
                            }
                        }
                    )
                except Exception as e:
                    logger.warning(f"WebSocket broadcast failed for {queue_status.department}: {str(e)}")
                
                closed_count += 1
                logger.info(f"Auto-closed queue {queue_status.department}")
                
            except Exception as e:
                logger.error(f"Error auto-closing queue {queue_status.department}: {str(e)}", exc_info=True)
    
    logger.info(f"Auto-close task completed: Checked {checked_count} queues, closed {closed_count}")
    
    return {
        'checked': checked_count,
        'closed': closed_count,
        'timestamp': timezone.now().isoformat()
    }


@shared_task(name='backend.operations.tasks.retry_failed_notifications')
def retry_failed_notifications():
    """
    Periodic task to retry sending failed notifications.
    Runs every 15 minutes to retry notifications that failed delivery.
    """
    from .models import Notification
    from .async_services import AsyncNotificationService
    import asyncio
    
    logger.info(f"Running retry_failed_notifications task at {timezone.now()}")
    
    try:
        # Get notifications that failed but haven't exceeded max attempts
        failed_notifications = Notification.objects.filter(
            delivery_status=Notification.DELIVERY_FAILED,
            delivery_attempts__lt=3
        )
        
        retry_count = 0
        
        for notification in failed_notifications:
            try:
                # Reset to pending for retry
                notification.delivery_status = Notification.DELIVERY_PENDING
                notification.delivery_attempts += 1
                notification.save()
                
                # Try to send via WebSocket again
                try:
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f'queue_user_{notification.user.id}',
                        {
                            'type': 'queue_notification',
                            'notification': {
                                'event': 'notification_retry',
                                'message': notification.message,
                                'notification_id': notification.id,
                                'timestamp': timezone.now().isoformat()
                            }
                        }
                    )
                    
                    # Mark as sent
                    notification.delivery_status = Notification.DELIVERY_SENT
                    notification.sent_at = timezone.now()
                    notification.save()
                    retry_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to retry notification {notification.id}: {str(e)}")
                    notification.delivery_status = Notification.DELIVERY_FAILED
                    notification.save()
                    
            except Exception as e:
                logger.error(f"Error processing notification {notification.id}: {str(e)}", exc_info=True)
        
        logger.info(f"Retry task completed: Retried {retry_count} notifications")
        
        return {
            'retried': retry_count,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in retry_failed_notifications task: {str(e)}", exc_info=True)
        return {'error': str(e)}


@shared_task(name='backend.operations.tasks.update_queue_statistics')
def update_queue_statistics():
    """
    Periodic task to update queue statistics and estimated wait times.
    Runs every 2 minutes to keep queue information current.
    """
    from .models import QueueStatus, QueueManagement
    from datetime import timedelta
    
    logger.info(f"Running update_queue_statistics task at {timezone.now()}")
    
    try:
        # Update all open queues
        open_queues = QueueStatus.objects.filter(is_open=True)
        
        for queue_status in open_queues:
            try:
                # Count waiting patients
                waiting_count = QueueManagement.objects.filter(
                    department=queue_status.department,
                    status='waiting'
                ).count()
                
                # Update statistics
                queue_status.total_waiting = waiting_count
                
                # Calculate estimated wait time (5 minutes per patient as baseline)
                if waiting_count > 0:
                    queue_status.estimated_wait_time = timedelta(minutes=5 * waiting_count)
                else:
                    queue_status.estimated_wait_time = None
                
                queue_status.update_status_message()
                queue_status.save()
                
                # Broadcast updated statistics
                try:
                    from .serializers import QueueStatusSerializer
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f'queue_{queue_status.department}',
                        {
                            'type': 'queue_status_update',
                            'status': QueueStatusSerializer(queue_status).data
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to broadcast statistics for {queue_status.department}: {str(e)}")
                    
            except Exception as e:
                logger.error(f"Error updating statistics for {queue_status.department}: {str(e)}", exc_info=True)
        
        logger.info(f"Queue statistics updated for {open_queues.count()} queues")
        
        return {
            'updated': open_queues.count(),
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in update_queue_statistics task: {str(e)}", exc_info=True)
        return {'error': str(e)}


@shared_task(name='backend.operations.tasks.process_queue_no_show')
def process_queue_no_show(queue_id: int):
    from datetime import timedelta
    from django.conf import settings
    from django.db import DatabaseError, transaction
    from django.db.models import Max
    from .models import QueueManagement, QueueStatus, Notification, WebPushSubscription, QueueNoShowAuditLog
    import json as _json
    from uuid import uuid4

    def _grace_seconds() -> int:
        raw = getattr(settings, "QUEUE_NO_SHOW_GRACE_SECONDS", 60)
        try:
            v = int(raw)
            return v if v > 0 else 60
        except Exception:
            return 60

    def _policy() -> str:
        v = str(getattr(settings, "QUEUE_NO_SHOW_POLICY", "move_to_end") or "").strip().lower()
        return v if v in ("move_to_end", "remove") else "move_to_end"

    def _log(entry: QueueManagement, event: str, metadata: dict | None = None):
        try:
            QueueNoShowAuditLog.objects.create(
                queue_entry=entry,
                patient=getattr(entry, "patient", None),
                actor=None,
                department=str(getattr(entry, "department", "") or ""),
                event=event,
                metadata=metadata or {},
            )
        except Exception:
            return

    def _send_web_push(user, payload) -> int:
        if not getattr(settings, "WEBPUSH_VAPID_PRIVATE_KEY", None) or not getattr(settings, "WEBPUSH_VAPID_PUBLIC_KEY", None):
            return 0
        try:
            from pywebpush import webpush, WebPushException
        except Exception:
            return 0
        sent = 0
        subs = list(WebPushSubscription.objects.filter(user=user, is_active=True))
        for sub in subs:
            try:
                webpush(
                    subscription_info=sub.subscription,
                    data=_json.dumps(payload),
                    vapid_private_key=settings.WEBPUSH_VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": settings.WEBPUSH_VAPID_SUBJECT},
                )
                sent += 1
            except WebPushException as e:
                try:
                    code = getattr(getattr(e, "response", None), "status_code", None)
                    if code in (404, 410):
                        sub.is_active = False
                        sub.save(update_fields=["is_active", "updated_at"])
                except Exception:
                    pass
            except Exception:
                continue
        return sent

    def _send_sms_http(to_number: str, message: str) -> tuple[bool, str]:
        url = str(getattr(settings, "SMS_HTTP_URL", "") or "").strip()
        token = str(getattr(settings, "SMS_HTTP_TOKEN", "") or "").strip()
        if not url:
            return False, "sms_http_url_missing"
        if not token:
            return False, "sms_http_token_missing"
        try:
            import requests
            resp = requests.post(
                url,
                json={"to": to_number, "message": message},
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            if 200 <= int(resp.status_code) < 300:
                return True, "sent"
            return False, f"http_{resp.status_code}"
        except Exception as e:
            return False, str(e)

    def _infer_phone(user, patient_profile) -> str | None:
        for attr in ["phone_number", "mobile_number", "contact_number", "phone", "mobile"]:
            try:
                val = getattr(user, attr, None)
                if isinstance(val, str) and val.strip():
                    return val.strip()
            except Exception:
                continue
        try:
            intake = getattr(patient_profile, "nursing_intake_assessment", None) or {}
            if isinstance(intake, dict):
                for key in ["phone_number", "mobile_number", "contact_number", "mobile", "phone"]:
                    v = intake.get(key)
                    if isinstance(v, str) and v.strip():
                        return v.strip()
        except Exception:
            pass
        return None

    now = timezone.now()
    try:
        event_id = uuid4().hex
        sync_v2 = bool(getattr(settings, "QUEUE_NO_SHOW_SYNC_V2", True))
        with transaction.atomic():
            entry = (QueueManagement.objects
                     .select_for_update()
                     .select_related("patient__user")
                     .filter(id=queue_id)
                     .first())
            if not entry:
                return {"ok": False, "reason": "not_found"}
            if entry.status != "called":
                return {"ok": False, "reason": "not_called", "status": entry.status}
            if entry.checked_in_at:
                return {"ok": False, "reason": "already_checked_in"}
            if entry.grace_expires_at and entry.grace_expires_at > now:
                return {"ok": False, "reason": "grace_not_expired", "grace_expires_at": entry.grace_expires_at.isoformat()}

            pol = _policy()
            entry.last_no_show_at = now
            entry.no_show_action = pol

            if pol == "remove":
                entry.status = "no_show"
                entry.dequeue_time = now
                entry.called_at = None
                entry.grace_expires_at = None
                entry.save(update_fields=["status", "dequeue_time", "called_at", "grace_expires_at", "last_no_show_at", "no_show_action", "updated_at"])
                _log(entry, "no_show_marked", {"reason": "grace_expired", "action": "remove"})
                _log(entry, "no_show_removed", {"reason": "grace_expired"})
            else:
                max_pos = (QueueManagement.objects
                           .select_for_update()
                           .filter(department=entry.department, status="waiting")
                           .aggregate(Max("position_in_queue"))
                           .get("position_in_queue__max") or 0)
                entry.status = "waiting"
                entry.called_at = None
                entry.grace_expires_at = None
                entry.enqueue_time = now
                entry.position_in_queue = int(max_pos) + 1
                entry.save(update_fields=["status", "called_at", "grace_expires_at", "enqueue_time", "position_in_queue", "last_no_show_at", "no_show_action", "updated_at"])
                _log(entry, "no_show_marked", {"reason": "grace_expired", "action": "move_to_end"})
                _log(entry, "no_show_moved_to_end", {"reason": "grace_expired"})

            try:
                qs = QueueStatus.objects.select_for_update().filter(department=entry.department).first()
                if qs:
                    qs.total_waiting = QueueManagement.objects.filter(department=entry.department, status='waiting').count()
                    if qs.current_serving == entry.queue_number:
                        replacement = (QueueManagement.objects
                                       .filter(department=entry.department, status__in=["called", "in_progress"])
                                       .exclude(id=entry.id)
                                       .order_by("-called_at", "-enqueue_time")
                                       .first())
                        qs.current_serving = replacement.queue_number if replacement else None
                    qs.save(update_fields=["current_serving", "total_waiting", "last_updated_at"])
            except Exception:
                pass
        effective_status = entry.status
        position_payload = {
            'department': entry.department,
            'queue_id': entry.id,
            'queue_number': entry.queue_number,
            'current_queue_number': entry.queue_number,
            'status': effective_status,
            'patient_id': entry.patient.user.id,
            'patient_name': entry.patient.user.full_name,
            'action': entry.no_show_action,
            'position_in_queue': entry.position_in_queue,
            'grace_expires_at': entry.grace_expires_at.isoformat() if entry.grace_expires_at else None,
            'updated_at': entry.updated_at.isoformat() if getattr(entry, "updated_at", None) else now.isoformat(),
            'event_id': event_id,
            'timestamp': now.isoformat(),
        }

        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'queue_{entry.department}',
                {
                    'type': 'queue_position_update',
                    'position': position_payload
                }
            )
            async_to_sync(channel_layer.group_send)(
                f'queue_user_{entry.patient.user.id}',
                {
                    'type': 'queue_position_update',
                    'position': position_payload
                }
            )
            if sync_v2:
                async_to_sync(channel_layer.group_send)(
                    f'queue_{entry.department}',
                    {
                        'type': 'queue_notification',
                        'notification': {
                            'event': 'queue_no_show_requeued' if entry.no_show_action == 'move_to_end' else 'queue_no_show_removed',
                            'department': entry.department,
                            'queue_id': entry.id,
                            'queue_number': entry.queue_number,
                            'patient_id': entry.patient.user.id,
                            'message': (
                                f"Patient #{entry.queue_number} was requeued to the end of the line."
                                if entry.no_show_action == 'move_to_end'
                                else f"Patient #{entry.queue_number} was marked as No-Show and removed."
                            ),
                            'timestamp': now.isoformat(),
                            'event_id': event_id,
                        }
                    }
                )
                async_to_sync(channel_layer.group_send)(
                    f'queue_{entry.department}',
                    {
                        'type': 'queue_notification',
                        'notification': {
                            'event': 'patient_removed' if effective_status in ('no_show', 'cancelled') else 'patient_requeued',
                            'department': entry.department,
                            'queue_id': entry.id,
                            'queue_number': entry.queue_number,
                            'patient_id': entry.patient.user.id,
                            'action': entry.no_show_action,
                            'timestamp': now.isoformat(),
                            'event_id': event_id,
                        }
                    }
                )
                try:
                    qs = QueueStatus.objects.filter(department=entry.department).first()
                    if qs:
                        async_to_sync(channel_layer.group_send)(
                            f'queue_{entry.department}',
                            {
                                'type': 'queue_status_update',
                                'status': {
                                    'department': qs.department,
                                    'is_open': qs.is_open,
                                    'current_serving': qs.current_serving,
                                    'total_waiting': qs.total_waiting,
                                    'status_message': qs.status_message,
                                },
                            }
                        )
                except Exception:
                    pass
        except Exception:
            pass

        msg = f"Queue update: you were marked as No-Show for Queue #{entry.queue_number} ({entry.department})."
        try:
            notif_ws = Notification.objects.create(
                user=entry.patient.user,
                message=msg,
                channel=Notification.CHANNEL_WEBSOCKET,
                delivery_status=Notification.DELIVERY_PENDING,
                delivery_attempts=0,
            )
            try:
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f'queue_user_{entry.patient.user.id}',
                    {
                        'type': 'queue_notification',
                        'notification': {
                            'event': 'queue_no_show',
                            'message': msg,
                            'notification_id': notif_ws.id,
                            'department': entry.department,
                            'queue_number': entry.queue_number,
                            'timestamp': now.isoformat(),
                        }
                    }
                )
                notif_ws.delivery_status = Notification.DELIVERY_SENT
                notif_ws.sent_at = now
                notif_ws.delivery_attempts = (notif_ws.delivery_attempts or 0) + 1
                notif_ws.save(update_fields=["delivery_status", "sent_at", "delivery_attempts", "updated_at"])
                _log(entry, "notification_sent", {"channel": "websocket", "notification_id": notif_ws.id})
            except Exception as e:
                notif_ws.delivery_status = Notification.DELIVERY_FAILED
                notif_ws.delivery_attempts = (notif_ws.delivery_attempts or 0) + 1
                notif_ws.save(update_fields=["delivery_status", "delivery_attempts", "updated_at"])
                _log(entry, "notification_failed", {"channel": "websocket", "error": str(e), "notification_id": notif_ws.id})
        except Exception:
            pass

        try:
            sent_push = _send_web_push(
                entry.patient.user,
                {
                    "title": "MediSync Queue Update",
                    "body": msg,
                    "url": "/patient-queue",
                    "tag": f"queue_{entry.department}",
                    "data": {"event": "queue_no_show", "department": entry.department, "queue_number": entry.queue_number},
                },
            )
            if sent_push:
                _log(entry, "notification_sent", {"channel": "push", "count": sent_push})
            else:
                _log(entry, "notification_failed", {"channel": "push", "reason": "no_active_subscriptions"})
        except Exception as e:
            _log(entry, "notification_failed", {"channel": "push", "error": str(e)})

        try:
            phone = _infer_phone(entry.patient.user, entry.patient)
            if phone:
                ok, reason = _send_sms_http(phone, msg)
                _log(entry, "notification_sent" if ok else "notification_failed", {"channel": "sms", "reason": reason})
            else:
                _log(entry, "notification_failed", {"channel": "sms", "reason": "phone_missing"})
        except Exception as e:
            _log(entry, "notification_failed", {"channel": "sms", "error": str(e)})

        try:
            with transaction.atomic():
                has_active = QueueManagement.objects.filter(department=entry.department, status__in=["called", "in_progress"]).exists()
                if not has_active:
                    next_priority = (QueueManagement.objects
                                     .select_for_update()
                                     .select_related("patient__user")
                                     .filter(department=entry.department, status='waiting', is_priority=True)
                                     .order_by('priority_position', 'enqueue_time')
                                     .first())
                    next_normal = (QueueManagement.objects
                                   .select_for_update()
                                   .select_related("patient__user")
                                   .filter(department=entry.department, status='waiting', is_priority=False)
                                   .order_by('enqueue_time')
                                   .first()) if not next_priority else None
                    nxt = next_priority or next_normal
                    if not nxt:
                        return {"ok": True, "no_show": True, "next": None}

                    grace = _grace_seconds()
                    nxt.status = "called"
                    nxt.called_at = timezone.now()
                    nxt.grace_expires_at = nxt.called_at + timedelta(seconds=grace)
                    nxt.checked_in_at = None
                    nxt.save(update_fields=["status", "called_at", "grace_expires_at", "checked_in_at", "updated_at"])
                    _log(nxt, "called", {"grace_seconds": grace, "source": "auto_after_no_show"})

            try:
                qs, _ = QueueStatus.objects.get_or_create(department=entry.department)
                qs.is_open = True
                qs.current_serving = nxt.queue_number
                qs.total_waiting = QueueManagement.objects.filter(department=entry.department, status='waiting').count()
                qs.status_message = 'Calling'
                qs.save()
            except Exception:
                pass
            try:
                if sync_v2:
                    qs2 = QueueStatus.objects.filter(department=entry.department).first()
                    if qs2:
                        channel_layer = get_channel_layer()
                        async_to_sync(channel_layer.group_send)(
                            f'queue_{entry.department}',
                            {
                                'type': 'queue_status_update',
                                'status': {
                                    'department': qs2.department,
                                    'is_open': qs2.is_open,
                                    'current_serving': qs2.current_serving,
                                    'total_waiting': qs2.total_waiting,
                                    'status_message': qs2.status_message,
                                },
                            }
                        )
            except Exception:
                pass

            call_msg = f"You are being called. Queue #{nxt.queue_number} ({nxt.department}). Please check in within {grace} seconds."
            try:
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f'queue_{nxt.department}',
                    {
                        'type': 'queue_position_update',
                        'position': {
                            'department': nxt.department,
                            'current_queue_number': nxt.queue_number,
                            'status': 'called',
                            'patient_id': nxt.patient.user.id,
                            'patient_name': nxt.patient.user.full_name,
                            'grace_expires_at': nxt.grace_expires_at.isoformat() if nxt.grace_expires_at else None,
                            'grace_seconds': grace,
                        }
                    }
                )
            except Exception:
                pass

            try:
                notif_ws = Notification.objects.create(
                    user=nxt.patient.user,
                    message=call_msg,
                    channel=Notification.CHANNEL_WEBSOCKET,
                    delivery_status=Notification.DELIVERY_PENDING,
                    delivery_attempts=0,
                )
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f'queue_user_{nxt.patient.user.id}',
                    {
                        'type': 'queue_notification',
                        'notification': {
                            'event': 'queue_called',
                            'message': call_msg,
                            'notification_id': notif_ws.id,
                            'department': nxt.department,
                            'queue_number': nxt.queue_number,
                            'timestamp': timezone.now().isoformat(),
                            'grace_expires_at': nxt.grace_expires_at.isoformat() if nxt.grace_expires_at else None,
                        }
                    }
                )
                notif_ws.delivery_status = Notification.DELIVERY_SENT
                notif_ws.sent_at = timezone.now()
                notif_ws.delivery_attempts = (notif_ws.delivery_attempts or 0) + 1
                notif_ws.save(update_fields=["delivery_status", "sent_at", "delivery_attempts", "updated_at"])
                _log(nxt, "notification_sent", {"channel": "websocket", "notification_id": notif_ws.id})
            except Exception as e:
                _log(nxt, "notification_failed", {"channel": "websocket", "error": str(e)})

            try:
                sent_push = _send_web_push(
                    nxt.patient.user,
                    {
                        "title": "MediSync Queue Update",
                        "body": call_msg,
                        "url": "/patient-queue",
                        "tag": f"queue_{nxt.department}",
                        "data": {"event": "queue_called", "department": nxt.department, "queue_number": nxt.queue_number},
                    },
                )
                if sent_push:
                    _log(nxt, "notification_sent", {"channel": "push", "count": sent_push})
                else:
                    _log(nxt, "notification_failed", {"channel": "push", "reason": "no_active_subscriptions"})
            except Exception as e:
                _log(nxt, "notification_failed", {"channel": "push", "error": str(e)})

            try:
                phone = _infer_phone(nxt.patient.user, nxt.patient)
                if phone:
                    ok, reason = _send_sms_http(phone, call_msg)
                    _log(nxt, "notification_sent" if ok else "notification_failed", {"channel": "sms", "reason": reason})
                else:
                    _log(nxt, "notification_failed", {"channel": "sms", "reason": "phone_missing"})
            except Exception as e:
                _log(nxt, "notification_failed", {"channel": "sms", "error": str(e)})

            try:
                process_queue_no_show.apply_async(args=[nxt.id], countdown=grace)
            except Exception as e:
                _log(nxt, "system_error", {"stage": "schedule_no_show_task", "error": str(e)})

        except Exception as e:
            _log(entry, "system_error", {"stage": "auto_call_next", "error": str(e)})

        return {"ok": True, "no_show": True, "queue_id": queue_id, "department": entry.department, "policy": entry.no_show_action}
    except (DatabaseError, Exception) as e:
        logger.error(f"process_queue_no_show failed: {str(e)}", exc_info=True)
        try:
            entry = QueueManagement.objects.filter(id=queue_id).first()
            if entry:
                _log(entry, "system_error", {"stage": "process_queue_no_show", "error": str(e)})
        except Exception:
            pass
        return {"ok": False, "error": str(e)}


@shared_task(name='backend.operations.tasks.process_expired_no_shows')
def process_expired_no_shows():
    from .models import QueueManagement
    now = timezone.now()
    qs = QueueManagement.objects.filter(
        status="called",
        checked_in_at__isnull=True,
        grace_expires_at__isnull=False,
        grace_expires_at__lte=now,
    ).values_list("id", flat=True)[:200]
    processed = 0
    for qid in list(qs):
        try:
            process_queue_no_show.delay(int(qid))
            processed += 1
        except Exception:
            continue
    return {"processed": processed, "timestamp": now.isoformat()}
