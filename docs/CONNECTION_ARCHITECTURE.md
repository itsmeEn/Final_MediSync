## Frontend–Backend Connection Architecture

### Goals

- Reduce user-facing errors when the backend is slow/unavailable.
- Prevent cascading failures via retries + circuit breaker.
- Standardize timeouts and error formatting.
- Provide health endpoints for automated monitoring.

### Backend

#### Health Checks

- `GET /health/`
- `GET /healthz/`

Response includes `status`, per-service `checks` (database, cache), `response_time_ms`, and `request_id`.

#### Request Context & Performance Headers

Every HTTP response includes:
- `X-Request-ID`
- `X-Response-Time-ms`

Requests slower than 2000ms are logged via `medisync.performance`.

#### Database Connection Pooling (Persistent Connections)

Database connections are kept open using:
- `DB_CONN_MAX_AGE` (default 60 seconds)
- `CONN_HEALTH_CHECKS = True`

#### CORS

- Production: requires explicit `CORS_ALLOWED_ORIGINS` (comma-separated).
- Development: allows common local dev origins and mobile app origins (Capacitor/Ionic) when `DJANGO_DEBUG=true`.
- Exposed headers: `X-Request-ID`, `X-Response-Time-ms`.

### Frontend (Axios API Client)

#### Timeouts

- Standard API requests: 30 seconds
- Health checks (`/health/`, `/healthz/`): 5 seconds

#### Interceptors

Request interceptor:
- Adds `Authorization: Bearer <access_token>` when available (skips auth endpoints).
- Adds `X-Request-ID` on every request.
- Applies health-check timeout override.
- Applies circuit breaker gating for non-health requests.

Response interceptor:
- Logs slow responses using performance thresholds:
  - 200ms for critical operations (queue/appointments/login)
  - 2000ms for standard operations
- Normalizes errors and attaches a consistent payload at `error.medisync`.

#### Retry (Exponential Backoff)

- Retries are enabled for:
  - Idempotent requests (GET/HEAD/OPTIONS) on network errors, 429, 5xx, and timeouts
  - Non-idempotent requests only if explicitly opted-in with `meta.retry=true`
- Backoff uses exponential growth with jitter and caps at a max delay.

#### Circuit Breaker

- Opens after 5 consecutive outage-like failures (network/timeout/429/5xx).
- While open, requests fail fast with `code=CIRCUIT_OPEN`.
- Automatically transitions to half-open after 15 seconds, allowing one probe request to close the breaker on success.

#### Offline Request Queue (Opt-In)

Requests can be queued when offline by setting:
- `meta.queueOnOffline=true`

Queued requests are replayed when the browser regains connectivity (`online` event).

### Error Boundaries

Global Vue error handler and unhandled promise rejection handler:
- Displays a user-friendly message when the backend is unreachable.
- Sends client error logs to `/operations/client-log/` (queued when offline).

