<template>
  <q-layout view="hHh Lpr fFf">
    <q-page class="q-pa-md role-body-bg">
      <div class="queue-management-page">
        <div class="page-header">
          <h2 class="page-title">Nurse Queue Management</h2>
          <p class="page-subtitle">Manage patient queues, remove entries, and mark served.</p>
        </div>

        <div class="actions row q-gutter-sm q-mb-md">
          <div class="col-auto">
            <q-select
              v-model="selectedDepartment"
              :options="departmentOptions"
              label="Department"
              emit-value
              map-options
              outlined
              dense
              class="dept-select"
            />
          </div>
          <div class="col-auto">
            <q-btn color="primary" icon="play_arrow" label="Start Next" @click="startNext" :loading="starting"/>
          </div>
          <div class="col-auto">
            <q-btn color="secondary" icon="refresh" label="Refresh" @click="fetchQueues" :loading="loading"/>
          </div>
        </div>

        <div class="row q-col-gutter-md">
          <div class="col-12 col-md-6">
            <q-card>
              <q-card-section>
                <div class="row items-center">
                  <q-icon name="priority_high" color="red" size="20px" class="q-mr-sm" />
                  <div class="text-h6 text-weight-bold">Priority Queue</div>
                  <q-space />
                  <q-badge color="red" :label="`${priorityQueue.length} waiting`" />
                </div>
              </q-card-section>
              <q-separator />
              <q-card-section>
                <q-list separator>
                  <q-item v-for="p in priorityQueue" :key="`prio-${p.queue_number}`">
                    <q-item-section avatar>
                      <q-avatar color="red" text-color="white">P</q-avatar>
                    </q-item-section>
                    <q-item-section>
                      <q-item-label class="text-weight-medium">{{ p.patient_name }} — #{{ p.queue_number }}</q-item-label>
                      <q-item-label caption>
                        {{ p.department }} • Position: {{ p.priority_position ?? '—' }} • Status: {{ p.status }}
                      </q-item-label>
                    </q-item-section>
                    <q-item-section side>
                      <div class="row q-gutter-xs">
                        <q-btn dense color="negative" icon="delete" @click="removeEntry(p, 'priority')"/>
                        <q-btn dense color="positive" icon="done_all" @click="markServed(p, 'priority')"/>
                      </div>
                    </q-item-section>
                  </q-item>
                  <q-item v-if="priorityQueue.length === 0">
                    <q-item-section class="text-center">No priority patients</q-item-section>
                  </q-item>
                </q-list>
              </q-card-section>
            </q-card>
          </div>

          <div class="col-12 col-md-6">
            <q-card>
              <q-card-section>
                <div class="row items-center">
                  <q-icon name="groups" color="teal" size="20px" class="q-mr-sm" />
                  <div class="text-h6 text-weight-bold">Normal Queue</div>
                  <q-space />
                  <q-badge color="teal" :label="`${normalQueue.length} waiting`" />
                </div>
              </q-card-section>
              <q-separator />
              <q-card-section>
                <q-list separator>
                  <q-item v-for="n in normalQueue" :key="`norm-${n.queue_number}`">
                    <q-item-section avatar>
                      <q-avatar color="teal" text-color="white">N</q-avatar>
                    </q-item-section>
                    <q-item-section>
                      <q-item-label class="text-weight-medium">{{ n.patient_name }} — #{{ n.queue_number }}</q-item-label>
                      <q-item-label caption>
                        {{ n.department }} • Position: {{ n.position_in_queue ?? '—' }} • Status: {{ n.status }}
                      </q-item-label>
                    </q-item-section>
                    <q-item-section side>
                      <div class="row q-gutter-xs">
                        <q-btn dense color="negative" icon="delete" @click="removeEntry(n, 'normal')"/>
                        <q-btn dense color="positive" icon="done_all" @click="markServed(n, 'normal')"/>
                      </div>
                    </q-item-section>
                  </q-item>
                  <q-item v-if="normalQueue.length === 0">
                    <q-item-section class="text-center">No normal patients</q-item-section>
                  </q-item>
                </q-list>
              </q-card-section>
            </q-card>
          </div>
        </div>
      </div>
    </q-page>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'src/boot/axios'

const $q = useQuasar()

// Department selection
// Updated to use shared department options to match Appointment system
import type { DepartmentOption } from '../utils/departments'
import { unifyDepartmentOptions } from '../utils/departments'
// Queue-enabled defaults; preserve legacy queue departments
const queueDefaultDepartments: DepartmentOption[] = [
  { label: 'Out Patient Department', value: 'OPD' },
  { label: 'Pharmacy', value: 'Pharmacy' },
  { label: 'Appointment', value: 'Appointment' }
]
const departmentOptions = ref<DepartmentOption[]>(queueDefaultDepartments)
const selectedDepartment = ref<string>(departmentOptions.value[0]?.value || 'OPD')

interface NurseQueueEntry {
  id?: number | string
  queue_number?: number | string
  patient_name?: string
  department?: string
  status?: string
  priority_position?: number
  position_in_queue?: number
}

const loading = ref(false)
const starting = ref(false)

// Queues
const priorityQueue = ref<NurseQueueEntry[]>([])
const normalQueue = ref<NurseQueueEntry[]>([])

// Fetch queues for the selected department only (segregated view)
const fetchQueues = async () => {
  loading.value = true
  try {
    const res = await api.get('/operations/nurse/queue/patients/', {
      params: { department: selectedDepartment.value }
    })
    priorityQueue.value = Array.isArray(res.data?.priority_queue) ? res.data.priority_queue : []
    normalQueue.value = Array.isArray(res.data?.normal_queue) ? res.data.normal_queue : []
  } catch {
    $q.notify({ type: 'negative', message: 'Failed to fetch queues' })
  } finally {
    loading.value = false
  }
}

const removeEntry = async (entry: NurseQueueEntry, queueType: 'normal' | 'priority') => {
  try {
    await api.post('/operations/nurse/queue/remove/', {
      entry_id: entry.id || entry.queue_number, // id preferred; fall back to number
      queue_type: queueType,
      department: selectedDepartment.value
    })
    $q.notify({ type: 'positive', message: 'Entry removed' })
    await fetchQueues()
  } catch {
    $q.notify({ type: 'negative', message: 'Failed to remove entry' })
  }
}

const markServed = async (entry: NurseQueueEntry, queueType: 'normal' | 'priority') => {
  try {
    await api.post('/operations/nurse/queue/mark-served/', {
      entry_id: entry.id || entry.queue_number,
      queue_type: queueType,
      department: selectedDepartment.value
    })
    $q.notify({ type: 'positive', message: 'Marked as served' })
    await fetchQueues()
  } catch {
    $q.notify({ type: 'negative', message: 'Failed to mark served' })
  }
}

// Start next patient for the selected department
const startNext = async () => {
  starting.value = true
  try {
    const res = await api.post('/operations/queue/start-processing/', {
      department: selectedDepartment.value
    })
    try {
      if (res?.data?.patient_profile) {
        const payload = { ...res.data.patient_profile, department: res.data?.department || selectedDepartment.value }
        localStorage.setItem('current_serving_patient', JSON.stringify(payload))
      }
    } catch (e) {
      console.warn('Failed to persist current serving patient from QueueManagement', e)
    }
    const served = res.data?.current_serving
    $q.notify({ type: 'positive', message: served ? `Started patient #${served}` : 'No patients waiting' })
    await fetchQueues()
  } catch {
    $q.notify({ type: 'negative', message: 'Failed to start next patient' })
  } finally {
    starting.value = false
  }
}

// Load hospital departments to ensure alignment with Appointment system
const loadHospitalDepartments = async () => {
  try {
    const res = await api.get('/operations/hospital/departments/')
    const raw = Array.isArray(res.data?.departments) ? res.data.departments : []
    departmentOptions.value = unifyDepartmentOptions(queueDefaultDepartments, raw as Array<string | { value?: string; label?: string }>)
    if (!departmentOptions.value.find(d => d.value === selectedDepartment.value)) {
      selectedDepartment.value = departmentOptions.value[0]?.value || 'OPD'
    }
  } catch (e) {
    console.warn('Failed to load hospital departments, using defaults:', e)
    departmentOptions.value = queueDefaultDepartments
    try {
      $q.notify({ type: 'warning', message: 'Loading default departments due to fetch error' })
    } catch (notifyErr) {
      console.debug('Notification fallback failed in NurseQueueManagement:', notifyErr)
    }
    if (!departmentOptions.value.find(d => d.value === selectedDepartment.value)) {
      selectedDepartment.value = departmentOptions.value[0]?.value || 'OPD'
    }
  }
}

onMounted(async () => {
  await loadHospitalDepartments()
  await fetchQueues()
})

// Refetch when department changes
import { watch } from 'vue'
watch(selectedDepartment, async () => {
  await fetchQueues()
})
</script>

<style scoped>
.queue-management-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.page-header { display: flex; flex-direction: column; gap: 8px; }
.page-title { font-size: 1.5rem; font-weight: 700; color: #333; }
.page-subtitle { font-size: 1rem; color: #607d8b; }
.actions { align-items: center; }
.dept-select { min-width: 240px; }
</style>
