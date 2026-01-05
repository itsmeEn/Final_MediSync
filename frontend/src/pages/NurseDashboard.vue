<template>
  <q-layout view="hHh Lpr fFf">
    <NurseHeader
      @toggle-drawer="toggleRightDrawer"
      @show-notifications="showNotifications = true"
      @show-stock-alerts="showStockAlerts = true"
      :unread-notifications-count="unreadNotificationsCount"
      :search-text="text"
      @search-input="onSearchInput"
      @clear-search="clearSearch"
      :search-results="searchResults"
      @select-search-result="selectSearchResult"
      :get-search-result-icon="getSearchResultIcon"
      :get-search-result-title="getSearchResultTitle"
      :get-search-result-subtitle="getSearchResultSubtitle"
    />

    <NurseSidebar v-model="rightDrawerOpen" :activeRoute="'nurse-dashboard'" />

    <q-page-container class="page-container-with-fixed-header role-body-bg">
      <!-- Greeting Section -->
      <div class="greeting-section">
        <q-card class="greeting-card">
          <q-card-section class="greeting-content">
            <h2 class="greeting-text">
              Good {{ getTimeOfDay() }}, Nurse {{ userProfile.full_name }}
            </h2>
            <p class="greeting-subtitle">
              Manage patient care and medical inventory - {{ currentDate }}
            </p>
          </q-card-section>
        </q-card>
      </div>

      <!-- Dashboard Cards Section -->
      <div class="dashboard-cards-section">
        <div class="dashboard-cards-grid">
          <!-- Today's Tasks Card -->
          <q-card class="dashboard-card tasks-card" clickable aria-label="Today's Tasks">
            <q-card-section class="card-content">
              <div class="card-text">
                <div class="card-title">Today's Tasks</div>
                <div class="card-description">Tasks to be completed today</div>
                <div class="card-value" role="status" aria-live="polite">
                  <q-spinner v-if="statsLoading" size="md" />
                  <span v-else>{{ dashboardStats.todaysTasks }}</span>
                </div>
              </div>
              <div class="card-icon">
                <q-icon name="assignment" size="2.5rem" />
              </div>
            </q-card-section>
          </q-card>

          <!-- Patients Under Care Card -->
          <q-card class="dashboard-card patients-card" clickable aria-label="Patients Under Care">
            <q-card-section class="card-content">
              <div class="card-text">
                <div class="card-title">Patients Under Care</div>
                <div class="card-description">Based on current queue</div>
                <div class="card-value" role="status" aria-live="polite">
                  <q-spinner v-if="statsLoading" size="md" />
                  <span v-else>{{ dashboardStats.patientsUnderCare }}</span>
                </div>
              </div>
              <div class="card-icon">
                <q-icon name="people" size="2.5rem" />
              </div>
            </q-card-section>
          </q-card>

          <!-- Vitals Checked Card -->
          <q-card class="dashboard-card vitals-card" clickable aria-label="Vitals Checked">
            <q-card-section class="card-content">
              <div class="card-text">
                <div class="card-title">Vitals Checked</div>
                <div class="card-description">Completed patient assessments</div>
                <div class="card-value" role="status" aria-live="polite">
                  <q-spinner v-if="statsLoading" size="md" />
                  <span v-else>{{ dashboardStats.vitalsChecked }}</span>
                </div>
              </div>
              <div class="card-icon">
                <q-icon name="favorite" size="2.5rem" />
              </div>
            </q-card-section>
          </q-card>

          <!-- Medications Given Card -->
          <q-card class="dashboard-card medications-card" clickable aria-label="Medications Given">
            <q-card-section class="card-content">
              <div class="card-text">
                <div class="card-title">Medications Given</div>
                <div class="card-description">Total medications in inventory</div>
                <div class="card-value" role="status" aria-live="polite">
                  <q-spinner v-if="statsLoading" size="md" />
                  <span v-else>{{ dashboardStats.medicationsGiven }}</span>
                </div>
              </div>
              <div class="card-icon">
                <q-icon name="medication" size="2.5rem" />
              </div>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <!-- Patient Care Management System -->
      <div class="queueing-section">
        <q-card class="queueing-card">
          <q-card-section class="queueing-header">
            <h3 class="queueing-title">QUEUEING MANAGEMENT SYSTEM</h3>
            <div class="queueing-actions">
              <q-btn
                color="primary"
                label="Call Next Patient"
                icon="volume_up"
                size="md"
                @click="callNextPatient"
                :disable="allPatients.length === 0 || isCallingPatient"
                :loading="isCallingPatient"
                class="action-btn"
              />
              <q-btn
                color="secondary"
                label="Manage Queue"
                icon="settings"
                size="md"
                @click="manageQueue"
                class="action-btn"
              />
            </div>
          </q-card-section>

          <q-card-section class="queue-panels-section">
            <!-- Consolidated Queue View with Filters -->
            <div class="row items-center q-col-gutter-sm q-mb-md">
              <div class="col-12 col-md-3">
                <q-select v-model="selectedDepartment" :options="departmentOptions" emit-value map-options label="Department" dense outlined />
              </div>
              <div class="col-6 col-md-3">
                <q-select v-model="queueTypeFilter" :options="[{ label: 'All', value: 'all' }, { label: 'Normal', value: 'normal' }, { label: 'Priority', value: 'priority' }]" emit-value map-options label="Queue Type" dense outlined />
              </div>
              <div class="col-6 col-md-3">
                <q-select v-model="sortBy" :options="[{ label: 'Position', value: 'position' }, { label: 'Enqueue Time', value: 'enqueue_time' }]" emit-value map-options label="Sort By" dense outlined />
              </div>
              <div class="col-6 col-md-3">
                <q-select v-model="sortDir" :options="[{ label: 'Ascending', value: 'asc' }, { label: 'Descending', value: 'desc' }]" emit-value map-options label="Order" dense outlined />
              </div>
            </div>

            <q-list bordered class="consolidated-queue-list">
              <q-item v-for="(patient, idx) in filteredSortedPatients" :key="`${patient.queue_type}-${patient.id}-${patient.queue_number}-${idx}`">
                <q-item-section avatar>
                  <q-avatar color="primary" text-color="white">{{ idx + 1 }}</q-avatar>
                </q-item-section>
                <q-item-section>
                  <q-item-label class="text-weight-medium">{{ patient.patient_name }}</q-item-label>
                  <q-item-label caption>
                    <q-chip dense :color="patient.queue_type === 'priority' ? 'red' : 'blue'" text-color="white" class="q-mr-sm">
                      {{ patient.queue_type === 'priority' ? 'Priority' : 'Normal' }}
                    </q-chip>
                    <q-chip dense color="positive" text-color="white" class="q-mr-sm">
                      Queue #{{ patient.queue_number ?? '—' }}
                    </q-chip>
                    <span class="text-grey-7">{{ patient.department }}</span>
                  </q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-btn flat round icon="more_vert" />
                </q-item-section>
              </q-item>
              <q-item v-if="filteredSortedPatients.length === 0">
                <q-item-section class="text-center text-grey-7">No patients in queue</q-item-section>
              </q-item>
            </q-list>
          </q-card-section>
        </q-card>
      </div>

      <!-- My Queue Schedules -->
      <div class="queueing-section">
        <q-card class="queueing-card">
          <q-card-section class="queueing-header">
            <h3 class="queueing-title">My Queue Schedules</h3>
            <div class="queueing-actions">
              <q-btn
                color="primary"
                label="Add Schedule"
                icon="add"
                size="md"
                @click="isEditingSchedule = false; editingScheduleId = null; showQueueScheduleDialog = true; void loadAllSchedules();"
                class="action-btn"
              />
            </div>
          </q-card-section>
          <q-card-section>
            <div v-if="schedulesLoading" class="text-center text-grey-7 q-pa-md">Loading schedules...</div>
            <div v-else-if="schedules.length === 0" class="text-center text-grey-6 q-pa-md">
              No schedules yet. Create one to manage queue availability.
            </div>
            <q-list v-else>
              <q-item v-for="s in schedules" :key="s.id">
                <q-item-section>
                  <q-item-label>
                    {{ getDepartmentLabel(s.department) }}
                    <q-chip dense :color="s.is_active ? 'positive' : 'grey'" text-color="white" class="q-ml-sm">
                      {{ s.is_active ? 'Active' : 'Inactive' }}
                    </q-chip>
                    <q-chip dense :color="s.is_open ? 'positive' : 'negative'" text-color="white" class="q-ml-sm">
                      {{ s.is_open ? 'Open' : 'Closed' }}
                    </q-chip>
                  </q-item-label>
                  <q-item-label caption>
                    {{ formatTimeDisplay(s.start_time) }} - {{ formatTimeDisplay(s.end_time) }} · {{ formatDays(s.days_of_week) }}
                  </q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-btn flat dense icon="edit" color="primary" @click="editSchedule(s)" />
                  <q-btn flat dense icon="delete" color="negative" @click="deleteSchedule(s)" />
                </q-item-section>
              </q-item>
            </q-list>
          </q-card-section>
        </q-card>
      </div>

      <router-view />
    </q-page-container>

    


    <!-- Queue Schedule Modal -->
    <q-dialog v-model="showQueueScheduleDialog" class="centered-dialog">
      <q-card class="dialog-card">
        <q-card-section class="dialog-header">
          <div class="text-h6">{{ isEditingSchedule ? 'Edit Queue Schedule' : 'Create Queue Schedule' }}</div>
        <q-btn icon="close" flat round dense v-close-popup class="modal-close-btn" />
        </q-card-section>
        <q-card-section class="dialog-body">
          <div class="form-container">
            <q-banner v-if="!isEditingSchedule && duplicateDeptScheduleExists" class="q-mb-md" rounded dense color="negative" text-color="white">
              A schedule already exists for {{ getDepartmentLabel(queueForm.department as DepartmentValue) }}. Please edit the existing schedule instead.
            </q-banner>
            <!-- Current Schedule Display -->
            <div v-if="currentSchedule" class="current-schedule-container">
              <div class="schedule-info">
                <div class="schedule-header">
                  <q-icon name="schedule" color="primary" size="sm" />
                  <span class="schedule-title">Current Schedule</span>
      </div>
                <div class="schedule-details">
                  <div class="schedule-row">
                    <span class="schedule-label">Department:</span>
                    <span class="schedule-value">{{ getDepartmentLabel(currentSchedule.department) }}</span>
                  </div>
                  <div class="schedule-row">
                    <span class="schedule-label">Time:</span>
                    <span class="schedule-value">{{ formatTimeDisplay(currentSchedule.start_time) }} - {{ formatTimeDisplay(currentSchedule.end_time) }}</span>
                  </div>
                  <div class="schedule-row">
                    <span class="schedule-label">Days:</span>
                    <span class="schedule-value">{{ formatDays(currentSchedule.days_of_week) }}</span>
                  </div>
                </div>
              </div>
              <div class="schedule-actions">
                <q-btn 
                  :color="currentSchedule.is_open ? 'negative' : 'positive'"
                  :label="currentSchedule.is_open ? 'Close Queue' : 'Open Queue'"
                  :icon="currentSchedule.is_open ? 'close' : 'play_arrow'"
                  @click="toggleQueueStatus"
                  :loading="togglingQueue"
                  class="queue-toggle-btn"
                />
              </div>
            </div>

            <q-select 
              v-model="queueForm.department" 
              :options="departmentOptions" 
              label="Department" 
              emit-value 
              map-options 
              outlined
              class="form-field"
            />
            <div class="row q-col-gutter-md">
              <div class="col-12 col-sm-6">
                <q-input 
                  v-model="queueForm.start_time" 
                  label="Queue Start Time" 
                  outlined
                  mask="##:## AM"
                  hint="Format: HH:MM AM/PM"
                  class="form-field"
                />
              </div>
              <div class="col-12 col-sm-6">
                <q-input 
                  v-model="queueForm.end_time" 
                  label="Queue End Time" 
                  outlined
                  mask="##:## AM"
                  hint="Format: HH:MM AM/PM"
                  class="form-field"
                />
              </div>
            </div>
            <q-select
              v-model="queueForm.days_of_week"
              :options="dayOptions"
              label="Days of Week"
              emit-value 
              map-options 
              multiple 
              use-chips
              outlined
              class="form-field"
            />
          </div>
        </q-card-section>
        <q-card-actions align="right" class="dialog-actions">
          <q-btn 
            color="positive" 
            :label="isEditingSchedule ? 'Save Changes' : 'Create Schedule'" 
            @click="saveQueueSchedule" 
            :loading="savingSchedule"
            class="save-btn"
            unelevated
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Notifications Modal -->
    <q-dialog v-model="showNotifications" persistent>
      <q-card style="width: 400px; max-width: 90vw">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">Notifications</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup class="modal-close-btn" />
        </q-card-section>

        <q-card-section>
          <div v-if="notifications.length === 0" class="text-center text-grey-6 q-py-lg">
            No notifications yet
          </div>
          <div v-else>
            <q-list>
              <q-item
                v-for="notification in notifications"
                :key="notification.id"
                clickable
                @click="handleNotificationClick(notification)"
                :class="{ unread: !notification.isRead }"
              >
                <q-item-section avatar>
                  <q-icon
                    :name="notification.type === 'message' ? 'message' : 'info'"
                    :color="notification.type === 'message' ? 'primary' : 'grey'"
                  />
                </q-item-section>
                <q-item-section>
                  <q-item-label>{{ notification.title }}</q-item-label>
                  <q-item-label caption>{{ notification.message }}</q-item-label>
                  <q-item-label caption class="text-grey-5">{{
                    formatTime(notification.created_at)
                  }}</q-item-label>
                </q-item-section>
                <q-item-section side v-if="!notification.isRead">
                  <q-badge color="red" rounded />
                </q-item-section>
              </q-item>
            </q-list>
          </div>
        </q-card-section>

        <q-card-actions align="right" v-if="notifications.length > 0">
          <q-btn flat label="Mark All Read" @click="markAllNotificationsRead" />
          <q-btn flat label="Close" color="primary" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Stock Alerts Modal -->
    <q-dialog v-model="showStockAlerts" persistent>
      <q-card style="width: 700px; max-width: 95vw">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">Stock Alerts & Notifications</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup class="modal-close-btn" />
        </q-card-section>

        <q-card-section>
          <div v-if="stockAlerts.length === 0" class="text-center text-grey-6 q-py-lg">
            No stock alerts at the moment
          </div>
          <div v-else>
            <q-list>
              <q-item v-for="alert in stockAlerts" :key="alert.id" clickable>
                <q-item-section avatar>
                  <q-icon :name="getStockAlertIcon(alert.severity)" :color="alert.color" />
                </q-item-section>
                <q-item-section>
                  <q-item-label>{{ alert.title }}</q-item-label>
                  <q-item-label caption>{{ alert.message }}</q-item-label>
                  <q-item-label caption class="text-grey-5">{{ formatTime(alert.created_at) }}</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-btn dense flat icon="done" v-if="!alert.isRead" @click="markStockAlertRead(alert.id)" />
                  <q-icon v-else name="check_circle" class="text-positive" />
                </q-item-section>
              </q-item>
            </q-list>
          </div>
        </q-card-section>

        <q-card-actions align="right" v-if="stockAlerts.length > 0">
          <q-btn flat label="Mark All Read" @click="markAllStockAlertsRead" />
          <q-btn flat label="Close" color="primary" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { api } from '../boot/axios';
import NurseHeader from '../components/NurseHeader.vue';
import NurseSidebar from 'src/components/NurseSidebar.vue';
import { usePatientStore } from 'src/stores/patientStore';

const router = useRouter();
const $q = useQuasar();
const patientStore = usePatientStore();
const rightDrawerOpen = ref(false);
const text = ref('');

// Type definitions for search
interface DoctorData {
  id: number;
  full_name: string;
  specialization: string;
  department?: string;
  is_available?: boolean;
  current_patients?: number;
  profile_picture?: string;
}

interface MedicineData {
  id: number;
  medicine_name: string;
  current_stock: number;
  unit_price?: number;
  minimum_stock_level?: number;
  stock_quantity?: number;
  minimum_stock?: number;
  expiry_date?: string;
  batch_number?: string;
  usage_pattern?: string;
  stock_level?: string;
}

interface PatientData {
  id: number;
  patient_name: string;
  queue_number: string;
  department?: string;
  status?: string;
  position_in_queue?: number;
  enqueue_time?: string;
  priority_level?: string;
  priority_position?: number;
}

interface SearchResult {
  type: 'patient' | 'doctor' | 'medicine';
  data: PatientData | DoctorData | MedicineData;
}

interface TaskData {
  id: number;
  title: string;
  description: string;
  icon: string;
  color: string;
  status: string;
  status_color: string;
}

interface AssessmentData {
  id: number;
  patient_name: string;
  vitals_summary: string;
  status: string;
}

// Search functionality
const searchResults = ref<SearchResult[]>([]);
const isSearching = ref(false);

// Location data
const locationData = ref<{
  city: string;
  country: string;
  latitude: number;
  longitude: number;
} | null>(null);
const locationLoading = ref(false);
const locationError = ref(false);

// Dialog states (modals removed for dashboard cards); keep other dialogs
const showNotifications = ref(false);
const showStockAlerts = ref(false);
const showQueueScheduleDialog = ref(false);
const savingSchedule = ref(false);
// Card loading indicator to mirror DoctorDashboard
const statsLoading = ref(false);
const isCallingPatient = ref(false);
const currentSchedule = ref<{
  id: number;
  department: DepartmentValue;
  start_time: string;
  end_time: string;
  days_of_week: number[];
  is_active: boolean;
  is_open: boolean;
} | null>(null);
const togglingQueue = ref(false);

// Notification system
const notifications = ref<Notification[]>([]);

interface Notification {
  id: number | string;
  title: string;
  message: string;
  type: 'message' | 'system';
  isRead: boolean;
  created_at: string;
  sender_id?: number | undefined;
  conversation_id?: number | undefined;
}

// Raw notification data from backend
interface RawNotification {
  id: number;
  message?: {
    sender?: {
      full_name?: string;
      id?: number;
    };
    content?: string;
    conversation?: {
      id?: number;
    };
  };
  is_sent?: boolean;
  created_at: string;
}


// Queue data
const normalQueue = ref<PatientData[]>([]);
const priorityQueue = ref<PatientData[]>([]);

// Consolidated queue view state
type QueueTypeFilter = 'all' | 'normal' | 'priority'
const selectedDepartment = ref<DepartmentValue>('OPD')
const queueTypeFilter = ref<QueueTypeFilter>('all')
const sortBy = ref<'position' | 'enqueue_time'>('position')
const sortDir = ref<'asc' | 'desc'>('asc')

interface QueueItem extends PatientData {
  queue_type: 'normal' | 'priority'
  position?: number
}
interface ConsolidatedPatientDTO {
  id: number
  queue_number?: number | string
  patient_name: string
  department?: string
  status?: string
  position?: number
  enqueue_time?: string
  queue_type: 'normal' | 'priority'
  priority_level?: string | number
}
const allPatients = ref<QueueItem[]>([])

const parseQueueNumber = (qn: string | number | undefined): number | undefined => {
  if (qn === undefined || qn === null) return undefined
  if (typeof qn === 'number' && Number.isFinite(qn)) return qn
  const m = String(qn).match(/\d+/)
  return m ? parseInt(m[0], 10) : undefined
}

const filteredSortedPatients = computed(() => {
  let list = allPatients.value
  if (queueTypeFilter.value !== 'all') {
    list = list.filter(p => p.queue_type === queueTypeFilter.value)
  }
  const compare = (a: QueueItem, b: QueueItem) => {
    // Always prioritize patients from the priority queue over normal
    const typeRank = (q: QueueItem) => (q.queue_type === 'priority' ? 0 : 1)
    const tDiff = typeRank(a) - typeRank(b)
    if (tDiff !== 0) return tDiff

    const field = sortBy.value
    const toNum = (n: number) => (Number.isFinite(n) ? n : 0)
    const avRaw = field === 'position' ? (a.position ?? a.position_in_queue ?? a.priority_position ?? 0) : (a.enqueue_time ? Date.parse(a.enqueue_time) : 0)
    const bvRaw = field === 'position' ? (b.position ?? b.position_in_queue ?? b.priority_position ?? 0) : (b.enqueue_time ? Date.parse(b.enqueue_time) : 0)
    const av = toNum(avRaw)
    const bv = toNum(bvRaw)
    return sortDir.value === 'asc' ? av - bv : bv - av
  }
  return [...list].sort(compare)
})

// Watch for department changes to reload queue data and WebSocket
watch(selectedDepartment, async (newDept) => {
  if (newDept) {
    await loadQueueData()
    await loadDashboardStats()
    await loadTodaysTasks()
    setupQueueWebSocket(true)
  }
})

// Keep selectedDepartment in sync with current schedule when available
watch(() => currentSchedule.value?.department, (dept) => {
  if (dept) selectedDepartment.value = dept
})

// Schedules list and editing state
const schedules = ref<Array<{
  id: number;
  department: DepartmentValue;
  start_time: string;
  end_time: string;
  days_of_week: number[];
  is_active: boolean;
  is_open?: boolean;
}>>([]);
const schedulesLoading = ref(false);
const isEditingSchedule = ref(false);
const editingScheduleId = ref<number | null>(null);
const duplicateDeptScheduleExists = computed(() => {
  if (!queueForm.value.department) return false;
  return schedules.value.some(s => s.department === queueForm.value.department);
});

// Queue schedule form
type DepartmentValue = string

// Queue-enabled defaults; preserve legacy queue departments
import type { DepartmentOption } from '../utils/departments'
const queueDefaultDepartments: DepartmentOption[] = [
  { label: 'Out Patient Department', value: 'OPD' },
  { label: 'Pharmacy', value: 'Pharmacy' },
  { label: 'Appointment', value: 'Appointment' }
]
const departmentOptions = ref<DepartmentOption[]>(queueDefaultDepartments)

const dayOptions = [
  { label: 'Monday', value: 0 },
  { label: 'Tuesday', value: 1 },
  { label: 'Wednesday', value: 2 },
  { label: 'Thursday', value: 3 },
  { label: 'Friday', value: 4 },
  { label: 'Saturday', value: 5 },
  { label: 'Sunday', value: 6 }
]

const queueForm = ref<{
  department: DepartmentValue | null
  start_time: string
  end_time: string
  days_of_week: number[]
  is_active: boolean
}>({ 
  department: 'OPD', 
  start_time: '08:00 AM', 
  end_time: '05:00 PM', 
  days_of_week: [0,1,2,3,4], 
  is_active: true 
})

// Load hospital departments for schedules and consolidated queues
const loadHospitalDepartments = (): void => {
  try {
    // Only use default queue departments (OPD, Pharmacy, Appointment)
    departmentOptions.value = queueDefaultDepartments
    
    // Ensure selectedDepartment stays valid
    const deptVal = selectedDepartment.value
    if (typeof deptVal === 'string') {
      const exists = departmentOptions.value.find((d) => d.value === deptVal)
      if (!exists && departmentOptions.value.length > 0) {
        const firstOption = departmentOptions.value[0]!
        selectedDepartment.value = firstOption.value
      }
    }
  } catch (e) {
    console.warn('Failed to load hospital departments in NurseDashboard, using defaults:', e)
    departmentOptions.value = queueDefaultDepartments
    try {
      $q.notify({ type: 'warning', message: 'Loading default departments due to fetch error' })
    } catch (notifyErr) {
      console.debug('Notification fallback failed in NurseDashboard:', notifyErr)
    }
  }
}

onMounted(() => {
  loadHospitalDepartments()
})

watch(() => queueForm.value.department, async (dept) => {
  if (!dept) {
    currentSchedule.value = null;
    return;
  }
  if (schedules.value.length === 0) {
    await loadAllSchedules();
  }
  const match = schedules.value.find((s) => s.department === dept);
  currentSchedule.value = match
    ? {
        id: match.id,
        department: match.department,
        start_time: match.start_time,
        end_time: match.end_time,
        days_of_week: match.days_of_week,
        is_active: match.is_active,
        is_open: match.is_open || false
      }
    : null;
});

// Medicine data
const medicines = ref<MedicineData[]>([]);

// Task and assessment data
const todaysTasks = ref<TaskData[]>([]);
const completedAssessments = ref<AssessmentData[]>([]);

const performSearch = async (query: string) => {
  if (!query.trim()) {
    searchResults.value = [];
    return;
  }

  try {
    isSearching.value = true;

    // Search patients using the correct endpoint with search parameter
    const patientsResponse = await api.get(
      `/users/nurse/patients/?search=${encodeURIComponent(query)}`,
    );
    const patients = patientsResponse.data.patients || [];

    // Search doctors using the correct endpoint with search parameter
    const doctorsResponse = await api.get(
      `/operations/available-doctors/?search=${encodeURIComponent(query)}`,
    );
    const doctors = doctorsResponse.data || [];

    // Search medicines using the correct endpoint with search parameter
    const medicinesResponse = await api.get(
      `/operations/medicine-inventory/?search=${encodeURIComponent(query)}`,
    );
    const medicines = medicinesResponse.data || [];

    searchResults.value = [
      ...patients.map((p: PatientData) => ({ type: 'patient' as const, data: p })),
      ...doctors.map((d: DoctorData) => ({ type: 'doctor' as const, data: d })),
      ...medicines.map((m: MedicineData) => ({ type: 'medicine' as const, data: m })),
    ];
  } catch (error) {
    console.error('Search error:', error);
    $q.notify({
      type: 'negative',
      message: 'Search failed',
      position: 'top',
      timeout: 3000,
    });
  } finally {
    isSearching.value = false;
  }
};

// Watch for search input changes
watch(text, (newValue: string) => {
  if (newValue && newValue.length > 2) {
    void performSearch(newValue);
  } else {
    searchResults.value = [];
  }
});

// Search result helpers
const getSearchResultIcon = (type: string) => {
  switch (type) {
    case 'patient':
      return 'person';
    case 'doctor':
      return 'medical_services';
    case 'medicine':
      return 'medication';
    default:
      return 'search';
  }
};

const getSearchResultTitle = (result: SearchResult) => {
  switch (result.type) {
    case 'patient':
      return (result.data as PatientData).patient_name || 'Unknown Patient';
    case 'doctor':
      return (result.data as DoctorData).full_name || 'Unknown Doctor';
    case 'medicine':
      return (result.data as MedicineData).medicine_name || 'Unknown Medicine';
    default:
      return 'Unknown';
  }
};

const getSearchResultSubtitle = (result: SearchResult) => {
  switch (result.type) {
    case 'patient':
      return `Queue: ${(result.data as PatientData).queue_number || 'N/A'}`;
    case 'doctor':
      return (result.data as DoctorData).specialization || 'General';
    case 'medicine':
      return `Stock: ${(result.data as MedicineData).current_stock || 0}`;
    default:
      return '';
  }
};

// Dashboard variables

// Dashboard statistics
const dashboardStats = ref({
  todaysTasks: 0,
  patientsUnderCare: 0,
  vitalsChecked: 0,
  medicationsGiven: 0,
});

// Queue management (removed duplicate declarations)

// Load dashboard statistics
const loadDashboardStats = async () => {
  try {
    // Load patients in queue (normal + priority)
    const patientsResponse = await api.get('/operations/nurse/queue/patients/');
    const totalPatients =
      patientsResponse.data.normal_queue.length + patientsResponse.data.priority_queue.length;

    // Load medicine inventory count
    const medicinesResponse = await api.get('/operations/medicine-inventory/');
    const totalMedicines = medicinesResponse.data.length;

    // Load completed patient assessments (vitals checked)
    const assessmentsResponse = await api.get('/operations/patient-assessments/', {
      params: { status: 'completed' },
    });
    const vitalsChecked = assessmentsResponse.data.count || 0;

    // Today's tasks based on actual patient data
    const todaysTasksCount =
      totalPatients > 0
        ? totalPatients + (patientsResponse.data.priority_queue.length > 0 ? 1 : 0)
        : 0;

    dashboardStats.value = {
      todaysTasks: todaysTasksCount,
      patientsUnderCare: totalPatients,
      vitalsChecked,
      medicationsGiven: totalMedicines,
    };
  } catch (error) {
    console.error('Failed to load dashboard stats:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to load dashboard statistics',
      position: 'top',
      timeout: 3000,
    });
  }
};

// Real-time time and weather
const currentTime = ref('');
const weatherData = ref<{
  temperature: number;
  condition: string;
  location: string;
  description: string;
} | null>(null);
const weatherLoading = ref(false);
const weatherError = ref(false);
let timeInterval: NodeJS.Timeout | null = null;

// Mock user profile data - replace with actual API call
const userProfile = ref<{
  first_name?: string;
  last_name?: string;
  full_name: string;
  department?: string;
  role: string;
  profile_picture: string | null;
  verification_status: string;
  email?: string;
}>({
  first_name: '',
  last_name: '',
  full_name: 'Nurse',
  department: 'General Ward',
  role: 'nurse',
  profile_picture: null,
  verification_status: 'not_submitted',
  email: '',
});


const getTimeOfDay = () => {
  const hour = new Date().getHours();
  if (hour < 12) return 'morning';
  if (hour < 18) return 'afternoon';
  return 'evening';
};

const currentDate = computed(() => {
  const now = new Date();
  return now.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
});


// Update current time
const updateTime = () => {
  const now = new Date();

  // Convert to 12-hour format with AM/PM beside the time
  const hour = now.getHours();
  const ampm = hour >= 12 ? 'PM' : 'AM';
  const hour12 = hour % 12 || 12;
  const minute = now.getMinutes().toString().padStart(2, '0');
  const second = now.getSeconds().toString().padStart(2, '0');

  currentTime.value = `${hour12}:${minute}:${second} ${ampm}`;
};

// Fetch weather data
const fetchWeather = async () => {
  weatherLoading.value = true;
  weatherError.value = false;

  try {
    // Get user's location (default to Manila if geolocation fails)
    let latitude = 14.5995; // Default: Manila
    let longitude = 120.9842;

    if (navigator.geolocation) {
      try {
        const position = await new Promise<GeolocationPosition>((resolve, reject) => {
          navigator.geolocation.getCurrentPosition(resolve, reject, {
            timeout: 5000,
            enableHighAccuracy: false,
          });
        });
        latitude = position.coords.latitude;
        longitude = position.coords.longitude;
      } catch {
        console.log('Geolocation failed, using default location (Manila)');
      }
    }

    // Use OpenWeatherMap API
    const apiKey = '5c328a0059938745d143138d206eb570';
    const response = await fetch(
      `https://api.openweathermap.org/data/2.5/weather?lat=${latitude}&lon=${longitude}&appid=${apiKey}&units=metric`,
    );

    if (!response.ok) {
      throw new Error('Weather API request failed');
    }

    const data = await response.json();

    weatherData.value = {
      temperature: Math.round(data.main.temp),
      condition: data.weather[0].main.toLowerCase(),
      location: data.name,
      description: data.weather[0].description,
    };
  } catch (error) {
    console.error('Weather fetch error:', error);
    weatherError.value = true;

    // Fallback weather data
    weatherData.value = {
      temperature: 22,
      condition: 'clear',
      location: 'Local Area',
      description: 'Partly cloudy',
    };
  } finally {
    weatherLoading.value = false;
  }
};

const toggleRightDrawer = () => {
  rightDrawerOpen.value = !rightDrawerOpen.value;
};


// Fetch user profile from API
const fetchUserProfile = async () => {
  try {
    const response = await api.get('/users/profile/');
    const userData = response.data.user; // The API returns nested user data

    // Module-level verification toast removed; banner is shown only at login

    userProfile.value = {
      first_name: userData.first_name,
      last_name: userData.last_name,
      full_name: userData.full_name,
      department: userData.nurse_profile?.department,
      role: userData.role,
      profile_picture: userData.profile_picture || localStorage.getItem('profile_picture'),
      verification_status: userData.verification_status,
      email: userData.email,
    };

    // Removed module-level verification toast; banner is shown only once at login

    // Store profile picture in localStorage if available
    if (userData.profile_picture) {
      localStorage.setItem('profile_picture', userData.profile_picture);
    }

    console.log('User profile loaded:', userProfile.value);
  } catch (error) {
    console.error('Failed to fetch user profile:', error);

    // Fallback to localStorage
    const userData = localStorage.getItem('user');
    if (userData) {
      const user = JSON.parse(userData);
      userProfile.value = {
        full_name: user.full_name,
        department: user.nurse_profile?.department,
        role: user.role,
        profile_picture: user.profile_picture || null,
        verification_status: user.verification_status || 'not_submitted',
      };
    }
  }
};

// Load queue data
const loadQueueData = async () => {
  try {
    const dept = selectedDepartment.value || 'OPD'
    const response = await api.get(`/operations/nurse/queue/patients/?department=${dept}`);
    normalQueue.value = response.data.normal_queue || [];
    priorityQueue.value = response.data.priority_queue || [];
    const consolidated: ConsolidatedPatientDTO[] = Array.isArray(response.data.all_patients) ? response.data.all_patients : []
     const filtered = consolidated.filter((item) => !/^\s*jane patient\s*$/i.test(item.patient_name))
     const mapped = filtered.map((item: ConsolidatedPatientDTO) => {
        const base: QueueItem = {
          id: item.id,
          patient_name: item.patient_name,
          queue_number: String(item.queue_number ?? ''),
          queue_type: item.queue_type,
        }
        if (item.department !== undefined) base.department = item.department
        if (item.status !== undefined) base.status = item.status
        if (item.enqueue_time !== undefined) base.enqueue_time = item.enqueue_time
        if (item.priority_level !== undefined) base.priority_level = typeof item.priority_level === 'string' ? item.priority_level : String(item.priority_level)
 
        const derivedPosition = parseQueueNumber(item.queue_number) ?? item.position
        if (derivedPosition !== undefined) {
          base.position = derivedPosition
          if (item.queue_type === 'normal') base.position_in_queue = derivedPosition
          else base.priority_position = derivedPosition
        }
 
        return base
      })
      const unique = new Map<string, QueueItem>()
      for (const p of mapped) {
        unique.set(`${p.queue_type}|${p.id}|${p.queue_number}`, p)
      }
      allPatients.value = Array.from(unique.values())
    console.log(`NurseDashboard queues loaded: normal=${normalQueue.value.length}, priority=${priorityQueue.value.length}, all=${allPatients.value.length}`)
  } catch (error) {
    console.error('Failed to load queue data:', error);
  }
};

// WebSocket for real-time queue updates
const queueWebSocket = ref<WebSocket | null>(null)
const setupQueueWebSocket = (restart = false) => {
  try {
    if (restart && queueWebSocket.value) {
      try { queueWebSocket.value.close() } catch (err) { console.debug('Ignoring WebSocket close error', err) }
      queueWebSocket.value = null
    }
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const base = new URL(api.defaults.baseURL || `http://${window.location.hostname}:8000/api`)
    const backendHost = base.hostname
    const backendPort = base.port || (base.protocol === 'https:' ? '443' : '80')
    const dept = selectedDepartment.value || 'OPD'
    const wsUrl = `${protocol}//${backendHost}:${backendPort}/ws/queue/${dept}/`
    const ws = new WebSocket(wsUrl)
    queueWebSocket.value = ws
    ws.onopen = () => {
      console.log('NurseDashboard WebSocket connected')
    }
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'queue_status' || data.type === 'queue_status_update' || data.type === 'queue_schedule' || data.type === 'queue_schedule_update' || data.type === 'queue_notification') {
          void loadQueueData()
          console.log(`NurseDashboard queues refreshed via WebSocket: type=${data.type}, department=${dept}`)
        }
      } catch (e) {
        console.warn('Invalid WS message for NurseDashboard', e)
      }
    }
    ws.onclose = () => {
      console.log('NurseDashboard WebSocket disconnected')
      setTimeout(() => setupQueueWebSocket(true), 5000)
    }
  } catch (e) {
    console.warn('Failed to setup NurseDashboard WebSocket', e)
  }
}

// Load all queue schedules for current nurse
const loadAllSchedules = async () => {
  try {
    schedulesLoading.value = true;
    const response = await api.get('/operations/queue/schedules/');
    schedules.value = response.data || [];
    
    // Fetch actual queue status for all departments to get real is_open state
    try {
      const statusResponse = await api.get('/operations/queue/status/');
      const queueStatuses = statusResponse.data || [];
      
      // Update schedules with actual queue status
      schedules.value = schedules.value.map(schedule => {
        const status = queueStatuses.find((s: { department: string }) => s.department === schedule.department);
        return {
          ...schedule,
          is_open: status ? status.is_open : false
        };
      });
    } catch (statusError) {
      console.error('Failed to fetch queue statuses:', statusError);
    }
    
    // Update current schedule to selected department match, else first
    const dept = queueForm.value.department;
    const match = dept ? schedules.value.find((s) => s.department === dept) : schedules.value[0];
    currentSchedule.value = match
      ? {
          id: match.id,
          department: match.department,
          start_time: match.start_time,
          end_time: match.end_time,
          days_of_week: match.days_of_week,
          is_active: match.is_active,
          is_open: match.is_open || false,
        }
      : null;
  } catch (error) {
    console.error('Failed to load schedules:', error);
    schedules.value = [];
  } finally {
    schedulesLoading.value = false;
  }
};

// Load medicine data
const loadMedicineData = async () => {
  try {
    const response = await api.get('/operations/medicine-inventory/');
    medicines.value = response.data;
  } catch (error) {
    console.error('Failed to load medicine data:', error);
  }
};

// Load today's tasks based on patient data
const loadTodaysTasks = async () => {
  try {
    const tasks = [];

    // Get queue data to generate tasks
    const queueResponse = await api.get('/operations/nurse/queue/patients/');
    const totalPatients =
      queueResponse.data.normal_queue.length + queueResponse.data.priority_queue.length;

    // Generate tasks based on actual patient data
    if (totalPatients > 0) {
      tasks.push({
        id: 1,
        title: 'Patient Management',
        description: `Assess ${totalPatients} patients in queue`,
        icon: 'assignment',
        color: 'primary',
        status: 'Pending',
        status_color: 'orange',
      });

      if (queueResponse.data.priority_queue.length > 0) {
        tasks.push({
          id: 2,
          title: 'Priority Patient Care',
          description: `Attend to ${queueResponse.data.priority_queue.length} priority patients`,
          icon: 'emergency',
          color: 'red',
          status: 'Urgent',
          status_color: 'red',
        });
      }
    }

    todaysTasks.value = tasks;
  } catch (error) {
    console.error('Failed to load tasks:', error);
    todaysTasks.value = [];
  }
};

// Load completed assessments
const loadCompletedAssessments = () => {
  try {
    // This would typically come from a backend endpoint for completed assessments
    // For now, we'll use empty array as assessments are completed through the patient assessment page
    completedAssessments.value = [];
  } catch (error) {
    console.error('Failed to load completed assessments:', error);
    completedAssessments.value = [];
  }
};

// Queue management methods
const callNextPatient = async () => {
  if (isCallingPatient.value) return;
  isCallingPatient.value = true;
  try {
    const dept = selectedDepartment.value || 'OPD'
    console.log(`Calling next patient for department: ${dept}`);

    const resp = await api.post('/operations/queue/start-processing/', { department: dept })
    const data = resp?.data
    
    if (!data) {
      throw new Error('No data received from server');
    }

    try {
      // Persist the called patient's profile for Patient Management handoff
      if (data?.patient_profile) {
        const payload = { ...data.patient_profile, department: data.department || dept }
        // Update both store and localStorage (store handles localStorage, but for safety in transition)
        patientStore.setCurrentPatient(payload);
        console.log('Patient data persisted to store:', payload);
      } else {
        console.warn('No patient profile in response data');
      }
    } catch (e) {
      // Non-blocking storage failure
      console.warn('Failed to persist current serving patient', e)
    }
    $q.notify({
      type: 'positive',
      message: data?.patient ? `Started processing: ${data.patient.name} (#${data.current_serving}).` : 'Started processing next patient.',
      position: 'top'
    })
    await loadQueueData()
  } catch (error) {
    console.error('Failed to start queue processing:', error)
    const errorMsg = error instanceof Error ? error.message : 'Unknown error';
    $q.notify({ type: 'negative', message: `Failed to start next patient: ${errorMsg}`, position: 'top' })
  } finally {
    isCallingPatient.value = false;
  }
};

const manageQueue = async () => {
  await loadAllSchedules();
  isEditingSchedule.value = false;
  editingScheduleId.value = null;
  showQueueScheduleDialog.value = true;
};

const convertTo12Hour = (time24: string): string => {
  const [hours = '00', minutes = '00'] = time24.split(':');
  const h = parseInt(hours, 10);
  const ampm = h >= 12 ? 'PM' : 'AM';
  const h12 = h % 12 || 12;
  return `${h12.toString().padStart(2, '0')}:${minutes} ${ampm}`;
};

const editSchedule = (s: { id: number; department: DepartmentValue; start_time: string; end_time: string; days_of_week: number[]; is_active: boolean; is_open?: boolean; }) => {
  isEditingSchedule.value = true;
  editingScheduleId.value = s.id;
  queueForm.value = {
    department: s.department,
    start_time: convertTo12Hour(s.start_time),
    end_time: convertTo12Hour(s.end_time),
    days_of_week: [...s.days_of_week],
    is_active: s.is_active
  };
  currentSchedule.value = {
    id: s.id,
    department: s.department,
    start_time: s.start_time,
    end_time: s.end_time,
    days_of_week: s.days_of_week,
    is_active: s.is_active,
    is_open: s.is_open || false
  };
  showQueueScheduleDialog.value = true;
};

const deleteSchedule = async (s: { id: number; department: DepartmentValue; }) => {
  const confirm = window.confirm(`Delete schedule for ${getDepartmentLabel(s.department)}?`);
  if (!confirm) return;
  try {
    await api.delete(`/operations/queue/schedules/${s.id}/`);
    $q.notify({ type: 'positive', message: 'Schedule deleted' });
    await loadAllSchedules();
  } catch (error) {
    console.error('Failed to delete schedule:', error);
    $q.notify({ type: 'negative', message: 'Failed to delete schedule' });
  }
};

const saveQueueSchedule = async () => {
  if (!queueForm.value.department) {
    $q.notify({ type: 'negative', message: 'Please select a department' })
    return
  }
  
  // Validate time format
  if (!queueForm.value.start_time || !queueForm.value.end_time) {
    $q.notify({ type: 'negative', message: 'Please enter both start and end times' })
    return
  }
  
  // Validate days selection
  if (!queueForm.value.days_of_week || queueForm.value.days_of_week.length === 0) {
    $q.notify({ type: 'negative', message: 'Please select at least one day of the week' })
    return
  }
  
  savingSchedule.value = true
  
  // Convert 12-hour format to 24-hour format for backend
  const convertTo24Hour = (time12: string): string => {
    const parts = time12.split(' ')
    if (parts.length !== 2) {
      throw new Error('Invalid time format. Expected "HH:MM AM/PM"')
    }
    
    const [time, period] = parts
    if (!time || !period) {
      throw new Error('Invalid time format. Expected "HH:MM AM/PM"')
    }
    
    const timeParts = time.split(':')
    if (timeParts.length !== 2) {
      throw new Error('Invalid time format. Expected "HH:MM"')
    }
    
    const [hours, minutes] = timeParts
    if (!hours || !minutes) {
      throw new Error('Invalid time format. Expected "HH:MM"')
    }
    
    let hour24 = parseInt(hours)
    
    if (period === 'PM' && hour24 !== 12) {
      hour24 += 12
    } else if (period === 'AM' && hour24 === 12) {
      hour24 = 0
    }
    
    return `${hour24.toString().padStart(2, '0')}:${minutes}`
  }

  // Prepare the request data - ensure proper format
  const requestData = {
    department: queueForm.value.department,
    start_time: convertTo24Hour(queueForm.value.start_time), // Convert to 24-hour format
    end_time: convertTo24Hour(queueForm.value.end_time),     // Convert to 24-hour format
    days_of_week: queueForm.value.days_of_week.map(day => Number(day)), // Ensure integers
    is_active: true // Always set to true since we removed the toggle
  }
  
  console.log('User profile:', userProfile.value)
  console.log('Sending queue schedule request:', requestData)
  
  try {
    const response = isEditingSchedule.value && editingScheduleId.value != null
      ? await api.put(`/operations/queue/schedules/${editingScheduleId.value}/`, requestData)
      : await api.post('/operations/queue/schedules/', requestData)
    console.log('Queue schedule saved successfully:', response.data)
    $q.notify({ type: 'positive', message: isEditingSchedule.value ? 'Queue schedule updated successfully' : 'Queue schedule created successfully' })
    await loadAllSchedules(); // Refresh schedules and current schedule display
    showQueueScheduleDialog.value = false
    // Reset form and editing state
    isEditingSchedule.value = false;
    editingScheduleId.value = null;
    queueForm.value = { 
      department: 'OPD', 
      start_time: '08:00 AM', 
      end_time: '05:00 PM', 
      days_of_week: [0,1,2,3,4], 
      is_active: true 
    }
  } catch (error: unknown) {
    console.error('Failed to save queue schedule:', error)
    let errorMessage = 'Failed to save queue schedule'
    
    // Type guard for axios error
    if (error && typeof error === 'object' && 'response' in error) {
      const axiosError = error as { response?: { data?: unknown; status?: number }; message?: string }
      console.error('Error response data:', axiosError.response?.data)
      console.error('Error status:', axiosError.response?.status)

      const data = axiosError.response?.data
      if (data && typeof data === 'object' && data !== null) {
        const obj = data as Record<string, unknown>
        console.error('Error object keys:', Object.keys(obj))
        console.error('Full error object:', obj)
        
        // Handle specific error cases
        if (obj.error && typeof obj.error === 'string') {
          errorMessage = obj.error
        } else if (obj.non_field_errors && Array.isArray(obj.non_field_errors)) {
          errorMessage = obj.non_field_errors.join(', ')
        } else {
          // Handle field-specific validation errors
          const errorFields = Object.entries(obj).filter(([, value]) => Array.isArray(value) && value.length > 0)
          if (errorFields.length > 0) {
            const firstErrorField = errorFields[0]
            if (firstErrorField) {
              const [field, errors] = firstErrorField
              errorMessage = `${field}: ${Array.isArray(errors) ? errors[0] : errors}`
            }
          } else {
            const [firstKey, value] = Object.entries(obj)[0] ?? ['error', 'Failed to create queue schedule']
            if (Array.isArray(value) && value.length > 0 && typeof value[0] === 'string') {
              errorMessage = `${firstKey}: ${value[0]}`
            } else if (typeof value === 'string') {
              errorMessage = `${firstKey}: ${value}`
            }
          }
        }
      } else if (axiosError.message) {
        errorMessage = axiosError.message
      }
    } else if (error instanceof Error) {
      errorMessage = error.message
    }
    
    $q.notify({ type: 'negative', message: errorMessage })
  } finally {
    savingSchedule.value = false
  }
};

// Fetch current schedule for the nurse
const fetchCurrentSchedule = async () => {
  try {
    const response = await api.get('/operations/queue/schedules/')
    if (response.data && response.data.length > 0) {
      // Get the first (most recent) schedule
      const schedule = response.data[0]
      
      // Fetch actual queue status to get real is_open state
      let actualIsOpen = schedule.is_open || false
      try {
        const statusResponse = await api.get(`/operations/queue/status/?department=${schedule.department}`)
        if (statusResponse.data) {
          actualIsOpen = statusResponse.data.is_open || false
        }
      } catch (statusError) {
        console.warn('Failed to fetch queue status, using schedule data:', statusError)
      }
      
      currentSchedule.value = {
        id: schedule.id,
        department: schedule.department,
        start_time: schedule.start_time,
        end_time: schedule.end_time,
        days_of_week: schedule.days_of_week,
        is_active: schedule.is_active,
        is_open: actualIsOpen
      }
    } else {
      currentSchedule.value = null
    }
  } catch (error) {
    console.error('Failed to fetch current schedule:', error)
    currentSchedule.value = null
  }
};

// Toggle queue status (open/close)
const toggleQueueStatus = async () => {
  if (!currentSchedule.value) return
  
  togglingQueue.value = true
  const newStatus = !currentSchedule.value.is_open
  
  const requestData = {
    department: currentSchedule.value.department,
    is_open: newStatus
  }
  
  console.log('Toggling queue status:', requestData)
  
  try {
    const response = await api.post('/operations/queue/status/', requestData)
    console.log('Queue status updated successfully:', response.data)
    
    // Update the local state
    if (currentSchedule.value) {
      currentSchedule.value.is_open = newStatus
      const idx = schedules.value.findIndex(s => s.id === currentSchedule.value!.id)
      if (idx !== -1) {
        const item = schedules.value[idx]
        if (item) item.is_open = newStatus
      }
    }
    
    // Use the message from the backend if available, otherwise use default
    const message = response.data?.message || (newStatus 
      ? 'Queue is now OPEN! Patients have been notified.' 
      : 'Queue is now CLOSED.')
    
    $q.notify({ 
      type: 'positive', 
      message,
      position: 'top',
      timeout: 4000
    })
    
  } catch (error: unknown) {
    console.error('Failed to toggle queue status:', error)
    let errorMessage = 'Failed to update queue status'
    
    if (error && typeof error === 'object' && 'response' in error) {
      const axiosError = error as { response?: { data?: unknown; status?: number }; message?: string }
      console.error('Error response data:', axiosError.response?.data)
      console.error('Error status:', axiosError.response?.status)
      
      const data = axiosError.response?.data
      if (data && typeof data === 'object' && data !== null) {
        const obj = data as Record<string, unknown>
        console.error('Error object keys:', Object.keys(obj))
        console.error('Full error object:', obj)
        
        if (obj.error && typeof obj.error === 'string') {
          errorMessage = obj.error
        } else if (obj.non_field_errors && Array.isArray(obj.non_field_errors)) {
          errorMessage = obj.non_field_errors.join(', ')
        } else {
          // Handle field-specific validation errors
          const errorFields = Object.entries(obj).filter(([, value]) => Array.isArray(value) && value.length > 0)
          if (errorFields.length > 0) {
            const firstErrorField = errorFields[0]
            if (firstErrorField) {
              const [field, errors] = firstErrorField
              errorMessage = `${field}: ${Array.isArray(errors) ? errors[0] : errors}`
            }
          } else {
            const [firstKey, value] = Object.entries(obj)[0] ?? ['error', 'Failed to update queue status']
            if (Array.isArray(value) && value.length > 0 && typeof value[0] === 'string') {
              errorMessage = `${firstKey}: ${value[0]}`
            } else if (typeof value === 'string') {
              errorMessage = `${firstKey}: ${value}`
            }
          }
        }
      } else if (axiosError.message) {
        errorMessage = axiosError.message
      }
    } else if (error instanceof Error) {
      errorMessage = error.message
    }
    
    $q.notify({ type: 'negative', message: errorMessage })
  } finally {
    togglingQueue.value = false
  }
};

// Helper functions for formatting
const getDepartmentLabel = (value: DepartmentValue): string => {
  const option = departmentOptions.value.find((opt) => opt.value === value)
  return option ? option.label : String(value)
};

const formatTimeDisplay = (time24: string): string => {
  const [hours, minutes] = time24.split(':')
  if (!hours || !minutes) return time24
  const hour = parseInt(hours)
  const ampm = hour >= 12 ? 'PM' : 'AM'
  const hour12 = hour % 12 || 12
  return `${hour12}:${minutes} ${ampm}`
};

const formatDays = (days: number[]): string => {
  const dayNames = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
  return days.map(day => dayNames[day]).join(', ')
};


// Notification functions
const unreadNotificationsCount = computed(() => {
  return notifications.value.filter((n) => !n.isRead).length;
});

const loadNotifications = async (): Promise<void> => {
  try {
    console.log('📬 Loading notifications...');

    // Load message notifications
    const messageResponse = await api.get('/operations/messaging/notifications/');
    const messageNotifications = messageResponse.data || [];

    // Load system notifications (medicine stock alerts, analytics alerts)
    const systemNotifications = await loadSystemNotifications();

    // Combine and format all notifications
    const allNotifications = [
      ...formatMessageNotifications(messageNotifications),
      ...systemNotifications,
    ];

    // Sort by creation date (newest first)
    notifications.value = allNotifications.sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    );

    console.log('✅ Notifications loaded:', notifications.value.length);
  } catch (error: unknown) {
    console.error('❌ Error loading notifications:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to load notifications',
    });
  }
};

// Format message notifications from backend
const formatMessageNotifications = (rawNotifications: RawNotification[]): Notification[] => {
  return rawNotifications.map((notif) => ({
    id: notif.id,
    title: `New message from ${notif.message?.sender?.full_name || 'Unknown'}`,
    message: notif.message?.content || 'You have a new message',
    type: 'message' as const,
    isRead: notif.is_sent || false,
    created_at: notif.created_at,
    sender_id: notif.message?.sender?.id,
    conversation_id: notif.message?.conversation?.id,
  }));
};

// Load system notifications (medicine stock, analytics alerts)
const loadSystemNotifications = async (): Promise<Notification[]> => {
  const systemNotifications: Notification[] = [];

  try {
    // Check for low medicine stock
    const medicineResponse = await api.get('/operations/medicine-inventory/');
    const medicines = (medicineResponse.data || []) as Array<{ stock_quantity?: number; minimum_stock?: number }>;

    const lowStockMedicines = medicines.filter(
      (med) => Number(med.stock_quantity ?? 0) <= Number(med.minimum_stock ?? 0),
    );

    if (lowStockMedicines.length > 0) {
      systemNotifications.push({
        id: `low-stock-${Date.now()}`,
        title: 'Low Medicine Stock Alert',
        message: `${lowStockMedicines.length} medicine(s) are running low on stock`,
        type: 'system',
        isRead: false,
        created_at: new Date().toISOString(),
      });
    }
  } catch (error) {
    console.error('Error loading system notifications:', error);
  }

  return systemNotifications;
};

// Stock Alerts types and state
 type StockSeverity = 'low' | 'critical' | 'expiry';
 interface StockAlert {
   id: string | number;
   title: string;
   message: string;
   severity: StockSeverity;
   color: string;
   created_at: string;
   isRead: boolean;
 }

 const stockAlerts = ref<StockAlert[]>([]);
 const READ_STOCK_KEY = 'read_stock_alert_ids';
 const loadReadStockAlertIds = (): Set<string> => {
   try {
     const raw = localStorage.getItem(READ_STOCK_KEY);
     const arr = raw ? (JSON.parse(raw) as string[]) : [];
     return new Set(Array.isArray(arr) ? arr : []);
   } catch {
     return new Set<string>();
   }
 };
 const persistReadStockAlertIds = (ids: Set<string>) => {
   try {
     localStorage.setItem(READ_STOCK_KEY, JSON.stringify(Array.from(ids)));
   } catch {
     // ignore
   }
 };
 const readStockAlertIds = ref<Set<string>>(loadReadStockAlertIds());

 const getStockAlertIcon = (severity: StockSeverity) => {
   if (severity === 'critical') return 'error';
   if (severity === 'low') return 'warning_amber';
   return 'schedule';
 };

 const loadStockAlerts = async (): Promise<void> => {
   try {
     const res = await api.get('/operations/medicine-inventory/');
     const list = Array.isArray(res.data?.results) ? res.data.results : res.data;
     const medicines: MedicineData[] = Array.isArray(list) ? list : [] as unknown as MedicineData[];

     const alerts: StockAlert[] = [];
     const now = new Date();
     const soonThresholdDays = 30;

     for (const med of medicines) {
       const name = med.medicine_name ?? 'Unknown Medicine';
       const current = Number(med.current_stock ?? med.stock_quantity ?? 0);
       const minLevel = Number(med.minimum_stock_level ?? med.minimum_stock ?? 0);
       const expiryStr = med.expiry_date ?? undefined;

       if (current === 0) {
         const id = `out-${med.id}`;
         alerts.push({
           id,
           title: `${name} is out of stock`,
           message: 'Please restock immediately.',
           severity: 'critical',
           color: 'negative',
           created_at: new Date().toISOString(),
           isRead: readStockAlertIds.value.has(String(id)),
         });
         continue;
       }
 
       if (!Number.isNaN(minLevel) && current <= minLevel) {
         const id = `low-${med.id}`;
         alerts.push({
           id,
           title: `${name} is running low on stock`,
           message: `Current quantity: ${current} units`,
           severity: 'low',
           color: 'warning',
           created_at: new Date().toISOString(),
           isRead: readStockAlertIds.value.has(String(id)),
         });
       }
 
       if (expiryStr) {
         const expiry = new Date(expiryStr);
         const diffDays = Math.round((expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
         if (diffDays >= 0 && diffDays <= soonThresholdDays && current > 0) {
           const id = `exp-${med.id}`;
           alerts.push({
             id,
             title: `${name} will expire in ${diffDays} days`,
             message: `Current quantity: ${current} units`,
             severity: 'expiry',
             color: 'orange',
             created_at: new Date().toISOString(),
             isRead: readStockAlertIds.value.has(String(id)),
           });
         }
       }
     }

     stockAlerts.value = alerts.sort(
       (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
     );
   } catch (error) {
     console.error('Failed to load stock alerts:', error);
     stockAlerts.value = [];
     $q.notify({ type: 'negative', message: 'Failed to load stock alerts' });
   }
 };

 watch(showStockAlerts, (val) => {
  if (val) {
    void loadStockAlerts();
  }
});

// Mark stock alerts as read
const markStockAlertRead = (id: string | number): void => {
  const key = String(id);
  if (!readStockAlertIds.value.has(key)) {
    readStockAlertIds.value.add(key);
    persistReadStockAlertIds(readStockAlertIds.value);
  }
  stockAlerts.value = stockAlerts.value.map((a) => (
    a.id === id ? { ...a, isRead: true } : a
  ));
};

const markAllStockAlertsRead = (): void => {
  for (const a of stockAlerts.value) {
    readStockAlertIds.value.add(String(a.id));
  }
  persistReadStockAlertIds(readStockAlertIds.value);
  stockAlerts.value = stockAlerts.value.map((a) => ({ ...a, isRead: true }));
};

const handleNotificationClick = (notification: Notification): void => {
  // Mark as read
  notification.isRead = true;

  // If it's a message notification, navigate to messaging
  if (notification.type === 'message') {
    showNotifications.value = false;
    void router.push('/nurse-messaging');
  }
};

const markAllNotificationsRead = async (): Promise<void> => {
  try {
    // Mark all notifications as read locally
    notifications.value.forEach((notification) => {
      notification.isRead = true;
    });

    // Mark message notifications as read on backend
    const messageNotifications = notifications.value.filter((n) => n.type === 'message');
    for (const notification of messageNotifications) {
      try {
        await api.post(`/operations/messaging/notifications/${notification.id}/mark-sent/`);
      } catch (error) {
        console.error('Error marking notification as read:', error);
      }
    }

    // Update the notification count
    await loadNotifications();

    $q.notify({
      type: 'positive',
      message: 'All notifications marked as read',
    });
  } catch (error) {
    console.error('Error marking notifications as read:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to mark notifications as read',
    });
  }
};

const formatTime = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
};

// Search input handler
const onSearchInput = (value: string) => {
  if (value && value.length > 2) {
    void performSearch(value);
  } else {
    searchResults.value = [];
  }
};

// Clear search
const clearSearch = () => {
  text.value = '';
  searchResults.value = [];
};

// Select search result
const selectSearchResult = (result: SearchResult) => {
  searchResults.value = [];
  text.value = '';

  // Navigate based on result type
  switch (result.type) {
    case 'patient':
      void router.push('/nurse-patient-assessment');
      break;
    case 'doctor':
      $q.notify({
        type: 'info',
        message: `Selected doctor: ${getSearchResultTitle(result)}`,
        position: 'top',
      });
      break;
    case 'medicine':
      void router.push('/nurse-medicine-inventory');
      break;
  }
};

// Fetch location data
const fetchLocation = async () => {
  locationLoading.value = true;
  locationError.value = false;

  try {
    if (navigator.geolocation) {
      const position = await new Promise<GeolocationPosition>((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          timeout: 5000,
          enableHighAccuracy: false,
        });
      });

      // Use reverse geocoding to get city name
      const response = await fetch(
        `https://api.openweathermap.org/geo/1.0/reverse?lat=${position.coords.latitude}&lon=${position.coords.longitude}&limit=1&appid=5c328a0059938745d143138d206eb570`,
      );

      if (response.ok) {
        const data = await response.json();
        if (data.length > 0) {
          locationData.value = {
            city: data[0].name,
            country: data[0].country,
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
          };
        }
      }
    }
  } catch (error) {
    console.error('Location fetch error:', error);
    locationError.value = true;
    // Fallback location
    locationData.value = {
      city: 'Manila',
      country: 'PH',
      latitude: 14.5995,
      longitude: 120.9842,
    };
  } finally {
    locationLoading.value = false;
  }
};

onMounted(() => {
  // Load user profile data from API
  void fetchUserProfile();

  // Load dashboard statistics
  void loadDashboardStats();

  // Load queue and medicine data
  void loadQueueData();
  setupQueueWebSocket();
  void loadMedicineData();

  // Load task and assessment data
  void loadTodaysTasks();
  void loadCompletedAssessments();

  // Load notifications
  void loadNotifications();

  // Load existing queue schedules
  void loadAllSchedules();
  
  // Ensure current schedule is available for toggling
  void fetchCurrentSchedule();

  // Initialize real-time features
  updateTime(); // Set initial time
  timeInterval = setInterval(updateTime, 1000); // Update every second

  // Fetch weather data
  void fetchWeather();

  // Fetch location data
  void fetchLocation();

  // Refresh weather every 30 minutes
  setInterval(() => void fetchWeather(), 30 * 60 * 1000);

  // Refresh dashboard stats every 5 minutes
  setInterval(() => void loadDashboardStats(), 5 * 60 * 1000);

  // Refresh user profile every 30 seconds to check for verification status updates
  setInterval(() => {
    void fetchUserProfile();
  }, 30000);

  // More frequent verification status check (every 10 seconds)
  setInterval(() => {
    void fetchUserProfile();
  }, 10000);
});

// Removed profile picture storage sync: initials-only avatar

// Cleanup on component unmount
onUnmounted(() => {
  if (timeInterval) {
    clearInterval(timeInterval);
  }
});
</script>

<style scoped>
/* Header Styles */
.prototype-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.header-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  min-height: 64px;
}

.header-left {
  flex: 1;
  display: flex;
  align-items: center;
  margin-left: 16px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.menu-toggle-btn {
  color: white;
}

.notification-btn {
  color: white;
}

/* Pills for time, weather, location */
.time-pill,
.weather-pill,
.location-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 20px;
  padding: 6px 12px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.time-text,
.weather-text,
.location-text {
  font-size: 13px;
  font-weight: 500;
  color: white;
}

.weather-loading,
.weather-error,
.location-loading,
.location-error {
  background: rgba(255, 255, 255, 0.1);
  opacity: 0.7;
}

/* Mobile Header Layout */
.mobile-header-layout {
  display: none;
  flex-direction: column;
  padding: 8px 16px;
  gap: 12px;
}

.header-top-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  justify-content: center;
}

.header-bottom-row {
  display: flex;
  align-items: center;
}

/* Responsive Design */
@media (max-width: 768px) {
  .header-toolbar {
    display: none;
  }

  .mobile-header-layout {
    display: flex;
  }

  .time-pill,
  .weather-pill,
  .location-pill {
    padding: 4px 8px;
    font-size: 12px;
  }

  .time-text,
  .weather-text,
  .location-text {
    font-size: 11px;
  }
}

.page-background {
  background: #f5f5f5;
  min-height: 100vh;
  position: relative;
}

.search-container {
  display: flex;
  justify-content: center;
  width: 100%;
  padding: 0 20px;
  position: relative;
}

.search-results {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  max-height: 300px;
  overflow-y: auto;
}

.search-input {
  max-width: 600px;
  width: 100%;
}

/* Real-time info styles */
.real-time-info {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-left: 20px;
}

.time-display,
.weather-display,
.weather-loading,
.weather-error {
  display: flex;
  align-items: center;
  gap: 8px;
  color: white;
  font-size: 14px;
}

.time-text,
.weather-text,
.weather-location {
  font-size: 14px;
  font-weight: 500;
  color: white;
}

.weather-location {
  font-size: 12px;
  opacity: 0.8;
}

/* Greeting Section Styles */
.greeting-section {
  padding: 30px 20px;
  margin-bottom: 20px;
}

.greeting-content {
  max-width: 1200px;
  margin: 0 auto;
}

.greeting-text {
  color: #333;
  font-size: 28px;
  font-weight: 600;
  margin: 0 0 8px 0;
}

.greeting-subtitle {
  color: #666;
  font-size: 16px;
  margin: 0;
  font-weight: 400;
}

/* Carousel Section Styles */
.carousel-section {
  padding: 20px;
  margin-bottom: 20px;
}

.dashboard-carousel {
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  max-width: 1200px;
  margin: 0 auto;
}

/* Dashboard Statistics Styles */
.stats-section {
  padding: 20px;
  margin-bottom: 20px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.stat-card {
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease;
  cursor: pointer;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

.stat-icon {
  margin-bottom: 10px;
}

.stat-number {
  font-size: 2.5rem;
  font-weight: bold;
  margin-bottom: 5px;
}

.stat-label {
  font-size: 1rem;
  color: #666;
  margin-bottom: 10px;
}

.tasks-breakdown {
  margin-top: 10px;
  font-size: 0.9rem;
}

.task-item {
  margin: 2px 0;
}

.task-type {
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: 500;
}

.task-type.urgent {
  background: rgba(244, 67, 54, 0.1);
  color: #f44336;
}

.task-type.routine {
  background: rgba(76, 175, 80, 0.1);
  color: #4caf50;
}

/* Card-specific colors */
.patients-card .stat-icon {
  color: #2196f3;
}

.tasks-card .stat-icon {
  color: #ff9800;
}

.vitals-card .stat-icon {
  color: #e91e63;
}

.medications-card .stat-icon {
  color: #4caf50;
}

.q-header {
  background: #286660 !important;
}

.q-toolbar {
  background: #286660 !important;
}

.q-avatar {
  background: white;
  border-radius: 8px;
}

.q-avatar img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

/* Drawer Styles */
.drawer-content {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.user-profile-section {
  padding: 20px;
  text-align: center;
  border-bottom: 1px solid #e0e0e0;
  background: #f8f9fa;
}

.profile-picture-container {
  position: relative;
  display: inline-block;
  margin-bottom: 15px;
}

.profile-avatar {
  border: 3px solid #1e7668 !important;
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


.user-info {
  margin-top: 10px;
}

.user-name {
  margin: 0 0 5px 0;
  color: #333;
  font-size: 18px;
  font-weight: 600;
}

.clickable-name {
  cursor: pointer;
  transition: color 0.2s ease;
}

.clickable-name:hover {
  color: #1e7668;
}

.user-specialization {
  margin: 0 0 10px 0;
  color: #666;
  font-size: 14px;
}

.navigation-menu {
  flex: 1;
  padding: 10px 0;
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

/* Safe Area Support */
.safe-area-top {
  padding-top: env(safe-area-inset-top);
}

.safe-area-bottom {
  padding-bottom: env(safe-area-inset-bottom);
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

/* Mobile Header Layout */
.mobile-header-layout {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.header-top-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  min-height: 48px;
}

.header-bottom-row {
  padding: 0 16px 8px;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  justify-content: center;
}

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

.header-right {
  display: flex;
  align-items: center;
  gap: 24px;
}

.search-container {
  width: 100%;
  max-width: 500px;
}

.search-input {
  background: white;
  border-radius: 8px;
}

.notification-btn {
  color: white;
}

/* Time and Weather Display Styles */
.time-display {
  display: flex;
  align-items: center;
  gap: 4px;
  color: white;
  font-size: 12px;
}

.weather-display {
  display: flex;
  align-items: center;
  gap: 4px;
  color: white;
  font-size: 12px;
}

.weather-loading,
.weather-error {
  display: flex;
  align-items: center;
  gap: 4px;
  color: white;
  font-size: 12px;
}

.time-text,
.weather-text {
  font-weight: 500;
}

.weather-location {
  font-size: 10px;
  opacity: 0.8;
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

/* Prototype Sidebar Styles */
.prototype-sidebar {
  background: white;
  border-right: 1px solid #e0e0e0;
  position: relative;
}

.sidebar-content {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding-bottom: 80px; /* Space for footer */
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


.verified-badge {
  position: absolute;
  top: -5px;
  right: -5px;
  background: white;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}

.user-name {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin: 0 0 4px 0;
}

.user-role {
  font-size: 14px;
  color: #666;
  margin: 0 0 12px 0;
}

.navigation-menu {
  flex: 1;
  padding: 16px 0;
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

.sidebar-footer {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 20px;
  border-top: 1px solid #e0e0e0;
  background: #f8f9fa;
}

/* Page Container with Background */
.page-container-with-fixed-header {
  background: #f8f9fa;
  min-height: 100vh;
  position: relative;
}

/* Greeting Section */
.greeting-section {
  padding: 24px;
  background: transparent;
}

.greeting-card {
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(25px);
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.25);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.4);
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  position: relative;
  width: 100%;
  max-width: none;
  margin: 0;
}

.greeting-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #286660, #6ca299, #b8d2ce);
  border-radius: 16px 16px 0 0;
  opacity: 1;
}

.greeting-content {
  padding: 24px;
  /* Ensure greeting spans full width and aligns left */
  max-width: none;
  margin: 0;
  text-align: left;
}

.greeting-text {
  font-size: 28px;
  font-weight: 700;
  color: #333;
  margin: 0 0 8px 0;
}

.greeting-subtitle {
  font-size: 16px;
  color: #666;
  margin: 0;
}

.greeting-card:hover {
  transform: none;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.25);
  background: rgba(255, 255, 255, 0.15);
}

.greeting-card:hover::before {
  opacity: 1;
}

/* Dashboard Content */
.dashboard-content {
  padding: 0 24px 24px;
  width: 100%;
  max-width: none;
  margin: 0;
}

.dashboard-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 26px;
  margin-bottom: 32px;
}

/* Unified grid container to match DoctorDashboard */
.dashboard-cards-section {
  padding: 0 24px 24px;
  width: 100%;
  max-width: none;
  margin: 0;
}

.dashboard-cards-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 26px;
  margin-bottom: 32px;
}

/* Responsive design to match DoctorDashboard */
@media (max-width: 768px) {
  .dashboard-cards {
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
  }
}

@media (max-width: 480px) {
  .dashboard-cards {
    grid-template-columns: 1fr;
    gap: 12px;
  }
}

/* Mobile readability and touch-friendly sizing */
@media (max-width: 768px) {
  .greeting-content { padding: 18px; }
  .greeting-text { font-size: 22px; }
  .greeting-subtitle { font-size: 14px; }
  .queueing-actions { gap: 12px; }
  .queueing-actions .q-btn, .action-btn { min-height: 44px; padding: 10px 14px; font-size: 14px; }
}

@media (max-width: 480px) {
  .greeting-content { padding: 16px; }
  .greeting-text { font-size: 20px; }
  .greeting-subtitle { font-size: 13px; }
  .queueing-actions { gap: 10px; }
  .queueing-actions .q-btn, .action-btn { min-height: 44px; padding: 10px 12px; font-size: 13px; }
}

@media (max-width: 768px) {
  .prototype-header {
    padding-top: max(env(safe-area-inset-top), 8px);
  }

  .header-toolbar {
    padding: 0 16px;
    min-height: 56px;
    padding-top: max(env(safe-area-inset-top), 4px);
  }

  .header-right {
    gap: 12px;
  }

  .search-container {
    max-width: 300px;
  }

  .time-pill,
  .weather-pill,
  .location-pill {
    font-size: 12px;
    padding: 4px 8px;
  }

  /* Mobile Header Layout */
  .header-top-row {
    padding: 4px 12px;
    min-height: 44px;
  }

  .header-bottom-row {
    padding: 0 12px 6px;
  }

  .header-info {
    gap: 8px;
  }

  .time-display,
  .weather-display,
  .weather-loading,
  .weather-error {
    font-size: 11px;
  }

  .time-text,
  .weather-text {
    font-size: 11px;
  }

  .weather-location {
    font-size: 9px;
  }

  /* Hide time display on mobile to save space */
  .time-display {
    display: none;
  }

  /* Make weather display more compact */
  .weather-display {
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
  }

  .weather-location {
    display: none;
  }

  .greeting-section {
    padding: 16px;
  }

  .greeting-content {
    padding: 20px;
  }

  .dashboard-cards-section {
    padding: 16px;
  }

  .dashboard-cards-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
    margin-bottom: 24px;
  }

  .card-content {
    padding: 20px;
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .card-title {
    font-size: 1.1rem;
  }

  .card-value {
    font-size: 2.2rem;
    align-self: flex-end;
  }

  .card-description {
    font-size: 0.85rem;
  }

  .card-icon {
    margin-left: 0;
    align-self: flex-end;
  }

  .queueing-section {
    padding: 0 16px 16px;
  }

  .queueing-header {
    padding: 20px;
  }

  .queueing-title {
    font-size: 1.3rem;
  }

  .queueing-actions {
    flex-direction: column;
    align-items: center;
  }

  .action-btn {
    min-width: 200px;
    width: 100%;
    max-width: 280px;
  }

  .queue-panels-section {
    padding: 16px;
  }

  .queue-panels-container {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .queue-panel {
    padding: 16px;
    min-height: 150px;
  }
}

.dashboard-card {
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(25px);
  -webkit-backdrop-filter: blur(25px);
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.25);
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.4);
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  position: relative;
  min-height: 240px;
}

.dashboard-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  /* Default brand gradient; overridden per card type below */
  background: linear-gradient(90deg, #286660, #6ca299, #b8d2ce);
  border-radius: 16px 16px 0 0;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.dashboard-card:hover {
  transform: translateY(-8px) scale(1.02);
  box-shadow:
    0 20px 60px rgba(0, 0, 0, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.4);
  background: rgba(255, 255, 255, 0.25);
}

.dashboard-card:hover::before {
  opacity: 1;
}

/* Tint glassmorphism top bar to match each card color */
.tasks-card::before {
  background: linear-gradient(90deg, #2196f3, #64b5f6, #bbdefb);
}
.patients-card::before {
  background: linear-gradient(90deg, #4caf50, #81c784, #c8e6c9);
}
.vitals-card::before {
  background: linear-gradient(90deg, #ff9800, #ffb74d, #ffe0b2);
}
.medications-card::before {
  background: linear-gradient(90deg, #9c27b0, #ba68c8, #e1bee7);
}

.card-content {
  padding: 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
}

.card-text {
  flex: 1;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
  line-height: 1.3;
}

.card-value {
  font-size: 32px;
  font-weight: 700;
  color: #286660;
  line-height: 1;
  margin-top: 8px;
}

.card-description {
  font-size: 14px;
  color: #666;
  line-height: 1.4;
  margin-bottom: 8px;
}

.card-icon {
  margin-left: 16px;
  color: #286660;
  opacity: 0.8;
  transition: all 0.3s ease;
}

.dashboard-card:hover .card-icon {
  opacity: 1;
  transform: scale(1.1);
}

/* Card-specific backgrounds and colors to match DoctorDashboard */
.tasks-card {
  background: linear-gradient(135deg,
    rgba(33, 150, 243, 0.15) 0%,
    rgba(66, 165, 245, 0.1) 25%,
    rgba(255, 255, 255, 0.2) 100%);
  border: 1px solid rgba(33, 150, 243, 0.3);
}
.tasks-card:hover {
  background: linear-gradient(135deg,
    rgba(33, 150, 243, 0.25) 0%,
    rgba(66, 165, 245, 0.2) 25%,
    rgba(255, 255, 255, 0.3) 100%);
  border: 1px solid rgba(33, 150, 243, 0.5);
}

.patients-card {
  background: linear-gradient(135deg,
    rgba(76, 175, 80, 0.15) 0%,
    rgba(102, 187, 106, 0.1) 25%,
    rgba(255, 255, 255, 0.2) 100%);
  border: 1px solid rgba(76, 175, 80, 0.3);
}
.patients-card:hover {
  background: linear-gradient(135deg,
    rgba(76, 175, 80, 0.25) 0%,
    rgba(102, 187, 106, 0.2) 25%,
    rgba(255, 255, 255, 0.3) 100%);
  border: 1px solid rgba(76, 175, 80, 0.5);
}

.vitals-card {
  background: linear-gradient(135deg,
    rgba(255, 152, 0, 0.15) 0%,
    rgba(255, 183, 77, 0.1) 25%,
    rgba(255, 255, 255, 0.2) 100%);
  border: 1px solid rgba(255, 152, 0, 0.3);
}
.vitals-card:hover {
  background: linear-gradient(135deg,
    rgba(255, 152, 0, 0.25) 0%,
    rgba(255, 183, 77, 0.2) 25%,
    rgba(255, 255, 255, 0.3) 100%);
  border: 1px solid rgba(255, 152, 0, 0.5);
}

.medications-card {
  background: linear-gradient(135deg,
    rgba(156, 39, 176, 0.15) 0%,
    rgba(186, 104, 200, 0.1) 25%,
    rgba(255, 255, 255, 0.2) 100%);
  border: 1px solid rgba(156, 39, 176, 0.3);
}
.medications-card:hover {
  background: linear-gradient(135deg,
    rgba(156, 39, 176, 0.25) 0%,
    rgba(186, 104, 200, 0.2) 25%,
    rgba(255, 255, 255, 0.3) 100%);
  border: 1px solid rgba(156, 39, 176, 0.5);
}

/* Add blue-tinted glassmorphism for Tasks card to match its color */
.tasks-card {
  background: linear-gradient(135deg,
    rgba(33, 150, 243, 0.15) 0%,
    rgba(100, 181, 246, 0.1) 25%,
    rgba(255, 255, 255, 0.2) 100%);
  border: 1px solid rgba(33, 150, 243, 0.3);
}
.tasks-card:hover {
  background: linear-gradient(135deg,
    rgba(33, 150, 243, 0.25) 0%,
    rgba(100, 181, 246, 0.2) 25%,
    rgba(255, 255, 255, 0.3) 100%);
  border: 1px solid rgba(33, 150, 243, 0.5);
}

/* Card-specific value colors */
.tasks-card .card-value { color: #2196f3; }
.patients-card .card-value { color: #4caf50; }
.vitals-card .card-value { color: #ff9800; }
.medications-card .card-value { color: #9c27b0; }

/* Queueing Section */
.queueing-section {
  padding: 0 24px 24px;
  width: 100%;
  max-width: none;
  margin: 0;
}

.queueing-card {
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(25px);
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.25);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.4);
  overflow: hidden;
  position: relative;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.queueing-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #286660, #6ca299, #b8d2ce);
  border-radius: 16px 16px 0 0;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.queueing-card:hover {
  transform: translateY(-8px) scale(1.02);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.4);
  background: rgba(255, 255, 255, 0.25);
}

.queueing-card:hover::before {
  opacity: 1;
}

.queueing-header {
  text-align: center;
  padding: 24px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

.queueing-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #333;
  margin: 0 0 20px 0;
}

.queueing-actions {
  display: flex;
  gap: 16px;
  justify-content: center;
  flex-wrap: wrap;
}

.action-btn {
  min-width: 180px;
}

.queue-panels-section {
  padding: 24px;
}

.queue-panels-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.queue-panel {
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(25px);
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.25);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.4);
  padding: 20px;
  min-height: 200px;
  position: relative;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.queue-panel::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #286660, #6ca299, #b8d2ce);
  border-radius: 16px 16px 0 0;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.queue-panel:hover {
  transform: translateY(-4px) scale(1.01);
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.4);
  background: rgba(255, 255, 255, 0.25);
}

.queue-panel:hover::before {
  opacity: 1;
}

.queue-panel-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #333;
  margin: 0 0 16px 0;
  text-align: center;
}

.queue-content {
  text-align: center;
}

.empty-queue {
  color: #666;
  font-style: italic;
  padding: 40px 20px;
}

.queue-list {
  /* Patient list styling will be added when patient data is implemented */
  padding: 0;
}

/* Modal Styles */
.modal-card {
  min-width: 500px;
  max-width: 600px;
  max-height: 80vh;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

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

.modal-card .q-card-section {
  padding: 20px;
}

.modal-card .text-h6 {
  font-size: 1.5rem;
  font-weight: 600;
  color: #286660;
  margin: 0;
}

.modal-card .q-list {
  max-height: 400px;
  overflow-y: auto;
}

.modal-card .q-item {
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
}

.modal-card .q-item:last-child {
  border-bottom: none;
}

.modal-card .q-item-section {
  padding: 0 8px;
}

.modal-card .q-item-label {
  font-size: 1rem;
  font-weight: 500;
  color: #333;
}

.modal-card .q-item-label.caption {
  font-size: 0.875rem;
  color: #666;
  margin-top: 4px;
}

.modal-card .q-chip {
  font-size: 0.75rem;
  font-weight: 500;
  padding: 4px 8px;
  border-radius: 12px;
}

/* Empty state styling */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
}

.empty-state .q-icon {
  margin-bottom: 16px;
}

.empty-state p {
  margin: 0;
  font-size: 1rem;
  font-weight: 500;
}

@media (max-width: 480px) {
  .prototype-header {
    padding-top: max(env(safe-area-inset-top), 12px);
  }

  .header-toolbar {
    padding: 0 12px;
    min-height: 52px;
    padding-top: max(env(safe-area-inset-top), 6px);
  }

  /* Mobile Header Layout - Extra Small */
  .header-top-row {
    padding: 2px 8px;
    min-height: 40px;
  }

  .header-bottom-row {
    padding: 0 8px 4px;
  }

  .header-info {
    gap: 6px;
  }

  .time-display,
  .weather-display,
  .weather-loading,
  .weather-error {
    font-size: 10px;
  }

  .time-text,
  .weather-text {
    font-size: 10px;
  }

  /* Make weather even more compact */
  .weather-display {
    flex-direction: row;
    align-items: center;
    gap: 2px;
  }

  .weather-location {
    display: none;
  }

  .header-right {
    gap: 8px;
  }

  .search-container {
    max-width: 200px;
  }

  .time-pill,
  .weather-pill,
  .location-pill {
    font-size: 11px;
    padding: 3px 6px;
  }

  .greeting-section {
    padding: 12px;
  }

  .greeting-content {
    padding: 16px;
  }

  .greeting-text {
    font-size: 24px;
  }

  .greeting-subtitle {
    font-size: 14px;
  }

  .dashboard-content {
    padding: 12px;
  }

  .dashboard-cards-grid {
    gap: 12px;
    margin-bottom: 20px;
  }

  .card-content {
    padding: 16px;
  }

  .card-title {
    font-size: 1rem;
  }

  .card-value {
    font-size: 2rem;
  }

  .card-description {
    font-size: 0.8rem;
  }

  .queueing-section {
    padding: 0 12px 12px;
  }

  .queueing-header {
    padding: 16px;
  }

  .queueing-title {
    font-size: 1.2rem;
  }

  .action-btn {
    min-width: 180px;
    padding: 12px 16px;
  }

  .queue-panels-section {
    padding: 12px;
  }

  .queue-panel {
    padding: 12px;
    min-height: 120px;
  }

  .queue-panel-title {
    font-size: 1rem;
  }

  .notification-btn {
    padding: 8px;
  }

  .menu-toggle-btn {
    padding: 8px;
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

  .modal-card {
    min-width: unset;
    width: 100%;
    max-width: 100%;
    margin: 0;
    border-radius: 12px;
    max-height: calc(
      100vh - max(env(safe-area-inset-top), 20px) - max(env(safe-area-inset-bottom), 8px)
    );
    overflow-y: auto;
  }

  .modal-card .q-card-section {
    padding: 16px;
  }

  .modal-card .text-h6 {
    font-size: 1.25rem;
  }

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

  .modal-card {
    border-radius: 8px;
    max-height: calc(
      100vh - max(env(safe-area-inset-top), 24px) - max(env(safe-area-inset-bottom), 4px)
    );
  }

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

/* Queue Schedule Modal Styles */
.centered-dialog {
  display: flex;
  align-items: center;
  justify-content: center;
}

.dialog-card {
  min-width: 480px;
  max-width: 600px;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.12);
}

.dialog-header {
  border-bottom: 1px solid var(--q-separator-color);
  padding-bottom: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.dialog-body {
  padding: 24px 24px 16px 24px;
}

.form-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-field {
  width: 100%;
}

.toggle-container {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px 0;
  border-bottom: 1px solid var(--q-separator-color);
  margin-bottom: 16px;
}

.dialog-actions {
  padding: 16px 24px;
  border-top: 1px solid var(--q-separator-color);
  gap: 8px;
  justify-content: flex-end;
}

.save-btn {
  font-weight: 600;
  min-width: 140px;
}

/* Current Schedule Styles */
.current-schedule-container {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.schedule-info {
  flex: 1;
}

.schedule-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.schedule-title {
  font-weight: 600;
  color: #495057;
  font-size: 14px;
}

.schedule-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.schedule-row {
  display: flex;
  gap: 8px;
  font-size: 13px;
}

.schedule-label {
  font-weight: 500;
  color: #6c757d;
  min-width: 80px;
}

.schedule-value {
  color: #495057;
}

.schedule-actions {
  display: flex;
  align-items: center;
}

.queue-toggle-btn {
  font-weight: 600;
  min-width: 120px;
}

/* Responsive adjustments */
@media (max-width: 600px) {
  .current-schedule-container {
    flex-direction: column;
    align-items: stretch;
  }
  
  .schedule-actions {
    justify-content: center;
    margin-top: 12px;
  }
  
  .queue-toggle-btn {
    width: 100%;
  }
}
</style>
