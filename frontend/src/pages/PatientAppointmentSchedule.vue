<template>
  <q-layout view="lHh Lpr lFf">
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
      <q-page class="patient-bg q-pa-md pb-safe">
        <div class="max-w-4xl mx-auto">
          <!-- Schedule New Appointment Section -->
          <q-card class="q-mb-md" flat bordered>
            <q-card-section class="row items-center">
              <q-avatar size="48px" color="teal" text-color="white" icon="add" />
              
              <div class="col q-ml-md">
                <div class="text-h6 text-teal-8">Schedule New Appointment</div>
                <div>Book your next medical appointment</div>
              </div>
              
              <q-btn 
                unelevated 
                color="teal" 
                label="Book Now" 
                icon-right="arrow_forward"
                @click="showScheduleForm = true"
              />
            </q-card-section>
          </q-card>

          <!-- Appointment Management Tabs -->
          <q-card>
            <q-tabs
              v-model="activeTab"
              dense
              active-color="primary"
              indicator-color="primary"
              align="left"
            >
              <q-tab name="scheduled" label="UPCOMING" />
              <q-tab name="rescheduled" label="RESCHEDULED" />
              <q-tab name="cancelled" label="CANCELLED" />
              <q-tab name="completed" label="COMPLETED" />
            </q-tabs>

            <q-separator />

            <!-- Search Bar -->
            <q-card-section class="q-pb-none">
              <q-input
                v-model="searchQuery"
                placeholder="Search appointments..."
                dense
                outlined
                clearable
              >
                <template #prepend>
                  <q-icon name="search" />
                </template>
              </q-input>
            </q-card-section>

            <!-- Tab Content -->
            <q-card-section>
              <q-tab-panels v-model="activeTab" animated>
                <!-- Scheduled Appointments -->
                <q-tab-panel name="scheduled">
                  <div class="text-h6 q-mb-md">Upcoming Appointments</div>
                  <div v-if="filteredScheduledAppointments.length === 0" class="text-center q-pa-xl">
                    <q-icon name="event_busy" size="64px" color="grey-5" />
                    <div class="text-h6 q-mt-md">No upcoming appointments</div>
                    <div class="text-caption">Schedule your first appointment to get started</div>
                  </div>
                  <div v-else class="row q-gutter-md">
                    <div
                      v-for="appointment in filteredScheduledAppointments"
                      :key="appointment.id"
                      class="col-12 col-md-6 col-lg-4"
                    >
                      <q-card class="appointment-card">
                        <q-card-section>
                          <div class="row items-center q-mb-sm">
                            <q-avatar color="primary" text-color="white" icon="medical_services" class="q-mr-sm" />
                            <div class="col">
                              <div class="text-weight-bold">{{ appointment.doctor_name || 'Assigned Doctor' }}</div>
                              <div class="text-caption">{{ appointment.department }}</div>
                            </div>
                            <q-badge color="green" label="Scheduled" />
                          </div>
                          <q-separator class="q-mb-sm" />
                          <div class="text-body2">
                            <div class="row q-mb-xs">
                              <q-icon name="event" size="16px" class="q-mr-xs" />
                              <span>{{ formatDate(appointment.appointment_date) }}</span>
                            </div>
                            <div class="row q-mb-xs">
                              <q-icon name="access_time" size="16px" class="q-mr-xs" />
                              <span>{{ formatHHMM(appointment.appointment_time) }}</span>
                            </div>
                            <div class="row q-mb-xs">
                              <q-icon name="category" size="16px" class="q-mr-xs" />
                              <span>{{ appointment.type }}</span>
                            </div>
                            <div v-if="appointment.reason" class="row">
                              <q-icon name="description" size="16px" class="q-mr-xs" />
                              <span class="text-caption">{{ appointment.reason }}</span>
                            </div>
                          </div>
                        </q-card-section>
                        <q-card-actions align="right">
                          <q-btn flat color="primary" label="Reschedule" @click="rescheduleAppointment(appointment)" />
                          <q-btn flat color="negative" label="Cancel" @click="showCancelModal(appointment)" />
                        </q-card-actions>
                      </q-card>
                    </div>
                  </div>
                </q-tab-panel>

                <!-- Rescheduled Appointments -->
                <q-tab-panel name="rescheduled">
                  <div class="text-h6 q-mb-md">Rescheduled Appointments</div>
                  <div v-if="filteredRescheduledAppointments.length === 0" class="text-center q-pa-xl">
                    <q-icon name="update" size="64px" color="grey-5" />
                    <div class="text-h6 q-mt-md">No rescheduled appointments</div>
                    <div class="text-caption">Appointments that have been modified will appear here</div>
                  </div>
                  <div v-else class="row q-gutter-md">
                    <div
                      v-for="appointment in filteredRescheduledAppointments"
                      :key="appointment.id"
                      class="col-12 col-md-6 col-lg-4"
                    >
                      <q-card class="appointment-card">
                        <q-card-section>
                          <div class="row items-center q-mb-sm">
                            <q-avatar color="orange" text-color="white" icon="update" class="q-mr-sm" />
                            <div class="col">
                              <div class="text-weight-bold">{{ appointment.doctor_name || 'Assigned Doctor' }}</div>
                              <div class="text-caption">{{ appointment.department }}</div>
                            </div>
                            <q-badge color="orange" label="Rescheduled" />
                          </div>
                          <q-separator class="q-mb-sm" />
                          <div class="text-body2">
                            <div class="row q-mb-xs">
                              <q-icon name="event" size="16px" class="q-mr-xs" />
                              <span>{{ formatDate(appointment.appointment_date) }}</span>
                            </div>
                            <div class="row q-mb-xs">
                              <q-icon name="access_time" size="16px" class="q-mr-xs" />
                              <span>{{ formatHHMM(appointment.appointment_time) }}</span>
                            </div>
                            <div class="row q-mb-xs">
                              <q-icon name="category" size="16px" class="q-mr-xs" />
                              <span>{{ appointment.type }}</span>
                            </div>
                            <div v-if="appointment.reschedule_reason" class="row">
                              <q-icon name="info" size="16px" class="q-mr-xs" />
                              <span class="text-caption">{{ appointment.reschedule_reason }}</span>
                            </div>
                          </div>
                        </q-card-section>
                        <q-card-actions align="right">
                          <q-btn flat color="primary" label="Reschedule Again" @click="rescheduleAppointment(appointment)" />
                          <q-btn flat color="negative" label="Cancel" @click="showCancelModal(appointment)" />
                        </q-card-actions>
                      </q-card>
                    </div>
                  </div>
                </q-tab-panel>

                <!-- Cancelled Appointments -->
                <q-tab-panel name="cancelled">
                  <div class="text-h6 q-mb-md">Cancelled Appointments</div>
                  <div v-if="filteredCancelledAppointments.length === 0" class="text-center q-pa-xl">
                    <q-icon name="cancel" size="64px" color="grey-5" />
                    <div class="text-h6 q-mt-md">No cancelled appointments</div>
                    <div class="text-caption">Cancelled appointments will be archived here</div>
                  </div>
                  <div v-else class="row q-gutter-md">
                    <div
                      v-for="appointment in filteredCancelledAppointments"
                      :key="appointment.id"
                      class="col-12 col-md-6 col-lg-4"
                    >
                      <q-card class="appointment-card cancelled-card">
                        <q-card-section>
                          <div class="row items-center q-mb-sm">
                            <q-avatar color="grey" text-color="white" icon="cancel" class="q-mr-sm" />
                            <div class="col">
                              <div class="text-weight-bold">{{ appointment.doctor_name || 'Assigned Doctor' }}</div>
                              <div class="text-caption">{{ appointment.department }}</div>
                            </div>
                            <q-badge color="grey" label="Cancelled" />
                          </div>
                          <q-separator class="q-mb-sm" />
                          <div class="text-body2">
                            <div class="row q-mb-xs">
                              <q-icon name="event" size="16px" class="q-mr-xs" />
                              <span>{{ formatDate(appointment.appointment_date) }}</span>
                            </div>
                            <div class="row q-mb-xs">
                              <q-icon name="access_time" size="16px" class="q-mr-xs" />
                              <span>{{ formatHHMM(appointment.appointment_time) }}</span>
                            </div>
                            <div class="row q-mb-xs">
                              <q-icon name="category" size="16px" class="q-mr-xs" />
                              <span>{{ appointment.type }}</span>
                            </div>
                            <div v-if="appointment.cancellation_reason" class="row">
                              <q-icon name="info" size="16px" class="q-mr-xs" />
                              <span class="text-caption">{{ appointment.cancellation_reason }}</span>
                            </div>
                          </div>
                        </q-card-section>
                        <q-card-actions align="right">
                          <q-btn flat color="primary" label="Reschedule" @click="rescheduleAppointment(appointment)" />
                        </q-card-actions>
                      </q-card>
                    </div>
                  </div>
                </q-tab-panel>

                <!-- Completed Appointments -->
                <q-tab-panel name="completed">
                  <div class="text-h6 q-mb-md">Completed Appointments</div>
                  <div v-if="filteredCompletedAppointments.length === 0" class="text-center q-pa-xl">
                    <q-icon name="task_alt" size="64px" color="grey-5" />
                    <div class="text-h6 q-mt-md">No completed appointments</div>
                    <div class="text-caption">Completed consultations will appear here</div>
                  </div>
                  <div v-else class="row q-gutter-md">
                    <div
                      v-for="appointment in filteredCompletedAppointments"
                      :key="appointment.id"
                      class="col-12 col-md-6 col-lg-4"
                    >
                      <q-card class="appointment-card completed-card">
                        <q-card-section>
                          <div class="row items-center q-mb-sm">
                            <q-avatar color="green" text-color="white" icon="check_circle" class="q-mr-sm" />
                            <div class="col">
                              <div class="text-weight-bold">{{ appointment.doctor_name || 'Assigned Doctor' }}</div>
                              <div class="text-caption">{{ appointment.department }}</div>
                            </div>
                            <q-badge color="green" label="Completed" />
                          </div>
                          <q-separator class="q-mb-sm" />
                          <div class="text-body2">
                            <div class="row q-mb-xs">
                              <q-icon name="event" size="16px" class="q-mr-xs" />
                              <span>
                                {{ appointment.consultation_finished_at ? formatDate(appointment.consultation_finished_at) : formatDate(appointment.appointment_date) }}
                              </span>
                            </div>
                            <div class="row q-mb-xs">
                              <q-icon name="access_time" size="16px" class="q-mr-xs" />
                              <span>
                                {{ appointment.consultation_finished_at ? formatTime(appointment.consultation_finished_at) : appointment.appointment_time }}
                              </span>
                            </div>
                            <div class="row q-mb-xs">
                              <q-icon name="category" size="16px" class="q-mr-xs" />
                              <span>{{ appointment.type }}</span>
                            </div>
                          </div>
                        </q-card-section>

                      </q-card>
                    </div>
                  </div>
                </q-tab-panel>
              </q-tab-panels>
            </q-card-section>
          </q-card>
        </div>
      </q-page>
    </q-page-container>

    <!-- Schedule New Appointment Dialog -->
    <q-dialog v-model="showScheduleForm" persistent :maximized="$q.screen.lt.md">
      <q-card class="dialog-card">
        <q-card-section class="row items-center">
          <q-avatar color="primary" text-color="white" icon="event_available" size="48px" class="q-mr-md" />
          <div>
            <div class="text-h6 text-weight-bold">Schedule New Appointment</div>
                    <div class="text-caption">Please fill out all the required information</div>
          </div>
        </q-card-section>

        <q-separator />

        <q-form ref="formRef" @submit="onSubmit" class="q-gutter-md q-pa-md">
          <!-- Appointment Type -->
          <q-select 
            v-model="form.type" 
            :options="typeOptions" 
            label="Appointment Type" 
            emit-value 
            map-options 
            :rules="[val => !!val || 'Type is required']"
            outlined
            color="primary"
            behavior="menu"
          />

          <!-- Department -->
          <q-select 
            v-model="form.department" 
            :options="departmentOptions" 
            label="Department" 
            emit-value 
            map-options 
            :rules="[val => !!val || 'Department is required']"
            outlined
            color="primary"
            behavior="menu"
          />

          <!-- Doctor Selection -->
          <q-select
            v-model="selectedDoctorId"
            :options="doctorOptions"
            label="Select Doctor (optional)"
            emit-value
            map-options
            outlined
            color="primary"
            behavior="menu"
            :loading="doctorLoading"
            :disable="!form.department"
            :hint="form.department && doctorOptions.length === 0 ? 'No verified doctors available in this department' : doctorOptions.length > 0 ? `${doctorOptions.length} verified doctor(s) available` : 'Select department to see verified doctors'"
          >
            <template #option="{ opt, selected, itemProps, toggleOption }">
              <q-item v-bind="itemProps" @click="toggleOption(opt)" :active="selected">
                <q-item-section avatar>
                  <q-avatar size="28px" color="primary" text-color="white">
                    <q-icon name="medical_services" />
                  </q-avatar>
                </q-item-section>
                <q-item-section>
                  <q-item-label>{{ opt.label }}</q-item-label>
                  <q-item-label caption>{{ opt.detail }}</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <div class="column items-end">
                    <q-badge :color="opt.isAvailable ? 'green' : 'grey'" :label="opt.isAvailable ? 'Available' : 'Unavailable'" />
                    <q-badge color="blue" label="Verified" size="xs" class="q-mt-xs" />
                  </div>
                </q-item-section>
              </q-item>
            </template>
          </q-select>

          <!-- Date and Time Row -->
          <div class="row q-gutter-md">
            <!-- Date -->
            <div class="col-12 col-md-6">
              <q-input 
                v-model="form.date" 
                label="Date (mm/dd/yyyy)"
                mask="##/##/####"
                placeholder="MM/DD/YYYY"
                :rules="[val => !!val || 'Date is required', val => validateDate(val) || 'Please enter a valid date']"
                outlined
                color="primary"
              >
                <template #append>
                  <q-icon name="event" class="cursor-pointer">
                    <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                      <q-date v-model="form.date" mask="MM/DD/YYYY" color="primary" today-btn minimal>
                        <div class="row items-center justify-end">
                          <q-btn v-close-popup label="Close" color="primary" flat />
                        </div>
                      </q-date>
                    </q-popup-proxy>
                  </q-icon>
                </template>
              </q-input>
            </div>

            <!-- Time -->
            <div class="col-12 col-md-6">
              <q-input
                v-model="form.time"
                label="Time (24-hour format)"
                mask="##:##"
                placeholder="HH:MM"
                :rules="[val => !!val || 'Time is required', val => validateTime(val) || 'Please enter a valid time']"
                outlined
                color="primary"
              >
                <template #append>
                  <q-icon name="access_time" class="cursor-pointer">
                    <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                      <q-time v-model="form.time" mask="HH:mm" format24h>
                        <div class="row items-center justify-end">
                          <q-btn v-close-popup label="Close" color="primary" flat />
                        </div>
                      </q-time>
                    </q-popup-proxy>
                  </q-icon>
                </template>
              </q-input>
            </div>
          </div>

          <!-- Reason -->
          <q-input 
            v-model="form.reason" 
            label="Reason for Appointment" 
            type="textarea" 
            :rules="[val => !!val || 'Reason is required']"
            outlined
            color="primary"
            rows="3"
            autogrow
            placeholder="Please describe the reason for your appointment"
          />
        </q-form>

        <q-separator />

        <q-card-actions align="right" class="q-pa-md">
          <q-btn flat color="grey-7" label="Cancel" @click="closeScheduleForm" />
          <q-btn 
            color="primary" 
            :label="isReschedule ? 'Reschedule Appointment' : 'Schedule Appointment'"
            @click="onSubmit"
            :loading="scheduling"
            unelevated
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Cancellation Confirmation Modal -->
    <q-dialog v-model="showCancelDialog">
      <q-card class="cancel-card">
        <q-btn
          flat
          round
          dense
          icon="close"
          aria-label="Close"
          class="absolute-top-right q-ma-sm"
          @click="closeCancelDialog"
        />
        <q-card-section class="text-center">
          <q-icon name="warning" size="64px" color="orange" class="q-mb-md" />
          <div class="text-h6 text-weight-bold">Cancel Appointment</div>
          <div class="text-caption">Are you sure you want to cancel this appointment?</div>
        </q-card-section>

        <q-card-section v-if="selectedAppointment">
          <q-card flat bordered class="q-pa-md">
            <div class="text-body2">
              <div class="row q-mb-sm">
                <q-icon name="medical_services" size="16px" class="q-mr-sm" />
                <span class="text-weight-bold">{{ selectedAppointment.doctor_name || 'Assigned Doctor' }}</span>
              </div>
              <div class="row q-mb-sm">
                <q-icon name="event" size="16px" class="q-mr-sm" />
                <span>{{ formatDate(selectedAppointment.appointment_date) }}</span>
              </div>
              <div class="row q-mb-sm">
                <q-icon name="access_time" size="16px" class="q-mr-sm" />
                <span>{{ formatHHMM(selectedAppointment.appointment_time) }}</span>
              </div>
              <div class="row">
                <q-icon name="category" size="16px" class="q-mr-sm" />
                <span>{{ selectedAppointment.type }}</span>
              </div>
            </div>
          </q-card>
        </q-card-section>

        <q-card-section>
          <q-input
            v-model="cancellationReason"
            label="Reason for cancellation (optional)"
            type="textarea"
            outlined
            rows="2"
            placeholder="Please let us know why you're cancelling..."
          />
        </q-card-section>

        <q-separator />

        <q-card-actions class="q-pa-md">
          <div class="row q-col-gutter-sm full-width">
            <div class="col-6">
              <q-btn color="orange" label="Reschedule Instead" @click="rescheduleFromCancel" unelevated class="full-width" />
            </div>
            <div class="col-6">
              <q-btn color="negative" label="Confirm Cancellation" @click="confirmCancellation" :loading="cancelling" unelevated class="full-width" />
            </div>
          </div>
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Duplicate Appointment Warning -->
    <q-dialog v-model="showDuplicateWarning" :maximized="$q.screen.lt.md">
      <q-card class="dialog-card-sm">
        <q-card-section class="text-center">
          <q-icon name="warning" size="48px" color="orange" class="q-mb-md" />
          <div class="text-h6 text-weight-bold">Time Slot Not Available</div>
          <div class="text-body2">This time slot is not available. Please choose another time.</div>
        </q-card-section>
        <q-card-actions align="center" class="q-pa-md">
          <q-btn color="primary" label="Choose Different Time" @click="showDuplicateWarning = false" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Success Notification -->
    <q-dialog v-model="showSuccessDialog">
      <q-card class="success-card">
        <q-card-section class="text-center">
          <q-icon name="check_circle" size="48px" color="green" class="q-mb-md" />
          <div class="text-h6 text-weight-bold">{{ successMessage }}</div>
        </q-card-section>
        <q-card-actions align="center" class="q-pa-md">
          <q-btn color="primary" label="OK" @click="showSuccessDialog = false" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <PatientBottomNav />
  </q-layout>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'

import { useQuasar } from 'quasar'
import { api } from 'src/boot/axios'
import logoUrl from 'src/assets/logo.png'
import PatientBottomNav from 'src/components/PatientBottomNav.vue'

// TypeScript interfaces
interface Appointment {
  appointment_id: number
  id: number
  patient_name: string
  doctor_name: string
  doctor_id: number
  department: string
  appointment_date: string
  appointment_time: string
  status: 'scheduled' | 'rescheduled' | 'cancelled' | 'completed' | 'no_show'
  appointment_type: string
  type: string
  reason: string
  cancellation_reason?: string | null
  reschedule_reason?: string | null
  consultation_finished_at?: string | null
}

interface DoctorOption {
  label: string
  value: string
  detail?: string
  isAvailable?: boolean
  currentPatients?: number
  verification_status?: string | undefined
  is_verified?: boolean | undefined
}

const router = useRouter()
const $q = useQuasar()
const formRef = ref()
const showUserMenu = ref(false)
const unreadCount = ref<number>(0)

// Appointment management state
const activeTab = ref('scheduled')
const searchQuery = ref('')
const showScheduleForm = ref(false)
const showCancelDialog = ref(false)
const showDuplicateWarning = ref(false)
const showSuccessDialog = ref(false)
const selectedAppointment = ref<Appointment | null>(null)
const cancellationReason = ref('')
const scheduling = ref(false)
const cancelling = ref(false)
const successMessage = ref('')
const isReschedule = ref(false)
const rescheduleAppointmentId = ref<number | null>(null)

// User data
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

// Form data
const form = ref({
  type: '',
  department: '',
  date: '',
  time: '',
  reason: ''
})

// Doctor selection state
const doctorOptions = ref<DoctorOption[]>([])
const selectedDoctorId = ref<string>('')
const doctorLoading = ref(false)

// Appointments data
const appointments = ref<Appointment[]>([])

// Options
const typeOptions = [
  { label: 'General Consultation', value: 'general-consultation' },
  { label: 'Follow-up Visit', value: 'follow-up' },
  { label: 'Lab Test', value: 'lab-test' },
  { label: 'Specialist Consultation', value: 'specialist-consultation' },
  { label: 'Emergency Visit', value: 'emergency' },
  { label: 'Vaccination', value: 'vaccination' },
  { label: 'Physical Examination', value: 'physical-exam' },
  { label: 'Mental Health Consultation', value: 'mental-health' }
]

import { departmentOptions as sharedDepartmentOptions } from '../utils/departments'
import type { DepartmentOption } from '../utils/departments'
const departmentOptions = ref<DepartmentOption[]>(sharedDepartmentOptions)

// Computed properties for filtered appointments
const scheduledAppointments = computed(() => 
  appointments.value.filter(apt => apt.status === 'scheduled')
)

const rescheduledAppointments = computed(() => 
  appointments.value.filter(apt => apt.status === 'rescheduled')
)

const cancelledAppointments = computed(() => 
  appointments.value.filter(apt => apt.status === 'cancelled')
)

const completedAppointments = computed(() => 
  appointments.value.filter(apt => apt.status === 'completed')
)

const filteredScheduledAppointments = computed(() => {
  if (!searchQuery.value) return scheduledAppointments.value
  return scheduledAppointments.value.filter(apt => 
    apt.doctor_name?.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
    apt.department?.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
    apt.type?.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
})

const filteredRescheduledAppointments = computed(() => {
  if (!searchQuery.value) return rescheduledAppointments.value
  return rescheduledAppointments.value.filter(apt => 
    apt.doctor_name?.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
    apt.department?.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
    apt.type?.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
})

const filteredCancelledAppointments = computed(() => {
  if (!searchQuery.value) return cancelledAppointments.value
  return cancelledAppointments.value.filter(apt => 
    apt.doctor_name?.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
    apt.department?.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
    apt.type?.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
})

const filteredCompletedAppointments = computed(() => {
  if (!searchQuery.value) return completedAppointments.value
  return completedAppointments.value.filter(apt => 
    apt.doctor_name?.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
    apt.department?.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
    apt.type?.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
})

// Methods
const validateDate = (date: string) => {
  const regex = /^(0[1-9]|1[0-2])\/(0[1-9]|[12][0-9]|3[01])\/\d{4}$/
  if (!regex.test(date)) return false
  
  const parts = date.split('/').map(Number)
  if (parts.length !== 3) return false
  
  const [month, day, year] = parts
  if (!month || !day || !year) return false
  
  const dateObj = new Date(year, month - 1, day)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  
  return dateObj >= today
}

const validateTime = (time: string) => {
  const regex = /^([01]?[0-9]|2[0-3]):[0-5][0-9]$/
  return regex.test(time)
}

const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', { 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric' 
  })
}

const formatTime = (isoString: string) => {
  const date = new Date(isoString)
  if (isNaN(date.getTime())) return ''
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const formatHHMM = (timeStr: string) => {
  const s = String(timeStr ?? '')
  // Backend returns HH:MM:SS; UI expects HH:MM for consistency
  return s.length >= 5 ? s.slice(0, 5) : s
}

// Convert MM/DD/YYYY from the form to a stable YYYY-MM-DD string
// Avoid toISOString to prevent timezone shifting the calendar date
const toISOFromMDY = (mdy: string): string => {
  const parts = mdy?.split('/') ?? []
  if (parts.length === 3) {
    const [mm, dd, yyyy] = parts
    const y = Number(yyyy), m = Number(mm), d = Number(dd)
    if (!Number.isNaN(y) && !Number.isNaN(m) && !Number.isNaN(d)) {
      const M = String(m).padStart(2, '0')
      const D = String(d).padStart(2, '0')
      return `${y}-${M}-${D}`
    }
  }
  // Fallback: try parsing string and format as local YYYY-MM-DD
  const dt = new Date(mdy)
  if (isNaN(dt.getTime())) {
    const today = new Date()
    const M = String(today.getMonth() + 1).padStart(2, '0')
    const D = String(today.getDate()).padStart(2, '0')
    return `${today.getFullYear()}-${M}-${D}`
  }
  const M = String(dt.getMonth() + 1).padStart(2, '0')
  const D = String(dt.getDate()).padStart(2, '0')
  return `${dt.getFullYear()}-${M}-${D}`
}

// Extract local YYYY-MM-DD from ISO datetime string safely
const ymdLocalFromISO = (iso: string): string => {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return ''
  const M = String(d.getMonth() + 1).padStart(2, '0')
  const D = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${M}-${D}`
}

const loadDoctors = async () => {
  if (!form.value.department) {
    doctorOptions.value = []
    selectedDoctorId.value = ''
    return
  }
  
  try {
    doctorLoading.value = true
    
    const token = localStorage.getItem('access_token')
    if (!token) {
      console.error('No access token found')
      doctorOptions.value = []
      return
    }
    
    const res = await api.get('/operations/available-doctors/', { 
      params: { 
        department: form.value.department 
      } 
    })
    
    type AvailableDoctor = { 
      id: number | string
      full_name?: string
      department?: string
      specialization?: string
      is_available?: boolean
      current_patients?: number
      verification_status?: string
      is_verified?: boolean
    }
    
    const list: AvailableDoctor[] = Array.isArray(res.data?.doctors)
      ? (res.data.doctors as AvailableDoctor[])
      : []
    
    const allDoctors: DoctorOption[] = list.map((d) => ({
      label: `${d.full_name ?? 'Unknown'} — ${d.department ?? d.specialization ?? 'Unknown'}`,
      value: String(d.id),
      detail: `${d.current_patients ?? 0} patients today | ${d.specialization ?? 'General Medicine'}`,
      isAvailable: d.is_available ?? false,
      currentPatients: d.current_patients ?? 0,
      verification_status: d.verification_status ?? undefined,
      is_verified: d.is_verified ?? undefined
    }))
    
    doctorOptions.value = allDoctors.filter((d) => {
      const isVerified = d.is_verified === true
      const isApproved = d.verification_status === 'approved'
      const isAvailable = d.isAvailable === true
      
      return isVerified && isApproved && isAvailable
    })
      
  } catch (e) {
    doctorOptions.value = []
    console.error('Failed to load doctors:', e)
    
    const error = e as { response?: { status?: number; data?: unknown } }
    
    if (error?.response?.status === 403) {
      console.warn('User verification required to view doctors')
    } else if (error?.response?.status === 401) {
      console.warn('Authentication required')
    }
  } finally {
    doctorLoading.value = false
  }
}

const loadHospitalDepartments = async () => {
  try {
    const res = await api.get('/operations/hospital/departments/')
    const list = Array.isArray(res.data?.departments) ? res.data.departments : []
    departmentOptions.value = list.length ? list : sharedDepartmentOptions
  } catch (e) {
    console.warn('Failed to load hospital departments, using defaults:', e)
    departmentOptions.value = sharedDepartmentOptions
  }
}

const loadAppointments = async () => {
  try {
    const res = await api.get('/operations/patient/appointments/')
    appointments.value = res.data?.results || res.data || []
  } catch (error) {
    console.error('Failed to load appointments:', error)
    appointments.value = []
    const err = error as { response?: { status?: number; data?: { error?: string, message?: string } } }
    const status = err?.response?.status
    const msg = err?.response?.data?.error || err?.response?.data?.message
    const fallback = 'Unable to fetch appointments. Please try again.'
    const message = msg || (status === 404 ? 'Patient profile not found' : status === 401 ? 'Authentication required' : fallback)
    $q.notify({ type: 'negative', message, position: 'top' })
  }
}

const checkForDuplicateAppointment = async () => {
  try {
    if (!form.value.date || !form.value.time) return false
    
    // Load all appointments for the patient to check for duplicates
    const res = await api.get('/operations/patient/appointments/')
    const existingAppointments = res.data?.results || res.data || []
    
    // Filter out cancelled appointments and the current appointment being rescheduled
    const activeAppointments = existingAppointments.filter((apt: Appointment) => {
      if (apt.status === 'cancelled') return false
      if (rescheduleAppointmentId.value && apt.appointment_id === rescheduleAppointmentId.value) return false
      
      // Check if the date and time match
      const aptYMD = ymdLocalFromISO(apt.appointment_date)
      const formYMD = toISOFromMDY(form.value.date)

      const isSameDate = aptYMD && formYMD && aptYMD === formYMD
      
      const isSameTime = String(apt.appointment_time ?? '').slice(0, 5) === form.value.time
      
      return isSameDate && isSameTime
    })
    
    return activeAppointments.length > 0
  } catch (error) {
    console.error('Error checking for duplicates:', error)
    return false
  }
}

const onSubmit = async () => {
  const valid = await formRef.value?.validate?.()
  if (valid === false) return
  
  // Check for duplicate appointments
  const isDuplicate = await checkForDuplicateAppointment()
  if (isDuplicate) {
    showDuplicateWarning.value = true
    return
  }
  
  scheduling.value = true
  
  try {
    type SchedulePayload = {
      type: string
      department: string
      date: string
      time: string
      reason: string
      doctor_id?: string
      reschedule_reason?: string
    }
    
    const payload: SchedulePayload = {
      type: form.value.type,
      department: form.value.department,
      date: toISOFromMDY(form.value.date),
      time: form.value.time,
      reason: form.value.reason
    }
    
    if (selectedDoctorId.value) {
      payload.doctor_id = selectedDoctorId.value
    }
    
    // If rescheduling, update the existing appointment
    if (isReschedule.value && rescheduleAppointmentId.value) {
      payload.reschedule_reason = 'Patient requested reschedule'
      await api.patch(`/operations/appointments/${rescheduleAppointmentId.value}/reschedule/`, payload)
      successMessage.value = 'Appointment rescheduled successfully!'
    } else {
      // Create new appointment
      await api.post('/operations/appointments/schedule/', payload)
      successMessage.value = 'Appointment scheduled successfully!'
    }
    
    showSuccessDialog.value = true
    
    // Reload appointments
    await loadAppointments()
    
    // Reset form and close dialog
    closeScheduleForm()
    
  } catch (e) {
    console.error('Failed to schedule appointment:', e)
    const error = e as { response?: { data?: { error?: string, message?: string } } }
    const errorMessage = error?.response?.data?.error || error?.response?.data?.message || 'Failed to schedule appointment. Please try again.'
    
    $q.notify({
      type: 'negative',
      message: errorMessage,
      position: 'top'
    })
  } finally {
    scheduling.value = false
  }
}

const showCancelModal = (appointment: Appointment) => {
  selectedAppointment.value = appointment
  cancellationReason.value = ''
  showCancelDialog.value = true
}

const closeCancelDialog = () => {
  showCancelDialog.value = false
  selectedAppointment.value = null
  cancellationReason.value = ''
}

const rescheduleFromCancel = () => {
  if (!selectedAppointment.value) return
  
  // Populate form with existing appointment data
  form.value.type = selectedAppointment.value.type
  form.value.department = selectedAppointment.value.department
  form.value.reason = selectedAppointment.value.reason
  selectedDoctorId.value = String(selectedAppointment.value.doctor_id) || ''
  
  isReschedule.value = true
  rescheduleAppointmentId.value = selectedAppointment.value.appointment_id
  
  closeCancelDialog()
  showScheduleForm.value = true
}

const confirmCancellation = async () => {
  if (!selectedAppointment.value) return
  
  cancelling.value = true
  
  try {
    await api.patch(`/operations/appointments/${selectedAppointment.value.appointment_id}/cancel/`, {
      cancellation_reason: cancellationReason.value
    })
    
    successMessage.value = 'Appointment cancelled successfully!'
    showSuccessDialog.value = true
    
    // Reload appointments
    await loadAppointments()
    
    closeCancelDialog()
    
  } catch (error) {
    console.error('Failed to cancel appointment:', error)
    $q.notify({
      type: 'negative',
      message: 'Failed to cancel appointment. Please try again.',
      position: 'top'
    })
  } finally {
    cancelling.value = false
  }
}

const rescheduleAppointment = (appointment: Appointment) => {
  // Populate form with existing appointment data
  form.value.type = appointment.type
  form.value.department = appointment.department
  form.value.reason = appointment.reason
  selectedDoctorId.value = String(appointment.doctor_id) || ''
  
  isReschedule.value = true
  rescheduleAppointmentId.value = appointment.appointment_id
  
  showScheduleForm.value = true
}


const closeScheduleForm = () => {
  showScheduleForm.value = false
  isReschedule.value = false
  rescheduleAppointmentId.value = null
  form.value = {
    type: '',
    department: '',
    date: '',
    time: '',
    reason: ''
  }
  selectedDoctorId.value = ''
  doctorOptions.value = []
}

const fetchUnreadCount = async () => {
  try {
    const res = await api.get('/operations/notifications/')
    type NotificationDTO = { is_read?: boolean }
    const list = (res.data?.results ?? res.data ?? []) as NotificationDTO[]
    unreadCount.value = Array.isArray(list) ? list.filter((n) => n && n.is_read === false).length : 0
  } catch {
    unreadCount.value = 0
  }
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

// Watch department changes to reload doctor options
watch(() => form.value.department, () => {
  selectedDoctorId.value = ''
  void loadDoctors()
})

onMounted(() => {
  void fetchUnreadCount()
  void loadAppointments()
  void loadHospitalDepartments()
  
  // Load doctors if department is preset
  if (form.value.department) {
    void loadDoctors()
  }
})
</script>

<style scoped>
.schedule-card {
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
}

.appointment-card {
  transition: all 0.3s ease;
  border-left: 4px solid #1976d2;
}

.appointment-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.cancelled-card {
  opacity: 0.7;
  border-left-color: #757575;
}

.completed-card {
  border-left-color: #2e7d32;
}

.header-content .text-h6 {
  margin: 0;
}

.header-content .text-caption {
  margin: 0;
}

@media (max-width: 768px) {
  .max-w-4xl {
    max-width: 100%;
  }
  
  .appointment-card {
    margin-bottom: 16px;
  }
}

.dialog-card {
  width: 100%;
  max-width: 800px;
}

.dialog-card-sm {
  width: 100%;
  max-width: 500px;
}

.success-card {
  width: 360px;
  max-width: 90vw;
}

.cancel-card {
  width: 420px;
  max-width: 95vw;
}

@media (max-width: 768px) {
  .dialog-card,
  .dialog-card-sm {
    max-width: 95vw;
  }
}
</style>