<template>
  <q-layout view="hHh lpR fFf">
    <!-- Patient Portal Header -->
    <q-header class="bg-white text-teal-9">
      <q-toolbar>
        <q-avatar size="40px" class="q-mr-md">
          <img :src="logoUrl" alt="MediSync Logo" />
        </q-avatar>

        <div class="header-content"></div>

        <q-space />

        <!-- Notification Icon -->
        <q-btn flat round icon="notifications" class="q-mr-sm">
          <q-badge v-if="unreadCount > 0" color="red" floating rounded>{{ unreadCount }}</q-badge>
        </q-btn>

        <!-- User Menu -->
        <q-btn flat round>
          <q-avatar size="32px" color="white" text-color="primary">
            {{ userInitials }}
          </q-avatar>
          <q-menu v-model="showUserMenu">
            <q-list style="min-width: 200px">
              <q-item clickable @click="navigateTo('/patient-settings')">
                <q-item-section avatar>
                  <q-icon name="settings" />
                </q-item-section>
                <q-item-section>Settings</q-item-section>
              </q-item>
              <q-item clickable @click="logout">
                <q-item-section avatar>
                  <q-icon name="logout" />
                </q-item-section>
                <q-item-section>Logout</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-btn>
      </q-toolbar>
    </q-header>

    <!-- Main Content -->
    <q-page-container>
      <q-page class="patient-bg q-pa-md">
        <div class="q-pa-md">
          <!-- Page Title -->
          <div class="q-mb-md">
            <div class="text-h5 text-weight-bold">Live Queue & Wait Time</div>
          </div>

          <!-- Queue Status Banner -->
          <q-banner 
            v-if="!isQueueAvailableApi" 
            class="bg-orange-1 text-orange-8 q-mb-md" 
            rounded
          >
            <template v-slot:avatar>
              <q-icon name="schedule" color="orange" />
            </template>
            {{ availabilityReason || ('Queue is not available at this time. Operating hours: ' + queueScheduleText) }}
          </q-banner>

          <!-- Current Status Cards -->
          <div class="row q-gutter-md q-mb-md">
            <div class="col-12 col-sm-6">
              <q-card class="bg-teal-6 text-white">
                <q-card-section class="q-pa-md">
                  <div class="text-caption text-weight-medium text-uppercase q-mb-xs">Now Serving</div>
                  <div class="text-h4 text-weight-bold">{{ nowServing || '—' }}</div>
                  <div class="text-body2 text-weight-medium q-mt-xs">{{ currentPatient || '—' }}</div>
                </q-card-section>
              </q-card>
            </div>
            <div class="col-12 col-sm-6">
              <q-card :class="myPosition ? 'bg-teal-7 text-white' : 'bg-grey-4 text-black'">
                <q-card-section class="q-pa-md">
                  <div class="text-caption text-weight-medium text-uppercase q-mb-xs">Your Queue Status</div>
                  <div class="text-h4 text-weight-bold">{{ myPosition || 'Not in queue' }}</div>
                  <div class="text-body2 text-weight-medium q-mt-xs">
                    {{ myPosition ? `Estimated Wait: ~${estimatedWaitMins} mins` : 'Join the queue to get your position' }}
                  </div>
                </q-card-section>
              </q-card>
            </div>
          </div>

          <!-- Join Queue Section -->
          <q-card v-if="!myPosition" class="q-mb-md">
            <q-card-section>
              <div class="row items-center q-mb-md">
                <q-icon name="add_circle" color="primary" size="20px" class="q-mr-sm" />
                <div class="text-h6 text-weight-bold">Join Queue</div>
              </div>

              <div class="text-body2 q-mb-md">
                Join the queue to secure your position and receive real-time updates on your wait time.
              </div>

              <div class="row q-gutter-md">
                <div class="col">
                  <q-select
                    v-model="selectedDepartment"
                    :options="departmentOptions"
                    label="Select Department"
                    outlined
                    emit-value
                    map-options
                    :disable="!isQueueAvailableApi"
                  />
                </div>
                <div class="col-auto">
                  <q-btn
                    color="primary"
                    icon="add"
                    label="Join Queue"
                    @click="openJoinDialog"
                    :loading="joiningQueue"
                    :disable="!selectedDepartment || !isQueueAvailableApi"
                    unelevated
                    class="full-height"
                  />
                </div>
              </div>

              <div v-if="queueStatus.is_open && isQueueAvailableApi" class="text-caption q-mt-sm">
                Current queue length: {{ queueEntries.length }} patients
              </div>
            </q-card-section>
          </q-card>

          <!-- Join Queue Modal -->
          <q-dialog v-model="joinDialog">
            <q-card style="min-width: 360px">
              <q-card-section class="row items-center q-pb-none">
                <div class="text-h6">Join Queue</div>
                <q-space />
                <q-btn icon="close" flat round dense v-close-popup @click="resetJoinDialog" />
              </q-card-section>

              <q-card-section>
                <div class="q-mb-md">
                  Do you fall into any of these priority categories?
                  <div class="text-caption q-mt-xs">PWD, Pregnant, Senior Citizen, Accompanying a Child</div>
                </div>

                <q-option-group
                  v-model="dialogIsPriority"
                  type="radio"
                  :options="[
                    { label: 'Yes', value: true },
                    { label: 'No', value: false }
                  ]"
                />

                <div v-if="dialogIsPriority" class="q-mt-md">
                  <div class="text-caption q-mb-sm">Select category</div>
                  <q-option-group
                    v-model="dialogPriorityLevel"
                    type="radio"
                    :options="priorityOptions"
                    color="primary"
                  />
                </div>
              </q-card-section>

              <q-card-actions align="right">
                <q-btn flat label="Cancel" v-close-popup @click="resetJoinDialog" />
                <q-btn color="primary" :loading="joiningQueue" :disable="!selectedDepartment || !isQueueAvailableApi || dialogIsPriority === null" label="Join" @click="confirmJoinFromDialog" />
              </q-card-actions>
            </q-card>
          </q-dialog>

          <!-- Current Queue -->
          <q-card class="q-mb-md">
            <q-card-section>
              <div class="row items-center q-mb-md">
                <q-icon name="format_list_numbered" color="teal" size="20px" class="q-mr-sm" />
                <div class="text-h6 text-weight-bold">Current Queue</div>
                <q-space />
                <q-badge color="teal" :label="`Position: ${myPosition || '—'}`" />
              </div>

              <q-list separator>
                <q-item
                  v-for="entry in queueEntries"
                  :key="entry.id"
                  class="q-pa-md"
                >
                  <q-item-section avatar>
                    <q-icon
                      name="person"
                      :color="entry.isCurrent ? 'teal' : 'grey-5'"
                      size="24px"
                    />
                  </q-item-section>
                  
                  <q-item-section>
                    <q-item-label class="text-weight-medium">{{ entry.name }} ({{ entry.number }})</q-item-label>
                    <q-item-label caption>{{ entry.isMe ? 'You' : entry.department }}</q-item-label>
                  </q-item-section>
                  
                  <q-item-section side>
                    <div class="text-right">
                      <div class="text-caption">~{{ entry.etaMins }} mins</div>
                      <q-badge
                        v-if="entry.isCurrent"
                        color="orange"
                        label="Next"
                        class="q-mt-xs"
                      />
                      <q-badge
                        v-else-if="entry.isMe"
                        color="grey-6"
                        label="You"
                        class="q-mt-xs"
                      />
                    </div>
                  </q-item-section>
                </q-item>
                
                <q-item v-if="queueEntries.length === 0">
                  <q-item-section class="text-center">
                    No queue data available.
                  </q-item-section>
                </q-item>
              </q-list>
            </q-card-section>
          </q-card>

          <!-- Queue Alerts & Info -->
          <q-card>
            <q-card-section>
              <div class="row items-center q-mb-md">
                <q-icon name="info" color="grey-6" size="20px" class="q-mr-sm" />
                <div class="text-h6 text-weight-bold">Queue Alerts & Info</div>
              </div>

              <div class="text-body2 q-mb-md">
                Request a text message alert when you are the <strong>next patient</strong> in line.
              </div>

              <q-banner class="bg-orange-1 text-orange-8 q-mb-md" rounded>
                <template v-slot:avatar>
                  <q-icon name="schedule" color="orange" />
                </template>
                Current estimated total wait time: ~{{ estimatedWaitMins }} minutes.
              </q-banner>

              <q-btn
                color="indigo"
                icon="sms"
                label="Activate SMS Alert"
                class="full-width"
                @click="activateSMSAlert"
                :disable="smsAlertActive"
                unelevated
              />

              <div v-if="smsAlertActive" class="text-center q-mt-md">
                <q-badge color="green" icon="check_circle" label="SMS Alert Active" />
              </div>
            </q-card-section>
          </q-card>
        </div>
      </q-page>
    </q-page-container>

    <PatientBottomNav />
  </q-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { api } from 'src/boot/axios'
import logoUrl from 'src/assets/logo.png'
import PatientBottomNav from 'src/components/PatientBottomNav.vue'

const router = useRouter()
const $q = useQuasar()

// Navigation and UI state
const smsAlertActive = ref(false)
const showUserMenu = ref(false)
const unreadCount = ref(0)

// Queue data
const nowServing = ref<string | number>('')
const currentPatient = ref<string>('')
const myPosition = ref<string | number>('')
const estimatedWaitMins = ref<number>(0)
const progressValue = ref<number>(0)

// New queue management state
const joiningQueue = ref(false)
const selectedDepartment = ref('OPD')
const queueStatus = ref({
  is_open: false,
  department: 'OPD',
  total_patients: 0,
  estimated_wait_time: 0
})
const isQueueAvailableApi = ref(false)
const availabilityReason = ref<string | null>(null)

interface QueueSchedule {
  id: number
  start_time: string
  end_time: string
  is_active: boolean
  department: string
}

const queueSchedules = ref<QueueSchedule[]>([])
const websocket = ref<WebSocket | null>(null)

interface QueueEntry {
  id: number
  name: string
  number: string
  department: string
  etaMins: number
  isCurrent?: boolean
  isMe?: boolean
}

const queueEntries = ref<QueueEntry[]>([])

// User information
const userName = computed(() => {
  try {
    const u = JSON.parse(localStorage.getItem('user') || '{}')
    return u.full_name || u.email || 'User'
  } catch {
    return 'User'
  }
})

const userInitials = computed(() => {
  const name = userName.value || ''
  const parts = name.trim().split(/\s+/)
  if (parts.length === 0) return 'U'
  const initials = parts.slice(0, 2).map((p: string) => p[0]?.toUpperCase() ?? '').join('')
  return initials || (name[0]?.toUpperCase() ?? 'U')
})

// Department options
// Updated to use shared hospital departments source to match Appointment system
// and ensure consistency across patient and nurse queue management.
import type { DepartmentOption } from '../utils/departments'
// Queue-enabled defaults; keep legacy departments intact
const queueDefaultDepartments: DepartmentOption[] = [
  { label: 'Out Patient Department', value: 'OPD' },
  { label: 'Pharmacy', value: 'Pharmacy' },
  { label: 'Appointment', value: 'Appointment' }
]
const departmentOptions = ref<DepartmentOption[]>(queueDefaultDepartments)

// Validate selected department exists in hospital departments list
const departmentExists = computed(() =>
  !!departmentOptions.value.find((d) => d.value === selectedDepartment.value)
)

// Add priority options for joining priority queue
const priorityOptions = computed(() => [
  { label: 'Person With Disability (PWD)', value: 'pwd' },
  { label: 'Pregnant', value: 'pregnant' },
  { label: 'Senior Citizen', value: 'senior' },
  { label: 'Accompanying a Child', value: 'with_child' }
])

const selectedPriority = ref<string | null>(null)

// Join Queue modal state
const joinDialog = ref(false)
const dialogIsPriority = ref<boolean | null>(null)
const dialogPriorityLevel = ref<string>('pwd')

const queueScheduleText = computed(() => {
  const activeSchedules = queueSchedules.value.filter(s => s.is_active)
  if (activeSchedules.length === 0) return 'No schedule available'
  
  return activeSchedules
    .map(s => `${s.start_time} - ${s.end_time}`)
    .join(', ')
})



// Methods
const openJoinDialog = () => {
  // Prevent joining if department is unavailable or invalid
  if (!departmentExists.value) {
    $q.notify({ type: 'warning', message: 'Please select a valid department.', position: 'top' })
    return
  }
  if (!isQueueAvailableApi.value) {
    $q.notify({ type: 'warning', message: availabilityReason.value || 'Queue is not available right now.', position: 'top' })
    return
  }
  dialogIsPriority.value = null
  dialogPriorityLevel.value = 'pwd'
  joinDialog.value = true
}

const resetJoinDialog = () => {
  dialogIsPriority.value = null
  dialogPriorityLevel.value = 'pwd'
}

const confirmJoinFromDialog = async () => {
  if (dialogIsPriority.value === null) {
    $q.notify({ type: 'warning', message: 'Please select Yes or No to continue.', position: 'top' })
    return
  }
  // Map modal choice to API payload (priority_level when Yes)
  selectedPriority.value = dialogIsPriority.value ? dialogPriorityLevel.value : null
  joinDialog.value = false
  await joinQueue()
  resetJoinDialog()
}

const joinQueue = async () => {
  if (!selectedDepartment.value) return
  if (!departmentExists.value) {
    $q.notify({ type: 'negative', message: 'Selected department is not available. Please choose another.', position: 'top' })
    return
  }
  
  joiningQueue.value = true
  try {
    await api.post('/operations/queue/join/', {
      department: selectedDepartment.value,
      // Include priority_level if selected
      priority_level: selectedPriority.value ?? undefined
    })
    $q.notify({ type: 'positive', message: 'Successfully joined the queue!', position: 'top' })
    await fetchQueueData()
  } catch (error: unknown) {
    const errorMessage = error instanceof Error && 'response' in error 
      ? (error as { response?: { data?: { error?: string } } }).response?.data?.error || 'Failed to join queue'
      : 'Failed to join queue'
    $q.notify({ type: 'negative', message: errorMessage, position: 'top' })
  } finally {
    joiningQueue.value = false
  }
}

const fetchQueueData = async () => {
  try {
    // Fetch queue status
    const statusRes = await api.get(`/operations/queue/status/?department=${selectedDepartment.value || 'OPD'}`)
    queueStatus.value = statusRes.data || queueStatus.value

    // Derive queue schedules from status current schedule
    const sStart = statusRes.data?.current_schedule_start_time || null
    const sEnd = statusRes.data?.current_schedule_end_time || null
    const dept = statusRes.data?.department || (selectedDepartment.value || 'OPD')
    queueSchedules.value = (sStart && sEnd)
      ? [{ id: 0, start_time: sStart, end_time: sEnd, is_active: true, department: dept }]
      : []

    // Derive availability from status instead of hitting availability endpoint
    isQueueAvailableApi.value = !!statusRes.data?.is_open
    availabilityReason.value = statusRes.data?.is_open ? null : (statusRes.data?.status_message || 'Queue is currently closed')

    // If department is invalid or not configured, reflect that in availability
    if (!departmentExists.value && !statusRes.data?.is_open) {
      availabilityReason.value = 'Queue system is not configured for this department'
    }

    // Fetch queue summary
    const summaryRes = await api.get(`/operations/patient/dashboard/summary/?department=${selectedDepartment.value || 'OPD'}`)
    const data = summaryRes.data || {}
    nowServing.value = data.nowServing || ''
    currentPatient.value = data.currentPatient || ''
    myPosition.value = data.myPosition || ''
    estimatedWaitMins.value = data.estimatedWaitMins || 0
    progressValue.value = data.progressValue || 0

    // No patient-visible queue list endpoint; keep empty
    queueEntries.value = []
  } catch (e) {
    console.warn('Failed to fetch queue data', e)
  }
}

const refreshAvailability = async () => {
  try {
    const dept = selectedDepartment.value || 'OPD'
    const statusRes = await api.get(`/operations/queue/status/?department=${dept}`)
    isQueueAvailableApi.value = !!statusRes.data?.is_open
    availabilityReason.value = statusRes.data?.is_open ? null : (statusRes.data?.status_message || 'Queue is currently closed')
  } catch (e) {
    console.warn('Failed to refresh queue availability', e)
  }
}

// Load hospital departments to keep in sync with Appointment system
const loadHospitalDepartments = async () => {
  try {
    const res = await api.get('/operations/hospital/departments/')
    const raw = Array.isArray(res.data?.departments) ? res.data.departments : []
    // Normalize department array: supports [string] or [{label,value}] inputs
    const normalizedValues = new Set<string>()
    raw.forEach((item: unknown) => {
      if (typeof item === 'string') normalizedValues.add(item)
      else if (item && typeof item === 'object') {
        const v = (item as { value?: string; label?: string }).value || (item as { label?: string }).label
        if (typeof v === 'string') normalizedValues.add(v)
      }
    })
    // Build options from backend (preserve labels when provided)
    const backendOptions: DepartmentOption[] = (raw as Array<string | { value?: string; label?: string }>)
      .map((item) => {
        if (typeof item === 'string') return { label: item, value: item }
        if (item && typeof item === 'object') {
          const obj = item
          const value = typeof obj.value === 'string' ? obj.value : (typeof obj.label === 'string' ? obj.label : '')
          const label = typeof obj.label === 'string' ? obj.label : (typeof value === 'string' ? value : '')
          if (value) return { label, value }
        }
        return null
      })
      .filter((opt) => !!opt) as DepartmentOption[]

    // Union: start with queue defaults, add any backend departments not already present
    const existing = new Set(queueDefaultDepartments.map((d) => d.value))
    const union: DepartmentOption[] = [...queueDefaultDepartments]
    backendOptions.forEach((opt) => {
      if (!existing.has(opt.value)) {
        union.push(opt)
        existing.add(opt.value)
      }
    })

    departmentOptions.value = union.length ? union : queueDefaultDepartments
    // Reset selection if invalid
    if (!departmentExists.value && departmentOptions.value.length > 0) {
      selectedDepartment.value = departmentOptions.value[0]?.value || 'OPD'
    }
  } catch (e) {
    console.warn('Failed to load hospital departments, using defaults:', e)
    departmentOptions.value = queueDefaultDepartments
  }
}

const setupWebSocket = () => {
  try {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const base = new URL(api.defaults.baseURL || `http://${window.location.hostname}:8000/api`)
    const backendHost = base.hostname
    const backendPort = base.port || (base.protocol === 'https:' ? '443' : '80')

    // Try to include user-specific segment to receive position updates
    let userIdSegment = ''
    try {
      const rawUser = localStorage.getItem('user') || '{}'
      const parsed = JSON.parse(rawUser)
      if (parsed && parsed.id) {
        userIdSegment = `${parsed.id}/`
      }
    } catch { userIdSegment = '' }

    const dept = selectedDepartment.value || 'OPD'
    const wsUrl = `${protocol}//${backendHost}:${backendPort}/ws/queue/${dept}/${userIdSegment}`
    const httpProtocol = window.location.protocol === 'https:' ? 'https:' : 'http:'
    const httpProbeUrl = `${httpProtocol}//${backendHost}:${backendPort}/ws/queue/${dept}/${userIdSegment}`
    
    // [2025-10-31] Preflight HEAD probe added to avoid browser console
    // errors when Queue WS routes are not present (local dev / Channels off)
    fetch(httpProbeUrl, { method: 'HEAD' }).then((res) => {
      if (!res.ok) {
        // Endpoint not available; skip WebSocket setup
        return
      }
      websocket.value = new WebSocket(wsUrl)
      
      websocket.value.onopen = () => {
        console.log('Queue WebSocket connected')
      }
    
      websocket.value.onmessage = (event) => {
        const data = JSON.parse(event.data)
      
      if (data.type === 'queue_status' || data.type === 'queue_status_update') {
        queueStatus.value = data.status
        // Refresh availability when status changes
        void refreshAvailability()
        
        // Also refresh the full queue data to update UI
        void fetchQueueData()
      } else if (data.type === 'queue_schedule' || data.type === 'queue_schedule_update') {
        queueSchedules.value = data.schedules || []
      } else if (data.type === 'queue_position_update') {
        myPosition.value = data.position.position
        estimatedWaitMins.value = data.position.estimated_wait_time
      } else if (data.type === 'queue_notification') {
        const n = data.notification || {}
        const event_type = n.event || ''
        
        // Check if queue was opened
        if (event_type === 'queue_opened') {
          console.log('Queue opened notification received, refreshing availability')
          // Refresh availability immediately
          void refreshAvailability()
          // Also refresh the full queue data
          void fetchQueueData()
          
          // Show success notification to patient
          $q.notify({
            type: 'positive',
            message: n.message || `The ${n.department || 'queue'} is now OPEN! You can now join.`,
            position: 'top',
            timeout: 5000,
            icon: 'check_circle'
          })
        } else if (event_type === 'queue_closed') {
          console.log('Queue closed notification received, refreshing availability')
          // Refresh availability immediately
          void refreshAvailability()
          void fetchQueueData()
          
          $q.notify({
            type: 'warning',
            message: n.message || `The ${n.department || 'queue'} has been closed.`,
            position: 'top',
            icon: 'info'
          })
        } else {
          // Other queue notifications
          const msg = n.message 
            || (n.notification && n.notification.message) 
            || (event_type === 'queue_started' && n.department && n.queue_number 
              ? `Your turn at ${n.department}. Queue #${n.queue_number} started.` 
              : (event_type === 'queue_joined' && n.department && n.queue_number 
                ? `Joined ${n.department} queue. Queue #${n.queue_number}.`
                : 'Queue update received.'))
          $q.notify({
            type: 'info',
            message: msg,
            position: 'top'
          })
        }
      } else if (data.type === 'patient_joined_queue') {
        // Legacy event support
        $q.notify({
          type: 'info',
          message: 'Successfully joined the queue!',
          position: 'top'
        })
      }
      }
      
      websocket.value.onclose = () => {
        console.log('Queue WebSocket disconnected')
        // Attempt to reconnect after 5 seconds
        setTimeout(setupWebSocket, 5000)
      }
    }).catch(() => {
      // Probe failed; skip connecting
    })
  } catch (e) {
    console.warn('Failed to setup WebSocket', e)
  }
}

onMounted(async () => {
  await fetchQueueData()
  setupWebSocket()
  // Ensure department list matches Appointment system
  await loadHospitalDepartments()
  
  try {
    // Declare window interface for lucide
    interface WindowWithLucide extends Window {
      lucide?: {
        createIcons(): void
      }
    }
    ;(window as WindowWithLucide).lucide?.createIcons()
  } catch (e) { console.warn('lucide icons init failed', e) }
})

onUnmounted(() => {
  if (websocket.value) {
    websocket.value.close()
  }
})

const navigateTo = (path: string) => {
  void router.push(path)
}

const logout = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user')
  void router.push('/login')
}

const activateSMSAlert = async () => {
  try {
    await api.post('/patient/queue/alerts/sms/')
    smsAlertActive.value = true
    $q.notify({ type: 'positive', message: 'SMS alert activated', position: 'top' })
  } catch {
    $q.notify({ type: 'negative', message: 'Failed to activate SMS alert', position: 'top' })
  }
}
</script>

<style scoped>
.status-card { border-radius: 12px; }
</style>
