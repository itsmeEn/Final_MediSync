<template>
  <q-layout view="hHh Lpr fFf">
    <DoctorHeader @toggle-drawer="toggleRightDrawer" />

    <DoctorSidebar v-model="rightDrawerOpen" active-route="appointments" />

    <q-page-container class="page-container-with-fixed-header safe-area-bottom role-body-bg">
      <!-- Greeting Section -->
      <div class="greeting-section">
        <q-card class="ms-card greeting-card">
          <q-card-section class="greeting-content">
            <h2 class="greeting-text">Appointment Calendar</h2>
            <p class="greeting-subtitle">Manage your appointments and schedule</p>

            <div class="appointments-toolbar">
              <q-input
                outlined
                dense
                v-model="text"
                aria-label="Search appointments"
                placeholder="Search patient, symptoms, or appointment"
                class="appointments-search"
              >
                <template v-slot:prepend>
                  <q-icon name="search" />
                </template>
                <template v-slot:append v-if="text">
                  <q-btn
                    flat
                    round
                    dense
                    icon="close"
                    aria-label="Clear search"
                    @click="text = ''"
                  />
                </template>
              </q-input>
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Dashboard Cards Section -->
      <div class="dashboard-cards-section">
        <div class="dashboard-cards-grid">


          <!-- Total Schedules Card -->
          <q-card class="dashboard-card schedule-card">
            <q-card-section class="card-content">
              <div class="card-text">
                <div class="card-title">Total Schedules</div>
                <div class="card-description">Scheduled appointments</div>
                <div class="card-value">
                  <q-spinner v-if="totalSchedulesLoading" size="md" />
                  <span v-else>{{ totalSchedules }}</span>
                </div>
              </div>
              <div class="card-icon">
                <q-icon name="event_available" size="2.5rem" />
              </div>
            </q-card-section>
          </q-card>

          <!-- Total Cancelled Appointments Card -->
          <q-card class="dashboard-card performance-card">
            <q-card-section class="card-content">
              <div class="card-text">
                <div class="card-title">Total Cancelled Appointments</div>
                <div class="card-description">All cancelled appointments</div>
                <div class="card-value">
                  <q-spinner v-if="monthlyCancelledLoading" size="md" />
                  <transition name="fade">
                    <span v-if="!monthlyCancelledLoading" :key="monthlyCancelled">
                      {{ monthlyCancelled }}
                    </span>
                  </transition>
                </div>
              </div>
              <div class="card-icon">
                <q-icon name="cancel" size="2.5rem" />
              </div>
            </q-card-section>
          </q-card>

          <!-- Total Rescheduled Appointments Card -->
          <q-card class="dashboard-card rescheduled-card">
            <q-card-section class="card-content">
              <div class="card-text">
                <div class="card-title">Total Rescheduled Appointments</div>
                <div class="card-description">All rescheduled appointments</div>
                <div class="card-value">
                  <q-spinner v-if="totalRescheduledLoading" size="md" />
                  <transition name="fade">
                    <span v-if="!totalRescheduledLoading" :key="totalRescheduled">
                      {{ totalRescheduled }}
                    </span>
                  </transition>
                </div>
              </div>
              <div class="card-icon">
                <q-icon name="event_repeat" size="2.5rem" />
              </div>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <div class="q-pa-md">
        <div class="calendar-panel" role="region" aria-label="Appointment calendar">
          <div class="calendar-panel-head">
            <div class="calendar-panel-head-left">
              <div class="calendar-checkbox" aria-hidden="true"></div>
              <div class="calendar-month">{{ currentMonthYear }}</div>
              <q-btn
                dense
                outline
                class="calendar-today-btn"
                label="Today"
                @click="goToToday"
                aria-label="Jump to today"
              />
            </div>
            <div class="calendar-panel-head-right">
              <q-btn dense flat round icon="chevron_left" class="calendar-nav-btn" @click="previousMonth" aria-label="Previous month" />
              <q-btn dense flat round icon="chevron_right" class="calendar-nav-btn" @click="nextMonth" aria-label="Next month" />
            </div>
          </div>

          <div class="calendar-panel-toolbar">
            <div class="calendar-view-tabs" role="tablist" aria-label="Calendar view">
              <q-btn-group unelevated class="calendar-view-group">
                <q-btn
                  dense
                  label="Day"
                  :class="{ 'is-active': currentView === 'day' }"
                  @click="setView('day')"
                  aria-label="Day view"
                />
                <q-btn
                  dense
                  label="Week"
                  :class="{ 'is-active': currentView === 'week' }"
                  @click="setView('week')"
                  aria-label="Week view"
                />
                <q-btn
                  dense
                  label="Month"
                  :class="{ 'is-active': currentView === 'month' }"
                  @click="setView('month')"
                  aria-label="Month view"
                />
              </q-btn-group>
            </div>

            <div class="calendar-panel-toolbar-right">
              <div class="calendar-mini-icons" aria-hidden="true">
                <span class="mini-icon"></span>
                <span class="mini-icon"></span>
                <span class="mini-icon"></span>
              </div>
            </div>
          </div>

        <!-- Calendar Grid -->
        <div class="calendar-grid" role="grid" aria-label="Monthly calendar">
          <!-- Day Headers -->
          <div class="calendar-row header-row" role="row">
            <div v-for="day in weekDays" :key="day" class="calendar-cell header-cell" role="columnheader">
              {{ day }}
            </div>
          </div>

          <!-- Calendar Days -->
          <div
            v-for="(week, weekIndex) in calendarWeeks"
            :key="`week-${weekIndex}`"
            class="calendar-row"
            role="row"
          >
            <div
              v-for="(day, dayIndex) in week"
              :key="`day-${weekIndex}-${dayIndex}`"
              class="calendar-cell"
              :class="{
                'other-month': !day?.isCurrentMonth,
                today: day?.isToday,
                selected: day?.isSelected,
                'has-appointments': day?.appointments?.length > 0,
                blocked: day?.isBlocked,
              }"
              @click="selectDate(day)"
              @keydown.enter.prevent="selectDate(day)"
              tabindex="0"
              role="gridcell"
              :aria-label="day?.date ? `${day.date.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}${day.appointments?.length ? `, ${day.appointments.length} appointments` : ''}` : 'Calendar day'"
            >
              <div class="calendar-cell-top">
                <div class="day-number">{{ day?.dayNumber }}</div>
                <span v-if="day?.appointments?.length > 0" class="event-dot" aria-hidden="true"></span>
                <span v-else-if="day?.isBlocked" class="blocked-dot" aria-hidden="true"></span>
              </div>
              <div v-if="day?.appointments?.length > 0" class="cell-appointments-list">
                <div
                  v-for="(appt, idx) in day.appointments.slice(0, 3)"
                  :key="`appt-${weekIndex}-${dayIndex}-${idx}`"
                  class="cell-appointment-pill"
                  :class="{ 'cell-appointment-completed': (appt?.status || '').toLowerCase() === 'completed' }"
                  role="note"
                  :aria-label="`Appointment: ${appt.patient_name || 'Patient'}`"
                >
                  <span class="cell-appt-name">{{ appt.patient_name || 'Patient' }}</span>
                </div>
                <div v-if="day.appointments.length > 3" class="cell-more-count">
                  +{{ day.appointments.length - 3 }} more
                </div>
              </div>
            </div>
          </div>
        </div>
        </div>
      </div>
    </q-page-container>

    <!-- Today's Schedule Dialog -->
    <q-dialog v-model="showTodayScheduleDialog">
      <q-card style="min-width: 480px; max-width: 720px;">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">Today's Schedule</div>
          <q-space />
          <q-btn icon="close" flat round dense @click="showTodayScheduleDialog = false" />
        </q-card-section>
        <q-separator />
        <q-card-section>
          <div v-if="scheduleLoading" class="row justify-center q-my-md">
            <q-spinner size="lg" />
          </div>
          <div v-else>
            <div v-if="!todaySchedule.length" class="text-grey-7">No appointments scheduled today.</div>
            <q-list v-else bordered separator>
              <q-item v-for="a in todaySchedule" :key="a.id">
                <q-item-section avatar>
                  <q-icon name="schedule" />
                </q-item-section>
                <q-item-section>
                  <q-item-label class="text-weight-medium">
                    {{ formatScheduleTime(a) }}
                  </q-item-label>
                  <q-item-label caption>
                    {{ a.patient_name || 'Patient Schedule' }}
                  </q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-badge outline color="primary">{{ a.status }}</q-badge>
                </q-item-section>
              </q-item>
            </q-list>
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Notifications Modal -->
    <q-dialog v-model="showNotifications" persistent>
      <q-card style="width: 400px; max-width: 90vw">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">Notifications</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
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
                :class="{ unread: !notification.is_read }"
              >
                <q-item-section avatar>
                  <q-icon name="info" color="primary" />
                </q-item-section>
                <q-item-section>
                  <q-item-label>{{ notification.message }}</q-item-label>
                  <q-item-label caption class="text-grey-5">{{
                    formatTime(notification.created_at)
                  }}</q-item-label>
                </q-item-section>
                <q-item-section side v-if="!notification.is_read">
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

    <!-- New Appointment Dialog -->
    <q-dialog v-model="showNewAppointmentDialog" persistent>
      <q-card style="min-width: 400px">
        <q-card-section class="row items-center">
          <div class="text-h6">New Appointment</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section>
          <q-form @submit="createAppointment" class="q-gutter-md">
            <q-input
              v-model="newAppointment.patient_name"
              label="Patient Name"
              outlined
              :rules="[(val) => !!val || 'Patient name is required']"
            />

            <q-input
              v-model="newAppointment.appointment_date"
              label="Date"
              outlined
              type="date"
              :rules="[(val) => !!val || 'Date is required']"
            />

            <q-input
              v-model="newAppointment.appointment_time"
              label="Time"
              outlined
              type="time"
              :rules="[(val) => !!val || 'Time is required']"
            />

            <q-select
              v-model="newAppointment.appointment_type"
              :options="appointmentTypes"
              label="Appointment Type"
              outlined
              :rules="[(val) => !!val || 'Appointment type is required']"
            />

            <q-input
              v-model="newAppointment.notes"
              label="Notes"
              outlined
              type="textarea"
              rows="3"
            />

            <div class="row q-gutter-sm justify-end">
              <q-btn label="Cancel" color="grey" v-close-popup />
              <q-btn label="Create Appointment" type="submit" color="primary" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>




  </q-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useQuasar } from 'quasar';
import { api } from 'src/boot/axios';
import DoctorHeader from '../components/DoctorHeader.vue';
import DoctorSidebar from '../components/DoctorSidebar.vue';

const $q = useQuasar();

// Drawer and navigation
const rightDrawerOpen = ref(false);
const text = ref('');
const showNotifications = ref(false);


// Monthly cancelled appointments count
const monthlyCancelled = ref(0);
// Per-card loading states
const monthlyCancelledLoading = ref(true);

// Total schedules / rescheduled counts
const totalSchedules = ref(0);
const totalSchedulesLoading = ref(true);
const totalRescheduled = ref(0);
const totalRescheduledLoading = ref(true);

const notificationsLoading = ref(true);
// Simple caches to avoid unnecessary state churn
const lastCountsCache = ref({
  monthlyCancelled: 0,
  notificationsUnread: 0,
});

// User profile
const userProfile = ref<{
  full_name: string;
  specialization?: string;
  role: string;
  profile_picture: string | null;
  verification_status: string;
}>({
  full_name: 'user',
  specialization: 'specialization',
  role: 'role',
  profile_picture: null,
  verification_status: 'not_submitted',
});

// Computed properties for user profile

// Time and date functions removed - not used in appointment page

// Profile picture URL computed property removed - not used in new design

// Types
interface DayData {
  date: Date;
  dayNumber: number;
  isCurrentMonth: boolean;
  isToday: boolean;
  isSelected: boolean;
  isBlocked: boolean;
  appointments: Appointment[];
}

interface Appointment {
  id: number;
  patient_name: string;
  appointment_date: string;
  appointment_time: string;
  appointment_type: string;
  status: string;
  notes?: string;
  medical_assessment?: {
    blood_pressure: string;
    heart_rate: number;
    temperature: number;
    weight: number;
    symptoms: string;
    nurse_notes: string;
    assessment_date: string;
  };
}

// Normalize and dedupe helpers to fix missing names and duplicates
interface RawAppointment {
  id?: number;
  appointment_id?: number;
  appointmentId?: number;
  patient_name?: string;
  patient?: { name?: string };
  patientName?: string;
  appointment_date?: string;
  date?: string;
  appointment_time?: string;
  time?: string;
  appointment_type?: string;
  type?: string;
  status?: string;
  notes?: string;
}
function normalizeAppointment(raw: RawAppointment): Appointment {
  return {
    id: Number(raw?.id ?? raw?.appointment_id ?? raw?.appointmentId ?? -1),
    patient_name: String(raw?.patient_name ?? raw?.patient?.name ?? raw?.patientName ?? ''),
    appointment_date: String(raw?.appointment_date ?? raw?.date ?? ''),
    appointment_time: String(raw?.appointment_time ?? raw?.time ?? ''),
    appointment_type: String(raw?.appointment_type ?? raw?.type ?? ''),
    status: String(raw?.status ?? 'scheduled'),
    notes: String(raw?.notes ?? ''),
  };
}

function dedupeAppointments(list: Appointment[]): Appointment[] {
  const byId = new Map<number, Appointment>();
  const bySig = new Set<string>();
  const out: Appointment[] = [];
  for (const a of list) {
    const sig = `${a.appointment_date}|${a.appointment_time}|${a.patient_name}|${a.appointment_type}|${a.status}`;
    if (a.id && a.id !== -1) {
      if (!byId.has(a.id)) {
        byId.set(a.id, a);
        out.push(a);
      }
    } else {
      if (!bySig.has(sig)) {
        bySig.add(sig);
        out.push(a);
      }
    }
  }
  return out;
}

// Reactive data
const currentDate = ref(new Date());
const selectedDate = ref<DayData | null>(null);
const showNewAppointmentDialog = ref(false);
const appointments = ref<Appointment[]>([]);
const blockedDates = ref<string[]>([]);
const currentView = ref<'day' | 'week' | 'month'>('month');

// Notification system
const notifications = ref<
  {
    id: number;
    message: string;
    is_read: boolean;
    created_at: string;
  }[]
>([]);

// Notification interface
interface Notification {
  id: number;
  message: string;
  is_read: boolean;
  created_at: string;
}

// New appointment form
const newAppointment = ref({
  patient_name: '',
  appointment_date: '',
  appointment_time: '',
  appointment_type: '',
  notes: '',
});

const appointmentTypes = ['consultation', 'follow_up', 'emergency'];

// Computed properties
const currentMonthYear = computed(() => {
  return currentDate.value.toLocaleDateString('en-US', {
    month: 'long',
    year: 'numeric',
  });
});

const weekDays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

const calendarWeeks = computed(() => {
  const year = currentDate.value.getFullYear();
  const month = currentDate.value.getMonth();

  const firstDay = new Date(year, month, 1);
  const startDate = new Date(firstDay);
  startDate.setDate(startDate.getDate() - firstDay.getDay());

  const weeks: DayData[][] = [];
  let currentWeek: DayData[] = [];

  for (let i = 0; i < 42; i++) {
    const date = new Date(startDate);
    date.setDate(startDate.getDate() + i);

    const dayData: DayData = {
      date: date,
      dayNumber: date.getDate(),
      isCurrentMonth: date.getMonth() === month,
      isToday: isToday(date),
      isSelected: selectedDate.value ? isSameDate(date, selectedDate.value.date) : false,
      isBlocked: isDateBlocked(date),
      appointments: getAppointmentsForDate(date),
    };

    currentWeek.push(dayData);

    if (currentWeek.length === 7) {
      weeks.push(currentWeek);
      currentWeek = [];
    }
  }

  return weeks;
});

// Generic time formatter for HH:MM strings or ISO date-times
function formatTime(value?: string): string {
  if (!value) return 'N/A';
  try {
    if (/\d{4}-\d{2}-\d{2}T/.test(value) || /Z$/.test(value)) {
      return new Date(value).toLocaleTimeString('en-US', {
        hour12: true,
        hour: 'numeric',
        minute: '2-digit',
      });
    }
    const [hours = '0', minutes = '00'] = value.split(':');
    let hourNum = parseInt(hours, 10);
    const ampm = hourNum >= 12 ? 'PM' : 'AM';
    hourNum = hourNum % 12 || 12;
    return `${hourNum}:${minutes.padStart(2, '0')} ${ampm}`;
  } catch {
    return value;
  }
}

// Today's Schedule state and helpers
const scheduleLoading = ref(false)
const todaySchedule = ref<Appointment[]>([])
const showTodayScheduleDialog = ref(false)

function isSameDay(dateStr: string, target: Date) {
  const d = new Date(dateStr)
  return (
    d.getFullYear() === target.getFullYear() &&
    d.getMonth() === target.getMonth() &&
    d.getDate() === target.getDate()
  )
}

function formatScheduleTime(appt: Appointment) {
  const raw = appt.appointment_time || appt.appointment_date
  return formatTime(raw)
}

function getScheduleTime(appt: Appointment): number {
  try {
    if (appt.appointment_time) {
      const [hStr = '0', mStr = '0'] = appt.appointment_time.split(':')
      const h = parseInt(hStr, 10)
      const m = parseInt(mStr, 10)
      const d = new Date()
      d.setHours(h, m, 0, 0)
      return d.getTime()
    }
    return new Date(appt.appointment_date).getTime()
  } catch {
    return 0
  }
}

async function fetchTodaySchedule() {
  try {
    scheduleLoading.value = true;
    const res = await api.get('/operations/appointments/');
    const raw = Array.isArray(res.data) ? res.data : (res.data?.results ?? []);
    const mapped = (raw as RawAppointment[]).map(normalizeAppointment);
    const deduped = dedupeAppointments(mapped);
    const today = new Date();
    const items = deduped.filter((a) => a.appointment_date && isSameDay(a.appointment_date, today));
    items.sort((a, b) => getScheduleTime(a) - getScheduleTime(b));
    todaySchedule.value = items;
  } catch (err) {
    console.error('Failed to fetch today schedule', err);
    todaySchedule.value = [];
  } finally {
    scheduleLoading.value = false;
  }
}

// Refresh at midnight to keep schedule current
const setupDailyScheduleRefresh = (): void => {
  const now = new Date()
  const tomorrow = new Date(now)
  tomorrow.setDate(tomorrow.getDate() + 1)
  tomorrow.setHours(0, 0, 0, 0)
  const msUntilMidnight = tomorrow.getTime() - now.getTime()
  setTimeout(() => {
    void fetchTodaySchedule()
    setInterval(() => void fetchTodaySchedule(), 24 * 60 * 60 * 1000)
  }, msUntilMidnight)
}

// Navigation functions
const toggleRightDrawer = () => {
  rightDrawerOpen.value = !rightDrawerOpen.value;
};

// Profile picture functions removed - not used in new design

// Fetch user profile from API
const fetchUserProfile = async () => {
  try {
    const response = await api.get('/users/profile/');
    const userData = response.data.user; // The API returns nested user data

    userProfile.value = {
      full_name: userData.full_name,
      specialization: userData.doctor_profile?.specialization,
      role: userData.role,
      profile_picture: userData.profile_picture || null,
      verification_status: userData.verification_status || 'not_submitted',
    };

    console.log('User profile loaded:', userProfile.value);
  } catch (error) {
    console.error('Failed to fetch user profile:', error);

    // Fallback to localStorage
    const userData = localStorage.getItem('user');
    if (userData) {
      const user = JSON.parse(userData);
      userProfile.value = {
        full_name: user.full_name,
        specialization: user.doctor_profile?.specialization,
        role: user.role,
        profile_picture: user.profile_picture || null,
        verification_status: user.verification_status || 'not_submitted',
      };
    }
  }
};

// Methods
function isToday(date: Date): boolean {
  const today = new Date();
  return date.toDateString() === today.toDateString();
}

function isSameDate(date1: Date, date2: Date): boolean {
  return date1.toDateString() === date2.toDateString();
}

function isDateBlocked(date: Date): boolean {
  return blockedDates.value.some((blockedDate) => isSameDate(new Date(blockedDate), date));
}

function getAppointmentsForDate(date: Date) {
  return appointments.value.filter((appointment) =>
    isSameDate(new Date(appointment.appointment_date), date),
  );
}

function selectDate(day: DayData | undefined) {
  if (day && day.isCurrentMonth) {
    selectedDate.value = day;
  }
}

function previousMonth() {
  currentDate.value = new Date(
    currentDate.value.getFullYear(),
    currentDate.value.getMonth() - 1,
    1,
  );
}

function nextMonth() {
  currentDate.value = new Date(
    currentDate.value.getFullYear(),
    currentDate.value.getMonth() + 1,
    1,
  );
}

function goToToday() {
  currentDate.value = new Date();
  const today = calendarWeeks.value.flat().find((day) => day.isToday);
  if (today) {
    selectedDate.value = today;
  }
}

async function fetchAppointments() {
  try {
    const response = await api.get('/operations/appointments/');
    const raw = Array.isArray(response.data) ? response.data : (response.data?.results ?? []);
    const mapped = (raw as RawAppointment[]).map(normalizeAppointment);
    appointments.value = dedupeAppointments(mapped);
  } catch (error) {
    console.error('Failed to fetch appointments:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to load appointments',
      position: 'top',
    });
  }
}

async function fetchBlockedDates() {
  try {
    // This would be a new endpoint for blocked dates
    const response = await api.get('/operations/blocked-dates/');
    blockedDates.value = response.data;
  } catch (error) {
    console.error('Failed to fetch blocked dates:', error);
  }
}

async function createAppointment() {
  try {
    const appointmentData = {
      ...newAppointment.value,
      appointment_date:
        newAppointment.value.appointment_date + 'T' + newAppointment.value.appointment_time,
    };

    await api.post('/operations/create-appointment/', appointmentData);

    // Reset form
    newAppointment.value = {
      patient_name: '',
      appointment_date: '',
      appointment_time: '',
      appointment_type: '',
      notes: '',
    };

    showNewAppointmentDialog.value = false;

    // Refresh appointments
    await fetchAppointments();
    void fetchTotalSchedules();
    void fetchMonthlyCancelled();
    void fetchTotalRescheduled();

    $q.notify({
      type: 'positive',
      message: 'Appointment created successfully',
      position: 'top',
    });
  } catch (error) {
    console.error('Failed to create appointment:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to create appointment',
      position: 'top',
    });
  }
}

// View management function
function setView(view: 'day' | 'week' | 'month') {
  currentView.value = view;
  console.log('Switched to view:', view);
}

// Lifecycle
// Notification functions
const loadNotifications = async (opts: { silent?: boolean } = {}): Promise<void> => {
  try {
    if (!opts.silent) notificationsLoading.value = true;
    console.log('Loading doctor notifications...');

    const response = await api.get('/operations/notifications/');
    const list = response.data || [];
    const unread = list.filter((n: Notification) => !n.is_read).length;
    // Only update if count or payload changed
    if (unread !== lastCountsCache.value.notificationsUnread || list.length !== notifications.value.length) {
      notifications.value = list;
      lastCountsCache.value.notificationsUnread = unread;
    }

    console.log('Doctor notifications loaded:', notifications.value.length);
  } catch (error: unknown) {
    console.error('Error loading doctor notifications:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to load notifications',
    });
  } finally {
    if (!opts.silent) notificationsLoading.value = false;
  }
};

const handleNotificationClick = (notification: Notification): void => {
  // Mark as read
  notification.is_read = true;

  // Update on backend
  void markNotificationAsRead(notification.id);
};

const markNotificationAsRead = async (notificationId: number): Promise<void> => {
  try {
    await api.patch(`/operations/notifications/${notificationId}/mark-read/`);
  } catch (error) {
    console.error('Error marking notification as read:', error);
  }
};

const markAllNotificationsRead = async (): Promise<void> => {
  try {
    // Mark all notifications as read locally
    notifications.value.forEach((notification) => {
      notification.is_read = true;
    });

    // Mark all notifications as read on backend
    await api.post('/operations/notifications/mark-all-read/');

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



// WebSocket handle for doctor messaging; kept at module scope for proper cleanup
let doctorMessagingWS: WebSocket | null = null;

function extractCount(data: unknown): number {
  const anyData = data as { count?: unknown; results?: unknown[] } | unknown[] | null | undefined;
  if (anyData && typeof anyData === 'object' && !Array.isArray(anyData)) {
    const c = (anyData as { count?: unknown }).count;
    if (typeof c === 'number') return c;
    const results = (anyData as { results?: unknown[] }).results;
    if (Array.isArray(results)) return results.length;
    return 0;
  }
  if (Array.isArray(anyData)) return anyData.length;
  return 0;
}

async function fetchAppointmentCount(params: Record<string, unknown>): Promise<number> {
  const res = await api.get('/operations/appointments/', { params });
  return extractCount(res.data);
}

const fetchTotalSchedules = async (): Promise<void> => {
  try {
    totalSchedulesLoading.value = true;
    totalSchedules.value = await fetchAppointmentCount({ status: 'scheduled' }).catch(() => 0);
  } catch (err) {
    console.error('Failed to fetch total schedules count', err);
    totalSchedules.value = 0;
  } finally {
    totalSchedulesLoading.value = false;
  }
};

const fetchTotalRescheduled = async (): Promise<void> => {
  try {
    totalRescheduledLoading.value = true;
    totalRescheduled.value = await fetchAppointmentCount({ status: 'rescheduled' }).catch(() => 0);
  } catch (err) {
    console.error('Failed to fetch total rescheduled count', err);
    totalRescheduled.value = 0;
  } finally {
    totalRescheduledLoading.value = false;
  }
};

// Fetch total cancelled appointments for current doctor
const fetchMonthlyCancelled = async (): Promise<void> => {
  try {
    monthlyCancelledLoading.value = true;
    const resolved = await fetchAppointmentCount({ status: 'cancelled' }).catch(() => 0);
    if (resolved !== lastCountsCache.value.monthlyCancelled) {
      monthlyCancelled.value = resolved;
      lastCountsCache.value.monthlyCancelled = resolved;
    }
  } catch (err) {
    console.error('Failed to fetch monthly cancelled count', err);
    monthlyCancelled.value = 0;
  } finally {
    monthlyCancelledLoading.value = false;
  }
};

onMounted(async () => {
  console.log('DoctorAppointment component mounted successfully!');

  // Load user profile data from API
  void fetchUserProfile();

  // Load notifications
  void loadNotifications();

  try {
    await fetchAppointments();
    await fetchBlockedDates();
    goToToday();
  } catch (error) {
    console.error('Error during component initialization:', error);
  }

  // Fetch dashboard counts (initial only)
  void fetchTotalSchedules();
  void fetchMonthlyCancelled();
  void fetchTotalRescheduled();

  // Fetch today's full schedule and set daily refresh
  void fetchTodaySchedule();
  setupDailyScheduleRefresh();

  // Setup messaging WebSocket for real-time appointment updates
  try {
    // Local setup without using window any-casts

    const base = new URL(api.defaults.baseURL || `http://${window.location.hostname}:8000`);
    const protocol = base.protocol === 'https:' ? 'wss:' : 'ws:';
    const backendHost = base.hostname;
    const backendPort = base.port || (base.protocol === 'https:' ? '443' : '80');
    const storedUser = JSON.parse(localStorage.getItem('user') || '{}');
    const userId = storedUser.id || storedUser.user?.id || storedUser.user_id;
    const handleDoctorWSMessage = async (event: MessageEvent): Promise<void> => {
      try {
        const data = JSON.parse(event.data as string);
        if (data.type === 'notification') {
          const notif = data.notification || {};
          if (notif.event === 'appointment_scheduled') {
            $q.notify({
              type: 'info',
              message: 'New appointment scheduled',
              position: 'top'
            });
          }
          // Refresh appointments and notifications only when new data arrives
          await fetchAppointments();
          void loadNotifications({ silent: true });
        }
      } catch (err) {
        console.warn('Failed to parse WS message', err);
      }
    };

    const setupDoctorMessagingWS = (wsUrl: string): void => {
      const ws = new WebSocket(wsUrl);
      doctorMessagingWS = ws;
      ws.onopen = () => {
        console.log('Doctor messaging WebSocket connected');
      };
      ws.onmessage = handleDoctorWSMessage;
      ws.onclose = () => {
        console.log('Doctor messaging WebSocket disconnected');
        // Attempt to reconnect after 5 seconds
        setTimeout(() => setupDoctorMessagingWS(wsUrl), 5000);
      };
    };

    if (userId) {
      const wsUrl = `${protocol}//${backendHost}:${backendPort}/ws/messaging/${userId}/`;
      setupDoctorMessagingWS(wsUrl);
    } else {
      console.warn('No user id found for messaging WebSocket');
    }
  } catch (e) {
    console.warn('Failed to setup doctor messaging WebSocket', e);
  }
});

// Cleanup on component unmount
onUnmounted(() => {
  // Close the WebSocket if open; avoid empty catch and any-casts
  try {
    if (doctorMessagingWS) {
      doctorMessagingWS.close();
    }
  } catch (err) {
    console.warn('Error closing doctor messaging WebSocket', err);
  } finally {
    doctorMessagingWS = null;
  }
});
</script>

<style scoped>
.page-background {
  background: #b5b7b9;
  background-size: cover;
  min-height: 100vh;
}

/* Smooth value transitions for dashboard counts */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Header and Navigation Styles */

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

/* Page Header Styles */
.page-header {
  padding: 30px 20px 20px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin: 0 auto 20px;
}

.page-header-left {
  flex: 1;
}

.page-header-right {
  display: flex;
  gap: 10px;
  align-items: center;
}

.page-title {
  color: #333;
  font-size: 28px;
  font-weight: 600;
  margin: 0 0 8px 0;
}

.page-subtitle {
  color: #666;
  font-size: 16px;
  margin: 0;
  font-weight: 400;
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

.profile-avatar img {
  border-radius: 50% !important;
  width: 100% !important;
  height: 100% !important;
  object-fit: cover !important;
}

.profile-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #1e7668;
  color: white;
  font-size: 24px;
  font-weight: bold;
  border-radius: 50%;
}

.upload-btn {
  position: absolute;
  bottom: -5px;
  right: -5px;
  background: #1e7668 !important;
  border-radius: 50% !important;
  width: 24px !important;
  height: 24px !important;
  min-height: 24px !important;
  padding: 0 !important;
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
  margin: 5px 10px;
  border-radius: 8px;
  transition: background-color 0.3s;
}

.nav-item:hover {
  background: rgba(30, 118, 104, 0.1);
}

.nav-item.active {
  background: rgba(30, 118, 104, 0.2);
  color: #1e7668;
}

.nav-item .q-icon {
  color: #1e7668;
}

.logout-section {
  padding: 20px;
  border-top: 1px solid #e0e0e0;
}

.logout-btn {
  width: 100%;
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

/* Calendar Navigation Bar Styles */
.calendar-navigation-bar {
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(25px);
  border-radius: 20px;
  padding: 24px;
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
  margin-bottom: 24px;
  border: 1px solid rgba(255, 255, 255, 0.25);
  margin: 0 auto 24px;
}

.month-navigation {
  display: flex;
  align-items: center;
  gap: 16px;
}

.nav-btn {
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(10px);
  color: #374151;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  width: 44px;
  height: 44px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.nav-btn:hover {
  background: rgba(40, 102, 96, 0.2);
  border: 1px solid rgba(40, 102, 96, 0.4);
  color: #1a4e47;
  transform: scale(1.1);
  box-shadow: 0 4px 16px rgba(40, 102, 96, 0.3);
}

.month-year {
  font-size: 24px;
  font-weight: 700;
  background: linear-gradient(135deg, #286660 0%, #1a4e47 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0;
  min-width: 200px;
  text-align: center;
  text-shadow: 0 2px 4px rgba(40, 102, 96, 0.2);
}

.today-btn {
  background: linear-gradient(135deg, 
    rgba(59, 130, 246, 0.2) 0%, 
    rgba(37, 99, 235, 0.15) 100%);
  backdrop-filter: blur(10px);
  color: #1e40af;
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 12px;
  padding: 12px 20px;
  font-weight: 600;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.2);
}

.today-btn:hover {
  background: linear-gradient(135deg, 
    rgba(59, 130, 246, 0.3) 0%, 
    rgba(37, 99, 235, 0.25) 100%);
  border: 1px solid rgba(59, 130, 246, 0.5);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(59, 130, 246, 0.4);
}

.view-export-controls {
  display: flex;
  align-items: center;
  gap: 20px;
}

.view-selector {
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.view-selector .q-btn {
  border-radius: 0;
  color: #286660;
  font-weight: 500;
  padding: 10px 18px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  background: transparent;
}

.view-selector .q-btn:hover {
  background: rgba(40, 102, 96, 0.1);
  color: #1a4e47;
}

.view-selector .q-btn.active-view {
  background: linear-gradient(135deg, 
    rgba(40, 102, 96, 0.2) 0%, 
    rgba(26, 78, 71, 0.15) 100%);
  color: #1a4e47;
  font-weight: 600;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.3);
}

.export-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.export-btn {
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
  color: #374151;
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 50%;
  width: 40px;
  height: 40px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.export-btn:hover {
  background: rgba(34, 197, 94, 0.2);
  border: 1px solid rgba(34, 197, 94, 0.4);
  color: #15803d;
  transform: scale(1.1);
  box-shadow: 0 4px 16px rgba(34, 197, 94, 0.3);
}

.export-controls {
  display: flex;
  gap: 8px;
}

.export-btn {
  color: #666;
  border: 1px solid #e0e0e0;
  border-radius: 50%;
  width: 36px;
  height: 36px;
}

.export-btn:hover {
  background: #f5f5f5;
  color: #333;
}

/* Medical Assessment Dialog Styles */
.assessment-content {
  max-width: 800px;
}

.assessment-section {
  margin-bottom: 24px;
}

.assessment-section h5 {
  color: #333;
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 12px 0;
  border-bottom: 2px solid #286660;
  padding-bottom: 8px;
}

.vital-signs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.vital-sign {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 6px;
}

.vital-sign .label {
  font-weight: 500;
  color: #666;
}

.vital-sign .value {
  font-weight: 600;
  color: #333;
}

.no-assessment {
  text-align: center;
  padding: 40px;
  color: #666;
}

.no-assessment h4 {
  margin: 16px 0 8px 0;
  color: #333;
}

.no-assessment p {
  margin: 0;
}

/* Calendar Styles */
.calendar-header {
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 24px;
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.25);
  margin-bottom: 20px;
}

.calendar-grid {
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(25px);
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 
    0 12px 40px rgba(0, 0, 0, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
  margin: 0 auto;
  border: 1px solid rgba(255, 255, 255, 0.25);
}

.calendar-row {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
}

.calendar-cell {
  min-height: 90px;
  padding: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  cursor: pointer;
  position: relative;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  background: rgba(255, 255, 255, 0.05);
}

.calendar-cell:hover {
  background: rgba(255, 255, 255, 0.15);
  transform: scale(1.02);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.calendar-cell.header-cell {
  background: linear-gradient(135deg, 
    rgba(40, 102, 96, 0.1) 0%, 
    rgba(26, 78, 71, 0.1) 100%);
  font-weight: 700;
  text-align: center;
  min-height: 50px;
  cursor: default;
  color: #286660;
  font-size: 14px;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.calendar-cell.header-cell:hover {
  background: linear-gradient(135deg, 
    rgba(40, 102, 96, 0.1) 0%, 
    rgba(26, 78, 71, 0.1) 100%);
  transform: none;
  box-shadow: none;
}

.calendar-cell.other-month {
  background: rgba(255, 255, 255, 0.02);
  color: rgba(156, 163, 175, 0.6);
  opacity: 0.5;
}

.calendar-cell.today {
  background: linear-gradient(135deg, 
    rgba(40, 102, 96, 0.2) 0%, 
    rgba(26, 78, 71, 0.15) 100%);
  border: 2px solid rgba(40, 102, 96, 0.6);
  color: #1a4e47;
  font-weight: 700;
  box-shadow: 
    0 4px 20px rgba(40, 102, 96, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.4);
}

.calendar-cell.today:hover {
  background: linear-gradient(135deg, 
    rgba(40, 102, 96, 0.3) 0%, 
    rgba(26, 78, 71, 0.25) 100%);
  border: 2px solid rgba(40, 102, 96, 0.8);
}

.calendar-cell.selected {
  background: linear-gradient(135deg, 
    rgba(52, 168, 83, 0.25) 0%, 
    rgba(34, 139, 34, 0.2) 100%);
  color: white;
  border: 2px solid rgba(52, 168, 83, 0.6);
  box-shadow: 
    0 6px 25px rgba(52, 168, 83, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
}

.calendar-cell.has-appointments {
  background: linear-gradient(135deg, 
    rgba(52, 168, 83, 0.15) 0%, 
    rgba(34, 139, 34, 0.1) 100%);
  border: 1px solid rgba(52, 168, 83, 0.3);
}

.calendar-cell.has-appointments:hover {
  background: linear-gradient(135deg, 
    rgba(52, 168, 83, 0.25) 0%, 
    rgba(34, 139, 34, 0.2) 100%);
  border: 1px solid rgba(52, 168, 83, 0.5);
}

.calendar-cell.blocked {
  background: linear-gradient(135deg, 
    rgba(255, 152, 0, 0.15) 0%, 
    rgba(255, 183, 77, 0.1) 100%);
  color: #e65100;
  border: 1px solid rgba(255, 152, 0, 0.3);
}

.calendar-cell.blocked:hover {
  background: linear-gradient(135deg, 
    rgba(255, 152, 0, 0.25) 0%, 
    rgba(255, 183, 77, 0.2) 100%);
  border: 1px solid rgba(255, 152, 0, 0.5);
}

.day-number {
  font-weight: 500;
  margin-bottom: 4px;
}

.appointment-indicator {
  position: absolute;
  top: 4px;
  right: 4px;
}

.blocked-indicator {
  position: absolute;
  bottom: 4px;
  right: 4px;
}

/* Calendar cell appointment preview */
.cell-appointments-list {
  margin-top: 18px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.cell-appointment-row {
  font-size: 12px;
  line-height: 1.2;
  color: #333;
  display: flex;
  gap: 6px;
  align-items: center;
}

.cell-appointment-completed {
  text-decoration: line-through;
  opacity: 0.65;
}

.cell-appt-time {
  color: #286660;
  font-weight: 600;
}

.cell-appt-name {
  color: #555;
}

.cell-more-count {
  font-size: 11px;
  color: #888;
}

.selected-date-info {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.appointments-list {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.appointment-item {
  border-radius: 4px;
}

/* Safe Area Support */
.safe-area-top {
  padding-top: env(safe-area-inset-top);
}

.safe-area-bottom {
  padding-bottom: env(safe-area-inset-bottom);
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

/* Prototype Sidebar Styles */
.prototype-sidebar {
  background: white;
  border-right: 1px solid #e0e0e0;
}

.sidebar-content {
  height: 100%;
  display: flex;
  flex-direction: column;
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

.logout-section {
  padding: 20px;
  border-top: 1px solid #e0e0e0;
}

.logout-btn {
  width: 100%;
  border-radius: 8px;
  font-weight: 600;
  text-transform: uppercase;
}

/* Page Container with Off-White Background */
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
  background: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(20px);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  overflow: hidden;
  position: relative;
  margin: 0 auto;
  min-height: 120px;
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
}

.greeting-content {
  padding: 24px;
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

/* Dashboard Cards Section */
.dashboard-cards-section {
  padding: 0 24px 24px;
  background: transparent;
}

.dashboard-cards-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 26px;
  margin: 0 auto;
}

.dashboard-card {
  background: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(20px);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  cursor: pointer;
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
  background: linear-gradient(90deg, #286660, #6ca299, #b8d2ce);
  border-radius: 16px 16px 0 0;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.dashboard-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.15);
  background: rgba(255, 255, 255, 0.35);
}

.dashboard-card:hover::before {
  opacity: 1;
}

/* Doctor-Centric Medical Color Schemes */
.medical-records-card::before {
  background: linear-gradient(90deg, #286660, #3d8b7c, #52a899);
}

.schedule-card::before {
  background: linear-gradient(90deg, #34a853, #48bb78, #68cc8a);
}

.performance-card::before {
  background: linear-gradient(90deg, #f44336, #e57373, #ffcdd2);
}

.notifications-card::before {
  background: linear-gradient(90deg, #ff9800, #ffb74d, #ffcc80);
}

/* Enhanced Card Styling with Medical Theme */
.dashboard-card {
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(25px);
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.25);
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.4);
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  position: relative;
  cursor: pointer;
}

.dashboard-card:hover {
  transform: translateY(-8px) scale(1.02);
  box-shadow: 
    0 20px 60px rgba(0, 0, 0, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.4);
  background: rgba(255, 255, 255, 0.25);
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

.card-description {
  font-size: 14px;
  color: #666;
  line-height: 1.4;
  margin-bottom: 8px;
}

.card-value {
  font-size: 32px;
  font-weight: 700;
  color: #286660;
  line-height: 1;
  margin-top: 8px;
}

/* Card-specific value colors */
.medical-records-card .card-value {
  color: #286660;
  text-shadow: 0 2px 4px rgba(40, 102, 96, 0.3);
}

.schedule-card .card-value {
  color: #34a853;
  text-shadow: 0 2px 4px rgba(52, 168, 83, 0.3);
}

.performance-card .card-value {
  color: #f44336;
  text-shadow: 0 2px 4px rgba(244, 67, 54, 0.3);
}

.notifications-card .card-value {
  color: #ff9800;
  text-shadow: 0 2px 4px rgba(255, 152, 0, 0.3);
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

/* Medical-Themed Card Icon Colors */
.medical-records-card .card-icon {
  color: #286660;
  filter: drop-shadow(0 2px 4px rgba(40, 102, 96, 0.4));
}

.schedule-card .card-icon {
  color: #34a853;
  filter: drop-shadow(0 2px 4px rgba(52, 168, 83, 0.4));
}

.performance-card .card-icon {
  color: #f44336;
  filter: drop-shadow(0 2px 4px rgba(244, 67, 54, 0.4));
}

.notifications-card .card-icon {
  color: #ff9800;
  filter: drop-shadow(0 2px 4px rgba(255, 152, 0, 0.4));
}

/* Enhanced Card Backgrounds with Medical Theme */
.medical-records-card {
  background: linear-gradient(135deg, 
    rgba(40, 102, 96, 0.15) 0%, 
    rgba(61, 139, 124, 0.1) 25%,
    rgba(255, 255, 255, 0.2) 100%);
  border: 1px solid rgba(40, 102, 96, 0.3);
}

.medical-records-card:hover {
  background: linear-gradient(135deg, 
    rgba(40, 102, 96, 0.25) 0%, 
    rgba(61, 139, 124, 0.2) 25%,
    rgba(255, 255, 255, 0.3) 100%);
  border: 1px solid rgba(40, 102, 96, 0.5);
}

.schedule-card {
  background: linear-gradient(135deg, 
    rgba(52, 168, 83, 0.15) 0%, 
    rgba(72, 187, 120, 0.1) 25%,
    rgba(255, 255, 255, 0.2) 100%);
  border: 1px solid rgba(52, 168, 83, 0.3);
}

.schedule-card:hover {
  background: linear-gradient(135deg, 
    rgba(52, 168, 83, 0.25) 0%, 
    rgba(72, 187, 120, 0.2) 25%,
    rgba(255, 255, 255, 0.3) 100%);
  border: 1px solid rgba(52, 168, 83, 0.5);
}

/* Today’s Schedule preview styles */
.schedule-preview {
  margin-top: 8px;
}
.preview-row {
  display: flex;
  gap: 8px;
  font-size: 13px;
  line-height: 20px;
}
.preview-time {
  color: #2e7d32;
  font-weight: 600;
}
.preview-name {
  color: #1f2937;
}
.preview-more {
  margin-top: 2px;
  font-size: 12px;
  color: #374151;
}

.performance-card {
  background: linear-gradient(135deg, 
    rgba(244, 67, 54, 0.15) 0%, 
    rgba(229, 115, 115, 0.1) 25%,
    rgba(255, 255, 255, 0.2) 100%);
  border: 1px solid rgba(244, 67, 54, 0.3);
}

.performance-card:hover {
  background: linear-gradient(135deg, 
    rgba(244, 67, 54, 0.25) 0%, 
    rgba(229, 115, 115, 0.2) 25%,
    rgba(255, 255, 255, 0.3) 100%);
  border: 1px solid rgba(244, 67, 54, 0.5);
}

.notifications-card {
  background: linear-gradient(135deg, 
    rgba(255, 152, 0, 0.15) 0%, 
    rgba(255, 183, 77, 0.1) 25%,
    rgba(255, 255, 255, 0.2) 100%);
  border: 1px solid rgba(255, 152, 0, 0.3);
}

.notifications-card:hover {
  background: linear-gradient(135deg, 
    rgba(255, 152, 0, 0.25) 0%, 
    rgba(255, 183, 77, 0.2) 25%,
    rgba(255, 255, 255, 0.3) 100%);
  border: 1px solid rgba(255, 152, 0, 0.5);
}

/* Notification styles */
.unread {
  background-color: rgba(25, 118, 210, 0.05);
  border-left: 3px solid #1976d2;
}

.unread .q-item-label {
  font-weight: 600;
}

/* Desktop Layout - Show desktop header, hide mobile */
@media (min-width: 769px) {
  .mobile-header-layout {
    display: none;
  }

  .prototype-header .header-toolbar {
    display: flex;
  }
}

/* Mobile Layout - Hide desktop header, show mobile */
@media (max-width: 768px) {
  .prototype-header {
    padding-top: max(env(safe-area-inset-top), 8px);
  }

  .header-toolbar {
    display: none;
  }

  .mobile-header-layout {
    padding: 8px 12px;
    padding-top: max(env(safe-area-inset-top), 8px);
  }

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
}

/* Mobile Portrait - Single Column */
@media (max-width: 480px) {
  .dashboard-cards-section {
    padding: 0 12px 12px;
  }

  .dashboard-cards-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .card-content {
    padding: 16px;
    min-height: 180px;
  }

  .card-title {
    font-size: 14px;
  }

  .card-description {
    font-size: 11px;
  }

  .card-value {
    font-size: 24px;
  }

  .card-icon .q-icon {
    font-size: 1.8rem !important;
  }
}

/* Tablet Responsive */
@media (min-width: 481px) and (max-width: 1024px) {
  .dashboard-cards-section {
    padding: 0 20px 20px;
  }

  .dashboard-cards-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
  }

  .card-content {
    padding: 22px;
    min-height: 220px;
  }

  .card-title {
    font-size: 15px;
  }

  .card-description {
    font-size: 12px;
  }

  .card-value {
    font-size: 30px;
  }
}

@media (max-width: 480px) {
  .prototype-header {
    padding-top: max(env(safe-area-inset-top), 12px);
  }

  .mobile-header-layout {
    padding: 6px 8px;
    padding-top: max(env(safe-area-inset-top), 12px);
  }

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
}

/* Dashboard Cards Responsive Styles */
@media (max-width: 768px) {
  .dashboard-cards-section {
    padding: 0 16px 16px;
  }

  .dashboard-cards-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
  }

  .card-content {
    padding: 20px;
    min-height: 200px;
  }

  .card-title {
    font-size: 15px;
  }

  .card-description {
    font-size: 12px;
  }

  .card-value {
    font-size: 28px;
  }

  .card-icon .q-icon {
    font-size: 2rem !important;
  }
}

/* Mobile Portrait - Single Column */
@media (max-width: 480px) {
  .dashboard-cards-section {
    padding: 0 12px 12px;
  }

  .dashboard-cards-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .card-content {
    padding: 16px;
    min-height: 180px;
  }

  .card-title {
    font-size: 14px;
  }

  .card-description {
    font-size: 11px;
  }

  .card-value {
    font-size: 24px;
  }

  .card-icon .q-icon {
    font-size: 1.8rem !important;
  }
}

/* Tablet Responsive */
@media (min-width: 481px) and (max-width: 1024px) {
  .dashboard-cards-section {
    padding: 0 20px 20px;
  }

  .dashboard-cards-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
  }

  .card-content {
    padding: 22px;
    min-height: 220px;
  }

  .card-title {
    font-size: 15px;
  }

  .card-description {
    font-size: 12px;
  }

  .card-value {
    font-size: 30px;
  }
}

.page-container-with-fixed-header {
  background: #f5f7fb;
}

.greeting-section {
  padding: 16px;
}

.greeting-card {
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 10px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
  min-height: auto;
}

.greeting-card::before {
  display: none;
}

.greeting-content {
  padding: 14px;
}

.greeting-text {
  font-size: 15px;
  font-weight: 700;
  margin: 0;
  color: #0f172a;
}

.greeting-subtitle {
  font-size: 12px;
  color: #6b7280;
  margin: 2px 0 0 0;
}

.appointments-toolbar {
  margin-top: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.appointments-search {
  flex: 1;
  min-width: 260px;
}

.appointments-quick {
  display: flex;
  align-items: center;
  gap: 8px;
}

.appointments-quick-btn {
  border-radius: 6px;
  min-height: 30px;
  text-transform: none;
  font-weight: 600;
}

.dashboard-cards-section {
  padding: 0 16px 14px;
}

.dashboard-cards-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.dashboard-card {
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 10px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
  min-height: auto;
  transition: box-shadow 160ms ease, transform 160ms ease, border-color 160ms ease;
}

.dashboard-card::before {
  display: none;
}

.dashboard-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.10);
}

.schedule-card {
  border-top: 3px solid rgba(20, 184, 166, 0.95);
}

.performance-card {
  border-top: 3px solid rgba(239, 68, 68, 0.95);
}

.rescheduled-card {
  border-top: 3px solid rgba(59, 130, 246, 0.95);
}

.card-content {
  padding: 12px 14px;
}

.card-title {
  font-size: 12px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 2px;
}

.card-description {
  font-size: 11px;
  color: #6b7280;
  margin-bottom: 6px;
}

.card-value {
  font-size: 22px;
  font-weight: 800;
  line-height: 1;
}

.card-icon {
  margin-left: 10px;
  opacity: 0.7;
}

.rescheduled-card .card-value {
  color: rgba(59, 130, 246, 0.95);
}

.rescheduled-card .card-icon {
  color: rgba(59, 130, 246, 0.95);
}

.calendar-panel {
  margin-top: 12px;
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 10px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
  padding: 12px;
}

.calendar-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.calendar-panel-head-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.calendar-checkbox {
  width: 18px;
  height: 18px;
  border-radius: 4px;
  border: 1px solid rgba(15, 23, 42, 0.18);
  background: rgba(15, 23, 42, 0.02);
}

.calendar-month {
  font-size: 12px;
  font-weight: 700;
  color: rgba(13, 148, 136, 0.95);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.calendar-today-btn {
  border-radius: 6px;
  min-height: 30px;
  text-transform: none;
  font-weight: 700;
}

.calendar-nav-btn {
  color: rgba(15, 23, 42, 0.65);
}

.calendar-panel-toolbar {
  margin-top: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.calendar-view-group {
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 7px;
  overflow: hidden;
  background: rgba(15, 23, 42, 0.02);
}

.calendar-view-group .q-btn {
  border-radius: 0;
  min-height: 30px;
  padding: 0 12px;
  text-transform: none;
  font-size: 11px;
  font-weight: 800;
  color: rgba(15, 23, 42, 0.70);
}

.calendar-view-group .q-btn.is-active {
  background: #ffffff;
  color: rgba(13, 148, 136, 0.95);
}

.calendar-panel-toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.calendar-mini-icons {
  display: inline-flex;
  gap: 6px;
}

.mini-icon {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  border: 1px solid rgba(15, 23, 42, 0.16);
  background: rgba(15, 23, 42, 0.02);
}

.calendar-action-btn {
  border-radius: 7px;
  min-height: 30px;
  text-transform: none;
  font-weight: 800;
  font-size: 11px;
}

.calendar-action-btn.is-primary {
  border-color: rgba(13, 148, 136, 0.35);
  background: rgba(13, 148, 136, 0.06);
}

.calendar-grid {
  margin-top: 10px;
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 10px;
  overflow: hidden;
  box-shadow: none;
}

.calendar-cell {
  min-height: 86px;
  padding: 8px 8px 10px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: #ffffff;
  transform: none;
  box-shadow: none;
  transition: background-color 160ms ease, border-color 160ms ease;
  outline: none;
}

.calendar-cell:hover {
  background: rgba(13, 148, 136, 0.06);
}

.calendar-cell:focus-visible {
  outline: 3px solid rgba(13, 148, 136, 0.45);
  outline-offset: -2px;
}

.calendar-cell.header-cell {
  min-height: 42px;
  padding: 8px 10px;
  background: #ffffff;
  font-size: 10px;
  font-weight: 800;
  color: rgba(15, 23, 42, 0.60);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  text-align: left;
}

.calendar-cell.header-cell:hover {
  background: #ffffff;
}

.calendar-cell.other-month {
  background: rgba(15, 23, 42, 0.01);
  color: rgba(15, 23, 42, 0.45);
  opacity: 1;
}

.calendar-cell.today {
  border-color: rgba(13, 148, 136, 0.35);
}

.calendar-cell.selected {
  background: rgba(245, 158, 11, 0.10);
  border-color: rgba(245, 158, 11, 0.25);
  color: inherit;
}

.calendar-cell-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.day-number {
  font-weight: 800;
  font-size: 11px;
  width: 22px;
  height: 22px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  color: rgba(15, 23, 42, 0.72);
  margin-bottom: 0;
}

.calendar-cell.today .day-number {
  border: 1px solid rgba(13, 148, 136, 0.95);
  color: rgba(13, 148, 136, 0.95);
  background: rgba(13, 148, 136, 0.08);
}

.event-dot {
  width: 5px;
  height: 5px;
  border-radius: 999px;
  background: rgba(13, 148, 136, 0.95);
}

.blocked-dot {
  width: 5px;
  height: 5px;
  border-radius: 999px;
  background: rgba(245, 158, 11, 0.95);
}

.cell-appointments-list {
  margin-top: 6px;
  display: grid;
  gap: 6px;
}

.cell-appointment-pill {
  border: 1px solid rgba(13, 148, 136, 0.10);
  border-left: 3px solid rgba(13, 148, 136, 0.85);
  background: rgba(13, 148, 136, 0.10);
  border-radius: 6px;
  padding: 6px 8px;
  font-size: 10px;
  font-weight: 700;
  line-height: 1.2;
  color: rgba(15, 23, 42, 0.92);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cell-appointment-completed {
  opacity: 0.65;
  text-decoration: line-through;
}

.cell-more-count {
  font-size: 10px;
  color: #6b7280;
}

@media (max-width: 768px) {
  .appointments-search {
    min-width: 100%;
  }
  .dashboard-cards-grid {
    grid-template-columns: 1fr;
  }
  .calendar-grid {
    overflow-x: auto;
  }
  .calendar-row {
    min-width: 720px;
  }
}
</style>
