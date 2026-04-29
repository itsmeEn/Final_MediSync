<template>
  <q-layout view="hHh Lpr fFf">
    <DoctorHeader 
      @toggle-drawer="toggleRightDrawer"
      @show-notifications="showNotifications = true"
      :unread-notifications-count="unreadNotificationsCount"
    />

    <DoctorSidebar 
      v-model="rightDrawerOpen"
      @toggle-drawer="toggleRightDrawer"
      active-route="doctor-dashboard"
    />

    <q-page-container class="page-container-with-fixed-header safe-area-bottom role-body-bg">
      <div class="doctor-dashboard-shell">
      <div class="greeting-section">
        <q-card class="greeting-card">
          <q-card-section class="greeting-content">
            <div class="greeting-main">
              <div class="greeting-text-section">
                <h2 class="greeting-text">
                  Good {{ getTimeOfDay() }},
                  {{ userProfile.role.charAt(0).toUpperCase() + userProfile.role.slice(1) }}
                  {{ userProfile.full_name }}
                </h2>
                <p class="greeting-subtitle">See what's happening today - {{ currentDateLabel }}</p>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>

      <div class="dashboard-cards-section">
        <div class="dashboard-cards-grid">
          <q-card class="dashboard-card schedules-card" @click="applyStatusAndScroll('scheduled')">
            <q-card-section class="card-content">
              <div class="card-icon">
                <q-icon name="event_note" size="2.5rem" />
              </div>
              <div class="card-text">
                <div class="card-title">Schedule Appointment</div>
                <div class="card-value">
                  <q-spinner v-if="statsLoading" size="md" />
                  <span v-else>{{ dashboardStats.totalScheduled }}</span>
                </div>
                <div class="card-description">All scheduled appointments</div>
              </div>
            </q-card-section>
          </q-card>

          <q-card class="dashboard-card cancelled-card" @click="applyStatusAndScroll('cancelled')">
            <q-card-section class="card-content">
              <div class="card-icon">
                <q-icon name="event_busy" size="2.5rem" />
              </div>
              <div class="card-text">
                <div class="card-title">Cancelled Appointment</div>
                <div class="card-value">
                  <q-spinner v-if="statsLoading" size="md" />
                  <span v-else>{{ dashboardStats.totalCancelled }}</span>
                </div>
                <div class="card-description">All cancelled appointments</div>
              </div>
            </q-card-section>
          </q-card>

          <q-card class="dashboard-card rescheduled-card" @click="applyStatusAndScroll('rescheduled')">
            <q-card-section class="card-content">
              <div class="card-icon">
                <q-icon name="refresh" size="2.5rem" />
              </div>
              <div class="card-text">
                <div class="card-title">Rescheduled Appointment</div>
                <div class="card-value">
                  <q-spinner v-if="statsLoading" size="md" />
                  <span v-else>{{ dashboardStats.totalRescheduled }}</span>
                </div>
                <div class="card-description">All rescheduled appointments</div>
              </div>
            </q-card-section>
          </q-card>

          <q-card class="dashboard-card assessment-card" @click="applyStatusAndScroll('in_progress')">
            <q-card-section class="card-content">
              <div class="card-icon">
                <q-icon name="assignment" size="2.5rem" />
              </div>
              <div class="card-text">
                <div class="card-title">Pending Assessment</div>
                <div class="card-value">
                  <q-spinner v-if="statsLoading" size="md" />
                  <span v-else>{{ dashboardStats.pendingAssessments }}</span>
                </div>
                <div class="card-description">Currently being assessed by nurses</div>
              </div>
            </q-card-section>
          </q-card>
        </div>
      </div>



      <div class="dashboard-main-grid">
        <div class="calendar-section">
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
                  <q-btn
                    dense
                    outline
                    class="calendar-action-btn"
                    label="Block date"
                    @click="blockDateFromCalendar"
                    :disable="!selectedDate || selectedDate.isBlocked"
                    aria-label="Block date"
                  />
                  <q-btn
                    dense
                    outline
                    class="calendar-action-btn is-primary"
                    label="+ New appointment"
                    @click="showNewAppointmentDialog = true"
                    aria-label="New appointment"
                  />
                </div>
              </div>

              <div class="calendar-grid" role="grid" aria-label="Monthly calendar">
                <div class="calendar-row header-row" role="row">
                  <div v-for="day in weekDays" :key="day" class="calendar-cell header-cell" role="columnheader">
                    {{ day }}
                  </div>
                </div>

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
        </div>

        <!-- Upcoming Appointments Section -->
        <div class="upcoming-appointments-section" ref="appointmentsSectionEl">
        <q-card>
          <q-card-section>
            <div class="section-header">
              <div class="section-header-top">
                <h3 class="section-title">Appointments</h3>
                <div class="appointments-actions">
                  <q-input
                    outlined
                    dense
                    v-model="appointmentSearch"
                    aria-label="Search appointments"
                    placeholder="Search by patient, status, or type"
                    class="appointments-search"
                  >
                    <template v-slot:prepend>
                      <q-icon name="search" />
                    </template>
                    <template v-slot:append v-if="appointmentSearch">
                      <q-btn flat round dense icon="close" aria-label="Clear search" @click="appointmentSearch = ''" />
                    </template>
                  </q-input>
                </div>
              </div>
              <div class="filter-controls">
                <q-btn-group flat class="status-filter">
                  <q-btn
                    flat
                    label="All"
                    :class="{ 'active-filter': selectedStatus === 'all' }"
                    @click="filterByStatus('all')"
                  />
                  <q-btn
                    flat
                    label="Scheduled"
                    :class="{ 'active-filter': selectedStatus === 'scheduled' }"
                    @click="filterByStatus('scheduled')"
                  />
                  <q-btn
                    flat
                    label="Rescheduled"
                    :class="{ 'active-filter': selectedStatus === 'rescheduled' }"
                    @click="filterByStatus('rescheduled')"
                  />
                  <q-btn
                    flat
                    label="In Progress"
                    :class="{ 'active-filter': selectedStatus === 'in_progress' }"
                    @click="filterByStatus('in_progress')"
                  />
                  <q-btn
                    flat
                    label="Completed"
                    :class="{ 'active-filter': selectedStatus === 'completed' }"
                    @click="filterByStatus('completed')"
                  />
                  <q-btn
                    flat
                    label="Cancelled"
                    :class="{ 'active-filter': selectedStatus === 'cancelled' }"
                    @click="filterByStatus('cancelled')"
                  />
                </q-btn-group>
              </div>
            </div>

            <!-- Appointments List -->
            <div class="appointments-list">
              <div
                v-for="appointment in filteredAppointments"
                :key="appointment.id"
                class="appointment-row"
                tabindex="0"
                role="group"
                @keydown.enter.prevent="viewMedicalAssessment(appointment)"
                @keydown.space.prevent="viewMedicalAssessment(appointment)"
                :aria-label="`Appointment for ${appointment.patient_name || appointment.patient?.name || 'Patient'} on ${formatAppointmentDateTime(appointment.appointment_date, appointment.appointment_time)} (${appointment.status})`"
              >
                <div class="appointment-entry">
                  <div class="appointment-title-row">
                    <div class="appointment-title-text">
                      {{ appointment.patient_name }}
                    </div>
                    <q-icon
                      v-if="isAssignedPatient(appointment)"
                      name="assignment"
                      color="secondary"
                      size="18px"
                      class="appointment-title-badge"
                      aria-label="Assigned patient"
                    />
                  </div>

                  <div class="appointment-datetime-row">
                    <div class="appointment-datetime-main">
                      <q-icon name="schedule" size="16px" aria-hidden="true" />
                      <div class="appointment-datetime-text">
                        {{
                          formatAppointmentDateTime(
                            appointment.appointment_date,
                            appointment.appointment_time,
                          )
                        }}
                      </div>
                    </div>
                    <q-chip
                      v-if="getPatientPriority(appointment) === 'high'"
                      color="negative"
                      text-color="white"
                      label="High Risk"
                      size="sm"
                      class="q-ml-xs"
                    />
                    <q-chip
                      v-else-if="getPatientPriority(appointment) === 'medium'"
                      color="orange"
                      text-color="white"
                      label="Medium Risk"
                      size="sm"
                      class="q-ml-xs"
                    />
                    <q-chip
                      :color="getStatusColor(appointment.status)"
                      text-color="white"
                      :label="appointment.status"
                      size="sm"
                      class="q-ml-xs"
                    />
                  </div>
                </div>

                <div class="appointment-actions" aria-label="Appointment actions">
                  <q-btn
                    round
                    flat
                    icon="visibility"
                    color="primary"
                    @click="viewMedicalAssessment(appointment)"
                    class="q-mr-sm"
                  >
                    <q-tooltip>View Medical Assessment</q-tooltip>
                  </q-btn>
                  <q-btn
                    round
                    flat
                    icon="notifications_active"
                    color="primary"
                    @click="notifyPatient(appointment)"
                    class="q-mr-sm"
                  >
                    <q-tooltip>Notify Patient</q-tooltip>
                  </q-btn>
                  <q-btn
                    round
                    flat
                    icon="manage_accounts"
                    color="secondary"
                    @click="managePatient(appointment)"
                    class="q-mr-sm"
                  >
                    <q-tooltip>Manage Patient</q-tooltip>
                  </q-btn>
                  <q-btn
                    round
                    flat
                    icon="check_circle"
                    color="positive"
                    @click="markAsCompleted(appointment)"
                    v-if="isCompletable(appointment)"
                    class="q-mr-sm"
                  >
                    <q-tooltip>Mark as Completed</q-tooltip>
                  </q-btn>
                  <q-btn
                    round
                    flat
                    icon="schedule"
                    color="warning"
                    @click="scheduleFollowUp(appointment)"
                    v-if="appointment.status === 'scheduled'"
                    class="q-mr-sm"
                  >
                    <q-tooltip>Schedule Follow-up</q-tooltip>
                  </q-btn>
                  <q-btn
                    round
                    flat
                    icon="cancel"
                    color="negative"
                    @click="cancelAppointment(appointment)"
                    v-if="appointment.status === 'scheduled' || appointment.status === 'rescheduled'"
                  >
                    <q-tooltip>Cancel Appointment</q-tooltip>
                  </q-btn>
                </div>
              </div>

              <!-- Empty State -->
              <div v-if="filteredAppointments.length === 0" class="empty-state">
                <q-icon name="event_busy" size="4rem" color="grey-4" />
                <h4>No appointments found</h4>
                <p>No appointments match the selected filter criteria.</p>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>
      </div>

      <q-dialog v-model="showNotifications" persistent>
        <q-card class="modal-card notification-modal">
          <q-card-section class="modal-header">
            <div class="modal-title">Notifications</div>
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

      <!-- Notify Patient Success Dialog -->
      <q-dialog v-model="showNotifyDialog" persistent>
        <q-card class="modal-card">
          <q-card-section class="modal-header">
            <div class="modal-title">Patient Notification Sent</div>
            <q-space />
            <q-btn icon="close" flat round dense v-close-popup class="modal-close-btn" />
          </q-card-section>

          <q-card-section v-if="notifyDialogInfo">
            <div class="q-mb-sm"><strong>Patient:</strong> {{ notifyDialogInfo.patientName }}</div>
            <div class="q-mb-sm"><strong>Appointment ID:</strong> {{ notifyDialogInfo.appointmentId }}</div>
            <div class="text-grey-7">{{ notifyDialogInfo.message }}</div>
          </q-card-section>

          <q-card-actions align="right">
            <q-btn flat label="Close" color="primary" v-close-popup />
          </q-card-actions>
        </q-card>
      </q-dialog>

      <!-- Follow-up Scheduling Dialog -->
      <q-dialog v-model="showFollowUpDialog" persistent>
        <q-card style="min-width: 400px">
          <q-card-section>
            <div class="text-h6">Schedule Follow-up</div>
          </q-card-section>

          <q-form @submit="confirmFollowUp">
            <q-card-section class="q-pt-none">
              <q-input
                filled
                v-model="followUpData.date"
                label="Follow-up Date"
                type="date"
                :rules="[(val) => !!val || 'Date is required']"
              />
              <q-input
                filled
                v-model="followUpData.time"
                label="Follow-up Time"
                type="time"
                :rules="[(val) => !!val || 'Time is required']"
              />
              <q-input
                filled
                v-model="followUpData.notes"
                label="Follow-up Notes"
                type="textarea"
                rows="3"
                placeholder="Reason for follow-up, instructions, etc."
              />
            </q-card-section>

            <q-card-actions align="right">
              <q-btn flat label="Cancel" color="grey" v-close-popup />
              <q-btn label="Schedule Follow-up" type="submit" color="primary" />
            </q-card-actions>
          </q-form>
        </q-card>
      </q-dialog>

      <!-- Medical Assessment Dialog -->
      <q-dialog v-model="showMedicalAssessmentDialog" maximized>
        <q-card class="medical-assessment-dialog">
          <q-card-section class="row items-center q-pb-none">
            <div class="text-h6">Medical Assessment - {{ selectedAppointment?.patient?.name || selectedAppointment?.patient_name }}</div>
            <q-space />
            <q-btn icon="close" flat round dense v-close-popup />
          </q-card-section>

          <q-card-section>
            <div v-if="selectedAppointment" class="medical-assessment-content">
              <div class="row q-gutter-md">
                <div class="col-md-6 col-12">
                  <q-card flat bordered>
                    <q-card-section>
                      <h6>Patient Information</h6>
                      <p><strong>Name:</strong> {{ selectedAppointment.patient?.name || selectedAppointment.patient_name }}</p>
                      <p><strong>Date:</strong> {{ selectedAppointment.appointment_date }}</p>
                      <p><strong>Time:</strong> {{ selectedAppointment.appointment_time }}</p>
                      <p><strong>Status:</strong> {{ selectedAppointment.status }}</p>
                    </q-card-section>
                  </q-card>
                </div>
                <div class="col-md-6 col-12">
                  <q-card flat bordered>
                    <q-card-section>
                      <h6>Assessment Details</h6>
                      <div class="text-center q-pa-lg">
                        <q-icon name="assignment" size="4rem" color="grey-5" />
                        <h4>No Medical Assessment Available</h4>
                        <p>No medical assessment has been completed for this patient yet.</p>
                      </div>
                    </q-card-section>
                  </q-card>
                </div>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </q-dialog>

      <q-dialog v-model="showNewAppointmentDialog" persistent>
        <q-card class="modal-card" style="min-width: 420px">
          <q-card-section class="modal-header">
            <div class="modal-title">New Appointment</div>
            <q-space />
            <q-btn icon="close" flat round dense v-close-popup class="modal-close-btn" />
          </q-card-section>

          <q-form @submit="createAppointment">
            <q-card-section class="q-pt-none">
              <q-input
                filled
                v-model="newAppointment.patient_name"
                label="Patient Name"
                :rules="[(val) => !!val || 'Patient name is required']"
              />
              <q-input
                filled
                v-model="newAppointment.appointment_date"
                label="Date"
                type="date"
                :rules="[(val) => !!val || 'Date is required']"
              />
              <q-input
                filled
                v-model="newAppointment.appointment_time"
                label="Time"
                type="time"
                :rules="[(val) => !!val || 'Time is required']"
              />
              <q-select
                filled
                v-model="newAppointment.appointment_type"
                label="Appointment Type"
                :options="appointmentTypes"
                :rules="[(val) => !!val || 'Type is required']"
              />
              <q-input
                filled
                v-model="newAppointment.notes"
                label="Notes (Optional)"
                type="textarea"
                rows="3"
              />
            </q-card-section>

            <q-card-actions align="right">
              <q-btn flat label="Cancel" color="grey" v-close-popup />
              <q-btn label="Create" type="submit" color="primary" />
            </q-card-actions>
          </q-form>
        </q-card>
      </q-dialog>

      <q-dialog v-model="showBlockDateDialog" persistent>
        <q-card class="modal-card" style="min-width: 420px">
          <q-card-section class="modal-header">
            <div class="modal-title">Block Date</div>
            <q-space />
            <q-btn icon="close" flat round dense v-close-popup class="modal-close-btn" />
          </q-card-section>

          <q-card-section class="q-pt-none">
            <q-date v-model="blockDateDate" mask="YYYY-MM-DD" class="full-width" />
            <div v-if="blockedDates.length" class="blocked-dates-list q-mt-md">
              <div class="text-subtitle2 q-mb-sm">Blocked Dates</div>
              <div class="row q-col-gutter-sm">
                <div v-for="d in blockedDates" :key="d" class="col-auto">
                  <q-chip color="negative" text-color="white" dense>{{ formatDate(d) }}</q-chip>
                </div>
              </div>
            </div>
          </q-card-section>

          <q-card-actions align="right">
            <q-btn flat label="Close" color="grey" v-close-popup />
            <q-btn label="Block" color="primary" @click="blockDateFromModal" />
          </q-card-actions>
        </q-card>
      </q-dialog>

      </div>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useQuasar } from 'quasar';
import { useRouter } from 'vue-router';
import { api } from '../boot/axios';
import { useIntervalManager } from '../utils/intervalManager';
import DoctorHeader from '../components/DoctorHeader.vue';
import DoctorSidebar from '../components/DoctorSidebar.vue';

// Type definitions
interface Patient {
  id: number;
  name: string;
  [key: string]: unknown;
}

interface Appointment {
  id: number;
  patient?: Patient;
  patient_name?: string;
  appointment_time?: string;
  appointment_date?: string;
  status: string;
  completed_at?: string;
  [key: string]: unknown;
}

const $q = useQuasar();
const router = useRouter();

const rightDrawerOpen = ref(false);
const unreadNotificationsCount = ref(0);

// Dashboard statistics
const dashboardStats = ref({
  pendingAssessments: 0,
  totalScheduled: 0,
  totalCancelled: 0,
  totalRescheduled: 0,
});

// Loading states for dashboard stats
const statsLoading = ref(true);

// Modal states
const showNotifications = ref(false);
const showNotifyDialog = ref(false);
const notifyDialogInfo = ref<null | { patientName: string; appointmentId: number; message: string }>(null);

// Modal data
const assignedPatients = ref<Array<{ patient_id: number; patient_name: string; priority?: string }>>([]);
const assignmentPriorityByPatientId = computed<Record<number, string>>(() => {
  const map: Record<number, string> = {};
  for (const a of assignedPatients.value) {
    if (a.patient_id) map[a.patient_id] = String(a.priority || '').toLowerCase();
  }
  return map;
});
void assignmentPriorityByPatientId.value;

// Upcoming appointments data
const appointments = ref<Appointment[]>([]);
const appointmentSearch = ref('');
const selectedStatus = ref<
  'all' | 'scheduled' | 'rescheduled' | 'in_progress' | 'completed' | 'cancelled'
>('all');
const appointmentsSectionEl = ref<HTMLElement | null>(null);
const showMedicalAssessmentDialog = ref(false);
const showFollowUpDialog = ref(false);
const selectedAppointment = ref<Appointment | null>(null);
const followUpData = ref({
  date: '',
  time: '',
  notes: '',
});

const showNewAppointmentDialog = ref(false);
const showBlockDateDialog = ref(false);
const blockedDates = ref<string[]>([]);
const blockDateDate = ref<string>('');
const newAppointment = ref({
  patient_name: '',
  appointment_date: '',
  appointment_time: '',
  appointment_type: '',
  notes: '',
});
const appointmentTypes = ['consultation', 'follow_up', 'emergency'];

type CalendarView = 'day' | 'week' | 'month';
type DayData = {
  date: Date;
  dayNumber: number;
  isCurrentMonth: boolean;
  isToday: boolean;
  isSelected: boolean;
  isBlocked: boolean;
  appointments: Appointment[];
};

const currentDate = ref(new Date());
const selectedDate = ref<DayData | null>(null);
const currentView = ref<CalendarView>('month');
const weekDays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

// Loading states for modals
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



// Real-time features
const currentTime = ref('');
const weatherData = ref<{
  temperature: number;
  condition: string;
  location: string;
} | null>(null);
const weatherLoading = ref(false);
const weatherError = ref(false);

// Initialize interval manager
const { createTimeInterval, createNotificationInterval, createRefreshInterval } = useIntervalManager();



// User profile data - fetched from API
const userProfile = ref<{
  id?: number;
  full_name: string;
  specialization?: string;
  role: string;
  profile_picture: string | null;
  verification_status: string;
}>({
  full_name: 'Loading...',
  specialization: 'Loading specialization...',
  role: 'doctor',
  profile_picture: null,
  verification_status: 'not_submitted',
});

// Get time of day for greeting
const getTimeOfDay = () => {
  const hour = new Date().getHours();
  if (hour < 12) return 'morning';
  if (hour < 18) return 'afternoon';
  return 'evening';
};

// Current date for greeting
const currentDateLabel = computed(() => {
  const now = new Date();
  return now.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
});

// Fetch weather data
const fetchWeatherData = async () => {
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
    console.error('Failed to fetch weather data:', error);
    weatherError.value = true;
  } finally {
    weatherLoading.value = false;
  }
};

const toggleRightDrawer = () => {
  rightDrawerOpen.value = !rightDrawerOpen.value;
};

// Fetch user profile data
const fetchUserProfile = async () => {
  try {
    const response = await api.get('/users/profile/');
    const userData = response.data.user; // The API returns nested user data

    // Role verification - ensure only doctors can access this dashboard
    if (userData.role !== 'doctor') {
      $q.notify({
        type: 'negative',
        message: 'Access denied. This dashboard is only available for doctors.',
        timeout: 3000,
      });
      
      // Enforce doctor context on doctor dashboard regardless of API role
      if (userData.role !== 'doctor') {
        console.warn('Profile API returned non-doctor role on doctor dashboard; enforcing doctor context. Received:', userData.role);
      }
    }

    // Check localStorage for updated profile picture
    const storedUser = JSON.parse(localStorage.getItem('user') || '{}');

    userProfile.value = {
      id: userData.id,
      full_name: userData.full_name,
      specialization: typeof userData.doctor_profile?.specialization === 'string' ? userData.doctor_profile.specialization : '',
      role: 'doctor',
      profile_picture: storedUser.profile_picture || userData.profile_picture || null,
      verification_status: userData.verification_status,
    };

    console.log('User profile loaded:', userProfile.value);

    // Fetch dashboard stats after profile is loaded
    await fetchDashboardStats();
  } catch (error) {
    console.error('Failed to fetch user profile:', error);

    // Fallback to localStorage without role-based redirects; enforce doctor context
    const raw = localStorage.getItem('user');
    if (raw) {
      const user = JSON.parse(raw);
      userProfile.value = {
        id: user.id,
        full_name: user.full_name,
        specialization: typeof user.doctor_profile?.specialization === 'string' ? user.doctor_profile.specialization : '',
        role: 'doctor',
        profile_picture: user.profile_picture || null,
        verification_status: user.verification_status || 'not_submitted',
      };
      await fetchDashboardStats();
    } else {
      $q.notify({
        type: 'negative',
        message: 'Failed to load user profile. Please log in again.',
        position: 'top',
        timeout: 3000,
      });
      await router.push('/login');
    }
  }
};

// Utility functions for formatting
const formatTime = (timeString?: string) => {
  if (!timeString) return 'N/A';
  return new Date(timeString).toLocaleTimeString('en-US', {
    hour12: true,
    hour: 'numeric',
    minute: '2-digit',
  });
};

const formatDate = (dateString?: string) => {
  if (!dateString) return 'N/A';
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
};

const getStatusColor = (status?: string) => {
  switch (status?.toLowerCase()) {
    case 'scheduled':
    case 'confirmed':
      return 'blue';
    case 'rescheduled':
      return 'secondary';
    case 'completed':
      return 'green';
    case 'cancelled':
      return 'red';
    case 'in_progress':
      return 'orange';
    case 'pending':
      return 'warning';
    default:
      return 'grey';
  }
};

// Upcoming appointments functions
const filteredAppointments = computed(() => {
  const status = selectedStatus.value;
  const q = appointmentSearch.value.trim().toLowerCase();
  const list = status === 'all' ? appointments.value : appointments.value.filter((a) => a.status === status);
  if (!q) return list;
  return list.filter((a) => {
    const patient = String(a.patient?.name ?? a.patient_name ?? '').toLowerCase();
    const type = String((a as unknown as { appointment_type?: string }).appointment_type ?? '').toLowerCase();
    const s = String(a.status ?? '').toLowerCase();
    return patient.includes(q) || type.includes(q) || s.includes(q);
  });
});

function filterByStatus(
  status: 'all' | 'scheduled' | 'rescheduled' | 'in_progress' | 'completed' | 'cancelled',
) {
  selectedStatus.value = status;
}

function applyStatusAndScroll(
  status: 'scheduled' | 'rescheduled' | 'in_progress' | 'completed' | 'cancelled',
) {
  selectedStatus.value = status;
  const el = appointmentsSectionEl.value;
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

const currentMonthYear = computed(() => {
  return currentDate.value.toLocaleDateString('en-US', {
    month: 'long',
    year: 'numeric',
  });
});

const calendarWeeks = computed(() => {
  const year = currentDate.value.getFullYear();
  const month = currentDate.value.getMonth();

  const firstDay = new Date(year, month, 1);
  const startDate = new Date(firstDay);
  startDate.setDate(startDate.getDate() - firstDay.getDay());

  const weeks: DayData[][] = [];
  let currentWeek: DayData[] = [];

  for (let i = 0; i < 42; i += 1) {
    const date = new Date(startDate);
    date.setDate(startDate.getDate() + i);

    const dayData: DayData = {
      date,
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

function toLocalDateString(dateObj: Date): string {
  const year = dateObj.getFullYear();
  const month = String(dateObj.getMonth() + 1).padStart(2, '0');
  const day = String(dateObj.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function isToday(dateObj: Date): boolean {
  const now = new Date();
  return (
    dateObj.getFullYear() === now.getFullYear() &&
    dateObj.getMonth() === now.getMonth() &&
    dateObj.getDate() === now.getDate()
  );
}

function isSameDate(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

function isDateBlocked(dateObj: Date): boolean {
  const key = toLocalDateString(dateObj);
  return blockedDates.value.includes(key);
}

function getAppointmentsForDate(dateObj: Date): Appointment[] {
  const key = toLocalDateString(dateObj);
  return appointments.value.filter((a) => {
    const raw = String(a.appointment_date || '');
    if (!raw) return false;
    const sliced = raw.length >= 10 ? raw.slice(0, 10) : '';
    if (sliced) return sliced === key;
    const d = new Date(raw);
    if (Number.isNaN(d.getTime())) return false;
    return toLocalDateString(d) === key;
  });
}

function selectDate(day: DayData) {
  selectedDate.value = day;
}

function previousMonth() {
  const d = currentDate.value;
  currentDate.value = new Date(d.getFullYear(), d.getMonth() - 1, 1);
}

function nextMonth() {
  const d = currentDate.value;
  currentDate.value = new Date(d.getFullYear(), d.getMonth() + 1, 1);
}

function goToToday() {
  const now = new Date();
  currentDate.value = new Date(now.getFullYear(), now.getMonth(), 1);
  const today = calendarWeeks.value.flat().find((d) => d.isToday);
  if (today) selectedDate.value = today;
}

function setView(view: CalendarView) {
  currentView.value = view;
}

async function fetchBlockedDates() {
  try {
    const response = await api.get('/operations/blocked-dates/');
    const raw = Array.isArray(response.data) ? response.data : (response.data?.results ?? []);
    blockedDates.value = Array.isArray(raw) ? raw.map((d) => String(d)) : [];
  } catch (error) {
    console.error('Failed to fetch blocked dates:', error);
    blockedDates.value = [];
  }
}

async function blockDateFromCalendar() {
  if (!selectedDate.value) {
    $q.notify({ type: 'negative', message: 'Please select a date to block', position: 'top' });
    return;
  }
  const dateString = toLocalDateString(selectedDate.value.date);
  if (!dateString) {
    $q.notify({ type: 'negative', message: 'Please select a date to block', position: 'top' });
    return;
  }
  try {
    await api.post('/operations/block-date/', { date: dateString });
    await fetchBlockedDates();
    selectedDate.value.isBlocked = true;
    $q.notify({ type: 'positive', message: 'Date blocked successfully', position: 'top' });
  } catch (error) {
    console.error('Failed to block date:', error);
    $q.notify({ type: 'negative', message: 'Failed to block date', position: 'top' });
  }
}

async function blockDateFromModal() {
  const dateString = String(blockDateDate.value || '').trim();
  if (!dateString) {
    $q.notify({ type: 'negative', message: 'Please select a date to block', position: 'top' });
    return;
  }
  try {
    await api.post('/operations/block-date/', { date: dateString });
    await fetchBlockedDates();
    $q.notify({ type: 'positive', message: 'Date blocked successfully', position: 'top' });
    showBlockDateDialog.value = false;
  } catch (error) {
    console.error('Failed to block date:', error);
    $q.notify({ type: 'negative', message: 'Failed to block date', position: 'top' });
  }
}

async function createAppointment() {
  try {
    const date = String(newAppointment.value.appointment_date || '').trim();
    const time = String(newAppointment.value.appointment_time || '').trim();
    const payload = {
      ...newAppointment.value,
      appointment_date: date && time ? `${date}T${time}` : date,
    };
    await api.post('/operations/create-appointment/', payload);
    newAppointment.value = {
      patient_name: '',
      appointment_date: '',
      appointment_time: '',
      appointment_type: '',
      notes: '',
    };
    showNewAppointmentDialog.value = false;
    await fetchAppointments();
    await fetchDashboardStats();
    $q.notify({ type: 'positive', message: 'Appointment created successfully', position: 'top' });
  } catch (error) {
    console.error('Failed to create appointment:', error);
    $q.notify({ type: 'negative', message: 'Failed to create appointment', position: 'top' });
  }
}

function formatAppointmentDateTime(date?: string, time?: string): string {
  if (!date || !time) return 'Date/Time not available';
  
  const dateObj = new Date(date);
  const formattedDate = dateObj.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  });
  return `${formattedDate} at ${time}`;
}

function viewMedicalAssessment(appointment: Appointment) {
  selectedAppointment.value = appointment;
  showMedicalAssessmentDialog.value = true;
}

function getAppointmentId(appt: Appointment): number {
  // Support both id and appointment_id coming from backend
  const anyAppt = appt as unknown as { id?: number; appointment_id?: number };
  return Number(anyAppt.appointment_id ?? anyAppt.id ?? -1);
}

function isCompletable(appt: Appointment): boolean {
  const status = String(appt?.status || '').toLowerCase();
  // Show complete action for active appointments
  return status === 'confirmed' || status === 'scheduled';
}

async function notifyPatient(appointment: Appointment) {
  try {
    const apptId = getAppointmentId(appointment);
    if (!apptId || apptId < 0) {
      $q.notify({ type: 'negative', message: 'Invalid appointment ID', position: 'top' });
      return;
    }

    const resp = await api.post(`/operations/appointments/${apptId}/notify-patient/`);
    const backendMsg = resp?.data?.message || 'Patient notification queued';
    const patientName = String(appointment.patient?.name ?? appointment.patient_name ?? 'Patient');

    // Toast confirmation
    $q.notify({ type: 'positive', message: backendMsg, position: 'top' });

    // Success popup dialog
    notifyDialogInfo.value = { patientName, appointmentId: apptId, message: backendMsg };
    showNotifyDialog.value = true;
  } catch (error) {
    console.error('Failed to notify patient:', error);
    const err = error;
    let httpStatus: number | undefined;
    let serverMsg: string | undefined;
    if (typeof err === 'object' && err && 'response' in err) {
      const resp = (err as { response?: { status?: number; data?: { error?: string; message?: string } } }).response;
      httpStatus = resp?.status;
      serverMsg = resp?.data?.error ?? resp?.data?.message;
    }
    let friendlyMsg = serverMsg || (err instanceof Error ? err.message : 'Failed to notify patient');

    if (httpStatus === 401) {
      friendlyMsg = 'Authentication required. Please sign in again.';
    } else if (httpStatus === 403) {
      friendlyMsg = 'Insufficient permissions to notify patient.';
    } else if (httpStatus === 400) {
      friendlyMsg = serverMsg || 'Notification allowed only shortly before the appointment start time.';
    }

    $q.notify({ type: 'negative', message: friendlyMsg, position: 'top' });
  }
}

async function managePatient(appointment: Appointment) {
  try {
    const anyAppt = appointment as unknown as { patient?: { id?: number; name?: string }; patient_id?: number };
    const pid = Number(anyAppt.patient?.id ?? anyAppt.patient_id ?? NaN);
    const query: Record<string, string> = {};
    if (!Number.isNaN(pid)) {
      query.patientId = String(pid);
    } else if (appointment.patient_name) {
      query.patientName = String(appointment.patient_name);
    }
    await router.push({ name: 'DoctorPatientManagement', query });
  } catch (error) {
    console.error('Failed to navigate to patient management:', error);
    $q.notify({ type: 'negative', message: 'Navigation error', position: 'top' });
  }
}

async function markAsCompleted(appointment: Appointment) {
  try {
    const apptId = getAppointmentId(appointment);
    await api.post(`/operations/appointments/${apptId}/finish/`);

    // Update local appointment
    const index = appointments.value.findIndex((a) => getAppointmentId(a) === apptId);
    if (index !== -1 && appointments.value[index]) {
      appointments.value[index].status = 'completed';
    }

    $q.notify({
      type: 'positive',
      message: 'Appointment marked as completed',
      position: 'top',
    });
  } catch (error) {
    console.error('Failed to mark appointment as completed:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to update appointment status',
      position: 'top',
    });
  }
}

function scheduleFollowUp(appointment: Appointment) {
  selectedAppointment.value = appointment;
  followUpData.value = {
    date: '',
    time: '',
    notes: '',
  };
  showFollowUpDialog.value = true;
}

async function confirmFollowUp() {
  if (!selectedAppointment.value) return;

  try {
    const date = String(followUpData.value.date || '').trim();
    const time = String(followUpData.value.time || '').trim();
    const baseId = getAppointmentId(selectedAppointment.value);
    const followUpAppointment = {
      patient_name: selectedAppointment.value.patient?.name,
      appointment_date: date && time ? `${date}T${time}` : date,
      appointment_time: time,
      appointment_type: 'follow_up',
      notes: followUpData.value.notes,
      original_appointment_id: baseId,
    };

    await api.post('/operations/create-appointment/', followUpAppointment);

    showFollowUpDialog.value = false;
    await fetchAppointments();
    await fetchDashboardStats();

    $q.notify({
      type: 'positive',
      message: 'Follow-up appointment scheduled successfully',
      position: 'top',
    });
  } catch (error) {
    console.error('Failed to schedule follow-up:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to schedule follow-up appointment',
      position: 'top',
    });
  }
}

async function cancelAppointment(appointment: Appointment) {
  try {
    const apptId = getAppointmentId(appointment);
    await api.patch(`/operations/appointments/${apptId}/`, {
      status: 'cancelled',
    });

    // Update local appointment
    const index = appointments.value.findIndex((a) => getAppointmentId(a) === apptId);
    if (index !== -1 && appointments.value[index]) {
      appointments.value[index].status = 'cancelled';
    }
    await fetchDashboardStats();

    $q.notify({
      type: 'positive',
      message: 'Appointment cancelled successfully',
      position: 'top',
    });
  } catch (error) {
    console.error('Failed to cancel appointment:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to cancel appointment',
      position: 'top',
    });
  }
}

async function fetchAppointments() {
  try {
    const response = await api.get('/operations/appointments/', {
      params: {
        ...(userProfile.value.id ? { doctor: userProfile.value.id } : {}),
      },
    });
    const raw = Array.isArray(response.data) ? response.data : (response.data?.results ?? []);
    // Normalize to ensure id and fields present
    type BackendAppointment = {
      id?: number;
      appointment_id?: number;
      patient_name?: string;
      patient?: { id?: number; name?: string } | null;
      appointment_date?: string;
      date?: string;
      appointment_time?: string;
      time?: string;
      status?: string;
      appointment_type?: string;
      type?: string;
      notes?: string;
      consultation_finished_at?: string;
      completed_at?: string;
    };

    const mapped = (raw as BackendAppointment[]).map((a) => {
      const patientObj = a?.patient && typeof a.patient === 'object' ? a.patient : null;
      const appt: Appointment = {
        id: Number(a?.id ?? a?.appointment_id ?? -1),
        patient_name: String(a?.patient_name ?? (patientObj?.name ?? '')),
        appointment_date: String(a?.appointment_date ?? a?.date ?? ''),
        appointment_time: String(a?.appointment_time ?? a?.time ?? ''),
        status: String(a?.status ?? 'scheduled'),
        completed_at: a?.consultation_finished_at ?? a?.completed_at ?? undefined,
        appointment_id: Number(a?.appointment_id ?? a?.id ?? -1),
        appointment_type: String(a?.appointment_type ?? a?.type ?? ''),
        notes: typeof a?.notes === 'string' ? a.notes : '',
      } as Appointment;

      if (patientObj) {
        appt.patient = {
          id: Number((patientObj as { id?: number }).id ?? -1),
          name: String((patientObj as { name?: string }).name ?? ''),
        };
      }

      return appt;
    });
    appointments.value = mapped;
  } catch (error) {
    console.error('Failed to fetch appointments:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to load appointments',
      position: 'top',
    });
  }
}



const loadNotifications = async (): Promise<void> => {
  try {
    console.log('📬 Loading doctor notifications...');

    const response = await api.get('/operations/notifications/');
    notifications.value = response.data || [];

    console.log('Doctor notifications loaded:', notifications.value.length);
  } catch (error: unknown) {
    console.error('Error loading doctor notifications:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to load notifications',
    });
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

function extractCount(payload: unknown): number {
  if (!payload) return 0;
  if (typeof payload === 'number') return payload;
  if (Array.isArray(payload)) return payload.length;
  if (typeof payload === 'object') {
    const p = payload as { count?: unknown; results?: unknown };
    if (typeof p.count === 'number') return p.count;
    if (Array.isArray(p.results)) return p.results.length;
  }
  return 0;
}

async function fetchAppointmentCount(params: Record<string, string | number | undefined>) {
  const response = await api.get('/operations/appointments/', { params });
  return extractCount(response.data);
}

// Fetch dashboard statistics
const fetchDashboardStats = async () => {
  try {
    statsLoading.value = true;

    // Fetch all required data in parallel
    const [
      pendingAssessmentsRes,
      totalScheduledRes,
      totalCancelledRes,
      totalRescheduledRes,
    ] = await Promise.all([
      // Pending assessments (currently being assessed by nurses)
      api
        .get('/operations/patient-assessments/', {
          params: {
            status: 'in_progress',
          },
        })
        .catch(() => ({ data: { count: 0 } })),

      fetchAppointmentCount({ doctor: userProfile.value.id, status: 'scheduled' }).catch(() => 0),
      fetchAppointmentCount({ doctor: userProfile.value.id, status: 'cancelled' }).catch(() => 0),
      fetchAppointmentCount({ doctor: userProfile.value.id, status: 'rescheduled' }).catch(() => 0),
    ]);

    dashboardStats.value = {
      pendingAssessments:
        pendingAssessmentsRes.data.count || pendingAssessmentsRes.data.results?.length || 0,
      totalScheduled: typeof totalScheduledRes === 'number' ? totalScheduledRes : 0,
      totalCancelled: typeof totalCancelledRes === 'number' ? totalCancelledRes : 0,
      totalRescheduled: typeof totalRescheduledRes === 'number' ? totalRescheduledRes : 0,
    };

    console.log('Dashboard stats loaded:', dashboardStats.value);
  } catch (error) {
    console.error('Failed to fetch dashboard stats:', error);

    // Set default values on error
    dashboardStats.value = {
      pendingAssessments: 0,
      totalScheduled: 0,
      totalCancelled: 0,
      totalRescheduled: 0,
    };
  } finally {
    statsLoading.value = false;
  }
};

// Daily refresh functionality
const setupDailyRefresh = () => {
  const now = new Date();
  const tomorrow = new Date(now);
  tomorrow.setDate(tomorrow.getDate() + 1);
  tomorrow.setHours(0, 0, 0, 0);

  const msUntilMidnight = tomorrow.getTime() - now.getTime();

  setTimeout(() => {
    // Refresh dashboard stats at midnight
    void fetchDashboardStats();

    // Set up daily refresh
    setInterval(
      () => {
        void fetchDashboardStats();
      },
      24 * 60 * 60 * 1000,
    ); // 24 hours
  }, msUntilMidnight);
};

const loadMessageNotifications = async (): Promise<void> => {
  try {
    const response = await api.get('/operations/messaging/notifications/');
    const list = Array.isArray(response.data) ? response.data : [];
    const unread = list.filter((n: { is_sent?: boolean }) => !n.is_sent).length;
    unreadNotificationsCount.value = unread;
  } catch {
    unreadNotificationsCount.value = 0;
  }
};

const loadAssignedPatients = async (): Promise<void> => {
  try {
    const response = await api.get('/operations/doctor/assignments/');
    const raw = Array.isArray(response.data) ? response.data : [];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    assignedPatients.value = raw.map((assignment: any) => ({
      patient_id: Number(assignment.patient_id ?? assignment.id ?? 0),
      patient_name:
        assignment.patient_name ?? assignment.name ?? assignment.full_name ?? 'Unknown Patient',
      priority: assignment.priority ?? assignment.risk_level ?? assignment.status,
    }));
  } catch {
    assignedPatients.value = [];
  }
};

const getPatientPriority = (appointment: Appointment): string | undefined => {
  const pid = Number(appointment.patient?.id ?? 0);
  const byId = assignmentPriorityByPatientId.value[pid];
  if (byId) return byId;
  const name = String(appointment.patient?.name ?? appointment.patient_name ?? '').trim();
  const found = assignedPatients.value.find(
    (a) => String(a.patient_name || '').trim().toLowerCase() === name.toLowerCase(),
  );
  return found ? String(found.priority || '').toLowerCase() : undefined;
};

const isAssignedPatient = (appointment: Appointment): boolean => {
  const pid = Number(appointment.patient?.id ?? 0);
  if (assignmentPriorityByPatientId.value[pid]) return true;
  const name = String(appointment.patient?.name ?? appointment.patient_name ?? '').trim();
  return assignedPatients.value.some(
    (a) => String(a.patient_name || '').trim().toLowerCase() === name.toLowerCase(),
  );
};

onMounted(() => {
  // Load user profile data from API (this will also fetch dashboard stats)
  void fetchUserProfile();

  // Load notifications
  void loadNotifications();

  // Load upcoming appointments
  void fetchAppointments();
  blockDateDate.value = toLocalDateString(new Date());
  void fetchBlockedDates();

  void loadMessageNotifications();
  void loadAssignedPatients();



  // Initialize real-time features with interval manager
  createTimeInterval('doctor-dashboard-time', (time) => {
    currentTime.value = time;
  });

  // Fetch weather data
  void fetchWeatherData();

  // Setup daily refresh
  setupDailyRefresh();

  // Setup notification polling with interval manager
  createNotificationInterval('doctor-dashboard-notifications', loadNotifications, 30000);
  createRefreshInterval('doctor-dashboard-appointments', fetchAppointments, 30000);
  createRefreshInterval('doctor-dashboard-messaging', loadMessageNotifications, 30000);
  createRefreshInterval('doctor-dashboard-assignments', loadAssignedPatients, 30000);
});

onUnmounted(() => {
  // Interval manager automatically cleans up intervals
  // No manual cleanup needed
});



</script>

<style scoped>
/* Prototype Header Styles */
.prototype-header {
  background: #286660;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* Safe Area Support */
.safe-area-top {
  padding-top: env(safe-area-inset-top);
}

.safe-area-bottom {
  padding-bottom: env(safe-area-inset-bottom);
}

.safe-area-left {
  padding-left: env(safe-area-inset-left);
}

.safe-area-right {
  padding-right: env(safe-area-inset-right);
}

/* Tooltip Safe Area Support */
.q-tooltip {
  max-width: calc(100vw - env(safe-area-inset-left) - env(safe-area-inset-right) - 16px);
  margin-top: max(env(safe-area-inset-top), 8px);
}

@media (max-width: 768px) {
  .q-tooltip {
    margin-top: max(env(safe-area-inset-top), 12px);
    max-width: calc(100vw - env(safe-area-inset-left) - env(safe-area-inset-right) - 24px);
  }
}

@media (max-width: 480px) {
  .q-tooltip {
    margin-top: max(env(safe-area-inset-top), 16px);
    max-width: calc(100vw - env(safe-area-inset-left) - env(safe-area-inset-right) - 32px);
  }
}

.header-toolbar {
  padding: 0 24px;
  min-height: 64px;
}

/* Mobile Header Layout */
.mobile-header-layout {
  display: flex;
  flex-direction: column;
  padding: 8px 16px;
  min-height: 80px;
}

.header-top-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  min-height: 40px;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  justify-content: center;
}

.header-bottom-row {
  display: flex;
  align-items: center;
  min-height: 40px;
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

/* Mobile Sidebar Styles */
@media (max-width: 768px) {
  .prototype-sidebar {
    width: 100vw !important;
    max-width: 100vw !important;
    z-index: 3000;
  }

  .q-drawer__backdrop {
    z-index: 2999;
  }

  .sidebar-content {
    padding-bottom: 60px;
  }

  .logo-section {
    padding: 16px;
  }

  .logo-text {
    font-size: 18px;
  }

  .sidebar-user-profile {
    padding: 16px;
  }

  .profile-avatar {
    width: 60px;
    height: 60px;
  }

  .user-name {
    font-size: 16px;
  }

  .user-role {
    font-size: 13px;
  }

  .navigation-menu {
    padding: 8px 0;
  }

  .nav-item {
    margin: 2px 12px;
    padding: 8px 12px;
    border-radius: 6px;
  }

  .logout-section {
    padding: 16px;
  }

  .logout-btn {
    padding: 8px 16px;
    font-size: 14px;
    border-radius: 6px;
  }
}

@media (max-width: 480px) {
  .prototype-sidebar {
    width: 100vw !important;
    max-width: 100vw !important;
  }

  .sidebar-content {
    padding-bottom: 50px;
  }

  .logo-section {
    padding: 12px;
  }

  .logo-text {
    font-size: 16px;
  }

  .sidebar-user-profile {
    padding: 12px;
  }

  .profile-avatar {
    width: 50px;
    height: 50px;
  }

  .user-name {
    font-size: 15px;
  }

  .user-role {
    font-size: 12px;
  }

  .navigation-menu {
    padding: 6px 0;
  }

  .nav-item {
    margin: 1px 8px;
    padding: 6px 10px;
    border-radius: 4px;
  }

  .logout-section {
    padding: 12px;
  }

  .logout-btn {
    padding: 6px 12px;
    font-size: 13px;
    border-radius: 4px;
  }
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

.upload-btn {
  position: absolute;
  bottom: 0;
  right: 0;
  transform: translate(25%, 25%);
}

.verified-badge {
  position: absolute;
  bottom: 0;
  right: 0;
  background: white;
  border-radius: 50%;
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

/* Page Container with Clean White Background */
.page-container-with-fixed-header {
  background: #ffffff;
  min-height: 100vh;
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
    rgba(248, 250, 252, 0.8) 0%,
    rgba(241, 245, 249, 0.6) 50%,
    rgba(248, 250, 252, 0.4) 100%
  );
  z-index: 0;
  pointer-events: none;
}

.page-container-with-fixed-header > * {
  position: relative;
  z-index: 1;
}

/* Enhanced Greeting Section */
.greeting-section {
  padding: 32px 24px 24px 24px;
  background: transparent;
}

.greeting-card {
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.95) 0%,
    rgba(248, 250, 252, 0.9) 50%,
    rgba(241, 245, 249, 0.85) 100%
  );
  backdrop-filter: blur(10px);
  border-radius: 20px;
  border: 1px solid rgba(40, 102, 96, 0.1);
  box-shadow: 
    0 10px 25px rgba(40, 102, 96, 0.08),
    0 4px 10px rgba(0, 0, 0, 0.03),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  position: relative;
  width: 100%;
  min-height: 160px;
}

.greeting-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(
    90deg,
    #286660 0%,
    #6ca299 50%,
    #b8d2ce 100%
  );
  border-radius: 20px 20px 0 0;
}

.greeting-card:hover {
  transform: translateY(-5px);
  box-shadow: 
    0 20px 40px rgba(40, 102, 96, 0.12),
    0 8px 16px rgba(0, 0, 0, 0.05),
    inset 0 1px 0 rgba(255, 255, 255, 1);
  border-color: rgba(40, 102, 96, 0.2);
}

.greeting-content {
  padding: 24px;
}

.greeting-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
}

.greeting-text-section {
  flex: 1;
}

.greeting-text {
  font-size: 28px;
  font-weight: 700;
  background: linear-gradient(135deg, #1a202c 0%, #2d3748 50%, #286660 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0 0 8px 0;
  line-height: 1.2;
}

.greeting-subtitle {
  font-size: 16px;
  color: #64748b;
  margin: 0 0 16px 0;
  font-weight: 500;
}

.greeting-stats {
  display: flex;
  gap: 24px;
  margin-top: 16px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #286660;
  font-size: 14px;
  font-weight: 500;
}

.stat-item .q-icon {
  color: #286660;
}

.greeting-avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.doctor-avatar {
  border: 3px solid #286660;
  box-shadow: 0 4px 16px rgba(40, 102, 96, 0.2);
}

.doctor-info {
  text-align: center;
}

.doctor-specialty {
  font-size: 14px;
  font-weight: 600;
  color: #286660;
  margin-bottom: 4px;
}

.doctor-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #4caf50;
  font-weight: 500;
}

/* Dashboard Cards Section */
.dashboard-cards-section {
  padding: 0 24px 24px;
  background: transparent;
}

.dashboard-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 26px;
  margin: 0 auto;
  width: 100%;
  max-width: 1400px;
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
  min-width: 0;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
  line-height: 1.3;
  overflow-wrap: anywhere;
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

.filter-controls {
  display: flex;
  gap: 8px;
}

.status-filter .q-btn {
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #333;
  font-weight: 500;
  transition: all 0.3s ease;
}

.status-filter .q-btn:hover {
  background: rgba(255, 255, 255, 0.25);
  transform: translateY(-1px);
}

.status-filter .q-btn.active-filter {
  background: #286660;
  color: white;
  border-color: #286660;
}

.empty-state {
  text-align: center;
  padding: 48px 24px;
  color: #666;
}

.empty-state h4 {
  margin: 16px 0 8px 0;
  font-size: 18px;
  font-weight: 600;
}

.empty-state p {
  margin: 0;
  font-size: 14px;
}

/* Card-specific gradient backgrounds and colors */
.appointments-card::before {
  background: linear-gradient(90deg, #2196f3, #42a5f5, #90caf9);
}

.patients-card::before {
  background: linear-gradient(90deg, #4caf50, #66bb6a, #a5d6a7);
}

.completed-card::before {
  background: linear-gradient(90deg, #ff9800, #ffb74d, #ffcc80);
}

.assessment-card::before {
  background: linear-gradient(90deg, #9c27b0, #ba68c8, #e1bee7);
}

/* Enhanced Card Backgrounds with Medical Theme */
.appointments-card {
  background: linear-gradient(135deg, 
    rgba(33, 150, 243, 0.15) 0%, 
    rgba(66, 165, 245, 0.1) 25%,
    rgba(255, 255, 255, 0.2) 100%);
  border: 1px solid rgba(33, 150, 243, 0.3);
}

.appointments-card:hover {
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

.completed-card {
  background: linear-gradient(135deg, 
    rgba(255, 152, 0, 0.15) 0%, 
    rgba(255, 183, 77, 0.1) 25%,
    rgba(255, 255, 255, 0.2) 100%);
  border: 1px solid rgba(255, 152, 0, 0.3);
}

.completed-card:hover {
  background: linear-gradient(135deg, 
    rgba(255, 152, 0, 0.25) 0%, 
    rgba(255, 183, 77, 0.2) 25%,
    rgba(255, 255, 255, 0.3) 100%);
  border: 1px solid rgba(255, 152, 0, 0.5);
}

.assessment-card {
  background: linear-gradient(135deg, 
    rgba(156, 39, 176, 0.15) 0%, 
    rgba(186, 104, 200, 0.1) 25%,
    rgba(255, 255, 255, 0.2) 100%);
  border: 1px solid rgba(156, 39, 176, 0.3);
}

.assessment-card:hover {
  background: linear-gradient(135deg, 
    rgba(156, 39, 176, 0.25) 0%, 
    rgba(186, 104, 200, 0.2) 25%,
    rgba(255, 255, 255, 0.3) 100%);
  border: 1px solid rgba(156, 39, 176, 0.5);
}

/* Card-specific value colors with text shadows */
.appointments-card .card-value {
  color: #2196f3;
  text-shadow: 0 2px 4px rgba(33, 150, 243, 0.3);
}

.patients-card .card-value {
  color: #4caf50;
  text-shadow: 0 2px 4px rgba(76, 175, 80, 0.3);
}

.completed-card .card-value {
  color: #ff9800;
  text-shadow: 0 2px 4px rgba(255, 152, 0, 0.3);
}

.assessment-card .card-value {
  color: #9c27b0;
  text-shadow: 0 2px 4px rgba(156, 39, 176, 0.3);
}

/* Card-specific icon colors with drop shadows */
.appointments-card .card-icon {
  color: #2196f3;
  filter: drop-shadow(0 2px 4px rgba(33, 150, 243, 0.4));
}

.patients-card .card-icon {
  color: #4caf50;
  filter: drop-shadow(0 2px 4px rgba(76, 175, 80, 0.4));
}

.completed-card .card-icon {
  color: #ff9800;
  filter: drop-shadow(0 2px 4px rgba(255, 152, 0, 0.4));
}

.assessment-card .card-icon {
  color: #9c27b0;
  filter: drop-shadow(0 2px 4px rgba(156, 39, 176, 0.4));
}

/* Responsive Design */
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
    min-height: auto;
  }

  .header-top-row {
    margin-bottom: 6px;
    min-height: 36px;
  }

  .header-info {
    gap: 8px;
  }

  .header-bottom-row {
    min-height: 36px;
  }

  .search-container {
    width: 100%;
  }

  .search-input {
    font-size: 14px;
  }

  .search-input .q-field__control {
    min-height: 36px;
  }

  .time-display {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .time-text {
    font-size: 12px;
    font-weight: 500;
  }

  .weather-display {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .weather-text {
    font-size: 11px;
  }

  .weather-location {
    font-size: 10px;
  }

  .notification-btn {
    padding: 4px;
    min-width: 32px;
    min-height: 32px;
  }

  .menu-toggle-btn {
    padding: 4px;
    min-width: 32px;
    min-height: 32px;
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
  }

  .additional-cards-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
  }

  .greeting-main {
    flex-direction: column;
    text-align: center;
    gap: 16px;
  }

  .greeting-stats {
    justify-content: center;
    gap: 16px;
  }

  .greeting-text {
    font-size: 24px;
  }

  .greeting-subtitle {
    font-size: 14px;
  }

  .card-content {
    padding: 20px;
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .card-title {
    font-size: 16px;
  }

  .card-description {
    font-size: 13px;
  }

  .card-value {
    font-size: 28px;
    align-self: flex-end;
  }

  .card-icon {
    margin-left: 0;
    align-self: flex-end;
  }

  /* Enhanced mobile card styling */
  .dashboard-card {
    min-height: 200px;
    border-radius: 20px;
  }

  .dashboard-card:hover {
    transform: translateY(-4px) scale(1.01);
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
  }

  .card-title {
    font-size: 16px;
  }

  .card-description {
    font-size: 12px;
  }

  .card-value {
    font-size: 24px;
  }

  .dashboard-card {
    min-height: 160px;
    border-radius: 16px;
  }

  .upcoming-appointments-section {
    margin: 16px 12px;
  }

  .upcoming-appointments-section .q-card {
    border-radius: 20px;
  }

  .section-header {
    padding: 20px 16px 12px 16px;
  }

  .section-title {
    font-size: 18px;
  }

  .appointment-card {
    margin: 6px 12px;
    border-radius: 12px;
  }
}

@media (max-width: 480px) {
  .prototype-header {
    padding-top: max(env(safe-area-inset-top), 12px);
  }

  .mobile-header-layout {
    padding: 6px 8px;
    padding-top: max(env(safe-area-inset-top), 8px);
  }

  .header-top-row {
    margin-bottom: 4px;
    min-height: 32px;
  }

  .header-info {
    gap: 6px;
  }

  .header-bottom-row {
    min-height: 32px;
  }

  .header-left {
    flex: 1;
    min-width: 0;
  }

  .header-right {
    gap: 6px;
    flex-shrink: 0;
  }

  .search-container {
    max-width: 100%;
    width: 100%;
  }

  .search-input {
    font-size: 12px;
  }

  .search-input .q-field__control {
    min-height: 32px;
  }

  .time-display {
    display: none;
  }

  .weather-display {
    flex-direction: column;
    align-items: center;
    gap: 1px;
  }

  .weather-text {
    font-size: 10px;
  }

  .weather-location {
    font-size: 9px;
  }

  .time-pill,
  .weather-pill,
  .location-pill {
    font-size: 9px;
    padding: 1px 3px;
  }

  .notification-btn {
    padding: 2px;
    min-width: 32px;
    min-height: 32px;
  }

  .menu-toggle-btn {
    padding: 2px;
    min-width: 32px;
    min-height: 32px;
  }

  .greeting-section {
    padding: 12px;
  }

  .greeting-content {
    padding: 16px;
  }

  .dashboard-cards-section {
    padding: 12px;
  }

  .dashboard-cards-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }



  .greeting-stats {
    flex-direction: column;
    align-items: center;
    gap: 12px;
  }

  .greeting-text {
    font-size: 20px;
  }

  .greeting-subtitle {
    font-size: 13px;
  }

  .card-content {
    padding: 16px;
  }

  .card-title {
    font-size: 15px;
  }

  .card-description {
    font-size: 12px;
  }

  .card-value {
    font-size: 24px;
  }

  .notification-btn {
    padding: 8px;
  }

  .menu-toggle-btn {
    padding: 8px;
  }
}

/* Profile avatar styles removed from greeting card */

/* Modal Styles */
.modal-card {
  min-width: 800px;
  max-width: 90vw;
  border-radius: 12px;
}

.modal-header {
  display: flex;
  align-items: center;
  padding-bottom: 0;
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
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

.notification-modal {
  width: 400px;
  max-width: 90vw;
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

/* Mobile Modal Styles */
@media (max-width: 768px) {
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

  .modal-header {
    padding: 16px;
    padding-bottom: 0;
  }

  .modal-title {
    font-size: 16px;
  }

  .modal-close-btn {
    padding: 8px !important;
    min-width: 44px !important;
    min-height: 44px !important;
    font-size: 20px !important;
    background: rgba(255, 255, 255, 0.25) !important;
    border-radius: 50% !important;
    color: white !important;
  }

  .modal-close-btn:hover {
    background: rgba(255, 255, 255, 0.3) !important;
  }

  .notification-modal {
    width: 100%;
    max-width: 100%;
  }

  .q-card__section {
    padding: 16px;
  }

  .q-item {
    padding: 12px 12px;
    min-height: 72px;
    border-bottom: 1px solid rgba(0, 0, 0, 0.08);
    transition: background-color 0.2s ease;
  }

  .q-item:hover {
    background-color: rgba(40, 102, 96, 0.04);
  }

  .q-item:last-child {
    border-bottom: none;
  }

  .q-item__section--avatar {
    min-width: 48px;
    padding-right: 12px;
  }

  .q-avatar {
    width: 40px;
    height: 40px;
    font-size: 16px;
    font-weight: 600;
  }

  .q-item__section--main {
    flex: 1;
    min-width: 0;
  }

  .q-item__label {
    font-size: 16px;
    font-weight: 600;
    color: #333;
    line-height: 1.3;
    margin-bottom: 4px;
  }

  .q-item__label--caption {
    font-size: 13px;
    color: #666;
    line-height: 1.3;
    margin-bottom: 2px;
  }

  .q-item__section--side {
    padding-left: 12px;
    align-items: flex-start;
    padding-top: 4px;
  }

  .q-chip {
    font-size: 12px;
    padding: 6px 12px;
    border-radius: 16px;
    font-weight: 500;
    min-height: 28px;
  }

  /* Empty state styling */
  .text-center.q-pa-md.text-grey-6 {
    padding: 40px 20px !important;
    font-size: 16px;
    color: #999 !important;
    background: rgba(0, 0, 0, 0.02);
    border-radius: 12px;
    margin: 16px;
  }
}

@media (max-width: 480px) {
  .modal-card {
    width: 100%;
    max-width: 100%;
    margin: 0;
    border-radius: 12px;
    max-height: calc(
      100vh - max(env(safe-area-inset-top), 24px) - max(env(safe-area-inset-bottom), 4px)
    );
    overflow-y: auto;
  }

  .modal-header {
    padding: 16px 12px 12px;
    border-radius: 12px 12px 0 0;
  }

  .modal-title {
    font-size: 16px;
    font-weight: 600;
  }

  .modal-close-btn {
    padding: 10px !important;
    min-width: 48px !important;
    min-height: 48px !important;
    font-size: 22px !important;
    background: rgba(255, 255, 255, 0.25) !important;
    border-radius: 50% !important;
  }

  .modal-close-btn:hover {
    background: rgba(255, 255, 255, 0.3) !important;
  }

  .notification-modal {
    width: 100%;
    max-width: 100%;
  }

  .q-card__section {
    padding: 12px;
  }

  .q-item {
    padding: 12px 8px;
    min-height: 64px;
  }

  .q-item__section--avatar {
    min-width: 44px;
    padding-right: 10px;
  }

  .q-avatar {
    width: 36px;
    height: 36px;
    font-size: 14px;
  }

  .q-item__label {
    font-size: 15px;
    margin-bottom: 3px;
  }

  .q-item__label--caption {
    font-size: 12px;
    margin-bottom: 1px;
  }

  .q-item__section--side {
    padding-left: 8px;
  }

  .q-chip {
    font-size: 11px;
    padding: 4px 10px;
    border-radius: 14px;
    min-height: 24px;
  }

  /* Empty state styling */
  .text-center.q-pa-md.text-grey-6 {
    padding: 32px 16px !important;
    font-size: 15px;
    margin: 12px;
  }
}

@media (max-width: 360px) {
  .modal-card {
    border-radius: 8px;
    max-height: calc(
      100vh - max(env(safe-area-inset-top), 20px) - max(env(safe-area-inset-bottom), 4px)
    );
  }

  .modal-header {
    padding: 12px 8px 8px;
    border-radius: 8px 8px 0 0;
  }

  .modal-title {
    font-size: 15px;
    line-height: 1.2;
  }

  .modal-close-btn {
    padding: 8px !important;
    min-width: 44px !important;
    min-height: 44px !important;
    font-size: 20px !important;
  }

  .q-card__section {
    padding: 8px;
  }

  .q-item {
    padding: 10px 6px;
    min-height: 60px;
  }

  .q-item__section--avatar {
    min-width: 40px;
    padding-right: 8px;
  }

  .q-avatar {
    width: 32px;
    height: 32px;
    font-size: 13px;
  }

  .q-item__label {
    font-size: 14px;
    line-height: 1.2;
  }

  .q-item__label--caption {
    font-size: 11px;
    line-height: 1.2;
  }

  .q-item__section--side {
    padding-left: 6px;
  }

  .q-chip {
    font-size: 10px;
    padding: 3px 8px;
    border-radius: 12px;
    min-height: 22px;
  }

  /* Empty state styling */
  .text-center.q-pa-md.text-grey-6 {
    padding: 24px 12px !important;
    font-size: 14px;
    margin: 8px;
  }
}

/* Appointment status colors for better mobile visibility */
.q-chip[color="primary"] {
  background: #2196f3 !important;
  color: white !important;
}

.q-chip[color="orange"] {
  background: #ff9800 !important;
  color: white !important;
}

.q-chip[color="purple"] {
  background: #9c27b0 !important;
  color: white !important;
}

.q-chip[color="green"] {
  background: #4caf50 !important;
  color: white !important;
}

.q-chip[color="red"] {
  background: #f44336 !important;
  color: white !important;
}

/* Loading spinner in modals */
.q-spinner {
  margin: 20px auto;
  display: block;
}

@media (max-width: 480px) {
  .q-spinner {
    margin: 16px auto;
  }
}

/* Upcoming Appointments Section - Enhanced Design */
.upcoming-appointments-section .q-card {
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
}

.upcoming-appointments-section .q-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #286660, #6ca299, #b8d2ce);
  border-radius: 24px 24px 0 0;
  opacity: 1;
}

.section-header {
  padding: 24px 24px 16px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.1);
}

.section-title {
  font-size: 20px;
  font-weight: 700;
  color: #333;
  margin: 0;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.appointment-card {
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(15px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 16px;
  margin: 8px 16px;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  position: relative;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
}

.appointment-card:hover {
  transform: translateY(-4px) scale(1.01);
  box-shadow: 
    0 12px 32px rgba(0, 0, 0, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.4);
  background: rgba(255, 255, 255, 0.3);
}

.appointment-card .q-item-section--avatar .q-avatar {
  border: 2px solid rgba(40, 102, 96, 0.3);
  box-shadow: 0 2px 8px rgba(40, 102, 96, 0.2);
}

.appointment-card .q-chip {
  background: linear-gradient(135deg, 
    rgba(40, 102, 96, 0.15) 0%, 
    rgba(255, 255, 255, 0.2) 100%) !important;
  color: #286660 !important;
  border: 1px solid rgba(40, 102, 96, 0.3);
  backdrop-filter: blur(10px);
  font-weight: 600;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.appointment-card .q-btn {
  background: linear-gradient(135deg, 
    rgba(40, 102, 96, 0.15) 0%, 
    rgba(255, 255, 255, 0.2) 100%);
  color: #286660;
  border: 1px solid rgba(40, 102, 96, 0.3);
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
  font-weight: 600;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.appointment-card .q-btn:hover {
  background: linear-gradient(135deg, #286660, #3d8b7c);
  color: white;
  border-color: #286660;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(40, 102, 96, 0.3);
}

/* Notification styles */
.unread {
  background-color: rgba(25, 118, 210, 0.05);
  border-left: 3px solid #1976d2;
}

.unread .q-item-label {
  font-weight: 600;
}

.doctor-dashboard-shell {
  max-width: 1120px;
  margin: 0 auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.greeting-section {
  padding: 0;
}

.greeting-card {
  border-radius: 12px;
  min-height: auto;
}

.greeting-content {
  padding: 18px 20px;
}

.dashboard-cards-section {
  padding: 0;
}

.dashboard-cards-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  max-width: none;
}

.dashboard-card {
  border-radius: 12px;
  min-height: 0;
}

.dashboard-card .q-card__section {
  padding: 14px;
}

.card-content {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
}

.card-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.card-icon .q-icon {
  font-size: 18px !important;
}

.card-text {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.card-title {
  font-size: 12px;
  line-height: 1.2;
}

.card-value {
  font-size: 22px;
  font-weight: 700;
  line-height: 1;
}

.card-description {
  font-size: 11px;
  line-height: 1.3;
}

.dashboard-main-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr);
  gap: 16px;
  align-items: start;
}

.calendar-section {
  min-width: 0;
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
  color: rgba(15, 23, 42, 0.7);
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
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 10px;
  overflow: hidden;
  box-shadow: none;
}

.calendar-row {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
}

.calendar-cell {
  min-height: 86px;
  padding: 8px 8px 10px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: #ffffff;
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
  color: rgba(15, 23, 42, 0.6);
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
}

.calendar-cell.today {
  border-color: rgba(13, 148, 136, 0.35);
}

.calendar-cell.selected {
  background: rgba(245, 158, 11, 0.1);
  border-color: rgba(245, 158, 11, 0.25);
}

.calendar-cell.blocked {
  border-color: rgba(245, 158, 11, 0.25);
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
  border: 1px solid rgba(13, 148, 136, 0.1);
  border-left: 3px solid rgba(13, 148, 136, 0.85);
  background: rgba(13, 148, 136, 0.1);
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

.upcoming-appointments-section {
  margin: 0;
  padding: 0;
  min-width: 0;
}

.upcoming-appointments-section .q-card {
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
  overflow: hidden;
}

.section-header {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
  padding: 12px 16px;
}

.section-header-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.section-title {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  line-height: 1.2;
}

.appointments-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.appointments-search {
  min-width: 260px;
}

.appointments-action-btn {
  border-radius: 10px;
  font-weight: 700;
  text-transform: none;
}

.filter-controls {
  display: flex;
  align-items: center;
}

.status-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.status-filter .q-btn {
  min-height: 28px;
  padding: 0 10px;
  border-radius: 8px;
}

.appointments-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.appointment-row {
  padding: 12px 14px;
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: start;
  column-gap: 12px;
  row-gap: 10px;
  border-radius: 8px;
  border: 1px solid rgba(13, 148, 136, 0.12);
  border-left: 4px solid rgba(13, 148, 136, 0.85);
  background: rgba(13, 148, 136, 0.06);
  transition: background-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
}

.appointment-row + .appointment-row {
  border-top: 0;
}

.appointment-row:hover {
  background: rgba(13, 148, 136, 0.1);
}

.appointment-row:focus-visible {
  outline: 2px solid rgba(13, 148, 136, 0.85);
  outline-offset: 2px;
  background: rgba(13, 148, 136, 0.12);
}

.appointment-entry {
  min-width: 0;
}

.appointment-title-row {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.appointment-title-text {
  font-size: 13px;
  font-weight: 800;
  line-height: 1.2;
  color: rgba(15, 23, 42, 0.92);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.appointment-title-badge {
  flex: 0 0 auto;
}

.appointment-datetime-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
  color: rgba(15, 23, 42, 0.72);
}

.appointment-datetime-main {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  white-space: nowrap;
}

.appointment-datetime-text {
  white-space: nowrap;
}

.appointment-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  justify-content: flex-end;
  align-self: start;
}

.appointment-actions .q-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
}

@media (max-width: 900px) {
  .appointment-row {
    grid-template-columns: 1fr auto;
    grid-template-rows: auto auto;
  }

  .appointment-actions {
    grid-column: 1 / -1;
    justify-content: flex-start;
  }
}

@media (max-width: 600px) {
  .appointment-row {
    grid-template-columns: 1fr;
  }
}

.schedules-card,
.cancelled-card,
.rescheduled-card,
.assessment-card {
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.25);
}

.schedules-card::before,
.cancelled-card::before,
.rescheduled-card::before,
.assessment-card::before {
  background: linear-gradient(90deg, #286660, #6ca299, #b8d2ce);
}

.assessment-card .card-value,
.assessment-card .card-icon {
  color: #286660;
  text-shadow: none;
  filter: none;
}

@media (max-width: 1024px) {
  .dashboard-cards-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .dashboard-main-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .appointments-search {
    min-width: 100%;
  }

  .calendar-grid {
    overflow-x: auto;
  }

  .calendar-row {
    min-width: 720px;
  }
}

@media (max-width: 600px) {
  .doctor-dashboard-shell {
    padding: 12px;
    gap: 12px;
  }

  .dashboard-cards-grid {
    grid-template-columns: 1fr;
  }

  .section-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .appointment-actions {
    width: 100%;
    justify-content: flex-start;
    align-self: stretch;
  }
}


</style>
