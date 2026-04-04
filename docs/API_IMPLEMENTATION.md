## API Implementation (MediSync)

This file lists the API structure that exists in the repository and explains how JWT authentication is used.

### Backend API Base Path

- Backend endpoints are mounted at clean root paths (no `/api/` prefix):
  - `/users/` → `backend/users/urls.py`
  - `/operations/` → `backend/operations/urls.py`
  - `/analytics/` → `backend/analytics/urls.py`
  - `/admin/` → `backend/admin_site/urls.py`
  - Django admin site: `/django-admin/` → Django admin UI
  - Source: `backend/urls.py`

### REST Framework & Authentication Configuration

- DRF is enabled and configured in `backend/settings.py`:
  - Authentication classes (in order):
    - JWT (`rest_framework_simplejwt.authentication.JWTAuthentication`)
    - Session auth
    - Token auth
  - Default permission: authenticated users only
  - Parsers: JSON, Form, Multipart

### How JWT Works in MediSync

#### A) Login (JWT access + refresh)

1) Client sends credentials:

```http
POST /users/login/
Content-Type: application/json

{ "email": "<email>", "password": "<password>" }
```

2) If credentials are valid and 2FA is not enabled, the backend returns:
- `access` token (short-lived)
- `refresh` token (longer-lived)

3) Client uses the access token on subsequent requests:

```http
Authorization: Bearer <access_token>
```

#### B) Token Refresh

When the access token expires, the client refreshes it:

```http
POST /users/token/refresh/
Content-Type: application/json

{ "refresh": "<refresh_token>" }
```

The backend returns a new access token (and refresh rotation behavior depends on `SIMPLE_JWT` settings in `backend/settings.py`).

#### C) 2FA Login Flow (when enabled)

1) `/users/login/` may respond with:
- `requires_2fa: true`

2) Client then verifies OTP:

```http
POST /users/2fa/login/verify/
Content-Type: application/json

{ "email": "<email>", "otp_code": "<6_digit_code>" }
```

3) If OTP is valid, backend returns JWT `access` + `refresh`.

### Endpoint Inventory (From URL Config Files)

#### 1) Users API (`/users/`)

Source: `backend/users/urls.py`

**Authentication**
- `POST register/`
- `POST login/`
- `POST token/refresh/`

**Public data**
- `GET specializations/`

**Profile**
- `GET profile/`
- `PUT|PATCH profile/update/`

**Verification**
- `POST verification/upload/`
- `POST verification/verify-now/`

**Password reset**
- `POST forgot-password/`
- `POST reset-password/<uidb64>/<token>/`

**2FA**
- `POST 2fa/enable/`
- `POST 2fa/verify/`
- `POST 2fa/disable/`
- `POST 2fa/login/verify/`

**Patient lists**
- `GET doctor/patients/`
- `GET nurse/patients/`

**Nurse-centric forms**
- `GET nurse/patient/<patient_id>/forms/`
- `GET|POST nurse/patient/<patient_id>/intake/`
- `GET|POST nurse/patient/<patient_id>/flow-sheets/`
- `PUT|PATCH nurse/patient/<patient_id>/flow-sheets/<index>/`
- `GET|POST nurse/patient/<patient_id>/mar/`
- `PUT|PATCH nurse/patient/<patient_id>/mar/<index>/`
- `GET|POST nurse/patient/<patient_id>/education/`
- `PUT|PATCH nurse/patient/<patient_id>/education/<index>/`
- `GET|POST nurse/patient/<patient_id>/discharge/`
- `GET|PUT nurse/patient/<patient_id>/psychiatric-opd/`
- `POST nurse/patient/<patient_id>/psychiatric-opd/submit/`

**Doctor-centric forms**
- `GET doctor/patient/<patient_id>/forms/`
- `GET doctor/patient/<patient_id>/nurse-intake/`
- `GET|POST doctor/patient/<patient_id>/hp/`
- `PUT|PATCH doctor/patient/<patient_id>/hp/<index>/`
- `GET|POST doctor/patient/<patient_id>/progress-notes/`
- `PUT|PATCH doctor/patient/<patient_id>/progress-notes/<index>/`
- `GET|POST doctor/patient/<patient_id>/orders/`
- `PUT|PATCH doctor/patient/<patient_id>/orders/<index>/`
- `GET|POST doctor/patient/<patient_id>/operative-reports/`
- `PUT|PATCH doctor/patient/<patient_id>/operative-reports/<index>/`

#### 2) Operations API (`/operations/`)

Source: `backend/operations/urls.py`

This module contains queues, appointments, messaging, notifications, archives, monitoring, and secure transmission endpoints:

**Dashboard / appointments / notifications**
- `dashboard/stats/`
- `appointments/`
- `queue/patients/`
- `notifications/`
- `notifications/<notification_id>/mark-read/`
- `notifications/mark-all-read/`
- `patient-assessments/`
- `pain-assessment/<patient_id>/history/`

**Appointment management**
- `blocked-dates/`
- `block-date/`
- `create-appointment/`
- `appointments/schedule/`
- `appointments/<appointment_id>/reschedule/`
- `appointments/<appointment_id>/cancel/`
- `appointments/<appointment_id>/check-in/`
- `appointments/<appointment_id>/start/`
- `appointments/<appointment_id>/finish/`
- `appointments/<appointment_id>/notify-patient/`
- `patient/appointments/`
- `patient/dashboard/summary/`

**Messaging**
- `messaging/conversations/`
- `messaging/conversations/create/`
- `messaging/conversations/<conversation_id>/messages/`
- `messaging/conversations/<conversation_id>/send/`
- `messaging/messages/<message_id>/react/`
- `messaging/available-users/`
- `messaging/notifications/`
- `messaging/notifications/<notification_id>/mark-sent/`
- `messaging/messages/<message_id>/mark-read/`

**Availability / nurse capacity**
- `availability/doctors/free/`
- `availability/nurses/`
- `nurses/list/`
- `nurse/capacity/validate/`

**Medicine inventory**
- `medicine-inventory/`
- `medicine-inventory/add/`
- `medicine-inventory/<medicine_id>/update/`
- `medicine-inventory/<medicine_id>/dispense/`
- `medicine-inventory/<medicine_id>/delete/`

**Nurse queue**
- `nurse/queue/patients/`
- `nurse/queue/remove/`
- `nurse/queue/mark-served/`

**Doctor selection / hospital departments / assignment**
- `available-doctors/`
- `hospital/departments/`
- `assign-patient/`

**Doctor assignment**
- `doctor/assignments/`
- `doctor/assignments/<assignment_id>/accept/`
- `doctor/assignments/<assignment_id>/consultation-notes/`

**Queue management**
- `queue/schedules/`
- `queue/schedules/<schedule_id>/`
- `queue/status/`
- `queue/status/logs/`
- `queue/daily-reset/`
- `queue/join/`
- `queue/availability/`
- `queue/start-processing/`
- `queue/notifications/confirm/`

**Nurse → Doctor handoff**
- `nurse/send-records/`

**Archives**
- `archives/`
- `archives/create/`
- `archives/<archive_id>/`
- `archives/<archive_id>/update/`
- `archives/<archive_id>/unarchive/`
- `archives/<archive_id>/export/`
- `archives/logs/`

**Monitoring / verification**
- `ui-config/`
- `client-log/`
- `verification-status/`

**Pain assessment**
- `pain-assessment/<patient_id>/record/`
- `pain-assessment/<patient_id>/history/`

**Secure transmission / MFA / purge**
- `secure/register-public-key/`
- `secure/doctor-public-key/<doctor_id>/`
- `secure/transmissions/`
- `secure/transmissions/list/`
- `secure/transmissions/<transmission_id>/`
- `secure/transmissions/<transmission_id>/received/`
- `secure/mfa/challenge/`
- `secure/mfa/verify/`
- `secure/transmissions/<transmission_id>/breach/`
- `secure/purge/medical-records/`

#### 3) Analytics API (`/analytics/`)

Source: `backend/analytics/urls.py`

- `GET /` (main analytics)
- `GET status/<task_id>/`
- `GET history/`
- `POST refresh/`
- `GET realtime/`
- `GET stream/`
- `GET performance/`
- `POST stress-test/`
- `GET doctor/`
- `GET nurse/`
- `GET doctor/recommendations/`
- `GET nurse/recommendations/`
- `POST pdf/`
- `GET events/`
- `POST events/log/`
- `POST uptime/ping/`
- `GET uptime/status/`

#### 4) Admin API (`/admin/`)

Source: `backend/admin_site/urls.py`

- `GET /` (overview)
- `GET config/`
- `POST login/`
- `POST register/`
- `POST token/refresh/`
- `GET csrf-token/`
- `POST verify-email/`
- `POST resend-verification/`
- `GET dashboard/stats/`
- `GET verifications/`
- `POST verifications/<verification_id>/accept/`
- `POST verifications/<verification_id>/decline/`
- `PUT verifications/<verification_id>/update/`
- `GET verifications/<verification_id>/document/`
- `GET logs/`
- `POST hospital/register/`
- `POST hospital/activate/`
- `GET hospital/status/`
- `GET hospitals/`
- `GET my/hospitals/`
- `POST hospital/verify-selection/`
- `GET settings/profile/`
- `POST settings/password/`
- `GET users/export/`
- `GET users/hospital/`

### WebSocket (Real-time) Routes

Source: `backend/operations/routing.py`

- `ws/messaging/<user_id>/`
- `ws/queue/<department>/<user_id>/`
- `ws/queue/<department>/`
- `ws/medication/<patient_id>/`

### Middleware / Integration Mechanisms

- Redis is used for:
  - caching (DRF/backend cache usage)
  - Channels (WebSocket event fanout)
  - Celery broker/result backend
- Celery tasks exist for queue/notification processing in `backend/operations/tasks.py`.

### Security Implementation (What Exists)

- Role-based access control: implemented at the view level (role checks in endpoints) + DRF authenticated default.
- Input validation: DRF serializers are used for many endpoints.
- Secure data handling: environment-driven secrets + file upload restrictions + encrypted storage for psychiatric OPD drafts + secure transmission/audit endpoints in operations.

### DevOps Practices (What Exists)

- Version control: repo structure supports Git workflows (root and app-level `.gitignore` files).
- CI/CD:
  - No CI workflow file is currently present in this repository.
  - Deployment approach is documented for Render + Cloudflare Pages in `docs/DEPLOYMENT_RENDER_CLOUDFLARE.md`.
- Monitoring/logging:
  - Python logging is used across backend modules.
- Client log ingestion endpoint exists: `/operations/client-log/`
- Analytics includes uptime/usage endpoints under `/analytics/uptime/*` and `/analytics/events/*`.
