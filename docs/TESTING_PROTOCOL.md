# Testing Protocol

Scope validates the newly added patient assessments endpoint and guards against regressions.

- Unit tests (backend)
  - Location: backend/operations/tests
  - Run: python manage.py test --settings=backend.test_settings -v 2
  - Coverage: patient_assessments returns archives for status=completed; returns empty for status=in_progress.

- Integration tests (API)
  - Use DRF APIClient to authenticate a doctor and hit /operations/patient-assessments/ with query params.
  - Validate response shape { results: [], count: N } and record fields.

- Regression tests
  - Run entire Django test suite with test settings (in-memory SQLite).
  - Track pre-existing failures unrelated to this change; confirm new tests pass.

- Frontend smoke
  - Nurse/Doctor dashboards call /operations/patient-assessments/. With backend running, load dashboards to verify cards render.

- UAT checklist
  - As a doctor, authenticate and GET /operations/patient-assessments/?status=completed → list shows recent archives.
  - As a doctor, GET /operations/patient-assessments/?status=in_progress → empty list for now.

Notes:
- Test settings file forces SQLite in-memory DB for fast isolated runs: backend/test_settings.py.
- Frontend uses existing axios boot config and requires the backend base URL to be reachable.
