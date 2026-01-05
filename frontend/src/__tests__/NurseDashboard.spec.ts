import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import type { ComponentPublicInstance } from 'vue'
import { createPinia, setActivePinia, type Pinia } from 'pinia'
import NurseDashboard from '../pages/NurseDashboard.vue'
import { usePatientStore } from '../stores/patientStore'
import { api } from '../boot/axios'

// Mock dependencies
vi.mock('../boot/axios', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    defaults: { baseURL: 'http://localhost:8000' }
  }
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: vi.fn()
  })
}))

vi.mock('quasar', () => ({
  useQuasar: () => ({
    notify: vi.fn(),
    dialog: vi.fn(() => ({ onOk: vi.fn() }))
  })
}))

describe('NurseDashboard.vue', () => {
  // Define component type with exposed properties
  type NurseDashboardInstance = ComponentPublicInstance & {
    callNextPatient: () => Promise<void>
    isCallingPatient: boolean
  }

  let wrapper: VueWrapper<NurseDashboardInstance>
  let patientStore: ReturnType<typeof usePatientStore>
  let pinia: Pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    patientStore = usePatientStore()
    
    // Reset mocks
    vi.clearAllMocks()
    
    // Default API mocks
    ;(api.get as Mock).mockImplementation((url: string) => {
      if (url.includes('/users/profile/')) {
        return Promise.resolve({
          data: {
            user: {
              full_name: 'Nurse Joy',
              role: 'nurse',
              nurse_profile: { department: 'OPD' }
            }
          }
        })
      }
      if (url.includes('/operations/nurse/queue/patients/')) {
        return Promise.resolve({
          data: {
            normal_queue: [],
            priority_queue: [],
            all_patients: []
          }
        })
      }
      if (url.includes('/operations/queue/schedules/')) {
        return Promise.resolve({ data: [] })
      }
      if (url.includes('/operations/medicine-inventory/')) {
        return Promise.resolve({ data: [] })
      }
      if (url.includes('/operations/messaging/notifications/')) {
        return Promise.resolve({ data: [] })
      }
      if (url.includes('/operations/queue/status/')) {
        return Promise.resolve({ data: { is_open: true } })
      }
      return Promise.resolve({ data: {} })
    })
  })

  it('calls next patient and updates store', async () => {
    // Mock API response for call next patient
    const mockPatientProfile = {
      id: 123,
      full_name: 'John Doe',
      age: 30,
      gender: 'Male',
      department: 'OPD'
    }
    
    ;(api.post as Mock).mockResolvedValueOnce({
      data: {
        department: 'OPD',
        current_serving: '001',
        patient: { name: 'John Doe' },
        patient_profile: mockPatientProfile
      }
    })

    wrapper = mount(NurseDashboard, {
      global: {
        plugins: [pinia],
        stubs: {
          NurseHeader: true,
          NurseSidebar: true,
          'q-layout': { template: '<div><slot /></div>' },
          'q-page-container': { template: '<div><slot /></div>' },
          'q-card': { template: '<div><slot /></div>' },
          'q-card-section': { template: '<div><slot /></div>' },
          'q-card-actions': { template: '<div><slot /></div>' },
          'q-btn': { 
            name: 'q-btn',
            template: '<button @click="$emit(\'click\')" :disabled="disable" :class="{ loading }"><slot /></button>',
            props: ['disable', 'loading', 'label', 'icon', 'color', 'size', 'round', 'flat', 'dense', 'unelevated']
          },
          'q-icon': true,
          'q-spinner': true,
          'q-select': true,
          'q-list': true,
          'q-item': true,
          'q-item-section': true,
          'q-item-label': true,
          'q-avatar': true,
          'q-chip': true,
          'q-dialog': true,
          'q-input': true,
          'q-banner': true,
          'q-space': true,
          'q-badge': true,
          'router-view': true
        },
        directives: {
          'close-popup': {}
        }
      }
    }) as unknown as VueWrapper<NurseDashboardInstance>

    // Wait for initial data load
    await flushPromises()
    
    // Verify callNextPatient method exists
    expect(wrapper.vm.callNextPatient).toBeDefined()
    
    // Manually trigger the method
    await wrapper.vm.callNextPatient()
    
    // Verify API call
    // eslint-disable-next-line @typescript-eslint/unbound-method
    expect(api.post).toHaveBeenCalledWith('/operations/queue/start-processing/', { department: 'OPD' })
    
    // Verify store state update directly
    expect(patientStore.currentPatient).toEqual(expect.objectContaining({
      id: 123,
      full_name: 'John Doe',
      age: 30,
      gender: 'Male'
    }))
  })

  it('handles error when calling next patient', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    
    ;(api.post as Mock).mockRejectedValueOnce(new Error('Network Error'))
    
    wrapper = mount(NurseDashboard, {
      global: {
        plugins: [pinia],
        stubs: {
          NurseHeader: true,
          NurseSidebar: true,
          'q-layout': { template: '<div><slot /></div>' },
          'q-page-container': { template: '<div><slot /></div>' },
          'q-card': { template: '<div><slot /></div>' },
          'q-card-section': { template: '<div><slot /></div>' },
          'q-card-actions': { template: '<div><slot /></div>' },
          'q-btn': { 
            name: 'q-btn',
            template: '<button @click="$emit(\'click\')" :disabled="disable" :class="{ loading }"><slot /></button>',
            props: ['disable', 'loading', 'label', 'icon', 'color', 'size', 'round', 'flat', 'dense', 'unelevated']
          },
          'q-icon': true,
          'q-spinner': true,
          'q-select': true,
          'q-list': true,
          'q-item': true,
          'q-item-section': true,
          'q-item-label': true,
          'q-avatar': true,
          'q-chip': true,
          'q-dialog': true,
          'q-input': true,
          'q-banner': true,
          'q-space': true,
          'q-badge': true,
          'router-view': true
        },
        directives: {
          'close-popup': {}
        }
      }
    }) as unknown as VueWrapper<NurseDashboardInstance>

    await flushPromises()
    await wrapper.vm.callNextPatient()
    
    expect(consoleSpy).toHaveBeenCalledWith('Failed to start queue processing:', expect.any(Error))
    consoleSpy.mockRestore()
  })

  it('sets loading state and disables button during patient call', async () => {
    // Delay response to check loading state
    ;(api.post as Mock).mockImplementationOnce(() => 
      new Promise(resolve => setTimeout(() => resolve({
        data: {
          department: 'OPD',
          current_serving: '001',
          patient: { name: 'John Doe' },
          patient_profile: { id: 123, full_name: 'John Doe' }
        }
      }), 100))
    )

    // Mock initial queue to enable button
    ;(api.get as Mock).mockImplementation((url: string) => {
      if (url.includes('/operations/nurse/queue/patients/')) {
        return Promise.resolve({
          data: {
            normal_queue: [{ id: 1, name: 'Waiting Patient' }],
            priority_queue: [],
            all_patients: [{ id: 1, name: 'Waiting Patient', queue_type: 'normal' }]
          }
        })
      }
      // Return default mocks for other calls
      if (url.includes('/users/profile/')) return Promise.resolve({ data: { user: { full_name: 'Nurse', role: 'nurse', nurse_profile: { department: 'OPD' } } } })
      if (url.includes('/operations/queue/status/')) return Promise.resolve({ data: { is_open: true } })
      return Promise.resolve({ data: [] })
    })

    wrapper = mount(NurseDashboard, {
      global: {
        plugins: [pinia],
        stubs: {
          NurseHeader: true,
          NurseSidebar: true,
          'q-layout': { template: '<div><slot /></div>' },
          'q-page-container': { template: '<div><slot /></div>' },
          'q-card': { template: '<div><slot /></div>' },
          'q-card-section': { template: '<div><slot /></div>' },
          'q-card-actions': { template: '<div><slot /></div>' },
          'q-btn': { 
            name: 'q-btn',
            template: '<button @click="$emit(\'click\')" :disabled="disable" :class="{ loading }"><slot /></button>',
            props: ['disable', 'loading', 'label', 'icon', 'color', 'size', 'round', 'flat', 'dense', 'unelevated']
          },
          'q-icon': true,
          'q-spinner': true,
          'q-select': true,
          'q-list': true,
          'q-item': true,
          'q-item-section': true,
          'q-item-label': true,
          'q-avatar': true,
          'q-chip': true,
          'q-dialog': true,
          'q-input': true,
          'q-banner': true,
          'q-space': true,
          'q-badge': true,
          'router-view': true
        },
        directives: { 'close-popup': {} }
      }
    }) as unknown as VueWrapper<NurseDashboardInstance>

    await flushPromises()
    
    // Find the call button (first button in queueing actions)
    const callBtn = wrapper.findAllComponents({ name: 'q-btn' }).find((btn) => btn.props('label') === 'Call Next Patient')
    
    expect(callBtn).toBeDefined()
    expect(callBtn?.props('disable')).toBe(false)
    expect(callBtn?.props('loading')).toBe(false)
    
    // Trigger call
    const callPromise = wrapper.vm.callNextPatient()
    
    // Check loading state immediately
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.isCallingPatient).toBe(true)
    
    // Check button props update
    expect(callBtn?.props('disable')).toBe(true)
    expect(callBtn?.props('loading')).toBe(true)
    
    // Finish call
    await callPromise
    
    // Verify reset
    expect(wrapper.vm.isCallingPatient).toBe(false)
    expect(callBtn?.props('loading')).toBe(false)
  })

  it('connects to WebSocket and updates queue on message', async () => {
    // Mock WebSocket
    const mockWebSocket = {
      close: vi.fn(),
      onopen: null,
      onmessage: null as ((event: MessageEvent) => void) | null,
      onclose: null
    }
    
    const mockWebSocketConstructor = vi.fn(function() {
      return mockWebSocket
    })
    vi.stubGlobal('WebSocket', mockWebSocketConstructor)

    wrapper = mount(NurseDashboard, {
      global: {
        plugins: [pinia],
        stubs: {
          NurseHeader: true,
          NurseSidebar: true,
          'q-layout': { template: '<div><slot /></div>' },
          'q-page-container': { template: '<div><slot /></div>' },
          'q-card': { template: '<div><slot /></div>' },
          'q-card-section': { template: '<div><slot /></div>' },
          'q-card-actions': { template: '<div><slot /></div>' },
          'q-btn': true,
          'q-icon': true,
          'q-spinner': true,
          'q-select': true,
          'q-list': true,
          'q-item': true,
          'q-item-section': true,
          'q-item-label': true,
          'q-avatar': true,
          'q-chip': true,
          'q-dialog': true,
          'q-input': true,
          'q-banner': true,
          'q-space': true,
          'q-badge': true,
          'router-view': true
        },
        directives: { 'close-popup': {} }
      }
    }) as unknown as VueWrapper<NurseDashboardInstance>

    await flushPromises()

    // Verify WebSocket connection was attempted
    expect(mockWebSocketConstructor).toHaveBeenCalled()
    
    // Simulate WebSocket message
    const messageEvent = new MessageEvent('message', {
      data: JSON.stringify({ type: 'queue_status', department: 'OPD' })
    })
    
    // Reset API mock to track new calls
    ;(api.get as Mock).mockClear()
    
    // Trigger message handler
    if (mockWebSocket.onmessage) {
      mockWebSocket.onmessage(messageEvent)
    }
    
    // Wait for potential async operations
    await flushPromises()
    
    // Verify queue data reload was triggered
    // eslint-disable-next-line @typescript-eslint/unbound-method
    expect(api.get).toHaveBeenCalledWith(expect.stringContaining('/operations/nurse/queue/patients/'))
    
    // Cleanup
    vi.unstubAllGlobals()
  })
})
