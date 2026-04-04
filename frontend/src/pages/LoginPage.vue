<template>
  <div
    class="login-page safe-area-top safe-area-bottom"
    style="
      background-color: white;
      background-size: cover;
    "
  >
    <div class="login-container">
      <div class="login-card">
        <div class="login-header">
          <h2>Welcome to MediSync</h2>
          <p>Sign in to your account</p>
        </div>

        <div class="login-form">
          <form @submit.prevent="onLogin">
            <div class="form-group">
              <label for="email">Email Address</label>
              <input
                id="email"
                v-model="email"
                type="email"
                required
                placeholder="Enter your email"
              />
            </div>

            <div class="form-group">
              <label for="password">Password</label>
              <input
                id="password"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                required
                placeholder="Enter your password"
              />
              <button type="button" @click="showPassword = !showPassword">
                {{ showPassword ? 'Hide' : 'Show' }}
              </button>
            </div>

            <div class="forgot-password">
              <button type="button" @click="$router.push('/forgot-password')" class="forgot-btn">
                Forgot Password?
              </button>
            </div>

            <button type="submit" :disabled="loading" class="login-btn">
              {{ loading ? 'Signing In...' : 'Sign In' }}
            </button>
          </form>
        </div>

        <div class="login-footer">
          <p>
            Don't have an account?
            <button @click="$router.push('/role-selection')" class="link-btn">
              Create Account
            </button>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue';
import { useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { api } from '../boot/axios';
import { isAxiosError } from 'axios';
import { updateApiEndpoint, getNetworkInfo } from '../utils/mobileConnectivity';

const router = useRouter();
const $q = useQuasar();

const email = ref('');
const password = ref('');
const showPassword = ref(false);
const loading = ref(false);

// Performance optimization: Cache network info
let cachedNetworkInfo: unknown = null;
let networkInfoCacheTime = 0;
const NETWORK_CACHE_DURATION = 30000; // 30 seconds

// Performance optimization: Debounce login attempts
let loginTimeout: NodeJS.Timeout | null = null;

// iOS-specific optimizations
const isIOS = ref(false);

onMounted(async () => {
  // Detect iOS for platform-specific optimizations
  isIOS.value =
    /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

  // Pre-warm network connection for faster login
  if (isIOS.value) {
    try {
      await updateApiEndpoint();
    } catch {
      // Network pre-warming failed silently
    }
  }
});

// Optimized network info getter with caching
const getCachedNetworkInfo = () => {
  const now = Date.now();
  if (cachedNetworkInfo && now - networkInfoCacheTime < NETWORK_CACHE_DURATION) {
    return cachedNetworkInfo;
  }

  try {
    cachedNetworkInfo = getNetworkInfo();
    networkInfoCacheTime = now;
    return cachedNetworkInfo;
  } catch {
    // Network info cache failed silently
    return null;
  }
};

const onLogin = () => {
  // Debounce login attempts to prevent multiple rapid calls
  if (loginTimeout) {
    clearTimeout(loginTimeout);
  }

  loginTimeout = setTimeout(
    () => {
      void performLogin();
    },
    isIOS.value ? 100 : 0,
  ); // Small delay on iOS for better UX
};

const performLogin = async () => {
  loading.value = true;

  // Mobile-specific platform detection
  const isMobile = !!(window as { Capacitor?: unknown }).Capacitor;

  try {
    // Optimized connectivity check with caching
    if (isMobile) {
      const networkInfo = getCachedNetworkInfo();

      if (!networkInfo) {
        throw new Error(
          'No working endpoints found. Please check your network connection and server status.',
        );
      }
    }

    // Optimized API call with timeout for iOS
    const loginPromise = api.post(
      '/users/login/',
      {
        email: email.value,
        password: password.value,
      },
      {
        timeout: isIOS.value ? 15000 : 10000, // Longer timeout on iOS
        headers: {
          'Content-Type': 'application/json',
          ...(isIOS.value && { 'X-Platform': 'iOS' }),
        },
      },
    );

    const response = await loginPromise;

    // Validate response structure
    if (!response.data.access || !response.data.refresh) {
      throw new Error('Invalid response: missing authentication tokens');
    }

    // Optimized storage operations - batch them for better performance
    const storageOperations = [];

    storageOperations.push(
      new Promise((resolve) => {
        try {
          localStorage.setItem('access_token', response.data.access);
          localStorage.setItem('refresh_token', response.data.refresh);
          resolve(true);
        } catch (error) {
          console.error('Token storage failed:', error);
          resolve(false);
        }
      }),
    );

    if (response.data.user) {
      storageOperations.push(
        new Promise((resolve) => {
          try {
            const rawUser = response.data.user;
            // Normalize role based on available profiles to avoid misclassification
            const hasDoctor = !!rawUser?.doctor_profile;
            const hasNurse = !!rawUser?.nurse_profile;
            const normalizedRole = hasDoctor ? 'doctor' : (hasNurse ? 'nurse' : (typeof rawUser.role === 'string' ? rawUser.role : 'patient'));
            const normalizedUser = { ...rawUser, role: normalizedRole };
            localStorage.setItem('user', JSON.stringify(normalizedUser));
            resolve(true);
          } catch (error) {
            console.error('User data storage failed:', error);
            resolve(false);
          }
        }),
      );
    }

    // Execute storage operations in parallel
    await Promise.all(storageOperations);

    // Optimized notification for iOS
    $q.notify({
      type: 'positive',
      message: 'Login successful!',
      position: 'top',
      timeout: isIOS.value ? 1500 : 2000, // Shorter on iOS for better UX
      actions: isIOS.value ? [] : [{ icon: 'close', color: 'white' }],
    });

    // Optimized navigation logic
    const user = response.data.user;

    // Show one-time verification banner only during login if backend indicates
    try {
      if (response.data.show_verification_banner === true) {
        $q.notify({
          type: 'positive',
          message: 'Your account has been verified!',
          position: 'top',
          timeout: 5000,
          actions: [{ icon: 'close', color: 'white' }],
        });
      }
    } catch (e) {
      console.error('Verification banner notify failed:', e);
    }

    // Use nextTick for better performance on iOS
    void nextTick();

    // Immediate navigation without setTimeout for better performance
    if (user && !user.is_verified) {
      await router.push('/verification');
      return;
    }

    // Role-based navigation
    if (!user || !user.role) {
      await router.push('/');
      return;
    }

    // Navigate based on user role
    switch (user.role) {
      case 'doctor':
        await router.push('/doctor-dashboard');
        break;
      case 'nurse':
        await router.push('/nurse-dashboard');
        break;
      case 'patient':
        await router.push('/patient-dashboard');
        break;
      default:
        await router.push('/');
    }
  } catch (error: unknown) {
    if (process.env.NODE_ENV === 'development') {
      if (isAxiosError(error)) {
        console.error('Login error:', {
          message: error.message,
          code: error.code,
          url: error.config?.url,
          baseURL: error.config?.baseURL,
          method: error.config?.method,
          status: error.response?.status,
          data: error.response?.data,
        });
      } else {
        console.error('Login error:', error);
      }
    }

    const isMobile = !!(window as { Capacitor?: unknown }).Capacitor;
    let errorMessage = 'Login failed. Please try again.';

    if (isAxiosError(error)) {
      if (error.response?.data) {
        // Handle specific backend error messages
        const data = error.response.data as Record<string, unknown>;
        const maybeError = data['error'];
        const maybeMessage = data['message'];
        const maybeDetail = data['detail'];
        if (typeof maybeError === 'string' && maybeError.trim().length > 0) {
          errorMessage = maybeError;
        } else if (typeof maybeMessage === 'string' && maybeMessage.trim().length > 0) {
          errorMessage = maybeMessage;
        } else if (typeof maybeDetail === 'string' && maybeDetail.trim().length > 0) {
          errorMessage = maybeDetail;
        }
      }

      // Handle specific HTTP status codes
      if (error.response?.status === 401) {
        errorMessage = 'Invalid email or password. Please check your credentials and try again.';
      } else if (error.response?.status === 403) {
        errorMessage = 'Access denied. Your account may be inactive or suspended.';
      } else if (error.response?.status === 404) {
        errorMessage = 'User not found. Please check your email address.';
      } else if (error.response?.status === 500) {
        errorMessage = 'Server error. Please try again later.';
      }

      // Optimized mobile-specific error handling
      if (isMobile) {
        if (error.code === 'NETWORK_ERROR' || error.message.includes('Network Error')) {
          errorMessage = 'Network connection failed. Please check your connection.';
        } else if (error.response?.status === 0) {
          errorMessage = 'Server unreachable. Please check your network.';
        }
      }
    } else if (error instanceof Error) {
      if (error.message.includes('ERR_CONNECTION_REFUSED')) {
        errorMessage = 'Cannot connect to server. Please check if the backend server is running.';
      } else {
        errorMessage = error.message;
      }
    }

    // Show optimized error notification with helpful actions
    const actions = [];
    
    // Add retry action for non-mobile
    if (!isIOS.value) {
      actions.push({
        label: 'Retry',
        color: 'white',
        handler: () => {
          onLogin();
        },
      });
    }
    
    // Add forgot password action for authentication errors
    if (errorMessage.includes('Invalid') || errorMessage.includes('password') || errorMessage.includes('credentials')) {
      actions.push({
        label: 'Forgot Password?',
        color: 'white',
        handler: () => {
          void router.push('/forgot-password');
        },
      });
    }

    $q.notify({
      type: 'negative',
      message: errorMessage,
      position: 'top',
      timeout: isIOS.value ? 4000 : 6000,
      actions: actions,
    });
  } finally {
    loading.value = false;
  }
};
</script>

<style>
body {
  background-color: white !important;
  background-size: cover !important;
  background-attachment: fixed !important;
  position: relative !important;
}

body::before {
  content: '';
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.3) 0%,
    rgba(248, 249, 250, 0.2) 50%,
    rgba(240, 242, 245, 0.1) 100%
  );
  z-index: -1;
  pointer-events: none;
}

.login-page {
  min-height: 100vh !important;
  background: transparent !important;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.login-container {
  width: 100%;
  max-width: 400px;
}

.login-card {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  box-shadow:
    0 20px 40px rgba(0, 0, 0, 0.15),
    0 8px 16px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  padding: 30px;
  position: relative;
  overflow: hidden;
}

.login-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #286660, #6ca299, #b8d2ce);
  border-radius: 16px 16px 0 0;
}

.login-header {
  text-align: center;
  margin-bottom: 30px;
}

.login-header h2 {
  margin: 0 0 10px 0;
  color: #333;
  font-size: 24px;
}

.login-header p {
  margin: 0;
  color: #666;
  font-size: 16px;
}

.login-form {
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: #333;
  font-weight: 500;
}

.form-group input {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 16px;
  box-sizing: border-box;
}

.form-group input:focus {
  outline: none;
  border-color: #1e7668;
  box-shadow: 0 0 0 2px rgba(30, 118, 104, 0.2);
}

.forgot-password {
  text-align: right;
  margin-bottom: 20px;
}

.forgot-btn {
  background: none;
  border: none;
  color: #1e7668;
  font-size: 14px;
  cursor: pointer;
  text-decoration: underline;
  padding: 0;
}

.forgot-btn:hover {
  color: #5a6fd8;
}

.form-group button {
  margin-top: 8px;
  background: none;
  border: none;
  color: #667eea;
  cursor: pointer;
  font-size: 14px;
}

.login-btn {
  width: 100%;
  padding: 12px;
  background: #1e7668;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.3s;
}

.login-btn:hover:not(:disabled) {
  background: #6ca299;
}

.login-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.login-footer {
  text-align: center;
  padding-top: 20px;
  border-top: 1px solid #eee;
}

.login-footer p {
  margin: 0;
  color: #666;
}

.link-btn {
  background: none;
  border: none;
  color: #1e7668;
  cursor: pointer;
  font-size: 14px;
  text-decoration: underline;
}

.link-btn:hover {
  color: #6ca299;
}

@media (max-width: 768px) {
  .login-page {
    padding: 8px;
    min-height: 100vh;
    /* Ensure content doesn't overlap with safe areas and navigation */
    padding-top: max(60px, calc(var(--safe-area-inset-top) + 40px));
    padding-bottom: max(8px, var(--safe-area-inset-bottom));
    padding-left: max(8px, var(--safe-area-inset-left));
    padding-right: max(8px, var(--safe-area-inset-right));
    /* Center the login form vertically */
    align-items: center;
    justify-content: center;
  }

  .login-container {
    max-width: 100%;
  }

  .login-card {
    padding: 16px;
    margin: 0;
    border-radius: 12px;
  }

  .login-header {
    margin-bottom: 20px;
  }

  .login-header h2 {
    font-size: 18px;
    margin-bottom: 6px;
  }

  .login-header p {
    font-size: 13px;
  }

  .form-group {
    margin-bottom: 12px;
  }

  .form-group label {
    margin-bottom: 4px;
    font-size: 14px;
  }

  .form-group input {
    padding: 10px;
    font-size: 14px;
    border-radius: 6px;
  }

  .login-btn {
    padding: 10px;
    font-size: 14px;
    border-radius: 6px;
  }

  .login-footer {
    padding-top: 16px;
  }

  .login-footer p {
    font-size: 13px;
  }

  .link-btn {
    font-size: 13px;
  }
}
</style>
