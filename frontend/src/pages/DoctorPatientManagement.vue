<template>
  <q-layout view="hHh Lpr fFf">
    <!-- Standardized Header Component -->
    <DoctorHeader @toggle-drawer="rightDrawerOpen = !rightDrawerOpen" />

    <!-- Standardized Sidebar Component -->
    <DoctorSidebar v-model="rightDrawerOpen" active-route="patients" />

    <q-page-container class="page-container-with-fixed-header safe-area-bottom role-body-bg">
      <!-- Main Content -->
      <div class="patient-management-content">
        <!-- Header Section -->
        <div class="greeting-section">
          <q-card class="greeting-card">
            <q-card-section class="greeting-content">
              <div class="greeting-text">
                <h2 class="greeting-title">Patient Management</h2>
                <p class="greeting-subtitle">Manage your patients and their medical records</p>
              </div>
            </q-card-section>
          </q-card>
        </div>

        <!-- Patient Management Cards -->
        <div class="management-cards-grid">
          <!-- Left Column: Patient List -->
          <div class="left-column">
            <q-card class="dashboard-card patient-list-card">
              <q-card-section class="card-header">
                <h5 class="card-title">Patient List</h5>
                <q-btn color="primary" icon="refresh" size="sm" @click="loadPatients" :loading="loading" />
              </q-card-section>

              <q-card-section class="card-content">
                <q-banner dense class="q-mb-sm" icon="info" inline-actions>
                  Select a patient from the list to view or manage details. Archived patients are hidden from selection.
                </q-banner>
                <div class="row items-center q-col-gutter-sm q-mb-sm">
                  <div class="col-12 col-sm-3">
                    <q-select
                      v-model="selectedFormType"
                      :options="formTypeOptions"
                      outlined
                      dense
                      label="Form Type"
                      emit-value
                      map-options
                      aria-label="Select form type"
                      @update:model-value="onFormTypeChange"
                    />
                  </div>
                  <div class="col-6 col-sm-2">
                    <q-select
                      v-model="sortKey"
                      :options="sortOptions"
                      outlined
                      dense
                      label="Sort by"
                      emit-value
                      map-options
                      aria-label="Sort patients"
                    />
                  </div>
                  <div class="col-6 col-sm-2">
                    <q-select
                      v-model="sortOrder"
                      :options="orderOptions"
                      outlined
                      dense
                      label="Order"
                      emit-value
                      map-options
                      aria-label="Sort order"
                    />
                  </div>
                </div>
              </q-card-section>

              <q-card-section class="card-content">
                <div v-if="loading" class="loading-section">
                  <q-spinner color="primary" size="2em" />
                  <p class="loading-text">Loading patients...</p>
                </div>

                <div v-else-if="patients.length === 0" class="empty-section">
                  <q-icon name="people" size="48px" color="grey-5" />
                  <p class="empty-text">No patients found</p>
                </div>

                <div v-else class="patients-list">
                  <div
                    v-for="patient in filteredPatients"
                    :key="patient.id"
                    :class="['patient-card', { selected: selectedPatient && selectedPatient.id === patient.id }]"
                    :aria-selected="selectedPatient && selectedPatient.id === patient.id ? 'true' : 'false'"
                    @click="selectPatient(patient)"
                  >
                    <div class="patient-avatar">
                      <q-avatar size="50px">
                        <img
                          v-if="patient.profile_picture"
                          :src="patient.profile_picture.startsWith('http') ? patient.profile_picture : `http://localhost:8000${patient.profile_picture}`"
                          :alt="patient.full_name"
                          @error="patient.profile_picture = ''"
                        />
                        <div v-else class="avatar-initials">{{ getInitials(patient.full_name || 'User') }}</div>
                      </q-avatar>
                    </div>

                    <div class="patient-info">
                      <h6 class="patient-name">{{ patient.full_name }}</h6>
                      <p class="patient-details">
                        Assigned by: {{ patient.assigned_by || 'N/A' }}
                      </p>
                      <p class="patient-condition">
                        {{ patient.assignment_reason || 'No reason specified' }}
                      </p>
                      <div class="patient-status">
                        <q-chip 
                          :color="patient.assignment_status === 'pending' ? 'orange' : 
                                  patient.assignment_status === 'accepted' ? 'blue' : 
                                  patient.assignment_status === 'in_progress' ? 'purple' : 
                                  patient.assignment_status === 'completed' ? 'green' : 'grey'" 
                          text-color="white" 
                          size="sm"
                        > 
                          {{ patient.assignment_status || 'pending' }} 
                        </q-chip>
                        <q-chip 
                          v-if="patient.priority && patient.priority !== 'normal'"
                          :color="patient.priority === 'high' ? 'red' : 'orange'" 
                          text-color="white" 
                          size="sm"
                          class="q-ml-xs"
                        > 
                          {{ patient.priority }} priority
                        </q-chip>
                      </div>
                    </div>

                    <div class="patient-actions">
                      <q-btn
                        flat
                        round
                        icon="visibility"
                        color="primary"
                        size="sm"
                        @click.stop="viewPatientDetails(patient)"
                        unelevated
                      >
                        <q-tooltip>View Details</q-tooltip>
                      </q-btn>
                      <q-btn
                        flat
                        round
                        icon="edit"
                        color="secondary"
                        size="sm"
                        @click.stop="editPatient(patient)"
                        unelevated
                      >
                        <q-tooltip>Edit Patient</q-tooltip>
                      </q-btn>
                      <q-btn
                        flat
                        round
                        icon="assignment"
                        color="primary"
                        size="sm"
                        @click.stop="openNurseIntake(patient)"
                        unelevated
                      >
                        <q-tooltip>Nurse Intake</q-tooltip>
                      </q-btn>
                      <q-btn
                        flat
                        round
                        icon="archive"
                        color="warning"
                        size="sm"
                        @click.stop="archivePatient(patient)"
                        unelevated
                      >
                        <q-tooltip>Archive</q-tooltip>
                      </q-btn>
                      <!-- Forms dropdown removed per request to keep UI clean -->
                    </div>
                  </div>
                </div>
              </q-card-section>
            </q-card>
          </div>

          <!-- Right Column: Statistics -->
          <div class="right-column">
            <!-- Patient Statistics Card -->
            <q-card class="dashboard-card statistics-card q-mb-lg">
              <q-card-section class="card-content">
                <div class="card-text">
                  <div class="card-title">Patient Statistics</div>
                </div>
              </q-card-section>

              <q-card-section class="card-content">
                <div class="stats-grid">
                  <div class="stat-item">
                    <div class="stat-number">{{ stats.total_patients }}</div>
                    <div class="stat-label">Total Patients</div>
                  </div>
                  <div class="stat-item">
                    <div class="stat-number">{{ stats.active_cases }}</div>
                    <div class="stat-label">Active Patients</div>
                  </div>
                </div>
              </q-card-section>
              
              <q-card-section class="card-content">
                <div v-if="statsLoading" class="loading-section" aria-live="polite">
                  <q-spinner color="primary" size="2em" />
                  <p class="loading-text">Updating statistics...</p>
                </div>
                <div v-else class="stats-chart" aria-label="Patient statistics chart">
                  <div class="chart-row">
                    <div class="chart-label">Active</div>
                    <q-linear-progress :value="stats.active_rate" color="blue" size="md" aria-label="Active cases rate" />
                  </div>
                  <div class="chart-row">
                    <div class="chart-label">Recovery</div>
                    <q-linear-progress :value="stats.recovery_rate" color="green" size="md" aria-label="Recovery rate" />
                  </div>
                </div>
              </q-card-section>
            </q-card>



            <!-- List of Available Nurses Card -->
            <q-card class="dashboard-card nurses-card q-mt-lg">
              <q-card-section class="card-content">
                <div class="card-text">
                  <div class="card-title">Available Nurses</div>
                  <div class="card-description">Nurses who can assign patients</div>
                </div>
                <div class="card-icon">
                  <q-icon name="local_hospital" size="2.2rem" />
                </div>
              </q-card-section>
              <q-card-section class="card-content">
                <div v-if="nursesLoading" class="loading-section">
                  <q-spinner color="primary" size="2em" />
                  <p class="loading-text">Loading nurses...</p>
                </div>
                <div v-else-if="availableNurses.length === 0" class="empty-section">
                  <q-icon name="local_hospital" size="48px" color="grey-5" />
                  <p class="empty-text">No available nurses</p>
                </div>
                <div v-else class="nurses-list">
                  <div v-for="(nurse, idx) in paginatedNurses" :key="String(nurse.id ?? nurse.email ?? nurse.full_name ?? idx)" class="nurse-row">
                    <div class="nurse-avatar">
                      <q-avatar size="40px" color="teal-8" text-color="white">
                        {{ getInitials(nurse.full_name || '') }}
                      </q-avatar>
                    </div>
                    <div class="nurse-info">
                      <div class="nurse-name">{{ nurse.full_name }}</div>
                      <div class="nurse-details">
                        Department: {{ nurse.department || nurse.specialization || '—' }}
                        <span class="separator">•</span>
                        <q-chip
                          :color="getAvailabilityColor(nurse.availability ?? nurse.status ?? 'Available')"
                          text-color="white"
                          size="sm"
                          :label="(nurse.availability ?? nurse.status ?? 'Available')"
                          dense
                          class="status-chip"
                        />
                      </div>
                      <div class="nurse-contact">Contact: {{ nurse.email || '—' }}</div>
                    </div>
                  </div>
                  <div class="row items-center justify-between q-mt-sm" aria-label="Nurses pagination controls">
                    <div class="text-caption text-grey-7">
                      Showing {{ nursesStartIndex }}–{{ nursesEndIndex }} of {{ availableNurses.length }}
                    </div>
                    <q-pagination
                      v-model="nursesPage"
                      :max="nurseTotalPages"
                      max-pages="7"
                      boundary-numbers
                      size="sm"
                      color="primary"
                      aria-label="Available nurses pagination"
                    />
                  </div>
                </div>
              </q-card-section>
            </q-card>

            <!-- Medical Records Card removed per refactor -->

            <!-- Record Preview Dialog removed per refactor -->


          </div>
        </div>
      </div>
    </q-page-container>



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



    <!-- Doctor Form Dialog -->
    <q-dialog v-model="showDoctorFormDialog" persistent :maximized="$q.screen.lt.md" transition-show="slide-up" transition-hide="slide-down">
      <q-card class="modal-card form-dialog-card" style="width: 800px; max-width: 95vw">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">{{ formDialogTitle }}</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup aria-label="Close form" @click="closeForm" />
        </q-card-section>
        <q-separator class="q-my-md" />
        <q-card-section class="form-dialog-content" style="max-height: 80vh; overflow: auto;">
          <!-- Patient Info Banner -->
          <q-banner v-if="selectedFormPatient" class="bg-primary text-white q-mb-md">
            <template v-slot:avatar>
              <q-avatar>
                <img :src="selectedFormPatient.profile_picture || '/img/default-avatar.png'" :alt="selectedFormPatient.full_name">
              </q-avatar>
            </template>
            <div class="text-subtitle1">{{ selectedFormPatient?.full_name || selectedFormPatient?.patient_name || '—' }}</div>
            <div class="text-caption">
              Provider: {{ userProfile.full_name }} | Date: {{ formatDateTime(new Date()) }}
            </div>
          </q-banner>

          <!-- H&P Form -->
          <div v-if="selectedFormType === 'hp'" class="hp-form">
            <q-form @submit.prevent="saveDoctorForm" class="q-gutter-md">
              <div class="row q-col-gutter-md">
                <div class="col-12">
                  <q-input
                    v-model="hpForm.chief_complaint"
                    label="Chief Complaint *"
                    outlined
                    :rules="[required('Chief complaint is required')]"
                  />
                </div>
              </div>

              <div class="row q-col-gutter-md">
                <div class="col-12 col-md-6">
                  <q-input
                    v-model="hpForm.hpi"
                    label="History of Present Illness (HPI) *"
                    type="textarea"
                    outlined
                    autogrow
                    :rules="[required('History of present illness is required')]"
                  />
                </div>
                <div class="col-12 col-md-6">
                  <q-input
                    v-model="hpForm.pmh"
                    label="Past Medical History (PMH)"
                    type="textarea"
                    outlined
                    autogrow
                  />
                </div>
              </div>

              <div class="row q-col-gutter-md">
                <div class="col-12 col-md-6">
                  <q-input
                    v-model="hpForm.allergies_medications"
                    label="Allergies & Medications"
                    type="textarea"
                    outlined
                    autogrow
                  />
                </div>
                <div class="col-12 col-md-6">
                  <q-input
                    v-model="hpForm.social_history"
                    label="Social History"
                    type="text"
                    outlined
                  />
                </div>
              </div>

              <div class="row q-col-gutter-md">
                <div class="col-12">
                  <q-input
                    v-model="hpForm.ros_notes"
                    label="Review of Systems (Notes)"
                    type="textarea"
                    outlined
                    autogrow
                  />
                </div>
              </div>

              <q-separator class="q-my-md" />
              <div class="text-subtitle1 q-mb-sm">Physical Examination</div>

              <div class="row q-col-gutter-md">
                <div class="col-12 col-md-6">
                  <q-input
                    v-model="hpForm.pe_general"
                    label="General *"
                    outlined
                    :rules="[required('General examination is required')]"
                  />
                </div>
                <div class="col-12 col-md-6">
                  <q-input
                    v-model="hpForm.pe_heent"
                    label="HEENT"
                    outlined
                  />
                </div>
              </div>

              <div class="row q-col-gutter-md">
                <div class="col-12 col-md-6">
                  <q-input
                    v-model="hpForm.pe_cardiac"
                    label="Cardiac"
                    outlined
                  />
                </div>
                <div class="col-12 col-md-6">
                  <q-input
                    v-model="hpForm.pe_pulmonary"
                    label="Pulmonary"
                    outlined
                  />
                </div>
              </div>

              <div class="row q-col-gutter-md">
                <div class="col-12 col-md-6">
                  <q-input
                    v-model="hpForm.pe_abdomen"
                    label="Abdomen"
                    outlined
                  />
                </div>
                <div class="col-12 col-md-6">
                  <q-input
                    v-model="hpForm.pe_neurologic"
                    label="Neurologic"
                    outlined
                  />
                </div>
              </div>

              <q-separator class="q-my-md" />
              <div class="text-subtitle1 q-mb-sm">Assessment & Plan</div>

              <div class="row q-col-gutter-md">
                <div class="col-12 col-md-6">
                  <q-input
                    v-model="hpForm.assessment"
                    label="Assessment *"
                    type="textarea"
                    outlined
                    autogrow
                    :rules="[required('Assessment is required')]"
                  />
                </div>
                <div class="col-12 col-md-6">
                  <q-input
                    v-model="hpForm.assessment_codes"
                    label="ICD Codes"
                    outlined
                  />
                </div>
              </div>

              <div class="row q-col-gutter-md">
                <div class="col-12">
                  <q-input
                    v-model="hpForm.plan"
                    label="Plan *"
                    type="textarea"
                    outlined
                    autogrow
                    :rules="[required('Plan is required')]"
                  />
                </div>
              </div>

              <div class="row q-col-gutter-md q-mt-md">
                <div class="col-12 flex justify-end">
                  <q-btn label="Clear" type="reset" flat class="q-mr-sm" @click="resetForm(selectedFormType as FormType)" />
                  <q-btn label="Cancel" v-close-popup flat class="q-mr-sm" @click="closeForm" />
                  <q-btn label="Submit" type="submit" color="primary" :loading="formSubmitting" />
                </div>
              </div>
            </q-form>
          </div>

          <!-- SOAP Form -->
          <div v-else-if="selectedFormType === 'soap'" class="soap-form">
            <q-form @submit.prevent="saveDoctorForm" class="q-gutter-md">
              <div class="row q-col-gutter-md">
                <div class="col-12">
                  <q-input
                    v-model="soapForm.subjective"
                    label="Subjective *"
                    type="textarea"
                    outlined
                    autogrow
                  :rules="[required('Subjective information is required')]"
                  />
                </div>
              </div>

              <div class="row q-col-gutter-md">
                <div class="col-12">
                  <q-input
                    v-model="soapForm.objective"
                    label="Objective *"
                    type="textarea"
                    outlined
                    autogrow
                  :rules="[required('Objective information is required')]"
                  />
                </div>
              </div>

              <div class="row q-col-gutter-md">
                <div class="col-12">
                  <q-input
                    v-model="soapForm.assessment"
                    label="Assessment *"
                    type="textarea"
                    outlined
                    autogrow
                  :rules="[required('Assessment is required')]"
                  />
                </div>
              </div>

              <div class="row q-col-gutter-md">
                <div class="col-12">
                  <q-input
                    v-model="soapForm.plan"
                    label="Plan *"
                    type="textarea"
                    outlined
                    autogrow
                  :rules="[required('Plan is required')]"
                  />
                </div>
              </div>

              <div class="row q-col-gutter-md q-mt-md">
                <div class="col-12 flex justify-end">
                  <q-btn label="Clear" type="reset" flat class="q-mr-sm" @click="resetForm(selectedFormType as FormType)" />
                  <q-btn label="Cancel" v-close-popup flat class="q-mr-sm" @click="closeForm" />
                  <q-btn label="Submit" type="submit" color="primary" :loading="formSubmitting" />
                </div>
              </div>
            </q-form>
          </div>

          <!-- Provider Order Sheet -->
          <div v-else-if="selectedFormType === 'orders'" class="q-gutter-md">
            <q-form @submit.prevent="saveDoctorForm" class="order-form">
              <q-select 
                v-model="orderForm.order_type" 
                :options="['Medication','Lab Test','Imaging','Consult','General']" 
                label="Order Type" 
                outlined 
               :rules="[required('Order type is required')]"
              />
              <div v-if="orderForm.order_type === 'Medication'" class="q-gutter-sm">
                <q-input 
                  v-model="orderForm.med_drug_name" 
                  label="Drug Name" 
                  outlined 
                   :rules="[required('Drug name is required')]"
                />
                <div class="row q-col-gutter-sm">
                  <div class="col-6">
                    <q-input 
                      v-model="orderForm.med_dose" 
                      label="Dose" 
                      outlined 
                       :rules="[required('Dose is required')]"
                    />
                  </div>
                  <div class="col-6">
                    <q-input 
                      v-model="orderForm.med_route" 
                      label="Route" 
                      outlined 
                       :rules="[required('Route is required')]"
                    />
                  </div>
                </div>
                <q-input 
                  v-model="orderForm.med_frequency" 
                  label="Frequency" 
                  outlined 
                   :rules="[required('Frequency is required')]"
                />
                <div class="row q-col-gutter-sm">
                  <div class="col-6">
                    <q-input 
                      v-model="orderForm.med_start_date" 
                      label="Start Date" 
                      type="date" 
                      outlined 
                      :rules="[required('Start date is required')]"
                    />
                  </div>
                  <div class="col-6">
                    <q-input 
                      v-model="orderForm.med_stop_date" 
                      label="Stop Date" 
                      type="date" 
                      outlined 
                    />
                  </div>
                </div>
              </div>
              <div v-else-if="orderForm.order_type === 'Lab Test' || orderForm.order_type === 'Imaging'" class="q-gutter-sm">
                <q-input 
                  v-model="orderForm.diag_test_name" 
                  label="Test Name" 
                  outlined 
                   :rules="[required('Test name is required')]"
                />
                <q-input 
                  v-model="orderForm.diag_specimen_type" 
                  label="Site/Specimen Type" 
                  outlined 
                   :rules="[required('Specimen type is required')]"
                />
                <q-input 
                  v-model="orderForm.diag_reason" 
                  label="Reason for Test" 
                  type="textarea" 
                  autogrow 
                  outlined 
                   :rules="[required('Reason is required')]"
                />
                <q-select 
                  v-model="orderForm.diag_priority" 
                  :options="['Stat','Routine']" 
                  label="Priority" 
                  outlined 
                   :rules="[required('Priority is required')]"
                />
              </div>
              <div v-else-if="orderForm.order_type === 'Consult'" class="q-gutter-sm">
                <q-input 
                  v-model="orderForm.consult_specialty" 
                  label="Specialty to Consult" 
                  outlined 
                  :rules="[required('Specialty is required')]"
                />
                <q-input 
                  v-model="orderForm.consult_reason" 
                  label="Reason for Consult" 
                  type="textarea" 
                  autogrow 
                  outlined 
                  :rules="[required('Reason is required')]"
                />
              </div>
              <div v-else-if="orderForm.order_type === 'General'" class="q-gutter-sm">
                <q-select 
                  v-model="orderForm.general_diet" 
                  :options="['Regular','NPO','Diabetic','Low-sodium']" 
                  label="Diet" 
                  outlined 
                />
                <q-select 
                  v-model="orderForm.general_activity_level" 
                  :options="['Bed rest','Light activity','As tolerated']" 
                  label="Activity Level" 
                  outlined 
                />
                <q-input 
                  v-model="orderForm.general_vitals_frequency" 
                  label="Vitals Frequency" 
                  outlined 
                />
                <q-select 
                  v-model="orderForm.general_isolation_status" 
                  :options="['None','Contact','Droplet','Airborne']" 
                  label="Isolation Status" 
                  outlined 
                />
              </div>
              <q-option-group 
                v-model="orderForm.order_status" 
                type="radio" 
                :options="[
                  { label: 'New', value: 'New' },
                  { label: 'Hold', value: 'Hold' },
                  { label: 'Discontinue', value: 'Discontinue' }
                ]" 
                label="Order Status" 
                inline 
                :rules="[required('Order status is required')]"
              />
              
              <div class="row q-col-gutter-md q-mt-md">
                <div class="col-12 flex justify-end">
                  <q-btn label="Clear" type="reset" flat class="q-mr-sm" @click="resetForm(selectedFormType as FormType)" />
                  <q-btn label="Cancel" v-close-popup flat class="q-mr-sm" @click="closeForm" />
                  <q-btn label="Submit" type="submit" color="primary" :loading="formSubmitting" />
                </div>
              </div>
            </q-form>
          </div>

          <!-- Procedure Report -->
          <div v-else-if="selectedFormType === 'procedure'" class="q-gutter-md">
            <q-form @submit.prevent="saveDoctorForm" class="procedure-form">
              <q-input 
                v-model="procedureForm.procedure_name" 
                label="Procedure Name" 
                outlined 
                :rules="[required('Procedure name is required')]"
              />
              <q-input 
                v-model="procedureForm.indications" 
                label="Indications" 
                type="textarea" 
                autogrow 
                outlined 
                :rules="[required('Indications are required')]"
              />
              <q-checkbox 
                v-model="procedureForm.consent_obtained" 
                label="Consent obtained" 
              />
              <q-input 
                v-model="procedureForm.anesthesia" 
                label="Anesthesia" 
                type="text" 
                outlined 
              />
              <q-input 
                v-model="procedureForm.steps" 
                label="Procedure Steps" 
                type="textarea" 
                autogrow 
                outlined 
                :rules="[required('Procedure steps are required')]"
              />
              <q-input 
                v-model="procedureForm.findings" 
                label="Findings" 
                type="textarea" 
                autogrow 
                outlined 
                :rules="[required('Findings are required')]"
              />
              <q-input 
                v-model="procedureForm.complications" 
                label="Complications" 
                type="textarea" 
                autogrow 
                outlined 
              />
              <q-input 
                v-model="procedureForm.disposition_plan" 
                label="Disposition & Plan" 
                type="textarea" 
                autogrow 
                outlined 
                :rules="[required('Disposition plan is required')]"
              />
              
              <div class="row q-col-gutter-md q-mt-md">
                <div class="col-12 flex justify-end">
                  <q-btn label="Clear" type="reset" flat class="q-mr-sm" @click="resetForm(selectedFormType as FormType)" />
                  <q-btn label="Cancel" v-close-popup flat class="q-mr-sm" @click="closeForm" />
                  <q-btn label="Submit" type="submit" color="primary" :loading="formSubmitting" />
                </div>
              </div>
            </q-form>
          </div>
        </q-card-section>
        <q-card-actions align="right" v-if="!['hp', 'soap', 'orders', 'procedure'].includes(selectedFormType as string)">
          <q-btn flat label="Clear" @click="selectedFormType && resetForm(selectedFormType)" />
          <q-btn
            color="primary"
            icon="save"
            label="Save"
            :loading="formSubmitting"
            :disable="formSubmitting"
            @click="saveDoctorForm"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
    <!-- Nurse Intake Dialog -->
    <q-dialog v-model="showNurseIntakeDialog">
      <q-card class="doctor-form-card" style="max-width: 860px; width: 92vw;">
        <q-card-section class="card-header">
          <div class="card-title">Nurse Intake Assessment</div>
        </q-card-section>
        <!-- Inline Patient Demographics positioned on top of intake content -->
        <q-card-section class="card-content">
          <div class="row items-center justify-between q-mb-xs">
            <div class="text-subtitle2">Patient Demographics</div>
            <q-btn flat dense size="sm" icon="refresh" label="Refresh" @click="refreshDemographics" />
          </div>
          <div v-if="demoLoading" class="row items-center q-gutter-sm q-mb-sm">
            <q-spinner color="primary" size="1.5em" />
            <span class="text-caption">Loading demographics...</span>
          </div>
          <div v-else-if="demographics" class="row q-col-gutter-sm q-mb-md demographics-inline">
            <div class="col-12 text-weight-medium">{{ demographicFullName || selectedPatient?.full_name }}</div>
            <div class="col-6"><strong>DOB:</strong> {{ formattedDOB || '—' }}</div>
            <div class="col-6"><strong>Age:</strong> {{ demographicAge || (demographics.age ?? '') || (selectedPatient?.age ?? '') || '—' }}</div>
            <div class="col-6"><strong>Sex:</strong> {{ demographics.sex || selectedPatient?.gender || '—' }}</div>
            <div v-if="demographics.mrn || selectedPatient?.mrn" class="col-6"><strong>MRN:</strong> {{ demographics.mrn || selectedPatient?.mrn }}</div>
            <div class="col-12"><strong>Email:</strong> {{ demographics.email || selectedPatient?.email || '—' }}</div>
          </div>
          <div v-else class="q-mb-md">
            <q-banner dense icon="info">No demographics found</q-banner>
          </div>
        </q-card-section>
        <q-card-section class="card-content">
          <div v-if="nurseIntakeLoading" class="loading-section">
            <q-spinner color="primary" size="2em" />
            <p class="loading-text">Loading assessment...</p>
          </div>
          <div v-else>
            <div v-if="hasNurseIntakeData" class="q-gutter-md">
              <div v-if="nurseIntakeView.chief_complaint">
                <strong>Chief Complaint:</strong> {{ nurseIntakeView.chief_complaint }}
              </div>
              <div v-if="nurseIntakeView.allergies">
                <strong>Allergies:</strong> {{ nurseIntakeView.allergies }}
              </div>
              <div v-if="nurseIntakeView.current_medications">
                <strong>Current Medications:</strong> {{ nurseIntakeView.current_medications }}
              </div>
              <div v-if="nurseIntakeView.medical_history">
                <strong>Medical History:</strong> {{ nurseIntakeView.medical_history }}
              </div>
              <div v-if="nurseIntakeView.assessment_notes">
                <strong>Assessment Notes:</strong> {{ nurseIntakeView.assessment_notes }}
              </div>

              <div class="vitals" v-if="nurseIntakeView.vitals && (nurseIntakeView.vitals.blood_pressure || nurseIntakeView.vitals.heart_rate || nurseIntakeView.vitals.temperature || nurseIntakeView.vitals.respiratory_rate || nurseIntakeView.vitals.oxygen_saturation)">
                <div class="text-subtitle2 q-mb-xs">Vitals</div>
                <div class="row q-col-gutter-sm">
                  <div class="col-12 col-sm-6" v-if="nurseIntakeView.vitals.blood_pressure"><strong>BP:</strong> {{ nurseIntakeView.vitals.blood_pressure }}</div>
                  <div class="col-12 col-sm-6" v-if="nurseIntakeView.vitals.heart_rate"><strong>HR:</strong> {{ nurseIntakeView.vitals.heart_rate }}</div>
                  <div class="col-12 col-sm-6" v-if="nurseIntakeView.vitals.temperature"><strong>Temp:</strong> {{ nurseIntakeView.vitals.temperature }}</div>
                  <div class="col-12 col-sm-6" v-if="nurseIntakeView.vitals.respiratory_rate"><strong>RR:</strong> {{ nurseIntakeView.vitals.respiratory_rate }}</div>
                  <div class="col-12 col-sm-6" v-if="nurseIntakeView.vitals.oxygen_saturation"><strong>SpO₂:</strong> {{ nurseIntakeView.vitals.oxygen_saturation }}</div>
                </div>
              </div>

              
            </div>
            <div v-else class="empty-intake q-pa-md">
              <div class="text-subtitle1 q-mb-sm">No nurse intake data available</div>
              <div class="text-caption text-grey-7 q-mb-md">The nursing team has not recorded an intake assessment for this patient yet.</div>
              
            </div>
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Close" color="primary" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
    <!-- Archive Reason Dialog -->
    <q-dialog v-model="showArchiveDialog">
      <q-card style="min-width: 420px">
        <q-card-section>
          <div class="text-h6">Archive Patient Record</div>
          <div class="text-subtitle2 text-grey-7">Optional: provide an archival reason</div>
        </q-card-section>
        <q-card-section>
          <q-input v-model="archiveReason" type="textarea" label="Archival reason (optional)" autogrow />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="primary" v-close-popup />
          <q-btn unelevated label="Archive" color="warning" @click="confirmArchive" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue';
import { useQuasar } from 'quasar';
import { api } from 'boot/axios';
import { useRouter, useRoute } from 'vue-router';
import type { AxiosError } from 'axios';
import DoctorHeader from '../components/DoctorHeader.vue';
import DoctorSidebar from '../components/DoctorSidebar.vue';
// Form validation helpers
type RuleFn = (val: unknown) => boolean | string;
const isPresent = (val: unknown): boolean => {
  if (val === null || val === undefined) return false;
  if (typeof val === 'string') return val.trim().length > 0;
  if (Array.isArray(val)) return val.length > 0;
  return !!val;
};
const required = (message: string): RuleFn => (val: unknown) => isPresent(val) || message;

// Types
interface Patient {
  id: number;
  user_id: number;
  full_name: string;
  patient_name?: string;
  date_of_birth?: string;
  mrn?: string;
  email?: string;
  age?: number | null;
  gender?: string;
  blood_type?: string;
  medical_condition?: string;
  hospital?: string;
  insurance_provider?: string;
  billing_amount?: number | null;
  room_number?: string;
  admission_type?: string;
  date_of_admission?: string;
  discharge_date?: string | null;
  medication?: string;
  test_results?: string;
  assigned_doctor?: string | null;
  profile_picture?: string | null;
  is_dummy?: boolean;
  assignment_id?: number;
  assignment_status?: string;
  assigned_by?: string;
  assigned_at?: string;
  specialization_required?: string;
  assignment_reason?: string;
  priority?: string;
  accepted_at?: string | null;
  completed_at?: string | null;
}

type DoctorNotification = {
  id: number;
  message: string;
  is_read: boolean;
  created_at: string;
};

// Typed helpers for safer error handling and localStorage parsing
type ApiError = { response?: { data?: { error?: unknown } }; message?: unknown };
type StoredUser = { hospital_name?: string };

// Reactive data
const $q = useQuasar();
const router = useRouter();
const rightDrawerOpen = ref(false);
const loading = ref(false);
const searchText = ref('');
const patients = ref<Patient[]>([]);
const selectedPatient = ref<Patient | null>(null);
const showNotifications = ref(false);





const sortKey = ref<'full_name' | 'age' | 'gender'>('full_name');
const sortOrder = ref<'asc' | 'desc'>('asc');
const sortOptions = [
  { label: 'Name', value: 'full_name' },
  { label: 'Age', value: 'age' },
  { label: 'Gender', value: 'gender' },
];
const orderOptions = [
  { label: 'Ascending', value: 'asc' },
  { label: 'Descending', value: 'desc' },
];

// User profile data
const userProfile = ref<{
  id: number;
  full_name: string;
  specialization?: string;
  role: string;
  profile_picture: string | null;
  verification_status: string;
}>({
  id: 0,
  full_name: '',
  specialization: '',
  role: '',
  profile_picture: null,
  verification_status: '',
});

// Notification system
const notifications = ref<DoctorNotification[]>([]);

const loadNotifications = async (): Promise<void> => {
  try {
    console.log('Loading doctor notifications...');
    const response = await api.get('/operations/notifications/');
    notifications.value = response.data || [];
    console.log('Doctor notifications loaded:', notifications.value.length);
  } catch (error) {
    console.error('Error loading doctor notifications:', error);
    $q.notify({ type: 'negative', message: 'Failed to load notifications' });
  }
};

// Archival dialog state
const showArchiveDialog = ref(false);
const archiveReason = ref('');
const selectedPatientForArchive = ref<Patient | null>(null);

// Nurse Intake dialog state
const showNurseIntakeDialog = ref(false)
const nurseIntakeLoading = ref(false)
const nurseIntakeData = ref<Record<string, unknown>>({})
const hasNurseIntakeData = computed(() => {
  const d = nurseIntakeData.value
  return !!d && Object.keys(d).length > 0
})
// Derive human-readable fields from nurse intake
const nurseIntakeView = computed(() => {
  // Avoid unnecessary assertions; value already typed as Record<string, unknown>
  const d: Record<string, unknown> = nurseIntakeData.value || {}

  const str = (v: unknown): string => {
    if (v === null || v === undefined) return ''
    if (Array.isArray(v)) {
      const parts = v
        .map((item) => {
          if (item === null || item === undefined) return ''
          if (typeof item === 'string') return item.trim()
          if (typeof item === 'number' || typeof item === 'boolean') return String(item)
          if (typeof item === 'object') {
            try { return JSON.stringify(item) } catch { return '' }
          }
          return String(item)
        })
        .filter((s) => s.length > 0)
      return parts.join(', ')
    }
    if (typeof v === 'object') {
      try { return JSON.stringify(v) } catch { return '' }
    }
    if (typeof v === 'string') return v
    if (typeof v === 'number' || typeof v === 'boolean' || typeof v === 'bigint' || typeof v === 'symbol') return String(v)
    // Avoid base-to-string on unknown/function types
    return ''
  }

  // Render allergies in a human-readable form instead of JSON
  const formatAllergies = (v: unknown): string => {
    const toText = (x: unknown): string => {
      if (x === null || x === undefined) return ''
      if (typeof x === 'string') return x.trim()
      if (typeof x === 'number' || typeof x === 'boolean') return String(x)
      return ''
    }

    if (v === null || v === undefined) return ''

    // Array of objects [{substance, reaction}] or [{name, reaction}] → "Penicillin — Rash"
    if (Array.isArray(v)) {
      const items = v
        .map((it) => {
          if (it && typeof it === 'object') {
            const obj = it as Record<string, unknown>
            const substance = toText(obj['substance'] ?? obj['name'])
            const reaction = toText(obj['reaction'])
            if (substance && reaction) return `${substance} — ${reaction}`
            if (substance) return substance
            if (reaction) return reaction
            return ''
          }
          return toText(it)
        })
        .filter((s) => s.length > 0)
      return items.join(', ')
    }

    // Single object {substance, reaction}
    if (typeof v === 'object') {
      const obj = v as Record<string, unknown>
      const substance = toText(obj['substance'] ?? obj['name'])
      const reaction = toText(obj['reaction'])
      if (substance && reaction) return `${substance} — ${reaction}`
      if (substance) return substance
      if (reaction) return reaction
      return ''
    }

    // Fallback: primitives only
    return toText(v)
  }

  const vitalsRaw = (d['vitals'] || d['vital_signs'] || {}) as Record<string, unknown>
  const vitals = {
    blood_pressure: str(vitalsRaw['blood_pressure'] || vitalsRaw['bp']),
    heart_rate: str(vitalsRaw['heart_rate'] || vitalsRaw['pulse']),
    respiratory_rate: str(vitalsRaw['respiratory_rate'] || vitalsRaw['rr']),
    temperature: str(vitalsRaw['temperature'] || vitalsRaw['temp']),
    oxygen_saturation: str(vitalsRaw['oxygen_saturation'] || vitalsRaw['spo2']),
  }

  return {
    chief_complaint: str(d['chief_complaint'] || d['complaint']),
    allergies: formatAllergies(d['allergies'] || d['known_allergies']),
    current_medications: str(d['current_medications'] || d['medications']),
    medical_history: str(d['medical_history'] || d['history']),
    assessment_notes: str(d['assessment_notes'] || d['notes'] || d['nurse_notes']),
    vitals,
  }
})

const openNurseIntake = async (patient: Patient): Promise<void> => {
  try {
    selectedPatient.value = patient
    showNurseIntakeDialog.value = true
    nurseIntakeLoading.value = true
    // Non-blocking specialization mismatch warning
    try {
      const normalizeSpec = (s: string): string => {
        const v = String(s || '').trim().toLowerCase()
        const synonyms: Record<string, string> = {
          'pulmonary medicine': 'pulmonology',
          'respiratory medicine': 'pulmonology',
          'cardiovascular medicine': 'cardiology',
          'ob-gyn': 'gynecology',
          'obgyn': 'gynecology',
        }
        return synonyms[v] || v
      }
      const titleCase = (s: string): string => {
        const tokens = String(s || '').trim().split(/\s+/)
        return tokens.map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
      }

      const requiredSpecRaw = String(patient.specialization_required || '')
      const doctorSpecRaw = String(userProfile.value?.specialization || '')
      const requiredSpec = normalizeSpec(requiredSpecRaw)
      const doctorSpec = normalizeSpec(doctorSpecRaw)
      if (requiredSpec && doctorSpec && requiredSpec !== doctorSpec) {
        console.warn('The specialization is not aligned with the doctor\'s specialization')
        $q.notify({ type: 'warning', message: `Specialization mismatch: patient requires ${titleCase(requiredSpec)}, you are ${titleCase(doctorSpec)}.`, position: 'top' })
      }
    } catch { 
      /* ignore */ 
    }
    const pid = patient.user_id ?? patient.id
    const endpoint = `/users/doctor/patient/${pid}/nurse-intake/`
    const resp = await api.get(endpoint)
    nurseIntakeData.value = resp.data?.data ?? {}
    void api.post('/operations/client-log/', {
      level: 'info',
      message: 'doctor_view_nurse_intake_succeeded',
      route: 'DoctorPatientManagement',
      context: { patient_id: String(pid), has_data: Boolean(nurseIntakeData.value && Object.keys(nurseIntakeData.value).length) }
    }).catch(() => { /* non-blocking */ })
  } catch (error) {
    console.error('Failed to load nurse intake:', error)
    const status = (error as { response?: { status?: number } })?.response?.status
    const msg = status === 403 ? 'Not authorized for this patient' : 'Failed to load nurse intake'
    $q.notify({ type: status === 403 ? 'warning' : 'negative', message: msg, position: 'top' })
    void api.post('/operations/client-log/', {
      level: 'error',
      message: 'doctor_view_nurse_intake_failed',
      route: 'DoctorPatientManagement',
      context: { patient_id: String((patient.user_id ?? patient.id) || ''), status: String(status || ''), error: String(error) }
    }).catch(() => { /* non-blocking */ })
    nurseIntakeData.value = {}
  } finally {
    nurseIntakeLoading.value = false
  }
}

// Archive action from doctor patient list: prompt for optional reason
const archivePatient = (patient: Patient): void => {
  selectedPatientForArchive.value = patient
  archiveReason.value = ''
  showArchiveDialog.value = true
}

const confirmArchive = async (): Promise<void> => {
  if (!selectedPatientForArchive.value) { $q.notify({ type: 'warning', message: 'No patient selected' }); return }
  try {
    const patient = selectedPatientForArchive.value
    const patientUserIdNum = Number(patient.user_id ?? patient.id)
    if (!Number.isFinite(patientUserIdNum)) {
      throw new Error('Invalid patient ID')
    }

    // Derive hospital name from patient or stored user profile
    let hospitalName = patient.hospital || ''
    try {
      const storedUser = JSON.parse(localStorage.getItem('user') || '{}') as StoredUser
      const maybeHospital = typeof storedUser.hospital_name === 'string' ? storedUser.hospital_name : ''
      hospitalName = hospitalName || maybeHospital
    } catch { /* ignore parse errors */ }

    const payload: Record<string, unknown> = {
      patient_id: patientUserIdNum,
      assessment_type: 'full_record',
      assessment_data: { actor: 'doctor', doctor_name: userProfile.value.full_name },
      full_record: true,
      medical_condition: patient.medical_condition || '',
      hospital_name: hospitalName,
      doctor_id: userProfile.value.id,
      specialization: userProfile.value.specialization || 'General',
      archival_reason: archiveReason.value || ''
    }

    await api.post('/operations/archives/create/', payload)

    // Remove from active list immediately (no page refresh)
    patients.value = patients.value.filter(p => (p.user_id ?? p.id) !== (patient.user_id ?? patient.id))

    $q.notify({ type: 'positive', message: 'Patient archived and removed from list' })
    showArchiveDialog.value = false
    selectedPatientForArchive.value = null
    archiveReason.value = ''
    // Optional: navigate to archive view
    // void router.push({ name: 'DoctorPatientArchive' })
  } catch (err) {
    console.error('Archive failed:', err)
    let msg = 'Failed to archive record'
    if (typeof err === 'object' && err !== null) {
      const e = err as ApiError
      const apiMsg = e.response?.data?.error
      if (typeof apiMsg === 'string' && apiMsg.trim()) {
        msg = apiMsg
      } else if (typeof e.message === 'string' && e.message.trim()) {
        msg = e.message
      }
    } else if (typeof err === 'string' && err.trim()) {
      msg = err
    }
    $q.notify({ type: 'negative', message: String(msg) })
  }
}

// loadMedicalRequests removed per refactor

// Available Nurses list
interface NurseSummary {
  id: number | string;
  full_name: string;
  specialization?: string;
  department?: string;
  status?: string;
  availability?: string;
  email?: string | undefined;
  profile_picture?: string | null;
}
 
const availableNurses = ref<NurseSummary[]>([]);
const nursesLoading = ref(false);
const nursesError = ref<string | null>(null);
const nursesCheckedAt = ref<string | null>(null);

// Pagination for Available Nurses (10 per page)
const nursesPage = ref(1);
const nursesPerPage = 10;
const nurseTotalPages = computed(() => {
  const total = availableNurses.value.length;
  return Math.max(1, Math.ceil(total / nursesPerPage));
});
const paginatedNurses = computed(() => {
  const start = (nursesPage.value - 1) * nursesPerPage;
  return availableNurses.value.slice(start, start + nursesPerPage);
});
const nursesStartIndex = computed(() => {
  if (availableNurses.value.length === 0) return 0;
  return (nursesPage.value - 1) * nursesPerPage + 1;
});
const nursesEndIndex = computed(() => {
  const end = nursesPage.value * nursesPerPage;
  return Math.min(availableNurses.value.length, end);
});
watch(availableNurses, (list) => {
  const max = Math.max(1, Math.ceil(list.length / nursesPerPage));
  if (nursesPage.value > max) nursesPage.value = max;
  if (nursesPage.value < 1) nursesPage.value = 1;
});

const getInitials = (name: string): string => {
  const safe = (name || '').trim();
  if (!safe) return 'U';
  const parts = safe.split(/\s+/);
  const initials = parts.slice(0, 2).map(p => (p[0] || '').toUpperCase()).join('');
  return initials || safe.charAt(0).toUpperCase();
};

const getAvailabilityColor = (status: string): string => {
  const s = (status || '').toLowerCase();
  if (s.includes('break')) return 'warning';
  if (s.includes('occupied') || s.includes('busy')) return 'negative';
  if (s.includes('available')) return 'positive';
  return 'primary';
};

// Safe error message extractor to avoid 'any' casts
const getErrorMessage = (e: unknown): string => {
  if (e instanceof Error && typeof e.message === 'string') return e.message;
  if (typeof e === 'object' && e !== null && 'message' in (e as Record<string, unknown>)) {
    const m = (e as { message?: unknown }).message;
    if (typeof m === 'string') return m;
  }
  try { return JSON.stringify(e); } catch { return String(e); }
};

// Demographics state and helpers
type Demographics = {
  mrn?: string; firstName?: string; middleName?: string; lastName?: string;
  dob?: string; age?: number; sex?: string; maritalStatus?: string; nationality?: string;
  homeAddress?: string; cellPhone?: string; homePhone?: string; email?: string;
  emergencyName?: string; emergencyRelationship?: string; emergencyPhone?: string;
}
const demographics = ref<Demographics | null>(null)
const demoLoadError = ref<string | null>(null)
const demoLoading = ref(false)
const DEMO_TTL_MS = 5 * 60 * 1000
const demoCache = new Map<number, { data: Demographics; ts: number }>()

const demographicFullName = computed(() => {
  const d = demographics.value
  if (!d) return ''
  const names = [d.firstName, d.middleName, d.lastName].filter(Boolean)
  return names.join(' ').trim()
})
const formattedDOB = computed(() => {
  const dob = demographics.value?.dob
  if (!dob) return ''
  try { return new Date(dob).toLocaleDateString() } catch { return String(dob) }
})
const demographicAge = computed(() => {
  const dob = demographics.value?.dob
  if (!dob) return ''
  try {
    const d = new Date(dob)
    const diff = Date.now() - d.getTime()
    const ageDt = new Date(diff)
    return Math.abs(ageDt.getUTCFullYear() - 1970)
  } catch { return '' }
})

const mergePatientOverview = (patient: Patient, base: Demographics | null): Demographics => {
  const merged: Demographics = { ...(base || {}) }
  if (!merged.email && patient.email) merged.email = patient.email
  if (!merged.sex && patient.gender) merged.sex = patient.gender
  // No DOB or address in patient list; keep base if present
  return merged
}

const tryLoadDemographicsLocal = (pid: number): Demographics | null => {
  const mainKey = `patient_reg_${pid}`
  const draftKey = `patient_reg_draft_${pid}`
  try {
    const raw = localStorage.getItem(mainKey)
    if (raw) return JSON.parse(raw)
    const draftRaw = localStorage.getItem(draftKey)
    if (draftRaw) return JSON.parse(draftRaw)
  } catch { /* ignore */ }
  return null
}

const loadDemographics = async (): Promise<void> => {
  demoLoadError.value = null
  demographics.value = null
  if (!selectedPatient.value) return

  const pid = Number(selectedPatient.value.id || selectedPatient.value.user_id)
  if (!Number.isFinite(pid)) {
    demoLoadError.value = 'Invalid patient identifier'
    return
  }

  // Use cache when fresh
  const cached = demoCache.get(pid)
  const now = Date.now()
  if (cached && now - cached.ts < DEMO_TTL_MS) {
    demographics.value = cached.data
    return
  }

  demoLoading.value = true
  try {
    // 1) Try localStorage (nurse registration)
    const localData = tryLoadDemographicsLocal(pid)
    let merged = mergePatientOverview(selectedPatient.value, localData)

    // 2) If still empty, attempt minimal overview endpoint to ensure we at least have email
    if (!merged || Object.keys(merged).length === 0) {
      try {
        const resp = await api.get(`/users/doctor/patient/${pid}/forms/`)
        const p = resp.data?.patient
        if (p && typeof p === 'object') {
          const overview: Demographics = {
            email: p.email,
            sex: p.gender,
            dob: p.date_of_birth,
            age: p.age,
          }
          merged = mergePatientOverview(selectedPatient.value, overview)
        }
      } catch { /* non-blocking */ }
    }

    if (!merged || Object.keys(merged).length === 0) {
      demoLoadError.value = 'Demographics not found for selected patient.'
      demographics.value = null
    } else {
      demographics.value = merged
      demoCache.set(pid, { data: merged, ts: Date.now() })
    }
  } catch (e) {
    console.warn('Failed to load demographics', e)
    demoLoadError.value = 'Unable to load demographics; please retry.'
    demographics.value = null
  } finally {
    demoLoading.value = false
  }
}

const refreshDemographics = (): void => {
  if (!selectedPatient.value) return
  const pid = Number(selectedPatient.value.id || selectedPatient.value.user_id)
  demoCache.delete(pid)
  void loadDemographics()
}

// Limited polling with exponential backoff when demographics missing
const loadDemographicsWithBackoff = async (): Promise<void> => {
  await loadDemographics()
  if (!demographics.value) {
    const delays = [1000, 2000, 4000]
    for (const d of delays) {
      await new Promise(res => setTimeout(res, d))
      await loadDemographics()
      if (demographics.value) break
    }
  }
}

watch(selectedPatient, (p) => {
  if (p) {
    void loadDemographicsWithBackoff()
  } else {
    demographics.value = null
    demoLoadError.value = null
  }
})



const loadAvailableNurses = async (): Promise<void> => {
  nursesLoading.value = true;
  nursesError.value = null;
  try {
    // New secured endpoint dedicated for nurse availability, includes timestamp and shift info
    const url = `/operations/availability/nurses/`;
    const response = await api.get(url);
    type ApiNurse = {
      id: number | string;
      full_name: string;
      email?: string;
      department?: string;
      availability?: string;
      on_duty?: boolean;
    };
    const nurses: ApiNurse[] = Array.isArray(response.data?.nurses)
      ? (response.data.nurses as ApiNurse[])
      : [];
    const checkedAt = String(response.data?.checked_at || '');

    const list: NurseSummary[] = nurses.map((n: ApiNurse) => ({
      id: n.id,
      full_name: n.full_name,
      department: n.department || 'General',
      status: n.on_duty ? 'On Duty' : 'Off Duty',
      availability: n.availability || (n.on_duty ? 'Available' : 'Off Duty'),
      email: n.email || '',
      profile_picture: null,
    } as NurseSummary));
    availableNurses.value = list;

    // Cache for fallback and auditing
    localStorage.setItem('available_nurses', JSON.stringify(list));
    if (checkedAt) {
      localStorage.setItem('available_nurses_checked_at', checkedAt);
      nursesCheckedAt.value = checkedAt;
    }
    // Optional: lightweight client log for success
    void api.post('/operations/client-log/', {
      level: 'info',
      message: 'loadAvailableNurses succeeded',
      route: 'DoctorPatientManagement',
      context: { count: list.length, checked_at: checkedAt }
    }).catch(() => { /* non-blocking */ });
  } catch (error) {
    console.error('Failed to load available nurses:', error);
    const msg = getErrorMessage(error);
    nursesError.value = msg || 'Unable to load nurses';
    $q.notify({ type: 'negative', message: 'Failed to load available nurses', position: 'top' });
    void api.post('/operations/client-log/', {
      level: 'error',
      message: 'loadAvailableNurses failed',
      route: 'DoctorPatientManagement',
      context: { error: String(error) }
    }).catch(() => { /* non-blocking */ });
    // Try to use cached data as fallback
    try {
      const cached = localStorage.getItem('available_nurses');
      availableNurses.value = cached ? (JSON.parse(cached) as NurseSummary[]) : [];
      const cachedTs = localStorage.getItem('available_nurses_checked_at');
      nursesCheckedAt.value = cachedTs || null;
    } catch {
      availableNurses.value = [];
    }
  } finally {
    nursesLoading.value = false;
  }
};

// Patients filtering and statistics
const filteredPatients = computed(() => {
  let list = patients.value;
  if (searchText.value) {
    const search = searchText.value.toLowerCase();
    list = list.filter(
      (patient) =>
        patient.full_name.toLowerCase().includes(search) ||
        (patient.medical_condition || '').toLowerCase().includes(search) ||
        (patient.hospital || '').toLowerCase().includes(search),
    );
  }
  const key = sortKey.value;
  const dir = sortOrder.value === 'desc' ? -1 : 1;
  const toComparable = (p: Patient) => {
    if (key === 'age') return p.age ?? 0;
    const raw = p[key as keyof Patient];
    if (typeof raw === 'string') return raw.toLowerCase();
    if (typeof raw === 'number') return String(raw).toLowerCase();
    return '';
  };
  return [...list].sort((a: Patient, b: Patient) => {
    const av = toComparable(a);
    const bv = toComparable(b);
    if (av < bv) return -1 * dir;
    if (av > bv) return 1 * dir;
    return 0;
  });
});


// Assignment-based statistics removed; card now uses aggregated `stats` only

// Patient statistics state and loader
const stats = ref<{ total_patients: number; active_cases: number; recovery_rate: number; active_rate: number }>({ total_patients: 0, active_cases: 0, recovery_rate: 0, active_rate: 0 })
const statsLoading = ref(false)

const loadDoctorStats = async (): Promise<void> => {
  statsLoading.value = true
  try {
    // Try backend dashboard stats first
    type DashboardStats = {
      total_patients?: number;
      patients_total?: number;
      active_cases?: number;
      pending_cases?: number;
      recovered_cases?: number;
      completed_cases?: number;
    };
    const res = await api.get('/operations/dashboard/stats/').catch(() => ({ data: null as DashboardStats | null }))
    const data = (res as { data: DashboardStats | null }).data
    if (data && typeof data === 'object') {
      const total = Number(data.total_patients ?? data.patients_total ?? 0)
      const active = Number(data.active_cases ?? data.pending_cases ?? 0)
      const recovered = Number(data.recovered_cases ?? data.completed_cases ?? 0)
      const denom = Math.max(total, 1)
      stats.value = {
        total_patients: total,
        active_cases: active,
        recovery_rate: Math.min(1, Math.max(0, recovered / denom)),
        active_rate: Math.min(1, Math.max(0, active / denom))
      }
    } else {
      // Fallback: compute from current patients list
      const total = patients.value.length
      const active = patients.value.filter(p => ['accepted', 'in_progress'].includes(String(p.assignment_status))).length
      const completed = patients.value.filter(p => String(p.assignment_status) === 'completed').length
      const denom = Math.max(total, 1)
      stats.value = {
        total_patients: total,
        active_cases: active,
        recovery_rate: Math.min(1, Math.max(0, completed / denom)),
        active_rate: Math.min(1, Math.max(0, active / denom))
      }
    }
  } catch (error) {
    console.error('Failed to load doctor stats:', error)
    $q.notify({ type: 'negative', message: 'Failed to load patient statistics', position: 'top' })
  } finally {
    statsLoading.value = false
  }
}

// Medical records UI and loader removed per refactor

// Patient assignment data loading and actions
const loadPatients = async () => {
  loading.value = true;
  try {
    // Load only assigned patients from the assignment API
    const response = await api.get('/operations/doctor/assignments/');
    if (response.data && Array.isArray(response.data)) {
      // Transform assignment data to patient format
      patients.value = response.data.map((assignment: {
        id: number;
        patient_id: number;
        patient_name: string;
        status: string;
        assigned_by_name: string;
        assigned_at: string;
        specialization_required: string;
        assignment_reason: string;
        priority: string;
        accepted_at: string | null;
        completed_at: string | null;
      }) => ({
        id: assignment.patient_id,
        user_id: assignment.patient_id,
        full_name: assignment.patient_name,
        patient_name: assignment.patient_name,
        assignment_id: assignment.id,
        assignment_status: assignment.status,
        assigned_by: assignment.assigned_by_name,
        assigned_at: assignment.assigned_at,
        specialization_required: assignment.specialization_required,
        assignment_reason: assignment.assignment_reason,
        priority: assignment.priority,
        accepted_at: assignment.accepted_at,
        completed_at: assignment.completed_at,
        // Default patient fields for compatibility
        medical_condition: '',
        blood_type: '',
        hospital: '',
        room_number: '',
        discharge_date: null,
        is_dummy: false
      }));
      console.log('Assigned patients loaded:', patients.value.length, 'User role:', userProfile.value.role);
      // Try preselecting patient based on route query parameters
      try {
        const route = useRoute();
        const q = route.query as Record<string, string | string[]>;
        const pidRaw = q.patientId ?? q.patient_id;
        const pnameRaw = q.patientName ?? q.patient_name;
        let candidate: Patient | undefined;
        if (pidRaw) {
          const pid = Number(Array.isArray(pidRaw) ? pidRaw[0] : pidRaw);
          candidate = patients.value.find(p => p.id === pid || p.user_id === pid);
        }
        if (!candidate && pnameRaw) {
          const pname = String(Array.isArray(pnameRaw) ? pnameRaw[0] : pnameRaw).toLowerCase();
          candidate = patients.value.find(p => (p.full_name || p.patient_name || '').toLowerCase() === pname);
        }
        if (candidate) {
          selectPatient(candidate);
          $q.notify({ type: 'info', message: `Preloaded patient: ${candidate.full_name}`, position: 'top' });
        }
      } catch (e) {
        console.warn('Route-based preselection failed', e);
      }
      const first = patients.value[0];
      if (first) { void loadVerificationStatus(first); }
    } else {
      patients.value = [];
      console.log('No patient assignments found');
    }
  } catch (error) {
    console.error('Failed to load patient assignments:', error);
    $q.notify({ type: 'negative', message: 'Failed to load patient assignments', position: 'top' });
    patients.value = [];
    void api.post('/operations/client-log/', {
      level: 'error',
      message: 'loadPatients failed',
      route: 'DoctorPatientManagement',
      context: { error: String(error) },
    });
  } finally {
    loading.value = false;
  }
};

const selectPatient = (patient: Patient) => {
  selectedPatient.value = patient;
  if (selectedPatient.value) {
    console.log('Selected patient id:', selectedPatient.value.id);
    void loadVerificationStatus(patient);
  }
};

// Verification status for selected patient
interface VerificationStatus {
  input: {
    patient_user_id: number;
    patient_profile_id: number;
    doctor_user_id: number;
    doctor_profile_id: number;
  };
  persistence: {
    assignments_count: number;
    appointments_count: number;
    archives_count: number;
  };
  transmission: {
    recent_notification_present: boolean;
    recent_notification_message: string | null;
    recent_notification_at: string | null;
  };
  mapping: {
    assignment_statuses: string[];
    appointment_statuses: string[];
  };
}
const verificationStatus = ref<VerificationStatus | null>(null);

const loadVerificationStatus = async (patient: Patient) => {
  try {
    const pid = Number(patient.user_id ?? patient.id);
    const did = userProfile.value.id;
    const resp = await api.get(`/operations/verification-status/?patient_id=${pid}&doctor_id=${did}`);
    verificationStatus.value = resp.data as VerificationStatus;
    $q.notify({
      type: 'positive',
      message: `Data availability: assignments ${resp.data?.persistence?.assignments_count ?? 0}, archives ${resp.data?.persistence?.archives_count ?? 0}`,
      position: 'top',
      timeout: 2500,
    });
    void api.post('/operations/client-log/', {
      level: 'info',
      message: 'doctor verification fetched',
      route: 'DoctorPatientManagement',
      context: {
        patient_id: pid,
        doctor_id: did,
        counts: resp.data?.persistence ?? {},
      },
    });
  } catch (error) {
    console.error('Verification status error:', error);
    $q.notify({ type: 'warning', message: 'Failed to verify data availability', position: 'top' });
    void api.post('/operations/client-log/', {
      level: 'error',
      message: 'doctor verification failed',
      route: 'DoctorPatientManagement',
      context: {
        patient_id: patient.user_id ?? patient.id,
        doctor_id: userProfile.value.id,
        error: String(error),
      },
    });
  }
};

const viewPatientDetails = (patient: Patient) => {
  // Ensure the clicked patient is selected so demographics load and bind correctly
  selectedPatient.value = patient;
  // Open the nurse intake assessment dialog
  void openNurseIntake(patient)
};

const editPatient = (patient: Patient) => {
  const currentId = selectedPatient.value?.id;
  console.log('Editing patient:', patient.full_name, 'Currently selected:', currentId);
  $q.notify({ type: 'info', message: `Editing ${patient.full_name}`, position: 'top' });
};

const fetchUserProfile = async () => {
  try {
    const response = await api.get('/users/profile/');
    const userData = response.data.user;

    // Prefer doctor_profile specialization; ensure strings only
    const docSpec = typeof userData?.doctor_profile?.specialization === 'string'
      ? userData.doctor_profile.specialization
      : '';

    // In doctor-facing components, do not let role be coerced by stale data
    const roleFromApi = typeof userData?.role === 'string' ? userData.role : 'doctor';
    const safeRole = roleFromApi === 'doctor' ? 'doctor' : 'doctor';

    userProfile.value = {
      id: userData.id,
      full_name: userData.full_name,
      specialization: docSpec,
      role: safeRole,
      profile_picture: userData.profile_picture || null,
      verification_status: userData.verification_status,
    };

    if (roleFromApi !== 'doctor') {
      console.warn('Profile API returned non-doctor role on doctor page; enforcing doctor context. Received:', roleFromApi);
    }

    console.log('Loaded user profile role:', userProfile.value.role);
  } catch (error) {
    console.error('Failed to fetch user profile:', error);
  }
};

// Fix DateTime optional input
const formatDateTime = (dateStr?: string | number | Date) => {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  return d.toLocaleString('en-US', {
    year: 'numeric', month: 'short', day: '2-digit',
    hour: 'numeric', minute: '2-digit', hour12: true,
  });
};



// Notifications handlers
const handleNotificationClick = (notification: DoctorNotification): void => {
  notification.is_read = true;
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

const formatTime = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
};

// Doctor Forms: dialog state and form models
type FormType = 'hp' | 'soap' | 'orders' | 'procedure'
const showDoctorFormDialog = ref(false)
const selectedFormType = ref<FormType | null>(null)
const selectedFormPatient = ref<Patient | null>(null)
const formSubmitting = ref(false)
const doctorFormLoading = ref(false)
const editingIndex = ref<number | null>(null)

// Form type options for dropdown
const formTypeOptions = [
  { label: 'Select Form Type', value: null },
  { label: 'History & Physical (H&P)', value: 'hp' },
  { label: 'SOAP Note', value: 'soap' },
  { label: 'Order Form', value: 'orders' },
  { label: 'Procedure Form', value: 'procedure' }
]

// Computed property for form dialog title
const formDialogTitle = computed(() => {
  if (!selectedFormType.value) return 'Medical Form';
  
  switch(selectedFormType.value) {
    case 'hp': return 'History & Physical Examination';
    case 'soap': return 'SOAP Note';
    case 'orders': return 'Order Form';
    case 'procedure': return 'Procedure Form';
    default: return 'Medical Form';
  }
})

// Form type change handler
const onFormTypeChange = (value: FormType | null) => {
  if (value && selectedPatient.value) {
    openFormForPatient(selectedPatient.value, value)
  }
}

// Close form function
const closeForm = () => {
  // Ask for confirmation if form has been modified
  if (formHasChanges()) {
    $q.dialog({
      title: 'Unsaved Changes',
      message: 'You have unsaved changes. Are you sure you want to close this form?',
      cancel: true,
      persistent: true
    }).onOk(() => {
      resetForm(selectedFormType.value as FormType)
      showDoctorFormDialog.value = false
      selectedFormType.value = null
      selectedFormPatient.value = null
    })
  } else {
    showDoctorFormDialog.value = false
    selectedFormType.value = null
    selectedFormPatient.value = null
  }
}

// Check if form has changes
const formHasChanges = (): boolean => {
  // Simple implementation - can be enhanced to compare with original values
  if (!selectedFormType.value) return false
  
  switch(selectedFormType.value) {
    case 'hp':
      return Object.values(hpForm.value).some(val => val !== '')
    case 'soap':
      return Object.values(soapForm.value).some(val => val !== '')
    case 'orders':
      return orderForm.value.order_type !== ''
    case 'procedure':
      return procedureForm.value.procedure_name !== ''
    default:
      return false
  }
}

// H&P Form model
interface HPFormModel {
  chief_complaint: string
  hpi: string
  pmh: string
  allergies_medications: string
  social_history: string
  ros_notes: string
  pe_general: string
  pe_heent: string
  pe_cardiac: string
  pe_pulmonary: string
  pe_abdomen: string
  pe_neurologic: string
  assessment: string
  assessment_codes: string
  plan: string
}

// SOAP Form model
interface SOAPFormModel {
  subjective: string
  objective: string
  assessment: string
  plan: string
}

// Order Sheet model
interface OrderFormModel {
  order_type: 'Medication' | 'Lab Test' | 'Imaging' | 'Consult' | 'General' | ''
  // Medication
  med_drug_name: string
  med_dose: string
  med_route: string
  med_frequency: string
  med_start_date: string
  med_stop_date: string
  // Diagnostic
  diag_test_name: string
  diag_specimen_type: string
  diag_reason: string
  diag_priority: 'Stat' | 'Routine' | ''
  // Consult
  consult_specialty: string
  consult_reason: string
  // General
  general_diet: string
  general_activity_level: string
  general_vitals_frequency: string
  general_isolation_status: string
  // Status
  order_status: 'New' | 'Hold' | 'Discontinue' | ''
}

// Procedure Report model
interface ProcedureFormModel {
  procedure_name: string
  indications: string
  consent_obtained: boolean
  anesthesia: string
  steps: string
  findings: string
  complications: string
  disposition_plan: string
}

const hpForm = ref<HPFormModel>({
  chief_complaint: '',
  hpi: '',
  pmh: '',
  allergies_medications: '',
  social_history: '',
  ros_notes: '',
  pe_general: '',
  pe_heent: '',
  pe_cardiac: '',
  pe_pulmonary: '',
  pe_abdomen: '',
  pe_neurologic: '',
  assessment: '',
  assessment_codes: '',
  plan: '',
})

const soapForm = ref<SOAPFormModel>({
  subjective: '',
  objective: '',
  assessment: '',
  plan: '',
})

const orderForm = ref<OrderFormModel>({
  order_type: '',
  med_drug_name: '',
  med_dose: '',
  med_route: '',
  med_frequency: '',
  med_start_date: '',
  med_stop_date: '',
  diag_test_name: '',
  diag_specimen_type: '',
  diag_reason: '',
  diag_priority: '',
  consult_specialty: '',
  consult_reason: '',
  general_diet: '',
  general_activity_level: '',
  general_vitals_frequency: '',
  general_isolation_status: '',
  order_status: '',
})

const procedureForm = ref<ProcedureFormModel>({
  procedure_name: '',
  indications: '',
  consent_obtained: false,
  anesthesia: '',
  steps: '',
  findings: '',
  complications: '',
  disposition_plan: '',
})

const resetForm = (type: FormType): void => {
  if (type === 'hp') {
    hpForm.value = {
      chief_complaint: '', hpi: '', pmh: '', allergies_medications: '', social_history: '', ros_notes: '',
      pe_general: '', pe_heent: '', pe_cardiac: '', pe_pulmonary: '', pe_abdomen: '', pe_neurologic: '',
      assessment: '', assessment_codes: '', plan: ''
    }
  } else if (type === 'soap') {
    soapForm.value = { subjective: '', objective: '', assessment: '', plan: '' }
  } else if (type === 'orders') {
    orderForm.value = {
      order_type: '',
      med_drug_name: '', med_dose: '', med_route: '', med_frequency: '', med_start_date: '', med_stop_date: '',
      diag_test_name: '', diag_specimen_type: '', diag_reason: '', diag_priority: '',
      consult_specialty: '', consult_reason: '',
      general_diet: '', general_activity_level: '', general_vitals_frequency: '', general_isolation_status: '',
      order_status: '',
    }
  } else if (type === 'procedure') {
    procedureForm.value = {
      procedure_name: '', indications: '', consent_obtained: false, anesthesia: '', steps: '', findings: '', complications: '', disposition_plan: ''
    }
  }
}

const openFormForPatient = (patient: Patient, type: FormType): void => {
  selectedFormPatient.value = patient
  selectedFormType.value = type
  resetForm(type)
  showDoctorFormDialog.value = true
  void loadExistingDoctorForms()
}

const validateForm = (): boolean => {
  if (!selectedFormType.value) return false;
  
  // Validate required fields based on form type
  switch (selectedFormType.value) {
    case 'hp':
      if (!hpForm.value.chief_complaint || !hpForm.value.hpi || 
          !hpForm.value.pe_general || !hpForm.value.assessment || !hpForm.value.plan) {
        return false;
      }
      break;
    case 'soap':
      if (!soapForm.value.subjective || !soapForm.value.objective || 
          !soapForm.value.assessment || !soapForm.value.plan) {
        return false;
      }
      break;
    case 'orders':
      if (!orderForm.value.order_type || !orderForm.value.order_status) {
        return false;
      }
      // Additional validation based on order type
      if (orderForm.value.order_type === 'Medication' && 
          (!orderForm.value.med_drug_name || !orderForm.value.med_dose || 
           !orderForm.value.med_route || !orderForm.value.med_frequency)) {
        return false;
      }
      break;
    case 'procedure':
      if (!procedureForm.value.procedure_name || !procedureForm.value.indications || 
          !procedureForm.value.steps || !procedureForm.value.findings || 
          !procedureForm.value.disposition_plan) {
        return false;
      }
      break;
    default:
      return false;
  }
  
  return true;
};

const saveDoctorForm = async (): Promise<void> => {
  // Validate form before submission
  if (!validateForm()) {
    $q.notify({ 
      type: 'warning', 
      message: 'Please fill in all required fields', 
      position: 'top' 
    });
    return;
  }
  
  formSubmitting.value = true
  try {
    const pid = selectedFormPatient.value?.user_id ?? selectedFormPatient.value?.id
    const endpointBase = `/users/doctor/patient/${pid}`
    let endpoint = ''
    let data: Record<string, unknown> = {}

    if (selectedFormType.value === 'hp') {
      endpoint = `${endpointBase}/hp/`
      const physicalExam = [
        hpForm.value.pe_general && `General: ${hpForm.value.pe_general}`,
        hpForm.value.pe_heent && `HEENT: ${hpForm.value.pe_heent}`,
        hpForm.value.pe_cardiac && `Cardiac: ${hpForm.value.pe_cardiac}`,
        hpForm.value.pe_pulmonary && `Pulmonary: ${hpForm.value.pe_pulmonary}`,
        hpForm.value.pe_abdomen && `Abdomen: ${hpForm.value.pe_abdomen}`,
        hpForm.value.pe_neurologic && `Neurologic: ${hpForm.value.pe_neurologic}`,
      ].filter(Boolean).join('\n')
      data = {
        patient_name: selectedFormPatient.value?.full_name ?? selectedFormPatient.value?.patient_name ?? '',
        dob: selectedFormPatient.value?.date_of_birth ?? '',
        mrn: selectedFormPatient.value?.mrn ?? '',
        chief_complaint: hpForm.value.chief_complaint,
        history_present_illness: hpForm.value.hpi,
        past_medical_history: hpForm.value.pmh,
        social_history: hpForm.value.social_history,
        review_of_systems: hpForm.value.ros_notes ? [hpForm.value.ros_notes] : [],
        physical_exam: physicalExam,
        assessment: hpForm.value.assessment,
        diagnoses_icd_codes: hpForm.value.assessment_codes ? hpForm.value.assessment_codes.split(',').map(s => s.trim()).filter(Boolean) : [],
        initial_plan: hpForm.value.plan,
      }
    } else if (selectedFormType.value === 'soap') {
      endpoint = `${endpointBase}/progress-notes/`
      data = {
        date_time_note: new Date().toISOString(),
        subjective: soapForm.value.subjective,
        objective: soapForm.value.objective,
        assessment: soapForm.value.assessment,
        plan: soapForm.value.plan,
      }
    } else if (selectedFormType.value === 'orders') {
      endpoint = `${endpointBase}/orders/`
      data = {
        order_type: orderForm.value.order_type,
        order_status: orderForm.value.order_status,
        medication_orders: {
          drug_name: orderForm.value.med_drug_name,
          dose: orderForm.value.med_dose,
          route: orderForm.value.med_route,
          frequency: orderForm.value.med_frequency,
        },
        diagnostic_orders: {
          test_name: orderForm.value.diag_test_name,
          priority: orderForm.value.diag_priority,
          reason: orderForm.value.diag_reason,
        },
        consultation_orders: {
          specialty: orderForm.value.consult_specialty,
          question: orderForm.value.consult_reason,
        },
        general_orders: {
          diet: orderForm.value.general_diet,
          activity_level: orderForm.value.general_activity_level,
          vitals_frequency: orderForm.value.general_vitals_frequency,
          isolation_status: orderForm.value.general_isolation_status,
        },
      }
    } else if (selectedFormType.value === 'procedure') {
      endpoint = `${endpointBase}/operative-reports/`
      data = {
        procedure_name: procedureForm.value.procedure_name,
        indications: procedureForm.value.indications,
        consent_status: procedureForm.value.consent_obtained ? 'obtained' : 'unknown',
        anesthesia_type: procedureForm.value.anesthesia,
        anesthesia_dose: '',
        procedure_steps: procedureForm.value.steps,
        findings: procedureForm.value.findings,
        complications: procedureForm.value.complications,
        disposition_plan: procedureForm.value.disposition_plan,
      }
    }

    if (!endpoint) throw new Error('Invalid form type')

    if (editingIndex.value !== null) {
      await api.put(`${endpoint}${editingIndex.value}/`, data)
      $q.notify({ type: 'positive', message: 'Form updated successfully', position: 'top' })
    } else {
      await api.post(endpoint, data)
      $q.notify({ type: 'positive', message: 'Form submitted successfully', position: 'top' })
      void router.push({ name: 'DoctorPatientArchive' })
    }
    showDoctorFormDialog.value = false
  } catch (error) {
    console.error('Failed to save form:', error)
    let message = 'Failed to save form'
    const axiosErr = error as AxiosError<{ detail?: string }>
    if (axiosErr && axiosErr.response) {
      message = axiosErr.response.data?.detail ?? message
    } else if (typeof (error as { message?: string }).message === 'string') {
      message = (error as { message?: string }).message ?? message
    }
    $q.notify({ type: 'negative', message, position: 'top' })
  } finally {
    formSubmitting.value = false
  }
}

// Backend record shapes used when prefilling forms from GET responses
type HPRecord = {
  chief_complaint?: string;
  history_present_illness?: string;
  past_medical_history?: string;
  social_history?: string;
  review_of_systems?: string[] | string;
  physical_exam?: string;
  assessment?: string;
  diagnoses_icd_codes?: string[];
  initial_plan?: string;
}

type SOAPRecord = {
  subjective?: string;
  objective?: string;
  assessment?: string;
  plan?: string;
}

type OrdersRecord = {
  order_type?: OrderFormModel['order_type'];
  order_status?: OrderFormModel['order_status'];
  medication_orders?: {
    drug_name?: string;
    dose?: string;
    route?: string;
    frequency?: string;
  };
  diagnostic_orders?: {
    test_name?: string;
    priority?: OrderFormModel['diag_priority'];
    reason?: string;
  };
  consultation_orders?: {
    specialty?: string;
    question?: string;
  };
  general_orders?: {
    diet?: string;
    activity_level?: string;
    vitals_frequency?: string;
    isolation_status?: string;
  };
}

type ProcedureRecord = {
  procedure_name?: string;
  indications?: string;
  consent_status?: string;
  anesthesia_type?: string;
  procedure_steps?: string;
  findings?: string;
  complications?: string;
  disposition_plan?: string;
}

const isRecord = (v: unknown): v is Record<string, unknown> => v !== null && typeof v === 'object'

const loadExistingDoctorForms = async (): Promise<void> => {
  if (!selectedFormType.value || !selectedFormPatient.value) return
  doctorFormLoading.value = true
  editingIndex.value = null
  try {
    const pid = selectedFormPatient.value.user_id ?? selectedFormPatient.value.id
    const endpointBase = `/users/doctor/patient/${pid}`
    let endpoint = ''
    if (selectedFormType.value === 'hp') endpoint = `${endpointBase}/hp/`
    else if (selectedFormType.value === 'soap') endpoint = `${endpointBase}/progress-notes/`
    else if (selectedFormType.value === 'orders') endpoint = `${endpointBase}/orders/`
    else if (selectedFormType.value === 'procedure') endpoint = `${endpointBase}/operative-reports/`
    if (!endpoint) return
    const resp = await api.get(endpoint)
    const raw = resp.data?.data
    const list: unknown[] = Array.isArray(raw) ? raw : []
    if (list.length > 0) {
      const lastIdx = list.length - 1
      const last = list[lastIdx]
      editingIndex.value = lastIdx
      if (selectedFormType.value === 'hp') {
        if (isRecord(last)) {
          const hp = last as Partial<HPRecord>
          hpForm.value.chief_complaint = hp.chief_complaint ?? ''
          hpForm.value.hpi = hp.history_present_illness ?? ''
          hpForm.value.pmh = hp.past_medical_history ?? ''
          hpForm.value.allergies_medications = ''
          hpForm.value.social_history = hp.social_history ?? ''
          hpForm.value.ros_notes = Array.isArray(hp.review_of_systems) ? hp.review_of_systems.join('; ') : (typeof hp.review_of_systems === 'string' ? hp.review_of_systems : '')
          const pe: string = hp.physical_exam ?? ''
          hpForm.value.pe_general = pe
          hpForm.value.pe_heent = ''
          hpForm.value.pe_cardiac = ''
          hpForm.value.pe_pulmonary = ''
          hpForm.value.pe_abdomen = ''
          hpForm.value.pe_neurologic = ''
          hpForm.value.assessment = hp.assessment ?? ''
          hpForm.value.assessment_codes = Array.isArray(hp.diagnoses_icd_codes) ? hp.diagnoses_icd_codes.join(', ') : ''
          hpForm.value.plan = hp.initial_plan ?? ''
        }
      } else if (selectedFormType.value === 'soap') {
        if (isRecord(last)) {
          const soap = last as Partial<SOAPRecord>
          soapForm.value.subjective = soap.subjective ?? ''
          soapForm.value.objective = soap.objective ?? ''
          soapForm.value.assessment = soap.assessment ?? ''
          soapForm.value.plan = soap.plan ?? ''
        }
      } else if (selectedFormType.value === 'orders') {
        if (isRecord(last)) {
          const ord = last as Partial<OrdersRecord>
          const med = ord.medication_orders ?? {}
          orderForm.value.order_type = ord.order_type ?? ''
          orderForm.value.order_status = ord.order_status ?? ''
          orderForm.value.med_drug_name = med.drug_name ?? ''
          orderForm.value.med_dose = med.dose ?? ''
          orderForm.value.med_route = med.route ?? ''
          orderForm.value.med_frequency = med.frequency ?? ''
          const diag = ord.diagnostic_orders ?? {}
          orderForm.value.diag_test_name = diag.test_name ?? ''
          orderForm.value.diag_priority = diag.priority ?? ''
          orderForm.value.diag_reason = diag.reason ?? ''
          const consult = ord.consultation_orders ?? {}
          orderForm.value.consult_specialty = consult.specialty ?? ''
          orderForm.value.consult_reason = consult.question ?? ''
          const gen = ord.general_orders ?? {}
          orderForm.value.general_diet = gen.diet ?? ''
          orderForm.value.general_activity_level = gen.activity_level ?? ''
          orderForm.value.general_vitals_frequency = gen.vitals_frequency ?? ''
          orderForm.value.general_isolation_status = gen.isolation_status ?? ''
        }
      } else if (selectedFormType.value === 'procedure') {
        if (isRecord(last)) {
          const proc = last as Partial<ProcedureRecord>
          procedureForm.value.procedure_name = proc.procedure_name ?? ''
          procedureForm.value.indications = proc.indications ?? ''
          procedureForm.value.consent_obtained = (proc.consent_status ?? '') === 'obtained'
          procedureForm.value.anesthesia = proc.anesthesia_type ?? ''
          procedureForm.value.steps = proc.procedure_steps ?? ''
          procedureForm.value.findings = proc.findings ?? ''
          procedureForm.value.complications = proc.complications ?? ''
          procedureForm.value.disposition_plan = proc.disposition_plan ?? ''
        }
      }
      $q.notify({ type: 'info', message: 'Loaded latest record for editing', position: 'top' })
    } else {
      editingIndex.value = null
    }
  } catch (error) {
    console.error('Failed to load doctor forms:', error)
  } finally {
    doctorFormLoading.value = false
  }
}

let assignmentsTicker: ReturnType<typeof setInterval> | null = null;

const startAssignmentsPolling = (): void => {
  if (assignmentsTicker) return;
  assignmentsTicker = setInterval(() => { void loadPatients(); }, 8000);
};

const stopAssignmentsPolling = (): void => {
  if (assignmentsTicker) {
    clearInterval(assignmentsTicker);
    assignmentsTicker = null;
  }
};

// Doctor messaging WebSocket for real-time patient assignments
let doctorMessagingWS: WebSocket | null = null;
let wsRetries = 0;

const setupDoctorMessagingWS = (): void => {
  try {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const base = new URL(api.defaults.baseURL || `http://${window.location.hostname}:8000/api`);
    const backendHost = base.hostname;
    const backendPort = base.port || (base.protocol === 'https:' ? '443' : '80');
    const storedUser = JSON.parse(localStorage.getItem('user') || '{}');
    const userId = storedUser.id || storedUser.user?.id || storedUser.user_id;

    if (!userId) {
      console.warn('No user id found for doctor messaging WebSocket');
      return;
    }

    const wsUrl = `${protocol}//${backendHost}:${backendPort}/ws/messaging/${userId}/`;
    const ws = new WebSocket(wsUrl);
    doctorMessagingWS = ws;

    ws.onopen = () => {
      console.log('DoctorPatientManagement messaging WebSocket connected');
      wsRetries = 0;
    };

    ws.onmessage = async (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data as string);
        if (data.type === 'notification') {
          const notif = data.notification || {};
          if (notif.event === 'patient_assigned') {
            $q.notify({
              type: 'info',
              message: 'New patient assigned to you',
              position: 'top'
            });
            // Immediate refresh of assignments, notifications, and requests
            try {
              await loadPatients();
            } catch (e) {
              console.warn('Failed to refresh patients after assignment', e);
              $q.notify({ type: 'negative', message: 'Failed to refresh patients. Retrying...', position: 'top' });
              // Quick retry once
              setTimeout(() => { void loadPatients(); }, 2000);
            }
            void loadNotifications();
          }
        }
      } catch (err) {
        console.warn('Failed to parse doctor WS message', err);
      }
    };

    ws.onerror = (ev) => {
      // Reduce noise: log at debug level, notify only via assignment events
      console.debug('DoctorPatientManagement messaging WebSocket error', ev);
    };

    ws.onclose = () => {
      console.log('DoctorPatientManagement messaging WebSocket disconnected');
      // Exponential backoff with cap to reduce noise
      const delay = Math.min(30000, 2000 * Math.pow(2, wsRetries++));
      setTimeout(() => setupDoctorMessagingWS(), delay);
    };
  } catch (e) {
    console.warn('Failed to setup doctor messaging WebSocket', e);
  }
};

onMounted(() => {

  console.log('🚀 DoctorPatientManagement component mounted');
  void fetchUserProfile();
  void loadNotifications();
  void loadPatients();
  void loadAvailableNurses();
  void loadDoctorStats();
  startAssignmentsPolling();
  setupDoctorMessagingWS();
});

onUnmounted(() => {
  stopAssignmentsPolling();
  try { if (doctorMessagingWS) doctorMessagingWS.close(); } catch (err) { console.warn('Error closing doctor WS', err); } finally { doctorMessagingWS = null; }
});
</script>

<style scoped>
/* Safe Area Support */
.safe-area-top {
  padding-top: env(safe-area-inset-top);
}

.safe-area-bottom {
  padding-bottom: env(safe-area-inset-bottom);
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

.time-display,
.weather-display,
.weather-loading,
.weather-error {
  display: flex;
  align-items: center;
  gap: 8px;
  color: white;
}

.time-text,
.weather-text,
.weather-location {
  font-size: 14px;
  font-weight: 500;
}

/* Drawer Styles */
.drawer-content {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 20px;
}

.user-profile-section {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  margin-bottom: 20px;
  position: relative;
}

.user-avatar-container {
  position: relative;
}

.user-avatar {
  border: 3px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
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

/* Sidebar Content */
.sidebar-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f8f9fa;
  position: relative;
  padding-bottom: 80px; /* Space for footer */
}

/* Logo Section */
.logo-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px;
  background: #f8f9fa;
  border-bottom: 1px solid #e0e0e0;
}

.logo-container {
  display: flex;
  align-items: center;
  flex: 1;
}

.logo-avatar {
  margin-right: 12px;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  color: #286660;
}

.menu-btn-right {
  color: #666;
  margin-left: auto;
}

/* Centered User Profile Section */
.sidebar-user-profile {
  padding: 24px 20px;
  border-bottom: 1px solid #e0e0e0;
  text-align: center;
}

/* Logout Section */
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

/* Page Container */
.page-container-with-fixed-header {
  background: #f8f9fa;
  background-size: cover;
  min-height: 100vh;
  position: relative;
}

.page-container-with-fixed-header::before {
  content: '';
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  z-index: 0;
}

.patient-management-content {
  position: relative;
  z-index: 1;
  padding: 20px;
}

/* Greeting Section */
.greeting-section {
  padding: 32px 24px 24px 24px;
  background: transparent;
}

.greeting-card {
  background: linear-gradient( 135deg,rgba(255, 255, 255, 0.95) 0%, rgba(248, 250, 252, 0.9) 50%,rgba(241, 245, 249, 0.85) 100%);
  backdrop-filter: blur(18px) saturate(120%);
  -webkit-backdrop-filter: blur(18px) saturate(120%);
  border-radius: 20px;
  .page-container-with-fixed-header::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background: rgba(255, 255, 255, 0.9);
    backdrop-filter: blur(10px);
    z-index: 0;
  }
}

.patient-management-content {
  position: relative;
  z-index: 1;
  padding: 20px;
}

/* Greeting Section */
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
  backdrop-filter: blur(18px) saturate(120%);
  -webkit-backdrop-filter: blur(18px) saturate(120%);
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
  background: linear-gradient(90deg, #286660, #6ca299, #b8d2ce);
  border-radius: 20px 20px 0 0;
}

.greeting-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 30px;
}

.greeting-text {
  flex: 1;
}

.greeting-title {
  font-size: 2.5rem;
  font-weight: 700;
  color: #333;
  margin: 0 0 10px 0;
  background: linear-gradient(135deg, #286660, #4a7c59);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.greeting-subtitle {
  font-size: 1.1rem;
  color: #666;
  margin: 0;
  font-weight: 500;
}

.greeting-icon {
  color: #286660;
  opacity: 0.8;
}

/* Management Cards */
.management-cards-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 30px;
  margin-bottom: 30px;
}

.glassmorphism-card {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 15px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 20px 0 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.card-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #333;
  margin: 0;
}

.card-content {
  padding: 20px;
}

.search-input {
  width: 240px;
}

/* Patient List */
.patients-list {
  max-height: 500px;
  overflow-y: auto;
}

.patient-card {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 10px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.patient-card:hover {
  background: rgba(255, 255, 255, 0.1);
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.patient-avatar {
  flex-shrink: 0;
}

.patient-info {
  flex: 1;
  min-width: 0;
}

.patient-name {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin: 0 0 5px 0;
}

.patient-details {
  font-size: 12px;
  color: #666;
  margin: 0 0 5px 0;
}

.patient-condition {
  font-size: 13px;
  color: #555;
  margin: 0 0 8px 0;
  font-style: italic;
}

.patient-status {
  margin-top: 5px;
}

.patient-actions {
  display: flex;
  gap: 5px;
  flex-shrink: 0;
}

/* Statistics */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.stat-item {
  text-align: center;
  padding: 15px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.stat-number {
  font-size: 2rem;
  font-weight: 700;
  color: #286660;
  margin-bottom: 5px;
}

.stat-label {
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

/* Loading & Empty */
.loading-section, .empty-section { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 40px; color: #666; }
.loading-text, .empty-text { margin-top: 15px; font-size: 14px; }

/* Responsive */
@media (max-width: 1024px) {
  .management-cards-grid { grid-template-columns: 1fr; }
  .search-input { width: 180px; }
}
/* Import the same styles as DoctorDashboard */
/* Safe Area Support */
.safe-area-top {
  padding-top: env(safe-area-inset-top);
}

.safe-area-bottom {
  padding-bottom: env(safe-area-inset-bottom);
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

.time-display,
.weather-display,
.weather-loading,
.weather-error {
  display: flex;
  align-items: center;
  gap: 8px;
  color: white;
}

.time-text,
.weather-text,
.weather-location {
  font-size: 14px;
  font-weight: 500;
}

/* Drawer Styles */
.drawer-content {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 20px;
}

.user-profile-section {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  margin-bottom: 20px;
  position: relative;
}

.user-avatar-container {
  position: relative;
}

.user-avatar {
  border: 3px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
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

/* Sidebar Content */
.sidebar-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f8f9fa;
  position: relative;
  padding-bottom: 80px; /* Space for footer */
}

/* Logo Section */
.logo-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px;
  background: #f8f9fa;
  border-bottom: 1px solid #e0e0e0;
}

.logo-container {
  display: flex;
  align-items: center;
  flex: 1;
}

.logo-avatar {
  margin-right: 12px;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  color: #286660;
}

.menu-btn-right {
  color: #666;
  margin-left: auto;
}

/* Centered User Profile Section */
.sidebar-user-profile {
  padding: 24px 20px;
  border-bottom: 1px solid #e0e0e0;
  text-align: center;
}

/* Logout Section */
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

/* Page Container */
.page-container-with-fixed-header {
  background: #f8f9fa;
  background-size: cover;
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
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  z-index: 0;
}

.patient-management-content {
  position: relative;
  z-index: 1;
  padding: 20px;
}

/* Greeting Section */
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
  backdrop-filter: blur(18px) saturate(120%);
  -webkit-backdrop-filter: blur(18px) saturate(120%);
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
  background: linear-gradient(90deg, #286660, #6ca299, #b8d2ce);
  border-radius: 20px 20px 0 0;
}

.greeting-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 30px;
}

.greeting-text {
  flex: 1;
}

.greeting-title {
  font-size: 2.5rem;
  font-weight: 700;
  color: #333;
  margin: 0 0 10px 0;
  background: linear-gradient(135deg, #286660, #4a7c59);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.greeting-subtitle {
  font-size: 1.1rem;
  color: #666;
  margin: 0;
  font-weight: 500;
}

.greeting-icon {
  color: #286660;
  opacity: 0.8;
}

/* Management Cards */
.management-cards-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 30px;
  margin-bottom: 30px;
}

.glassmorphism-card {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 15px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 20px 0 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.card-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #333;
  margin: 0;
}

.card-content {
  padding: 20px;
}

.search-input {
  width: 240px;
}

/* Patient List */
.patients-list {
  max-height: 500px;
  overflow-y: auto;
}

.patient-card {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 10px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.patient-card:hover {
  background: rgba(255, 255, 255, 0.1);
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.patient-avatar {
  flex-shrink: 0;
}

.patient-info {
  flex: 1;
  min-width: 0;
}

.patient-name {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin: 0 0 5px 0;
}

.patient-details {
  font-size: 12px;
  color: #666;
  margin: 0 0 5px 0;
}

.patient-condition {
  font-size: 13px;
  color: #555;
  margin: 0 0 8px 0;
  font-style: italic;
}

.patient-status {
  margin-top: 5px;
}

.patient-actions {
  display: flex;
  gap: 5px;
  flex-shrink: 0;
}

/* Statistics */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.stat-item {
  text-align: center;
  padding: 15px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.stat-number {
  font-size: 2rem;
  font-weight: 700;
  color: #286660;
  margin-bottom: 5px;
}

.stat-label {
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

/* Loading & Empty */
.loading-section,
.empty-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #666;
}

.loading-text,
.empty-text {
  margin-top: 15px;
  font-size: 14px;
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

/* Responsive Design */
@media (max-width: 768px) {
  .prototype-header {
    padding-top: max(env(safe-area-inset-top), 8px);
  }

  .header-toolbar {
    padding: 0 16px;
    min-height: 56px;
    padding-top: max(env(safe-area-inset-top), 4px);
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

  .q-page-container {
    padding: 8px;
  }

  .q-card {
    margin: 8px 0;
    border-radius: 12px;
  }

  .q-card__section {
    padding: 16px;
  }

  .management-cards-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .greeting-content {
    flex-direction: column;
    text-align: center;
    gap: 12px;
    padding: 16px;
  }

  .greeting-title {
    font-size: 1.5rem;
    margin-bottom: 8px;
  }

  .greeting-subtitle {
    font-size: 13px;
  }

  .stats-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .stat-card {
    padding: 16px;
  }

  .stat-value {
    font-size: 24px;
  }

  .stat-label {
    font-size: 13px;
  }

  .patient-card {
    flex-direction: column;
    text-align: center;
    padding: 16px;
  }

  .patient-info h6 {
    font-size: 16px;
    margin-bottom: 4px;
  }

  .patient-info .text-caption {
    font-size: 12px;
  }

  .patient-actions {
    justify-content: center;
    gap: 8px;
    margin-top: 12px;
  }

  .q-btn {
    padding: 8px 12px;
    font-size: 12px;
    border-radius: 6px;
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
}

/* Profile Avatar Styles - Circular Design */
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

/* Notification styles */
.unread {
  background-color: rgba(25, 118, 210, 0.05);
  border-left: 3px solid #1976d2;
}

.unread .q-item-label {
  font-weight: 600;
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
}
</style>