## API Implementation (MediSync)

This file lists the API structure that exists in the repository and explains how JWT authentication works. Tables follow the format: Verb / Endpoint / Data / Description.

### Backend Base Paths (No `/api/` Prefix)

| Module | Base Path | URL Config |
|---|---|---|
| Users | `/users/` | `backend/users/urls.py` |
| Operations | `/operations/` | `backend/operations/urls.py` |
| Analytics | `/analytics/` | `backend/analytics/urls.py` |
| Admin API (admin_site) | `/admin/` | `backend/admin_site/urls.py` |
| Django Admin UI | `/django-admin/` | Django admin site |

### JWT Token Flow (How It Works)

**1) Login**

| Step | What happens |
|---|---|
| 1 | Client sends credentials to `POST /users/login/` |
| 2 | Backend validates user credentials |
| 3 | If 2FA is disabled → backend returns `access` + `refresh` JWT tokens |
| 4 | Client sends requests with `Authorization: Bearer <access_token>` |

**2) Refresh Token**

| Step | What happens |
|---|---|
| 1 | When access token expires, client calls `POST /users/token/refresh/` |
| 2 | Backend validates refresh token and returns a new access token |

**3) 2FA Login (if enabled)**

| Step | What happens |
|---|---|
| 1 | `POST /users/login/` returns `requires_2fa: true` |
| 2 | Client submits OTP via `POST /users/2fa/login/verify/` |
| 3 | Backend validates OTP and returns `access` + `refresh` |

### 1) Users API (`/users/`)

Source: `backend/users/urls.py`

#### Authentication

| Verb | Endpoint | Data | Description |
|---|---|---|---|
| POST | `register/` | `{ email, password, role, ... }` | Register a new user account |
| POST | `login/` | `{ email, password }` | Login and receive JWT tokens (or 2FA required) |
| POST | `token/refresh/` | `{ refresh }` | Refresh access token using refresh token |

#### 2FA

| Verb | Endpoint | Data | Description |
|---|---|---|---|
| POST | `2fa/enable/` | `{ password }` | Enable 2FA for the logged-in user |
| POST | `2fa/verify/` | `{ otp_code }` | Verify 2FA setup OTP |
| POST | `2fa/disable/` | `{ password, otp_code }` | Disable 2FA |
| POST | `2fa/login/verify/` | `{ email, otp_code }` | Complete 2FA login and receive tokens |

#### Profile

| Verb | Endpoint | Data | Description |
|---|---|---|---|
| GET | `profile/` | — | Get current user profile |
| PUT/PATCH | `profile/update/` | `{ ...fields }` | Update current user profile |

#### Verification

| Verb | Endpoint | Data | Description |
|---|---|---|---|
| POST | `verification/upload/` | `multipart/form-data` | Upload verification documents |
| POST | `verification/verify-now/` | — | Trigger verification workflow |

#### Password Reset

| Verb | Endpoint | Data | Description |
|---|---|---|---|
| POST | `forgot-password/` | `{ email }` | Request password reset email |
| POST | `reset-password/<uidb64>/<token>/` | `{ new_password }` | Reset password using token |

#### Public Data

| Verb | Endpoint | Data | Description |
|---|---|---|---|
| GET | `specializations/` | — | List available specializations |

#### Patient Lists

| Verb | Endpoint | Data | Description |
|---|---|---|---|
| GET | `doctor/patients/` | — | Doctor’s patient list |
| GET | `nurse/patients/` | — | Nurse’s patient list |

#### Nurse-Centric Forms

| Verb | Endpoint | Data | Description |
|---|---|---|---|
| GET | `nurse/patient/<patient_id>/forms/` | — | List available forms for a patient |
| GET/POST | `nurse/patient/<patient_id>/intake/` | `{ ... }` | Create or fetch nurse intake |
| GET/POST | `nurse/patient/<patient_id>/flow-sheets/` | `{ ... }` | Add/list flow sheet entries |
| PUT/PATCH | `nurse/patient/<patient_id>/flow-sheets/<index>/` | `{ ... }` | Update a flow sheet entry |
| GET/POST | `nurse/patient/<patient_id>/mar/` | `{ ... }` | Add/list MAR entries |
| PUT/PATCH | `nurse/patient/<patient_id>/mar/<index>/` | `{ ... }` | Update MAR entry |
| GET/POST | `nurse/patient/<patient_id>/education/` | `{ ... }` | Add/list patient education records |
| PUT/PATCH | `nurse/patient/<patient_id>/education/<index>/` | `{ ... }` | Update an education entry |
| GET/POST | `nurse/patient/<patient_id>/discharge/` | `{ ... }` | Discharge planning record |
| GET/PUT | `nurse/patient/<patient_id>/psychiatric-opd/` | `{ ... }` | Get/update psychiatric OPD draft |
| POST | `nurse/patient/<patient_id>/psychiatric-opd/submit/` | `{ ... }` | Submit psychiatric OPD questionnaire |

#### Doctor-Centric Forms

| Verb | Endpoint | Data | Description |
|---|---|---|---|
| GET | `doctor/patient/<patient_id>/forms/` | — | List available forms for a patient |
| GET | `doctor/patient/<patient_id>/nurse-intake/` | — | View nurse intake for a patient |
| GET/POST | `doctor/patient/<patient_id>/hp/` | `{ ... }` | Add/list history & physical |
| PUT/PATCH | `doctor/patient/<patient_id>/hp/<index>/` | `{ ... }` | Update H&P entry |
| GET/POST | `doctor/patient/<patient_id>/progress-notes/` | `{ ... }` | Add/list progress notes |
| PUT/PATCH | `doctor/patient/<patient_id>/progress-notes/<index>/` | `{ ... }` | Update progress note |
| GET/POST | `doctor/patient/<patient_id>/orders/` | `{ ... }` | Add/list orders |
| PUT/PATCH | `doctor/patient/<patient_id>/orders/<index>/` | `{ ... }` | Update order entry |
| GET/POST | `doctor/patient/<patient_id>/operative-reports/` | `{ ... }` | Add/list operative reports |
| PUT/PATCH | `doctor/patient/<patient_id>/operative-reports/<index>/` | `{ ... }` | Update operative report |

### 2) Operations API (`/operations/`)

Source: `backend/operations/urls.py`

#### Dashboard / Appointments / Notifications

| Verb | Endpoint | Data | Description |
|---|---|---|---|
| GET | `dashboard/stats/` | — | Dashboard statistics |
| GET | `appointments/` | — | List appointments |
| GET | `queue/patients/` | — | Queue patient listing |
| GET | `notifications/` | — | List notifications |
| POST | `notifications/<notification_id>/mark-read/` | — | Mark notification as read |
| POST | `notifications/mark-all-read/` | — | Mark all notifications as read |
| GET | `patient-assessments/` | query params | Patient assessment archives listing |
| GET | `pain-assessment/<patient_id>/history/` | — | Pain assessment history |

#### Appointment Management

| Verb | Endpoint | Data | Description |
|---|---|---|---|
| GET | `blocked-dates/` | — | View blocked dates |
| POST | `block-date/` | `{ date, reason }` | Block a schedule date |
| POST | `create-appointment/` | `{ ... }` | Create appointment |
| GET | `appointments/schedule/` | query params | Get available schedule slots |
| POST | `appointments/<appointment_id>/reschedule/` | `{ ... }` | Reschedule appointment |
| POST | `appointments/<appointment_id>/cancel/` | `{ ... }` | Cancel appointment |
| POST | `appointments/<appointment_id>/check-in/` | — | Mark appointment checked-in |
| POST | `appointments/<appointment_id>/start/` | — | Start consultation |
| POST | `appointments/<appointment_id>/finish/` | — | Finish consultation |
| POST | `appointments/<appointment_id>/notify-patient/` | — | Send patient reminder/notification |
| GET | `patient/appointments/` | — | Patient appointment list |
| GET | `patient/dashboard/summary/` | query params | Patient dashboard summary |

#### Messaging

| Verb | Endpoint | Data | Description |
|---|---|---|---|
| GET | `messaging/conversations/` | — | List conversations |
| POST | `messaging/conversations/create/` | `{ participants, ... }` | Create conversation |
| GET | `messaging/conversations/<conversation_id>/messages/` | — | List messages |
| POST | `messaging/conversations/<conversation_id>/send/` | `{ text, ... }` | Send message |
| POST | `messaging/messages/<message_id>/react/` | `{ emoji }` | React to a message |
| GET | `messaging/available-users/` | — | List users available for messaging |
| GET | `messaging/notifications/` | — | Messaging notifications |
| POST | `messaging/notifications/<notification_id>/mark-sent/` | — | Mark notification sent |
| POST | `messaging/messages/<message_id>/mark-read/` | — | Mark message as read |

#### Queue Management

| Verb | Endpoint | Data | Description |
|---|---|---|---|
| GET/POST | `queue/schedules/` | `{ ... }` | Manage queue schedules |
| GET/PUT/DELETE | `queue/schedules/<schedule_id>/` | `{ ... }` | Manage a single schedule |
| GET/POST | `queue/status/` | `{ department }` | Get/update queue status |
| GET | `queue/status/logs/` | query params | Queue status logs |
| POST | `queue/daily-reset/` | `{ department }` | Reset daily queue |
| POST | `queue/join/` | `{ department, ... }` | Patient joins queue |
| GET | `queue/availability/` | query params | Queue availability |
| POST | `queue/start-processing/` | `{ department }` | Start serving next patient |
| POST | `queue/notifications/confirm/` | `{ notification_id }` | Confirm notification delivery |

#### Nurse Queue + Handoff

| Verb | Endpoint | Data | Description |
|---|---|---|---|
| GET | `nurse/queue/patients/` | query params | Nurse queue view |
| POST | `nurse/queue/remove/` | `{ ... }` | Remove patient from queue |
| POST | `nurse/queue/mark-served/` | `{ ... }` | Mark queue entry served |
| POST | `nurse/send-records/` | `{ patient_id, doctor_id, message }` | Send patient records to doctor |

#### Inventory

| Verb | Endpoint | Data | Description |
|---|---|---|---|
| GET | `medicine-inventory/` | — | List medicines |
| POST | `medicine-inventory/add/` | `{ ... }` | Add medicine item |
| PUT/PATCH | `medicine-inventory/<medicine_id>/update/` | `{ ... }` | Update medicine |
| POST | `medicine-inventory/<medicine_id>/dispense/` | `{ ... }` | Dispense medicine |
| DELETE | `medicine-inventory/<medicine_id>/delete/` | — | Delete medicine |

#### Departments / Doctors / Assignments

| Verb | Endpoint | Data | Description |
|---|---|---|---|
| GET | `available-doctors/` | query params | List doctors for assignment |
| GET | `hospital/departments/` | query params | List hospital departments/specializations |
| POST | `assign-patient/` | `{ patient_id, doctor_id }` | Assign patient to doctor |
| GET | `doctor/assignments/` | — | List doctor assignments |
| POST | `doctor/assignments/<assignment_id>/accept/` | — | Accept assignment |
| POST | `doctor/assignments/<assignment_id>/consultation-notes/` | `{ ... }` | Submit consultation notes |

#### Archives

| Verb | Endpoint | Data | Description |
|---|---|---|---|
| GET | `archives/` | query params | List archives |
| POST | `archives/create/` | `{ ... }` | Create archive |
| GET | `archives/<archive_id>/` | — | View archive details |
| PUT/PATCH | `archives/<archive_id>/update/` | `{ ... }` | Update archive |
| POST | `archives/<archive_id>/unarchive/` | — | Unarchive record |
| GET | `archives/<archive_id>/export/` | — | Export archive |
| GET | `archives/logs/` | query params | Archive access logs |

#### Monitoring / Verification

| Verb | Endpoint | Data | Description |
|---|---|---|---|
| GET | `ui-config/` | — | UI configuration |
| POST | `client-log/` | `{ level, message, ... }` | Client log ingestion |
| GET | `verification-status/` | — | Verification status |

#### Secure Transmission / MFA / Purge

| Verb | Endpoint | Data | Description |
|---|---|---|---|
| POST | `secure/register-public-key/` | `{ public_key }` | Register public key |
| GET | `secure/doctor-public-key/<doctor_id>/` | — | Get doctor public key |
| POST/GET | `secure/transmissions/` | `{ ... }` | Create/list transmissions |
| GET | `secure/transmissions/list/` | — | Transmission listing |
| GET | `secure/transmissions/<transmission_id>/` | — | Transmission detail |
| POST | `secure/transmissions/<transmission_id>/received/` | — | Mark received |
| POST | `secure/mfa/challenge/` | `{ ... }` | MFA challenge |
| POST | `secure/mfa/verify/` | `{ ... }` | MFA verify |
| POST | `secure/transmissions/<transmission_id>/breach/` | `{ ... }` | Report breach |
| POST | `secure/purge/medical-records/` | `{ ... }` | Purge records |

### 3) Analytics API (`/analytics/`)

Source: `backend/analytics/urls.py`

| Verb | Endpoint | Data | Description |
|---|---|---|---|
| GET | `/` | — | Main analytics response |
| GET | `status/<task_id>/` | — | Check async task status |
| GET | `history/` | — | Analytics history |
| POST | `refresh/` | `{ ... }` | Trigger refresh |
| GET | `realtime/` | — | Realtime analytics dashboard |
| GET | `stream/` | — | Streaming analytics |
| GET | `performance/` | — | Performance analytics |
| POST | `stress-test/` | `{ ... }` | Run stress test |
| GET | `doctor/` | — | Doctor analytics |
| GET | `nurse/` | — | Nurse analytics |
| GET | `doctor/recommendations/` | — | Doctor AI recommendations |
| GET | `nurse/recommendations/` | — | Nurse AI recommendations |
| POST | `pdf/` | `{ ... }` | Generate analytics PDF |
| GET | `events/` | — | List events |
| POST | `events/log/` | `{ ... }` | Log an event |
| POST | `uptime/ping/` | `{ ... }` | Uptime ping |
| GET | `uptime/status/` | — | Uptime status |

### 4) Admin API (`/admin/`)

Source: `backend/admin_site/urls.py`

| Verb | Endpoint | Data | Description |
|---|---|---|---|
| GET | `/` | — | Admin API overview |
| GET | `config/` | — | Admin config |
| POST | `login/` | `{ email, password }` | Admin login |
| POST | `register/` | `{ ... }` | Admin registration |
| POST | `token/refresh/` | `{ refresh }` | Refresh admin access token |
| GET | `csrf-token/` | — | CSRF token |
| POST | `verify-email/` | `{ ... }` | Verify email |
| POST | `resend-verification/` | `{ ... }` | Resend verification |
| GET | `dashboard/stats/` | — | Admin dashboard stats |
| GET | `verifications/` | query params | List verification requests |
| POST | `verifications/<verification_id>/accept/` | — | Accept verification |
| POST | `verifications/<verification_id>/decline/` | — | Decline verification |
| PUT | `verifications/<verification_id>/update/` | `{ ... }` | Update verification |
| GET | `verifications/<verification_id>/document/` | — | Get verification document |
| GET | `logs/` | — | System logs |
| POST | `hospital/register/` | `{ ... }` | Register hospital |
| POST | `hospital/activate/` | `{ ... }` | Activate hospital |
| GET | `hospital/status/` | — | Hospital status |
| GET | `hospitals/` | — | List hospitals |
| GET | `my/hospitals/` | — | List my hospitals |
| POST | `hospital/verify-selection/` | `{ ... }` | Verify selected hospital |
| GET | `settings/profile/` | — | Admin profile |
| POST | `settings/password/` | `{ ... }` | Change password |
| GET | `users/export/` | — | Export users |
| GET | `users/hospital/` | query params | Users by hospital |

### WebSocket Routes (Real-time)

Source: `backend/operations/routing.py`

| Transport | Route | Description |
|---|---|---|
| WS | `ws/messaging/<user_id>/` | Messaging updates |
| WS | `ws/queue/<department>/<user_id>/` | Queue updates per user |
| WS | `ws/queue/<department>/` | Queue updates per department |
| WS | `ws/medication/<patient_id>/` | Medication updates |
