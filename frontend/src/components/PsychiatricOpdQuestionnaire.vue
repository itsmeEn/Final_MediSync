<template>
  <div class="psych-form-container q-gutter-md">
    <div class="text-subtitle1 text-bold">{{ hospitalName }}</div>
    <div class="text-caption">Department: {{ departmentName }}</div>

    <q-toolbar class="psych-toolbar q-pa-none">
      <div class="text-caption" aria-live="polite">
        {{ autosaveLabel }}
      </div>
      <q-space />
      <div class="text-caption text-grey-7" v-if="draftSavedAt">
        Draft saved: {{ new Date(draftSavedAt).toLocaleString() }}
      </div>
    </q-toolbar>

    <q-linear-progress v-if="loadingDraft" indeterminate color="primary" aria-label="Loading psychiatric form draft" />

    <div class="q-mt-md">
      <div class="text-body2 q-mt-sm">
        To gain a more accurate understanding of your condition, we kindly ask you to answer the following questions carefully. Your information will help us develop appropriate therapy recommendations for you. Please answer the questions as they apply to you personally; there are no right or wrong answers. Of course, your information is confidential.
      </div>
      <div class="text-body2 q-mt-sm">Thank you for your cooperation.</div>
    </div>

    <div class="psych-grid psych-grid-3 q-mt-md">
      <q-input v-model="psychForm.applicantLastName" label="Last Name" outlined dense />
      <q-input v-model="psychForm.applicantFirstName" label="First Name" outlined dense />
      <q-input v-model="psychForm.dateOfBirth" label="Date of Birth" type="date" outlined dense />
    </div>
    <div class="psych-grid psych-grid-3 q-mt-sm">
      <q-input v-model.number="psychForm.age" label="Age" type="number" outlined dense />
      <q-input v-model="psychForm.streetAddress" label="Street Address" outlined dense />
      <q-input v-model="psychForm.postalCodeCity" label="Postal Code, City" outlined dense />
    </div>
    <div class="psych-grid psych-grid-2 q-mt-sm">
      <q-input v-model="psychForm.healthInsurance" label="Health Insurance" outlined dense />
      <q-checkbox v-model="psychForm.privatePhysicianInInsurance" label="Optional Services: Private Physician in Health Insurance" />
    </div>
    <div class="psych-grid psych-grid-2 q-mt-sm">
      <q-input v-model="psychForm.telephoneLandline" label="Telephone (Landline)" outlined dense />
      <q-input v-model="psychForm.telephoneMobile" label="Telephone (Mobile)" outlined dense />
    </div>
    <div class="psych-grid psych-grid-2 q-mt-sm">
      <div>
        <q-input v-model="psychForm.email" label="Email" outlined dense />
        <div class="text-caption text-grey-7 q-mt-xs">
          By providing your email address, you consent to communication via email.
        </div>
      </div>
      <div />
    </div>

    <div class="q-mt-md">
      <div class="text-subtitle2 text-bold">1.5 Problems (select all that apply)</div>
      <div class="psych-grid psych-grid-3 q-mt-sm">
        <q-checkbox
          v-for="opt in psychProblemOptions"
          :key="opt.value"
          v-model="psychForm.problemChecklist"
          :val="opt.value"
          :label="opt.label"
        />
      </div>
      <q-input v-model="psychForm.problemOther" label="Other" outlined dense class="q-mt-sm" />
    </div>

    <div class="q-mt-md">
      <div class="text-subtitle2 text-bold">1.11. What was the decisive factor for your decision to undergo psychotherapy now?</div>
      <q-input v-model="psychForm.decisiveFactorForTherapy" label="Response" type="textarea" outlined autogrow class="q-mt-sm" />
      <div class="text-body2 q-mt-sm">Did someone give the decisive impetus? If yes, who and why?</div>
      <q-option-group
        v-model="psychForm.therapyImpetus"
        type="radio"
        :options="[
          { label: 'No', value: 'no' },
          { label: 'Yes', value: 'yes' }
        ]"
        inline
      />
      <q-input
        v-if="psychForm.therapyImpetus === 'yes'"
        v-model="psychForm.therapyImpetusDetails"
        label="If yes, who and why?"
        type="textarea"
        outlined
        autogrow
        class="q-mt-sm"
      />
    </div>

    <div class="q-mt-md">
      <div class="text-subtitle2 text-bold">3.9 What is your current professional status?</div>
      <div class="text-body2 text-bold q-mt-sm">Employed:</div>
      <q-option-group v-model="psychForm.employmentStatus" type="radio" :options="employedStatusOptions" />
      <div class="text-body2 text-bold q-mt-sm">Not employed:</div>
      <q-option-group v-model="psychForm.employmentStatus" type="radio" :options="notEmployedStatusOptions" />

      <q-input
        v-if="psychForm.employmentStatus === 'employed_self_employed'"
        v-model="psychForm.selfEmployedLearnedProfession"
        label="Learned profession"
        outlined
        dense
      />
      <q-input
        v-if="psychForm.employmentStatus === 'employed_employee'"
        v-model="psychForm.employeeCurrentActivity"
        label="Current activity"
        outlined
        dense
      />
      <q-input
        v-if="psychForm.employmentStatus === 'not_employed_unemployed'"
        v-model="psychForm.unemployedSince"
        label="Unemployed since"
        outlined
        dense
      />
      <q-input
        v-if="psychForm.employmentStatus === 'not_employed_other'"
        v-model="psychForm.employmentOther"
        label="Other"
        outlined
        dense
      />
    </div>

    <div class="q-mt-lg q-gutter-md">
      <div class="text-subtitle1 text-bold">4. Current Life Situation</div>

      <div class="q-gutter-sm">
        <div class="text-subtitle2 text-bold">4.1. Do you currently have a partnership?</div>
        <q-option-group
          v-model="psychForm.partnership"
          type="radio"
          :options="[
            { label: 'No', value: 'no' },
            { label: 'Yes', value: 'yes' }
          ]"
          inline
        />
        <q-input
          v-if="psychForm.partnership === 'yes'"
          v-model="psychForm.partnershipDescribe"
          label="Yes, since when and how would you describe your partnership:"
          type="textarea"
          outlined
          autogrow
        />
      </div>

      <div class="q-gutter-sm">
        <div class="text-subtitle2 text-bold">4.2. How would you describe your friendships (do you have many friendships, few, or none)?</div>
        <q-input v-model="psychForm.friendshipsDescribe" label="Response" type="textarea" outlined autogrow />
      </div>

      <div class="q-gutter-sm">
        <div class="text-subtitle2 text-bold">4.3. How do you spend your leisure time? Do you have hobbies; if yes, which ones and how often do you engage in them?</div>
        <q-input v-model="psychForm.leisureDescribe" label="Response" type="textarea" outlined autogrow />
      </div>

      <div class="q-gutter-sm">
        <div class="text-subtitle2 text-bold">4.4. Have you ever had contact with the police (e.g., loss of driver's license)? Are there any currently pending or previous criminal proceedings against you?</div>
        <q-input v-model="psychForm.policeContact" label="Response" type="textarea" outlined autogrow />
      </div>

      <div class="q-gutter-sm">
        <div class="text-subtitle2 text-bold">4.5. How would you currently describe yourself (please use adjectives)?</div>
        <q-input v-model="psychForm.selfDescribe" label="Response" type="textarea" outlined autogrow />
      </div>

      <div class="q-gutter-sm">
        <div class="text-subtitle2 text-bold">4.6. What is positive in your life, and what are your resources?</div>
        <q-input v-model="psychForm.resources" label="Response" type="textarea" outlined autogrow />
      </div>
    </div>

    <div class="q-mt-lg q-gutter-md">
      <div class="text-subtitle1 text-bold">5. Life History Development</div>

      <div class="q-gutter-sm">
        <div class="text-subtitle2 text-bold">5.1. Family and Reference Persons</div>
        <div class="text-body2">
          The following questions relate to how you grew up, for example, the relationship with important people in your life.
        </div>
      </div>

      <div class="q-gutter-sm q-mt-md">
        <div class="text-subtitle2 text-bold">Mother:</div>
        <q-input v-model="psychForm.mother.description" label="Response" type="textarea" outlined autogrow />
        <div class="psych-grid psych-grid-3 q-mt-sm">
          <q-input v-model="psychForm.mother.ageAtBirth" label="Age at your birth" outlined dense />
          <q-input v-model="psychForm.mother.profession" label="Profession" outlined dense />
          <q-option-group
            v-model="psychForm.mother.deceased"
            type="radio"
            :options="[
              { label: 'If deceased: No', value: 'no' },
              { label: 'If deceased: Yes', value: 'yes' }
            ]"
            inline
          />
        </div>
        <div class="psych-grid psych-grid-2 q-mt-sm" v-if="psychForm.mother.deceased === 'yes'">
          <q-input v-model="psychForm.mother.deceasedYear" label="Year" outlined dense />
          <q-input v-model="psychForm.mother.deceasedCause" label="Cause of death" outlined dense />
        </div>
        <q-input v-model="psychForm.mother.psychIllnesses" label="Psychological illnesses of your mother? e.g., alcoholism, suicide attempts, depression etc.:" type="textarea" outlined autogrow class="q-mt-sm" />
        <q-input v-model="psychForm.mother.personalityDescribe" label="How would you describe your mother (please use adjectives):" type="textarea" outlined autogrow class="q-mt-sm" />
        <q-input v-model="psychForm.mother.relationshipDescribe" label="How would you describe your relationship with your mother:" type="textarea" outlined autogrow class="q-mt-sm" />
      </div>

      <div class="q-gutter-sm q-mt-lg">
        <div class="text-subtitle2 text-bold">Father:</div>
        <q-input v-model="psychForm.father.description" label="Response" type="textarea" outlined autogrow />
        <div class="psych-grid psych-grid-3 q-mt-sm">
          <q-input v-model="psychForm.father.ageAtBirth" label="Age at your birth" outlined dense />
          <q-input v-model="psychForm.father.profession" label="Profession" outlined dense />
          <q-option-group
            v-model="psychForm.father.deceased"
            type="radio"
            :options="[
              { label: 'If deceased: No', value: 'no' },
              { label: 'If deceased: Yes', value: 'yes' }
            ]"
            inline
          />
        </div>
        <div class="psych-grid psych-grid-2 q-mt-sm" v-if="psychForm.father.deceased === 'yes'">
          <q-input v-model="psychForm.father.deceasedYear" label="Year" outlined dense />
          <q-input v-model="psychForm.father.deceasedCause" label="Cause of death" outlined dense />
        </div>
        <q-input v-model="psychForm.father.psychIllnesses" label="Psychological illnesses of your father? e.g., alcoholism, suicide attempts, depression etc.:" type="textarea" outlined autogrow class="q-mt-sm" />
        <q-input v-model="psychForm.father.personalityDescribe" label="How would you describe your father (please use adjectives):" type="textarea" outlined autogrow class="q-mt-sm" />
        <q-input v-model="psychForm.father.relationshipDescribe" label="How would you describe your relationship with your father:" type="textarea" outlined autogrow class="q-mt-sm" />
      </div>

      <div class="q-gutter-sm q-mt-lg">
        <div class="text-subtitle2 text-bold">5.2. How was the relationship between the parents?</div>
        <q-input v-model="psychForm.parentalRelationship" label="Response" type="textarea" outlined autogrow />
      </div>

      <div class="q-gutter-sm q-mt-md">
        <div class="text-subtitle2 text-bold">5.3. How would you generally describe the family atmosphere?</div>
        <q-input v-model="psychForm.familyAtmosphere" label="Response" type="textarea" outlined autogrow />
      </div>
    </div>

    <q-card-actions align="between">
      <div class="text-caption text-grey-7" v-if="errorMessage">{{ errorMessage }}</div>
      <div class="row items-center q-gutter-sm">
        <q-btn flat label="Save Draft" color="primary" @click="() => void saveDraft(false)" :loading="saving" />
        <q-btn color="primary" label="Save & Submit" :loading="saving" @click="submit" />
      </div>
    </q-card-actions>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'
import type { AxiosError } from 'axios'

const props = defineProps<{
  patientId: number
  hospitalName: string
  departmentName: string
  patientFullName?: string
  patientDateOfBirth?: string
  patientAge?: number | null
}>()

type PsychLineItem = { text: string; since: string }
type PsychContact = { name: string; address: string; telephone: string; email: string }

type PsychFormState = {
  applicantLastName: string
  applicantFirstName: string
  dateOfBirth: string
  age: number | null
  streetAddress: string
  postalCodeCity: string
  healthInsurance: string
  privatePhysicianInInsurance: boolean
  telephoneLandline: string
  telephoneMobile: string
  email: string
  contact1: PsychContact
  contact2: PsychContact
  problemChecklist: string[]
  problemOther: string
  decisiveFactorForTherapy: string
  therapyImpetus: 'no' | 'yes' | ''
  therapyImpetusDetails: string
  employmentStatus:
    | 'employed_self_employed'
    | 'employed_assisting_family_member'
    | 'employed_civil_servant'
    | 'employed_employee'
    | 'employed_worker'
    | 'not_employed_self_employed'
    | 'not_employed_assisting_family_member'
    | 'not_employed_civil_servant'
    | 'not_employed_employee'
    | 'not_employed_worker'
    | 'not_employed_homemaker'
    | 'not_employed_unemployed'
    | 'not_employed_pension'
    | 'not_employed_disability_pension'
    | 'not_employed_student_school'
    | 'not_employed_other'
    | ''
  selfEmployedLearnedProfession: string
  employeeCurrentActivity: string
  unemployedSince: string
  employmentOther: string
  partnership: 'no' | 'yes' | ''
  partnershipDescribe: string
  friendshipsDescribe: string
  leisureDescribe: string
  policeContact: string
  selfDescribe: string
  resources: string
  mother: {
    description: string
    ageAtBirth: string
    profession: string
    deceased: 'no' | 'yes' | ''
    deceasedYear: string
    deceasedCause: string
    psychIllnesses: string
    personalityDescribe: string
    relationshipDescribe: string
  }
  father: {
    description: string
    ageAtBirth: string
    profession: string
    deceased: 'no' | 'yes' | ''
    deceasedYear: string
    deceasedCause: string
    psychIllnesses: string
    personalityDescribe: string
    relationshipDescribe: string
  }
  parentalRelationship: string
  familyAtmosphere: string
  complaints: [PsychLineItem, PsychLineItem, PsychLineItem]
  diagnoses: [PsychLineItem, PsychLineItem, PsychLineItem]
}

const emptyPsychForm = (): PsychFormState => ({
  applicantLastName: '',
  applicantFirstName: '',
  dateOfBirth: '',
  age: null,
  streetAddress: '',
  postalCodeCity: '',
  healthInsurance: '',
  privatePhysicianInInsurance: false,
  telephoneLandline: '',
  telephoneMobile: '',
  email: '',
  contact1: { name: '', address: '', telephone: '', email: '' },
  contact2: { name: '', address: '', telephone: '', email: '' },
  problemChecklist: [],
  problemOther: '',
  decisiveFactorForTherapy: '',
  therapyImpetus: '',
  therapyImpetusDetails: '',
  employmentStatus: '',
  selfEmployedLearnedProfession: '',
  employeeCurrentActivity: '',
  unemployedSince: '',
  employmentOther: '',
  partnership: '',
  partnershipDescribe: '',
  friendshipsDescribe: '',
  leisureDescribe: '',
  policeContact: '',
  selfDescribe: '',
  resources: '',
  mother: {
    description: '',
    ageAtBirth: '',
    profession: '',
    deceased: '',
    deceasedYear: '',
    deceasedCause: '',
    psychIllnesses: '',
    personalityDescribe: '',
    relationshipDescribe: '',
  },
  father: {
    description: '',
    ageAtBirth: '',
    profession: '',
    deceased: '',
    deceasedYear: '',
    deceasedCause: '',
    psychIllnesses: '',
    personalityDescribe: '',
    relationshipDescribe: '',
  },
  parentalRelationship: '',
  familyAtmosphere: '',
  complaints: [{ text: '', since: '' }, { text: '', since: '' }, { text: '', since: '' }],
  diagnoses: [{ text: '', since: '' }, { text: '', since: '' }, { text: '', since: '' }],
})

const $q = useQuasar()
const psychForm = reactive<PsychFormState>(emptyPsychForm())
const loadingDraft = ref(false)
const saving = ref(false)
const draftSavedAt = ref<string | null>(null)
const autosaveState = ref<'idle' | 'saving' | 'saved' | 'error'>('idle')
const errorMessage = ref('')
let autosaveTimer: ReturnType<typeof setTimeout> | null = null
let suppressAutosave = false

const employedStatusOptions = [
  { label: 'Self-employed - Learned profession', value: 'employed_self_employed' },
  { label: 'Assisting family member', value: 'employed_assisting_family_member' },
  { label: 'Civil servant', value: 'employed_civil_servant' },
  { label: 'Employee - Current activity', value: 'employed_employee' },
  { label: 'Worker', value: 'employed_worker' },
]

const notEmployedStatusOptions = [
  { label: 'Self-employed', value: 'not_employed_self_employed' },
  { label: 'Assisting family member', value: 'not_employed_assisting_family_member' },
  { label: 'Civil servant', value: 'not_employed_civil_servant' },
  { label: 'Employee', value: 'not_employed_employee' },
  { label: 'Worker', value: 'not_employed_worker' },
  { label: 'Homemaker', value: 'not_employed_homemaker' },
  { label: 'Unemployed', value: 'not_employed_unemployed' },
  { label: 'Pension (early retirement / old-age / survivor pension)', value: 'not_employed_pension' },
  { label: 'Disability pension', value: 'not_employed_disability_pension' },
  { label: 'Student / School', value: 'not_employed_student_school' },
  { label: 'Other', value: 'not_employed_other' },
]

const psychProblemOptions = [
  { label: 'Depressed mood', value: 'depressed_mood' },
  { label: 'Anxiety', value: 'anxiety' },
  { label: 'Sleep disturbance', value: 'sleep_disturbance' },
  { label: 'Trauma-related symptoms', value: 'trauma' },
  { label: 'Compulsions/obsessions', value: 'ocd' },
  { label: 'Eating-related issues', value: 'eating' },
  { label: 'Pain', value: 'pain' },
  { label: 'Social withdrawal', value: 'social_withdrawal' },
  { label: 'Concentration problems', value: 'concentration' },
]

const autosaveLabel = computed(() => {
  if (autosaveState.value === 'saving') return 'Autosave: Saving…'
  if (autosaveState.value === 'saved') return 'Autosave: Saved'
  if (autosaveState.value === 'error') return 'Autosave: Error'
  return 'Autosave: —'
})

const getApiErrorMessage = (e: unknown, fallback: string): string => {
  const ax = e as AxiosError<{ error?: unknown; detail?: unknown; message?: unknown }>
  const data = ax.response?.data
  const candidate = data?.error ?? data?.detail ?? data?.message
  if (typeof candidate === 'string' && candidate.trim().length > 0) return candidate
  return fallback
}

const computeAgeFromIsoDate = (dob: string): number | null => {
  const iso = dob.trim()
  const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (!m) return null
  const y = Number(m[1])
  const mm = Number(m[2])
  const dd = Number(m[3])
  if (!Number.isFinite(y) || !Number.isFinite(mm) || !Number.isFinite(dd)) return null
  const birth = new Date(y, mm - 1, dd)
  if (Number.isNaN(birth.getTime())) return null
  const now = new Date()
  let age = now.getFullYear() - birth.getFullYear()
  const hasHadBirthday =
    now.getMonth() > birth.getMonth() ||
    (now.getMonth() === birth.getMonth() && now.getDate() >= birth.getDate())
  if (!hasHadBirthday) age -= 1
  return age >= 0 && age <= 150 ? age : null
}

const pickIsoDate = (raw: unknown): string => {
  if (typeof raw !== 'string') return ''
  const s = raw.trim()
  if (!s) return ''
  const m = s.match(/^(\d{4}-\d{2}-\d{2})/)
  return m && typeof m[1] === 'string' ? m[1] : ''
}

const splitFullName = (full: string): { first: string; last: string } => {
  const parts = full.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return { first: '', last: '' }
  if (parts.length === 1) return { first: parts[0]!, last: '' }
  const last = parts[parts.length - 1]!
  const first = parts.slice(0, -1).join(' ')
  return { first, last }
}

const prefillBasics = (): void => {
  const full = String(props.patientFullName || '').trim()
  const dob = pickIsoDate(props.patientDateOfBirth)
  const ageFromProps = typeof props.patientAge === 'number' && Number.isFinite(props.patientAge) ? props.patientAge : null

  if (full && (!psychForm.applicantFirstName.trim() || !psychForm.applicantLastName.trim())) {
    const { first, last } = splitFullName(full)
    if (!psychForm.applicantFirstName.trim() && first) psychForm.applicantFirstName = first
    if (!psychForm.applicantLastName.trim() && last) psychForm.applicantLastName = last
  }

  if (!psychForm.dateOfBirth.trim() && dob) {
    psychForm.dateOfBirth = dob
  }

  if (psychForm.age === null) {
    if (ageFromProps !== null) {
      psychForm.age = ageFromProps
    } else if (psychForm.dateOfBirth.trim()) {
      const computed = computeAgeFromIsoDate(psychForm.dateOfBirth)
      if (computed !== null) psychForm.age = computed
    }
  }
}

const loadDraft = async () => {
  if (!props.patientId) return
  loadingDraft.value = true
  errorMessage.value = ''
  suppressAutosave = true
  try {
    const res = await api.get(`/users/doctor/patient/${props.patientId}/psychiatric-opd/`)
    const data = (res.data?.data ?? {}) as Record<string, unknown>
    Object.assign(psychForm, emptyPsychForm(), data)
    prefillBasics()
    draftSavedAt.value = res.data?.updated_at ?? null
  } catch (e) {
    errorMessage.value = getApiErrorMessage(e, 'Failed to load draft')
  } finally {
    loadingDraft.value = false
    suppressAutosave = false
  }
}

const saveDraft = async (silent: boolean) => {
  if (!props.patientId) return
  if (saving.value) return
  saving.value = true
  autosaveState.value = silent ? 'saving' : autosaveState.value
  try {
    await api.put(`/users/doctor/patient/${props.patientId}/psychiatric-opd/`, { data: psychForm })
    draftSavedAt.value = new Date().toISOString()
    autosaveState.value = silent ? 'saved' : autosaveState.value
    if (!silent) $q.notify({ type: 'positive', message: 'Draft saved' })
  } catch (e) {
    autosaveState.value = 'error'
    const msg = getApiErrorMessage(e, 'Failed to save draft')
    errorMessage.value = msg
    if (!silent) $q.notify({ type: 'negative', message: msg })
  } finally {
    saving.value = false
  }
}

const submit = async () => {
  if (!props.patientId) return
  errorMessage.value = ''
  try {
    await saveDraft(true)
    await api.post(`/users/doctor/patient/${props.patientId}/psychiatric-opd/submit/`)
    $q.notify({ type: 'positive', message: 'Questionnaire submitted' })
  } catch (e) {
    const msg = getApiErrorMessage(e, 'Failed to submit questionnaire')
    errorMessage.value = msg
    $q.notify({ type: 'negative', message: msg })
  }
}

watch(
  psychForm,
  () => {
    if (suppressAutosave) return
    if (autosaveTimer) clearTimeout(autosaveTimer)
    autosaveTimer = setTimeout(() => { void saveDraft(true) }, 700)
  },
  { deep: true },
)

watch(
  () => [props.patientId, props.patientFullName, props.patientDateOfBirth, props.patientAge] as const,
  ([pid], [prevPid]) => {
    if (!pid) return
    if (pid !== prevPid) {
      void loadDraft()
      return
    }
    suppressAutosave = true
    try {
      prefillBasics()
    } finally {
      suppressAutosave = false
    }
  },
)

onMounted(() => { void loadDraft() })
</script>

<style scoped>
.psych-form-container { font-size: 14px; }
.psych-toolbar { min-height: 42px; }
.psych-grid { display: grid; gap: 10px; }
.psych-grid-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.psych-grid-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.psych-grid-4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }
@media (max-width: 768px) {
  .psych-grid-3, .psych-grid-4 { grid-template-columns: 1fr; }
  .psych-grid-2 { grid-template-columns: 1fr; }
}
</style>
