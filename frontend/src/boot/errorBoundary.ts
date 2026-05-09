import { defineBoot } from '#q-app/wrappers';
import { Notify } from 'quasar';
import type { AxiosError } from 'axios';
import { api } from './axios';
import { formatAxiosError, isOffline } from 'src/utils/apiResilience';

export default defineBoot(({ app }) => {
  const handleChunkError = (message: string) => {
    const isChunkError =
      message.includes('Failed to fetch dynamically imported module') ||
      message.includes('error loading dynamic import') ||
      message.includes('Loading chunk') ||
      message.includes('net::ERR_ABORTED') ||
      message.includes('404 (Not Found)');

    if (isChunkError) {
      // Check if we already tried to reload in the last 10 seconds to avoid loops
      const lastReload = sessionStorage.getItem('last_chunk_error_reload');
      const now = Date.now();
      if (!lastReload || now - parseInt(lastReload) > 10000) {
        sessionStorage.setItem('last_chunk_error_reload', String(now));
        window.location.reload();
        return true;
      }
    }
    return false;
  };

  app.config.errorHandler = (err, _instance, info) => {
    const message = err instanceof Error ? err.message : String(err);
    
    if (handleChunkError(message)) return;

    Notify.create({
      type: 'negative',
      message: isOffline() ? 'You are offline. Some actions may be queued.' : `Unexpected error: ${message}`,
      caption: info,
    });

    void api.post(
      '/operations/client-log/',
      {
        level: 'error',
        message,
        context: { info },
      },
      { meta: { queueOnOffline: true, retry: true, requestName: 'client_error' } },
    );
  };

  window.addEventListener('unhandledrejection', (event: PromiseRejectionEvent) => {
    const reason = event.reason;
    const maybeAxios = reason as { isAxiosError?: boolean } | null;
    const normalized = maybeAxios?.isAxiosError ? formatAxiosError(reason as AxiosError) : null;
    const message = normalized?.message || (reason instanceof Error ? reason.message : String(reason));

    if (handleChunkError(message)) return;

    Notify.create({
      type: 'negative',
      message: isOffline() ? 'You are offline. Some actions may be queued.' : message,
    });

    void api.post(
      '/operations/client-log/',
      {
        level: 'error',
        message,
        context: { normalized },
      },
      { meta: { queueOnOffline: true, retry: true, requestName: 'unhandled_rejection' } },
    );
  });

  // Global error listener for script/asset load failures
  window.addEventListener(
    'error',
    (e) => {
      const target = e.target as HTMLElement | null;
      if (target && (target.tagName === 'SCRIPT' || target.tagName === 'LINK')) {
        const url = (target as HTMLScriptElement).src || (target as HTMLLinkElement).href;
        if (url && (url.includes('.js') || url.includes('.css'))) {
          handleChunkError(`Asset failed to load: ${url}`);
        }
      }
    },
    true,
  );
});
