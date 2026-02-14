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
                        aria-label="Pain Assessment"
                        flat
                        round
                        icon="mood"
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
                     <q-input v-model="registrationForm.symptomsDescription" label="Current Symptoms" type="textarea" outlined dense autogrow aria-label="Current Symptoms" hint="Describe the patient's current symptoms in detail"/>
                   </div>
                   <div class="col-12 col-md-6">
                     <div class="text-caption q-mb-xs">Pain Scale (0-10)</div>
                     <q-slider v-model="registrationForm.painScale" :min="0" :max="10" label label-always color="primary" markers snap />
                   </div>
                   <div class="col-12 col-md-6">
                     <q-select v-model="registrationForm.affectedBodyParts" label="Affected Body Parts" multiple use-chips use-input new-value-mode="add-unique" outlined dense :options="['Head', 'Chest', 'Abdomen', 'Back', 'Arms', 'Legs', 'Skin', 'Joints']" aria-label="Affected Body Parts"/>
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

        <q-card-section>
          <div class="text-subtitle2 q-mb-md">Patient: {{ selectedPatient?.full_name }}</div>
          
          <div class="text-center q-mb-lg">
            <div class="text-h1">{{ getPainEmoji(currentPainScore) }}</div>
            <div class="text-h5 text-weight-bold" :class="{
              'text-positive': currentPainScore <= 2,
              'text-primary': currentPainScore > 2 && currentPainScore <= 4,
              'text-warning': currentPainScore > 4 && currentPainScore <= 6,
              'text-orange': currentPainScore > 6 && currentPainScore <= 8,
              'text-negative': currentPainScore > 8
            }">
              {{ getPainLabel(currentPainScore) }} ({{ currentPainScore }})
            </div>
          </div>

          <q-slider
            v-model="currentPainScore"
            :min="1"
            :max="10"
            :step="1"
            label
            label-always
            color="primary"
            markers
          />
          
          <div class="row justify-between text-caption text-grey q-mb-md">
            <span>Mild</span>
            <span>Moderate</span>
            <span>Severe</span>
          </div>

          <q-input
            v-model="painNotes"
            type="textarea"
            label="Clinical Notes"
            outlined
            dense
            autogrow
            rows="3"
            class="q-mb-md"
          />

          <q-separator class="q-my-md" />
          
          <div class="text-subtitle2 q-mb-sm">History</div>
          <q-scroll-area style="height: 150px;">
            <q-list dense separator>
              <q-item v-for="assessment in painHistory" :key="assessment.id">
                <q-item-section avatar>
                  <div class="text-h6">{{ assessment.pain_emoji }}</div>
                </q-item-section>
                <q-item-section>
                  <q-item-label>Score: {{ assessment.pain_score }}</q-item-label>
                  <q-item-label caption>{{ new Date(assessment.created_at).toLocaleString() }}</q-item-label>
                  <q-item-label caption v-if="assessment.notes">{{ assessment.notes }}</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <div class="text-caption">{{ assessment.performed_by_name }}</div>
                </q-item-section>
              </q-item>
              <div v-if="painHistory.length === 0" class="text-center text-grey q-pa-sm">
                No previous assessments
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
import NurseHeader from '../components/NurseHeader.vue';
import NurseSidebar from '../components/NurseSidebar.vue';
import { usePatientStore } from 'src/stores/patientStore';

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
    } as unknown as Patient;

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

// Pain Assessment Logic
const painDialogOpen = ref(false);
const currentPainScore = ref(5);
const painNotes = ref('');
const painHistory = ref<PainAssessment[]>([]);
const painSubmitting = ref(false);

const painEmojis = {
  1: '😀', 2: '😀',
  3: '🙂', 4: '🙂',
  5: '😐', 6: '😐',
  7: '😟', 8: '😟',
  9: '😫', 10: '😫'
};

const getPainEmoji = (score: number) => {
  return painEmojis[score as keyof typeof painEmojis] || '❓';
};

const getPainLabel = (score: number) => {
  if (score <= 2) return 'Mild';
  if (score <= 4) return 'Moderate';
  if (score <= 6) return 'Distressing';
  if (score <= 8) return 'Intense';
  return 'Severe';
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
  symptomsDescription?: string; painScale?: number; affectedBodyParts?: string[];
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
    // NOTE: Axios baseURL already includes '/api', so do not prefix with '/api' here
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

// Real-time availability polling handle
let doctorPoller: ReturnType<typeof setTimeout> | null = null

function startDoctorPolling() {
    stopDoctorPolling()
    const poll = async () => {
        // Only poll if component is mounted (doctorPoller is not null)
        // Note: We check doctorPoller inside the function to break the loop if stopped
        await loadAvailableDoctors(true)
        if (doctorPoller !== null) { 
             doctorPoller = setTimeout(() => { void poll() }, 10000)
        }
    }
    // Initial trigger - set a dummy timeout id to indicate active state
    doctorPoller = setTimeout(() => { void poll() }, 10000)
    // Also trigger immediately? The poll function waits 10s.
    // The original code called setInterval which waits 10s first.
    // So we'll stick to that.
}

function stopDoctorPolling() {
    if (doctorPoller) {
        clearTimeout(doctorPoller)
        doctorPoller = null
    }
}



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
  void loadAvailableDoctors();

  // Poll doctor availability using recursive timeout to prevent overlap
  startDoctorPolling()
});
onUnmounted(() => {
  stopDoctorPolling()
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
