<template>
  <q-layout view="hHh Lpr fFf">
    <q-page class="q-pa-md role-body-bg">
      <div class="queue-management-page">
        <div class="page-header">
          <h2 class="page-title">Nurse Queue Management</h2>
          <p class="page-subtitle">Automated queue monitoring and calling.</p>
        </div>

        <q-banner class="bg-blue-1 text-blue-10 q-mb-md" rounded>
          <template v-slot:avatar>
            <q-icon name="info" color="blue" />
          </template>
          <div class="text-weight-medium">Queue automation is enabled.</div>
          <div class="text-body2">
            Manual queue setup and manual open/close controls are not required and are not available. The system automatically opens queues and performs a daily reset at 12:01 AM (00:01) to start each day with a fresh queue state.
          </div>
        </q-banner>

        <div class="actions row q-gutter-sm q-mb-md items-center">
          <div class="col-auto">
            <q-badge color="teal" :label="`Department: ${departmentLabel}`" />
          </div>
          <div class="col-auto">
            <q-badge
              :color="isQueueOpen ? 'green' : 'grey'"
              :label="isQueueOpen ? 'Queue OPEN' : 'Queue CLOSED'"
            />
          </div>
          <div class="col-auto">
            <q-btn color="primary" icon="play_arrow" label="Start Next" @click="startNext" :loading="starting"/>
          </div>
        </div>

        <q-banner v-if="initError" class="bg-red-1 text-red-8 q-mb-md" rounded>
          <template v-slot:avatar>
            <q-icon name="error" color="red" />
          </template>
          {{ initError }}
        </q-banner>

        <div class="row q-col-gutter-md">
          <div class="col-12 col-md-6">
            <q-card>
              <q-card-section>
                <div class="row items-center">
                  <q-icon name="priority_high" color="red" size="20px" class="q-mr-sm" />
                  <div class="text-h6 text-weight-bold">Priority Queue</div>
                  <q-space />
                  <q-badge color="red" :label="`${priorityQueue.length} waiting`" />
                </div>
              </q-card-section>
              <q-separator />
              <q-card-section>
                <q-list separator>
                  <q-item v-for="p in priorityQueue" :key="`prio-${p.queue_number}`">
                    <q-item-section avatar>
                      <q-avatar color="red" text-color="white">P</q-avatar>
                    </q-item-section>
                    <q-item-section>
                      <q-item-label class="text-weight-medium">{{ p.patient_name }} — #{{ p.queue_number }}</q-item-label>
                      <q-item-label caption>
                        {{ p.department }} • Position: {{ p.priority_position ?? '—' }} • Status: {{ p.status }}
                      </q-item-label>
                    </q-item-section>
                  </q-item>
                  <q-item v-if="priorityQueue.length === 0">
                    <q-item-section class="text-center">No priority patients</q-item-section>
                  </q-item>
                </q-list>
              </q-card-section>
            </q-card>
          </div>

          <div class="col-12 col-md-6">
            <q-card>
              <q-card-section>
                <div class="row items-center">
                  <q-icon name="groups" color="teal" size="20px" class="q-mr-sm" />
                  <div class="text-h6 text-weight-bold">Normal Queue</div>
                  <q-space />
                  <q-badge color="teal" :label="`${normalQueue.length} waiting`" />
                </div>
              </q-card-section>
              <q-separator />
              <q-card-section>
                <q-list separator>
                  <q-item v-for="n in normalQueue" :key="`norm-${n.queue_number}`">
                    <q-item-section avatar>
                      <q-avatar color="teal" text-color="white">N</q-avatar>
                    </q-item-section>
                    <q-item-section>
                      <q-item-label class="text-weight-medium">{{ n.patient_name }} — #{{ n.queue_number }}</q-item-label>
                      <q-item-label caption>
                        {{ n.department }} • Position: {{ n.position_in_queue ?? '—' }} • Status: {{ n.status }}
                      </q-item-label>
                    </q-item-section>
                  </q-item>
                  <q-item v-if="normalQueue.length === 0">
                    <q-item-section class="text-center">No patients waiting</q-item-section>
                  </q-item>
                </q-list>
              </q-card-section>
            </q-card>
          </div>
        </div>

        <!-- Calling Countdown Overlay -->
        <q-dialog v-model="showCallingCountdown" persistent maximized transition-show="fade" transition-hide="fade">
          <q-card class="column flex-center bg-info text-white">
            <q-spinner-audio size="80px" color="white" class="q-mb-lg" />
            <div class="text-h1 text-weight-bold q-mb-lg">{{ callingCountdownSeconds }}</div>
            <div class="text-h4 text-center q-px-md">Calling Next Patient...</div>
          </q-card>
        </q-dialog>
      </div>
    </q-page>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { api } from 'src/boot/axios'
import { useQueueStore } from 'src/stores/queue'
import { usePatientStore } from 'src/stores/patientStore'

const $q = useQuasar()
const router = useRouter()
const patientStore = usePatientStore()
const queueStore = useQueueStore()

const departmentValue = ref<string>('OPD')
const initError = ref<string | null>(null)
const initializing = ref(false)
let refreshTimer: ReturnType<typeof setInterval> | null = null
let autoOpenTimer: ReturnType<typeof setTimeout> | null = null
let retryTimer: ReturnType<typeof setTimeout> | null = null
const retryAttempt = ref(0)

interface NurseQueueEntry {
  id?: number | string
  queue_number?: number | string
  patient_name?: string
  department?: string
  status?: string
  priority_position?: number
  position_in_queue?: number
}

const loading = ref(false)
const starting = ref(false)
const showCallingCountdown = ref(false)
const callingCountdownSeconds = ref(3)

// Queues
const priorityQueue = ref<NurseQueueEntry[]>([])
const normalQueue = ref<NurseQueueEntry[]>([])

interface QueueStatusShape {
  id?: number
  department?: string
  is_open?: boolean
  current_serving?: number
  total_waiting?: number
  status_message?: string
}
const queueStatus = ref<QueueStatusShape>({ is_open: false })
const websocket = ref<WebSocket | null>(null)
const isQueueOpen = computed(() => !!queueStatus.value?.is_open)
const isNurse = computed(() => {
  try {
    const raw = localStorage.getItem('user') || '{}'
    const u = JSON.parse(raw)
    const role = (u && (u.role || u.user_type || u.account_type)) || ''
    return String(role).toLowerCase() === 'nurse'
  } catch {
    return true
  }
})

const departmentLabel = computed(() => {
  const dep = departmentValue.value || 'OPD'
  if (dep === 'OPD') return 'Out Patient Department'
  return dep
})

const extractErrorMessage = (err: unknown, fallback: string) => {
  if (err && typeof err === 'object') {
    const resp = (err as { response?: { data?: { error?: unknown } } }).response
    const maybeError = resp?.data?.error
    if (typeof maybeError === 'string' && maybeError.trim().length > 0) return maybeError
  }
  return fallback
}

const logClient = (level: string, message: string, context: Record<string, unknown> = {}) => {
  try {
    void api.post(
      '/operations/client-log/',
      { level, message, context },
      { meta: { queueOnOffline: true, retry: true, requestName: 'queue_requeue' } },
    )
  } catch {
    return
  }
}

// Fetch queues for the selected department only (segregated view)
const fetchQueues = async () => {
  loading.value = true
  try {
    const res = await api.get('/operations/nurse/queue/patients/', {
      params: { department: departmentValue.value }
    })
    priorityQueue.value = Array.isArray(res.data?.priority_queue) ? res.data.priority_queue : []
    normalQueue.value = Array.isArray(res.data?.normal_queue) ? res.data.normal_queue : []
  } catch {
    $q.notify({ type: 'negative', message: 'Failed to fetch queues' })
  } finally {
    loading.value = false
  }
}

const loadQueueStatus = async () => {
  try {
    const dept = departmentValue.value || 'OPD'
    const res = await api.get(`/operations/queue/status/?department=${dept}`)
    const data: QueueStatusShape = res.data || {}
    queueStatus.value = data
    queueStore.setStatus(dept, !!data.is_open)
  } catch {
    queueStatus.value = { is_open: false, department: departmentValue.value, status_message: 'Queue status unavailable' }
  }
}

// Start next patient for the selected department
const startNext = () => {
  starting.value = true
  
  // Show countdown
  showCallingCountdown.value = true
  callingCountdownSeconds.value = 3
  
  const timer = setInterval(() => {
    callingCountdownSeconds.value--
    if (callingCountdownSeconds.value <= 0) {
      clearInterval(timer)
      showCallingCountdown.value = false
      
      // Call API
      void (async () => {
        try {
          const res = await api.post('/operations/queue/start-processing/', {
            department: departmentValue.value
          })
          try {
            if (res?.data?.patient_profile) {
              const payload = { ...res.data.patient_profile, department: res.data?.department || departmentValue.value }
              localStorage.setItem('current_serving_patient', JSON.stringify(payload))
            }
          } catch (e) {
            console.warn('Failed to persist current serving patient from QueueManagement', e)
          }
          const served = res.data?.current_serving
          $q.notify({ type: 'positive', message: served ? `Started patient #${served}` : 'No patients waiting' })
          await fetchQueues()
        } catch (error: unknown) {
          const msg = extractErrorMessage(error, 'Failed to start next patient')
          $q.notify({ type: 'negative', message: msg })
        } finally {
          starting.value = false
        }
      })()
    }
  }, 1000)
}

const detectDepartment = () => {
  return 'OPD'
}

const openQueue = async () => {
  if (!isNurse.value) {
    initError.value = 'Unauthorized: only nurses can manage queues.'
    return
  }

  try {
    await api.post('/operations/queue/status/', {
      department: departmentValue.value,
      is_open: true
    })
    queueStore.broadcastOpen(departmentValue.value)
  } catch (error: unknown) {
    throw new Error(extractErrorMessage(error, 'Failed to auto-open queue'))
  }
}

const dailyResetAndOpen = async () => {
  if (!isNurse.value) return
  try {
    await api.post('/operations/queue/daily-reset/', { department: departmentValue.value })
  } catch {
    // Non-blocking; queue numbering already resets by day in backend counters
  }
  try {
    await openQueue()
  } catch {
    // ignore
  }
}

const scheduleDailyReset = () => {
  const now = new Date()
  const next = new Date(now)
  next.setHours(0, 1, 0, 0)
  if (next.getTime() <= now.getTime()) {
    next.setDate(next.getDate() + 1)
  }
  const ms = next.getTime() - now.getTime()
  autoOpenTimer = setTimeout(() => {
    void (async () => {
      await dailyResetAndOpen()
      scheduleDailyReset()
    })()
  }, ms)
}

const setupWebSocket = () => {
  try {
    const base = new URL(api.defaults.baseURL || `http://${window.location.hostname}:8000`)
    const protocol = base.protocol === 'https:' ? 'wss:' : 'ws:'
    const backendHost = base.hostname
    const backendPort = base.port || (base.protocol === 'https:' ? '443' : '80')
    const dept = departmentValue.value || 'OPD'
    const wsUrl = `${protocol}//${backendHost}:${backendPort}/ws/queue/${dept}/`
    if (websocket.value) {
      try { websocket.value.close() } catch { /* ignore */ }
      websocket.value = null
    }
    websocket.value = new WebSocket(wsUrl)
    websocket.value.onopen = () => { /* no-op */ }
    websocket.value.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'queue_status' || data.type === 'queue_status_update') {
          queueStatus.value = data.status || queueStatus.value
          queueStore.setStatus(dept, !!queueStatus.value.is_open)
        } else if (data.type === 'queue_position_update') {
          const pos = data.position || {}
          const evt = typeof pos.event === 'string' ? pos.event : ''
          const act = typeof pos.action === 'string' ? pos.action : ''
          if (evt === 'no_show' || act === 'move_to_end') {
            try {
              logClient('info', 'nurse_queue_mgmt_ws_requeue_received', {
                department: dept,
                patient_id: pos.patient_id,
                queue_number: pos.queue_number ?? pos.current_queue_number,
                status: pos.status,
                action: act,
                event: evt,
                position_in_queue: pos.position_in_queue,
                priority_position: pos.priority_position,
                timestamp: pos.timestamp,
              })
            } catch {
              void 0
            }
            try {
              const pid = typeof pos.patient_id === 'number' ? pos.patient_id : Number(pos.patient_id)
              const qn = typeof pos.queue_number === 'number' ? pos.queue_number : Number(pos.queue_number ?? pos.current_queue_number)
              const current = patientStore.currentPatient
              const pidMatch = Number.isFinite(pid) && !!current && current.user_id === pid
              const qnMatch = Number.isFinite(qn) && !!current && current.queue_number === qn
              let storagePidMatch = false
              let storageQnMatch = false
              try {
                const raw = localStorage.getItem('current_serving_patient')
                const parsed = raw ? JSON.parse(raw) : null
                const spid = typeof parsed?.user_id === 'number' ? parsed.user_id : Number(parsed?.user_id)
                const sqn = typeof parsed?.queue_number === 'number' ? parsed.queue_number : Number(parsed?.queue_number)
                storagePidMatch = Number.isFinite(pid) && Number.isFinite(spid) && pid === spid
                storageQnMatch = Number.isFinite(qn) && Number.isFinite(sqn) && qn === sqn
              } catch {
                storagePidMatch = false
                storageQnMatch = false
              }
              if (pidMatch || qnMatch || storagePidMatch || storageQnMatch) patientStore.clearCurrentPatient()
            } catch (e) {
              console.warn('Failed to clear current patient on no-show position update', e)
            }
          }
          if (String(pos.status || '') === 'waiting') {
            try {
              const qn = typeof pos.queue_number === 'number' ? pos.queue_number : Number(pos.queue_number ?? pos.current_queue_number)
              if (Number.isFinite(qn)) {
                const raw = localStorage.getItem('current_serving_patient')
                const parsed = raw ? JSON.parse(raw) : null
                const sqn = typeof parsed?.queue_number === 'number' ? parsed.queue_number : Number(parsed?.queue_number)
                if (Number.isFinite(sqn) && sqn === qn) patientStore.clearCurrentPatient()
              }
            } catch (e) {
              console.warn('Failed to clear current patient on waiting position update', e)
            }
          }
          void loadQueueStatus()
          void fetchQueues()
        } else if (data.type === 'queue_notification') {
          const n = data.notification || {}
          const ev = n.event || ''
          if (ev === 'queue_opened') {
            queueStore.broadcastOpen(dept, n.message)
          } else if (ev === 'queue_closed') {
            queueStore.broadcastClose(dept, n.message)
          } else if (ev === 'patient_checked_in') {
            $q.notify({ type: 'positive', message: n.message || 'Patient arrived (checked in).', position: 'top' })
            try {
              if (n.patient_profile) {
                patientStore.setCurrentPatient(n.patient_profile)
              }
            } catch (e) {
              console.warn('Failed to set current patient from patient_checked_in event', e)
            }
            void router.push('/nurse-patient-assessment')
          } else if (ev === 'patient_no_show') {
            const popupMessage = typeof n.message === 'string' && n.message.trim()
              ? n.message
              : 'This patient did not show up, kindly call on the next patient'
            $q.notify({ type: 'warning', message: popupMessage, position: 'top', timeout: 7000 })
            try {
              const pid = typeof n.patient_id === 'number' ? n.patient_id : Number(n.patient_id)
              const qnRaw = n.queue_number
              const qn = typeof qnRaw === 'number' ? qnRaw : Number(qnRaw)
              const current = patientStore.currentPatient
              const pidMatch = Number.isFinite(pid) && !!current && current.user_id === pid
              const qnMatch = Number.isFinite(qn) && !!current && current.queue_number === qn
              let storagePidMatch = false
              let storageQnMatch = false
              try {
                const raw = localStorage.getItem('current_serving_patient')
                const parsed = raw ? JSON.parse(raw) : null
                const spid = typeof parsed?.user_id === 'number' ? parsed.user_id : Number(parsed?.user_id)
                const sqn = typeof parsed?.queue_number === 'number' ? parsed.queue_number : Number(parsed?.queue_number)
                storagePidMatch = Number.isFinite(pid) && Number.isFinite(spid) && pid === spid
                storageQnMatch = Number.isFinite(qn) && Number.isFinite(sqn) && qn === sqn
              } catch {
                storagePidMatch = false
                storageQnMatch = false
              }
              if (pidMatch || qnMatch || storagePidMatch || storageQnMatch) patientStore.clearCurrentPatient()
            } catch (e) {
              console.warn('Failed to clear current patient on no-show notification', e)
            }
          }
          void loadQueueStatus()
          void fetchQueues()
        }
      } catch (e) { console.warn('Invalid WebSocket message for queue status', e) }
    }
    websocket.value.onclose = () => {
      setTimeout(() => {
        if (websocket.value) return
        setupWebSocket()
      }, 5000)
    }
  } catch (e) { console.warn('Failed to setup NurseQueueManagement WebSocket', e) }
}

const scheduleRetry = (message: string) => {
  initError.value = message
  retryAttempt.value += 1
  const delay = Math.min(30000, Math.pow(2, retryAttempt.value) * 1000)
  if (retryTimer) clearTimeout(retryTimer)
  retryTimer = setTimeout(() => {
    void initializeAutomatedQueue()
  }, delay)
}

const initializeAutomatedQueue = async () => {
  if (initializing.value) return
  initializing.value = true
  initError.value = null
  try {
    departmentValue.value = detectDepartment()
    await openQueue()
    await loadQueueStatus()
    await fetchQueues()
    setupWebSocket()
    retryAttempt.value = 0
  } catch (e) {
    scheduleRetry(e instanceof Error ? e.message : 'Failed to initialize automated queue')
  } finally {
    initializing.value = false
  }
}

onMounted(async () => {
  await initializeAutomatedQueue()
  scheduleDailyReset()
  refreshTimer = setInterval(() => {
    void loadQueueStatus()
    void fetchQueues()
  }, 5000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
  if (autoOpenTimer) {
    clearTimeout(autoOpenTimer)
    autoOpenTimer = null
  }
  if (retryTimer) {
    clearTimeout(retryTimer)
    retryTimer = null
  }
  if (websocket.value) {
    try { websocket.value.close() } catch (e) { console.debug('Queue WS close error on unmount', e) }
    websocket.value = null
  }
})
</script>

<style scoped>
.queue-management-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.page-header { display: flex; flex-direction: column; gap: 8px; }
.page-title { font-size: 1.5rem; font-weight: 700; color: #333; }
.page-subtitle { font-size: 1rem; color: #607d8b; }
.actions { align-items: center; }
</style>
