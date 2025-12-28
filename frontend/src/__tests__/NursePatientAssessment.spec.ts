import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import NursePatientAssessment from '@/pages/NursePatientAssessment.vue'
import { api } from 'src/boot/axios'
import { useQuasar } from 'quasar'

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

// Mock child components
const NurseHeader = { template: '<div>Header</div>' }
const NurseSidebar = { template: '<div>Sidebar</div>' }

describe('NursePatientAssessment Registration Flow', () => {
  let notifyMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    
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
          'q-toolbar': { template: '<div><slot /></div>' },
          'q-toolbar-title': { template: '<div><slot /></div>' },
          'q-stepper': { template: '<div class="q-stepper"><slot /></div>' },
          'q-step': { template: '<div class="q-step"><slot /></div>' },
          'q-stepper-navigation': { template: '<div><slot /></div>' },
          'q-input': { 
            template: '<input :aria-label="label" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />', 
            props: ['modelValue', 'label'] 
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

    // Wait for initial load
    await flushPromises()
    
    // Select a patient using editPatient to ensure selectedPatient is set
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(wrapper.vm as any).editPatient({
      id: 1,
      full_name: 'John Doe',
      email: 'john@example.com',
      age: 30,
      gender: 'Male',
      discharge_date: null
    })
    
    await wrapper.vm.$nextTick()

    // Find the inputs for registration form.
    const inputs = wrapper.findAll('input')
    
    // Helper to click button by label
    const clickBtn = async (label: string) => {
      const btns = wrapper.findAll('button')
      // Filter for visible buttons if needed, but text check usually suffices
      const btn = btns.find(b => b.text().includes(label))
      if (btn) await btn.trigger('click')
      else throw new Error(`Button with label "${label}" not found`)
    }

    // Step 1: Administrative
    const findInput = (label: string) => inputs.find(i => i.attributes('aria-label') === label)
    
    const hospitalNameInput = findInput('Hospital Name')
    expect(hospitalNameInput).toBeDefined()
    
    // Fill Step 1
    if (hospitalNameInput) await hospitalNameInput.setValue('Test Hospital')
    const hospAddr = findInput('Hospital Address')
    if (hospAddr) await hospAddr.setValue('123 Street')
    const mrn = findInput('MRN')
    if (mrn) await mrn.setValue('MRN-123')
    
    // Click Continue
    await clickBtn('Continue')
    
    // Step 2: Patient ID
    await wrapper.vm.$nextTick()
    
    const firstNameInput = findInput('First Name')
    expect(firstNameInput?.exists()).toBe(true)
    
    if (firstNameInput) await firstNameInput.setValue('Jane')
    const lastName = findInput('Last Name')
    if (lastName) await lastName.setValue('Doe')
    const age = findInput('Age')
    if (age) await age.setValue('25')
    const dob = findInput('Date of Birth')
    if (dob) await dob.setValue('1999-01-01')
    
    // Sex is a select.
    const selects = wrapper.findAll('select')
    const sexSelect = selects.find(s => s.attributes('aria-label') === 'Sex')
    if (sexSelect) await sexSelect.setValue('Female') 
    
    // Click Continue
    await clickBtn('Continue')
    
    // Step 3: Contact
    await wrapper.vm.$nextTick()
    const address = findInput('Complete Address')
    if (address) await address.setValue('456 Lane')
    const phone = findInput('Contact Number')
    if (phone) await phone.setValue('0912-345-6789')
    const email = findInput('Email Address')
    if (email) await email.setValue('jane@example.com')
    
    // Click Continue
    await clickBtn('Continue')
    
    // Step 4: Emergency & Tests
    await wrapper.vm.$nextTick()
    const emName = findInput('Emergency Contact Name')
    if (emName) await emName.setValue('Mom')
    
    const selects2 = wrapper.findAll('select')
    const relSelect = selects2.find(s => s.attributes('aria-label') === 'Emergency Relationship')
    if (relSelect) await relSelect.setValue('Parent')
    const emPhone = findInput('Emergency Phone')
    if (emPhone) await emPhone.setValue('0911-111-1111')
    
    // Medical Tests
    const testsSelect = selects2.find(s => s.attributes('aria-label') === 'Medical Tests')
    if (testsSelect) await testsSelect.setValue(['CBC']) 
    
    // Click Continue
    await clickBtn('Continue')
    
    // Step 5: Assessment
    await wrapper.vm.$nextTick()
    const symptoms = findInput('Symptoms')
    if (symptoms) await symptoms.setValue('Headache')
    
    // Click Finish
    await clickBtn('Finish & Submit')
    
    // Verify success notification
    expect(notifyMock).toHaveBeenCalledWith(expect.objectContaining({
      type: 'positive',
      message: 'Patient registration & assessment saved'
    }))
  })
})
