## Psychiatric OPD Questionnaire — UI Modernization

### Scope
- Target: Psychiatric OPD Questionnaire inside [NursePatientAssessment.vue](file:///Users/judeibardaloza/Desktop/Final_MediSync/frontend/src/pages/NursePatientAssessment.vue)
- Goal: Improve usability, accessibility, and clinician workflow without changing clinical content.

### Clinical Content Integrity
- Question text, section numbering, and ordering remain unchanged.
- No scoring algorithms or diagnostic thresholds were modified (the form is a data-capture instrument in the current implementation).

### Accessibility (WCAG 2.1 AA-Oriented Improvements)
- Screen reader live status for autosave state (polite announcements).
- High contrast toggle for improved readability.
- Adjustable font sizing via in-form slider.
- All interactive controls are standard Quasar inputs with keyboard navigation support.
- Additional explicit `aria-label` attributes added for the new UI controls.

### Workflow Improvements
- Autosave enabled with debounce (700ms) while editing the form.
- Drafts are loaded automatically when “Psychiatric OPD Questionnaire” is selected for a patient.
- Manual actions remain available: Save Draft and Save & Submit.

### Data Security / HIPAA Alignment
- Draft persistence moved from browser `localStorage` (PHI risk) to encrypted server-side storage.
- Backend stores the payload encrypted at rest using a Fernet key derived from `MESSAGE_ENCRYPTION_KEY`.
- Server endpoints require authenticated nurse role and verified account status.

### Backend API
- GET/PUT draft:
  - `/users/nurse/patient/<patient_id>/psychiatric-opd/`
- Submit:
  - `/users/nurse/patient/<patient_id>/psychiatric-opd/submit/`

### Storage Model
- Backend model: `PsychiatricOpdQuestionnaire` (operations app)
  - Encrypted payload field plus integrity hash.

### Comparison Testing Guidance
- Compare questionnaire outputs by loading the same patient and validating that each field maps identically pre/post UI changes.
- For regression, verify:
  - Same patient data inputs produce the same saved payload JSON structure.
  - Autosave does not change field values.
