/**
 * Comprehensive Async Error Handling Utility
 * Provides standardized error handling patterns for network operations
 * and cross-platform compatibility
 */

import { Notify } from 'quasar';
import type { AxiosError } from 'axios';

// Error types for better type safety
export interface NetworkError {
  type: 'network' | 'timeout' | 'auth' | 'validation' | 'server' | 'unknown';
  message: string;
  code?: string | number | undefined;
  details?: Record<string, unknown>;
  retryable: boolean;
}

export interface AsyncOperationResult<T = unknown> {
  success: boolean;
  data?: T;
  error?: NetworkError;
  retryCount?: number;
}

// Platform detection utility
export const getPlatformInfo = () => {
  const isCapacitor = !!(window as { Capacitor?: unknown }).Capacitor;
  const isMobile = /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
    navigator.userAgent,
  );

  return {
    isCapacitor,
    isMobile,
    isWeb: !isCapacitor,
    platform: isCapacitor ? 'mobile' : 'web',
    userAgent: navigator.userAgent,
    online: navigator.onLine,
  };
};

// Enhanced error classification
export const classifyError = (error: unknown): NetworkError => {
  // Handle Axios errors
  if (error && typeof error === 'object' && 'response' in error) {
    const axiosError = error as AxiosError;
    const status = axiosError.response?.status;
    const data = axiosError.response?.data as Record<string, unknown>;

    switch (status) {
      case 400:
        return {
          type: 'validation',
          message: (data?.detail as string) || (data?.message as string) || 'Invalid request data',
          code: status,
          details: data,
          retryable: false,
        };
      case 401:
        return {
          type: 'auth',
          message: 'Authentication required',
          code: status,
          retryable: true,
        };
      case 403:
        return {
          type: 'auth',
          message: 'Access denied',
          code: status,
          retryable: false,
        };
      case 404:
        return {
          type: 'server',
          message: 'Resource not found',
          code: status,
          retryable: false,
        };
      case 408:
      case 504:
        return {
          type: 'timeout',
          message: 'Request timeout',
          code: status,
          retryable: true,
        };
      case 429:
        return {
          type: 'server',
          message: 'Too many requests. Please try again later.',
          code: status,
          retryable: true,
        };
      case 500:
      case 502:
      case 503:
        return {
          type: 'server',
          message: 'Server error. Please try again later.',
          code: status,
          retryable: true,
        };
      default:
        return {
          type: 'server',
          message: (data?.detail as string) || (data?.message as string) || 'Server error',
          code: status || undefined,
          retryable: status ? status >= 500 : false,
        };
    }
  }

  // Handle network errors
  if (error && typeof error === 'object' && 'message' in error) {
    const message = (error as { message: string }).message.toLowerCase();

    if (message.includes('network error') || message.includes('failed to fetch')) {
      return {
        type: 'network',
        message: 'Network connection failed. Please check your internet connection.',
        retryable: true,
      };
    }

    if (message.includes('timeout')) {
      return {
        type: 'timeout',
        message: 'Request timed out. Please try again.',
        retryable: true,
      };
    }
  }

  // Default unknown error
  return {
    type: 'unknown',
    message: error instanceof Error ? error.message : 'An unexpected error occurred',
    retryable: false,
  };
};

// Retry configuration
export interface RetryConfig {
  maxRetries: number;
  baseDelay: number;
  maxDelay: number;
  backoffMultiplier: number;
  retryCondition?: (error: NetworkError) => boolean;
}

const defaultRetryConfig: RetryConfig = {
  maxRetries: 3,
  baseDelay: 1000,
  maxDelay: 10000,
  backoffMultiplier: 2,
  retryCondition: (error) => error.retryable,
};

// Exponential backoff delay calculation
const calculateDelay = (attempt: number, config: RetryConfig): number => {
  const delay = config.baseDelay * Math.pow(config.backoffMultiplier, attempt - 1);
  return Math.min(delay, config.maxDelay);
};

// Sleep utility for delays
const sleep = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms));

// Main async operation wrapper with retry logic
export async function executeWithRetry<T>(
  operation: () => Promise<T>,
  config: Partial<RetryConfig> = {},
): Promise<AsyncOperationResult<T>> {
  const finalConfig = { ...defaultRetryConfig, ...config };
  let lastError: NetworkError | undefined;

  for (let attempt = 1; attempt <= finalConfig.maxRetries + 1; attempt++) {
    try {
      const data = await operation();
      return {
        success: true,
        data,
        retryCount: attempt - 1,
      };
    } catch (error) {
      lastError = classifyError(error);

      // Don't retry if it's the last attempt or error is not retryable
      if (attempt > finalConfig.maxRetries || !finalConfig.retryCondition?.(lastError)) {
        break;
      }

      // Calculate delay and wait before retry
      const delay = calculateDelay(attempt, finalConfig);
      console.warn(`Attempt ${attempt} failed, retrying in ${delay}ms:`, lastError.message);
      await sleep(delay);
    }
  }

  return {
    success: false,
    error: lastError || {
      type: 'unknown',
      message: 'Operation failed after retries',
      retryable: false,
    },
    retryCount: finalConfig.maxRetries,
  };
}

// Notification helper for consistent error display
export const showErrorNotification = (error: NetworkError, context?: string) => {
  const platform = getPlatformInfo();
  const prefix = context ? `${context}: ` : '';

  const notifyOptions: Parameters<typeof Notify.create>[0] = {
    type: 'negative',
    message: `${prefix}${error.message}`,
    position: platform.isMobile ? 'top' : 'top-right',
    timeout: error.type === 'validation' ? 6000 : 4000,
  };

  if (error.retryable) {
    notifyOptions.actions = [
      {
        label: 'Retry',
        color: 'white',
        handler: () => {
          // This will be handled by the calling component
        },
      },
    ];
  }

  Notify.create(notifyOptions);
};

// Success notification helper
export const showSuccessNotification = (message: string, context?: string) => {
  const platform = getPlatformInfo();
  const prefix = context ? `${context}: ` : '';

  Notify.create({
    type: 'positive',
    message: `${prefix}${message}`,
    position: platform.isMobile ? 'top' : 'top-right',
    timeout: 3000,
  });
};

// Async operation wrapper for Vue components
export const useAsyncOperation = <T>(
  operation: () => Promise<T>,
  options: {
    loadingRef?: { value: boolean };
    successMessage?: string;
    errorContext?: string;
    retryConfig?: Partial<RetryConfig>;
    onSuccess?: (data: T) => void;
    onError?: (error: NetworkError) => void;
  } = {},
) => {
  return async (): Promise<AsyncOperationResult<T>> => {
    if (options.loadingRef) {
      options.loadingRef.value = true;
    }

    try {
      const result = await executeWithRetry(operation, options.retryConfig);

      if (result.success && result.data !== undefined) {
        if (options.successMessage) {
          showSuccessNotification(options.successMessage, options.errorContext);
        }
        options.onSuccess?.(result.data);
      } else if (result.error) {
        showErrorNotification(result.error, options.errorContext);
        options.onError?.(result.error);
      }

      return result;
    } finally {
      if (options.loadingRef) {
        options.loadingRef.value = false;
      }
    }
  };
};

// Platform-specific timeout configurations
export const getTimeoutConfig = () => {
  const platform = getPlatformInfo();

  if (platform.isCapacitor) {
    return {
      timeout: 30000,
      retryConfig: {
        maxRetries: 3,
        baseDelay: 1000,
        maxDelay: 15000,
      },
    };
  }

  return {
    timeout: 30000,
    retryConfig: {
      maxRetries: 3,
      baseDelay: 800,
      maxDelay: 10000,
    },
  };
};

// Thread-safe operation queue for mobile
class OperationQueue {
  private queue: Array<() => Promise<unknown>> = [];
  private processing = false;

  async add<T>(operation: () => Promise<T>): Promise<T> {
    return new Promise((resolve, reject) => {
      this.queue.push(async () => {
        try {
          const result = await operation();
          resolve(result);
        } catch (error) {
          reject(error instanceof Error ? error : new Error(String(error)));
        }
      });

      void this.process();
    });
  }

  private async process(): Promise<void> {
    if (this.processing || this.queue.length === 0) {
      return;
    }

    this.processing = true;

    while (this.queue.length > 0) {
      const operation = this.queue.shift();
      if (operation) {
        try {
          await operation();
        } catch (error) {
          console.error('Operation queue error:', error);
        }
      }
    }

    this.processing = false;
  }
}

// Global operation queue for thread safety
export const operationQueue = new OperationQueue();

// Mobile-specific async wrapper
export const executeMobileSafe = <T>(operation: () => Promise<T>): Promise<T> => {
  const platform = getPlatformInfo();

  if (platform.isCapacitor) {
    // Use operation queue for thread safety on mobile
    return operationQueue.add(operation);
  }

  // Direct execution on web
  return operation();
};
