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

const makeStubs = () => ({
  PatientBottomNav: true,
  'q-layout': { template: '<div><slot /></div>' },
  'q-header': { template: '<header><slot /></header>' },
  'q-toolbar': { template: '<div><slot /></div>' },
  'q-avatar': { template: '<div><slot /></div>', props: ['icon'] },
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
})

describe('PatientDashboard.vue (queue wait reset)', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
    localStorage.setItem('user', JSON.stringify({ id: 1, full_name: 'Test Patient', email: 'patient@example.com' }))
    ;(globalThis as unknown as { WebSocket: unknown }).WebSocket = FakeWebSocket
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('recalculates estimated wait when a patient ahead is removed', async () => {
    let summaryCall = 0
    const summaries = [
      {
        nowServing: '1',
        currentPatient: 'P***',
        myPosition: '10',
        estimatedWaitMins: 120,
        queueEntries: [
          { id: 11, name: 'A***', number: '9', department: 'OPD', etaMins: 999, isMe: false },
          { id: 12, name: 'Test Patient', number: '10', department: 'OPD', etaMins: 30, isMe: true },
        ],
      },
      {
        nowServing: '1',
        currentPatient: 'P***',
        myPosition: '10',
        estimatedWaitMins: 105,
        queueEntries: [
          { id: 12, name: 'Test Patient', number: '10', department: 'OPD', etaMins: 15, isMe: true },
        ],
      },
    ]
    ;(api.get as Mock).mockImplementation((url: string) => {
      if (url.includes('/operations/patient/dashboard/summary/')) {
        const data = summaries[Math.min(summaryCall, summaries.length - 1)]
        summaryCall += 1
        return Promise.resolve({ data })
      }
      if (url.includes('/operations/medical-requests/patient/')) {
        return Promise.resolve({ data: { results: [] } })
      }
      return Promise.resolve({ data: {} })
    })

    const wrapper = mount(PatientDashboard, {
      global: {
        stubs: makeStubs(),
      },
    })

    await flushPromises()

    expect(wrapper.get('[data-testid="my-est-wait"]').text()).toContain('30 mins')

    vi.advanceTimersByTime(10000)
    await flushPromises()

    expect(wrapper.get('[data-testid="my-est-wait"]').text()).toContain('15 mins')
  })

  it('resets estimated wait to placeholder when patient is removed from the queue', async () => {
    let summaryCall = 0
    const summaries = [
      {
        nowServing: '1',
        currentPatient: 'P***',
        myPosition: '5',
        estimatedWaitMins: 60,
        queueEntries: [
          { id: 99, name: 'Test Patient', number: '5', department: 'OPD', etaMins: 15, isMe: true },
        ],
      },
      {
        nowServing: '2',
        currentPatient: 'P***',
        myPosition: '',
        estimatedWaitMins: 0,
        queueEntries: [],
      },
    ]
    ;(api.get as Mock).mockImplementation((url: string) => {
      if (url.includes('/operations/patient/dashboard/summary/')) {
        const data = summaries[Math.min(summaryCall, summaries.length - 1)]
        summaryCall += 1
        return Promise.resolve({ data })
      }
      if (url.includes('/operations/medical-requests/patient/')) {
        return Promise.resolve({ data: { results: [] } })
      }
      return Promise.resolve({ data: {} })
    })

    const wrapper = mount(PatientDashboard, {
      global: {
        stubs: makeStubs(),
      },
    })

    await flushPromises()
    expect(wrapper.get('[data-testid="my-est-wait"]').text()).toContain('15 mins')

    vi.advanceTimersByTime(10000)
    await flushPromises()

    expect(wrapper.get('[data-testid="my-est-wait"]').text()).toContain('—')
  })
})
