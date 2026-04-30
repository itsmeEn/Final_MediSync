import { describe, it, expect, vi, beforeEach, afterEach, type Mock } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import DoctorPatientManagement from '../pages/DoctorPatientManagement.vue'
import { api } from '../boot/axios'

vi.mock('../boot/axios', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    defaults: { baseURL: 'http://localhost:8000' },
  },
  optimizeEndpoint: vi.fn().mockResolvedValue(undefined),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ query: {} }),
}))

const notify = vi.fn()

vi.mock('quasar', () => ({
  useQuasar: () => ({
    notify,
    screen: { lt: { md: false } },
    platform: { is: { mobile: false } },
  }),
}))

class FakeWebSocket {
  url: string
  onmessage: ((evt: MessageEvent) => void) | null = null
  onclose: (() => void) | null = null
  constructor(url: string) {
    this.url = url
  }
  close(): void {
    // no-op
  }
}

const stubs = {
  DoctorHeader: true,
  DoctorSidebar: true,
  'q-layout': { template: '<div><slot /></div>' },
  'q-page-container': { template: '<div><slot /></div>' },
  'q-card': { template: '<div><slot /></div>' },
  'q-card-section': { template: '<div><slot /></div>' },
  'q-card-actions': { template: '<div><slot /></div>' },
  'q-separator': { template: '<hr />' },
  'q-space': { template: '<span />' },
  'q-chip': { template: '<div><slot /></div>' },
  'q-spinner': { template: '<div />' },
  'q-avatar': { template: '<div><slot /></div>' },
  'q-dialog': { template: '<div><slot /></div>' },
  'q-banner': { template: '<div><slot /></div>' },
  'q-input': { template: '<input />' },
  'q-select': { template: '<select />' },
  'q-icon': { template: '<i />' },
  'q-tooltip': { template: '<span />' },
  'q-pagination': { template: '<div />' },
  'q-btn': { template: `<button @click="$emit('click')"><slot />{{ label }}</button>`, props: ['label', 'loading', 'disable', 'icon', 'flat', 'dense', 'size', 'color', 'unelevated', 'outline', 'round'] },
}

describe('DoctorPatientManagement.vue (medical requests consultation notes)', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
    ;(globalThis as unknown as { WebSocket: unknown }).WebSocket = FakeWebSocket as unknown
    ;(api.post as Mock).mockResolvedValue({ data: {} })
    ;(api.patch as Mock).mockResolvedValue({ data: {} })

    ;(api.get as Mock).mockImplementation((url: string) => {
      if (url.includes('/users/profile/')) {
        return Promise.resolve({
          data: { user: { id: 99, full_name: 'Dr Test', role: 'doctor', verification_status: 'approved', doctor_profile: { specialization: 'General' } } },
        })
      }
      if (url.includes('/operations/notifications/')) return Promise.resolve({ data: [] })
      if (url.includes('/operations/doctor/assignments/')) return Promise.resolve({ data: [] })
      if (url.includes('/operations/archives/')) return Promise.resolve({ data: [] })
      if (url.includes('/operations/availability/nurses/')) return Promise.resolve({ data: { nurses: [], checked_at: '2026-04-30T00:00:00Z' } })
      if (url.includes('/operations/medical-requests/doctor/')) {
        return Promise.resolve({
          data: {
            results: [
              {
                id: 1,
                created_at: '2026-04-30T00:00:00Z',
                requested: ['Medical Certificate'],
                patient_profile_id: 10,
                patient_name: 'Patient One',
                patient_id: 'P-1',
                patient_email: 'patient1@example.com',
                patient_message: '',
                assignment_id: 123,
                consultation_notes: {
                  id: 55,
                  status: 'completed',
                  created_at: '2026-04-29T00:00:00Z',
                  updated_at: '2026-04-29T01:00:00Z',
                  completed_at: '2026-04-29T01:00:00Z',
                  chief_complaint: 'Headache',
                  history_of_present_illness: 'Two days',
                  physical_examination: 'Normal',
                  diagnosis: 'Migraine',
                  treatment_plan: 'Rest',
                  medications_prescribed: 'Paracetamol',
                  follow_up_instructions: 'Return if worse',
                  additional_notes: '',
                },
              },
            ],
          },
        })
      }
      return Promise.resolve({ data: {} })
    })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders consultation notes returned alongside medical requests', async () => {
    const wrapper = mount(DoctorPatientManagement, { global: { stubs } })
    await flushPromises()
    expect(wrapper.text()).toContain('Medical Requests')
    expect(wrapper.text()).toContain('Consultation Notes')
    expect(wrapper.text()).toContain('Diagnosis:')
    expect(wrapper.text()).toContain('Migraine')
    expect(wrapper.text()).toContain('Treatment:')
    expect(wrapper.text()).toContain('Rest')
  })
})
