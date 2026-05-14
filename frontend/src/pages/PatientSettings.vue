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

    <q-page-container>
      <q-page 
              :class="{ 
                'patient-bg q-pa-md settings-page': true,
                'q-pa-sm': $q.screen.xs,
                'ios-safe-area': $q.platform.is.ios,
                'android-safe-area': $q.platform.is.android
              }"
              style="padding-bottom: 80px;">
        <!-- Profile Section -->
        <q-card class="q-mb-md" flat bordered>
          <q-card-section>
            <div class="text-h6 text-teal-800 q-mb-md">
              <q-icon name="person" class="q-mr-sm" />
              Profile Information
            </div>
            
            <div class="row q-col-gutter-md">
              <div class="col-12 text-center q-mb-md">
                <q-avatar size="80px" class="q-mb-sm">
                  <img v-if="userProfile.avatar" :src="userProfile.avatar" />
                  <div v-else class="bg-teal-800 text-white text-h5">
                    {{ userInitials }}
                  </div>
                </q-avatar>
                <q-btn 
                  flat 
                  round 
                  icon="camera_alt" 
                  size="sm" 
                  color="teal"
                  @click="uploadAvatar"
                  class="q-ml-sm"
                />
              </div>
              
              <div class="col-12">
                <q-input
                  v-model="userProfile.fullName"
                  label="Full Name"
                  outlined
                  dense
                  :readonly="!editMode"
                />
              </div>
              
              <div class="col-12">
                <q-input
                  v-model="userProfile.email"
                  label="Email"
                  outlined
                  dense
                  type="email"
                  :readonly="!editMode"
                />
              </div>
              
              <div class="col-12">
                <q-input
                  v-model="userProfile.phone"
                  label="Phone Number"
                  outlined
                  dense
                  :readonly="!editMode"
                />
              </div>
              
              <div class="col-12">
                <q-input
                  v-model="userProfile.dateOfBirth"
                  label="Date of Birth"
                  outlined
                  dense
                  type="date"
                  :readonly="!editMode"
                />
              </div>
            </div>
            
            <div class="q-mt-md text-right">
              <q-btn 
                v-if="!editMode"
                flat 
                color="teal" 
                icon="edit"
                label="Edit Profile"
                @click="editMode = true"
              />
              <div v-else class="q-gutter-sm">
                <q-btn 
                  flat 
                  color="grey" 
                  label="Cancel"
                  @click="cancelEdit"
                />
                <q-btn 
                  color="teal" 
                  label="Save Changes"
                  @click="saveProfile"
                />
              </div>
            </div>
          </q-card-section>
        </q-card>

        <!-- Notification Settings -->
        <q-card class="q-mb-md" flat bordered>
          <q-card-section>
            <div class="text-h6 text-teal-800 q-mb-md">
              <q-icon name="notifications" class="q-mr-sm" />
              Notification Preferences
            </div>
            
            <q-list>
              <q-item>
                <q-item-section>
                  <q-item-label>Appointment Reminders</q-item-label>
                  <q-item-label caption>Get notified about upcoming appointments</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-toggle 
                    v-model="notificationSettings.appointments" 
                    color="teal"
                  />
                </q-item-section>
              </q-item>
              
              <q-item>
                <q-item-section>
                  <q-item-label>Queue Updates</q-item-label>
                  <q-item-label caption>Receive updates about your queue position</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-toggle 
                    v-model="notificationSettings.queueUpdates" 
                    color="teal"
                  />
                </q-item-section>
              </q-item>
              
              <q-item>
                <q-item-section>
                  <q-item-label>Medical Alerts</q-item-label>
                  <q-item-label caption>Important health and medical notifications</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-toggle 
                    v-model="notificationSettings.medicalAlerts" 
                    color="teal"
                  />
                </q-item-section>
              </q-item>
              
              <q-item>
                <q-item-section>
                  <q-item-label>SMS Notifications</q-item-label>
                  <q-item-label caption>Receive notifications via SMS</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-toggle 
                    v-model="notificationSettings.sms" 
                    color="teal"
                  />
                </q-item-section>
              </q-item>
            </q-list>
          </q-card-section>
        </q-card>

        <!-- Privacy & Security -->
        <q-card class="q-mb-md" flat bordered>
          <q-card-section>
            <div class="text-h6 text-teal-800 q-mb-md">
              <q-icon name="security" class="q-mr-sm" />
              Privacy & Security
            </div>
            
            <q-list>
              <q-item clickable @click="changePassword">
                <q-item-section avatar>
                  <q-icon name="lock" color="teal" />
                </q-item-section>
                <q-item-section>
                  <q-item-label>Change Password</q-item-label>
                  <q-item-label caption>Update your account password</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-icon name="chevron_right" />
                </q-item-section>
              </q-item>
              
              <q-item>
                <q-item-section avatar>
                  <q-icon name="fingerprint" color="teal" />
                </q-item-section>
                <q-item-section>
                  <q-item-label>Biometric Login</q-item-label>
                  <q-item-label caption>Use fingerprint or face ID to login</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-toggle 
                    v-model="securitySettings.biometric" 
                    color="teal"
                  />
                </q-item-section>
              </q-item>
              
              <q-item>
                <q-item-section avatar>
                  <q-icon name="visibility" color="teal" />
                </q-item-section>
                <q-item-section>
                  <q-item-label>Profile Visibility</q-item-label>
                  <q-item-label caption>Control who can see your profile</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-select
                    v-model="securitySettings.profileVisibility"
                    :options="visibilityOptions"
                    dense
                    outlined
                    style="min-width: 120px"
                  />
                </q-item-section>
              </q-item>
            </q-list>
          </q-card-section>
        </q-card>

        <!-- App Preferences -->
        <q-card class="q-mb-md" flat bordered>
          <q-card-section>
            <div class="text-h6 text-teal-800 q-mb-md">
              <q-icon name="settings" class="q-mr-sm" />
              App Preferences
            </div>
            
            <q-list>
              <q-item>
                <q-item-section>
                  <q-item-label>Dark Mode</q-item-label>
                  <q-item-label caption>Switch to dark theme</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-toggle 
                    v-model="appSettings.darkMode" 
                    color="teal"
                    @update:model-value="toggleDarkMode"
                  />
                </q-item-section>
              </q-item>
              
              <q-item>
                <q-item-section>
                  <q-item-label>Language</q-item-label>
                  <q-item-label caption>Choose your preferred language</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-select
                    v-model="appSettings.language"
                    :options="languageOptions"
                    dense
                    outlined
                    style="min-width: 120px"
                  />
                </q-item-section>
              </q-item>
              
              <q-item>
                <q-item-section>
                  <q-item-label>Font Size</q-item-label>
                  <q-item-label caption>Adjust text size for better readability</q-item-label>
                </q-item-section>
                <q-item-section side class="q-px-md" style="min-width: 150px">
                  <q-slider
                    v-model="appSettings.fontSize"
                    :min="12"
                    :max="20"
                    :step="1"
                    color="teal"
                    label
                    label-always
                  />
                </q-item-section>
              </q-item>
              
              <q-item>
                <q-item-section>
                  <q-item-label>Auto-refresh</q-item-label>
                  <q-item-label caption>Automatically refresh data</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-toggle 
                    v-model="appSettings.autoRefresh" 
                    color="teal"
                  />
                </q-item-section>
              </q-item>
            </q-list>
          </q-card-section>
        </q-card>

        <!-- Support & Help -->
        <q-card class="q-mb-md" flat bordered>
          <q-card-section>
            <div class="text-h6 text-teal-800 q-mb-md">
              <q-icon name="help" class="q-mr-sm" />
              Support & Help
            </div>
            
            <q-list>
              <q-item clickable @click="openHelp">
                <q-item-section avatar>
                  <q-icon name="help_outline" color="teal" />
                </q-item-section>
                <q-item-section>
                  <q-item-label>Help Center</q-item-label>
                  <q-item-label caption>Find answers to common questions</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-icon name="chevron_right" />
                </q-item-section>
              </q-item>
              
              <q-item clickable @click="contactSupport">
                <q-item-section avatar>
                  <q-icon name="support_agent" color="teal" />
                </q-item-section>
                <q-item-section>
                  <q-item-label>Contact Support</q-item-label>
                  <q-item-label caption>Get help from our support team</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-icon name="chevron_right" />
                </q-item-section>
              </q-item>
              
              <q-item clickable @click="showAbout">
                <q-item-section avatar>
                  <q-icon name="info" color="teal" />
                </q-item-section>
                <q-item-section>
                  <q-item-label>About MediSync</q-item-label>
                  <q-item-label caption>App version and information</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-icon name="chevron_right" />
                </q-item-section>
              </q-item>
            </q-list>
          </q-card-section>
        </q-card>
      </q-page>
    </q-page-container>

    <PatientBottomNav />
  </q-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { api } from 'src/boot/axios'
import logoUrl from 'src/assets/logo.png'
import PatientBottomNav from 'src/components/PatientBottomNav.vue'

const router = useRouter()
const $q = useQuasar()

// Navigation and UI state
const showUserMenu = ref(false)
const unreadCount = ref<number>(0)

// Profile editing state
const editMode = ref(false)
const originalProfile = ref({
  fullName: '',
  email: '',
  phone: '',
  dateOfBirth: '',
  avatar: ''
})

// User profile data
const userProfile = ref({
  fullName: '',
  email: '',
  phone: '',
  dateOfBirth: '',
  avatar: ''
})

// Notification settings
const notificationSettings = ref({
  appointments: false,
  queueUpdates: false,
  medicalAlerts: false,
  sms: false
})

// Security settings
const securitySettings = ref({
  biometric: false,
  profileVisibility: ''
})

// App preferences
const appSettings = ref({
  darkMode: false,
  language: '',
  fontSize: 16,
  autoRefresh: false
})

// Options for dropdowns
const visibilityOptions = [
  'Healthcare Providers Only',
  'Public',
  'Private'
]

const languageOptions = [
  'English',
  'Spanish',
  'French',
  'German'
]

// Computed properties
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

// Navigation functions
const navigateTo = (path: string) => { 
  void router.push(path) 
}

const logout = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user')
  void router.push('/login')
}

// Profile management functions
const uploadAvatar = () => {
  $q.notify({
    message: 'Avatar upload feature coming soon!',
    color: 'info',
    position: 'top'
  })
}

const cancelEdit = () => {
  editMode.value = false
  userProfile.value = { ...originalProfile.value }
}

const saveProfile = async () => {
  try {
    // API call to save profile would go here
    await api.put('/patient/profile/', userProfile.value)
    
    editMode.value = false
    originalProfile.value = { ...userProfile.value }
    
    $q.notify({
      message: 'Profile updated successfully!',
      color: 'positive',
      position: 'top'
    })
  } catch (error) {
    console.error('Profile save error:', error)
    $q.notify({
      message: 'Failed to update profile. Please try again.',
      color: 'negative',
      position: 'top'
    })
  }
}

// Security functions
const changePassword = () => {
  $q.dialog({
    title: 'Change Password',
    message: 'This feature will redirect you to the password change page.',
    ok: 'Continue',
    cancel: 'Cancel'
  }).onOk(() => {
    navigateTo('/change-password')
  })
}

// App preference functions
const toggleDarkMode = (value: boolean) => {
  $q.dark.set(value)
  localStorage.setItem('darkMode', value.toString())
}

// Support functions
const openHelp = () => {
  $q.notify({
    message: 'Opening help center...',
    color: 'info',
    position: 'top'
  })
}

const contactSupport = () => {
  $q.notify({
    message: 'Contact support feature coming soon!',
    color: 'info',
    position: 'top'
  })
}

const showAbout = () => {
  $q.dialog({
    title: 'About MediSync',
    message: 'A comprehensive healthcare management platform designed to streamline patient care and improve healthcare accessibility.',
    ok: 'Close'
  })
}

// Load user data
const loadUserProfile = async () => {
  try {
    const response = await api.get('/patient/profile/')
    userProfile.value = response.data
    originalProfile.value = { ...response.data }
  } catch (error) {
    console.error('Failed to load user profile:', error)
  }
}

const loadNotificationSettings = async () => {
  try {
    const response = await api.get('/patient/notification-settings/')
    notificationSettings.value = response.data
  } catch (error) {
    console.error('Failed to load notification settings:', error)
  }
}

const loadAppSettings = () => {
  try {
    // Load from localStorage for now
    const darkMode = localStorage.getItem('darkMode') === 'true'
    appSettings.value.darkMode = darkMode
    $q.dark.set(darkMode)
  } catch (error) {
    console.error('Failed to load app settings:', error)
  }
}

onMounted(async () => {
  try {
    // Load unread notifications count
    const res = await api.get('/operations/notifications/')
    type NotificationDTO = { is_read?: boolean }
    const list = (res.data?.results ?? res.data ?? []) as NotificationDTO[]
    unreadCount.value = Array.isArray(list) ? list.filter((n) => n && n.is_read === false).length : 0
  } catch (e) { 
    console.warn('unread count fetch failed', e)
    unreadCount.value = 0 
  }

  // Load user data
  await loadUserProfile()
  await loadNotificationSettings()
  loadAppSettings()
})
</script>

<style scoped>
/* Platform-specific safe area handling */
.settings-page.ios-safe-area {
  padding-top: env(safe-area-inset-top);
  padding-bottom: calc(80px + env(safe-area-inset-bottom));
}

.settings-page.android-safe-area {
  /* Android specific adjustments */
  padding-bottom: calc(80px + 16px);
}

/* Mobile-optimized card spacing */
@media (max-width: 599px) {
  .q-card {
    margin-bottom: 12px !important;
  }
  
  .q-card-section {
    padding: 12px !important;
  }
}

/* Touch-friendly button sizing */
.q-btn {
  min-height: 44px;
}

/* Improved readability on small screens */
@media (max-width: 599px) {
  .q-item__label {
    font-size: 14px;
  }
  
  .q-item__label--caption {
    font-size: 12px;
  }
}

/* Platform-specific header adjustments */
.q-header.ios-safe-area {
  padding-top: env(safe-area-inset-top);
}

/* Bottom navigation safe area */
.q-footer.ios-safe-area {
  padding-bottom: env(safe-area-inset-bottom);
}

.q-footer.android-safe-area {
  padding-bottom: 8px;
}

/* Smooth transitions for better UX */
.q-card, .q-btn, .q-item {
  transition: all 0.2s ease;
}

/* Focus states for accessibility */
.q-btn:focus, .q-item:focus {
  outline: 2px solid var(--q-primary);
  outline-offset: 2px;
}
</style>