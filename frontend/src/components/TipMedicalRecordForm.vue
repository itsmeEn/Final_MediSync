<template>
  <div class="tip-form-root" :class="{ readonly }">
    <div class="tip-header">
      <div class="tip-header-left">
        <div class="facility-name">{{ facilityName }}</div>
      </div>
      <div class="tip-header-right">
        <div class="revision">Latest revision: {{ revisionDate }}</div>
      </div>
    </div>

    <div v-if="mode === 'registration' || mode === 'both'" class="tip-section">
      <div class="tip-section-title">REGISTRATION</div>

      <div class="tip-grid">
        <div class="tip-field">
          <div class="tip-label">Surname</div>
          <q-input v-model="local.registration.surname" dense outlined :readonly="readonly" aria-label="Surname" />
        </div>
        <div class="tip-field">
          <div class="tip-label">First Name</div>
          <q-input v-model="local.registration.first_name" dense outlined :readonly="readonly" aria-label="First Name" />
        </div>
        <div class="tip-field">
          <div class="tip-label">Middle Name</div>
          <q-input v-model="local.registration.middle_name" dense outlined :readonly="readonly" aria-label="Middle Name" />
        </div>
        <div class="tip-field">
          <div class="tip-label">Age</div>
          <q-input v-model.number="local.registration.age" type="number" dense outlined :readonly="readonly" aria-label="Age" />
        </div>
        <div class="tip-field">
          <div class="tip-label">Birthday</div>
          <q-input v-model="local.registration.birthday" type="date" dense outlined :readonly="readonly" aria-label="Birthday" />
        </div>
        <div class="tip-field">
          <div class="tip-label">Sex</div>
          <q-select
            v-model="local.registration.sex"
            :options="['Male', 'Female', 'Other']"
            dense
            outlined
            :readonly="readonly"
            :disable="readonly"
            aria-label="Sex"
          />
        </div>
        <div class="tip-field">
          <div class="tip-label">Civil Status</div>
          <q-select
            v-model="local.registration.civil_status"
            :options="['Single', 'Married', 'Divorced', 'Widowed', 'Separated']"
            dense
            outlined
            :readonly="readonly"
            :disable="readonly"
            aria-label="Civil Status"
          />
        </div>
        <div class="tip-field span-2">
          <div class="tip-label">Address</div>
          <q-input v-model="local.registration.address" dense outlined :readonly="readonly" aria-label="Address" />
        </div>
        <div class="tip-field">
          <div class="tip-label">Contact No.</div>
          <q-input v-model="local.registration.contact_no" dense outlined :readonly="readonly" aria-label="Contact Number" />
        </div>
        <div class="tip-field">
          <div class="tip-label">Patient ID</div>
          <q-input v-model="local.registration.patient_id" dense outlined readonly disable aria-label="Patient ID" />
        </div>
        <div class="tip-field">
          <div class="tip-label">Nationality</div>
          <q-input v-model="local.registration.nationality" dense outlined :readonly="readonly" aria-label="Nationality" />
        </div>
        <div class="tip-field">
          <div class="tip-label">Religion</div>
          <q-input v-model="local.registration.religion" dense outlined :readonly="readonly" aria-label="Religion" />
        </div>
      </div>

      <div class="tip-subsection">
        <div class="tip-subtitle">Emergency Contact</div>
        <div class="tip-grid">
          <div class="tip-field">
            <div class="tip-label">Name</div>
            <q-input v-model="local.registration.emergency_contact.name" dense outlined :readonly="readonly" aria-label="Emergency Contact Name" />
          </div>
          <div class="tip-field">
            <div class="tip-label">Relationship</div>
            <q-input v-model="local.registration.emergency_contact.relationship" dense outlined :readonly="readonly" aria-label="Emergency Contact Relationship" />
          </div>
          <div class="tip-field">
            <div class="tip-label">Contact No.</div>
            <q-input v-model="local.registration.emergency_contact.contact_no" dense outlined :readonly="readonly" aria-label="Emergency Contact Number" />
          </div>
        </div>
      </div>
    </div>

    <div v-if="mode === 'assessment' || mode === 'both'" class="tip-section">
      <div class="tip-section-title">ASSESSMENT</div>

      <div class="assessment-grid">
        <div class="assessment-center">
          <div class="center-title">COMPLAINTS/P.E. FINDINGS</div>

          <q-input
            v-model="local.opd_assessment.complaints_pe_findings"
            type="textarea"
            autogrow
            outlined
            :readonly="readonly"
            aria-label="Complaints and Physical Exam Findings"
            class="notes-area"
          />

          <div class="boxed">
            <div class="boxed-title">VITAL SIGNS</div>
            <div class="vitals-row">
              <div class="vital">
                <div class="tip-label">BP</div>
                <q-input v-model="local.opd_assessment.vitals.bp" dense outlined :readonly="readonly" aria-label="BP" />
              </div>
              <div class="vital">
                <div class="tip-label">PR</div>
                <q-input v-model.number="local.opd_assessment.vitals.pr" type="number" dense outlined :readonly="readonly" aria-label="PR" />
              </div>
              <div class="vital">
                <div class="tip-label">RR</div>
                <q-input v-model.number="local.opd_assessment.vitals.rr" type="number" dense outlined :readonly="readonly" aria-label="RR" />
              </div>
              <div class="vital">
                <div class="tip-label">TEMP</div>
                <q-input v-model.number="local.opd_assessment.vitals.temp" type="number" dense outlined :readonly="readonly" aria-label="TEMP" />
              </div>
            </div>
          </div>

          <div class="boxed">
            <div class="boxed-title">PHYSICAL EXAMINATION</div>
            <div class="pe-grid">
              <div class="pe-field">
                <div class="tip-label">HEENT</div>
                <q-input v-model="local.opd_assessment.physical_exam.heent" dense outlined :readonly="readonly" aria-label="HEENT" />
              </div>
              <div class="pe-field">
                <div class="tip-label">HEART</div>
                <q-input v-model="local.opd_assessment.physical_exam.heart" dense outlined :readonly="readonly" aria-label="HEART" />
              </div>
              <div class="pe-field">
                <div class="tip-label">LUNGS</div>
                <q-input v-model="local.opd_assessment.physical_exam.lungs" dense outlined :readonly="readonly" aria-label="LUNGS" />
              </div>
              <div class="pe-field span-2">
                <div class="tip-label">ABDOMEN/EXTREMITIES</div>
                <q-input v-model="local.opd_assessment.physical_exam.abdomen_extremities" dense outlined :readonly="readonly" aria-label="Abdomen and Extremities" />
              </div>
            </div>
          </div>

          <div class="boxed">
            <div class="boxed-title">LABORATORY WORKUPS</div>
            <div class="labs-grid">
              <div v-for="item in labItems" :key="item.key" class="lab-row">
                <q-checkbox
                  v-model="local.opd_assessment.labs[item.key].checked"
                  :disable="readonly"
                  :aria-label="`${item.label} checkbox`"
                />
                <div class="lab-label">{{ item.label }}</div>
                <q-input
                  v-model="local.opd_assessment.labs[item.key].result"
                  dense
                  outlined
                  :readonly="readonly"
                  aria-label="Laboratory result"
                  placeholder="Result / Remarks"
                />
              </div>
            </div>
          </div>

          <div class="bottom-grid">
            <div class="bottom-field">
              <div class="tip-label">DATE</div>
              <q-input v-model="local.opd_assessment.date" type="date" dense outlined :readonly="readonly" aria-label="Date" />
            </div>
            <div class="bottom-field span-2">
              <div class="tip-label">DIAGNOSIS/TREATMENT/REMARKS</div>
              <q-input
                v-model="local.opd_assessment.diagnosis_treatment_remarks"
                type="textarea"
                autogrow
                dense
                outlined
                :readonly="readonly"
                aria-label="Diagnosis Treatment Remarks"
              />
            </div>
            <div class="bottom-field">
              <div class="tip-label">STAFF</div>
              <q-select
                v-model="local.opd_assessment.staff"
                :options="staffOptions"
                dense
                outlined
                use-input
                new-value-mode="add-unique"
                :readonly="readonly"
                :disable="readonly"
                aria-label="Staff"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

type LabKey =
  | 'cbc'
  | 'urinalysis'
  | 'fecalysis'
  | 'cxr'
  | 'ishihara'
  | 'audio'
  | 'psychological_exam'
  | 'drug_test'
  | 'hbsag'

type TipRegistration = {
  surname: string
  first_name: string
  middle_name: string
  age: number | null
  birthday: string
  sex: string
  civil_status: string
  address: string
  contact_no: string
  patient_id: string
  department: string
  nationality: string
  religion: string
  emergency_contact: { name: string; relationship: string; contact_no: string }
}

type TipAssessment = {
  complaints_pe_findings: string
  vitals: { bp: string; pr: number | null; rr: number | null; temp: number | null }
  physical_exam: { heent: string; heart: string; lungs: string; abdomen_extremities: string }
  labs: Record<LabKey, { checked: boolean; result: string }>
  date: string
  diagnosis_treatment_remarks: string
  staff: string
}

type TipFormModel = {
  registration: TipRegistration
  opd_assessment: TipAssessment
}

const props = withDefaults(
  defineProps<{
    modelValue: Partial<TipFormModel>
    mode: 'registration' | 'assessment' | 'both'
    facilityName: string
    revisionDate: string
    staffOptions: string[]
    readonly?: boolean
  }>(),
  {
    readonly: false
  }
)

const emit = defineEmits<{
  (e: 'update:modelValue', v: TipFormModel): void
}>()

const buildDefault = (v: Partial<TipFormModel>): TipFormModel => {
  const labs = ((): Record<LabKey, { checked: boolean; result: string }> => {
    const base: Record<LabKey, { checked: boolean; result: string }> = {
      cbc: { checked: false, result: '' },
      urinalysis: { checked: false, result: '' },
      fecalysis: { checked: false, result: '' },
      cxr: { checked: false, result: '' },
      ishihara: { checked: false, result: '' },
      audio: { checked: false, result: '' },
      psychological_exam: { checked: false, result: '' },
      drug_test: { checked: false, result: '' },
      hbsag: { checked: false, result: '' }
    }

    const incoming = v.opd_assessment?.labs ?? ({} as Record<string, unknown>)
    for (const k of Object.keys(base) as LabKey[]) {
      const item = incoming[k] as { checked?: unknown; result?: unknown } | undefined
      if (item && typeof item === 'object') {
        base[k] = {
          checked: !!item.checked,
          result: typeof item.result === 'string' ? item.result : ''
        }
      }
    }
    return base
  })()

  return {
    registration: {
      surname: v.registration?.surname ?? '',
      first_name: v.registration?.first_name ?? '',
      middle_name: v.registration?.middle_name ?? '',
      age: typeof v.registration?.age === 'number' ? v.registration?.age : null,
      birthday: v.registration?.birthday ?? '',
      sex: v.registration?.sex ?? '',
      civil_status: v.registration?.civil_status ?? '',
      address: v.registration?.address ?? '',
      contact_no: v.registration?.contact_no ?? '',
      patient_id: v.registration?.patient_id ?? '',
      department: v.registration?.department ?? '',
      nationality: v.registration?.nationality ?? '',
      religion: v.registration?.religion ?? '',
      emergency_contact: {
        name: v.registration?.emergency_contact?.name ?? '',
        relationship: v.registration?.emergency_contact?.relationship ?? '',
        contact_no: v.registration?.emergency_contact?.contact_no ?? ''
      }
    },
    opd_assessment: {
      complaints_pe_findings: v.opd_assessment?.complaints_pe_findings ?? '',
      vitals: {
        bp: v.opd_assessment?.vitals?.bp ?? '',
        pr: typeof v.opd_assessment?.vitals?.pr === 'number' ? v.opd_assessment?.vitals?.pr : null,
        rr: typeof v.opd_assessment?.vitals?.rr === 'number' ? v.opd_assessment?.vitals?.rr : null,
        temp: typeof v.opd_assessment?.vitals?.temp === 'number' ? v.opd_assessment?.vitals?.temp : null
      },
      physical_exam: {
        heent: v.opd_assessment?.physical_exam?.heent ?? '',
        heart: v.opd_assessment?.physical_exam?.heart ?? '',
        lungs: v.opd_assessment?.physical_exam?.lungs ?? '',
        abdomen_extremities: v.opd_assessment?.physical_exam?.abdomen_extremities ?? ''
      },
      labs,
      date: v.opd_assessment?.date ?? '',
      diagnosis_treatment_remarks: v.opd_assessment?.diagnosis_treatment_remarks ?? '',
      staff: v.opd_assessment?.staff ?? ''
    }
  }
}

const local = ref<TipFormModel>(buildDefault(props.modelValue || {}))
const syncingFromProps = ref(false)

watch(
  () => props.modelValue,
  (v) => {
    if (v === local.value) return
    syncingFromProps.value = true
    local.value = buildDefault(v || {})
    syncingFromProps.value = false
  },
  { deep: false }
)

watch(
  local,
  (v) => {
    if (syncingFromProps.value) return
    emit('update:modelValue', v)
  },
  { deep: true }
)

const staffOptions = computed(() => props.staffOptions || [])

const labItems = [
  { key: 'cbc', label: 'CBC' },
  { key: 'urinalysis', label: 'URINALYSIS' },
  { key: 'fecalysis', label: 'FECALYSIS' },
  { key: 'cxr', label: 'CXR' },
  { key: 'ishihara', label: 'ISHIHARA' },
  { key: 'audio', label: 'AUDIO' },
  { key: 'psychological_exam', label: 'PSYCHOLOGICAL EXAM' },
  { key: 'drug_test', label: 'DRUG TEST' },
  { key: 'hbsag', label: 'HBSAG' }
] as const

const validateRegistration = (): { valid: boolean; message?: string } => {
  const r = local.value.registration || {}
  const missing: string[] = []
  if (!String(r.surname || '').trim()) missing.push('Surname')
  if (!String(r.first_name || '').trim()) missing.push('First Name')
  if (!String(r.birthday || '').trim()) missing.push('Birthday')
  if (!String(r.address || '').trim()) missing.push('Address')
  if (!String(r.contact_no || '').trim()) missing.push('Contact No.')
  if (missing.length > 0) return { valid: false, message: `Missing required fields: ${missing.join(', ')}` }
  return { valid: true }
}

const validateAssessment = (): { valid: boolean; message?: string } => {
  const a = local.value.opd_assessment || {}
  const missing: string[] = []
  if (!String(a.date || '').trim()) missing.push('Date')
  if (!String(a.staff || '').trim()) missing.push('Staff')
  if (!String(a.complaints_pe_findings || '').trim()) missing.push('Complaints/P.E. Findings')
  if (missing.length > 0) return { valid: false, message: `Missing required fields: ${missing.join(', ')}` }
  return { valid: true }
}

defineExpose({ validateRegistration, validateAssessment })
</script>

<style scoped>
.tip-form-root {
  max-width: 1200px;
  margin: 0 auto;
  background: #ffffff;
  color: #111827;
}

.tip-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  border: 1px solid #111827;
  padding: 12px 14px;
}

.facility-name {
  font-weight: 700;
  letter-spacing: 0.3px;
  text-transform: uppercase;
}

.revision {
  font-size: 12px;
  opacity: 0.85;
}

.tip-section {
  border: 1px solid #111827;
  border-top: 0;
  padding: 12px 14px 14px;
}

.tip-section-title {
  font-weight: 700;
  font-size: 13px;
  letter-spacing: 0.4px;
  margin-bottom: 10px;
}

.tip-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 12px;
}

.assessment-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.assessment-center {
  min-width: 0;
}

.center-title {
  font-weight: 700;
  text-align: center;
  font-size: 13px;
  margin-bottom: 8px;
}

.tip-field {
  min-width: 0;
}

.tip-label {
  font-size: 12px;
  opacity: 0.9;
  margin-bottom: 4px;
}

.span-2 {
  grid-column: span 2;
}

.tip-subsection {
  margin-top: 14px;
}

.tip-subtitle {
  font-weight: 600;
  font-size: 12px;
  margin-bottom: 8px;
}

.notes-area :deep(textarea) {
  min-height: 160px;
}

.boxed {
  border: 1px solid #111827;
  padding: 10px;
  margin-top: 10px;
}

.boxed-title {
  font-weight: 700;
  font-size: 12px;
  margin-bottom: 8px;
}

.vitals-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}

.vital {
  min-width: 0;
}

.pe-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 12px;
}

.pe-field {
  min-width: 0;
}

.labs-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
}

.lab-row {
  display: grid;
  grid-template-columns: 42px 140px 1fr;
  align-items: center;
  gap: 8px;
}

.lab-label {
  font-size: 12px;
  font-weight: 600;
}

.bottom-grid {
  display: grid;
  grid-template-columns: 1fr 2fr 1fr;
  gap: 10px 12px;
  margin-top: 12px;
}

.bottom-field {
  min-width: 0;
}

@media (max-width: 900px) {
  .tip-grid {
    grid-template-columns: 1fr;
  }
  .span-2 {
    grid-column: span 1;
  }
  .vitals-row {
    grid-template-columns: 1fr 1fr;
  }
  .pe-grid {
    grid-template-columns: 1fr;
  }
  .bottom-grid {
    grid-template-columns: 1fr;
  }
  .lab-row {
    grid-template-columns: 42px 1fr;
    grid-auto-rows: minmax(0, auto);
  }
  .lab-row :deep(.q-field) {
    grid-column: span 2;
  }
}
</style>
