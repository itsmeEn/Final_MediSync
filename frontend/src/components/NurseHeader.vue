<template>
  <q-header elevated class="prototype-header">
    <q-toolbar class="header-toolbar">
      <!-- Menu button to open sidebar -->
      <q-btn dense flat round icon="menu" @click="$emit('toggle-drawer')" class="menu-toggle-btn" />

      <!-- Spacer to push right content -->
      <q-space />

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

interface WeatherData {
  temperature: number;
  condition: string;
  location: string;
}

interface LocationData {
  city: string;
  country: string;
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

/* Responsive Design */
@media (max-width: 768px) {
  .header-toolbar {
    padding: 12px 16px;
    display: grid;
    grid-template-columns: auto 1fr auto auto;
    grid-template-rows: auto;
    grid-template-areas: "menu weather stock notifications";
    gap: 12px 8px;
    height: auto;
    min-height: auto;
  }

  .menu-toggle-btn {
    grid-area: menu;
    margin-right: 0;
  }

  .header-right {
    display: contents;
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
