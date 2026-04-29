import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import NursePatientAssessment from '@/pages/NursePatientAssessment.vue'
import { usePatientStore } from 'src/stores/patientStore'
import { api } from 'src/boot/axios'
import { useQuasar } from 'quasar'
import { reactive } from 'vue'

// Mock dependencies
vi.mock('src/boot/axios', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    defaults: { baseURL: 'http://localhost:8000' }
  }
}))

vi.mock('quasar', () => ({
  useQuasar: vi.fn()
}))

const routeQuery = reactive<Record<string, unknown>>({})
const replaceMock = vi.fn()
vi.mock('vue-router', () => ({
  useRoute: () => ({ query: routeQuery }),
  useRouter: () => ({ replace: replaceMock, push: vi.fn() })
}))

// Mock child components
const NurseHeader = { template: '<div>Header</div>' }
const NurseSidebar = { template: '<div>Sidebar</div>' }

describe('NursePatientAssessment Registration Flow', () => {
  let notifyMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    Object.keys(routeQuery).forEach((k) => { delete routeQuery[k] })
    
    notifyMock = vi.fn()
    ;(useQuasar as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      notify: notifyMock,
      dialog: vi.fn(() => ({ onOk: vi.fn(), onCancel: vi.fn() }))
    })

    localStorage.setItem('user', JSON.stringify({
      full_name: 'Test Nurse',
      role: 'nurse',
      verification_status: 'approved',
      nurse_profile: { department: 'OPD', hospital_name: 'Test Hospital' },
      hospital_name: 'Test Hospital' // Ensure root level also has it if needed
    }))
  })

  it('initializes and validates registration form steps', async () => {
    // Mock API responses based on URL
    // eslint-disable-next-line @typescript-eslint/no-misused-promises
    (api.get as unknown as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/users/nurse/patients/')) {
        return Promise.resolve({
          data: {
            success: true,
            patients: [{
              id: 1,
              full_name: 'John Doe',
              email: 'john@example.com',
              age: 30,
              gender: 'Male',
              discharge_date: null
            }]
          }
        })
      }
      if (url.includes('/operations/notifications/')) {
        return Promise.resolve({ data: [] })
      }
      if (url.includes('/operations/availability/doctors/free/')) {
        return Promise.resolve({ data: { success: true, doctors: [] } })
      }
      if (url.includes('/users/profile/')) {
        return Promise.resolve({
          data: {
            user: {
              full_name: 'Test Nurse',
              role: 'nurse',
              verification_status: 'approved',
              hospital_name: 'Test Hospital',
              nurse_profile: { department: 'OPD', specialization: 'General' }
            }
          }
        })
      }
      return Promise.resolve({ data: {} })
    });

    // Mock other methods to return Promises
    (api.post as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ data: {} });
    (api.put as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ data: {} });
    (api.patch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ data: {} });

    const wrapper = mount(NursePatientAssessment, {
      global: {
        plugins: [createPinia()],
        components: { NurseHeader, NurseSidebar },
        stubs: {
          'q-layout': { template: '<div><slot /></div>' },
          'q-page-container': { template: '<div><slot /></div>' },
          'q-dialog': { template: '<div v-if="modelValue"><slot /></div>', props: ['modelValue'] }, 
          'q-card': { template: '<div class="q-card"><slot /></div>' },
          'q-card-section': { template: '<div class="q-card-section"><slot /></div>' },
          'q-tabs': { template: '<div class="q-tabs"><slot /></div>', props: ['modelValue'] },
          'q-tab': { template: '<button @click="$emit(\'update:modelValue\', name)">{{ label }}<slot /></button>', props: ['name', 'label'] },
          'q-toolbar': { template: '<div><slot /></div>' },
          'q-toolbar-title': { template: '<div><slot /></div>' },
          'q-stepper': { template: '<div class="q-stepper"><slot /></div>' },
          'q-step': { template: '<div class="q-step"><slot /></div>' },
          'q-stepper-navigation': { template: '<div><slot /></div>' },
          'q-input': { 
            template: '<input :aria-label="label" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />', 
            props: ['modelValue', 'label', 'rules'] 
          },
          'q-select': { 
            template: '<select :aria-label="label" :value="modelValue" @change="handleChange" :multiple="multiple"><option v-for="(opt, i) in options" :key="i" :value="opt">{{ opt }}</option></select>', 
            props: ['modelValue', 'label', 'options', 'multiple'],
            methods: {
              handleChange(e: Event) {
                const target = e.target as HTMLSelectElement
                const val = this.multiple 
                  ? Array.from(target.selectedOptions).map((o) => o.value)
                  : target.value
                this.$emit('update:modelValue', val)
              }
            }
          },
          'q-option-group': {
            template: '<div class="q-option-group-stub"><div v-for="opt in options" :key="opt.value" :data-value="opt.value" @click="$emit(\'update:modelValue\', opt.value)" :class="{selected: modelValue === opt.value}">{{ opt.label }}</div></div>',
            props: ['modelValue', 'options']
          },
          'q-btn': { template: '<button @click="$emit(\'click\')">{{ label }}<slot /></button>', props: ['label'] },
          'q-slide-transition': { template: '<div><slot /></div>' },
          'q-separator': true,
          'q-icon': true,
          'q-avatar': true,
          'q-badge': true,
          'q-banner': true,
          'q-spinner': true,
          'q-list': true,
          'q-item': true,
          'q-item-section': true,
          'q-item-label': true,
          'q-chip': true,
          'q-pagination': true,
          'q-tooltip': true,
          'q-space': true,
          'q-inner-loading': true,
          'q-checkbox': true,
          'q-slider': true,
          'q-toggle': true,
        }
      }
    })

    // Wait for initial load
    await flushPromises()
    
    // Select a patient
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(wrapper.vm as any).selectPatient({
      id: 1,
      full_name: 'John Doe',
      email: 'john@example.com',
      age: 30,
      gender: 'Male',
      discharge_date: null
    })
    
    await wrapper.vm.$nextTick()

    // Open the registration dialog explicitly for this test flow
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(wrapper.vm as any).openRegistration()
    await wrapper.vm.$nextTick()

    // Helper to find input by aria-label
    const findInput = (label: string) => wrapper.findAll('input').find(i => i.attributes('aria-label') === label)
    
    // Helper to click button by label
    const clickBtn = async (label: string) => {
      const btns = wrapper.findAll('button')
      const btn = btns.find(b => b.text().includes(label))
      if (btn) await btn.trigger('click')
      else throw new Error(`Button with label "${label}" not found`)
    }

    // Step 1: Hospital & Basic Contact Details
    const hospitalNameInput = findInput('Hospital Name')
    expect(hospitalNameInput).toBeDefined()
    
    // Fill Step 1
    if (hospitalNameInput) await hospitalNameInput.setValue('Test Hospital')
    const hospAddr = findInput('Hospital Address')
    if (hospAddr) await hospAddr.setValue('123 Street')

    // Click Continue
    await clickBtn('Continue')
    await wrapper.vm.$nextTick()

    // Step 2: Patient Information
    const mrn = findInput('Patient ID / MRN')
    if (mrn) await mrn.setValue('MRN-123')
    
    const firstNameInput = findInput('First Name')
    if (firstNameInput) await firstNameInput.setValue('Jane')
    const lastName = findInput('Last Name')
    if (lastName) await lastName.setValue('Doe')
    const dob = findInput('Date of Birth')
    if (dob) await dob.setValue('1999-01-01')
    const age = findInput('Age')
    if (age) await age.setValue('25')

    const selects = wrapper.findAll('select')
    const sexSelect = selects.find(s => s.attributes('aria-label') === 'Gender')
    if (sexSelect) await sexSelect.setValue('Female')
    const maritalSelect = selects.find(s => s.attributes('aria-label') === 'Marital Status')
    if (maritalSelect) await maritalSelect.setValue('Single')
    
    const cellPhone = findInput('Phone Number')
    if (cellPhone) await cellPhone.setValue('0912-345-6789')
    const homeAddress = findInput('Home Address')
    if (homeAddress) await homeAddress.setValue('456 Lane')
    
    // Click Continue
    await clickBtn('Continue')
    await wrapper.vm.$nextTick()
    
    // Step 3: Emergency Contact
    const emName = findInput('Emergency Contact Name')
    if (emName) await emName.setValue('Mom')
    
    const selects2 = wrapper.findAll('select')
    const relSelect = selects2.find(s => s.attributes('aria-label') === 'Emergency Relationship')
    if (relSelect) await relSelect.setValue('Parent')
    const emPhone = findInput('Emergency Phone')
    if (emPhone) await emPhone.setValue('0911-111-1111')
    
    // Click Continue
    await clickBtn('Continue')
    await wrapper.vm.$nextTick()
    
    // Step 4: Medical History
    await clickBtn('Continue')
    await wrapper.vm.$nextTick()
    
    // Step 5: Authorization
    const signature = findInput('Patient/Guardian Signature')
    if (signature) await signature.setValue('Jane Doe')
    
    // Click Finish
    await clickBtn('Finish & Submit')
    
    // Verify success notification
    expect(notifyMock).toHaveBeenCalledWith(expect.objectContaining({
      type: 'positive',
      message: 'Patient registration saved'
    }))
  })

  it('blocks assessment until registration is completed', async () => {
    const wrapper = mount(NursePatientAssessment, {
      global: {
        plugins: [createPinia()],
        components: { NurseHeader, NurseSidebar },
        stubs: {
          'q-layout': { template: '<div><slot /></div>' },
          'q-page-container': { template: '<div><slot /></div>' },
          'q-dialog': { template: '<div v-if="modelValue"><slot /></div>', props: ['modelValue'] },
          'q-card': { template: '<div class="q-card"><slot /></div>' },
          'q-card-section': { template: '<div class="q-card-section"><slot /></div>' },
          'q-tabs': { template: '<div class="q-tabs"><slot /></div>', props: ['modelValue'] },
          'q-tab': { template: '<button @click="$emit(\'update:modelValue\', name)">{{ label }}<slot /></button>', props: ['name', 'label'] },
          'q-toolbar': { template: '<div><slot /></div>' },
          'q-toolbar-title': { template: '<div><slot /></div>' },
          'q-stepper': { template: '<div class="q-stepper"><slot /></div>' },
          'q-step': { template: '<div class="q-step"><slot /></div>' },
          'q-stepper-navigation': { template: '<div><slot /></div>' },
          'q-input': { template: '<input />' },
          'q-select': { template: '<select />' },
          'q-option-group': { template: '<div />' },
          'q-btn': { template: '<button @click="$emit(\'click\')">{{ label }}<slot /></button>', props: ['label'] },
          'q-slide-transition': { template: '<div><slot /></div>' },
          'q-separator': true,
          'q-icon': true,
          'q-avatar': true,
          'q-badge': true,
          'q-banner': true,
          'q-spinner': true,
          'q-list': true,
          'q-item': true,
          'q-item-section': true,
          'q-item-label': true,
          'q-chip': true,
          'q-pagination': true,
          'q-tooltip': true,
          'q-space': true,
          'q-inner-loading': true,
          'q-checkbox': true,
          'q-slider': true,
          'q-toggle': true,
        },
      },
    })

    await flushPromises()

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(wrapper.vm as any).selectPatient({ id: 1, full_name: 'John Doe' })
    await wrapper.vm.$nextTick()

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(wrapper.vm as any).openAssessmentGuarded()
    await wrapper.vm.$nextTick()

    expect(notifyMock).toHaveBeenCalledWith(expect.objectContaining({
      type: 'warning',
      message: 'Complete registration first before assessment'
    }))
  })

  it('propagates patient data from store to local state', async () => {
    setActivePinia(createPinia())
    const patientStore = usePatientStore()
    
    // Setup mock data in store
    const mockPatient = {
      id: 999,
      user_id: 999,
      full_name: 'Store Patient',
      email: 'store@test.com',
      age: 45,
      gender: 'Male',
      blood_type: 'O+',
      medical_condition: 'Flu',
      hospital: 'Test Hospital',
      insurance_provider: 'Test Ins',
      billing_amount: 100,
      room_number: '101',
      admission_type: 'Emergency',
      date_of_admission: '2024-01-01',
      discharge_date: null,
      medication: 'None',
      test_results: 'None',
      assigned_doctor: null,
      is_dummy: false
    }
    patientStore.setCurrentPatient(mockPatient)

    const wrapper = mount(NursePatientAssessment, {
      global: {
        plugins: [createPinia()], // Note: this creates a new pinia, we might need to share the instance or mock the store
        components: { NurseHeader, NurseSidebar },
        stubs: {
            'q-layout': { template: '<div><slot /></div>' },
            'q-page-container': { template: '<div><slot /></div>' },
            'q-dialog': { template: '<div v-if="modelValue"><slot /></div>', props: ['modelValue'] }, 
            'q-card': { template: '<div class="q-card"><slot /></div>' },
            'q-card-section': { template: '<div class="q-card-section"><slot /></div>' },
            'q-tabs': { template: '<div class="q-tabs"><slot /></div>', props: ['modelValue'] },
            'q-tab': { template: '<button @click="$emit(\'update:modelValue\', name)">{{ label }}<slot /></button>', props: ['name', 'label'] },
            'q-toolbar': { template: '<div><slot /></div>' },
            'q-toolbar-title': { template: '<div><slot /></div>' },
            'q-stepper': { template: '<div class="q-stepper"><slot /></div>' },
            'q-step': { template: '<div class="q-step"><slot /></div>' },
            'q-stepper-navigation': { template: '<div><slot /></div>' },
            'q-input': { template: '<div></div>' },
            'q-select': { template: '<div></div>' },
            'q-option-group': { template: '<div></div>' },
            'q-btn': { template: '<button @click="$emit(\'click\')">{{ label }}<slot /></button>', props: ['label'] },
            'q-slide-transition': { template: '<div><slot /></div>' },
            'q-separator': true,
            'q-icon': true,
            'q-avatar': true,
            'q-badge': true,
            'q-banner': true,
            'q-spinner': true,
            'q-list': true,
            'q-item': true,
            'q-item-section': true,
            'q-item-label': true,
            'q-chip': true,
            'q-tooltip': true,
            'q-space': true,
            'q-inner-loading': true,
            'q-checkbox': true,
            'q-slider': true,
            'q-toggle': true,
        }
      }
    })
    
    // Inject the store with data into the component's context
    // Actually, since we passed createPinia() to global.plugins, that instance is used.
    // We should pre-fill localStorage because the component calls patientStore.loadFromStorage()
    // or we can mock the store.
    // The component calls loadFromStorage() then reads currentPatient.
    // Let's rely on localStorage mocking which we cleared in beforeEach.
    
    localStorage.setItem('current_serving_patient', JSON.stringify(mockPatient))
    
    // Trigger loadPatients which calls prefillFromCurrentServing
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    await (wrapper.vm as any).loadPatients()
    
    // Verify selectedPatient matches
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const selected = (wrapper.vm as any).selectedPatient
    expect(selected).toBeDefined()
    expect(selected.id).toBe(999)
    expect(selected.full_name).toBe('Store Patient')
  })

  it('validates patient data from store before propagating', async () => {
    // Setup invalid data in localStorage
    const invalidPatient = {
      // Missing id and user_id
      full_name: 'Invalid Patient',
      age: 45
    }
    localStorage.setItem('current_serving_patient', JSON.stringify(invalidPatient))
    
    // Mock console.warn to verify it's called
    const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

    const wrapper = mount(NursePatientAssessment, {
      global: {
        plugins: [createPinia()],
        components: { NurseHeader, NurseSidebar },
        stubs: {
          'q-layout': { template: '<div><slot /></div>' },
          'q-page-container': { template: '<div><slot /></div>' },
          'q-dialog': true,
          'q-card': true,
          'q-card-section': true,
          'q-tabs': true,
          'q-tab': true,
          'q-toolbar': true,
          'q-toolbar-title': true,
          'q-stepper': true,
          'q-step': true,
          'q-stepper-navigation': true,
          'q-input': true,
          'q-select': true,
          'q-option-group': true,
          'q-btn': true,
          'q-slide-transition': true,
          'q-separator': true,
          'q-icon': true,
          'q-avatar': true,
          'q-badge': true,
          'q-banner': true,
          'q-spinner': true,
          'q-list': true,
          'q-item': true,
          'q-item-section': true,
          'q-item-label': true,
          'q-chip': true,
          'q-pagination': true,
          'q-tooltip': true,
          'q-space': true,
          'q-inner-loading': true,
          'q-checkbox': true,
          'q-slider': true,
          'q-toggle': true,
        }
      }
    })

    // Trigger loadPatients which calls prefillFromCurrentServing
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    await (wrapper.vm as any).loadPatients()
    
    // Verify warning was logged
    expect(consoleSpy).toHaveBeenCalledWith('Invalid patient data from store:', expect.objectContaining(invalidPatient))
    
    // Verify selectedPatient is NOT set (or remains null)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const selected = (wrapper.vm as any).selectedPatient
    expect(selected).toBeNull()
    
    consoleSpy.mockRestore()
  })

  it('prioritizes currently-being-assessed patient at the top of the list', async () => {
    // eslint-disable-next-line @typescript-eslint/no-misused-promises
    ;(api.get as unknown as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/users/nurse/patients/')) {
        return Promise.resolve({
          data: {
            success: true,
            patients: [
              {
                id: 1,
                user_id: 1,
                full_name: 'Alice Zebra',
                email: 'alice@example.com',
                age: 30,
                gender: 'Female',
                discharge_date: null,
              },
              {
                id: 2,
                user_id: 2,
                full_name: 'Bob Alpha',
                email: 'bob@example.com',
                age: 40,
                gender: 'Male',
                discharge_date: null,
              },
            ],
          },
        })
      }
      if (url.includes('/operations/notifications/')) return Promise.resolve({ data: [] })
      if (url.includes('/operations/availability/doctors/free/')) return Promise.resolve({ data: { success: true, doctors: [] } })
      if (url.includes('/users/profile/')) {
        return Promise.resolve({
          data: {
            user: {
              full_name: 'Test Nurse',
              role: 'nurse',
              verification_status: 'approved',
              hospital_name: 'Test Hospital',
              nurse_profile: { department: 'OPD', specialization: 'General' },
            },
          },
        })
      }
      return Promise.resolve({ data: {} })
    })

    const pinia = createPinia()
    setActivePinia(pinia)
    const store = usePatientStore()
    store.setCurrentPatient({ id: 2, user_id: 2, full_name: 'Bob Alpha' })

    const wrapper = mount(NursePatientAssessment, {
      global: {
        plugins: [pinia],
        components: { NurseHeader, NurseSidebar },
        stubs: {
          'q-layout': { template: '<div><slot /></div>' },
          'q-page-container': { template: '<div><slot /></div>' },
          'q-dialog': { template: '<div><slot /></div>' },
          'q-card': { template: '<div class="q-card"><slot /></div>' },
          'q-card-section': { template: '<div class="q-card-section"><slot /></div>' },
          'q-tabs': { template: '<div class="q-tabs"><slot /></div>', props: ['modelValue'] },
          'q-tab': { template: '<button @click="$emit(\'update:modelValue\', name)">{{ label }}<slot /></button>', props: ['name', 'label'] },
          'q-toolbar': { template: '<div><slot /></div>' },
          'q-toolbar-title': { template: '<div><slot /></div>' },
          'q-stepper': { template: '<div class="q-stepper"><slot /></div>' },
          'q-step': { template: '<div class="q-step"><slot /></div>' },
          'q-stepper-navigation': { template: '<div><slot /></div>' },
          'q-input': { template: '<input />' },
          'q-select': { template: '<select />' },
          'q-option-group': { template: '<div />' },
          'q-btn': { template: '<button />' },
          'q-slide-transition': { template: '<div><slot /></div>' },
          'q-separator': true,
          'q-icon': true,
          'q-avatar': true,
          'q-badge': true,
          'q-banner': true,
          'q-spinner': true,
          'q-list': true,
          'q-item': true,
          'q-item-section': true,
          'q-item-label': true,
          'q-chip': true,
          'q-pagination': true,
          'q-tooltip': true,
          'q-space': true,
          'q-inner-loading': true,
          'q-checkbox': true,
          'q-slider': true,
          'q-toggle': true,
        },
      },
    })

    await flushPromises()

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const list = (wrapper.vm as any).filteredPatients as Array<{ full_name: string }>
    expect(list[0]?.full_name).toBe('Bob Alpha')
  })

  it('loads archives when opened in archive view via route query', async () => {
    routeQuery.view = 'archive'

    // eslint-disable-next-line @typescript-eslint/no-misused-promises
    ;(api.get as unknown as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/users/nurse/patients/')) return Promise.resolve({ data: { success: true, patients: [] } })
      if (url.includes('/operations/notifications/')) return Promise.resolve({ data: [] })
      if (url.includes('/operations/availability/doctors/free/')) return Promise.resolve({ data: { success: true, doctors: [] } })
      if (url.includes('/users/profile/')) {
        return Promise.resolve({
          data: {
            user: {
              full_name: 'Test Nurse',
              role: 'nurse',
              verification_status: 'approved',
              hospital_name: 'Test Hospital',
              nurse_profile: { department: 'OPD', specialization: 'General' },
            },
          },
        })
      }
      if (url.includes('/operations/archives/')) {
        return Promise.resolve({
          data: [
            {
              id: 99,
              patient_id: 1,
              patient_name: 'John Doe',
              assessment_type: 'General',
              medical_condition: 'Flu',
              hospital_name: 'Test Hospital',
              created_at: '2026-01-01T00:00:00Z',
              is_archived: true,
              decrypted_assessment_data: {},
            },
          ],
        })
      }
      return Promise.resolve({ data: {} })
    })

    const wrapper = mount(NursePatientAssessment, {
      global: {
        plugins: [createPinia()],
        components: { NurseHeader, NurseSidebar },
        stubs: {
          'q-layout': { template: '<div><slot /></div>' },
          'q-page-container': { template: '<div><slot /></div>' },
          'q-dialog': { template: '<div><slot /></div>' },
          'q-card': { template: '<div class="q-card"><slot /></div>' },
          'q-card-section': { template: '<div class="q-card-section"><slot /></div>' },
          'q-tabs': { template: '<div class="q-tabs"><slot /></div>', props: ['modelValue'] },
          'q-tab': { template: '<button>{{ label }}<slot /></button>', props: ['name', 'label'] },
          'q-toolbar': { template: '<div><slot /></div>' },
          'q-toolbar-title': { template: '<div><slot /></div>' },
          'q-stepper': { template: '<div class="q-stepper"><slot /></div>' },
          'q-step': { template: '<div class="q-step"><slot /></div>' },
          'q-stepper-navigation': { template: '<div><slot /></div>' },
          'q-input': { template: '<input />' },
          'q-select': { template: '<select />' },
          'q-option-group': { template: '<div />' },
          'q-btn': { template: '<button />' },
          'q-slide-transition': { template: '<div><slot /></div>' },
          'q-separator': true,
          'q-icon': true,
          'q-avatar': true,
          'q-badge': true,
          'q-banner': true,
          'q-spinner': true,
          'q-list': true,
          'q-item': true,
          'q-item-section': true,
          'q-item-label': true,
          'q-chip': true,
          'q-pagination': true,
          'q-tooltip': true,
          'q-space': true,
          'q-inner-loading': true,
          'q-checkbox': true,
          'q-slider': true,
          'q-toggle': true,
        },
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Patient Archive')
    const getMock = (api as unknown as Record<string, unknown>)['get'] as ReturnType<typeof vi.fn>
    expect(getMock).toHaveBeenCalledWith('/operations/archives/', expect.any(Object))
  })
})
