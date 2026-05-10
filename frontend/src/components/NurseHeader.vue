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

interface WeatherData {
  temperature: number;
  condition: string;
  location: string;
}

interface LocationData {
  city: string;
  country: string;
}

// Define emits
defineEmits(['toggle-drawer', 'show-notifications']);

// Define props
interface Props {
  unreadNotificationsCount?: number;
}

const props = defineProps<Props>();

// Time functionality
const currentTime = ref('');
let timeInterval: NodeJS.Timeout | null = null;

// Weather functionality
const weatherData = ref<WeatherData | null>(null);
const weatherLoading = ref(false);
const weatherError = ref(false);

// Location functionality
const locationData = ref<LocationData | null>(null);
const locationLoading = ref(false);
const locationError = ref(false);

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
});

onUnmounted(() => {
  if (timeInterval) {
    clearInterval(timeInterval);
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
    grid-template-columns: auto 1fr auto;
    grid-template-rows: auto;
    grid-template-areas: "menu weather notifications";
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
