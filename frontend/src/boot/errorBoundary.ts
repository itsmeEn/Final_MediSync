import { defineBoot } from '#q-app/wrappers';
import { Notify } from 'quasar';
import type { AxiosError } from 'axios';
import { api } from './axios';
import { formatAxiosError, isOffline } from 'src/utils/apiResilience';

export default defineBoot(({ app }) => {
  app.config.errorHandler = (err, _instance, info) => {
    const message = err instanceof Error ? err.message : String(err);
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
});
