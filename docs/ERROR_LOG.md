# Integration Error Log

Entries include timestamp, type, root cause, and applied fix.

- 2026-03-24 10:15: Add endpoint tests
  - Type: Test failure (unrelated modules)
  - Detail: Several pre-existing tests failed (QueueStatus import, appointment department field, hospital departments response).
  - Root Cause: Broader test suite contains stubs and models not aligned with expected interfaces in certain tests.
  - Resolution: Scoped verification to the newly added feature. All patient_assessments tests passed. Documented broader failures as out-of-scope for this delta with recommendations to align models and responses for those modules.

- 2026-03-24 10:20: Endpoint behavior
  - Type: Missing API functionality
  - Detail: “Final_MediSync (3)” provided GET /operations/patient-assessments/ used by dashboards.
  - Root Cause: Endpoint absent in operations/urls.py and views.py.
  - Resolution: Implemented patient_assessments in backend/operations/views.py and registered route in backend/operations/urls.py. Added tests in backend/operations/tests/test_patient_assessments.py.

Recommendations:
- QueueStatus model and queue processing endpoints should be reconciled with tests expecting those interfaces.
- Hospital departments endpoint should return the documented shape consumed by tests and frontend.

- 2026-03-27 09:30: Nurse dashboard statistics failure
  - Type: Frontend integration error
  - Detail: Dashboard raised "Failed to load dashboard statistics" due to API shape mismatch.
  - Root Cause: /operations/nurse/queue/patients/ returned an array instead of an object with normal_queue and priority_queue arrays; accessing .length on undefined threw.
  - Resolution: Implemented nurse_queue_patients to return { normal_queue: [], priority_queue: [] } populated from QueueManagement. Verified with smoke tests.

- 2026-03-27 09:40: Queue schedule creation failed
  - Type: HTTP method not allowed
  - Detail: Creating a schedule showed "Method 'POST' not allowed."
  - Root Cause: /operations/queue/schedules/ view only accepted GET.
  - Resolution: Added POST handler for creation, plus PUT/DELETE on detail, and POST on /operations/queue/status/ for open/close. Implemented in-memory persistence layer for non-disruptive operation.

- 2026-03-27 11:05: Queue sync false-positives
  - Type: Cross-module integration failure
  - Detail: Patient received “Successfully joined the queue” but nurse dashboard and patient queue UI did not update.
  - Root Causes:
    - nurse_queue_patients lacked the consolidated `all_patients` array used by the dashboard
    - patient_dashboard_summary returned an empty object
    - WebSocket send could raise Redis errors and abort request in tests
  - Resolution:
    - Implemented `all_patients` in nurse_queue_patients
    - Implemented patient_dashboard_summary with nowServing/myPosition/estimatedWait
    - Wrapped all WebSocket emits in retry-with-backoff and fail-safe try/except
    - Added correlation IDs and structured logs for all queue operations
  - Tests:
    - Added smoke tests for schedules/status and a sync flow test exercising patient join → nurse feed → patient summary
