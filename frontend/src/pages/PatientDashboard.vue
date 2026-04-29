<template>
  <q-layout view="hHh lpR fFf" :class="{ 'high-contrast': highContrast, 'large-text': largeText }">
    <!-- Patient Portal Header -->
    <q-header flat class="bg-white text-teal-9 main-header">
      <q-toolbar class="q-px-lg">
        <q-avatar size="44px" class="q-mr-md shadow-1">
          <img :src="logoUrl" alt="MediSync Logo" />
        </q-avatar>
        
        <div class="header-brand">
          <div class="text-h6 text-weight-bolder text-teal-10">MediSync</div>
          <div class="text-caption text-teal-6 text-weight-medium">Patient Portal</div>
        </div>

        <q-space />

        <div class="header-actions row items-center q-gutter-sm">
          <!-- Accessibility Menu -->
          <q-btn flat round color="grey-7" icon="settings_accessibility">
            <q-menu transition-show="scale" transition-hide="scale">
              <q-list style="min-width: 200px">
                <q-item-label header>Accessibility</q-item-label>
                <q-item clickable v-ripple @click="toggleAccessibility">
                  <q-item-section avatar>
                    <q-icon :name="highContrast ? 'visibility_off' : 'visibility'" :color="highContrast ? 'teal' : 'grey'" />
                  </q-item-section>
                  <q-item-section>High Contrast</q-item-section>
                  <q-item-section side>
                    <q-toggle v-model="highContrast" color="teal" />
                  </q-item-section>
                </q-item>
                <q-item clickable v-ripple @click="toggleLargeText">
                  <q-item-section avatar>
                    <q-icon name="text_fields" :color="largeText ? 'teal' : 'grey'" />
                  </q-item-section>
                  <q-item-section>Larger Text</q-item-section>
                  <q-item-section side>
                    <q-toggle v-model="largeText" color="teal" />
                  </q-item-section>
                </q-item>
              </q-list>
            </q-menu>
            <q-tooltip>Accessibility Options</q-tooltip>
          </q-btn>

          <!-- Notification Icon -->
          <q-btn flat round icon="notifications" color="teal-8" class="relative-position">
            <q-badge v-if="unreadCount > 0" color="red" floating rounded>{{ unreadCount }}</q-badge>
            <q-tooltip>Notifications</q-tooltip>
          </q-btn>

          <!-- User Profile -->
          <q-btn flat round class="q-ml-sm profile-btn">
            <q-avatar size="36px" color="teal-1" text-color="teal-9" class="text-weight-bold shadow-1">
              {{ userInitials }}
            </q-avatar>
            <q-menu v-model="showUserMenu" transition-show="jump-down" transition-hide="jump-up" class="user-menu-dropdown">
              <q-list style="min-width: 220px">
                <q-item class="q-py-md">
                  <q-item-section avatar>
                    <q-avatar color="teal-6" text-color="white">{{ userInitials }}</q-avatar>
                  </q-item-section>
                  <q-item-section>
                    <q-item-label class="text-weight-bold">{{ userName }}</q-item-label>
                    <q-item-label caption>Patient</q-item-label>
                  </q-item-section>
                </q-item>
                <q-separator />
                <q-item clickable v-ripple @click="navigateTo('/patient-settings')">
                  <q-item-section avatar><q-icon name="person_outline" color="teal-7" /></q-item-section>
                  <q-item-section>My Profile</q-item-section>
                </q-item>
                <q-item clickable v-ripple @click="navigateTo('/patient-settings')">
                  <q-item-section avatar><q-icon name="settings" color="teal-7" /></q-item-section>
                  <q-item-section>Settings</q-item-section>
                </q-item>
                <q-separator />
                <q-item clickable v-ripple @click="logout" class="text-negative">
                  <q-item-section avatar><q-icon name="logout" color="negative" /></q-item-section>
                  <q-item-section>Logout</q-item-section>
                </q-item>
              </q-list>
            </q-menu>
          </q-btn>
        </div>
      </q-toolbar>
    </q-header>

    <!-- Main Content -->
    <q-page-container>
      <q-page class="patient-bg q-pa-md" :class="{ 'high-contrast': highContrast, 'large-text': largeText }" role="main" aria-label="Patient Dashboard">
        <!-- Hero Section & Personalized Greeting -->
        <div class="hero-section q-mb-xl q-pa-lg rounded-xl shadow-2 animate-fade-in" style="animation-delay: 0.1s" role="region" aria-label="Welcome section">
          <div class="row items-center justify-between">
            <div class="col-12 col-md-7">
              <div class="greeting-badge q-mb-md inline-block">
                <q-chip color="teal-1" text-color="teal-9" icon="sunny" size="md" class="text-weight-medium" aria-label="Current greeting">
                  {{ greetingTime }}
                </q-chip>
              </div>
              <h1 class="text-h3 text-weight-bolder text-teal-10 q-mt-none q-mb-sm">
                Welcome back, <span class="text-teal-7">{{ firstName }}</span>
              </h1>
              <p class="text-subtitle1 text-grey-8 q-mb-lg max-width-500">
                Your health is our priority. Have a look at your dashboard for today's updates and appointments.
              </p>
              <div class="row q-gutter-sm">
                <q-btn 
                  unelevated 
                  color="teal-7" 
                  label="Book Appointment" 
                  icon="add_circle" 
                  class="rounded-lg q-px-md action-primary-btn"
                  @click="navigateTo('/patient-appointment-schedule')"
                  aria-label="Book a new appointment"
                />
                <q-btn 
                  outline 
                  color="negative" 
                  label="Emergency" 
                  icon="emergency" 
                  class="rounded-lg q-px-md emergency-btn"
                  @click="callEmergency"
                  aria-label="Emergency call button"
                >
                  <q-tooltip>Quick contact emergency services</q-tooltip>
                </q-btn>
              </div>
            </div>
            <div class="col-12 col-md-5 gt-sm text-right relative-position">
              <div class="hero-image-container">
                <q-img src="https://images.unsplash.com/photo-1576091160550-2173dba999ef?auto=format&fit=crop&q=80&w=800" class="hero-image rounded-xl shadow-10" alt="Healing atmosphere imagery" />
                <div class="floating-badge shadow-2">
                  <q-icon name="verified_user" color="teal-7" size="sm" />
                  <span class="text-caption text-weight-bold q-ml-xs">Verified Care</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Health Tip Section (New Patient-Centric Feature) -->
        <div class="health-tip-container q-mb-xl animate-fade-in" style="animation-delay: 0.2s">
          <q-card flat class="bg-teal-1 text-teal-10 rounded-xl overflow-hidden border-teal-2">
            <q-card-section class="row items-center q-pa-lg">
              <div class="col-auto q-mr-md">
                <div class="tip-icon-bg">
                  <q-icon name="lightbulb" size="md" color="amber-8" />
                </div>
              </div>
              <div class="col">
                <div class="text-subtitle2 text-weight-bolder text-uppercase letter-spacing-1 q-mb-xs">Health Tip of the Day</div>
                <div class="text-body1">{{ currentHealthTip }}</div>
              </div>
              <div class="col-auto gt-xs">
                <q-btn flat round icon="refresh" color="teal-7" @click="rotateHealthTip">
                  <q-tooltip>New Tip</q-tooltip>
                </q-btn>
              </div>
            </q-card-section>
          </q-card>
        </div>

        <!-- Live Queue Status -->
        <div class="q-mb-xl animate-fade-in" style="animation-delay: 0.3s">
          <div class="section-header q-mb-lg">
            <div class="text-h5 text-weight-bold text-teal-10">Live Queue Status</div>
            <div class="text-caption text-grey-7">Real-time updates from your current clinic</div>
          </div>
          <div class="row q-col-gutter-md">
            <div class="col-12 col-sm-6">
              <q-card class="queue-card now-serving-card text-white rounded-xl shadow-8 overflow-hidden" role="status" aria-live="polite">
                <q-card-section class="q-pa-lg relative-position">
                  <div class="text-overline text-weight-bolder opacity-70">NOW SERVING</div>
                  <div class="text-h2 text-weight-bolder q-my-sm animate-pulse">
                    {{ dashboardSummary?.nowServing ?? '—' }}
                  </div>
                  <div class="text-subtitle1 text-weight-medium row items-center">
                    <q-icon name="person" size="20px" class="q-mr-xs" aria-hidden="true" />
                    {{ dashboardSummary?.currentPatient ?? 'Waiting for update...' }}
                  </div>
                  <q-icon name="bolt" class="card-bg-icon" aria-hidden="true" />
                </q-card-section>
              </q-card>
            </div>
            <div class="col-12 col-sm-6">
              <q-card class="queue-card my-position-card text-white rounded-xl shadow-8 overflow-hidden" role="status">
                <q-card-section class="q-pa-lg relative-position">
                  <div class="text-overline text-weight-bolder opacity-70">YOUR POSITION</div>
                  <div class="text-h2 text-weight-bolder q-my-sm">
                    {{ dashboardSummary?.myPosition ?? '—' }}
                  </div>
                  <div class="text-subtitle1 text-weight-medium row items-center">
                    <q-icon name="hourglass_empty" size="20px" class="q-mr-xs" aria-hidden="true" />
                    Est. Wait: 15 mins
                  </div>
                  <q-icon name="timer" class="card-bg-icon" aria-hidden="true" />
                </q-card-section>
              </q-card>
            </div>
          </div>
        </div>

        <!-- Appointment History Redesigned -->
        <div class="q-mb-xl animate-fade-in" style="animation-delay: 1s" role="region" aria-label="Appointments Section">
          <div class="section-header row items-center justify-between q-mb-lg">
            <div>
              <div class="text-h5 text-weight-bold text-teal-10">Appointment Schedule</div>
              <div class="text-caption text-grey-7">Upcoming and recent medical visits</div>
            </div>
            <q-btn outline color="teal-7" label="View History" icon="history" class="rounded-lg" aria-label="View all appointment history" />
          </div>
          
          <div class="row q-col-gutter-md">
            <!-- Next Appointment -->
            <div class="col-12 col-md-6">
              <q-card 
                flat 
                bordered 
                class="appointment-card next-appt rounded-xl hover-shadow transition-all cursor-pointer animate-fade-in"
                style="animation-delay: 1.1s"
                @click="openNextApptModal"
                :class="{ 'empty-appt': !nextAppointment }"
                role="button"
                :aria-label="nextAppointment ? `Next appointment with Dr. ${nextAppointment.doctor}` : 'No upcoming appointments'"
              >
                <div class="appt-status-tag bg-teal-7 text-white text-overline text-weight-bold q-px-md" aria-hidden="true">UPCOMING</div>
                <q-card-section class="q-pa-xl">
                  <div v-if="nextAppointment">
                    <div class="row items-center no-wrap">
                      <q-avatar size="60px" class="q-mr-lg shadow-2">
                        <img src="https://cdn.quasar.dev/img/avatar.png" alt="Doctor's avatar" />
                      </q-avatar>
                      <div>
                        <div class="text-h6 text-weight-bolder text-teal-10">
                          {{ getAppointmentTypeLabel(nextAppointment.type) }}
                        </div>
                        <div class="text-subtitle2 text-grey-8">Dr. {{ nextAppointment.doctor || 'Amelia Chen' }}</div>
                      </div>
                    </div>
                    <q-separator class="q-my-lg opacity-30" />
                    <div class="row q-col-gutter-md">
                      <div class="col-6">
                        <div class="row items-center text-grey-7 q-mb-xs">
                          <q-icon name="calendar_today" size="xs" class="q-mr-xs" aria-hidden="true" />
                          <span class="text-caption text-weight-bold">DATE</span>
                        </div>
                        <div class="text-body1 text-weight-bold">{{ formatShortDate(nextAppointment.date) }}</div>
                      </div>
                      <div class="col-6">
                        <div class="row items-center text-grey-7 q-mb-xs">
                          <q-icon name="schedule" size="xs" class="q-mr-xs" aria-hidden="true" />
                          <span class="text-caption text-weight-bold">TIME</span>
                        </div>
                        <div class="text-body1 text-weight-bold">{{ formatTime(nextAppointment.time) }}</div>
                      </div>
                    </div>
                  </div>
                  <div v-else class="text-center q-py-md">
                    <q-icon name="event_busy" color="grey-4" size="64px" class="q-mb-md" aria-hidden="true" />
                    <div class="text-h6 text-grey-6">No upcoming appointments</div>
                    <q-btn flat color="teal-7" label="Schedule Now" @click.stop="navigateTo('/patient-appointment-schedule')" aria-label="Schedule a new appointment now" />
                  </div>
                </q-card-section>
              </q-card>
            </div>

            <!-- Last Appointment -->
            <div class="col-12 col-md-6">
              <q-card flat bordered class="appointment-card last-appt rounded-xl hover-shadow transition-all animate-fade-in" style="animation-delay: 1.2s" role="article" aria-label="Last past appointment">
                <div class="appt-status-tag bg-grey-6 text-white text-overline text-weight-bold q-px-md" aria-hidden="true">PAST VISIT</div>
                <q-card-section class="q-pa-xl">
                  <div v-if="lastAppointment">
                    <div class="row items-center no-wrap">
                      <q-avatar size="60px" class="q-mr-lg bg-grey-2">
                        <q-icon name="person" color="grey-6" aria-hidden="true" />
                      </q-avatar>
                      <div>
                        <div class="text-h6 text-weight-bolder text-grey-9">
                          {{ getAppointmentTypeLabel(lastAppointment.type) }}
                        </div>
                        <div class="text-subtitle2 text-grey-7">Dr. {{ lastAppointment.doctor || 'Amelia Chen' }}</div>
                      </div>
                    </div>
                    <q-separator class="q-my-lg opacity-30" />
                    <div class="row q-col-gutter-md">
                      <div class="col-6">
                        <div class="row items-center text-grey-7 q-mb-xs">
                          <q-icon name="calendar_today" size="xs" class="q-mr-xs" aria-hidden="true" />
                          <span class="text-caption text-weight-bold">DATE</span>
                        </div>
                        <div class="text-body1 text-weight-medium">{{ formatShortDate(lastAppointment.date) }}</div>
                      </div>
                      <div class="col-6 text-right">
                        <q-btn outline color="grey-7" size="sm" label="View Summary" class="rounded-lg q-mt-sm" aria-label="View visit summary" />
                      </div>
                    </div>
                  </div>
                  <div v-else class="text-center q-py-md">
                    <q-icon name="history" color="grey-3" size="64px" class="q-mb-md" aria-hidden="true" />
                    <div class="text-h6 text-grey-4">No previous visit records</div>
                  </div>
                </q-card-section>
              </q-card>
            </div>
          </div>
        </div>
      </q-page>
    </q-page-container>

    <!-- Fixed Bottom Navigation removed per request -->
     <PatientBottomNav />

    <!-- Mobile-Optimized Appointment Modal -->
    <q-dialog 
      v-model="showNextApptModal" 
      position="bottom"
      :maximized="$q.platform.is.mobile"
    >
      <q-card class="q-dialog-plugin">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">Next Appointment Details</div>
          <q-space />
          <q-btn 
            icon="close" 
            flat 
            round 
            dense 
            v-close-popup 
            color="grey-7"
          />
        </q-card-section>

        <q-card-section v-if="nextAppointment">
          <q-list>
            <q-item>
              <q-item-section avatar>
                <q-icon name="category" color="teal" />
              </q-item-section>
              <q-item-section>
                <q-item-label>Type</q-item-label>
                <q-item-label caption>{{ getAppointmentTypeLabel(nextAppointment.type || '') }}</q-item-label>
              </q-item-section>
            </q-item>

            <q-item>
              <q-item-section avatar>
                <q-icon name="business" color="teal" />
              </q-item-section>
              <q-item-section>
                <q-item-label>Department</q-item-label>
                <q-item-label caption>{{ getDepartmentLabel(nextAppointment.department || '') }}</q-item-label>
              </q-item-section>
            </q-item>

            <q-item>
              <q-item-section avatar>
                <q-icon name="person" color="teal" />
              </q-item-section>
              <q-item-section>
                <q-item-label>Doctor</q-item-label>
                <q-item-label caption>Dr. {{ nextAppointment.doctor || 'Amelia Chen' }}</q-item-label>
              </q-item-section>
            </q-item>

            <q-item>
              <q-item-section avatar>
                <q-icon name="event" color="teal" />
              </q-item-section>
              <q-item-section>
                <q-item-label>Date</q-item-label>
                <q-item-label caption>{{ formatLongDate(nextAppointment.date || '') }}</q-item-label>
              </q-item-section>
            </q-item>

            <q-item>
              <q-item-section avatar>
                <q-icon name="schedule" color="teal" />
              </q-item-section>
              <q-item-section>
                <q-item-label>Time</q-item-label>
                <q-item-label caption>{{ formatTime(nextAppointment.time || '') }}</q-item-label>
              </q-item-section>
            </q-item>

            <q-item>
              <q-item-section avatar>
                <q-icon name="description" color="teal" />
              </q-item-section>
              <q-item-section>
                <q-item-label>Reason</q-item-label>
                <q-item-label caption>{{ nextAppointment.reason || '—' }}</q-item-label>
              </q-item-section>
            </q-item>

            <q-item>
              <q-item-section avatar>
                <q-icon name="info" color="teal" />
              </q-item-section>
              <q-item-section>
                <q-item-label>Status</q-item-label>
                <q-item-label caption class="text-teal-700">{{ capitalize(nextAppointment.status || 'Upcoming') }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>

        <q-card-actions align="right" class="q-pa-md">
          <q-btn 
            flat 
            label="Close" 
            color="grey-7" 
            v-close-popup 
          />
          <q-btn 
            unelevated 
            label="View Details" 
            color="teal" 
            class="q-ml-sm"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from 'src/boot/axios'
import logoUrl from 'src/assets/logo.png'
import PatientBottomNav from 'src/components/PatientBottomNav.vue'

const router = useRouter()
// Footer state handled by shared PatientBottomNav component
const showUserMenu = ref(false)
const unreadCount = ref(0)
const highContrast = ref(false)
const largeText = ref(false)

const userName = computed(() => {
  try {
    const u = JSON.parse(localStorage.getItem('user') || '{}')
    return u.full_name || u.email || 'User'
  } catch (error) {
    console.warn('Failed to parse user from localStorage:', error)
    return 'User'
  }
})

const firstName = computed(() => {
  return userName.value.split(' ')[0]
})

const greetingTime = computed(() => {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good Morning'
  if (hour < 18) return 'Good Afternoon'
  return 'Good Evening'
})

const userInitials = computed(() => {
  const name = userName.value || ''
  const parts = name.trim().split(/\s+/)
  if (parts.length === 0) return 'U'
  const initials = parts.slice(0, 2).map((p: string) => p[0]?.toUpperCase() ?? '').join('')
  return initials || (name[0]?.toUpperCase() ?? 'U')
})

const toggleAccessibility = () => {
  highContrast.value = !highContrast.value
}

const toggleLargeText = () => {
  largeText.value = !largeText.value
}

// Health Tips Logic
const healthTips = [
  "Stay hydrated! Aim for at least 8 glasses of water a day.",
  "A 30-minute walk daily can significantly improve your cardiovascular health.",
  "Remember to take your prescribed medications at the same time every day.",
  "Prioritize sleep: 7-9 hours is ideal for physical and mental recovery.",
  "Include more leafy greens and fiber in your diet for better digestion.",
  "Practice mindfulness or deep breathing for 5 minutes to reduce stress."
]
const tipIndex = ref(Math.floor(Math.random() * healthTips.length))
const currentHealthTip = computed(() => healthTips[tipIndex.value])
const rotateHealthTip = () => {
  let next = tipIndex.value
  while (next === tipIndex.value) {
    next = Math.floor(Math.random() * healthTips.length)
  }
  tipIndex.value = next
}

const callEmergency = () => {
  window.open('tel:911', '_self')
}

interface DashboardSummary {
  nowServing: string | number
  currentPatient: string
  myPosition: string | number
}

const dashboardSummary = ref<DashboardSummary | null>(null)

const navigateTo = (path: string) => {
  void router.push(path)
}

const logout = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user')
  void router.push('/login')
}

// Appointment functionality
const showNextApptModal = ref(false)
// Use shared appointments store
import { useAppointmentsStore } from '../stores/appointments'
const appointmentsStore = useAppointmentsStore()
const nextAppointment = computed(() => appointmentsStore.nextAppointment)
const lastAppointment = computed(() => appointmentsStore.lastAppointment)

const getAppointmentTypeLabel = (type: string) => {
  const types: Record<string, string> = {
    'general': 'General Consultation',
    'specialist': 'Specialist Consultation',
    'follow_up': 'Follow-up Visit',
    'emergency': 'Emergency Visit'
  }
  return types[type] || 'General Consultation'
}

const getDepartmentLabel = (department: string) => {
  const departments: Record<string, string> = {
    'general': 'General Medicine',
    'cardiology': 'Cardiology',
    'neurology': 'Neurology',
    'pediatrics': 'Pediatrics'
  }
  return departments[department] || 'General Medicine'
}

const formatShortDate = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

const formatLongDate = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', { 
    weekday: 'long', 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric' 
  })
}

const formatTime = (timeStr?: string) => {
  if (!timeStr) return ''
  const [hours = '0', minutes = '00'] = timeStr.split(':')
  const hour = parseInt(hours, 10)
  const ampm = hour >= 12 ? 'PM' : 'AM'
  const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour
  return `${displayHour}:${minutes} ${ampm}`
}

const capitalize = (str: string) => {
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase()
}

const openNextApptModal = () => {
  if (nextAppointment.value) {
    showNextApptModal.value = true
  }
}

// Combined onMounted hook for all initialization
onMounted(async () => {
  // Load dashboard summary
  try {
    const res = await api.get('/operations/patient/dashboard/summary/', { params: { department: 'OPD' } })
    dashboardSummary.value = res.data as DashboardSummary
  } catch (error: unknown) {
    console.warn('Failed to fetch dashboard summary', error)
    dashboardSummary.value = {
      nowServing: '',
      currentPatient: '',
      myPosition: ''
    }
  }

  // Load appointments via store
  try {
    await appointmentsStore.loadAppointments()
  } catch (error: unknown) {
    console.warn('Failed to load appointments via store:', error)
  }

  // Initialize lucide icons from global CDN
  try {
    type Lucide = { createIcons: () => void }
    const lucideCandidate: unknown = (globalThis as Record<string, unknown>).lucide
    if (lucideCandidate && typeof (lucideCandidate as { createIcons?: unknown }).createIcons === 'function') {
      (lucideCandidate as Lucide).createIcons()
    }
  } catch (error: unknown) {
    console.warn('Lucide icons initialization error:', error)
  }
})
</script>

<style scoped>
.patient-bg {
  background-color: #f8fafb;
  min-height: 100vh;
}

/* Header Styling */
.main-header {
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.header-brand {
  line-height: 1.2;
}

/* Hero Section */
.hero-section {
  background: linear-gradient(135deg, #e0f2f1 0%, #f1f8e9 100%);
  position: relative;
  overflow: hidden;
}

.hero-image {
  height: 240px;
  width: 100%;
  object-fit: cover;
}

.greeting-badge {
  border-radius: 20px;
}

.max-width-500 {
  max-width: 500px;
}

/* Hero Image & Container */
.hero-image-container {
  position: relative;
  display: inline-block;
}

.hero-image {
  height: 280px;
  width: 100%;
  object-fit: cover;
  transition: transform 0.5s ease;
}

.hero-image-container:hover .hero-image {
  transform: scale(1.02);
}

.floating-badge {
  position: absolute;
  bottom: 20px;
  left: -20px;
  background: white;
  padding: 12px 20px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  border: 1px solid rgba(0, 121, 107, 0.1);
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0% { transform: translateY(0px); }
  50% { transform: translateY(-10px); }
  100% { transform: translateY(0px); }
}

/* Health Tip Styles */
.tip-icon-bg {
  width: 56px;
  height: 56px;
  background: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.letter-spacing-1 {
  letter-spacing: 1px;
}

.border-teal-2 {
  border: 1px solid #b2dfdb;
}

/* Card Styling */
.rounded-xl {
  border-radius: 24px;
}

.rounded-lg {
  border-radius: 16px;
}

.hover-shadow:hover {
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.08) !important;
  transform: translateY(-4px);
}

.transition-all {
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

/* Queue Cards */
.queue-card {
  min-height: 180px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.now-serving-card {
  background: linear-gradient(135deg, #00897b 0%, #00796b 100%);
}

.my-position-card {
  background: linear-gradient(135deg, #26a69a 0%, #00897b 100%);
}

.card-bg-icon {
  position: absolute;
  right: -20px;
  bottom: -20px;
  font-size: 120px;
  opacity: 0.1;
  transform: rotate(-15deg);
}

/* Appointment Cards */
.appointment-card {
  position: relative;
  overflow: hidden;
}

.appt-status-tag {
  position: absolute;
  top: 0;
  right: 0;
  border-bottom-left-radius: 12px;
}

.empty-appt {
  background-color: #f9f9f9;
  border-style: dashed;
}

/* Emergency Button Pulse */
.emergency-btn {
  border-width: 2px;
}

@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(198, 40, 40, 0.4); }
  70% { box-shadow: 0 0 0 10px rgba(198, 40, 40, 0); }
  100% { box-shadow: 0 0 0 0 rgba(198, 40, 40, 0); }
}

.emergency-btn:hover {
  animation: pulse 1.5s infinite;
}

/* Accessibility Modes */
.high-contrast {
  --q-primary: #000000 !important;
  --q-secondary: #000000 !important;
  background-color: #ffffff !important;
  color: #000000 !important;
}

.high-contrast .q-card,
.high-contrast .q-btn,
.high-contrast .hero-section {
  border: 2px solid #000 !important;
  background: #fff !important;
  color: #000 !important;
  box-shadow: none !important;
}

.high-contrast .text-teal-10,
.high-contrast .text-teal-9,
.high-contrast .text-teal-7,
.high-contrast .text-grey-7,
.high-contrast .text-grey-8 {
  color: #000 !important;
  font-weight: 800 !important;
}

.large-text {
  font-size: 1.25rem !important;
}

.large-text h1, .large-text .text-h3 { font-size: 4.5rem !important; line-height: 1.1; }
.large-text .text-h4 { font-size: 3.5rem !important; }
.large-text .text-h5 { font-size: 2.5rem !important; }
.large-text .text-h6 { font-size: 2rem !important; }
.large-text .text-subtitle1 { font-size: 1.75rem !important; }
.large-text .text-subtitle2 { font-size: 1.5rem !important; }
.large-text .text-body1 { font-size: 1.4rem !important; }
.large-text .text-caption { font-size: 1.2rem !important; }
.large-text .q-btn { padding: 12px 24px !important; }

/* Animations */
.animate-fade-in {
  animation: fadeIn 0.8s ease-out forwards;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-pulse {
  animation: q-pulse 2s infinite;
}

@keyframes q-pulse {
  0% { opacity: 1; }
  50% { opacity: 0.7; }
  100% { opacity: 1; }
}

/* Mobile Adjustments */
@media (max-width: 600px) {
  .hero-section {
    padding: 1.5rem;
  }
  
  .text-h3 {
    font-size: 2.25rem;
  }
  
  .queue-card {
    min-height: 150px;
  }
  
  .appointment-card .q-pa-xl {
    padding: 1.5rem;
  }
}
</style>
