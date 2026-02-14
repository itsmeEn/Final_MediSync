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
          @click="showNotifications = true"
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

    <!-- Notifications Dialog -->
    <q-dialog v-model="showNotifications" class="notifications-dialog">
      <q-card class="notifications-card">
        <q-card-section class="notifications-header">
          <div class="notifications-title">
            <q-icon name="notifications" size="md" />
            <span>Notifications</span>
          </div>
          <q-btn flat round icon="close" v-close-popup />
        </q-card-section>

        <q-card-section class="notifications-content">
          <div v-if="notifications.length === 0" class="no-notifications">
            <q-icon name="notifications_none" size="48px" color="grey-5" />
            <p>No notifications</p>
          </div>

          <div v-else class="notifications-list">
            <q-list>
              <q-item
                v-for="notification in notifications"
                :key="notification.id"
                clickable
                @click="handleNotificationClick(notification)"
                :class="{ unread: !notification.isRead }"
              >
                <q-item-section avatar>
                  <q-icon
                    :name="notification.type === 'message' ? 'message' : 'info'"
                    :color="notification.type === 'message' ? 'primary' : 'grey'"
                  />
                </q-item-section>
                <q-item-section>
                  <q-item-label>{{ notification.title }}</q-item-label>
                  <q-item-label caption>{{ notification.message }}</q-item-label>
                  <q-item-label caption class="text-grey-5">{{
                    formatTime(notification.created_at)
                  }}</q-item-label>
                </q-item-section>
                <q-item-section side v-if="!notification.isRead">
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
  </q-header>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { api } from 'src/boot/axios';

// Define interfaces
interface WeatherData {
  temperature: number;
  condition: string;
  location: string;
}

interface LocationData {
  city: string;
  country: string;
}

interface Notification {
  id: number;
  title: string;
  message: string;
  type: string;
  isRead: boolean;
  created_at: string;
  conversation_id?: number | undefined;
}

interface RawNotification {
  id: number;
  message?: {
    id: number;
    sender?: {
      id: number;
      full_name: string;
    };
    content: string;
    conversation?: {
      id: number;
    };
  };
  notification_type: string;
  is_sent: boolean;
  created_at: string;
}

// Define emits
defineEmits(['toggle-drawer']);

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

// Notifications functionality
const showNotifications = ref(false);
const notifications = ref<Notification[]>([]);



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

// Notifications functionality
const formatMessageNotifications = (rawNotifications: RawNotification[]): Notification[] => {
  return rawNotifications.map((notif) => {
    const notification: Notification = {
      id: notif.id,
      title: `New message from ${notif.message?.sender?.full_name || 'Unknown'}`,
      message: notif.message?.content || 'You have a new message',
      type: 'message',
      isRead: notif.is_sent || false,
      created_at: notif.created_at,
    };
    
    if (notif.message?.conversation?.id) {
      notification.conversation_id = notif.message.conversation.id;
    }
    
    return notification;
  });
};

const loadNotifications = async () => {
  try {
    console.log('📬 Loading notifications...');
    
    // Load message notifications
    const messageResponse = await api.get('/operations/messaging/notifications/');
    const messageNotifications = messageResponse.data || [];
    
    // Format the notifications for human-readable display
    const formattedNotifications = formatMessageNotifications(messageNotifications);
    
    // Sort by creation date (newest first)
    notifications.value = formattedNotifications.sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    );
    
    console.log('✅ Notifications loaded:', notifications.value.length);
  } catch (error) {
    console.error('❌ Error loading notifications:', error);
  }
};

const handleNotificationClick = (notification: Notification) => {
  notification.isRead = true;
  // Handle notification click - can be customized for doctor-specific actions
  console.log('Notification clicked:', notification);
};

const markAllNotificationsRead = () => {
  notifications.value.forEach((notification) => {
    notification.isRead = true;
  });
};

const formatTime = (timestamp: string) => {
  return new Date(timestamp).toLocaleString();
};

// Lifecycle
onMounted(() => {
  // Initialize time
  updateTime();
  timeInterval = setInterval(updateTime, 1000);

  // Fetch weather and location
  void fetchWeather();
  void fetchLocation();
  void loadNotifications();
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
.notifications-dialog .q-dialog__inner {
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.notifications-card {
  width: 400px;
  max-width: 90vw;
  max-height: 80vh;
  margin: auto;
}

.notifications-header {
  background: #286660;
  color: white;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.notifications-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.notifications-content {
  padding: 0;
  max-height: 400px;
  overflow-y: auto;
}

.no-notifications {
  text-align: center;
  padding: 40px 20px;
  color: #666;
}

.notifications-list .q-item {
  border-bottom: 1px solid #f0f0f0;
}

.notifications-list .q-item.unread {
  background: #f8f9ff;
}

.notifications-list .q-item:last-child {
  border-bottom: none;
}

/* Responsive Design */
@media (max-width: 768px) {
  .header-toolbar {
    padding: 12px 16px;
    display: grid;
    grid-template-columns: auto 1fr auto;
    grid-template-rows: auto auto;
    grid-template-areas:
      "menu weather notifications"
      "search search search";
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