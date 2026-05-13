<template>
  <q-layout view="hHh Lpr fFf">
    <!-- Standardized Header Component -->
    <NurseHeader @toggle-drawer="rightDrawerOpen = !rightDrawerOpen" />

    <!-- Standardized Sidebar Component -->
    <NurseSidebar v-model="rightDrawerOpen" :active-route="activeRoute" />

    <q-page-container class="page-container-with-fixed-header role-body-bg">
      <!-- Main Content -->
      <div class="patient-management-content">
        <!-- Header Section -->
        <div class="greeting-section">
          <q-card class="greeting-card">
            <q-card-section class="greeting-content">
              <div class="greeting-text">
                <h4 class="greeting-title">{{ greetingTitle }}</h4>
                <p class="greeting-subtitle">{{ greetingSubtitle }}</p>
              </div>
            </q-card-section>
          </q-card>
        </div>
        
        <!-- Patient Document View (Modal) -->
        <q-dialog v-model="showDocumentView" transition-show="scale" transition-hide="scale" :persistent="false" content-class="document-dialog-container">
          <q-card class="document-view-card">
            <q-card-section class="doc-header">
              <div class="text-h6">{{ userProfile.hospital_name || 'Hospital' }}</div>
              <div class="text-caption">{{ userProfile.hospital_address || 'Address' }}</div>
              <div class="text-caption">Department: {{ department }}</div>
            </q-card-section>
            <q-separator />
            <q-card-section class="doc-content">
              <div class="text-subtitle1 text-bold q-mb-sm">Patient Records</div>
              <div v-if="!selectedPatientDoc">
                <q-banner dense class="q-mt-sm" icon="info">No patient selected</q-banner>
              </div>
              <div v-else>
                <div v-if="documentFormsLoading" class="row items-center q-gutter-sm">
                  <q-spinner size="24px" />
                  <span>Loading records…</span>
                </div>
                <div v-else-if="documentFormsError">
                  <q-banner dense class="q-mt-sm" icon="warning">{{ documentFormsError }}</q-banner>
                </div>
                <div v-else>
                  <TipMedicalRecordForm
                    v-model="documentPhysicalPreviewModel"
                    mode="both"
                    :facility-name="userProfile.hospital_name || 'Hospital'"
                    :revision-date="documentRevisionDate"
                    :staff-options="documentStaffOptions"
                    readonly
                  />
                </div>
              </div>
            </q-card-section>
            <q-card-actions align="right">
              <q-btn flat icon="close" label="Close" @click="showDocumentView = false" />
            </q-card-actions>
          </q-card>
        </q-dialog>
        <!-- Patient Management Cards -->
        <div class="management-cards-grid">
          <div class="left-column">
            <!-- Patient List Card -->
            <q-card class="glassmorphism-card patient-list-card">
              <q-card-section class="card-header">
                <h5 class="card-title">Patient List</h5>
                <q-btn
                  color="primary"
                  icon="refresh"
                  size="sm"
                  @click="loadPatients"
                  :loading="loading"
                />
              </q-card-section>

              <q-card-section class="card-content">
                <q-banner dense class="q-mb-sm" icon="info" inline-actions>
                  Select a patient from the list to work on OPD forms. Archived patients are hidden from selection.
                </q-banner>
                <div class="row items-center q-col-gutter-sm q-mb-sm">
                  <div class="col-12 col-sm-8">
                    <div class="row q-col-gutter-sm items-center">
                      <div class="col-auto">
                        <q-btn
                          outline
                          color="teal"
                          label="Registration & Assessment Form"
                          :disable="!selectedPatient || !isVerifiedUser"
                          @click="openPhysicalForm"
                          aria-label="Open Registration and Assessment Form"
                        />
                      </div>
                    </div>
                    <q-banner v-if="selectedPatient && !isVerifiedUser" dense icon="info" class="q-mt-xs">
                      Verification required to open OPD forms.
                    </q-banner>
                  </div>
                  <div class="col-6 col-sm-2">
                    <q-select v-model="sortKey" :options="sortOptions" outlined dense label="Sort by" emit-value map-options aria-label="Sort patients"/>
                  </div>
                  <div class="col-6 col-sm-2">
                    <q-select v-model="sortOrder" :options="orderOptions" outlined dense label="Order" emit-value map-options aria-label="Sort order"/>
                  </div>
                </div>
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
                          :src="
                            patient.profile_picture.startsWith('http')
                              ? patient.profile_picture
                              : `http://localhost:8000${patient.profile_picture}`
                          "
                          :alt="patient.full_name"
                          @error="patient.profile_picture = ''"
                        />
                        <div v-else class="avatar-initials">{{ getInitials(patient.full_name || '') }}</div>
                      </q-avatar>
                    </div>

                    <div class="patient-info">
                      <h6 class="patient-name">{{ patient.full_name }}</h6>
                      <p class="patient-details">
                        Age: {{ patient.age ?? 'N/A' }} | {{ patient.gender || 'N/A' }} |
                        {{ patient.blood_type || 'N/A' }}
                      </p>
                      <p class="patient-condition">
                        Priority Patient: {{ isPriorityPatient(patient) ? 'Yes' : 'No' }}
                      </p>
                      <div class="patient-status">
                        <q-chip color="primary" text-color="white" size="sm"> Patient </q-chip>
                      </div>
                    </div>

                    <div class="patient-actions">
                      <q-btn
                        aria-label="View patient"
                        flat
                        round
                        icon="visibility"
                        color="primary"
                        size="sm"
                        @click.stop="viewPatientDetails(patient)"
                      >
                        <q-tooltip>View</q-tooltip>
                      </q-btn>
                      <q-btn
                        aria-label="Edit patient"
                        flat
                        round
                        icon="edit"
                        color="secondary"
                        size="sm"
                        @click.stop="editPatient(patient)"
                      >
                        <q-tooltip>Edit</q-tooltip>
                      </q-btn>
                      <q-btn
                        aria-label="Send to doctor"
                        flat
                        round
                        icon="send"
                        color="positive"
                        size="sm"
                        @click.stop="openSendDialog(patient)"
                      >
                        <q-tooltip>Send</q-tooltip>
                      </q-btn>
                      <q-btn
                        aria-label="Pain Assessment"
                        flat
                        round
                        icon="medical_services"
                        color="orange"
                        size="sm"
                        @click.stop="openPainAssessment(patient)"
                      >
                        <q-tooltip>Assess Pain</q-tooltip>
                      </q-btn>
                      <q-btn
                        aria-label="Archive patient"
                        flat
                        round
                        icon="archive"
                        color="warning"
                        size="sm"
                        @click.stop="archivePatient(patient)"
                      >
                        <q-tooltip>Archive</q-tooltip>
                      </q-btn>
                    </div>
                  </div>
                </div>
              </q-card-section>

              <q-separator class="q-mt-sm" />
              <q-card-section class="card-content archived-section">
                <div class="row items-center justify-between q-mb-sm">
                  <div class="row items-center q-gutter-sm">
                    <div class="text-subtitle2 text-weight-medium">Archived patients</div>
                    <div class="text-caption text-grey-7">({{ archivedPatients.length }} records)</div>
                  </div>
                  <q-btn
                    flat
                    dense
                    size="sm"
                    icon="refresh"
                    :loading="archivedPatientsLoading"
                    @click="loadArchivedPatients"
                    aria-label="Refresh archived patients"
                  />
                </div>

                <div v-if="archivedPatientsLoading" class="loading-section">
                  <q-spinner color="primary" size="2em" />
                  <p class="loading-text">Loading archived patients...</p>
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
                </div>

                <div v-else-if="archivedPatientsVisible.length === 0" class="empty-archived">
                  <div class="text-caption text-grey-7">No archived patients</div>
                </div>

                <div v-else class="archived-list">
                  <div v-for="rec in archivedPatientsVisible" :key="rec.id" class="archived-row">
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

                  <div v-if="archivedPatients.length > archivedPatientsVisible.length" class="text-caption text-grey-7 q-mt-sm">
                    Showing {{ archivedPatientsVisible.length }} of {{ archivedPatients.length }}
                  </div>
                </div>
              </q-card-section>
            </q-card>
          </div>
          <div class="right-column">
            <!-- Patient Statistics Card -->
            <q-card class="glassmorphism-card statistics-card section-spacing">
              <q-card-section class="card-header">
                <h5 class="card-title">Patient Statistics</h5>
              </q-card-section>

              <q-card-section class="card-content">
                <div class="stats-grid">
                  <div class="stat-item">
                    <div class="stat-number">{{ totalPatientsCount }}</div>
                    <div class="stat-label">Total Patients</div>
                  </div>
                  <div class="stat-item">
                    <div class="stat-number">{{ activePatientsCount }}</div>
                    <div class="stat-label">Active</div>
                  </div>
                </div>
              </q-card-section>
            </q-card>

            <!-- List of Available Doctors Card -->
            <q-card class="glassmorphism-card doctors-card section-spacing">
              <q-card-section class="card-header">
                <div class="row items-center justify-between full-width">
                  <h5 class="card-title q-mb-none">Available Doctors</h5>
                  <q-btn
                    flat
                    dense
                    size="sm"
                    icon="refresh"
                    :loading="doctorsLoading"
                    @click="() => { void loadAvailableDoctors() }"
                    aria-label="Refresh available doctors"
                  />
                </div>
              </q-card-section>
              <q-card-section class="card-content">
                <q-banner v-if="doctorsLoadError" dense class="q-mb-sm" icon="warning" inline-actions>
                  <span class="text-negative">{{ doctorsLoadError }}</span>
                  <q-btn flat color="primary" icon="refresh" label="Retry" @click="() => { void loadAvailableDoctors() }"/>
                </q-banner>
                <div v-else-if="doctorsCheckedAt" class="text-caption text-grey-7 q-mb-sm">
                  Last checked: {{ formatDateDisplay(doctorsCheckedAt || '') }}
                </div>
                <div v-if="doctorsLoading" class="loading-section">
                  <q-spinner color="primary" size="2em" />
                  <p class="loading-text">Loading doctors...</p>
                </div>
                <div v-else-if="filteredAvailableDoctors.length === 0" class="empty-section">
                  <q-icon name="medical_services" size="48px" color="grey-5" />
                  <p class="empty-text">No available doctors</p>
                </div>
                <div v-else class="doctors-list">
                  <div v-for="(doc, idx) in paginatedDoctors" :key="String(doc.id ?? doc.email ?? doc.full_name ?? idx)" class="doctor-row">
                    <div class="doctor-avatar">
                      <q-avatar size="40px" color="teal-8" text-color="white">
                        {{ getInitials(doc.full_name || '') }}
                      </q-avatar>
                    </div>
                    <div class="doctor-info">
                      <div class="doctor-name">{{ doc.full_name }}</div>
                      <div class="doctor-details">
                        Specialization: {{ doc.specialization || '—' }}
                        <span class="separator">•</span>
                        <q-chip
                          :color="getAvailabilityColor(doc.availability ?? doc.status ?? 'Available')"
                          text-color="white"
                          size="sm"
                          :label="(doc.availability ?? doc.status ?? 'Available')"
                          dense
                          class="status-chip"
                        />
                      </div>
                      <div class="doctor-contact">Contact: {{ doc.email || '—' }}</div>
                    </div>
                  </div>
                  <div class="row items-center justify-between q-mt-sm" aria-label="Doctors pagination controls">
                    <div class="text-caption text-grey-7">
                      Showing {{ doctorsStartIndex }}–{{ doctorsEndIndex }} of {{ filteredAvailableDoctors.length }}
                    </div>
                    <q-pagination
                      v-model="doctorsPage"
                      :max="doctorTotalPages"
                      max-pages="7"
                      boundary-numbers
                      size="sm"
                      color="primary"
                      aria-label="Available doctors pagination"
                    />
                  </div>
                </div>
              </q-card-section>
            </q-card>

          </div>
        </div>

        <div v-if="false" class="archive-view">
          <q-card class="glassmorphism-card archive-card section-spacing">
            <q-card-section class="card-header">
              <div class="row items-center justify-between full-width">
                <h5 class="card-title q-mb-none">Patient Archive</h5>
                <q-btn color="primary" icon="add" label="New Archive" @click="openCreateDialog" />
              </div>
            </q-card-section>

            <q-card-section class="card-content">
              <div class="row q-col-gutter-md q-mb-lg">
                <div class="col-12 col-md-6">
                  <q-input v-model="archiveFilters.query" label="Patient Name or ID" outlined dense />
                </div>
                <div class="col-12 col-sm-6 col-md-3">
                  <q-input v-model="archiveFilters.assessment_type" label="Assessment Type" outlined dense />
                </div>
                <div class="col-12 col-sm-6 col-md-3">
                  <q-input v-model="archiveFilters.medical_condition" label="Medical Condition" outlined dense />
                </div>
              </div>

              <div class="row q-col-gutter-md q-mb-md">
                <div class="col-12 col-sm-6 col-md-3">
                  <q-input v-model="archiveFilters.start_date" label="Start Date" type="date" outlined dense />
                </div>
                <div class="col-12 col-sm-6 col-md-3">
                  <q-input v-model="archiveFilters.end_date" label="End Date" type="date" outlined dense />
                </div>
                <div class="col-12 col-sm-6 col-md-3">
                  <q-btn
                    color="primary"
                    icon="search"
                    label="Search"
                    class="full-width"
                    :loading="archivesLoading"
                    @click="searchArchives"
                  />
                </div>
              </div>

              <q-inner-loading :showing="archivesLoading">
                <q-spinner color="primary" />
              </q-inner-loading>

              <div v-if="!archivesLoading && archivedRecords.length === 0" class="empty-section">
                <q-icon name="inventory_2" size="48px" color="grey-5" />
                <p class="empty-text">No archived records</p>
              </div>

              <q-list v-else bordered separator>
                <q-item v-for="rec in archivedRecords" :key="rec.id">
                  <q-item-section>
                    <q-item-label>
                      {{ rec.patient_name }} — {{ rec.assessment_type }} · {{ formatDateDisplay(rec.last_assessed_at) }}
                    </q-item-label>
                    <q-item-label caption>
                      Condition: {{ rec.medical_condition || '—' }} • Hospital: {{ rec.hospital_name || '—' }}
                    </q-item-label>
                  </q-item-section>
                  <q-item-section side top>
                    <q-chip color="grey-8" text-color="white" size="sm">Archived</q-chip>
                  </q-item-section>
                  <q-item-section side>
                    <div class="row q-gutter-xs">
                      <q-btn dense flat icon="visibility" color="primary" @click="viewArchive(rec)" />
                      <q-btn dense flat icon="download" color="secondary" @click="exportArchive(rec)" />
                    </div>
                  </q-item-section>
                </q-item>
              </q-list>

              <div class="row q-gutter-sm q-mt-md" v-if="archivedRecords.length">
                <q-btn outline color="primary" icon="file_download" label="Export Results" @click="exportFilteredArchives" />
              </div>
            </q-card-section>
          </q-card>

          <q-dialog v-model="showArchiveDetail">
            <q-card style="max-width: 1000px; width: 90vw">
              <q-card-section>
                <div class="text-h6">Archived Assessment</div>
              </q-card-section>
              <q-separator />
              <q-card-section>
                <div class="q-mb-sm"><b>Patient:</b> {{ selectedArchive?.patient_name }}</div>
                <div class="q-mb-sm"><b>Assessment:</b> {{ selectedArchive?.assessment_type }}</div>
                <div class="q-mb-sm"><b>Last Assessed:</b> {{ formatDateDisplay(selectedArchive?.last_assessed_at || '') }}</div>
                <div class="q-mb-sm"><b>Condition:</b> {{ selectedArchive?.medical_condition || '—' }}</div>
                <div class="q-mb-sm"><b>Hospital:</b> {{ selectedArchive?.hospital_name || '—' }}</div>
                <div class="q-mb-sm"><b>Medical History:</b> {{ selectedArchive?.medical_history_summary || '—' }}</div>
                <div class="q-mt-md">
                  <div class="text-subtitle2 q-mb-xs">Assessment Data</div>
                  <div v-if="selectedArchive">
                    <div class="q-mb-md">
                      <div class="text-body1 text-bold q-mb-sm">Participants</div>
                      <q-markup-table flat separator="cell">
                        <tbody>
                          <tr v-for="row in participantRows" :key="row.label">
                            <td class="text-weight-medium">{{ row.label }}</td>
                            <td>{{ row.value || '—' }}</td>
                          </tr>
                        </tbody>
                      </q-markup-table>
                    </div>
                    <div class="q-mb-md">
                      <div class="text-body1 text-bold q-mb-sm">Vitals</div>
                      <q-markup-table flat separator="cell">
                        <tbody>
                          <tr v-for="row in vitalsRows" :key="row.label">
                            <td class="text-weight-medium">{{ row.label }}</td>
                            <td>{{ row.value || '—' }}</td>
                          </tr>
                        </tbody>
                      </q-markup-table>
                    </div>
                    <div class="q-mb-md">
                      <div class="text-body1 text-bold q-mb-sm">Scores & Status</div>
                      <q-markup-table flat separator="cell">
                        <tbody>
                          <tr v-for="row in metricRows" :key="row.label">
                            <td class="text-weight-medium">{{ row.label }}</td>
                            <td>{{ row.value || '—' }}</td>
                          </tr>
                        </tbody>
                      </q-markup-table>
                    </div>
                    <div class="q-mb-md">
                      <div class="text-body1 text-bold q-mb-sm">Notes</div>
                      <q-markup-table flat separator="cell">
                        <tbody>
                          <tr v-for="row in noteRows" :key="row.label">
                            <td class="text-weight-medium">{{ row.label }}</td>
                            <td>{{ row.value || '—' }}</td>
                          </tr>
                        </tbody>
                      </q-markup-table>
                    </div>
                    <div class="q-mb-md" v-if="listSections.length">
                      <div class="text-body1 text-bold q-mb-sm">Lists</div>
                      <div class="q-gutter-sm">
                        <div v-for="lst in listSections" :key="lst.title">
                          <div class="text-subtitle2 q-mb-xs">{{ lst.title }}</div>
                          <q-markup-table flat separator="cell">
                            <tbody>
                              <tr v-if="!lst.items.length">
                                <td>—</td>
                              </tr>
                              <tr v-for="(item, idx) in lst.items" :key="idx">
                                <td>{{ item }}</td>
                              </tr>
                            </tbody>
                          </q-markup-table>
                        </div>
                      </div>
                    </div>
                    <div class="q-mb-md" v-if="otherRows.length">
                      <div class="text-body1 text-bold q-mb-sm">Other Fields</div>
                      <q-markup-table flat separator="cell">
                        <tbody>
                          <tr v-for="row in otherRows" :key="row.label">
                            <td class="text-weight-medium">{{ row.label }}</td>
                            <td>{{ row.value || '—' }}</td>
                          </tr>
                        </tbody>
                      </q-markup-table>
                    </div>
                  </div>
                </div>
              </q-card-section>
              <q-card-actions align="right">
                <q-btn flat icon="edit" label="Edit" @click="openEditDialog" :disable="!selectedArchive" />
                <q-btn outline color="warning" icon="unarchive" label="Unarchive" @click="unarchiveSelected" :disable="!selectedArchive" />
                <q-btn flat icon="close" label="Close" v-close-popup />
              </q-card-actions>
            </q-card>
          </q-dialog>

          <q-dialog v-model="showCreateDialog">
            <q-card style="max-width: 800px; width: 92vw">
              <q-card-section>
                <div class="text-h6">Create Archive</div>
              </q-card-section>
              <q-separator />
              <q-card-section class="q-gutter-md">
                <q-input v-model="createForm.patient_id" label="Patient ID" outlined dense />
                <q-input v-model="createForm.assessment_type" label="Assessment Type" outlined dense />
                <q-input v-model="createForm.medical_condition" label="Medical Condition" outlined dense />
                <q-input v-model="createForm.hospital_name" label="Hospital Name" outlined dense />
                <q-input v-model="createForm.assessment_data" label="Assessment Data (JSON)" type="textarea" outlined autogrow />
              </q-card-section>
              <q-card-actions align="right">
                <q-btn flat label="Cancel" v-close-popup />
                <q-btn flat label="Save" color="primary" :loading="createLoading" @click="createArchive" />
              </q-card-actions>
            </q-card>
          </q-dialog>

          <q-dialog v-model="showEditDialog">
            <q-card style="max-width: 800px; width: 92vw">
              <q-card-section>
                <div class="text-h6">Edit Archive</div>
              </q-card-section>
              <q-separator />
              <q-card-section class="q-gutter-md">
                <q-input v-model="editForm.assessment_type" label="Assessment Type" outlined dense />
                <q-input v-model="editForm.medical_condition" label="Medical Condition" outlined dense />
                <q-input v-model="editForm.hospital_name" label="Hospital Name" outlined dense />
                <q-input v-model="editForm.assessment_data" label="Assessment Data (JSON)" type="textarea" outlined autogrow />
              </q-card-section>
              <q-card-actions align="right">
                <q-btn flat label="Cancel" v-close-popup />
                <q-btn flat label="Save" color="primary" :loading="editLoading" @click="updateArchive" />
              </q-card-actions>
            </q-card>
          </q-dialog>
        </div>

      <!-- Registration / Demographics Dialog -->
      <q-dialog v-model="showRegistrationDialog" persistent maximized transition-show="slide-up" transition-hide="slide-down">
        <q-card class="registration-dialog-card">
          <q-toolbar class="bg-primary text-white">
            <q-btn flat round dense icon="close" v-close-popup aria-label="Close Registration" />
            <q-toolbar-title>Patient Registration</q-toolbar-title>
            <q-btn flat label="Save Draft" @click="saveRegistrationDraft" aria-label="Save Draft" />
            <q-btn flat label="Save & Submit" @click="saveRegistration" :loading="savingRegistration" aria-label="Save and Submit" />
          </q-toolbar>

          <q-card-section class="q-pa-md">
            <q-stepper v-model="registrationStep" vertical color="primary" animated header-nav>
              <!-- Step 1: Hospital & Basic Contact Details -->
              <q-step :name="1" title="Hospital & Basic Contact Details" icon="local_hospital" :done="registrationStep > 1">
                <div class="row q-col-gutter-md">
                  <div class="col-12 col-md-6">
                    <q-input v-model="registrationForm.hospitalName" label="Hospital Name *" outlined dense :rules="[v=>!!v||'Required']" aria-label="Hospital Name"/>
                  </div>
                  <div class="col-12 col-md-6">
                    <q-input v-model="registrationForm.hospitalAddress" label="Hospital Address *" outlined dense :rules="[v=>!!v||'Required']" aria-label="Hospital Address"/>
                  </div>
                </div>
                <q-stepper-navigation>
                  <q-btn @click="nextStep" color="primary" label="Continue" />
                </q-stepper-navigation>
              </q-step>

              <!-- Step 2: Patient Information -->
              <q-step :name="2" title="Patient Information" icon="person" :done="registrationStep > 2">
                <div class="text-subtitle2 q-mb-sm">Identifiers</div>
                <div class="row q-col-gutter-md q-mb-md">
                   <div class="col-12 col-md-4">
                      <q-input v-model="registrationForm.mrn" label="Patient ID / MRN *" outlined dense :rules="[v=>!!v||'Required']" aria-label="MRN"/>
                   </div>
                   <div class="col-12 col-md-4">
                      <q-input v-model="registrationForm.firstName" label="First Name *" outlined dense :rules="[v => !!v && v.length >= 2 || 'Min 2 chars']" aria-label="First Name"/>
                   </div>
                   <div class="col-12 col-md-4">
                      <q-input v-model="registrationForm.lastName" label="Last Name *" outlined dense :rules="[v => !!v && v.length >= 2 || 'Min 2 chars']" aria-label="Last Name"/>
                   </div>
                   <div class="col-12 col-md-4">
                      <q-input v-model="registrationForm.middleName" label="Middle Name" outlined dense aria-label="Middle Name"/>
                   </div>
                   <div class="col-12 col-md-4">
                      <q-input v-model="registrationForm.dob" type="date" label="Date of Birth *" outlined dense :rules="[v=>!!v||'Required']" aria-label="Date of Birth"/>
                   </div>
                </div>

                <div class="text-subtitle2 q-mb-sm">Demographics</div>
                <div class="row q-col-gutter-md q-mb-md">
                   <div class="col-12 col-md-4">
                      <q-input v-model.number="registrationForm.age" type="number" label="Age *" outlined dense :rules="[v => (v !== '' && v >= 0 && v <= 120) || '0-120']" aria-label="Age"/>
                   </div>
                   <div class="col-12 col-md-4">
                      <q-select v-model="registrationForm.sex" :options="['Male','Female','Other']" label="Gender *" outlined dense :rules="[v=>!!v||'Required']" aria-label="Gender"/>
                   </div>
                   <div class="col-12 col-md-4">
                      <q-select v-model="registrationForm.maritalStatus" :options="['Single','Married','Divorced','Widowed']" label="Marital Status *" outlined dense :rules="[v=>!!v||'Required']" aria-label="Marital Status"/>
                   </div>
                </div>

                <div class="text-subtitle2 q-mb-sm">Personal Contact</div>
                <div class="row q-col-gutter-md">
                   <div class="col-12 col-md-6">
                      <q-input v-model="registrationForm.cellPhone" label="Phone Number *" mask="####-###-####" hint="Format: 0912-345-6789" outlined dense :rules="[v=>!!v||'Required']" aria-label="Phone Number"/>
                   </div>
                   <div class="col-12 col-md-6">
                      <q-input v-model="registrationForm.homeAddress" label="Home Address *" outlined dense :rules="[v=>!!v||'Required']" aria-label="Home Address"/>
                   </div>
                </div>

                <q-stepper-navigation>
                  <q-btn @click="nextStep" color="primary" label="Continue" />
                  <q-btn flat @click="prevStep" color="primary" label="Back" class="q-ml-sm" />
                </q-stepper-navigation>
              </q-step>

              <!-- Step 3: Emergency Contact -->
              <q-step :name="3" title="Emergency Contact" icon="contact_phone" :done="registrationStep > 3">
                <div class="row q-col-gutter-md">
                  <div class="col-12 col-md-4">
                    <q-input v-model="registrationForm.emergencyName" label="Name *" outlined dense :rules="[v=>!!v||'Required']" aria-label="Emergency Contact Name"/>
                  </div>
                  <div class="col-12 col-md-4">
                    <q-select v-model="registrationForm.emergencyRelationship" :options="relationshipOptions" label="Relationship *" outlined dense :rules="[v=>!!v||'Required']" aria-label="Emergency Relationship"/>
                  </div>
                  <div class="col-12 col-md-4">
                     <q-input v-model="registrationForm.emergencyPhone" label="Contact Number *" outlined dense :rules="[v=>!!v||'Required']" aria-label="Emergency Phone"/>
                  </div>
                </div>
                <q-stepper-navigation>
                  <q-btn @click="nextStep" color="primary" label="Continue" />
                  <q-btn flat @click="prevStep" color="primary" label="Back" class="q-ml-sm" />
                </q-stepper-navigation>
              </q-step>

              <!-- Step 4: Medical History -->
              <q-step :name="4" title="Medical History" icon="medical_services" :done="registrationStep > 4">
                
                <div class="row q-col-gutter-md">
                   <div class="col-12">
                     <q-select v-model="registrationForm.knownAllergies" :options="allergyOptions" multiple use-input use-chips new-value-mode="add-unique" label="Known Allergies" outlined dense aria-label="Allergies"/>
                   </div>
                   <div class="col-12">
                     <q-input v-model="registrationForm.currentMedications" label="Current Medications" type="textarea" outlined dense autogrow aria-label="Current Medications"/>
                   </div>
                   <div class="col-12">
                    <q-input v-model="registrationForm.medicalHistory" type="textarea" label="Past Medical History" outlined dense aria-label="Past Medical History"/>
                   </div>
                </div>

                <q-stepper-navigation>
                  <q-btn @click="nextStep" color="primary" label="Continue" />
                  <q-btn flat @click="prevStep" color="primary" label="Back" class="q-ml-sm" />
                </q-stepper-navigation>
              </q-step>

              <!-- Step 5: Authorization -->
              <q-step :name="5" title="Authorization" icon="verified_user" :done="registrationStep > 5">
                <div class="text-h6 q-mb-md">Consent</div>
                <div class="q-mb-md">
                  <q-checkbox v-model="registrationForm.consentAgreed" label="I authorize the release of my medical information for the purpose of care and treatment. I agree to the hospital policies." />
                </div>
                
                <div class="row q-col-gutter-md">
                   <div class="col-12 col-md-8">
                      <q-input v-model="registrationForm.patientSignature" label="Patient/Guardian Signature *" outlined dense :rules="[v=>!!v||'Required']" aria-label="Signature"/>
                   </div>
                   <div class="col-12 col-md-4">
                      <q-input v-model="registrationForm.signatureDate" type="date" label="Date *" outlined dense readonly :rules="[v=>!!v||'Required']" aria-label="Signature Date"/>
                   </div>
                </div>

                <q-stepper-navigation>
                  <q-btn color="positive" label="Finish & Submit" @click="saveRegistration" :loading="savingRegistration" />
                  <q-btn flat @click="prevStep" color="primary" label="Back" class="q-ml-sm" />
                </q-stepper-navigation>
              </q-step>
            </q-stepper>
          </q-card-section>
        </q-card>
      </q-dialog>

      <q-dialog v-model="showAssessmentDialog" persistent maximized transition-show="slide-up" transition-hide="slide-down">
        <q-card class="registration-dialog-card">
          <q-toolbar class="bg-teal text-white">
            <q-btn flat round dense icon="close" v-close-popup aria-label="Close Assessment" />
            <q-toolbar-title>Patient Assessment</q-toolbar-title>
            <q-btn flat label="Save Draft" @click="saveAssessmentDraft" aria-label="Save Assessment Draft" />
            <q-btn flat label="Save & Submit" @click="saveAssessment" :loading="savingAssessment" aria-label="Save Assessment and Submit" />
          </q-toolbar>

          <q-card-section class="q-pa-md">
            <q-stepper v-model="assessmentStep" vertical color="teal" animated header-nav>
              <q-step :name="1" title="Vital Signs" icon="monitor_heart" :done="assessmentStep > 1">
                <div class="row q-col-gutter-md">
                  <div class="col-12 col-md-4">
                    <q-input v-model="assessmentForm.vitals.bp" label="Blood Pressure" outlined dense aria-label="Blood Pressure" />
                  </div>
                  <div class="col-12 col-md-4">
                    <q-input v-model.number="assessmentForm.vitals.hr" type="number" label="Heart Rate (bpm)" outlined dense aria-label="Heart Rate" />
                  </div>
                  <div class="col-12 col-md-4">
                    <q-input v-model.number="assessmentForm.vitals.rr" type="number" label="Respiratory Rate" outlined dense aria-label="Respiratory Rate" />
                  </div>
                  <div class="col-12 col-md-4">
                    <q-input v-model.number="assessmentForm.vitals.temp_c" type="number" label="Temperature (°C)" outlined dense aria-label="Temperature" />
                  </div>
                  <div class="col-12 col-md-4">
                    <q-input v-model.number="assessmentForm.vitals.spo2" type="number" label="SpO₂ (%)" outlined dense aria-label="Oxygen Saturation" />
                  </div>
                  <div class="col-12 col-md-4">
                    <q-input v-model.number="assessmentForm.weight_kg" type="number" label="Weight (kg)" outlined dense aria-label="Weight" />
                  </div>
                  <div class="col-12 col-md-4">
                    <q-input v-model.number="assessmentForm.height_cm" type="number" label="Height (cm)" outlined dense aria-label="Height" />
                  </div>
                </div>
                <q-stepper-navigation>
                  <q-btn @click="nextAssessmentStep" color="teal" label="Continue" />
                </q-stepper-navigation>
              </q-step>

              <q-step :name="2" title="Complaints & Observations" icon="assignment" :done="assessmentStep > 2">
                <div class="row q-col-gutter-md">
                  <div class="col-12">
                    <q-input v-model="assessmentForm.chief_complaint" label="Chief Complaint *" outlined dense :rules="[v=>!!v||'Required']" aria-label="Chief Complaint" />
                  </div>
                  <div class="col-12 col-md-6">
                    <div class="text-caption q-mb-xs">Pain Scale (0-10)</div>
                    <q-slider v-model="assessmentForm.pain_score" :min="0" :max="10" label label-always color="teal" markers snap />
                  </div>
                  <div class="col-12 col-md-6">
                    <q-select v-model="assessmentForm.affected_body_parts" label="Affected Body Parts" multiple use-chips use-input new-value-mode="add-unique" outlined dense :options="['Head', 'Chest', 'Abdomen', 'Back', 'Arms', 'Legs', 'Skin', 'Joints']" aria-label="Affected Body Parts"/>
                  </div>
                  <div class="col-12">
                    <q-input v-model="assessmentForm.assessment_notes" label="Initial Nursing Observations" type="textarea" outlined dense autogrow aria-label="Assessment Notes"/>
                  </div>
                  <div class="col-12 col-md-6">
                    <q-input v-model="assessmentForm.mental_status" label="Mental Status (optional)" outlined dense aria-label="Mental Status"/>
                  </div>
                  <div class="col-12 col-md-6">
                    <q-input v-model.number="assessmentForm.fall_risk_score" type="number" label="Fall Risk Score (optional)" outlined dense aria-label="Fall Risk Score"/>
                  </div>
                </div>
                <q-stepper-navigation>
                  <q-btn color="positive" label="Finish & Submit" @click="saveAssessment" :loading="savingAssessment" />
                  <q-btn flat @click="prevAssessmentStep" color="teal" label="Back" class="q-ml-sm" />
                </q-stepper-navigation>
              </q-step>
            </q-stepper>
          </q-card-section>
        </q-card>
      </q-dialog>

      <q-dialog v-model="showPhysicalFormDialog" persistent maximized transition-show="slide-up" transition-hide="slide-down">
        <q-card class="registration-dialog-card">
          <q-toolbar class="bg-grey-9 text-white">
            <q-btn flat round dense icon="close" v-close-popup aria-label="Close Physical Form" />
            <q-toolbar-title>Registration & Assessment Form</q-toolbar-title>
            <q-space />
            <q-btn flat label="Save & Submit" :loading="savingPhysicalForm" @click="savePhysicalForm" aria-label="Save Physical Form" />
          </q-toolbar>

          <q-card-section class="q-pa-md">
            <TipMedicalRecordForm
              ref="physicalFormRef"
              v-model="physicalFormModel"
              mode="both"
              :facility-name="userProfile.hospital_name || selectedPatient?.hospital || 'Medical Facility'"
              :revision-date="physicalFormRevisionDate"
              :staff-options="physicalStaffOptions"
            />
          </q-card-section>
        </q-card>
      </q-dialog>
      </div>
    </q-page-container>

    <!-- Send Patient Records Dialog -->
    <q-dialog v-model="sendDialogOpen">
      <q-card style="min-width: 720px; max-width: 92vw;">
        <q-card-section class="row items-center">
          <div class="text-h6">Send Patient Records</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup aria-label="Close" />
        </q-card-section>
        <q-separator />
        <q-card-section>
          <q-select
            v-model="sendSelectedDoctorId"
            :options="sendDoctorOptions"
            label="Select Doctor"
            outlined
            dense
            emit-value
            map-options
          />
          <q-select
            v-model="sendPriority"
            :options="sendPriorityOptions"
            label="Urgency"
            outlined
            dense
            emit-value
            map-options
            class="q-mt-md"
          />
          <div class="text-caption text-grey-7 q-mt-sm">Notify via</div>
          <q-option-group
            v-model="sendChannels"
            :options="sendChannelOptions"
            type="checkbox"
            color="primary"
            inline
            class="q-mt-md"
          />
          <q-input v-model="sendMessage" label="Message (optional)" outlined dense class="q-mt-md" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="CANCEL" color="dark" v-close-popup />
          <q-btn label="SEND" color="primary" @click="sendPatientRecords" :loading="sendingRecords" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Archive Success Dialog -->
    <q-dialog v-model="archiveSuccessDialogOpen">
      <q-card>
        <q-card-section>
          <div class="text-h6">Archive Successful</div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          Patient record has been successfully archived. Would you like to download the assessment as a PDF?
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Close" color="primary" v-close-popup />
          <q-btn flat label="Download PDF" color="primary" @click="downloadArchivePdf" />
        </q-card-actions>
      </q-card>
    </q-dialog>
    <!-- Pain Assessment Dialog -->
    <q-dialog v-model="painDialogOpen" persistent>
      <q-card style="width: 500px; max-width: 90vw">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">Pain Assessment</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section class="pain-assessment-body">
          <div class="text-subtitle1 text-weight-medium q-mb-md">Patient: {{ selectedPatient?.full_name }}</div>
          
          <div class="pain-display-container text-center q-mb-xl">
            <transition name="scale" mode="out-in">
              <div 
                :key="currentPainScore" 
                class="pain-emoji-large" 
                :style="{ color: `var(--q-${getPainColor(currentPainScore)})` }"
                role="img"
                :aria-label="`Pain level emoticon: ${getPainLabel(currentPainScore)}`"
              >
                {{ getPainEmoji(currentPainScore) }}
              </div>
            </transition>
            <div class="pain-label-container">
              <div class="text-h4 text-weight-bold" :class="`text-${getPainColor(currentPainScore)}`" aria-live="polite">
                {{ getPainLabel(currentPainScore) }}
              </div>
              <div class="text-h6 text-grey-7">Score: {{ currentPainScore }}/10</div>
            </div>
          </div>

          <div class="pain-slider-wrapper q-px-md">
            <q-slider
              v-model="currentPainScore"
              :min="0"
              :max="10"
              :step="1"
              label
              label-always
              :color="getPainColor(currentPainScore)"
              markers
              snap
              class="modern-pain-slider"
              aria-label="Pain score slider from 0 (no pain) to 10 (unbearable pain)"
            />
            
            <div class="pain-scale-indicators row justify-between q-mt-sm" role="list" aria-label="Pain scale reference dots">
              <div v-for="n in [0, 2, 4, 6, 8, 10]" :key="n" class="column items-center" role="listitem">
                <span class="text-caption text-grey-6" aria-hidden="true">{{ n }}</span>
                <span 
                  class="pain-dot" 
                  :class="{ active: currentPainScore === n }" 
                  :style="{ backgroundColor: currentPainScore >= n ? `var(--q-${getPainColor(n)})` : '#eee' }"
                  :aria-label="`Pain score indicator for level ${n}`"
                ></span>
              </div>
            </div>
          </div>

          <div class="row justify-between text-caption text-weight-medium text-grey-7 q-mt-lg q-mb-md">
            <span class="status-mild">Comfortable</span>
            <span class="status-moderate">Manageable</span>
            <span class="status-severe">Urgent Care</span>
          </div>

          <q-input
            v-model="painNotes"
            type="textarea"
            label="Clinical Observations / Notes"
            outlined
            dense
            autogrow
            rows="3"
            class="pain-notes-input q-mb-md"
            placeholder="Describe the nature of pain (throbbing, sharp, etc.)"
          />

          <q-separator class="q-my-md" />
          
          <div class="text-subtitle2 text-grey-8 q-mb-sm flex items-center">
            <q-icon name="history" size="xs" class="q-mr-xs" />
            Pain History
          </div>
          <q-scroll-area class="pain-history-scroll" style="height: 180px;">
            <q-list dense separator class="pain-history-list">
              <q-item v-for="assessment in painHistory" :key="assessment.id" class="pain-history-item">
                <q-item-section avatar>
                  <div class="pain-emoji-small">{{ getPainEmoji(assessment.pain_score) }}</div>
                </q-item-section>
                <q-item-section>
                  <q-item-label class="text-weight-bold">Score: {{ assessment.pain_score }}</q-item-label>
                  <q-item-label caption class="text-grey-7">{{ new Date(assessment.created_at).toLocaleString() }}</q-item-label>
                  <q-item-label caption v-if="assessment.notes" class="pain-history-notes">{{ assessment.notes }}</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-chip outline size="xs" color="grey-7" icon="person">
                    {{ assessment.performed_by_name }}
                  </q-chip>
                </q-item-section>
              </q-item>
              <div v-if="painHistory.length === 0" class="empty-history text-center text-grey-6 q-pa-md">
                <q-icon name="history_toggle_off" size="md" class="q-mb-xs" />
                <div>No previous assessments</div>
              </div>
            </q-list>
          </q-scroll-area>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn color="primary" label="Save Assessment" :loading="painSubmitting" @click="submitPainAssessment" />
        </q-card-actions>
      </q-card>
    </q-dialog>

  </q-layout>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue';
import { useQuasar } from 'quasar';
import { api } from 'boot/axios';
import { useRoute, useRouter } from 'vue-router';
import NurseHeader from '../components/NurseHeader.vue';
import NurseSidebar from '../components/NurseSidebar.vue';
import { usePatientStore } from 'src/stores/patientStore';
import TipMedicalRecordForm from 'src/components/TipMedicalRecordForm.vue'
import { normalizeAssessmentData, formatSectionRows } from 'src/utils/archiveFormat'

// Types
interface Patient {
  id: number;
  user_id: number;
  patient_id?: string;
  full_name: string;
  email: string;
  age: number | null;
  gender: string;
  date_of_birth?: string | null;
  blood_type: string;
  medical_condition: string;
  hospital: string;
  insurance_provider: string;
  billing_amount: number | null;
  room_number: string;
  admission_type: string;
  date_of_admission: string;
  discharge_date: string;
  medication: string;
  test_results: string;
  assigned_doctor: string | null;
  profile_picture?: string | null;
  // Provided by backend to identify analytics dummy records
  is_dummy?: boolean;
  assessment_status?: 'pending' | 'assessed';
}

interface PainAssessment {
  id: number;
  pain_score: number;
  pain_emoji: string;
  pain_label?: string;
  notes: string;
  performed_by_name: string;
  created_at: string;
}

// Reactive data
const $q = useQuasar();
const patientStore = usePatientStore();
const route = useRoute()
const router = useRouter()
const rightDrawerOpen = ref(false);
type ViewMode = 'patients' | 'archive'
const currentView = ref<ViewMode>('patients')
const greetingTitle = computed(() => (currentView.value === 'archive' ? 'Patient Archive' : 'Patient Management'))
const greetingSubtitle = computed(() =>
  currentView.value === 'archive'
    ? 'Browse and export archived patient assessments'
    : 'Manage your patients and their medical records',
)
const activeRoute = computed(() =>
  currentView.value === 'archive' ? 'patient-archive' : 'nurse-patient-assessment',
)

watch(
  () => route.query.view,
  (v) => {
    currentView.value = v === 'archive' ? 'archive' : 'patients'
  },
  { immediate: true },
)
watch(currentView, (v) => {
  const desired = v === 'archive' ? 'archive' : undefined
  const current = route.query.view
  if (desired === current) return
  const nextQuery = { ...route.query } as Record<string, string | string[] | null | undefined>
  if (desired) nextQuery.view = desired
  else delete nextQuery.view
  void router.replace({ query: nextQuery })
})

const loading = ref(false);
const searchText = ref('');
const sortKey = ref<'full_name' | 'age' | 'gender'>('full_name');
const sortOptions = [
  { label: 'Name', value: 'full_name' },
  { label: 'Age', value: 'age' },
  { label: 'Gender', value: 'gender' },
];
const sortOrder = ref<'asc' | 'desc'>('asc');
const orderOptions = [
  { label: 'Ascending', value: 'asc' },
  { label: 'Descending', value: 'desc' },
];
const patients = ref<Patient[]>([]);
const selectedPatient = ref<Patient | null>(null);

type ArchivedPatientItem = {
  id: number;
  patient_name: string;
  last_assessed_at: string | null;
  archival_reason?: string;
}
const archivedPatientsLoading = ref(false)
const archivedPatients = ref<ArchivedPatientItem[]>([])
const restoreLoadingId = ref<number | null>(null)
const downloadLoadingId = ref<number | null>(null)
const archivedPatientsVisible = computed(() => archivedPatients.value.slice(0, 4))

const formatArchivedAt = (dateStr: string | null): string => {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

const buildPatientPdfFilename = (patientName: string, id: number): string => {
  const cleaned = String(patientName || '')
    .trim()
    .replace(/[\\/:*?"<>|]+/g, '')
    .replace(/\s+/g, ' ')
  const base = cleaned || `patient_${id}`
  return `${base}.pdf`
}

const loadArchivedPatients = async (): Promise<void> => {
  archivedPatientsLoading.value = true
  try {
    const res = await api.get('/operations/archives/', { params: { assessment_type: 'full_record' } })
    const list = Array.isArray(res.data)
      ? res.data
      : Array.isArray(res.data?.results)
        ? res.data.results
        : (res.data?.records || [])

    archivedPatients.value = (list as Array<Record<string, unknown>>).map((raw) => {
      const id = Number(raw.id)
      const userName = typeof raw.user_name === 'string' ? raw.user_name : ''
      const patientName = typeof raw.patient_name === 'string' ? raw.patient_name : ''
      const lastAssessed = typeof raw.last_assessed_at === 'string'
        ? raw.last_assessed_at
        : (typeof raw.archived_at === 'string' ? raw.archived_at : null)
      const assessmentData = (raw.assessment_data && typeof raw.assessment_data === 'object')
        ? (raw.assessment_data as Record<string, unknown>)
        : {}
      const reasonRaw = assessmentData.archival_reason ?? assessmentData.reason
      const reason = typeof reasonRaw === 'string' ? reasonRaw.trim() : ''
      const base: ArchivedPatientItem = {
        id,
        patient_name: patientName || userName || '—',
        last_assessed_at: lastAssessed,
      }
      if (reason) return { ...base, archival_reason: reason }
      return base
    }).filter((x) => Number.isFinite(x.id) && x.patient_name !== '—')
  } catch (e) {
    console.error('Failed to load archived patients', e)
    archivedPatients.value = []
  } finally {
    archivedPatientsLoading.value = false
  }
}

const downloadArchivedPatient = async (rec: ArchivedPatientItem): Promise<void> => {
  downloadLoadingId.value = rec.id
  try {
    const res = await api.get(`/operations/archives/${rec.id}/export/`, { responseType: 'blob' })
    const blob = new Blob([res.data], { type: 'application/pdf' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = buildPatientPdfFilename(rec.patient_name, rec.id)
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

interface ArchiveRecord {
  id: number;
  patient_id: number;
  patient_name: string;
  assessment_type: string;
  medical_condition: string;
  medical_history_summary?: string;
  diagnostics?: Record<string, unknown>;
  last_assessed_at: string;
  hospital_name?: string;
  decrypted_assessment_data?: Record<string, unknown>;
}

const archivesLoading = ref(false)
const archivedRecords = ref<ArchiveRecord[]>([])
const showArchiveDetail = ref(false)
const selectedArchive = ref<ArchiveRecord | null>(null)

const archiveFilters = ref({
  query: '',
  patient_id: '',
  assessment_type: '',
  medical_condition: '',
  start_date: '',
  end_date: '',
})

const formatDateDisplay = (dateStr: string): string => {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  return d.toLocaleString()
}

const participantRows = computed(() => {
  const data = selectedArchive.value?.decrypted_assessment_data
  const sections = normalizeAssessmentData(data)
  return formatSectionRows(sections.participants)
})
const vitalsRows = computed(() => {
  const data = selectedArchive.value?.decrypted_assessment_data
  const sections = normalizeAssessmentData(data)
  return formatSectionRows(sections.vitals)
})
const metricRows = computed(() => {
  const data = selectedArchive.value?.decrypted_assessment_data
  const sections = normalizeAssessmentData(data)
  return formatSectionRows(sections.metrics)
})
const noteRows = computed(() => {
  const data = selectedArchive.value?.decrypted_assessment_data
  const sections = normalizeAssessmentData(data)
  return formatSectionRows(sections.notes)
})
const listSections = computed(() => {
  const data = selectedArchive.value?.decrypted_assessment_data
  const sections = normalizeAssessmentData(data)
  return Object.entries(sections.lists).map(([title, items]) => ({ title, items }))
})
const otherRows = computed(() => {
  const data = selectedArchive.value?.decrypted_assessment_data
  const sections = normalizeAssessmentData(data)
  return formatSectionRows(sections.other)
})

const buildArchiveParams = (): Record<string, string> => {
  const params: Record<string, string> = {}
  const f = archiveFilters.value
  if (f.query) params.patient_name = f.query
  if (f.patient_id) params.patient_id = f.patient_id
  if (f.assessment_type) params.assessment_type = f.assessment_type
  if (f.medical_condition) params.condition = f.medical_condition
  if (f.start_date) params.start = f.start_date
  if (f.end_date) params.end = f.end_date
  return params
}

const searchArchives = async () => {
  archivesLoading.value = true
  try {
    const res = await api.get('/operations/archives/', { params: buildArchiveParams() })
    const list = Array.isArray(res.data)
      ? res.data
      : Array.isArray(res.data?.results)
        ? res.data.results
        : (res.data?.records || [])
    archivedRecords.value = list as ArchiveRecord[]
  } catch (err: unknown) {
    console.error('Archive search failed:', err)
    let msg = 'Archive search failed'
    if (typeof err === 'object' && err !== null) {
      const e = err as { response?: { data?: { error?: unknown } }, message?: unknown }
      const apiMsg = e.response?.data?.error
      if (typeof apiMsg === 'string' && apiMsg.trim()) {
        msg = apiMsg
      } else if (typeof e.message === 'string' && e.message.trim()) {
        msg = e.message
      }
    } else if (typeof err === 'string' && err.trim()) {
      msg = err
    }
    $q.notify({ type: 'negative', message: msg, position: 'top' })
  } finally {
    archivesLoading.value = false
  }
}

const viewArchive = async (rec: ArchiveRecord) => {
  try {
    const res = await api.get(`/operations/archives/${rec.id}/`)
    selectedArchive.value = (res.data?.record || res.data) as ArchiveRecord
    showArchiveDetail.value = true
  } catch (err) {
    console.error('Failed to load archive detail:', err)
    $q.notify({ type: 'negative', message: 'Failed to load archive detail', position: 'top' })
  }
}

const exportArchive = async (rec: ArchiveRecord) => {
  try {
    const res = await api.get(`/operations/archives/${rec.id}/export/`, { responseType: 'blob' })
    const blob = new Blob([res.data], { type: 'application/pdf' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = buildPatientPdfFilename(rec.patient_name, rec.id)
    a.click()
    URL.revokeObjectURL(url)
    $q.notify({ type: 'positive', message: 'Archive exported (PDF)', position: 'top' })
  } catch (err) {
    console.error('Export failed:', err)
    $q.notify({ type: 'negative', message: 'Export failed', position: 'top' })
  }
}

const exportFilteredArchives = async () => {
  try {
    const res = await api.get('/operations/archives/export/', {
      params: buildArchiveParams(),
      responseType: 'blob',
    })
    const blob = new Blob([res.data], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'archives_export.json'
    a.click()
    URL.revokeObjectURL(url)
    $q.notify({ type: 'positive', message: 'Archives exported', position: 'top' })
  } catch (err) {
    console.error('Export failed:', err)
    $q.notify({ type: 'negative', message: 'Export failed', position: 'top' })
  }
}

const showCreateDialog = ref(false)
const createLoading = ref(false)
const createForm = ref<{
  patient_id: string
  assessment_type: string
  medical_condition: string
  hospital_name: string
  assessment_data: string
}>({
  patient_id: '',
  assessment_type: '',
  medical_condition: '',
  hospital_name: '',
  assessment_data: '',
})

const openCreateDialog = () => {
  showCreateDialog.value = true
}

const createArchive = async () => {
  try {
    createLoading.value = true
    const pid = Number(createForm.value.patient_id)
    if (!pid || Number.isNaN(pid)) {
      $q.notify({ type: 'negative', message: 'Invalid patient ID', position: 'top' })
      return
    }
    let parsed: unknown = {}
    if (createForm.value.assessment_data && createForm.value.assessment_data.trim()) {
      try {
        parsed = JSON.parse(createForm.value.assessment_data)
      } catch {
        $q.notify({ type: 'negative', message: 'Assessment Data must be valid JSON', position: 'top' })
        return
      }
    }
    const payload = {
      patient_id: pid,
      assessment_type: createForm.value.assessment_type || 'General',
      medical_condition: createForm.value.medical_condition || '',
      hospital_name: createForm.value.hospital_name || '',
      assessment_data: parsed,
    }
    await api.post('/operations/archives/create/', payload)
    $q.notify({ type: 'positive', message: 'Archive created', position: 'top' })
    showCreateDialog.value = false
    await searchArchives()
    createForm.value = {
      patient_id: '',
      assessment_type: '',
      medical_condition: '',
      hospital_name: '',
      assessment_data: '',
    }
  } catch (err) {
    console.error('Create archive failed:', err)
    let msg = 'Create archive failed'
    const e = err as { response?: { data?: { error?: unknown } }, message?: unknown }
    const apiErr = e?.response?.data?.error
    if (typeof apiErr === 'string' && apiErr.trim()) {
      msg = apiErr
    } else if (apiErr) {
      try {
        msg = JSON.stringify(apiErr)
      } catch {
        msg = 'Create archive failed'
      }
    } else if (typeof e?.message === 'string' && e.message.trim()) {
      msg = e.message
    }
    $q.notify({ type: 'negative', message: msg, position: 'top' })
  } finally {
    createLoading.value = false
  }
}

const showEditDialog = ref(false)
const editLoading = ref(false)
const editForm = ref<{
  assessment_type: string
  medical_condition: string
  hospital_name: string
  assessment_data: string
}>({
  assessment_type: '',
  medical_condition: '',
  hospital_name: '',
  assessment_data: '',
})

const openEditDialog = () => {
  if (!selectedArchive.value) return
  editForm.value.assessment_type = selectedArchive.value.assessment_type || ''
  editForm.value.medical_condition = selectedArchive.value.medical_condition || ''
  editForm.value.hospital_name = selectedArchive.value.hospital_name || ''
  editForm.value.assessment_data = JSON.stringify(selectedArchive.value.decrypted_assessment_data || {}, null, 2)
  showEditDialog.value = true
}

const updateArchive = async () => {
  if (!selectedArchive.value) return
  try {
    editLoading.value = true
    let parsed: unknown = {}
    if (editForm.value.assessment_data && editForm.value.assessment_data.trim()) {
      try {
        parsed = JSON.parse(editForm.value.assessment_data)
      } catch {
        $q.notify({ type: 'negative', message: 'Assessment Data must be valid JSON', position: 'top' })
        return
      }
    }
    const payload = {
      assessment_type: editForm.value.assessment_type,
      medical_condition: editForm.value.medical_condition,
      hospital_name: editForm.value.hospital_name,
      assessment_data: parsed,
    }
    await api.put(`/operations/archives/${selectedArchive.value.id}/update/`, payload)
    $q.notify({ type: 'positive', message: 'Archive updated', position: 'top' })
    showEditDialog.value = false
    await searchArchives()
    await viewArchive(selectedArchive.value)
  } catch (err) {
    console.error('Update archive failed:', err)
    let msg = 'Update archive failed'
    const e = err as { response?: { data?: { error?: unknown } }, message?: unknown }
    const apiErr = e?.response?.data?.error
    if (typeof apiErr === 'string' && apiErr.trim()) {
      msg = apiErr
    } else if (apiErr) {
      try {
        msg = JSON.stringify(apiErr)
      } catch {
        msg = 'Update archive failed'
      }
    } else if (typeof e?.message === 'string' && e.message.trim()) {
      msg = e.message
    }
    $q.notify({ type: 'negative', message: msg, position: 'top' })
  } finally {
    editLoading.value = false
  }
}

const unarchiveSelected = async () => {
  if (!selectedArchive.value) return
  try {
    await api.post(`/operations/archives/${selectedArchive.value.id}/unarchive/`)
    $q.notify({ type: 'positive', message: 'Record unarchived', position: 'top' })
    showArchiveDetail.value = false
    await searchArchives()
  } catch (err) {
    console.error('Unarchive failed:', err)
    let msg = 'Unarchive failed'
    const e = err as { response?: { data?: { error?: unknown } }, message?: unknown }
    const apiErr = e?.response?.data?.error
    if (typeof apiErr === 'string' && apiErr.trim()) {
      msg = apiErr
    } else if (apiErr) {
      try {
        msg = JSON.stringify(apiErr)
      } catch {
        msg = 'Unarchive failed'
      }
    } else if (typeof e?.message === 'string' && e.message.trim()) {
      msg = e.message
    }
    $q.notify({ type: 'negative', message: msg, position: 'top' })
  }
}

watch(currentView, (v) => {
  if (v === 'archive' && archivedRecords.value.length === 0) {
    void searchArchives()
  }
})

const isVerifiedUser = computed(() => userProfile.value.verification_status === 'approved')

// User profile data
const userProfile = ref<{
  full_name: string;
  specialization?: string;
  department?: string;
  role: string;
  profile_picture: string | null;
  verification_status: string;
  hospital_name?: string;
  hospital_address?: string;
}>({
  full_name: '',
  specialization: '',
  department: '',
  role: '',
  profile_picture: null,
  verification_status: '',
  hospital_name: '',
  hospital_address: '',
});

// Document view dialog state
const showDocumentView = ref(false)
const selectedPatientDoc = ref<Patient | null>(null)
const department = computed(() => (userProfile.value?.department || userProfile.value?.specialization || '').trim() || 'Nursing')
const queueWebSocket = ref<WebSocket | null>(null)

const inferQueueDepartment = (): string => {
  return 'OPD'
}

const setupQueueWebSocket = (restart = false) => {
  try {
    if (restart && queueWebSocket.value) {
      try { queueWebSocket.value.close() } catch { /* ignore */ }
      queueWebSocket.value = null
    }
    const base = new URL(api.defaults.baseURL || `http://${window.location.hostname}:8000`)
    const protocol = base.protocol === 'https:' ? 'wss:' : 'ws:'
    const backendHost = base.hostname
    const backendPort = base.port || (base.protocol === 'https:' ? '443' : '80')
    const dept = inferQueueDepartment()
    const wsUrl = `${protocol}//${backendHost}:${backendPort}/ws/queue/${dept}/`
    const ws = new WebSocket(wsUrl)
    queueWebSocket.value = ws
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'queue_notification') {
          const n = data.notification || {}
          const ev = n.event || ''
          if (ev === 'patient_no_show') {
            const pidRaw = n.patient_id
            const pid = typeof pidRaw === 'number' ? pidRaw : Number(pidRaw)
            const cur = patientStore.currentPatient
            if (cur && Number.isFinite(pid) && Number(cur.user_id ?? 0) === pid) {
              patientStore.clearCurrentPatient()
              $q.notify({
                type: 'warning',
                message: 'This patient did not show up, kindly call on the next patient',
                position: 'top',
                timeout: 7000,
              })
            }
          }
        } else if (data.type === 'queue_position_update') {
          const pos = data.position || {}
          const evt = String(pos.event || '')
          const action = String(pos.action || '')
          const status = String(pos.status || '').toLowerCase()
          const qnRaw = pos.queue_number ?? pos.current_queue_number
          const qn = typeof qnRaw === 'number' ? qnRaw : Number(qnRaw)
          const pidRaw = pos.patient_id
          const pid = typeof pidRaw === 'number' ? pidRaw : Number(pidRaw)
          const cur = patientStore.currentPatient
          const curPid = cur ? Number(cur.user_id ?? 0) : 0
          const curQn = cur ? (typeof cur.queue_number === 'number' ? cur.queue_number : Number(cur.queue_number)) : NaN
          const selected = selectedPatient.value
          const selectedPid = selected ? Number((selected as unknown as { user_id?: unknown }).user_id ?? selected.id ?? 0) : 0
          let storagePid = NaN
          let storageQn = NaN
          try {
            const raw = localStorage.getItem('current_serving_patient') || ''
            if (raw) {
              const parsed = JSON.parse(raw) as { user_id?: unknown; queue_number?: unknown }
              const spid = typeof parsed.user_id === 'number' ? parsed.user_id : Number(parsed.user_id)
              const sqn = typeof parsed.queue_number === 'number' ? parsed.queue_number : Number(parsed.queue_number)
              storagePid = Number.isFinite(spid) ? spid : NaN
              storageQn = Number.isFinite(sqn) ? sqn : NaN
            }
          } catch {
            storagePid = NaN
            storageQn = NaN
          }

          const matchesActive =
            (Number.isFinite(pid) && curPid && pid === curPid) ||
            (Number.isFinite(qn) && Number.isFinite(curQn) && qn === curQn) ||
            (Number.isFinite(pid) && selectedPid && pid === selectedPid) ||
            (Number.isFinite(pid) && Number.isFinite(storagePid) && pid === storagePid) ||
            (Number.isFinite(qn) && Number.isFinite(storageQn) && qn === storageQn)

          const shouldRelease =
            status === 'waiting' && matchesActive

          const isNoShowRelease =
            evt === 'no_show' || action === 'move_to_end'

          if (shouldRelease) {
            patientStore.clearCurrentPatient()
            if (selectedPatient.value && selectedPid && ((Number.isFinite(pid) && pid === selectedPid) || (Number.isFinite(qn) && Number.isFinite(curQn) && qn === curQn))) {
              selectedPatient.value = null
              selectedPatientDoc.value = null
              showDocumentView.value = false
            }
            try {
              void api.post('/operations/client-log/', {
                level: 'info',
                message: 'released_active_patient_due_to_queue_return',
                route: 'NursePatientAssessment',
                context: {
                  department: String(pos.department || ''),
                  patient_id: Number.isFinite(pid) ? pid : null,
                  queue_number: Number.isFinite(qn) ? qn : null,
                  status,
                  event: evt,
                  action,
                },
              }).catch(() => {})
            } catch {
            }
            $q.notify({
              type: 'warning',
              message: isNoShowRelease
                ? 'This patient did not show up, kindly call on the next patient'
                : 'Patient was returned to the queue.',
              position: 'top',
              timeout: 7000,
            })
          }
        }
      } catch (e) {
        console.warn('Invalid WS message for NursePatientAssessment', e)
      }
    }
    ws.onclose = () => {
      setTimeout(() => setupQueueWebSocket(true), 5000)
    }
  } catch (e) {
    console.warn('Failed to setup NursePatientAssessment WebSocket', e)
  }
}

watch(
  () => inferQueueDepartment(),
  () => {
    setupQueueWebSocket(true)
  },
)

// Computed properties
const filteredPatients = computed(() => {
  // Base: only active (not discharged) patients
  let list = patients.value.filter((p) => p.discharge_date === null || p.discharge_date === '');

  // Search filter
  if (searchText.value) {
    const search = searchText.value.toLowerCase();
    list = list.filter(
      (patient) =>
        (patient.full_name || '').toLowerCase().includes(search) ||
        (patient.medical_condition || '').toLowerCase().includes(search) ||
        (patient.hospital || '').toLowerCase().includes(search),
    );
  }

  // Sorting
  const key = sortKey.value;
  const dir = sortOrder.value === 'desc' ? -1 : 1;

  const currentServingId = patientStore.currentPatient
    ? Number(patientStore.currentPatient.user_id ?? patientStore.currentPatient.id ?? 0)
    : 0;
  const assessmentRank = (p: Patient) => {
    if (!currentServingId) return 1;
    const pid = Number((p as unknown as { user_id?: unknown }).user_id ?? p.id ?? 0);
    return pid === currentServingId ? 0 : 1;
  };

  list = [...list].sort((a, b) => {
    const ar = assessmentRank(a);
    const br = assessmentRank(b);
    if (ar !== br) return ar - br;

    const av = (key === 'age' ? (a.age ?? 0) : (a[key] ?? '')).toString().toLowerCase();
    const bv = (key === 'age' ? (b.age ?? 0) : (b[key] ?? '')).toString().toLowerCase();
    if (av < bv) return -1 * dir;
    if (av > bv) return 1 * dir;

    const an = (a.full_name ?? '').toString().toLowerCase();
    const bn = (b.full_name ?? '').toString().toLowerCase();
    if (an < bn) return -1;
    if (an > bn) return 1;

    return Number(a.id ?? 0) - Number(b.id ?? 0);
  });

  return list;
});

const activePatientsCount = computed(
  () => patients.value.filter((p) => p.discharge_date === null || p.discharge_date === '').length,
);

const totalPatientsCount = computed(() => patients.value.length)

// Methods
const loadPatients = async () => {
  loading.value = true;
  try {
    const response = await api.get('/users/nurse/patients/');
    if (response.data.success) {
      // Exclude any dummy patients used for analytics/demo data
      const fetched = (response.data.patients || [])
        .filter((p: Patient | Record<string, unknown>) => !(p as Patient).is_dummy)
        .map((p: Patient) => {
          const dob = typeof p.date_of_birth === 'string' ? p.date_of_birth : ''
          const computedAge = computeAgeFromIsoDate(dob)
          const apiAge = typeof p.age === 'number' ? p.age : null
          const age = apiAge === 0 && (computedAge ?? 0) > 0 ? computedAge : (apiAge ?? computedAge)
          const bloodRaw = (p as unknown as { blood_type?: unknown }).blood_type
          const blood = typeof bloodRaw === 'string' ? bloodRaw.trim() : ''
          return {
            ...p,
            age,
            blood_type: blood || 'UNK'
          }
        }) as Patient[];

      patients.value = fetched.map((p) => ({ ...p, assessment_status: 'pending' }))
      console.log('Patients loaded:', patients.value.length);
      // Attempt to preselect the most recently called patient
      prefillFromCurrentServing();
    }
  } catch (error) {
    console.error('Failed to load patients:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to load patients',
      position: 'top',
    });
  } finally {
    loading.value = false;
  }
};

const selectPatient = (patient: Patient) => {
  selectedPatient.value = patient;
  console.log('Selected patient:', patient);
};

const viewPatientDetails = (patient: Patient) => {
  // Open document-style view with header details
  selectedPatient.value = patient;
  selectedPatientDoc.value = patient;
  void loadDocumentForms(patient.id)
  showDocumentView.value = true;
  $q.notify({ type: 'info', message: `Viewing record for ${patient.full_name}`, position: 'top' });
};

// Prefill selection from the latest "Call Next Patient" action
const prefillFromCurrentServing = () => {
  try {
    patientStore.loadFromStorage();
    const cp = patientStore.currentPatient;
    
    if (!cp) return;
    
    // Validate essential fields
    if (!cp.full_name || (!cp.id && !cp.user_id)) {
      console.warn('Invalid patient data from store:', cp);
      return;
    }

    // Normalize to Patient type shape used by this page
    const candidate: Patient = {
      ...cp,
      // Ensure date strings are compatible
      date_of_admission: cp.date_of_admission || '',
      discharge_date: cp.discharge_date || ''
    };

    // If not already in the list, append for immediate visibility
    const exists = patients.value.some((p) => p.user_id === candidate.user_id || p.id === candidate.id);
    if (!exists) {
      patients.value.unshift(candidate);
    }
    // Select in UI for quick access
    selectedPatient.value = candidate;
    $q.notify({ type: 'info', message: `Forwarded ${candidate.full_name} to Patient Management`, position: 'top' });
  } catch (e) {
    console.warn('Failed to prefill current serving patient', e);
  }
};

watch(
  () => patientStore.currentPatient,
  (cp) => {
    if (!cp) return;
    const currentId = Number(cp.user_id ?? cp.id ?? 0);
    if (!currentId) return;

    const match = patients.value.find((p) => Number(p.user_id ?? p.id ?? 0) === currentId);
    if (match) {
      selectedPatient.value = match;
      return;
    }

    const candidate: Patient = {
      ...(cp as unknown as Patient),
      date_of_admission: (cp as unknown as Patient).date_of_admission || '',
      discharge_date: (cp as unknown as Patient).discharge_date || '',
    };

    patients.value.unshift(candidate);
    selectedPatient.value = candidate;
  },
  { deep: true },
);

const editPatient = (patient: Patient) => {
  selectedPatient.value = patient;
  if (!isVerifiedUser.value) {
    $q.notify({ type: 'warning', message: 'Account verification required.' })
    return
  }
  void openPhysicalForm()
};

const fetchUserProfile = async () => {
  try {
    const response = await api.get('/users/profile/');
    const userData = response.data.user;

    userProfile.value = {
      full_name: userData.full_name,
      specialization: userData.nurse_profile?.specialization,
      department: userData.nurse_profile?.department || userData.department || userData.nurse_profile?.specialization || '',
      role: userData.role,
      profile_picture: userData.profile_picture || null,
      verification_status: userData.verification_status,
      hospital_name: userData.hospital_name || '',
      hospital_address: userData.hospital_address || '',
    };
  } catch (error) {
    console.error('Failed to fetch user profile:', error);
    // Fallback to localStorage if API call fails
    const userLS = localStorage.getItem('user');
    if (userLS) {
      const user = JSON.parse(userLS);
      userProfile.value = {
        full_name: user.full_name,
        specialization: user.nurse_profile?.specialization,
        department: user.nurse_profile?.department || user.department || user.nurse_profile?.specialization || '',
        role: user.role,
        profile_picture: user.profile_picture || null,
        verification_status: user.verification_status,
        hospital_name: user.hospital_name || '',
        hospital_address: user.hospital_address || '',
      };
    }
  }
};

// Navigation and logout functionality handled by NurseSidebar component

// Pain Assessment Logic
const painDialogOpen = ref(false);
const currentPainScore = ref(5);
const painNotes = ref('');
const painHistory = ref<PainAssessment[]>([]);
const painSubmitting = ref(false);

const painEmojis = {
  0: '😊',
  1: '😊',
  2: '🙂',
  3: '🙂',
  4: '😐',
  5: '😐',
  6: '😟',
  7: '😟',
  8: '😰',
  9: '😰',
  10: '😫'
};

const getPainEmoji = (score: number) => {
  return painEmojis[score as keyof typeof painEmojis] || '❓';
};

const getPainLabel = (score: number) => {
  if (score === 0) return 'No Pain';
  if (score <= 2) return 'Mild Pain';
  if (score <= 4) return 'Moderate Pain';
  if (score <= 6) return 'Severe Pain';
  if (score <= 8) return 'Very Severe Pain';
  return 'Unbearable Pain';
};

const getPainColor = (score: number) => {
  if (score === 0) return 'positive';
  if (score <= 2) return 'light-green';
  if (score <= 4) return 'yellow-9';
  if (score <= 6) return 'orange-8';
  if (score <= 8) return 'deep-orange-9';
  return 'negative';
};

const openPainAssessment = async (patient: Patient) => {
  if (!patient) return;
  selectedPatient.value = patient;
  painDialogOpen.value = true;
  currentPainScore.value = 5;
  painNotes.value = '';
  await loadPainHistory(patient.id);
};

const loadPainHistory = async (patientId: number) => {
  try {
    const response = await api.get(`/operations/pain-assessment/${patientId}/history/`);
    painHistory.value = response.data;
  } catch (error) {
    console.error('Failed to load pain history:', error);
    $q.notify({ type: 'negative', message: 'Failed to load pain history' });
  }
};

const submitPainAssessment = async () => {
  if (!selectedPatient.value) return;
  painSubmitting.value = true;
  try {
    await api.post(`/operations/pain-assessment/${selectedPatient.value.id}/record/`, {
      pain_score: currentPainScore.value,
      notes: painNotes.value
    });
    $q.notify({ type: 'positive', message: 'Pain assessment recorded' });
    await loadPainHistory(selectedPatient.value.id);
    painNotes.value = '';
  } catch (error) {
    console.error('Failed to record pain assessment:', error);
    $q.notify({ type: 'negative', message: 'Failed to record pain assessment' });
  } finally {
    painSubmitting.value = false;
  }
};

// Registration / Demographics gating
const showRegistrationDialog = ref(false)
const registrationCompleted = ref(false)
const registrationForm = ref({
  // Header and Administrative Data
  hospitalName: '',
  departmentName: 'OPD',
  hospitalAddress: '',
  mrn: '',
  dateOfRegistration: '',
  registeredBy: '',
  // Patient Identification Data
  firstName: '',
  middleName: '',
  lastName: '',
  dob: '',
  age: '',
  sex: '',
  maritalStatus: '',
  nationality: '',
  // Contact Information
  homeAddress: '',
  cellPhone: '',
  homePhone: '',
  email: '',
  occupation: '',
  // Emergency Contact Information
  emergencyName: '',
  emergencyRelationship: '',
  emergencyPhone: '',
  // New Registration Fields
  medicalTests: [] as string[],
  consultationLocation: '',
  attendingPhysician: '',
  // Medical Information
  reasonForVisit: '',
  referringDoctor: '',
  primaryCarePhysician: '',
  currentMedications: '',
  medicalHistory: '', // Past Medical History
  commonConditions: [] as string[],
  symptomsDescription: '',
  painScale: 0,
  affectedBodyParts: [] as string[],
  knownAllergies: [] as string[],
  // Authorization
  consentAgreed: false,
  patientSignature: '',
  signatureDate: ''
})

const showAssessmentDialog = ref(false)
const savingAssessment = ref(false)
const assessmentStep = ref(1)
const assessmentDraftSavedAt = ref<string | null>(null)
const assessmentForm = ref({
  vitals: {
    bp: '',
    hr: null as number | null,
    rr: null as number | null,
    temp_c: null as number | null,
    spo2: null as number | null,
  },
  height_cm: null as number | null,
  weight_kg: null as number | null,
  chief_complaint: '',
  pain_score: 0,
  affected_body_parts: [] as string[],
  assessment_notes: '',
  mental_status: '',
  fall_risk_score: null as number | null,
})

type PhysicalLabKey =
  | 'cbc'
  | 'urinalysis'
  | 'fecalysis'
  | 'cxr'
  | 'ishihara'
  | 'audio'
  | 'psychological_exam'
  | 'drug_test'
  | 'hbsag'

type PhysicalFormModel = {
  registration: {
    surname: string
    first_name: string
    middle_name: string
    age: number | null
    birthday: string
    sex: string
    civil_status: string
    address: string
    contact_no: string
    patient_id: string
    department: string
    nationality: string
    religion: string
    emergency_contact: { name: string; relationship: string; contact_no: string }
  }
  opd_assessment: {
    complaints_pe_findings: string
    vitals: { bp: string; pr: number | null; rr: number | null; temp: number | null }
    physical_exam: { heent: string; heart: string; lungs: string; abdomen_extremities: string }
    labs: Record<PhysicalLabKey, { checked: boolean; result: string }>
    date: string
    diagnosis_treatment_remarks: string
    staff: string
  }
}

const showPhysicalFormDialog = ref(false)
const savingPhysicalForm = ref(false)
const physicalFormRef = ref<InstanceType<typeof TipMedicalRecordForm> | null>(null)
const physicalFormRevisionDate = computed(() => {
  const d = new Date()
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
})
const emptyPhysicalForm = (): PhysicalFormModel => ({
  registration: {
    surname: '',
    first_name: '',
    middle_name: '',
    age: null,
    birthday: '',
    sex: '',
    civil_status: '',
    address: '',
    contact_no: '',
    patient_id: '',
    department: '',
    nationality: '',
    religion: '',
    emergency_contact: { name: '', relationship: '', contact_no: '' }
  },
  opd_assessment: {
    complaints_pe_findings: '',
    vitals: { bp: '', pr: null, rr: null, temp: null },
    physical_exam: { heent: '', heart: '', lungs: '', abdomen_extremities: '' },
    labs: {
      cbc: { checked: false, result: '' },
      urinalysis: { checked: false, result: '' },
      fecalysis: { checked: false, result: '' },
      cxr: { checked: false, result: '' },
      ishihara: { checked: false, result: '' },
      audio: { checked: false, result: '' },
      psychological_exam: { checked: false, result: '' },
      drug_test: { checked: false, result: '' },
      hbsag: { checked: false, result: '' }
    },
    date: '',
    diagnosis_treatment_remarks: '',
    staff: ''
  }
})
const physicalFormModel = ref<PhysicalFormModel>(emptyPhysicalForm())

const documentFormsLoading = ref(false)
const documentFormsError = ref<string | null>(null)
const documentIntakeRaw = ref<Record<string, unknown> | null>(null)
const documentPhysicalPreviewModel = ref<PhysicalFormModel>(emptyPhysicalForm())

const documentRevisionDate = computed(() => {
  const d = String(documentPhysicalPreviewModel.value?.opd_assessment?.date || '').trim()
  return d || physicalFormRevisionDate.value
})

const documentStaffOptions = computed(() => {
  const opts: string[] = []
  const nurseName = String(userProfile.value?.full_name || '').trim()
  if (nurseName) opts.push(nurseName)
  const staff = String(documentPhysicalPreviewModel.value?.opd_assessment?.staff || '').trim()
  if (staff && !opts.includes(staff)) opts.push(staff)
  return opts
})

const buildPhysicalPreviewFromIntake = (data: Record<string, unknown>, patient: Patient | null): PhysicalFormModel => {
  const selectedFullName = String(patient?.full_name || '').trim()
  const parts = selectedFullName.split(/\s+/).filter(Boolean)
  const firstFromName = parts[0] || ''
  const lastFromName = parts.length > 1 ? (parts.at(-1) ?? '') : ''
  const middleFromName = parts.length > 2 ? parts.slice(1, -1).join(' ') : ''
  const selectedDob = typeof patient?.date_of_birth === 'string' ? patient?.date_of_birth : ''
  const selectedGender = String(patient?.gender || '').trim()
  const selectedAge = typeof patient?.age === 'number' ? patient?.age : computeAgeFromIsoDate(selectedDob)
  const selectedPatientId = typeof patient?.patient_id === 'string' ? patient?.patient_id : ''

  const reg = (data.registration_physical ?? data.registration ?? {}) as Record<string, unknown>
  const opd = (data.opd_assessment ?? {}) as Record<string, unknown>
  const regBday = typeof reg.birthday === 'string' ? reg.birthday : selectedDob
  const regAgeRaw = reg.age
  const regAgeNum =
    typeof regAgeRaw === 'number'
      ? regAgeRaw
      : typeof regAgeRaw === 'string' && regAgeRaw.trim() && Number.isFinite(Number(regAgeRaw))
        ? Number(regAgeRaw)
        : null
  const derivedAge = computeAgeFromIsoDate(regBday)

  const model: PhysicalFormModel = {
    registration: {
      surname: typeof reg.surname === 'string' ? reg.surname : lastFromName,
      first_name: typeof reg.first_name === 'string' ? reg.first_name : firstFromName,
      middle_name: typeof reg.middle_name === 'string' ? reg.middle_name : middleFromName,
      age: selectedAge ?? regAgeNum ?? derivedAge,
      birthday: regBday,
      sex: typeof reg.sex === 'string' ? reg.sex : selectedGender,
      civil_status: typeof reg.civil_status === 'string' ? reg.civil_status : '',
      address: typeof reg.address === 'string' ? reg.address : '',
      contact_no: typeof reg.contact_no === 'string' ? reg.contact_no : '',
      patient_id:
        typeof reg.patient_id === 'string'
          ? reg.patient_id
          : typeof reg.student_employee_no === 'string'
            ? reg.student_employee_no
            : selectedPatientId,
      department: typeof reg.department === 'string' ? reg.department : '',
      nationality: typeof reg.nationality === 'string' ? reg.nationality : '',
      religion: typeof reg.religion === 'string' ? reg.religion : '',
      emergency_contact: {
        name: typeof (reg.emergency_contact as Record<string, unknown> | undefined)?.name === 'string'
          ? String((reg.emergency_contact as Record<string, unknown>).name)
          : '',
        relationship: typeof (reg.emergency_contact as Record<string, unknown> | undefined)?.relationship === 'string'
          ? String((reg.emergency_contact as Record<string, unknown>).relationship)
          : '',
        contact_no: typeof (reg.emergency_contact as Record<string, unknown> | undefined)?.contact_no === 'string'
          ? String((reg.emergency_contact as Record<string, unknown>).contact_no)
          : ''
      }
    },
    opd_assessment: {
      complaints_pe_findings: typeof opd.complaints_pe_findings === 'string' ? opd.complaints_pe_findings : '',
      vitals: {
        bp: typeof (opd.vitals as Record<string, unknown> | undefined)?.bp === 'string'
          ? String((opd.vitals as Record<string, unknown>).bp)
          : '',
        pr: typeof (opd.vitals as Record<string, unknown> | undefined)?.pr === 'number'
          ? Number((opd.vitals as Record<string, unknown>).pr)
          : null,
        rr: typeof (opd.vitals as Record<string, unknown> | undefined)?.rr === 'number'
          ? Number((opd.vitals as Record<string, unknown>).rr)
          : null,
        temp: typeof (opd.vitals as Record<string, unknown> | undefined)?.temp === 'number'
          ? Number((opd.vitals as Record<string, unknown>).temp)
          : null
      },
      physical_exam: {
        heent: typeof (opd.physical_exam as Record<string, unknown> | undefined)?.heent === 'string'
          ? String((opd.physical_exam as Record<string, unknown>).heent)
          : '',
        heart: typeof (opd.physical_exam as Record<string, unknown> | undefined)?.heart === 'string'
          ? String((opd.physical_exam as Record<string, unknown>).heart)
          : '',
        lungs: typeof (opd.physical_exam as Record<string, unknown> | undefined)?.lungs === 'string'
          ? String((opd.physical_exam as Record<string, unknown>).lungs)
          : '',
        abdomen_extremities: typeof (opd.physical_exam as Record<string, unknown> | undefined)?.abdomen_extremities === 'string'
          ? String((opd.physical_exam as Record<string, unknown>).abdomen_extremities)
          : ''
      },
      labs:
        typeof opd.labs === 'object' && opd.labs !== null
          ? (opd.labs as PhysicalFormModel['opd_assessment']['labs'])
          : emptyPhysicalForm().opd_assessment.labs,
      date: typeof opd.date === 'string' ? opd.date : '',
      diagnosis_treatment_remarks: typeof opd.diagnosis_treatment_remarks === 'string' ? opd.diagnosis_treatment_remarks : '',
      staff: typeof opd.staff === 'string' ? opd.staff : ''
    }
  }

  if (!model.opd_assessment.date) model.opd_assessment.date = physicalFormRevisionDate.value
  if (!model.opd_assessment.staff) model.opd_assessment.staff = String(userProfile.value?.full_name || '').trim()
  if (!model.registration.department) model.registration.department = String(userProfile.value?.department || 'OPD').trim()

  return model
}

const loadDocumentForms = async (patientId: number) => {
  documentFormsLoading.value = true
  documentFormsError.value = null
  documentIntakeRaw.value = null
  documentPhysicalPreviewModel.value = emptyPhysicalForm()
  try {
    const intakeRes = await api.get(`/users/nurse/patient/${patientId}/intake/`)
    const intakeData = ((intakeRes as { data?: { data?: unknown } } | null)?.data?.data ?? {}) as Record<string, unknown>
    documentIntakeRaw.value = intakeData
    documentPhysicalPreviewModel.value = buildPhysicalPreviewFromIntake(intakeData, selectedPatientDoc.value)
  } catch (e) {
    documentFormsError.value = `Failed to load forms. ${extractApiErrorMessage(e)}`
  } finally {
    documentFormsLoading.value = false
  }
}

// Options for new fields
const allergyOptions = [
  'Penicillin', 'Sulfa Drugs', 'Aspirin', 'Peanuts', 'Shellfish', 'Latex', 'Dust', 'Pollen'
]
const relationshipOptions = ['Spouse', 'Parent', 'Child', 'Sibling', 'Friend', 'Other']

// Stepper state & validation
const registrationStep = ref(1)
const draftSavedAt = ref<string | null>(null)

const requiredByStep = {
  1: ['hospitalName', 'hospitalAddress'],
  2: ['mrn', 'firstName', 'lastName', 'dob', 'age', 'sex', 'maritalStatus', 'cellPhone', 'homeAddress'],
  3: ['emergencyName', 'emergencyRelationship', 'emergencyPhone'],
  4: [],
  5: ['consentAgreed', 'patientSignature', 'signatureDate']
} as Record<number, string[]>

const isStepValid = (step: number) => {
  const r = registrationForm.value as Record<string, unknown>
  const required = requiredByStep[step] || []
  return required.every(k => {
    const val = r[k]
    if (Array.isArray(val)) return val.length > 0
    return !!val
  })
}

const nextStep = () => {
  if (!isStepValid(registrationStep.value)) {
    $q.notify({ type: 'warning', message: 'Please complete required fields before proceeding' })
    return
  }
  if (registrationStep.value < 5) registrationStep.value += 1
}

const prevStep = () => { if (registrationStep.value > 1) registrationStep.value -= 1 }

const saveRegistrationDraft = () => {
  if (!selectedPatient.value) { $q.notify({ type: 'negative', message: 'Select a patient first' }); return }
  const key = `patient_reg_draft_${selectedPatient.value.id}`
  const payload = { patientId: selectedPatient.value.id, ...registrationForm.value, step: registrationStep.value, savedAt: new Date().toISOString() }
  localStorage.setItem(key, JSON.stringify(payload))
  draftSavedAt.value = payload.savedAt
  $q.notify({ type: 'info', message: 'Draft saved' })
}

const loadRegistrationDraft = () => {
  if (!selectedPatient.value) return
  const key = `patient_reg_draft_${selectedPatient.value.id}`
  const raw = localStorage.getItem(key)
  if (!raw) return
  try {
    const payload = JSON.parse(raw)
    if (Array.isArray(payload.currentMedications)) {
      payload.currentMedications = payload.currentMedications.filter(Boolean).join('\n')
    }
    Object.assign(registrationForm.value, payload)
    if (payload.step) registrationStep.value = Number(payload.step) || 1
    draftSavedAt.value = payload.savedAt || null
  } catch { /* ignore */ }
}


const prefillRegistrationFromProfile = () => {
  try {
    // Attempt to infer nurse profile info if available with a safe type
    type MaybeUserProfile = {
      hospital_name?: string;
      hospital_address?: string;
      nurse_profile?: { department?: string };
      full_name?: string;
    }
    const upHolder = userProfile as unknown as { value?: MaybeUserProfile | null }
    const up: MaybeUserProfile | null = upHolder?.value ?? null
    if (up) {
      registrationForm.value.hospitalName = up.hospital_name ?? ''
      registrationForm.value.hospitalAddress = up.hospital_address ?? ''
      registrationForm.value.departmentName = up.nurse_profile?.department ?? 'OPD'
      registrationForm.value.registeredBy = up.full_name ?? ''
    }
  } catch {
    // ignore
  }
}

const generateMRN = (id: number | string) => {
  const rand = Math.floor(Math.random() * 9000) + 1000
  return `MRN-${id}-${rand}`
}

const openRegistration = () => {
  if (!selectedPatient.value) { $q.notify({ type: 'warning', message: 'Select a patient first' }); return }
  // Load draft if available; otherwise prefill defaults
  type MaybePatient = { mrn?: string; id: number; full_name?: string; email?: string; age?: number | null; dob?: string; gender?: string; home_address?: string; phone?: string }
  const sp = selectedPatient.value as unknown as MaybePatient
  const draftKey = `patient_reg_draft_${sp.id}`
  if (localStorage.getItem(draftKey)) {
    loadRegistrationDraft()
  } else {
    prefillRegistrationFromProfile()
    // prefill MRN and date
    registrationForm.value.mrn = sp.mrn ?? generateMRN(sp.id)
    registrationForm.value.dateOfRegistration = new Date().toISOString()
    registrationForm.value.signatureDate = new Date().toISOString().slice(0, 10)
    // prefill identity if available from patient list
    const names = (sp.full_name ?? '').trim().split(/\s+/)
    registrationForm.value.firstName = String(names[0] || '')
    registrationForm.value.lastName = String(names.length > 1 ? names[names.length - 1] : '')
    registrationForm.value.email = sp.email ?? ''
    
    // Attempt to prefill other fields if available in patient object
    if (typeof sp.age === 'number' && Number.isFinite(sp.age)) registrationForm.value.age = String(sp.age)
    if (sp.dob) registrationForm.value.dob = sp.dob
    if (sp.gender) registrationForm.value.sex = sp.gender
    // Note: home_address/phone might not be standard fields in Patient type, but good to try
    
    registrationStep.value = 1
    draftSavedAt.value = null
  }
  showRegistrationDialog.value = true
}

const openAssessment = async () => {
  if (!selectedPatient.value) { $q.notify({ type: 'warning', message: 'Select a patient first' }); return }
  const pid = selectedPatient.value.id
  const draftKey = `patient_assessment_draft_${pid}`
  if (localStorage.getItem(draftKey)) {
    loadAssessmentDraft()
  } else {
    try {
      const res = await api.get(`/users/nurse/patient/${pid}/intake/`)
      const data = (res.data?.data ?? {}) as Record<string, unknown>
      const vitals = (data.vitals ?? {}) as Record<string, unknown>
      assessmentForm.value.vitals.bp = typeof vitals.bp === 'string' ? vitals.bp : ''
      assessmentForm.value.vitals.hr = typeof vitals.hr === 'number' ? vitals.hr : null
      assessmentForm.value.vitals.rr = typeof vitals.rr === 'number' ? vitals.rr : null
      assessmentForm.value.vitals.temp_c = typeof vitals.temp_c === 'number' ? vitals.temp_c : null
      assessmentForm.value.vitals.spo2 = typeof vitals.spo2 === 'number' ? vitals.spo2 : null
      assessmentForm.value.height_cm = typeof data.height_cm === 'number' ? data.height_cm : null
      assessmentForm.value.weight_kg = typeof data.weight_kg === 'number' ? data.weight_kg : null
      assessmentForm.value.chief_complaint = typeof data.chief_complaint === 'string' ? data.chief_complaint : ''
      assessmentForm.value.pain_score = typeof data.pain_score === 'number' ? data.pain_score : 0
      assessmentForm.value.affected_body_parts = Array.isArray(data.affected_body_parts)
        ? (data.affected_body_parts as unknown[]).filter((x): x is string => typeof x === 'string')
        : []
      assessmentForm.value.assessment_notes = typeof data.assessment_notes === 'string' ? data.assessment_notes : ''
      assessmentForm.value.mental_status = typeof data.mental_status === 'string' ? data.mental_status : ''
      assessmentForm.value.fall_risk_score = typeof data.fall_risk_score === 'number' ? data.fall_risk_score : null
      assessmentDraftSavedAt.value = null
      assessmentStep.value = 1
    } catch {
      assessmentDraftSavedAt.value = null
      assessmentStep.value = 1
    }
  }
  showAssessmentDialog.value = true
}

const openAssessmentGuarded = () => {
  if (!registrationCompleted.value) {
    $q.notify({ type: 'warning', message: 'Complete registration first before assessment' })
    openRegistration()
    return
  }
  void openAssessment()
}

defineExpose({ openAssessment, openAssessmentGuarded })

const savingRegistration = ref(false)

const sanitizeExistingIntake = (existing: Record<string, unknown>) => {
  const out: Record<string, unknown> = { ...(existing || {}) }
  const reg = out.registration
  if (reg && typeof reg === 'object' && !Array.isArray(reg)) {
    const r = reg as Record<string, unknown>
    const hasAny = Object.keys(r).length > 0
    const surnameOk = typeof r.surname === 'string' && r.surname.trim().length > 0
    const firstOk = typeof r.first_name === 'string' && r.first_name.trim().length > 0
    const bdayOk = typeof r.birthday === 'string' && r.birthday.trim().length > 0
    if (hasAny && !(surnameOk && firstOk && bdayOk)) {
      out.registration = {}
    }
  }
  return out
}

const extractApiErrorMessage = (e: unknown): string => {
  const maybe = e as { response?: { data?: unknown; status?: number } }
  const data = maybe?.response?.data
  const status = maybe?.response?.status
  const errors = (data as { errors?: unknown } | undefined)?.errors
  const error = (data as { error?: unknown } | undefined)?.error
  if (typeof errors === 'string' && errors.trim()) return errors
  if (typeof error === 'string' && error.trim()) return error
  if (errors && typeof errors === 'object') return `Validation failed (${status ?? 400})`
  if (typeof status === 'number') return `Request failed (${status})`
  return 'Request failed'
}

const computeAgeFromIsoDate = (iso: string): number | null => {
  const s = String(iso || '').trim()
  if (!s) return null
  const raw = s.length >= 10 ? s.slice(0, 10) : s
  const d = new Date(raw)
  if (Number.isNaN(d.getTime())) return null
  const today = new Date()
  let age = today.getFullYear() - d.getFullYear()
  const m = today.getMonth() - d.getMonth()
  if (m < 0 || (m === 0 && today.getDate() < d.getDate())) age -= 1
  return Number.isFinite(age) ? age : null
}

const saveRegistration = async () => {
  if (!selectedPatient.value) { $q.notify({ type: 'negative', message: 'Select a patient first' }); return }
  
  // Validate all steps
  const r = registrationForm.value
  // Check required fields manually for safety
  const missing: string[] = []
  if (!r.hospitalName) missing.push('Hospital Name')
  if (!r.mrn) missing.push('MRN')
  if (!r.firstName) missing.push('First Name')
  if (!r.lastName) missing.push('Last Name')
  if (!String(r.age || '').trim()) missing.push('Age')
  if (!r.dob) missing.push('Date of Birth')
  if (!r.homeAddress) missing.push('Address')
  if (!r.cellPhone) missing.push('Contact Number')
  if (!r.emergencyName) missing.push('Emergency Contact')
  
  if (missing.length > 0) {
     $q.notify({ type: 'warning', message: `Missing required fields: ${missing.join(', ')}` })
     return
  }

  savingRegistration.value = true
  try {
    const today = new Date().toISOString().slice(0, 10)
    registrationForm.value.signatureDate = today

    const existing = await api
      .get(`/users/nurse/patient/${selectedPatient.value.id}/intake/`)
      .then((res) => (res.data?.data ?? {}) as Record<string, unknown>)
      .catch(() => ({}))
    const existingSafe = sanitizeExistingIntake(existing)

    const registrationPayload = {
      hospitalName: r.hospitalName,
      departmentName: r.departmentName,
      hospitalAddress: r.hospitalAddress,
      mrn: r.mrn,
      dateOfRegistration: r.dateOfRegistration,
      registeredBy: r.registeredBy,
      firstName: r.firstName,
      middleName: r.middleName,
      lastName: r.lastName,
      dob: r.dob,
      age: r.age,
      sex: r.sex,
      maritalStatus: r.maritalStatus,
      nationality: r.nationality,
      homeAddress: r.homeAddress,
      cellPhone: r.cellPhone,
      homePhone: r.homePhone,
      email: r.email,
      occupation: r.occupation,
      emergencyName: r.emergencyName,
      emergencyRelationship: r.emergencyRelationship,
      emergencyPhone: r.emergencyPhone,
      knownAllergies: r.knownAllergies,
      currentMedications: r.currentMedications,
      medicalHistory: r.medicalHistory,
      consentAgreed: r.consentAgreed,
      patientSignature: r.patientSignature,
      signatureDate: r.signatureDate || today,
    }

    const intakeRegistration = {
      ...registrationPayload,
      surname: String(r.lastName || ''),
      first_name: String(r.firstName || ''),
      middle_name: String(r.middleName || ''),
      birthday: String(r.dob || ''),
      address: String(r.homeAddress || ''),
      contact_no: String(r.cellPhone || ''),
      sex: String(r.sex || ''),
      patient_id: typeof selectedPatient.value.patient_id === 'string' ? selectedPatient.value.patient_id : ''
    }

    const intakePayload = {
      ...existingSafe,
      registration: intakeRegistration,
      allergies: r.knownAllergies || [],
      current_medications: r.currentMedications || '',
      medical_history: r.medicalHistory || '',
      consent_agreed: !!r.consentAgreed,
      patient_signature: r.patientSignature || '',
      signature_date: r.signatureDate || today,
    }

    await api.put(`/users/nurse/patient/${selectedPatient.value.id}/intake/`, intakePayload)

    const key = `patient_reg_${selectedPatient.value.id}`
    const payload = { patientId: selectedPatient.value.id, ...r, completedAt: new Date().toISOString() }
    localStorage.setItem(key, JSON.stringify(payload))
    registrationCompleted.value = true
    showRegistrationDialog.value = false
    $q.notify({ type: 'positive', message: 'Patient registration saved' })
    void api.post('/operations/client-log/', {
      level: 'info',
      message: 'saveRegistration succeeded',
      route: 'NursePatientAssessment',
      context: { patient_id: selectedPatient.value.id }
    }).catch(() => { /* non-blocking */ })
  } catch (e) {
    console.error('Failed to save registration/intake:', e)
    $q.notify({ type: 'negative', message: `Failed to save registration. ${extractApiErrorMessage(e)}`, position: 'top' })
    void api.post('/operations/client-log/', {
      level: 'error',
      message: 'saveRegistration failed',
      route: 'NursePatientAssessment',
      context: { error: String(e), patient_id: selectedPatient.value?.id }
    }).catch(() => { /* non-blocking */ })
  } finally {
    savingRegistration.value = false
  }
}

const saveAssessmentDraft = () => {
  if (!selectedPatient.value) { $q.notify({ type: 'negative', message: 'Select a patient first' }); return }
  const key = `patient_assessment_draft_${selectedPatient.value.id}`
  const payload = { patientId: selectedPatient.value.id, ...assessmentForm.value, step: assessmentStep.value, savedAt: new Date().toISOString() }
  localStorage.setItem(key, JSON.stringify(payload))
  assessmentDraftSavedAt.value = payload.savedAt
  $q.notify({ type: 'info', message: 'Assessment draft saved' })
}

const loadAssessmentDraft = () => {
  if (!selectedPatient.value) return
  const key = `patient_assessment_draft_${selectedPatient.value.id}`
  const raw = localStorage.getItem(key)
  if (!raw) return
  try {
    const payload = JSON.parse(raw)
    Object.assign(assessmentForm.value, payload)
    if (payload.step) assessmentStep.value = Number(payload.step) || 1
    assessmentDraftSavedAt.value = payload.savedAt || null
  } catch { /* ignore */ }
}

const nextAssessmentStep = () => {
  if (assessmentStep.value === 1) {
    assessmentStep.value = 2
    return
  }
}

const prevAssessmentStep = () => { if (assessmentStep.value > 1) assessmentStep.value -= 1 }

const saveAssessment = async () => {
  if (!selectedPatient.value) { $q.notify({ type: 'negative', message: 'Select a patient first' }); return }

  if (!assessmentForm.value.chief_complaint) {
    $q.notify({ type: 'warning', message: 'Chief Complaint is required' })
    return
  }

  savingAssessment.value = true
  try {
    const existing = await api
      .get(`/users/nurse/patient/${selectedPatient.value.id}/intake/`)
      .then((res) => (res.data?.data ?? {}) as Record<string, unknown>)
      .catch(() => ({}))
    const existingSafe = sanitizeExistingIntake(existing)

    const intakePayload = {
      ...existingSafe,
      vitals: assessmentForm.value.vitals,
      height_cm: assessmentForm.value.height_cm,
      weight_kg: assessmentForm.value.weight_kg,
      chief_complaint: assessmentForm.value.chief_complaint,
      pain_score: assessmentForm.value.pain_score,
      affected_body_parts: assessmentForm.value.affected_body_parts,
      assessment_notes: assessmentForm.value.assessment_notes,
      mental_status: assessmentForm.value.mental_status,
      fall_risk_score: assessmentForm.value.fall_risk_score,
      assessed_at: new Date().toISOString(),
    }

    await api.put(`/users/nurse/patient/${selectedPatient.value.id}/intake/`, intakePayload)

    showAssessmentDialog.value = false
    $q.notify({ type: 'positive', message: 'Patient assessment saved' })
    void api.post('/operations/client-log/', {
      level: 'info',
      message: 'saveAssessment succeeded',
      route: 'NursePatientAssessment',
      context: { patient_id: selectedPatient.value.id }
    }).catch(() => { /* non-blocking */ })
  } catch (e) {
    console.error('Failed to save assessment:', e)
    $q.notify({ type: 'negative', message: `Failed to save assessment. ${extractApiErrorMessage(e)}`, position: 'top' })
    void api.post('/operations/client-log/', {
      level: 'error',
      message: 'saveAssessment failed',
      route: 'NursePatientAssessment',
      context: { error: String(e), patient_id: selectedPatient.value?.id }
    }).catch(() => { /* non-blocking */ })
  } finally {
    savingAssessment.value = false
  }
}



watch(selectedPatient, (p) => {
  registrationCompleted.value = !!(p && localStorage.getItem(`patient_reg_${p.id}`))
  if (p) {
    loadDemographics();
  } else {
    demographics.value = null
  }
})

// Demographics state and helpers
type Demographics = {
  mrn?: string; firstName?: string; middleName?: string; lastName?: string;
  dob?: string; sex?: string; maritalStatus?: string; nationality?: string;
  homeAddress?: string; cellPhone?: string; homePhone?: string; email?: string;
  emergencyName?: string; emergencyRelationship?: string; emergencyPhone?: string;
  consultationLocation?: string; attendingPhysician?: string;
  hospitalName?: string; hospitalAddress?: string;
  reasonForVisit?: string; referringDoctor?: string; primaryCarePhysician?: string;
  currentMedications?: string; medicalHistory?: string;
  symptomsDescription?: string; painScale?: number; affectedBodyParts?: string[];
  consentAgreed?: boolean; patientSignature?: string; signatureDate?: string;
}
const demographics = ref<Demographics | null>(null)
const demoLoadError = ref<string | null>(null)
const demoLoading = ref(false)
const loadDemographics = () => {
  demoLoadError.value = null
  demographics.value = null
  if (!selectedPatient.value) return
  demoLoading.value = true
  const key = `patient_reg_${selectedPatient.value.id}`
  try {
    const raw = localStorage.getItem(key)
    if (raw) {
      const p = JSON.parse(raw)
      demographics.value = { ...p }
    } else {
      // fallback to current registration form draft/completed state
      demographics.value = registrationCompleted.value ? ({ ...registrationForm.value }) : null
    }
    if (!demographics.value) {
      demoLoadError.value = 'Demographics not found for selected patient.'
    }
  } catch (e) {
    console.warn('Failed to load demographics', e)
    demoLoadError.value = 'Unable to load demographics; showing current registration data'
    demographics.value = registrationCompleted.value ? ({ ...registrationForm.value }) : null
  } finally {
    demoLoading.value = false
  }
}
// Refresh demographics when registration completes
watch(registrationCompleted, (val) => { if (val && selectedPatient.value) loadDemographics() })



// Doctors state and helpers
const doctorsLoading = ref(false)
const doctorsLoadError = ref<string | null>(null)
interface DoctorSummary {
  id?: string | number
  email?: string
  full_name?: string
  specialization?: string
  availability?: string
  status?: string
  hospital_name?: string
}
const availableDoctors = ref<DoctorSummary[]>([])
const doctorsCheckedAt = ref<string | null>(null)



const nurseHospital = computed(() => (userProfile.value?.hospital_name || '') || (JSON.parse(localStorage.getItem('user') || '{}').hospital_name || ''))

const filteredAvailableDoctors = computed(() => {
  const currentHospital = nurseHospital.value

  // Safe normalizer: only accepts strings, otherwise returns empty
  const norm = (s: unknown) => (typeof s === 'string' ? s.toLowerCase().trim() : '')

  // Filter strictly by hospital and availability; do not tie to selected patient
  const baseList = (availableDoctors.value || []).filter((d) => {
    const docHosp = norm(d.hospital_name)
    const nurseHosp = norm(currentHospital)
    const hospitalOk = nurseHosp ? (docHosp ? docHosp === nurseHosp : true) : true
    const statusNorm = norm(d.availability || d.status)
    const availOk = statusNorm === 'available' || !d.availability
    return hospitalOk && availOk
  })

  return baseList
})

const doctorsPage = ref(1)
const doctorsPerPage = 10

const doctorTotalPages = computed(() => {
  const total = filteredAvailableDoctors.value.length
  return total > 0 ? Math.ceil(total / doctorsPerPage) : 1
})
const paginatedDoctors = computed(() => {
  const start = (doctorsPage.value - 1) * doctorsPerPage
  return filteredAvailableDoctors.value.slice(start, start + doctorsPerPage)
})
const doctorsStartIndex = computed(() => {
  if (filteredAvailableDoctors.value.length === 0) return 0
  return (doctorsPage.value - 1) * doctorsPerPage + 1
})
const doctorsEndIndex = computed(() => {
  if (filteredAvailableDoctors.value.length === 0) return 0
  const end = doctorsPage.value * doctorsPerPage
  return Math.min(filteredAvailableDoctors.value.length, end)
})

watch(filteredAvailableDoctors, (list) => {
  const maxPage = list.length > 0 ? Math.ceil(list.length / doctorsPerPage) : 1
  if (doctorsPage.value > maxPage) doctorsPage.value = 1
})

function getInitials(name: string): string {
  const parts = String(name).split(' ').filter(Boolean)
  const initials = parts.map((p: string) => p[0]).slice(0, 2).join('')
  return initials || 'U'
}

const getAvailabilityColor = (status: string): string => {
  const s = (status || '').toLowerCase()
  if (s.includes('break')) return 'warning'
  if (s.includes('occupied') || s.includes('busy')) return 'negative'
  if (s.includes('available')) return 'positive'
  return 'primary'
}

const isPriorityPatient = (patient: Patient): boolean => {
  const age =
    typeof patient.age === 'number'
      ? patient.age
      : computeAgeFromIsoDate(typeof patient.date_of_birth === 'string' ? patient.date_of_birth : '')

  if (age !== null && age >= 60) return true

  const priorityRaw = (patient as unknown as { priority_level?: unknown; priority?: unknown }).priority_level
    ?? (patient as unknown as { priority?: unknown }).priority
  return typeof priorityRaw === 'string' ? priorityRaw.trim().length > 0 : false
}

// Safe error message extractor to avoid 'any' casts
function getErrorMessage(e: unknown): string {
  if (e instanceof Error && typeof e.message === 'string') return e.message
  if (typeof e === 'object' && e !== null && 'message' in (e as Record<string, unknown>)) {
    const m = (e as { message?: unknown }).message
    if (typeof m === 'string') return m
  }
  try { return JSON.stringify(e) } catch { return String(e) }
}

let isLoadAvailableDoctorsInProgress = false

async function loadAvailableDoctors(silent?: boolean) {
  if (isLoadAvailableDoctorsInProgress) return
  isLoadAvailableDoctorsInProgress = true

  if (!silent) doctorsLoading.value = true
  doctorsLoadError.value = null
  
  // Validate that nurse has hospital information
  const currentHospital = nurseHospital.value
  if (!currentHospital || currentHospital.trim() === '') {
    doctorsLoadError.value = 'Hospital information missing. Please update your profile with hospital details.'
    doctorsLoading.value = false
    isLoadAvailableDoctorsInProgress = false
    availableDoctors.value = []
    $q.notify({ type: 'warning', message: 'Hospital information missing. Update your profile.', position: 'top' })
    void api.post('/operations/client-log/', {
      level: 'warning',
      message: 'loadAvailableDoctors aborted: missing hospital',
      route: 'NursePatientAssessment',
      context: {}
    }).catch(() => { /* non-blocking */ })
    return
  }
  
  try {
    // New secured endpoint returns only free doctors with timestamp and count
    // NOTE: The axios client already uses the backend base URL, so do not prefix with '/api' here
    const res = await api.get('/operations/availability/doctors/free/', {
      params: {
        include_email: true
        // Backend scopes to nurse's hospital; hospital_id not required here
      },
      timeout: 45000 // Increased timeout to 45s to handle potential network/backend delays
    })

    type ApiDoctor = { id?: number|string; full_name?: string; specialization?: string; email?: string; availability?: string; hospital_name?: string }
    const doctors: ApiDoctor[] = Array.isArray(res.data?.doctors) ? res.data.doctors : []
    const checkedAt = String(res.data?.checked_at || '')

    availableDoctors.value = doctors.map((d) => ({
      id: d.id ?? '',
      full_name: d.full_name || 'Unknown Doctor',
      specialization: d.specialization || 'General',
      availability: d.availability || 'available',
      hospital_name: d.hospital_name || nurseHospital.value || ''
    }))

    // Cache for fallback use with timestamp
    localStorage.setItem('available_doctors', JSON.stringify(availableDoctors.value))
    if (checkedAt) {
      localStorage.setItem('available_doctors_checked_at', checkedAt)
      doctorsCheckedAt.value = checkedAt
    }
    void api.post('/operations/client-log/', {
      level: 'info',
      message: 'loadAvailableDoctors succeeded',
      route: 'NursePatientAssessment',
      context: { count: availableDoctors.value.length, checked_at: checkedAt }
    }).catch(() => { /* non-blocking */ })
  } catch (err) {
    // Handle timeout specifically
    const axiosError = err as { code?: string; message?: string }
    if (axiosError?.code === 'ECONNABORTED' || axiosError?.message?.includes('timeout')) {
         console.warn('Doctor availability check timed out - retrying in next poll')
         // Don't show notification for silent background polls to avoid spamming user
         if (!silent) {
             $q.notify({ type: 'warning', message: 'Doctor availability check timed out. Retrying...', position: 'top' })
         }
    } else {
        console.error('Failed to fetch doctors:', err)
        const msg = getErrorMessage(err)
        doctorsLoadError.value = msg || 'Unable to load doctors from your hospital'
        $q.notify({ type: 'negative', message: 'Failed to load available doctors', position: 'top' })
        void api.post('/operations/client-log/', {
          level: 'error',
          message: 'loadAvailableDoctors failed',
          route: 'NursePatientAssessment',
          context: { error: String(err) }
        }).catch(() => { /* non-blocking */ })
    }
    
    // Try to use cached data as fallback
    try {
      const cached = localStorage.getItem('available_doctors')
      if (cached) {
        availableDoctors.value = JSON.parse(cached) as DoctorSummary[]
        console.log(`Using cached doctors: ${availableDoctors.value.length} available`)
      } else {
        availableDoctors.value = []
      }
      const cachedTs = localStorage.getItem('available_doctors_checked_at')
      doctorsCheckedAt.value = cachedTs || null
    } catch {
      availableDoctors.value = []
    }
  } finally {
    isLoadAvailableDoctorsInProgress = false
    if (!silent) {
      doctorsLoading.value = false
    }
  }
}

// Archive state
const archiveLoading = ref(false)
const lastArchivedId = ref<number | null>(null)
const archiveSuccessDialogOpen = ref(false)

// Send records state
const sendDialogOpen = ref(false)
const sendingRecords = ref(false)
const sendSelectedDoctorId = ref<number | null>(null)
const sendMessage = ref('')
const sendPatientTarget = ref<PatientSummary | null>(null)
const sendPriority = ref<'low' | 'medium' | 'high' | 'urgent'>('medium')
const sendChannels = ref<Array<'websocket' | 'email' | 'sms'>>(['websocket'])

const sendPriorityOptions = [
  { label: 'Low', value: 'low' },
  { label: 'Medium', value: 'medium' },
  { label: 'High', value: 'high' },
  { label: 'Urgent', value: 'urgent' }
]

const sendChannelOptions = [
  { label: 'In-app', value: 'websocket' },
  { label: 'Email', value: 'email' },
  { label: 'SMS', value: 'sms' }
]

const sendDoctorOptions = computed(() => {
  const docs = (filteredAvailableDoctors.value || []) as unknown as Array<{ id?: number; full_name?: string; specialization?: string }>
  return docs
    .filter((d) => typeof d.id === 'number')
    .map((d) => ({
      label: `${d.full_name || 'Doctor'}${d.specialization ? ` — ${d.specialization}` : ''}`,
      value: d.id as number
    }))
})

const physicalStaffOptions = computed(() => {
  const opts: string[] = []
  const nurseName = (userProfile.value?.full_name || '').trim()
  if (nurseName) opts.push(nurseName)
  for (const d of filteredAvailableDoctors.value || []) {
    const name = String(d.full_name || '').trim()
    if (name && !opts.includes(name)) opts.push(name)
  }
  return opts
})

const openPhysicalForm = async () => {
  if (!selectedPatient.value) {
    $q.notify({ type: 'warning', message: 'Select a patient first' })
    return
  }
  const pid = selectedPatient.value.id
  physicalFormModel.value = emptyPhysicalForm()
  const selectedFullName = String(selectedPatient.value.full_name || '').trim()
  const parts = selectedFullName.split(/\s+/).filter(Boolean)
  const firstFromName = parts[0] || ''
  const lastFromName = parts.length > 1 ? (parts.at(-1) ?? '') : ''
  const middleFromName = parts.length > 2 ? parts.slice(1, -1).join(' ') : ''
  const selectedDob = typeof selectedPatient.value.date_of_birth === 'string' ? selectedPatient.value.date_of_birth : ''
  const selectedGender = String(selectedPatient.value.gender || '').trim()
  const selectedAge = typeof selectedPatient.value.age === 'number' ? selectedPatient.value.age : computeAgeFromIsoDate(selectedDob)
  const selectedPatientId = typeof selectedPatient.value.patient_id === 'string' ? selectedPatient.value.patient_id : ''
  try {
    const res = await api.get(`/users/nurse/patient/${pid}/intake/`)
    const data = (res.data?.data ?? {}) as Record<string, unknown>
    const reg = (data.registration_physical ?? {}) as Record<string, unknown>
    const opd = (data.opd_assessment ?? {}) as Record<string, unknown>
    const regBday = typeof reg.birthday === 'string' ? reg.birthday : selectedDob
    const regAgeRaw = reg.age
    const regAgeNum =
      typeof regAgeRaw === 'number'
        ? regAgeRaw
        : typeof regAgeRaw === 'string' && regAgeRaw.trim() && Number.isFinite(Number(regAgeRaw))
          ? Number(regAgeRaw)
          : null
    const derivedAge = computeAgeFromIsoDate(regBday)
    physicalFormModel.value = {
      registration: {
        surname: typeof reg.surname === 'string' ? reg.surname : lastFromName,
        first_name: typeof reg.first_name === 'string' ? reg.first_name : firstFromName,
        middle_name: typeof reg.middle_name === 'string' ? reg.middle_name : middleFromName,
        age: selectedAge ?? regAgeNum ?? derivedAge,
        birthday: regBday,
        sex: typeof reg.sex === 'string' ? reg.sex : selectedGender,
        civil_status: typeof reg.civil_status === 'string' ? reg.civil_status : '',
        address: typeof reg.address === 'string' ? reg.address : '',
        contact_no: typeof reg.contact_no === 'string' ? reg.contact_no : '',
        patient_id:
          typeof reg.patient_id === 'string'
            ? reg.patient_id
            : typeof reg.student_employee_no === 'string'
              ? reg.student_employee_no
              : selectedPatientId,
        department: typeof reg.department === 'string' ? reg.department : '',
        nationality: typeof reg.nationality === 'string' ? reg.nationality : '',
        religion: typeof reg.religion === 'string' ? reg.religion : '',
        emergency_contact: {
          name: typeof (reg.emergency_contact as Record<string, unknown> | undefined)?.name === 'string'
            ? String((reg.emergency_contact as Record<string, unknown>).name)
            : '',
          relationship: typeof (reg.emergency_contact as Record<string, unknown> | undefined)?.relationship === 'string'
            ? String((reg.emergency_contact as Record<string, unknown>).relationship)
            : '',
          contact_no: typeof (reg.emergency_contact as Record<string, unknown> | undefined)?.contact_no === 'string'
            ? String((reg.emergency_contact as Record<string, unknown>).contact_no)
            : ''
        }
      },
      opd_assessment: {
        complaints_pe_findings: typeof opd.complaints_pe_findings === 'string' ? opd.complaints_pe_findings : '',
        vitals: {
          bp: typeof (opd.vitals as Record<string, unknown> | undefined)?.bp === 'string'
            ? String((opd.vitals as Record<string, unknown>).bp)
            : '',
          pr: typeof (opd.vitals as Record<string, unknown> | undefined)?.pr === 'number'
            ? Number((opd.vitals as Record<string, unknown>).pr)
            : null,
          rr: typeof (opd.vitals as Record<string, unknown> | undefined)?.rr === 'number'
            ? Number((opd.vitals as Record<string, unknown>).rr)
            : null,
          temp: typeof (opd.vitals as Record<string, unknown> | undefined)?.temp === 'number'
            ? Number((opd.vitals as Record<string, unknown>).temp)
            : null
        },
        physical_exam: {
          heent: typeof (opd.physical_exam as Record<string, unknown> | undefined)?.heent === 'string'
            ? String((opd.physical_exam as Record<string, unknown>).heent)
            : '',
          heart: typeof (opd.physical_exam as Record<string, unknown> | undefined)?.heart === 'string'
            ? String((opd.physical_exam as Record<string, unknown>).heart)
            : '',
          lungs: typeof (opd.physical_exam as Record<string, unknown> | undefined)?.lungs === 'string'
            ? String((opd.physical_exam as Record<string, unknown>).lungs)
            : '',
          abdomen_extremities: typeof (opd.physical_exam as Record<string, unknown> | undefined)?.abdomen_extremities === 'string'
            ? String((opd.physical_exam as Record<string, unknown>).abdomen_extremities)
            : ''
        },
        labs: (typeof opd.labs === 'object' && opd.labs !== null ? (opd.labs as PhysicalFormModel['opd_assessment']['labs']) : emptyPhysicalForm().opd_assessment.labs),
        date: typeof opd.date === 'string' ? opd.date : '',
        diagnosis_treatment_remarks: typeof opd.diagnosis_treatment_remarks === 'string' ? opd.diagnosis_treatment_remarks : '',
        staff: typeof opd.staff === 'string' ? opd.staff : ''
      }
    }
  } catch {
    physicalFormModel.value = emptyPhysicalForm()
  }

  if (!physicalFormModel.value.registration.surname) physicalFormModel.value.registration.surname = lastFromName
  if (!physicalFormModel.value.registration.first_name) physicalFormModel.value.registration.first_name = firstFromName
  if (!physicalFormModel.value.registration.middle_name) physicalFormModel.value.registration.middle_name = middleFromName
  if (physicalFormModel.value.registration.age === null && selectedAge !== null) physicalFormModel.value.registration.age = selectedAge
  if (!physicalFormModel.value.registration.birthday && selectedDob) physicalFormModel.value.registration.birthday = selectedDob
  if (!physicalFormModel.value.registration.sex && selectedGender) physicalFormModel.value.registration.sex = selectedGender
  if (!physicalFormModel.value.registration.patient_id && selectedPatientId) physicalFormModel.value.registration.patient_id = selectedPatientId

  if (!physicalFormModel.value.opd_assessment.date) {
    physicalFormModel.value.opd_assessment.date = physicalFormRevisionDate.value
  }
  if (!physicalFormModel.value.opd_assessment.staff) {
    physicalFormModel.value.opd_assessment.staff = (userProfile.value?.full_name || '').trim()
  }
  if (!physicalFormModel.value.registration.department) {
    physicalFormModel.value.registration.department = (userProfile.value?.department || 'OPD').trim()
  }
  showPhysicalFormDialog.value = true
  void loadAvailableDoctors(true)
}

const savePhysicalForm = async () => {
  if (!selectedPatient.value) {
    $q.notify({ type: 'negative', message: 'Select a patient first' })
    return
  }
  const regValidation = physicalFormRef.value?.validateRegistration()
  if (regValidation && !regValidation.valid) {
    $q.notify({ type: 'warning', message: regValidation.message || 'Please complete required registration fields' })
    return
  }
  const assessValidation = physicalFormRef.value?.validateAssessment()
  if (assessValidation && !assessValidation.valid) {
    $q.notify({ type: 'warning', message: assessValidation.message || 'Please complete required assessment fields' })
    return
  }

  savingPhysicalForm.value = true
  try {
    const pid = selectedPatient.value.id
    const existing = await api
      .get(`/users/nurse/patient/${pid}/intake/`)
      .then((res) => (res.data?.data ?? {}) as Record<string, unknown>)
      .catch(() => ({}))
    const existingSafe = sanitizeExistingIntake(existing)

    const intakePayload = {
      ...existingSafe,
      registration_physical: physicalFormModel.value.registration,
      opd_assessment: physicalFormModel.value.opd_assessment
    }

    await api.put(`/users/nurse/patient/${pid}/intake/`, intakePayload)
    showPhysicalFormDialog.value = false
    $q.notify({ type: 'positive', message: 'Registration & assessment form saved' })
  } catch (e) {
    console.error('Failed to save physical form:', e)
    $q.notify({ type: 'negative', message: `Failed to save form. ${extractApiErrorMessage(e)}`, position: 'top' })
  } finally {
    savingPhysicalForm.value = false
  }
}

function openSendDialog(patient: PatientSummary) {
  sendPatientTarget.value = patient
  sendSelectedDoctorId.value = null
  sendMessage.value = ''
  sendPriority.value = 'medium'
  sendChannels.value = ['websocket']
  sendDialogOpen.value = true
  void loadAvailableDoctors(true)
}

async function sendPatientRecords() {
  if (!sendPatientTarget.value) {
    $q.notify({ type: 'negative', message: 'Select a patient first' })
    return
  }
  if (!sendSelectedDoctorId.value) {
    $q.notify({ type: 'warning', message: 'Please select a doctor' })
    return
  }
  sendingRecords.value = true
  try {
    await api.post('/operations/nurse/send-records/', {
      patient_id: sendPatientTarget.value.id,
      doctor_id: sendSelectedDoctorId.value,
      message: sendMessage.value,
      priority: sendPriority.value,
      channels: sendChannels.value
    })
    $q.notify({ type: 'positive', message: 'Patient records sent to doctor' })
    sendDialogOpen.value = false
    await archivePatient(sendPatientTarget.value)
  } catch (e) {
    console.error('Send patient records failed', e)
    $q.notify({ type: 'negative', message: 'Failed to send records. Please try again.' })
  } finally {
    sendingRecords.value = false
  }
}

 
interface PatientSummary {
  id: number | string;
  full_name?: string | null;
  profile_picture?: string | null;
  age?: number | null;
  gender?: string | null;
  blood_type?: string | null;
  medical_condition?: string | null;
  email?: string | null;
  hospital?: string | null;
  insurance_provider?: string | null;
}

async function archivePatient(patient: PatientSummary) {
  archiveLoading.value = true
  try {
    const rawPatient = patient as unknown as { user_id?: number | string; id: number | string; medical_condition?: string | null };
    const patientUserIdNum = Number(rawPatient.user_id ?? rawPatient.id);
    if (!Number.isFinite(patientUserIdNum)) {
      throw new Error('Invalid patient user ID');
    }
    const patientProfileIdNum = Number(rawPatient.id ?? rawPatient.user_id);
    if (!Number.isFinite(patientProfileIdNum)) {
      throw new Error('Invalid patient profile ID');
    }

    // Load demographics from localStorage for the specific patient being archived
    const regKey = `patient_reg_${patientProfileIdNum}`;
    const rawDemo = localStorage.getItem(regKey);
    const demographicsData = rawDemo ? JSON.parse(rawDemo) : null;

    // Build assessment data
    const assessmentData: Record<string, unknown> = {
      demographics: demographicsData,
      actor: 'nurse',
      nurse_name: userProfile.value.full_name,
      message: ''
    };

    const payload: Record<string, unknown> = {
      patient_id: patientUserIdNum,
      assessment_type: 'full_record',
      assessment_data: assessmentData,
      full_record: true,
      archival_reason: '',
      medical_condition: rawPatient.medical_condition || '',
      hospital_name: userProfile.value.hospital_name || ''
    };

    const res = await api.post('/operations/archives/create/', payload);
    const newArchiveId = res.data?.id
    if (newArchiveId) {
      lastArchivedId.value = newArchiveId
      archiveSuccessDialogOpen.value = true
    }

    // Remove from active list immediately
    patients.value = patients.value.filter(p => String(p.id ?? p.user_id) !== String(rawPatient.id ?? rawPatient.user_id))
    
    // Clear from localStorage if it matches current_serving_patient
    try {
      const currentServing = localStorage.getItem('current_serving_patient');
      if (currentServing) {
        const cs = JSON.parse(currentServing);
        const csId = cs.id ?? cs.user_id;
        const archivedId = rawPatient.id ?? rawPatient.user_id;
        if (String(csId) === String(archivedId)) {
          localStorage.removeItem('current_serving_patient');
        }
      }
    } catch (e) {
      console.warn('Failed to clear current serving patient from storage', e);
    }

    $q.notify({ type: 'positive', message: 'Patient archived and removed from list' });

  } catch (err: unknown) {
    console.error('Archive create failed', err);
    let msg = 'Failed to archive record';
    if (typeof err === 'object' && err !== null) {
      const e = err as { response?: { data?: { error?: unknown } }, message?: unknown };
      const apiMsg = e.response?.data?.error;
      if (typeof apiMsg === 'string' && apiMsg.trim()) {
        msg = apiMsg;
      } else if (typeof e.message === 'string' && e.message.trim()) {
        msg = e.message;
      }
    } else if (typeof err === 'string' && err.trim()) {
      msg = err;
    }
    $q.notify({ type: 'negative', message: msg });
  } finally {
    archiveLoading.value = false;
  }
}

async function downloadArchivePdf() {
  if (!lastArchivedId.value) return
  try {
    const res = await api.get(`/operations/archives/${lastArchivedId.value}/export/`, {
      responseType: 'blob'
    })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `archive_${lastArchivedId.value}.pdf`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    $q.notify({ type: 'positive', message: 'PDF Download started' })
  } catch (err) {
    console.error('PDF download failed', err)
    $q.notify({ type: 'negative', message: 'Failed to download PDF' })
  }
}

// Removed developer-only dummy assignment helper; switching to real API-driven data



onMounted(() => {
  console.log('🚀 NursePatientAssessment component mounted');
  void fetchUserProfile();
  void loadPatients();
  void loadArchivedPatients();
  void loadAvailableDoctors();
  setupQueueWebSocket()
});

onUnmounted(() => {
  if (queueWebSocket.value) {
    try { queueWebSocket.value.close() } catch { /* ignore */ }
    queueWebSocket.value = null
  }
})
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
  background: #ffffff;
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
  background: #ffffff;
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
  background: linear-gradient(
    90deg,
    #286660 0%,
    #6ca299 50%,
    #b8d2ce 100%
  );
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

.view-tabs {
  margin-left: 12px;
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

/* removed greeting icon for cleaner header */

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

/* Patient List */
.patients-list {
  max-height: 460px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
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

.archived-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.archived-actions .q-btn {
  border-radius: 10px;
  border: 1px solid rgba(15, 23, 42, 0.14);
}

.assessed-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.assessed-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: #ffffff;
  transition: background-color 0.15s ease, border-color 0.15s ease;
}

.assessed-row:hover {
  background: rgba(13, 148, 136, 0.05);
  border-color: rgba(13, 148, 136, 0.18);
}

.assessed-info {
  flex: 1;
  min-width: 0;
}

.assessed-name {
  font-weight: 800;
  color: rgba(15, 23, 42, 0.92);
  font-size: 12px;
}

.assessed-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.assessed-actions .q-btn {
  border-radius: 10px;
  border: 1px solid rgba(15, 23, 42, 0.14);
}

.doctors-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.doctor-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: #ffffff;
  transition: background-color 0.15s ease, border-color 0.15s ease;
}

.doctor-row:hover {
  background: rgba(13, 148, 136, 0.05);
  border-color: rgba(13, 148, 136, 0.18);
}

.doctor-info {
  flex: 1;
  min-width: 0;
}

.doctor-name {
  font-weight: 800;
  color: rgba(15, 23, 42, 0.92);
  font-size: 12px;
}

.doctor-contact {
  font-size: 12px;
  color: rgba(15, 23, 42, 0.65);
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

/* Selected patient highlight */
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
}

.patient-actions .q-btn {
  width: 28px;
  height: 28px;
  border-radius: 7px;
  border: 1px solid rgba(15, 23, 42, 0.10);
  background: rgba(255, 255, 255, 0.9);
}

.patient-list-card :deep(.q-banner) {
  border-radius: 12px;
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

/* Loading and Empty States */
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
}

/* Pain Assessment Modern Styles */
.pain-assessment-body {
  padding: 24px;
}

.pain-display-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.pain-emoji-large {
  font-size: 84px;
  line-height: 1;
  filter: drop-shadow(0 4px 8px rgba(0,0,0,0.1));
  transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.pain-emoji-large:hover {
  transform: scale(1.1);
}

.pain-label-container {
  text-align: center;
}

.pain-slider-wrapper {
  background: #f8f9fa;
  padding: 32px 24px 16px;
  border-radius: 16px;
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);
}

.modern-pain-slider {
  height: 40px;
}

.pain-scale-indicators {
  padding: 0 4px;
}

.pain-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 4px;
  transition: all 0.3s ease;
}

.pain-dot.active {
  transform: scale(1.5);
  box-shadow: 0 0 8px currentColor;
}

.status-mild { color: var(--q-positive); }
.status-moderate { color: var(--q-warning); }
.status-severe { color: var(--q-negative); }

.pain-notes-input {
  background: white;
}

.pain-history-scroll {
  border: 1px solid #eee;
  border-radius: 12px;
  background: #fafafa;
}

.pain-history-list {
  padding: 8px;
}

.pain-history-item {
  border-radius: 8px;
  margin-bottom: 4px;
  transition: background 0.2s;
}

.pain-history-item:hover {
  background: #f0f0f0;
}

.pain-emoji-small {
  font-size: 24px;
  background: white;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.pain-history-notes {
  font-style: italic;
  white-space: pre-wrap;
  margin-top: 4px;
  color: #555;
  background: #fff;
  padding: 4px 8px;
  border-radius: 4px;
  border-left: 3px solid #ddd;
}

.empty-history {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
}

/* Transitions */
.scale-enter-active,
.scale-leave-active {
  transition: all 0.3s ease;
}

.scale-enter-from,
.scale-leave-to {
  opacity: 0;
  transform: scale(0.8);
}

@media (max-width: 768px) {
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

/* Avatar Initials Styles */
.avatar-initials {
  font-size: 18px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
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
.registration-form { padding-left: 2rem; padding-right: 2rem; }
.registration-form .q-field { margin-bottom: 14px; }

/* Registration dialog visual containment */
.registration-dialog-card {
  max-height: 80vh;
  overflow-y: auto;
  background: #ffffff;
  margin-left: 2rem;
  margin-right: 2rem;
}

/* Stepper tabs sizing for clarity */
.q-stepper--horizontal .q-stepper__tab { padding: 6px 8px; }

/* Slightly darken backdrop to avoid background card bleed-through */
.q-dialog__backdrop {
  background: rgba(0, 0, 0, 0.35) !important;
}

/* Responsive tweaks */
@media (max-width: 768px) {
  .registration-dialog-card { margin-left: 1rem; margin-right: 1rem; }
  .registration-form { padding-left: 1rem; padding-right: 1rem; }
  .registration-form .q-field { margin-bottom: 12px; }
}

@media (min-width: 1280px) {
  .registration-dialog-card { margin-left: 3rem; margin-right: 3rem; }
  .registration-form { padding-left: 3rem; padding-right: 3rem; }
}
.full-width-tabs { width: 100%; }
.form-dialog-container { z-index: 2050; padding: 16px; }
.form-dialog-card {
  width: min(1040px, 94vw);
  max-height: min(88vh, 980px);
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(20, 32, 53, 0.08);
  border-radius: 18px;
  overflow: hidden;
  box-shadow:
    0 24px 64px rgba(16, 24, 40, 0.18),
    0 2px 10px rgba(16, 24, 40, 0.08);
}
.modern-modal { backdrop-filter: blur(10px); }
.form-dialog-card .q-card-section { padding: 18px 20px; }
.form-dialog-header {
  position: sticky;
  top: 0;
  z-index: 2;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(255, 255, 255, 0.86));
}
.form-dialog-titlebar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.title-block { min-width: 0; }
.title-block .text-subtitle1 {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.modal-close-btn {
  background: rgba(16, 24, 40, 0.06);
}
.modal-close-btn:hover {
  background: rgba(16, 24, 40, 0.1);
}
.form-dialog-card .row { align-items: flex-start; }
.form-dialog-card :deep(.q-field) { margin-bottom: 12px; }
.form-body { max-height: 68vh; overflow-y: auto; padding-top: 16px; }
.psych-form-container { font-size: 14px; }
.psych-toolbar { min-height: 42px; }
.psych-form-container :deep(.q-field:not(.q-textarea) .q-field__control) {
  min-height: 42px;
}
.psych-form-container :deep(.q-field:not(.q-textarea).q-field--dense .q-field__control) {
  min-height: 40px;
}
.psych-form-container :deep(.q-field:not(.q-textarea) .q-field__native),
.psych-form-container :deep(.q-field:not(.q-textarea) .q-field__input) {
  min-height: 24px;
  line-height: 24px;
}
.psych-form-container :deep(.q-field:not(.q-textarea) .q-field__append),
.psych-form-container :deep(.q-field:not(.q-textarea) .q-field__prepend) {
  height: 40px;
  align-items: center;
}
.psych-form-container :deep(.q-checkbox) {
  min-height: 40px;
  display: flex;
  align-items: center;
}
.psych-grid {
  display: grid;
  gap: 12px;
}
.psych-grid-2 {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.psych-grid-3 {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.psych-grid-4 {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}
@media (max-width: 1024px) {
  .psych-grid-3 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .psych-grid-4 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 600px) {
  .psych-grid-2,
  .psych-grid-3,
  .psych-grid-4 { grid-template-columns: 1fr; }
  .psych-grid { gap: 10px; }
}
@media (max-width: 768px) {
  .form-dialog-container { padding: 10px; }
  .form-dialog-card { width: 96vw; border-radius: 14px; max-height: 92vh; }
  .form-dialog-card .q-card-section { padding: 16px; }
}
@media (min-width: 1280px) { .form-dialog-card { max-width: 1100px; margin-left: 24px; margin-right: 24px; } }
.forms-card { background: #ffffff; }

/* Section spacing for consistent vertical gaps */
.section-spacing {
  margin-bottom: 20px;
}

/* Responsive section spacing */
@media (max-width: 768px) {
  .section-spacing {
    margin-bottom: 16px;
  }
}

@media (min-width: 1280px) {
  .section-spacing {
    margin-bottom: 24px;
  }
}
</style>
