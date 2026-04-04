import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import NurseQueueManagement from '@/pages/NurseQueueManagement.vue'
import { api } from 'src/boot/axios'
import { useQuasar } from 'quasar'

vi.mock('src/boot/axios', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    defaults: { baseURL: 'http://localhost:8000/api' }
  }
}))

vi.mock('quasar', () => ({
  useQuasar: vi.fn()
}))

class MockWebSocket {
  url: string
  onopen: (() => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  onclose: (() => void) | null = null
  constructor(url: string) {
    this.url = url
  }
  close() {}
}

describe('NurseQueueManagement (Automated)', () => {
  let notifyMock: ReturnType<typeof vi.fn>
  const apiMock = api as unknown as {
    get: ReturnType<typeof vi.fn>
    post: ReturnType<typeof vi.fn>
    defaults: { baseURL: string }
  }

  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    setActivePinia(createPinia())

    notifyMock = vi.fn()
    ;(useQuasar as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      notify: notifyMock
    })

    ;(globalThis as unknown as { WebSocket: typeof WebSocket }).WebSocket = MockWebSocket as unknown as typeof WebSocket

    localStorage.setItem(
      'user',
      JSON.stringify({
        full_name: 'Test Nurse',
        role: 'nurse',
        nurse_profile: { department: 'OPD' }
      }),
    )

    apiMock.get.mockImplementation((url: string) => {
      if (url.startsWith('/operations/queue/status/')) {
        return { data: { department: 'OPD', is_open: true } }
      }
      if (url === '/operations/nurse/queue/patients/') {
        return { data: { normal_queue: [], priority_queue: [] } }
      }
      return { data: {} }
    })
    apiMock.post.mockImplementation((url: string) => {
      if (url === '/operations/queue/daily-reset/') {
        return { data: { message: 'ok' } }
      }
      return { data: { is_open: true } }
    })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('auto-opens the queue on mount (no manual controls)', async () => {
    const wrapper = mount(NurseQueueManagement, {
      global: {
        plugins: [createPinia()],
        stubs: {
          'q-layout': { template: '<div><slot /></div>' },
          'q-page': { template: '<div><slot /></div>' },
          'q-card': { template: '<div><slot /></div>' },
          'q-card-section': { template: '<div><slot /></div>' },
          'q-separator': { template: '<div />' },
          'q-list': { template: '<div><slot /></div>' },
          'q-item': { template: '<div><slot /></div>' },
          'q-item-section': { template: '<div><slot /></div>' },
          'q-item-label': { template: '<div><slot /></div>' },
          'q-icon': { template: '<i />' },
          'q-space': { template: '<span />' },
          'q-badge': { props: ['label'], template: '<span>{{ label }}</span>' },
          'q-btn': { props: ['label'], template: '<button>{{ label }}</button>' },
          'q-dialog': { template: '<div><slot /></div>' },
          'q-avatar': { template: '<div><slot /></div>' },
          'q-banner': { template: '<div><slot /></div>' }
        }
      }
    })

    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith('/operations/queue/status/', { department: 'OPD', is_open: true })
    expect(wrapper.text()).not.toContain('Open Queue')
    expect(wrapper.text()).not.toContain('Close Queue')
    expect(wrapper.text()).not.toContain('Refresh')
    expect(wrapper.text()).not.toContain('Manage Queue')
  })

  it('schedules a daily reset/open at 00:01', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2026, 2, 30, 0, 0, 30))

    mount(NurseQueueManagement, {
      global: {
        plugins: [createPinia()],
        stubs: {
          'q-layout': { template: '<div><slot /></div>' },
          'q-page': { template: '<div><slot /></div>' },
          'q-card': { template: '<div><slot /></div>' },
          'q-card-section': { template: '<div><slot /></div>' },
          'q-separator': { template: '<div />' },
          'q-list': { template: '<div><slot /></div>' },
          'q-item': { template: '<div><slot /></div>' },
          'q-item-section': { template: '<div><slot /></div>' },
          'q-item-label': { template: '<div><slot /></div>' },
          'q-icon': { template: '<i />' },
          'q-space': { template: '<span />' },
          'q-badge': { props: ['label'], template: '<span>{{ label }}</span>' },
          'q-btn': { props: ['label'], template: '<button>{{ label }}</button>' },
          'q-dialog': { template: '<div><slot /></div>' },
          'q-avatar': { template: '<div><slot /></div>' },
          'q-banner': { template: '<div><slot /></div>' }
        }
      }
    })

    await flushPromises()
    apiMock.post.mockClear()

    await vi.advanceTimersByTimeAsync(31_000)
    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith('/operations/queue/daily-reset/', { department: 'OPD' })
    expect(apiMock.post).toHaveBeenCalledWith('/operations/queue/status/', { department: 'OPD', is_open: true })
  })
})
