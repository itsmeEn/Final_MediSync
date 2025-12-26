<template>
  <q-header elevated class="prototype-header">
    <q-toolbar class="header-toolbar">
      <!-- Menu button to open sidebar -->
      <q-btn dense flat round icon="menu" @click="$emit('toggle-drawer')" class="menu-toggle-btn" />

      <!-- Left side - Search bar -->
      <div class="header-left">
        <div class="search-container">
          <q-input
            outlined
            dense
            v-model="searchText"
            placeholder="Search Patient, symptoms and Appointments"
            class="search-input"
            bg-color="white"
            @input="onSearchInput"
          >
            <template v-slot:prepend>
              <q-icon name="search" color="grey-6" />
            </template>
            <template v-slot:append v-if="searchText">
              <q-icon name="clear" class="cursor-pointer" @click="clearSearch" />
            </template>
          </q-input>

          <!-- Search Results Dropdown -->
          <div v-if="searchResults.length > 0" class="search-results-dropdown">
            <div
              v-for="result in searchResults"
              :key="result.id"
              class="search-result-item"
              @click="selectSearchResult(result)"
            >
              <div class="search-result-content">
                <q-icon :name="getSearchResultIcon(result.type)" class="search-result-icon" />
                <div class="search-result-text">
                  <div class="search-result-title">{{ getSearchResultTitle(result) }}</div>
                  <div class="search-result-subtitle">{{ getSearchResultSubtitle(result) }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Right side - Notifications, Time, Weather, Location -->
      <div class="header-right">
        <!-- Notifications -->
        <q-btn
          flat
          round
          icon="notifications"
          class="notification-btn"
          @click="$emit('show-notifications')"
        >
          <q-badge
            color="red"
            floating
            v-if="props.unreadNotificationsCount && props.unreadNotificationsCount > 0"
            >{{ props.unreadNotificationsCount }}</q-badge
          >
        </q-btn>

        <!-- Stock Alerts -->
        <q-btn
          flat
          round
          icon="warning"
          class="stock-alert-btn"
          @click="$emit('show-stock-alerts')"
        >
          <q-badge
            color="orange"
            floating
            v-if="stockAlertsCount > 0"
            >{{ stockAlertsCount }}</q-badge
          >
        </q-btn>

        <!-- Time Display -->
        <div class="time-display">
          <q-icon name="schedule" size="md" />
          <span class="time-text">{{ currentTime }}</span>
        </div>

        <!-- Weather Display -->
        <div class="weather-display" v-if="weatherData">
          <q-icon :name="getWeatherIcon(weatherData.condition)" size="sm" />
          <span class="weather-text">{{ weatherData.temperature }}°C</span>
          <span class="weather-location">{{ weatherData.location }}</span>
        </div>

        <!-- Loading Weather -->
        <div class="weather-loading" v-else-if="weatherLoading">
          <q-spinner size="sm" />
          <span class="weather-text">Loading weather...</span>
        </div>

        <!-- Weather Error -->
        <div class="weather-error" v-else-if="weatherError">
          <q-icon name="error" size="sm" />
          <span class="weather-text">Weather Update and Place</span>
        </div>

        <!-- Location Display -->
        <div class="location-display" v-if="locationData">
          <q-icon name="location_on" size="sm" />
          <span class="location-text">{{ locationData.city }}, {{ locationData.country }}</span>
        </div>

        <!-- Loading Location -->
        <div class="location-loading" v-else-if="locationLoading">
          <q-spinner size="sm" />
          <span class="location-text">Loading location...</span>
        </div>

        <!-- Location Error -->
        <div class="location-error" v-else-if="locationError">
          <q-icon name="error" size="sm" />
          <span class="location-text">Location unavailable</span>
        </div>
      </div>
    </q-toolbar>
  </q-header>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { api } from 'src/boot/axios';

// Define interfaces
interface SearchResult {
  id: number;
  type: string;
  data: Record<string, string | number>;
}

interface WeatherData {
  temperature: number;
  condition: string;
  location: string;
}

interface LocationData {
  city: string;
  country: string;
}

interface PatientData {
  id: number;
  patient_name?: string;
  name?: string;
  room_number?: string;
}

interface DoctorData {
  id: number;
  full_name?: string;
  name?: string;
  specialization?: string;
}

interface MedicineData {
  id: number;
  medicine_name?: string;
  name?: string;
  stock_quantity?: number;
  current_stock?: number;
  minimum_stock?: number;
  minimum_stock_level?: number;
  expiry_date?: string;
}

// Define emits
defineEmits(['toggle-drawer', 'show-notifications', 'show-stock-alerts']);

// Define props
interface Props {
  unreadNotificationsCount?: number;
}

const props = defineProps<Props>();

// Search functionality
const searchText = ref('');
const searchResults = ref<SearchResult[]>([]);

// Time functionality
const currentTime = ref('');
let timeInterval: NodeJS.Timeout | null = null;
let stockInterval: NodeJS.Timeout | null = null;

// Weather functionality
const weatherData = ref<WeatherData | null>(null);
const weatherLoading = ref(false);
const weatherError = ref(false);

// Location functionality
const locationData = ref<LocationData | null>(null);
const locationLoading = ref(false);
const locationError = ref(false);

// Stock alerts count
const stockAlertsCount = ref(0);
const READ_STOCK_KEY = 'read_stock_alert_ids';

const refreshStockAlertsCount = async () => {
  try {
    const res = await api.get('/operations/medicine-inventory/');
    const list = Array.isArray(res.data?.results) ? res.data.results : res.data;
    const items: MedicineData[] = Array.isArray(list) ? list : [] as unknown as MedicineData[];

    const raw = localStorage.getItem(READ_STOCK_KEY);
    const arr = raw ? (JSON.parse(raw) as string[]) : [];
    const readSet = new Set(Array.isArray(arr) ? arr : []);

    let lowStock = 0;
    let expiringSoon = 0;
    const now = new Date();
    const soonThresholdDays = 30;

    for (const m of items) {
      const current = Number(m.current_stock ?? m.stock_quantity ?? 0);
      const minLevel = Number(m.minimum_stock_level ?? m.minimum_stock ?? 0);

      if (!Number.isNaN(current) && !Number.isNaN(minLevel) && current <= minLevel) {
        const id = `low-${m.id}`;
        if (!readSet.has(String(id))) {
          lowStock += 1;
        }
      }

      const expiryStr = m.expiry_date ?? undefined;
      if (expiryStr) {
        const expiry = new Date(expiryStr);
        const diffDays = Math.round((expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
        if (diffDays >= 0 && diffDays <= soonThresholdDays && current > 0) {
          const id = `exp-${m.id}`;
          if (!readSet.has(String(id))) {
            expiringSoon += 1;
          }
        }
      }
    }

    stockAlertsCount.value = lowStock + expiringSoon;
  } catch (error) {
    console.error('Stock alerts count error:', error);
    stockAlertsCount.value = 0;
  }
};

// Search functionality
const onSearchInput = async () => {
  const searchValue = searchText.value.trim();
  if (!searchValue || searchValue.length < 2) {
    searchResults.value = [];
    return;
  }

  try {
    // Search for patients, doctors, and medicines using correct endpoints
    const [patientsResponse, doctorsResponse, medicinesResponse] = await Promise.all([
      api.get(`/users/nurse/patients/?search=${encodeURIComponent(searchValue)}`),
      api.get(`/operations/available-doctors/?search=${encodeURIComponent(searchValue)}`),
      api.get(`/operations/medicine-inventory/?search=${encodeURIComponent(searchValue)}`),
    ]);

    const results: SearchResult[] = [];

    // Process patients from the response
    if (patientsResponse.data.patients) {
      results.push(
        ...patientsResponse.data.patients.map((item: PatientData) => ({
          id: item.id,
          type: 'patient',
          data: {
            name: item.patient_name || item.name || 'Unknown Patient',
            id: item.id,
            room: item.room_number || 'N/A',
          },
        })),
      );
    }

    // Process doctors from the response
    if (Array.isArray(doctorsResponse.data)) {
      results.push(
        ...doctorsResponse.data.map((item: DoctorData) => ({
          id: item.id,
          type: 'doctor',
          data: {
            name: item.full_name || item.name || 'Unknown Doctor',
            id: item.id,
            specialization: item.specialization || 'General',
          },
        })),
      );
    }

    // Process medicines from the response
    if (Array.isArray(medicinesResponse.data)) {
      results.push(
        ...medicinesResponse.data.map((item: MedicineData) => ({
          id: item.id,
          type: 'medicine',
          data: {
            name: item.medicine_name || item.name || 'Unknown Medicine',
            id: item.id,
            stock: item.current_stock ?? item.stock_quantity ?? 0,
          },
        })),
      );
    }

    searchResults.value = results.slice(0, 10); // Limit to 10 results
  } catch (error) {
    console.error('Search error:', error);
    searchResults.value = [];
  }
};

const clearSearch = () => {
  searchText.value = '';
  searchResults.value = [];
};

const selectSearchResult = (result: SearchResult) => {
  // Handle search result selection
  searchResults.value = [];
  searchText.value = '';

  // Navigate based on result type
  switch (result.type) {
    case 'patient':
      // Navigate to patient details
      break;
    case 'appointment':
      // Navigate to appointment
      break;
    default:
      break;
  }
};

const getSearchResultIcon = (type: string) => {
  switch (type) {
    case 'patient':
      return 'person';
    case 'doctor':
      return 'medical_services';
    case 'medicine':
      return 'medication';
    default:
      return 'search';
  }
};

const getSearchResultTitle = (result: SearchResult) => {
  switch (result.type) {
    case 'patient':
      return result.data.name as string;
    case 'doctor':
      return result.data.name as string;
    case 'medicine':
      return result.data.name as string;
    default:
      return 'Unknown';
  }
};

const getSearchResultSubtitle = (result: SearchResult) => {
  switch (result.type) {
    case 'patient':
      return `Patient ID: ${result.data.id}${result.data.room ? ` • Room: ${result.data.room}` : ''}`;
    case 'doctor':
      return `${result.data.specialization || 'Doctor'} • ID: ${result.data.id}`;
    case 'medicine':
      return `Stock: ${(result.data.stock || 'N/A')}`;
    default:
      return '';
  }
};

// Time functionality
const updateTime = () => {
  const now = new Date();
  currentTime.value = now.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  });
};

// Weather functionality
const fetchWeather = async () => {
  weatherLoading.value = true;
  weatherError.value = false;

  try {
    // Simulate weather API call - replace with actual API
    await new Promise((resolve) => setTimeout(resolve, 1000));

    weatherData.value = {
      temperature: 28,
      condition: 'sunny',
      location: 'Manila',
    };
  } catch (error) {
    console.error('Weather fetch error:', error);
    weatherError.value = true;
  } finally {
    weatherLoading.value = false;
  }
};

const getWeatherIcon = (condition: string) => {
  switch (condition) {
    case 'sunny':
      return 'wb_sunny';
    case 'cloudy':
      return 'cloud';
    case 'rainy':
      return 'umbrella';
    case 'stormy':
      return 'thunderstorm';
    default:
      return 'wb_sunny';
  }
};

// Location functionality
const fetchLocation = async () => {
  locationLoading.value = true;
  locationError.value = false;

  try {
    // Simulate location API call - replace with actual API
    await new Promise((resolve) => setTimeout(resolve, 1000));

    locationData.value = {
      city: 'Manila',
      country: 'Philippines',
    };
  } catch (error) {
    console.error('Location fetch error:', error);
    locationError.value = true;
  } finally {
    locationLoading.value = false;
  }
};

// Lifecycle
onMounted(() => {
  // Initialize time
  updateTime();
  timeInterval = setInterval(updateTime, 1000);

  // Fetch weather and location
  void fetchWeather();
  void fetchLocation();

  // Stock alerts count
  void refreshStockAlertsCount();
  stockInterval = setInterval(() => { void refreshStockAlertsCount(); }, 60000);
});

onUnmounted(() => {
  if (timeInterval) {
    clearInterval(timeInterval);
  }
  if (stockInterval) {
    clearInterval(stockInterval);
  }
});
</script>

<style scoped>
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

.search-container {
  width: 100%;
  max-width: 500px;
  position: relative;
}

.search-input {
  background: white;
  border-radius: 8px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.notification-btn {
  color: white;
}

.stock-alert-btn {
  color: white;
}

.time-display {
  display: flex;
  align-items: center;
  gap: 8px;
  color: white;
}

.time-text {
  font-size: 14px;
  font-weight: 500;
}

.weather-display {
  display: flex;
  align-items: center;
  gap: 8px;
  color: white;
}

.weather-text {
  font-size: 14px;
  font-weight: 500;
}

.weather-location {
  font-size: 14px;
  font-weight: 500;
}

.weather-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  color: white;
}

.weather-error {
  display: flex;
  align-items: center;
  gap: 8px;
  color: white;
}

.location-display {
  display: flex;
  align-items: center;
  gap: 8px;
  color: white;
}

.location-text {
  font-size: 14px;
  font-weight: 500;
}

.location-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  color: white;
}

.location-error {
  display: flex;
  align-items: center;
  gap: 8px;
  color: white;
}

/* Search Results Dropdown */
.search-results-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 1000;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  margin-top: 4px;
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
  margin-bottom: 4px;
}

.search-result-subtitle {
  font-size: 0.875rem;
  color: #666;
}

/* Responsive Design */
@media (max-width: 768px) {
  .header-toolbar {
    padding: 12px 16px;
    display: grid;
    grid-template-columns: auto 1fr auto auto;
    grid-template-rows: auto auto;
    grid-template-areas:
      "menu weather stock notifications"
      "search search search search";
    gap: 12px 8px;
    height: auto;
    min-height: auto;
  }

  .menu-toggle-btn {
    grid-area: menu;
    margin-right: 0;
  }

  .header-left,
  .header-right {
    display: contents;
  }

  .search-container {
    grid-area: search;
    width: 100%;
    max-width: none;
  }

  .notification-btn {
    grid-area: notifications;
    margin-left: auto;
  }

  .stock-alert-btn {
    grid-area: stock;
  }

  .weather-display {
    grid-area: weather;
    justify-content: center;
    width: 100%;
  }

  .weather-location,
  .location-display,
  .time-display,
  .weather-loading,
  .weather-error,
  .location-loading,
  .location-error {
    display: none !important;
  }
}

@media (max-width: 480px) {
  .header-right {
    gap: 8px;
  }

  .time-display,
  .weather-display,
  .location-display {
    font-size: 12px;
  }
}
</style>
