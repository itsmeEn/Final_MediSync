import type { AxiosError, AxiosInstance, AxiosRequestConfig, InternalAxiosRequestConfig, Method } from 'axios';

export type ApiErrorType =
  | 'network'
  | 'timeout'
  | 'auth'
  | 'validation'
  | 'server'
  | 'circuit_open'
  | 'unknown';

export type ApiErrorPayload = {
  type: ApiErrorType;
  message: string;
  status?: number;
  code?: string;
  retryable: boolean;
  requestId?: string;
  url?: string;
  method?: string;
  details?: unknown;
};

declare module 'axios' {
  export interface AxiosRequestConfig {
    meta?: {
      retry?: boolean;
      queueOnOffline?: boolean;
      isHealthCheck?: boolean;
      requestName?: string;
    };
  }

  export interface InternalAxiosRequestConfig {
    meta?: {
      retry?: boolean;
      queueOnOffline?: boolean;
      isHealthCheck?: boolean;
      requestName?: string;
    };
  }
}

export const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

export const jitteredBackoffMs = (attempt: number, baseMs: number, maxMs: number) => {
  const exp = baseMs * Math.pow(2, Math.max(0, attempt - 1));
  const capped = Math.min(exp, maxMs);
  const jitter = Math.floor(Math.random() * Math.min(250, capped * 0.1));
  return capped + jitter;
};

export const isOffline = () => typeof navigator !== 'undefined' && navigator.onLine === false;

export const formatAxiosError = (error: AxiosError): ApiErrorPayload => {
  const status = error.response?.status;
  const url = error.config?.url;
  const method = (error.config?.method || '').toUpperCase();
  const requestId =
    (error.response?.headers?.['x-request-id'] as string | undefined) ||
    (error.response?.headers?.['X-Request-ID'] as string | undefined);

  const data = error.response?.data;
  const detail = (data as { detail?: unknown; message?: unknown } | undefined)?.detail;
  const messageField = (data as { message?: unknown } | undefined)?.message;

  const normalizedMessage =
    typeof detail === 'string'
      ? detail
      : typeof messageField === 'string'
        ? messageField
        : error.message || 'Request failed';

  const code = typeof error.code === 'string' ? error.code : undefined;
  const statusPart = status != null ? { status } : {};
  const codePart = code != null ? { code } : {};
  const requestIdPart = requestId != null ? { requestId } : {};
  const urlPart = url != null ? { url } : {};
  const methodPart = method ? { method } : {};
  const detailsPart = data != null ? { details: data } : {};

  if (code === 'ECONNABORTED') {
    return { type: 'timeout', message: 'Request timed out', retryable: true, ...statusPart, ...codePart, ...requestIdPart, ...urlPart, ...methodPart, ...detailsPart };
  }

  if (!error.response) {
    return {
      type: isOffline() ? 'network' : 'network',
      message: isOffline() ? 'You appear to be offline' : 'Network connection failed',
      retryable: true,
      ...statusPart,
      ...codePart,
      ...requestIdPart,
      ...urlPart,
      ...methodPart,
    };
  }

  if (status === 400) return { type: 'validation', message: normalizedMessage, retryable: false, ...statusPart, ...codePart, ...requestIdPart, ...urlPart, ...methodPart, ...detailsPart };
  if (status === 401) return { type: 'auth', message: 'Authentication required', retryable: true, ...statusPart, ...codePart, ...requestIdPart, ...urlPart, ...methodPart, ...detailsPart };
  if (status === 403) return { type: 'auth', message: 'Access denied', retryable: false, ...statusPart, ...codePart, ...requestIdPart, ...urlPart, ...methodPart, ...detailsPart };
  if (status === 404) return { type: 'server', message: 'Resource not found', retryable: false, ...statusPart, ...codePart, ...requestIdPart, ...urlPart, ...methodPart, ...detailsPart };
  if (status === 408 || status === 504) return { type: 'timeout', message: 'Request timed out', retryable: true, ...statusPart, ...codePart, ...requestIdPart, ...urlPart, ...methodPart, ...detailsPart };
  if (status === 429) return { type: 'server', message: 'Too many requests. Please try again later.', retryable: true, ...statusPart, ...codePart, ...requestIdPart, ...urlPart, ...methodPart, ...detailsPart };
  if (status != null && status >= 500) return { type: 'server', message: 'Server error. Please try again later.', retryable: true, ...statusPart, ...codePart, ...requestIdPart, ...urlPart, ...methodPart, ...detailsPart };

  return { type: 'unknown', message: normalizedMessage, retryable: false, ...statusPart, ...codePart, ...requestIdPart, ...urlPart, ...methodPart, ...detailsPart };
};

export const shouldRetry = (error: AxiosError, config: InternalAxiosRequestConfig) => {
  if (config.meta?.isHealthCheck) {
    return true;
  }

  const method = (config.method || 'GET').toUpperCase();
  const isIdempotent = ['GET', 'HEAD', 'OPTIONS'].includes(method);
  if (!isIdempotent && !config.meta?.retry) {
    return false;
  }

  const status = error.response?.status;
  if (!status) {
    return true;
  }
  if (status === 429) return true;
  if (status >= 500) return true;
  if (status === 408 || status === 504) return true;
  return false;
};

type CircuitState = 'closed' | 'open' | 'half_open';

export class CircuitBreaker {
  private state: CircuitState = 'closed';
  private failures = 0;
  private openedAt = 0;
  private halfOpenAllowed = true;

  constructor(
    private readonly options: {
      failureThreshold: number;
      openMs: number;
    },
  ) {}

  beforeRequest(): void {
    if (this.state === 'closed') return;

    const now = Date.now();
    if (this.state === 'open') {
      if (now - this.openedAt >= this.options.openMs) {
        this.state = 'half_open';
        this.halfOpenAllowed = true;
      } else {
        const err = new Error('Circuit breaker is open') as Error & { code?: string };
        err.code = 'CIRCUIT_OPEN';
        throw err;
      }
    }

    if (this.state === 'half_open') {
      if (!this.halfOpenAllowed) {
        const err = new Error('Circuit breaker is half-open') as Error & { code?: string };
        err.code = 'CIRCUIT_OPEN';
        throw err;
      }
      this.halfOpenAllowed = false;
    }
  }

  recordSuccess(): void {
    this.failures = 0;
    this.state = 'closed';
    this.halfOpenAllowed = true;
  }

  recordFailure(): void {
    this.failures += 1;
    if (this.failures >= this.options.failureThreshold) {
      this.state = 'open';
      this.openedAt = Date.now();
      this.halfOpenAllowed = true;
    }
  }
}

type OfflineQueueItem = {
  id: string;
  createdAt: number;
  baseURL?: string;
  url?: string;
  method?: string;
  params?: unknown;
  data?: unknown;
  headers?: Record<string, string>;
};

export class OfflineQueue {
  private readonly storageKey = 'MEDISYNC_OFFLINE_QUEUE';
  private readonly maxItems = 200;

  enqueue(config: InternalAxiosRequestConfig): OfflineQueueItem | null {
    const method = (config.method || 'GET').toUpperCase();
    if (!['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) return null;
    if (!config.meta?.queueOnOffline) return null;
    if (!isOffline()) return null;

    const item: OfflineQueueItem = {
      id: `${Date.now()}_${Math.random().toString(16).slice(2)}`,
      createdAt: Date.now(),
      method,
    };
    if (config.baseURL != null) item.baseURL = config.baseURL;
    if (config.url != null) item.url = config.url;
    if (config.params != null) item.params = config.params;
    if (config.data != null) item.data = config.data;
    const safe = this.safeHeaders(config);
    if (safe) item.headers = safe;

    const items = this.read();
    items.unshift(item);
    const capped = items.slice(0, this.maxItems);
    this.write(capped);
    return item;
  }

  async flush(api: AxiosInstance): Promise<number> {
    if (isOffline()) return 0;
    const items = this.read();
    if (items.length === 0) return 0;

    const remaining: OfflineQueueItem[] = [];
    let sent = 0;
    for (const item of items.reverse()) {
      try {
        const req: AxiosRequestConfig & { meta?: InternalAxiosRequestConfig['meta'] } = {
          method: item.method as Method,
          meta: { retry: true },
        };
        if (item.baseURL != null) req.baseURL = item.baseURL;
        if (item.url != null) req.url = item.url;
        if (item.params != null) req.params = item.params;
        if (item.data != null) req.data = item.data;
        if (item.headers != null) req.headers = item.headers;
        await api.request(req);
        sent += 1;
      } catch {
        remaining.push(item);
      }
    }

    this.write(remaining.reverse());
    return sent;
  }

  private read(): OfflineQueueItem[] {
    try {
      const raw = localStorage.getItem(this.storageKey);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) return [];
      return parsed as OfflineQueueItem[];
    } catch {
      return [];
    }
  }

  private write(items: OfflineQueueItem[]) {
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(items));
    } catch {
      return;
    }
  }

  private safeHeaders(config: InternalAxiosRequestConfig): Record<string, string> | undefined {
    const h: Record<string, string> = {};
    const headers = (config.headers || {}) as Record<string, unknown>;
    for (const [k, v] of Object.entries(headers)) {
      const key = k.toLowerCase();
      if (key === 'authorization') continue;
      if (typeof v === 'string') h[k] = v;
    }
    return Object.keys(h).length ? h : undefined;
  }
}
