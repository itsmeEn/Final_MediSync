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
                <div class="row items-center justify-between full-width">
                  <div class="row items-center q-gutter-sm">
                    <h5 class="card-title q-mb-none">Patient List</h5>
                    <q-chip dense color="grey-2" text-color="grey-9" class="count-chip">
                      {{ patients.length }} active
                    </q-chip>
                  </div>
                  <div class="row items-center q-gutter-xs">
                    <q-chip
                      v-if="hasAssignmentsUpdate"
                      dense
                      color="green-1"
                      text-color="green-10"
                      class="count-chip"
                    >
                      New
                    </q-chip>
                    <q-btn
                      color="primary"
                      icon="refresh"
                      size="sm"
                      @click="refreshPatientPanel"
                      :loading="loading || archivedLoading"
                    />
                  </div>
                </div>
              </q-card-section>

              <q-card-section class="card-content">
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
                      <q-avatar size="50px" color="primary" text-color="white">
                        <img
                          v-if="patient.profile_picture"
                          :src="patient.profile_picture.startsWith('http') ? patient.profile_picture : getMediaUrl(patient.profile_picture)"
                          :alt="patient.full_name"
                          @error="patient.profile_picture = ''"
                        />
                        <div v-else class="avatar-initials">{{ getInitials(patient.full_name || 'User') }}</div>
                      </q-avatar>
                    </div>

                    <div class="patient-info">
                      <h6 class="patient-name">{{ patient.full_name }}</h6>
                      <p class="patient-details">
                        Age: {{ patient.age ?? 'N/A' }} | {{ patient.gender || 'N/A' }} | {{ patient.blood_type || 'N/A' }}
                      </p>
                      <p class="patient-condition">
                        Assigned by: {{ patient.assigned_by || 'N/A' }} • {{ patient.assignment_reason || 'No reason specified' }}
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
                        v-if="patient.assignment_id && patient.assignment_status === 'pending'"
                        flat
                        round
                        icon="check_circle"
                        color="positive"
                        size="sm"
                        @click.stop="acceptAssignment(patient)"
                        unelevated
                      >
                        <q-tooltip :delay="500">Accept</q-tooltip>
                      </q-btn>
                      <q-btn
                        v-if="canAssessPatient(patient)"
                        flat
                        round
                        icon="done"
                        color="positive"
                        size="sm"
                        @click.stop="viewPatientDetails(patient)"
                        unelevated
                      >
                        <q-tooltip :delay="500">Assess</q-tooltip>
                      </q-btn>
                      <q-btn
                        v-if="patient.assignment_id"
                        flat
                        round
                        icon="note"
                        color="primary"
                        size="sm"
                        @click.stop="openConsultationNotes(patient)"
                        unelevated
                      >
                        <q-tooltip :delay="500">Consultation Notes</q-tooltip>
                      </q-btn>
                      <q-btn
                        flat
                        round
                        icon="visibility"
                        color="primary"
                        size="sm"
                        @click.stop="viewPatientDetails(patient)"
                        unelevated
                      >
                        <q-tooltip :delay="500">View Details</q-tooltip>
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
                        <q-tooltip :delay="500">Edit Patient</q-tooltip>
                      </q-btn>
                      <q-btn
                        flat
                        round
                        unelevated
                        icon="send"
                        color="primary"
                        size="sm"
                        aria-label="Send medical records"
                        class="send-medical-records-btn"
                        :style="sendMedicalRecordsBtnStyle"
                        @click.stop="openSendMedicalRecords(patient)"
                      >
                        <q-tooltip :delay="500">Send Medical Records</q-tooltip>
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
                        <q-tooltip :delay="500">Archive</q-tooltip>
                      </q-btn>
                      <!-- Forms dropdown removed per request to keep UI clean -->
                    </div>
                  </div>
                </div>
              </q-card-section>

              <q-separator class="q-mt-sm" />
              <q-card-section class="card-content archived-section">
                <div class="row items-center justify-between q-mb-sm">
                  <div class="row items-center q-gutter-sm">
                    <div class="text-subtitle2 text-weight-medium">Archived patients</div>
                    <div class="text-caption text-grey-7">({{ archivedRecords.length }} records)</div>
                  </div>
                  <q-btn
                    flat
                    dense
                    size="sm"
                    icon="refresh"
                    :loading="archivedLoading"
                    @click="loadArchivedPatients"
                    aria-label="Refresh archived patients"
                  />
                </div>
                                <q-input
                  v-model="searchText"
                  outlined
                  dense
                  clearable
                  class="q-mb-sm patient-search"
                  placeholder="Search patient name..."
                  aria-label="Search patient"
                >
                  <template v-slot:prepend>
                    <q-icon name="search" />
                  </template>
                </q-input>

                <div v-if="archivedLoading" class="loading-section">
                  <q-spinner color="primary" size="2em" />
                  <p class="loading-text">Loading archived patients...</p>
                </div>

                <div v-else-if="archivedVisible.length === 0" class="empty-archived">
                  <div class="text-caption text-grey-7">No archived patients</div>
                </div>

                <div v-else class="archived-list">
                  <div v-for="rec in archivedVisible" :key="rec.id" class="archived-row">
                    <div class="archived-avatar">
                      <q-avatar size="36px" color="grey-3" text-color="grey-9">
                        {{ getInitials(rec.patient_name || 'Patient') }}
                      </q-avatar>
                    </div>
                    <div class="archived-info">
                      <div class="archived-name">{{ rec.patient_name }}</div>
                      <div class="archived-meta text-caption text-grey-7">
                        Archived {{ formatArchivedAt(rec.last_assessed_at) }}
                        <span v-if="rec.archival_reason" class="separator">•</span>
                        <span v-if="rec.archival_reason">{{ rec.archival_reason }}</span>
                      </div>
                    </div>
                    <div class="archived-actions">
                      <q-btn
                        outline
                        dense
                        color="primary"
                        label="Download"
                        :loading="downloadLoadingId === rec.id"
                        :disable="downloadLoadingId === rec.id || restoreLoadingId === rec.id"
                        @click.stop="downloadArchivedPatient(rec)"
                      />
                      <q-btn
                        outline
                        dense
                        color="grey-8"
                        label="Restore"
                        :loading="restoreLoadingId === rec.id"
                        :disable="restoreLoadingId === rec.id || downloadLoadingId === rec.id"
                        @click.stop="restoreArchivedPatient(rec)"
                      />
                    </div>
                  </div>

                  <div v-if="archivedRecords.length > archivedVisible.length" class="text-caption text-grey-7 q-mt-sm">
                    Showing {{ archivedVisible.length }} of {{ archivedRecords.length }}
                  </div>
                </div>
              </q-card-section>
            </q-card>
          </div>

          <!-- Right Column: Statistics -->
          <div class="right-column">
            <!-- Patient Statistics Card -->
            <q-card class="dashboard-card statistics-card q-mb-lg">
              <q-card-section class="card-header">
                <h5 class="card-title">Patient Statistics</h5>
              </q-card-section>
              <q-card-section class="card-content">
                <div class="stats-grid">
                  <div class="stat-item">
                    <div class="stat-number">{{ stats.total_patients }}</div>
                    <div class="stat-label">Total Patients</div>
                  </div>
                  <div class="stat-item">
                    <div class="stat-number">{{ stats.active_patients }}</div>
                    <div class="stat-label">Active</div>
                  </div>
                </div>
              </q-card-section>
            </q-card>

            <q-card class="dashboard-card q-mb-lg">
              <q-card-section class="card-header">
                <div class="row items-center justify-between full-width">
                  <h5 class="card-title q-mb-none">Medical Requests</h5>
                  <div class="row items-center q-gutter-xs">
                    <q-chip dense color="grey-2" text-color="grey-9" class="count-chip">
                      {{ medicalRequests.length }}
                    </q-chip>
                    <q-btn flat dense size="sm" icon="refresh" :loading="medicalRequestsLoading" @click="loadMedicalRequests" />
                  </div>
                </div>
              </q-card-section>
              <q-card-section class="card-content">
                <div v-if="medicalRequestsError" class="text-caption text-negative q-mb-sm" role="alert">
                  {{ medicalRequestsError }}
                </div>
                <div v-if="medicalRequestsLoading" class="loading-section">
                  <q-spinner color="primary" size="2em" />
                  <p class="loading-text">Loading requests...</p>
                </div>
                <div v-else-if="medicalRequests.length === 0" class="empty-section">
                  <p class="empty-text">No pending medical requests</p>
                </div>
                <div v-else class="q-gutter-sm">
                  <q-card v-for="req in medicalRequests" :key="req.id" flat bordered class="q-pa-sm">
                    <div class="row items-start justify-between">
                      <div>
                        <div class="text-weight-medium">{{ req.patient_name }}</div>
                        <div class="text-caption text-grey-7">
                          Request #{{ req.id }} • {{ formatDateTime(req.created_at) }}
                        </div>
                        <div class="text-caption">
                          {{ req.requested.join(', ') }}
                        </div>
                        <div class="q-mt-xs">
                          <template v-if="consultationNotesForRequest(req)">
                            <div class="text-caption text-grey-7">
                              Consultation Notes • {{ formatDateTime(consultationNotesForRequest(req)?.created_at || undefined) }} • {{ consultationNotesForRequest(req)?.status }}
                            </div>
                            <div class="text-caption">
                              <strong>Diagnosis:</strong> {{ consultationNotesForRequest(req)?.diagnosis || '—' }}
                            </div>
                            <div v-if="consultationNotesForRequest(req)?.treatment_plan" class="text-caption">
                              <strong>Treatment:</strong> {{ consultationNotesForRequest(req)?.treatment_plan }}
                            </div>
                            <div v-if="consultationNotesForRequest(req)?.medications_prescribed" class="text-caption">
                              <strong>Meds:</strong> {{ consultationNotesForRequest(req)?.medications_prescribed }}
                            </div>
                            <div v-if="consultationNotesForRequest(req)?.follow_up_instructions" class="text-caption">
                              <strong>Follow-up:</strong> {{ consultationNotesForRequest(req)?.follow_up_instructions }}
                            </div>
                          </template>
                          <template v-else>
                            <div class="text-caption text-grey-7">Consultation notes: —</div>
                          </template>
                        </div>
                      </div>
                      <q-btn
                        unelevated
                        color="primary"
                        size="sm"
                        label="Fulfill"
                        :disable="medicalRequestSubmitting"
                        @click="openFulfillMedicalRequest(req)"
                      />
                    </div>
                  </q-card>
                </div>
              </q-card-section>
            </q-card>



            <!-- List of Available Nurses Card -->
            <q-card class="dashboard-card nurses-card q-mt-lg">
              <q-card-section class="card-header">
                <h5 class="card-title">Available Nurses</h5>
                <div v-if="nursesError" class="text-caption text-negative q-mb-sm" role="alert">
                  {{ nursesError }}
                </div>
                <div v-else-if="nursesCheckedAt" class="text-caption text-grey-7 q-mb-sm">
                  Last checked: {{ formatDateTime(nursesCheckedAt || undefined) }}
                </div>
                <div v-if="nursesLoading" class="loading-section">
                  <q-spinner color="primary" size="2em" />
                  <p class="loading-text">Loading nurses...</p>
                </div>
                <div v-else-if="availableNurses.length === 0" class="empty-section">
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
              <q-avatar color="white" text-color="primary">
                <img
                  v-if="selectedFormPatientAvatarSrc && !selectedFormPatientAvatarFailed"
                  :src="selectedFormPatientAvatarSrc"
                  :alt="selectedFormPatient.full_name"
                  @error="selectedFormPatientAvatarFailed = true"
                >
                <div v-else class="avatar-initials">
                  {{ getInitials(selectedFormPatient.full_name || selectedFormPatient.patient_name || 'User') }}
                </div>
              </q-avatar>
            </template>
            <div class="text-subtitle1">{{ selectedFormPatient?.full_name || selectedFormPatient?.patient_name || '—' }}</div>
            <div class="text-caption">
              Provider: {{ userProfile.full_name }} | Date: {{ formatDateTime(new Date()) }}
            </div>
          </q-banner>

          <div v-if="selectedFormType === 'nurse_opd_form'" class="q-gutter-md">
            <q-banner v-if="!hasNursePhysicalFormData" dense icon="info" class="q-mb-sm">
              No nurse registration & assessment form recorded for this patient.
            </q-banner>
            <TipMedicalRecordForm
              v-else
              :model-value="nursePhysicalFormModel"
              mode="both"
              :facility-name="userProfile.hospital_name || selectedFormPatient?.hospital || 'Medical Facility'"
              :revision-date="physicalFormRevisionDate"
              :staff-options="physicalStaffOptions"
              readonly
            />
          </div>

          <div v-else-if="selectedFormType === 'psych_opd'" class="q-gutter-md">
            <PsychiatricOpdQuestionnaire
              v-if="selectedFormPatient"
              :patient-id="selectedFormPatient.id"
              :hospital-name="selectedFormPatient.hospital || 'Hospital'"
              :department-name="'OPD'"
              :patient-full-name="psychPrefillFullName"
              :patient-date-of-birth="psychPrefillDateOfBirth"
              :patient-age="psychPrefillAge"
            />
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>
    <!-- Nurse Intake Dialog -->
    <q-dialog v-model="showNurseIntakeDialog">
      <q-card class="doctor-form-card" style="max-width: 860px; width: 92vw;">
        <q-card-section class="card-header">
          <div class="card-title">Patient Records</div>
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

              <q-separator class="q-my-md" />
              <div class="text-subtitle2">Nurse Registration & Assessment</div>
              <q-banner v-if="!hasNursePhysicalFormData" dense icon="info" class="q-mt-sm">
                No nurse registration & assessment form recorded for this patient.
              </q-banner>
              <TipMedicalRecordForm
                v-else
                :model-value="nursePhysicalFormModel"
                mode="both"
                :facility-name="userProfile.hospital_name || selectedPatient?.hospital || 'Medical Facility'"
                :revision-date="physicalFormRevisionDate"
                :staff-options="physicalStaffOptions"
                readonly
              />
              
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
    <q-dialog v-model="showSendMedicalRecordsDialog" persistent>
      <q-card class="doctor-form-card" style="max-width: 920px; width: 92vw;">
        <q-card-section class="card-header row items-center">
          <div class="card-title">Send Medical Records</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>
        <q-card-section class="card-content">
          <q-stepper v-model="sendMedicalRecordsStep" animated flat>
            <q-step :name="1" title="Preview" icon="description" :done="sendMedicalRecordsStep > 1">
              <div v-if="sendMedicalRecordsPreviewLoading" class="row items-center q-gutter-sm">
                <q-spinner color="primary" size="1.5em" />
                <span class="text-caption">Loading preview...</span>
              </div>
              <div v-else-if="sendMedicalRecordsPreviewError" class="text-negative" role="alert">
                {{ sendMedicalRecordsPreviewError }}
              </div>
              <div v-else class="q-gutter-sm">
                <div class="text-subtitle2">{{ sendMedicalRecordsPatient?.full_name || 'Patient' }}</div>
                <div class="text-caption text-grey-7">
                  This preview shows the medical certificate content that will be generated and sent.
                </div>
                <q-separator class="q-my-sm" />
                <div class="text-caption"><strong>Doctor:</strong> {{ userProfile.full_name }}</div>
                <div class="text-caption"><strong>Hospital:</strong> {{ userProfile.hospital_name || 'Medical Facility' }}</div>
                <div class="text-caption"><strong>Diagnoses included:</strong></div>
                <q-list dense bordered class="rounded-borders">
                  <q-item v-for="(d, idx) in sendMedicalRecordsDiagnoses" :key="String(idx)">
                    <q-item-section>
                      <q-item-label>{{ d.diagnosis }}</q-item-label>
                      <q-item-label caption v-if="d.completed_at || d.created_at">
                        {{ d.completed_at || d.created_at }}
                      </q-item-label>
                    </q-item-section>
                  </q-item>
                </q-list>
              </div>
            </q-step>

            <q-step :name="2" title="Confirm" icon="check_circle" :done="sendMedicalRecordsStep > 2">
              <div class="q-gutter-md">
                <q-banner dense icon="warning" class="bg-orange-1 text-orange-10">
                  Confirm before sending. This action transmits sensitive medical information.
                </q-banner>
                <q-checkbox
                  v-model="sendMedicalRecordsConfirmed"
                  label="I confirm the preview is correct and I am authorized to send these medical records to the patient."
                />
              </div>
            </q-step>

            <q-step :name="3" title="Delivery Status" icon="schedule">
              <div class="q-gutter-sm">
                <div class="text-caption"><strong>Transfer ID:</strong> {{ sendMedicalRecordsTransferId ?? '—' }}</div>
                <div class="text-caption"><strong>Status:</strong> {{ sendMedicalRecordsStatusLabel }}</div>
                <div class="text-caption" v-if="sendMedicalRecordsStatusUpdatedAt">
                  <strong>Last update:</strong> {{ sendMedicalRecordsStatusUpdatedAt }}
                </div>
                <div class="text-caption" v-if="sendMedicalRecordsSentAt">
                  <strong>Delivered:</strong> {{ sendMedicalRecordsSentAt }}
                </div>
                <div class="text-negative" v-if="sendMedicalRecordsStatusError" role="alert">
                  {{ sendMedicalRecordsStatusError }}
                </div>
                <div v-if="sendMedicalRecordsStatusPolling" class="row items-center q-gutter-sm">
                  <q-spinner color="primary" size="1.5em" />
                  <span class="text-caption">Checking delivery status...</span>
                </div>
              </div>
            </q-step>
          </q-stepper>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn
            v-if="sendMedicalRecordsStep > 1 && sendMedicalRecordsStep < 3"
            flat
            label="Back"
            color="primary"
            @click="sendMedicalRecordsStep -= 1"
          />
          <q-btn
            v-if="sendMedicalRecordsStep === 1"
            unelevated
            label="Next"
            color="primary"
            :disable="!!sendMedicalRecordsPreviewError || sendMedicalRecordsPreviewLoading"
            @click="sendMedicalRecordsStep = 2"
          />
          <q-btn
            v-if="sendMedicalRecordsStep === 2"
            unelevated
            label="Send"
            color="primary"
            :loading="sendMedicalRecordsSubmitting"
            :disable="!sendMedicalRecordsConfirmed"
            @click="submitSendMedicalRecords"
          />
          <q-btn
            v-if="sendMedicalRecordsStep === 3"
            flat
            label="Close"
            color="primary"
            v-close-popup
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
    <q-dialog v-model="showConsultationDialog">
      <q-card class="doctor-form-card" style="max-width: 860px; width: 92vw;">
        <q-card-section class="card-header">
          <div class="card-title">Consultation Notes</div>
        </q-card-section>
        <q-card-section class="card-content">
          <div class="row items-center justify-between q-mb-sm">
            <div class="text-subtitle2">{{ consultationPatient?.full_name || 'Patient' }}</div>
            <q-btn flat dense size="sm" icon="refresh" label="Refresh" @click="reloadConsultationNotes" />
          </div>
          <div v-if="consultationLoading" class="loading-section">
            <q-spinner color="primary" size="2em" />
            <p class="loading-text">Loading notes...</p>
          </div>
          <div v-else class="q-gutter-md">
            <div class="row q-col-gutter-sm">
              <div class="col-12 col-sm-6">
                <q-select
                  v-model="consultationForm.assignment_status"
                  :options="consultationAssignmentStatusOptions"
                  outlined
                  dense
                  emit-value
                  map-options
                  label="Patient Status"
                />
              </div>
              <div class="col-12 col-sm-6">
                <q-select
                  v-model="consultationForm.status"
                  :options="consultationNoteStatusOptions"
                  outlined
                  dense
                  emit-value
                  map-options
                  label="Note Status"
                />
              </div>
            </div>
            <q-input v-model="consultationForm.chief_complaint" type="textarea" autogrow outlined label="Chief Complaint" />
            <q-input v-model="consultationForm.history_of_present_illness" type="textarea" autogrow outlined label="History of Present Illness" />
            <q-input v-model="consultationForm.physical_examination" type="textarea" autogrow outlined label="Physical Examination" />
            <q-input v-model="consultationForm.diagnosis" type="textarea" autogrow outlined label="Diagnosis" />
            <q-input v-model="consultationForm.treatment_plan" type="textarea" autogrow outlined label="Treatment Plan" />
            <q-input v-model="consultationForm.medications_prescribed" type="textarea" autogrow outlined label="Medications Prescribed" />
            <q-input v-model="consultationForm.follow_up_instructions" type="textarea" autogrow outlined label="Follow-up Instructions" />
            <q-input v-model="consultationForm.additional_notes" type="textarea" autogrow outlined label="Additional Notes" />
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Close" color="primary" v-close-popup />
          <q-btn
            unelevated
            label="Save"
            color="primary"
            :loading="consultationSaving"
            :disable="consultationSaving || consultationLoading || !consultationAssignmentId"
            @click="saveConsultationNotes"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="showFulfillMedicalRequestDialog" persistent :maximized="$q.screen.lt.md">
      <q-card style="width: 860px; max-width: 95vw;">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">Fulfill Medical Request</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup :disable="medicalRequestSubmitting" />
        </q-card-section>
        <q-separator class="q-my-md" />
        <q-card-section class="q-gutter-md" style="max-height: 75vh; overflow: auto;">
          <q-banner v-if="selectedMedicalRequest" dense class="bg-grey-1 text-grey-9">
            <div class="text-weight-medium">{{ selectedMedicalRequest.patient_name }}</div>
            <div class="text-caption">Request #{{ selectedMedicalRequest.id }} • {{ selectedMedicalRequest.requested.join(', ') }}</div>
            <div v-if="selectedMedicalRequest.patient_message" class="text-caption q-mt-xs">
              Message: {{ selectedMedicalRequest.patient_message }}
            </div>
            <div class="q-mt-xs">
              <template v-if="consultationNotesForRequest(selectedMedicalRequest)">
                <div class="text-caption text-grey-7">
                  Consultation Notes • {{ formatDateTime(consultationNotesForRequest(selectedMedicalRequest)?.created_at || undefined) }} • {{ consultationNotesForRequest(selectedMedicalRequest)?.status }}
                </div>
                <div class="text-caption">
                  <strong>Diagnosis:</strong> {{ consultationNotesForRequest(selectedMedicalRequest)?.diagnosis || '—' }}
                </div>
                <div v-if="consultationNotesForRequest(selectedMedicalRequest)?.treatment_plan" class="text-caption">
                  <strong>Treatment:</strong> {{ consultationNotesForRequest(selectedMedicalRequest)?.treatment_plan }}
                </div>
                <div v-if="consultationNotesForRequest(selectedMedicalRequest)?.medications_prescribed" class="text-caption">
                  <strong>Meds:</strong> {{ consultationNotesForRequest(selectedMedicalRequest)?.medications_prescribed }}
                </div>
                <div v-if="consultationNotesForRequest(selectedMedicalRequest)?.follow_up_instructions" class="text-caption">
                  <strong>Follow-up:</strong> {{ consultationNotesForRequest(selectedMedicalRequest)?.follow_up_instructions }}
                </div>
              </template>
              <template v-else>
                <div class="text-caption text-grey-7">Consultation notes: —</div>
              </template>
            </div>
          </q-banner>

          <div v-if="selectedMedicalRequest?.requested.includes('Medical Certificate')" class="q-gutter-sm">
            <div class="text-subtitle2">Medical Certificate</div>
            <div class="row q-col-gutter-sm">
              <div class="col-12 col-sm-6">
                <q-input v-model="certificateLeaveStart" type="date" outlined dense label="Sick Leave Start Date" />
              </div>
              <div class="col-12 col-sm-6">
                <q-input v-model="certificateLeaveEnd" type="date" outlined dense label="Sick Leave End Date" />
              </div>
            </div>
            <q-input v-model="certificateDiagnosis" type="textarea" autogrow outlined label="Diagnosis" />
          </div>

          <div v-if="selectedMedicalRequest?.requested.includes('Prescription')" class="q-gutter-sm">
            <div class="text-subtitle2">Prescription</div>
            <div v-for="(m, idx) in prescriptionMedications" :key="idx" class="q-pa-sm rounded-borders" style="border: 1px solid rgba(0,0,0,0.08);">
              <div class="row items-center justify-between q-mb-sm">
                <div class="text-caption text-grey-7">Medication {{ idx + 1 }}</div>
                <q-btn flat dense size="sm" icon="delete" color="negative" @click="removeMedication(idx)" :disable="medicalRequestSubmitting || prescriptionMedications.length <= 1" />
              </div>
              <div class="row q-col-gutter-sm">
                <div class="col-12 col-sm-6">
                  <q-input v-model="m.drug_name" outlined dense label="Drug Name" />
                </div>
                <div class="col-12 col-sm-6">
                  <q-input v-model="m.dosage" outlined dense label="Dosage" />
                </div>
                <div class="col-12 col-sm-6">
                  <q-input v-model="m.frequency" outlined dense label="Frequency" />
                </div>
                <div class="col-12 col-sm-6">
                  <q-input v-model="m.duration" outlined dense label="Duration" />
                </div>
                <div class="col-12">
                  <q-input v-model="m.instructions" outlined dense label="Special Instructions" />
                </div>
              </div>
            </div>
            <q-btn outline color="primary" icon="add" label="Add Medication" @click="addMedication" :disable="medicalRequestSubmitting" />
          </div>

          <q-input v-model="medicalRequestDoctorMessage" type="textarea" autogrow outlined label="Optional note to patient" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup :disable="medicalRequestSubmitting" />
          <q-btn
            unelevated
            color="primary"
            label="Generate & Email"
            :loading="medicalRequestSubmitting"
            :disable="medicalRequestSubmitting || !selectedMedicalRequest"
            @click="submitFulfillMedicalRequest"
          />
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
          <q-btn unelevated label="Done" color="warning" @click="confirmArchive" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue';
import { useQuasar } from 'quasar';
import { api, optimizeEndpoint } from 'boot/axios';
import { useRoute } from 'vue-router';
import type { AxiosError, AxiosRequestConfig, AxiosResponse } from 'axios';
import DoctorHeader from '../components/DoctorHeader.vue';
import DoctorSidebar from '../components/DoctorSidebar.vue';
import { getMediaUrl } from 'src/utils/mediaUrl';
import PsychiatricOpdQuestionnaire from 'src/components/PsychiatricOpdQuestionnaire.vue';
import TipMedicalRecordForm from 'src/components/TipMedicalRecordForm.vue';
import { canAssessPatientForUser } from '../utils/assessmentAccess';

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
  source?: 'appointment' | 'queue';
  appointment_id?: number;
  appointment_status?: string;
  appointment_date?: string;
  appointment_time?: string;
  assigned_doctor_id?: number;
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
const route = useRoute();
const rightDrawerOpen = ref(false);
const loading = ref(false);
const searchText = ref('');
const patients = ref<Patient[]>([]);
const selectedPatient = ref<Patient | null>(null);
const showNotifications = ref(false);
const didInitialPatientsLoad = ref(false)
const didRoutePreselect = ref(false)
const hasAssignmentsUpdate = ref(false)

type ArchivedPatientItem = {
  id: number;
  patient_name: string;
  last_assessed_at: string | null;
  archival_reason?: string;
}
const archivedLoading = ref(false)
const archivedRecords = ref<ArchivedPatientItem[]>([])
const restoreLoadingId = ref<number | null>(null)
const downloadLoadingId = ref<number | null>(null)
const archivedVisible = computed(() => archivedRecords.value.slice(0, 4))

const viewportWidth = ref<number>(typeof window !== 'undefined' ? window.innerWidth : 1024)
const handleViewportResize = (): void => {
  if (typeof window === 'undefined') return
  viewportWidth.value = window.innerWidth
}
const sendMedicalRecordsBtnStyle = computed<Record<string, string>>(() => {
  const w = Number(viewportWidth.value)
  const isXs = Number.isFinite(w) && w <= 600
  const isTiny = Number.isFinite(w) && w <= 360
  return {
    position: 'relative',
    zIndex: isXs ? '40' : '20',
    marginLeft: isXs ? '0px' : '2px',
    marginTop: isTiny ? '6px' : '0px',
  }
})

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
  hospital_name?: string;
  role: string;
  profile_picture: string | null;
  verification_status: string;
}>({
  id: 0,
  full_name: '',
  specialization: '',
  hospital_name: '',
  role: '',
  profile_picture: null,
  verification_status: '',
});

const canAssessPatient = (patient: Patient): boolean => {
  return canAssessPatientForUser({ id: Number(userProfile.value.id), role: userProfile.value.role }, patient);
};

// Notification system
const notifications = ref<DoctorNotification[]>([]);

const isNetworkFailure = (error: unknown): boolean => {
  const ax = error as AxiosError
  const code = (ax as unknown as { code?: unknown })?.code
  const medisyncType = (ax as unknown as { medisync?: { type?: unknown } })?.medisync?.type
  const msg = typeof ax?.message === 'string' ? ax.message.toLowerCase() : ''
  return (
    code === 'ERR_NETWORK' ||
    code === 'ECONNABORTED' ||
    code === 'CIRCUIT_OPEN' ||
    medisyncType === 'network' ||
    medisyncType === 'circuit_open' ||
    msg.includes('network') ||
    msg.includes('backend temporarily unavailable') ||
    (!ax.response && !!ax.request)
  )
}

const apiGetWithRecovery = async <T = unknown>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> => {
  try {
    return await api.get<T>(url, config)
  } catch (e) {
    if (!isNetworkFailure(e)) throw e
    localStorage.setItem('ENABLE_8001_FALLBACK', 'true')
    await optimizeEndpoint()
    const retryConfig: AxiosRequestConfig = { ...(config || {}), meta: { ...(config?.meta || {}), isHealthCheck: true } }
    return await api.get<T>(url, retryConfig)
  }
}

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

type MedicalRequestItem = {
  id: number
  created_at: string
  requested: string[]
  patient_profile_id: number
  patient_name: string
  patient_id: string
  patient_email: string
  patient_message: string
  consultation_notes?: ConsultationNotes | null
}

type ConsultationNotes = {
  id: number
  status: string
  created_at: string | null
  updated_at: string | null
  completed_at: string | null
  chief_complaint: string
  history_of_present_illness: string
  physical_examination: string
  diagnosis: string
  treatment_plan: string
  medications_prescribed: string
  follow_up_instructions: string
  additional_notes: string
}

type MedicationItem = {
  drug_name: string
  dosage: string
  frequency: string
  duration: string
  instructions: string
}

const medicalRequests = ref<MedicalRequestItem[]>([])
const medicalRequestsLoading = ref(false)
const medicalRequestsError = ref<string | null>(null)

const showFulfillMedicalRequestDialog = ref(false)
const selectedMedicalRequest = ref<MedicalRequestItem | null>(null)
const medicalRequestSubmitting = ref(false)

const certificateLeaveStart = ref('')
const certificateLeaveEnd = ref('')
const certificateDiagnosis = ref('')
const prescriptionMedications = ref<MedicationItem[]>([
  { drug_name: '', dosage: '', frequency: '', duration: '', instructions: '' }
])
const medicalRequestDoctorMessage = ref('')

const apiPostWithRecovery = async <T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> => {
  try {
    return await api.post<T>(url, data, config)
  } catch (e) {
    if (!isNetworkFailure(e)) throw e
    localStorage.setItem('ENABLE_8001_FALLBACK', 'true')
    await optimizeEndpoint()
    const retryConfig: AxiosRequestConfig = { ...(config || {}), meta: { ...(config?.meta || {}), isHealthCheck: true } }
    return await api.post<T>(url, data, retryConfig)
  }
}

const loadMedicalRequests = async (): Promise<void> => {
  if (medicalRequestsLoading.value) return
  medicalRequestsLoading.value = true
  medicalRequestsError.value = null
  try {
    const res = await apiGetWithRecovery<{ results?: MedicalRequestItem[]; count?: number }>('/operations/medical-requests/doctor/')
    const raw = res.data?.results ?? []
    const list = Array.isArray(raw) ? raw : []
    const seen = new Set<number>()
    const unique: MedicalRequestItem[] = []
    for (const r of list) {
      const id = Number((r as { id?: unknown })?.id ?? NaN)
      if (!Number.isFinite(id) || seen.has(id)) continue
      seen.add(id)
      unique.push(r)
    }
    if (unique.length !== list.length) {
      console.warn('Duplicate medical request entries removed', { before: list.length, after: unique.length })
    }
    medicalRequests.value = unique
  } catch {
    medicalRequestsError.value = 'Failed to load medical requests.'
  } finally {
    medicalRequestsLoading.value = false
  }
}

const consultationNotesForRequest = (req: MedicalRequestItem): ConsultationNotes | null => {
  if (!req || typeof req.id !== 'number') return null
  if (req.consultation_notes && typeof req.consultation_notes === 'object') return req.consultation_notes
  return null
}

const openFulfillMedicalRequest = (req: MedicalRequestItem): void => {
  selectedMedicalRequest.value = req
  certificateLeaveStart.value = ''
  certificateLeaveEnd.value = ''
  certificateDiagnosis.value = ''
  prescriptionMedications.value = [{ drug_name: '', dosage: '', frequency: '', duration: '', instructions: '' }]
  medicalRequestDoctorMessage.value = ''
  showFulfillMedicalRequestDialog.value = true
}

const addMedication = (): void => {
  prescriptionMedications.value = [...prescriptionMedications.value, { drug_name: '', dosage: '', frequency: '', duration: '', instructions: '' }]
}

const removeMedication = (idx: number): void => {
  if (prescriptionMedications.value.length <= 1) return
  prescriptionMedications.value = prescriptionMedications.value.filter((_, i) => i !== idx)
}

const submitFulfillMedicalRequest = async (): Promise<void> => {
  const req = selectedMedicalRequest.value
  if (!req) return
  if (medicalRequestSubmitting.value) return

  medicalRequestSubmitting.value = true
  try {
    const payload: Record<string, unknown> = {
      doctor_message: medicalRequestDoctorMessage.value,
    }
    if (req.requested.includes('Medical Certificate')) {
      payload.certificate = {
        leave_start_date: certificateLeaveStart.value,
        leave_end_date: certificateLeaveEnd.value,
        diagnosis: certificateDiagnosis.value,
      }
    }
    if (req.requested.includes('Prescription')) {
      const meds = prescriptionMedications.value
        .map((m) => ({
          drug_name: (m.drug_name || '').trim(),
          dosage: (m.dosage || '').trim(),
          frequency: (m.frequency || '').trim(),
          duration: (m.duration || '').trim(),
          instructions: (m.instructions || '').trim(),
        }))
        .filter((m) => !!m.drug_name)
      payload.prescription = { medications: meds }
    }

    const resp = await apiPostWithRecovery<{
      email_sent?: boolean
      email_reason?: string
      email_backend?: string
    }>(`/operations/medical-requests/${req.id}/fulfill/`, payload)
    const emailSent = resp.data?.email_sent === true
    const reason = typeof resp.data?.email_reason === 'string' ? resp.data.email_reason : ''
    const backend = typeof resp.data?.email_backend === 'string' ? resp.data.email_backend : ''
    if (emailSent) {
      $q.notify({ type: 'positive', message: `Medical request #${req.id} fulfilled and emailed to patient.`, position: 'top' })
    } else {
      let suffix = reason ? ` (${reason})` : ''
      if (reason === 'email_backend_not_configured') {
        suffix = ` (${reason}${backend ? ` • ${backend}` : ''}) — configure SENDGRID_API_KEY and DEFAULT_FROM_EMAIL on the backend to send real emails.`
      } else if (reason === 'missing_patient_email') {
        suffix = ` (${reason}) — patient has no email address on file.`
      } else if (reason === 'email_send_failed') {
        suffix = ` (${reason}${backend ? ` • ${backend}` : ''}) — check backend email configuration and logs.`
      } else if (reason === 'missing_attachments') {
        suffix = ` (${reason}) — no documents were attached to email.`
      }
      $q.notify({ type: 'warning', message: `Medical request #${req.id} fulfilled, but email was not sent${suffix ? ` ${suffix}` : ''}`, position: 'top' })
    }
    showFulfillMedicalRequestDialog.value = false
    selectedMedicalRequest.value = null
    await loadMedicalRequests()
    await loadNotifications()
  } catch (e) {
    const ax = e as { response?: { data?: unknown } }
    const data = ax?.response?.data as { error?: unknown; details?: unknown } | undefined
    const err = typeof data?.error === 'string' ? data.error : ''
    const details = typeof data?.details === 'string' ? data.details : ''
    const msg = err || details || getErrorMessage(e) || 'Failed to fulfill medical request.'
    $q.notify({ type: 'negative', message: msg, position: 'top' })
  } finally {
    medicalRequestSubmitting.value = false
  }
}

// Archival dialog state
const showArchiveDialog = ref(false);
const archiveReason = ref('');
const selectedPatientForArchive = ref<Patient | null>(null);

type MedicalRecordDiagnosisItem = {
  diagnosis: string
  created_at?: string | null
  completed_at?: string | null
  assignment_id?: number | null
}

const showSendMedicalRecordsDialog = ref(false)
const sendMedicalRecordsStep = ref(1)
const sendMedicalRecordsPatient = ref<Patient | null>(null)
const sendMedicalRecordsPreviewLoading = ref(false)
const sendMedicalRecordsPreviewError = ref<string | null>(null)
const sendMedicalRecordsDiagnoses = ref<MedicalRecordDiagnosisItem[]>([])
const sendMedicalRecordsConfirmed = ref(false)
const sendMedicalRecordsSubmitting = ref(false)
const sendMedicalRecordsTransferId = ref<number | null>(null)
const sendMedicalRecordsSentAt = ref<string | null>(null)
const sendMedicalRecordsStatusUpdatedAt = ref<string | null>(null)
const sendMedicalRecordsStatusError = ref<string | null>(null)
const sendMedicalRecordsStatusPolling = ref(false)
const sendMedicalRecordsEmailStatus = ref<string>('')
let sendMedicalRecordsPollTimer: ReturnType<typeof setInterval> | null = null

const sendMedicalRecordsStatusLabel = computed(() => {
  const s = (sendMedicalRecordsEmailStatus.value || '').toLowerCase()
  if (s === 'sent') return 'Sent'
  if (s === 'failed') return 'Failed'
  if (s === 'pending') return 'Pending'
  return '—'
})

// Nurse Intake dialog state
const showNurseIntakeDialog = ref(false)
const nurseIntakeLoading = ref(false)
const nurseIntakeData = ref<Record<string, unknown>>({})
const nurseIntakeError = ref<string | null>(null)
const nurseIntakePatientId = ref<number | null>(null)

const showConsultationDialog = ref(false)
const consultationLoading = ref(false)
const consultationSaving = ref(false)
const consultationAssignmentId = ref<number | null>(null)
const consultationPatient = ref<Patient | null>(null)
const consultationForm = ref({
  chief_complaint: '',
  history_of_present_illness: '',
  physical_examination: '',
  diagnosis: '',
  treatment_plan: '',
  medications_prescribed: '',
  follow_up_instructions: '',
  additional_notes: '',
  status: 'draft',
  assignment_status: 'pending'
})

const consultationAssignmentStatusOptions = [
  { label: 'Pending', value: 'pending' },
  { label: 'Accepted', value: 'accepted' },
  { label: 'In Progress', value: 'in_progress' },
  { label: 'Completed', value: 'completed' },
  { label: 'Rejected', value: 'rejected' }
]

const consultationNoteStatusOptions = [
  { label: 'Draft', value: 'draft' },
  { label: 'Reviewed', value: 'reviewed' },
  { label: 'Completed', value: 'completed' }
]
const hasNurseIntakeData = computed(() => {
  const d = nurseIntakeData.value
  return !!d && Object.keys(d).length > 0
})
const physicalFormRevisionDate = computed(() => {
  const d = new Date()
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
})
const hasNursePhysicalFormData = computed(() => {
  const d = nurseIntakeData.value || {}
  return Boolean(d['registration_physical'] || d['registration'] || d['opd_assessment'])
})
const nursePhysicalFormModel = computed(() => {
  const d = nurseIntakeData.value || {}
  const registrationPhysical = ((d['registration_physical'] as Record<string, unknown> | undefined) || (d['registration'] as Record<string, unknown> | undefined)) || {}
  const emergencyContact = (registrationPhysical['emergency_contact'] as Record<string, unknown> | undefined) || {}
  const opdAssessment = (d['opd_assessment'] as Record<string, unknown> | undefined) || {}
  const vitals = (opdAssessment['vitals'] as Record<string, unknown> | undefined) || {}
  const physicalExam = (opdAssessment['physical_exam'] as Record<string, unknown> | undefined) || {}
  const incomingLabs = (opdAssessment['labs'] as Record<string, unknown> | undefined) || {}

  const labKeys = ['cbc', 'urinalysis', 'fecalysis', 'cxr', 'ishihara', 'audio', 'psychological_exam', 'drug_test', 'hbsag'] as const
  const labs: Record<(typeof labKeys)[number], { checked: boolean; result: string }> = {
    cbc: { checked: false, result: '' },
    urinalysis: { checked: false, result: '' },
    fecalysis: { checked: false, result: '' },
    cxr: { checked: false, result: '' },
    ishihara: { checked: false, result: '' },
    audio: { checked: false, result: '' },
    psychological_exam: { checked: false, result: '' },
    drug_test: { checked: false, result: '' },
    hbsag: { checked: false, result: '' }
  }
  for (const k of labKeys) {
    const item = incomingLabs[k] as { checked?: unknown; result?: unknown } | undefined
    labs[k] = {
      checked: !!item?.checked,
      result: typeof item?.result === 'string' ? item.result : ''
    }
  }

  const toText = (v: unknown): string => (typeof v === 'string' ? v : typeof v === 'number' ? String(v) : '')

  return {
    registration: {
      surname: toText(registrationPhysical['surname']),
      first_name: toText(registrationPhysical['first_name']),
      middle_name: toText(registrationPhysical['middle_name']),
      age: typeof registrationPhysical['age'] === 'number' ? registrationPhysical['age'] : null,
      birthday: toText(registrationPhysical['birthday']),
      sex: toText(registrationPhysical['sex']),
      civil_status: toText(registrationPhysical['civil_status']),
      address: toText(registrationPhysical['address']),
      contact_no: toText(registrationPhysical['contact_no']),
      patient_id: toText(registrationPhysical['patient_id'] ?? registrationPhysical['student_employee_no']),
      department: toText(registrationPhysical['department']),
      nationality: toText(registrationPhysical['nationality']),
      religion: toText(registrationPhysical['religion']),
      emergency_contact: {
        name: toText(emergencyContact['name']),
        relationship: toText(emergencyContact['relationship']),
        contact_no: toText(emergencyContact['contact_no'])
      }
    },
    opd_assessment: {
      complaints_pe_findings: toText(opdAssessment['complaints_pe_findings']),
      vitals: {
        bp: toText(vitals['bp']),
        pr: typeof vitals['pr'] === 'number' ? vitals['pr'] : null,
        rr: typeof vitals['rr'] === 'number' ? vitals['rr'] : null,
        temp: typeof vitals['temp'] === 'number' ? vitals['temp'] : null
      },
      physical_exam: {
        heent: toText(physicalExam['heent']),
        heart: toText(physicalExam['heart']),
        lungs: toText(physicalExam['lungs']),
        abdomen_extremities: toText(physicalExam['abdomen_extremities'])
      },
      labs,
      date: toText(opdAssessment['date']),
      diagnosis_treatment_remarks: toText(opdAssessment['diagnosis_treatment_remarks']),
      staff: toText(opdAssessment['staff'])
    }
  }
})
const physicalStaffOptions = computed(() => {
  const opts: string[] = []
  const staff = ((nurseIntakeData.value || {})['opd_assessment'] as Record<string, unknown> | undefined)?.['staff']
  const staffName = typeof staff === 'string' ? staff.trim() : ''
  const doctorName = String(userProfile.value?.full_name || '').trim()
  if (staffName) opts.push(staffName)
  if (doctorName && !opts.includes(doctorName)) opts.push(doctorName)
  return opts
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

const loadNurseIntakeForPatient = async (patient: Patient, silent: boolean): Promise<void> => {
  const pid = Number(patient.id ?? patient.user_id)
  if (!Number.isFinite(pid)) {
    nurseIntakePatientId.value = null
    nurseIntakeData.value = {}
    nurseIntakeError.value = 'Invalid patient ID.'
    if (!silent) $q.notify({ type: 'negative', message: nurseIntakeError.value, position: 'top' })
    return
  }

  nurseIntakePatientId.value = pid
  nurseIntakeLoading.value = true
  nurseIntakeError.value = null

  try {
    const endpoint = `/users/doctor/patient/${pid}/nurse-intake/`
    const resp = await api.get(endpoint)
    nurseIntakeData.value = resp.data?.data ?? {}
    nurseIntakeError.value = null
    void api.post('/operations/client-log/', {
      level: 'info',
      message: 'doctor_view_nurse_intake_succeeded',
      route: 'DoctorPatientManagement',
      context: { patient_id: String(pid), has_data: Boolean(nurseIntakeData.value && Object.keys(nurseIntakeData.value).length) }
    }).catch(() => { /* non-blocking */ })
  } catch (error) {
    const ax = error as AxiosError<{ error?: unknown }>
    const statusCode = ax.response?.status
    const serverError = ax.response?.data?.error
    const msg =
      typeof serverError === 'string' && serverError.trim().length > 0
        ? serverError
        : statusCode === 403
          ? 'Not authorized for this patient.'
          : 'Failed to load nurse intake.'

    nurseIntakeError.value = msg
    nurseIntakeData.value = {}
    if (!silent) $q.notify({ type: statusCode === 403 ? 'warning' : 'negative', message: msg, position: 'top' })
    void api.post('/operations/client-log/', {
      level: 'error',
      message: 'doctor_view_nurse_intake_failed',
      route: 'DoctorPatientManagement',
      context: { patient_id: String(pid), status: String(statusCode || ''), error: String(error) }
    }).catch(() => { /* non-blocking */ })
  } finally {
    nurseIntakeLoading.value = false
  }
}

const _stopMedicalRecordsStatusPolling = (): void => {
  if (sendMedicalRecordsPollTimer) {
    clearInterval(sendMedicalRecordsPollTimer)
    sendMedicalRecordsPollTimer = null
  }
  sendMedicalRecordsStatusPolling.value = false
}

const _resetSendMedicalRecordsState = (): void => {
  _stopMedicalRecordsStatusPolling()
  sendMedicalRecordsStep.value = 1
  sendMedicalRecordsPatient.value = null
  sendMedicalRecordsPreviewLoading.value = false
  sendMedicalRecordsPreviewError.value = null
  sendMedicalRecordsDiagnoses.value = []
  sendMedicalRecordsConfirmed.value = false
  sendMedicalRecordsSubmitting.value = false
  sendMedicalRecordsTransferId.value = null
  sendMedicalRecordsSentAt.value = null
  sendMedicalRecordsStatusUpdatedAt.value = null
  sendMedicalRecordsStatusError.value = null
  sendMedicalRecordsEmailStatus.value = ''
}

const _loadMedicalRecordsStatus = async (transferId: number, silent: boolean): Promise<void> => {
  sendMedicalRecordsStatusPolling.value = true
  try {
    const resp = await api.get(`/operations/medical-record-transfers/${transferId}/status/`)
    const statusRaw = String(resp.data?.email_delivery_status || '').toLowerCase()
    sendMedicalRecordsEmailStatus.value = statusRaw
    sendMedicalRecordsSentAt.value = typeof resp.data?.email_sent_at === 'string' ? resp.data.email_sent_at : null
    sendMedicalRecordsStatusUpdatedAt.value = new Date().toISOString()
    sendMedicalRecordsStatusError.value = typeof resp.data?.error_message === 'string' ? resp.data.error_message : null

    if (statusRaw === 'sent' || statusRaw === 'failed') {
      _stopMedicalRecordsStatusPolling()
      if (!silent) {
        $q.notify({
          type: statusRaw === 'sent' ? 'positive' : 'negative',
          message: statusRaw === 'sent' ? 'Medical records sent successfully.' : 'Medical records delivery failed.',
          position: 'top'
        })
      }
    }
  } catch (e) {
    const msg = extractErrorMessage(e, 'Failed to load delivery status')
    sendMedicalRecordsStatusError.value = msg
    if (!silent) $q.notify({ type: 'negative', message: msg, position: 'top' })
  } finally {
    sendMedicalRecordsStatusPolling.value = false
  }
}

const _startMedicalRecordsStatusPolling = (transferId: number): void => {
  _stopMedicalRecordsStatusPolling()
  void _loadMedicalRecordsStatus(transferId, true)
  sendMedicalRecordsPollTimer = setInterval(() => {
    void _loadMedicalRecordsStatus(transferId, true)
  }, 2000)
}

const _loadMedicalRecordsPreview = async (patient: Patient): Promise<void> => {
  sendMedicalRecordsPreviewLoading.value = true
  sendMedicalRecordsPreviewError.value = null
  sendMedicalRecordsDiagnoses.value = []
  try {
    const pid = Number(patient.user_id ?? patient.id)
    if (!Number.isFinite(pid)) throw new Error('Invalid patient ID')
    const resp = await api.post('/operations/doctor/medical-records/preview/', { patient_id: pid })
    const rows = Array.isArray(resp.data?.diagnoses) ? resp.data.diagnoses : []
    sendMedicalRecordsDiagnoses.value = rows
  } catch (e) {
    const msg = extractErrorMessage(e, 'Failed to load medical records preview')
    sendMedicalRecordsPreviewError.value = msg
  } finally {
    sendMedicalRecordsPreviewLoading.value = false
  }
}

const openSendMedicalRecords = async (patient: Patient): Promise<void> => {
  _resetSendMedicalRecordsState()
  sendMedicalRecordsPatient.value = patient
  showSendMedicalRecordsDialog.value = true
  await _loadMedicalRecordsPreview(patient)
}

const submitSendMedicalRecords = async (): Promise<void> => {
  const patient = sendMedicalRecordsPatient.value
  if (!patient) {
    $q.notify({ type: 'warning', message: 'No patient selected', position: 'top' })
    return
  }
  const pid = Number(patient.user_id ?? patient.id)
  if (!Number.isFinite(pid)) {
    $q.notify({ type: 'warning', message: 'Invalid patient ID', position: 'top' })
    return
  }
  sendMedicalRecordsSubmitting.value = true
  sendMedicalRecordsStatusError.value = null
  try {
    const payload: Record<string, unknown> = {
      patient_id: pid,
      assignment_id: patient.assignment_id ?? null,
      confirm: true
    }
    const resp = await api.post('/operations/doctor/medical-records/send/', payload)
    const transferId = Number(resp.data?.transfer_id)
    if (!Number.isFinite(transferId)) throw new Error('Missing transfer_id from server')
    sendMedicalRecordsTransferId.value = transferId
    sendMedicalRecordsStep.value = 3
    _startMedicalRecordsStatusPolling(transferId)
  } catch (e) {
    const msg = extractErrorMessage(e, 'Failed to send medical records')
    $q.notify({ type: 'negative', message: msg, position: 'top' })
  } finally {
    sendMedicalRecordsSubmitting.value = false
  }
}

const openNurseIntake = async (patient: Patient): Promise<void> => {
  try {
    selectedPatient.value = patient
    showNurseIntakeDialog.value = true
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
    await loadNurseIntakeForPatient(patient, false)
  } catch (error) {
    console.error('Failed to load nurse intake:', error)
  } finally {
    nurseIntakeLoading.value = false
  }
}

const acceptAssignment = async (patient: Patient): Promise<void> => {
  const assignmentId = Number(patient.assignment_id)
  if (!Number.isFinite(assignmentId)) {
    $q.notify({ type: 'warning', message: 'Missing assignment id', position: 'top' })
    return
  }
  try {
    await api.post(`/operations/doctor/assignments/${assignmentId}/accept/`)
    patient.assignment_status = 'accepted'
    $q.notify({ type: 'positive', message: 'Assignment accepted', position: 'top' })
    void loadPatients()
  } catch (e) {
    const ax = e as AxiosError<{ error?: unknown }>
    const apiMsg = ax.response?.data?.error
    const msg = typeof apiMsg === 'string' && apiMsg.trim() ? apiMsg : 'Failed to accept assignment'
    $q.notify({ type: 'negative', message: msg, position: 'top' })
  }
}

const _resetConsultationForm = (): void => {
  consultationForm.value = {
    chief_complaint: '',
    history_of_present_illness: '',
    physical_examination: '',
    diagnosis: '',
    treatment_plan: '',
    medications_prescribed: '',
    follow_up_instructions: '',
    additional_notes: '',
    status: 'draft',
    assignment_status: 'pending'
  }
}

const openConsultationNotes = async (patient: Patient): Promise<void> => {
  const assignmentId = Number(patient.assignment_id)
  if (!Number.isFinite(assignmentId)) {
    $q.notify({ type: 'warning', message: 'Missing assignment id', position: 'top' })
    return
  }
  consultationPatient.value = patient
  consultationAssignmentId.value = assignmentId
  _resetConsultationForm()
  showConsultationDialog.value = true
  await reloadConsultationNotes()
}

const reloadConsultationNotes = async (): Promise<void> => {
  const assignmentId = Number(consultationAssignmentId.value)
  if (!Number.isFinite(assignmentId)) return
  consultationLoading.value = true
  try {
    const resp = await apiGetWithRecovery<{
      success?: boolean
      data?: Record<string, unknown> | null
      assignment?: { status?: string }
    }>(`/operations/doctor/assignments/${assignmentId}/consultation-notes/`)
    const data = resp.data?.data
    const assignmentStatus = String(resp.data?.assignment?.status || '').trim()

    if (assignmentStatus === 'pending' || assignmentStatus === 'accepted' || assignmentStatus === 'in_progress' || assignmentStatus === 'completed' || assignmentStatus === 'rejected') {
      consultationForm.value.assignment_status = assignmentStatus
    }
    if (!data) return

    const getStr = (k: string): string => (typeof data[k] === 'string' ? String(data[k]) : '')
    const noteStatusRaw = getStr('status').toLowerCase()
    if (noteStatusRaw === 'draft' || noteStatusRaw === 'completed' || noteStatusRaw === 'reviewed') {
      consultationForm.value.status = noteStatusRaw
    }
    consultationForm.value.chief_complaint = getStr('chief_complaint')
    consultationForm.value.history_of_present_illness = getStr('history_of_present_illness')
    consultationForm.value.physical_examination = getStr('physical_examination')
    consultationForm.value.diagnosis = getStr('diagnosis')
    consultationForm.value.treatment_plan = getStr('treatment_plan')
    consultationForm.value.medications_prescribed = getStr('medications_prescribed')
    consultationForm.value.follow_up_instructions = getStr('follow_up_instructions')
    consultationForm.value.additional_notes = getStr('additional_notes')
  } catch (e) {
    const ax = e as AxiosError<{ error?: unknown }>
    const apiMsg = ax.response?.data?.error
    const msg = typeof apiMsg === 'string' && apiMsg.trim() ? apiMsg : 'Failed to load consultation notes'
    $q.notify({ type: 'negative', message: msg, position: 'top' })
  } finally {
    consultationLoading.value = false
  }
}

const saveConsultationNotes = async (): Promise<void> => {
  const assignmentId = Number(consultationAssignmentId.value)
  if (!Number.isFinite(assignmentId)) return
  consultationSaving.value = true
  try {
    const payload = {
      ...consultationForm.value,
      assignment_status: consultationForm.value.assignment_status,
      status: consultationForm.value.status
    }
    const resp = await api.post(`/operations/doctor/assignments/${assignmentId}/consultation-notes/`, payload)
    const newStatus = String(resp.data?.assignment?.status || consultationForm.value.assignment_status)
    if (consultationPatient.value) {
      consultationPatient.value.assignment_status = newStatus
    }
    $q.notify({ type: 'positive', message: 'Consultation notes saved', position: 'top' })
    void loadPatients()
  } catch (e) {
    const ax = e as AxiosError<{ error?: unknown }>
    const apiMsg = ax.response?.data?.error
    const msg = typeof apiMsg === 'string' && apiMsg.trim() ? apiMsg : 'Failed to save consultation notes'
    $q.notify({ type: 'negative', message: msg, position: 'top' })
  } finally {
    consultationSaving.value = false
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

    $q.notify({ 
      type: 'positive', 
      message: 'Patient record has been successfully archived and moved to the archive list.',
      position: 'top',
      timeout: 3000
    })
    showArchiveDialog.value = false
    selectedPatientForArchive.value = null
    archiveReason.value = ''
    void loadArchivedPatients()
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

const extractErrorMessage = (err: unknown, fallback: string): string => {
  const e = err as { response?: { data?: unknown; status?: number }; message?: unknown }
  const data = e?.response?.data as Record<string, unknown> | undefined
  const errorVal = data?.error
  const messageVal = data?.message
  const detailVal = data?.detail
  if (typeof messageVal === 'string' && messageVal.trim()) return messageVal.trim()
  if (typeof errorVal === 'string' && errorVal.trim()) return errorVal.trim()
  if (typeof detailVal === 'string' && detailVal.trim()) return detailVal.trim()
  const raw = getErrorMessage(err)
  if (raw && raw !== '{}' && raw !== 'null' && raw !== 'undefined') return raw
  return fallback
}

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

const applyPatientDemographics = (
  pid: number,
  patch: { age?: number | null; gender?: string | null; blood_type?: string | null; email?: string | null },
): void => {
  const safeAge = typeof patch.age === 'number' && Number.isFinite(patch.age) ? patch.age : null
  const safeGender = typeof patch.gender === 'string' ? patch.gender : null
  const safeBlood = typeof patch.blood_type === 'string' ? patch.blood_type : null
  const safeEmail = typeof patch.email === 'string' ? patch.email : null

  if (selectedPatient.value && Number(selectedPatient.value.user_id ?? selectedPatient.value.id) === pid) {
    if (safeAge !== null) selectedPatient.value.age = safeAge
    if (safeGender) selectedPatient.value.gender = safeGender
    if (safeBlood) selectedPatient.value.blood_type = safeBlood
    if (safeEmail) selectedPatient.value.email = safeEmail
  }

  const idx = patients.value.findIndex(p => Number(p.user_id ?? p.id) === pid)
  if (idx >= 0) {
    const cur = patients.value[idx]
    if (!cur) return
    const next: Patient = {
      ...cur,
      ...(safeAge !== null ? { age: safeAge } : {}),
      ...(safeGender ? { gender: safeGender } : {}),
      ...(safeBlood ? { blood_type: safeBlood } : {}),
      ...(safeEmail ? { email: safeEmail } : {}),
    }
    patients.value.splice(idx, 1, next)
  }
}

type PatientOverviewPatch = { age?: number | null; gender?: string | null; blood_type?: string | null; email?: string | null }
const OVERVIEW_TTL_MS = 5 * 60 * 1000
const overviewCache = new Map<number, { patch: PatientOverviewPatch; ts: number }>()
const overviewFailCache = new Map<number, number>()

const extractPatientOverview = (p: unknown): PatientOverviewPatch | null => {
  if (!p || typeof p !== 'object') return null
  const a = p as Record<string, unknown>
  const email = typeof a.email === 'string' && a.email.trim() ? a.email : null
  const genderRaw =
    (typeof a.gender === 'string' && a.gender.trim() ? a.gender : null) ??
    (typeof a.sex === 'string' && a.sex.trim() ? a.sex : null)
  const dobRaw =
    (typeof a.date_of_birth === 'string' && a.date_of_birth.trim() ? a.date_of_birth : null) ??
    (typeof a.dob === 'string' && a.dob.trim() ? a.dob : null)
  const bloodRaw =
    (typeof a.blood_type === 'string' && a.blood_type.trim() ? a.blood_type : null) ??
    (typeof a.bloodType === 'string' && a.bloodType.trim() ? a.bloodType : null)

  const ageRaw = a.age
  const ageFromApi =
    typeof ageRaw === 'number' && Number.isFinite(ageRaw)
      ? ageRaw
      : (typeof ageRaw === 'string' && ageRaw.trim() && Number.isFinite(Number(ageRaw)) ? Number(ageRaw) : null)

  let ageFromDob: number | null = null
  if (ageFromApi === null && dobRaw) {
    try {
      const d = new Date(dobRaw)
      if (!Number.isNaN(d.getTime())) {
        const diff = Date.now() - d.getTime()
        const ageDt = new Date(diff)
        ageFromDob = Math.abs(ageDt.getUTCFullYear() - 1970)
      }
    } catch {
      ageFromDob = null
    }
  }

  const age = ageFromApi ?? ageFromDob
  const patch: PatientOverviewPatch = {
    ...(email ? { email } : {}),
    ...(genderRaw ? { gender: genderRaw } : {}),
    ...(bloodRaw ? { blood_type: bloodRaw } : {}),
    ...(typeof age === 'number' && Number.isFinite(age) ? { age } : {}),
  }
  return Object.keys(patch).length ? patch : null
}

const fetchPatientOverview = async (pid: number): Promise<PatientOverviewPatch | null> => {
  const now = Date.now()
  const cached = overviewCache.get(pid)
  if (cached && now - cached.ts < OVERVIEW_TTL_MS) return cached.patch

  const failedAt = overviewFailCache.get(pid)
  if (failedAt && now - failedAt < 60 * 1000) return null

  try {
    const resp = await api.get(`/users/doctor/patient/${pid}/forms/`)
    const patch = extractPatientOverview(resp.data?.patient)
    if (patch) overviewCache.set(pid, { patch, ts: now })
    return patch
  } catch {
    overviewFailCache.set(pid, now)
    return null
  }
}

const hydratePatientsOverview = async (list: Patient[]): Promise<void> => {
  const ids = Array.from(
    new Set(
      list
        .map(p => Number(p.user_id ?? p.id))
        .filter(n => Number.isFinite(n) && n > 0),
    ),
  )

  const needs = (pid: number) => {
    const p = patients.value.find(x => Number(x.user_id ?? x.id) === pid)
    if (!p) return false
    const missingAge = typeof p.age !== 'number' || !Number.isFinite(p.age)
    const missingGender = !p.gender || !String(p.gender).trim()
    const missingBlood = !p.blood_type || !String(p.blood_type).trim()
    return missingAge || missingGender || missingBlood
  }

  let i = 0
  const workerCount = Math.min(3, ids.length)
  const workers = Array.from({ length: workerCount }, async () => {
    while (i < ids.length) {
      const pid = ids[i]
      i += 1
      if (typeof pid !== 'number') continue
      if (!needs(pid)) continue
      const patch = await fetchPatientOverview(pid)
      if (patch) applyPatientDemographics(pid, patch)
    }
  })
  await Promise.all(workers)
}

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

    const needsApiOverview =
      !merged ||
      Object.keys(merged).length === 0 ||
      !merged.email ||
      !merged.sex ||
      !merged.dob ||
      typeof merged.age !== 'number' ||
      typeof selectedPatient.value?.age !== 'number' ||
      !selectedPatient.value?.gender ||
      !selectedPatient.value?.blood_type

    // 2) Attempt minimal overview endpoint to fill gaps (age/sex/blood type/email/DOB)
    if (needsApiOverview) {
      try {
        const resp = await api.get(`/users/doctor/patient/${pid}/forms/`)
        const p = resp.data?.patient
        if (p && typeof p === 'object') {
          const pAny = p as {
            email?: unknown;
            gender?: unknown;
            sex?: unknown;
            date_of_birth?: unknown;
            dob?: unknown;
            age?: unknown;
            blood_type?: unknown;
            bloodType?: unknown;
          }

          const email = typeof pAny.email === 'string' && pAny.email.trim() ? pAny.email : null
          const genderRaw =
            (typeof pAny.gender === 'string' && pAny.gender.trim() ? pAny.gender : null) ??
            (typeof pAny.sex === 'string' && pAny.sex.trim() ? pAny.sex : null)
          const dobRaw =
            (typeof pAny.date_of_birth === 'string' && pAny.date_of_birth.trim() ? pAny.date_of_birth : null) ??
            (typeof pAny.dob === 'string' && pAny.dob.trim() ? pAny.dob : null)
          const bloodRaw =
            (typeof pAny.blood_type === 'string' && pAny.blood_type.trim() ? pAny.blood_type : null) ??
            (typeof pAny.bloodType === 'string' && pAny.bloodType.trim() ? pAny.bloodType : null)

          const ageFromApi =
            typeof pAny.age === 'number' && Number.isFinite(pAny.age)
              ? pAny.age
              : (typeof pAny.age === 'string' && pAny.age.trim() && Number.isFinite(Number(pAny.age)) ? Number(pAny.age) : null)

          let ageFromDob: number | null = null
          if (ageFromApi === null && dobRaw) {
            try {
              const d = new Date(dobRaw)
              if (!Number.isNaN(d.getTime())) {
                const diff = Date.now() - d.getTime()
                const ageDt = new Date(diff)
                ageFromDob = Math.abs(ageDt.getUTCFullYear() - 1970)
              }
            } catch {
              ageFromDob = null
            }
          }

          const age = ageFromApi ?? ageFromDob
          const overview: Demographics = {
            ...(email ? { email } : {}),
            ...(genderRaw ? { sex: genderRaw } : {}),
            ...(dobRaw ? { dob: dobRaw } : {}),
            ...(typeof age === 'number' && Number.isFinite(age) ? { age } : {}),
          }
          applyPatientDemographics(pid, {
            email,
            gender: genderRaw,
            age,
            blood_type: bloodRaw,
          })
          merged = mergePatientOverview(selectedPatient.value, overview)
        }
      } catch (e) {
        const ax = e as AxiosError
        if (ax.response?.status === 404) {
          demoLoadError.value = 'Demographics endpoint not found.'
        } else if (ax.response?.status === 403) {
          demoLoadError.value = 'Not authorized to view demographics for this patient.'
        }
      }
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

watch(selectedPatient, (p) => {
  if (p) {
    void loadDemographics()
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
    type ApiNurse = {
      id: number | string;
      full_name: string;
      email?: string;
      department?: string;
      availability?: string;
      on_duty?: boolean;
    };
    const response = await apiGetWithRecovery<{ nurses?: ApiNurse[]; checked_at?: unknown }>(url, {
      params: { include_email: true },
      timeout: 45000,
    });
    const maybeNurses = response.data?.nurses;
    const nurses: ApiNurse[] = Array.isArray(maybeNurses) ? maybeNurses : [];
    const rawCheckedAt = response.data?.checked_at;
    const checkedAt =
      typeof rawCheckedAt === 'string'
        ? rawCheckedAt
        : typeof rawCheckedAt === 'number'
          ? String(rawCheckedAt)
          : rawCheckedAt instanceof Date
            ? rawCheckedAt.toISOString()
            : '';

    const list: NurseSummary[] = nurses.map((n: ApiNurse) => ({
      id: n.id,
      full_name: n.full_name,
      department: n.department || 'General',
      status: n.on_duty ? 'On Duty' : 'Off Duty',
      availability: n.availability || (n.on_duty ? 'Available' : 'Off Duty'),
      email: n.email || '',
      profile_picture: null,
    }));
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

const stats = computed(() => {
  const normalize = (v: unknown) => {
    if (typeof v === 'string') return v.trim().toLowerCase()
    if (typeof v === 'number') return String(v).trim().toLowerCase()
    return ''
  }
  const total = patients.value.length
  const active = patients.value.filter(p => {
    const st = normalize(p.assignment_status)
    return st === 'pending' || st === 'accepted' || st === 'in_progress'
  }).length
  return { total_patients: total, active_patients: active }
})

// Medical records UI and loader removed per refactor

// Patient assignment data loading and actions
const loadPatients = async (opts?: { initial?: boolean }): Promise<void> => {
  loading.value = true;
  try {
    const selectedId = selectedPatient.value
      ? Number(selectedPatient.value.user_id ?? selectedPatient.value.id)
      : null

    let did = Number(userProfile.value.id)
    if (!Number.isFinite(did) || did <= 0) {
      try {
        const stored = JSON.parse(localStorage.getItem('user') || '{}') as { id?: unknown; user?: { id?: unknown }; user_id?: unknown }
        const maybe = stored.id ?? stored.user?.id ?? stored.user_id
        did = Number(maybe)
      } catch {
        // ignore
      }
    }

    const [assignmentsRes, appointmentsRes] = await Promise.all([
      apiGetWithRecovery('/operations/doctor/assignments/'),
      apiGetWithRecovery('/operations/appointments/', {
        params: Number.isFinite(did) && did > 0 ? { doctor: did } : {},
      }).catch(() => ({ data: [] } as AxiosResponse<unknown>)),
    ])

    const assignmentsRaw = assignmentsRes.data
    const appointmentsRaw = appointmentsRes.data

    const assignmentPatients: Patient[] = Array.isArray(assignmentsRaw)
      ? (assignmentsRaw as Array<{
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
      }>).map((assignment) => {
        const local = tryLoadDemographicsLocal(assignment.patient_id)
        const localPatch = extractPatientOverview(local)
        const localAge =
          typeof localPatch?.age === 'number' && Number.isFinite(localPatch.age) ? localPatch.age : null
        const localGender =
          typeof localPatch?.gender === 'string' && localPatch.gender.trim() ? localPatch.gender : null
        const localBlood =
          typeof localPatch?.blood_type === 'string' && localPatch.blood_type.trim() ? localPatch.blood_type : null

        return {
        id: assignment.patient_id,
        user_id: assignment.patient_id,
        full_name: assignment.patient_name,
        patient_name: assignment.patient_name,
        assignment_id: assignment.id,
        assignment_status: String(assignment.status || 'pending').trim().toLowerCase(),
        assigned_by: assignment.assigned_by_name,
        assigned_at: assignment.assigned_at,
        specialization_required: assignment.specialization_required,
        assignment_reason: assignment.assignment_reason,
        priority: assignment.priority,
        accepted_at: assignment.accepted_at,
        completed_at: assignment.completed_at,
        source: 'queue',
        // Default patient fields for compatibility
        medical_condition: '',
          age: localAge,
          gender: localGender || '',
          blood_type: localBlood || '',
        hospital: '',
        room_number: '',
        discharge_date: null,
        is_dummy: false
        }
      })
      : []

    type BackendAppointment = {
      id?: number;
      appointment_id?: number;
      patient_name?: string;
      patient?: { id?: number; name?: string; full_name?: string } | null;
      patient_id?: number;
      appointment_date?: string;
      date?: string;
      appointment_time?: string;
      time?: string;
      status?: string;
      doctor_id?: number;
      doctor?: number | { id?: number } | null;
    }

    const appointmentPatients: Patient[] = (Array.isArray(appointmentsRaw) ? appointmentsRaw : (appointmentsRaw as { results?: unknown[] } | null)?.results || [])
      .map((raw: unknown) => raw as BackendAppointment)
      .map((a): Patient | null => {
        const patientObj = a?.patient && typeof a.patient === 'object' ? a.patient : null
        const pid = Number(patientObj?.id ?? a?.patient_id ?? NaN)
        if (!Number.isFinite(pid) || pid <= 0) return null

        const name = String(a?.patient_name ?? patientObj?.name ?? patientObj?.full_name ?? '').trim()
        const apptId = Number(a?.appointment_id ?? a?.id ?? NaN)
        if (!Number.isFinite(apptId) || apptId <= 0) return null

        const status = String(a?.status ?? 'scheduled').trim().toLowerCase()
        const local = tryLoadDemographicsLocal(pid)
        const localPatch = extractPatientOverview(local)
        const localAge =
          typeof localPatch?.age === 'number' && Number.isFinite(localPatch.age) ? localPatch.age : null
        const localGender =
          typeof localPatch?.gender === 'string' && localPatch.gender.trim() ? localPatch.gender : null
        const localBlood =
          typeof localPatch?.blood_type === 'string' && localPatch.blood_type.trim() ? localPatch.blood_type : null

        const base: Patient = {
          id: pid,
          user_id: pid,
          full_name: name || `Patient ${pid}`,
          patient_name: name || `Patient ${pid}`,
          assignment_status: status,
          appointment_id: apptId,
          appointment_status: status,
          appointment_date: String(a?.appointment_date ?? a?.date ?? ''),
          appointment_time: String(a?.appointment_time ?? a?.time ?? ''),
          source: 'appointment',
          assigned_by: 'Appointment',
          assignment_reason: 'Scheduled appointment',
          priority: 'normal',
          medical_condition: '',
          age: localAge,
          gender: localGender || '',
          blood_type: localBlood || '',
          hospital: '',
          room_number: '',
          discharge_date: null,
          is_dummy: false,
        }
        if (Number.isFinite(did) && did > 0) base.assigned_doctor_id = did
        return base
      })
      .filter((p): p is Patient => !!p)

    const seen = new Set<number>()
    const merged: Patient[] = []
    for (const p of assignmentPatients) {
      const pid = Number(p.user_id ?? p.id)
      if (!Number.isFinite(pid)) continue
      if (seen.has(pid)) continue
      seen.add(pid)
      merged.push(p)
    }
    for (const p of appointmentPatients) {
      const pid = Number(p.user_id ?? p.id)
      if (!Number.isFinite(pid)) continue
      if (seen.has(pid)) continue
      seen.add(pid)
      merged.push(p)
    }

    patients.value = merged
      hasAssignmentsUpdate.value = false
      void hydratePatientsOverview(merged)

      if (selectedId !== null) {
        const stillSelected = patients.value.find(p => Number(p.user_id ?? p.id) === selectedId) || null
        selectedPatient.value = stillSelected
      }

      const isInitial = !!opts?.initial && !didInitialPatientsLoad.value
      if (isInitial) {
        didInitialPatientsLoad.value = true
      }

      if (isInitial && !didRoutePreselect.value) {
        didRoutePreselect.value = true
        const q = route.query as Record<string, string | string[] | undefined>
        const pidRaw = q.patientId ?? q.patient_id
        const pnameRaw = q.patientName ?? q.patient_name
        let candidate: Patient | undefined
        if (pidRaw) {
          const pid = Number(Array.isArray(pidRaw) ? pidRaw[0] : pidRaw)
          candidate = patients.value.find(p => p.id === pid || p.user_id === pid)
        }
        if (!candidate && pnameRaw) {
          const pname = String(Array.isArray(pnameRaw) ? pnameRaw[0] : pnameRaw).toLowerCase()
          candidate = patients.value.find(p => (p.full_name || p.patient_name || '').toLowerCase() === pname)
        }
        if (candidate) {
          selectPatient(candidate)
        }
      }

      if (isInitial && !selectedPatient.value) {
        const first = patients.value[0]
        if (first) {
          selectedPatient.value = first
          void loadVerificationStatus(first)
          void loadNurseIntakeForPatient(first, true)
        }
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
    }).catch(() => { /* non-blocking */ });
  } finally {
    loading.value = false;
  }
};

const formatArchivedAt = (dateStr: string | null): string => {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

const loadArchivedPatients = async (): Promise<void> => {
  archivedLoading.value = true
  try {
    const res = await api.get('/operations/archives/')
    const list = Array.isArray(res.data)
      ? res.data
      : Array.isArray(res.data?.results)
        ? res.data.results
        : (res.data?.records || [])

    archivedRecords.value = (list as Array<Record<string, unknown>>).map((raw) => {
      const id = Number(raw.id)
      const patientName = typeof raw.patient_name === 'string' ? raw.patient_name : (typeof raw.user_name === 'string' ? raw.user_name : '')
      const lastAssessed = typeof raw.last_assessed_at === 'string' ? raw.last_assessed_at : (typeof raw.archived_at === 'string' ? raw.archived_at : null)
      const assessmentData = (raw.assessment_data && typeof raw.assessment_data === 'object') ? (raw.assessment_data as Record<string, unknown>) : {}
      const reasonRaw = assessmentData.archival_reason ?? assessmentData.reason
      const reason = typeof reasonRaw === 'string' ? reasonRaw.trim() : ''
      const base: ArchivedPatientItem = {
        id,
        patient_name: patientName || '—',
        last_assessed_at: lastAssessed,
      }
      if (reason) return { ...base, archival_reason: reason }
      return base
    }).filter((x) => Number.isFinite(x.id) && x.patient_name !== '—')
  } catch (e) {
    console.error('Failed to load archived patients', e)
    archivedRecords.value = []
  } finally {
    archivedLoading.value = false
  }
}

const restoreArchivedPatient = async (rec: ArchivedPatientItem): Promise<void> => {
  restoreLoadingId.value = rec.id
  try {
    await api.post(`/operations/archives/${rec.id}/unarchive/`)
    $q.notify({ type: 'positive', message: 'Patient restored', position: 'top' })
    await loadArchivedPatients()
    await loadPatients()
  } catch (e) {
    console.error('Restore failed', e)
    $q.notify({ type: 'negative', message: 'Failed to restore patient', position: 'top' })
  } finally {
    restoreLoadingId.value = null
  }
}

const buildArchivePdfFilename = (rec: ArchivedPatientItem): string => {
  const raw = rec.patient_name || 'Patient'
  const cleaned = String(raw)
    .trim()
    .replace(/[\\/:*?"<>|]+/g, '')
    .replace(/\s+/g, ' ')
  const base = cleaned || `patient_${rec.id}`
  return `${base}.pdf`
}

const downloadArchivedPatient = async (rec: ArchivedPatientItem): Promise<void> => {
  downloadLoadingId.value = rec.id
  try {
    const res = await api.get(`/operations/archives/${rec.id}/export/`, { responseType: 'blob' })
    const blob = new Blob([res.data], { type: 'application/pdf' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = buildArchivePdfFilename(rec)
    a.click()
    URL.revokeObjectURL(url)
    $q.notify({ type: 'positive', message: 'Archive download started', position: 'top' })
  } catch (e) {
    console.error('Download failed', e)
    $q.notify({ type: 'negative', message: 'Failed to download archive', position: 'top' })
  } finally {
    downloadLoadingId.value = null
  }
}

const refreshPatientPanel = (): void => {
  void loadPatients()
  void loadArchivedPatients()
  hasAssignmentsUpdate.value = false
}

const selectPatient = (patient: Patient) => {
  selectedPatient.value = patient;
  if (selectedPatient.value) {
    console.log('Selected patient id:', selectedPatient.value.id);
    void loadVerificationStatus(patient);
    void loadNurseIntakeForPatient(patient, true)
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
    if (!Number.isFinite(pid) || pid <= 0) return;
    
    let did = Number(userProfile.value.id)
    if (!Number.isFinite(did) || did <= 0) {
      try {
        await fetchUserProfile()
        did = Number(userProfile.value.id)
      } catch {
        // ignore
      }
    }
    if (!Number.isFinite(did) || did <= 0) {
      try {
        const stored = JSON.parse(localStorage.getItem('user') || '{}') as { id?: unknown; user?: { id?: unknown }; user_id?: unknown }
        const maybe = stored.id ?? stored.user?.id ?? stored.user_id
        did = Number(maybe)
      } catch {
        // ignore
      }
    }
    if (!Number.isFinite(did) || did <= 0) return
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
    const ax = error as AxiosError
    if (ax.response?.status !== 404) {
      $q.notify({ type: 'warning', message: 'Failed to verify data availability', position: 'top' });
    }
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
  selectedPatient.value = patient;
  const type = selectedFormType.value;
  if (!type) {
    $q.notify({ type: 'info', message: 'Select a form type first.', position: 'top' });
    return;
  }
  void openFormForPatient(patient, type);
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
type FormType = 'psych_opd' | 'nurse_opd_form'
const showDoctorFormDialog = ref(false)
const selectedFormType = ref<FormType | null>(null)
const selectedFormPatient = ref<Patient | null>(null)
const selectedFormPatientAvatarFailed = ref(false)
const selectedFormPatientAvatarSrc = computed(() => {
  const raw = selectedFormPatient.value?.profile_picture
  if (typeof raw !== 'string') return null
  const v = raw.trim()
  if (!v) return null
  return v.startsWith('http') ? v : getMediaUrl(v)
})
const psychPrefillFullName = computed(() => {
  const d = demographics.value
  if (d && (d.firstName || d.lastName)) {
    return `${d.firstName || ''} ${d.lastName || ''}`.trim()
  }
  const p = selectedFormPatient.value
  return String(p?.full_name || p?.patient_name || '').trim()
})
const psychPrefillDateOfBirth = computed(() => {
  const d = demographics.value
  if (d?.dob) return d.dob
  const p = selectedFormPatient.value
  return String(p?.date_of_birth || '').trim()
})
const psychPrefillAge = computed(() => {
  const d = demographics.value
  if (typeof d?.age === 'number' && Number.isFinite(d.age)) return d.age
  const p = selectedFormPatient.value
  return typeof p?.age === 'number' && Number.isFinite(p.age) ? p.age : null
})
watch(
  () => [selectedFormPatient.value?.id, selectedFormPatient.value?.profile_picture],
  () => { selectedFormPatientAvatarFailed.value = false }
)

const hasRegistration = computed(() => {
  const d = nurseIntakeData.value || {}
  const raw = ((d['registration_physical'] as Record<string, unknown> | undefined) || (d['registration'] as Record<string, unknown> | undefined)) || {}
  if (raw && Object.keys(raw).length > 0) return true

  const m = nursePhysicalFormModel.value?.registration
  if (!m) return false
  return Boolean(
    (m.surname && String(m.surname).trim()) ||
    (m.first_name && String(m.first_name).trim()) ||
    (m.patient_id && String(m.patient_id).trim()) ||
    (m.address && String(m.address).trim()) ||
    (m.contact_no && String(m.contact_no).trim())
  )
})

const formTypeOptions = computed(() => ([
  { label: 'Select Form Type', value: null },
  { label: 'Nurse Registration & Assessment Form', value: 'nurse_opd_form' },
  { label: 'Psychiatric OPD Questionnaire', value: 'psych_opd' },
]))

// Computed property for form dialog title
const formDialogTitle = computed(() => {
  if (!selectedFormType.value) return 'Medical Form';
  
  switch(selectedFormType.value) {
    case 'nurse_opd_form': return 'Nurse Registration & Assessment Form';
    case 'psych_opd': return 'Psychiatric OPD Questionnaire';
    default: return 'Medical Form';
  }
})

// Form type change handler
const onFormTypeChange = (value: FormType | null) => {
  if (value && selectedPatient.value) {
    void openFormForPatient(selectedPatient.value, value)
  }
}

// Close form function
const closeForm = () => {
  showDoctorFormDialog.value = false
  selectedFormType.value = null
  selectedFormPatient.value = null
}

const openFormForPatient = async (patient: Patient, type: FormType): Promise<void> => {
  const pid = Number(patient.id ?? patient.user_id)
  const shouldRefresh = !Number.isFinite(pid) || nurseIntakePatientId.value !== pid || (!hasNurseIntakeData.value && !nurseIntakeLoading.value)
  if (shouldRefresh) {
    await loadNurseIntakeForPatient(patient, true)
  }

  if (type === 'psych_opd' && !hasRegistration.value) {
    $q.notify({ type: 'warning', message: 'Patient registration is required before opening the psychiatric questionnaire.' })
    selectedFormType.value = null
    return
  }
  selectedFormPatient.value = patient
  selectedFormType.value = type
  showDoctorFormDialog.value = true
}

// Doctor messaging WebSocket for real-time patient assignments
let doctorMessagingWS: WebSocket | null = null;
let wsRetries = 0;
let wsShouldRun = false;
let wsReconnectTimer: number | null = null;

const setupDoctorMessagingWS = (): void => {
  try {
    if (!wsShouldRun) return;
    const base = new URL(api.defaults.baseURL || `http://${window.location.hostname}:8000`);
    const protocol = base.protocol === 'https:' ? 'wss:' : 'ws:';
    const backendHost = base.host || base.hostname;
    const storedUser = JSON.parse(localStorage.getItem('user') || '{}');
    const userId = storedUser.id || storedUser.user?.id || storedUser.user_id;

    if (!userId) {
      console.warn('No user id found for doctor messaging WebSocket');
      return;
    }

    const wsUrl = `${protocol}//${backendHost}/ws/messaging/${userId}/`;
    if (wsReconnectTimer != null) {
      clearTimeout(wsReconnectTimer);
      wsReconnectTimer = null;
    }
    if (doctorMessagingWS) {
      try { doctorMessagingWS.close(); } catch { /* ignore */ } finally { doctorMessagingWS = null; }
    }
    const ws = new WebSocket(wsUrl);
    doctorMessagingWS = ws;

    ws.onopen = () => {
      console.log('DoctorPatientManagement messaging WebSocket connected');
      wsRetries = 0;
    };

    ws.onmessage = (event: MessageEvent) => {
      try {
        if (typeof event.data !== 'string') return;
        const data = JSON.parse(event.data);
        if (data.type === 'notification') {
          const notif = data.notification || {};
          if (notif.event === 'patient_assigned') {
            $q.notify({
              type: 'info',
              message: 'New patient assigned to you. Click refresh to update your list.',
              position: 'top'
            });
            hasAssignmentsUpdate.value = true
            void loadNotifications();
          } else if (notif.event === 'medical_request_created') {
            $q.notify({
              type: 'info',
              message: 'New medical request received.',
              position: 'top'
            })
            void loadMedicalRequests()
            void loadNotifications()
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
      if (!wsShouldRun) return;
      if (wsRetries >= 6) return;
      const delay = Math.min(30000, 2000 * Math.pow(2, wsRetries++));
      wsReconnectTimer = window.setTimeout(() => setupDoctorMessagingWS(), delay);
    };
  } catch (e) {
    console.warn('Failed to setup doctor messaging WebSocket', e);
  }
};

watch(showSendMedicalRecordsDialog, (open) => {
  if (!open) {
    _resetSendMedicalRecordsState()
  }
})

onMounted(() => {

  console.log('🚀 DoctorPatientManagement component mounted');
  wsShouldRun = true;
  if (typeof window !== 'undefined') window.addEventListener('resize', handleViewportResize, { passive: true })
  void fetchUserProfile()
    .catch(() => undefined)
    .finally(() => {
      void loadPatients({ initial: true })
    })
  void loadNotifications();
  void loadMedicalRequests();
  void loadArchivedPatients()
  void loadAvailableNurses();
  setupDoctorMessagingWS();
});

onUnmounted(() => {
  _stopMedicalRecordsStatusPolling()
  if (typeof window !== 'undefined') window.removeEventListener('resize', handleViewportResize)
  wsShouldRun = false;
  if (wsReconnectTimer != null) {
    clearTimeout(wsReconnectTimer);
    wsReconnectTimer = null;
  }
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

.greeting-section {
  padding: 32px 24px 24px 24px;
  background: transparent;
}

.greeting-card {
  background: #ffffff;
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
  transition: box-shadow 0.2s ease, transform 0.2s ease;
  overflow: hidden;
  position: relative;
  width: 100%;
}

.greeting-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #286660, #6ca299, #b8d2ce);
  border-radius: 14px 14px 0 0;
}

.greeting-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px;
}

.greeting-text {
  flex: 1;
}

.greeting-title {
  font-size: 18px;
  font-weight: 800;
  color: rgba(15, 23, 42, 0.92);
  margin: 0 0 4px 0;
}

.greeting-subtitle {
  font-size: 12px;
  color: rgba(15, 23, 42, 0.65);
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
  gap: 18px;
  margin-bottom: 18px;
}

.glassmorphism-card {
  background: #ffffff;
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
  overflow: hidden;
  position: relative;
}

.dashboard-card {
  background: #ffffff;
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
  overflow: hidden;
  position: relative;
}

.patient-list-card::before,
.statistics-card::before,
.nurses-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #286660, #6ca299, #b8d2ce);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
}

.card-title {
  font-size: 13px;
  font-weight: 800;
  color: rgba(15, 23, 42, 0.92);
  margin: 0;
}

.card-content {
  padding: 14px 16px;
}

.search-input {
  width: 240px;
}

/* Patient List */
.patients-list {
  max-height: 360px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.patient-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #ffffff;
  border-radius: 12px;
  cursor: pointer;
  transition: background-color 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
  border: 1px solid rgba(15, 23, 42, 0.08);
}

.patient-card:hover {
  background: rgba(13, 148, 136, 0.06);
  border-color: rgba(13, 148, 136, 0.22);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
}
  
  .patient-card.selected {
    border: 2px solid rgba(40, 102, 96, 0.95);
    background: rgba(13, 148, 136, 0.08);
  }

.patient-avatar {
  flex-shrink: 0;
}

.patient-info {
  flex: 1;
  min-width: 0;
}

.patient-name {
  font-size: 13px;
  font-weight: 800;
  color: rgba(15, 23, 42, 0.92);
  margin: 0 0 5px 0;
}

.patient-details {
  font-size: 12px;
  color: rgba(15, 23, 42, 0.65);
  margin: 0 0 5px 0;
}

.patient-condition {
  font-size: 12px;
  color: rgba(15, 23, 42, 0.72);
  margin: 0 0 8px 0;
  font-style: normal;
}

.patient-status {
  margin-top: 5px;
}

.patient-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
  flex-wrap: nowrap;
}

.patient-actions .q-btn {
  width: 28px;
  height: 28px;
  border-radius: 7px;
  border: 1px solid rgba(15, 23, 42, 0.10);
  background: rgba(255, 255, 255, 0.9);
  position: relative;
  z-index: 1;
}

.patient-actions .q-btn:hover {
  border-color: rgba(13, 148, 136, 0.3);
  background: rgba(13, 148, 136, 0.08);
}

.patient-search :deep(.q-field__control) {
  border-radius: 10px;
}

.patients-list::-webkit-scrollbar {
  width: 8px;
}

.patients-list::-webkit-scrollbar-thumb {
  background: rgba(15, 23, 42, 0.14);
  border-radius: 999px;
}

.patients-list::-webkit-scrollbar-track {
  background: transparent;
}

.count-chip {
  height: 24px;
}

.archived-section {
  padding-top: 14px;
}

.archived-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.archived-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: #ffffff;
  transition: background-color 0.15s ease, border-color 0.15s ease;
}

.archived-row:hover {
  background: rgba(13, 148, 136, 0.05);
  border-color: rgba(13, 148, 136, 0.18);
}

.archived-info {
  flex: 1;
  min-width: 0;
}

.archived-name {
  font-weight: 800;
  color: rgba(15, 23, 42, 0.92);
  font-size: 12px;
}

.archived-meta {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.separator {
  margin: 0 6px;
}

/* Statistics */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.stat-item {
  text-align: center;
  padding: 12px;
  background: #f8fafc;
  border-radius: 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
}

.stat-number {
  font-size: 22px;
  font-weight: 900;
  color: rgba(40, 102, 96, 0.95);
  margin-bottom: 2px;
}

.stat-label {
  font-size: 12px;
  color: rgba(15, 23, 42, 0.6);
  font-weight: 500;
}

.archived-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.archived-actions .q-btn {
  border-radius: 10px;
  border: 1px solid rgba(15, 23, 42, 0.14);
}

.patient-list-card :deep(.q-banner) {
  border-radius: 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: #f8fafc;
  color: rgba(15, 23, 42, 0.76);
}

.patient-list-card :deep(.q-banner .q-banner__content) {
  font-size: 12px;
}

.nurses-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.nurse-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: #ffffff;
}

.nurse-avatar {
  flex: 0 0 auto;
}

.nurse-info {
  flex: 1;
  min-width: 0;
}

.nurse-name {
  font-size: 12px;
  font-weight: 800;
  color: rgba(15, 23, 42, 0.92);
}

.nurse-details {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  font-size: 11px;
  color: rgba(15, 23, 42, 0.65);
}

.nurse-contact {
  font-size: 11px;
  color: rgba(15, 23, 42, 0.6);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.status-chip {
  border-radius: 999px;
  font-weight: 700;
}

/* Loading & Empty */
.loading-section, .empty-section { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 40px; color: #666; }
.loading-text, .empty-text { margin-top: 15px; font-size: 14px; }

/* Responsive */
@media (max-width: 1024px) {
  .management-cards-grid { grid-template-columns: 1fr; }
  .search-input { width: 180px; }
}

@media (max-width: 600px) {
  .greeting-section {
    padding: 18px 12px 12px;
  }

  .patient-management-content {
    padding: 12px;
  }

  .patients-list {
    max-height: none;
  }

  .patient-card {
    flex-direction: column;
    align-items: flex-start;
  }

  .patient-actions {
    width: 100%;
    justify-content: flex-end;
    flex-wrap: wrap;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }
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
  background: #ffffff;
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
  transition: box-shadow 0.2s ease, transform 0.2s ease;
  overflow: hidden;
  position: relative;
  width: 100%;
}

.greeting-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #286660, #6ca299, #b8d2ce);
  border-radius: 14px 14px 0 0;
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

.avatar-initials {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 14px;
  line-height: 1;
}
</style>
