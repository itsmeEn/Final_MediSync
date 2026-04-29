import MsToastHost from 'src/components/MsToastHost.vue'
import { emitMsToast } from 'src/utils/toastBus'

export default {
  title: 'Patient/Toasts',
  component: MsToastHost
}

export const Toasts = {
  render: () => ({
    components: { MsToastHost },
    setup() {
      const show = (type, message) => {
        emitMsToast({ type, message, timeoutMs: 2500 })
      }

      return { show }
    },
    template: `
      <div style="padding: 24px; max-width: 640px;">
        <div style="display: flex; gap: 12px; flex-wrap: wrap;">
          <q-btn color="positive" unelevated label="Success" @click="show('positive','Appointment scheduled.')" />
          <q-btn color="warning" unelevated label="Warning" @click="show('warning','Double-check the selected time.')" />
          <q-btn color="negative" unelevated label="Error" @click="show('negative','Unable to book. Try again.')" />
          <q-btn color="info" unelevated label="Info" @click="show('info','New message received.')" />
        </div>
        <MsToastHost />
      </div>
    `
  })
}
