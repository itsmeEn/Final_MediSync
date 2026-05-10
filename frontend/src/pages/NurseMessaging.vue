<template>
  <q-layout view="hHh Lpr fFf">
    <NurseHeader
      @toggle-drawer="toggleRightDrawer"
      @show-notifications="showNotifications = true"
      :unread-notifications-count="unreadNotificationsCount"
      :search-text="searchText"
      @search-input="onSearchInput"
      @clear-search="clearSearch"
      :search-results="searchResults"
      @select-search-result="selectSearchResult"
      :get-search-result-icon="getSearchResultIcon"
      :get-search-result-title="getSearchResultTitle"
      :get-search-result-subtitle="getSearchResultSubtitle"
    />

    <NurseSidebar v-model="rightDrawerOpen" :activeRoute="'nurse-messaging'" />

    <q-page-container class="page-container-with-fixed-header role-body-bg">
      <!-- Main Content -->
      <div class="messaging-content">
        <!-- Header Section -->
        <div class="greeting-section">
          <q-card class="greeting-card">
            <q-card-section class="greeting-content">
              <div class="greeting-text">
                <h4 class="greeting-title">Messages</h4>
                <p class="greeting-subtitle">Secure communication with your team</p>
              </div>
            </q-card-section>
          </q-card>
        </div>

        <!-- Main Messaging Card -->
        <div class="main-messaging-section">
          <!-- Verification Required Overlay -->
          <div v-if="userProfile.verification_status !== 'approved'" class="verification-overlay">
            <q-card class="verification-card">
              <q-card-section class="verification-content">
                <q-icon name="warning" size="64px" color="orange" />
                <h4 class="verification-title">Account Verification Required</h4>
                <p class="verification-message">
                  Your account needs to be verified before you can access messaging functionality.
                  Please upload your verification document to complete the process.
                </p>
                <q-chip color="negative" text-color="white" size="lg" icon="cancel">
                  Not Verified
                </q-chip>
                <q-btn
                  color="primary"
                  label="Upload Verification Document"
                  icon="upload_file"
                  @click="$router.push('/verification')"
                  class="q-mt-md"
                  unelevated
                />
              </q-card-section>
            </q-card>
          </div>

          <q-card
            class="glassmorphism-card main-messaging-card"
            :class="{ 'disabled-content': userProfile.verification_status !== 'approved' }"
          >
            <!-- Available Users Section -->
            <q-card-section class="card-header">
              <h5 class="card-title">Available Users</h5>
              <q-btn
                color="primary"
                icon="refresh"
                size="sm"
                @click="loadAvailableUsers"
                :loading="loading"
              />
            </q-card-section>

            <q-card-section class="card-content">
              <div v-if="loading" class="loading-section">
                <q-spinner color="primary" size="2em" />
                <p class="loading-text">Loading users...</p>
              </div>

              <div v-else-if="availableUsers.length === 0" class="empty-section">
                <q-icon name="people" size="48px" color="grey-5" />
                <p class="empty-text">No users available</p>
              </div>

              <div v-else class="users-scroll">
                <div class="scroll-actions">
                  <q-btn round dense icon="chevron_left" @click="scrollUsers('left')" aria-label="Scroll left" />
                  <q-btn round dense icon="chevron_right" @click="scrollUsers('right')" aria-label="Scroll right" />
                </div>
                <div class="users-scroll-viewport" ref="usersScrollEl">
                  <div class="users-row">
                    <div
                      v-for="user in availableUsers"
                      :key="user.id"
                      class="user-item"
                      @click="startConversation(user)"
                    >
                      <div class="avatar-container">
                        <q-avatar size="80px" class="user-avatar">
                          <img
                            v-if="user.profile_picture"
                            :src="
                              user.profile_picture.startsWith('http')
                                ? user.profile_picture
                                : getMediaUrl(user.profile_picture)
                            "
                            :alt="user?.full_name || 'User'"
                            @error="user.profile_picture = ''"
                          />
                          <div v-else class="avatar-initials">{{ getInitials(user?.full_name || '') }}</div>
                        </q-avatar>
                        
                        <q-badge
                          v-if="user.verification_status === 'approved'"
                          floating
                          color="positive"
                          class="verification-badge"
                        >
                          <q-icon name="verified" size="16px" />
                        </q-badge>
                      </div>

                      <div class="avatar-info">
                        <h6 class="avatar-name">{{ user.full_name || 'User' }}</h6>
                        <p class="avatar-role">{{ user.role === 'doctor' ? 'Dr.' : 'Nurse' }}</p>
                        
                        <q-chip
                          v-if="user.verification_status === 'approved'"
                          color="positive"
                          text-color="white"
                          size="xs"
                          icon="verified_user"
                          class="verification-chip"
                        >
                          Verified
                        </q-chip>
                      </div>

                      <q-btn flat round icon="chat" color="primary" size="sm" class="chat-btn" />
                    </div>
                  </div>
                </div>
              </div>
            </q-card-section>

            <!-- Start New Conversation Button -->
            <q-card-section class="new-conversation-section">
              <div class="new-conversation-container">
                <q-btn
                  class="glassmorphism-btn new-conversation-btn"
                  @click="handleNewConversationClick"
                  :disable="userProfile.verification_status !== 'approved'"
                >
                  <q-icon name="add" class="btn-icon" />
                  Start New Conversation
                </q-btn>
              </div>
            </q-card-section>

            <!-- Recent Conversations Section -->
            <q-card-section class="conversations-section">
              <div class="conversations-header">
                <h5 class="conversations-title">Recent Conversations</h5>
                <q-btn
                  color="secondary"
                  icon="add"
                  size="sm"
                  @click="handleNewConversationClick"
                  :disable="userProfile.verification_status !== 'approved'"
                />
              </div>

              <div v-if="conversations.length === 0" class="empty-section">
                <q-icon name="chat" size="48px" color="grey-5" />
                <p class="empty-text">No conversations yet</p>
                <p class="empty-subtext">Start a conversation with a user</p>
              </div>

              <div v-else class="conversations-list">
                <div
                  v-for="conversation in conversations"
                  :key="conversation.id"
                  class="conversation-card glassmorphism-conversation-card"
                  @click="selectConversation(conversation)"
                >
                  <div class="conversation-avatar">
                    <q-avatar size="45px">
                      <img
                        v-if="conversation.other_participant?.profile_picture"
                      :src="
                          conversation.other_participant.profile_picture.startsWith('http')
                            ? conversation.other_participant.profile_picture
                            : getMediaUrl(conversation.other_participant.profile_picture)
                        "
                        :alt="conversation.other_participant?.full_name || 'User'"
                        @error="conversation.other_participant && (conversation.other_participant.profile_picture = '')"
                      />
                      <div v-else class="avatar-initials">{{ getInitials(conversation.other_participant?.full_name || '') }}</div>
                    </q-avatar>
                  </div>

                  <div class="conversation-info">
                    <h6 class="conversation-name">
                      {{ conversation.other_participant?.full_name || 'Name of Users' }}
                    </h6>
                    <p class="conversation-preview">
                      {{ conversation.last_message?.content || 'Chat content here' }}
                    </p>
                  </div>

                  <div class="conversation-meta">
                    <span class="conversation-time">
                      {{ formatTime(conversation.last_message?.created_at) }}
                    </span>
                    <q-badge
                      v-if="conversation.unread_count > 0"
                      color="primary"
                      :label="conversation.unread_count"
                      class="unread-badge"
                    />
                  </div>
                </div>
              </div>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <!-- Chat Modal -->
      <q-dialog v-model="showChatModal" persistent>
        <q-card class="chat-modal">
          <q-card-section class="chat-header">
            <div class="chat-user-info">
              <q-avatar size="40px">
                <img
                  v-if="selectedUser?.profile_picture"
                  :src="
                    selectedUser.profile_picture.startsWith('http')
                      ? selectedUser.profile_picture
                      : getMediaUrl(selectedUser.profile_picture)
                  "
                  :alt="selectedUser.full_name"
                  @error="selectedUser && (selectedUser.profile_picture = '')"
                />
                <q-icon
                  v-else
                  :name="selectedUser?.role === 'doctor' ? 'medical_services' : 'local_hospital'"
                  size="20px"
                  color="white"
                />
              </q-avatar>
              <div class="chat-user-details">
                <h6 class="text-h6 text-white q-mb-none">
                  {{ selectedUser?.full_name || 'Unknown User' }}
                </h6>
                <p class="text-white-7 text-caption q-mb-none">
                  {{ selectedUser?.role === 'doctor' ? 'Doctor' : 'Nurse' }}
                </p>
              </div>
            </div>
            <q-btn flat round icon="close" @click="showChatModal = false" />
          </q-card-section>

          <q-card-section class="chat-messages">
            <div v-if="messages.length === 0" class="no-messages">
              <q-icon name="message" size="48px" color="grey-5" />
              <p class="text-grey-6">No messages yet</p>
              <p class="text-grey-6 text-caption">Start the conversation by sending a message</p>
            </div>

            <div
              v-for="message in messages"
              :key="message.id"
              class="message"
              :class="{ 'own-message': message.sender.id === currentUser.id }"
            >
              <div class="message-content">
                <div class="message-header">
                  <q-avatar size="32px">
                    <img
                      v-if="message.sender.profile_picture"
                      :src="
                        message.sender.profile_picture.startsWith('http')
                          ? message.sender.profile_picture
                          : getMediaUrl(message.sender.profile_picture)
                      "
                      :alt="message.sender?.full_name || 'User'"
                      @error="message.sender.profile_picture = ''"
                    />
                    <div v-else class="avatar-initials">{{ getInitials(message.sender?.full_name || '') }}</div>
                  </q-avatar>
                  <span class="message-sender text-white-7">
                    {{ message.sender.full_name }}
                  </span>
                  <span class="message-time text-white-7">
                    {{ formatTime(message.created_at) }}
                  </span>
                </div>

                <div class="message-body">
                  <p v-if="message.content" class="message-text">
                    {{ message.content }}
                  </p>
                </div>
              </div>
            </div>
          </q-card-section>

          <q-card-section class="chat-input">
            <div class="input-container">
              <q-input
                v-model="newMessage"
                placeholder="Type a message..."
                @keyup.enter="sendMessage"
                :disable="!selectedUser"
                class="message-input"
              >
                <template v-slot:append>
                  <q-btn
                    flat
                    round
                    icon="send"
                    color="primary"
                    @click="sendMessage"
                    :disable="!newMessage.trim()"
                  />
                </template>
              </q-input>
            </div>
          </q-card-section>
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
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useQuasar } from 'quasar';
import { api } from 'boot/axios';
import NurseHeader from '../components/NurseHeader.vue';
import NurseSidebar from 'src/components/NurseSidebar.vue';
import { getMediaUrl } from 'src/utils/mediaUrl';

// Types
interface User {
  id: number;
  full_name: string;
  role: string;
  profile_picture?: string;
  is_active?: boolean;
  verification_status?: string;
  is_verified?: boolean;
}

interface Message {
  id: number;
  sender: User;
  content: string;
  created_at: string;
}

interface Conversation {
  id: number;
  other_participant?: User;
  last_message?: Message;
  unread_count: number;
}

// Reactive data
const $q = useQuasar();
const rightDrawerOpen = ref(false);
const loading = ref(false);
const searchText = ref('');
const currentTime = ref('');

// Notification system
const showNotifications = ref(false);
const notifications = ref<Notification[]>([]);

interface Notification {
  id: number | string;
  title: string;
  message: string;
  type: 'message' | 'system';
  isRead: boolean;
  created_at: string;
  sender_id?: number | undefined;
  conversation_id?: number | undefined;
}

// Raw notification data from backend
interface RawNotification {
  id: number;
  message?: {
    sender?: {
      full_name?: string;
      id?: number;
    };
    content?: string;
    conversation?: {
      id?: number;
    };
  };
  is_sent?: boolean;
  created_at: string;
}
const availableUsers = ref<User[]>([]);
const conversations = ref<Conversation[]>([]);
const messages = ref<Message[]>([]);
const currentUser = ref<User>({ id: 0, full_name: '', role: '' });
const selectedUser = ref<User | null>(null);
const selectedConversation = ref<Conversation | null>(null);
const showChatModal = ref(false);
const showNewConversationDialog = ref(false);
const newMessage = ref('');
// Horizontal scroll ref for available users list
const usersScrollEl = ref<HTMLElement | null>(null);

// Search functionality
// Search result interfaces
interface PatientData {
  id: string | number;
  full_name?: string;
  name?: string;
  [key: string]: unknown;
}

interface DoctorData {
  id: string | number;
  full_name?: string;
  name?: string;
  specialization?: string;
  [key: string]: unknown;
}
type SearchResultData = PatientData | DoctorData;

const searchResults = ref<
  Array<{
    type: 'patient' | 'doctor';
    data: SearchResultData;
  }>
>([]);

// Location data
const locationData = ref<{
  city: string;
  country: string;
} | null>(null);
const locationLoading = ref(false);
const locationError = ref(false);

// Weather data
const weatherData = ref<{
  temperature: number;
  condition: string;
  location: string;
} | null>(null);
const weatherLoading = ref(false);
const weatherError = ref(false);

// User profile
const userProfile = ref<{
  full_name: string;
  specialization?: string;
  role: string;
  profile_picture: string | null;
  verification_status: string;
}>({
  full_name: 'Loading...',
  role: 'nurse',
  profile_picture: null,
  verification_status: 'not_submitted',
});

// Computed

const unreadNotificationsCount = computed(() => {
  return notifications.value.filter((n) => !n.isRead).length;
});

// Smooth horizontal scrolling controls for users list
const scrollUsers = (dir: 'left' | 'right'): void => {
  const el = usersScrollEl.value;
  if (!el) return;
  const amount = Math.round(el.clientWidth * 0.8);
  el.scrollBy({ left: dir === 'left' ? -amount : amount, behavior: 'smooth' });
};

// Helper: derive initials from a full name
const getInitials = (name: string): string => {
  const safe = (name || '').trim();
  if (!safe) return 'U';
  const parts = safe.split(/\s+/);
  const initials = parts.slice(0, 2).map(p => (p[0] || '').toUpperCase()).join('');
  // Use charAt to avoid undefined when string is empty; final fallback 'U'
  return initials || (safe ? safe.charAt(0).toUpperCase() : 'U');
};

// Methods
const getCurrentUser = (): void => {
  try {
    const userData = localStorage.getItem('user');
    if (userData) {
      currentUser.value = JSON.parse(userData);
      console.log('👤 Current user loaded:', currentUser.value);
    } else {
      console.error('❌ No user data found in localStorage');
    }
  } catch (error) {
    console.error('❌ Error parsing user data:', error);
  }
};

// Fetch user profile from API
const fetchUserProfile = async () => {
  try {
    const response = await api.get('/users/profile/');
    const userData = response.data.user; // The API returns nested user data

    // Check localStorage for updated profile picture
    const storedUser = JSON.parse(localStorage.getItem('user') || '{}');

    userProfile.value = {
      full_name: userData.full_name,
      role: userData.role,
      profile_picture: storedUser.profile_picture || userData.profile_picture || null,
      verification_status: userData.verification_status,
    };

    console.log('👤 User profile loaded:', userProfile.value);
  } catch (error) {
    console.error('Failed to fetch user profile:', error);

    // Fallback to localStorage
    const userData = localStorage.getItem('user');
    if (userData) {
      const user = JSON.parse(userData);
      userProfile.value = {
        full_name: user.full_name,
        role: user.role,
        profile_picture: user.profile_picture || null,
        verification_status: user.verification_status || 'not_submitted',
      };
    }
  }
};


const loadAvailableUsers = async (): Promise<void> => {
  try {
    loading.value = true;
    console.log('📞 Loading available users...');

    const response = await api.get('/operations/messaging/available-users/');
    
    // Handle new API response format
    if (response.data.users) {
      availableUsers.value = response.data.users;
      console.log('✅ Available users loaded:', availableUsers.value);
      console.log('📊 Total verified users found:', response.data.total_count);
      console.log('🔒 Security message:', response.data.message);
      
      // Show success notification with verification info
      $q.notify({
        type: 'positive',
        message: response.data.message || `Found ${response.data.total_count} verified users`,
        timeout: 3000
      });

      // Informative notice when no users are returned
      if (response.data.total_count === 0) {
        $q.notify({
          type: 'warning',
          message: 'No verified users found in your hospital. Check your profile hospital and verification status.',
          timeout: 4000
        });
      }
    } else {
      // Fallback for old API format
      availableUsers.value = response.data;
      console.log('Available users loaded (legacy format):', availableUsers.value);
      if (Array.isArray(availableUsers.value) && availableUsers.value.length === 0) {
        $q.notify({
          type: 'warning',
          message: 'No verified users found in your hospital. Check your profile hospital and verification status.',
          timeout: 4000
        });
      }
    }

    // Log each user's verification status
    availableUsers.value.forEach((user: User) => {
      console.log(`👤 User: ${user.full_name}, Role: ${user.role}, Verified: ${user.verification_status === 'approved'}`);
    });
  } catch (error: unknown) {
    console.error('❌ Error loading available users:', error);
    
    // Type guard for Axios errors
    const isAxiosError = (err: unknown): err is { response: { status: number } } => {
      return err !== null && typeof err === 'object' && 'response' in err;
    };
    
    // Handle specific verification errors
    if (isAxiosError(error) && error.response?.status === 403) {
      $q.notify({
        type: 'negative',
        message: 'Access denied: Your account must be verified to access messaging',
        timeout: 5000
      });
    } else {
      $q.notify({
        type: 'negative',
        message: 'Failed to load users',
      });
    }
  } finally {
    loading.value = false;
  }
};

const loadConversations = async (): Promise<void> => {
  try {
    console.log('📞 Loading conversations...');

    const response = await api.get('/operations/messaging/conversations/');
    conversations.value = response.data;
    console.log('✅ Conversations loaded:', conversations.value);
  } catch (error) {
    console.error('❌ Error loading conversations:', error);
  }
};

const startConversation = (user: User): void => {
  // Check if user is verified before allowing messaging
  if (userProfile.value.verification_status !== 'approved') {
    $q.notify({
      type: 'negative',
      message: 'Account verification required to access messaging',
      position: 'top',
    });
    return;
  }

  selectedUser.value = user;
  showChatModal.value = true;
  void loadMessagesForUser(user.id);
};

const selectConversation = (conversation: Conversation): void => {
  // Check if user is verified before allowing messaging
  if (userProfile.value.verification_status !== 'approved') {
    $q.notify({
      type: 'negative',
      message: 'Account verification required to access messaging',
      position: 'top',
    });
    return;
  }

  selectedConversation.value = conversation;
  if (conversation.other_participant) {
    selectedUser.value = conversation.other_participant;
    showChatModal.value = true;
    void loadMessagesForUser(conversation.other_participant.id);
  }
};

const loadMessagesForUser = async (userId: number): Promise<void> => {
  try {
    console.log('📞 Loading messages for user:', userId);

    const conversation = conversations.value.find((c) => c.other_participant?.id === userId);

    if (conversation) {
      const response = await api.get(
        `/operations/messaging/conversations/${conversation.id}/messages/`,
      );
      messages.value = response.data;
      console.log('✅ Messages loaded:', messages.value);
    } else {
      messages.value = [];
      console.log('ℹ️ No conversation found, starting fresh');
    }
  } catch (error) {
    console.error('❌ Error loading messages:', error);
    messages.value = [];
  }
};

const sendMessage = async (): Promise<void> => {
  if (!newMessage.value.trim() || !selectedUser.value) return;

  // Check if user is verified before allowing messaging
  if (userProfile.value.verification_status !== 'approved') {
    $q.notify({
      type: 'negative',
      message: 'Account verification required to send messages',
      position: 'top',
    });
    return;
  }

  try {
    console.log('📤 Sending message:', newMessage.value);

    let conversation = conversations.value.find(
      (c) => c.other_participant?.id === selectedUser.value?.id,
    );

    if (!conversation) {
      console.log('📝 Creating new conversation with user:', selectedUser.value.id);
      const response = await api.post('/operations/messaging/conversations/create/', {
        other_user_id: selectedUser.value.id,
      });
      console.log('✅ Conversation created:', response.data);
      conversation = response.data as Conversation;
      conversations.value.unshift(conversation);
    }

    if (conversation) {
      await api.post(`/operations/messaging/conversations/${conversation.id}/send/`, {
        content: newMessage.value,
      });

      newMessage.value = '';
      await loadMessagesForUser(selectedUser.value.id);
      await loadConversations();

      $q.notify({
        type: 'positive',
        message: 'Message sent successfully',
      });
    }
  } catch (error: unknown) {
    console.error('Error sending message:', error);
    const axiosError = error as {
      response?: { data?: { error?: string }; status?: number };
      message?: string;
    };
    console.error('Error details:', axiosError.response?.data);
    console.error('Error status:', axiosError.response?.status);
    $q.notify({
      type: 'negative',
      message: `Failed to send message: ${axiosError.response?.data?.error || axiosError.message || 'Unknown error'}`,
    });
  }
};

const handleNewConversationClick = (): void => {
  // Check if user is verified before allowing new conversations
  if (userProfile.value.verification_status !== 'approved') {
    $q.notify({
      type: 'negative',
      message: 'Account verification required to start new conversations',
      position: 'top',
    });
    return;
  }

  showNewConversationDialog.value = true;
};

const formatTime = (dateString?: string): string => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

const toggleRightDrawer = (): void => {
  rightDrawerOpen.value = !rightDrawerOpen.value;
};



const updateTime = (): void => {
  const now = new Date();
  currentTime.value = now.toLocaleTimeString('en-US', {
    hour12: true,
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
  });
};

// Notification functions
const loadNotifications = async (): Promise<void> => {
  try {
    console.log('📬 Loading notifications...');

    // Load message notifications
    const messageResponse = await api.get('/operations/messaging/notifications/');
    const messageNotifications = messageResponse.data || [];

    // Combine and format all notifications
    const allNotifications = [
      ...formatMessageNotifications(messageNotifications),
    ];

    // Sort by creation date (newest first)
    notifications.value = allNotifications.sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    );

    console.log('✅ Notifications loaded:', notifications.value.length);
  } catch (error: unknown) {
    console.error('❌ Error loading notifications:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to load notifications',
    });
  }
};

// Format message notifications from backend
const formatMessageNotifications = (rawNotifications: RawNotification[]): Notification[] => {
  return rawNotifications.map((notif) => ({
    id: notif.id,
    title: `New message from ${notif.message?.sender?.full_name || 'Unknown'}`,
    message: notif.message?.content || 'You have a new message',
    type: 'message' as const,
    isRead: notif.is_sent || false,
    created_at: notif.created_at,
    sender_id: notif.message?.sender?.id,
    conversation_id: notif.message?.conversation?.id,
  }));
};

const handleNotificationClick = (notification: Notification): void => {
  // Mark as read
  notification.isRead = true;

  // If it's a message notification, open the chat
  if (notification.type === 'message' && notification.conversation_id) {
    showNotifications.value = false;
    // Find and open the conversation
    const conversation = conversations.value.find((c) => c.id === notification.conversation_id);
    if (conversation && conversation.other_participant) {
      selectedUser.value = conversation.other_participant;
      showChatModal.value = true;
      void loadMessagesForUser(conversation.other_participant.id);
    }
  }
};

const markAllNotificationsRead = async (): Promise<void> => {
  try {
    // Mark all notifications as read locally
    notifications.value.forEach((notification) => {
      notification.isRead = true;
    });

    // Mark message notifications as read on backend
    const messageNotifications = notifications.value.filter((n) => n.type === 'message');
    for (const notification of messageNotifications) {
      try {
        await api.post(`/operations/messaging/notifications/${notification.id}/mark-sent/`);
      } catch (error) {
        console.error('Error marking notification as read:', error);
      }
    }

    // Update the notification count
    await loadNotifications();

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

// Search functionality methods
const onSearchInput = async (value: string | number | null): Promise<void> => {
  const searchValue = String(value || '');
  if (!searchValue || searchValue.length < 2) {
    searchResults.value = [];
    return;
  }

  try {
    // Search for patients and doctors using correct endpoints
    const [patientsResponse, doctorsResponse] = await Promise.all([
      api.get(`/users/nurse/patients/?search=${encodeURIComponent(searchValue)}`),
      api.get(`/operations/availability/doctors/free/`, { params: { search: searchValue } }),
    ]);

    const results = [
      ...(patientsResponse.data.patients || []).map((item: PatientData) => ({
        type: 'patient' as const,
        data: item,
      })),
      ...((doctorsResponse.data?.doctors || []) as DoctorData[]).map((item: DoctorData) => ({
        type: 'doctor' as const,
        data: item,
      })),
    ];

    searchResults.value = results.slice(0, 10); // Limit to 10 results
  } catch (error) {
    console.error('Search error:', error);
    searchResults.value = [];
  }
};

const clearSearch = (): void => {
  searchText.value = '';
  searchResults.value = [];
};

const selectSearchResult = (result: { type: 'patient' | 'doctor'; data: SearchResultData }): void => {
  // Handle search result selection based on type
  switch (result.type) {
    case 'patient':
      // Navigate to patient details or start conversation
      console.log('Selected patient:', result.data);
      break;
    case 'doctor':
      // Start conversation with doctor
      if (result.data) {
        const doctorData = result.data;
        selectedUser.value = {
          id: Number(doctorData.id),
          full_name: doctorData.full_name || doctorData.name || 'Unknown Doctor',
          role: 'doctor',
          profile_picture: (doctorData as Record<string, unknown>).profile_picture as string,
          is_active: true,
        };
        showChatModal.value = true;
        void loadMessagesForUser(Number(doctorData.id));
      }
      break;
  }
  clearSearch();
};

const getSearchResultIcon = (type: 'patient' | 'doctor'): string => {
  switch (type) {
    case 'patient':
      return 'person';
    case 'doctor':
      return 'medical_services';
    default:
      return 'search';
  }
};

const getSearchResultTitle = (result: { type: 'patient' | 'doctor'; data: SearchResultData }): string => {
  switch (result.type) {
    case 'patient': {
      return result.data.full_name || result.data.name || 'Unknown';
    }
    case 'doctor': {
      return result.data.full_name || result.data.name || 'Unknown';
    }
    default:
      return 'Unknown';
  }
};

const getSearchResultSubtitle = (result: { type: 'patient' | 'doctor'; data: SearchResultData }): string => {
  switch (result.type) {
    case 'patient':
      return `Patient ID: ${result.data.id}`;
    case 'doctor': {
      const specialization = (result.data as Record<string, unknown>).specialization;
      return `Doctor - ${typeof specialization === 'string' ? specialization : 'General'}`;
    }
    default:
      return '';
  }
};

// Location functionality
const fetchLocation = async (): Promise<void> => {
  locationLoading.value = true;
  locationError.value = false;

  try {
    // Mock location data - replace with actual geolocation API
    await new Promise((resolve) => setTimeout(resolve, 1000));
    locationData.value = {
      city: 'Mandaluyong City',
      country: 'Philippines',
    };
  } catch (error) {
    console.error('Failed to fetch location:', error);
    locationError.value = true;
  } finally {
    locationLoading.value = false;
  }
};

// Fetch weather data
const fetchWeatherData = async (): Promise<void> => {
  weatherLoading.value = true;
  weatherError.value = false;

  try {
    // Mock weather data - replace with actual API call
    await new Promise((resolve) => setTimeout(resolve, 1000));
    weatherData.value = {
      temperature: 28,
      condition: 'sunny',
      location: 'Mandaluyong City',
    };
  } catch (error) {
    console.error('Failed to fetch weather data:', error);
    weatherError.value = true;
  } finally {
    weatherLoading.value = false;
  }
};

// Lifecycle
onMounted(() => {
  console.log('NurseMessaging component mounted');
  getCurrentUser();
  void fetchUserProfile();
  updateTime();
  setInterval(updateTime, 1000);
  void loadAvailableUsers();
  void loadConversations();
  void loadNotifications();
  void fetchWeatherData();
  void fetchLocation();

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
</script>

<style scoped>
/* Prototype Header Styles */

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
  position: relative;
}

.search-input {
  background: white;
  border-radius: 8px;
}

.search-results {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  max-height: 300px;
  overflow-y: auto;
}

.notification-btn {
  color: white;
}

/* Pill-style displays for time, weather, and location */
.time-pill,
.weather-pill,
.location-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 20px;
  padding: 6px 12px;
  color: white;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.time-pill:hover,
.weather-pill:hover,
.location-pill:hover {
  background: rgba(255, 255, 255, 0.25);
  transform: translateY(-1px);
}

.time-text,
.weather-text,
.location-text {
  white-space: nowrap;
}

/* Mobile responsive adjustments */
@media (max-width: 768px) {
  .header-right {
    gap: 12px;
  }

  .time-pill,
  .weather-pill,
  .location-pill {
    padding: 4px 8px;
    font-size: 12px;
  }

  .time-text,
  .weather-text,
  .location-text {
    display: none;
  }
}

/* Notification styles */
.unread {
  background-color: #f0f8ff;
  border-left: 4px solid #286660;
}

.unread .q-item__label {
  font-weight: 600;
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
}

/* Prototype Sidebar Styles */
.prototype-sidebar {
  background: white;
  border-right: 1px solid #e0e0e0;
  position: relative;
}

.sidebar-content {
  height: 100%;
  display: flex;
  flex-direction: column;
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


/* Responsive design for different screen sizes */
@media (max-width: 768px) {
  .profile-picture-container {
    width: 50px !important;
    height: 50px !important;
  }

  .upload-btn {
    width: 24px !important;
    height: 24px !important;
    min-height: 24px !important;
  }
}

@media (max-width: 480px) {
  .profile-picture-container {
    width: 45px !important;
    height: 45px !important;
  }

  .upload-btn {
    width: 22px !important;
    height: 22px !important;
    min-height: 22px !important;
  }

  .profile-avatar,
  .profile-placeholder {
    font-size: 14px !important;
  }
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

/* Page Container with Off-White Background */
.page-container-with-fixed-header {
  background: #f8f9fa;
  min-height: 100vh;
  position: relative;
}

/* Messaging Content */
.messaging-content {
  padding: 24px;
}

/* Greeting Section */
.greeting-section {
  margin-bottom: 24px;
}

.greeting-card {
  background: linear-gradient(135deg, #ffffff 0%, #f7fbf9 100%);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  border: 1px solid rgba(40, 102, 96, 0.08);
  box-shadow: 0 10px 30px rgba(40, 102, 96, 0.08);
  position: relative;
  overflow: hidden;
}

.greeting-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #286660, #6ca299, #b8d2ce);
  border-radius: 20px 20px 0 0;
}

.greeting-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
}

.greeting-title {
  font-size: 2rem;
  font-weight: 700;
  color: #286660;
  margin: 0 0 8px 0;
}

.greeting-subtitle {
  font-size: 1.1rem;
  color: #666;
  margin: 0;
}

.greeting-icon {
  color: #286660;
}

/* Glassmorphism Cards */
.glassmorphism-card {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  margin-bottom: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
}

.card-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #286660;
  margin: 0;
}

.card-content {
  padding: 20px 24px;
  flex: 1;
  display: flex;
  flex-direction: column;
}

/* Verification Overlay */
.verification-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 20px;
}

.verification-card {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  max-width: 400px;
  margin: 20px;
}

.verification-content {
  text-align: center;
  padding: 40px 30px;
}

.verification-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #333;
  margin: 20px 0 16px 0;
}

.verification-message {
  font-size: 1rem;
  color: #666;
  line-height: 1.6;
  margin-bottom: 24px;
}

.disabled-content {
  opacity: 0.3;
  pointer-events: none;
  filter: blur(2px);
}

/* Main Messaging Section */
.main-messaging-section {
  position: relative;
  margin-bottom: 24px;
}

.main-messaging-card {
  max-width: none;
  margin: 0;
  width: 100%;
}

/* Users Grid */
.users-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 16px;
  flex: 1;
}

.glassmorphism-user-card {
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  padding: 16px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  text-align: center;
}

.glassmorphism-user-card:hover {
  background: rgba(255, 255, 255, 0.25);
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.user-avatar-container {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-avatar {
  border: 2px solid rgba(255, 255, 255, 0.3);
}

.user-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.user-name {
  font-size: 0.9rem;
  font-weight: 600;
  color: #333;
  margin: 0;
  text-align: center;
}

.user-role {
  font-size: 0.75rem;
  color: #666;
  margin: 0;
  text-align: center;
}

.chat-btn {
  margin-top: 8px;
}

/* New Conversation Section */
.new-conversation-section {
  padding: 20px 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
}

.new-conversation-container {
  text-align: center;
}

.glassmorphism-btn {
  background: rgba(255, 255, 255, 0.2) !important;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 12px;
  padding: 12px 24px;
  font-weight: 500;
  text-transform: none;
  color: #286660 !important;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.glassmorphism-btn:hover {
  background: rgba(255, 255, 255, 0.3) !important;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
}

.btn-icon {
  margin-right: 8px;
}

/* Conversations Section */
.conversations-section {
  padding: 20px 24px;
}

.conversations-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.conversations-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #286660;
  margin: 0;
}

.conversations-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
}

.glassmorphism-conversation-card {
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  padding: 16px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 12px;
}

.glassmorphism-conversation-card:hover {
  background: rgba(255, 255, 255, 0.25);
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.conversation-info {
  flex: 1;
}

.conversation-name {
  font-size: 0.95rem;
  font-weight: 600;
  color: #333;
  margin: 0 0 4px 0;
}

.conversation-preview {
  font-size: 0.8rem;
  color: #666;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conversation-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.conversation-time {
  font-size: 0.75rem;
  color: #999;
}

.unread-badge {
  font-size: 0.7rem;
}

/* Loading and Empty States */
.loading-section,
.empty-section {
  text-align: center;
  padding: 40px 20px;
}

.loading-text,
.empty-text {
  color: #666;
  margin: 12px 0 0 0;
}

.empty-subtext {
  color: #999;
  font-size: 0.9rem;
  margin: 4px 0 0 0;
}

/* Chat Modal */
.chat-modal {
  background: white;
  width: 80vw;
  max-width: 800px;
  height: 70vh;
  max-height: 600px;
  border-radius: 16px;
  overflow: hidden;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #286660;
  color: white;
  padding: 16px 20px;
}

.chat-user-info {
  display: flex;
  align-items: center;
  gap: 15px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  padding-bottom: 80px;
  max-height: 400px;
  background: white;
}

.no-messages {
  text-align: center;
  padding: 40px 20px;
}

.message {
  margin-bottom: 20px;
}

.message-content {
  background: #f5f5f5;
  border-radius: 15px;
  padding: 15px;
  border: 1px solid #e0e0e0;
  color: #333;
}

.own-message .message-content {
  background: #286660;
  color: white;
  margin-left: 50px;
}

/* Ensure all message text is readable */
.message-text {
  color: #333 !important;
}

.own-message .message-text {
  color: white !important;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.message-sender {
  font-weight: 500;
}

.message-time {
  margin-left: auto;
  font-size: 0.8em;
}

.message-text {
  margin: 0;
  line-height: 1.4;
}

.chat-input {
  background: #f8f9fa;
  border-top: 1px solid #e0e0e0;
  padding: 16px 20px;
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 10;
}

.input-container {
  display: flex;
  align-items: center;
  gap: 8px;
}

.message-input {
  flex: 1;
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

.search-container {
  width: 100%;
  max-width: 500px;
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

/* Notification styles */
.unread {
  background-color: #f0f8ff;
  border-left: 4px solid #286660;
}

.unread .q-item__label {
  font-weight: 600;
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

/* Horizontal Users Scroll Styles */
.users-scroll {
  margin: 20px 0;
  position: relative;
}

.scroll-actions {
  position: absolute;
  right: 10px;
  top: -8px;
  display: flex;
  gap: 8px;
}

.users-scroll-viewport {
  overflow-x: auto;
  overflow-y: hidden;
  scroll-behavior: smooth;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.35);
  box-shadow: 0 8px 24px rgba(40, 102, 96, 0.12);
  padding: 16px;
}

.users-row {
  display: flex;
  gap: 20px;
  align-items: center;
  width: max-content;
}

.user-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px;
  cursor: pointer;
  transition: all 0.3s ease;
  min-width: 120px;
  position: relative;
}

.user-item:hover {
  transform: scale(1.05);
}

.avatar-container {
  position: relative;
  margin-bottom: 10px;
}

.user-avatar {
  border: 3px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.avatar-info {
  text-align: center;
  margin-bottom: 10px;
}

.avatar-name {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin: 0 0 4px 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100px;
}

.avatar-role {
  font-size: 12px;
  color: #666;
  margin: 0 0 6px 0;
  font-weight: 500;
}

.chat-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(25, 118, 210, 0.1);
  backdrop-filter: blur(10px);
}

.chat-btn:hover {
  background: rgba(25, 118, 210, 0.2);
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

/* Responsive Design */
@media (max-width: 768px) {
  .users-row {
    gap: 15px;
  }

  .user-item {
    min-width: 100px;
    padding: 8px;
  }

  .user-avatar {
    width: 60px !important;
    height: 60px !important;
  }

  .avatar-name {
    font-size: 12px;
    max-width: 80px;
  }

  .avatar-role {
    font-size: 10px;
  }

  .avatar-status {
    font-size: 10px;
  }
}

/* Verification Badge Styles */
.verification-badge {
  position: absolute;
  top: -5px;
  right: -5px;
  border: 2px solid white;
  border-radius: 50%;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.verification-chip {
  margin-top: 4px;
  font-size: 10px;
  height: 18px;
}

.avatar-container {
  position: relative;
}

/* Initials fallback for avatars */
.avatar-initials {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #286660; /* matches theme */
  color: white;
  font-weight: 700;
  font-size: 1rem;
  border-radius: 50%;
}
</style>
