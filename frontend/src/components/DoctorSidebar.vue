<template>
  <q-drawer
    v-model="drawerOpen"
    side="left"
    overlay
    bordered
    class="prototype-sidebar"
    :width="280"
  >
    <div class="sidebar-content">
      <div class="logo-section">
        <div class="logo-container">
          <q-avatar size="40px" class="logo-avatar">
            <img src="../assets/logo.png" alt="MediSync Logo" />
          </q-avatar>
          <span class="logo-text">MediSync</span>
        </div>
        <q-btn
          dense
          flat
          round
          icon="menu"
          aria-label="Close navigation"
          @click="toggleDrawer"
          class="menu-btn"
        />
      </div>

      <div class="sidebar-user-profile">
        <div class="profile-picture-container">
          <q-avatar 
            size="80px" 
            class="profile-avatar clickable-avatar" 
            @click="navigateToProfile"
            v-ripple
          >
            <div class="profile-placeholder">
              {{ userInitials }}
            </div>
          </q-avatar>
          <q-icon
            :name="userProfile.verification_status === 'approved' ? 'check_circle' : 'cancel'"
            :color="userProfile.verification_status === 'approved' ? 'positive' : 'negative'"
            class="verified-badge"
          />
        </div>

        <div class="user-info">
          <h6 class="user-name clickable-name" @click="navigateToProfile">{{ userProfile.full_name || 'Loading...' }}</h6>
          <p class="user-role">{{ userProfile.specialization || 'Loading specialization...' }}</p>
          <q-chip
            :color="userProfile.verification_status === 'approved' ? 'positive' : 'negative'"
            text-color="white"
            size="sm"
          >
            {{ userProfile.verification_status === 'approved' ? 'Verified' : 'Not Verified' }}
          </q-chip>
        </div>
      </div>

      <q-list class="navigation-menu" role="navigation" aria-label="Doctor navigation">
        <q-item
          clickable
          v-ripple
          @click="navigateTo('doctor-dashboard')"
          :class="['nav-item', { active: activeRoute === 'doctor-dashboard' }]"
          :aria-current="activeRoute === 'doctor-dashboard' ? 'page' : undefined"
        >
          <q-item-section avatar>
            <q-icon name="dashboard" />
          </q-item-section>
          <q-item-section>Dashboard</q-item-section>
        </q-item>

        <q-item
          clickable
          v-ripple
          @click="navigateTo('messaging')"
          :class="['nav-item', { active: activeRoute === 'messaging' }]"
          :aria-current="activeRoute === 'messaging' ? 'page' : undefined"
        >
          <q-item-section avatar>
            <q-icon name="message" />
          </q-item-section>
          <q-item-section>Messaging</q-item-section>
        </q-item>

        <q-item
          clickable
          v-ripple
          @click="navigateTo('patients')"
          :class="['nav-item', { active: activeRoute === 'patients' }]"
          :aria-current="activeRoute === 'patients' ? 'page' : undefined"
        >
          <q-item-section avatar>
            <q-icon name="people" />
          </q-item-section>
          <q-item-section>Patient Management</q-item-section>
        </q-item>
        
        <q-item
          clickable
          v-ripple
          @click="navigateTo('analytics')"
          :class="['nav-item', { active: activeRoute === 'analytics' }]"
          :aria-current="activeRoute === 'analytics' ? 'page' : undefined"
        >
          <q-item-section avatar>
            <q-icon name="analytics" />
          </q-item-section>
          <q-item-section>Analytics</q-item-section>
        </q-item>

        <q-item
          clickable
          v-ripple
          @click="navigateTo('settings')"
          :class="['nav-item', { active: activeRoute === 'settings' }]"
          :aria-current="activeRoute === 'settings' ? 'page' : undefined"
        >
          <q-item-section avatar>
            <q-icon name="settings" />
          </q-item-section>
          <q-item-section>Settings</q-item-section>
        </q-item>
      </q-list>

      <div class="logout-section">
        <q-btn color="negative" icon="logout" label="Logout" class="logout-btn" @click="logout" />
      </div>
    </div>
  </q-drawer>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { api } from 'boot/axios';
import { performLogout } from 'src/utils/logout';

// Props
interface Props {
  modelValue: boolean;
  activeRoute?: string;
}

const props = withDefaults(defineProps<Props>(), {
  activeRoute: '',
});

// Emits
const emit = defineEmits<{
  'update:modelValue': [value: boolean];
}>();

// Types
interface UserProfile {
  id: number;
  full_name: string;
  specialization: string;
  verification_status: string;
  first_name?: string;
  last_name?: string;
}

// Router and Quasar
const router = useRouter();
const $q = useQuasar();

// Reactive data
const userProfile = ref<UserProfile>({
  id: 0,
  full_name: '',
  specialization: '',
  verification_status: 'pending',
});

// Computed
const drawerOpen = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
});

const userInitials = computed(() => {
  const first = userProfile.value.first_name?.trim();
  const last = userProfile.value.last_name?.trim();
  if (first || last) {
    const f = first ? first.charAt(0) : '';
    const l = last ? last.charAt(0) : '';
    const initials = `${f}${l}`.toUpperCase();
    return initials || 'U';
  }
  const full = userProfile.value.full_name?.trim() || '';
  const initials = full
    .split(' ')
    .filter(Boolean)
    .map((name) => name.charAt(0))
    .join('')
    .toUpperCase();
  return initials || (full ? full.charAt(0).toUpperCase() : 'U');
});

// Removed profilePictureUrl logic to consistently use initials-only display

// Methods
const toggleDrawer = () => {
  drawerOpen.value = !drawerOpen.value;
};

const navigateTo = (route: string) => {
  drawerOpen.value = false;
  
  switch (route) {
    case 'doctor-dashboard':
      void router.push('/doctor-dashboard');
      break;
    case 'messaging':
      void router.push('/doctor-messaging');
      break;
    case 'patients':
      void router.push('/doctor-patient-management');
      break;
    case 'analytics':
      void router.push('/doctor-predictive-analytics');
      break;
    case 'settings':
      void router.push('/doctor-settings');
      break;
  }
};

const logout = () => {
  $q.dialog({
    title: 'Confirm Logout',
    message: 'Are you sure you want to logout?',
    cancel: true,
    persistent: true,
  }).onOk(() => {
    // Close the drawer
    drawerOpen.value = false;

    // Show logout notification
    $q.notify({
      type: 'positive',
      message: 'Logged out successfully',
      position: 'top',
      timeout: 2000,
    });

    // Perform centralized logout and redirect
    void performLogout(router);
  });
};

const navigateToProfile = () => {
  void router.push('/doctor-settings');
  emit('update:modelValue', false); // Close the sidebar on mobile
};

const loadUserProfile = async () => {
  try {
    const response = await api.get('/users/profile/');
    const userData = response.data.user || response.data;

    userProfile.value = {
      id: userData.id,
      full_name: userData.full_name,
      specialization: userData.doctor_profile?.specialization || userData.specialization,
      verification_status: userData.verification_status,
      first_name: userData.first_name,
      last_name: userData.last_name,
    };

    // Removed sidebar-triggered verification toast; banner is shown only once at login
  } catch (error) {
    console.error('Error loading user profile:', error);
  }
};

// Lifecycle
onMounted(() => {
  void loadUserProfile();
  
  // Refresh user profile every 30 seconds to check for verification status updates
  setInterval(() => {
    void loadUserProfile();
  }, 30000);
});
</script>

<style scoped>
/* Sidebar Styles */
.prototype-sidebar {
  background: var(--ms-surface);
  border-right: 1px solid var(--ms-border);
  box-shadow: 2px 0 10px rgba(0, 0, 0, 0.08);
}

.sidebar-content {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* Logo Section */
.logo-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--ms-border);
}

.logo-container {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-avatar {
  border: 2px solid var(--ms-primary-2);
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: var(--ms-primary-2);
}

.menu-btn {
  color: var(--ms-muted);
}

/* User Profile Section */
.sidebar-user-profile {
  text-align: center;
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--ms-border);
}

.profile-picture-container {
  position: relative;
  display: inline-block;
  margin-bottom: 16px;
}


.verified-badge {
  position: absolute;
  top: -5px;
  right: -5px;
  background: var(--ms-surface);
  border-radius: 50%;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}

.profile-avatar {
  border: 3px solid var(--ms-primary) !important;
  border-radius: 50% !important;
  overflow: hidden !important;
}

.clickable-avatar {
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.clickable-avatar:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(30, 118, 104, 0.3);
}


.profile-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--ms-primary-2);
  color: white;
  font-weight: 600;
  font-size: 1.5rem;
  border-radius: 50%;
}

.user-info {
  text-align: center;
}

.user-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--ms-text);
  margin: 0 0 4px 0;
}

.clickable-name {
  cursor: pointer;
  transition: color 0.2s ease;
}

.clickable-name:hover {
  color: var(--ms-primary);
}

.user-role {
  font-size: 14px;
  color: var(--ms-muted);
  margin: 0 0 12px 0;
}

/* Navigation Menu */
.navigation-menu {
  flex: 1;
  padding: 16px 0;
}

.nav-item {
  margin: 4px 16px;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.nav-sub-item {
  margin-left: 28px;
}

.nav-item.active {
  background: var(--ms-primary-2);
  color: white;
}

.nav-item.active .q-icon {
  color: white;
}

.nav-item:hover:not(.active) {
  background: var(--ms-surface-2);
}

/* Logout Section */
.logout-section {
  padding: 20px;
  border-top: 1px solid var(--ms-border);
}

.logout-btn {
  width: 100%;
}

/* Responsive Design */
@media (max-width: 768px) {
  .sidebar-content {
    padding: 16px;
  }

  .logo-section {
    margin-bottom: 20px;
    padding-bottom: 16px;
  }

  .sidebar-user-profile {
    margin-bottom: 20px;
    padding-bottom: 16px;
  }

  .profile-picture-container {
    margin-bottom: 12px;
  }

  .navigation-menu {
    padding: 12px 0;
  }

  .logout-section {
    padding: 16px;
  }
}
</style>
