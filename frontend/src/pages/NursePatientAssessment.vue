<template>
  <q-layout view="hHh Lpr fFf">
    <!-- Standardized Header Component -->
    <NurseHeader @toggle-drawer="rightDrawerOpen = !rightDrawerOpen" />

    <!-- Standardized Sidebar Component -->
    <NurseSidebar v-model="rightDrawerOpen" active-route="patients" />

    <q-page-container class="page-container-with-fixed-header role-body-bg">
      <!-- Main Content -->
      <div class="patient-management-content">
        <!-- Header Section -->
        <div class="greeting-section">
          <q-card class="greeting-card">
            <q-card-section class="greeting-content">
              <div class="greeting-text">
                <h4 class="greeting-title">Patient Management</h4>
                <p class="greeting-subtitle">Manage your patients and their medical records</p>
              </div>
            </q-card-section>
          </q-card>
        </div>
        
        <q-dialog
          v-model="formDialogOpen"
          transition-show="scale"
          transition-hide="scale"
          :persistent="false"
          content-class="form-dialog-container"
        >
          <q-card class="form-dialog-card">
            <q-card-section class="card-header">
              <div class="row items-center justify-between">
                <div class="text-h6">{{ currentFormTitle }}</div>
                <q-btn flat round dense icon="close" aria-label="Close OPD Form modal" @click="formDialogOpen = false" />
              </div>
            </q-card-section>
            <q-separator />
            <q-card-section class="card-content">
              <q-inner-loading :showing="demoLoading">
                <q-spinner color="primary" />
              </q-inner-loading>

              <!-- Patient Demographics (Standard Upper Section) -->
              <div v-if="demographics" class="q-gutter-md q-mb-md">
                <div class="text-subtitle1 text-bold">Patient Demographics</div>
                <div class="row q-col-gutter-md">
                  <div class="col-12 col-sm-6 col-md-3"><q-input :model-value="demographics.mrn" label="MRN" outlined dense readonly/></div>
                  <div class="col-12 col-sm-6 col-md-3"><q-input :model-value="demographicFullName" label="Name" outlined dense readonly/></div>
                  <div class="col-12 col-sm-6 col-md-3"><q-input :model-value="formattedDOB" label="Date of Birth" outlined dense readonly/></div>
                  <div class="col-12 col-sm-6 col-md-3"><q-input :model-value="String(demographicAge)" label="Age" outlined dense readonly/></div>
                  <div class="col-12 col-sm-6 col-md-3"><q-input :model-value="demographics.sex" label="Sex/Gender" outlined dense readonly/></div>
                  <div class="col-12 col-sm-6 col-md-3"><q-input :model-value="demographics.homeAddress" label="Home Address" outlined dense readonly/></div>
                  <div class="col-12 col-sm-6 col-md-3"><q-input :model-value="demographics.cellPhone" label="Cell Phone" outlined dense readonly/></div>
                  <div class="col-12 col-sm-6 col-md-3"><q-input :model-value="demographics.email" label="Email" outlined dense readonly/></div>
                  <div class="col-12 col-sm-6 col-md-3"><q-input :model-value="demographics.emergencyName" label="Emergency Contact" outlined dense readonly/></div>
                  <div class="col-12 col-sm-6 col-md-3"><q-input :model-value="demographics.emergencyPhone" label="Emergency Phone" outlined dense readonly/></div>
                </div>
                <div v-if="demoLoadError" class="text-negative text-caption">{{ demoLoadError }}</div>
              </div>

              <!-- Removed inline OPD form selector; modal reflects patient list selection -->
              <q-banner dense class="q-mb-sm" icon="assignment">
                {{ currentFormTitle }}
              </q-banner>
            </q-card-section>
          </q-card>
        </q-dialog>

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
              <div class="text-subtitle1 text-bold q-mb-sm">Patient Record</div>
              <div v-if="selectedPatientDoc" class="q-gutter-sm">
                <div><strong>Name:</strong> {{ selectedPatientDoc.full_name || '—' }}</div>
                <div><strong>ID:</strong> {{ selectedPatientDoc.id }}</div>
                <div><strong>Age:</strong> {{ selectedPatientDoc.age || '—' }}</div>
                <div><strong>Gender:</strong> {{ selectedPatientDoc.gender || '—' }}</div>
                <div><strong>Blood Type:</strong> {{ selectedPatientDoc.blood_type || '—' }}</div>
                <div><strong>Condition:</strong> {{ selectedPatientDoc.medical_condition || '—' }}</div>
                <div><strong>Email:</strong> {{ selectedPatientDoc.email || '—' }}</div>
                <div><strong>Hospital:</strong> {{ selectedPatientDoc.hospital || userProfile.hospital_name || '—' }}</div>
                <div><strong>Insurance:</strong> {{ selectedPatientDoc.insurance_provider || '—' }}</div>
              </div>
              <div v-else>
                <q-banner dense class="q-mt-sm" icon="info">No patient selected</q-banner>
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
                    <q-select v-model="selectedForm" :options="opdFormOptions" outlined dense label="OPD Forms" emit-value map-options :disable="!selectedPatient" aria-label="OPD Forms"/>
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
                        Age: {{ patient.age || 'N/A' }} | {{ patient.gender || 'N/A' }} |
                        {{ patient.blood_type || 'N/A' }}
                      </p>
                      <p class="patient-condition">
                        {{ patient.medical_condition || 'No condition specified' }}
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
                        aria-label="Send patient records"
                        flat
                        round
                        icon="send"
                        color="positive"
                        size="sm"
                        @click.stop="sendPatientRecords(patient)"
                      >
                        <q-tooltip>Send</q-tooltip>
                      </q-btn>
                      <q-btn
                        aria-label="Archive patient"
                        flat
                        round
                        icon="archive"
                        color="warning"
                        size="sm"
                        @click.stop="archivePatientInline(patient)"
                      >
                        <q-tooltip>Archive</q-tooltip>
                      </q-btn>
                    </div>
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
                    <div class="stat-number">{{ patients.length }}</div>
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
                <h5 class="card-title">List of Available Doctors</h5>
              </q-card-section>
              <q-card-section class="card-content">
                <q-banner v-if="doctorsLoadError" dense class="q-mb-sm" icon="warning" inline-actions>
                  <span class="text-negative">{{ doctorsLoadError }}</span>
                  <q-btn flat color="primary" icon="refresh" label="Retry" @click="() => { void loadAvailableDoctors() }"/>
                </q-banner>
                <div v-if="doctorsLoading" class="loading-section">
                  <q-spinner color="primary" size="2em" />
                  <p class="loading-text">Loading doctors...</p>
                </div>
                <div v-else-if="filteredAvailableDoctors.length === 0" class="empty-section">
                  <q-icon name="medical_services" size="48px" color="grey-5" />
                  <p class="empty-text">No available doctors</p>
                </div>
                <div v-else class="doctors-list">
                  <div v-for="(doc, idx) in filteredAvailableDoctors" :key="String(doc.id ?? doc.email ?? doc.full_name ?? idx)" class="doctor-row">
                    <div class="doctor-avatar">
                      <q-avatar size="40px" color="teal-8" text-color="white">
                        {{ getInitials(doc.full_name || '') }}
                      </q-avatar>
                    </div>
                    <div class="doctor-info">
                      <div class="doctor-name">{{ doc.full_name }}</div>
                      <div class="doctor-details">Specialization: {{ doc.specialization || '—' }} | Availability: {{ doc.availability ?? doc.status ?? '—' }}</div>
                    </div>
                  </div>
                </div>
              </q-card-section>
            </q-card>

          </div>
        </div>


      <!-- Registration / Demographics Dialog -->
      <q-dialog v-model="showRegistrationDialog" persistent maximized transition-show="slide-up" transition-hide="slide-down">
        <q-card class="registration-dialog-card">
          <q-toolbar class="bg-primary text-white">
            <q-btn flat round dense icon="close" v-close-popup aria-label="Close Registration" />
            <q-toolbar-title>Patient Registration & Assessment</q-toolbar-title>
            <q-btn flat label="Save Draft" @click="saveRegistrationDraft" aria-label="Save Draft" />
            <q-btn flat label="Save & Submit" @click="saveRegistration" aria-label="Save and Submit" />
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
                  <div class="col-12 col-md-6">
                    <q-input v-model="registrationForm.hospitalPhone" label="Hospital Phone *" outlined dense :rules="[v=>!!v||'Required']" aria-label="Hospital Phone"/>
                  </div>
                  <div class="col-12 col-md-6">
                    <q-input v-model="registrationForm.hospitalEmail" label="Hospital Email *" outlined dense :rules="[v=>!!v||'Required', v => /.+@.+\..+/.test(v) || 'Invalid email']" aria-label="Hospital Email"/>
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

              <!-- Step 4: Medical Information -->
              <q-step :name="4" title="Medical Information" icon="medical_services" :done="registrationStep > 4">
                <div class="text-subtitle2 q-mb-sm">Context</div>
                <div class="row q-col-gutter-md q-mb-md">
                   <div class="col-12">
                     <q-input v-model="registrationForm.reasonForVisit" label="Reason for Visit *" outlined dense :rules="[v=>!!v||'Required']" aria-label="Reason for Visit"/>
                   </div>
                   <div class="col-12">
                     <div class="text-subtitle2 q-mb-sm">Where did you consult a doctor? *</div>
                     <q-option-group
                       v-model="registrationForm.consultationLocation"
                       :options="[
                         { label: 'In the hospital', value: 'In the hospital' },
                         { label: 'Outside the hospital', value: 'Outside the hospital' }
                       ]"
                       color="primary"
                       inline
                     />
                   </div>
                   <div class="col-12 col-md-6" v-if="registrationForm.consultationLocation">
                     <q-input
                       v-model="registrationForm.attendingPhysician"
                       label="Name of Attending Physician *"
                       outlined
                       dense
                       :rules="[
                         v => !!v || 'Required',
                         v => /^[A-Za-z\s]+$/.test(v) || 'Only letters and spaces allowed'
                       ]"
                       aria-label="Name of Attending Physician"
                     />
                   </div>
                   <div class="col-12 col-md-6">
                      <q-input v-model="registrationForm.referringDoctor" label="Referring Doctor" outlined dense aria-label="Referring Doctor"/>
                   </div>
                   <div class="col-12 col-md-6">
                      <q-input v-model="registrationForm.primaryCarePhysician" label="Primary Care Physician" outlined dense aria-label="Primary Care Physician"/>
                   </div>
                </div>

                <div class="text-subtitle2 q-mb-sm">History</div>
                <div class="row q-col-gutter-md">
                   <div class="col-12">
                     <q-select v-model="registrationForm.knownAllergies" :options="allergyOptions" multiple use-input use-chips new-value-mode="add-unique" label="Known Allergies" outlined dense aria-label="Allergies"/>
                   </div>
                   <div class="col-12">
                      <q-select v-model="registrationForm.currentMedications" multiple use-input use-chips new-value-mode="add-unique" label="Current Medications" outlined dense aria-label="Current Medications"/>
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
                  <q-btn color="positive" label="Finish & Submit" @click="saveRegistration" />
                  <q-btn flat @click="prevStep" color="primary" label="Back" class="q-ml-sm" />
                </q-stepper-navigation>
              </q-step>
            </q-stepper>
          </q-card-section>
        </q-card>
      </q-dialog>
      </div>
    </q-page-container>

    <!-- Send Records Dialog -->
    <q-dialog v-model="showSendDialog" persistent content-class="form-dialog-container">
      <q-card class="form-dialog-card">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">Send Patient Records</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup aria-label="Close" />
        </q-card-section>
        <q-separator />
        <q-card-section>
          <q-inner-loading :showing="sendLoading">
            <q-spinner color="primary" size="32px" />
          </q-inner-loading>
          <q-select
            v-model="sendForm.doctorId"
            :options="doctorOptions"
            label="Select Doctor"
            outlined
            dense
            emit-value
            map-options
            aria-label="Select doctor to send to"
          />
          <q-input
            v-model="sendForm.message"
            type="textarea"
            label="Message (optional)"
            outlined
            dense
            autogrow
            aria-label="Message to include with records"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup aria-label="Cancel" />
          <q-btn color="secondary" label="Archive" :loading="sendLoading" @click="archiveCurrentRecord" aria-label="Archive record" />
          <q-btn color="primary" label="Send" :loading="sendLoading" @click="confirmSend" aria-label="Confirm send" />
        </q-card-actions>
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
  </q-layout>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue';
import { useQuasar } from 'quasar';
import { api } from 'boot/axios';
import NurseHeader from '../components/NurseHeader.vue';
import NurseSidebar from '../components/NurseSidebar.vue';

// Types
interface Patient {
  id: number;
  user_id: number;
  full_name: string;
  email: string;
  age: number | null;
  gender: string;
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
}

// Reactive data
const $q = useQuasar();
const rightDrawerOpen = ref(false);
const loading = ref(false);
const searchText = ref('');
const sortKey = ref<'full_name' | 'age' | 'gender'>('full_name');
const sortOptions = [
  { label: 'Name', value: 'full_name' },
  { label: 'Age', value: 'age' },
  { label: 'Gender', value: 'gender' },
];

interface FormOption {
  label: string;
  value: string;
  roles: string[];
  disabled?: boolean;
}

// Base form options with role permissions
// Intentional empty array: Form options removed as requested, ready for future implementation.
const allFormOptions: FormOption[] = [];

// Computed property for filtered form options based on user role and verification
const opdFormOptions = computed(() => {
  const userRole = userProfile.value.role;
  const isVerified = userProfile.value.verification_status === 'approved';
  
  // If user is not verified, only show the select placeholder
  if (!isVerified) {
    return [
      {label: 'Select Form Type', value: ''},
      {label: 'Verification Required', value: '', disabled: true}
    ];
  }
  
  // Filter forms based on user role
  return allFormOptions
    .filter(option => option.roles.includes(userRole))
    .map(option => ({
      label: option.label,
      value: option.value,
      disable: option.value !== '' && !option.roles.includes(userRole)
    }));
});
const sortOrder = ref<'asc' | 'desc'>('asc');
const orderOptions = [
  { label: 'Ascending', value: 'asc' },
  { label: 'Descending', value: 'desc' },
];
const patients = ref<Patient[]>([]);
const selectedPatient = ref<Patient | null>(null);
const showNotifications = ref(false);

// User profile data
const userProfile = ref<{
  full_name: string;
  specialization?: string;
  role: string;
  profile_picture: string | null;
  verification_status: string;
  hospital_name?: string;
  hospital_address?: string;
}>({
  full_name: '',
  specialization: '',
  role: '',
  profile_picture: null,
  verification_status: '',
  hospital_name: '',
  hospital_address: '',
});

// Document view dialog state
const showDocumentView = ref(false)
const selectedPatientDoc = ref<Patient | null>(null)
const department = computed(() => (userProfile.value?.specialization || '').trim() || 'Nursing')

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
  list = [...list].sort((a, b) => {
    const av = (key === 'age' ? (a.age ?? 0) : (a[key] ?? '')).toString().toLowerCase();
    const bv = (key === 'age' ? (b.age ?? 0) : (b[key] ?? '')).toString().toLowerCase();
    if (av < bv) return -1 * dir;
    if (av > bv) return 1 * dir;
    return 0;
  });

  return list;
});

const activePatientsCount = computed(
  () => patients.value.filter((p) => p.discharge_date === null || p.discharge_date === '').length,
);

// Methods
const loadPatients = async () => {
  loading.value = true;
  try {
    const response = await api.get('/users/nurse/patients/');
    if (response.data.success) {
      // Exclude any dummy patients used for analytics/demo data
      patients.value = (response.data.patients || []).filter(
        (p: Patient | Record<string, unknown>) => !(p as Patient).is_dummy,
      ) as Patient[];
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
  loadDemographics();
  showDocumentView.value = true;
  $q.notify({ type: 'info', message: `Viewing record for ${patient.full_name}`, position: 'top' });
};

// Prefill selection from the latest "Call Next Patient" action
const prefillFromCurrentServing = () => {
  try {
    const raw = localStorage.getItem('current_serving_patient');
    if (!raw) return;
    const cp = JSON.parse(raw);
    // Normalize to Patient type shape used by this page
    const candidate: Patient = {
      id: cp.id ?? cp.user_id ?? 0,
      user_id: cp.user_id ?? cp.id ?? 0,
      full_name: String(cp.full_name || cp.name || ''),
      email: String(cp.email || ''),
      age: typeof cp.age === 'number' ? cp.age : null,
      gender: String(cp.gender || ''),
      blood_type: String(cp.blood_type || ''),
      medical_condition: String(cp.medical_condition || ''),
      hospital: String(cp.hospital || ''),
      insurance_provider: String(cp.insurance_provider || ''),
      billing_amount: cp.billing_amount ?? null,
      room_number: String(cp.room_number || ''),
      admission_type: String(cp.admission_type || ''),
      date_of_admission: cp.date_of_admission || null,
      discharge_date: cp.discharge_date || null,
      medication: String(cp.medication || ''),
      test_results: String(cp.test_results || ''),
      is_dummy: false,
      assigned_doctor: cp.assigned_doctor || null
    } as Patient;

    // If not already in the list, append for immediate visibility
    const exists = patients.value.some((p) => p.user_id === candidate.user_id || p.id === candidate.id);
    if (!exists) {
      patients.value.unshift(candidate);
    }
    // Select in UI for quick access
    selectedPatient.value = candidate;
    // Persist current serving patient across reloads - do not remove
    // localStorage.removeItem('current_serving_patient');
    $q.notify({ type: 'info', message: `Forwarded ${candidate.full_name} to Patient Management`, position: 'top' });
  } catch (e) {
    console.warn('Failed to prefill current serving patient', e);
  }
};

const editPatient = (patient: Patient) => {
  selectedPatient.value = patient;
  openRegistration();
};

const fetchUserProfile = async () => {
  try {
    const response = await api.get('/users/profile/');
    const userData = response.data.user;

    userProfile.value = {
      full_name: userData.full_name,
      specialization: userData.nurse_profile?.specialization,
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

// Notification functions
const loadNotifications = async (): Promise<void> => {
  try {
    console.log('📬 Loading nurse notifications...');

    const response = await api.get('/operations/notifications/');
    notifications.value = response.data || [];

    console.log('✅ Nurse notifications loaded:', notifications.value.length);
  } catch (error: unknown) {
    console.error('❌ Error loading notifications:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to load notifications',
    });
  }
};

const handleNotificationClick = (notification: Notification): void => {
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
    notifications.value.forEach((notification) => {
      notification.is_read = true;
    });

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

// Registration / Demographics gating
const showRegistrationDialog = ref(false)
const registrationCompleted = ref(false)
const registrationForm = ref({
  // Header and Administrative Data
  hospitalName: '',
  departmentName: 'OPD',
  hospitalAddress: '',
  hospitalPhone: '',
  hospitalEmail: '',
  mrn: '',
  dateOfRegistration: '',
  registeredBy: '',
  // Patient Identification Data
  firstName: '',
  middleName: '',
  lastName: '',
  dob: '',
  age: '' as string | number,
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
  currentMedications: [] as string[],
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

// Options for new fields
const allergyOptions = [
  'Penicillin', 'Sulfa Drugs', 'Aspirin', 'Peanuts', 'Shellfish', 'Latex', 'Dust', 'Pollen'
]
const relationshipOptions = ['Spouse', 'Parent', 'Child', 'Sibling', 'Friend', 'Other']

// Stepper state & validation
const registrationStep = ref(1)
const draftSavedAt = ref<string | null>(null)

const requiredByStep = {
  1: ['hospitalName', 'hospitalAddress', 'hospitalPhone', 'hospitalEmail'],
  2: ['mrn', 'firstName', 'lastName', 'dob', 'age', 'sex', 'maritalStatus', 'cellPhone', 'homeAddress'],
  3: ['emergencyName', 'emergencyRelationship', 'emergencyPhone'],
  4: ['reasonForVisit', 'consultationLocation'], // attendingPhysician is conditional
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
    if (sp.age) registrationForm.value.age = sp.age
    if (sp.dob) registrationForm.value.dob = sp.dob
    if (sp.gender) registrationForm.value.sex = sp.gender
    // Note: home_address/phone might not be standard fields in Patient type, but good to try
    
    registrationStep.value = 1
    draftSavedAt.value = null
  }
  showRegistrationDialog.value = true
}

const saveRegistration = () => {
  if (!selectedPatient.value) { $q.notify({ type: 'negative', message: 'Select a patient first' }); return }
  
  // Validate all steps
  const r = registrationForm.value
  // Check required fields manually for safety
  const missing: string[] = []
  if (!r.hospitalName) missing.push('Hospital Name')
  if (!r.mrn) missing.push('MRN')
  if (!r.consultationLocation) missing.push('Consultation Location')
  if (r.consultationLocation && !r.attendingPhysician) missing.push('Attending Physician')
  if (!r.firstName) missing.push('First Name')
  if (!r.lastName) missing.push('Last Name')
  if (!r.age && r.age !== 0) missing.push('Age')
  if (!r.dob) missing.push('Date of Birth')
  if (!r.homeAddress) missing.push('Address')
  if (!r.cellPhone) missing.push('Contact Number')
  if (!r.email) missing.push('Email')
  if (!r.emergencyName) missing.push('Emergency Contact')
  
  if (missing.length > 0) {
     $q.notify({ type: 'warning', message: `Missing required fields: ${missing.join(', ')}` })
     return
  }

  const key = `patient_reg_${selectedPatient.value.id}`
  const payload = { patientId: selectedPatient.value.id, ...r, completedAt: new Date().toISOString() }
  localStorage.setItem(key, JSON.stringify(payload))
  registrationCompleted.value = true
  showRegistrationDialog.value = false
  $q.notify({ type: 'positive', message: 'Patient registration & assessment saved' })
}



watch(selectedPatient, (p) => {
  registrationCompleted.value = !!(p && localStorage.getItem(`patient_reg_${p.id}`))
  if (p) {
    loadDemographics();
  } else {
    demographics.value = null
  }
})

// OPD Forms state and methods
const selectedForm = ref<'' | 'intake' | 'flow' | 'mar' | 'education' | 'discharge'>('')

// Modal state for OPD forms
const formDialogOpen = ref(false)
const currentFormTitle = computed(() => {
  if (selectedForm.value === '') return 'Select Form Type'
  return 'OPD Form'
})

// Demographics state and helpers
type Demographics = {
  mrn?: string; firstName?: string; middleName?: string; lastName?: string;
  dob?: string; sex?: string; maritalStatus?: string; nationality?: string;
  homeAddress?: string; cellPhone?: string; homePhone?: string; email?: string;
  emergencyName?: string; emergencyRelationship?: string; emergencyPhone?: string;
  consultationLocation?: string; attendingPhysician?: string;
  hospitalName?: string; hospitalAddress?: string; hospitalPhone?: string; hospitalEmail?: string;
  reasonForVisit?: string; referringDoctor?: string; primaryCarePhysician?: string;
  currentMedications?: string[]; medicalHistory?: string;
  consentAgreed?: boolean; patientSignature?: string; signatureDate?: string;
}
const demographics = ref<Demographics | null>(null)
const demoLoadError = ref<string | null>(null)
const demographicFullName = computed(() => {
  const d = demographics.value
  if (!d) return ''
  const names = [d.firstName, d.middleName, d.lastName].filter(Boolean)
  return names.join(' ').trim()
})
const formattedDOB = computed(() => {
  const dob = demographics.value?.dob
  if (!dob) return ''
  try {
    const dt = new Date(dob)
    return dt.toLocaleDateString()
  } catch { return String(dob) }
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
      demographics.value = registrationCompleted.value ? ({ ...registrationForm.value } as Demographics) : null
    }
    if (!demographics.value) {
      demoLoadError.value = 'Demographics not found for selected patient.'
    }
  } catch (e) {
    console.warn('Failed to load demographics', e)
    demoLoadError.value = 'Unable to load demographics; showing current registration data'
    demographics.value = registrationCompleted.value ? ({ ...registrationForm.value } as Demographics) : null
  } finally {
    demoLoading.value = false
  }
}

// Open modal when a tab is selected and load relevant form data
watch(selectedForm, (val) => {
  if (val) {
    formDialogOpen.value = true
  }
})
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

// Derive a best-guess specialization from patient's condition for outpatient matching
function deriveSpecializationFromCondition(condition: string | null | undefined): string | null {
  const c = (condition || '').toLowerCase()
  if (!c) return null
  if (/(cardio|heart)/.test(c)) return 'Cardiology'
  if (/(neuro|brain|stroke)/.test(c)) return 'Neurology'
  if (/(pulmo|lung|asthma|copd)/.test(c)) return 'Pulmonology'
  if (/(endo|diabet)/.test(c)) return 'Endocrinology'
  if (/(renal|kidney)/.test(c)) return 'Nephrology'
  if (/(ortho|bone|fracture)/.test(c)) return 'Orthopedics'
  if (/(derma|skin)/.test(c)) return 'Dermatology'
  if (/(gastro|stomach|liver)/.test(c)) return 'Gastroenterology'
  if (/(obgyn|pregnan|gyne|women)/.test(c)) return 'Obstetrics & Gynecology'
  return 'General'
}

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

function getInitials(name: string): string {
  const parts = String(name).split(' ').filter(Boolean)
  const initials = parts.map((p: string) => p[0]).slice(0, 2).join('')
  return initials || 'U'
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

async function loadAvailableDoctors(silent?: boolean) {
  if (!silent) doctorsLoading.value = true
  doctorsLoadError.value = null
  
  // Validate that nurse has hospital information
  const currentHospital = nurseHospital.value
  if (!currentHospital || currentHospital.trim() === '') {
    doctorsLoadError.value = 'Hospital information missing. Please update your profile with hospital details.'
    doctorsLoading.value = false
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
    // NOTE: Axios baseURL already includes '/api', so do not prefix with '/api' here
    const res = await api.get('/operations/availability/doctors/free/', {
      params: {
        include_email: true
        // Backend scopes to nurse's hospital; hospital_id not required here
      }
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
    })) as DoctorSummary[]

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
    if (!silent) {
      doctorsLoading.value = false
    }
  }
}

// Send dialog state and handlers
const showSendDialog = ref(false)
const sendLoading = ref(false)
const sendForm = ref<{ doctorId: string | null; message: string }>({ doctorId: null, message: '' })
const selectedPatientForSend = ref<PatientSummary | null>(null)

// Real-time availability polling handle
// polling interval id stored for cleanup (currently unused)
let doctorPoller: number | null = null

const doctorOptions = computed(() => (filteredAvailableDoctors.value || []).map(d => ({
  label: `${d.full_name}${d.specialization ? ' — ' + d.specialization : ''}`,
  value: d.id
})))

interface PatientSummary {
  id: number | string;
  user_id?: number | string;
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

function sendPatientRecords(patient: PatientSummary) {
  selectedPatientForSend.value = patient
  if (!availableDoctors.value.length) { void loadAvailableDoctors(true) }
  // If filtered list has a single match, preselect it
  const docs = filteredAvailableDoctors.value
  if (docs.length === 1) {
    const first = docs[0]
    sendForm.value.doctorId = first && first.id != null ? String(first.id) : null
  }
  showSendDialog.value = true
}

// Inline archive action in patient list: reuse archive flow without opening dialog
function archivePatientInline(patient: PatientSummary) {
  try {
    selectedPatientForSend.value = patient
    // Default to no doctor context and empty message for quick archive
    sendForm.value = { doctorId: null, message: '' }
    void archiveCurrentRecord()
  } catch (err) {
    console.error('Inline archive init failed', err)
    $q.notify({ type: 'negative', message: 'Failed to start archive' })
  }
}

async function confirmSend() {
  if (!selectedPatientForSend.value) { $q.notify({ type: 'warning', message: 'No patient selected' }); return }
  if (!sendForm.value.doctorId) { $q.notify({ type: 'warning', message: 'Please select a doctor' }); return }
  sendLoading.value = true
  try {
    const rawPatient = selectedPatientForSend.value as unknown as { user_id?: number | string; id: number | string; medical_condition?: string | null };
    const patientUserIdNum = Number(rawPatient.user_id ?? rawPatient.id);
    if (!Number.isFinite(patientUserIdNum)) {
      throw new Error('Invalid patient user ID');
    }
    const patientProfileIdNum = Number(rawPatient.id ?? rawPatient.user_id);
    if (!Number.isFinite(patientProfileIdNum)) {
      throw new Error('Invalid patient profile ID');
    }
    const doctorIdNum = Number(sendForm.value.doctorId);
    if (!Number.isFinite(doctorIdNum)) {
      throw new Error('Invalid doctor ID');
    }
    const specialization = deriveSpecializationFromCondition(rawPatient.medical_condition) || 'General';
    await api.post('/operations/assign-patient/', {
      patient_id: patientUserIdNum,
      doctor_id: doctorIdNum,
      specialization,
    })
    $q.notify({ type: 'positive', message: 'Patient assigned to doctor' })

    // Build record bundle to transmit
    // Note: Intake form removed, sending only demographics and message
    const intakePayload: unknown = null;

    // Load demographics from localStorage for the specific patient being sent
    const regKey = `patient_reg_${patientProfileIdNum}`;
    const rawDemo = localStorage.getItem(regKey);
    const demographicsData = rawDemo ? JSON.parse(rawDemo) : null;

    const recordBundle = {
      kind: 'intake',
      at: new Date().toISOString(),
      patientId: patientProfileIdNum,
      demographics: demographicsData,
      intake: intakePayload,
      message: sendForm.value.message || ''
    };

    // Transmit securely to the selected doctor
    await sendSecureToDoctor({ patientId: patientProfileIdNum, doctorId: doctorIdNum, recordJson: JSON.stringify(recordBundle) });
    $q.notify({ type: 'positive', message: 'Secure record transmitted to doctor' })

    // Verify persistence and mapping for this assignment
    try {
      const resp = await api.get(`/operations/verification-status/?patient_id=${patientUserIdNum}&doctor_id=${doctorIdNum}`);
      const counts = resp.data?.persistence ?? {};
      $q.notify({ type: 'info', message: `Verification: assignments ${counts.assignments_count ?? 0}, archives ${counts.archives_count ?? 0}` });
      void api.post('/operations/client-log/', {
        level: 'info',
        message: 'nurse verification fetched',
        route: 'NursePatientAssessment',
        context: { patient_id: patientUserIdNum, doctor_id: doctorIdNum, counts },
      });
    } catch (verr) {
      console.warn('Verification check failed', verr);
      void api.post('/operations/client-log/', {
        level: 'warning',
        message: 'nurse verification failed',
        route: 'NursePatientAssessment',
        context: { patient_id: patientUserIdNum, doctor_id: doctorIdNum, error: String(verr) },
      });
    }

    showSendDialog.value = false
    sendForm.value = { doctorId: null, message: '' }
    selectedPatientForSend.value = null
  } catch (err: unknown) {
    console.error('Assignment or transmission failed', err)
    let msg = 'Failed to assign patient';
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
    $q.notify({ type: 'negative', message: msg })
    void api.post('/operations/client-log/', {
      level: 'error',
      message: 'nurse assign/transmit failed',
      route: 'NursePatientAssessment',
      context: { error: String(err), patient_id: selectedPatientForSend.value?.id ?? null, doctor_id: sendForm.value.doctorId },
    });
  } finally { sendLoading.value = false }
}

async function archiveCurrentRecord() {
  if (!selectedPatientForSend.value) { $q.notify({ type: 'warning', message: 'No patient selected' }); return }
  sendLoading.value = true
  try {
    const rawPatient = selectedPatientForSend.value as unknown as { user_id?: number | string; id: number | string; medical_condition?: string | null };
    const patientUserIdNum = Number(rawPatient.user_id ?? rawPatient.id);
    if (!Number.isFinite(patientUserIdNum)) {
      throw new Error('Invalid patient user ID');
    }
    const patientProfileIdNum = Number(rawPatient.id ?? rawPatient.user_id);
    if (!Number.isFinite(patientProfileIdNum)) {
      throw new Error('Invalid patient profile ID');
    }

    // Optional doctor context
    const hasDoctor = !!sendForm.value.doctorId;
    const doctorIdNum = hasDoctor ? Number(sendForm.value.doctorId) : NaN;
    const specialization = hasDoctor ? (deriveSpecializationFromCondition(rawPatient.medical_condition) || 'General') : null;

    // Load demographics from localStorage for the specific patient being archived
    const regKey = `patient_reg_${patientProfileIdNum}`;
    const rawDemo = localStorage.getItem(regKey);
    const demographicsData = rawDemo ? JSON.parse(rawDemo) : null;

    // Build assessment data
    // Note: Intake form removed
    const intakePayload: Record<string, unknown> | null = null;

    const assessmentData: Record<string, unknown> = {
      ...(intakePayload || {}),
      demographics: demographicsData,
      actor: 'nurse',
      nurse_name: userProfile.value.full_name,
      message: sendForm.value.message || ''
    };

    const payload: Record<string, unknown> = {
      patient_id: patientUserIdNum,
      assessment_type: 'full_record',
      assessment_data: assessmentData,
      full_record: true,
      archival_reason: sendForm.value.message || '',
      medical_condition: rawPatient.medical_condition || '',
      hospital_name: userProfile.value.hospital_name || ''
    };
    if (hasDoctor && Number.isFinite(doctorIdNum)) {
      payload.doctor_id = doctorIdNum;
      payload.specialization = specialization || 'General';
    }

    await api.post('/operations/archives/create/', payload);
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

    // Optional: keep dialog open to allow sending right after archiving
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
    sendLoading.value = false;
  }
}

// Removed developer-only dummy assignment helper; switching to real API-driven data



onMounted(() => {
  console.log('🚀 NursePatientAssessment component mounted');
  void fetchUserProfile();
  void loadNotifications();
  void loadPatients();
  void loadAvailableDoctors();

  // Refresh notifications every 30 seconds
  setInterval(() => void loadNotifications(), 30000);
  // Poll doctor availability every 10 seconds to keep list fresh
  doctorPoller = window.setInterval(() => { void loadAvailableDoctors(true) }, 10000)
});
onUnmounted(() => {
  if (doctorPoller !== null) {
    window.clearInterval(doctorPoller);
    doctorPoller = null;
  }
});

// Secure medical record transmission helpers
const bufferToBase64 = (buf: ArrayBuffer): string => {
  const bytes = new Uint8Array(buf)
  let binary = ''
  for (const b of bytes) binary += String.fromCharCode(b)
  return btoa(binary)
}
const base64ToBuffer = (b64: string): ArrayBuffer => {
  const binary = atob(b64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
  return bytes.buffer
}
const getDoctorPublicKey = async (doctorId: number): Promise<string> => {
  const { data } = await api.get(`/operations/secure/doctor-public-key/${doctorId}/`)
  return data.public_key_pem as string
}
const generateAesKey = async (): Promise<CryptoKey> => {
  return await window.crypto.subtle.generateKey({ name: 'AES-GCM', length: 256 }, true, ['encrypt', 'decrypt'])
}
const exportRawKeyB64 = async (key: CryptoKey): Promise<string> => {
  const raw = await window.crypto.subtle.exportKey('raw', key)
  return bufferToBase64(raw)
}
const encryptRecord = async (jsonStr: string, aesKey: CryptoKey): Promise<{ ciphertext_b64: string; iv_b64: string }> => {
  const iv = window.crypto.getRandomValues(new Uint8Array(12))
  const enc = new TextEncoder().encode(jsonStr)
  const ct = await window.crypto.subtle.encrypt({ name: 'AES-GCM', iv }, aesKey, enc)
  return { ciphertext_b64: bufferToBase64(ct), iv_b64: bufferToBase64(iv.buffer) }
}
const sha256Hex = async (str: string): Promise<string> => {
  const enc = new TextEncoder().encode(str)
  const digest = await window.crypto.subtle.digest('SHA-256', enc)
  const bytes = new Uint8Array(digest)
  return Array.from(bytes).map(b => b.toString(16).padStart(2, '0')).join('')
}
const generateSigningKeyPair = async () => {
  return await window.crypto.subtle.generateKey({ name: 'ECDSA', namedCurve: 'P-256' }, true, ['sign', 'verify'])
}
const exportSpkiPem = async (publicKey: CryptoKey): Promise<string> => {
  const spki = await window.crypto.subtle.exportKey('spki', publicKey)
  const b64 = bufferToBase64(spki)
  const lines = b64.match(/.{1,64}/g)?.join('\n') || b64
  return `-----BEGIN PUBLIC KEY-----\n${lines}\n-----END PUBLIC KEY-----`
}
const signPayloadB64 = async (priv: CryptoKey, dataBuffer: ArrayBuffer): Promise<string> => {
  const sig = await window.crypto.subtle.sign({ name: 'ECDSA', hash: 'SHA-256' }, priv, dataBuffer)
  return bufferToBase64(sig)
}
const importRsaFromPem = async (pem: string): Promise<CryptoKey> => {
  const pemBody = pem.replace('-----BEGIN PUBLIC KEY-----', '').replace('-----END PUBLIC KEY-----', '').replace(/\n/g, '')
  const der = base64ToBuffer(pemBody)
  return await window.crypto.subtle.importKey('spki', der, { name: 'RSA-OAEP', hash: 'SHA-256' }, true, ['encrypt'])
}
const encryptSessionKeyWithDoctorRSA = async (doctorPublicPem: string, rawKeyB64: string): Promise<string> => {
  const rsaPub = await importRsaFromPem(doctorPublicPem)
  const raw = base64ToBuffer(rawKeyB64)
  const encrypted = await window.crypto.subtle.encrypt({ name: 'RSA-OAEP' }, rsaPub, raw)
  return bufferToBase64(encrypted)
}

const sendSecureToDoctor = async (args: { patientId: number; doctorId: number; recordJson: string }) => {
  const { patientId, doctorId, recordJson } = args
  try {
    if (!patientId || !doctorId || !recordJson) {
      $q.notify({ type: 'negative', message: 'Missing required fields', position: 'top' })
      return
    }
    const doctorPublicPem = await getDoctorPublicKey(doctorId)
    const aesKey = await generateAesKey()
    const rawKeyB64 = await exportRawKeyB64(aesKey)
    const { ciphertext_b64, iv_b64 } = await encryptRecord(recordJson, aesKey)
    const checksum_hex = await sha256Hex(recordJson)
    const signingKeys = await generateSigningKeyPair()
    const dataBuf = base64ToBuffer(ciphertext_b64)
    const signature_b64 = await signPayloadB64(signingKeys.privateKey, dataBuf)
    const signing_public_key_pem = await exportSpkiPem(signingKeys.publicKey)
    const encrypted_key_b64 = await encryptSessionKeyWithDoctorRSA(doctorPublicPem, rawKeyB64)

    const confirmSend = (): Promise<boolean> => {
      return new Promise((resolve) => {
        $q.dialog({
          title: 'Confirm Send',
          message: "We’re preparing to send your health information to your doctor. This may include visit notes and test results. Do you want to continue?",
          cancel: true,
          ok: { label: 'Send' }
        })
        .onOk(() => resolve(true))
        .onCancel(() => resolve(false))
        .onDismiss(() => {})
      })
    }

    const confirmed = await confirmSend()
    if (!confirmed) return

    const payload = {
      receiver_id: doctorId,
      patient_id: patientId,
      ciphertext_b64,
      iv_b64,
      encrypted_key_b64,
      signature_b64,
      signing_public_key_pem,
      checksum_hex,
      encryption_alg: 'AES-256-GCM',
      signature_alg: 'ECDSA-P256-SHA256'
    }
    const maxRetries = 3
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        await api.post('/operations/secure/transmissions/', payload)
        $q.notify({ type: 'positive', message: 'Secure transmission sent', position: 'top' })
        break
      } catch (err: unknown) {
        if (attempt === maxRetries - 1) {
          let msg = 'Failed to send secure transmission'
          let backendErr: unknown = null
          if (typeof err === 'object' && err !== null) {
            const e = err as { response?: { data?: { error?: unknown } }, message?: unknown }
            backendErr = e.response?.data?.error
            const apiMsg = e.response?.data?.error
            if (typeof apiMsg === 'string' && apiMsg.trim()) msg = apiMsg
            else if (typeof e.message === 'string' && e.message.trim()) msg = e.message
          }
          $q.notify({ type: 'negative', message: msg, position: 'top' })
          // Client-side diagnostic log
          void api.post('/operations/client-log/', {
            level: 'error',
            message: 'secure transmission failed',
            route: 'NursePatientAssessment',
            context: {
              error: typeof backendErr === 'string' ? backendErr : String(msg),
              patient_id: patientId,
              doctor_id: doctorId,
              fields_present: Object.entries(payload).filter((entry) => Boolean(entry[1])).map((entry) => entry[0])
            }
          })
          break
        }
        await new Promise(r => setTimeout(r, 500 * Math.pow(2, attempt + 1)))
      }
    }
  } catch (err) {
    console.error('Secure send error:', err)
    $q.notify({ type: 'negative', message: 'Secure send error', position: 'top' })
  }
}

//await sendSecureToDoctor({ patientId: selectedPatient!.id, doctorId: selectedDoctorId, recordJson: JSON.stringify(intakeForm) })
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
  margin-bottom: 30px;
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

/* removed greeting icon for cleaner header */

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

/* Selected patient highlight */
.patient-card.selected {
  border: 2px solid #286660;
  background: rgba(40, 102, 96, 0.08);
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
.form-dialog-container { z-index: 2050; }
.form-dialog-card { width: 90vw; max-width: 1000px; background: #ffffff; margin-left: 16px; margin-right: 16px; }
.form-dialog-card .q-card-section { padding: 20px; }
.form-dialog-card .row { align-items: flex-start; }
.form-dialog-card :deep(.q-field) { margin-bottom: 12px; }
@media (max-width: 768px) { .form-dialog-card { width: 95vw; max-width: 95vw; margin-left: 12px; margin-right: 12px; } }
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
