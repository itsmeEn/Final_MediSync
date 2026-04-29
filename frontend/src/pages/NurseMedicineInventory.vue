<template>
  <q-layout view="hHh Lpr fFf">
    <NurseHeader
      :search-text="searchText"
      :search-results="searchResults"
      :unread-notifications-count="unreadNotificationsCount"
      :current-time="currentTime"
      :weather-data="weatherData"
      :weather-loading="weatherLoading"
      :weather-error="weatherError"
      :location-data="locationData"
      :location-loading="locationLoading"
      @toggle-drawer="toggleRightDrawer"
      @search-input="onSearchInput"
      @clear-search="clearSearch"
      @select-search-result="selectSearchResult"
      @show-notifications="showNotifications = true"
    />
    <NurseSidebar v-model="rightDrawerOpen" :activeRoute="'nurse-medicine-inventory'" />

    <q-page-container class="page-container-with-fixed-header role-body-bg">
      <!-- Greeting Section -->
      <div class="greeting-section">
        <q-card class="greeting-card">
          <q-card-section class="greeting-content">
            <h2 class="greeting-text">Medicine Inventory</h2>
            <p class="greeting-subtitle">
              Track and manage your medicine stock, monitor expiry dates, and ensure adequate supply
              for patient care - {{ currentDate }}
            </p>
          </q-card-section>
        </q-card>
      </div>

      <div class="page-content">
        <!-- Search and Filters -->
        <q-card class="search-filters-card">
          <q-card-section>
            <div class="row q-gutter-md items-center">
              <div class="col-12 col-md-4">
                <q-input
                  v-model="searchQuery"
                  placeholder="Search medicines..."
                  outlined
                  dense
                  clearable
                >
                  <template v-slot:prepend>
                    <q-icon name="search" />
                  </template>
                </q-input>
              </div>
              <div class="col-12 col-md-3">
                <q-select
                  v-model="categoryFilter"
                  :options="medicineCategories"
                  label="Category"
                  outlined
                  dense
                  clearable
                  emit-value
                  map-options
                />
              </div>
              <div class="col-12 col-md-3">
                <q-select
                  v-model="stockFilter"
                  :options="stockLevels"
                  label="Stock Level"
                  outlined
                  dense
                  clearable
                  emit-value
                  map-options
                />
              </div>
              <div class="col-12 col-md-2">
                <q-btn
                  color="secondary"
                  label="Filter"
                  icon="filter_list"
                  @click="applyFilters"
                  class="full-width"
                />
              </div>
              <div class="col-12 col-md-2">
                <q-btn
                  color="primary"
                  label="Add Medicine"
                  icon="add"
                  @click="handleAddMedicineClick"
                  :disable="!isUserVerified"
                  class="full-width"
                />
                <q-tooltip v-if="!isUserVerified">
                  Account verification required to manage medicine inventory
                </q-tooltip>
              </div>
            </div>
          </q-card-section>
        </q-card>

        <!-- Inventory Statistics -->
        <div class="stats-section">
          <div class="stats-grid">
            <q-card class="stat-card total-medicines" clickable>
              <q-card-section class="card-content">
                <div class="card-text">
                  <div class="card-title">Total Medicines</div>
                  <div class="card-description">All medicines in inventory</div>
                  <div class="card-value">{{ inventoryStats.totalMedicines }}</div>
                </div>
                <div class="card-icon">
                  <q-icon name="medication" size="2.5rem" />
                </div>
              </q-card-section>
            </q-card>

            <q-card class="stat-card low-stock" clickable>
              <q-card-section class="card-content">
                <div class="card-text">
                  <div class="card-title">Low Stock Items</div>
                  <div class="card-description">Below minimum stock</div>
                  <div class="card-value">{{ inventoryStats.lowStock }}</div>
                </div>
                <div class="card-icon">
                  <q-icon name="warning" size="2.5rem" />
                </div>
              </q-card-section>
            </q-card>

            <q-card class="stat-card out-of-stock" clickable>
              <q-card-section class="card-content">
                <div class="card-text">
                  <div class="card-title">Out of Stock</div>
                  <div class="card-description">Currently unavailable</div>
                  <div class="card-value">{{ inventoryStats.outOfStock }}</div>
                </div>
                <div class="card-icon">
                  <q-icon name="error" size="2.5rem" />
                </div>
              </q-card-section>
            </q-card>

            <q-card class="stat-card expiring-soon" clickable>
              <q-card-section class="card-content">
                <div class="card-text">
                  <div class="card-title">Expiring Soon</div>
                  <div class="card-description">Near expiry</div>
                  <div class="card-value">{{ inventoryStats.expiringSoon }}</div>
                </div>
                <div class="card-icon">
                  <q-icon name="schedule" size="2.5rem" />
                </div>
              </q-card-section>
            </q-card>
          </div>
        </div>

        <!-- Medicine Inventory Table -->
        <!-- Medicine Inventory Table -->
        <q-card class="inventory-table-card">
          <q-card-section>
            <div class="row items-center q-mb-md">
              <h6 class="text-h6 q-mb-none">Medicine Inventory</h6>
              <q-space />
              <q-btn
                color="primary"
                label="Export"
                icon="download"
                size="sm"
                @click="exportInventory"
              />
            </div>

            <q-table
              :rows="filteredMedicines"
              :columns="columns"
              row-key="id"
              :pagination="pagination"
              :loading="loading"
              class="inventory-table"
            >
              <!-- Stock Level Column -->
              <template v-slot:body-cell-stockLevel="props">
                <q-td :props="props">
                  <q-chip
                    :color="getStockLevelColor(props.value)"
                    text-color="white"
                    :label="props.value"
                    size="sm"
                  />
                </q-td>
              </template>

              <!-- Expiry Date Column -->
              <template v-slot:body-cell-expiryDate="props">
                <q-td :props="props">
                  <span :class="getExpiryDateClass(props.value)">
                    {{ formatDate(props.value) }}
                  </span>
                </q-td>
              </template>

              <!-- Actions Column -->
              <template v-slot:body-cell-actions="props">
                <q-td :props="props">
                  <div class="row q-gutter-xs">
                    <q-btn
                      round
                      flat
                      dense
                      color="primary"
                      icon="edit"
                      @click="editMedicine(props.row)"
                      size="sm"
                    >
                      <q-tooltip>Edit Medicine</q-tooltip>
                    </q-btn>
                    <q-btn
                      round
                      flat
                      dense
                      color="secondary"
                      icon="inventory"
                      @click="dispenseMedicine(props.row)"
                      size="sm"
                    >
                      <q-tooltip>Dispense</q-tooltip>
                    </q-btn>
                    <q-btn
                      round
                      flat
                      dense
                      color="accent"
                      icon="add_shopping_cart"
                      @click="restockMedicine(props.row)"
                      size="sm"
                    >
                      <q-tooltip>Restock</q-tooltip>
                    </q-btn>
                  </div>
                </q-td>
              </template>
            </q-table>
          </q-card-section>
        </q-card>

        <!-- Notifications Panel -->
        <q-card class="notifications-card" v-if="notifications.length > 0">
          <q-card-section>
            <div class="row items-center q-mb-md">
              <h6 class="text-h6 q-mb-none">Stock Alerts & Notifications</h6>
              <q-space />
              <q-btn
                color="primary"
                label="Mark All Read"
                icon="check_all"
                size="sm"
                @click="markAllNotificationsRead"
              />
            </div>

            <div class="notifications-list">
              <div
                v-for="notification in notifications"
                :key="notification.id"
                class="notification-item"
                :class="{ unread: !notification.isRead, read: notification.isRead }"
                @click="viewNotification(notification)"
              >
                <div class="notification-icon">
                  <q-icon
                    :name="getNotificationIcon(notification.type)"
                    :color="getNotificationColor(notification.type)"
                    size="md"
                  />
                </div>
                <div class="notification-content">
                  <div class="notification-message">{{ notification.message }}</div>
                  <div class="notification-time">
                    {{ formatNotificationTime(notification.timestamp) }}
                  </div>
                </div>
                <div class="notification-actions">
                  <q-btn
                    round
                    flat
                    dense
                    color="primary"
                    icon="visibility"
                    @click.stop="viewNotification(notification)"
                    size="sm"
                  >
                    <q-tooltip>View Details</q-tooltip>
                  </q-btn>
                  <q-btn
                    round
                    flat
                    dense
                    color="positive"
                    icon="check"
                    @click.stop="markNotificationRead(notification)"
                    size="sm"
                    v-if="!notification.isRead"
                  >
                    <q-tooltip>Mark as Read</q-tooltip>
                  </q-btn>
                </div>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Add/Edit Medicine Dialog -->
      <q-dialog v-model="showAddDialog" persistent>
        <q-card class="medicine-modal">
          <q-card-section class="modal-header">
            <div class="modal-title">
              <q-icon name="medication" size="md" class="title-icon" />
              {{ editingMedicine ? 'Edit Medicine' : 'Add New Medicine' }}
            </div>
            <q-btn flat round icon="close" @click="cancelEdit" class="close-btn" />
          </q-card-section>

          <q-card-section class="modal-content">
            <div class="form-fields">
              <div class="form-row">
                <q-input
                  v-model="medicineForm.name"
                  label="Medicine Name"
                  outlined
                  class="form-input"
                  :rules="[(val) => !!val || 'Name is required']"
                />
              </div>
              <div class="form-row">
                <q-input
                  v-model="medicineForm.genericName"
                  label="Generic Name"
                  outlined
                  class="form-input"
                />
              </div>
              <div class="form-row">
                <q-select
                  v-model="medicineForm.category"
                  :options="medicineCategories"
                  label="Category"
                  outlined
                  class="form-input"
                  emit-value
                  map-options
                  :rules="[(val) => !!val || 'Category is required']"
                />
              </div>
              <div class="form-row">
                <q-input
                  v-model="medicineForm.dosage"
                  label="Dosage Form"
                  outlined
                  class="form-input"
                  placeholder="e.g., Tablet, Syrup, Injection"
                />
              </div>
              <div class="form-row">
                <q-input
                  v-model.number="medicineForm.strength"
                  label="Strength"
                  outlined
                  class="form-input"
                  placeholder="e.g., 500mg, 10ml"
                />
              </div>
              <div class="form-row">
                <q-input
                  v-model.number="medicineForm.quantity"
                  label="Quantity"
                  type="number"
                  outlined
                  class="form-input"
                  :rules="[(val) => val >= 0 || 'Quantity must be non-negative']"
                />
              </div>
              <div class="form-row">
                <q-input
                  v-model="medicineForm.unit"
                  label="Unit"
                  outlined
                  class="form-input"
                  placeholder="e.g., tablets, bottles, vials"
                />
              </div>
              <div class="form-row">
                <q-input
                  v-model="medicineForm.expiryDate"
                  label="Expiry Date"
                  type="date"
                  outlined
                  class="form-input"
                  :rules="[(val) => !!val || 'Expiry date is required']"
                />
              </div>
              <div class="form-row">
                <q-input
                  v-model.number="medicineForm.minStockLevel"
                  label="Minimum Stock Level"
                  type="number"
                  outlined
                  class="form-input"
                  :rules="[(val) => val >= 0 || 'Minimum stock must be non-negative']"
                />
              </div>
              <div class="form-row">
                <q-input
                  v-model.number="medicineForm.unitPrice"
                  label="Unit Price"
                  type="number"
                  outlined
                  class="form-input"
                  placeholder="0.00"
                  step="0.01"
                  :rules="[(val) => val >= 0 || 'Unit price must be non-negative']"
                />
              </div>
              <div class="form-row">
                <q-input
                  v-model="medicineForm.batchNumber"
                  label="Batch Number"
                  outlined
                  class="form-input"
                  placeholder="e.g., BATCH-2024-001"
                />
              </div>
              <div class="form-row">
                <q-input
                  v-model="medicineForm.description"
                  label="Description"
                  type="textarea"
                  outlined
                  class="form-input"
                  rows="3"
                />
              </div>
            </div>
          </q-card-section>

          <q-card-actions class="modal-actions">
            <q-btn flat label="Cancel" color="grey-7" @click="cancelEdit" class="cancel-btn" />
            <q-btn
              :label="editingMedicine ? 'Update Medicine' : 'Add Medicine'"
              color="primary"
              @click="saveMedicine"
              :loading="saving"
              class="save-btn"
              icon="save"
            />
          </q-card-actions>
        </q-card>
      </q-dialog>

      <!-- Dispense Medicine Dialog -->
      <q-dialog v-model="showDispenseDialog" persistent>
        <q-card class="dispense-modal-card">
          <q-card-section class="dispense-header row items-center">
            <div class="col">
              <div class="dispense-title">Dispense Medicine</div>
              <div class="med-info">
                <q-icon name="medication" color="primary" class="med-icon" />
                <div class="med-texts">
                  <div class="med-name">{{ selectedMedicine?.name || 'Unknown Medicine' }}</div>
                  <div class="med-meta">
                    <span>Strength: {{ selectedMedicine?.strength || 'N/A' }}</span>
                    <span>Stock: {{ selectedMedicine?.quantity || 0 }}</span>
                    <span>Expiry: {{ selectedMedicine?.expiryDate || 'N/A' }}</span>
                  </div>
                </div>
              </div>
            </div>
            <q-space />
            <q-btn icon="close" flat round dense v-close-popup class="close-btn" />
          </q-card-section>

          <q-card-section class="form-grid">
            <div class="row q-col-gutter-md">
              <div class="col-12">
                <q-input
                  v-model="dispenseForm.patientName"
                  label="Patient Name"
                  outlined
                  dense
                  :rules="[(val) => !!val || 'Patient name is required']"
                />
              </div>

              <div class="col-12 col-sm-6">
                <q-input
                  v-model.number="dispenseForm.quantity"
                  label="Quantity to Dispense"
                  type="number"
                  outlined
                  dense
                  :min="1"
                  :max="selectedMedicine?.quantity || 0"
                  :rules="[
                    (val) => !!val || 'Quantity is required',
                    (val) => Number(val) > 0 || 'Enter a quantity greater than 0',
                    (val) => Number(val) <= (selectedMedicine?.quantity || 0) || 'Insufficient stock',
                  ]"
                />
              </div>
              <div class="col-12 col-sm-6">
                <q-input
                  v-model="dispenseForm.dosage"
                  label="Dosage Instructions"
                  outlined
                  dense
                  placeholder="e.g., 1 tablet twice daily"
                />
              </div>
              <div class="col-12">
                <q-input
                  v-model="dispenseForm.notes"
                  label="Notes"
                  type="textarea"
                  outlined
                  dense
                  rows="3"
                />
              </div>
            </div>

            <q-banner class="stock-banner" rounded>
              <q-icon name="inventory_2" color="primary" />
              <div>
                Available stock: <strong>{{ selectedMedicine?.quantity || 0 }}</strong>
                <span class="divider">•</span>
                Minimum stock level guidance applies to alerts
              </div>
            </q-banner>
          </q-card-section>

          <q-card-actions class="actions-responsive" align="right">
            <q-btn flat label="Cancel" color="grey-7" @click="cancelDispense" class="cancel-btn" />
            <q-btn
              label="Dispense"
              color="primary"
              @click="confirmDispense"
              :loading="dispensing"
              class="save-btn"
            />
          </q-card-actions>
        </q-card>
      </q-dialog>

      <!-- Restock Medicine Dialog -->
      <q-dialog v-model="showRestockDialog" persistent>
        <q-card class="restock-modal" style="min-width: 560px">
          <!-- Header with medication details and stock banner -->
          <q-card-section class="restock-header">
            <div class="restock-title-row">
              <div class="med-head">
                <div class="med-name">{{ selectedMedicine?.name }}</div>
                <div class="med-subtitle">
                  {{ selectedMedicine?.genericName }} • {{ selectedMedicine?.dosage }} {{ selectedMedicine?.strength }} {{ selectedMedicine?.unit }} • {{ selectedMedicine?.category }}
                </div>
              </div>
              <div
                class="stock-banner restock-stock-banner"
                :class="selectedMedicine?.stockLevel === 'out_of_stock' ? 'stock-out' : (selectedMedicine?.stockLevel === 'low_stock' ? 'stock-low' : 'stock-ok')"
              >
                <div class="stock-row">
                  <span class="stock-current">Current: {{ selectedMedicine?.quantity }}</span>
                  <span class="stock-min">Min: {{ selectedMedicine?.minStockLevel }}</span>
                </div>
              </div>
            </div>
          </q-card-section>

          <!-- Inputs in a clean two-column layout -->
          <q-card-section class="restock-inputs">
            <div class="row q-col-gutter-md">
              <div class="col-12 col-md-6">
                <q-input
                  v-model.number="restockForm.quantity"
                  label="Quantity to Add"
                  type="number"
                  outlined
                  :rules="[(val) => val > 0 || 'Quantity must be positive']"
                  hint="Enter units to add"
                />
              </div>
              <div class="col-12 col-md-6">
                <q-input
                  v-model="restockForm.expiryDate"
                  label="New Expiry Date"
                  type="date"
                  outlined
                  :rules="[(val) => !!val || 'Expiry date is required']"
                />
              </div>
              <div class="col-12 col-md-6">
                <q-input v-model="restockForm.supplier" label="Supplier" outlined />
              </div>
              <div class="col-12 col-md-6">
                <q-input v-model="restockForm.notes" label="Notes" type="textarea" outlined rows="3" />
              </div>
            </div>
          </q-card-section>

          <!-- Actions -->
          <q-card-actions class="actions-responsive" align="right">
            <q-btn flat label="Cancel" color="grey-7" @click="cancelRestock" class="cancel-btn" />
            <q-btn label="Restock" color="primary" @click="confirmRestock" :loading="restocking" class="save-btn" />
          </q-card-actions>
        </q-card>
      </q-dialog>

      <!-- Notification Detail Dialog -->
      <q-dialog v-model="showNotificationDialog" persistent>
        <q-card style="min-width: 500px">
          <q-card-section>
            <div class="text-h6">Notification Details</div>
          </q-card-section>

          <q-card-section v-if="selectedNotification">
            <div class="notification-detail">
              <div class="notification-header">
                <q-icon
                  :name="getNotificationIcon(selectedNotification.type)"
                  :color="getNotificationColor(selectedNotification.type)"
                  size="2rem"
                />
                <div class="notification-title">
                  {{ selectedNotification.medicineName }}
                </div>
              </div>

              <div class="notification-message">
                {{ selectedNotification.message }}
              </div>

              <div class="notification-time">
                {{ formatNotificationTime(selectedNotification.timestamp) }}
              </div>

              <div class="notification-actions q-mt-md">
                <q-btn
                  color="primary"
                  label="View Medicine"
                  icon="visibility"
                  @click="viewMedicineFromNotification"
                />
                <q-btn
                  color="secondary"
                  label="Restock"
                  icon="add_shopping_cart"
                  @click="restockFromNotification"
                />
              </div>
            </div>
          </q-card-section>

          <q-card-actions align="right">
            <q-btn flat label="Close" color="primary" @click="showNotificationDialog = false" />
          </q-card-actions>
        </q-card>
      </q-dialog>
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useQuasar } from 'quasar';
import { api } from 'src/boot/axios';
import axios from 'axios';
import NurseHeader from 'src/components/NurseHeader.vue';
import NurseSidebar from 'src/components/NurseSidebar.vue';

const $q = useQuasar();

// Sidebar and navigation
const rightDrawerOpen = ref(false);

// Search functionality
const searchText = ref('');
const searchResults = ref<
  {
    id: string;
    type: string;
    title: string;
    subtitle: string;
    data: Record<string, string | number>;
  }[]
>([]);

// Notification system
const showNotifications = ref(false);
const unreadNotificationsCount = ref(0);

// Location data
const locationData = ref<{
  city: string;
  region: string;
  country: string;
} | null>(null);
const locationLoading = ref(false);
const locationError = ref(false);

// Time and weather
const currentTime = ref('');
const currentDate = computed(() => {
  const now = new Date();
  return now.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
});
const weatherData = ref<{
  temperature: number;
  condition: string;
  location: string;
} | null>(null);
const weatherLoading = ref(false);
const weatherError = ref(false);
let timeInterval: NodeJS.Timeout | null = null;


// User verification
const userProfile = ref<{
  first_name?: string;
  last_name?: string;
  full_name?: string;
  role?: string;
  is_verified?: boolean;
  verification_status?: string;
  profile_picture?: string | null;
  email?: string;
}>({});

const isUserVerified = computed(() => {
  return userProfile.value.verification_status === 'approved';
});



// Page state
const loading = ref(false);
const saving = ref(false);
const dispensing = ref(false);
const restocking = ref(false);

// Notification system
const notifications = ref<
  {
    id: number;
    type: 'low_stock' | 'expiring_soon' | 'out_of_stock';
    message: string;
    medicineName: string;
    timestamp: Date;
    isRead: boolean;
  }[]
>([]);

// Notification interface
interface Notification {
  id: number;
  type: 'low_stock' | 'out_of_stock' | 'expiring_soon';
  message: string;
  medicineName: string;
  timestamp: Date;
  isRead: boolean;
}

// Show notification dialog
const showNotificationDialog = ref(false);
const selectedNotification = ref<Notification | null>(null);

// Search and filters
const searchQuery = ref('');
const categoryFilter = ref(null);
const stockFilter = ref(null);

// Dialog states
const showAddDialog = ref(false);
const showDispenseDialog = ref(false);
const showRestockDialog = ref(false);

// Form data
const editingMedicine = ref<Medicine | null>(null);
const selectedMedicine = ref<Medicine | null>(null);

const medicineForm = ref({
  name: '',
  genericName: '',
  category: '',
  dosage: '',
  strength: '',
  quantity: 0,
  unit: '',
  expiryDate: '',
  minStockLevel: 0,
  description: '',
  unitPrice: 0,
  batchNumber: '',
});

const dispenseForm = ref({
  patientName: '',
  patientId: '',
  quantity: 0,
  dosage: '',
  notes: '',
  time: '',
});


const restockForm = ref({
  quantity: 0,
  expiryDate: '',
  supplier: '',
  notes: '',
});

// Table pagination
const pagination = ref({
  sortBy: 'name',
  descending: false,
  page: 1,
  rowsPerPage: 10,
});

// Options for dropdowns
const medicineCategories = [
  { label: 'Analgesics', value: 'analgesics' },
  { label: 'Antibiotics', value: 'antibiotics' },
  { label: 'Antihypertensives', value: 'antihypertensives' },
  { label: 'Antidiabetics', value: 'antidiabetics' },
  { label: 'Cardiovascular', value: 'cardiovascular' },
  { label: 'Respiratory', value: 'respiratory' },
  { label: 'Gastrointestinal', value: 'gastrointestinal' },
  { label: 'Psychiatric', value: 'psychiatric' },
  { label: 'Other', value: 'other' },
];

const stockLevels = [
  { label: 'In Stock', value: 'in_stock' },
  { label: 'Low Stock', value: 'low_stock' },
  { label: 'Out of Stock', value: 'out_of_stock' },
];

// Table columns
const columns = [
  {
    name: 'name',
    required: true,
    label: 'Medicine Name',
    align: 'left' as const,
    field: 'name',
    sortable: true,
  },
  {
    name: 'category',
    label: 'Category',
    align: 'left' as const,
    field: 'category',
    sortable: true,
  },
  {
    name: 'strength',
    label: 'Strength',
    align: 'left' as const,
    field: 'strength',
  },
  {
    name: 'quantity',
    label: 'Quantity',
    align: 'center' as const,
    field: 'quantity',
    sortable: true,
  },
  {
    name: 'stockLevel',
    label: 'Stock Level',
    align: 'center' as const,
    field: 'stockLevel',
  },
  {
    name: 'expiryDate',
    label: 'Expiry Date',
    align: 'center' as const,
    field: 'expiryDate',
    sortable: true,
  },
  {
    name: 'actions',
    label: 'Actions',
    align: 'center' as const,
    field: 'actions',
  },
];

// Empty inventory data - nurses will input their stock
const medicines = ref<Medicine[]>([]);

// Dummy inventory generator for demo/testing when backend is empty/unavailable
const generateFutureDate = (days: number): string => {
  // Avoid noUncheckedIndexedAccess by using substring, guaranteeing a string
  return new Date(Date.now() + days * 24 * 60 * 60 * 1000)
    .toISOString()
    .substring(0, 10);
};

const getDummyMedicines = (): Medicine[] => [
  {
    id: 1,
    name: 'Paracetamol',
    genericName: 'Acetaminophen',
    category: 'analgesics',
    dosage: 'Tablet',
    strength: '500mg',
    quantity: 100,
    unit: 'tablets',
    expiryDate: generateFutureDate(180),
    minStockLevel: 20,
    description: 'Pain relief and fever reducer',
    stockLevel: 'in_stock',
  },
  {
    id: 2,
    name: 'Ibuprofen',
    genericName: 'Ibuprofen',
    category: 'analgesics',
    dosage: 'Tablet',
    strength: '200mg',
    quantity: 8,
    unit: 'tablets',
    expiryDate: generateFutureDate(25),
    minStockLevel: 15,
    description: 'NSAID for pain and inflammation',
    stockLevel: 'low_stock',
  },
  {
    id: 3,
    name: 'Amoxicillin',
    genericName: 'Amoxicillin',
    category: 'antibiotics',
    dosage: 'Capsule',
    strength: '500mg',
    quantity: 0,
    unit: 'capsules',
    expiryDate: generateFutureDate(90),
    minStockLevel: 10,
    description: 'Antibiotic for bacterial infections',
    stockLevel: 'out_of_stock',
  },
  {
    id: 4,
    name: 'Metformin',
    genericName: 'Metformin',
    category: 'antidiabetics',
    dosage: 'Tablet',
    strength: '500mg',
    quantity: 40,
    unit: 'tablets',
    expiryDate: generateFutureDate(365),
    minStockLevel: 20,
    description: 'Blood sugar control',
    stockLevel: 'in_stock',
  },
  {
    id: 5,
    name: 'Salbutamol',
    genericName: 'Albuterol',
    category: 'respiratory',
    dosage: 'Inhaler',
    strength: '100mcg/dose',
    quantity: 12,
    unit: 'inhalers',
    expiryDate: generateFutureDate(60),
    minStockLevel: 10,
    description: 'Bronchodilator for asthma',
    stockLevel: 'in_stock',
  },
  {
    id: 6,
    name: 'Aspirin',
    genericName: 'Acetylsalicylic Acid',
    category: 'cardiovascular',
    dosage: 'Tablet',
    strength: '81mg',
    quantity: 5,
    unit: 'tablets',
    expiryDate: generateFutureDate(15),
    minStockLevel: 10,
    description: 'Antiplatelet therapy',
    stockLevel: 'low_stock',
  },
];

// Computed properties
const filteredMedicines = computed(() => {
  let filtered = medicines.value;

  // Search filter
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    filtered = filtered.filter(
      (medicine) =>
        (medicine.name ?? '').toLowerCase().includes(query) ||
        (medicine.genericName ?? '').toLowerCase().includes(query),
    );
  }

  // Category filter
  if (categoryFilter.value) {
    filtered = filtered.filter((medicine) => medicine.category === categoryFilter.value);
  }

  // Stock level filter
  if (stockFilter.value) {
    filtered = filtered.filter((medicine) => medicine.stockLevel === stockFilter.value);
  }

  return filtered;
});

const inventoryStats = computed(() => {
  const total = medicines.value.length;
  const lowStock = medicines.value.filter((m) => m.stockLevel === 'low_stock').length;
  const outOfStock = medicines.value.filter((m) => m.stockLevel === 'out_of_stock').length;
  const expiringSoon = medicines.value.filter((m) => {
    const expiryDate = new Date(m.expiryDate);
    const today = new Date();
    const daysUntilExpiry = Math.ceil(
      (expiryDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24),
    );
    return daysUntilExpiry <= 30 && daysUntilExpiry > 0;
  }).length;

  return {
    totalMedicines: total,
    lowStock,
    outOfStock,
    expiringSoon,
  };
});

// Methods

const handleAddMedicineClick = () => {
  if (!isUserVerified.value) {
    $q.notify({
      type: 'warning',
      message:
        'Account verification required to manage medicine inventory. Please complete verification first.',
      position: 'top',
      timeout: 4000,
    });
    return;
  }
  showAddDialog.value = true;
};

const applyFilters = () => {
  // Filters are applied automatically through computed property
  console.log('Filters applied');
};

const getStockLevelColor = (level?: string) => {
  switch (level) {
    case 'in_stock':
      return 'positive';
    case 'low_stock':
      return 'warning';
    case 'out_of_stock':
      return 'negative';
    default:
      return 'grey';
  }
};

const getExpiryDateClass = (date?: string) => {
  if (!date) return 'text-warning';
  const expiryDate = new Date(date);
  const today = new Date();
  const daysUntilExpiry = Math.ceil(
    (expiryDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24),
  );

  if (daysUntilExpiry < 0) return 'text-negative';
  if (daysUntilExpiry <= 30) return 'text-warning';
  return 'text-positive';
};

const formatDate = (date?: string) => {
  return date ? new Date(date).toLocaleDateString() : '';
};

interface Medicine {
  id: number;
  name: string;
  genericName: string;
  category: string;
  dosage: string;
  strength: string;
  quantity: number;
  unit: string;
  expiryDate: string;
  minStockLevel: number;
  description: string;
  stockLevel: string;
  unitPrice?: number;
  batchNumber?: string;
}

// Search result interfaces
interface MedicineSearchResult {
  id: number | string;
  medicine_name?: string;
  name?: string;
  stock_quantity?: number;
  current_stock?: number;
  manufacturer?: string;
}

interface PatientSearchResult {
  id: number | string;
  full_name?: string;
  patient_name?: string;
  name?: string;
  room_number?: string;
}

interface DoctorSearchResult {
  id: number | string;
  full_name?: string;
  name?: string;
  specialization?: string;
}

const editMedicine = (medicine: Medicine) => {
  editingMedicine.value = medicine;
  medicineForm.value = {
    name: medicine.name,
    genericName: medicine.genericName,
    category: medicine.category,
    dosage: medicine.dosage,
    strength: medicine.strength,
    quantity: medicine.quantity,
    unit: medicine.unit,
    expiryDate: medicine.expiryDate,
    minStockLevel: medicine.minStockLevel,
    description: medicine.description,
    unitPrice: medicine.unitPrice || 0,
    batchNumber: medicine.batchNumber || '',
  };
  showAddDialog.value = true;
};

const dispenseMedicine = (medicine: Medicine) => {
  selectedMedicine.value = medicine;
  dispenseForm.value = {
    patientName: '',
    patientId: '',
    quantity: 0,
    dosage: '',
    notes: '',
    time: new Date().toISOString(),
  };
  showDispenseDialog.value = true;
};


const restockMedicine = (medicine: Medicine) => {
  selectedMedicine.value = medicine;
  restockForm.value = {
    quantity: 0,
    expiryDate: '',
    supplier: '',
    notes: '',
  };
  showRestockDialog.value = true;
};

const cancelEdit = () => {
  editingMedicine.value = null;
  medicineForm.value = {
    name: '',
    genericName: '',
    category: '',
    dosage: '',
    strength: '',
    quantity: 0,
    unit: '',
    expiryDate: '',
    minStockLevel: 0,
    description: '',
    unitPrice: 0,
    batchNumber: '',
  };
  showAddDialog.value = false;
};

// Function to check stock levels and generate notifications
const checkStockLevels = () => {
  const today = new Date();
  const thirtyDaysFromNow = new Date(today.getTime() + 30 * 24 * 60 * 60 * 1000);

  medicines.value.forEach((medicine) => {
    // Check for low stock
    if (medicine.quantity <= medicine.minStockLevel && medicine.quantity > 0) {
      const existingNotification = notifications.value.find(
        (n) => n.medicineName === medicine.name && n.type === 'low_stock' && !n.isRead,
      );

      if (!existingNotification) {
        notifications.value.unshift({
          id: Date.now(),
          type: 'low_stock',
          message: `${medicine.name} is running low on stock. Current quantity: ${medicine.quantity} ${medicine.unit}`,
          medicineName: medicine.name,
          timestamp: new Date(),
          isRead: false,
        });
      }
    }

    // Check for out of stock
    if (medicine.quantity === 0) {
      const existingNotification = notifications.value.find(
        (n) => n.medicineName === medicine.name && n.type === 'out_of_stock' && !n.isRead,
      );

      if (!existingNotification) {
        notifications.value.unshift({
          id: Date.now(),
          type: 'out_of_stock',
          message: `${medicine.name} is out of stock. Please restock immediately.`,
          medicineName: medicine.name,
          timestamp: new Date(),
          isRead: false,
        });
      }
    }

    // Check for expiring soon (within 30 days)
    const expiryDate = new Date(medicine.expiryDate);
    if (expiryDate <= thirtyDaysFromNow && expiryDate >= today) {
      const daysUntilExpiry = Math.ceil(
        (expiryDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24),
      );

      const existingNotification = notifications.value.find(
        (n) => n.medicineName === medicine.name && n.type === 'expiring_soon' && !n.isRead,
      );

      if (!existingNotification) {
        notifications.value.unshift({
          id: Date.now(),
          type: 'expiring_soon',
          message: `${medicine.name} will expire in ${daysUntilExpiry} days. Current quantity: ${medicine.quantity} ${medicine.unit}`,
          medicineName: medicine.name,
          timestamp: new Date(),
          isRead: false,
        });
      }
    }
  });
};

const saveMedicine = async () => {
  saving.value = true;

  try {
    if (editingMedicine.value) {
      // Update existing medicine
      const response = await api.put(
        `/operations/medicine-inventory/${editingMedicine.value.id}/update/`,
        {
          name: medicineForm.value.name,
          quantity: medicineForm.value.quantity,
          //unit_price: medicineForm.value.unitPrice || 0,
          minimum_stock_level: medicineForm.value.minStockLevel,
          expiry_date: medicineForm.value.expiryDate,
          //batch_number: medicineForm.value.batchNumber || `BATCH-${Date.now()}`,
          usage_pattern: medicineForm.value.description || '',
        },
      );

      // Update local state with backend response
      const index = medicines.value.findIndex((m) => m.id === editingMedicine.value?.id);
      if (index !== -1 && editingMedicine.value && medicines.value[index]) {
        const currentMedicine = medicines.value[index];
        medicines.value[index] = {
          id: currentMedicine.id,
          name: response.data.medicine_name,
          genericName: currentMedicine.genericName,
          category: currentMedicine.category,
          dosage: currentMedicine.dosage,
          strength: currentMedicine.strength,
          quantity: response.data.current_stock,
          unit: currentMedicine.unit,
          expiryDate: response.data.expiry_date,
          minStockLevel: response.data.minimum_stock_level,
          description: response.data.usage_pattern,
          stockLevel: response.data.stock_level,
          // unitPrice: response.data.unit_price,
          //batchNumber: response.data.batch_number
        };
      }
    } else {
      // Add new medicine
      const response = await api.post('/operations/medicine-inventory/add/', {
        name: medicineForm.value.name,
        quantity: medicineForm.value.quantity,
        //unit_price: medicineForm.value.unitPrice || 0,
        minimum_stock_level: medicineForm.value.minStockLevel,
        expiry_date: medicineForm.value.expiryDate,
        //batch_number: medicineForm.value.batchNumber || `BATCH-${Date.now()}`,
        usage_pattern: medicineForm.value.description || '',
      });

      // Add to local state
      const newMedicine: Medicine = {
        id: response.data.id,
        name: response.data.medicine_name,
        genericName: medicineForm.value.genericName,
        category: medicineForm.value.category,
        dosage: medicineForm.value.dosage,
        strength: medicineForm.value.strength,
        quantity: response.data.current_stock,
        unit: medicineForm.value.unit,
        expiryDate: response.data.expiry_date,
        minStockLevel: response.data.minimum_stock_level,
        description: response.data.usage_pattern,
        stockLevel: response.data.stock_level,
        //unitPrice: response.data.unit_price,
        //batchNumber: response.data.batch_number
      };
      medicines.value.push(newMedicine);
    }

    // Check stock levels after saving
    checkStockLevels();

    $q.notify({
      type: 'positive',
      message: `Medicine ${editingMedicine.value ? 'updated' : 'added'} successfully!`,
      position: 'top',
    });

    cancelEdit();
  } catch (error) {
    console.error('Error saving medicine:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to save medicine. Please try again.',
      position: 'top',
    });
  } finally {
    saving.value = false;
  }
};

const cancelDispense = () => {
  selectedMedicine.value = null;
  showDispenseDialog.value = false;
};

const confirmDispense = async () => {
  dispensing.value = true;

  try {
    if (!selectedMedicine.value) {
      throw new Error('No medicine selected for dispensing');
    }

    const id = selectedMedicine.value.id;
    const qty = Number(dispenseForm.value.quantity || 0);

    if (!qty || qty <= 0) {
      $q.notify({ type: 'warning', message: 'Enter a valid quantity', position: 'top' });
      return;
    }

    const payload = {
      quantity: qty,
      expiry_days: 21,
    };
    const response = await api.post(`/operations/medicine-inventory/${id}/dispense/`, payload);

    // Update local inventory with backend response
    const updated = response.data?.inventory;
    if (updated) {
      const idx = medicines.value.findIndex((m) => m.id === id);
      if (idx !== -1) {
        const current = medicines.value[idx];
        if (current) {
          current.quantity = Number(updated.current_stock ?? current.quantity);
          current.expiryDate = String(updated.expiry_date ?? current.expiryDate);
          current.minStockLevel = Number(updated.minimum_stock_level ?? current.minStockLevel);
          current.description = String(updated.usage_pattern ?? current.description);
          current.stockLevel = String(updated.stock_level ?? current.stockLevel);
          if (updated.unit_price !== undefined) current.unitPrice = Number(updated.unit_price);
          if (updated.batch_number !== undefined) current.batchNumber = String(updated.batch_number);
        }
      }
    }

    // Check stock levels after dispensing
    checkStockLevels();

    $q.notify({ type: 'positive', message: 'Medicine dispensed successfully!', position: 'top' });
    cancelDispense();
  } catch (error) {
    console.error('Error dispensing medicine:', error);

    let msg = 'Failed to dispense medicine. Please try again.';
    if (axios.isAxiosError(error)) {
      const data = error.response?.data as { error?: string; message?: string } | undefined;
      const backendMessage = data?.error || data?.message;
      if (backendMessage) msg = backendMessage;
    }

    $q.notify({ type: 'negative', message: msg, position: 'top' });
  } finally {
    dispensing.value = false;
  }
};

const cancelRestock = () => {
  selectedMedicine.value = null;
  showRestockDialog.value = false;
};

const confirmRestock = async () => {
  restocking.value = true;

  try {
    const medicine = medicines.value.find((m) => m.id === selectedMedicine.value?.id);
    if (!medicine || !selectedMedicine.value) {
      throw new Error('No medicine selected for restock');
    }

    const id = selectedMedicine.value.id;
    const addQty = Number(restockForm.value.quantity || 0);
    if (!addQty || addQty <= 0) {
      $q.notify({ type: 'warning', message: 'Enter a valid restock quantity', position: 'top' });
      return;
    }

    const currentQty = Number(medicine.quantity || 0);
    const newQty = currentQty + addQty;
    const newExpiry = restockForm.value.expiryDate || medicine.expiryDate;

    // Persist restock via backend update endpoint
    const response = await api.put(`/operations/medicine-inventory/${id}/update/`, {
      quantity: newQty,
      expiry_date: newExpiry,
    });

    // Sync local state with backend response
    const updated = response.data;
    if (updated) {
      medicine.quantity = Number(updated.current_stock ?? newQty);
      medicine.expiryDate = String(updated.expiry_date ?? newExpiry);
      medicine.minStockLevel = Number(updated.minimum_stock_level ?? medicine.minStockLevel);
      medicine.description = String(updated.usage_pattern ?? medicine.description);
      medicine.stockLevel = String(updated.stock_level ?? medicine.stockLevel);
      if (updated.unit_price !== undefined) medicine.unitPrice = Number(updated.unit_price);
      if (updated.batch_number !== undefined) medicine.batchNumber = String(updated.batch_number);
    } else {
      // Fallback local update if response is missing
      medicine.quantity = newQty;
      medicine.expiryDate = newExpiry;
    }

    // Check stock levels after restocking
    checkStockLevels();

    $q.notify({
      type: 'positive',
      message: 'Medicine restocked successfully!',
      position: 'top',
    });

    cancelRestock();
  } catch (error) {
    console.error('Error restocking medicine:', error);

    let msg = 'Failed to restock medicine. Please try again.';
    if (axios.isAxiosError(error)) {
      const data = error.response?.data as { error?: string; message?: string } | undefined;
      const backendMessage = data?.error || data?.message;
      if (backendMessage) msg = backendMessage;
    }

    $q.notify({
      type: 'negative',
      message: msg,
      position: 'top',
    });
  } finally {
    restocking.value = false;
  }
};

const exportInventory = () => {
  // Mock export functionality
  $q.notify({
    type: 'info',
    message: 'Inventory export feature coming soon!',
    position: 'top',
  });
};

// Notification helper functions
const getNotificationIcon = (type: string) => {
  switch (type) {
    case 'low_stock':
      return 'warning';
    case 'out_of_stock':
      return 'error';
    case 'expiring_soon':
      return 'schedule';
    default:
      return 'info';
  }
};

const getNotificationColor = (type: string) => {
  switch (type) {
    case 'low_stock':
      return 'warning';
    case 'out_of_stock':
      return 'negative';
    case 'expiring_soon':
      return 'orange';
    default:
      return 'primary';
  }
};

const formatNotificationTime = (timestamp: Date) => {
  const now = new Date();
  const diff = now.getTime() - timestamp.getTime();
  const minutes = Math.floor(diff / (1000 * 60));
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));

  if (minutes < 60) {
    return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;
  } else if (hours < 24) {
    return `${hours} hour${hours !== 1 ? 's' : ''} ago`;
  } else {
    return `${days} day${days !== 1 ? 's' : ''} ago`;
  }
};

const viewNotification = (notification: Notification) => {
  selectedNotification.value = notification;
  showNotificationDialog.value = true;
};

const markNotificationRead = (notification: Notification) => {
  notification.isRead = true;
  $q.notify({
    type: 'positive',
    message: 'Notification marked as read',
    position: 'top',
  });
};

const markAllNotificationsRead = () => {
  notifications.value.forEach((notification) => {
    notification.isRead = true;
  });
  $q.notify({
    type: 'positive',
    message: 'All notifications marked as read',
    position: 'top',
  });
};

const viewMedicineFromNotification = () => {
  if (selectedNotification.value) {
    const medicine = medicines.value.find(
      (m) => m.name === selectedNotification.value!.medicineName,
    );
    if (medicine) {
      editMedicine(medicine);
      showNotificationDialog.value = false;
    }
  }
};

const restockFromNotification = () => {
  if (selectedNotification.value) {
    const medicine = medicines.value.find(
      (m) => m.name === selectedNotification.value!.medicineName,
    );
    if (medicine) {
      restockMedicine(medicine);
      showNotificationDialog.value = false;
    }
  }
};

const fetchUserProfile = async () => {
  try {
    const response = await api.get('/users/profile/');
    const userData = response.data.user; // The API returns nested user data

    // Module-level verification toast removed; banner is shown only at login

    userProfile.value = {
      first_name: userData.first_name,
      last_name: userData.last_name,
      full_name: userData.full_name,
      role: userData.role,
      is_verified: userData.is_verified,
      verification_status: userData.verification_status,
      profile_picture: userData.profile_picture || localStorage.getItem('profile_picture'),
      email: userData.email,
    };

    // Removed module-level verification toast; banner is shown only once at login

    // Store profile picture in localStorage if available
    if (userData.profile_picture) {
      localStorage.setItem('profile_picture', userData.profile_picture);
    }

    console.log('User profile loaded:', userProfile.value);
  } catch (error) {
    console.error('Failed to fetch user profile:', error);
  }
};

// Sidebar and navigation functions
const toggleRightDrawer = () => {
  rightDrawerOpen.value = !rightDrawerOpen.value;
};



// Search functionality methods
const onSearchInput = async (value: string | number | null) => {
  const stringValue = String(value || '');
  searchText.value = stringValue;
  if (stringValue.trim() && stringValue.length > 2) {
    try {
      // Search for patients, doctors, and medicines using real API endpoints
      const [patientsResponse, doctorsResponse, medicinesResponse] = await Promise.all([
        api.get(`/users/nurse/patients/?search=${encodeURIComponent(stringValue)}`),
        api.get(`/operations/availability/doctors/free/`, { params: { search: stringValue } }),
        api.get(`/operations/medicine-inventory/?search=${encodeURIComponent(stringValue)}`),
      ]);

      const results = [];

      // Add medicine results first (most relevant for this page)
      if (medicinesResponse.data) {
        results.push(
          ...medicinesResponse.data.map((item: MedicineSearchResult) => ({
            id: `medicine-${item.id}`,
            type: 'medicine',
            title: item.medicine_name || item.name || 'Unknown Medicine',
            subtitle: `Stock: ${item.stock_quantity || item.current_stock || 0} - ${item.manufacturer || 'Unknown Manufacturer'}`,
            data: item,
          })),
        );
      }

      // Add patient results
      if (patientsResponse.data.patients) {
        results.push(
          ...patientsResponse.data.patients.map((item: PatientSearchResult) => ({
            id: `patient-${item.id}`,
            type: 'patient',
            title: item.full_name || item.patient_name || item.name || 'Unknown Patient',
            subtitle: `Patient - Room: ${item.room_number || 'N/A'}`,
            data: item,
          })),
        );
      }

      // Add doctor results
      if (doctorsResponse.data?.doctors) {
        results.push(
          ...(doctorsResponse.data.doctors || []).map((item: DoctorSearchResult) => ({
            id: `doctor-${item.id}`,
            type: 'doctor',
            title: item.full_name || item.name || 'Unknown Doctor',
            subtitle: `Doctor - ${item.specialization || 'General'}`,
            data: item,
          })),
        );
      }

      searchResults.value = results.slice(0, 10); // Limit to 10 results
    } catch (error) {
      console.error('Search error:', error);
      searchResults.value = [];
    }
  } else {
    searchResults.value = [];
  }
};

const clearSearch = () => {
  searchText.value = '';
  searchResults.value = [];
};

const selectSearchResult = (result: {
  id: string;
  type: string;
  title: string;
  subtitle: string;
  data: Record<string, string | number>;
}) => {
  // Handle search result selection
  console.log('Selected search result:', result);
  clearSearch();
};

// Location functionality
const fetchLocation = async () => {
  locationLoading.value = true;
  locationError.value = false;

  try {
    // Simulate API call for location data
    await new Promise((resolve) => setTimeout(resolve, 1000));
    locationData.value = {
      city: 'Manila',
      region: 'Metro Manila',
      country: 'Philippines',
    };
  } catch (error) {
    console.error('Error fetching location:', error);
    locationError.value = true;
  } finally {
    locationLoading.value = false;
  }
};

// Time and weather functions
const updateTime = () => {
  const now = new Date();

  // Convert to 12-hour format with AM/PM beside the time
  const hour = now.getHours();
  const ampm = hour >= 12 ? 'PM' : 'AM';
  const hour12 = hour % 12 || 12;
  const minute = now.getMinutes().toString().padStart(2, '0');
  const second = now.getSeconds().toString().padStart(2, '0');

  currentTime.value = `${hour12}:${minute}:${second} ${ampm}`;
};

const fetchWeather = async () => {
  weatherLoading.value = true;
  weatherError.value = false;

  try {
    // Mock weather data for now
    await new Promise((resolve) => setTimeout(resolve, 1000));
    weatherData.value = {
      temperature: 22,
      condition: 'clear',
      location: 'Manila, PH',
    };
  } catch (error) {
    console.error('Weather fetch failed:', error);
    weatherError.value = true;
  } finally {
    weatherLoading.value = false;
  }
};

// Load medicine inventory from backend
const loadMedicineInventory = async () => {
  try {
    loading.value = true;
    const response = await api.get('/operations/medicine-inventory/');

    // Transform backend data to frontend format
    const mapped: Medicine[] = Array.isArray(response.data)
      ? response.data.map(
          (medicine: {
            id: number,
            medicine_name: string,
            current_stock: number,
            expiry_date?: string | null,
            minimum_stock_level: number,
            usage_pattern?: string | null,
            stock_level?: string | null,
            unit_price?: number | null,
            batch_number?: string | null,
          }) => {
            const expiryDateStr: string =
              typeof medicine.expiry_date === 'string' && medicine.expiry_date
                ? medicine.expiry_date
                : generateFutureDate(90);

            return {
              id: medicine.id,
              name: medicine.medicine_name || '',
              genericName: medicine.medicine_name || '',
              category: 'General',
              dosage: 'As prescribed',
              strength: 'Standard',
              quantity: medicine.current_stock,
              unit: 'units',
              expiryDate: expiryDateStr,
              minStockLevel: medicine.minimum_stock_level,
              description: medicine.usage_pattern || '',
              stockLevel: medicine.stock_level ?? 'in_stock',
              unitPrice: medicine.unit_price ?? 0,
              batchNumber: medicine.batch_number || '',
            } as Medicine;
          }
        )
      : [];

    medicines.value = mapped.length ? mapped : getDummyMedicines();

    // Check stock levels on initial load
    checkStockLevels();
  } catch (error) {
    console.error('Failed to load medicine inventory:', error);
    // Fallback to dummy inventory for demo/testing
    medicines.value = getDummyMedicines();
    $q.notify({
      type: 'negative',
      message: 'Failed to load medicine inventory',
      position: 'top',
      timeout: 3000,
    });
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  // Load user profile first
  void fetchUserProfile();

  // Initialize real-time features
  updateTime(); // Set initial time
  timeInterval = setInterval(updateTime, 1000); // Update every second

  // Fetch weather data
  void fetchWeather();

  // Fetch location data
  void fetchLocation();

  // Load inventory data from backend
  void loadMedicineInventory();

  // Refresh user profile every 30 seconds to check for verification status updates
  setInterval(() => {
    void fetchUserProfile();
  }, 30000);

  // More frequent verification status check (every 10 seconds)
  setInterval(() => {
    void fetchUserProfile();
  }, 10000);
});

// Removed profile picture storage sync: initials-only avatar

onUnmounted(() => {
  if (timeInterval) {
    clearInterval(timeInterval);
  }
});
</script>

<style scoped>
/* Page Container with Clean White Background */
.page-container-with-fixed-header {
  background: #ffffff;
  min-height: 100vh;
  position: relative;
  padding-top: 64px; /* Account for fixed header */
}

.page-container-with-fixed-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    135deg,
    rgba(248, 250, 252, 0.8) 0%,
    rgba(241, 245, 249, 0.6) 50%,
    rgba(248, 250, 252, 0.4) 100%
  );
  z-index: 0;
  pointer-events: none;
}

.page-container-with-fixed-header > * {
  position: relative;
  z-index: 1;
}

/* Enhanced Greeting Section */
.greeting-section {
  padding: 32px 40px 24px 40px;
  background: transparent;
  max-width: 1800px;
  margin: 0 auto;
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
  margin-bottom: 28px;
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

.greeting-card:hover {
  transform: translateY(-5px);
  box-shadow: 
    0 20px 40px rgba(40, 102, 96, 0.12),
    0 8px 16px rgba(0, 0, 0, 0.05),
    inset 0 1px 0 rgba(255, 255, 255, 1);
  border-color: rgba(40, 102, 96, 0.2);
}

.greeting-content {
  padding: 24px;
}

.greeting-text {
  font-size: 28px;
  font-weight: 700;
  background: linear-gradient(135deg, #1a202c 0%, #2d3748 50%, #286660 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0 0 8px 0;
  line-height: 1.2;
}

.greeting-subtitle {
  font-size: 16px;
  color: #64748b;
  margin: 0;
  font-weight: 500;
}

.page-header {
  background: white;
  color: #333;
  padding: 20px;
  border-bottom: 1px solid #e0e0e0;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1400px;
  margin: 0 auto;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.back-btn {
  color: white;
}

.page-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #333;
}

.page-content {
  max-width: 1800px;
  margin: 0 auto;
  padding: 24px 40px;
}

.search-filters-card,
.inventory-table-card {
  width: 100%;
  margin-bottom: 32px;
  border-radius: 20px;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.95) 0%,
    rgba(248, 250, 252, 0.9) 50%,
    rgba(241, 245, 249, 0.85) 100%
  );
  backdrop-filter: blur(10px);
  border: 1px solid rgba(40, 102, 96, 0.08);
  box-shadow: 
    0 8px 20px rgba(40, 102, 96, 0.06),
    0 3px 8px rgba(0, 0, 0, 0.02),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  position: relative;
}

.search-filters-card::before,
.inventory-table-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(
    90deg,
    #286660 0%,
    #6ca299 50%,
    #b8d2ce 100%
  );
  border-radius: 20px 20px 0 0;
}

.search-filters-card:hover,
.inventory-table-card:hover {
  transform: translateY(-2px);
  box-shadow: 
    0 12px 28px rgba(40, 102, 96, 0.08),
    0 4px 12px rgba(0, 0, 0, 0.03),
    inset 0 1px 0 rgba(255, 255, 255, 1);
  border-color: rgba(40, 102, 96, 0.12);
}

.stats-section {
  margin-bottom: 16px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
  gap: 16px;
}

@media (min-width: 1280px) {
  .stats-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

/* Enhanced Responsive Design - Mobile First Approach */
@media (max-width: 1400px) {
  .greeting-section,
  .page-content {
    max-width: 1200px;
    padding-left: 32px;
    padding-right: 32px;
  }
  
  .stats-grid {
    gap: 20px;
  }
}

@media (max-width: 1024px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 18px;
  }
  
  .stat-card {
    min-height: 140px;
  }
  
  .card-content {
    padding: 24px 20px;
  }
  
  .card-value {
    font-size: 32px;
  }
  
  .card-icon {
    width: 48px;
    height: 48px;
  }
}

@media (max-width: 768px) {
  .greeting-section {
    padding: 24px 20px;
  }
  
  .page-content {
    padding: 20px 20px;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
  
  .stat-card {
    min-height: 120px;
  }
  
  .card-content {
    padding: 20px 18px;
  }
  
  .card-value {
    font-size: 28px;
  }
  
  .card-icon {
    width: 44px;
    height: 44px;
    font-size: 20px;
  }
  
  .search-filters-card,
  .inventory-table-card,
  .greeting-card,
  .notifications-card {
    margin-bottom: 24px;
  }
  
  .stats-section {
    margin-bottom: 24px;
  }
}

@media (max-width: 480px) {
  .greeting-section {
    padding: 20px 16px;
  }
  
  .page-content {
    padding: 16px;
  }
  
  .greeting-text {
    font-size: 24px;
  }
  
  .greeting-subtitle {
    font-size: 14px;
  }
  
  .card-title {
    font-size: 12px;
  }
  
  .card-value {
    font-size: 24px;
  }
  
  .card-icon {
    width: 40px;
    height: 40px;
    font-size: 18px;
  }
}

.stat-card {
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.95) 0%,
    rgba(248, 250, 252, 0.9) 50%,
    rgba(241, 245, 249, 0.85) 100%
  );
  backdrop-filter: blur(10px);
  border-radius: 20px;
  border: 1px solid rgba(40, 102, 96, 0.08);
  box-shadow: 
    0 8px 20px rgba(40, 102, 96, 0.06),
    0 3px 8px rgba(0, 0, 0, 0.02),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  position: relative;
  height: 170px;
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  border-radius: 20px 20px 0 0;
  transition: all 0.3s ease;
}

.stat-card.total-medicines::before {
  background: linear-gradient(90deg, rgba(102, 126, 234, 0.35) 0%, rgba(118, 75, 162, 0.35) 100%);
}

.stat-card.low-stock::before {
  background: linear-gradient(90deg, rgba(240, 147, 251, 0.35) 0%, rgba(245, 87, 108, 0.35) 100%);
}

.stat-card.out-of-stock::before {
  background: linear-gradient(90deg, rgba(79, 172, 254, 0.35) 0%, rgba(0, 242, 254, 0.35) 100%);
}

.stat-card.expiring-soon::before {
  background: linear-gradient(90deg, rgba(255, 213, 79, 0.35) 0%, rgba(255, 179, 0, 0.35) 100%);
}

/* Subtle tinted overlays for each card (match sample design) */
.stat-card::after {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
}
.stat-card.total-medicines::after {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.12) 0%, rgba(118, 75, 162, 0.08) 100%);
}
.stat-card.low-stock::after {
  background: linear-gradient(135deg, rgba(240, 147, 251, 0.12) 0%, rgba(245, 87, 108, 0.08) 100%);
}
.stat-card.out-of-stock::after {
  background: linear-gradient(135deg, rgba(79, 172, 254, 0.12) 0%, rgba(0, 242, 254, 0.08) 100%);
}
.stat-card.expiring-soon::after {
  background: linear-gradient(135deg, rgba(255, 193, 7, 0.12) 0%, rgba(255, 152, 0, 0.08) 100%);
}

/* Subtle accent only (glassmorphism) — remove full-card color fills */
.stat-card.total-medicines,
.stat-card.low-stock,
.stat-card.out-of-stock,
.stat-card.expiring-soon {
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.95) 0%,
    rgba(248, 250, 252, 0.9) 50%,
    rgba(241, 245, 249, 0.85) 100%
  );
  color: inherit;
}

/* Text colors use defaults for glassmorphism cards */
.total-medicines .card-title,
.low-stock .card-title,
.out-of-stock .card-title,
.expiring-soon .card-title {
  color: inherit;
}
.total-medicines .card-description,
.low-stock .card-description,
.out-of-stock .card-description,
.expiring-soon .card-description {
  color: inherit;
}
.total-medicines .card-value,
.low-stock .card-value,
.out-of-stock .card-value,
.expiring-soon .card-value {
  -webkit-text-fill-color: unset;
  color: inherit;
}

.stat-card:hover {
  transform: translateY(-8px) scale(1.02);
  box-shadow: 
    0 20px 40px rgba(40, 102, 96, 0.12),
    0 8px 16px rgba(0, 0, 0, 0.04),
    inset 0 1px 0 rgba(255, 255, 255, 1);
  border-color: rgba(40, 102, 96, 0.15);
}

.stat-card:hover::before {
  height: 4px;
}

.card-content {
  padding: 28px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
  position: relative;
  z-index: 1;
}

.card-text { 
  flex: 1; 
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.card-title {
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  line-height: 1.2;
}

.card-description {
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.3;
  margin-bottom: 8px;
  font-weight: 500;
}

.card-value {
  font-size: 36px;
  font-weight: 800;
  background: linear-gradient(135deg, #1a202c 0%, #2d3748 50%, #286660 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  line-height: 1;
  margin-top: 8px;
  transition: all 0.3s ease;
}

.stat-card:hover .card-value {
  transform: scale(1.05);
}

.card-icon {
  width: 52px;
  height: 52px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: white;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transition: all 0.3s ease;
}

.stat-card:hover .card-icon {
  transform: scale(1.1);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
}

/* Card-specific icon chips — toned down to match sample */
.total-medicines .card-icon {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.25) 0%, rgba(118, 75, 162, 0.25) 100%);
  border: 1px solid rgba(102, 126, 234, 0.25);
  color: #3f51b5;
}

.low-stock .card-icon {
  background: linear-gradient(135deg, rgba(240, 147, 251, 0.25) 0%, rgba(245, 87, 108, 0.25) 100%);
  border: 1px solid rgba(240, 147, 251, 0.25);
  color: #d54b8c;
}

.out-of-stock .card-icon {
  background: linear-gradient(135deg, rgba(79, 172, 254, 0.25) 0%, rgba(0, 242, 254, 0.25) 100%);
  border: 1px solid rgba(79, 172, 254, 0.25);
  color: #2196f3;
}

.expiring-soon .card-icon {
  background: linear-gradient(135deg, rgba(255, 193, 7, 0.25) 0%, rgba(255, 152, 0, 0.25) 100%);
  border: 1px solid rgba(255, 193, 7, 0.25);
  color: #ff9800;
}

.inventory-table {
  border-radius: 8px;
}

/* Enhanced Notifications Styles */
.notifications-card {
  width: 100%;
  margin-bottom: 32px;
  border-radius: 20px;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.95) 0%,
    rgba(248, 250, 252, 0.9) 50%,
    rgba(241, 245, 249, 0.85) 100%
  );
  backdrop-filter: blur(10px);
  border: 1px solid rgba(40, 102, 96, 0.08);
  box-shadow: 
    0 8px 20px rgba(40, 102, 96, 0.06),
    0 3px 8px rgba(0, 0, 0, 0.02),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  position: relative;
}

.notifications-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(
    90deg,
    #286660 0%,
    #6ca299 50%,
    #b8d2ce 100%
  );
  border-radius: 20px 20px 0 0;
}

.notifications-card:hover {
  transform: translateY(-2px);
  box-shadow: 
    0 12px 28px rgba(40, 102, 96, 0.08),
    0 4px 12px rgba(0, 0, 0, 0.03),
    inset 0 1px 0 rgba(255, 255, 255, 1);
  border-color: rgba(40, 102, 96, 0.12);
}

.notifications-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.notification-item {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px;
  border-radius: 8px;
  background: #f8f9fa;
  border-left: 4px solid #2196f3;
  transition: all 0.2s ease;
  cursor: pointer;
}

.notification-item:hover {
  background: #e3f2fd;
  transform: translateX(5px);
}

.notification-item.unread {
  background: #fff3e0;
  border-left-color: #ff9800;
}

.notification-item.unread:hover {
  background: #ffe0b2;
}

.notification-item.read {
  opacity: 0.7;
}

.notification-icon {
  flex-shrink: 0;
}

.notification-content {
  flex: 1;
}

.notification-message {
  font-weight: 500;
  color: #333;
  margin-bottom: 5px;
}

.notification-time {
  font-size: 12px;
  color: #666;
}

.notification-actions {
  display: flex;
  gap: 5px;
}

.notification-detail {
  padding: 10px 0;
}

.notification-header {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 15px;
}

.notification-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.notification-message {
  font-size: 14px;
  color: #666;
  line-height: 1.5;
  margin-bottom: 10px;
}

.notification-time {
  font-size: 12px;
  color: #999;
  margin-bottom: 15px;
}

.notification-actions {
  display: flex;
  gap: 10px;
}

/* Ensure mobile header is always visible on mobile devices */
@media (max-width: 768px) {
  .mobile-header-layout {
    display: flex !important;
  }

  .header-toolbar {
    display: none !important;
  }

  /* Force header visibility on iOS */
  .prototype-header {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    z-index: 2000 !important;
    padding-top: max(env(safe-area-inset-top), 8px) !important;
  }

  /* Ensure main content doesn't overlap header */
  .q-page {
    padding-top: calc(env(safe-area-inset-top) + 120px) !important;
  }
}

/* Responsive Design - Mobile and Web Support */
@media (max-width: 768px) {
  .mobile-header-layout {
    display: flex !important;
  }

  .header-toolbar {
    display: none !important;
  }

  /* Mobile header positioning */
  .prototype-header {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    z-index: 2000 !important;
    padding-top: max(env(safe-area-inset-top), 8px) !important;
  }

  /* Ensure main content doesn't overlap header */
  .q-page {
    padding-top: calc(env(safe-area-inset-top) + 120px) !important;
  }
}

/* Desktop Header Layout */
@media (min-width: 769px) {
  .mobile-header-layout {
    display: none;
  }

  .prototype-header .header-toolbar {
    display: flex;
  }
}

/* Global Modal Safe Area Support */
@media (max-width: 768px) {
  :deep(.q-dialog) {
    padding: 0 !important;
    margin: 0 !important;
  }

  :deep(.q-dialog__inner) {
    padding: max(env(safe-area-inset-top), 20px) max(env(safe-area-inset-right), 8px)
      max(env(safe-area-inset-bottom), 8px) max(env(safe-area-inset-left), 8px) !important;
    margin: 0 !important;
    min-height: 100vh !important;
    display: flex !important;
    align-items: flex-start !important;
    justify-content: center !important;
    padding-top: max(env(safe-area-inset-top), 20px) !important;
  }

  :deep(.q-dialog__inner > div) {
    max-height: calc(
      100vh - max(env(safe-area-inset-top), 20px) - max(env(safe-area-inset-bottom), 8px)
    ) !important;
    width: 100% !important;
    max-width: calc(
      100vw - max(env(safe-area-inset-left), 8px) - max(env(safe-area-inset-right), 8px)
    ) !important;
    margin: 0 !important;
  }
}

@media (max-width: 480px) {
  :deep(.q-dialog__inner) {
    padding: max(env(safe-area-inset-top), 24px) max(env(safe-area-inset-right), 4px)
      max(env(safe-area-inset-bottom), 4px) max(env(safe-area-inset-left), 4px) !important;
  }

  :deep(.q-dialog__inner > div) {
    max-height: calc(
      100vh - max(env(safe-area-inset-top), 24px) - max(env(safe-area-inset-bottom), 4px)
    ) !important;
    max-width: calc(
      100vw - max(env(safe-area-inset-left), 4px) - max(env(safe-area-inset-right), 4px)
    ) !important;
  }
}

/* Modal Close Button Styles */
.modal-close-btn {
  padding: 4px;
  transition: all 0.2s ease;
}

/* Desktop close button styling */
@media (min-width: 769px) {
  .modal-close-btn {
    padding: 6px;
    min-width: 36px;
    min-height: 36px;
    font-size: 18px;
  }

  .modal-close-btn:hover {
    background: rgba(0, 0, 0, 0.1);
    border-radius: 50%;
  }
}

/* Mobile close button styling */
@media (max-width: 768px) {
  .modal-close-btn {
    padding: 8px !important;
    min-width: 44px !important;
    min-height: 44px !important;
    font-size: 20px !important;
    background: rgba(0, 0, 0, 0.1) !important;
    border-radius: 50% !important;
  }

  .modal-close-btn:hover {
    background: rgba(0, 0, 0, 0.2) !important;
  }
}

@media (max-width: 480px) {
  .modal-close-btn {
    padding: 10px !important;
    min-width: 48px !important;
    min-height: 48px !important;
    font-size: 22px !important;
    background: rgba(0, 0, 0, 0.1) !important;
    border-radius: 50% !important;
  }

  .modal-close-btn:hover {
    background: rgba(0, 0, 0, 0.2) !important;
  }
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .page-content {
    padding: 8px;
  }

  .q-card {
    margin: 8px 0;
    border-radius: 12px;
  }

  .q-card__section {
    padding: 16px;
  }

  .header-content {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
    padding: 16px;
  }

  .header-right {
    align-self: flex-end;
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

  .notification-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
    padding: 12px;
  }

  .notification-actions {
    align-self: flex-end;
  }

  .medicine-card {
    margin-bottom: 16px;
  }

  .medicine-card h6 {
    font-size: 16px;
    margin-bottom: 8px;
  }

  .medicine-info .text-caption {
    font-size: 12px;
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

  .q-btn {
    padding: 10px 16px;
    font-size: 14px;
    border-radius: 6px;
  }

  .q-table {
    font-size: 12px;
  }

  .q-table th,
  .q-table td {
    padding: 8px;
  }
}

/* Header Styles */
.prototype-header {
  background: #286660;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header-toolbar {
  padding: 0 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 24px;
}

.search-container {
  min-width: 300px;
}

.search-input {
  border-radius: 8px;
}

.time-display,
.weather-display,
.weather-loading,
.weather-error {
  display: flex;
  align-items: center;
  gap: 8px;
  color: white;
  font-size: 14px;
  font-size: 14px;
  font-weight: 500;
  padding: 6px 12px;
  border-radius: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.time-text,
.weather-text,
.weather-location {
  font-size: 14px;
  font-weight: 500;
  color: white;
}

.weather-location {
  font-size: 12px;
  opacity: 0.8;
}

.weather-loading,
.weather-error {
  display: flex;
  align-items: center;
  gap: 6px;
  color: white;
  font-size: 14px;
  font-weight: 500;
}

.weather-error .q-icon {
  color: #ff6b6b;
}

/* Sidebar Styles */
.prototype-sidebar {
  background: white;
  border-right: 1px solid #e0e0e0;
  position: relative;
}

.sidebar-content {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding-bottom: 80px; /* Space for footer */
}

.logo-section {
  padding: 20px;
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo-container {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  color: #286660;
}

.menu-btn {
  color: #666;
}

.sidebar-user-profile {
  padding: 24px 20px;
  border-bottom: 1px solid #e0e0e0;
  text-align: center;
}

.profile-picture-container {
  position: relative;
  display: inline-block;
  margin-bottom: 16px;
}


.user-info {
  text-align: center;
}

.user-name {
  margin: 0 0 4px 0;
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.user-role {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #666;
}

.navigation-menu {
  flex: 1;
  padding: 8px 0;
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

.sidebar-footer {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 20px;
  border-top: 1px solid #e0e0e0;
}

.logout-section {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 20px;
  border-top: 1px solid #e0e0e0;
  background: #f8f9fa;
}

.logout-btn {
  width: 100%;
  border-radius: 8px;
  font-weight: 600;
  text-transform: uppercase;
}

/* Profile Avatar Styles - Circular Design */
.profile-avatar {
  border: 3px solid #1e7668 !important;
  border-radius: 50% !important;
  overflow: hidden !important;
}


.profile-placeholder {
  width: 100%;
  height: 100%;
  display: flex !important;
  align-items: center;
  justify-content: center;
  background: #286660 !important;
  color: white !important;
  font-weight: 600;
  font-size: 1.5rem;
  border-radius: 50%;
  position: relative;
  z-index: 1;
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

/* Medicine Modal Styles */
.medicine-modal {
  min-width: 750px;
  max-width: 950px;
  border-radius: 16px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
}

.modal-header {
  background: linear-gradient(135deg, #286660 0%, #1e7668 100%);
  color: white;
  padding: 20px 24px;
  border-radius: 16px 16px 0 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 20px;
  font-weight: 600;
}

.title-icon {
  color: white;
}

.close-btn {
  color: white !important;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.modal-actions {
  padding: 20px 24px;
  background: #f8f9fa;
  border-radius: 0 0 16px 16px;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.cancel-btn {
  padding: 8px 24px;
  border-radius: 8px;
}

.save-btn {
  padding: 8px 24px;
  border-radius: 8px;
  font-weight: 600;
}

/* Form Field Styles */
.modal-content {
  padding: 24px;
}

.form-fields {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-row {
  width: 100%;
}

.form-input {
  width: 100%;
  min-width: 400px;
}

.form-input .q-field__control {
  min-height: 48px;
}

.form-input .q-field__native {
  font-size: 14px;
  padding: 12px 16px;
}

/* Dispense Modal Styles */
.dispense-modal-card {
  min-width: 480px;
  max-width: 920px;
  border-radius: 16px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
}

.dispense-header {
  padding: 16px 20px;
  border-bottom: 1px solid #eee;
}

.dispense-title {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 6px;
}

.med-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.med-icon {
  font-size: 24px;
}

.med-texts {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.med-name {
  font-size: 16px;
  font-weight: 600;
}

.med-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  font-size: 13px;
  color: #6b7280;
}

.form-grid {
  padding: 16px 20px;
}

.stock-banner {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
}

.actions-responsive {
  padding: 16px 20px;
  background: #f8f9fa;
  border-top: 1px solid #eee;
}

@media (max-width: 768px) {
  .dispense-modal-card {
    min-width: 100%;
    width: 100%;
  }
  .actions-responsive {
    justify-content: stretch;
  }
  .actions-responsive .q-btn + .q-btn {
    margin-left: 8px;
  }
}

/* Enhanced Header Styles */
.search-results-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  max-height: 300px;
  overflow-y: auto;
}

.search-result-item {
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.search-result-item:hover {
  background-color: #f5f5f5;
}

.search-result-item:last-child {
  border-bottom: none;
}

.search-result-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.search-result-icon {
  color: #286660;
}

.search-result-text {
  flex: 1;
}

.search-result-title {
  font-weight: 500;
  color: #333;
  margin-bottom: 2px;
}

.search-result-subtitle {
  font-size: 12px;
  color: #666;
}

/* Pill-style displays for time, weather, and location */
.time-display {
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.weather-display {
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.location-display {
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  gap: 8px;
  color: white;
  font-size: 14px;
  font-weight: 500;
  padding: 6px 12px;
  border-radius: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.location-loading,
.location-error {
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  gap: 6px;
  color: white;
  font-size: 14px;
  font-weight: 500;
  padding: 6px 12px;
  border-radius: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.location-error .q-icon {
  color: #ff6b6b;
}

/* Mobile responsive adjustments */
@media (max-width: 768px) {
  .header-right {
    gap: 8px;
  }

  .time-display,
  .weather-display,
  .location-display {
    font-size: 12px;
    padding: 4px 8px;
  }

  .search-container {
    min-width: 200px;
  }
}

/* Restock Modal UI */
.restock-modal {
  border-radius: 16px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
}

.restock-header {
  padding: 16px 20px;
  border-bottom: 1px solid #eee;
}

.restock-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.med-head {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.med-name {
  font-size: 18px;
  font-weight: 700;
  color: #1f2937;
}

.med-subtitle {
  font-size: 13px;
  color: #64748b;
}

.restock-stock-banner {
  padding: 8px 12px;
  border-radius: 12px;
  font-weight: 600;
}

.stock-row {
  display: flex;
  gap: 12px;
}

.stock-ok {
  background: #ecfdf5;
  color: #065f46;
}

.stock-low {
  background: #fff7ed;
  color: #9a3412;
}

.stock-out {
  background: #fee2e2;
  color: #7f1d1d;
}

.restock-inputs {
  padding: 16px 20px;
}

@media (max-width: 768px) {
  .restock-modal {
    min-width: 100%;
    width: 100%;
  }

  .restock-title-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
}
</style>
