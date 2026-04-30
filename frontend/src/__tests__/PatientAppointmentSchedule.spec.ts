import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import PatientAppointmentSchedule from '../pages/PatientAppointmentSchedule.vue'
import { api } from '../boot/axios'

vi.mock('../boot/axios', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    defaults: { baseURL: 'http://localhost:8000' },
  },
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('quasar', () => ({
  useQuasar: () => ({
    notify: vi.fn(),
    screen: { lt: { md: false } },
  }),
}))

describe('PatientAppointmentSchedule.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    ;(api.get as Mock).mockImplementation((url: string) => {
      if (url.includes('/operations/notifications/')) return Promise.resolve({ data: { results: [] } })
      if (url.includes('/operations/hospital/departments/')) return Promise.resolve({ data: { departments: [] } })
      if (url.includes('/operations/patient/appointments/')) {
        return Promise.resolve({
          data: {
            results: [
              {
                appointment_id: 1,
                id: 1,
                patient_name: 'Patient',
                doctor_name: 'Dr A',
                doctor_id: 10,
                department: 'General',
                appointment_date: '2026-01-01T09:00:00Z',
                appointment_time: '09:00:00',
                status: 'scheduled',
                appointment_type: 'consultation',
                type: 'consultation',
                reason: 'Checkup',
              },
            ],
          },
        })
      }
      return Promise.resolve({ data: {} })
    })
  })

  it('renders appointment type and department from API results', async () => {
    const wrapper = mount(PatientAppointmentSchedule, {
      global: {
        stubs: {
          PatientBottomNav: true,
          'q-layout': { template: '<div><slot /></div>' },
          'q-header': { template: '<header><slot /></header>' },
          'q-toolbar': { template: '<div><slot /></div>' },
          'q-avatar': { template: '<div><slot /></div>', props: ['icon'] },
          'q-btn': { template: '<button><slot /></button>' },
          'q-badge': { template: '<span><slot /></span>' },
          'q-menu': { template: '<div><slot /></div>' },
          'q-list': { template: '<div><slot /></div>' },
          'q-item': { template: '<div><slot /></div>' },
          'q-item-section': { template: '<div><slot /></div>' },
          'q-icon': { template: '<i />' },
          'q-space': { template: '<span />' },
          'q-page-container': { template: '<div><slot /></div>' },
          'q-page': { template: '<div><slot /></div>' },
          'q-card': { template: '<div><slot /></div>' },
          'q-card-section': { template: '<div><slot /></div>' },
          'q-card-actions': { template: '<div><slot /></div>' },
          'q-tabs': { template: '<div><slot /></div>' },
          'q-tab': { template: '<div />' },
          'q-tab-panels': { template: '<div><slot /></div>' },
          'q-tab-panel': { template: '<div><slot /></div>' },
          'q-separator': { template: '<hr />' },
          'q-input': { template: '<input />' },
          'q-select': { template: '<select />' },
          'q-dialog': { template: '<div><slot /></div>' },
          'q-form': { template: '<form><slot /></form>' },
          'q-popup-proxy': { template: '<div><slot /></div>' },
          'q-date': { template: '<div><slot /></div>' },
          'q-time': { template: '<div><slot /></div>' },
        },
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('General')
    expect(wrapper.text()).toContain('General Consultation')
  })
})

