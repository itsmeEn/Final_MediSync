<template>
  <q-layout view="hHh Lpr fFf" class="page-background">
    <NurseHeader @toggle-drawer="rightDrawerOpen = !rightDrawerOpen" />
    <NurseSidebar v-model="rightDrawerOpen" active-route="patient-archive" />

    <q-page-container class="page-container-with-fixed-header">
      <div class="patient-management-content">
        <!-- Greeting card: styled to match Appointment Calendar header (no icon) -->
        <q-card class="greeting-card">
          <q-card-section class="greeting-content">
            <div class="greeting-text">
              <h4 class="greeting-title">Patient Archive</h4>
              <p class="greeting-subtitle">Browse and export archived patient assessments</p>
            </div>
          </q-card-section>
        </q-card>

        <!-- Main archive card (search, results) -->
        <q-card class="white-card archive-card section-spacing">
          <q-card-section class="card-header">
            <div class="row items-center justify-between">
              <h5 class="card-title q-mb-none">Patient Archive</h5>
              <q-btn color="primary" icon="add" label="New Archive" @click="openCreateDialog" />
            </div>
          </q-card-section>

          <q-card-section class="card-content">
            <div class="row q-col-gutter-md q-mb-lg">
              <div class="col-12 col-md-6"><q-input v-model="archiveFilters.query" label="Patient Name or ID" outlined dense/></div>
              <div class="col-12 col-sm-6 col-md-3"><q-input v-model="archiveFilters.assessment_type" label="Assessment Type" outlined dense/></div>
              <div class="col-12 col-sm-6 col-md-3"><q-input v-model="archiveFilters.medical_condition" label="Medical Condition" outlined dense/></div>
            </div>
            <div class="row q-col-gutter-md q-mb-md">
              <div class="col-12 col-sm-6 col-md-3"><q-input v-model="archiveFilters.start_date" label="Start Date" type="date" outlined dense/></div>
              <div class="col-12 col-sm-6 col-md-3"><q-input v-model="archiveFilters.end_date" label="End Date" type="date" outlined dense/></div>
              <div class="col-12 col-sm-6 col-md-3"><q-btn color="primary" icon="search" label="Search" class="full-width" :loading="archivesLoading" @click="searchArchives"/></div>
            </div>

            <q-inner-loading :showing="archivesLoading"><q-spinner color="primary"/></q-inner-loading>

            <div v-if="!archivesLoading && archivedRecords.length === 0" class="empty-section">
              <q-icon name="inventory_2" size="48px" color="grey-5" />
              <p class="empty-text">No archived records</p>
            </div>

            <q-list v-else bordered separator>
              <q-item v-for="rec in archivedRecords" :key="rec.id">
                <q-item-section>
                  <q-item-label>{{ rec.patient_name }} — {{ rec.assessment_type }} · {{ formatDateDisplay(rec.last_assessed_at) }}</q-item-label>
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
              <q-btn outline color="primary" icon="file_download" label="Export Results" @click="exportFilteredArchives"/>
            </div>

            <q-dialog v-model="showArchiveDetail">
              <q-card style="max-width: 1000px; width: 90vw">
                <q-card-section>
                  <div class="text-h6">Archived Assessment</div>
                </q-card-section>
                <q-separator/>
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
                      <!-- No Overview section per request -->
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
                <q-separator/>
                <q-card-actions align="right">
                  <q-btn flat label="Close" color="primary" v-close-popup/>
                  <q-btn flat label="Edit" color="primary" :disable="!selectedArchive" @click="openEditDialog"/>
                  <q-btn flat label="Unarchive" color="warning" :disable="!selectedArchive" @click="unarchiveSelected"/>
                  <q-btn flat label="Export" color="secondary" @click="selectedArchive && exportArchive(selectedArchive)"/>
                </q-card-actions>
              </q-card>
            </q-dialog>
            <q-dialog v-model="showCreateDialog">
              <q-card style="max-width: 700px; width: 90vw">
                <q-card-section>
                  <div class="text-h6">Create Archive</div>
                </q-card-section>
                <q-separator/>
                <q-card-section class="q-gutter-md">
                  <q-input v-model="createForm.patient_id" label="Patient ID" outlined dense/>
                  <q-input v-model="createForm.assessment_type" label="Assessment Type" outlined dense/>
                  <q-input v-model="createForm.medical_condition" label="Medical Condition" outlined dense/>
                  <q-input v-model="createForm.hospital_name" label="Hospital Name" outlined dense/>
                  <q-input v-model="createForm.assessment_data" type="textarea" label="Assessment Data (JSON)" outlined dense autogrow/>
                </q-card-section>
                <q-separator/>
                <q-card-actions align="right">
                  <q-btn flat label="Cancel" color="primary" v-close-popup/>
                  <q-btn flat label="Save" color="primary" :loading="createLoading" @click="createArchive"/>
                </q-card-actions>
              </q-card>
            </q-dialog>
            <q-dialog v-model="showEditDialog">
              <q-card style="max-width: 700px; width: 90vw">
                <q-card-section>
                  <div class="text-h6">Edit Archive</div>
                </q-card-section>
                <q-separator/>
                <q-card-section class="q-gutter-md">
                  <q-input v-model="editForm.assessment_type" label="Assessment Type" outlined dense/>
                  <q-input v-model="editForm.medical_condition" label="Medical Condition" outlined dense/>
                  <q-input v-model="editForm.hospital_name" label="Hospital Name" outlined dense/>
                  <q-input v-model="editForm.assessment_data" type="textarea" label="Assessment Data (JSON)" outlined dense autogrow/>
                </q-card-section>
                <q-separator/>
                <q-card-actions align="right">
                  <q-btn flat label="Cancel" color="primary" v-close-popup/>
                  <q-btn flat label="Update" color="primary" :loading="editLoading" @click="updateArchive"/>
                </q-card-actions>
              </q-card>
            </q-dialog>
          </q-card-section>
        </q-card>
      </div>
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useQuasar } from 'quasar'
import NurseHeader from 'components/NurseHeader.vue'
import NurseSidebar from 'components/NurseSidebar.vue'
import { api } from 'boot/axios'
import { normalizeAssessmentData, formatSectionRows } from 'src/utils/archiveFormat'

// Sidebar state
const rightDrawerOpen = ref(false)

// Archive state and methods
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

const $q = useQuasar()
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
  end_date: ''
})

const formatDateDisplay = (dateStr: string): string => {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  return d.toLocaleString()
}

// Build human-readable computed rows (omit the Overview section per request)
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
    a.download = `archive_${rec.id}.pdf`
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
    const res = await api.get('/operations/archives/export/', { params: buildArchiveParams(), responseType: 'blob' })
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

// Create/Edit/Unarchive logic
const showCreateDialog = ref(false)
const createLoading = ref(false)
const createForm = ref<{ patient_id: string; assessment_type: string; medical_condition: string; hospital_name: string; assessment_data: string }>({
  patient_id: '',
  assessment_type: '',
  medical_condition: '',
  hospital_name: '',
  assessment_data: ''
})

const openCreateDialog = () => { showCreateDialog.value = true }

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
      try { parsed = JSON.parse(createForm.value.assessment_data) } catch {
        $q.notify({ type: 'negative', message: 'Assessment Data must be valid JSON', position: 'top' })
        return
      }
    }
    const payload = {
      patient_id: pid,
      assessment_type: createForm.value.assessment_type || 'General',
      medical_condition: createForm.value.medical_condition || '',
      hospital_name: createForm.value.hospital_name || '',
      assessment_data: parsed
    }
    await api.post('/operations/archives/create/', payload);
    $q.notify({ type: 'positive', message: 'Archive created', position: 'top' })
    showCreateDialog.value = false
    await searchArchives()
    createForm.value = { patient_id: '', assessment_type: '', medical_condition: '', hospital_name: '', assessment_data: '' }
  } catch (err) {
    console.error('Create archive failed:', err)
    let msg = 'Create archive failed'
    const e = err as { response?: { data?: { error?: unknown } }, message?: unknown }
    const apiErr = e?.response?.data?.error
    if (typeof apiErr === 'string' && apiErr.trim()) {
      msg = apiErr
    } else if (apiErr) {
      try { msg = JSON.stringify(apiErr) } catch { msg = 'Create archive failed' }
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
const editForm = ref<{ assessment_type: string; medical_condition: string; hospital_name: string; assessment_data: string }>({
  assessment_type: '',
  medical_condition: '',
  hospital_name: '',
  assessment_data: ''
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
      try { parsed = JSON.parse(editForm.value.assessment_data) } catch {
        $q.notify({ type: 'negative', message: 'Assessment Data must be valid JSON', position: 'top' })
        return
      }
    }
    const payload = {
      assessment_type: editForm.value.assessment_type,
      medical_condition: editForm.value.medical_condition,
      hospital_name: editForm.value.hospital_name,
      assessment_data: parsed
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
      try { msg = JSON.stringify(apiErr) } catch { msg = 'Update archive failed' }
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
      try { msg = JSON.stringify(apiErr) } catch { msg = 'Unarchive failed' }
    } else if (typeof e?.message === 'string' && e.message.trim()) {
      msg = e.message
    }
    $q.notify({ type: 'negative', message: msg, position: 'top' })
  }
}

// Auto-load archives on page mount
onMounted(() => {
  // Load with current (empty) filters so users immediately see data
  void searchArchives()
})
</script>

<style scoped>
/* Page background */
.page-background {
  background: #f6f7f8;
  min-height: 100vh;
  background-size: cover;
}

/* Keep header space */
.page-container-with-fixed-header {
  padding-top: 50px;
}

.patient-management-content {
  max-width: none;        
  width: 100%;
  margin: 0;
  padding: 18px 28px;     
  box-sizing: border-box;
}

.greeting-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 22px 24px;
  box-shadow: 0 6px 24px rgba(17, 24, 39, 0.06);
  border: 1px solid rgba(0,0,0,0.04);
  position: relative;
  margin: 0 0 22px 0;
  overflow: visible;
  width: 100%;
}

/* Decorative thin top bar (matches the Appointment Calendar look) */
.greeting-card::before {
  content: "";
  position: absolute;
  left: 12px;
  right: 12px;
  top: 8px;
  height: 6px;
  border-radius: 6px;
  background: linear-gradient(90deg, rgba(40,102,96,0.95), rgba(46,153,124,0.6));
  opacity: 0.95;
  pointer-events: none;
  box-shadow: 0 2px 6px rgba(46,153,124,0.06);
}

.greeting-content {
  display: flex;
  align-items: flex-start;
  justify-content: flex-start;
  gap: 16px;
  position: relative;
  z-index: 1;
}

.greeting-text { padding: 6px 0; }
.greeting-title {
  font-size: 24px;
  margin: 0;
  color: #1f3f3a;
  font-weight: 700;
}
.greeting-subtitle {
  margin: 10px 0 0;
  color: #6b7a77;
  font-size: 14px;
}

/* Main white card (archive area) - stretch full width of parent */
.white-card {
  background: linear-gradient(180deg, #ffffff, #fcfdfd);
  border-radius: 12px;
  box-shadow: 0 10px 32px rgba(11,22,23,0.06);
  overflow: hidden;
  margin: 0;
  padding: 28px;
  width: 100%;
  border: 1px solid rgba(0,0,0,0.04);
  box-sizing: border-box;
}

/* Slightly larger inner spacing so controls appear wide and airy */
.card-header .card-title {
  font-size: 18px;
  font-weight: 700;
  color: #2a4b46;
  margin-bottom: 18px;
}
.card-content {
  padding-top: 8px;
}

/* empty state */
.empty-section {
  text-align: center;
  padding: 48px 0;
}
.empty-text {
  color: #8a9592;
}

/* Responsive fallbacks */
@media (max-width: 1100px) {
  .patient-management-content { 
    padding: 16px; 
  }
}
@media (max-width: 640px) {
  .greeting-title { 
    font-size: 20px; 
  }
  .greeting-subtitle { 
    font-size: 13px; 
  }
  .patient-management-content { 
    padding: 12px; 
  }
  .white-card { 
    padding: 16px; 
  }
}
</style>