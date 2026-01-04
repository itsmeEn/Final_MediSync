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
    const hospPhone = findInput('Hospital Phone')
    if (hospPhone) await hospPhone.setValue('123-456-7890')
    const hospEmail = findInput('Hospital Email')
    if (hospEmail) await hospEmail.setValue('hospital@test.com')

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
    
    // Step 4: Medical Information
    const reason = findInput('Reason for Visit')
    if (reason) await reason.setValue('Checkup')
    
    // Consultation Location
    const optionGroup = wrapper.find('.q-option-group-stub')
    const inHospitalOption = optionGroup.find('[data-value="In the hospital"]')
    await inHospitalOption.trigger('click')
    
    await wrapper.vm.$nextTick()
    const physicianInput = findInput('Name of Attending Physician')
    if (physicianInput) await physicianInput.setValue('Dr Smith')

    // Click Continue
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
      message: 'Patient registration & assessment saved'
    }))
  })

  it('validates consultation fields correctly', async () => {
    // This test specifically checks the new requirements:
    // 1. Mandatory consultation location
    // 2. Conditional physician field
    // 3. Physician name validation (letters and spaces only)
    
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
            props: ['modelValue', 'label', 'rules'] 
          },
            'q-select': { template: '<div></div>' },
            'q-option-group': {
              template: '<div class="q-option-group-stub"><div v-for="opt in options" :key="opt.value" :data-value="opt.value" @click="$emit(\'update:modelValue\', opt.value)">{{ opt.label }}</div></div>',
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
            'q-tooltip': true,
            'q-space': true,
            'q-inner-loading': true,
            'q-checkbox': true,
            'q-slider': true,
            'q-toggle': true,
          }
        }
      })
  
      await flushPromises()
      
      // Select a patient to open form
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ;(wrapper.vm as any).editPatient({ id: 1, full_name: 'John Doe' })
      await wrapper.vm.$nextTick()

      const findInput = (label: string) => wrapper.findAll('input').find(i => i.attributes('aria-label') === label)
      
      // 1. Check Physician Field is hidden initially
      let physicianInput = findInput('Name of Attending Physician')
      expect(physicianInput).toBeUndefined()

      // 2. Select Consultation Location
      const optionGroup = wrapper.find('.q-option-group-stub')
      const inHospitalOption = optionGroup.find('[data-value="In the hospital"]')
      await inHospitalOption.trigger('click')
      
      await wrapper.vm.$nextTick()
      
      // 3. Check Physician Field is now visible
      physicianInput = findInput('Name of Attending Physician')
      expect(physicianInput?.exists()).toBe(true)
      
      // 4. Test validation (though logic is internal to rules prop, we can check if Step 1 is invalid with invalid input)
      // Note: testing rules directly in unit tests with q-input stub is tricky because rules are processed by Quasar.
      // But we can check the 'isStepValid' function or similar if exposed, or check that we cannot proceed.
      // The current implementation of `isStepValid` (exposed or used internally) checks for truthiness.
      
      // Let's rely on the fact that we can fill it.
      if (physicianInput) await physicianInput.setValue('Dr. Invalid 123')
      // Since we are mocking q-input, the rules prop isn't executed by the browser. 
      // However, we verified the rules array exists in the component code.
      // We can inspect the props passed to the stub.
      
      const physicianComponent = wrapper.findComponent('[aria-label="Name of Attending Physician"]')
      const rules = (physicianComponent as unknown as { props: (k: string) => unknown }).props('rules') as ((val: string) => boolean | string)[]
      
      expect(rules).toBeDefined()
      expect(rules.length).toBeGreaterThan(0)
      
      // Test the regex rule
      const regexRule = rules.find(r => typeof r === 'function' && r('123') !== true)
      expect(regexRule).toBeDefined()
      if (regexRule) {
        expect(regexRule('Dr Smith')).toBe(true) // Valid
        expect(regexRule('Dr. Smith')).toBe('Only letters and spaces allowed') // Invalid (dot)
        expect(regexRule('Dr Smith 2')).toBe('Only letters and spaces allowed') // Invalid (number)
      }
  })
})
