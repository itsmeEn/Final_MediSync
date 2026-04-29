<template>
  <q-layout view="lHh Lpr lFf" :class="{ 'high-contrast': highContrast, 'large-text': largeText, 'ms-dark': darkMode }">
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
        <q-btn flat round icon="notifications" class="q-mr-sm" aria-label="View notifications" @click="navigateTo('/patient-notifications')">
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
      <q-page class="patient-bg q-pa-md pb-safe" :class="{ 'high-contrast': highContrast, 'large-text': largeText, 'ms-dark': darkMode }" role="main" aria-label="Appointment scheduling">
        <div class="sr-only" aria-live="polite">{{ liveMessage }}</div>
        <MsToastHost />
        <div class="max-w-4xl mx-auto">
          <q-card class="calendar-shell" flat bordered>
            <q-card-section class="calendar-shell-header">
              <div class="calendar-shell-title">
                <div class="calendar-title">Appointment calendar</div>
                <div class="calendar-subtitle">Manage your appointments and schedule</div>
              </div>

              <div class="calendar-shell-actions">
                <q-input
                  v-model="calendarSearch"
                  dense
                  outlined
                  class="calendar-search"
                  placeholder="Search patient, symptoms, or appointment"
                  aria-label="Search appointments"
                  clearable
                >
                  <template #prepend>
                    <q-icon name="search" />
                  </template>
                </q-input>

                <div class="calendar-shell-action-buttons">
                  <q-btn
                    dense
                    unelevated
                    class="calendar-action-btn"
                    label="+ New"
                    @click="showScheduleForm = true"
                    aria-label="Create new appointment"
                  />
                  <q-btn
                    dense
                    outline
                    class="calendar-action-btn"
                    icon="download"
                    label="Export"
                    @click="exportAppointments"
                    aria-label="Export appointments"
                  />
                </div>
              </div>
            </q-card-section>

            <q-separator />

            <q-card-section class="calendar-stats">
              <div class="calendar-stats-grid">
                <div class="calendar-stat-card is-today" role="group" aria-label="Today's schedule">
                  <div class="calendar-stat-icon">
                    <q-icon name="event" />
                  </div>
                  <div class="calendar-stat-label">Today's schedule</div>
                  <div class="calendar-stat-value">{{ todayScheduleCount }}</div>
                  <div class="calendar-stat-meta">
                    <span v-if="todaySchedulePreview.length === 0">No appointments today</span>
                    <span v-else>{{ todaySchedulePreview.join(', ') }}</span>
                  </div>
                </div>

                <div class="calendar-stat-card is-cancelled" role="group" aria-label="Total cancelled appointments">
                  <div class="calendar-stat-icon">
                    <q-icon name="cancel" />
                  </div>
                  <div class="calendar-stat-label">Total cancelled</div>
                  <div class="calendar-stat-value">{{ totalCancelledCount }}</div>
                  <div class="calendar-stat-meta">All time</div>
                </div>

                <div class="calendar-stat-card is-notifications" role="group" aria-label="Notifications">
                  <div class="calendar-stat-icon">
                    <q-icon name="notifications" />
                  </div>
                  <div class="calendar-stat-label">Notifications</div>
                  <div class="calendar-stat-value">{{ unreadCount }}</div>
                  <div class="calendar-stat-meta">Unread</div>
                </div>
              </div>
            </q-card-section>

            <q-separator />

            <q-card-section class="calendar-card">
              <div class="calendar-topbar">
                <div class="calendar-topbar-left">
                  <div class="calendar-topbar-check" aria-hidden="true"></div>
                  <div class="calendar-month">{{ calendarMonthLabel }}</div>
                  <q-btn
                    dense
                    outline
                    class="calendar-today-btn"
                    label="Today"
                    @click="goToToday"
                    aria-label="Jump to today"
                  />
                </div>

                <div class="calendar-topbar-right">
                  <q-btn dense flat round icon="chevron_left" class="calendar-nav-btn" @click="prevMonth" aria-label="Previous month" />
                  <q-btn dense flat round icon="chevron_right" class="calendar-nav-btn" @click="nextMonth" aria-label="Next month" />
                </div>
              </div>

              <div class="calendar-toolbar">
                <div class="calendar-view-tabs" role="tablist" aria-label="Calendar view">
                  <button
                    type="button"
                    class="calendar-tab"
                    :class="{ 'is-active': calendarView === 'day' }"
                    role="tab"
                    :aria-selected="calendarView === 'day'"
                    @click="calendarView = 'day'"
                  >
                    Day
                  </button>
                  <button
                    type="button"
                    class="calendar-tab"
                    :class="{ 'is-active': calendarView === 'week' }"
                    role="tab"
                    :aria-selected="calendarView === 'week'"
                    @click="calendarView = 'week'"
                  >
                    Week
                  </button>
                  <button
                    type="button"
                    class="calendar-tab"
                    :class="{ 'is-active': calendarView === 'month' }"
                    role="tab"
                    :aria-selected="calendarView === 'month'"
                    @click="calendarView = 'month'"
                  >
                    Month
                  </button>
                </div>

                <div class="calendar-toolbar-actions">
                  <div class="calendar-mini-toggles" aria-hidden="true">
                    <span class="mini-toggle"></span>
                    <span class="mini-toggle"></span>
                    <span class="mini-toggle"></span>
                  </div>
                  <q-btn dense outline class="calendar-chip-btn" label="Block date" aria-label="Block date" />
                  <q-btn dense unelevated class="calendar-chip-btn is-primary" label="+ New appointment" @click="showScheduleForm = true" aria-label="New appointment" />
                </div>
              </div>

              <div v-if="calendarView === 'month'" class="calendar-grid" role="grid" aria-label="Monthly calendar">
                <div class="calendar-dow" role="row">
                  <div v-for="d in weekDayLabels" :key="d" class="calendar-dow-cell" role="columnheader">{{ d }}</div>
                </div>

                <div class="calendar-weeks">
                  <div v-for="(week, wIdx) in monthGrid" :key="wIdx" class="calendar-week" role="row">
                    <div
                      v-for="day in week"
                      :key="day.key"
                      class="calendar-day"
                      :class="{ 'is-out': !day.inMonth, 'is-today': day.isToday, 'has-events': day.events.length > 0 }"
                      role="gridcell"
                      tabindex="0"
                      :aria-label="day.ariaLabel"
                      @keydown.enter.prevent="openDay(day)"
                      @click="openDay(day)"
                    >
                      <div class="calendar-day-top">
                        <div class="calendar-day-num">{{ day.dayOfMonth }}</div>
                        <div v-if="day.events.length > 0" class="calendar-day-dot" aria-hidden="true"></div>
                      </div>

                      <div class="calendar-day-events">
                        <button
                          v-for="e in day.visibleEvents"
                          :key="e.key"
                          type="button"
                          class="calendar-event"
                          @click.stop="openAppointmentActions(e.appointment)"
                          :aria-label="`Appointment with ${e.label} at ${formatHHMM(e.appointment.appointment_time)}`"
                        >
                          <span class="calendar-event-title">{{ e.label }}</span>
                        </button>
                        <div v-if="day.moreCount > 0" class="calendar-more" aria-hidden="true">+{{ day.moreCount }} more</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div v-else-if="calendarView === 'week'" class="calendar-weekview" aria-label="Weekly calendar">
                <div class="calendar-weekview-head">
                  <div v-for="d in weekViewDays" :key="d.key" class="calendar-weekview-headcell">
                    <div class="weekview-dow">{{ d.dow }}</div>
                    <div class="weekview-daynum" :class="{ 'is-today': d.isToday }">{{ d.day }}</div>
                  </div>
                </div>
                <div class="calendar-weekview-body">
                  <div v-for="d in weekViewDays" :key="d.key" class="calendar-weekview-col">
                    <button
                      v-for="e in d.events"
                      :key="e.key"
                      type="button"
                      class="calendar-event"
                      @click="openAppointmentActions(e.appointment)"
                      :aria-label="`Appointment with ${e.label} at ${formatHHMM(e.appointment.appointment_time)}`"
                    >
                      <span class="calendar-event-title">{{ e.label }}</span>
                    </button>
                  </div>
                </div>
              </div>

              <div v-else class="calendar-dayview" aria-label="Daily calendar">
                <div class="calendar-dayview-title">{{ dayViewLabel }}</div>
                <div v-if="dayViewEvents.length === 0" class="calendar-empty">No appointments</div>
                <div v-else class="calendar-dayview-events">
                  <button
                    v-for="e in dayViewEvents"
                    :key="e.key"
                    type="button"
                    class="calendar-event is-dayview"
                    @click="openAppointmentActions(e.appointment)"
                    :aria-label="`Appointment with ${e.label} at ${formatHHMM(e.appointment.appointment_time)}`"
                  >
                    <span class="calendar-event-title">{{ e.label }}</span>
                    <span class="calendar-event-time">{{ formatHHMM(e.appointment.appointment_time) }}</span>
                  </button>
                </div>
              </div>
            </q-card-section>
          </q-card>

          <q-card class="q-mt-md">
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
                          <q-btn flat color="primary" label="Reschedule" class="touch-target ms-focusable" @click="rescheduleAppointment(appointment)" />
                          <q-btn flat color="negative" label="Cancel" class="touch-target ms-focusable" @click="showCancelModal(appointment)" />
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
                          <q-btn flat color="primary" label="Reschedule Again" class="touch-target ms-focusable" @click="rescheduleAppointment(appointment)" />
                          <q-btn flat color="negative" label="Cancel" class="touch-target ms-focusable" @click="showCancelModal(appointment)" />
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
                          <q-btn flat color="primary" label="Reschedule" class="touch-target ms-focusable" @click="rescheduleAppointment(appointment)" />
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
      <q-card class="dialog-card" :style="dialogThemeVars">
        <q-card-section class="row items-center">
          <q-avatar color="primary" text-color="white" icon="event_available" size="48px" class="q-mr-md" />
          <div>
            <div class="text-h6 text-weight-bold">Schedule New Appointment</div>
                    <div class="text-caption">Please fill out all the required information</div>
          </div>
        </q-card-section>

        <q-separator />

        <q-form ref="formRef" @submit="onSubmit" class="q-gutter-md q-pa-md">
          <q-banner rounded class="ms-banner" aria-label="Scheduling guidance">
            Select a department and date to see available time slots. Confirmation appears as a toast and will auto-dismiss.
          </q-banner>

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
                aria-label="Select appointment date"
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
                label="Time"
                readonly
                placeholder="Select a time slot"
                :rules="[val => !!val || 'Time is required', val => validateTime(val) || 'Please enter a valid time']"
                outlined
                color="primary"
                aria-label="Selected appointment time"
              >
                <template #append>
                  <q-icon name="access_time" />
                </template>
              </q-input>
              <div class="time-slot-grid q-mt-sm" role="radiogroup" aria-label="Available time slots">
                <q-btn
                  v-for="slot in timeSlots"
                  :key="slot.value"
                  flat
                  class="time-slot-btn touch-target ms-focusable"
                  :class="{ 'is-selected': form.time === slot.value, 'is-disabled': slot.disabled }"
                  :disable="slot.disabled"
                  :aria-label="slot.disabled ? `Time slot ${slot.label} unavailable` : `Select time slot ${slot.label}`"
                  :aria-checked="form.time === slot.value"
                  role="radio"
                  @click="selectTimeSlot(slot.value, slot.disabled)"
                >
                  <span class="text-weight-medium">{{ slot.label }}</span>
                </q-btn>
              </div>
              <div class="text-caption text-grey-7 q-mt-xs" aria-live="polite">{{ timeSlotHint }}</div>
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
          <q-btn flat color="grey-7" label="Cancel" class="touch-target ms-focusable" @click="closeScheduleForm" />
          <q-btn 
            color="primary" 
            :label="isReschedule ? 'Reschedule Appointment' : 'Schedule Appointment'"
            @click="onSubmit"
            :loading="scheduling"
            unelevated
            class="touch-target ms-focusable"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Cancellation Confirmation Modal -->
    <q-dialog v-model="showCancelDialog">
      <q-card class="cancel-card" :style="dialogThemeVars">
        <q-btn
          flat
          round
          dense
          icon="close"
          aria-label="Close"
          class="absolute-top-right q-ma-sm ms-focusable"
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

    <q-dialog v-model="showAppointmentActionsDialog">
      <q-card class="appointment-actions-card" :style="dialogThemeVars">
        <q-btn
          flat
          round
          dense
          icon="close"
          aria-label="Close"
          class="absolute-top-right q-ma-sm ms-focusable"
          @click="showAppointmentActionsDialog = false"
        />
        <q-card-section class="q-pa-lg">
          <div class="text-h6 text-weight-bold">Appointment</div>
          <div v-if="selectedAppointment" class="q-mt-md">
            <div class="row items-center q-mb-sm">
              <q-icon name="medical_services" size="18px" class="q-mr-sm" />
              <div class="text-body1 text-weight-medium">{{ selectedAppointment.doctor_name || 'Assigned Doctor' }}</div>
            </div>
            <div class="row items-center q-mb-xs">
              <q-icon name="event" size="18px" class="q-mr-sm" />
              <div class="text-body2">{{ formatDate(selectedAppointment.appointment_date) }}</div>
            </div>
            <div class="row items-center q-mb-xs">
              <q-icon name="access_time" size="18px" class="q-mr-sm" />
              <div class="text-body2">{{ formatHHMM(selectedAppointment.appointment_time) }}</div>
            </div>
            <div class="row items-center">
              <q-icon name="category" size="18px" class="q-mr-sm" />
              <div class="text-body2">{{ selectedAppointment.type }}</div>
            </div>
          </div>
        </q-card-section>
        <q-separator />
        <q-card-actions class="q-pa-md">
          <div class="row q-col-gutter-sm full-width">
            <div class="col-6">
              <q-btn
                outline
                color="primary"
                label="Reschedule"
                class="full-width"
                :disable="!selectedAppointment"
                @click="rescheduleSelectedFromCalendar"
              />
            </div>
            <div class="col-6">
              <q-btn
                color="negative"
                unelevated
                label="Cancel"
                class="full-width"
                :disable="!selectedAppointment"
                @click="cancelSelectedFromCalendar"
              />
            </div>
          </div>
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
import MsToastHost from 'src/components/MsToastHost.vue'
import PatientBottomNav from 'src/components/PatientBottomNav.vue'
import { emitMsToast } from 'src/utils/toastBus'

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
const highContrast = ref(false)
const largeText = ref(false)
const darkMode = ref(false)
const liveMessage = ref('')

const dialogThemeVars = computed<Record<string, string>>(() => {
  if (highContrast.value) {
    return {
      '--ms-bg': '#ffffff',
      '--ms-card': '#ffffff',
      '--ms-text': '#000000',
      '--ms-muted': '#000000',
      '--ms-border': '#000000',
      '--ms-shadow': 'none',
      '--ms-shadow-hover': 'none',
      '--ms-focus': '#000000',
    }
  }

  if (darkMode.value) {
    return {
      '--ms-bg': '#0b1220',
      '--ms-card': '#111a2e',
      '--ms-text': '#e6edf6',
      '--ms-muted': '#aeb9c8',
      '--ms-border': 'rgba(230, 237, 246, 0.12)',
      '--ms-shadow': '0 10px 28px rgba(0, 0, 0, 0.35)',
      '--ms-shadow-hover': '0 18px 44px rgba(0, 0, 0, 0.45)',
      '--ms-focus': 'rgba(255, 255, 255, 0.8)',
    }
  }

  return {
    '--ms-bg': '#f8fafb',
    '--ms-card': '#ffffff',
    '--ms-text': '#0f172a',
    '--ms-muted': '#5b6472',
    '--ms-border': 'rgba(15, 23, 42, 0.08)',
    '--ms-shadow': '0 10px 28px rgba(15, 23, 42, 0.06)',
    '--ms-shadow-hover': '0 16px 40px rgba(15, 23, 42, 0.10)',
    '--ms-focus': 'rgba(38, 166, 154, 0.55)',
  }
})

const announce = (message: string) => {
  liveMessage.value = ''
  requestAnimationFrame(() => {
    liveMessage.value = message
  })
}

const toast = (type: 'positive' | 'negative' | 'warning' | 'info', message: string) => {
  emitMsToast({ type, message, timeoutMs: 2500 })
  announce(message)
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

// Appointment management state
const activeTab = ref('scheduled')
const searchQuery = ref('')
const showScheduleForm = ref(false)
const showCancelDialog = ref(false)
const showAppointmentActionsDialog = ref(false)
const selectedAppointment = ref<Appointment | null>(null)
const cancellationReason = ref('')
const scheduling = ref(false)
const cancelling = ref(false)
const isReschedule = ref(false)
const rescheduleAppointmentId = ref<number | null>(null)

type CalendarView = 'day' | 'week' | 'month'
type CalendarEventVM = { key: string; label: string; appointment: Appointment }
type CalendarDayCell = {
  key: string
  date: Date
  dayOfMonth: number
  inMonth: boolean
  isToday: boolean
  events: CalendarEventVM[]
  visibleEvents: CalendarEventVM[]
  moreCount: number
  ariaLabel: string
}

const calendarSearch = ref('')
const calendarView = ref<CalendarView>('month')
const nowForCalendar = new Date()
const calendarMonthCursor = ref<Date>(new Date(nowForCalendar.getFullYear(), nowForCalendar.getMonth(), 1))
const selectedDay = ref<Date>(new Date())
const weekDayLabels = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']

const ymdFromDate = (d: Date): string => {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const addDays = (d: Date, days: number): Date => {
  const copy = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  copy.setDate(copy.getDate() + days)
  return copy
}

const startOfWeekSunday = (d: Date): Date => {
  const copy = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  const offset = copy.getDay()
  copy.setDate(copy.getDate() - offset)
  return copy
}

const formatMonthYear = (d: Date): string => {
  return d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
}

const makePersonShort = (fullName: string): string => {
  const parts = String(fullName ?? '').trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return 'Appointment'
  if (parts.length === 1) return parts[0] ?? 'Appointment'
  const first = parts.at(0) ?? ''
  const last = parts.at(-1) ?? ''
  const initial = first ? first.slice(0, 1).toUpperCase() : ''
  return `${initial}. ${last}`.trim()
}

const calendarAppointments = computed(() => {
  const q = calendarSearch.value.trim().toLowerCase()
  const list = appointments.value.filter((a) => a.status === 'scheduled' || a.status === 'rescheduled')
  if (!q) return list
  return list.filter((a) => {
    const haystack = [
      a.patient_name,
      a.doctor_name,
      a.department,
      a.type,
      a.appointment_type,
      a.reason
    ].join(' ').toLowerCase()
    return haystack.includes(q)
  })
})

const calendarBuckets = computed<Record<string, CalendarEventVM[]>>(() => {
  const buckets: Record<string, CalendarEventVM[]> = {}
  for (const a of calendarAppointments.value) {
    const key = String(a.appointment_date ?? '').slice(0, 10)
    if (!key) continue
    const label = makePersonShort(a.doctor_name || a.department || a.type || 'Appointment')
    const vm: CalendarEventVM = { key: `${a.id}-${a.appointment_time}`, label, appointment: a }
    if (!buckets[key]) buckets[key] = []
    buckets[key].push(vm)
  }
  for (const k of Object.keys(buckets)) {
    const list = buckets[k]
    if (list) {
      list.sort((x, y) => String(x.appointment.appointment_time).localeCompare(String(y.appointment.appointment_time)))
    }
  }
  return buckets
})

const calendarMonthLabel = computed(() => formatMonthYear(calendarMonthCursor.value))

const monthGrid = computed<CalendarDayCell[][]>(() => {
  const cursor = calendarMonthCursor.value
  const y = cursor.getFullYear()
  const m = cursor.getMonth()
  const first = new Date(y, m, 1)
  const gridStart = startOfWeekSunday(first)
  const todayKey = ymdFromDate(new Date())

  const weeks: CalendarDayCell[][] = []
  for (let w = 0; w < 6; w += 1) {
    const row: CalendarDayCell[] = []
    for (let i = 0; i < 7; i += 1) {
      const date = addDays(gridStart, w * 7 + i)
      const key = ymdFromDate(date)
      const inMonth = date.getMonth() === m
      const events = calendarBuckets.value[key] ?? []
      const visibleEvents = events.slice(0, 2)
      const moreCount = Math.max(0, events.length - visibleEvents.length)
      const ariaLabel = `${date.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}${events.length ? `, ${events.length} appointment${events.length === 1 ? '' : 's'}` : ''}`
      row.push({
        key,
        date,
        dayOfMonth: date.getDate(),
        inMonth,
        isToday: key === todayKey,
        events,
        visibleEvents,
        moreCount,
        ariaLabel
      })
    }
    weeks.push(row)
  }
  return weeks
})

const goToToday = () => {
  const now = new Date()
  selectedDay.value = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  calendarMonthCursor.value = new Date(now.getFullYear(), now.getMonth(), 1)
  announce('Showing today')
}

const prevMonth = () => {
  const d = calendarMonthCursor.value
  calendarMonthCursor.value = new Date(d.getFullYear(), d.getMonth() - 1, 1)
}

const nextMonth = () => {
  const d = calendarMonthCursor.value
  calendarMonthCursor.value = new Date(d.getFullYear(), d.getMonth() + 1, 1)
}

const openDay = (day: CalendarDayCell) => {
  selectedDay.value = new Date(day.date.getFullYear(), day.date.getMonth(), day.date.getDate())
  announce(`Selected ${day.date.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}`)
}

const openAppointmentActions = (appointment: Appointment) => {
  selectedAppointment.value = appointment
  showAppointmentActionsDialog.value = true
}

const rescheduleSelectedFromCalendar = () => {
  if (!selectedAppointment.value) return
  showAppointmentActionsDialog.value = false
  rescheduleAppointment(selectedAppointment.value)
}

const cancelSelectedFromCalendar = () => {
  if (!selectedAppointment.value) return
  showAppointmentActionsDialog.value = false
  showCancelModal(selectedAppointment.value)
}

const todayKey = computed(() => ymdFromDate(new Date()))
const todayScheduleCount = computed(() => (calendarBuckets.value[todayKey.value] ?? []).length)
const todaySchedulePreview = computed(() => {
  const list = (calendarBuckets.value[todayKey.value] ?? []).slice(0, 2).map((e) => e.label)
  const total = todayScheduleCount.value
  if (total <= list.length) return list
  return [...list, `+${total - list.length} more`]
})
const totalCancelledCount = computed(() => appointments.value.filter((a) => a.status === 'cancelled').length)

const weekViewDays = computed(() => {
  const start = startOfWeekSunday(selectedDay.value)
  const today = ymdFromDate(new Date())
  return Array.from({ length: 7 }, (_, i) => {
    const date = addDays(start, i)
    const key = ymdFromDate(date)
    return {
      key,
      date,
      dow: weekDayLabels[i],
      day: date.getDate(),
      isToday: key === today,
      events: calendarBuckets.value[key] ?? []
    }
  })
})

const dayViewLabel = computed(() => {
  return selectedDay.value.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })
})

const dayViewEvents = computed(() => {
  const key = ymdFromDate(selectedDay.value)
  return calendarBuckets.value[key] ?? []
})

const exportAppointments = () => {
  const headers = ['id', 'doctor', 'department', 'date', 'time', 'status', 'type', 'reason'] as const
  const escape = (v: string) => `"${v.replaceAll('"', '""')}"`
  const csvRows = appointments.value.map((a) => ([
    String(a.id ?? ''),
    String(a.doctor_name ?? ''),
    String(a.department ?? ''),
    String(a.appointment_date ?? ''),
    String(formatHHMM(a.appointment_time ?? '')),
    String(a.status ?? ''),
    String(a.type ?? ''),
    String(a.reason ?? '')
  ].map(escape).join(',')))
  const csv = [headers.join(','), ...csvRows].join('\n')

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `appointments-${ymdFromDate(new Date())}.csv`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

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
const doctorSlotsLoading = ref(false)
const doctorOccupiedTimes = ref<string[]>([])

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

const pad2 = (n: number) => String(n).padStart(2, '0')
const formatSlotLabel = (time24: string) => {
  const [hStr = '0', mStr = '00'] = time24.split(':')
  const h = parseInt(hStr, 10)
  const ampm = h >= 12 ? 'PM' : 'AM'
  const displayHour = h % 12 === 0 ? 12 : h % 12
  return `${displayHour}:${mStr} ${ampm}`
}

const buildTimeSlots = () => {
  const slots: { value: string; label: string }[] = []
  for (let hour = 8; hour <= 16; hour += 1) {
    for (const minute of [0, 30]) {
      const value = `${pad2(hour)}:${pad2(minute)}`
      slots.push({ value, label: formatSlotLabel(value) })
    }
  }
  slots.push({ value: '17:00', label: formatSlotLabel('17:00') })
  return slots
}

const isSlotTaken = (time: string) => {
  if (!form.value.date) return false
  const formYMD = toISOFromMDY(form.value.date)
  if (!formYMD) return false
  if (selectedDoctorId.value) {
    const t = String(time ?? '').slice(0, 5)
    if (doctorOccupiedTimes.value.includes(t)) return true
  }
  return appointments.value.some((apt) => {
    if (apt.status === 'cancelled') return false
    if (rescheduleAppointmentId.value && apt.appointment_id === rescheduleAppointmentId.value) return false
    const aptYMD = ymdLocalFromISO(apt.appointment_date)
    const aptTime = String(apt.appointment_time ?? '').slice(0, 5)
    return aptYMD === formYMD && aptTime === time
  })
}

const timeSlots = computed(() => {
  const slots = buildTimeSlots()
  return slots.map((s) => ({ ...s, disabled: isSlotTaken(s.value) }))
})

const timeSlotHint = computed(() => {
  if (!form.value.date) return 'Select a date to view available time slots.'
  if (!selectedDoctorId.value) return 'Select a doctor to view accurate availability.'
  if (doctorSlotsLoading.value) return 'Loading doctor availability...'
  const available = timeSlots.value.filter((s) => !s.disabled).length
  return available ? `${available} time slot(s) available.` : 'No time slots available for this date.'
})

const selectTimeSlot = (value: string, disabled?: boolean) => {
  if (disabled) {
    toast('warning', 'This time slot is not available. Please choose another time.')
    return
  }
  form.value.time = value
}

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
    doctorOccupiedTimes.value = []
    return
  }
  
  try {
    doctorLoading.value = true
    
    const token = localStorage.getItem('access_token')
    if (!token) {
      console.error('No access token found')
      doctorOptions.value = []
      toast('negative', 'Session expired. Please log in again.')
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
      toast('negative', 'Account verification required to view doctors.')
    } else if (error?.response?.status === 401) {
      console.warn('Authentication required')
      toast('negative', 'Authentication required. Please log in again.')
    } else {
      toast('negative', 'Unable to load doctors right now. Please try again.')
    }
  } finally {
    doctorLoading.value = false
  }
}

const loadDoctorOccupiedSlots = async () => {
  doctorOccupiedTimes.value = []
  if (!selectedDoctorId.value) return
  if (!form.value.date) return

  const date = toISOFromMDY(form.value.date)
  if (!date) return

  doctorSlotsLoading.value = true
  try {
    const res = await api.get('/operations/appointments/doctor-slots/', {
      params: { doctor_id: selectedDoctorId.value, date }
    })

    const raw = res.data?.occupied_times
    const times = Array.isArray(raw) ? raw : []
    doctorOccupiedTimes.value = times
      .map((t: unknown) => {
        if (typeof t === 'string' || typeof t === 'number') return String(t).slice(0, 5)
        return ''
      })
      .filter((t: string) => /^\d{2}:\d{2}$/.test(t))
  } catch (e) {
    doctorOccupiedTimes.value = []
    const err = e as { response?: { status?: number; data?: { error?: string, message?: string } } }
    const msg = err?.response?.data?.error || err?.response?.data?.message
    toast('negative', msg || 'Unable to load doctor availability. Please try again.')
  } finally {
    doctorSlotsLoading.value = false
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
    toast('negative', message)
  }
}

const onSubmit = async () => {
  const valid = await formRef.value?.validate?.()
  if (valid === false) return
  
  if (selectedDoctorId.value && form.value.date) {
    await loadDoctorOccupiedSlots()
  }

  if (isSlotTaken(form.value.time)) {
    toast('warning', 'This time slot is not available. Please choose another time.')
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
      toast('positive', 'Appointment rescheduled successfully!')
    } else {
      // Create new appointment
      await api.post('/operations/appointments/schedule/', payload)
      toast('positive', 'Appointment scheduled successfully!')
    }
    
    // Reload appointments
    await loadAppointments()
    
    // Reset form and close dialog
    closeScheduleForm()
    
  } catch (e) {
    console.error('Failed to schedule appointment:', e)
    const error = e as { response?: { data?: { error?: string, message?: string } } }
    const errorMessage = error?.response?.data?.error || error?.response?.data?.message || 'Failed to schedule appointment. Please try again.'
    toast('negative', errorMessage)
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
    toast('positive', 'Appointment cancelled successfully!')
    
    // Reload appointments
    await loadAppointments()
    
    closeCancelDialog()
    
  } catch (error) {
    console.error('Failed to cancel appointment:', error)
    toast('negative', 'Failed to cancel appointment. Please try again.')
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
  doctorOccupiedTimes.value = []
}

watch(highContrast, (val) => persistBool('ms_patient_high_contrast', val))
watch(largeText, (val) => persistBool('ms_patient_large_text', val))
watch(darkMode, (val) => {
  persistBool('ms_patient_dark_mode', val)
  $q.dark.set(val)
})

onMounted(() => {
  highContrast.value = readBool('ms_patient_high_contrast')
  largeText.value = readBool('ms_patient_large_text')
  darkMode.value = readBool('ms_patient_dark_mode')
  $q.dark.set(darkMode.value)
})

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
  doctorOccupiedTimes.value = []
  form.value.time = ''
  void loadDoctors()
})

watch([() => selectedDoctorId.value, () => form.value.date], () => {
  form.value.time = ''
  void loadDoctorOccupiedSlots()
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

.schedule-cta-card {
  background: var(--ms-card);
  border: 1px solid var(--ms-border);
  border-radius: 20px;
  box-shadow: var(--ms-shadow);
}

.calendar-shell {
  background: var(--ms-card);
  border: 1px solid var(--ms-border);
  border-radius: 10px;
  box-shadow: 0 2px 14px rgba(15, 23, 42, 0.05);
  overflow: hidden;
}

.calendar-shell-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  padding: 16px;
}

.calendar-shell-title {
  min-width: 220px;
}

.calendar-title {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--ms-text);
}

.calendar-subtitle {
  margin-top: 2px;
  font-size: 12px;
  color: var(--ms-muted);
}

.calendar-shell-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex: 1;
  flex-wrap: wrap;
}

.calendar-search {
  width: min(420px, 100%);
}

.calendar-shell-action-buttons {
  display: flex;
  gap: 8px;
}

.calendar-action-btn {
  border-radius: 6px;
  text-transform: none;
  font-weight: 600;
}

.calendar-stats {
  padding: 14px 16px;
}

.calendar-stats-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.calendar-stat-card {
  border: 1px solid var(--ms-border);
  border-radius: 10px;
  padding: 12px;
  background: var(--ms-card);
  box-shadow: 0 1px 10px rgba(15, 23, 42, 0.04);
  transition: box-shadow 160ms ease, transform 160ms ease, border-color 160ms ease;
}

.calendar-stat-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.10);
}

.calendar-stat-card.is-today {
  border-top: 3px solid rgba(38, 166, 154, 0.95);
}

.calendar-stat-card.is-cancelled {
  border-top: 3px solid rgba(239, 68, 68, 0.95);
}

.calendar-stat-card.is-notifications {
  border-top: 3px solid rgba(245, 158, 11, 0.95);
}

.calendar-stat-icon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  background: rgba(15, 23, 42, 0.04);
  color: rgba(15, 23, 42, 0.72);
}

.ms-dark .calendar-stat-icon {
  background: rgba(230, 237, 246, 0.08);
  color: rgba(230, 237, 246, 0.85);
}

.calendar-stat-label {
  margin-top: 8px;
  font-size: 11px;
  color: var(--ms-muted);
}

.calendar-stat-value {
  margin-top: 2px;
  font-size: 18px;
  font-weight: 800;
  color: var(--ms-text);
}

.calendar-stat-meta {
  margin-top: 2px;
  font-size: 11px;
  color: var(--ms-muted);
  line-height: 1.35;
}

.calendar-card {
  padding: 14px 16px 18px;
}

.calendar-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.calendar-topbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.calendar-topbar-check {
  width: 18px;
  height: 18px;
  border-radius: 4px;
  border: 1px solid rgba(15, 23, 42, 0.18);
  background: rgba(15, 23, 42, 0.02);
}

.ms-dark .calendar-topbar-check {
  border-color: rgba(230, 237, 246, 0.18);
  background: rgba(230, 237, 246, 0.06);
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
  text-transform: none;
  font-weight: 600;
}

.calendar-nav-btn {
  color: rgba(15, 23, 42, 0.65);
}

.ms-dark .calendar-nav-btn {
  color: rgba(230, 237, 246, 0.75);
}

.calendar-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.calendar-view-tabs {
  display: inline-flex;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 7px;
  overflow: hidden;
  background: rgba(15, 23, 42, 0.02);
}

.ms-dark .calendar-view-tabs {
  border-color: rgba(230, 237, 246, 0.14);
  background: rgba(230, 237, 246, 0.06);
}

.calendar-tab {
  appearance: none;
  border: 0;
  background: transparent;
  padding: 6px 12px;
  font-size: 11px;
  font-weight: 700;
  color: rgba(15, 23, 42, 0.72);
  cursor: pointer;
  transition: background-color 160ms ease, color 160ms ease;
}

.ms-dark .calendar-tab {
  color: rgba(230, 237, 246, 0.82);
}

.calendar-tab.is-active {
  background: var(--ms-card);
  color: rgba(13, 148, 136, 0.95);
}

.calendar-tab:focus-visible {
  outline: 3px solid var(--ms-focus);
  outline-offset: -3px;
}

.calendar-toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.calendar-mini-toggles {
  display: inline-flex;
  gap: 6px;
}

.mini-toggle {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  border: 1px solid rgba(15, 23, 42, 0.16);
  background: rgba(15, 23, 42, 0.02);
}

.ms-dark .mini-toggle {
  border-color: rgba(230, 237, 246, 0.16);
  background: rgba(230, 237, 246, 0.06);
}

.calendar-chip-btn {
  border-radius: 7px;
  text-transform: none;
  font-weight: 700;
  font-size: 11px;
}

.calendar-chip-btn.is-primary {
  background: rgba(13, 148, 136, 0.95);
  color: #ffffff;
}

.calendar-grid {
  margin-top: 10px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 10px;
  overflow: hidden;
}

.calendar-dow {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  background: rgba(15, 23, 42, 0.02);
  border-bottom: 1px solid rgba(15, 23, 42, 0.12);
}

.ms-dark .calendar-dow {
  background: rgba(230, 237, 246, 0.05);
  border-bottom-color: rgba(230, 237, 246, 0.12);
}

.calendar-dow-cell {
  padding: 8px 10px;
  font-size: 10px;
  font-weight: 800;
  color: rgba(15, 23, 42, 0.65);
  text-align: left;
}

.ms-dark .calendar-dow-cell {
  color: rgba(230, 237, 246, 0.75);
}

.calendar-week {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
}

.calendar-day {
  min-height: 86px;
  padding: 8px 8px 10px;
  border-right: 1px solid rgba(15, 23, 42, 0.10);
  border-bottom: 1px solid rgba(15, 23, 42, 0.10);
  background: var(--ms-card);
  transition: background-color 160ms ease, border-color 160ms ease;
  cursor: pointer;
  outline: none;
}

.calendar-week .calendar-day:nth-child(7n) {
  border-right: 0;
}

.calendar-weeks .calendar-week:last-child .calendar-day {
  border-bottom: 0;
}

.ms-dark .calendar-day {
  border-right-color: rgba(230, 237, 246, 0.10);
  border-bottom-color: rgba(230, 237, 246, 0.10);
}

.calendar-day:hover {
  background: rgba(13, 148, 136, 0.06);
}

.calendar-day:focus-visible {
  outline: 3px solid var(--ms-focus);
  outline-offset: -2px;
}

.calendar-day.is-out {
  background: rgba(15, 23, 42, 0.01);
  color: rgba(15, 23, 42, 0.45);
}

.ms-dark .calendar-day.is-out {
  background: rgba(230, 237, 246, 0.02);
  color: rgba(230, 237, 246, 0.45);
}

.calendar-day-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.calendar-day-num {
  font-size: 11px;
  font-weight: 800;
  width: 22px;
  height: 22px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  color: rgba(15, 23, 42, 0.72);
}

.ms-dark .calendar-day-num {
  color: rgba(230, 237, 246, 0.82);
}

.calendar-day.is-today .calendar-day-num {
  border: 1px solid rgba(13, 148, 136, 0.95);
  color: rgba(13, 148, 136, 0.95);
  background: rgba(13, 148, 136, 0.08);
}

.calendar-day-dot {
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: rgba(13, 148, 136, 0.95);
}

.calendar-day-events {
  margin-top: 6px;
  display: grid;
  gap: 6px;
}

.calendar-event {
  appearance: none;
  border: 1px solid rgba(13, 148, 136, 0.10);
  border-left: 3px solid rgba(13, 148, 136, 0.85);
  background: rgba(13, 148, 136, 0.10);
  color: rgba(15, 23, 42, 0.92);
  border-radius: 6px;
  padding: 6px 8px;
  font-size: 10px;
  font-weight: 700;
  line-height: 1.2;
  text-align: left;
  cursor: pointer;
  transition: transform 120ms ease, background-color 160ms ease, border-color 160ms ease;
}

.ms-dark .calendar-event {
  color: rgba(230, 237, 246, 0.90);
  border-color: rgba(13, 148, 136, 0.18);
  background: rgba(13, 148, 136, 0.12);
}

.calendar-event:hover {
  transform: translateY(-1px);
  background: rgba(13, 148, 136, 0.16);
}

.calendar-event:focus-visible {
  outline: 3px solid var(--ms-focus);
  outline-offset: 2px;
}

.calendar-event-title {
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.calendar-more {
  font-size: 10px;
  color: var(--ms-muted);
}

.calendar-weekview {
  margin-top: 12px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 10px;
  overflow: hidden;
}

.calendar-weekview-head {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  background: rgba(15, 23, 42, 0.02);
  border-bottom: 1px solid rgba(15, 23, 42, 0.12);
}

.calendar-weekview-headcell {
  padding: 8px 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.weekview-dow {
  font-size: 10px;
  font-weight: 800;
  color: rgba(15, 23, 42, 0.65);
}

.weekview-daynum {
  width: 22px;
  height: 22px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  font-size: 11px;
  font-weight: 800;
  color: rgba(15, 23, 42, 0.72);
}

.weekview-daynum.is-today {
  border: 1px solid rgba(13, 148, 136, 0.95);
  color: rgba(13, 148, 136, 0.95);
  background: rgba(13, 148, 136, 0.08);
}

.calendar-weekview-body {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
}

.calendar-weekview-col {
  padding: 10px;
  min-height: 160px;
  border-right: 1px solid rgba(15, 23, 42, 0.10);
  display: grid;
  align-content: start;
  gap: 8px;
}

.calendar-weekview-col:nth-child(7n) {
  border-right: 0;
}

.calendar-dayview {
  margin-top: 12px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 10px;
  padding: 14px;
}

.calendar-dayview-title {
  font-size: 12px;
  font-weight: 800;
  color: var(--ms-text);
}

.calendar-empty {
  margin-top: 10px;
  color: var(--ms-muted);
  font-size: 12px;
}

.calendar-dayview-events {
  margin-top: 10px;
  display: grid;
  gap: 10px;
}

.calendar-event.is-dayview {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-size: 12px;
}

.calendar-event-time {
  font-weight: 800;
  color: rgba(15, 23, 42, 0.75);
}

.ms-dark .calendar-event-time {
  color: rgba(230, 237, 246, 0.75);
}

.appointment-actions-card {
  width: 520px;
  max-width: 96vw;
  border-radius: 20px;
  background: var(--ms-card);
  border: 1px solid var(--ms-border);
}

.dialog-card {
  width: 100%;
  max-width: 860px;
  border-radius: 20px;
  background: var(--ms-card);
  border: 1px solid var(--ms-border);
}

.cancel-card {
  width: 460px;
  max-width: 95vw;
  border-radius: 20px;
  background: var(--ms-card);
  border: 1px solid var(--ms-border);
}

.appointment-card {
  border: 1px solid var(--ms-border);
  border-radius: 18px;
  background: var(--ms-card);
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
  transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
}

.appointment-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--ms-shadow-hover);
}

.cancelled-card {
  opacity: 0.78;
}

.completed-card {
  border-color: rgba(46, 125, 50, 0.25);
}

.ms-banner {
  background: rgba(38, 166, 154, 0.08);
  border: 1px solid rgba(38, 166, 154, 0.25);
  color: var(--ms-text);
}

.time-slot-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.time-slot-btn {
  min-height: 44px;
  border-radius: 14px;
  border: 1px solid var(--ms-border);
  background: var(--ms-card);
  transition: transform 160ms ease, background-color 160ms ease, border-color 160ms ease;
}

.time-slot-btn.is-selected {
  border-color: rgba(38, 166, 154, 0.6);
  background: rgba(38, 166, 154, 0.12);
  transform: translateY(-1px);
}

.time-slot-btn.is-disabled {
  opacity: 0.55;
}

.touch-target {
  min-height: 44px;
}

.ms-focusable:focus-visible {
  outline: 3px solid var(--ms-focus);
  outline-offset: 2px;
}

.rounded-lg {
  border-radius: 16px;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (max-width: 600px) {
  .time-slot-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .max-w-4xl {
    max-width: 100%;
  }
  .dialog-card {
    max-width: 95vw;
  }
  .calendar-shell-header {
    align-items: flex-start;
  }
  .calendar-stats-grid {
    grid-template-columns: 1fr;
  }
  .calendar-grid {
    overflow-x: auto;
  }
  .calendar-dow,
  .calendar-week {
    min-width: 720px;
  }
}
</style>
