<template>
  <q-layout view="hHh lpR fFf" :class="{ 'high-contrast': highContrast, 'large-text': largeText, 'ms-dark': darkMode }">
    <!-- Patient Portal Header -->
    <q-header class="bg-white text-teal-9">
      <q-toolbar>
        <q-avatar size="40px" class="q-mr-md">
          <img :src="logoUrl" alt="MediSync Logo" />
        </q-avatar>
        
        <div class="header-content"></div>

        <q-space />

        <q-btn flat round color="grey-7" icon="settings_accessibility" aria-label="Accessibility options">
          <q-menu transition-show="scale" transition-hide="scale">
            <q-list style="min-width: 220px">
              <q-item-label header>Accessibility</q-item-label>
              <q-item clickable v-ripple @click="toggleHighContrast" aria-label="Toggle high contrast mode">
                <q-item-section avatar>
                  <q-icon :name="highContrast ? 'visibility_off' : 'visibility'" :color="highContrast ? 'teal' : 'grey'" />
                </q-item-section>
                <q-item-section>High Contrast</q-item-section>
                <q-item-section side>
                  <q-toggle v-model="highContrast" color="teal" />
                </q-item-section>
              </q-item>
              <q-item clickable v-ripple @click="toggleLargeText" aria-label="Toggle larger text">
                <q-item-section avatar>
                  <q-icon name="text_fields" :color="largeText ? 'teal' : 'grey'" />
                </q-item-section>
                <q-item-section>Larger Text</q-item-section>
                <q-item-section side>
                  <q-toggle v-model="largeText" color="teal" />
                </q-item-section>
              </q-item>
              <q-item clickable v-ripple @click="toggleDarkMode" aria-label="Toggle dark mode">
                <q-item-section avatar>
                  <q-icon :name="darkMode ? 'dark_mode' : 'light_mode'" :color="darkMode ? 'teal' : 'grey'" />
                </q-item-section>
                <q-item-section>Dark Mode</q-item-section>
                <q-item-section side>
                  <q-toggle v-model="darkMode" color="teal" />
                </q-item-section>
              </q-item>
            </q-list>
          </q-menu>
          <q-tooltip>Accessibility Options</q-tooltip>
        </q-btn>

        <!-- Notification Icon -->
        <q-btn flat round icon="notifications" class="q-mr-sm" aria-label="Notifications">
          <q-badge v-if="unreadCount > 0" color="red" floating rounded>{{ unreadCount }}</q-badge>
        </q-btn>

        <!-- User Menu -->
        <q-btn flat round aria-label="User menu">
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

    <q-page-container>
      <q-page class="patient-bg q-pa-md pb-safe" :class="{ 'high-contrast': highContrast, 'large-text': largeText, 'ms-dark': darkMode }" role="main" aria-label="Notifications">
        <MsToastHost />
        <div class="max-w-4xl mx-auto">
          <!-- Search and Filter Section -->
          <q-card class="q-mb-md ms-card" flat bordered>
            <q-card-section class="q-pa-lg">
              <q-input
                v-model="searchQuery"
                outlined
                placeholder="Search notifications..."
                color="teal"
                clearable
                aria-label="Search notifications"
                class="ms-input"
              >
                <template #prepend>
                  <q-icon name="search" />
                </template>
              </q-input>
            </q-card-section>
            
            <q-card-section class="q-pt-none q-px-lg q-pb-lg">
              <div class="text-subtitle2 q-mb-sm">Filter Notifications</div>
              <q-scroll-area style="height: 60px">
                <div class="row no-wrap q-gutter-sm">
                  <q-chip
                    v-for="filter in filterOptions"
                    :key="filter.value"
                    :selected="activeTab === filter.value"
                    @click="activeTab = filter.value"
                    :color="activeTab === filter.value ? 'teal' : 'grey-3'"
                    :text-color="activeTab === filter.value ? 'white' : 'grey-8'"
                    clickable
                    class="ms-chip touch-target ms-focusable"
                    :aria-label="`Filter: ${filter.label}`"
                  >
                    <q-icon :name="getFilterIcon(filter.value)" class="q-mr-xs" />
                    {{ filter.label }}
                    <q-badge 
                      v-if="filter.count > 0" 
                      :color="activeTab === filter.value ? 'white' : 'teal'"
                      :text-color="activeTab === filter.value ? 'teal' : 'white'"
                      :label="filter.count"
                      class="q-ml-xs"
                    />
                  </q-chip>
                </div>
              </q-scroll-area>
            </q-card-section>
          </q-card>

          <!-- Notifications List -->
          <q-card class="ms-card" flat bordered>
            <q-card-section class="q-pa-lg">
              <div class="text-h6 text-weight-bold">
                {{ getFilterLabel() }} Notifications
                <q-badge color="grey-5" :label="filteredNotifications.length" class="q-ml-sm" />
              </div>
            </q-card-section>

            <q-card-section class="q-pt-none q-px-lg q-pb-lg">
              <div v-if="filteredNotifications.length === 0" class="text-center q-py-xl">
                <q-icon name="notifications_off" size="64px" color="grey-4" class="q-mb-md" />
                <div class="text-h6 text-weight-medium q-mb-sm">
                  No notifications found
                </div>
                <div class="text-body2">
                  Try adjusting your filters or search terms
                </div>
              </div>

              <q-list v-else separator>
                <q-item
                  v-for="n in filteredNotifications"
                  :key="n.id"
                  clickable
                  @click="openNotification(n)"
                  @touchstart="startLongPress(n, $event)"
                  @touchend="endLongPress"
                  class="notification-item q-pa-md ms-focusable"
                  :class="{ 'is-unread': !n.read, 'is-archived': !!n.archived }"
                  :aria-label="`Notification: ${n.title}`"
                >
                  <q-item-section side>
                    <q-icon
                      :name="getNotificationIcon(n.type)"
                      :color="n.read ? 'grey-5' : getNotificationColor(n.type)"
                      size="md"
                    />
                  </q-item-section>

                  <q-item-section>
                    <q-item-label
                      v-if="(n.title || '').toLowerCase() !== 'notification'"
                      class="text-weight-medium"
                    >
                      {{ n.title }}
                    </q-item-label>
                    <q-item-label
                      caption
                      lines="2"
                      :class="{ 'text-weight-medium': (n.title || '').toLowerCase() === 'notification' }"
                    >
                      {{ n.message }}
                    </q-item-label>
                    <q-item-label caption class="q-mt-xs">
                      {{ formatDate(n.createdAt) }} • {{ n.type }}
                      <q-badge v-if="n.archived" color="orange" label="Archived" class="q-ml-xs" />
                    </q-item-label>
                  </q-item-section>

                  <q-item-section side>
                    <div class="column items-center">
                      <q-icon
                        v-if="!n.read"
                        name="circle"
                        color="teal"
                        size="8px"
                        class="q-mb-xs"
                      />
                      <q-badge
                        v-if="n.archived"
                        color="orange"
                        label="Archived"
                      />
                      <q-btn
                        flat
                        round
                        icon="more_vert"
                        class="q-mt-sm touch-target ms-focusable"
                        aria-label="More notification actions"
                        @click.stop="openActionMenu(n)"
                      />
                    </div>
                  </q-item-section>
                </q-item>
              </q-list>
            </q-card-section>
          </q-card>
        </div>
      </q-page>
    </q-page-container>

    <!-- Long Press Action Menu -->
    <q-dialog v-model="showActionMenu" position="bottom">
      <q-card class="dialog-card-sm">
        <q-card-section class="q-pa-lg">
          <div class="text-h6 text-weight-bolder">Notification Actions</div>
          <div class="text-body2 text-grey-7 q-mt-xs">{{ selectedNotification?.title }}</div>
        </q-card-section>
        <q-separator />
        <q-card-section class="q-pa-md">
          <q-list class="q-gutter-sm">
            <q-btn
              v-if="!selectedNotification?.read"
              color="teal-7"
              unelevated
              class="full-width touch-target"
              label="Mark as Read"
              @click="markAsRead(selectedNotification)"
              aria-label="Mark notification as read"
            />
            <q-btn
              v-if="selectedNotification?.read"
              color="blue-6"
              unelevated
              class="full-width touch-target"
              label="Mark as Unread"
              @click="markAsUnread(selectedNotification)"
              aria-label="Mark notification as unread"
            />
            <q-btn
              v-if="!selectedNotification?.archived"
              color="orange-6"
              unelevated
              class="full-width touch-target"
              label="Archive"
              @click="archiveNotification(selectedNotification)"
              aria-label="Archive notification"
            />
            <q-btn
              v-if="selectedNotification?.archived"
              color="green-7"
              unelevated
              class="full-width touch-target"
              label="Unarchive"
              @click="unarchiveNotification(selectedNotification)"
              aria-label="Unarchive notification"
            />
            <q-btn
              color="negative"
              unelevated
              class="full-width touch-target"
              label="Delete"
              @click="deleteNotification(selectedNotification)"
              aria-label="Delete notification"
            />
          </q-list>
        </q-card-section>
        <q-card-actions align="center" class="q-pa-md">
          <q-btn flat color="teal-7" label="Close" v-close-popup class="touch-target" aria-label="Close actions" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Notification Detail Modal -->
    <q-dialog v-model="showNotificationDetail">
      <q-card class="dialog-card">
        <q-card-section class="q-pa-lg">
          <div class="text-h6 text-weight-bolder">Notification Details</div>
          <div class="text-body2 text-grey-7 q-mt-xs">{{ selectedNotification?.title }}</div>
        </q-card-section>
        <q-separator />
        <q-card-section class="q-pa-lg">
          <q-list dense class="q-gutter-sm">
            <q-item class="q-px-none">
              <q-item-section>Type</q-item-section>
              <q-item-section side class="text-weight-medium text-capitalize">{{ selectedNotification?.type }}</q-item-section>
            </q-item>
            <q-item class="q-px-none">
              <q-item-section>Date</q-item-section>
              <q-item-section side class="text-weight-medium">{{ formatDate(selectedNotification?.createdAt) }}</q-item-section>
            </q-item>
            <q-item class="q-px-none">
              <q-item-section>Status</q-item-section>
              <q-item-section side class="text-weight-medium">{{ selectedNotification?.read ? 'Read' : 'Unread' }}</q-item-section>
            </q-item>
            <q-item v-if="selectedNotification?.archived" class="q-px-none">
              <q-item-section>Archive</q-item-section>
              <q-item-section side class="text-weight-medium">Archived</q-item-section>
            </q-item>
          </q-list>
          <q-separator class="q-my-md" />
          <div class="text-subtitle2 q-mb-xs">Message</div>
          <div class="text-body2">{{ selectedNotification?.message }}</div>
        </q-card-section>
        <q-card-actions align="center" class="q-pa-md">
          <q-btn flat color="teal-7" label="Close" v-close-popup class="touch-target" aria-label="Close details" />
          <q-btn
            v-if="!selectedNotification?.read"
            unelevated
            color="teal-7"
            label="Mark as Read"
            class="touch-target"
            aria-label="Mark as read"
            @click="markAsRead(selectedNotification); showNotificationDetail = false"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <PatientBottomNav />
  </q-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { api } from 'src/boot/axios'
import logoUrl from 'src/assets/logo.png'
import MsToastHost from 'src/components/MsToastHost.vue'
import PatientBottomNav from 'src/components/PatientBottomNav.vue'
import { emitMsToast } from 'src/utils/toastBus'

const router = useRouter()
const $q = useQuasar()
const activeTab = ref<FilterValue>('all')
const searchQuery = ref('')
const showActionMenu = ref(false)
const showNotificationDetail = ref(false)
const selectedNotification = ref<Notification | null>(null)
const longPressTimer = ref<NodeJS.Timeout | null>(null)
const showUserMenu = ref(false)
const unreadCount = ref(0)
const highContrast = ref(false)
const largeText = ref(false)
const darkMode = ref(false)

const toast = (type: 'positive' | 'negative' | 'warning' | 'info', message: string) => {
  emitMsToast({ type, message, timeoutMs: 2500 })
}

const readBool = (key: string) => {
  const raw = localStorage.getItem(key)
  return raw === '1' || raw === 'true'
}

const persistBool = (key: string, value: boolean) => {
  localStorage.setItem(key, value ? '1' : '0')
}

const toggleHighContrast = () => { highContrast.value = !highContrast.value }
const toggleLargeText = () => { largeText.value = !largeText.value }
const toggleDarkMode = () => { darkMode.value = !darkMode.value }

// Queue websocket state - removed unused variables

interface Notification {
  id: number
  title: string
  message: string
  type: 'appointment' | 'queue' | 'medical' | 'info' | 'urgent'
  read: boolean
  archived?: boolean
  createdAt: string
}

// Filter value type to align template interactions
type FilterValue = 'all' | 'unread' | 'read' | 'appointments' | 'queue' | 'medical' | 'archived'

const notifications = ref<Notification[]>([])

// WebSocket for real-time medication notifications on this page
let medicationWS: WebSocket | null = null

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

// unread count now handled by PatientBottomNav

// Filter options for the vertical sidebar
const filterOptions = computed((): { value: FilterValue; label: string; icon: string; count: number }[] => [
  { value: 'all', label: 'All', icon: 'bell', count: notifications.value.length },
  { value: 'unread', label: 'Unread', icon: 'mail', count: notifications.value.filter(n => !n.read).length },
  { value: 'read', label: 'Read', icon: 'mail-check', count: notifications.value.filter(n => n.read).length },
  { value: 'appointments', label: 'Appointments', icon: 'calendar', count: notifications.value.filter(n => n.type === 'appointment').length },
  { value: 'queue', label: 'Queue', icon: 'list-ordered', count: notifications.value.filter(n => n.type === 'queue').length },
  { value: 'medical', label: 'Medical', icon: 'heart', count: notifications.value.filter(n => n.type === 'medical').length },
  { value: 'archived', label: 'Archived', icon: 'archive', count: notifications.value.filter(n => n.archived).length }
])

const getFilterLabel = () => {
  const filter = filterOptions.value.find(f => f.value === activeTab.value)
  return filter ? filter.label : 'All'
}

// Declare window interface for lucide
interface WindowWithLucide extends Window {
  lucide?: {
    createIcons(): void
  }
}

const setupMedicationWS = (): void => {
  try {
    const userStr = localStorage.getItem('user') || '{}'
    const userObj = JSON.parse(userStr)
    const patientId: number | undefined = userObj?.patient_profile?.id
    if (!patientId) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const base = new URL(api.defaults.baseURL || `http://${window.location.hostname}:8000`)
    const backendHost = base.hostname
    const backendPort = base.port || '8000'
    const wsUrl = `${protocol}//${backendHost}:${backendPort}/ws/medication/${patientId}/`

    const ws = new WebSocket(wsUrl)
    medicationWS = ws
    ws.onmessage = async (evt: MessageEvent) => {
      try {
        const data = JSON.parse(evt.data)
        if (data?.type === 'medication_notification') {
          const payload = data.notification || {}
          // Create a readable notification entry locally
          const title = 'Medication Dispensed'
          const message = `${payload?.medicine?.name || 'Medicine'} | Qty: ${payload?.quantity ?? ''}`
          const createdAt = payload?.dispensed_at || new Date().toISOString()
          const newItem: Notification = {
            id: Date.now(), // temporary id for UI; real id will come from REST
            title,
            message,
            type: 'medical',
            read: false,
            archived: false,
            createdAt
          }
          notifications.value = [newItem, ...notifications.value]
          // Sync with backend to get persisted notification and badge alignment
          await fetchNotifications()
        }
      } catch {
        // ignore
      }
    }
    ws.onclose = () => {
      setTimeout(() => {
        try { setupMedicationWS() } catch { /* ignore */ }
      }, 5000)
    }
  } catch {
    // ignore
  }
}

onMounted(async () => {
  highContrast.value = readBool('ms_patient_high_contrast')
  largeText.value = readBool('ms_patient_large_text')
  darkMode.value = readBool('ms_patient_dark_mode')
  $q.dark.set(darkMode.value)

  await fetchNotifications()
  try { (window as WindowWithLucide).lucide?.createIcons() } catch (e) { console.warn('lucide icons init failed', e) }
  try {
    const res = await api.get('/patient/notifications/unread-count/')
    unreadCount.value = res.data?.count ?? 0
  } catch (e) {
    console.warn('unread count fetch failed', e)
    unreadCount.value = 0
  }
  setupMedicationWS()
})

onUnmounted(() => {
  try { 
    if (medicationWS) medicationWS.close() 
  } catch (error) {
    // Ignore WebSocket close errors during cleanup
    console.debug('WebSocket close error during cleanup:', error)
  }
  medicationWS = null
})

const fetchNotifications = async () => {
  try {
    const res = await api.get('/operations/notifications/')
    type NotificationDTO = { id: number; message?: string; is_read?: boolean; created_at?: string }
    const raw = (res.data?.results ?? res.data ?? []) as NotificationDTO[]
    notifications.value = raw.map((n) => ({
      id: n.id,
      title: 'Notification',
      message: n.message ?? '',
      type: 'info',
      read: !!n.is_read,
      archived: false,
      createdAt: n.created_at ?? new Date().toISOString()
    }))
  } catch (e) {
    console.warn('Failed to fetch notifications', e)
    toast('warning', 'Unable to load notifications. Showing local sample data.')
    notifications.value = [
      { 
        id: 1, 
        title: 'Upcoming appointment', 
        message: 'You have an appointment tomorrow at 10:00 AM with Dr. Smith for your regular checkup.', 
        type: 'appointment', 
        read: false,
        archived: false,
        createdAt: new Date(Date.now() - 3600000).toISOString()
      },
      { 
        id: 2, 
        title: 'Queue update', 
        message: 'Your position in the queue has moved up to 3. Estimated wait time: 15 minutes.', 
        type: 'queue', 
        read: false,
        archived: false,
        createdAt: new Date(Date.now() - 1800000).toISOString()
      },
      { 
        id: 3, 
        title: 'Lab result ready', 
        message: 'Your blood test results are now available. Please check your medical records.', 
        type: 'medical', 
        read: true,
        archived: false,
        createdAt: new Date(Date.now() - 86400000).toISOString()
      },
      { 
        id: 4, 
        title: 'Appointment reminder', 
        message: 'Don\'t forget your appointment with Dr. Johnson tomorrow at 2:00 PM.', 
        type: 'appointment', 
        read: true,
        archived: true,
        createdAt: new Date(Date.now() - 172800000).toISOString()
      },
    ]
  }
}

const markRead = async (n: Notification) => {
  try {
    await api.patch(`/operations/notifications/${n.id}/mark-read/`)
    n.read = true
    toast('positive', 'Marked as read.')
  } catch (e) {
    console.warn('Failed to mark notification as read', e)
    n.read = true
    toast('info', 'Marked as read.')
  }
}

// Bulk mark-all-read can be implemented via a future menu action

const filteredNotifications = computed(() => {
  let filtered = notifications.value

  // Apply filter
  switch (activeTab.value) {
    case 'unread':
      filtered = filtered.filter(n => !n.read)
      break
    case 'read':
      filtered = filtered.filter(n => n.read)
      break
    case 'appointments':
      filtered = filtered.filter(n => n.type === 'appointment')
      break
    case 'queue':
      filtered = filtered.filter(n => n.type === 'queue')
      break
    case 'medical':
      filtered = filtered.filter(n => n.type === 'medical')
      break
    case 'archived':
      filtered = filtered.filter(n => n.archived)
      break
    // 'all' shows everything
  }

  // Apply search
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(n => 
      n.title.toLowerCase().includes(query) || 
      n.message.toLowerCase().includes(query)
    )
  }

  return filtered
})

// Functions for Quasar components
const getFilterIcon = (value: FilterValue) => {
  switch (value) {
    case 'all': return 'notifications'
    case 'unread': return 'mark_email_unread'
    case 'read': return 'mark_email_read'
    case 'appointments': return 'event'
    case 'queue': return 'people'
    case 'medical': return 'local_hospital'
    case 'archived': return 'archive'
    default: return 'notifications'
  }
}

const getNotificationIcon = (type: Notification['type']) => {
  switch (type) {
    case 'appointment': return 'event'
    case 'queue': return 'people'
    case 'medical': return 'local_hospital'
    case 'urgent': return 'warning'
    case 'info': return 'info'
    default: return 'notifications'
  }
}

const getNotificationColor = (type: Notification['type']) => {
  switch (type) {
    case 'appointment': return 'blue'
    case 'queue': return 'indigo'
    case 'medical': return 'red'
    case 'urgent': return 'orange'
    case 'info': return 'grey'
    default: return 'grey'
  }
}

const formatDate = (dateString?: string) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  const now = new Date()
  const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60)
  if (diffInHours < 1) {
    return 'Just now'
  } else if (diffInHours < 24) {
    return `${Math.floor(diffInHours)}h ago`
  } else if (diffInHours < 48) {
    return 'Yesterday'
  } else {
    return date.toLocaleDateString()
  }
}

// Long press functionality
const startLongPress = (notification: Notification, event: Event) => {
  if ((event as TouchEvent).touches) event.preventDefault()
  selectedNotification.value = notification
  longPressTimer.value = setTimeout(() => {
    showActionMenu.value = true
  }, 500) // 500ms long press
}

const endLongPress = () => {
  if (longPressTimer.value) {
    clearTimeout(longPressTimer.value)
    longPressTimer.value = null
  }
}

// Notification actions
const openNotification = (notification: Notification) => {
  selectedNotification.value = notification
  showNotificationDetail.value = true
  // Auto-mark as read when opened
  if (!notification.read) {
    void markRead(notification)
  }
}

const openActionMenu = (notification: Notification) => {
  selectedNotification.value = notification
  showActionMenu.value = true
}

// Actions below complement single markRead behavior

const markAsRead = (n: Notification | null) => {
  if (!n) return
  // Delegate to markRead which handles backend and local state
  void markRead(n)
  showActionMenu.value = false
}

const markAsUnread = (n: Notification | null) => {
  if (!n) return
  // No backend endpoint; update locally
  n.read = false
  showActionMenu.value = false
  toast('info', 'Marked as unread.')
}

const archiveNotification = (n: Notification | null) => {
  if (!n) return
  // No backend archive endpoint; update locally
  n.archived = true
  showActionMenu.value = false
  toast('positive', 'Archived.')
}

const unarchiveNotification = (n: Notification | null) => {
  if (!n) return
  // No backend unarchive endpoint; update locally
  n.archived = false
  showActionMenu.value = false
  toast('info', 'Unarchived.')
}

const deleteNotification = (n: Notification | null) => {
  if (!n) return
  // No backend delete endpoint; remove locally
  notifications.value = notifications.value.filter(x => x.id !== n.id)
  showActionMenu.value = false
  toast('warning', 'Deleted.')
}

const navigateTo = (path: string) => {
  void router.push(path)
}

const logout = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user')
  void router.push('/login')
}

watch(highContrast, (val) => persistBool('ms_patient_high_contrast', val))
watch(largeText, (val) => persistBool('ms_patient_large_text', val))
watch(darkMode, (val) => {
  persistBool('ms_patient_dark_mode', val)
  $q.dark.set(val)
})
</script>

<style scoped>
.patient-bg {
  --ms-bg: #f8fafb;
  --ms-card: #ffffff;
  --ms-text: #0f172a;
  --ms-muted: #5b6472;
  --ms-border: rgba(15, 23, 42, 0.08);
  --ms-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
  --ms-shadow-hover: 0 16px 40px rgba(15, 23, 42, 0.10);
  --ms-focus: rgba(38, 166, 154, 0.55);
  background: var(--ms-bg);
  color: var(--ms-text);
  min-height: 100vh;
}

.ms-dark {
  --ms-bg: #0b1220;
  --ms-card: #111a2e;
  --ms-text: #e6edf6;
  --ms-muted: #aeb9c8;
  --ms-border: rgba(230, 237, 246, 0.12);
  --ms-shadow: 0 10px 28px rgba(0, 0, 0, 0.35);
  --ms-shadow-hover: 0 18px 44px rgba(0, 0, 0, 0.45);
  --ms-focus: rgba(255, 255, 255, 0.8);
}

.high-contrast {
  --ms-bg: #ffffff;
  --ms-card: #ffffff;
  --ms-text: #000000;
  --ms-muted: #000000;
  --ms-border: #000000;
  --ms-shadow: none;
  --ms-shadow-hover: none;
  --ms-focus: #000000;
}

.large-text {
  font-size: 18px;
}

.ms-card {
  background: var(--ms-card);
  border: 1px solid var(--ms-border);
  border-radius: 20px;
  box-shadow: var(--ms-shadow);
}

.ms-chip {
  border-radius: 999px;
  transition: transform 160ms ease, box-shadow 160ms ease;
}

.notification-item {
  border: 1px solid var(--ms-border);
  border-radius: 18px;
  background: var(--ms-card);
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
  transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
}

.notification-item:hover {
  transform: translateY(-1px);
  box-shadow: var(--ms-shadow-hover);
}

.notification-item.is-unread {
  border-color: rgba(38, 166, 154, 0.35);
  background: rgba(38, 166, 154, 0.06);
}

.notification-item.is-archived {
  opacity: 0.8;
}

.dialog-card,
.dialog-card-sm {
  width: 100%;
  border-radius: 20px;
  background: var(--ms-card);
  border: 1px solid var(--ms-border);
}

.dialog-card {
  max-width: 680px;
}

.dialog-card-sm {
  max-width: 520px;
}

.touch-target {
  min-height: 44px;
}

.ms-focusable:focus-visible {
  outline: 3px solid var(--ms-focus);
  outline-offset: 2px;
}

@media (max-width: 768px) {
  .dialog-card,
  .dialog-card-sm {
    max-width: 95vw;
  }
}
</style>
