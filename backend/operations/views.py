from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import DatabaseError, transaction, connection
from django.db.models import Q, Max, Count
from django.conf import settings
from datetime import datetime, timedelta, date as dt_date, time as dt_time
import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import uuid
import time
import json
import secrets
import hashlib
import hmac

from django.core.files.base import ContentFile
from django.core.mail import EmailMessage

from .models import QueueManagement, QueueStatus, Notification, WebPushSubscription, QueueNoShowAuditLog, PainAssessment, AppointmentManagement, PatientAssignment, ConsultationNotes, DailySequenceCounter, PatientAssignmentAuditLog, FormAccessLog, Conversation, Message, MessageNotification, MessageReaction, MedicalRequest, GeneratedMedicalDocument, MedicalRecordTransfer, MedicalRecordTransferLog, encrypt_json_payload, decrypt_json_payload
from backend.users.models import User, GeneralDoctorProfile, NurseProfile, PatientProfile
from .pdf_service import generate_medical_certificate_pdf, generate_prescription_pdf, encrypt_pdf_aes256
from .serializers import (
    DashboardStatsSerializer, 
    NotificationSerializer, 
    QueueSerializer, 
    PainAssessmentSerializer
)

logger = logging.getLogger(__name__)

QUEUE_SCHEDULES_STORE = []
QUEUE_STATUS_STORE = {}
NEXT_SCHEDULE_ID = 1

def _corr_id(request):
    req_id = request.META.get('HTTP_X_REQUEST_ID') or request.headers.get('X-Request-ID') if hasattr(request, 'headers') else None
    if not req_id:
        req_id = str(uuid.uuid4())
    return req_id

def _broadcast(group, event, attempts=3, base_delay=0.1):
    try:
        channel_layer = get_channel_layer()
    except Exception:
        return
    for i in range(attempts):
        try:
            async_to_sync(channel_layer.group_send)(group, event)
            return
        except Exception:
            if i == attempts - 1:
                return
            time.sleep(base_delay * (2 ** i))

def _send_web_push(user, payload):
    if not settings.WEBPUSH_VAPID_PRIVATE_KEY or not settings.WEBPUSH_VAPID_PUBLIC_KEY:
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
                data=json.dumps(payload),
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

def _avg_consult_minutes_for_department(department: str) -> int:
    dept = str(department or "").strip() or "OPD"
    raw = getattr(settings, "QUEUE_AVG_CONSULT_MINUTES", 15)
    try:
        if isinstance(raw, dict):
            val = raw.get(dept) or raw.get(dept.upper()) or raw.get(dept.lower()) or raw.get("default") or 15
        else:
            val = raw
        mins = int(val)
        return mins if mins > 0 else 15
    except Exception:
        return 15

def _has_active_serving_patient(department: str) -> bool:
    dept = str(department or "").strip() or "OPD"
    return QueueManagement.objects.filter(department=dept, status__in=["called", "in_progress"]).exists()

def _count_waiting_ahead(entry: QueueManagement, *, department: str) -> int:
    dept = str(department or "").strip() or "OPD"
    base = QueueManagement.objects.filter(department=dept, status="waiting")
    try:
        is_priority = bool(getattr(entry, "is_priority", False))
        if is_priority:
            my_pos = int(getattr(entry, "priority_position", 0) or 0)
            my_time = getattr(entry, "enqueue_time", None) or getattr(entry, "created_at", None)
            qs = base.filter(is_priority=True)
            if my_time:
                return qs.filter(
                    Q(priority_position__lt=my_pos)
                    | (Q(priority_position=my_pos) & Q(enqueue_time__lt=my_time))
                ).count()
            return qs.filter(priority_position__lt=my_pos).count()
        my_time = getattr(entry, "enqueue_time", None) or getattr(entry, "created_at", None)
        prio_ahead = base.filter(is_priority=True).count()
        if my_time:
            normal_ahead = base.filter(is_priority=False, enqueue_time__lt=my_time).count()
        else:
            normal_ahead = 0
        return int(prio_ahead) + int(normal_ahead)
    except Exception:
        return 0

def _serialize_user(u):
    if not u:
        return None
    pic = getattr(u, "profile_picture", None)
    try:
        pic_val = pic.url if pic and hasattr(pic, "url") else (str(pic) if pic else None)
    except Exception:
        pic_val = None
    return {
        "id": u.id,
        "full_name": getattr(u, "full_name", "") or "",
        "role": str(getattr(u, "role", "") or ""),
        "profile_picture": pic_val,
        "verification_status": getattr(u, "verification_status", None),
        "is_active": getattr(u, "is_active", True),
    }

def _serialize_message(m):
    if not m:
        return None
    return {
        "id": m.id,
        "sender": _serialize_user(getattr(m, "sender", None)),
        "content": getattr(m, "content", "") or "",
        "created_at": m.created_at.isoformat() if getattr(m, "created_at", None) else None,
    }

def _require_verified_messaging_user(user):
    return str(getattr(user, "verification_status", "") or "").lower() == "approved"

def _ip_address(request) -> str:
    xff = request.META.get("HTTP_X_FORWARDED_FOR") or ""
    if xff:
        return str(xff.split(",")[0]).strip()
    return str(request.META.get("REMOTE_ADDR") or "").strip()

def _user_agent(request) -> str:
    return str(request.META.get("HTTP_USER_AGENT") or "").strip()

def _user_group(user_id: int) -> str:
    return f"messaging_{user_id}"

def _broadcast_user_notification(user_id: int, payload: dict):
    try:
        _broadcast(
            _user_group(user_id),
            {
                "type": "notification",
                "notification": payload,
            },
        )
    except Exception:
        return

def _normalize_channels(raw) -> list[str]:
    if raw is None:
        return [Notification.CHANNEL_WEBSOCKET]
    if isinstance(raw, str):
        val = raw.strip().lower()
        if not val:
            return [Notification.CHANNEL_WEBSOCKET]
        return [val]
    if isinstance(raw, list):
        out = []
        for x in raw:
            if isinstance(x, str) and x.strip():
                out.append(x.strip().lower())
        return out or [Notification.CHANNEL_WEBSOCKET]
    return [Notification.CHANNEL_WEBSOCKET]

def _queue_no_show_grace_seconds() -> int:
    raw = getattr(settings, "QUEUE_NO_SHOW_GRACE_SECONDS", 60)
    try:
        v = int(raw)
        return v if v > 0 else 60
    except Exception:
        return 60

def _queue_no_show_policy() -> str:
    val = str(getattr(settings, "QUEUE_NO_SHOW_POLICY", "move_to_end") or "").strip().lower()
    if val in ("move_to_end", "remove"):
        return val
    return "move_to_end"

def _queue_late_arrival_rejoin_seconds() -> int:
    raw = getattr(settings, "QUEUE_LATE_ARRIVAL_REJOIN_SECONDS", 600)
    try:
        v = int(raw)
        return v if v >= 0 else 600
    except Exception:
        return 600

def _broadcast_queue_user_notification(user_id: int, payload: dict):
    try:
        _broadcast(
            f"queue_user_{user_id}",
            {
                "type": "queue_notification",
                "notification": payload,
            },
        )
    except Exception:
        return

def _log_no_show_event(queue_entry: QueueManagement, *, event: str, actor=None, metadata: dict | None = None):
    try:
        QueueNoShowAuditLog.objects.create(
            queue_entry=queue_entry,
            patient=getattr(queue_entry, "patient", None),
            actor=actor,
            department=str(getattr(queue_entry, "department", "") or ""),
            event=event,
            metadata=metadata or {},
        )
    except Exception:
        return

def _infer_patient_phone_number(user, patient_profile) -> str | None:
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

def _create_and_send_queue_notifications(*, queue_entry: QueueManagement, message: str, actor=None, channels: list[str] | None = None, event: str = "queue_called") -> dict:
    channels = _normalize_channels(channels)
    user = queue_entry.patient.user
    results: dict[str, dict] = {}
    now = timezone.now()

    for ch in channels:
        if ch not in {Notification.CHANNEL_WEBSOCKET, Notification.CHANNEL_PUSH, Notification.CHANNEL_SMS}:
            ch = Notification.CHANNEL_WEBSOCKET

        notif = None
        try:
            notif = Notification.objects.create(
                user=user,
                message=message,
                channel=ch,
                delivery_status=Notification.DELIVERY_PENDING,
                delivery_attempts=0,
            )
        except Exception as e:
            _log_no_show_event(queue_entry, event="system_error", actor=actor, metadata={"stage": "notification_create", "error": str(e), "channel": ch})
            results[ch] = {"ok": False, "reason": "create_failed"}
            continue

        ok = True
        reason = "sent"
        try:
            if ch == Notification.CHANNEL_WEBSOCKET:
                _broadcast_queue_user_notification(
                    user.id,
                    {
                        "event": event,
                        "message": message,
                        "notification_id": notif.id,
                        "department": queue_entry.department,
                        "queue_number": queue_entry.queue_number,
                        "timestamp": now.isoformat(),
                        "grace_expires_at": queue_entry.grace_expires_at.isoformat() if queue_entry.grace_expires_at else None,
                    },
                )
            elif ch == Notification.CHANNEL_PUSH:
                sent = _send_web_push(
                    user,
                    {
                        "title": "MediSync Queue Update",
                        "body": message,
                        "url": "/patient-queue",
                        "tag": f"queue_{queue_entry.department}",
                        "data": {
                            "department": queue_entry.department,
                            "queue_number": queue_entry.queue_number,
                            "event": event,
                            "notification_id": notif.id,
                        },
                    },
                )
                if not sent:
                    ok = False
                    reason = "no_active_subscriptions"
            elif ch == Notification.CHANNEL_SMS:
                to_number = _infer_patient_phone_number(user, queue_entry.patient)
                if not to_number:
                    ok = False
                    reason = "phone_missing"
                else:
                    ok, reason = _send_sms_http(to_number, message)
        except Exception as e:
            ok = False
            reason = str(e)

        try:
            notif.delivery_status = Notification.DELIVERY_SENT if ok else Notification.DELIVERY_FAILED
            notif.sent_at = now if ok else None
            notif.delivery_attempts = (notif.delivery_attempts or 0) + 1
            notif.save(update_fields=["delivery_status", "sent_at", "delivery_attempts", "updated_at"])
        except Exception:
            pass

        results[ch] = {"ok": bool(ok), "reason": reason, "notification_id": getattr(notif, "id", None)}
        _log_no_show_event(
            queue_entry,
            event="notification_sent" if ok else "notification_failed",
            actor=actor,
            metadata={"channel": ch, "reason": reason, "notification_id": getattr(notif, "id", None)},
        )

    return results

def _normalize_priority(raw: str | None) -> str:
    v = str(raw or "").strip().lower()
    if v in ("low", "medium", "high", "urgent"):
        return v
    return "medium"

def _priority_from_severity(severity) -> str:
    try:
        s = int(severity)
    except Exception:
        s = None
    if s is None:
        return "medium"
    if s >= 8:
        return "urgent"
    if s >= 5:
        return "high"
    if s >= 3:
        return "medium"
    return "low"

def _create_notification_records(user: User, message: str, channels: list[str], payload: dict | None = None):
    created = []
    for ch in channels:
        if ch not in dict(Notification.CHANNEL_CHOICES):
            continue
        safe_out_of_app_message = "MediSync alert: You have a new patient referral. Please open the app to review details."
        if payload and isinstance(payload, dict):
            pr = str(payload.get("priority") or "").strip().lower()
            if pr:
                safe_out_of_app_message = f"MediSync alert: New patient referral ({pr}). Please open the app to review details."
        notif = Notification.objects.create(
            user=user,
            message=message,
            channel=ch,
            delivery_status=Notification.DELIVERY_PENDING,
        )
        created.append(notif)
        if ch == Notification.CHANNEL_WEBSOCKET:
            _broadcast_user_notification(
                user.id,
                payload
                or {
                    "event": "notification",
                    "notification_id": notif.id,
                    "message": message,
                    "channel": ch,
                    "created_at": notif.created_at.isoformat(),
                },
            )
        elif ch == Notification.CHANNEL_EMAIL:
            try:
                if user.email:
                    send_mail(
                        "MediSync: New Patient Referral",
                        safe_out_of_app_message,
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        fail_silently=True,
                    )
                    notif.delivery_status = Notification.DELIVERY_SENT
                    notif.sent_at = timezone.now()
                    notif.save(update_fields=["delivery_status", "sent_at"])
                else:
                    notif.delivery_status = Notification.DELIVERY_FAILED
                    notif.save(update_fields=["delivery_status"])
            except Exception:
                notif.delivery_status = Notification.DELIVERY_FAILED
                notif.save(update_fields=["delivery_status"])
        elif ch == Notification.CHANNEL_SMS:
            notif.delivery_status = Notification.DELIVERY_PENDING
            notif.save(update_fields=["delivery_status"])
    return created

def _audit_assignment_event(request, assignment: PatientAssignment, event: str, detail: str = ""):
    try:
        PatientAssignmentAuditLog.objects.create(
            actor=getattr(request, "user", None),
            assignment=assignment,
            patient=assignment.patient,
            doctor=assignment.doctor,
            event=event,
            detail=detail or "",
            ip_address=_ip_address(request),
            user_agent=_user_agent(request),
        )
    except Exception:
        return

def _log_form_access_ops(request, assignment: PatientAssignment, form_key: str, allowed: bool, reason: str = ""):
    try:
        FormAccessLog.objects.create(
            user=getattr(request, "user", None),
            patient=assignment.patient,
            assignment=assignment,
            role=str(getattr(getattr(request, "user", None), "role", "") or ""),
            form_key=str(form_key or "")[:64],
            endpoint=str(getattr(request, "path", "") or "")[:255],
            method=str(getattr(request, "method", "") or "")[:16],
            allowed=bool(allowed),
            reason=str(reason or ""),
            ip_address=_ip_address(request)[:64],
            user_agent=_user_agent(request),
        )
    except Exception:
        return

def _safe_insert_queue_entry(patient_profile, department, queue_number, est_wait, waiting_count):
    try:
        now = timezone.now()
        obj = QueueManagement.objects.create(
            patient=patient_profile,
            department=department,
            queue_number=queue_number,
            status='waiting',
            enqueue_time=now,
            position_in_queue=waiting_count + 1,
            estimated_wait_time=est_wait,
            total_patients=waiting_count + 1 
        )
        return obj
    except DatabaseError as e:
        msg = str(e)
        if 'daily_sequence_number' not in msg and 'queue_management.daily_sequence_number' not in msg:
            raise
        now = timezone.now()
        with connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO queue_management
                (patient_id, queue_number, total_patients, estimated_wait_time, department, status, enqueue_time, position_in_queue, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [patient_profile.id, queue_number, waiting_count + 1, est_wait, department, 'waiting', now, waiting_count + 1, now, now]
            )
            new_id = connection.ops.last_insert_id(cur, 'queue_management', 'id')
        return QueueManagement.objects.only('id').get(id=new_id)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def doctor_dashboard_stats(request):
    """
    Get dashboard statistics for a doctor
    """
    try:
        doctor = request.user
        today = timezone.now().date()
        
        # 1. Total Appointments (dummy for now)
        total_appointments = 0
        
        # 2. Patients in Queue
        normal_queue = QueueManagement.objects.filter(
            department='OPD',
            status='waiting',
            is_priority=False
        ).count()
        
        priority_queue = QueueManagement.objects.filter(
            department='OPD',
            status='waiting',
            is_priority=True
        ).count()
        
        total_patients = normal_queue + priority_queue
        
        # 3. Notifications
        notifications = Notification.objects.filter(
            user=doctor,
            is_read=False
        ).count()
        
        # 4. Monthly cancelled
        monthly_cancelled = 0
        
        stats_data = {
            'total_appointments': total_appointments,
            'total_patients': total_patients,
            'normal_queue': normal_queue,
            'priority_queue': priority_queue,
            'notifications': notifications,
            'pending_assessment': 0,
            'monthly_cancelled': monthly_cancelled
        }
        
        serializer = DashboardStatsSerializer(stats_data)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to fetch dashboard statistics: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def doctor_appointments(request):
    """
    Get appointments for the current doctor
    """
    try:
        user = request.user
        role = str(getattr(user, 'role', '') or '').lower()
        if role not in ['doctor', 'admin']:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        status_param = (request.query_params.get('status') or '').strip()
        date_param = (request.query_params.get('date') or '').strip()
        doctor_param = (request.query_params.get('doctor') or '').strip()

        # Resolve doctor profile
        doctor_user = user
        if role == 'admin' and doctor_param:
            doctor_user = User.objects.filter(id=doctor_param, role=User.Role.DOCTOR, is_active=True).first() or doctor_user
        elif role == 'doctor' and doctor_param and str(user.id) != str(doctor_param):
            # Doctors cannot query other doctors
            doctor_user = user

        doctor_profile = GeneralDoctorProfile.objects.filter(user=doctor_user).select_related('user').first()
        if not doctor_profile:
            return Response({'results': [], 'count': 0}, status=status.HTTP_200_OK)

        qs = (AppointmentManagement.objects
              .filter(doctor=doctor_profile)
              .select_related('patient__user', 'doctor__user'))

        if status_param:
            normalized = status_param.lower()
            if normalized == 'confirmed':
                normalized = 'scheduled'
            qs = qs.filter(status__iexact=normalized)

        if date_param:
            try:
                target_date = datetime.strptime(date_param, '%Y-%m-%d').date()
                qs = qs.filter(appointment_date__date=target_date)
            except Exception:
                return Response({'error': 'Invalid date format. Expected YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        qs = qs.order_by('appointment_date', 'appointment_time', 'appointment_id')

        results = []
        for appt in qs:
            patient_obj = getattr(appt, "patient", None)
            patient_user = getattr(patient_obj, "user", None) if patient_obj else None
            patient_name = (getattr(patient_user, "full_name", "") or "") if patient_user else ""

            doctor_obj = getattr(appt, "doctor", None)
            doctor_user = getattr(doctor_obj, "user", None) if doctor_obj else None
            doctor_name = (getattr(doctor_user, "full_name", "") or "") if doctor_user else ""
            doctor_user_id = getattr(doctor_obj, "user_id", None)
            dept = getattr(doctor_obj, "specialization", None)

            try:
                appt_date = appt.appointment_date.isoformat() if appt.appointment_date else None
            except Exception:
                appt_date = None
            try:
                appt_time = appt.appointment_time.strftime("%H:%M:%S") if appt.appointment_time else None
            except Exception:
                appt_time = None

            results.append(
                {
                    'id': appt.appointment_id,
                    'appointment_id': appt.appointment_id,
                    'patient_name': patient_name,
                    'patient': {
                        'id': getattr(appt, "patient_id", None),
                        'name': patient_name,
                    },
                    'doctor_id': doctor_user_id,
                    'doctor_name': doctor_name,
                    'department': dept,
                    'appointment_date': appt_date,
                    'appointment_time': appt_time,
                    'appointment_type': appt.appointment_type,
                    'type': appt.appointment_type,
                    'status': appt.status,
                    'notes': '',
                    'queue_number': appt.queue_number,
                    'consultation_finished_at': appt.consultation_finished_at.isoformat() if appt.consultation_finished_at else None,
                }
            )

        return Response({'results': results, 'count': len(results)}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception("doctor_appointments failed")
        return Response({'error': 'Failed to fetch appointments', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def doctor_queue_patients(request):
    """
    Get patients in queue for the current doctor
    """
    try:
        normal_queue = QueueManagement.objects.filter(
            department='OPD',
            status='waiting'
        ).order_by('created_at') # 'position_in_queue' might not exist, checking models... models.py said queue_number
        
        normal_serializer = QueueSerializer(normal_queue, many=True)
        
        return Response({
            'normal_queue': normal_serializer.data,
            'priority_queue': []
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to fetch queue patients: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def doctor_notifications(request):
    """
    Get notifications for the current doctor
    """
    try:
        doctor = request.user
        
        notifications = Notification.objects.filter(
            user=doctor
        ).order_by('-created_at')[:10]
        
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to fetch notifications: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def mark_notification_as_read(request, notification_id):
    try:
        doctor = request.user
        notification = Notification.objects.filter(
            id=notification_id,
            user=doctor
        ).first()
        
        if not notification:
            return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)
        
        notification.is_read = True
        notification.save()
        return Response({'message': 'Notification marked as read'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read(request):
    try:
        doctor = request.user
        Notification.objects.filter(user=doctor, is_read=False).update(is_read=True)
        return Response({'message': 'All notifications marked as read'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_patient_pain_history(request, patient_id):
    """
    Get pain assessment history for a specific patient.
    """
    try:
        # Check permissions - only doctors and nurses can view other patients' history
        if request.user.role not in ['doctor', 'nurse', 'admin']:
             return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        # Try to resolve patient
        try:
            # Check if patient_id is PatientProfile ID
            patient = PatientProfile.objects.get(id=patient_id)
        except PatientProfile.DoesNotExist:
            try:
                # Check if patient_id is User ID
                patient = PatientProfile.objects.get(user__id=patient_id)
            except PatientProfile.DoesNotExist:
                 return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)

        pain_assessments = PainAssessment.objects.filter(patient=patient).order_by('-created_at')
        serializer = PainAssessmentSerializer(pain_assessments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error fetching pain history: {str(e)}")
        return Response({'error': 'Failed to fetch pain history'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def record_pain_assessment(request, patient_id):
    """
    Record a new pain assessment for a patient.
    """
    try:
        # Check permissions
        if request.user.role not in ['doctor', 'nurse', 'admin']:
             return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        # Try to resolve patient
        try:
            patient = PatientProfile.objects.get(id=patient_id)
        except PatientProfile.DoesNotExist:
            try:
                patient = PatientProfile.objects.get(user__id=patient_id)
            except PatientProfile.DoesNotExist:
                 return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        data['patient'] = patient.id
        # performed_by is set in perform_create equivalent logic or explicitly here if needed
        # But since we are using functional views, we handle it manually or pass context
        
        serializer = PainAssessmentSerializer(data=data)
        if serializer.is_valid():
            serializer.save(performed_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error recording pain assessment: {str(e)}")
        return Response({'error': 'Failed to record assessment'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def patient_assessments(request):
    try:
        status_filter = str(request.query_params.get('status', '')).lower()
        results = []
        count = 0
        if status_filter == 'completed':
            from .models import PatientAssessmentArchive
            from .serializers import PatientAssessmentArchiveSerializer
            qs = PatientAssessmentArchive.objects.all()
            hospital = getattr(request.user, 'hospital_name', None)
            if hospital:
                qs = qs.filter(hospital_name__iexact=hospital)
            serializer = PatientAssessmentArchiveSerializer(qs.order_by('-last_assessed_at')[:50], many=True)
            results = serializer.data
            count = len(results)
        elif status_filter == 'in_progress':
            results = []
            count = 0
        else:
            results = []
            count = 0
        return Response({'results': results, 'count': count}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': f'Failed to fetch patient assessments: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def nurse_send_patient_records(request):
    try:
        corr = _corr_id(request)
        if request.user.role != 'nurse':
            return Response({'error': 'Only nurses can send patient records.'}, status=status.HTTP_403_FORBIDDEN)
        patient_id = request.data.get('patient_id')
        doctor_id = request.data.get('doctor_id')
        note = request.data.get('message') or ''
        channels = _normalize_channels(request.data.get("channels"))
        priority = _normalize_priority(request.data.get("priority"))
        severity = request.data.get("severity")
        if severity is not None:
            priority = _priority_from_severity(severity)
        if not patient_id or not doctor_id:
            return Response({'error': 'patient_id and doctor_id are required.'}, status=status.HTTP_400_BAD_REQUEST)

        patient_profile = PatientProfile.objects.filter(id=patient_id).first() or PatientProfile.objects.filter(user_id=patient_id).first()
        if not patient_profile:
            return Response({'error': 'Patient not found.'}, status=status.HTTP_404_NOT_FOUND)

        doctor_user = User.objects.filter(id=doctor_id, role=User.Role.DOCTOR).first()
        if not doctor_user:
            return Response({'error': 'Doctor not found.'}, status=status.HTTP_404_NOT_FOUND)

        patient_profile.assigned_doctor = doctor_user
        patient_profile.save(update_fields=['assigned_doctor'])

        # Update queue status to completed when sent to doctor
        try:
            from backend.operations.models import QueueManagement
            queue_entry = QueueManagement.objects.filter(
                patient=patient_profile,
                status__in=['waiting', 'called', 'in_progress']
            ).first()
            if queue_entry:
                queue_entry.status = 'completed'
                queue_entry.finished_at = timezone.now()
                queue_entry.save(update_fields=['status', 'finished_at', 'updated_at'])
                
                # Broadcast WebSocket update
                try:
                    from channels.layers import get_channel_layer
                    from asgiref.sync import async_to_sync
                    channel_layer = get_channel_layer()
                    dept = queue_entry.department or 'OPD'
                    async_to_sync(channel_layer.group_send)(
                        f"queue_{dept}",
                        {
                            "type": "queue_status_update",
                            "message": f"Patient {patient_profile.user.full_name} sent to doctor",
                            "department": dept
                        }
                    )
                except Exception as ws_err:
                    logger.warning(f"WS broadcast failed in nurse_send_patient_records: {ws_err}")
        except Exception as q_err:
            logger.warning(f"Queue update failed in nurse_send_patient_records: {q_err}")

        msg = f"A nurse sent patient records to you (Priority: {priority}). Open MediSync to review patient details."

        try:
            doctor_profile = GeneralDoctorProfile.objects.filter(user=doctor_user).first()
            if doctor_profile:
                from backend.operations.models import PatientAssignment
                existing = PatientAssignment.objects.filter(
                    patient=patient_profile,
                    doctor=doctor_profile,
                    status__in=['pending', 'accepted', 'in_progress']
                ).order_by('-assigned_at').first()
                if not existing:
                    assignment = PatientAssignment.objects.create(
                        assigned_by=request.user,
                        doctor=doctor_profile,
                        patient=patient_profile,
                        specialization_required=doctor_profile.specialization or '',
                        assignment_reason=note.strip() if isinstance(note, str) else '',
                        status='pending',
                        priority=priority
                    )
                    _audit_assignment_event(request, assignment, "created", "nurse_send_patient_records")
        except Exception:
            pass

        payload = {
            "event": "patient_assigned",
            "patient_profile_id": patient_profile.id,
            "priority": priority,
            "message": msg,
        }
        _create_notification_records(doctor_user, msg, channels, payload=payload)

        logger.info(f"[{corr}] nurse_send_patient_records nurse_id={request.user.id} patient_profile_id={patient_profile.id} doctor_id={doctor_user.id}")
        return Response({'success': True, 'message': 'Patient records sent to doctor.'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _safe_age_from_dob(dob) -> str:
    try:
        if not dob:
            return ""
        today = timezone.now().date()
        years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return str(max(0, years))
    except Exception:
        return ""


def _medical_request_types(req: MedicalRequest) -> list[str]:
    out: list[str] = []
    if bool(req.request_medical_certificate):
        out.append("Medical Certificate")
    if bool(req.request_prescription):
        out.append("Prescription")
    return out


def _hmac_hex(value: bytes) -> str:
    key = str(getattr(settings, "SECRET_KEY", "") or "").encode("utf-8")
    return hmac.new(key, value, hashlib.sha256).hexdigest()


def _doc_number(prefix: str, req_id: int) -> str:
    date_part = timezone.now().strftime("%Y%m%d")
    rand = secrets.token_hex(3).upper()
    return f"{prefix}-{date_part}-{req_id}-{rand}"


def _doctor_details_map(doctor_profiles: list[GeneralDoctorProfile]) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for d in doctor_profiles:
        if not d or not getattr(d, "id", None) or not getattr(d, "user", None):
            continue
        u = d.user
        out[int(d.id)] = {
            "id": int(d.id),
            "name": u.full_name or "",
            "specialty": d.specialization or "",
            "contact": {
                "email": u.email or "",
                "hospital_name": getattr(u, "hospital_name", "") or "",
                "hospital_address": getattr(u, "hospital_address", "") or "",
            },
            "availability": {
                "available_for_consultation": bool(d.available_for_consultation),
            },
        }
    return out


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_medical_request(request):
    user = request.user
    role = str(getattr(user, "role", "") or "").lower()
    if role != "patient":
        return Response({"error": "Only patients can create medical requests."}, status=status.HTTP_403_FORBIDDEN)

    patient_profile = PatientProfile.objects.select_related("user").filter(user=user).first()
    if not patient_profile:
        return Response({"error": "Patient profile not found."}, status=status.HTTP_404_NOT_FOUND)

    want_cert = bool(request.data.get("medical_certificate"))
    want_rx = bool(request.data.get("prescription"))
    if not want_cert and not want_rx:
        return Response({"error": "Select at least one request type."}, status=status.HTTP_400_BAD_REQUEST)

    patient_message = str(request.data.get("message") or "").strip()

    assignment = (
        PatientAssignment.objects.select_related("doctor__user")
        .filter(patient=patient_profile, status__in=["pending", "accepted", "in_progress"])
        .order_by("-assigned_at")
        .first()
    )
    doctor_profile = getattr(assignment, "doctor", None) if assignment else None
    if not doctor_profile:
        assigned_doctor_user = getattr(patient_profile, "assigned_doctor", None)
        if assigned_doctor_user:
            doctor_profile = GeneralDoctorProfile.objects.select_related("user").filter(user=assigned_doctor_user).first()

    if not doctor_profile:
        return Response({"error": "No assigned doctor found for this patient."}, status=status.HTTP_400_BAD_REQUEST)

    consult = None
    try:
        if assignment:
            consult = (
                ConsultationNotes.objects.filter(assignment=assignment, patient=patient_profile, doctor=doctor_profile)
                .order_by("-created_at")
                .first()
            )
        if not consult:
            consult = (
                ConsultationNotes.objects.filter(patient=patient_profile, doctor=doctor_profile)
                .order_by("-created_at")
                .first()
            )
    except Exception:
        consult = None

    req = MedicalRequest.objects.create(
        requested_by=user,
        patient=patient_profile,
        doctor=doctor_profile,
        assignment=assignment,
        consultation_notes=consult,
        request_medical_certificate=want_cert,
        request_prescription=want_rx,
        patient_message=patient_message,
        status="pending",
    )

    doctor_user = doctor_profile.user
    requested_items = ", ".join(_medical_request_types(req)) or "Medical Document"
    subject = f"MediSync Medical Request: {patient_profile.user.full_name} ({requested_items}) - Request #{req.id}"
    body_lines = [
        "A patient submitted a medical request in MediSync.",
        "",
        f"Request ID: {req.id}",
        f"Patient: {patient_profile.user.full_name}",
        f"Patient ID: {patient_profile.patient_id}",
        f"Requested: {requested_items}",
        f"Submitted: {req.created_at.strftime('%Y-%m-%d %H:%M:%S %Z') if req.created_at else ''}",
    ]
    if patient_message:
        body_lines.extend(["", "Patient Message:", patient_message])
    body_lines.extend(["", "Please open MediSync to review and fulfill the request."])
    body = "\n".join(body_lines)

    if doctor_user.email:
        try:
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [doctor_user.email], fail_silently=True)
        except Exception:
            pass

    doctor_msg = f"New medical request from {patient_profile.user.full_name}: {requested_items}."
    Notification.objects.create(user=doctor_user, message=doctor_msg, channel=Notification.CHANNEL_WEBSOCKET, delivery_status=Notification.DELIVERY_PENDING)
    _broadcast_user_notification(
        doctor_user.id,
        {
            "event": "medical_request_created",
            "medical_request_id": req.id,
            "patient_profile_id": patient_profile.id,
            "message": doctor_msg,
            "created_at": req.created_at.isoformat(),
        },
    )

    patient_msg = f"Your medical request has been sent to {doctor_user.full_name}."
    Notification.objects.create(user=user, message=patient_msg, channel=Notification.CHANNEL_WEBSOCKET, delivery_status=Notification.DELIVERY_PENDING)
    _broadcast_user_notification(
        user.id,
        {
            "event": "medical_request_submitted",
            "medical_request_id": req.id,
            "message": patient_msg,
            "created_at": req.created_at.isoformat(),
        },
    )

    return Response({"success": True, "id": req.id}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def patient_medical_requests(request):
    user = request.user
    role = str(getattr(user, "role", "") or "").lower()
    if role != "patient":
        return Response({"error": "Only patients can view their medical requests."}, status=status.HTTP_403_FORBIDDEN)

    patient_profile = PatientProfile.objects.select_related("user").filter(user=user).first()
    if not patient_profile:
        return Response({"results": [], "count": 0}, status=status.HTTP_200_OK)

    try:
        qs = (
            MedicalRequest.objects.select_related("doctor__user")
            .filter(patient=patient_profile)
            .order_by("-created_at")[:50]
        )
        doctor_profiles = [r.doctor for r in qs if getattr(r, "doctor_id", None) and getattr(r, "doctor", None)]
        doctor_map = _doctor_details_map(doctor_profiles)
        results = []
        missing_doctor = 0
        for r in qs:
            doctor = None
            if getattr(r, "doctor_id", None):
                doctor = doctor_map.get(int(r.doctor_id))
            if getattr(r, "doctor_id", None) and not doctor:
                missing_doctor += 1
            results.append(
                {
                    "id": r.id,
                    "status": r.status,
                    "requested": _medical_request_types(r),
                    "created_at": r.created_at.isoformat(),
                    "doctor": doctor,
                    "doctor_status": "assigned" if doctor else "unassigned",
                    "patient_message": r.patient_message,
                    "fulfilled_at": r.fulfilled_at.isoformat() if r.fulfilled_at else None,
                }
            )
        logger.info(
            "patient_medical_requests doctor_details_resolved=%s missing=%s patient_user_id=%s",
            len(doctor_map),
            missing_doctor,
            getattr(user, "id", None),
        )
        if missing_doctor:
            logger.warning(
                "patient_medical_requests missing_doctor_details count=%s patient_user_id=%s",
                missing_doctor,
                getattr(user, "id", None),
            )
        return Response({"results": results, "count": len(results)}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception("patient_medical_requests failed to fetch doctor details")
        return Response({"error": "Failed to load medical requests.", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def doctor_medical_requests(request):
    user = request.user
    role = str(getattr(user, "role", "") or "").lower()
    if role != "doctor":
        return Response({"error": "Only doctors can view incoming medical requests."}, status=status.HTTP_403_FORBIDDEN)

    doctor_profile = GeneralDoctorProfile.objects.select_related("user").filter(user=user).first()
    if not doctor_profile:
        return Response({"results": [], "count": 0}, status=status.HTTP_200_OK)

    try:
        qs = (
            MedicalRequest.objects.select_related("patient__user", "doctor__user", "assignment", "consultation_notes")
            .filter(doctor=doctor_profile, status="pending")
            .order_by("-created_at")[:50]
        )
        doctor_map = _doctor_details_map([doctor_profile])
        assignment_ids = [int(r.assignment_id) for r in qs if getattr(r, "assignment_id", None)]
        patient_ids = [int(r.patient_id) for r in qs if getattr(r, "patient_id", None)]
        notes_by_assignment: dict[int, ConsultationNotes] = {}
        notes_by_patient: dict[int, ConsultationNotes] = {}
        try:
            if assignment_ids:
                for n in (
                    ConsultationNotes.objects.filter(assignment_id__in=assignment_ids, doctor=doctor_profile)
                    .order_by("assignment_id", "-created_at")
                ):
                    if int(n.assignment_id) not in notes_by_assignment:
                        notes_by_assignment[int(n.assignment_id)] = n
            if patient_ids:
                for n in (
                    ConsultationNotes.objects.filter(patient_id__in=patient_ids, doctor=doctor_profile)
                    .order_by("patient_id", "-created_at")
                ):
                    if int(n.patient_id) not in notes_by_patient:
                        notes_by_patient[int(n.patient_id)] = n
        except Exception:
            notes_by_assignment = {}
            notes_by_patient = {}

        def _serialize_notes(n: ConsultationNotes | None) -> dict | None:
            if not n:
                return None
            return {
                "id": int(n.id),
                "status": str(getattr(n, "status", "") or ""),
                "created_at": n.created_at.isoformat() if getattr(n, "created_at", None) else None,
                "updated_at": n.updated_at.isoformat() if getattr(n, "updated_at", None) else None,
                "completed_at": n.completed_at.isoformat() if getattr(n, "completed_at", None) else None,
                "chief_complaint": str(getattr(n, "chief_complaint", "") or ""),
                "history_of_present_illness": str(getattr(n, "history_of_present_illness", "") or ""),
                "physical_examination": str(getattr(n, "physical_examination", "") or ""),
                "diagnosis": str(getattr(n, "diagnosis", "") or ""),
                "treatment_plan": str(getattr(n, "treatment_plan", "") or ""),
                "medications_prescribed": str(getattr(n, "medications_prescribed", "") or ""),
                "follow_up_instructions": str(getattr(n, "follow_up_instructions", "") or ""),
                "additional_notes": str(getattr(n, "additional_notes", "") or ""),
            }

        results = []
        for r in qs:
            pu = r.patient.user
            notes = getattr(r, "consultation_notes", None)
            if not notes and getattr(r, "assignment_id", None):
                notes = notes_by_assignment.get(int(r.assignment_id))
            if not notes and getattr(r, "patient_id", None):
                notes = notes_by_patient.get(int(r.patient_id))
            results.append(
                {
                    "id": r.id,
                    "created_at": r.created_at.isoformat(),
                    "requested": _medical_request_types(r),
                    "patient_profile_id": r.patient.id,
                    "patient_name": pu.full_name,
                    "patient_id": r.patient.patient_id,
                    "patient_dob": pu.date_of_birth.isoformat() if getattr(pu, "date_of_birth", None) else None,
                    "patient_age": _safe_age_from_dob(getattr(pu, "date_of_birth", None)),
                    "patient_gender": getattr(pu, "gender", "") or "",
                    "patient_email": pu.email,
                    "patient_message": r.patient_message,
                    "assignment_id": getattr(r.assignment, "id", None),
                    "consultation_notes": _serialize_notes(notes),
                    "doctor": doctor_map.get(int(doctor_profile.id)),
                }
            )
        logger.info("doctor_medical_requests count=%s doctor_user_id=%s", len(results), getattr(user, "id", None))
        return Response({"results": results, "count": len(results)}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception("doctor_medical_requests failed to load requests")
        return Response({"error": "Failed to load medical requests.", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def fulfill_medical_request(request, request_id: int):
    user = request.user
    role = str(getattr(user, "role", "") or "").lower()
    if role != "doctor":
        return Response({"error": "Only doctors can fulfill medical requests."}, status=status.HTTP_403_FORBIDDEN)

    doctor_profile = GeneralDoctorProfile.objects.select_related("user").filter(user=user).first()
    if not doctor_profile:
        return Response({"error": "Doctor profile not found."}, status=status.HTTP_404_NOT_FOUND)

    req = MedicalRequest.objects.select_related("patient__user", "doctor__user", "assignment", "consultation_notes").filter(id=request_id).first()
    if not req:
        return Response({"error": "Medical request not found."}, status=status.HTTP_404_NOT_FOUND)
    if req.status != "pending":
        return Response({"error": "Medical request is not pending."}, status=status.HTTP_400_BAD_REQUEST)
    if req.doctor_id and req.doctor_id != doctor_profile.id:
        return Response({"error": "Unauthorized for this request."}, status=status.HTTP_403_FORBIDDEN)

    certificate_input = request.data.get("certificate") or {}
    prescription_input = request.data.get("prescription") or {}
    doctor_message = str(request.data.get("doctor_message") or "").strip()

    issued_at = timezone.now()
    hospital_name = (getattr(user, "hospital_name", None) or getattr(req.patient, "hospital", "") or "").strip() or "Medical Facility"
    hospital_address = (getattr(user, "hospital_address", "") or "").strip()
    hospital_contact = " ".join([str(getattr(user, "hospital_phone", "") or "").strip(), str(getattr(user, "hospital_email", "") or "").strip()]).strip()

    pu = req.patient.user
    consultation_date = None
    if req.consultation_notes and req.consultation_notes.created_at:
        consultation_date = req.consultation_notes.created_at.date().isoformat()
    elif req.assignment and getattr(req.assignment, "assigned_at", None):
        consultation_date = req.assignment.assigned_at.date().isoformat()

    attachments: list[tuple[str, bytes, str]] = []
    generated_docs: list[GeneratedMedicalDocument] = []

    if bool(req.request_medical_certificate):
        leave_start = str(certificate_input.get("leave_start_date") or "").strip()
        leave_end = str(certificate_input.get("leave_end_date") or "").strip()
        diagnosis = str(certificate_input.get("diagnosis") or "").strip()
        if not diagnosis:
            diagnosis = str(getattr(req.consultation_notes, "diagnosis", "") or "").strip()
        hpi = str(getattr(req.consultation_notes, "history_of_present_illness", "") or "").strip()
        follow_up = str(getattr(req.consultation_notes, "follow_up_instructions", "") or "").strip()
        additional_notes = str(getattr(req.consultation_notes, "additional_notes", "") or "").strip()
        leave_days = str(certificate_input.get("leave_days") or "").strip()
        if not leave_days and leave_start and leave_end:
            try:
                start_d = datetime.strptime(leave_start, "%Y-%m-%d").date()
                end_d = datetime.strptime(leave_end, "%Y-%m-%d").date()
                delta = (end_d - start_d).days + 1
                if delta > 0:
                    leave_days = str(delta)
            except Exception:
                leave_days = leave_days

        cert_no = _doc_number("MC", req.id)
        cert_payload = {
            "hospital_name": hospital_name,
            "hospital_address": hospital_address,
            "hospital_contact": hospital_contact,
            "certificate_number": cert_no,
            "consultation_date": consultation_date or "",
            "patient_name": pu.full_name,
            "patient_dob": pu.date_of_birth.isoformat() if getattr(pu, "date_of_birth", None) else "",
            "patient_age": _safe_age_from_dob(getattr(pu, "date_of_birth", None)),
            "patient_gender": getattr(pu, "gender", "") or "",
            "diagnosis": diagnosis,
            "history_of_present_illness": hpi,
            "follow_up_instructions": follow_up,
            "additional_notes": additional_notes,
            "leave_start_date": leave_start,
            "leave_end_date": leave_end,
            "leave_days": leave_days,
            "doctor_name": user.full_name,
            "doctor_license_number": doctor_profile.license_number or "",
            "issued_at": issued_at.strftime("%Y-%m-%d %H:%M:%S %Z"),
        }
        try:
            raw_pdf = generate_medical_certificate_pdf(cert_payload)
            password = secrets.token_urlsafe(12)
            enc_pdf = encrypt_pdf_aes256(raw_pdf, password)
        except Exception as e:
            logger.exception("fulfill_medical_request certificate pdf/encryption failed request_id=%s", req.id)
            return Response({"error": "Failed to generate the medical certificate document.", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        auth_input = json.dumps({"type": "medical_certificate", "document_number": cert_no, "request_id": req.id, "issued_at": issued_at.isoformat()}, sort_keys=True).encode("utf-8")
        signature_hex = _hmac_hex(auth_input)
        sha256_hex = hashlib.sha256(raw_pdf).hexdigest()
        enc_pw = encrypt_json_payload({"password": password})

        doc = GeneratedMedicalDocument.objects.create(
            medical_request=req,
            patient=req.patient,
            doctor=doctor_profile,
            assignment=req.assignment,
            consultation_notes=req.consultation_notes,
            doc_type="medical_certificate",
            document_number=cert_no,
            file=ContentFile(enc_pdf, name=f"{cert_no}.pdf"),
            sha256_hex=sha256_hex,
            signature_hmac_hex=signature_hex,
            encrypted_password=enc_pw,
            is_encrypted=True,
            email_delivery_status="pending",
            metadata={"certificate": cert_payload},
            authenticated_at=issued_at,
            created_by=user,
            ip_address=_ip_address(request),
            user_agent=_user_agent(request),
        )
        generated_docs.append(doc)
        attachments.append((f"{cert_no}.pdf", enc_pdf, "application/pdf"))
        req.certificate_details = {**(req.certificate_details or {}), **{"certificate_number": cert_no, "leave_start_date": leave_start, "leave_end_date": leave_end, "diagnosis": diagnosis, "leave_days": leave_days}}

    if bool(req.request_prescription):
        meds = prescription_input.get("medications")
        if meds is None:
            meds_text = str(getattr(req.consultation_notes, "medications_prescribed", "") or "").strip()
            items = []
            for line in [x.strip() for x in meds_text.splitlines() if x.strip()]:
                items.append({"drug_name": line, "dosage": "", "frequency": "", "duration": "", "instructions": ""})
            meds = items
        if not isinstance(meds, list):
            meds = []

        rx_no = _doc_number("RX", req.id)
        rx_payload = {
            "hospital_name": hospital_name,
            "hospital_address": hospital_address,
            "hospital_contact": hospital_contact,
            "prescription_number": rx_no,
            "consultation_date": consultation_date or "",
            "patient_name": pu.full_name,
            "patient_id": req.patient.patient_id,
            "patient_dob": pu.date_of_birth.isoformat() if getattr(pu, "date_of_birth", None) else "",
            "patient_age": _safe_age_from_dob(getattr(pu, "date_of_birth", None)),
            "patient_gender": getattr(pu, "gender", "") or "",
            "doctor_name": user.full_name,
            "doctor_license_number": doctor_profile.license_number or "",
            "issued_at": issued_at.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "medications": meds,
        }
        try:
            raw_pdf = generate_prescription_pdf(rx_payload)
        except Exception as e:
            logger.exception("fulfill_medical_request prescription pdf generation failed request_id=%s", req.id)
            return Response({"error": "Failed to generate the prescription document.", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        auth_input = json.dumps({"type": "prescription", "document_number": rx_no, "request_id": req.id, "issued_at": issued_at.isoformat()}, sort_keys=True).encode("utf-8")
        signature_hex = _hmac_hex(auth_input)
        sha256_hex = hashlib.sha256(raw_pdf).hexdigest()

        doc = GeneratedMedicalDocument.objects.create(
            medical_request=req,
            patient=req.patient,
            doctor=doctor_profile,
            assignment=req.assignment,
            consultation_notes=req.consultation_notes,
            doc_type="prescription",
            document_number=rx_no,
            file=ContentFile(raw_pdf, name=f"{rx_no}.pdf"),
            sha256_hex=sha256_hex,
            signature_hmac_hex=signature_hex,
            encrypted_password="",
            is_encrypted=False,
            email_delivery_status="pending",
            metadata={"prescription": rx_payload},
            authenticated_at=issued_at,
            created_by=user,
            ip_address=_ip_address(request),
            user_agent=_user_agent(request),
        )
        generated_docs.append(doc)
        attachments.append((f"{rx_no}.pdf", raw_pdf, "application/pdf"))
        req.prescription_details = {**(req.prescription_details or {}), **{"prescription_number": rx_no, "medications": meds}}

    req.status = "fulfilled"
    req.fulfilled_by = user
    req.fulfilled_at = issued_at
    req.doctor_message = doctor_message
    req.save(update_fields=["status", "fulfilled_by", "fulfilled_at", "doctor_message", "certificate_details", "prescription_details", "updated_at"])

    patient_email = pu.email
    email_ok = False
    email_backend = str(getattr(settings, "EMAIL_BACKEND", "") or "")
    email_error = ""
    email_reason = ""
    non_delivering_backends = (
        "django.core.mail.backends.console.EmailBackend",
        "django.core.mail.backends.locmem.EmailBackend",
        "django.core.mail.backends.filebased.EmailBackend",
    )
    backend_can_deliver = email_backend not in non_delivering_backends
    if patient_email and attachments:
        subject = f"MediSync: Your Requested Medical Documents - Request #{req.id}"
        any_encrypted = any(bool(getattr(d, "is_encrypted", False)) for d in generated_docs)
        if any_encrypted:
            body = (
                "Your requested documents are attached.\n"
                "Some attachments are encrypted PDFs. The password is delivered via your MediSync in-app notifications.\n"
                "If you did not request these documents, contact your clinic immediately."
            )
        else:
            body = (
                "Your requested documents are attached.\n"
                "If you did not request these documents, contact your clinic immediately."
            )
        try:
            email = EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, [patient_email])
            for fn, data, mime in attachments:
                email.attach(fn, data, mime)
            email.send(fail_silently=False)
            email_ok = bool(backend_can_deliver)
            if not backend_can_deliver:
                email_reason = "email_backend_not_configured"
        except Exception as e:
            logger.exception("fulfill_medical_request email failed request_id=%s", req.id)
            email_ok = False
            email_error = str(e)
            email_reason = "email_send_failed"
    else:
        if not patient_email:
            email_reason = "missing_patient_email"
        elif not attachments:
            email_reason = "missing_attachments"

    for d in generated_docs:
        if email_ok:
            d.email_delivery_status = "sent"
            d.email_sent_at = issued_at
            d.save(update_fields=["email_delivery_status", "email_sent_at"])
        else:
            d.email_delivery_status = "failed"
            d.save(update_fields=["email_delivery_status"])
    
    encrypted_docs = [d for d in generated_docs if bool(getattr(d, "is_encrypted", False))]
    if encrypted_docs:
        doc_nums = ", ".join([f"{d.document_number}.pdf" for d in encrypted_docs])
        if email_ok:
            patient_pw_msg = f"Your encrypted document password is available in MediSync for: {doc_nums}"
        else:
            patient_pw_msg = f"Your encrypted document password is available in MediSync for: {doc_nums}. Email delivery may not be available on this system."
        Notification.objects.create(user=pu, message=patient_pw_msg, channel=Notification.CHANNEL_WEBSOCKET, delivery_status=Notification.DELIVERY_PENDING)
        _broadcast_user_notification(
            pu.id,
            {
                "event": "medical_document_password_available",
                "medical_request_id": req.id,
                "documents": [{"id": d.id, "doc_type": d.doc_type, "document_number": d.document_number} for d in encrypted_docs],
                "message": patient_pw_msg,
                "created_at": issued_at.isoformat(),
            },
        )

    if email_ok:
        patient_msg = f"Your requested medical documents for request #{req.id} were sent to your email."
    else:
        if email_reason == "missing_patient_email":
            patient_msg = f"Your requested medical documents for request #{req.id} are ready. No email address is on file."
        elif email_reason == "email_backend_not_configured":
            patient_msg = f"Your requested medical documents for request #{req.id} are ready. Email delivery is not configured on this system."
        else:
            patient_msg = f"Your requested medical documents for request #{req.id} are ready, but email delivery failed. Please contact your clinic."
    Notification.objects.create(user=pu, message=patient_msg, channel=Notification.CHANNEL_WEBSOCKET, delivery_status=Notification.DELIVERY_PENDING)
    _broadcast_user_notification(
        pu.id,
        {
            "event": "medical_request_fulfilled",
            "medical_request_id": req.id,
            "message": patient_msg,
            "email_sent": bool(email_ok),
            "email_reason": email_reason,
            "created_at": issued_at.isoformat(),
        },
    )

    if email_ok:
        doctor_msg = f"Medical request #{req.id} fulfilled for {pu.full_name}. Email sent to patient."
    else:
        doctor_msg = f"Medical request #{req.id} fulfilled for {pu.full_name}. Email not sent ({email_reason or 'unknown'})."
    Notification.objects.create(user=user, message=doctor_msg, channel=Notification.CHANNEL_WEBSOCKET, delivery_status=Notification.DELIVERY_PENDING)
    _broadcast_user_notification(
        user.id,
        {
            "event": "medical_request_fulfilled",
            "medical_request_id": req.id,
            "message": doctor_msg,
            "email_sent": bool(email_ok),
            "email_reason": email_reason,
            "created_at": issued_at.isoformat(),
        },
    )

    return Response(
        {
            "success": True,
            "documents": [{"id": d.id, "doc_type": d.doc_type, "document_number": d.document_number} for d in generated_docs],
            "email_sent": bool(email_ok),
            "email_reason": email_reason,
            "email_backend": email_backend,
            "email_error": email_error,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def medical_document_password(request, doc_id: int):
    user = request.user
    doc = GeneratedMedicalDocument.objects.select_related("patient__user", "doctor__user").filter(id=doc_id).first()
    if not doc:
        return Response({"error": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

    role = str(getattr(user, "role", "") or "").lower()
    is_owner_patient = getattr(doc.patient, "user_id", None) == getattr(user, "id", None)
    is_owner_doctor = getattr(getattr(doc.doctor, "user", None), "id", None) == getattr(user, "id", None)
    if role != "admin" and not is_owner_patient and not is_owner_doctor:
        return Response({"error": "Unauthorized."}, status=status.HTTP_403_FORBIDDEN)

    try:
        dec = decrypt_json_payload(doc.encrypted_password) if doc.encrypted_password else {}
        password = str(dec.get("password") or "")
    except Exception:
        password = ""
    if not password:
        return Response({"error": "Password unavailable."}, status=status.HTTP_404_NOT_FOUND)

    try:
        meta = dict(doc.metadata or {})
        log_entry = {
            "viewed_at": timezone.now().isoformat(),
            "viewer_user_id": getattr(user, "id", None),
            "ip_address": _ip_address(request),
            "user_agent": _user_agent(request),
        }
        history = meta.get("password_views")
        if isinstance(history, list):
            meta["password_views"] = (history + [log_entry])[-50:]
        else:
            meta["password_views"] = [log_entry]
        doc.metadata = meta
        doc.save(update_fields=["metadata"])
    except Exception:
        pass

    return Response({"password": password, "document_number": doc.document_number, "doc_type": doc.doc_type}, status=status.HTTP_200_OK)


def _rate_limit_medical_record_send(request, sender_user_id: int, patient_user_id: int) -> tuple[bool, int | None]:
    try:
        cooldown_key = f"rate:medical_record_send:cooldown:{sender_user_id}:{patient_user_id}"
        if cache.get(cooldown_key):
            return False, 60
        cache.set(cooldown_key, "1", timeout=60)
    except Exception:
        pass

    try:
        day_key = f"rate:medical_record_send:daily:{sender_user_id}:{timezone.now().date().isoformat()}"
        count = cache.get(day_key)
        if count is None:
            cache.set(day_key, 1, timeout=60 * 60 * 24)
        else:
            try:
                count_int = int(count)
            except Exception:
                count_int = 0
            if count_int >= 50:
                return False, None
            cache.set(day_key, count_int + 1, timeout=60 * 60 * 24)
    except Exception:
        pass

    return True, None


def _resolve_patient_profile_by_any(patient_id) -> PatientProfile | None:
    try:
        pid = int(patient_id)
    except Exception:
        return None
    return PatientProfile.objects.filter(id=pid).first() or PatientProfile.objects.filter(user_id=pid).first()


def _doctor_profile_for_user(user: User) -> GeneralDoctorProfile | None:
    return GeneralDoctorProfile.objects.select_related("user").filter(user=user).first()


def _collect_diagnoses(patient_profile: PatientProfile, doctor_profile: GeneralDoctorProfile | None) -> list[dict]:
    qs = ConsultationNotes.objects.select_related("assignment").filter(patient=patient_profile).order_by("-created_at")
    if doctor_profile:
        qs = qs.filter(doctor=doctor_profile)
    rows: list[dict] = []
    for n in qs[:100]:
        diag = str(getattr(n, "diagnosis", "") or "").strip()
        if not diag:
            continue
        rows.append(
            {
                "diagnosis": diag,
                "created_at": n.created_at.isoformat() if getattr(n, "created_at", None) else None,
                "completed_at": n.completed_at.isoformat() if getattr(n, "completed_at", None) else None,
                "assignment_id": getattr(n.assignment, "id", None),
            }
        )
    return rows


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def doctor_medical_records_preview(request):
    user = request.user
    role = str(getattr(user, "role", "") or "").lower()
    if role != "doctor":
        return Response({"error": "Only doctors can send medical records."}, status=status.HTTP_403_FORBIDDEN)

    doctor_profile = _doctor_profile_for_user(user)
    if not doctor_profile:
        return Response({"error": "Doctor profile not found."}, status=status.HTTP_404_NOT_FOUND)

    patient_id = (request.data or {}).get("patient_id")
    patient_profile = _resolve_patient_profile_by_any(patient_id)
    if not patient_profile:
        return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)

    pu = getattr(patient_profile, "user", None)
    diagnoses_rows = _collect_diagnoses(patient_profile, doctor_profile)
    diagnoses = [r.get("diagnosis") for r in diagnoses_rows if isinstance(r.get("diagnosis"), str)]
    diagnoses = [d for d in diagnoses if d and str(d).strip()]

    if not diagnoses:
        return Response(
            {
                "error": "No diagnoses found for this patient.",
                "code": "ERR_MISSING_DIAGNOSES",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    issued_at = timezone.now()
    last_consult = diagnoses_rows[0] if diagnoses_rows else {}
    consultation_date = str((last_consult.get("completed_at") or last_consult.get("created_at") or "") or "")
    hospital_name = getattr(user, "hospital_name", "") or getattr(doctor_profile, "hospital_name", "") or "Medical Facility"

    payload = {
        "hospital_name": hospital_name,
        "hospital_address": "",
        "hospital_contact": "",
        "certificate_number": "",
        "consultation_date": consultation_date,
        "patient_name": getattr(pu, "full_name", "") or "",
        "patient_dob": str(getattr(pu, "date_of_birth", "") or ""),
        "patient_age": _safe_age_from_dob(getattr(pu, "date_of_birth", None)),
        "patient_gender": getattr(pu, "gender", "") or "",
        "diagnoses": diagnoses,
        "doctor_name": getattr(user, "full_name", "") or "",
        "doctor_license_number": doctor_profile.license_number or "",
        "issued_at": issued_at.strftime("%Y-%m-%d %H:%M:%S %Z"),
    }

    return Response(
        {
            "success": True,
            "patient": {
                "id": getattr(pu, "id", None),
                "full_name": getattr(pu, "full_name", "") or "",
                "email": getattr(pu, "email", "") or "",
            },
            "doctor": {
                "id": getattr(user, "id", None),
                "full_name": getattr(user, "full_name", "") or "",
                "license_number": doctor_profile.license_number or "",
            },
            "diagnoses": diagnoses_rows,
            "certificate_preview": payload,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def doctor_send_medical_records(request):
    corr = _corr_id(request)
    user = request.user
    role = str(getattr(user, "role", "") or "").lower()
    if role != "doctor":
        return Response({"error": "Only doctors can send medical records."}, status=status.HTTP_403_FORBIDDEN)

    data = request.data or {}
    patient_id = data.get("patient_id")
    confirm = bool(data.get("confirm"))
    assignment_id = data.get("assignment_id")
    if not patient_id:
        return Response({"error": "patient_id is required."}, status=status.HTTP_400_BAD_REQUEST)
    if not confirm:
        return Response({"error": "Confirmation is required."}, status=status.HTTP_400_BAD_REQUEST)

    doctor_profile = _doctor_profile_for_user(user)
    if not doctor_profile:
        return Response({"error": "Doctor profile not found."}, status=status.HTTP_404_NOT_FOUND)

    patient_profile = _resolve_patient_profile_by_any(patient_id)
    if not patient_profile:
        return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)

    pu = getattr(patient_profile, "user", None)
    patient_user_id = getattr(pu, "id", None)
    patient_email = getattr(pu, "email", "") or ""
    if not patient_user_id:
        return Response({"error": "Patient account not found."}, status=status.HTTP_400_BAD_REQUEST)

    allowed, retry_after = _rate_limit_medical_record_send(request, int(getattr(user, "id", 0) or 0), int(patient_user_id))
    if not allowed:
        payload = {"error": "Too many requests. Please try again later.", "code": "ERR_RATE_LIMITED"}
        if retry_after:
            payload["retry_after_seconds"] = retry_after
        return Response(payload, status=status.HTTP_429_TOO_MANY_REQUESTS)

    diagnoses_rows = _collect_diagnoses(patient_profile, doctor_profile)
    diagnoses = [r.get("diagnosis") for r in diagnoses_rows if isinstance(r.get("diagnosis"), str)]
    diagnoses = [d for d in diagnoses if d and str(d).strip()]
    if not diagnoses:
        return Response({"error": "No diagnoses found for this patient.", "code": "ERR_MISSING_DIAGNOSES"}, status=status.HTTP_400_BAD_REQUEST)

    issued_at = timezone.now()
    rand = secrets.token_hex(3).upper()
    date_part = issued_at.strftime("%Y%m%d")
    doc_no = f"MCERT-{date_part}-{rand}"

    last_consult = diagnoses_rows[0] if diagnoses_rows else {}
    consultation_date = str((last_consult.get("completed_at") or last_consult.get("created_at") or "") or "")
    hospital_name = getattr(user, "hospital_name", "") or getattr(doctor_profile, "hospital_name", "") or "Medical Facility"

    cert_payload = {
        "hospital_name": hospital_name,
        "hospital_address": "",
        "hospital_contact": "",
        "certificate_number": doc_no,
        "consultation_date": consultation_date,
        "patient_name": getattr(pu, "full_name", "") or "",
        "patient_dob": str(getattr(pu, "date_of_birth", "") or ""),
        "patient_age": _safe_age_from_dob(getattr(pu, "date_of_birth", None)),
        "patient_gender": getattr(pu, "gender", "") or "",
        "diagnoses": diagnoses,
        "doctor_name": getattr(user, "full_name", "") or "",
        "doctor_license_number": doctor_profile.license_number or "",
        "issued_at": issued_at.strftime("%Y-%m-%d %H:%M:%S %Z"),
    }

    try:
        raw_pdf = generate_medical_certificate_pdf(cert_payload)
        password = secrets.token_urlsafe(12)
        enc_pdf = encrypt_pdf_aes256(raw_pdf, password)
    except Exception as e:
        logger.exception("doctor_send_medical_records pdf generation failed corr=%s", corr)
        return Response({"error": "Failed to generate the medical certificate document.", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    auth_input = json.dumps({"type": "medical_certificate", "document_number": doc_no, "issued_at": issued_at.isoformat()}, sort_keys=True).encode("utf-8")
    signature_hex = _hmac_hex(auth_input)
    sha256_hex = hashlib.sha256(raw_pdf).hexdigest()
    enc_pw = encrypt_json_payload({"password": password})

    assignment = None
    try:
        if assignment_id is not None:
            assignment = PatientAssignment.objects.filter(id=int(assignment_id), doctor=doctor_profile, patient=patient_profile).first()
    except Exception:
        assignment = None

    transfer = MedicalRecordTransfer.objects.create(
        sender=user,
        receiver_id=int(patient_user_id),
        patient=patient_profile,
        assignment=assignment,
        document_number=doc_no,
        file=ContentFile(enc_pdf, name=f"{doc_no}.pdf"),
        sha256_hex=sha256_hex,
        signature_hmac_hex=signature_hex,
        encrypted_password=enc_pw,
        is_encrypted=True,
        email_delivery_status="pending",
        metadata={"certificate": cert_payload, "diagnoses": diagnoses_rows},
        authenticated_at=issued_at,
        created_by=user,
        ip_address=_ip_address(request),
        user_agent=_user_agent(request),
    )
    MedicalRecordTransferLog.objects.create(
        transfer=transfer,
        actor=user,
        event="created",
        detail="medical_record_transfer_created",
        ip_address=_ip_address(request),
        user_agent=_user_agent(request),
    )

    email_ok = False
    email_error = ""
    email_reason = ""
    email_backend = str(getattr(settings, "EMAIL_BACKEND", "") or "")
    non_delivering_backends = (
        "django.core.mail.backends.console.EmailBackend",
        "django.core.mail.backends.locmem.EmailBackend",
        "django.core.mail.backends.filebased.EmailBackend",
    )
    backend_can_deliver = email_backend not in non_delivering_backends
    if patient_email:
        subject = f"MediSync: Medical Records - {doc_no}"
        body = (
            "Your medical certificate is attached as an encrypted PDF.\n"
            "The password is available in MediSync.\n"
            "If you did not request this, contact your clinic immediately."
        )
        try:
            email = EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, [patient_email])
            email.attach(f"{doc_no}.pdf", enc_pdf, "application/pdf")
            email.send(fail_silently=False)
            email_ok = bool(backend_can_deliver)
            if not backend_can_deliver:
                email_reason = "email_backend_not_configured"
        except Exception as e:
            logger.exception("doctor_send_medical_records email failed corr=%s transfer_id=%s", corr, transfer.id)
            email_ok = False
            email_error = str(e)
            email_reason = "email_send_failed"
    else:
        email_reason = "missing_patient_email"

    if email_ok:
        transfer.email_delivery_status = "sent"
        transfer.email_sent_at = issued_at
        transfer.save(update_fields=["email_delivery_status", "email_sent_at"])
        MedicalRecordTransferLog.objects.create(
            transfer=transfer,
            actor=user,
            event="email_sent",
            detail="medical_record_transfer_email_sent",
            ip_address=_ip_address(request),
            user_agent=_user_agent(request),
        )
    else:
        transfer.email_delivery_status = "failed"
        transfer.error_message = email_error or email_reason
        transfer.save(update_fields=["email_delivery_status", "error_message"])
        MedicalRecordTransferLog.objects.create(
            transfer=transfer,
            actor=user,
            event="email_failed",
            detail=(email_error or email_reason)[:1000],
            ip_address=_ip_address(request),
            user_agent=_user_agent(request),
        )

    if email_ok:
        msg = f"An encrypted medical certificate ({doc_no}.pdf) was sent to your email. The password is available in MediSync."
    else:
        if email_reason == "missing_patient_email":
            msg = f"Your encrypted medical certificate ({doc_no}.pdf) is ready. No email address is on file."
        elif email_reason == "email_backend_not_configured":
            msg = f"Your encrypted medical certificate ({doc_no}.pdf) is ready. Email delivery is not configured on this system."
        else:
            msg = f"Your encrypted medical certificate ({doc_no}.pdf) is ready. Email delivery failed."

    try:
        Notification.objects.create(
            user=pu,
            message=msg,
            channel=Notification.CHANNEL_WEBSOCKET,
            delivery_status=Notification.DELIVERY_PENDING,
            extra_data={"transfer_id": transfer.id, "document_number": doc_no}
        )
        _broadcast_user_notification(
            int(patient_user_id),
            {
                "event": "medical_record_transfer_created",
                "transfer_id": transfer.id,
                "document_number": doc_no,
                "message": msg,
                "created_at": issued_at.isoformat(),
            },
        )
    except Exception:
        pass

    logger.info(
        "[%s] doctor_send_medical_records doctor_id=%s patient_user_id=%s transfer_id=%s email_ok=%s email_reason=%s",
        corr,
        getattr(user, "id", None),
        patient_user_id,
        transfer.id,
        bool(email_ok),
        email_reason,
    )

    return Response(
        {
            "success": True,
            "transfer_id": transfer.id,
            "document_number": doc_no,
            "email_sent": bool(email_ok),
            "email_reason": email_reason,
            "email_backend": email_backend,
            "email_error": email_error,
            "created_at": issued_at.isoformat(),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def medical_record_transfer_status(request, transfer_id: int):
    user = request.user
    role = str(getattr(user, "role", "") or "").lower()
    transfer = MedicalRecordTransfer.objects.select_related("sender", "receiver").filter(id=transfer_id).first()
    if not transfer:
        return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    is_sender = getattr(transfer.sender, "id", None) == getattr(user, "id", None)
    is_receiver = getattr(transfer.receiver, "id", None) == getattr(user, "id", None)
    if role != "admin" and not is_sender and not is_receiver:
        return Response({"error": "Unauthorized."}, status=status.HTTP_403_FORBIDDEN)
    return Response(
        {
            "id": transfer.id,
            "document_number": transfer.document_number,
            "email_delivery_status": transfer.email_delivery_status,
            "email_sent_at": transfer.email_sent_at.isoformat() if transfer.email_sent_at else None,
            "created_at": transfer.created_at.isoformat() if transfer.created_at else None,
            "error_message": transfer.error_message or "",
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def medical_record_transfer_password(request, transfer_id: int):
    user = request.user
    role = str(getattr(user, "role", "") or "").lower()
    transfer = MedicalRecordTransfer.objects.select_related("sender", "receiver").filter(id=transfer_id).first()
    if not transfer:
        return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    is_sender = getattr(transfer.sender, "id", None) == getattr(user, "id", None)
    is_receiver = getattr(transfer.receiver, "id", None) == getattr(user, "id", None)
    if role != "admin" and not is_sender and not is_receiver:
        return Response({"error": "Unauthorized."}, status=status.HTTP_403_FORBIDDEN)
    try:
        dec = decrypt_json_payload(transfer.encrypted_password) if transfer.encrypted_password else {}
        password = str(dec.get("password") or "")
    except Exception:
        password = ""
    if not password:
        return Response({"error": "Password unavailable."}, status=status.HTTP_404_NOT_FOUND)
    MedicalRecordTransferLog.objects.create(
        transfer=transfer,
        actor=user,
        event="password_viewed",
        detail="medical_record_transfer_password_viewed",
        ip_address=_ip_address(request),
        user_agent=_user_agent(request),
    )
    return Response({"password": password, "document_number": transfer.document_number}, status=status.HTTP_200_OK)

# --- Stubs for missing views referenced in urls.py ---

@api_view(['GET', 'POST'])
def doctor_blocked_dates(request): return Response([], status=status.HTTP_200_OK)

@api_view(['POST'])
def doctor_block_date(request): return Response({}, status=status.HTTP_200_OK)

@api_view(['POST'])
def doctor_create_appointment(request): return Response({}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def schedule_appointment(request):
    """
    Patient-facing appointment scheduling endpoint.

    Accepts:
      - department: string (doctor specialization / department)
      - date: YYYY-MM-DD
      - time: HH:MM (24h)
      - type: string (frontend appointment type)
      - doctor_id: optional (user id of doctor)

    Returns created appointment payload.
    """
    try:
        user = request.user
        role = str(getattr(user, 'role', '') or '').lower()
        if role != 'patient':
            return Response({'error': 'Only patients can schedule appointments.'}, status=status.HTTP_403_FORBIDDEN)

        patient_profile = PatientProfile.objects.filter(user=user).first()
        if not patient_profile:
            return Response({'error': 'Patient profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data or {}
        dept = (data.get('department') or '').strip()
        date_str = (data.get('date') or '').strip()
        time_str = (data.get('time') or '').strip()
        frontend_type = (data.get('type') or '').strip()
        doctor_id = data.get('doctor_id')

        if not dept:
            return Response({'error': 'Department is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not date_str:
            return Response({'error': 'Date is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not time_str:
            return Response({'error': 'Time is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except Exception:
            return Response({'error': 'Invalid date format. Expected YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_time = datetime.strptime(time_str, '%H:%M').time()
        except Exception:
            return Response({'error': 'Invalid time format. Expected HH:MM (24h).'}, status=status.HTTP_400_BAD_REQUEST)

        # Reject scheduling in the past (local date)
        today = timezone.localdate()
        if isinstance(target_date, dt_date) and target_date < today:
            return Response({'error': 'Cannot schedule an appointment in the past.'}, status=status.HTTP_400_BAD_REQUEST)

        # Select doctor
        hospital_name = (getattr(patient_profile, 'hospital', None) or getattr(user, 'hospital_name', None) or '').strip()
        doctor_profile = None

        if doctor_id:
            doctor_user = User.objects.filter(id=doctor_id, role=User.Role.DOCTOR, is_active=True).first()
            if not doctor_user:
                return Response({'error': 'Doctor not found.'}, status=status.HTTP_404_NOT_FOUND)
            if str(getattr(doctor_user, 'verification_status', '') or '').lower() != 'approved':
                return Response({'error': 'Selected doctor is not verified.'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                doctor_profile = doctor_user.doctor_profile
            except Exception:
                doctor_profile = GeneralDoctorProfile.objects.filter(user=doctor_user).first()
            if not doctor_profile:
                return Response({'error': 'Doctor profile not found.'}, status=status.HTTP_400_BAD_REQUEST)
            if not getattr(doctor_profile, 'available_for_consultation', False):
                return Response({'error': 'Selected doctor is currently unavailable.'}, status=status.HTTP_400_BAD_REQUEST)
            if dept and (doctor_profile.specialization or '').strip():
                a = (doctor_profile.specialization or '').strip().lower()
                b = dept.lower()
                if a != b and (a not in b) and (b not in a):
                    return Response({'error': 'Selected doctor does not match the chosen department.'}, status=status.HTTP_400_BAD_REQUEST)
            if hospital_name and (getattr(doctor_user, 'hospital_name', '') or '').strip() != hospital_name:
                return Response({'error': 'Selected doctor is not in your hospital.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            qs = GeneralDoctorProfile.objects.filter(
                available_for_consultation=True,
                user__role=User.Role.DOCTOR,
                user__is_active=True,
                user__verification_status='approved',
            ).select_related('user')
            if dept:
                qs = qs.filter(specialization__icontains=dept)
            if hospital_name:
                qs = qs.filter(user__hospital_name=hospital_name)
            doctor_profile = qs.first()
            if not doctor_profile:
                return Response({'error': 'No available verified doctors found for this department.'}, status=status.HTTP_404_NOT_FOUND)

        # Prevent patient double-booking at same date/time (regardless doctor)
        existing_patient = AppointmentManagement.objects.filter(
            patient=patient_profile,
            appointment_date__date=target_date,
            appointment_time=target_time,
        ).exclude(status__in=['cancelled', 'no_show']).exists()
        if existing_patient:
            return Response({'error': 'You already have an appointment at this time.'}, status=status.HTTP_409_CONFLICT)

        # Prevent doctor double-booking
        existing_doctor = AppointmentManagement.objects.filter(
            doctor=doctor_profile,
            appointment_date__date=target_date,
            appointment_time=target_time,
        ).exclude(status__in=['cancelled', 'no_show']).exists()
        if existing_doctor:
            return Response({'error': 'This time slot is already booked for the selected doctor.'}, status=status.HTTP_409_CONFLICT)

        # Map frontend appointment type to backend model choices
        normalized = frontend_type.lower()
        if 'follow' in normalized:
            appt_type = 'follow_up'
        elif 'emergency' in normalized:
            appt_type = 'emergency'
        else:
            appt_type = 'consultation'

        # Build appointment datetime in current timezone
        dt_naive = datetime.combine(target_date, target_time)
        appt_dt = timezone.make_aware(dt_naive, timezone.get_current_timezone())

        # Generate queue_number: YYMMDD * 1000 + daily_seq (1..999)
        yymmdd = int(appt_dt.strftime('%y%m%d'))
        with transaction.atomic():
            counter, _ = DailySequenceCounter.objects.select_for_update().get_or_create(
                department='Appointment',
                date=target_date,
                defaults={'current_value': 0},
            )
            counter.current_value = int(counter.current_value or 0) + 1
            if counter.current_value > 999:
                return Response({'error': 'Daily appointment capacity exceeded.'}, status=status.HTTP_409_CONFLICT)
            counter.save(update_fields=['current_value'])
            queue_number = yymmdd * 1000 + counter.current_value

            appt = AppointmentManagement.objects.create(
                patient=patient_profile,
                doctor=doctor_profile,
                appointment_date=appt_dt,
                appointment_time=target_time,
                appointment_type=appt_type,
                queue_number=queue_number,
                status='scheduled',
            )

        try:
            doctor_user = doctor_profile.user
            patient_profile.assigned_doctor = doctor_user
            patient_profile.save(update_fields=["assigned_doctor"])

            if appt_type == "emergency":
                appt_priority = "urgent"
            elif appt_type == "follow_up":
                appt_priority = "low"
            else:
                appt_priority = "medium"

            existing_assignment = PatientAssignment.objects.filter(
                patient=patient_profile,
                doctor=doctor_profile,
                status__in=["pending", "accepted", "in_progress"],
            ).order_by("-assigned_at").first()
            if not existing_assignment:
                assignment = PatientAssignment.objects.create(
                    assigned_by=user,
                    doctor=doctor_profile,
                    patient=patient_profile,
                    specialization_required=(doctor_profile.specialization or "").strip(),
                    assignment_reason=f"Appointment scheduled ({appt_type}).",
                    status="pending",
                    priority=appt_priority,
                )
                _audit_assignment_event(request, assignment, "created", "schedule_appointment")

            channels = _normalize_channels(data.get("notify_channels") or data.get("channels"))
            when = appt_dt.strftime("%Y-%m-%d %H:%M")
            msg = f"New {appt_type.replace('_', ' ')} scheduled at {when} (Priority: {appt_priority}). Open MediSync to review patient details."
            payload_ws = {
                "event": "patient_assigned",
                "appointment_id": appt.appointment_id,
                "patient_profile_id": patient_profile.id,
                "priority": appt_priority,
                "message": msg,
            }
            _create_notification_records(doctor_user, msg, channels, payload=payload_ws)
        except Exception:
            pass

        payload = {
            'appointment_id': appt.appointment_id,
            'appointment_date': appt.appointment_date.isoformat(),
            'appointment_time': appt.appointment_time.strftime('%H:%M:%S'),
            'status': appt.status,
            'appointment_type': appt.appointment_type,
            'type': appt.appointment_type,
            'doctor_id': appt.doctor.user_id,
            'doctor_name': appt.doctor.user.full_name,
            'department': appt.doctor.specialization,
            'queue_number': appt.queue_number,
        }
        return Response(payload, status=status.HTTP_201_CREATED)
    except Exception as e:
        logger.exception("schedule_appointment failed")
        return Response({'error': 'Failed to schedule appointment', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST', 'PATCH'])
@permission_classes([IsAuthenticated])
def reschedule_appointment(request, appointment_id):
    """
    Patient reschedule endpoint. Only the owning patient can reschedule.
    """
    try:
        user = request.user
        role = str(getattr(user, 'role', '') or '').lower()
        if role != 'patient':
            return Response({'error': 'Only patients can reschedule appointments.'}, status=status.HTTP_403_FORBIDDEN)

        patient_profile = PatientProfile.objects.filter(user=user).first()
        if not patient_profile:
            return Response({'error': 'Patient profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        appt = AppointmentManagement.objects.filter(appointment_id=appointment_id, patient=patient_profile).select_related('doctor__user').first()
        if not appt:
            return Response({'error': 'Appointment not found.'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data or {}
        date_str = (data.get('date') or '').strip()
        time_str = (data.get('time') or '').strip()
        if not date_str or not time_str:
            return Response({'error': 'Date and time are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except Exception:
            return Response({'error': 'Invalid date format. Expected YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_time = datetime.strptime(time_str, '%H:%M').time()
        except Exception:
            return Response({'error': 'Invalid time format. Expected HH:MM (24h).'}, status=status.HTTP_400_BAD_REQUEST)

        # Prevent double-booking patient and doctor (excluding the appointment being rescheduled)
        if AppointmentManagement.objects.filter(
            patient=patient_profile,
            appointment_date__date=target_date,
            appointment_time=target_time,
        ).exclude(appointment_id=appt.appointment_id).exclude(status__in=['cancelled', 'no_show']).exists():
            return Response({'error': 'You already have an appointment at this time.'}, status=status.HTTP_409_CONFLICT)

        if AppointmentManagement.objects.filter(
            doctor=appt.doctor,
            appointment_date__date=target_date,
            appointment_time=target_time,
        ).exclude(appointment_id=appt.appointment_id).exclude(status__in=['cancelled', 'no_show']).exists():
            return Response({'error': 'This time slot is already booked for the selected doctor.'}, status=status.HTTP_409_CONFLICT)

        dt_naive = datetime.combine(target_date, target_time)
        appt_dt = timezone.make_aware(dt_naive, timezone.get_current_timezone())

        appt.appointment_date = appt_dt
        appt.appointment_time = target_time
        appt.status = 'rescheduled'
        appt.save(update_fields=['appointment_date', 'appointment_time', 'status', 'updated_at'])

        payload = {
            'appointment_id': appt.appointment_id,
            'appointment_date': appt.appointment_date.isoformat(),
            'appointment_time': appt.appointment_time.strftime('%H:%M:%S'),
            'status': appt.status,
            'appointment_type': appt.appointment_type,
            'type': appt.appointment_type,
            'doctor_id': appt.doctor.user_id,
            'doctor_name': appt.doctor.user.full_name,
            'department': appt.doctor.specialization,
            'queue_number': appt.queue_number,
        }
        return Response(payload, status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception("reschedule_appointment failed")
        return Response({'error': 'Failed to reschedule appointment', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST', 'PATCH'])
@permission_classes([IsAuthenticated])
def cancel_appointment(request, appointment_id):
    try:
        user = request.user
        role = str(getattr(user, 'role', '') or '').lower()

        appt = AppointmentManagement.objects.filter(appointment_id=appointment_id).select_related('patient__user', 'doctor__user').first()
        if not appt:
            return Response({'error': 'Appointment not found.'}, status=status.HTTP_404_NOT_FOUND)

        allowed_staff_roles = {'doctor', 'nurse', 'admin'}
        if role == 'patient':
            patient_profile = PatientProfile.objects.filter(user=user).first()
            if not patient_profile or appt.patient_id != patient_profile.id:
                return Response({'error': 'Unauthorized.'}, status=status.HTTP_403_FORBIDDEN)
        elif role not in allowed_staff_roles:
            return Response({'error': 'Unauthorized.'}, status=status.HTTP_403_FORBIDDEN)

        if appt.status in ['cancelled', 'completed']:
            return Response({'error': 'Appointment cannot be cancelled.'}, status=status.HTTP_409_CONFLICT)

        appt.status = 'cancelled'
        appt.save(update_fields=['status', 'updated_at'])
        return Response({'success': True}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception("cancel_appointment failed")
        return Response({'error': 'Failed to cancel appointment', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_in_appointment(request, appointment_id):
    if request.user.role not in ['doctor', 'nurse', 'admin']:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    appt = AppointmentManagement.objects.filter(appointment_id=appointment_id).first()
    if not appt:
        return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)
    appt.status = 'checked_in'
    appt.checked_in_at = timezone.now()
    appt.save(update_fields=['status', 'checked_in_at', 'updated_at'])
    return Response({'success': True}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_consultation(request, appointment_id):
    if request.user.role not in ['doctor', 'admin']:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    appt = AppointmentManagement.objects.filter(appointment_id=appointment_id).first()
    if not appt:
        return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)
    appt.status = 'in_progress'
    appt.consultation_started_at = timezone.now()
    appt.save(update_fields=['status', 'consultation_started_at', 'updated_at'])
    return Response({'success': True}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def finish_consultation(request, appointment_id):
    if request.user.role not in ['doctor', 'admin']:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    appt = AppointmentManagement.objects.filter(appointment_id=appointment_id).first()
    if not appt:
        return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)
    appt.status = 'completed'
    appt.consultation_finished_at = timezone.now()
    appt.save(update_fields=['status', 'consultation_finished_at', 'updated_at'])
    return Response({'success': True}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notify_patient_appointment(request, appointment_id):
    if request.user.role not in ['doctor', 'nurse', 'admin']:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    appt = AppointmentManagement.objects.filter(appointment_id=appointment_id).select_related('patient__user', 'doctor__user').first()
    if not appt:
        return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)
    try:
        dt = appt.appointment_date
        msg = f"Appointment reminder: {dt.strftime('%Y-%m-%d %H:%M')}."
    except Exception:
        msg = "Appointment reminder."
    notif = Notification.objects.create(
        user=appt.patient.user,
        message=msg,
        channel=Notification.CHANNEL_WEBSOCKET,
        delivery_status=Notification.DELIVERY_SENT,
        sent_at=timezone.now(),
    )
    try:
        _send_web_push(
            appt.patient.user,
            {
                "title": "MediSync Appointment Reminder",
                "body": msg,
                "url": "/patient-appointment-schedule",
                "tag": "appointment_reminder",
                "data": {"appointment_id": appointment_id, "event": "appointment_reminder"},
            },
        )
    except Exception:
        pass
    payload = NotificationSerializer(notif).data
    return Response({'message': 'Notification queued', 'notification': payload}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def patient_appointments(request):
    """
    Return the authenticated patient's appointments.
    """
    try:
        user = request.user
        role = str(getattr(user, 'role', '') or '').lower()
        if role != 'patient':
            return Response({'error': 'Only patients can access this endpoint.'}, status=status.HTTP_403_FORBIDDEN)
        patient_profile = PatientProfile.objects.filter(user=user).first()
        if not patient_profile:
            return Response({'error': 'Patient profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        qs = (AppointmentManagement.objects
              .filter(patient=patient_profile)
              .select_related('doctor__user')
              .order_by('-appointment_date'))

        results = []
        for appt in qs:
            doctor_obj = getattr(appt, "doctor", None)
            doctor_user = getattr(doctor_obj, "user", None) if doctor_obj else None
            doctor_name = (getattr(doctor_user, "full_name", "") or "") if doctor_user else ""
            doctor_user_id = getattr(doctor_obj, "user_id", None)
            dept = getattr(doctor_obj, "specialization", None)

            try:
                appt_date = appt.appointment_date.isoformat() if appt.appointment_date else None
            except Exception:
                appt_date = None
            try:
                appt_time = appt.appointment_time.strftime("%H:%M:%S") if appt.appointment_time else None
            except Exception:
                appt_time = None

            results.append(
                {
                    'appointment_id': appt.appointment_id,
                    'id': appt.appointment_id,
                    'appointment_date': appt_date,
                    'appointment_time': appt_time,
                    'status': appt.status,
                    'appointment_type': appt.appointment_type,
                    'type': appt.appointment_type,
                    'doctor_id': doctor_user_id,
                    'doctor_name': doctor_name,
                    'department': dept,
                    'queue_number': appt.queue_number,
                    'consultation_finished_at': appt.consultation_finished_at.isoformat() if appt.consultation_finished_at else None,
                }
            )

        return Response({'results': results}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception("patient_appointments failed")
        return Response({'error': 'Failed to fetch appointments', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def patient_dashboard_summary(request):
    try:
        corr = _corr_id(request)
        user = request.user
        dept = request.query_params.get('department') or 'OPD'
        try:
            patient_profile = user.patient_profile
        except (AttributeError, PatientProfile.DoesNotExist):
            patient_profile = PatientProfile.objects.filter(user=user).first()
        my_entry = None
        if patient_profile:
            my_entry = (QueueManagement.objects
                        .only('queue_number', 'status', 'enqueue_time', 'called_at', 'grace_expires_at', 'last_no_show_at', 'is_priority', 'priority_position')
                        .filter(patient=patient_profile, department=dept, status__in=['waiting', 'called', 'no_show'])
                        .order_by('-enqueue_time')
                        .first())
        now_called = (QueueManagement.objects
                      .only('queue_number', 'patient', 'called_at', 'is_priority', 'priority_position')
                      .filter(department=dept, status='called')
                      .order_by('-called_at')
                      .first())
        now_in_progress = (QueueManagement.objects
                           .only('queue_number', 'patient', 'enqueue_time', 'is_priority', 'priority_position')
                           .filter(department=dept, status='in_progress')
                           .order_by('-is_priority', 'priority_position', 'enqueue_time')
                           .first())
        now_serving = now_called or now_in_progress
        avg_mins = _avg_consult_minutes_for_department(dept)
        waiting_count = QueueManagement.objects.filter(department=dept, status='waiting').count()
        has_active = bool(now_serving)
        
        # Calculate progress value (0-100)
        # If my_entry is position 1, progress is higher than if position 10
        progress = 0
        if my_entry and my_entry.status == 'waiting':
            # Get my actual position in the waiting list
            my_pos = QueueManagement.objects.filter(
                department=dept,
                status='waiting',
                enqueue_time__lt=my_entry.enqueue_time
            ).count() + 1
            
            total_waiting = waiting_count
            if total_waiting > 0:
                progress = max(0, min(100, int((1 - (my_pos / (total_waiting + 1))) * 100)))
        elif my_entry and my_entry.status in ('called', 'in_progress'):
            progress = 100

        # Get next 5 patients in line
        next_patients = (QueueManagement.objects
                        .filter(department=dept, status='waiting')
                        .order_by('-is_priority', 'priority_position', 'enqueue_time')[:5])
        
        next_patients_data = []
        for i, p in enumerate(next_patients):
            next_patients_data.append({
                'id': p.id,
                'name': p.patient.user.full_name[:1] + '***' if p.patient.user.id != user.id else p.patient.user.full_name,
                'number': str(p.queue_number),
                'department': p.department,
                'etaMins': max(0, (i + (1 if has_active else 0)) * avg_mins),
                'isMe': p.patient.user.id == user.id
            })

        patients_ahead = 0
        if my_entry and my_entry.status == "waiting":
            patients_ahead = _count_waiting_ahead(my_entry, department=dept) + (1 if has_active else 0)
        estimated_wait = max(0, int(patients_ahead) * int(avg_mins)) if my_entry else max(0, int(waiting_count + (1 if has_active else 0)) * int(avg_mins))
        my_status = ''
        if my_entry:
            if my_entry.status == 'called':
                my_status = 'Called'
            elif my_entry.status == 'no_show':
                my_status = 'No Show'
        payload = {
            'department': dept,
            'nowServing': now_serving.queue_number if now_serving else '',
            'currentPatient': now_serving.patient.user.full_name if now_serving else '',
            'myPosition': my_status if my_status else (str(my_entry.queue_number) if my_entry else ''),
            'myQueueNumber': my_entry.queue_number if my_entry else None,
            'myQueueStatus': my_entry.status if my_entry else None,
            'myGraceExpiresAt': my_entry.grace_expires_at.isoformat() if my_entry and my_entry.grace_expires_at else None,
            'estimatedWaitMins': estimated_wait,
            'avgConsultMins': avg_mins,
            'patientsAhead': patients_ahead if my_entry and my_entry.status == "waiting" else None,
            'progressValue': progress,
            'queueEntries': next_patients_data,
        }
        logger.debug(f"[{corr}] patient_dashboard_summary user={user.id} dept={dept} -> {payload}")
        return Response(payload, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_conversations(request):
    user = request.user
    if not _require_verified_messaging_user(user):
        return Response({"error": "Account verification required."}, status=status.HTTP_403_FORBIDDEN)

    qs = (
        Conversation.objects.filter(participants=user, is_active=True)
        .prefetch_related("participants")
        .order_by("-updated_at")
    )

    result = []
    for conv in qs:
        others = [p for p in list(conv.participants.all()) if p.id != user.id]
        other = others[0] if others else None
        last_msg = (
            Message.objects.filter(conversation=conv)
            .select_related("sender")
            .order_by("-created_at")
            .first()
        )
        unread_count = 0
        if other:
            unread_count = Message.objects.filter(conversation=conv, sender=other, is_read=False).count()
        result.append(
            {
                "id": conv.id,
                "other_participant": _serialize_user(other),
                "last_message": _serialize_message(last_msg),
                "unread_count": unread_count,
            }
        )
    return Response(result, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_conversation(request):
    user = request.user
    if not _require_verified_messaging_user(user):
        return Response({"error": "Account verification required."}, status=status.HTTP_403_FORBIDDEN)

    other_user_id = request.data.get("other_user_id")
    try:
        other_id = int(other_user_id)
    except Exception:
        return Response({"error": "other_user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    if other_id == user.id:
        return Response({"error": "Cannot create a conversation with yourself"}, status=status.HTTP_400_BAD_REQUEST)

    other = User.objects.filter(id=other_id, is_active=True, verification_status="approved").first()
    if not other:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    my_hospital = (getattr(user, "hospital_name", "") or "").strip()
    other_hospital = (getattr(other, "hospital_name", "") or "").strip()
    if my_hospital and other_hospital and my_hospital.lower() != other_hospital.lower():
        return Response({"error": "Users must be in the same hospital to message."}, status=status.HTTP_403_FORBIDDEN)

    existing = (
        Conversation.objects.filter(is_active=True, participants=user)
        .filter(participants=other)
        .distinct()
        .order_by("-updated_at")
        .first()
    )
    conv = existing
    if not conv:
        conv = Conversation.objects.create()
        conv.participants.add(user, other)

    last_msg = (
        Message.objects.filter(conversation=conv)
        .select_related("sender")
        .order_by("-created_at")
        .first()
    )
    unread_count = Message.objects.filter(conversation=conv, sender=other, is_read=False).count()
    payload = {
        "id": conv.id,
        "other_participant": _serialize_user(other),
        "last_message": _serialize_message(last_msg),
        "unread_count": unread_count,
    }
    return Response(payload, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_messages(request, conversation_id):
    user = request.user
    if not _require_verified_messaging_user(user):
        return Response({"error": "Account verification required."}, status=status.HTTP_403_FORBIDDEN)

    conv = Conversation.objects.filter(id=conversation_id, is_active=True).first()
    if not conv or not conv.participants.filter(id=user.id).exists():
        return Response({"error": "Conversation not found"}, status=status.HTTP_404_NOT_FOUND)

    msgs = (
        Message.objects.filter(conversation=conv)
        .select_related("sender")
        .order_by("created_at")
    )
    return Response([_serialize_message(m) for m in msgs], status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def send_message(request, conversation_id):
    user = request.user
    if not _require_verified_messaging_user(user):
        return Response({"error": "Account verification required."}, status=status.HTTP_403_FORBIDDEN)

    conv = Conversation.objects.filter(id=conversation_id, is_active=True).first()
    if not conv or not conv.participants.filter(id=user.id).exists():
        return Response({"error": "Conversation not found"}, status=status.HTTP_404_NOT_FOUND)

    content = request.data.get("content")
    if not isinstance(content, str) or not content.strip():
        return Response({"error": "content is required"}, status=status.HTTP_400_BAD_REQUEST)

    msg = Message.objects.create(conversation=conv, sender=user, content=content.strip())
    Conversation.objects.filter(id=conv.id).update(updated_at=timezone.now())

    recipient = conv.participants.exclude(id=user.id).first()
    if recipient:
        MessageNotification.objects.create(message=msg, recipient=recipient, notification_type="new_message")

    return Response(_serialize_message(msg), status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_reaction(request, message_id):
    user = request.user
    if not _require_verified_messaging_user(user):
        return Response({"error": "Account verification required."}, status=status.HTTP_403_FORBIDDEN)

    msg = Message.objects.select_related("conversation").filter(id=message_id).first()
    if not msg or not msg.conversation.participants.filter(id=user.id).exists():
        return Response({"error": "Message not found"}, status=status.HTTP_404_NOT_FOUND)

    reaction = request.data.get("reaction_type") or request.data.get("reaction") or "like"
    allowed = {c[0] for c in MessageReaction._meta.get_field("reaction_type").choices}
    reaction_type = reaction if reaction in allowed else "like"
    MessageReaction.objects.create(message=msg, user=user, reaction_type=reaction_type)
    return Response({"ok": True}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_available_users(request):
    user = request.user
    if not _require_verified_messaging_user(user):
        return Response({"error": "Account verification required."}, status=status.HTTP_403_FORBIDDEN)

    hospital_name = (getattr(user, "hospital_name", "") or "").strip()
    search_query = (request.query_params.get("search") or "").strip()

    qs = (
        User.objects.filter(
            role__in=[User.Role.DOCTOR, User.Role.NURSE],
            is_active=True,
            verification_status="approved",
        )
        .exclude(id=user.id)
        .order_by("full_name")
    )

    if hospital_name:
        qs = qs.filter(hospital_name__iexact=hospital_name)

    if search_query:
        qs = qs.filter(Q(full_name__icontains=search_query) | Q(email__icontains=search_query))

    total_count = qs.count()
    users = list(qs[:200])
    payload = {
        "users": [_serialize_user(u) for u in users],
        "total_count": total_count,
        "message": f"Found {total_count} verified users",
    }
    return Response(payload, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def available_doctors_free(request):
    """
    Get list of available doctors for the nurse's hospital.
    """
    try:
        user = request.user
        hospital_name = user.hospital_name
        search_query = (request.GET.get('search') or '').strip()
        
        # Base query for doctors
        doctors_query = User.objects.filter(role=User.Role.DOCTOR, is_active=True)
        
        # Filter by hospital if nurse has one
        if hospital_name:
            doctors_query = doctors_query.filter(hospital_name__iexact=hospital_name)
        if search_query:
            doctors_query = doctors_query.filter(
                Q(full_name__icontains=search_query)
                | Q(email__icontains=search_query)
                | Q(doctor_profile__specialization__icontains=search_query)
            )
            
        # Get doctors who are available
        # efficient way: filter users who have a related doctor_profile with available_for_consultation=True
        doctors_query = doctors_query.filter(doctor_profile__available_for_consultation=True)
        
        doctors_data = []
        for doctor in doctors_query:
            try:
                profile = doctor.doctor_profile
                doctors_data.append({
                    'id': doctor.id,
                    'full_name': doctor.full_name,
                    'specialization': profile.specialization,
                    'email': doctor.email if request.GET.get('include_email') == 'true' else None,
                    'availability': 'available', # Since we filtered for available ones
                    'hospital_name': doctor.hospital_name
                })
            except GeneralDoctorProfile.DoesNotExist:
                continue
                
        return Response({
            'doctors': doctors_data,
            'checked_at': timezone.now().isoformat()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error fetching available doctors: {str(e)}")
        return Response({
            'error': 'Failed to fetch available doctors',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def available_nurses(request):
    """
    Get list of available nurses for the requester's hospital.

    Query params:
      - search: optional substring match across name/email/department
      - include_email: 'true' to include nurse emails
    """
    try:
        user = request.user
        hospital_name = getattr(user, "hospital_name", None)
        search_query = (request.GET.get("search") or "").strip()
        include_email = (request.GET.get("include_email") or "").strip().lower() == "true"

        nurses_query = (
            User.objects.filter(role=User.Role.NURSE, is_active=True)
            .select_related("nurse_profile")
            .filter(verification_status="approved")
        )

        if hospital_name:
            nurses_query = nurses_query.filter(hospital_name__iexact=hospital_name)

        if search_query:
            nurses_query = nurses_query.filter(
                Q(full_name__icontains=search_query)
                | Q(email__icontains=search_query)
                | Q(nurse_profile__department__icontains=search_query)
            )

        nurses_data = []
        for nurse in nurses_query:
            profile = getattr(nurse, "nurse_profile", None)
            nurses_data.append(
                {
                    "id": nurse.id,
                    "full_name": nurse.full_name,
                    "email": nurse.email if include_email else None,
                    "department": getattr(profile, "department", "") or "General",
                    "availability": "available",
                    "on_duty": True,
                }
            )

        return Response(
            {"nurses": nurses_data, "checked_at": timezone.now().isoformat()},
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        logger.error(f"Error fetching available nurses: {str(e)}")
        return Response(
            {"error": "Failed to fetch available nurses", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

@api_view(['GET'])
def nurses_list(request): return Response([], status=status.HTTP_200_OK)

@api_view(['POST'])
def nurse_capacity_validate(request): return Response({}, status=status.HTTP_200_OK)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_message_notifications(request):
    user = request.user
    if not _require_verified_messaging_user(user):
        return Response({"error": "Account verification required."}, status=status.HTTP_403_FORBIDDEN)

    qs = (
        MessageNotification.objects.filter(recipient=user, notification_type="new_message", is_sent=False)
        .select_related("message__sender", "message__conversation")
        .order_by("-created_at")[:100]
    )
    out = []
    for n in qs:
        msg = n.message
        sender = getattr(msg, "sender", None)
        conv = getattr(msg, "conversation", None)
        out.append(
            {
                "id": n.id,
                "message": {
                    "sender": {
                        "id": getattr(sender, "id", None),
                        "full_name": getattr(sender, "full_name", "") or "",
                    }
                    if sender
                    else None,
                    "content": getattr(msg, "content", "") or "",
                    "conversation": {"id": getattr(conv, "id", None)} if conv else None,
                },
                "is_sent": bool(getattr(n, "is_sent", False)),
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
        )
    return Response(out, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_notification_as_sent(request, notification_id):
    user = request.user
    n = MessageNotification.objects.filter(id=notification_id, recipient=user).first()
    if not n:
        return Response({"error": "Notification not found"}, status=status.HTTP_404_NOT_FOUND)
    if not n.is_sent:
        n.is_sent = True
        n.sent_at = timezone.now()
        n.save(update_fields=["is_sent", "sent_at"])
    return Response({"ok": True}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_all_message_notifications_as_sent(request):
    user = request.user
    if not _require_verified_messaging_user(user):
        return Response({"error": "Account verification required."}, status=status.HTTP_403_FORBIDDEN)

    now = timezone.now()
    updated = MessageNotification.objects.filter(
        recipient=user,
        notification_type="new_message",
        is_sent=False,
    ).update(is_sent=True, sent_at=now)

    return Response({"ok": True, "updated": int(updated), "unread_count": 0}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_message_as_read(request, message_id):
    user = request.user
    if not _require_verified_messaging_user(user):
        return Response({"error": "Account verification required."}, status=status.HTTP_403_FORBIDDEN)

    msg = Message.objects.select_related("conversation").filter(id=message_id).first()
    if not msg or not msg.conversation.participants.filter(id=user.id).exists():
        return Response({"error": "Message not found"}, status=status.HTTP_404_NOT_FOUND)

    if msg.sender_id != user.id and not msg.is_read:
        msg.is_read = True
        msg.read_at = timezone.now()
        msg.save(update_fields=["is_read", "read_at"])

    MessageNotification.objects.filter(
        recipient=user, message=msg, notification_type="new_message", is_sent=False
    ).update(is_sent=True, sent_at=timezone.now())

    return Response({"ok": True}, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_medicine_inventory(request): return Response([], status=status.HTTP_200_OK)

@api_view(['POST'])
def add_medicine(request): return Response({}, status=status.HTTP_200_OK)

@api_view(['PUT'])
def update_medicine(request, medicine_id): return Response({}, status=status.HTTP_200_OK)

@api_view(['POST'])
def dispense_medicine(request, medicine_id): return Response({}, status=status.HTTP_200_OK)

@api_view(['DELETE'])
def delete_medicine(request, medicine_id): return Response({}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def nurse_completed_assessments(request):
    """
    Get list of patients who have completed their nurse assessment 
    and were sent to doctors today.
    """
    try:
        corr = _corr_id(request)
        department = request.query_params.get('department') or 'OPD'
        
        # Get completed queue entries for today in this department
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        completed_entries = QueueManagement.objects.filter(
            department=department,
            status='completed',
            finished_at__gte=today_start
        ).select_related('patient__user', 'patient__assigned_doctor').order_by('-finished_at')
        
        results = []
        for entry in completed_entries:
            profile = entry.patient
            intake = profile.nursing_intake_assessment or {}
            
            # Only include if they actually have an assessment
            if not intake or not intake.get('assessed_at'):
                continue
                
            results.append({
                'id': profile.id,
                'patient_name': profile.user.full_name,
                'queue_number': entry.queue_number,
                'assessed_at': intake.get('assessed_at'),
                'finished_at': entry.finished_at.isoformat() if entry.finished_at else None,
                'doctor_name': profile.assigned_doctor.full_name if profile.assigned_doctor else 'Not Assigned',
                'medical_condition': profile.medical_condition,
                'assessment_summary': {
                    'vitals': intake.get('vitals', {}),
                    'chief_complaint': intake.get('chief_complaint', ''),
                    'pain_score': intake.get('pain_score', 0),
                }
            })
            
        logger.info(f"[{corr}] nurse_completed_assessments dept={department} count={len(results)}")
        return Response(results, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error in nurse_completed_assessments: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def nurse_queue_patients(request):
    try:
        corr = _corr_id(request)
        department = request.query_params.get('department') or 'OPD'
        priority_qs = QueueManagement.objects.only(
            'id', 'patient', 'queue_number', 'department', 'status', 'enqueue_time', 'priority_level', 'priority_position', 'is_priority'
        ).filter(
            department=department,
            status='waiting',
            is_priority=True
        ).order_by('priority_position', 'enqueue_time')
        normal_qs = QueueManagement.objects.only(
            'id', 'patient', 'queue_number', 'department', 'status', 'enqueue_time', 'is_priority'
        ).filter(
            department=department,
            status='waiting',
            is_priority=False
        ).order_by('enqueue_time')
        priority_serializer = QueueSerializer(priority_qs, many=True)
        normal_serializer = QueueSerializer(normal_qs, many=True)
        all_patients = []
        for obj in priority_qs:
            all_patients.append({
                'id': obj.id,
                'queue_number': obj.queue_number,
                'patient_name': obj.patient.user.full_name,
                'queue_type': 'priority',
                'department': obj.department,
                'status': obj.status,
                'enqueue_time': obj.enqueue_time.isoformat() if obj.enqueue_time else obj.created_at.isoformat(),
                'priority_level': obj.priority_level or None,
                'priority_position': obj.priority_position or 0,
            })
        for obj in normal_qs:
            all_patients.append({
                'id': obj.id,
                'queue_number': obj.queue_number,
                'patient_name': obj.patient.user.full_name,
                'queue_type': 'normal',
                'department': obj.department,
                'status': obj.status,
                'enqueue_time': obj.enqueue_time.isoformat() if obj.enqueue_time else obj.created_at.isoformat(),
            })
        logger.info(f"[{corr}] nurse_queue_patients dept={department} normal={normal_qs.count()} priority={priority_qs.count()}")
        return Response({
            'normal_queue': normal_serializer.data,
            'priority_queue': priority_serializer.data,
            'all_patients': all_patients
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def nurse_remove_from_queue(request):
    """
    Remove a patient from the queue (sets status=cancelled and records dequeue_time).

    Accepts one of:
      - queue_id
      - queue_number (+ optional department)
      - patient_id
      - patient_name (substring match; removes most recent waiting/in_progress entry)
    """
    try:
        user = request.user
        role = str(getattr(user, 'role', '') or '').lower()
        if role not in ['nurse', 'admin', 'doctor']:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data or {}
        queue_id = data.get('queue_id') or data.get('id')
        queue_number = data.get('queue_number')
        patient_id = data.get('patient_id')
        patient_name = (data.get('patient_name') or '').strip()
        department = (data.get('department') or '').strip()

        qs = QueueManagement.objects.select_related('patient__user')

        if queue_id:
            qs = qs.filter(id=queue_id)
        elif queue_number:
            qs = qs.filter(queue_number=queue_number)
            if department:
                qs = qs.filter(department=department)
        elif patient_id:
            qs = qs.filter(patient__user_id=patient_id)
            if department:
                qs = qs.filter(department=department)
        elif patient_name:
            qs = qs.filter(patient__user__full_name__icontains=patient_name)
            if department:
                qs = qs.filter(department=department)
        else:
            return Response({'error': 'Provide queue_id, queue_number, patient_id, or patient_name.'}, status=status.HTTP_400_BAD_REQUEST)

        entry = (qs.filter(status__in=['waiting', 'called', 'in_progress'])
                   .order_by('-created_at')
                   .first())
        if not entry:
            return Response({'error': 'Queue entry not found.'}, status=status.HTTP_404_NOT_FOUND)

        entry.status = 'cancelled'
        entry.dequeue_time = timezone.now()
        entry.called_at = None
        entry.grace_expires_at = None
        entry.save(update_fields=['status', 'dequeue_time', 'called_at', 'grace_expires_at', 'updated_at'])

        return Response({'success': True, 'queue_id': entry.id, 'queue_number': entry.queue_number}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception("nurse_remove_from_queue failed")
        return Response({'error': 'Failed to remove from queue', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def nurse_mark_served(request): return Response({}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_available_doctors(request):
    """
    Patient-facing doctor selection endpoint.

    Query params:
      - department: specialization (optional)

    Returns:
      { doctors: [...], checked_at: <iso> }
    """
    try:
        user = request.user
        role = str(getattr(user, 'role', '') or '').lower()
        verification = str(getattr(user, 'verification_status', '') or '').lower()

        if role != 'patient' and verification != 'approved':
            return Response({'error': 'Account verification required.'}, status=status.HTTP_403_FORBIDDEN)

        dept = (request.query_params.get('department') or '').strip()
        requested_hospital = (request.query_params.get('hospital') or '').strip()

        hospital_name = requested_hospital
        if not hospital_name and role == 'patient':
            profile = PatientProfile.objects.filter(user=user).first()
            hospital_name = (getattr(profile, 'hospital', None) or getattr(user, 'hospital_name', None) or '').strip()

        qs = GeneralDoctorProfile.objects.filter(
            available_for_consultation=True,
            user__role=User.Role.DOCTOR,
            user__is_active=True,
            user__verification_status='approved',
        ).select_related('user')

        if dept:
            dept_norm = dept.strip().lower()
            for ch in ['_', '-', '/', '&']:
                dept_norm = dept_norm.replace(ch, ' ')
            tokens = [t for t in dept_norm.split() if t]
            for tok in tokens:
                qs = qs.filter(specialization__icontains=tok)
        if hospital_name:
            qs = qs.filter(user__hospital_name__iexact=hospital_name.strip())

        today = timezone.localdate()
        doctors = []
        for doc in qs:
            doctor_user = doc.user
            current_patients = AppointmentManagement.objects.filter(
                doctor=doc,
                appointment_date__date=today,
            ).exclude(status__in=['cancelled', 'no_show']).count()

            doctors.append({
                'id': doctor_user.id,
                'full_name': doctor_user.full_name,
                'department': doc.specialization,
                'specialization': doc.specialization,
                'is_available': True,
                'current_patients': current_patients,
                'verification_status': 'approved',
                'is_verified': True,
                'hospital_name': doctor_user.hospital_name,
            })

        return Response({'doctors': doctors, 'checked_at': timezone.now().isoformat()}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception("get_available_doctors failed")
        return Response({'error': 'Failed to fetch available doctors', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def doctor_occupied_slots(request):
    """
    Return booked time slots for a doctor on a given date.

    Query params:
      - doctor_id: required (User id)
      - date: required (YYYY-MM-DD)
    """
    try:
        doctor_id = request.query_params.get('doctor_id')
        date_str = (request.query_params.get('date') or '').strip()
        if not doctor_id or not date_str:
            return Response({'error': 'doctor_id and date are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except Exception:
            return Response({'error': 'Invalid date format. Expected YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        doctor_user = User.objects.filter(id=doctor_id, role=User.Role.DOCTOR, is_active=True).first()
        if not doctor_user:
            return Response({'error': 'Doctor not found.'}, status=status.HTTP_404_NOT_FOUND)

        doctor_profile = GeneralDoctorProfile.objects.filter(user=doctor_user).first()
        if not doctor_profile:
            return Response({'error': 'Doctor profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        qs = AppointmentManagement.objects.filter(
            doctor=doctor_profile,
            appointment_date__date=target_date,
        ).exclude(status__in=['cancelled', 'no_show'])

        occupied_times = []
        for appt in qs:
            try:
                occupied_times.append(appt.appointment_time.strftime('%H:%M'))
            except Exception:
                pass

        # de-dup + sort
        occupied_times = sorted(set([t for t in occupied_times if isinstance(t, str)]))

        return Response({'occupied_times': occupied_times, 'checked_at': timezone.now().isoformat()}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception("doctor_occupied_slots failed")
        return Response({'error': 'Failed to fetch doctor schedule', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hospital_departments(request):
    actor_role = str(getattr(request.user, 'role', '') or '').lower()
    actor_verification = str(getattr(request.user, 'verification_status', '') or '').lower()

    if actor_role != 'patient' and actor_verification != 'approved':
        return Response({'error': 'Account verification required.'}, status=status.HTTP_403_FORBIDDEN)

    requested_hospital = (request.query_params.get('hospital') or '').strip()
    hospital_name = requested_hospital

    if not hospital_name and actor_role == 'patient':
        profile = PatientProfile.objects.filter(user=request.user).first()
        hospital_name = (getattr(profile, 'hospital', None) or getattr(request.user, 'hospital_name', None) or '').strip()

    qs = GeneralDoctorProfile.objects.filter(
        available_for_consultation=True,
        user__role=User.Role.DOCTOR,
        user__is_active=True,
        user__verification_status='approved',
    ).select_related('user')

    if hospital_name:
        qs = qs.filter(user__hospital_name__iexact=hospital_name.strip())

    values = []
    seen = set()
    for doc in qs:
        raw_spec = (doc.specialization or '').strip()
        if not raw_spec:
            continue
        norm = raw_spec.lower()
        for ch in ['_', '-', '/', '&']:
            norm = norm.replace(ch, ' ')
        norm = ' '.join(norm.split())
        if not norm:
            continue
        value = norm.replace(' ', '-')
        if value in seen:
            continue
        seen.add(value)
        label = ' '.join([w.capitalize() for w in norm.split()])
        values.append({'label': label, 'value': value})

    if not values:
        values = [{'label': 'General Medicine', 'value': 'general-medicine'}]

    return Response({'departments': values, 'hospital': hospital_name or None}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_patient_to_doctor(request):
    try:
        user = request.user
        role = str(getattr(user, "role", "") or "").lower()
        if role not in ("nurse", "admin"):
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)
        if role != "admin" and str(getattr(user, "verification_status", "") or "").lower() != "approved":
            return Response({"error": "Account verification required."}, status=status.HTTP_403_FORBIDDEN)

        data = request.data or {}
        patient_id = data.get("patient_id")
        doctor_id = data.get("doctor_id")
        assignment_reason = str(data.get("assignment_reason") or data.get("reason") or "").strip()
        specialization_required = str(data.get("specialization_required") or "").strip()
        channels = _normalize_channels(data.get("channels"))
        priority = _normalize_priority(data.get("priority"))
        severity = data.get("severity")
        if severity is not None:
            priority = _priority_from_severity(severity)

        if not patient_id or not doctor_id:
            return Response({"error": "patient_id and doctor_id are required."}, status=status.HTTP_400_BAD_REQUEST)

        patient_profile = PatientProfile.objects.filter(id=patient_id).select_related("user").first() or PatientProfile.objects.filter(user_id=patient_id).select_related("user").first()
        if not patient_profile:
            return Response({"error": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)

        doctor_user = User.objects.filter(id=doctor_id, role=User.Role.DOCTOR, is_active=True).first()
        if not doctor_user:
            return Response({"error": "Doctor not found."}, status=status.HTTP_404_NOT_FOUND)
        if str(getattr(doctor_user, "verification_status", "") or "").lower() != "approved":
            return Response({"error": "Selected doctor is not verified."}, status=status.HTTP_400_BAD_REQUEST)

        doctor_profile = GeneralDoctorProfile.objects.filter(user=doctor_user).first()
        if not doctor_profile:
            return Response({"error": "Doctor profile not found."}, status=status.HTTP_400_BAD_REQUEST)

        if not specialization_required:
            specialization_required = (doctor_profile.specialization or "").strip()

        existing = PatientAssignment.objects.filter(
            patient=patient_profile,
            doctor=doctor_profile,
            status__in=["pending", "accepted", "in_progress"],
        ).order_by("-assigned_at").first()
        if existing:
            assignment = existing
        else:
            assignment = PatientAssignment.objects.create(
                assigned_by=user,
                doctor=doctor_profile,
                patient=patient_profile,
                specialization_required=specialization_required,
                assignment_reason=assignment_reason,
                status="pending",
                priority=priority,
            )
            _audit_assignment_event(request, assignment, "created", "assign_patient_to_doctor")

        try:
            patient_profile.assigned_doctor = doctor_user
            patient_profile.save(update_fields=["assigned_doctor"])
        except Exception:
            pass

        msg = f"New patient referral assigned (Priority: {assignment.priority}). Open MediSync to review patient details."

        payload = {
            "event": "patient_assigned",
            "assignment_id": assignment.id,
            "patient_profile_id": patient_profile.id,
            "priority": assignment.priority,
            "message": msg,
        }
        _create_notification_records(doctor_user, msg, channels, payload=payload)

        return Response(
            {
                "success": True,
                "assignment": {
                    "id": assignment.id,
                    "patient_id": patient_profile.id,
                    "patient_name": patient_profile.user.full_name,
                    "doctor_id": doctor_user.id,
                    "doctor_name": doctor_user.full_name,
                    "status": assignment.status,
                    "priority": assignment.priority,
                    "specialization_required": assignment.specialization_required,
                    "assignment_reason": assignment.assignment_reason,
                    "assigned_by_name": user.full_name,
                    "assigned_at": assignment.assigned_at.isoformat() if assignment.assigned_at else None,
                },
            },
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        logger.exception("assign_patient_to_doctor failed")
        return Response({"error": "Failed to assign patient", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_doctor_assignments(request):
    try:
        user = request.user
        role = str(getattr(user, "role", "") or "").lower()
        if role not in ("doctor", "admin"):
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)
        if role != "admin" and str(getattr(user, "verification_status", "") or "").lower() != "approved":
            return Response({"error": "Account verification required."}, status=status.HTTP_403_FORBIDDEN)

        if role == "admin":
            qs = PatientAssignment.objects.select_related("patient__user", "doctor__user", "assigned_by").all()
        else:
            doctor_profile = GeneralDoctorProfile.objects.filter(user=user).first()
            if not doctor_profile:
                return Response([], status=status.HTTP_200_OK)
            qs = PatientAssignment.objects.select_related("patient__user", "doctor__user", "assigned_by").filter(doctor=doctor_profile)

        qs = qs.order_by("-assigned_at")[:200]
        out = []
        for a in qs:
            out.append(
                {
                    "id": a.id,
                    "patient_id": a.patient_id,
                    "patient_name": a.patient.user.full_name if a.patient_id and a.patient and a.patient.user_id else "Unknown Patient",
                    "status": a.status,
                    "assigned_by_name": getattr(a.assigned_by, "full_name", "") or "",
                    "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None,
                    "specialization_required": a.specialization_required,
                    "assignment_reason": a.assignment_reason,
                    "priority": a.priority,
                    "accepted_at": a.accepted_at.isoformat() if a.accepted_at else None,
                    "completed_at": a.completed_at.isoformat() if a.completed_at else None,
                }
            )
        return Response(out, status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception("get_doctor_assignments failed")
        return Response({"error": "Failed to fetch assignments", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_assignment(request, assignment_id):
    try:
        user = request.user
        role = str(getattr(user, "role", "") or "").lower()
        if role not in ("doctor", "admin"):
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)
        if role != "admin" and str(getattr(user, "verification_status", "") or "").lower() != "approved":
            return Response({"error": "Account verification required."}, status=status.HTTP_403_FORBIDDEN)

        qs = PatientAssignment.objects.select_related("doctor__user", "patient__user", "assigned_by")
        assignment = qs.filter(id=assignment_id).first()
        if not assignment:
            return Response({"error": "Assignment not found."}, status=status.HTTP_404_NOT_FOUND)

        if role != "admin":
            doctor_profile = GeneralDoctorProfile.objects.filter(user=user).first()
            if not doctor_profile or assignment.doctor_id != doctor_profile.id:
                return Response({"error": "Not authorized for this assignment."}, status=status.HTTP_403_FORBIDDEN)

        if assignment.status not in ("pending", "accepted", "in_progress"):
            return Response({"error": "Assignment is not active."}, status=status.HTTP_400_BAD_REQUEST)

        if assignment.status == "pending":
            assignment.status = "accepted"
            assignment.accepted_at = timezone.now()
            assignment.save(update_fields=["status", "accepted_at"])
            _audit_assignment_event(request, assignment, "accepted", "")

            try:
                if assignment.assigned_by_id:
                    msg = "Referral accepted. Open MediSync to review details."
                    _create_notification_records(
                        assignment.assigned_by,
                        msg,
                        [Notification.CHANNEL_WEBSOCKET],
                        payload={
                            "event": "assignment_accepted",
                            "assignment_id": assignment.id,
                            "patient_profile_id": assignment.patient_id,
                            "message": msg,
                        },
                    )
            except Exception:
                pass

        return Response(
            {
                "success": True,
                "assignment": {
                    "id": assignment.id,
                    "status": assignment.status,
                    "accepted_at": assignment.accepted_at.isoformat() if assignment.accepted_at else None,
                },
            },
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        logger.exception("accept_assignment failed")
        return Response({"error": "Failed to accept assignment", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def consultation_notes(request, assignment_id):
    try:
        user = request.user
        role = str(getattr(user, "role", "") or "").lower()
        if role not in ("doctor", "admin"):
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)
        if role != "admin" and str(getattr(user, "verification_status", "") or "").lower() != "approved":
            return Response({"error": "Account verification required."}, status=status.HTTP_403_FORBIDDEN)

        assignment = PatientAssignment.objects.select_related("doctor__user", "patient__user").filter(id=assignment_id).first()
        if not assignment:
            return Response({"error": "Assignment not found."}, status=status.HTTP_404_NOT_FOUND)

        doctor_profile = None
        if role != "admin":
            doctor_profile = GeneralDoctorProfile.objects.filter(user=user).first()
            if not doctor_profile or assignment.doctor_id != doctor_profile.id:
                _log_form_access_ops(request, assignment, "consultation_notes", False, "not_authorized")
                return Response({"error": "Not authorized for this assignment."}, status=status.HTTP_403_FORBIDDEN)

        if request.method == "GET":
            _log_form_access_ops(request, assignment, "consultation_notes", True, "")
            note = ConsultationNotes.objects.filter(assignment=assignment).order_by("-updated_at").first()
            if not note:
                return Response(
                    {
                        "success": True,
                        "data": None,
                        "assignment": {
                            "id": assignment.id,
                            "status": assignment.status,
                            "priority": assignment.priority,
                            "patient_id": assignment.patient_id,
                            "patient_name": assignment.patient.user.full_name,
                        },
                    },
                    status=status.HTTP_200_OK,
                )
            return Response(
                {
                    "success": True,
                    "data": {
                        "id": note.id,
                        "chief_complaint": note.chief_complaint,
                        "history_of_present_illness": note.history_of_present_illness,
                        "physical_examination": note.physical_examination,
                        "diagnosis": note.diagnosis,
                        "treatment_plan": note.treatment_plan,
                        "medications_prescribed": note.medications_prescribed,
                        "follow_up_instructions": note.follow_up_instructions,
                        "additional_notes": note.additional_notes,
                        "status": note.status,
                        "created_at": note.created_at.isoformat() if note.created_at else None,
                        "updated_at": note.updated_at.isoformat() if note.updated_at else None,
                        "completed_at": note.completed_at.isoformat() if note.completed_at else None,
                    },
                    "assignment": {
                        "id": assignment.id,
                        "status": assignment.status,
                        "priority": assignment.priority,
                        "patient_id": assignment.patient_id,
                        "patient_name": assignment.patient.user.full_name,
                    },
                },
                status=status.HTTP_200_OK,
            )

        payload = request.data or {}
        assignment_status = str(payload.get("assignment_status") or "").strip().lower()
        note_status = str(payload.get("status") or "").strip().lower()

        allowed_note_status = {"draft", "completed", "reviewed"}
        if note_status and note_status not in allowed_note_status:
            return Response({"error": "Invalid note status."}, status=status.HTTP_400_BAD_REQUEST)

        if not doctor_profile and role == "admin":
            doctor_profile = assignment.doctor

        note = ConsultationNotes.objects.filter(assignment=assignment).order_by("-updated_at").first()
        created = False
        if not note:
            created = True
            note = ConsultationNotes(
                assignment=assignment,
                doctor=doctor_profile,
                patient=assignment.patient,
                chief_complaint="",
                history_of_present_illness="",
                physical_examination="",
                diagnosis="",
                treatment_plan="",
                medications_prescribed="",
                follow_up_instructions="",
                additional_notes="",
                status="draft",
            )

        for field in [
            "chief_complaint",
            "history_of_present_illness",
            "physical_examination",
            "diagnosis",
            "treatment_plan",
            "medications_prescribed",
            "follow_up_instructions",
            "additional_notes",
        ]:
            if field in payload:
                setattr(note, field, str(payload.get(field) or ""))
        if note_status:
            note.status = note_status
        if note.status == "completed" and not note.completed_at:
            note.completed_at = timezone.now()

        note.save()
        _audit_assignment_event(request, assignment, "notes_saved", "created" if created else "updated")
        _log_form_access_ops(request, assignment, "consultation_notes", True, "saved")

        if assignment_status in ("accepted", "in_progress", "completed", "rejected", "pending"):
            if assignment.status != assignment_status:
                assignment.status = assignment_status
                fields = ["status"]
                now = timezone.now()
                if assignment_status == "in_progress":
                    assignment.accepted_at = assignment.accepted_at or now
                    fields.append("accepted_at")
                if assignment_status == "completed":
                    assignment.completed_at = now
                    fields.append("completed_at")
                assignment.save(update_fields=fields)
                _audit_assignment_event(request, assignment, "status_changed", assignment_status)

        return Response(
            {
                "success": True,
                "note_id": note.id,
                "assignment": {
                    "id": assignment.id,
                    "status": assignment.status,
                    "accepted_at": assignment.accepted_at.isoformat() if assignment.accepted_at else None,
                    "completed_at": assignment.completed_at.isoformat() if assignment.completed_at else None,
                },
            },
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        logger.exception("consultation_notes failed")
        return Response({"error": "Failed to handle consultation notes", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_assignment_audit_logs(request):
    user = request.user
    if str(getattr(user, "role", "") or "").lower() != "admin":
        return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

    qs = PatientAssignmentAuditLog.objects.select_related("actor", "assignment", "doctor__user", "patient__user").order_by("-created_at")
    patient_id = request.query_params.get("patient_id")
    assignment_id = request.query_params.get("assignment_id")
    doctor_user_id = request.query_params.get("doctor_user_id")
    limit = request.query_params.get("limit")

    if assignment_id:
        qs = qs.filter(assignment_id=assignment_id)
    if patient_id:
        qs = qs.filter(patient_id=patient_id)
    if doctor_user_id:
        qs = qs.filter(doctor__user_id=doctor_user_id)

    try:
        lim = int(limit) if limit is not None else 200
    except Exception:
        lim = 200
    lim = max(1, min(lim, 500))
    qs = qs[:lim]

    out = []
    for r in qs:
        out.append(
            {
                "id": r.id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "event": r.event,
                "detail": r.detail,
                "ip_address": r.ip_address,
                "actor_id": r.actor_id,
                "actor_name": getattr(r.actor, "full_name", None),
                "assignment_id": r.assignment_id,
                "patient_id": r.patient_id,
                "patient_name": (r.patient.user.full_name if r.patient_id and r.patient and getattr(r.patient, "user_id", None) else None),
                "doctor_id": r.doctor_id,
                "doctor_name": (r.doctor.user.full_name if r.doctor_id and r.doctor and getattr(r.doctor, "user_id", None) else None),
            }
        )
    return Response({"success": True, "results": out}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_form_access_logs(request):
    user = request.user
    if str(getattr(user, "role", "") or "").lower() != "admin":
        return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

    qs = FormAccessLog.objects.select_related("user", "patient__user", "assignment").order_by("-created_at")
    patient_id = request.query_params.get("patient_id")
    assignment_id = request.query_params.get("assignment_id")
    user_id = request.query_params.get("user_id")
    form_key = request.query_params.get("form_key")
    limit = request.query_params.get("limit")

    if assignment_id:
        qs = qs.filter(assignment_id=assignment_id)
    if patient_id:
        qs = qs.filter(patient_id=patient_id)
    if user_id:
        qs = qs.filter(user_id=user_id)
    if form_key:
        qs = qs.filter(form_key=form_key)

    try:
        lim = int(limit) if limit is not None else 200
    except Exception:
        lim = 200
    lim = max(1, min(lim, 500))
    qs = qs[:lim]

    out = []
    for r in qs:
        out.append(
            {
                "id": r.id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "role": r.role,
                "form_key": r.form_key,
                "endpoint": r.endpoint,
                "method": r.method,
                "allowed": r.allowed,
                "reason": r.reason,
                "ip_address": r.ip_address,
                "user_id": r.user_id,
                "user_name": getattr(r.user, "full_name", None),
                "patient_id": r.patient_id,
                "patient_name": (r.patient.user.full_name if r.patient_id and r.patient and getattr(r.patient, "user_id", None) else None),
                "assignment_id": r.assignment_id,
            }
        )
    return Response({"success": True, "results": out}, status=status.HTTP_200_OK)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def queue_schedules(request):
    try:
        corr = _corr_id(request)
        global NEXT_SCHEDULE_ID
        if request.method == 'GET':
            return Response(QUEUE_SCHEDULES_STORE, status=status.HTTP_200_OK)
        data = request.data
        department = data.get('department') or 'OPD'
        start_time = str(data.get('start_time') or '08:00')
        end_time = str(data.get('end_time') or '17:00')
        days = data.get('days_of_week') or [0, 1, 2, 3, 4]
        is_active = bool(data.get('is_active', True))
        schedule = {
            'id': NEXT_SCHEDULE_ID,
            'department': department,
            'start_time': start_time,
            'end_time': end_time,
            'days_of_week': [int(x) for x in days],
            'is_active': is_active,
            'is_open': bool(QUEUE_STATUS_STORE.get(department, {}).get('is_open', False)),
        }
        QUEUE_SCHEDULES_STORE.insert(0, schedule)
        NEXT_SCHEDULE_ID += 1
        logger.info(f"[{corr}] queue_schedule created dept={department} id={schedule['id']}")
        return Response(schedule, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def queue_schedule_detail(request, schedule_id):
    try:
        corr = _corr_id(request)
        idx = next((i for i, s in enumerate(QUEUE_SCHEDULES_STORE) if s['id'] == schedule_id), None)
        if idx is None:
            return Response({'error': 'Schedule not found'}, status=status.HTTP_404_NOT_FOUND)
        if request.method == 'GET':
            return Response(QUEUE_SCHEDULES_STORE[idx], status=status.HTTP_200_OK)
        if request.method == 'PUT':
            data = request.data
            schedule = QUEUE_SCHEDULES_STORE[idx]
            schedule.update({
                'department': data.get('department', schedule['department']),
                'start_time': data.get('start_time', schedule['start_time']),
                'end_time': data.get('end_time', schedule['end_time']),
                'days_of_week': [int(x) for x in data.get('days_of_week', schedule['days_of_week'])],
                'is_active': bool(data.get('is_active', schedule['is_active'])),
            })
            QUEUE_SCHEDULES_STORE[idx] = schedule
            logger.info(f"[{corr}] queue_schedule updated id={schedule_id}")
            return Response(schedule, status=status.HTTP_200_OK)
        QUEUE_SCHEDULES_STORE.pop(idx)
        logger.info(f"[{corr}] queue_schedule deleted id={schedule_id}")
        return Response(status=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def queue_status(request):
    try:
        corr = _corr_id(request)
        if request.method == 'GET':
            department = request.query_params.get('department')
            if department:
                status_obj = QUEUE_STATUS_STORE.get(department, {'is_open': True})
                start_time = None
                end_time = None
                for s in QUEUE_SCHEDULES_STORE:
                    if s['department'] == department:
                        start_time = s.get('start_time')
                        end_time = s.get('end_time')
                        break
                payload = {
                    'department': department,
                    'is_open': bool(status_obj.get('is_open', True)),
                    'status_message': 'Open' if status_obj.get('is_open', True) else 'Closed',
                    'current_schedule_start_time': start_time,
                    'current_schedule_end_time': end_time,
                }
                logger.debug(f"[{corr}] queue_status get dept={department} -> {payload}")
                return Response(payload, status=status.HTTP_200_OK)
            items = []
            for s in QUEUE_SCHEDULES_STORE:
                dep = s['department']
                st = QUEUE_STATUS_STORE.get(dep, {'is_open': True})
                items.append({
                    'department': dep,
                    'is_open': bool(st.get('is_open', True)),
                    'current_schedule_start_time': s.get('start_time'),
                    'current_schedule_end_time': s.get('end_time'),
                })
            return Response(items, status=status.HTTP_200_OK)
        department = request.data.get('department') or 'OPD'
        is_open = bool(request.data.get('is_open', False))
        QUEUE_STATUS_STORE[department] = {'is_open': is_open}
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'queue_{department}',
                {
                    'type': 'queue_status_update',
                    'status': {
                        'department': department,
                        'is_open': is_open
                    }
                }
            )
            async_to_sync(channel_layer.group_send)(
                f'queue_{department}',
                {
                    'type': 'queue_notification',
                    'notification': {
                        'event': 'queue_opened' if is_open else 'queue_closed',
                        'department': department,
                        'message': f"Queue is now {'open' if is_open else 'closed'} for {department}.",
                        'timestamp': timezone.now().isoformat(),
                    }
                }
            )
        except Exception:
            pass
        logger.info(f"[{corr}] queue_status updated dept={department} is_open={is_open}")
        return Response({'message': 'Queue status updated', 'department': department, 'is_open': is_open}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def queue_status_logs(request):
    return Response([], status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def queue_no_show_report(request):
    user = request.user
    role = str(getattr(user, 'role', '') or '').lower()
    if role not in {'nurse', 'doctor', 'admin'}:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

    dept = (request.query_params.get('department') or '').strip()
    start = (request.query_params.get('start') or '').strip()
    end = (request.query_params.get('end') or '').strip()

    qs = QueueNoShowAuditLog.objects.all()
    if dept:
        qs = qs.filter(department=dept)
    if start:
        try:
            qs = qs.filter(created_at__gte=timezone.make_aware(datetime.fromisoformat(start)))
        except Exception:
            pass
    if end:
        try:
            qs = qs.filter(created_at__lte=timezone.make_aware(datetime.fromisoformat(end)))
        except Exception:
            pass

    event_counts = list(qs.values('event').annotate(count=Count('id')).order_by('event'))
    patient_counts = list(qs.filter(event__in=['no_show_marked', 'no_show_removed', 'no_show_moved_to_end']).values('patient_id').annotate(count=Count('id')).order_by('-count')[:20])

    return Response(
        {
            'department': dept or None,
            'range': {'start': start or None, 'end': end or None},
            'event_counts': event_counts,
            'top_patients': patient_counts,
        },
        status=status.HTTP_200_OK,
    )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def queue_daily_reset(request):
    if request.user.role not in ['nurse', 'doctor', 'admin']:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

    department = request.data.get('department') or 'OPD'
    today = timezone.now().date()

    try:
        with transaction.atomic():
            counter, _ = DailySequenceCounter.objects.select_for_update().get_or_create(
                department=department, date=today, defaults={'current_value': 0}
            )
            counter.current_value = 0
            counter.save()

        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'queue_{department}',
                {
                    'type': 'queue_notification',
                    'notification': {
                        'event': 'queue_reset',
                        'department': department,
                        'message': f'Queue numbering has been reset for {department}.',
                        'timestamp': timezone.now().isoformat(),
                    }
                }
            )
            async_to_sync(channel_layer.group_send)(
                f'queue_{department}',
                {
                    'type': 'queue_notification',
                    'notification': {
                        'event': 'queue_opened',
                        'department': department,
                        'message': f'Queue is now open for {department}.',
                        'timestamp': timezone.now().isoformat(),
                    }
                }
            )
        except Exception:
            pass

        logger.info(f"[{_corr_id(request)}] queue_daily_reset dept={department} date={today}")
        return Response({'message': 'Queue daily reset completed', 'department': department}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Queue daily reset failed: {str(e)}", exc_info=True)
        return Response({'error': 'Queue daily reset failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_queue(request):
    try:
        corr = _corr_id(request)
        user = request.user
        department = request.data.get('department', 'OPD')
        priority_level = request.data.get('priority_level')
        
        # Check if patient profile exists
        try:
            patient_profile = user.patient_profile
        except (AttributeError, PatientProfile.DoesNotExist):
            # Try to find by user id manually if related name issue
            patient_profile = PatientProfile.objects.filter(user=user).first()
            if not patient_profile:
                return Response({'error': 'Patient profile not found'}, status=status.HTTP_404_NOT_FOUND)

        # Check if already in queue (waiting/called/in_progress)
        existing_queue = QueueManagement.objects.filter(
            patient=patient_profile,
            status__in=['waiting', 'called', 'in_progress']
        ).first()

        if existing_queue:
             return Response({
                'message': 'Already in queue',
                'queue_number': existing_queue.queue_number,
                'status': existing_queue.status,
                'department': existing_queue.department,
                'estimated_wait_time': str(existing_queue.estimated_wait_time) if existing_queue.estimated_wait_time else None
            }, status=status.HTTP_200_OK)

        with transaction.atomic():
            today = timezone.now().date()
            # Lock the counter row
            counter, created = DailySequenceCounter.objects.select_for_update().get_or_create(
                department=department,
                date=today,
                defaults={'current_value': 0}
            )
            counter.current_value += 1
            counter.save()
            
            queue_number = counter.current_value
            
            avg_mins = _avg_consult_minutes_for_department(department)
            waiting_count = QueueManagement.objects.filter(department=department, status='waiting').count()
            has_active = _has_active_serving_patient(department)
            est_wait = timedelta(minutes=avg_mins * (int(waiting_count) + (1 if has_active else 0)))

            queue_entry = _safe_insert_queue_entry(
                patient_profile=patient_profile,
                department=department,
                queue_number=queue_number,
                est_wait=est_wait,
                waiting_count=waiting_count
            )
            if priority_level:
                prio_waiting = QueueManagement.objects.filter(department=department, status='waiting', is_priority=True).count()
                queue_entry.is_priority = True
                queue_entry.priority_level = str(priority_level)
                if str(priority_level).strip().lower() == "emergency":
                    queue_entry.priority_position = 0
                else:
                    queue_entry.priority_position = prio_waiting + 1
                queue_entry.save(update_fields=["is_priority", "priority_level", "priority_position", "updated_at"])
            
        # Broadcast update via WebSocket
        _broadcast(f'queue_{department}', {
            'type': 'queue_status_update',
            'status': {
                'department': department,
                'is_open': True
            }
        })
        _broadcast(f'queue_{department}', {
            'type': 'queue_position_update',
            'position': {
                'current_queue_number': queue_entry.queue_number,
                'status': queue_entry.status,
                'patient_id': patient_profile.user.id,
                'patient_name': patient_profile.user.full_name,
                'estimated_wait_mins': int(est_wait.total_seconds() // 60) if est_wait else 0,
                'queue_number': queue_entry.queue_number,
                'department': department,
            }
        })
        _broadcast(f'queue_user_{patient_profile.user.id}', {
            'type': 'queue_position_update',
            'position': {
                'current_queue_number': queue_entry.queue_number,
                'status': queue_entry.status,
                'patient_id': patient_profile.user.id,
                'patient_name': patient_profile.user.full_name,
                'estimated_wait_mins': int(est_wait.total_seconds() // 60) if est_wait else 0,
                'queue_number': queue_entry.queue_number,
                'department': department,
            }
        })

        logger.info(f"[{corr}] patient {patient_profile.user.id} joined queue {department} #{counter.current_value}")
        return Response(QueueSerializer(queue_entry).data, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error joining queue: {str(e)}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def leave_queue(request):
    """
    Patient-facing endpoint to voluntarily leave the queue.

    Accepts optional:
      - department: string (defaults to 'OPD')

    Idempotent behavior:
      - If no active queue entry exists, returns success with removed=False.
    """
    try:
        corr = _corr_id(request)
        user = request.user
        role = str(getattr(user, 'role', '') or '').lower()
        if role != 'patient':
            return Response({'error': 'Only patients can leave the queue.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            patient_profile = user.patient_profile
        except (AttributeError, PatientProfile.DoesNotExist):
            patient_profile = PatientProfile.objects.filter(user=user).first()
        if not patient_profile:
            return Response({'error': 'Patient profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data or {}
        department = (data.get('department') or request.query_params.get('department') or 'OPD').strip() or 'OPD'

        entry = (QueueManagement.objects
                 .select_related('patient__user')
                 .filter(patient=patient_profile, department=department, status__in=['waiting', 'called', 'in_progress'])
                 .order_by('-created_at')
                 .first())

        if not entry:
            logger.info(f"[{corr}] patient {patient_profile.user.id} leave_queue noop (no active entry) dept={department}")
            return Response({'success': True, 'removed': False, 'message': 'Not currently in queue.'}, status=status.HTTP_200_OK)

        entry.status = 'cancelled'
        entry.dequeue_time = timezone.now()
        entry.called_at = None
        entry.grace_expires_at = None
        entry.save(update_fields=['status', 'dequeue_time', 'called_at', 'grace_expires_at', 'updated_at'])

        _broadcast(f'queue_{department}', {
            'type': 'queue_status_update',
            'status': {'department': department, 'is_open': True}
        })

        logger.info(f"[{corr}] patient {patient_profile.user.id} left queue dept={department} queue_id={entry.id}")
        return Response({'success': True, 'removed': True, 'queue_id': entry.id, 'queue_number': entry.queue_number}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception("leave_queue failed")
        return Response({'error': 'Failed to leave queue', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_in_queue(request):
    user = request.user
    role = str(getattr(user, 'role', '') or '').lower()
    department = str((request.data or {}).get('department') or 'OPD').strip() or 'OPD'

    try:
        if role == 'patient':
            try:
                patient_profile = user.patient_profile
            except (AttributeError, PatientProfile.DoesNotExist):
                patient_profile = PatientProfile.objects.filter(user=user).first()
            if not patient_profile:
                return Response({'error': 'Patient profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        elif role in {'nurse', 'doctor', 'admin'}:
            patient_id = (request.data or {}).get("patient_id") or (request.data or {}).get("user_id")
            if not patient_id:
                return Response({'error': 'patient_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
            patient_profile = PatientProfile.objects.filter(user_id=patient_id).select_related("user").first()
            if not patient_profile:
                return Response({'error': 'Patient profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({'error': 'Unauthorized.'}, status=status.HTTP_403_FORBIDDEN)

        now = timezone.now()
        with transaction.atomic():
            entry = (QueueManagement.objects
                     .select_for_update()
                     .select_related('patient__user')
                     .filter(patient=patient_profile, department=department, status='called')
                     .order_by('-called_at')
                     .first())

            if not entry:
                last_no_show = (QueueManagement.objects
                                .select_for_update()
                                .filter(patient=patient_profile, department=department, status='no_show')
                                .order_by('-last_no_show_at', '-updated_at')
                                .first())
                if last_no_show and last_no_show.last_no_show_at:
                    late_window = _queue_late_arrival_rejoin_seconds()
                    if late_window and (now - last_no_show.last_no_show_at).total_seconds() <= late_window:
                        with transaction.atomic():
                            today = timezone.now().date()
                            counter, _ = DailySequenceCounter.objects.select_for_update().get_or_create(
                                department=department,
                                date=today,
                                defaults={'current_value': 0}
                            )
                            counter.current_value += 1
                            counter.save()

                            avg_mins = _avg_consult_minutes_for_department(department)
                            waiting_count = QueueManagement.objects.filter(department=department, status='waiting').count()
                            has_active = _has_active_serving_patient(department)
                            est_wait = timedelta(minutes=avg_mins * (int(waiting_count) + (1 if has_active else 0)))
                            queue_entry = _safe_insert_queue_entry(
                                patient_profile=patient_profile,
                                department=department,
                                queue_number=counter.current_value,
                                est_wait=est_wait,
                                waiting_count=waiting_count
                            )
                            _log_no_show_event(queue_entry, event="late_arrival", actor=user if role != "patient" else None, metadata={"from_queue_id": last_no_show.id})
                        return Response({'success': True, 'requeued': True, 'queue_number': queue_entry.queue_number, 'department': department}, status=status.HTTP_200_OK)

                return Response({'error': 'No active called queue entry found.'}, status=status.HTTP_404_NOT_FOUND)

            entry.checked_in_at = now
            entry.status = 'completed'
            entry.dequeue_time = now
            entry.finished_at = now
            try:
                if entry.enqueue_time:
                    entry.actual_wait_time = now - entry.enqueue_time
            except Exception:
                pass
            entry.save(update_fields=['checked_in_at', 'status', 'dequeue_time', 'finished_at', 'actual_wait_time', 'updated_at'])
            _log_no_show_event(entry, event="checked_in", actor=user if role != "patient" else None, metadata={"late": bool(entry.grace_expires_at and now > entry.grace_expires_at)})

        try:
            qs, _ = QueueStatus.objects.get_or_create(department=department)
            qs.is_open = True
            qs.current_serving = entry.queue_number
            qs.total_waiting = QueueManagement.objects.filter(department=department, status='waiting').count()
            qs.status_message = 'In Progress'
            if role in {'nurse', 'doctor', 'admin'}:
                qs.last_updated_by = user
            qs.save()
        except Exception:
            pass

        try:
            _broadcast(f'queue_{department}', {
                'type': 'queue_position_update',
                'position': {
                    'department': department,
                    'current_queue_number': entry.queue_number,
                    'status': 'completed',
                    'patient_id': entry.patient.user.id,
                    'patient_name': entry.patient.user.full_name,
                    'checked_in': True,
                }
            })
            _broadcast(f'queue_user_{entry.patient.user.id}', {
                'type': 'queue_position_update',
                'position': {
                    'department': department,
                    'current_queue_number': entry.queue_number,
                    'status': 'completed',
                    'patient_id': entry.patient.user.id,
                    'patient_name': entry.patient.user.full_name,
                    'checked_in': True,
                }
            })
        except Exception:
            pass

        try:
            _broadcast(
                f"queue_{department}",
                {
                    "type": "queue_notification",
                    "notification": {
                        "event": "patient_checked_in",
                        "department": department,
                        "message": f"Patient arrived for Queue #{entry.queue_number} ({department}).",
                        "timestamp": now.isoformat(),
                        "patient_profile": {
                            "id": entry.patient.id,
                            "user_id": entry.patient.user.id,
                            "full_name": entry.patient.user.full_name,
                            "queue_number": entry.queue_number,
                            "department": department,
                            "gender": entry.patient.user.gender,
                            "blood_type": entry.patient.blood_type,
                            "medical_condition": entry.patient.medical_condition,
                        },
                    },
                },
            )
        except Exception:
            pass

        try:
            _create_and_send_queue_notifications(
                queue_entry=entry,
                message=f"Check-in confirmed. Please proceed for Queue #{entry.queue_number} ({department}).",
                actor=user if role in {'nurse', 'doctor', 'admin'} else None,
                channels=[Notification.CHANNEL_WEBSOCKET, Notification.CHANNEL_PUSH, Notification.CHANNEL_SMS],
                event="queue_checked_in",
            )
        except Exception:
            pass

        return Response({'success': True, 'checked_in': True, 'queue_number': entry.queue_number, 'department': department, 'removed_from_queue': True}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception("check_in_queue failed")
        return Response({'error': 'Failed to check in', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def check_queue_availability(request):
    # 24/7 Operation: Always return open
    return Response({
        'is_open': True,
        'status_message': 'Queue is open 24/7',
        'current_schedule_start_time': '00:00:00',
        'current_schedule_end_time': '23:59:59'
    }, status=status.HTTP_200_OK)

def _select_next_waiting_patient(department: str):
    next_priority = (QueueManagement.objects
                     .select_related("patient__user")
                     .filter(department=department, status='waiting', is_priority=True)
                     .order_by('priority_position', 'enqueue_time')
                     .first())
    if next_priority:
        return next_priority
    return (QueueManagement.objects
            .select_related("patient__user")
            .filter(department=department, status='waiting', is_priority=False)
            .order_by('enqueue_time')
            .first())

def _mark_queue_entry_no_show(queue_entry: QueueManagement, *, actor=None, reason: str = "grace_expired") -> dict:
    now = timezone.now()
    policy = _queue_no_show_policy()
    dept = str(queue_entry.department or "")

    queue_entry.last_no_show_at = now
    queue_entry.no_show_action = policy

    if policy == "remove":
        queue_entry.status = "no_show"
        queue_entry.dequeue_time = now
        queue_entry.called_at = None
        queue_entry.grace_expires_at = None
        queue_entry.checked_in_at = None
        queue_entry.save(update_fields=["status", "dequeue_time", "called_at", "grace_expires_at", "checked_in_at", "last_no_show_at", "no_show_action", "updated_at"])
        _log_no_show_event(queue_entry, event="no_show_marked", actor=actor, metadata={"reason": reason, "action": "remove"})
        _log_no_show_event(queue_entry, event="no_show_removed", actor=actor, metadata={"reason": reason})
    else:
        max_pos = QueueManagement.objects.filter(department=dept, status="waiting").aggregate(Max("position_in_queue")).get("position_in_queue__max") or 0
        queue_entry.status = "waiting"
        queue_entry.called_at = None
        queue_entry.grace_expires_at = None
        queue_entry.checked_in_at = None
        queue_entry.enqueue_time = now
        queue_entry.position_in_queue = int(max_pos) + 1
        queue_entry.save(update_fields=["status", "called_at", "grace_expires_at", "checked_in_at", "enqueue_time", "position_in_queue", "last_no_show_at", "no_show_action", "updated_at"])
        _log_no_show_event(queue_entry, event="no_show_marked", actor=actor, metadata={"reason": reason, "action": "move_to_end"})
        _log_no_show_event(queue_entry, event="no_show_moved_to_end", actor=actor, metadata={"reason": reason})

    try:
        _broadcast(f'queue_{dept}', {
            'type': 'queue_position_update',
            'position': {
                'department': dept,
                'current_queue_number': queue_entry.queue_number,
                'status': 'no_show',
                'patient_id': queue_entry.patient.user.id if queue_entry.patient and queue_entry.patient.user else None,
                'patient_name': queue_entry.patient.user.full_name if queue_entry.patient and queue_entry.patient.user else None,
                'action': policy,
                'timestamp': now.isoformat(),
            }
        })
    except Exception:
        pass

    try:
        _create_and_send_queue_notifications(
            queue_entry=queue_entry,
            message=f"Queue update: you were marked as No-Show for Queue #{queue_entry.queue_number} ({dept}).",
            actor=actor,
            channels=[Notification.CHANNEL_WEBSOCKET, Notification.CHANNEL_PUSH, Notification.CHANNEL_SMS],
            event="queue_no_show",
        )
    except Exception:
        pass

    return {"department": dept, "queue_id": queue_entry.id, "queue_number": queue_entry.queue_number, "policy": policy}

def _call_next_patient(*, department: str, actor=None, channels: list[str] | None = None, force_skip_called: bool = False) -> dict:
    now = timezone.now()
    grace_seconds = _queue_no_show_grace_seconds()
    dept = str(department or "OPD").strip() or "OPD"

    if not force_skip_called:
        existing_called = QueueManagement.objects.filter(department=dept, status="called").order_by("-called_at").first()
        if existing_called:
            return {"ok": False, "reason": "already_called", "queue_id": existing_called.id, "queue_number": existing_called.queue_number}

    next_patient = _select_next_waiting_patient(dept)
    if not next_patient:
        return {"ok": False, "reason": "empty"}

    next_patient.status = "called"
    next_patient.called_at = now
    next_patient.grace_expires_at = now + timedelta(seconds=grace_seconds)
    next_patient.checked_in_at = None
    next_patient.save(update_fields=["status", "called_at", "grace_expires_at", "checked_in_at", "updated_at"])

    _log_no_show_event(next_patient, event="called", actor=actor, metadata={"grace_seconds": grace_seconds})

    try:
        qs, _ = QueueStatus.objects.get_or_create(department=dept)
        qs.is_open = True
        qs.current_serving = next_patient.queue_number
        qs.total_waiting = QueueManagement.objects.filter(department=dept, status='waiting').count()
        qs.status_message = 'Calling'
        qs.last_updated_by = actor if actor and getattr(actor, "id", None) else None
        qs.save()
    except Exception:
        pass

    notif_message = f"You are being called. Queue #{next_patient.queue_number} ({dept}). Please check in within {grace_seconds} seconds."
    notif_results = _create_and_send_queue_notifications(
        queue_entry=next_patient,
        message=notif_message,
        actor=actor,
        channels=channels or [Notification.CHANNEL_SMS, Notification.CHANNEL_PUSH, Notification.CHANNEL_WEBSOCKET],
        event="queue_called",
    )

    try:
        avg_mins = _avg_consult_minutes_for_department(dept)
        _broadcast(f'queue_{dept}', {
            'type': 'queue_position_update',
            'position': {
                'department': dept,
                'current_queue_number': next_patient.queue_number,
                'status': 'called',
                'patient_id': next_patient.patient.user.id,
                'patient_name': next_patient.patient.user.full_name,
                'grace_expires_at': next_patient.grace_expires_at.isoformat() if next_patient.grace_expires_at else None,
                'grace_seconds': grace_seconds,
                'avg_consult_mins': avg_mins,
            }
        })
        _broadcast(f'queue_user_{next_patient.patient.user.id}', {
            'type': 'queue_position_update',
            'position': {
                'department': dept,
                'current_queue_number': next_patient.queue_number,
                'status': 'called',
                'patient_id': next_patient.patient.user.id,
                'patient_name': next_patient.patient.user.full_name,
                'grace_expires_at': next_patient.grace_expires_at.isoformat() if next_patient.grace_expires_at else None,
                'grace_seconds': grace_seconds,
                'avg_consult_mins': avg_mins,
            }
        })
    except Exception:
        pass

    try:
        from backend.operations.tasks import process_queue_no_show
        process_queue_no_show.apply_async(args=[next_patient.id], countdown=grace_seconds)
    except Exception as e:
        _log_no_show_event(next_patient, event="system_error", actor=actor, metadata={"stage": "schedule_no_show_task", "error": str(e)})

    return {
        "ok": True,
        "queue_id": next_patient.id,
        "queue_number": next_patient.queue_number,
        "department": dept,
        "grace_seconds": grace_seconds,
        "grace_expires_at": next_patient.grace_expires_at.isoformat() if next_patient.grace_expires_at else None,
        "notification_results": notif_results,
        "patient_user_id": next_patient.patient.user.id,
    }

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_queue_processing(request):
    user = request.user
    if user.role not in ['nurse', 'doctor', 'admin']:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

    department = str(request.data.get('department', 'OPD') or 'OPD').strip() or 'OPD'
    channels = request.data.get("channels")
    force_skip_called = bool(request.data.get("force_skip_called", False))

    try:
        now = timezone.now()
        with transaction.atomic():
            expired_called = list(
                QueueManagement.objects.select_for_update().filter(
                    department=department,
                    status="called",
                    checked_in_at__isnull=True,
                    grace_expires_at__isnull=False,
                    grace_expires_at__lte=now,
                )
            )
            for entry in expired_called:
                _mark_queue_entry_no_show(entry, actor=user, reason="grace_expired")

            if force_skip_called:
                active_called = (QueueManagement.objects.select_for_update()
                                 .filter(department=department, status="called", checked_in_at__isnull=True)
                                 .order_by("-called_at")
                                 .first())
                if active_called:
                    _mark_queue_entry_no_show(active_called, actor=user, reason="skipped_by_staff")

            current_patients = QueueManagement.objects.filter(department=department, status='in_progress')
            for current in current_patients:
                current.status = 'completed'
                current.finished_at = now
                current.save(update_fields=["status", "finished_at", "updated_at"])

        result = _call_next_patient(department=department, actor=user, channels=channels, force_skip_called=force_skip_called)
        if not result.get("ok"):
            if result.get("reason") == "already_called":
                return Response({'success': True, 'message': 'Patient already called', **result}, status=status.HTTP_200_OK)
            return Response({'message': 'Queue is empty', 'success': False, **result}, status=status.HTTP_200_OK)

        next_patient = QueueManagement.objects.select_related("patient__user").filter(id=result["queue_id"]).first()
        queue_status_payload = None
        try:
            qs = QueueStatus.objects.filter(department=department).first()
            if qs:
                queue_status_payload = {
                    'department': qs.department,
                    'is_open': qs.is_open,
                    'current_serving': qs.current_serving,
                    'total_waiting': qs.total_waiting,
                    'status_message': qs.status_message,
                }
        except Exception:
            queue_status_payload = None

        patient_profile_payload = None
        if next_patient:
            from datetime import date
            def _calc_age(birth_date):
                if not birth_date:
                    return None
                today = date.today()
                return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

            patient_profile_payload = {
                'id': next_patient.patient.id,
                'user_id': next_patient.patient.user.id,
                'full_name': next_patient.patient.user.full_name,
                'queue_number': next_patient.queue_number,
                'department': department,
                'age': _calc_age(next_patient.patient.user.date_of_birth),
                'gender': next_patient.patient.user.gender,
                'blood_type': next_patient.patient.blood_type,
                'medical_condition': next_patient.patient.medical_condition,
                'profile_picture': next_patient.patient.user.profile_picture.url if getattr(next_patient.patient.user, "profile_picture", None) and hasattr(next_patient.patient.user.profile_picture, "url") else None,
            }

        return Response(
            {
                'success': True,
                'message': f'Called patient #{result["queue_number"]}',
                'current_serving': result["queue_number"],
                'department': department,
                'queue_status': queue_status_payload,
                'notification_results': result.get("notification_results"),
                'grace_seconds': result.get("grace_seconds"),
                'grace_expires_at': result.get("grace_expires_at"),
                'patient_profile': patient_profile_payload,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        logger.error(f"Error starting queue processing: {str(e)}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirm_notification_delivery(request):
    notification_id = request.data.get('notification_id')
    if not notification_id:
        return Response({'error': 'notification_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    notif = Notification.objects.filter(id=notification_id, user=request.user).first()
    if not notif:
        return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

    notif.delivery_status = Notification.DELIVERY_DELIVERED
    notif.delivered_at = timezone.now()
    notif.save(update_fields=['delivery_status', 'delivered_at', 'updated_at'])
    payload = None
    try:
        payload = NotificationSerializer(notif).data
    except Exception:
        payload = None
    return Response({'message': 'Notification confirmed', 'notification': payload}, status=status.HTTP_200_OK)

@api_view(['GET'])
def ui_config(request):
    return Response(
        {
            "webpush_vapid_public_key": settings.WEBPUSH_VAPID_PUBLIC_KEY,
        },
        status=status.HTTP_200_OK,
    )

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def webpush_subscribe(request):
    subscription = request.data.get("subscription") if isinstance(request.data, dict) else None
    if not subscription:
        subscription = request.data

    if not isinstance(subscription, dict):
        return Response({"error": "subscription payload is required"}, status=status.HTTP_400_BAD_REQUEST)

    endpoint = subscription.get("endpoint")
    keys = subscription.get("keys") or {}
    if not endpoint or not isinstance(keys, dict) or not keys.get("p256dh") or not keys.get("auth"):
        return Response({"error": "invalid subscription payload"}, status=status.HTTP_400_BAD_REQUEST)

    ua = request.headers.get("User-Agent", "") if hasattr(request, "headers") else ""
    obj, _ = WebPushSubscription.objects.update_or_create(
        user=request.user,
        endpoint=endpoint,
        defaults={
            "subscription": subscription,
            "user_agent": ua or "",
            "is_active": True,
        },
    )
    return Response({"success": True, "id": obj.id}, status=status.HTTP_200_OK)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def webpush_unsubscribe(request):
    endpoint = None
    if isinstance(request.data, dict):
        endpoint = request.data.get("endpoint")
        if not endpoint and isinstance(request.data.get("subscription"), dict):
            endpoint = request.data["subscription"].get("endpoint")

    if not endpoint:
        return Response({"error": "endpoint is required"}, status=status.HTTP_400_BAD_REQUEST)

    qs = WebPushSubscription.objects.filter(user=request.user, endpoint=endpoint, is_active=True)
    updated = qs.update(is_active=False)
    return Response({"success": True, "updated": updated}, status=status.HTTP_200_OK)
