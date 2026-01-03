<template>
  <q-footer class="patient-bottom-nav">
    <div class="nav-safe-area"></div>

    <div class="nav-wrapper">
      <!-- Pill container with icons -->
      <div class="nav-pill">
        <div
          v-for="item in items"
          :key="item.key"
          class="nav-pill-item"
        >
          <q-btn
            flat
            round
            class="nav-icon-btn"
            :class="{ active: isActive(item.to) }"
            :to="item.to"
          >
            <q-icon :name="item.icon" />
            <q-badge
              v-if="item.key === 'alerts' && unreadCount > 0"
              color="red"
              floating
              rounded
            >{{ unreadCount }}</q-badge>
          </q-btn>
          <div class="nav-label">{{ item.label }}</div>
        </div>
      </div>
      <!-- Labels moved inside each pill item -->
    </div>
  </q-footer>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from 'src/boot/axios'

const route = useRoute()

const unreadCount = ref<number>(0)

// WebSocket for medication alerts; module scope to manage lifecycle
let medicationWS: WebSocket | null = null

const items = [
  { key: 'queue', label: 'queue', icon: 'format_list_numbered', to: '/patient-queue' },
  { key: 'appointments', label: 'appointment', icon: 'event', to: '/patient-appointment-schedule' },
  { key: 'home', label: 'home', icon: 'home', to: '/patient-dashboard' },
  { key: 'alerts', label: 'alert', icon: 'notifications', to: '/patient-notifications' }
]

const isActive = (to: string) => route.path === to

const fetchUnreadCount = async () => {
  try {
    const token = localStorage.getItem('access_token')
    if (!token) {
      unreadCount.value = 0
      return
    }
    const resp = await api.get('/operations/messaging/notifications/', {
      params: { unread_only: true }
    })
    const data = Array.isArray(resp.data) ? resp.data : []
    unreadCount.value = data.length
  } catch {
    // Silent failure to avoid UI noise; keep previous value
  }
}

const setupMedicationWS = (): void => {
  try {
    const userStr = localStorage.getItem('user') || '{}'
    const userObj = JSON.parse(userStr)
    const patientId: number | undefined = userObj?.patient_profile?.id
    if (!patientId) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const base = new URL(api.defaults.baseURL || `http://${window.location.hostname}:8000/api`)
    const backendHost = base.hostname
    const backendPort = base.port || '8000'
    const wsUrl = `${protocol}//${backendHost}:${backendPort}/ws/medication/${patientId}/`
    const httpProtocol = window.location.protocol === 'https:' ? 'https:' : 'http:'
    const httpProbeUrl = `${httpProtocol}//${backendHost}:${backendPort}/ws/medication/${patientId}/`

    // [2025-10-31] Preflight HEAD probe added to avoid noisy browser
    // WebSocket errors when Channels routes are unavailable (dev environments)
    fetch(httpProbeUrl, { method: 'HEAD' }).then((res) => {
      if (!res.ok) {
        // Endpoint not available; skip WebSocket setup silently
        return
      }
      const ws = new WebSocket(wsUrl)
      medicationWS = ws
      ws.onopen = () => {
        // Connected to medication channel
      }
      ws.onmessage = async (evt: MessageEvent) => {
        try {
          const data = JSON.parse(evt.data)
          if (data?.type === 'medication_notification') {
            // Increment badge and refresh from backend to keep in sync
            unreadCount.value = (unreadCount.value || 0) + 1
            await fetchUnreadCount()
          }
        } catch {
          // Ignore parse errors
        }
      }
      ws.onclose = () => {
        // Attempt lightweight reconnect after a delay
        setTimeout(() => {
          try { setupMedicationWS() } catch { /* ignore */ }
        }, 5000)
      }
    }).catch(() => {
      // Probe failed; skip connecting
    })
  } catch {
    // Ignore setup errors
  }
}

onMounted(() => {
  void fetchUnreadCount()
  setupMedicationWS()
})

onUnmounted(() => {
  try {
    if (medicationWS) medicationWS.close()
  } catch {
    // ignore
  } finally {
    medicationWS = null
  }
})
</script>

<style scoped>
/* Safe area for modern phones */
.nav-safe-area {
  height: env(safe-area-inset-bottom);
}

.patient-bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  width: 100%;
  z-index: 1000;
  /* Light gray background for the bottom navigation area */
  background: #f3f4f6;
  padding: 8px 10px 16px;
}

.nav-wrapper {
  width: 100%;
  max-width: 900px;
  margin: 0 auto;
}

/* Pill container matching the sample: soft background, rounded, subtle shadow */
.nav-pill {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: #f5f5f7; /* light card */
  border-radius: 22px;
  padding: 12px 16px;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.06);
}

.nav-pill-item {
  flex: 1 1 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.nav-icon-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s ease;
}

.nav-icon-btn:hover {
  background-color: #8fdbd3;
}

.nav-icon-btn.active {
  background-color:#8fdbd3;
}

.nav-icon-btn .q-icon {
  font-family: 'Material Icons' !important;
  font-style: normal !important;
  font-weight: normal !important;
  font-size: 20px;
  line-height: 1;
  display: inline-block;
  color: #000 !important;
  text-shadow: 1px 1px 0 rgba(0, 0, 0, 0.18);
}

/* Labels below the pill */
.nav-label {
  margin-top: 6px;
  text-align: center;
  font-size: 12px;
  font-weight: 600;
  color: #000; /* black labels */
  text-transform: capitalize;
}

/* Responsive tweaks */
@media (max-width: 600px) {
  .patient-bottom-nav {
    padding: 8px 10px 26px;
  }
  .nav-pill {
    padding: 10px 14px;
  }
  .nav-icon-btn {
    width: 42px;
    height: 42px;
  }
  .nav-icon-btn .q-icon {
    font-size: 19px;
  }
  .nav-label {
    font-size: 12px;
  }
}
</style>