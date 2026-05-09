import { describe, it, expect, vi, beforeEach, afterEach, type Mock } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import DoctorPatientManagement from '../pages/DoctorPatientManagement.vue'
import { canAssessPatientForUser } from '../utils/assessmentAccess'
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
  'q-dialog': { template: '<div v-if="modelValue"><slot /></div>', props: ['modelValue'] },
  'q-banner': { template: '<div><slot /></div>' },
  'q-input': { template: '<input />' },
  'q-select': { template: '<select />' },
  'q-icon': { template: '<i />' },
  'q-tooltip': { template: '<span />' },
  'q-pagination': { template: '<div />' },
  'q-btn': {
    template: `<button v-bind="$attrs" :data-icon="icon" @click="$emit('click')"><span class="btn-icon">{{ icon }}</span><slot />{{ label }}</button>`,
    props: ['label', 'loading', 'disable', 'icon', 'flat', 'dense', 'size', 'color', 'unelevated', 'outline', 'round'],
  },
}

function setWindowWidth(width: number): void {
  Object.defineProperty(window, 'innerWidth', { value: width, configurable: true })
  window.dispatchEvent(new Event('resize'))
}

describe('DoctorPatientManagement.vue (Send Medical Records button + assessment permissions)', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
    ;(globalThis as unknown as { WebSocket: unknown }).WebSocket = FakeWebSocket
    ;(api.post as Mock).mockResolvedValue({ data: {} })
    ;(api.patch as Mock).mockResolvedValue({ data: {} })

    ;(api.get as Mock).mockImplementation((url: string, config?: { params?: Record<string, unknown> }) => {
      if (url.includes('/users/profile/')) {
        return Promise.resolve({
          data: { user: { id: 99, full_name: 'Dr Test', role: 'doctor', verification_status: 'approved', doctor_profile: { specialization: 'General' } } },
        })
      }
      if (url.includes('/operations/notifications/')) return Promise.resolve({ data: [] })
      if (url.includes('/operations/archives/')) return Promise.resolve({ data: [] })
      if (url.includes('/operations/availability/nurses/')) return Promise.resolve({ data: { nurses: [], checked_at: '2026-04-30T00:00:00Z' } })
      if (url.includes('/operations/medical-requests/doctor/')) return Promise.resolve({ data: { results: [] } })
      if (url.includes('/operations/doctor/assignments/')) {
        return Promise.resolve({
          data: [
            {
              id: 10,
              patient_id: 1,
              patient_name: 'Queue Patient',
              status: 'pending',
              assigned_by_name: 'Nurse One',
              assigned_at: '2026-04-30T00:00:00Z',
              specialization_required: 'General',
              assignment_reason: 'Walk-in',
              priority: 'normal',
              accepted_at: null,
              completed_at: null,
            },
          ],
        })
      }
      if (url.includes('/operations/appointments/')) {
        const doctorParam = Number(config?.params?.doctor ?? NaN)
        if (doctorParam && doctorParam !== 99) return Promise.resolve({ data: [] })
        return Promise.resolve({
          data: [
            {
              id: 20,
              patient: { id: 2, name: 'Appointment Patient' },
              appointment_date: '2026-04-30',
              appointment_time: '09:00',
              status: 'scheduled',
            },
          ],
        })
      }

      return Promise.resolve({ data: {} })
    })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('removes button text and renders an icon-only Send Medical Records button with aria-label', async () => {
    setWindowWidth(1024)
    const wrapper = mount(DoctorPatientManagement, { global: { stubs } })
    await flushPromises()

    const sendBtn = wrapper.get('button[aria-label="Send medical records"]')
    expect(sendBtn.text().toLowerCase()).not.toContain('send medical records')
    expect(sendBtn.attributes('data-icon')).toBe('send')
  })

  it('applies responsive positioning styles across 320px–1920px viewports (no fixed/overlapping positioning)', async () => {
    setWindowWidth(320)
    const wrapper = mount(DoctorPatientManagement, { global: { stubs } })
    await flushPromises()

    const sendBtn = wrapper.get('button[aria-label="Send medical records"]')
    const style320 = String(sendBtn.attributes('style') || '')
    expect(style320).toContain('position: relative')
    expect(style320).toContain('z-index: 40')

    setWindowWidth(1920)
    await flushPromises()
    const style1920 = String(sendBtn.attributes('style') || '')
    expect(style1920).toContain('position: relative')
    expect(style1920).toContain('z-index: 20')
  })

  it('grants assessment access only to the appointment assigned doctor (denies queue-only and non-assigned users)', async () => {
    expect(
      canAssessPatientForUser(
        { id: 10, role: 'doctor' },
        { source: 'appointment', appointment_id: 123, appointment_status: 'scheduled', assigned_doctor_id: 10 },
      ),
    ).toBe(true)

    expect(
      canAssessPatientForUser(
        { id: 11, role: 'doctor' },
        { source: 'appointment', appointment_id: 123, appointment_status: 'scheduled', assigned_doctor_id: 10 },
      ),
    ).toBe(false)

    expect(
      canAssessPatientForUser(
        { id: 10, role: 'doctor' },
        { source: 'queue', assignment_id: 55 },
      ),
    ).toBe(false)
  })
})
