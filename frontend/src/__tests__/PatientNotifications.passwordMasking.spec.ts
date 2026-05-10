import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import PatientNotifications from '../pages/PatientNotifications.vue'
import { api } from '../boot/axios'

vi.mock('../boot/axios', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    defaults: { baseURL: 'http://localhost:8000' },
  },
}))

const notify = vi.fn()

vi.mock('quasar', async () => {
  const actual = await vi.importActual<Record<string, unknown>>('quasar')
  return {
    ...actual,
    useQuasar: () => ({
      notify,
      screen: { lt: { md: false } },
      platform: { is: { mobile: false } },
      dark: { set: vi.fn() },
    }),
    copyToClipboard: vi.fn().mockResolvedValue(undefined),
  }
})

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

const stubs = {
  MsToastHost: true,
  PatientBottomNav: true,
  'q-layout': { template: '<div><slot /></div>' },
  'q-header': { template: '<div><slot /></div>' },
  'q-toolbar': { template: '<div><slot /></div>' },
  'q-page-container': { template: '<div><slot /></div>' },
  'q-page': { template: '<div><slot /></div>' },
  'q-card': { template: '<div><slot /></div>' },
  'q-card-section': { template: '<div><slot /></div>' },
  'q-card-actions': { template: '<div><slot /></div>' },
  'q-separator': { template: '<hr />' },
  'q-space': { template: '<span />' },
  'q-avatar': { template: '<div><slot /></div>' },
  'q-menu': { template: '<div><slot /></div>' },
  'q-list': { template: '<div><slot /></div>' },
  'q-item': { template: '<div><slot /></div>' },
  'q-item-section': { template: '<div><slot /></div>' },
  'q-item-label': { template: '<div><slot /></div>' },
  'q-dialog': { template: '<div><slot /></div>' },
  'q-scroll-area': { template: '<div><slot /></div>' },
  'q-chip': { template: '<div><slot /></div>' },
  'q-icon': { template: '<i />' },
  'q-badge': { template: '<span><slot /></span>' },
  'q-input': { template: '<input />' },
  'q-toggle': { template: '<input type="checkbox" />' },
  'q-tooltip': { template: '<span />' },
  'q-btn': {
    template: `<button v-bind="$attrs" :data-icon="icon" @click="$emit('click')"><slot />{{ label }}</button>`,
    props: ['label', 'icon', 'loading', 'dense', 'round', 'flat', 'color', 'outline'],
  },
}

describe('PatientNotifications.vue (password masking)', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-05-09T00:00:00.000Z'))
    vi.clearAllMocks()
  })

  it('keeps password masked unless explicitly copied', async () => {
    ;(api.get as Mock).mockImplementation((url: string) => {
      if (String(url).includes('/operations/medical-record-transfers/')) {
        return Promise.resolve({ data: { password: 'super-secret' } })
      }
      return Promise.resolve({ data: { results: [] } })
    })

    const wrapper = mount(PatientNotifications, { global: { stubs } })
    ;(wrapper.vm as unknown as { selectedNotification: unknown }).selectedNotification = {
      id: 1,
      title: 'Notification',
      message: 'Your encrypted document password is available.',
      type: 'medical',
      read: true,
      createdAt: new Date().toISOString(),
      extra_data: { transfer_id: 999, document_number: 'MC-2026.pdf' },
    }
    ;(wrapper.vm as unknown as { showNotificationDetail: boolean }).showNotificationDetail = true

    expect((wrapper.vm as unknown as { maskedPassword: string }).maskedPassword).toBe('••••••••')

    await (wrapper.vm as unknown as { copyDocumentPassword: () => Promise<void> }).copyDocumentPassword()
    await flushPromises()

    expect((wrapper.vm as unknown as { maskedPassword: string }).maskedPassword).toBe('super-secret')

    vi.advanceTimersByTime(9000)
    await flushPromises()
    expect((wrapper.vm as unknown as { maskedPassword: string }).maskedPassword).toBe('••••••••')
  })

  it('maps notification extra_data and renders details in Type -> Date -> Status -> Password order', async () => {
    ;(api.get as Mock).mockResolvedValue({
      data: {
        results: [
          {
            id: 10,
            message: 'An encrypted medical certificate (MCERT-20260510-AAAAAA.pdf) was sent to your email. The password is available in MediSync.',
            is_read: true,
            created_at: '2026-05-10T00:00:00.000Z',
            extra_data: { transfer_id: 321, document_number: 'MCERT-20260510-AAAAAA' },
          },
        ],
      },
    })
    ;(api.patch as Mock).mockResolvedValue({ data: {} })

    const wrapper = mount(PatientNotifications, { global: { stubs } })
    await flushPromises()

    const vm = wrapper.vm as unknown as {
      notifications: Array<{
        id: number
        title: string
        message: string
        type: string
        read: boolean
        createdAt: string
        extra_data?: { transfer_id?: number; document_number?: string }
      }>
      selectedNotification: unknown
      showNotificationDetail: boolean
      passwordSource: unknown
    }

    expect(vm.notifications.length).toBe(1)
    vm.selectedNotification = vm.notifications[0]
    vm.showNotificationDetail = true

    expect(vm.passwordSource).toEqual({ kind: 'transfer', id: 321 })

    const text = wrapper.text()
    const iType = text.indexOf('Type')
    const iDate = text.indexOf('Date')
    const iStatus = text.indexOf('Status')
    const iPassword = text.indexOf('Password')
    expect(iType).toBeGreaterThanOrEqual(0)
    expect(iDate).toBeGreaterThan(iType)
    expect(iStatus).toBeGreaterThan(iDate)
    expect(iPassword).toBeGreaterThan(iStatus)
  })
})
