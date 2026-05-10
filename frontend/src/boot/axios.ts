import { defineBoot } from '#q-app/wrappers';
import axios, { AxiosError as AxiosErrorClass, type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { getPlatformInfo, getTimeoutConfig } from 'src/utils/asyncErrorHandler';
import { CircuitBreaker, OfflineQueue, formatAxiosError, jitteredBackoffMs, shouldRetry, sleep } from 'src/utils/apiResilience';

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
  const isHttpsPage = (typeof window !== 'undefined' && window.location?.protocol === 'https:');
  const prodDefault = 'https://medisync-backend-m3zd.onrender.com';
  const platform = getPlatformInfo();
  const isProdMobile = platform.isCapacitor && import.meta.env.PROD;

  const override = localStorage.getItem('API_BASE_URL');
  if (override) {
    const normalizedOverride = override.replace(/\/$/, '');
    if ((isHttpsPage || isProdMobile) && normalizedOverride.startsWith('http://')) {
      // Prevent mixed-content failures on HTTPS pages if a previous session saved an HTTP base URL.
      try { localStorage.removeItem('API_BASE_URL'); } catch { /* ignore */ }
    } else {
      return normalizedOverride;
    }
  }

  const envBase = import.meta.env.VITE_API_BASE_URL as string | undefined;
  if (envBase) {
    const normalizedEnvBase = envBase.replace(/\/$/, '');
    if ((isHttpsPage || isProdMobile) && normalizedEnvBase.startsWith('http://')) {
      return prodDefault;
    }
    return normalizedEnvBase;
  }

  if (platform.isCapacitor) {
    if (import.meta.env.PROD) {
      return prodDefault;
    }
    const host = window.location?.hostname || '';
    if (host && host !== 'localhost' && host !== '127.0.0.1' && host !== '0.0.0.0') {
      return `http://${host}:8000`;
    }

    const mobileEndpoints = [
      'http://10.0.2.2:8000',
      'http://localhost:8000',
      'http://192.168.1.3:8000',
      'http://172.20.29.202:8000',
      'http://192.168.55.101:8000',
      'http://192.168.1.100:8000',
    ];

    return mobileEndpoints[0] || 'http://localhost:8000';
  }

  // For web browsers, use the current hostname and prefer port 8000
  const host = window.location?.hostname || 'localhost';

  // On HTTPS pages, default to the deployed backend to avoid mixed-content blocks.
  if (isHttpsPage) {
    return prodDefault;
  }

  return `http://${host}:8000`;
};

// Connectivity test helper: probes a stable PUBLIC endpoint and treats 404 as NOT reachable
const testConnectivity = async (endpoint: string): Promise<boolean> => {
  try {
    const probeUrl = `${endpoint}/operations/ui-config/`;
    const testResponse = await axios.get(probeUrl, {
      // Use a short timeout to avoid hanging when port is closed
      timeout: 2500,
      validateStatus: () => true,
    });
    const status = testResponse.status;
    if (status >= 200 && status < 300) return true;
    if (status === 401 || status === 403) return true;
    return false;
  } catch {
    // Network errors (like ECONNREFUSED) will land here
    return false;
  }
};

// Mobile endpoints to probe when running under Capacitor
const MOBILE_ENDPOINTS = [
  'http://10.0.2.2:8000', // Android emulator
  'http://localhost:8000', // iOS simulator / local development
  'http://192.168.1.3:8000', // Common LAN IP
  'http://172.20.29.202:8000', // Common hotspot/LAN IP
  'http://192.168.55.101:8000', // Alternative development IP
  'http://192.168.1.100:8000', // Alternative common IP
];

// Web fallback testing: prefer :8000, optionally try :8001 for legacy setups
const resolveWebEndpointWithFallback = async (): Promise<string> => {
  const isHttpsPage = (typeof window !== 'undefined' && window.location?.protocol === 'https:');
  if (isHttpsPage) {
    const envBase = import.meta.env.VITE_API_BASE_URL as string | undefined;
    if (envBase) {
      const normalizedEnvBase = envBase.replace(/\/$/, '');
      if (normalizedEnvBase.startsWith('http://')) {
        return 'https://medisync-backend-m3zd.onrender.com';
      }
      return normalizedEnvBase;
    }
    return 'https://medisync-backend-m3zd.onrender.com';
  }

  const host = window.location?.hostname || 'localhost';
  const primary = `http://${host}:8000`;
  const enableProbe = import.meta.env.DEV || localStorage.getItem('ENABLE_WEB_ENDPOINT_PROBE') === 'true';
  if (!enableProbe) return primary;

  const candidates: string[] = [primary];
  if (import.meta.env.DEV) {
    candidates.push(`http://${host}:8010`);
  }
  const enable8001 = localStorage.getItem('ENABLE_8001_FALLBACK') === 'true';
  if (enable8001) {
    candidates.push(`http://${host}:8001`);
  }

  for (const endpoint of candidates) {
    const ok = await testConnectivity(endpoint);
    if (ok) return endpoint;
  }

  return primary;
};

// Test a list of mobile endpoints and pick the first reachable
const resolveMobileEndpointWithFallback = async (): Promise<string> => {
  if (import.meta.env.PROD) {
    const envBase = import.meta.env.VITE_API_BASE_URL as string | undefined;
    if (envBase) {
      const normalizedEnvBase = envBase.replace(/\/$/, '');
      if (!normalizedEnvBase.startsWith('http://')) return normalizedEnvBase;
    }
    return 'https://medisync-backend-m3zd.onrender.com';
  }
  const host = window.location?.hostname || '';
  const derived = host && host !== 'localhost' && host !== '127.0.0.1' && host !== '0.0.0.0'
    ? `http://${host}:8000`
    : null;

  if (derived) {
    const ok = await testConnectivity(derived);
    if (ok) return derived;
  }

  for (const endpoint of MOBILE_ENDPOINTS) {
    const ok = await testConnectivity(endpoint);
    if (ok) {
      return endpoint;
    }
  }
  return MOBILE_ENDPOINTS[0] || 'http://localhost:8000';
};

// Unified async optimizer: works for both web and mobile
export const optimizeEndpoint = async (): Promise<void> => {
  const platform = getPlatformInfo();

  try {
    if (platform.isCapacitor && import.meta.env.PROD) {
      const envBase = import.meta.env.VITE_API_BASE_URL as string | undefined;
      const normalizedEnvBase = typeof envBase === 'string' ? envBase.replace(/\/$/, '') : '';
      const target = normalizedEnvBase && !normalizedEnvBase.startsWith('http://')
        ? normalizedEnvBase
        : 'https://medisync-backend-m3zd.onrender.com';
      if (api.defaults.baseURL !== target) {
        api.defaults.baseURL = target;
        localStorage.setItem('API_BASE_URL', target);
      }
      return;
    }
    let workingEndpoint: string | null = null;

    if (platform.isCapacitor) {
      workingEndpoint = await resolveMobileEndpointWithFallback();
    } else {
      workingEndpoint = await resolveWebEndpointWithFallback();
    }

    const isHttpsPage = (typeof window !== 'undefined' && window.location?.protocol === 'https:');
    if (isHttpsPage && workingEndpoint?.startsWith('http://')) {
      workingEndpoint = null;
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

const circuitBreaker = new CircuitBreaker({ failureThreshold: 5, openMs: 15000 });
const offlineQueue = new OfflineQueue();

// Request interceptor to add auth token and CSRF
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const url = config.url || '';
    const isHealthCheck = url.includes('/health/') || url.includes('/healthz/') || config.meta?.isHealthCheck === true;
    config.meta = { ...(config.meta || {}), isHealthCheck };

    if (isHealthCheck) {
      config.timeout = 5000;
    } else {
      config.timeout = timeoutConfig.timeout;
      try {
        circuitBreaker.beforeRequest();
      } catch (e) {
        const err = e as Error & { code?: string };
        if (err.code === 'CIRCUIT_OPEN') {
          const ax = new AxiosErrorClass('Backend temporarily unavailable', 'CIRCUIT_OPEN', config);
          (ax as unknown as { medisync?: unknown }).medisync = { type: 'circuit_open', message: ax.message, retryable: true };
          throw ax;
        }
        throw e;
      }
    }

    (config as unknown as { _startAt?: number })._startAt = performance.now();
    const requestId = (typeof crypto !== 'undefined' && 'randomUUID' in crypto) ? crypto.randomUUID() : `${Date.now()}_${Math.random().toString(16).slice(2)}`;
    (config.headers as Record<string, string>)['X-Request-ID'] = requestId;

    const token = localStorage.getItem('access_token');

    // Avoid attaching tokens to auth-related endpoints
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
      url.includes('/operations/ui-config/') ||
      url.includes('/users/specializations/');

    // Important: do NOT attach Authorization header to public endpoints.
    // If we attach an expired/invalid token, DRF can return 401 even when the endpoint is AllowAny.
    if (token && !isAuthEndpoint && !isPublicEndpoint) {
      config.headers.Authorization = `Bearer ${token}`;
    } else if (!token && !isAuthEndpoint && !isPublicEndpoint) {
      // Only warn for endpoints that are expected to be authenticated
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

let refreshInFlight: Promise<{ access?: string; refresh?: string } | null> | null = null;

const refreshAuthTokens = async (): Promise<{ access?: string; refresh?: string } | null> => {
  const refreshToken = localStorage.getItem('refresh_token');
  if (!refreshToken) return null;

  const response = await axios.post(`${api.defaults.baseURL}/users/token/refresh/`, {
    refresh: refreshToken,
  });

  const access = response.data?.access;
  const refresh = response.data?.refresh;

  if (typeof access === 'string' && access) {
    localStorage.setItem('access_token', access);
  }
  if (typeof refresh === 'string' && refresh) {
    localStorage.setItem('refresh_token', refresh);
  }

  return { access, refresh };
};

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => {
    const startedAt = (response.config as unknown as { _startAt?: number })._startAt;
    if (typeof startedAt === 'number') {
      const ms = Math.round(performance.now() - startedAt);
      const url = response.config.url || '';
      const isCritical = url.includes('/operations/queue/') || url.includes('/operations/appointments/') || url.includes('/users/login/');
      if ((isCritical && ms > 200) || ms > 2000) {
        console.warn('Slow API response', { url, ms, status: response.status });
      }
    }
    circuitBreaker.recordSuccess();
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
      originalRequest._retry = true;

      try {
        if (!refreshInFlight) {
          refreshInFlight = refreshAuthTokens().finally(() => {
            refreshInFlight = null;
          });
        }
        const tokens = await refreshInFlight;
        if (tokens?.access) {
          return api(originalRequest);
        }
      } catch {
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

    if (originalRequest) {
      const queued = offlineQueue.enqueue(originalRequest);
      if (queued) {
        const ax = new AxiosErrorClass('Request queued (offline)', 'OFFLINE_QUEUED', originalRequest);
        (ax as unknown as { medisync?: unknown }).medisync = { type: 'network', message: ax.message, retryable: true };
        return Promise.reject(ax);
      }
    }

    if (originalRequest) {
      const retryCfg = timeoutConfig.retryConfig;
      const current = (originalRequest as unknown as { _retryCount?: number })._retryCount || 0;
      const maxRetries = retryCfg?.maxRetries ?? 0;
      if (current < maxRetries && shouldRetry(error, originalRequest)) {
        (originalRequest as unknown as { _retryCount?: number })._retryCount = current + 1;
        const delay = jitteredBackoffMs(current + 1, retryCfg?.baseDelay ?? 800, retryCfg?.maxDelay ?? 10000);
        await sleep(delay);
        return api(originalRequest);
      }
    }

    const normalized = formatAxiosError(error);
    (error as unknown as { medisync?: unknown }).medisync = normalized;
    const status = error.response?.status;
    const code = typeof error.code === 'string' ? error.code : '';
    const failureIndicatesOutage =
      !error.response || code === 'ECONNABORTED' || status === 429 || (status != null && status >= 500);
    if (failureIndicatesOutage) {
      circuitBreaker.recordFailure();
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
  circuitBreaker.recordSuccess();

  window.addEventListener('online', () => {
    void offlineQueue.flush(api);
  });
});

export { api };
