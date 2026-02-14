import { defineBoot } from '#q-app/wrappers';
import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { getPlatformInfo, getTimeoutConfig } from 'src/utils/asyncErrorHandler';

declare module 'vue' {
  interface ComponentCustomProperties {
    $axios: AxiosInstance;
    $api: AxiosInstance;
  }
}

// Helper to read cookies (for CSRF)
function getCookie(name: string): string | null {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop()!.split(';').shift() || null;
  return null;
}

// Initial endpoint resolution (synchronous for boot)
const resolveBaseURL = (): string => {
  const override = localStorage.getItem('API_BASE_URL');
  if (override) {
    return override.replace(/\/$/, '');
  }

  const platform = getPlatformInfo();

    if (platform.isCapacitor) {
    // For mobile devices, use primary endpoint initially
    const mobileEndpoints = [
      'http://192.168.1.3:8000/api', // Current machine IP
      'http://172.20.29.202:8000/api', // Previous network IP
      'http://10.0.2.2:8000/api', // Android emulator
      'http://192.168.55.101:8000/api', // Alternative development IP
      'http://192.168.1.100:8000/api', // Alternative common IP
      'http://localhost:8000/api', // Fallback
    ];

    return mobileEndpoints[0] || 'http://localhost:8000/api';
  }

  // For web browsers, use the current hostname and prefer port 8000
  const host = window.location?.hostname || 'localhost';
  const webEndpoint = `http://${host}:8000/api`;
  return webEndpoint;
};

// Connectivity test helper: probes a stable PUBLIC endpoint and treats 404 as NOT reachable
const testConnectivity = async (endpoint: string): Promise<boolean> => {
  try {
    // Probe a public UI config endpoint with GET; should respond 200
    const probeUrl = `${endpoint}/operations/ui-config/`;
    const testResponse = await axios.get(probeUrl, {
      // Use a short timeout to avoid hanging when port is closed
      timeout: 2500,
      validateStatus: () => true,
    });
    // Consider 2xx as reachable; 404 means wrong baseURL
    return (testResponse.status >= 200 && testResponse.status < 300);
  } catch {
    // Network errors (like ECONNREFUSED) will land here
    return false;
  }
};

// Mobile endpoints to probe when running under Capacitor
const MOBILE_ENDPOINTS = [
  'http://192.168.1.3:8000/api', // Current machine IP
  'http://172.20.29.202:8000/api', // Previous network IP
  'http://10.0.2.2:8000/api', // Android emulator
  'http://192.168.55.101:8000/api', // Alternative development IP
  'http://192.168.1.100:8000/api', // Alternative common IP
  'http://localhost:8000/api', // Fallback
];

// Web fallback testing: prefer :8000, optionally try :8001 for legacy setups
const resolveWebEndpointWithFallback = async (): Promise<string> => {
  const host = window.location?.hostname || 'localhost';
  const primary = `http://${host}:8000/api`;
  const enable8001 = localStorage.getItem('ENABLE_8001_FALLBACK') === 'true';
  if (!enable8001) {
    return primary;
  }
  const fallback = `http://${host}:8001/api`;

  // Test :8000 first
  const okPrimary = await testConnectivity(primary);
  if (okPrimary) {
    return primary;
  }
  // Then try :8001 as a secondary option (only if enabled)
  const okFallback = await testConnectivity(fallback);
  if (okFallback) {
    return fallback;
  }
  // As last resort, return primary to avoid undefined baseURL
  return primary;
};

// Test a list of mobile endpoints and pick the first reachable
const resolveMobileEndpointWithFallback = async (): Promise<string> => {
  for (const endpoint of MOBILE_ENDPOINTS) {
    const ok = await testConnectivity(endpoint);
    if (ok) {
      return endpoint;
    }
  }
  return MOBILE_ENDPOINTS[0] || 'http://localhost:8000/api';
};

// Unified async optimizer: works for both web and mobile
export const optimizeEndpoint = async (): Promise<void> => {
  const platform = getPlatformInfo();

  try {
    let workingEndpoint: string | null = null;

    if (platform.isCapacitor) {
      workingEndpoint = await resolveMobileEndpointWithFallback();
    } else {
      workingEndpoint = await resolveWebEndpointWithFallback();
    }

    if (workingEndpoint && workingEndpoint !== api.defaults.baseURL) {
      api.defaults.baseURL = workingEndpoint;
      localStorage.setItem('API_BASE_URL', workingEndpoint);
      console.log('API base URL optimized to:', workingEndpoint);
    }
  } catch (e) {
    // Fail silently to avoid blocking app startup
    console.warn('Endpoint optimization failed:', e);
  }
};

// Create axios instance with platform-specific configuration
const timeoutConfig = getTimeoutConfig();
const api = axios.create({
  baseURL: resolveBaseURL(),
  timeout: timeoutConfig.timeout,
});

// Request interceptor to add auth token and CSRF
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token');

    // Avoid attaching tokens to auth-related endpoints
    const url = config.url || '';
    const isAuthEndpoint =
      url.includes('/users/login/') ||
      url.includes('/users/register/') ||
      url.includes('/users/forgot-password/') ||
      url.includes('/users/reset-password') ||
      url.includes('/users/token/refresh/');

    // Public endpoints that do not require auth; suppress missing-token warnings
    const isPublicEndpoint =
      url.includes('/admin/hospitals/') ||
      url.includes('/admin/config/') ||
      url.includes('/admin/csrf-token/') ||
      url.includes('/operations/ui-config/');

    if (token && !isAuthEndpoint) {
      config.headers.Authorization = `Bearer ${token}`;
      console.log('Adding auth token to request:', config.url);
    } else if (!token && !isAuthEndpoint && !isPublicEndpoint) {
      // Only warn for endpoints that are expected to be authenticated
      console.warn('No access token found for request:', config.url);
    } else if (isAuthEndpoint) {
      // No token expected for auth endpoints like register/login
      // console.log('Skipping auth header for auth endpoint:', config.url);
    }

    // Add CSRF header for unsafe methods if cookie exists
    const unsafeMethod = ['POST', 'PUT', 'PATCH', 'DELETE'].includes((config.method || 'GET').toUpperCase());
    const csrf = getCookie('csrftoken');
    if (unsafeMethod && csrf) {
      (config.headers as Record<string, string>)['X-CSRFToken'] = csrf;
    }

    return config;
  },
  (error: Error) => {
    // Preserve original Axios error to keep response/details for downstream handlers
    return Promise.reject(error);
  },
);

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;

    // Do not attempt refresh on auth endpoints
    const url = originalRequest?.url || '';
    const isAuthEndpoint =
      url.includes('/users/login/') ||
      url.includes('/users/register/') ||
      url.includes('/users/forgot-password/') ||
      url.includes('/users/reset-password') ||
      url.includes('/users/token/refresh/');

    if (error.response?.status === 401 && originalRequest && !originalRequest._retry && !isAuthEndpoint) {
      console.log('401 Unauthorized detected, attempting token refresh...');
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          console.log('Attempting to refresh token...');
          const response = await axios.post(`${api.defaults.baseURL}/users/token/refresh/`, {
            refresh: refreshToken,
          });

          const { access } = response.data;
          localStorage.setItem('access_token', access);
          console.log('Token refreshed successfully');

          // Retry the original request; request interceptor will attach the new token
          return api(originalRequest);
        } else {
          console.warn('No refresh token found');
        }
      } catch (refreshError) {
        console.error('Token refresh failed:', refreshError);
        // Refresh token failed, redirect to login
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        window.location.href = '/login';
      }
      }

    const urlLower = (originalRequest?.url || '').toLowerCase();
    const methodUpper = (originalRequest?.method || 'GET').toUpperCase();
    const isNotificationsListRequest = methodUpper === 'GET' && (
      urlLower.includes('/operations/notifications/') ||
      urlLower.includes('/operations/messaging/notifications/')
    );

    if (isNotificationsListRequest && error.response?.status && [404, 500].includes(error.response.status)) {
      const useAlt = urlLower.includes('/operations/notifications/')
        ? '/operations/messaging/notifications/'
        : '/operations/notifications/';
      return api
        .get(useAlt, { params: (originalRequest?.params as Record<string, unknown>) || undefined })
        .catch(() => Promise.reject(error));
    }

    
    // Preserve original Axios error so callers can inspect status and response body
    return Promise.reject(error);
  },
);

export default defineBoot(async ({ app }) => {
  app.config.globalProperties.$axios = axios;
  app.config.globalProperties.$api = api;

  // Skip endpoint probe on the landing route to avoid noisy network errors
  const hash = window.location?.hash || '';
  const onLanding = hash.includes('/landing');
  const disableProbe = localStorage.getItem('DISABLE_ENDPOINT_PROBE') === 'true';

  if (!onLanding && !disableProbe) {
    await optimizeEndpoint();
  }
});

export { api };
