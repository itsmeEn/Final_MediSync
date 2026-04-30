import { describe, it, expect, vi, beforeEach, afterEach, type Mock } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import PatientDashboard from '../pages/PatientDashboard.vue'
import { api } from '../boot/axios'

vi.mock('../boot/axios', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    defaults: { baseURL: 'http://localhost:8000' },
  },
  optimizeEndpoint: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('../stores/appointments', () => ({
  useAppointmentsStore: () => ({
    nextAppointment: null,
    lastAppointment: null,
    loadAppointments: vi.fn().mockResolvedValue(undefined),
  }),
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
  PatientBottomNav: true,
  'q-layout': { template: '<div><slot /></div>' },
  'q-header': { template: '<header><slot /></header>' },
  'q-toolbar': { template: '<div><slot /></div>' },
  'q-avatar': { template: '<div><slot /></div>' },
  'q-btn': { template: `<button @click="$emit('click')"><slot />{{ label }}</button>`, props: ['label', 'loading', 'disable', 'icon'] },
  'q-badge': { template: '<span><slot /></span>' },
  'q-menu': { template: '<div><slot /></div>' },
  'q-list': { template: '<div><slot /></div>' },
  'q-item': { template: '<div><slot /></div>' },
  'q-item-section': { template: '<div><slot /></div>' },
  'q-item-label': { template: '<div><slot /></div>' },
  'q-separator': { template: '<hr />' },
  'q-tooltip': { template: '<span />' },
  'q-space': { template: '<span />' },
  'q-page-container': { template: '<div><slot /></div>' },
  'q-page': { template: '<div><slot /></div>' },
  'q-chip': { template: '<div><slot /></div>' },
  'q-card': { template: '<div><slot /></div>' },
  'q-card-section': { template: '<div><slot /></div>' },
  'q-card-actions': { template: '<div><slot /></div>' },
  'q-icon': { template: '<i />' },
  'q-img': { template: '<img />' },
  'q-dialog': { template: '<div><slot /></div>' },
  'q-input': { template: '<input />' },
  'q-checkbox': { template: '<input type="checkbox" />' },
  'q-banner': { template: '<div><slot /></div>' },
  'q-select': { template: '<select />' },
}

describe('PatientDashboard.vue (medical request doctor details)', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
    localStorage.setItem('user', JSON.stringify({ id: 1, full_name: 'Test Patient', email: 'patient@example.com' }))
    ;(globalThis as unknown as { WebSocket: unknown }).WebSocket = FakeWebSocket as unknown

    ;(api.get as Mock).mockImplementation((url: string) => {
      if (url.includes('/operations/patient/dashboard/summary/')) {
        return Promise.resolve({ data: { nowServing: '', currentPatient: '', myPosition: '', estimatedWaitMins: 0, queueEntries: [] } })
      }
      if (url.includes('/operations/medical-requests/patient/')) {
        return Promise.resolve({
          data: {
            results: [
              {
                id: 1,
                status: 'pending',
                requested: ['Prescription'],
                created_at: '2026-04-30T00:00:00Z',
                doctor: {
                  id: 10,
                  name: 'Dr Alpha',
                  specialty: 'Cardiology',
                  contact: { email: 'alpha@example.com', hospital_name: 'H', hospital_address: 'A' },
                  availability: { available_for_consultation: true },
                },
              },
              {
                id: 2,
                status: 'pending',
                requested: ['Medical Certificate'],
                created_at: '2026-04-30T00:00:00Z',
                doctor: null,
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

  it('renders assigned doctor info and fallback for unassigned', async () => {
    const wrapper = mount(PatientDashboard, { global: { stubs } })
    await flushPromises()
    expect(wrapper.text()).toContain('Medical Requests')
    expect(wrapper.text()).toContain('Dr. Dr Alpha')
    expect(wrapper.text()).toContain('Cardiology')
    expect(wrapper.text()).toContain('alpha@example.com')
    expect(wrapper.text()).toContain('Unassigned')
  })
})

