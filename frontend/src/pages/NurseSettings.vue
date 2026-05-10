<template>
  <q-layout view="hHh Lpr fFf">
    <NurseHeader
      :search-text="searchText"
      :search-results="searchResults"
      :unread-notifications-count="unreadNotificationsCount"
      :current-time="currentTime"
      :weather-data="weatherData"
      :weather-loading="weatherLoading"
      :weather-error="weatherError"
      :location-data="locationData"
      :location-loading="locationLoading"
      @toggle-drawer="toggleRightDrawer"
      @search-input="onSearchInput"
      @clear-search="clearSearch"
      @select-search-result="selectSearchResult"
      @show-notifications="showNotifications = true"
    />
    <NurseSidebar v-model="rightDrawerOpen" active-route="nurse-settings" />

    <q-page-container class="page-container-with-fixed-header white-background role-body-bg">
      <div class="page-content">
        <div class="row justify-center">
          <div class="col-12 col-lg-10">
            <!-- All Settings in One Card -->
            <q-card class="settings-card">
              <q-card-section>
                <h6 class="text-h6 q-mb-lg text-center">Settings</h6>

                <!-- Profile Information Section -->
                <div class="settings-section">
                  <h6 class="text-subtitle1 q-mb-md">Profile Information</h6>

                  <div class="profile-section">
                    <div class="profile-picture-container">
                      <q-avatar size="120px" class="profile-avatar">
                        <div class="profile-placeholder">
                          {{ userInitials }}
                        </div>
                      </q-avatar>
                      <!-- Upload controls removed: initials-only avatar -->
                    </div>

                    <div class="profile-form">
                      <div class="row q-gutter-md">
                        <div class="col-12">
                          <q-input
                            v-model="profileForm.fullName"
                            label="Full Name"
                            outlined
                            readonly
                            class="large-input"
                          />
                        </div>
                        <div class="col-12">
                          <q-input
                            v-model="profileForm.email"
                            label="Email Address"
                            type="email"
                            outlined
                            readonly
                            class="large-input"
                          />
                        </div>
                        <div class="col-12">
                          <q-input
                            v-model="profileForm.hospitalName"
                            label="Hospital Name"
                            outlined
                            class="large-input"
                          />
                        </div>
                        <div class="col-12">
                          <q-input
                            v-model="profileForm.hospitalAddress"
                            label="Hospital Address"
                            outlined
                            class="large-input"
                          />
                        </div>
                        <div class="col-12">
                          <q-select
                            v-model="profileForm.department"
                            :options="departmentOptions"
                            label="Department"
                            outlined
                            emit-value
                            map-options
                            class="large-input"
                          />
                        </div>
                        <div class="col-12">
                          <q-input
                            v-model="profileForm.licenseNumber"
                            label="Nursing License Number"
                            outlined
                            readonly
                            class="large-input"
                          />
                        </div>

                      </div>
                    </div>
                  </div>
                </div>

                <q-separator class="q-my-lg" />

                <!-- Security Settings Section -->
                <div class="settings-section">
                  <h6 class="text-subtitle1 q-mb-md">Security Settings</h6>

                  <div class="row">
                    <div class="col-12 q-mb-md">
                      <q-input
                        v-model="securityForm.currentPassword"
                        label="Current Password"
                        type="password"
                        outlined
                        :rules="[(val) => !!val || 'Current password is required']"
                        class="large-input"
                      />
                    </div>
                    <div class="col-12 q-mb-md">
                      <q-input
                        v-model="securityForm.newPassword"
                        label="New Password"
                        type="password"
                        outlined
                        :rules="[
                          (val) => !!val || 'New password is required',
                          (val) => val.length >= 8 || 'Password must be at least 8 characters',
                        ]"
                        class="large-input"
                      />
                    </div>
                    <div class="col-12 q-mb-md">
                      <q-input
                        v-model="securityForm.confirmPassword"
                        label="Confirm New Password"
                        type="password"
                        outlined
                        :rules="[
                          (val) => !!val || 'Please confirm your password',
                          (val) => val === securityForm.newPassword || 'Passwords do not match',
                        ]"
                        class="large-input"
                      />
                    </div>
                    <div class="col-12">
                      <q-toggle
                        v-model="securityForm.twoFactorAuth"
                        label="Enable Two-Factor Authentication"
                        color="primary"
                        class="large-toggle"
                      />
                    </div>
                  </div>
                </div>

                <q-separator class="q-my-lg" />

                <!-- Notification Preferences Section -->
                <div class="settings-section">
                  <h6 class="text-subtitle1 q-mb-md">Notification Preferences</h6>

                  <div class="notification-settings">
                    <div class="notification-item">
                      <div class="notification-info">
                        <div class="notification-title">Patient Alerts</div>
                        <div class="notification-description">
                          Receive notifications for patient emergencies and urgent care needs
                        </div>
                      </div>
                      <q-toggle v-model="notificationSettings.patientAlerts" color="primary" />
                    </div>

                    <div class="notification-item">
                      <div class="notification-info">
                        <div class="notification-title">Medication Reminders</div>
                        <div class="notification-description">
                          Get reminded about medication schedules and administration
                        </div>
                      </div>
                      <q-toggle
                        v-model="notificationSettings.medicationReminders"
                        color="primary"
                      />
                    </div>

                    <div class="notification-item">
                      <div class="notification-info">
                        <div class="notification-title">Assessment Updates</div>
                        <div class="notification-description">
                          Notifications for completed assessments and pending tasks
                        </div>
                      </div>
                      <q-toggle v-model="notificationSettings.assessmentUpdates" color="primary" />
                    </div>
                  </div>
                </div>

                <q-separator class="q-my-lg" />

                <!-- Account Status Section -->
                <div class="settings-section">
                  <h6 class="text-subtitle1 q-mb-md">Account Status</h6>

                  <div class="account-status-grid">
                    <div class="status-item">
                      <div class="status-label">Account Type</div>
                      <div class="status-value">Nurse</div>
                    </div>

                    <div class="status-item">
                      <div class="status-label">Verification Status</div>
                      <div class="status-value">
                        <q-chip
                          :color="getVerificationColor(userProfile.verification_status)"
                          text-color="white"
                          :label="getVerificationLabel(userProfile.verification_status)"
                          size="sm"
                        />
                      </div>
                    </div>

                    <div class="status-item">
                      <div class="status-label">Last Login</div>
                      <div class="status-value">{{ accountStatus.lastLogin }}</div>
                    </div>

                    <div class="status-item">
                      <div class="status-label">Member Since</div>
                      <div class="status-value">{{ accountStatus.memberSince }}</div>
                    </div>
                  </div>
                </div>

                <q-separator class="q-my-lg" />

                <!-- Quick Actions Section -->
                <div class="settings-section">
                  <h6 class="text-subtitle1 q-mb-md">Quick Actions</h6>

                  <div class="quick-actions-container">
                    <q-btn
                      color="primary"
                      label="Save Changes"
                      icon="save"
                      class="large-button"
                      @click="saveSettings"
                      :loading="saving"
                    />
                    <q-btn
                      color="secondary"
                      label="Export Data"
                      icon="download"
                      class="large-button"
                      @click="exportData"
                    />
                    <q-btn
                      color="accent"
                      label="Backup Patient Data"
                      icon="backup"
                      class="large-button"
                      @click="backupPatientData"
                    />
                  </div>
                </div>
              </q-card-section>
            </q-card>
          </div>
        </div>
      </div>
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useQuasar } from 'quasar';
import { api } from '../boot/axios';
import NurseHeader from '../components/NurseHeader.vue';
import NurseSidebar from 'src/components/NurseSidebar.vue';

// Type definitions
interface Patient {
  id: number;
  name: string;
  full_name?: string;
  patient_name?: string;
  room_number?: string;
  [key: string]: unknown;
}

interface Doctor {
  id: number;
  name?: string;
  full_name?: string;
  specialization?: string;
  [key: string]: unknown;
}

interface Assessment {
  id: number;
  patient_id: number;
  [key: string]: unknown;
}

const $q = useQuasar();

// Header functionality
const rightDrawerOpen = ref(false);

// Search functionality
const searchText = ref('');
const searchResults = ref<
  {
    id: string;
    type: string;
    title: string;
    subtitle: string;
    data: Record<string, string | number>;
  }[]
>([]);

// Notification system
const showNotifications = ref(false);
const unreadNotificationsCount = ref(0);

// Location data
const locationData = ref<{
  city: string;
  region: string;
  country: string;
} | null>(null);
const locationLoading = ref(false);
const locationError = ref(false);
const currentTime = ref('');
const weatherData = ref<{
  temperature: number;
  condition: string;
  location: string;
} | null>(null);
const weatherLoading = ref(false);
const weatherError = ref(false);
let timeInterval: NodeJS.Timeout | null = null;


// User profile
const userProfile = ref<{
  first_name?: string;
  last_name?: string;
  full_name?: string;
  verification_status?: string;
  profile_picture?: string | null;
  email?: string;
}>({});


const userInitials = computed(() => {
  const fn = (userProfile.value.first_name || '').trim();
  const ln = (userProfile.value.last_name || '').trim();
  if (fn && ln) {
    return `${fn[0]}${ln[0]}`.toUpperCase();
  }

  const full = (userProfile.value.full_name || profileForm.value.fullName || '').trim();
  if (full) {
    const parts = full.split(/\s+/);
    const initials = parts.slice(0, 2).map((p) => p[0]?.toUpperCase() ?? '').join('');
    return initials || (full[0]?.toUpperCase() ?? 'N');
  }

  const email = (userProfile.value.email || '').trim();
  if (email) {
    return (email[0]?.toUpperCase() ?? 'N');
  }

  return 'NU';
});

// Header methods
const toggleRightDrawer = () => {
  rightDrawerOpen.value = !rightDrawerOpen.value;
};

const updateTime = () => {
  const now = new Date();
  currentTime.value = now.toLocaleTimeString('en-US', {
    hour12: true,
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
  });
};

// Search functionality methods
const onSearchInput = async (value: string | number | null) => {
  const stringValue = String(value || '');
  searchText.value = stringValue;
  if (stringValue.trim() && stringValue.length > 2) {
    try {
      // Search for patients and doctors using real API endpoints
      const [patientsResponse, doctorsResponse] = await Promise.all([
        api.get(`/users/nurse/patients/?search=${encodeURIComponent(stringValue)}`),
        api.get(`/operations/availability/doctors/free/`, { params: { search: stringValue } }),
      ]);

      const results = [];

      // Add patient results
      if (patientsResponse.data.patients) {
        results.push(
          ...patientsResponse.data.patients.map((item: Patient) => ({
            id: `patient-${item.id}`,
            type: 'patient',
            title: item.full_name || item.patient_name || item.name || 'Unknown Patient',
            subtitle: `Patient - Room: ${item.room_number || 'N/A'}`,
            data: item,
          })),
        );
      }

      // Add doctor results
      if (doctorsResponse.data?.doctors) {
        results.push(
          ...(doctorsResponse.data.doctors || []).map((item: Doctor) => ({
            id: `doctor-${item.id}`,
            type: 'doctor',
            title: item.full_name || item.name || 'Unknown Doctor',
            subtitle: `Doctor - ${item.specialization || 'General'}`,
            data: item,
          })),
        );
      }

      searchResults.value = results.slice(0, 10); // Limit to 10 results
    } catch (error) {
      console.error('Search error:', error);
      searchResults.value = [];
    }
  } else {
    searchResults.value = [];
  }
};

const clearSearch = () => {
  searchText.value = '';
  searchResults.value = [];
};

const selectSearchResult = (result: {
  id: string;
  type: string;
  title: string;
  subtitle: string;
  data: Record<string, string | number>;
}) => {
  // Handle search result selection
  console.log('Selected search result:', result);
  clearSearch();
};

// Location functionality
const fetchLocation = async () => {
  locationLoading.value = true;
  locationError.value = false;

  try {
    // Simulate API call for location data
    await new Promise((resolve) => setTimeout(resolve, 1000));
    locationData.value = {
      city: 'Manila',
      region: 'Metro Manila',
      country: 'Philippines',
    };
  } catch (error) {
    console.error('Error fetching location:', error);
    locationError.value = true;
  } finally {
    locationLoading.value = false;
  }
};

const fetchWeather = async () => {
  weatherLoading.value = true;
  weatherError.value = false;

  try {
    // Mock weather data - replace with actual API call
    await new Promise((resolve) => setTimeout(resolve, 1000));
    weatherData.value = {
      temperature: 28,
      condition: 'sunny',
      location: 'Mandaluyong City',
    };
  } catch (error) {
    console.error('Failed to fetch weather:', error);
    weatherError.value = true;
  } finally {
    weatherLoading.value = false;
  }
};

// Navigation and logout handled by NurseSidebar

// Fetch user profile
const fetchUserProfile = async () => {
  try {
    const response = await api.get('/users/profile/');
    const userData = response.data.user;

    userProfile.value = {
      first_name: userData.first_name,
      last_name: userData.last_name,
      full_name: userData.full_name,
      verification_status: userData.verification_status,
      profile_picture: userData.profile_picture || localStorage.getItem('profile_picture'),
      email: userData.email,
    };

    // Update memberSince with formatted date_joined
    if (userData.date_joined) {
      accountStatus.value.memberSince = formatDate(userData.date_joined);
    }

    // Removed module-level verification toast; now shown only once at login

    // Update localStorage with new verification status
    const storedUser = JSON.parse(localStorage.getItem('user') || '{}');
    if (storedUser) {
      storedUser.verification_status = userData.verification_status;
      localStorage.setItem('user', JSON.stringify(storedUser));
    }

    // Store profile picture in localStorage if available
    if (userData.profile_picture) {
      localStorage.setItem('profile_picture', userData.profile_picture);
    }

    // Sync hospital info into settings form
    profileForm.value.hospitalName = userData.hospital_name || profileForm.value.hospitalName;
    profileForm.value.hospitalAddress = userData.hospital_address || profileForm.value.hospitalAddress;
    profileForm.value.department = userData.nurse_profile?.department || profileForm.value.department;
  } catch (error) {
    console.error('Failed to fetch user profile:', error);
  }
};

// Loading states
const saving = ref(false);

// Form data
const profileForm = ref({
  fullName: '',
  email: '',
  hospitalName: '',
  hospitalAddress: '',
  department: '',
  licenseNumber: '',
});

const securityForm = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
  twoFactorAuth: false,
});

const notificationSettings = ref({
  patientAlerts: true,
  medicationReminders: true,
  assessmentUpdates: true,
});

// Account status
const accountStatus = ref({
  verified: true,
  lastLogin: '2024-01-15 10:30 AM',
  memberSince: '',
});

// Options
const departmentOptions = [
  { label: 'Emergency Department', value: 'emergency' },
  { label: 'Intensive Care Unit', value: 'icu' },
  { label: 'General Ward', value: 'general' },
  { label: 'Pediatrics', value: 'pediatrics' },
  { label: 'Maternity', value: 'maternity' },
  { label: 'Surgery', value: 'surgery' },
  { label: 'Outpatient', value: 'outpatient' },
  { label: 'Other', value: 'other' },
];

// Computed properties
// Methods

const saveSettings = async () => {
  console.log('🔥 Save Settings button clicked!');
  console.log('🔑 Access token:', localStorage.getItem('access_token') ? 'Present' : 'Missing');
  console.log('📝 Profile form data:', profileForm.value);
  
  saving.value = true;

  try {
    // Save profile information
    console.log('📤 Sending profile update...');
    await api.put('/users/profile/update/', {
      email: profileForm.value.email,
      // Move hospital fields to top-level to match backend serializer
      hospital_name: profileForm.value.hospitalName,
      hospital_address: profileForm.value.hospitalAddress,
      // Keep nurse-specific fields under nurse_profile if supported separately
      nurse_profile: {
        department: profileForm.value.department,
      },
    });
    console.log('Profile updated successfully');
    // Backend endpoint for notification preferences is not yet implemented
    console.log('Notification preferences saved locally:', notificationSettings.value);

    // Handle password change if requested
    if (securityForm.value.newPassword) {
      if (securityForm.value.newPassword !== securityForm.value.confirmPassword) {
        $q.notify({
          type: 'negative',
          message: 'New passwords do not match',
          position: 'top',
        });
        return;
      }

      // Note: Password change endpoint is not yet implemented
      // For now, show a message that this feature is coming soon
      $q.notify({
        type: 'info',
        message: 'Password change feature is coming soon. Please use the forgot password option for now.',
        position: 'top',
        timeout: 5000,
      });

      // Reset password fields
      securityForm.value.currentPassword = '';
      securityForm.value.newPassword = '';
      securityForm.value.confirmPassword = '';
    }

    $q.notify({
      type: 'positive',
      message: 'Settings saved successfully!',
      position: 'top',
    });
  } catch (error: unknown) {
    console.error('Error saving settings:', error);
    
    let errorMessage = 'Failed to save settings. Please try again.';
    
    // Type guard to check if error is an axios error
    if (error && typeof error === 'object' && 'response' in error) {
      const axiosError = error as { response?: { status?: number; data?: { message?: string } } };
      
      console.error('❌ Error details:', {
        status: axiosError.response?.status,
        data: axiosError.response?.data,
      });
      
      if (axiosError.response?.status === 401) {
        errorMessage = 'Authentication required. Please log in again.';
      } else if (axiosError.response?.status === 403) {
        errorMessage = 'Permission denied. You may not have access to modify these settings.';
      } else if (axiosError.response?.status === 404) {
        errorMessage = 'Settings endpoint not found. Please contact support.';
      } else if (axiosError.response?.data?.message) {
        errorMessage = axiosError.response.data.message;
      }
    }
    
    $q.notify({
      type: 'negative',
      message: errorMessage,
      position: 'top',
      timeout: 5000,
    });
  } finally {
    saving.value = false;
  }
};

const exportData = async () => {
  console.log('Export Data button clicked!');
  try {
    $q.loading.show({
      message: 'Exporting profile data...',
      spinnerColor: 'primary',
    });

    // Fetch complete profile data
    const profileResponse = await api.get('/users/profile/');
    const profileData = profileResponse.data.user;

    // Create export data object
    const exportData = {
      profileInformation: {
        fullName: profileData.full_name,
        email: profileData.email,
        phone: profileData.phone || 'Not provided',
        department: profileData.nurse_profile?.department || 'Not specified',
        licenseNumber: profileData.nurse_profile?.license_number || 'Not provided',
        verificationStatus: profileData.verification_status,
        memberSince: accountStatus.value.memberSince,
        lastLogin: accountStatus.value.lastLogin,
      },
      exportDate: new Date().toISOString(),
      exportType: 'Nurse Profile Information',
      exportedBy: profileData.full_name,
    };

    // Create and download JSON file
    const dataStr = JSON.stringify(exportData, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);

    const link = document.createElement('a');
    link.href = url;
    link.download = `nurse-profile-export-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    $q.notify({
      type: 'positive',
      message: 'Profile data exported successfully!',
      position: 'top',
      timeout: 3000,
    });
  } catch (error) {
    console.error('Export failed:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to export data. Please try again.',
      position: 'top',
      timeout: 4000,
    });
  } finally {
    $q.loading.hide();
  }
};

const backupPatientData = async () => {
  console.log('Backup Patient Data button clicked!');
  try {
    $q.loading.show({
      message: 'Backing up patient management data...',
      spinnerColor: 'primary',
    });

    // Fetch patient management data
    const patientsResponse = await api.get('/operations/patients/');
    const assessmentsResponse = await api.get('/operations/patient-assessments/');

    // Create backup data object
    const patients = (patientsResponse.data.results || patientsResponse.data) as Patient[];
    const assessments = (assessmentsResponse.data.results ||
      assessmentsResponse.data) as Assessment[];

    const backupData = {
      patientManagement: {
        patients: patients,
        assessments: assessments,
        totalPatients: patientsResponse.data.count || 0,
        totalAssessments: assessmentsResponse.data.count || 0,
      },
      backupDate: new Date().toISOString(),
      backupType: 'Patient Management Data',
      backedUpBy: userProfile.value.full_name,
    };

    // Create and download JSON file
    const dataStr = JSON.stringify(backupData, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);

    const link = document.createElement('a');
    link.href = url;
    link.download = `nurse-settings-backup-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    $q.notify({
      type: 'positive',
      message: 'Patient management data backed up successfully!',
      position: 'top',
      timeout: 3000,
    });
  } catch (error) {
    console.error('Backup failed:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to backup patient data. Please try again.',
      position: 'top',
      timeout: 4000,
    });
  } finally {
    $q.loading.hide();
  }
};

// Verification status helpers
const getVerificationColor = (status: string | undefined) => {
  switch (status) {
    case 'approved':
    case 'verified':
      return 'positive';
    case 'pending':
    case 'for_review':
      return 'warning';
    case 'declined':
    case 'rejected':
      return 'negative';
    default:
      return 'warning';
  }
};

const getVerificationLabel = (status: string | undefined) => {
  switch (status) {
    case 'approved':
    case 'verified':
      return 'Verified';
    case 'pending':
      return 'Pending';
    case 'for_review':
      return 'For Review';
    case 'declined':
    case 'rejected':
      return 'Declined';
    default:
      return 'Unverified';
  }
};

// Load user profile data
const loadUserProfile = async () => {
  try {
    const response = await api.get('/users/profile/');
    const userData = response.data.user;

    profileForm.value = {
      fullName: userData.full_name || '',
      email: userData.email || '',
      // Read hospital fields from top-level user fields
      hospitalName: userData.hospital_name || '',
      hospitalAddress: userData.hospital_address || '',
      department: userData.nurse_profile?.department || '',
      licenseNumber: userData.nurse_profile?.license_number || '',
    };
  } catch (error) {
    console.error('Failed to load user profile:', error);

    // Fallback to localStorage
    const userData = localStorage.getItem('user');
    if (userData) {
      const user = JSON.parse(userData);
      profileForm.value = {
        fullName: user.full_name || '',
        email: user.email || '',
        // Read hospital fields from top-level user fields in localStorage
        hospitalName: user.hospital_name || '',
        hospitalAddress: user.hospital_address || '',
        department: user.nurse_profile?.department || '',
        licenseNumber: user.nurse_profile?.license_number || '',
      };
    }
  }
};

const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
};

onMounted(() => {
  void loadUserProfile();
  void fetchUserProfile();

  // Initialize time, weather, and location
  updateTime();
  timeInterval = setInterval(updateTime, 1000);
  void fetchWeather();
  void fetchLocation();

  // Refresh user profile every 10 seconds to check for verification status updates
  setInterval(() => void fetchUserProfile(), 10000);
});

// Removed profile picture storage sync: initials-only avatar

onUnmounted(() => {
  if (timeInterval) {
    clearInterval(timeInterval);
  }
});
</script>

<style scoped>
/* Prototype Header Styles */
.prototype-header {
  background: #286660;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header-toolbar {
  padding: 0 24px;
  min-height: 64px;
}

.menu-toggle-btn {
  color: white;
  margin-right: 16px;
}

.header-left {
  flex: 1;
  display: flex;
  align-items: center;
}

.search-container {
  width: 100%;
  max-width: 500px;
}

.search-input {
  background: white;
  border-radius: 8px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.notification-btn {
  color: white;
}

.time-display {
  display: flex;
  align-items: center;
  gap: 8px;
  color: white;
}

.time-text {
  font-size: 14px;
  font-weight: 500;
}

.weather-display {
  display: flex;
  align-items: center;
  gap: 8px;
  color: white;
}

.weather-text {
  font-size: 14px;
  font-weight: 500;
}

.weather-location {
  font-size: 14px;
  font-weight: 500;
}

.weather-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  color: white;
}

.weather-error {
  display: flex;
  align-items: center;
  gap: 8px;
  color: white;
}

/* Page Container */
.page-container-with-fixed-header {
  background-color: white;
  background-size: cover;
  min-height: 100vh;
  padding-top: 64px;
  position: relative;
}

.page-container-with-fixed-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.25) 0%,
    rgba(248, 249, 250, 0.15) 50%,
    rgba(240, 242, 245, 0.08) 100%
  );
  z-index: 0;
  pointer-events: none;
}

.page-container-with-fixed-header > * {
  position: relative;
  z-index: 1;
}

.page-content {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.nurse-settings {
  background-color: white;
  background-size: cover;
  min-height: 100vh;
}

.page-header {
  background: linear-gradient(135deg, #286660 0%, #1e7668 100%);
  color: white;
  padding: 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1200px;
  margin: 0 auto;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.back-btn {
  color: white;
}

.page-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.page-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.settings-card {
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.profile-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.profile-picture-container {
  position: relative;
  display: inline-block;
}

.profile-avatar {
  border: 3px solid #1e7668 !important;
  border-radius: 50% !important;
  overflow: hidden !important;
}

.profile-placeholder {
  width: 100%;
  height: 100%;
  display: flex !important;
  align-items: center;
  justify-content: center;
  background: #286660 !important;
  color: white !important;
  font-weight: 600;
  font-size: 1.5rem;
  border-radius: 50%;
  position: relative;
  z-index: 1;
}


.profile-form {
  width: 100%;
}

.notification-settings {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.notification-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  border-radius: 8px;
  background: #f8f9fa;
}

.notification-info {
  flex: 1;
  margin-right: 20px;
}

.notification-title {
  font-weight: 600;
  margin-bottom: 5px;
  color: #333;
}

.notification-description {
  font-size: 0.9rem;
  color: #666;
  line-height: 1.4;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #e0e0e0;
}

.status-item:last-child {
  border-bottom: none;
}

.status-label {
  font-weight: 500;
  color: #666;
}

.status-value {
  font-weight: 600;
  color: #333;
}

.danger-zone {
  border: 2px solid #f44336;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .page-content {
    padding: 8px;
  }

  .q-card {
    margin: 8px 0;
    border-radius: 12px;
  }

  .q-card__section {
    padding: 16px;
  }

  .profile-section {
    align-items: stretch;
    gap: 16px;
  }

  .profile-avatar {
    width: 80px;
    height: 80px;
  }

  .profile-info h6 {
    font-size: 18px;
    margin-bottom: 4px;
  }

  .profile-info .text-caption {
    font-size: 13px;
  }

  .notification-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
    padding: 12px;
  }

  .notification-info {
    margin-right: 0;
  }

  .notification-info .q-item-label {
    font-size: 14px;
  }

  .notification-info .q-item-label--caption {
    font-size: 12px;
  }

  .q-field {
    margin-bottom: 12px;
  }

  .q-field__label {
    font-size: 14px;
  }

  .q-field__control {
    font-size: 14px;
  }

  .q-btn {
    padding: 10px 16px;
    font-size: 14px;
    border-radius: 6px;
  }

  .q-tab {
    padding: 8px 12px;
    font-size: 14px;
  }

  .q-tab-panel {
    padding: 16px 0;
  }
}

/* Sidebar Styles */
.prototype-sidebar {
  background: white;
  border-right: 1px solid #e0e0e0;
}

.sidebar-content {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding-bottom: 80px; /* Space for footer */
}

/* Sidebar Account Status Styles */
.sidebar-account-status {
  padding: 20px;
  border-bottom: 1px solid #e0e0e0;
  background: #f8f9fa;
}

.sidebar-account-status h6 {
  color: #286660;
  font-weight: 600;
  margin-bottom: 16px;
  font-size: 14px;
}

.sidebar-status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #e0e0e0;
}

.sidebar-status-item:last-child {
  border-bottom: none;
}

.sidebar-status-label {
  font-weight: 500;
  color: #666;
  font-size: 12px;
  flex: 1;
}

.sidebar-status-value {
  font-weight: 600;
  color: #333;
  font-size: 12px;
  text-align: right;
  flex: 1;
  display: flex;
  justify-content: flex-end;
  align-items: center;
}

.logo-section {
  padding: 20px;
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo-container {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  color: #286660;
}

.menu-btn {
  color: #666;
}

.sidebar-user-profile {
  padding: 24px 20px;
  border-bottom: 1px solid #e0e0e0;
  text-align: center;
}

.profile-picture-container {
  position: relative;
  display: inline-block;
  margin-bottom: 16px;
}


/* Sidebar-specific upload button positioning */


.user-info {
  text-align: center;
}

.user-name {
  margin: 0 0 4px 0;
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.user-role {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #666;
}

.navigation-menu {
  flex: 1;
  padding: 8px 0;
}

.nav-item {
  margin: 4px 16px;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.nav-item.active {
  background: #286660;
  color: white;
}

.nav-item.active .q-icon {
  color: white;
}

.nav-item:hover:not(.active) {
  background: #f5f5f5;
}

.logout-section {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 20px;
  border-top: 1px solid #e0e0e0;
  background: #f8f9fa;
}

.logout-btn {
  width: 100%;
  border-radius: 8px;
  font-weight: 600;
  text-transform: uppercase;
}

/* White background for settings page */
.white-background {
  background: white !important;
}

/* Header Styles */
.prototype-header {
  background: #286660;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header-toolbar {
  padding: 0 16px;
}

.header-left,
.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.search-container {
  min-width: 300px;
}

.search-input {
  border-radius: 8px;
}

/* Pill-shaped elements for time, weather, and location */
.time-pill,
.weather-pill,
.location-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  background: white;
  color: #286660;
  font-size: 14px;
  font-weight: 500;
  padding: 6px 12px;
  border-radius: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.time-text,
.weather-text,
.location-text {
  white-space: nowrap;
}

.weather-loading,
.weather-error {
  display: flex;
  align-items: center;
  gap: 6px;
  color: white;
  font-size: 14px;
  font-weight: 500;
}

.weather-error .q-icon {
  color: #ff6b6b;
}

/* Settings Section Styles */
.settings-section {
  margin-bottom: 24px;
}

.settings-section:last-child {
  margin-bottom: 0;
}

.settings-section h6 {
  color: #286660;
  font-weight: 600;
  border-bottom: 2px solid #e8f5e8;
  padding-bottom: 8px;
}

/* Profile Section Styles */
.profile-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
}

.profile-picture-container {
  position: relative;
  display: flex;
  justify-content: center;
}

.profile-avatar {
  border: 3px solid #286660;
  box-shadow: 0 4px 12px rgba(40, 102, 96, 0.2);
}

.upload-btn {
  position: absolute;
  bottom: 0;
  right: 0;
  background: white;
  border: 2px solid #286660;
}

.profile-form {
  width: 100%;
  max-width: 600px;
}

/* Notification Settings Styles */
.notification-settings {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.notification-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
}

.notification-info {
  flex: 1;
  margin-right: 16px;
}

.notification-title {
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}

.notification-description {
  font-size: 14px;
  color: #666;
  line-height: 1.4;
}

/* Status Item Styles */
.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #e0e0e0;
  width: 100%;
}

.status-item:last-child {
  border-bottom: none;
}

.status-label {
  font-weight: 500;
  color: #666;
  flex: 1;
}

.status-value {
  font-weight: 600;
  color: #333;
}

.status-value-right {
  font-weight: 600;
  color: #333;
  text-align: right;
  flex: 1;
  display: flex;
  justify-content: flex-end;
  align-items: center;
}

/* Large Input Styles */
.large-input {
  font-size: 16px;
}

.large-input .q-field__control {
  min-height: 56px;
  font-size: 16px;
}

.large-input .q-field__label {
  font-size: 16px;
  font-weight: 500;
}

.large-input .q-field__native {
  font-size: 16px;
  padding: 12px 16px;
}

.large-toggle {
  font-size: 16px;
}

.large-toggle .q-toggle__label {
  font-size: 16px;
  font-weight: 500;
}

/* Account Status Grid */
.account-status-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}

/* First row: Account Type and Verification Status */
.account-status-grid .status-item:nth-child(1),
.account-status-grid .status-item:nth-child(2) {
  grid-column: span 1;
}

/* Second row: Last Login and Member Since side by side */
.account-status-grid .status-item:nth-child(3),
.account-status-grid .status-item:nth-child(4) {
  grid-column: span 1;
}

.account-status-grid .status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
}

.account-status-grid .status-label {
  font-weight: 500;
  color: #666;
  font-size: 14px;
}

.account-status-grid .status-value {
  font-weight: 600;
  color: #333;
  font-size: 14px;
}

/* Quick Actions Container */
.quick-actions-container {
  display: flex;
  gap: 16px;
  justify-content: center;
  flex-wrap: wrap;
}

/* Large Button Styles */
.large-button {
  min-height: 48px;
  font-size: 16px;
  font-weight: 600;
  padding: 12px 24px;
  min-width: 200px;
  max-width: 200px;
  flex: 1;
}

/* Header Layout Styles */
.header-search-container {
  position: relative;
  flex: 1;
  max-width: 400px;
}

.search-results-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 1000;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  margin-top: 4px;
  max-height: 300px;
  overflow-y: auto;
}

.search-result-item {
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.search-result-item:hover {
  background-color: #f5f5f5;
}

.search-result-item:last-child {
  border-bottom: none;
}

.search-result-title {
  font-weight: 500;
  color: #333;
  margin-bottom: 4px;
}

.search-result-subtitle {
  font-size: 0.875rem;
  color: #666;
}

/* Pill-style displays for time, weather, and location */
.header-info-pill {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  padding: 6px 12px;
  margin: 0 4px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  transition: all 0.2s ease;
}

.header-info-pill:hover {
  background: rgba(255, 255, 255, 0.15);
  transform: translateY(-1px);
}

.header-info-content {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.875rem;
  color: white;
  font-weight: 500;
}

.header-info-icon {
  font-size: 1rem;
}

/* Loading and error states */
.header-loading {
  animation: pulse 1.5s ease-in-out infinite;
}

.header-error {
  color: #ff6b6b;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

/* Mobile responsive adjustments */
@media (max-width: 768px) {
  .header-info-pill {
    padding: 4px 8px;
    margin: 0 2px;
  }

  .header-info-content {
    font-size: 0.75rem;
    gap: 4px;
  }

  .header-info-icon {
    font-size: 0.875rem;
  }

  .header-search-container {
    max-width: none;
    flex: 1;
  }
}

/* Ensure mobile header is always visible on mobile devices */
@media (max-width: 768px) {
  .mobile-header-layout {
    display: flex !important;
  }

  .header-toolbar {
    display: none !important;
  }

  /* Force header visibility on iOS */
  .prototype-header {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    z-index: 2000 !important;
    padding-top: max(env(safe-area-inset-top), 8px) !important;
  }

  /* Ensure main content doesn't overlap header */
  .q-page {
    padding-top: calc(env(safe-area-inset-top) + 120px) !important;
  }
}

/* Responsive Design - Mobile and Web Support */
@media (max-width: 768px) {
  .mobile-header-layout {
    display: flex !important;
  }

  .header-toolbar {
    display: none !important;
  }

  /* Mobile header positioning */
  .prototype-header {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    z-index: 2000 !important;
    padding-top: max(env(safe-area-inset-top), 8px) !important;
  }

  /* Ensure main content doesn't overlap header */
  .q-page {
    padding-top: calc(env(safe-area-inset-top) + 120px) !important;
  }
}

/* Desktop Header Layout */
@media (min-width: 769px) {
  .mobile-header-layout {
    display: none;
  }

  .prototype-header .header-toolbar {
    display: flex;
  }
}

/* Global Modal Safe Area Support */
@media (max-width: 768px) {
  :deep(.q-dialog) {
    padding: 0 !important;
    margin: 0 !important;
  }

  :deep(.q-dialog__inner) {
    padding: max(env(safe-area-inset-top), 20px) max(env(safe-area-inset-right), 8px)
      max(env(safe-area-inset-bottom), 8px) max(env(safe-area-inset-left), 8px) !important;
    margin: 0 !important;
    min-height: 100vh !important;
    display: flex !important;
    align-items: flex-start !important;
    justify-content: center !important;
    padding-top: max(env(safe-area-inset-top), 20px) !important;
  }

  :deep(.q-dialog__inner > div) {
    max-height: calc(
      100vh - max(env(safe-area-inset-top), 20px) - max(env(safe-area-inset-bottom), 8px)
    ) !important;
    width: 100% !important;
    max-width: calc(
      100vw - max(env(safe-area-inset-left), 8px) - max(env(safe-area-inset-right), 8px)
    ) !important;
    margin: 0 !important;
  }
}

@media (max-width: 480px) {
  :deep(.q-dialog__inner) {
    padding: max(env(safe-area-inset-top), 24px) max(env(safe-area-inset-right), 4px)
      max(env(safe-area-inset-bottom), 4px) max(env(safe-area-inset-left), 4px) !important;
  }

  :deep(.q-dialog__inner > div) {
    max-height: calc(
      100vh - max(env(safe-area-inset-top), 24px) - max(env(safe-area-inset-bottom), 4px)
    ) !important;
    max-width: calc(
      100vw - max(env(safe-area-inset-left), 4px) - max(env(safe-area-inset-right), 4px)
    ) !important;
  }
}

/* Modal Close Button Styles */
.modal-close-btn {
  padding: 4px;
  transition: all 0.2s ease;
}

/* Desktop close button styling */
@media (min-width: 769px) {
  .modal-close-btn {
    padding: 6px;
    min-width: 36px;
    min-height: 36px;
    font-size: 18px;
  }

  .modal-close-btn:hover {
    background: rgba(0, 0, 0, 0.1);
    border-radius: 50%;
  }
}

/* Mobile close button styling */
@media (max-width: 768px) {
  .modal-close-btn {
    padding: 8px !important;
    min-width: 44px !important;
    min-height: 44px !important;
    font-size: 20px !important;
    background: rgba(0, 0, 0, 0.1) !important;
    border-radius: 50% !important;
  }

  .modal-close-btn:hover {
    background: rgba(0, 0, 0, 0.2) !important;
  }
}

@media (max-width: 480px) {
  .modal-close-btn {
    padding: 10px !important;
    min-width: 48px !important;
    min-height: 48px !important;
    font-size: 22px !important;
    background: rgba(0, 0, 0, 0.1) !important;
    border-radius: 50% !important;
  }

  .modal-close-btn:hover {
    background: rgba(0, 0, 0, 0.2) !important;
  }
}

/* Responsive Design */
@media (max-width: 768px) {
  .profile-section {
    flex-direction: column;
    text-align: center;
    gap: 16px;
  }

  .notification-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
    padding: 12px;
  }

  .notification-info {
    margin-right: 0;
  }

  .notification-info .q-item-label {
    font-size: 14px;
  }

  .notification-info .q-item-label--caption {
    font-size: 12px;
  }

  .status-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
    padding: 12px;
  }

  .account-status-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  /* On mobile, all items stack vertically */
  .account-status-grid .status-item:nth-child(1),
  .account-status-grid .status-item:nth-child(2),
  .account-status-grid .status-item:nth-child(3),
  .account-status-grid .status-item:nth-child(4) {
    grid-column: span 1;
  }

  .account-status-grid .status-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
    padding: 12px;
  }

  .q-btn {
    padding: 10px 16px;
    font-size: 14px;
    border-radius: 6px;
  }
}
</style>
