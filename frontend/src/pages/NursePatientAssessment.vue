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

            </q-card-section>

            <q-separator />

            <q-card-section class="form-body" v-if="selectedForm === 'psych'">
              <div
                class="psych-form-container q-gutter-md"
                :class="{ 'psych-high-contrast': psychUiPrefs.highContrast }"
                :style="{ '--psych-font-scale': String(psychUiPrefs.fontScale) }"
              >
                <div class="text-subtitle1 text-bold">{{ hospitalDisplayName }}</div>
                <div class="text-caption">Department: {{ departmentDisplayName }}</div>

                <q-toolbar class="psych-toolbar q-pa-none">
                  <div class="text-caption" aria-live="polite">
                    {{ psychAutosaveLabel }}
                  </div>
                  <q-space />
                  <div class="row items-center q-gutter-sm">
                    <q-toggle v-model="psychUiPrefs.highContrast" label="High Contrast" aria-label="Toggle high contrast mode" />
                    <div class="row items-center q-gutter-xs">
                      <div class="text-caption">Font</div>
                      <q-slider
                        v-model="psychUiPrefs.fontScale"
                        :min="0.9"
                        :max="1.3"
                        :step="0.05"
                        style="width: 140px;"
                        aria-label="Adjust font size"
                      />
                    </div>
                  </div>
                </q-toolbar>

                <q-linear-progress v-if="psychLoadingDraft" indeterminate color="primary" aria-label="Loading psychiatric form draft" />

                <div class="q-mt-md">
                  <div class="text-body1">
                    Dear Patient,
                  </div>
                  <div class="text-body2 q-mt-sm">
                    To gain a more accurate understanding of your condition, we kindly ask you to answer the following questions carefully. Your information will help us develop appropriate therapy recommendations for you. Please answer the questions as they apply to you personally; there are no right or wrong answers. Of course, your information is confidential.
                  </div>
                  <div class="text-body2 q-mt-sm">
                    Thank you for your cooperation.
                  </div>
                </div>

                <div class="psych-grid psych-grid-3 q-mt-md">
                  <q-input v-model="psychForm.applicantLastName" label="Last Name" outlined dense />
                  <q-input v-model="psychForm.applicantFirstName" label="First Name" outlined dense />
                  <q-input v-model="psychForm.dateOfBirth" label="Date of Birth" type="date" outlined dense />
                </div>
                <div class="psych-grid psych-grid-3 q-mt-sm">
                  <q-input v-model.number="psychForm.age" label="Age" type="number" outlined dense />
                  <q-input v-model="psychForm.streetAddress" label="Street Address" outlined dense />
                  <q-input v-model="psychForm.postalCodeCity" label="Postal Code, City" outlined dense />
                </div>
                <div class="psych-grid psych-grid-2 q-mt-sm">
                  <q-input v-model="psychForm.healthInsurance" label="Health Insurance" outlined dense />
                  <q-checkbox v-model="psychForm.privatePhysicianInInsurance" label="Optional Services: Private Physician in Health Insurance" />
                </div>
                <div class="psych-grid psych-grid-2 q-mt-sm">
                  <q-input v-model="psychForm.telephoneLandline" label="Telephone (Landline)" outlined dense />
                  <q-input v-model="psychForm.telephoneMobile" label="Telephone (Mobile)" outlined dense />
                </div>
                <div class="psych-grid psych-grid-2 q-mt-sm">
                  <div>
                    <q-input v-model="psychForm.email" label="Email" outlined dense />
                    <div class="text-caption text-grey-7 q-mt-xs">
                      By providing your email address, you consent to communication via email.
                    </div>
                  </div>
                  <div />
                </div>

                <div class="q-mt-md">
                  <div class="text-subtitle2 text-bold">Contact Persons</div>
                  <div class="q-mt-sm">
                    <div>
                      <div class="text-caption text-grey-7">Contact Person 1 may receive information about the registration status</div>
                    </div>
                    <div class="psych-grid psych-grid-4 q-mt-sm">
                      <q-input v-model="psychForm.contact1.name" label="Last Name, First Name" outlined dense />
                      <q-input v-model="psychForm.contact1.address" label="Address" outlined dense />
                      <q-input v-model="psychForm.contact1.telephone" label="Telephone" outlined dense />
                      <q-input v-model="psychForm.contact1.email" label="Email" outlined dense />
                    </div>

                    <div class="q-mt-md">
                      <div class="text-caption text-grey-7">Contact Person 2 may receive information about the registration status</div>
                    </div>
                    <div class="psych-grid psych-grid-4 q-mt-sm">
                      <q-input v-model="psychForm.contact2.name" label="Last Name, First Name" outlined dense />
                      <q-input v-model="psychForm.contact2.address" label="Address" outlined dense />
                      <q-input v-model="psychForm.contact2.telephone" label="Telephone" outlined dense />
                      <q-input v-model="psychForm.contact2.email" label="Email" outlined dense />
                    </div>
                  </div>
                </div>

                <q-separator class="q-my-md" />

                <div class="q-gutter-md">
                  <div class="text-subtitle2 text-bold">Note</div>
                  <div class="text-body2">
                    Please note that the medical and therapeutic team, as well as the patient management team processing the registration documents, may review your medical history from previous treatments at {{ hospitalDisplayName }}. Please do not send original documents, as these will not be returned. We assure you that your data will be treated confidentially and will not be shared with third parties.
                  </div>
                  <div class="text-body2">
                    However, it is possible that your condition cannot be treated in our outpatient clinic and that inpatient treatment at the {{ hospitalDisplayName }} would be more suitable. Under certain circumstances, and only with your explicit consent, we may forward the documents we have on file to the inpatient department of the {{ hospitalDisplayName }}.
                  </div>
                  <div class="row items-center q-gutter-md">
                    <q-option-group
                      v-model="psychForm.forwardConsent"
                      type="radio"
                      :options="[
                        { label: 'Yes, forwarding possible after consultation', value: 'yes' },
                        { label: 'No', value: 'no' }
                      ]"
                      inline
                    />
                  </div>
                  <div class="text-caption text-grey-7">
                    I understand that I can revoke my consent at any time, without giving reasons, with effect for the future.
                  </div>
                  <div class="row q-col-gutter-md">
                    <div class="col-12 col-md-4">
                      <q-input v-model="psychForm.signatureApplicantLastName" label="Applicant Last Name" outlined dense />
                    </div>
                    <div class="col-12 col-md-4">
                      <q-input v-model="psychForm.signatureApplicantFirstName" label="Applicant First Name" outlined dense />
                    </div>
                    <div class="col-12 col-md-4">
                      <q-input v-model="psychForm.signatureApplicantDob" label="Applicant Date of Birth" type="date" outlined dense />
                    </div>
                    <div class="col-12 col-md-6">
                      <q-input v-model="psychForm.signatureDate" label="Date" type="date" outlined dense />
                    </div>
                    <div class="col-12 col-md-6">
                      <q-input v-model="psychForm.signatureApplicant" label="Signature of Applicant" outlined dense />
                    </div>
                    <div class="col-12">
                      <q-checkbox v-model="psychForm.isRepresentative" label="I am acting as a representative with power of attorney or legal guardian. Copy enclosed." />
                    </div>
                    <div class="col-12 col-md-4">
                      <q-input v-model="psychForm.representativeLastName" label="Representative Last Name" outlined dense />
                    </div>
                    <div class="col-12 col-md-4">
                      <q-input v-model="psychForm.representativeFirstName" label="Representative First Name" outlined dense />
                    </div>
                    <div class="col-12 col-md-4">
                      <q-input v-model="psychForm.representativeDob" label="Representative Date of Birth" type="date" outlined dense />
                    </div>
                    <div class="col-12 col-md-6">
                      <q-input v-model="psychForm.representativeSignatureDate" label="Date" type="date" outlined dense />
                    </div>
                    <div class="col-12 col-md-6">
                      <q-input v-model="psychForm.representativeSignature" label="Signature of Representative / Legal Guardian" outlined dense />
                    </div>
                  </div>
                </div>

                <q-separator class="q-my-md" />

                <div class="q-gutter-md">
                  <div class="text-subtitle1 text-bold">Section 1: Information on Current Complaints</div>
                  <div class="text-subtitle2 text-bold">1.1. What psychological complaints are you currently experiencing?</div>
                  <div class="text-caption text-grey-7">List complaints and duration.</div>
                  <div class="row q-col-gutter-md">
                    <div class="col-12 col-md-8">
                      <q-input v-model="psychForm.complaints[0].text" label="Complaint 1" outlined dense />
                    </div>
                    <div class="col-12 col-md-4">
                      <q-input v-model="psychForm.complaints[0].since" label="Since" outlined dense />
                    </div>
                    <div class="col-12 col-md-8">
                      <q-input v-model="psychForm.complaints[1].text" label="Complaint 2" outlined dense />
                    </div>
                    <div class="col-12 col-md-4">
                      <q-input v-model="psychForm.complaints[1].since" label="Since" outlined dense />
                    </div>
                    <div class="col-12 col-md-8">
                      <q-input v-model="psychForm.complaints[2].text" label="Complaint 3" outlined dense />
                    </div>
                    <div class="col-12 col-md-4">
                      <q-input v-model="psychForm.complaints[2].since" label="Since" outlined dense />
                    </div>
                  </div>

                  <div class="text-subtitle2 text-bold q-mt-sm">1.2. Have you received any psychiatric diagnoses?</div>
                  <div class="text-caption text-grey-7">List diagnoses and duration.</div>
                  <div class="row q-col-gutter-md">
                    <div class="col-12 col-md-8">
                      <q-input v-model="psychForm.diagnoses[0].text" label="Diagnosis 1" outlined dense />
                    </div>
                    <div class="col-12 col-md-4">
                      <q-input v-model="psychForm.diagnoses[0].since" label="Since" outlined dense />
                    </div>
                    <div class="col-12 col-md-8">
                      <q-input v-model="psychForm.diagnoses[1].text" label="Diagnosis 2" outlined dense />
                    </div>
                    <div class="col-12 col-md-4">
                      <q-input v-model="psychForm.diagnoses[1].since" label="Since" outlined dense />
                    </div>
                    <div class="col-12 col-md-8">
                      <q-input v-model="psychForm.diagnoses[2].text" label="Diagnosis 3" outlined dense />
                    </div>
                    <div class="col-12 col-md-4">
                      <q-input v-model="psychForm.diagnoses[2].since" label="Since" outlined dense />
                    </div>
                  </div>

                  <div class="row q-col-gutter-md q-mt-sm">
                    <div class="col-12">
                      <div class="text-subtitle2 text-bold">1.3. What physical illnesses do you have or have you had?</div>
                      <q-input v-model="psychForm.physicalIllnesses" label="Physical illnesses (current/past)" type="textarea" outlined autogrow class="q-mt-sm" />
                    </div>
                    <div class="col-12">
                      <div class="text-subtitle2 text-bold q-mt-sm">1.4. Your height and weight?</div>
                    </div>
                    <div class="col-12 col-md-6">
                      <q-input v-model.number="psychForm.heightCm" label="1.4 Height (cm)" type="number" outlined dense />
                    </div>
                    <div class="col-12 col-md-6">
                      <q-input v-model.number="psychForm.weightKg" label="1.4 Weight (kg)" type="number" outlined dense />
                    </div>
                    <div class="col-12">
                      <div class="text-subtitle2 text-bold q-mt-sm">Are you satisfied with your weight?</div>
                      <q-option-group
                        v-model="psychForm.satisfiedWithWeight"
                        type="radio"
                        :options="[
                          { label: 'Yes', value: 'yes' },
                          { label: 'No', value: 'no' }
                        ]"
                        inline
                      />
                      <q-input v-if="psychForm.satisfiedWithWeight === 'no'" v-model="psychForm.weightDissatisfactionReason" label="Why are you not satisfied with your weight?" outlined dense class="q-mt-sm" />
                    </div>
                  </div>

                  <div class="text-subtitle2 text-bold q-mt-sm">1.5 Problems (select all that apply)</div>
                  <q-option-group
                    v-model="psychForm.problemChecklist"
                    type="checkbox"
                    :options="psychProblemOptions"
                  />
                  <q-input v-model="psychForm.problemOther" label="Other" outlined dense class="q-mt-sm" />

                  <div class="q-mt-md">
                    <div class="text-subtitle2 text-bold">1.6 Serious thoughts of taking your own life?</div>
                    <q-option-group
                      v-model="psychForm.suicidalThoughts"
                      type="radio"
                      :options="[
                        { label: 'No', value: 'no' },
                        { label: 'Yes', value: 'yes' }
                      ]"
                      inline
                    />
                  </div>

                  <div class="q-mt-md">
                    <div class="text-subtitle2 text-bold">1.7 Have you ever attempted suicide?</div>
                    <q-option-group
                      v-model="psychForm.suicideAttempts"
                      type="radio"
                      :options="[
                        { label: 'No', value: 'no' },
                        { label: 'Yes', value: 'yes' }
                      ]"
                      inline
                    />
                    <q-input v-if="psychForm.suicideAttempts === 'yes'" v-model="psychForm.suicideAttemptLastWhen" label="If yes, when did the last attempt take place?" outlined dense class="q-mt-sm" />
                  </div>

                  <div class="text-subtitle2 text-bold q-mt-md">1.8. What do you think is the reason for your current complaints?</div>
                  <q-input v-model="psychForm.reasonForComplaints" label="Response" type="textarea" outlined autogrow class="q-mt-sm" />

                  <div class="text-subtitle2 text-bold q-mt-md">1.9. Was there a major change or a high level of stress in your life before the onset of the complaints? If yes, please describe briefly:</div>
                  <q-input v-model="psychForm.majorChangeBeforeOnset" label="Response" type="textarea" outlined autogrow class="q-mt-sm" />

                  <div class="text-subtitle2 text-bold q-mt-md">1.10. What has caused you the most difficulty in your life?</div>
                  <q-input v-model="psychForm.mostDifficultyInLife" label="Response" type="textarea" outlined autogrow class="q-mt-sm" />
                  <q-input v-model="psychForm.decisiveFactorForTherapy" label="1.11 Decisive factor to undergo psychotherapy now (who/why)" type="textarea" outlined autogrow class="q-mt-sm" />
                </div>

                <q-separator class="q-my-md" />

                <div class="q-gutter-md">
                  <div class="text-subtitle1 text-bold">Section 2: Psychiatric Previous Treatments</div>
                  <div class="text-subtitle2 text-bold">2.1. Have you previously been or are you currently in outpatient psychotherapeutic treatment?</div>
                  <q-option-group
                    v-model="psychForm.outpatientPsychotherapy"
                    type="radio"
                    :options="[
                      { label: 'Never', value: 'never' },
                      { label: 'Yes, previously', value: 'previously' },
                      { label: 'Yes, currently', value: 'currently' }
                    ]"
                    inline
                  />
                  <div class="row q-col-gutter-md" v-if="psychForm.outpatientPsychotherapy === 'previously'">
                    <div class="col-12 col-md-4">
                      <q-input v-model="psychForm.outpatientPreviouslyYear" label="Year" outlined dense />
                    </div>
                  </div>
                  <div class="row q-col-gutter-md" v-if="psychForm.outpatientPsychotherapy === 'currently'">
                    <div class="col-12 col-md-6">
                      <q-input v-model="psychForm.outpatientCurrentlyWith" label="Currently in treatment with (Name)" outlined dense />
                    </div>
                  </div>

                  <div class="text-subtitle2 text-bold q-mt-sm">2.2 Current medical treatment because of your psyche</div>
                  <div class="row q-col-gutter-md">
                    <div class="col-12 col-md-6">
                      <q-input v-model="psychForm.medicalTreatment1.withWhom" label="With whom" outlined dense />
                    </div>
                    <div class="col-12 col-md-6">
                      <q-input v-model="psychForm.medicalTreatment1.specialistField" label="Specialist field" outlined dense />
                    </div>
                    <div class="col-12 col-md-6">
                      <q-input v-model="psychForm.medicalTreatment2.withWhom" label="With whom" outlined dense />
                    </div>
                    <div class="col-12 col-md-6">
                      <q-input v-model="psychForm.medicalTreatment2.specialistField" label="Specialist field" outlined dense />
                    </div>
                  </div>

                  <div class="text-subtitle2 text-bold q-mt-sm">2.3 Day-clinic or inpatient psychotherapeutic treatment (facilities)</div>
                  <div class="row q-col-gutter-md">
                    <div class="col-12 col-md-6">
                      <q-input v-model="psychForm.inpatient1.where" label="Where" outlined dense />
                    </div>
                    <div class="col-12 col-md-6">
                      <q-input v-model="psychForm.inpatient1.when" label="When" outlined dense />
                    </div>
                    <div class="col-12 col-md-6">
                      <q-input v-model="psychForm.inpatient2.where" label="Where" outlined dense />
                    </div>
                    <div class="col-12 col-md-6">
                      <q-input v-model="psychForm.inpatient2.when" label="When" outlined dense />
                    </div>
                    <div class="col-12 col-md-6">
                      <q-input v-model="psychForm.inpatient3.where" label="Where" outlined dense />
                    </div>
                    <div class="col-12 col-md-6">
                      <q-input v-model="psychForm.inpatient3.when" label="When" outlined dense />
                    </div>
                    <div class="col-12 col-md-6">
                      <q-input v-model="psychForm.inpatient4.where" label="Where" outlined dense />
                    </div>
                    <div class="col-12 col-md-6">
                      <q-input v-model="psychForm.inpatient4.when" label="When" outlined dense />
                    </div>
                  </div>
                </div>

                <q-separator class="q-my-md" />

                <div class="q-gutter-md">
                  <div class="text-subtitle1 text-bold">Section 3: Sociodemographic Data</div>

                  <div class="q-gutter-sm">
                    <div class="text-subtitle2 text-bold">3.1 Gender</div>
                    <div class="text-body2">What is your gender?</div>
                    <q-option-group v-model="psychForm.gender" type="radio" :options="genderRadioOptions" />
                    <q-input
                      v-if="psychForm.gender === 'self_describe'"
                      v-model="psychForm.genderSelfDescribe"
                      label="Prefer to self-describe"
                      outlined
                      dense
                    />
                  </div>

                  <div class="q-gutter-sm">
                    <div class="text-subtitle2 text-bold">3.2 Place of Birth</div>
                    <div class="text-body2">Where were you born?</div>
                    <q-option-group
                      v-model="psychForm.bornInPhilippines"
                      type="radio"
                      :options="[
                        { label: 'Philippines', value: 'philippines' },
                        { label: 'Other country', value: 'other' }
                      ]"
                      inline
                    />
                    <q-input v-if="psychForm.bornInPhilippines === 'other'" v-model="psychForm.birthCountryOther" label="Other country" outlined dense />
                  </div>

                  <div class="q-gutter-sm">
                    <div class="text-subtitle2 text-bold">3.3 Marital Status</div>
                    <div class="text-body2">What is your current marital status?</div>
                    <q-option-group v-model="psychForm.maritalStatus" type="radio" :options="maritalStatusOptions" inline />
                  </div>

                  <div class="q-gutter-sm">
                    <div class="text-subtitle2 text-bold">3.4 Do you have children?</div>
                    <q-option-group
                      v-model="psychForm.hasChildren"
                      type="radio"
                      :options="[
                        { label: 'No children', value: 'no' },
                        { label: 'Yes', value: 'yes' }
                      ]"
                      inline
                    />
                    <q-input
                      v-if="psychForm.hasChildren === 'yes'"
                      v-model="psychForm.childrenInfo"
                      label="If yes, please indicate Age / Gender"
                      outlined
                      dense
                    />
                  </div>

                  <div class="q-gutter-sm">
                    <div class="text-subtitle2 text-bold">3.5 What is your current living/housing situation?</div>
                    <q-option-group v-model="psychForm.housingSituation" type="radio" :options="housingSituationOptions" />
                    <q-input
                      v-if="psychForm.housingSituation === 'institution'"
                      v-model="psychForm.housingInstitutionDescribe"
                      label="Living in an institution"
                      outlined
                      dense
                    />
                  </div>

                  <div class="q-gutter-sm">
                    <div class="text-subtitle2 text-bold">3.6 Do you have debts?</div>
                    <q-option-group
                      v-model="psychForm.hasDebts"
                      type="radio"
                      :options="[
                        { label: 'No', value: 'no' },
                        { label: 'Yes', value: 'yes' }
                      ]"
                      inline
                    />
                    <q-input
                      v-if="psychForm.hasDebts === 'yes'"
                      v-model="psychForm.debtsApprox"
                      label="Yes, approximately: €"
                      outlined
                      dense
                    />
                  </div>

                  <div class="q-gutter-sm">
                    <div class="text-subtitle2 text-bold">3.7 What is your highest school-leaving qualification?</div>
                    <q-option-group v-model="psychForm.schoolQualification" type="radio" :options="schoolQualificationOptions" />
                    <q-input
                      v-if="psychForm.schoolQualification === 'other'"
                      v-model="psychForm.schoolQualificationOther"
                      label="Other"
                      outlined
                      dense
                    />
                  </div>

                  <div class="q-gutter-sm">
                    <div class="text-subtitle2 text-bold">3.8 What is your highest professional qualification achieved?</div>
                    <q-option-group v-model="psychForm.professionalQualification" type="radio" :options="professionalQualificationOptions" />
                  </div>

                  <div class="q-gutter-sm">
                    <div class="text-subtitle2 text-bold">3.9 What is your current professional status?</div>
                    <div class="text-body2 text-bold">Employed:</div>
                    <div class="text-body2">Self-employed — Learned profession / Assisting family member / Civil servant / Employee — Current activity / Worker</div>
                    <div class="text-body2 text-bold q-mt-sm">Not employed:</div>
                    <div class="text-body2">Homemaker / Unemployed / Pension / Disability pension / Student / School / Other</div>

                    <q-option-group v-model="psychForm.employmentStatus" type="radio" :options="employmentStatusOptions" />

                    <q-input
                      v-if="psychForm.employmentStatus === 'self_employed'"
                      v-model="psychForm.selfEmployedLearnedProfession"
                      label="Learned profession"
                      outlined
                      dense
                    />
                    <q-input
                      v-if="psychForm.employmentStatus === 'employee'"
                      v-model="psychForm.employeeCurrentActivity"
                      label="Current activity"
                      outlined
                      dense
                    />
                    <q-input
                      v-if="psychForm.employmentStatus === 'unemployed'"
                      v-model="psychForm.unemployedSince"
                      label="Unemployed since"
                      outlined
                      dense
                    />
                    <q-input
                      v-if="psychForm.employmentStatus === 'other'"
                      v-model="psychForm.employmentOther"
                      label="Other"
                      outlined
                      dense
                    />
                  </div>

                  <div class="q-gutter-sm">
                    <div class="text-subtitle2 text-bold">Currently unable to work?</div>
                    <q-option-group
                      v-model="psychForm.unableToWork"
                      type="radio"
                      :options="[
                        { label: 'No', value: 'no' },
                        { label: 'Yes', value: 'yes' }
                      ]"
                      inline
                    />
                    <q-input v-if="psychForm.unableToWork === 'yes'" v-model="psychForm.unableToWorkSince" label="Yes, since" outlined dense />
                  </div>

                  <div class="q-gutter-sm">
                    <div class="text-subtitle2 text-bold">Are you retired?</div>
                    <q-option-group v-model="psychForm.retired" type="radio" :options="retiredOptions" />
                  </div>
                </div>

                <q-separator class="q-my-md" />

                <div class="q-gutter-md">
                  <div class="text-subtitle1 text-bold">Section 4: Current Life Situation</div>
                  <q-option-group
                    v-model="psychForm.partnership"
                    type="radio"
                    :options="[
                      { label: 'No partnership', value: 'no' },
                      { label: 'Yes', value: 'yes' }
                    ]"
                    inline
                  />
                  <q-input v-if="psychForm.partnership === 'yes'" v-model="psychForm.partnershipDescribe" label="If yes, since when and how would you describe your partnership" type="textarea" outlined autogrow />
                  <q-input v-model="psychForm.friendshipsDescribe" label="4.2 Friendships description" type="textarea" outlined autogrow />
                  <q-input v-model="psychForm.leisureDescribe" label="4.3 Leisure time / hobbies" type="textarea" outlined autogrow />
                  <q-input v-model="psychForm.policeContact" label="4.4 Police contact / proceedings" type="textarea" outlined autogrow />
                  <q-input v-model="psychForm.selfDescribe" label="4.5 Describe yourself (adjectives)" type="textarea" outlined autogrow />
                  <q-input v-model="psychForm.resources" label="4.6 Positive aspects / resources" type="textarea" outlined autogrow />
                </div>

                <q-separator class="q-my-md" />

                <div class="q-gutter-md">
                  <div class="text-subtitle1 text-bold">Section 5: Life History Development</div>

                  <div class="text-subtitle2 text-bold">5.1 Family and Reference Persons</div>
                  <div class="text-body2">
                    The following questions relate to how you grew up, for example, the relationship with important people in your life.
                  </div>

                  <div class="text-subtitle2 text-bold q-mt-sm">Mother</div>
                  <div class="psych-grid psych-grid-3">
                    <q-input v-model="psychForm.mother.ageAtBirth" label="Age at your birth" outlined dense />
                    <q-input v-model="psychForm.mother.profession" label="Profession" outlined dense />
                    <q-option-group
                      v-model="psychForm.mother.deceased"
                      type="radio"
                      :options="[
                        { label: 'Deceased: No', value: 'no' },
                        { label: 'Deceased: Yes', value: 'yes' }
                      ]"
                      inline
                    />
                  </div>
                  <div class="psych-grid psych-grid-2 q-mt-sm" v-if="psychForm.mother.deceased === 'yes'">
                    <q-input v-model="psychForm.mother.deceasedYear" label="If deceased: Year" outlined dense />
                    <q-input v-model="psychForm.mother.deceasedCause" label="Cause of death" outlined dense />
                  </div>
                  <q-input v-model="psychForm.mother.psychIllnesses" label="Psychological illnesses of your mother? (e.g., alcoholism, suicide attempts, depression)" type="textarea" outlined autogrow />
                  <q-input v-model="psychForm.mother.personalityDescribe" label="How would you describe your mother (please use adjectives)" type="textarea" outlined autogrow />
                  <q-input v-model="psychForm.mother.relationshipDescribe" label="How would you describe your relationship with your mother" type="textarea" outlined autogrow />

                  <div class="text-subtitle2 text-bold q-mt-md">Father</div>
                  <div class="psych-grid psych-grid-3">
                    <q-input v-model="psychForm.father.ageAtBirth" label="Age at your birth" outlined dense />
                    <q-input v-model="psychForm.father.profession" label="Profession" outlined dense />
                    <q-option-group
                      v-model="psychForm.father.deceased"
                      type="radio"
                      :options="[
                        { label: 'Deceased: No', value: 'no' },
                        { label: 'Deceased: Yes', value: 'yes' }
                      ]"
                      inline
                    />
                  </div>
                  <div class="psych-grid psych-grid-2 q-mt-sm" v-if="psychForm.father.deceased === 'yes'">
                    <q-input v-model="psychForm.father.deceasedYear" label="If deceased: Year" outlined dense />
                    <q-input v-model="psychForm.father.deceasedCause" label="Cause of death" outlined dense />
                  </div>
                  <q-input v-model="psychForm.father.psychIllnesses" label="Psychological illnesses of your father? (e.g., alcoholism, suicide attempts, depression)" type="textarea" outlined autogrow />
                  <q-input v-model="psychForm.father.personalityDescribe" label="How would you describe your father (please use adjectives)" type="textarea" outlined autogrow />
                  <q-input v-model="psychForm.father.relationshipDescribe" label="How would you describe your relationship with your father" type="textarea" outlined autogrow />

                  <q-input v-model="psychForm.parentalRelationship" label="5.2 How was the relationship between the parents?" type="textarea" outlined autogrow />
                  <q-input v-model="psychForm.familyAtmosphere" label="5.3 How would you generally describe the family atmosphere?" type="textarea" outlined autogrow />

                  <div class="text-subtitle2 text-bold q-mt-sm">5.4 Siblings</div>
                  <q-option-group
                    v-model="psychForm.hasSiblings"
                    type="radio"
                    :options="[
                      { label: 'No', value: 'no' },
                      { label: 'Yes', value: 'yes' }
                    ]"
                    inline
                  />
                  <div class="psych-grid psych-grid-2 q-mt-sm" v-if="psychForm.hasSiblings === 'yes'">
                    <q-input v-model="psychForm.siblingsDetails" label="If yes, how many (please state age and gender)" outlined dense />
                    <q-input v-model="psychForm.siblingsRelationship" label="How is the relationship with your siblings?" outlined dense />
                  </div>

                  <div class="text-subtitle2 text-bold q-mt-sm">5.5 Life events</div>
                  <div class="psych-grid psych-grid-2">
                    <q-input v-model="psychForm.lifeEventsPositive" label="Most important positive events" type="textarea" outlined autogrow />
                    <q-input v-model="psychForm.lifeEventsBurdensome" label="Most important burdensome events" type="textarea" outlined autogrow />
                  </div>

                  <div class="text-subtitle2 text-bold q-mt-sm">5.6 Traumatic, frightening experiences determining for your further sexual life?</div>
                  <q-option-group
                    v-model="psychForm.sexualTrauma"
                    type="radio"
                    :options="[
                      { label: 'No', value: 'no' },
                      { label: 'Yes', value: 'yes' }
                    ]"
                    inline
                  />

                  <div class="text-subtitle2 text-bold q-mt-sm">5.7 Burdensome events or aggravating circumstances (e.g., death of a reference person, stays in a home, accident, robbery, etc.)?</div>
                  <q-option-group
                    v-model="psychForm.aggravatingCircumstances"
                    type="radio"
                    :options="[
                      { label: 'No', value: 'no' },
                      { label: 'Yes', value: 'yes' }
                    ]"
                    inline
                  />
                  <q-input v-if="psychForm.aggravatingCircumstances === 'yes'" v-model="psychForm.aggravatingCircumstancesDescribe" label="If yes, please describe" type="textarea" outlined autogrow />

                  <div class="text-subtitle2 text-bold q-mt-sm">5.8 Have you experienced exclusion (e.g., due to origin, sexual orientation, or gender)?</div>
                  <q-option-group
                    v-model="psychForm.exclusion"
                    type="radio"
                    :options="[
                      { label: 'No', value: 'no' },
                      { label: 'Yes', value: 'yes' }
                    ]"
                    inline
                  />
                  <q-input v-if="psychForm.exclusion === 'yes'" v-model="psychForm.exclusionWhatKind" label="If yes, what kind?" outlined dense />
                </div>

                <q-separator class="q-my-md" />

                <div class="q-gutter-md">
                  <div class="text-subtitle1 text-bold">Section 6: Medications / Substance Consumption</div>
                  <div class="text-subtitle2 text-bold">6.1 Substances taken in the past, in the last 6 months, and most recently</div>

                  <div class="psych-grid psych-grid-4">
                    <q-input v-model="psychForm.substances.drugs.name" label="Drugs (name)" outlined dense />
                    <q-input v-model="psychForm.substances.drugs.amountEarlier" label="Amount earlier (last 5 years)" outlined dense />
                    <q-input v-model="psychForm.substances.drugs.amount6Months" label="Amount (last 6 months avg/week)" outlined dense />
                    <q-input v-model="psychForm.substances.drugs.lastConsumption" label="Last consumption" outlined dense />

                    <q-input v-model="psychForm.substances.alcohol.name" label="Alcohol (name)" outlined dense />
                    <q-input v-model="psychForm.substances.alcohol.amountEarlier" label="Amount earlier (last 5 years)" outlined dense />
                    <q-input v-model="psychForm.substances.alcohol.amount6Months" label="Amount (last 6 months avg/week)" outlined dense />
                    <q-input v-model="psychForm.substances.alcohol.lastConsumption" label="Last consumption" outlined dense />

                    <q-input v-model="psychForm.substances.tranquilizers.name" label="Tranquilizers (name)" outlined dense />
                    <q-input v-model="psychForm.substances.tranquilizers.amountEarlier" label="Amount earlier (last 5 years)" outlined dense />
                    <q-input v-model="psychForm.substances.tranquilizers.amount6Months" label="Amount (last 6 months avg/week)" outlined dense />
                    <q-input v-model="psychForm.substances.tranquilizers.lastConsumption" label="Last consumption" outlined dense />

                    <q-input v-model="psychForm.substances.nicotine.name" label="Nicotine (name)" outlined dense />
                    <q-input v-model="psychForm.substances.nicotine.amountEarlier" label="Amount earlier (last 5 years)" outlined dense />
                    <q-input v-model="psychForm.substances.nicotine.amount6Months" label="Amount (last 6 months avg/week)" outlined dense />
                    <q-input v-model="psychForm.substances.nicotine.lastConsumption" label="Last consumption" outlined dense />
                  </div>

                  <div class="text-subtitle2 text-bold q-mt-sm">6.2 Are you worried about your consumption?</div>
                  <div class="psych-grid psych-grid-3">
                    <q-option-group
                      v-model="psychForm.worriesDrugs"
                      type="radio"
                      :options="[
                        { label: 'Drugs: No', value: 'no' },
                        { label: 'Drugs: Yes', value: 'yes' }
                      ]"
                      inline
                    />
                    <q-option-group
                      v-model="psychForm.worriesAlcohol"
                      type="radio"
                      :options="[
                        { label: 'Alcohol: No', value: 'no' },
                        { label: 'Alcohol: Yes', value: 'yes' }
                      ]"
                      inline
                    />
                    <q-option-group
                      v-model="psychForm.worriesMedia"
                      type="radio"
                      :options="[
                        { label: 'Media/Computer: No', value: 'no' },
                        { label: 'Media/Computer: Yes', value: 'yes' }
                      ]"
                      inline
                    />
                  </div>
                  <q-input v-model="psychForm.mediaHoursPerDay" label="Average hours per day on Internet/PC/social networks" outlined dense />

                  <div class="text-subtitle2 text-bold q-mt-sm">6.3 Current medication plan (include as-needed medication)</div>
                  <q-input v-model="psychForm.medicationPlan" label="Medication plan" type="textarea" outlined autogrow />
                </div>

                <div class="q-gutter-md">
                  <div class="text-subtitle1 text-bold">Section 7: Expectations</div>
                  <q-input v-model="psychForm.goals" label="7.1 Goals (3 goals)" type="textarea" outlined autogrow />
                  <q-input v-model="psychForm.selfHelpSoFar" label="7.2 How have you tried to help yourself so far?" type="textarea" outlined autogrow />
                  <div class="text-subtitle2 text-bold q-mt-sm">7.3 Importance of problem areas</div>
                  <div class="q-gutter-sm">
                    <div v-for="area in psychImportanceAreas" :key="area.key" class="row items-center q-col-gutter-sm">
                      <div class="col-12 col-md-7">
                        <div class="text-body2">{{ area.label }}</div>
                      </div>
                      <div class="col-12 col-md-5">
                        <q-select
                          v-model="psychForm.importance[area.key]"
                          :options="importanceOptions"
                          outlined
                          dense
                          emit-value
                          map-options
                          label="Importance"
                        />
                      </div>
                    </div>
                  </div>
                  <q-input v-model="psychForm.fearsWithTeam" label="7.4 Fears in contact with the therapeutic team?" type="textarea" outlined autogrow class="q-mt-md" />
                  <div class="text-subtitle2 text-bold q-mt-sm">Who filled out the questionnaire</div>
                  <q-option-group
                    v-model="psychForm.filledBy"
                    type="radio"
                    :options="[
                      { label: 'By myself', value: 'self' },
                      { label: 'By someone else', value: 'other' }
                    ]"
                    inline
                  />
                </div>
              </div>
            </q-card-section>

            <q-card-actions align="between" v-if="selectedForm === 'psych'">
              <div class="text-caption text-grey-7" v-if="psychDraftSavedAt">
                Draft saved: {{ new Date(psychDraftSavedAt).toLocaleString() }}
              </div>
              <div class="row items-center q-gutter-sm">
                <q-btn flat label="Save Draft" color="primary" @click="() => void savePsychDraft(false)" />
                <q-btn color="primary" label="Save & Submit" :loading="savingPsychForm" @click="savePsychSubmit" />
              </div>
            </q-card-actions>
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
          <q-input v-model="sendMessage" label="Message (optional)" outlined dense class="q-mt-md" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="CANCEL" color="dark" v-close-popup />
          <q-btn label="ARCHIVE" color="teal" @click="archiveFromSendDialog" />
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
const allFormOptions: FormOption[] = [
  { label: 'Select Form Type', value: '', roles: ['nurse', 'admin'] },
  { label: 'Registration', value: 'registration', roles: ['nurse', 'admin'] },
  { label: 'Psychiatric OPD Questionnaire', value: 'psych', roles: ['nurse', 'admin'] },
];

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
const hospitalDisplayName = computed(() => (userProfile.value?.hospital_name || '').trim() || 'Hospital')
const departmentDisplayName = computed(() => department.value)

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
    if (sp.age) registrationForm.value.age = sp.age
    if (sp.dob) registrationForm.value.dob = sp.dob
    if (sp.gender) registrationForm.value.sex = sp.gender
    // Note: home_address/phone might not be standard fields in Patient type, but good to try
    
    registrationStep.value = 1
    draftSavedAt.value = null
  }
  showRegistrationDialog.value = true
}

const savingRegistration = ref(false)

const saveRegistration = async () => {
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

  savingRegistration.value = true
  try {
    const today = new Date().toISOString().slice(0, 10)
    registrationForm.value.signatureDate = today

    const intakePayload = {
      chief_complaint: r.reasonForVisit || '',
      pain_score: typeof r.painScale === 'number' ? r.painScale : undefined,
      allergies: r.knownAllergies || [],
      current_medications: r.currentMedications || '',
      medical_history: r.medicalHistory || '',
      assessment_notes: r.symptomsDescription || '',
      assessed_at: new Date().toISOString(),
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
    $q.notify({ type: 'positive', message: 'Patient registration & assessment saved' })
    void api.post('/operations/client-log/', {
      level: 'info',
      message: 'saveRegistration succeeded',
      route: 'NursePatientAssessment',
      context: { patient_id: selectedPatient.value.id }
    }).catch(() => { /* non-blocking */ })
  } catch (e) {
    console.error('Failed to save registration/intake:', e)
    $q.notify({ type: 'negative', message: 'Failed to save assessment. Please try again.', position: 'top' })
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



watch(selectedPatient, (p) => {
  registrationCompleted.value = !!(p && localStorage.getItem(`patient_reg_${p.id}`))
  if (p) {
    loadDemographics();
  } else {
    demographics.value = null
  }
})

// OPD Forms state and methods
const selectedForm = ref<'' | 'registration' | 'psych'>('')

// Modal state for OPD forms
const formDialogOpen = ref(false)
const currentFormTitle = computed(() => {
  if (selectedForm.value === '') return 'Select Form Type'
  if (selectedForm.value === 'registration') return 'Registration'
  if (selectedForm.value === 'psych') return 'Psychiatric OPD Questionnaire'
  return 'OPD Form'
})

type PsychLineItem = { text: string; since: string }
type PsychContact = { name: string; address: string; telephone: string; email: string }

type PsychImportanceKey =
  | 'persistentSadnessDepression'
  | 'anxietyPanicAttacks'
  | 'eatingDisorderWeight'
  | 'physicalComplaints'
  | 'tinnitus'
  | 'depressedMood'
  | 'stressRegulation'
  | 'socialWithdrawal'
  | 'obsessiveThoughtsCompulsions'
  | 'adhd'
  | 'traumaPtsd'
  | 'tensionSelfHarmPressure'
  | 'chronicPain'
  | 'sexuality'
  | 'occupationalPerformance'
  | 'misc'

type PsychImportanceValue = '' | 'unimportant' | 'less' | 'important' | 'very' | 'preurgent'

type PsychSubstanceRow = { name: string; amountEarlier: string; amount6Months: string; lastConsumption: string }

type PsychFormGender = '' | 'male' | 'female' | 'non_binary' | 'self_describe' | 'prefer_not_to_say'

type PsychFormState = {
  applicantLastName: string
  applicantFirstName: string
  dateOfBirth: string
  age: number | null
  streetAddress: string
  postalCodeCity: string
  healthInsurance: string
  privatePhysicianInInsurance: boolean
  telephoneLandline: string
  telephoneMobile: string
  email: string
  contact1: PsychContact
  contact2: PsychContact
  forwardConsent: 'yes' | 'no' | ''
  signatureApplicantLastName: string
  signatureApplicantFirstName: string
  signatureApplicantDob: string
  signatureDate: string
  signatureApplicant: string
  isRepresentative: boolean
  representativeLastName: string
  representativeFirstName: string
  representativeDob: string
  representativeSignatureDate: string
  representativeSignature: string
  complaints: [PsychLineItem, PsychLineItem, PsychLineItem]
  diagnoses: [PsychLineItem, PsychLineItem, PsychLineItem]
  physicalIllnesses: string
  heightCm: number | null
  weightKg: number | null
  satisfiedWithWeight: 'yes' | 'no' | ''
  weightDissatisfactionReason: string
  problemChecklist: string[]
  problemOther: string
  suicidalThoughts: 'no' | 'yes' | ''
  suicideAttempts: 'no' | 'yes' | ''
  suicideAttemptLastWhen: string
  reasonForComplaints: string
  majorChangeBeforeOnset: string
  mostDifficultyInLife: string
  decisiveFactorForTherapy: string
  outpatientPsychotherapy: 'never' | 'previously' | 'currently' | ''
  outpatientPreviouslyYear: string
  outpatientCurrentlyWith: string
  medicalTreatment1: { withWhom: string; specialistField: string }
  medicalTreatment2: { withWhom: string; specialistField: string }
  inpatient1: { where: string; when: string }
  inpatient2: { where: string; when: string }
  inpatient3: { where: string; when: string }
  inpatient4: { where: string; when: string }
  gender: PsychFormGender
  genderSelfDescribe: string
  bornInPhilippines: 'philippines' | 'other' | ''
  birthCountryOther: string
  maritalStatus: string
  hasChildren: 'no' | 'yes' | ''
  childrenInfo: string
  housingSituation: 'alone' | 'partner' | 'parents' | 'alone_with_children' | 'shared_apartment' | 'no_permanent_housing' | 'institution' | ''
  housingInstitutionDescribe: string
  hasDebts: 'no' | 'yes' | ''
  debtsApprox: string
  schoolQualification: string
  schoolQualificationOther: string
  professionalQualification: string
  employmentStatus:
    | 'self_employed'
    | 'assisting_family_member'
    | 'civil_servant'
    | 'employee'
    | 'worker'
    | 'homemaker'
    | 'unemployed'
    | 'pension'
    | 'disability_pension'
    | 'student_school'
    | 'other'
    | ''
  selfEmployedLearnedProfession: string
  employeeCurrentActivity: string
  unemployedSince: string
  employmentOther: string
  unableToWork: 'no' | 'yes' | ''
  unableToWorkSince: string
  retired: 'no' | 'planning' | 'in_process' | 'old_age_pension' | 'temporary_pension' | ''
  partnership: 'no' | 'yes' | ''
  partnershipDescribe: string
  friendshipsDescribe: string
  leisureDescribe: string
  policeContact: string
  selfDescribe: string
  resources: string
  mother: {
    ageAtBirth: string
    profession: string
    deceased: 'no' | 'yes' | ''
    deceasedYear: string
    deceasedCause: string
    psychIllnesses: string
    personalityDescribe: string
    relationshipDescribe: string
  }
  father: {
    ageAtBirth: string
    profession: string
    deceased: 'no' | 'yes' | ''
    deceasedYear: string
    deceasedCause: string
    psychIllnesses: string
    personalityDescribe: string
    relationshipDescribe: string
  }
  parentalRelationship: string
  familyAtmosphere: string
  hasSiblings: 'no' | 'yes' | ''
  siblingsDetails: string
  siblingsRelationship: string
  lifeEventsPositive: string
  lifeEventsBurdensome: string
  sexualTrauma: 'no' | 'yes' | ''
  aggravatingCircumstances: 'no' | 'yes' | ''
  aggravatingCircumstancesDescribe: string
  exclusion: 'no' | 'yes' | ''
  exclusionWhatKind: string
  substances: {
    drugs: PsychSubstanceRow
    alcohol: PsychSubstanceRow
    tranquilizers: PsychSubstanceRow
    nicotine: PsychSubstanceRow
  }
  worriesDrugs: 'no' | 'yes' | ''
  worriesAlcohol: 'no' | 'yes' | ''
  worriesMedia: 'no' | 'yes' | ''
  mediaHoursPerDay: string
  medicationPlan: string
  goals: string
  selfHelpSoFar: string
  importance: Record<PsychImportanceKey, PsychImportanceValue>
  fearsWithTeam: string
  filledBy: 'self' | 'other' | ''
}

const emptyPsychForm = (): PsychFormState => ({
  applicantLastName: '',
  applicantFirstName: '',
  dateOfBirth: '',
  age: null,
  streetAddress: '',
  postalCodeCity: '',
  healthInsurance: '',
  privatePhysicianInInsurance: false,
  telephoneLandline: '',
  telephoneMobile: '',
  email: '',
  contact1: { name: '', address: '', telephone: '', email: '' },
  contact2: { name: '', address: '', telephone: '', email: '' },
  forwardConsent: '',
  signatureApplicantLastName: '',
  signatureApplicantFirstName: '',
  signatureApplicantDob: '',
  signatureDate: '',
  signatureApplicant: '',
  isRepresentative: false,
  representativeLastName: '',
  representativeFirstName: '',
  representativeDob: '',
  representativeSignatureDate: '',
  representativeSignature: '',
  complaints: [{ text: '', since: '' }, { text: '', since: '' }, { text: '', since: '' }],
  diagnoses: [{ text: '', since: '' }, { text: '', since: '' }, { text: '', since: '' }],
  physicalIllnesses: '',
  heightCm: null,
  weightKg: null,
  satisfiedWithWeight: '',
  weightDissatisfactionReason: '',
  problemChecklist: [],
  problemOther: '',
  suicidalThoughts: '',
  suicideAttempts: '',
  suicideAttemptLastWhen: '',
  reasonForComplaints: '',
  majorChangeBeforeOnset: '',
  mostDifficultyInLife: '',
  decisiveFactorForTherapy: '',
  outpatientPsychotherapy: '',
  outpatientPreviouslyYear: '',
  outpatientCurrentlyWith: '',
  medicalTreatment1: { withWhom: '', specialistField: '' },
  medicalTreatment2: { withWhom: '', specialistField: '' },
  inpatient1: { where: '', when: '' },
  inpatient2: { where: '', when: '' },
  inpatient3: { where: '', when: '' },
  inpatient4: { where: '', when: '' },
  gender: '',
  genderSelfDescribe: '',
  bornInPhilippines: '',
  birthCountryOther: '',
  maritalStatus: '',
  hasChildren: '',
  childrenInfo: '',
  housingSituation: '',
  housingInstitutionDescribe: '',
  hasDebts: '',
  debtsApprox: '',
  schoolQualification: '',
  schoolQualificationOther: '',
  professionalQualification: '',
  employmentStatus: '',
  selfEmployedLearnedProfession: '',
  employeeCurrentActivity: '',
  unemployedSince: '',
  employmentOther: '',
  unableToWork: '',
  unableToWorkSince: '',
  retired: '',
  partnership: '',
  partnershipDescribe: '',
  friendshipsDescribe: '',
  leisureDescribe: '',
  policeContact: '',
  selfDescribe: '',
  resources: '',
  mother: {
    ageAtBirth: '',
    profession: '',
    deceased: '',
    deceasedYear: '',
    deceasedCause: '',
    psychIllnesses: '',
    personalityDescribe: '',
    relationshipDescribe: '',
  },
  father: {
    ageAtBirth: '',
    profession: '',
    deceased: '',
    deceasedYear: '',
    deceasedCause: '',
    psychIllnesses: '',
    personalityDescribe: '',
    relationshipDescribe: '',
  },
  parentalRelationship: '',
  familyAtmosphere: '',
  hasSiblings: '',
  siblingsDetails: '',
  siblingsRelationship: '',
  lifeEventsPositive: '',
  lifeEventsBurdensome: '',
  sexualTrauma: '',
  aggravatingCircumstances: '',
  aggravatingCircumstancesDescribe: '',
  exclusion: '',
  exclusionWhatKind: '',
  substances: {
    drugs: { name: '', amountEarlier: '', amount6Months: '', lastConsumption: '' },
    alcohol: { name: '', amountEarlier: '', amount6Months: '', lastConsumption: '' },
    tranquilizers: { name: '', amountEarlier: '', amount6Months: '', lastConsumption: '' },
    nicotine: { name: '', amountEarlier: '', amount6Months: '', lastConsumption: '' },
  },
  worriesDrugs: '',
  worriesAlcohol: '',
  worriesMedia: '',
  mediaHoursPerDay: '',
  medicationPlan: '',
  goals: '',
  selfHelpSoFar: '',
  importance: {
    persistentSadnessDepression: '',
    anxietyPanicAttacks: '',
    eatingDisorderWeight: '',
    physicalComplaints: '',
    tinnitus: '',
    depressedMood: '',
    stressRegulation: '',
    socialWithdrawal: '',
    obsessiveThoughtsCompulsions: '',
    adhd: '',
    traumaPtsd: '',
    tensionSelfHarmPressure: '',
    chronicPain: '',
    sexuality: '',
    occupationalPerformance: '',
    misc: '',
  },
  fearsWithTeam: '',
  filledBy: '',
})

const psychForm = ref<PsychFormState>(emptyPsychForm())
const psychDraftSavedAt = ref<string | null>(null)
const savingPsychForm = ref(false)
const psychLoadingDraft = ref(false)
const psychAutosaveState = ref<'idle' | 'saving' | 'saved' | 'error'>('idle')
const psychUiPrefs = ref<{ fontScale: number; highContrast: boolean }>({ fontScale: 1, highContrast: false })
let psychAutosaveTimer: ReturnType<typeof setTimeout> | null = null
let psychSuppressAutosave = false

const psychAutosaveLabel = computed(() => {
  if (psychLoadingDraft.value) return 'Loading draft...'
  if (psychAutosaveState.value === 'saving') return 'Autosave: Saving...'
  if (psychAutosaveState.value === 'error') return 'Autosave: Error saving'
  if (psychDraftSavedAt.value) {
    try {
      const dt = new Date(psychDraftSavedAt.value)
      const stamp = Number.isNaN(dt.getTime()) ? String(psychDraftSavedAt.value) : dt.toLocaleString()
      return psychAutosaveState.value === 'saved' ? `Autosave: Saved ${stamp}` : `Last saved ${stamp}`
    } catch {
      return `Last saved ${psychDraftSavedAt.value}`
    }
  }
  return 'Autosave: Not saved yet'
})

const psychProblemOptions = [
  { label: 'Feelings of guilt', value: 'Feelings of guilt' },
  { label: 'Helplessness', value: 'Helplessness' },
  { label: 'Sleep disorders', value: 'Sleep disorders' },
  { label: 'Occupational problems', value: 'Occupational problems' },
  { label: 'Conflicts with others', value: 'Conflicts with others' },
  { label: 'Feelings of inferiority', value: 'Feelings of inferiority' },
  { label: 'Mood swings', value: 'Mood swings' },
  { label: 'Groundless persistent sadness', value: 'Groundless persistent sadness' },
  { label: 'Suicidal thoughts', value: 'Suicidal thoughts' },
  { label: 'Relationship problems', value: 'Relationship problems' },
  { label: 'Loss of libido', value: 'Loss of libido' },
  { label: 'Sexual problems', value: 'Sexual problems' },
  { label: 'Daydreaming', value: 'Daydreaming' },
  { label: 'Brooding/Ruminating', value: 'Brooding/Ruminating' },
  { label: 'Physical restlessness', value: 'Physical restlessness' },
  { label: 'Lack of exercise', value: 'Lack of exercise' },
  { label: 'Insomnia', value: 'Insomnia' },
  { label: 'Lump in the throat feeling', value: 'Lump in the throat feeling' },
  { label: 'Pain', value: 'Pain' },
  { label: 'Dizziness', value: 'Dizziness' },
  { label: 'Heart complaints', value: 'Heart complaints' },
  { label: 'Headaches', value: 'Headaches' },
  { label: 'Panic attacks', value: 'Panic attacks' },
  { label: 'Exam anxiety', value: 'Exam anxiety' },
  { label: 'Shyness', value: 'Shyness' },
  { label: 'Compulsions/Obsessions', value: 'Compulsions/Obsessions' },
  { label: 'Fear of being alone', value: 'Fear of being alone' },
  { label: 'Hypersensitivity', value: 'Hypersensitivity' },
  { label: 'Anger', value: 'Anger' },
  { label: 'Gambling addiction', value: 'Gambling addiction' },
  { label: 'Shopping addiction', value: 'Shopping addiction' },
  { label: 'Uncontrolled outbursts of anger', value: 'Uncontrolled outbursts of anger' },
  { label: 'Financial problems', value: 'Financial problems' },
  { label: 'Gastrointestinal complaints', value: 'Gastrointestinal complaints' },
  { label: 'Eating behavior disorders', value: 'Eating behavior disorders' },
  { label: 'Weight changes', value: 'Weight changes' },
  { label: 'Loss of appetite', value: 'Loss of appetite' },
  { label: 'Alcohol consumption', value: 'Alcohol consumption' },
  { label: 'Use of tranquilizers', value: 'Use of tranquilizers' },
  { label: 'Drug use', value: 'Drug use' },
  { label: 'Substance dependency', value: 'Substance dependency' },
  { label: 'Thoughts of persecution', value: 'Thoughts of persecution' },
  { label: 'Fear of people', value: 'Fear of people' },
]

const importanceOptions = [
  { label: 'Unimportant', value: 'unimportant' },
  { label: 'Less Important', value: 'less' },
  { label: 'Important', value: 'important' },
  { label: 'Very Important', value: 'very' },
  { label: 'Pre-urgent', value: 'preurgent' },
]

const psychImportanceAreas: Array<{ key: PsychImportanceKey; label: string }> = [
  { key: 'persistentSadnessDepression', label: 'Persistent sadness / depression' },
  { key: 'anxietyPanicAttacks', label: 'Anxiety / panic attacks' },
  { key: 'eatingDisorderWeight', label: 'Eating disorder / overweight / underweight' },
  { key: 'physicalComplaints', label: 'Physical complaints' },
  { key: 'tinnitus', label: 'Tinnitus' },
  { key: 'depressedMood', label: 'Depressed mood' },
  { key: 'stressRegulation', label: 'Stress regulation' },
  { key: 'socialWithdrawal', label: 'Social withdrawal / inhibition in social contacts' },
  { key: 'obsessiveThoughtsCompulsions', label: 'Obsessive thoughts / compulsions' },
  { key: 'adhd', label: 'ADHD (Attention-Deficit/Hyperactivity Disorder)' },
  { key: 'traumaPtsd', label: 'Trauma / post-traumatic stress disorder' },
  { key: 'tensionSelfHarmPressure', label: 'Handling tension / self-harm pressure' },
  { key: 'chronicPain', label: 'Chronic pain' },
  { key: 'sexuality', label: 'Sexuality' },
  { key: 'occupationalPerformance', label: 'Occupational performance' },
  { key: 'misc', label: 'Miscellaneous' },
]

const genderRadioOptions = [
  { label: 'Male', value: 'male' },
  { label: 'Female', value: 'female' },
  { label: 'Non-binary', value: 'non_binary' },
  { label: 'Prefer to self-describe', value: 'self_describe' },
  { label: 'Prefer not to say', value: 'prefer_not_to_say' },
]

const maritalStatusOptions = [
  { label: 'Single', value: 'Single' },
  { label: 'Married', value: 'Married' },
  { label: 'Separated', value: 'Separated' },
  { label: 'Divorced', value: 'Divorced' },
  { label: 'Widowed', value: 'Widowed' },
]

const housingSituationOptions = [
  { label: 'Living alone', value: 'alone' },
  { label: 'Living with partner', value: 'partner' },
  { label: 'Living with parents', value: 'parents' },
  { label: 'Living alone with child(ren)', value: 'alone_with_children' },
  { label: 'Shared apartment', value: 'shared_apartment' },
  { label: 'No permanent housing', value: 'no_permanent_housing' },
  { label: 'Living in an institution', value: 'institution' },
]

const schoolQualificationOptions = [
  { label: 'Basic secondary school qualification', value: 'basic_secondary' },
  { label: 'Intermediate secondary school qualification', value: 'intermediate_secondary' },
  { label: 'Higher secondary school / University entrance qualification', value: 'higher_secondary_university_entrance' },
  { label: 'Polytechnic secondary school qualification', value: 'polytechnic_secondary' },
  { label: 'Completed university studies', value: 'completed_university_studies' },
  { label: 'Other', value: 'other' },
]

const professionalQualificationOptions = [
  { label: 'Completed apprenticeship / vocational training', value: 'apprenticeship_vocational' },
  { label: 'University degree', value: 'university_degree' },
  { label: 'No professional qualification', value: 'no_professional_qualification' },
]

const employmentStatusOptions = [
  { label: 'Self-employed', value: 'self_employed' },
  { label: 'Assisting family member', value: 'assisting_family_member' },
  { label: 'Civil servant', value: 'civil_servant' },
  { label: 'Employee', value: 'employee' },
  { label: 'Worker', value: 'worker' },
  { label: 'Homemaker', value: 'homemaker' },
  { label: 'Unemployed', value: 'unemployed' },
  { label: "Pension (early retirement / old-age / survivor pension)", value: 'pension' },
  { label: 'Disability pension', value: 'disability_pension' },
  { label: 'Student / School', value: 'student_school' },
  { label: 'Other', value: 'other' },
]

const retiredOptions = [
  { label: 'No', value: 'no' },
  { label: 'Planning retirement', value: 'planning' },
  { label: 'Retirement application in process', value: 'in_process' },
  { label: 'Yes, receiving old-age pension', value: 'old_age_pension' },
  { label: 'Yes, receiving temporary pension', value: 'temporary_pension' },
]

const loadPsychDraft = async () => {
  psychDraftSavedAt.value = null
  psychAutosaveState.value = 'idle'
  if (!selectedPatient.value) {
    psychForm.value = emptyPsychForm()
    return
  }
  psychLoadingDraft.value = true
  psychSuppressAutosave = true
  try {
    const res = await api.get(`/users/nurse/patient/${selectedPatient.value.id}/psychiatric-opd/`)
    const payload = res.data?.data && typeof res.data.data === 'object' ? res.data.data : {}
    psychForm.value = { ...emptyPsychForm(), ...(payload as Partial<PsychFormState>) }
    psychDraftSavedAt.value = res.data?.updated_at || null
  } catch (e) {
    console.warn('Failed to load psychiatric form draft', e)
    psychForm.value = emptyPsychForm()
    $q.notify({ type: 'negative', message: 'Failed to load psychiatric form draft', position: 'top' })
  } finally {
    psychLoadingDraft.value = false
    setTimeout(() => { psychSuppressAutosave = false }, 0)
  }
}

const savePsychDraft = async (silent = false) => {
  if (!selectedPatient.value) {
    if (!silent) $q.notify({ type: 'negative', message: 'Select a patient first', position: 'top' })
    return
  }
  psychAutosaveState.value = 'saving'
  try {
    const res = await api.put(`/users/nurse/patient/${selectedPatient.value.id}/psychiatric-opd/`, { data: psychForm.value })
    psychDraftSavedAt.value = res.data?.updated_at || new Date().toISOString()
    psychAutosaveState.value = 'saved'
    if (!silent) $q.notify({ type: 'info', message: 'Draft saved', position: 'top' })
  } catch (e) {
    console.warn('Failed to save psychiatric draft', e)
    psychAutosaveState.value = 'error'
    if (!silent) $q.notify({ type: 'negative', message: 'Failed to save draft', position: 'top' })
  }
}

const savePsychSubmit = async () => {
  if (!selectedPatient.value) {
    $q.notify({ type: 'negative', message: 'Select a patient first', position: 'top' })
    return
  }
  savingPsychForm.value = true
  try {
    await savePsychDraft(true)
    await api.post(`/users/nurse/patient/${selectedPatient.value.id}/psychiatric-opd/submit/`)
    $q.notify({ type: 'positive', message: 'Psychiatric OPD questionnaire submitted', position: 'top' })
    formDialogOpen.value = false
  } finally {
    savingPsychForm.value = false
  }
}

const schedulePsychAutosave = () => {
  if (psychSuppressAutosave) return
  if (selectedForm.value !== 'psych') return
  if (!selectedPatient.value) return
  if (psychAutosaveTimer) clearTimeout(psychAutosaveTimer)
  psychAutosaveTimer = setTimeout(() => { void savePsychDraft(true) }, 700)
}

watch(psychForm, () => {
  schedulePsychAutosave()
}, { deep: true })

const loadPsychUiPrefs = () => {
  try {
    const raw = localStorage.getItem('psych_ui_prefs_v1')
    if (!raw) return
    const parsed = JSON.parse(raw) as { fontScale?: unknown; highContrast?: unknown }
    const fontScale = typeof parsed.fontScale === 'number' ? parsed.fontScale : 1
    const highContrast = typeof parsed.highContrast === 'boolean' ? parsed.highContrast : false
    psychUiPrefs.value = { fontScale, highContrast }
  } catch {
    psychUiPrefs.value = { fontScale: 1, highContrast: false }
  }
}

watch(psychUiPrefs, (v) => {
  localStorage.setItem('psych_ui_prefs_v1', JSON.stringify(v))
}, { deep: true })

loadPsychUiPrefs()

// Demographics state and helpers
type Demographics = {
  mrn?: string; firstName?: string; middleName?: string; lastName?: string;
  dob?: string; sex?: string; maritalStatus?: string; nationality?: string;
  homeAddress?: string; cellPhone?: string; homePhone?: string; email?: string;
  emergencyName?: string; emergencyRelationship?: string; emergencyPhone?: string;
  consultationLocation?: string; attendingPhysician?: string;
  hospitalName?: string; hospitalAddress?: string; hospitalPhone?: string; hospitalEmail?: string;
  reasonForVisit?: string; referringDoctor?: string; primaryCarePhysician?: string;
  currentMedications?: string; medicalHistory?: string;
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
  if (!val) return
  if (val === 'registration') {
    openRegistration()
    // keep selection so user sees current form
  } else {
    if (val === 'psych') {
      void loadPsychDraft()
    }
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

// Send records state
const sendDialogOpen = ref(false)
const sendingRecords = ref(false)
const sendSelectedDoctorId = ref<number | null>(null)
const sendMessage = ref('')
const sendPatientTarget = ref<PatientSummary | null>(null)

const sendDoctorOptions = computed(() => {
  const docs = (filteredAvailableDoctors.value || []) as unknown as Array<{ id?: number; full_name?: string; specialization?: string }>
  return docs
    .filter((d) => typeof d.id === 'number')
    .map((d) => ({
      label: `${d.full_name || 'Doctor'}${d.specialization ? ` — ${d.specialization}` : ''}`,
      value: d.id as number
    }))
})

function openSendDialog(patient: PatientSummary) {
  sendPatientTarget.value = patient
  sendSelectedDoctorId.value = null
  sendMessage.value = ''
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
      message: sendMessage.value
    })
    $q.notify({ type: 'positive', message: 'Patient records sent to doctor' })
    sendDialogOpen.value = false
  } catch (e) {
    console.error('Send patient records failed', e)
    $q.notify({ type: 'negative', message: 'Failed to send records. Please try again.' })
  } finally {
    sendingRecords.value = false
  }
}

function archiveFromSendDialog() {
  if (!sendPatientTarget.value) return
  void archivePatient(sendPatientTarget.value)
  sendDialogOpen.value = false
}

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
.form-body { max-height: 70vh; overflow-y: auto; }
.psych-form-container { font-size: calc(14px * var(--psych-font-scale, 1)); }
.psych-toolbar { min-height: 42px; }
.psych-high-contrast { color: #000; }
.psych-high-contrast :deep(.q-field__label) { color: #000; }
.psych-high-contrast :deep(.q-field__native), .psych-high-contrast :deep(.q-field__control) { color: #000; }
.psych-high-contrast :deep(.q-field--outlined .q-field__control:before) { border-color: #000; }
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
