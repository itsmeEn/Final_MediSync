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
          <div class="row q-col-gutter-md q-mb-lg">
            <div class="col-12 col-sm-6">
              <q-card class="status-card gradient-teal text-white shadow-10">
                <q-card-section class="q-pa-lg">
                  <div class="row items-center q-mb-md">
                    <span class="live-indicator" aria-hidden="true"></span>
                    <div class="text-caption text-weight-bold text-uppercase tracking-widest" role="status">Now Serving</div>
                  </div>
                  <div class="text-h2 text-weight-bolder q-mb-sm pulse-animation" aria-live="polite">{{ nowServing || '—' }}</div>
                  <div class="text-subtitle1 text-weight-medium opacity-80">
                    <q-icon name="person" size="xs" class="q-mr-xs" />
                    {{ currentPatient || 'Waiting for next patient' }}
                  </div>
                </q-card-section>
              </q-card>
            </div>
            <div class="col-12 col-sm-6">
              <q-card 
                class="status-card shadow-10"
                :class="inQueue ? 'gradient-blue text-white' : 'glass-card text-teal-9'"
              >
                <q-card-section class="q-pa-lg">
                  <div class="text-caption text-weight-bold text-uppercase q-mb-md tracking-widest" role="status">
                    {{ inQueue ? 'Your Queue' : 'Queue Status' }}
                  </div>
                  
                  <div v-if="inQueue" class="row items-center no-wrap" aria-live="assertive">
                    <div class="col">
                      <div class="queue-metrics q-mb-md">
                        <div class="queue-metric">
                          <div class="queue-metric-label">Queue Number</div>
                          <div class="queue-metric-value">{{ myQueueNumberDisplay }}</div>
                        </div>
                        <div class="queue-metric">
                          <div class="queue-metric-label">Position in Queue</div>
                          <div class="queue-metric-value">{{ myPositionInQueueDisplay }}</div>
                        </div>
                      </div>

                      <q-banner v-if="movedToBackInfo" class="bg-warning text-black q-mb-md" rounded dense>
                        {{ movedToBackInfo.message }}
                      </q-banner>

                      <div v-if="isCalled" class="grace-timer-wrap q-mt-md">
                        <q-circular-progress
                          show-value
                          size="200px"
                          :thickness="0.12"
                          color="white"
                          track-color="rgba(255,255,255,0.25)"
                          :value="graceProgress"
                          class="grace-timer"
                        >
                          <div class="grace-timer-content">
                            <div class="text-caption text-weight-bold opacity-80">Check-in window</div>
                            <div class="text-h4 text-weight-bolder">{{ graceRemainingText }}</div>
                            <q-btn
                              color="positive"
                              icon="how_to_reg"
                              label="Check In"
                              rounded
                              class="q-mt-sm"
                              :loading="checkingIn"
                              :disable="checkingIn || graceRemainingSeconds <= 0"
                              @click="checkInNow"
                            />
                          </div>
                        </q-circular-progress>
                      </div>
                      <div v-else class="text-subtitle1 text-weight-medium opacity-80">
                        <q-icon name="access_time" size="xs" class="q-mr-xs" />
                        Est. Wait: ~{{ estimatedWaitDisplayMins }} mins
                        <span v-if="estimatedWaitDisplayMins > 0" class="q-ml-sm opacity-80">({{ estWaitRemainingText }} remaining)</span>
                      </div>
                      <div class="q-mt-md">
                        <q-btn
                          outline
                          color="negative"
                          icon="exit_to_app"
                          label="Leave Queue"
                          rounded
                          :loading="leavingQueue"
                          :disable="leavingQueue"
                          @click="requestLeaveQueue"
                        />
                      </div>
                    </div>
                    <div class="col-auto">
                      <q-knob
                        readonly
                        v-model="progressValue"
                        size="80px"
                        :thickness="0.15"
                        color="white"
                        track-color="transparent"
                        class="q-ma-sm"
                        style="background: rgba(255, 255, 255, 0.2); border-radius: 50%;"
                      >
                        <q-icon name="trending_up" size="sm" />
                      </q-knob>
                    </div>
                  </div>
                  
                  <div v-else class="column items-center q-py-sm">
                    <q-icon name="info" size="xl" color="teal-3" class="q-mb-sm opacity-50" />
                    <div class="text-body1 text-center text-weight-medium">Not in queue</div>
                    <div class="text-caption text-center opacity-70">Join to see your estimated wait time</div>
                  </div>
                </q-card-section>
              </q-card>
            </div>
          </div>

          <!-- Join Queue Section -->
          <q-card v-if="!inQueue" class="status-card glass-card q-mb-lg">
            <q-card-section class="q-pa-lg">
              <div class="row items-center q-mb-lg">
                <div class="q-pa-sm bg-primary-soft rounded-borders q-mr-md">
                  <q-icon name="add_task" color="primary" size="24px" />
                </div>
                <div>
                  <div class="text-h6 text-weight-bold">Ready to join?</div>
                  <div class="text-caption text-soft">Select your department and secure your spot.</div>
                </div>
              </div>

              <div class="row q-col-gutter-md items-end">
                <div class="col-12 col-sm">
                  <q-select
                    v-model="selectedDepartment"
                    :options="departmentOptions"
                    label="Department"
                    outlined
                    rounded
                    bg-color="white"
                    emit-value
                    map-options
                    :disable="!isQueueAvailableApi"
                  >
                    <template v-slot:prepend>
                      <q-icon name="business" />
                    </template>
                  </q-select>
                </div>
                <div class="col-12 col-sm-auto">
                  <q-btn
                    color="primary"
                    size="lg"
                    label="Join Queue"
                    @click="openJoinDialog"
                    :loading="joiningQueue"
                    :disable="!selectedDepartment || !isQueueAvailableApi"
                    unelevated
                    rounded
                    class="full-width floating-button q-px-xl"
                  >
                    <template v-slot:loading>
                      <q-spinner-dots />
                    </template>
                  </q-btn>
                </div>
              </div>

              <div v-if="queueStatus.is_open && isQueueAvailableApi" class="row items-center q-mt-md text-caption text-soft">
                <div class="col-12 col-sm-auto q-mr-md">
                  <q-icon name="people" size="xs" class="q-mr-xs" />
                  <span>{{ queueEntries.length }} patients currently waiting</span>
                </div>
                <div v-if="estimatedWaitMins > 0" class="col-12 col-sm-auto text-primary text-weight-medium">
                  <q-icon name="access_time" size="xs" class="q-mr-xs" />
                  <span>Est. wait time if you join now: ~{{ estimatedWaitMins }} mins</span>
                </div>
              </div>
            </q-card-section>
          </q-card>

          <!-- Join Queue Modal -->
          <q-dialog v-model="joinDialog" transition-show="scale" transition-hide="scale">
            <q-card class="status-card q-pa-sm" style="min-width: 360px">
              <q-card-section class="row items-center q-pb-none">
                <div class="text-h6 text-weight-bold">Priority Assistance</div>
                <q-space />
                <q-btn icon="close" flat round dense v-close-popup @click="resetJoinDialog" />
              </q-card-section>

              <q-card-section>
                <div class="q-mb-md text-body1">
                  Do you fall into any of these priority categories?
                  <div class="text-caption text-soft q-mt-xs">We provide special assistance for those in need.</div>
                </div>

                <div class="row q-gutter-sm q-mb-md">
                  <q-btn
                    :outline="dialogIsPriority !== true"
                    :color="dialogIsPriority === true ? 'primary' : 'grey-7'"
                    label="Yes"
                    class="col"
                    rounded
                    @click="dialogIsPriority = true"
                    unelevated
                  />
                  <q-btn
                    :outline="dialogIsPriority !== false"
                    :color="dialogIsPriority === false ? 'primary' : 'grey-7'"
                    label="No"
                    class="col"
                    rounded
                    @click="dialogIsPriority = false"
                    unelevated
                  />
                </div>

                <q-slide-transition>
                  <div v-if="dialogIsPriority" class="q-mt-md bg-grey-2 q-pa-md rounded-borders">
                    <div class="text-caption text-weight-bold q-mb-sm text-uppercase">Select category</div>
                    <q-option-group
                      v-model="dialogPriorityLevel"
                      type="radio"
                      :options="priorityOptions"
                      color="primary"
                    />
                  </div>
                </q-slide-transition>

                <div v-if="estimatedWaitMins > 0" class="q-mt-lg q-pa-md bg-indigo-1 text-indigo-9 rounded-borders row items-center">
                  <q-icon name="timer" size="sm" class="q-mr-sm" />
                  <div>
                    <div class="text-caption text-weight-bold text-uppercase">Estimated Wait</div>
                    <div class="text-h6">~{{ estimatedWaitMins }} minutes</div>
                  </div>
                </div>
              </q-card-section>

              <q-card-actions align="right" class="q-pa-md">
                <q-btn flat label="Cancel" color="grey-7" v-close-popup @click="resetJoinDialog" rounded />
                <q-btn 
                  color="primary" 
                  :loading="joiningQueue" 
                  :disable="!selectedDepartment || !isQueueAvailableApi || dialogIsPriority === null" 
                  label="Confirm & Join" 
                  @click="confirmJoinFromDialog" 
                  rounded
                  unelevated
                  class="q-px-lg"
                />
              </q-card-actions>
            </q-card>
          </q-dialog>

          <!-- Current Queue -->
          <q-card class="status-card glass-card q-mb-lg">
            <q-card-section class="q-pa-lg">
              <div class="row items-center q-mb-lg">
                <div class="q-pa-sm bg-teal-soft rounded-borders q-mr-md">
                  <q-icon name="format_list_numbered" color="teal" size="24px" />
                </div>
                <div>
                  <div class="text-h6 text-weight-bold">Live Queue</div>
                  <div class="text-caption text-soft">Real-time updates of patients in line.</div>
                </div>
                <q-space />
                <q-badge
                  outline
                  color="teal"
                  class="q-pa-sm"
                  :label="inQueue ? `Queue #: ${myQueueNumberDisplay} • Position: ${myPositionInQueueDisplay}` : 'Not in queue'"
                />
              </div>

              <q-list separator>
                <transition-group name="queue-list">
                  <q-item
                    v-for="entry in queueEntries"
                    :key="entry.id"
                    class="q-pa-md rounded-borders q-mb-sm transition-all"
                    :class="entry.isMe ? 'bg-blue-1' : (entry.isCurrent ? 'bg-teal-1' : '')"
                  >
                    <q-item-section avatar>
                      <q-avatar 
                        :color="entry.isCurrent ? 'teal' : (entry.isMe ? 'blue' : 'grey-3')" 
                        text-color="white"
                        size="40px"
                      >
                        {{ entry.number.slice(-2) }}
                      </q-avatar>
                    </q-item-section>
                    
                    <q-item-section>
                      <q-item-label class="text-weight-bold text-subtitle1">
                        {{ entry.isMe ? 'You' : entry.name }}
                        <q-badge v-if="entry.isCurrent" color="teal" label="Serving" class="q-ml-sm" />
                      </q-item-label>
                      <q-item-label caption class="text-soft">{{ entry.department }}</q-item-label>
                    </q-item-section>
                    
                    <q-item-section side>
                      <div class="column items-end">
                        <div class="text-weight-bold text-primary">~{{ entry.etaMins }}m</div>
                        <div class="text-caption text-soft">Wait time</div>
                      </div>
                    </q-item-section>
                  </q-item>
                </transition-group>
                
                <q-item v-if="queueEntries.length === 0" class="q-pa-xl">
                  <q-item-section class="text-center">
                    <q-icon name="hourglass_empty" size="48px" color="grey-4" class="q-mb-sm" />
                    <div class="text-body1 text-grey-5">The queue is currently empty</div>
                  </q-item-section>
                </q-item>
              </q-list>
            </q-card-section>
          </q-card>

          <!-- Queue Alerts & Info -->
          <q-card class="status-card glass-card">
            <q-card-section class="q-pa-lg">
              <div class="row items-center q-mb-md">
                <q-icon name="notifications_active" color="indigo" size="24px" class="q-mr-sm" />
                <div class="text-h6 text-weight-bold">Stay Notified</div>
              </div>

              <div class="text-body2 text-soft q-mb-lg">
                We'll notify you when you're almost next. Enable SMS alerts for peace of mind while you wait.
              </div>

              <q-banner class="bg-indigo-1 text-indigo-9 q-mb-lg rounded-borders" dense>
                <template v-slot:avatar>
                  <q-icon name="info" color="indigo" />
                </template>
                Estimated total wait time: <strong>~{{ estimatedWaitMins }} minutes</strong>.
              </q-banner>

              <q-btn
                color="indigo"
                icon="sms"
                label="Activate SMS Alerts"
                class="full-width floating-button"
                size="lg"
                rounded
                @click="activateSMSAlert"
                :disable="smsAlertActive"
                unelevated
              />

              <div v-if="smsAlertActive" class="row justify-center q-mt-md">
                <q-chip icon="check_circle" color="green-1" text-color="green-9" label="SMS Alerts Active" />
              </div>
            </q-card-section>
          </q-card>
        </div>

        <!-- Join Queue Countdown Overlay -->
        <q-dialog v-model="showJoinCountdown" persistent maximized transition-show="fade" transition-hide="fade">
          <q-card class="column flex-center countdown-overlay text-white">
            <div class="countdown-card column items-center">
              <q-spinner-dots size="60px" color="white" class="q-mb-lg" />
              <div class="text-h1 text-weight-bolder q-mb-md">{{ joinCountdownSeconds }}</div>
              <div class="text-h5 text-center text-weight-medium opacity-80">Securing your spot in the queue...</div>
              <div class="text-caption q-mt-md opacity-60">Please stay on this page</div>
            </div>
          </q-card>
        </q-dialog>

        <!-- Serving Countdown Overlay -->
        <q-dialog v-model="showServingCountdown" persistent maximized transition-show="fade" transition-hide="fade">
          <q-card class="column flex-center countdown-overlay text-white">
            <div class="countdown-card column items-center bg-positive-transparent">
              <q-icon name="check_circle" size="80px" color="white" class="q-mb-lg pulse-animation" />
              <div class="text-h2 text-weight-bolder q-mb-md">It's Your Turn!</div>
              <div class="text-h5 text-center text-weight-medium opacity-80">Please proceed to the counter.</div>
              <q-btn flat color="white" label="Dismiss" v-close-popup class="q-mt-xl" />
            </div>
          </q-card>
        </q-dialog>

        <!-- Hang Tight Countdown Overlay -->
        <q-dialog v-model="showHangTightCountdown" persistent maximized transition-show="fade" transition-hide="fade">
          <q-card class="column flex-center countdown-overlay text-white">
            <div class="countdown-card column items-center">
              <q-spinner-hourglass size="60px" color="white" class="q-mb-lg" />
              <div class="text-h2 text-weight-bolder q-mb-md">Almost There</div>
              <div class="text-h5 text-center text-weight-medium opacity-80">Hang tight, we're preparing for you.</div>
              <div class="text-h1 text-weight-bolder q-mt-md">{{ hangTightCountdownSeconds }}</div>
            </div>
          </q-card>
        </q-dialog>
      </q-page>
    </q-page-container>

    <PatientBottomNav />
  </q-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { api, optimizeEndpoint } from 'src/boot/axios'
import logoUrl from 'src/assets/logo.png'
import PatientBottomNav from 'src/components/PatientBottomNav.vue'

const router = useRouter()
const $q = useQuasar()

const ACTIVE_QUEUE_DEPT_KEY = 'medisync_active_queue_department'

// Navigation and UI state
const smsAlertActive = ref(false)
const showUserMenu = ref(false)
const unreadCount = ref(0)

// Queue data
const nowServing = ref<string | number>('')
const currentPatient = ref<string>('')
const myPosition = ref<string | number>('')
const myQueueNumber = ref<number | null>(null)
const myPositionInQueue = ref<number | null>(null)
const myQueueStatus = ref<string>('')
const myGraceExpiresAt = ref<string | null>(null)
const estimatedWaitMins = ref<number>(0)
const estimatedWaitSeconds = ref<number>(0)
const progressValue = ref<number>(0)

const nowTickMs = ref<number>(Date.now())
let secondTickTimer: ReturnType<typeof setInterval> | null = null

const estWaitTotalSeconds = ref<number>(0)
const estWaitStartedAtMs = ref<number>(Date.now())
const estWaitEtaAtMs = ref<number | null>(null)

const currentUserId = computed<number | null>(() => {
  try {
    const u = JSON.parse(localStorage.getItem('user') || '{}')
    const v = Number(u?.id)
    return Number.isFinite(v) ? v : null
  } catch {
    return null
  }
})

const inQueue = computed<boolean>(() => {
  const status = String(myQueueStatus.value || '').trim().toLowerCase()
  if (status === 'no_show' || status === 'cancelled' || status === 'completed') return false
  if (status === 'waiting' || status === 'called' || status === 'in_progress') return true

  const n = myQueueNumber.value
  if (typeof n === 'number' && Number.isFinite(n) && n > 0) return true

  const mp = String(myPosition.value ?? '').trim()
  if (!mp) return false
  const mpLower = mp.toLowerCase()
  if (
    mpLower === '—' ||
    mpLower === '-' ||
    mpLower === 'n/a' ||
    mpLower === 'not in queue' ||
    mpLower === 'no show'
  ) {
    return false
  }
  const mpNum = Number(mp)
  if (Number.isFinite(mpNum)) return mpNum > 0
  if (mpLower === 'called' || mpLower === 'now serving') return true
  return false
})

const isCalled = computed<boolean>(() => myQueueStatus.value === 'called')

const myQueueNumberDisplay = computed<string>(() => {
  const n = myQueueNumber.value
  if (typeof n === 'number' && Number.isFinite(n) && n > 0) return String(n)
  const raw = myPosition.value
  const v = typeof raw === 'number' ? raw : Number(raw)
  if (Number.isFinite(v) && v > 0) return String(v)
  return '—'
})

const myPositionInQueueDisplay = computed<string>(() => {
  const s = String(myQueueStatus.value || '')
  if (s === 'called') return 'Called'
  if (s === 'in_progress') return 'Now Serving'
  const p = myPositionInQueue.value
  if (typeof p === 'number' && Number.isFinite(p) && p > 0) return String(p)
  return '—'
})

const graceRemainingSeconds = computed<number>(() => {
  if (!myGraceExpiresAt.value) return 0
  const ts = Date.parse(myGraceExpiresAt.value)
  if (!Number.isFinite(ts)) return 0
  return Math.max(0, Math.ceil((ts - nowTickMs.value) / 1000))
})

const formatSeconds = (total: number): string => {
  const s = Math.max(0, Math.floor(total))
  const mm = Math.floor(s / 60)
  const ss = s % 60
  return `${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}`
}

const graceRemainingText = computed<string>(() => formatSeconds(graceRemainingSeconds.value))

const graceProgress = computed<number>(() => {
  const total = 60
  const rem = Math.min(total, Math.max(0, graceRemainingSeconds.value))
  return (rem / total) * 100
})

const estWaitRemainingSeconds = computed<number>(() => {
  const etaMs = estWaitEtaAtMs.value
  if (typeof etaMs === 'number' && Number.isFinite(etaMs) && etaMs > 0) {
    return Math.max(0, Math.ceil((etaMs - nowTickMs.value) / 1000))
  }
  const elapsed = Math.floor((nowTickMs.value - estWaitStartedAtMs.value) / 1000)
  return Math.max(0, estWaitTotalSeconds.value - elapsed)
})

const estWaitRemainingText = computed<string>(() => formatSeconds(estWaitRemainingSeconds.value))

const estimatedWaitDisplayMins = computed<number>(() => {
  const sec = estWaitRemainingSeconds.value
  if (sec > 0) return Math.max(0, Math.ceil(sec / 60))
  const m = Number(estimatedWaitMins.value)
  return Number.isFinite(m) ? Math.max(0, Math.round(m)) : 0
})

// New queue management state
const joiningQueue = ref(false)
const selectedDepartment = ref('OPD')
const leavingQueue = ref(false)
const checkingIn = ref(false)
type MovedToBackInfo = { message: string; atMs: number }
const movedToBackInfo = ref<MovedToBackInfo | null>(null)

// Countdown state
const showJoinCountdown = ref(false)
const joinCountdownSeconds = ref(5)
const showServingCountdown = ref(false)
const servingCountdownSeconds = ref(3)
const showHangTightCountdown = ref(false)
const hangTightCountdownSeconds = ref(3)
const lastPosition = ref<string | number>('')
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

const confirmJoinFromDialog = () => {
  if (dialogIsPriority.value === null) {
    $q.notify({ type: 'warning', message: 'Please select Yes or No to continue.', position: 'top' })
    return
  }
  
  // Provide haptic feedback if supported
  if ('vibrate' in navigator) {
    navigator.vibrate(200)
  }
  
  // Close dialog
  joinDialog.value = false
  
  // Start countdown
  showJoinCountdown.value = true
  joinCountdownSeconds.value = 5
  
  const timer = setInterval(() => {
    joinCountdownSeconds.value--
    if (joinCountdownSeconds.value <= 0) {
      clearInterval(timer)
      showJoinCountdown.value = false
      
      // Map modal choice to API payload (priority_level when Yes)
      selectedPriority.value = dialogIsPriority.value ? dialogPriorityLevel.value : null
      void joinQueue()
      resetJoinDialog()
    }
  }, 1000)
}

const isNetworkFailure = (error: unknown): boolean => {
  const e = error as { code?: unknown; message?: unknown; response?: unknown; request?: unknown; medisync?: { type?: unknown } }
  const code = typeof e?.code === 'string' ? e.code : ''
  const msg = typeof e?.message === 'string' ? e.message.toLowerCase() : ''
  const medisyncType = (e as { medisync?: { type?: unknown } })?.medisync?.type
  return (
    code === 'ERR_NETWORK' ||
    code === 'ECONNABORTED' ||
    code === 'CIRCUIT_OPEN' ||
    medisyncType === 'network' ||
    medisyncType === 'circuit_open' ||
    msg.includes('network') ||
    msg.includes('backend temporarily unavailable') ||
    (!e.response && !!e.request)
  )
}

const apiPostWithRecovery = async <T = unknown>(url: string, data?: unknown): Promise<T> => {
  try {
    const res = await api.post(url, data)
    return res.data as T
  } catch (e) {
    if (!isNetworkFailure(e)) throw e
    localStorage.setItem('ENABLE_8001_FALLBACK', 'true')
    await optimizeEndpoint()
    const res = await api.post(url, data, { meta: { isHealthCheck: true } })
    return res.data as T
  }
}

const leaveQueue = async (): Promise<void> => {
  if (leavingQueue.value) return
  if (!selectedDepartment.value) {
    $q.notify({ type: 'warning', message: 'Select a department first.', position: 'top' })
    return
  }

  leavingQueue.value = true
  try {
    type LeaveResp = { success?: boolean; removed?: boolean; message?: string; error?: string; department?: string }
    const resp = await apiPostWithRecovery<LeaveResp>('/operations/queue/leave/', { department: selectedDepartment.value })
    const removed = resp?.removed === true
    const removedDept = typeof resp?.department === 'string' && resp.department ? resp.department : selectedDepartment.value
    const msg = typeof resp?.message === 'string' && resp.message.trim().length > 0
      ? resp.message
      : removed
        ? 'You have left the queue.'
        : 'You are not currently in the queue.'

    myPosition.value = ''
    myQueueNumber.value = null
    myPositionInQueue.value = null
    myQueueStatus.value = ''
    lastPosition.value = ''
    queueEntries.value = queueEntries.value.filter((e) => e && e.isMe !== true)
    localStorage.removeItem(ACTIVE_QUEUE_DEPT_KEY)
    if (removedDept && removedDept !== selectedDepartment.value) selectedDepartment.value = removedDept

    $q.notify({ type: 'positive', message: msg, position: 'top' })
    await fetchQueueData()
  } catch (error: unknown) {
    const err = error as { response?: { status?: number; data?: { error?: string; message?: string } } }
    const status = err?.response?.status
    const msg = err?.response?.data?.error || err?.response?.data?.message
    const fallback =
      status === 401 ? 'Authentication required. Please log in again.' :
      status === 403 ? 'You are not allowed to leave the queue.' :
      status === 404 ? 'Queue entry not found. You may have already been removed.' :
      'Failed to leave queue. Please try again.'
    $q.notify({ type: 'negative', message: msg || fallback, position: 'top' })
    await fetchQueueData()
  } finally {
    leavingQueue.value = false
  }
}

const requestLeaveQueue = (): void => {
  if (leavingQueue.value) return
  $q.dialog({
    title: 'Leave Queue?',
    message: 'Are you sure you want to leave the queue? You will lose your current position.',
    cancel: true,
    persistent: true,
  }).onOk(() => {
    void leaveQueue()
  })
}

const checkInNow = async (): Promise<void> => {
  if (checkingIn.value) return
  if (!selectedDepartment.value) {
    $q.notify({ type: 'warning', message: 'Select a department first.', position: 'top' })
    return
  }
  checkingIn.value = true
  try {
    type CheckInResp = { success?: boolean; checked_in?: boolean; requeued?: boolean; queue_number?: number; department?: string; error?: string }
    const resp = await apiPostWithRecovery<CheckInResp>('/operations/queue/check-in/', { department: selectedDepartment.value })
    if (typeof resp?.department === 'string' && resp.department && resp.department !== selectedDepartment.value) {
      localStorage.setItem(ACTIVE_QUEUE_DEPT_KEY, resp.department)
      selectedDepartment.value = resp.department
    }
    if (resp?.checked_in) {
      localStorage.removeItem(ACTIVE_QUEUE_DEPT_KEY)
      $q.notify({ type: 'positive', message: 'Check-in confirmed.', position: 'top' })
    } else if (resp?.requeued) {
      $q.notify({ type: 'warning', message: `You were re-queued. New Queue #${resp.queue_number ?? ''}`, position: 'top' })
    } else {
      $q.notify({ type: 'info', message: 'Check-in processed.', position: 'top' })
    }
    await fetchQueueData()
  } catch (error: unknown) {
    const err = error as { response?: { status?: number; data?: { error?: string; details?: string; message?: string } } }
    const status = err?.response?.status
    const msg = err?.response?.data?.message || err?.response?.data?.error || err?.response?.data?.details
    if (status === 409) {
      movedToBackInfo.value = { message: msg || 'Grace period expired. You were moved to the back of the queue. Please wait to be called again.', atMs: Date.now() }
      $q.notify({ type: 'warning', message: movedToBackInfo.value.message, position: 'top' })
    } else {
      $q.notify({ type: 'negative', message: msg || 'Failed to check in. Please try again.', position: 'top' })
    }
    await fetchQueueData()
  } finally {
    checkingIn.value = false
  }
}

const joinQueue = async () => {
  if (!selectedDepartment.value) return
  if (!departmentExists.value) {
    $q.notify({ type: 'negative', message: 'Selected department is not available. Please choose another.', position: 'top' })
    return
  }
  
  joiningQueue.value = true
  try {
    const res = await api.post('/operations/queue/join/', {
      department: selectedDepartment.value,
      // Include priority_level if selected
      priority_level: selectedPriority.value ?? undefined
    })
    const payload = (res && typeof res.data === 'object' ? (res.data as Record<string, unknown>) : {}) || {}
    const msg = typeof payload.message === 'string' ? payload.message : ''
    const dept = typeof payload.department === 'string' ? payload.department : ''
    if (msg.toLowerCase().includes('already in queue') && dept) {
      localStorage.setItem(ACTIVE_QUEUE_DEPT_KEY, dept)
      if (dept !== selectedDepartment.value) selectedDepartment.value = dept
      $q.notify({ type: 'warning', message: `You are already in a queue for ${dept}.`, position: 'top' })
      await fetchQueueData()
      return
    }
    localStorage.setItem(ACTIVE_QUEUE_DEPT_KEY, selectedDepartment.value)
    $q.notify({ type: 'positive', message: 'Successfully joined the queue!', position: 'top' })
    await fetchQueueData()
  } catch (error: unknown) {
    const err = error as { response?: { status?: number; data?: Record<string, unknown> } }
    const status = err?.response?.status
    const data = err?.response?.data || {}
    const dept = typeof data.department === 'string' ? data.department : ''
    const rawMsg = (typeof data.error === 'string' ? data.error : (typeof data.message === 'string' ? data.message : '')) || ''
    if (status === 409 && dept) {
      localStorage.setItem(ACTIVE_QUEUE_DEPT_KEY, dept)
      if (dept !== selectedDepartment.value) selectedDepartment.value = dept
      $q.notify({ type: 'warning', message: `You are already in a queue for ${dept}.`, position: 'top' })
      await fetchQueueData()
      return
    }
    $q.notify({ type: 'negative', message: rawMsg || 'Failed to join queue', position: 'top' })
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

    const activeDept = typeof (data as { activeDepartment?: unknown }).activeDepartment === 'string'
      ? (data as { activeDepartment: string }).activeDepartment
      : ''
    if (activeDept && activeDept !== selectedDepartment.value) {
      localStorage.setItem(ACTIVE_QUEUE_DEPT_KEY, activeDept)
      selectedDepartment.value = activeDept
      return
    }
    
    // Check for serving status change
    const newPosition = data.myPosition || ''
    const currentNowServing = data.nowServing || ''
    
    // Check if user is being served
    const isNowServing = (newPosition && newPosition === 'Now Serving') || 
                         (newPosition && currentNowServing && String(newPosition) === String(currentNowServing))
    
    const wasServing = lastPosition.value === 'Now Serving' || lastPosition.value === 'serving'

    if (isNowServing && !wasServing) {
        showServingCountdown.value = true
        servingCountdownSeconds.value = 3
        const timer = setInterval(() => {
            servingCountdownSeconds.value--
            if (servingCountdownSeconds.value <= 0) {
                clearInterval(timer)
                showServingCountdown.value = false
            }
        }, 1000)
        lastPosition.value = 'serving'
    } else if (!isNowServing) {
        lastPosition.value = newPosition
    }

    nowServing.value = data.nowServing || ''
    currentPatient.value = data.currentPatient || ''
    myPosition.value = data.myPosition || ''
    const rawQueueNum = (data as { myQueueNumber?: unknown }).myQueueNumber
    const qn = typeof rawQueueNum === 'number' ? rawQueueNum : Number(rawQueueNum)
    myQueueNumber.value = Number.isFinite(qn) ? qn : null
    const rawPosInQueue = (data as { myPositionInQueue?: unknown }).myPositionInQueue
    const pin = typeof rawPosInQueue === 'number' ? rawPosInQueue : Number(rawPosInQueue)
    myPositionInQueue.value = Number.isFinite(pin) ? pin : null
    myQueueStatus.value = data.myQueueStatus || ''
    myGraceExpiresAt.value = data.myGraceExpiresAt || null
    const rawSecs = (data as { estimatedWaitSeconds?: unknown }).estimatedWaitSeconds
    const secs = typeof rawSecs === 'number' ? rawSecs : Number(rawSecs)
    estimatedWaitSeconds.value = Number.isFinite(secs) ? Math.max(0, Math.round(secs)) : 0
    const rawEta = (data as { estimatedWaitEtaAt?: unknown }).estimatedWaitEtaAt
    const etaMs = typeof rawEta === 'string' ? Date.parse(rawEta) : NaN
    estWaitEtaAtMs.value = Number.isFinite(etaMs) ? etaMs : null
    if (estWaitEtaAtMs.value == null) {
      estWaitTotalSeconds.value = estimatedWaitSeconds.value
      estWaitStartedAtMs.value = Date.now()
    }

    const rawMins = (data as { estimatedWaitMins?: unknown }).estimatedWaitMins
    const mins = typeof rawMins === 'number' ? rawMins : Number(rawMins)
    estimatedWaitMins.value = Number.isFinite(mins) ? Math.max(0, Math.round(mins)) : Math.max(0, Math.ceil(estimatedWaitSeconds.value / 60))
    progressValue.value = data.progressValue || 0
    queueEntries.value = data.queueEntries || []
  } catch (e) {
    console.warn('Failed to fetch queue data', e)
  }
}

let pollTimer: ReturnType<typeof setInterval> | null = null

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
const loadHospitalDepartments = () => {
  try {
    // Only use default queue departments (OPD, Pharmacy, Appointment)
    departmentOptions.value = queueDefaultDepartments
    
    // Reset selection if invalid
    if (!departmentExists.value && departmentOptions.value.length > 0) {
      selectedDepartment.value = departmentOptions.value[0]?.value || 'OPD'
    }
  } catch (e) {
    console.warn('Failed to load hospital departments, using defaults:', e)
    departmentOptions.value = queueDefaultDepartments
  }
}

const urlBase64ToUint8Array = (base64String: string) => {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = window.atob(base64)
  const outputArray = new Uint8Array(rawData.length)
  for (let i = 0; i < rawData.length; i += 1) {
    outputArray[i] = rawData.charCodeAt(i)
  }
  return outputArray
}

const ensurePushSubscription = async () => {
  try {
    if (!('serviceWorker' in navigator) || !('PushManager' in window) || !('Notification' in window)) {
      return
    }

    const token = localStorage.getItem('access_token')
    if (!token) {
      return
    }

    const cfg = await api.get('/operations/ui-config/')
    const vapidPublicKey = (cfg.data?.webpush_vapid_public_key || '').trim()
    if (!vapidPublicKey) {
      return
    }

    const promptedKey = 'push_notifications_prompted'
    if (Notification.permission === 'default' && localStorage.getItem(promptedKey) !== 'true') {
      localStorage.setItem(promptedKey, 'true')
      await Notification.requestPermission()
    }

    if (Notification.permission !== 'granted') {
      return
    }

    const reg = await navigator.serviceWorker.ready
    const existing = await reg.pushManager.getSubscription()
    const subscription = existing || await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
    })

    await api.post('/operations/push/subscribe/', { subscription })
  } catch (e) {
    console.warn('Push subscription failed', e)
  }
}

const attachServiceWorkerNavigationHandler = () => {
  try {
    if (!('serviceWorker' in navigator)) {
      return
    }
    navigator.serviceWorker.addEventListener('message', (event: MessageEvent) => {
      const data = event.data as { type?: string; url?: string } | undefined
      if (data?.type === 'navigate' && typeof data.url === 'string') {
        void router.push(data.url)
      }
    })
  } catch {
    // ignore
  }
}

const setupWebSocket = () => {
  try {
    const base = new URL(api.defaults.baseURL || `http://${window.location.hostname}:8000`)
    const protocol = base.protocol === 'https:' ? 'wss:' : 'ws:'
    const backendHost = base.hostname
    const backendPort = base.port || (base.protocol === 'https:' ? '443' : '80')

    // Try to include user-specific segment to receive position updates
    let userIdSegment: string | null = null
    try {
      const rawUser = localStorage.getItem('user') || '{}'
      const parsed = JSON.parse(rawUser)
      if (parsed && parsed.id) {
        userIdSegment = String(parsed.id)
      }
    } catch { userIdSegment = null }

    const dept = selectedDepartment.value || 'OPD'
    const wsPath = userIdSegment ? `/ws/queue/${dept}/${userIdSegment}/` : `/ws/queue/${dept}/`
    const wsUrl = `${protocol}//${backendHost}:${backendPort}${wsPath}`

    if (websocket.value) {
      try {
        websocket.value.close()
      } catch {
        // ignore
      }
      websocket.value = null
    }

    websocket.value = new WebSocket(wsUrl)

    websocket.value.onopen = () => {
      console.log('Queue WebSocket connected')
    }

    websocket.value.onmessage = (event) => {
      const data = JSON.parse(event.data)

      if (data.type === 'queue_status' || data.type === 'queue_status_update') {
        queueStatus.value = data.status
        void refreshAvailability()
        void fetchQueueData()
      } else if (data.type === 'queue_schedule' || data.type === 'queue_schedule_update') {
        queueSchedules.value = data.schedules || []
      } else if (data.type === 'queue_position_update') {
        const pos = data.position || {}
        const pid = typeof pos.patient_id === 'number' ? pos.patient_id : Number(pos.patient_id)
        const isMine = currentUserId.value != null && Number.isFinite(pid) && pid === currentUserId.value
        if (isMine) {
          const status = String(pos.status || '')
          const dept = String(pos.department || selectedDepartment.value || 'OPD')
          const ev = String(pos.event || '')
          const action = String(pos.action || '')
          if (ev === 'queue_no_show' && action === 'move_to_end') {
            movedToBackInfo.value = { message: 'You did not show up in time. You were moved to the back of the queue.', atMs: Date.now() }
            $q.notify({ type: 'warning', message: movedToBackInfo.value.message, position: 'top', timeout: 6000 })
          }
          myQueueStatus.value = status
          myGraceExpiresAt.value = typeof pos.grace_expires_at === 'string' ? pos.grace_expires_at : null
          const waitSecs = typeof pos.estimated_wait_seconds === 'number' ? pos.estimated_wait_seconds : Number(pos.estimated_wait_seconds)
          if (Number.isFinite(waitSecs)) {
            estimatedWaitSeconds.value = Math.max(0, Math.round(waitSecs))
          }
          const etaMs = typeof pos.estimated_wait_eta_at === 'string' ? Date.parse(pos.estimated_wait_eta_at) : NaN
          estWaitEtaAtMs.value = Number.isFinite(etaMs) ? etaMs : null
          if (estWaitEtaAtMs.value == null && Number.isFinite(waitSecs)) {
            estWaitTotalSeconds.value = Math.max(0, Math.round(waitSecs))
            estWaitStartedAtMs.value = Date.now()
          }
          const waitMins = typeof pos.estimated_wait_mins === 'number' ? pos.estimated_wait_mins : Number(pos.estimated_wait_mins)
          if (Number.isFinite(waitMins)) estimatedWaitMins.value = Math.max(0, Math.round(waitMins))
          else if (Number.isFinite(waitSecs)) estimatedWaitMins.value = Math.max(0, Math.ceil(Math.max(0, Math.round(waitSecs)) / 60))

          if (status === 'called') {
            myPosition.value = 'Called'
            myQueueNumber.value = null
            myPositionInQueue.value = null
            if (dept) localStorage.setItem(ACTIVE_QUEUE_DEPT_KEY, dept)
          } else if (status === 'waiting') {
            const qn = pos.queue_number ?? pos.current_queue_number
            myPosition.value = qn != null ? String(qn) : myPosition.value
            const parsedQn = typeof qn === 'number' ? qn : Number(qn)
            myQueueNumber.value = Number.isFinite(parsedQn) ? parsedQn : myQueueNumber.value
            myPositionInQueue.value = null
            if (dept) localStorage.setItem(ACTIVE_QUEUE_DEPT_KEY, dept)
          } else if (status === 'completed' || status === 'cancelled') {
            myPosition.value = ''
            myQueueStatus.value = ''
            myQueueNumber.value = null
            myPositionInQueue.value = null
            myGraceExpiresAt.value = null
            estimatedWaitMins.value = 0
            estimatedWaitSeconds.value = 0
            estWaitEtaAtMs.value = null
            estWaitTotalSeconds.value = 0
            localStorage.removeItem(ACTIVE_QUEUE_DEPT_KEY)
          } else {
            void fetchQueueData()
          }
          if (status === 'waiting' || status === 'called' || status === 'in_progress') {
            void fetchQueueData()
          }

          if (dept && dept !== selectedDepartment.value) {
            selectedDepartment.value = dept
          }
        } else {
          void fetchQueueData()
        }
      } else if (data.type === 'queue_notification') {
        const n = data.notification || {}
        const event_type = n.event || ''

        if (event_type === 'queue_opened') {
          void refreshAvailability()
          void fetchQueueData()

          $q.notify({
            type: 'positive',
            message: n.message || `The ${n.department || 'queue'} is now OPEN! You can now join.`,
            position: 'top',
            timeout: 5000,
            icon: 'check_circle'
          })
        } else if (event_type === 'queue_closed') {
          void refreshAvailability()
          void fetchQueueData()

          $q.notify({
            type: 'warning',
            message: n.message || `The ${n.department || 'queue'} has been closed.`,
            position: 'top',
            icon: 'info'
          })
        } else {
          const msg = n.message
            || (n.notification && n.notification.message)
            || (event_type === 'queue_started' && n.department && n.queue_number
              ? `Your turn at ${n.department}. Queue #${n.queue_number} started.`
              : (event_type === 'queue_joined' && n.department && n.queue_number
                ? `Joined ${n.department} queue. Queue #${n.queue_number}.`
                : 'Queue update received.'))
          if (event_type === 'queue_no_show' && String(n.action || '') === 'move_to_end') {
            movedToBackInfo.value = { message: msg || 'You did not show up in time. You were moved to the back of the queue.', atMs: Date.now() }
          }
          $q.notify({
            type: event_type === 'queue_no_show' ? 'warning' : 'info',
            message: msg,
            position: 'top'
          })
        }
      } else if (data.type === 'patient_joined_queue') {
        $q.notify({
          type: 'info',
          message: 'Successfully joined the queue!',
          position: 'top'
        })
      }
    }

    websocket.value.onclose = () => {
      console.log('Queue WebSocket disconnected')
      setTimeout(setupWebSocket, 5000)
    }
  } catch (e) {
    console.warn('Failed to setup WebSocket', e)
  }
}

onMounted(async () => {
  secondTickTimer = setInterval(() => {
    nowTickMs.value = Date.now()
  }, 1000)
  attachServiceWorkerNavigationHandler()
  void ensurePushSubscription()
  // Ensure department list matches Appointment system
  loadHospitalDepartments()
  try {
    const storedDept = (localStorage.getItem(ACTIVE_QUEUE_DEPT_KEY) || '').trim()
    if (storedDept) selectedDepartment.value = storedDept
  } catch { return }
  await fetchQueueData()
  setupWebSocket()
  pollTimer = setInterval(() => {
    void fetchQueueData()
  }, 3000)
  
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

// Watch for department changes to reload data and WebSocket
watch(selectedDepartment, async () => {
  await fetchQueueData()
  if (websocket.value) {
    websocket.value.close()
  }
  setupWebSocket()
})

onUnmounted(() => {
  if (secondTickTimer) {
    clearInterval(secondTickTimer)
    secondTickTimer = null
  }
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
  if (websocket.value) {
    websocket.value.close()
  }
})

watch(estimatedWaitMins, (mins) => {
  if (estWaitEtaAtMs.value != null) return
  const m = Number(mins)
  estWaitTotalSeconds.value = Number.isFinite(m) && m > 0 ? Math.round(m * 60) : 0
  estWaitStartedAtMs.value = Date.now()
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
.patient-bg {
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  min-height: 100vh;
}

.status-card {
  border-radius: 20px;
  overflow: hidden;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  border: none;
}

.status-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1);
}

.glass-card {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.gradient-teal {
  background: linear-gradient(135deg, #4db6ac 0%, #00796b 100%);
}

.gradient-blue {
  background: linear-gradient(135deg, #64b5f6 0%, #1976d2 100%);
}

.grace-timer-wrap {
  display: flex;
  justify-content: flex-start;
}

.queue-metrics {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  justify-content: flex-start;
  flex-wrap: nowrap;
  gap: 28px;
}

.queue-metric {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.queue-metric-label {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.8;
  line-height: 1.1;
}

.queue-metric-value {
  font-size: 3.5rem;
  font-weight: 800;
  line-height: 1;
}

@media (max-width: 599px) {
  .queue-metrics {
    gap: 18px;
  }
  .queue-metric-value {
    font-size: 3rem;
  }
}

.grace-timer {
  background: rgba(255, 255, 255, 0.18);
  border-radius: 999px;
  padding: 12px;
}

.grace-timer-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.pulse-animation {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.05); opacity: 0.8; }
  100% { transform: scale(1); opacity: 1; }
}

.floating-button {
  transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.floating-button:active {
  transform: scale(0.95);
}

.queue-list-move,
.queue-list-enter-active,
.queue-list-leave-active {
  transition: all 0.5s ease;
}

.queue-list-enter-from,
.queue-list-leave-to {
  opacity: 0;
  transform: translateX(30px);
}

.countdown-overlay {
  background: rgba(0, 0, 0, 0.4) !important;
  backdrop-filter: blur(8px);
}

.countdown-card {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 30px;
  padding: 40px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
}

.text-soft {
  color: #546e7a;
}

.progress-container {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
}

.live-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #ff5252;
  display: inline-block;
  margin-right: 8px;
  box-shadow: 0 0 0 rgba(255, 82, 82, 0.4);
  animation: live-pulse 2s infinite;
}

@keyframes live-pulse {
  0% { box-shadow: 0 0 0 0 rgba(255, 82, 82, 0.4); }
  70% { box-shadow: 0 0 0 10px rgba(255, 82, 82, 0); }
  100% { box-shadow: 0 0 0 0 rgba(255, 82, 82, 0); }
}
</style>
