import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import PatientQueue from '../pages/PatientQueue.vue'
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

const notify = vi.fn()
const dialog = vi.fn(() => ({ onOk: (cb: () => void) => { cb(); return { } } }))

vi.mock('quasar', () => ({
  useQuasar: () => ({
    notify,
    dialog,
    screen: { lt: { md: false } },
  }),
}))

describe('PatientQueue.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    ;(api.get as Mock).mockImplementation((url: string) => {
      if (url.includes('/operations/queue/status/')) {
        return Promise.resolve({ data: { is_open: true, department: 'OPD', status_message: '' } })
      }
      if (url.includes('/operations/patient/dashboard/summary/')) {
        return Promise.resolve({
          data: {
            nowServing: '1',
            currentPatient: 'P***',
            myPosition: '5',
            estimatedWaitMins: 30,
            progressValue: 60,
            queueEntries: [{ id: 1, name: 'You', number: '5', department: 'OPD', etaMins: 30, isMe: true }],
          },
        })
      }
      if (url.includes('/operations/ui-config/')) return Promise.resolve({ data: {} })
      return Promise.resolve({ data: {} })
    })

    ;(api.post as Mock).mockImplementation((url: string) => {
      if (url.includes('/operations/queue/leave/')) return Promise.resolve({ data: { success: true, removed: true } })
      return Promise.resolve({ data: {} })
    })
  })

  it('confirms and leaves the queue via API, then refreshes state', async () => {
    const wrapper = mount(PatientQueue, {
      global: {
        stubs: {
          PatientBottomNav: true,
          'q-layout': { template: '<div><slot /></div>' },
          'q-header': { template: '<header><slot /></header>' },
          'q-toolbar': { template: '<div><slot /></div>' },
          'q-avatar': { template: '<div><slot /></div>', props: ['icon'] },
          'q-btn': { template: `<button @click="$emit('click')">{{ label }}<slot /></button>`, props: ['label', 'loading', 'disable'] },
          'q-badge': { template: '<span><slot /></span>' },
          'q-menu': { template: '<div><slot /></div>' },
          'q-list': { template: '<div><slot /></div>' },
          'q-item': { template: '<div><slot /></div>' },
          'q-item-section': { template: '<div><slot /></div>' },
          'q-item-label': { template: '<div><slot /></div>' },
          'q-icon': { template: '<i />' },
          'q-space': { template: '<span />' },
          'q-page-container': { template: '<div><slot /></div>' },
          'q-page': { template: '<div><slot /></div>' },
          'q-card': { template: '<div><slot /></div>' },
          'q-card-section': { template: '<div><slot /></div>' },
          'q-card-actions': { template: '<div><slot /></div>' },
          'q-banner': { template: '<div><slot /></div>' },
          'q-select': { template: '<select />' },
          'q-option-group': { template: '<div />' },
          'q-slide-transition': { template: '<div><slot /></div>' },
          'q-dialog': { template: '<div><slot /></div>' },
          'q-knob': { template: '<div />' },
          'q-spinner-dots': { template: '<div />' },
          'q-spinner-hourglass': { template: '<div />' },
          'q-chip': { template: '<div />' },
        },
      },
    })

    await flushPromises()
    expect(wrapper.text()).toContain('Leave Queue')

    const btn = wrapper.findAll('button').find((b) => b.text().includes('Leave Queue'))
    expect(btn).toBeTruthy()
    await (btn as NonNullable<typeof btn>).trigger('click')
    await flushPromises()

    expect(dialog).toHaveBeenCalled()
    expect(((api as unknown as Record<string, unknown>)['post'] as Mock)).toHaveBeenCalledWith('/operations/queue/leave/', { department: 'OPD' })
    expect(notify).toHaveBeenCalled()
  })

  it('shows Join Queue when the user was previously marked no_show', async () => {
    ;(api.get as Mock).mockImplementation((url: string) => {
      if (url.includes('/operations/queue/status/')) {
        return Promise.resolve({ data: { is_open: true, department: 'OPD', status_message: '' } })
      }
      if (url.includes('/operations/patient/dashboard/summary/')) {
        return Promise.resolve({
          data: {
            nowServing: '1',
            currentPatient: 'P***',
            myPosition: 'No Show',
            myQueueNumber: 12,
            myQueueStatus: 'no_show',
            estimatedWaitMins: 0,
            progressValue: 0,
            queueEntries: [],
          },
        })
      }
      if (url.includes('/operations/ui-config/')) return Promise.resolve({ data: {} })
      return Promise.resolve({ data: {} })
    })

    const wrapper = mount(PatientQueue, {
      global: {
        stubs: {
          PatientBottomNav: true,
          'q-layout': { template: '<div><slot /></div>' },
          'q-header': { template: '<header><slot /></header>' },
          'q-toolbar': { template: '<div><slot /></div>' },
          'q-avatar': { template: '<div><slot /></div>', props: ['icon'] },
          'q-btn': { template: `<button @click="$emit('click')">{{ label }}<slot /></button>`, props: ['label', 'loading', 'disable'] },
          'q-badge': { template: '<span><slot /></span>' },
          'q-menu': { template: '<div><slot /></div>' },
          'q-list': { template: '<div><slot /></div>' },
          'q-item': { template: '<div><slot /></div>' },
          'q-item-section': { template: '<div><slot /></div>' },
          'q-item-label': { template: '<div><slot /></div>' },
          'q-icon': { template: '<i />' },
          'q-space': { template: '<span />' },
          'q-page-container': { template: '<div><slot /></div>' },
          'q-page': { template: '<div><slot /></div>' },
          'q-card': { template: '<div><slot /></div>' },
          'q-card-section': { template: '<div><slot /></div>' },
          'q-card-actions': { template: '<div><slot /></div>' },
          'q-banner': { template: '<div><slot /></div>' },
          'q-select': { template: '<select />' },
          'q-option-group': { template: '<div />' },
          'q-slide-transition': { template: '<div><slot /></div>' },
          'q-dialog': { template: '<div><slot /></div>' },
          'q-knob': { template: '<div />' },
          'q-spinner-dots': { template: '<div />' },
          'q-spinner-hourglass': { template: '<div />' },
          'q-chip': { template: '<div />' },
        },
      },
    })

    await flushPromises()
    expect(wrapper.text()).toContain('Join Queue')
  })

  it('hides the grace timer when the grace window is already expired', async () => {
    const past = new Date(Date.now() - 30_000).toISOString()
    ;(api.get as Mock).mockImplementation((url: string) => {
      if (url.includes('/operations/queue/status/')) {
        return Promise.resolve({ data: { is_open: true, department: 'OPD', status_message: '' } })
      }
      if (url.includes('/operations/patient/dashboard/summary/')) {
        return Promise.resolve({
          data: {
            nowServing: '1',
            currentPatient: 'P***',
            myPosition: 'Called',
            myQueueNumber: 5,
            myQueueStatus: 'called',
            myGraceExpiresAt: past,
            estimatedWaitMins: 0,
            progressValue: 100,
            queueEntries: [],
          },
        })
      }
      if (url.includes('/operations/ui-config/')) return Promise.resolve({ data: {} })
      return Promise.resolve({ data: {} })
    })

    const wrapper = mount(PatientQueue, {
      global: {
        stubs: {
          PatientBottomNav: true,
          'q-layout': { template: '<div><slot /></div>' },
          'q-header': { template: '<header><slot /></header>' },
          'q-toolbar': { template: '<div><slot /></div>' },
          'q-avatar': { template: '<div><slot /></div>', props: ['icon'] },
          'q-btn': { template: `<button @click="$emit('click')">{{ label }}<slot /></button>`, props: ['label', 'loading', 'disable'] },
          'q-badge': { template: '<span><slot /></span>' },
          'q-menu': { template: '<div><slot /></div>' },
          'q-list': { template: '<div><slot /></div>' },
          'q-item': { template: '<div><slot /></div>' },
          'q-item-section': { template: '<div><slot /></div>' },
          'q-item-label': { template: '<div><slot /></div>' },
          'q-icon': { template: '<i />' },
          'q-space': { template: '<span />' },
          'q-page-container': { template: '<div><slot /></div>' },
          'q-page': { template: '<div><slot /></div>' },
          'q-card': { template: '<div><slot /></div>' },
          'q-card-section': { template: '<div><slot /></div>' },
          'q-card-actions': { template: '<div><slot /></div>' },
          'q-banner': { template: '<div><slot /></div>' },
          'q-select': { template: '<select />' },
          'q-option-group': { template: '<div />' },
          'q-slide-transition': { template: '<div><slot /></div>' },
          'q-dialog': { template: '<div><slot /></div>' },
          'q-knob': { template: '<div />' },
          'q-spinner-dots': { template: '<div />' },
          'q-spinner-hourglass': { template: '<div />' },
          'q-chip': { template: '<div />' },
          'q-circular-progress': { template: '<div><slot /></div>' },
        },
      },
    })

    await flushPromises()
    expect(wrapper.find('.grace-timer-wrap').exists()).toBe(false)
  })
})
