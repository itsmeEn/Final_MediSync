<template>
  <q-layout view="lHh Lpr lFf" :class="{ 'high-contrast': highContrast, 'large-text': largeText, 'ms-dark': darkMode }">
    <q-header class="bg-white text-teal-9">
      <q-toolbar>
        <q-avatar size="40px" class="q-mr-md">
          <img :src="logoUrl" alt="MediSync Logo" />
        </q-avatar>
        <q-space />
        <q-btn flat round color="grey-7" icon="settings_accessibility" aria-label="Accessibility options">
          <q-menu transition-show="scale" transition-hide="scale">
            <q-list style="min-width: 220px">
              <q-item-label header>Accessibility</q-item-label>
              <q-item clickable v-ripple @click="toggleHighContrast" aria-label="Toggle high contrast mode">
                <q-item-section avatar>
                  <q-icon :name="highContrast ? 'visibility_off' : 'visibility'" :color="highContrast ? 'teal' : 'grey'" />
                </q-item-section>
                <q-item-section>High Contrast</q-item-section>
                <q-item-section side>
                  <q-toggle v-model="highContrast" color="teal" />
                </q-item-section>
              </q-item>
              <q-item clickable v-ripple @click="toggleLargeText" aria-label="Toggle larger text">
                <q-item-section avatar>
                  <q-icon name="text_fields" :color="largeText ? 'teal' : 'grey'" />
                </q-item-section>
                <q-item-section>Larger Text</q-item-section>
                <q-item-section side>
                  <q-toggle v-model="largeText" color="teal" />
                </q-item-section>
              </q-item>
              <q-item clickable v-ripple @click="toggleDarkMode" aria-label="Toggle dark mode">
                <q-item-section avatar>
                  <q-icon :name="darkMode ? 'dark_mode' : 'light_mode'" :color="darkMode ? 'teal' : 'grey'" />
                </q-item-section>
                <q-item-section>Dark Mode</q-item-section>
                <q-item-section side>
                  <q-toggle v-model="darkMode" color="teal" />
                </q-item-section>
              </q-item>
            </q-list>
          </q-menu>
          <q-tooltip>Accessibility Options</q-tooltip>
        </q-btn>
      </q-toolbar>
    </q-header>

    <q-page-container>
      <q-page class="patient-bg q-pa-md pb-safe" :class="{ 'high-contrast': highContrast, 'large-text': largeText, 'ms-dark': darkMode }" role="main" aria-label="UI kit">
        <MsToastHost />
        <div class="max-w-4xl mx-auto">
          <q-card class="ms-card q-mb-md" flat bordered>
            <q-card-section class="q-pa-lg">
              <div class="text-h5 text-weight-bolder">Patient Portal UI Kit</div>
              <div class="text-body2 text-grey-7 q-mt-xs">Components, spacing tokens, and typography scale</div>
            </q-card-section>
          </q-card>

          <q-card class="ms-card q-mb-md" flat bordered>
            <q-card-section class="q-pa-lg">
              <div class="text-subtitle1 text-weight-bold q-mb-md">Tokens</div>
              <div class="token-grid">
                <div class="token">
                  <div class="token-label">Background</div>
                  <div class="token-swatch" :style="{ background: cssVar('--ms-bg') }" />
                  <div class="token-value">{{ cssVar('--ms-bg') }}</div>
                </div>
                <div class="token">
                  <div class="token-label">Surface</div>
                  <div class="token-swatch" :style="{ background: cssVar('--ms-card') }" />
                  <div class="token-value">{{ cssVar('--ms-card') }}</div>
                </div>
                <div class="token">
                  <div class="token-label">Text</div>
                  <div class="token-swatch" :style="{ background: cssVar('--ms-text') }" />
                  <div class="token-value">{{ cssVar('--ms-text') }}</div>
                </div>
                <div class="token">
                  <div class="token-label">Border</div>
                  <div class="token-swatch" :style="{ background: cssVar('--ms-border') }" />
                  <div class="token-value">{{ cssVar('--ms-border') }}</div>
                </div>
                <div class="token">
                  <div class="token-label">Focus</div>
                  <div class="token-swatch" :style="{ background: cssVar('--ms-focus') }" />
                  <div class="token-value">{{ cssVar('--ms-focus') }}</div>
                </div>
              </div>
            </q-card-section>
          </q-card>

          <q-card class="ms-card q-mb-md" flat bordered>
            <q-card-section class="q-pa-lg">
              <div class="text-subtitle1 text-weight-bold q-mb-md">Typography</div>
              <div class="type-sample">
                <div class="text-h5 text-weight-bolder">Heading / H5</div>
                <div class="text-subtitle1 text-weight-bold">Subtitle / Subtitle1</div>
                <div class="text-body1">Body / Body1</div>
                <div class="text-body2 text-grey-7">Muted / Body2</div>
              </div>
            </q-card-section>
          </q-card>

          <q-card class="ms-card q-mb-md" flat bordered>
            <q-card-section class="q-pa-lg">
              <div class="text-subtitle1 text-weight-bold q-mb-md">Components</div>

              <div class="section">
                <div class="text-subtitle2 text-weight-bold q-mb-sm">Buttons</div>
                <div class="row q-col-gutter-sm">
                  <div class="col-12 col-sm-6 col-md-4">
                    <q-btn unelevated color="teal-7" label="Primary" class="full-width touch-target ms-focusable" aria-label="Primary button" />
                  </div>
                  <div class="col-12 col-sm-6 col-md-4">
                    <q-btn outline color="teal-7" label="Secondary" class="full-width touch-target ms-focusable" aria-label="Secondary button" />
                  </div>
                  <div class="col-12 col-sm-6 col-md-4">
                    <q-btn flat color="teal-7" label="Tertiary" class="full-width touch-target ms-focusable" aria-label="Tertiary button" />
                  </div>
                </div>
              </div>

              <div class="section">
                <div class="text-subtitle2 text-weight-bold q-mb-sm">Chips</div>
                <div class="row q-gutter-sm">
                  <q-chip clickable class="ms-chip touch-target ms-focusable" color="teal" text-color="white" aria-label="Selected chip">Selected</q-chip>
                  <q-chip clickable class="ms-chip touch-target ms-focusable" color="grey-3" text-color="grey-8" aria-label="Unselected chip">Unselected</q-chip>
                </div>
              </div>

              <div class="section">
                <div class="text-subtitle2 text-weight-bold q-mb-sm">Banner</div>
                <q-banner rounded class="ms-banner" aria-label="Information banner">
                  Real-time validation and confirmations use toasts; dialogs are reserved for complex flows.
                </q-banner>
              </div>

              <div class="section">
                <div class="text-subtitle2 text-weight-bold q-mb-sm">Time Slots</div>
                <div class="time-slot-grid" role="radiogroup" aria-label="Time slot examples">
                  <q-btn flat class="time-slot-btn touch-target ms-focusable is-selected" aria-label="Selected time slot">9:00 AM</q-btn>
                  <q-btn flat class="time-slot-btn touch-target ms-focusable" aria-label="Time slot">9:30 AM</q-btn>
                  <q-btn flat class="time-slot-btn touch-target ms-focusable is-disabled" disable aria-label="Unavailable time slot">10:00 AM</q-btn>
                </div>
              </div>

              <div class="section">
                <div class="text-subtitle2 text-weight-bold q-mb-sm">Toasts</div>
                <div class="row q-col-gutter-sm">
                  <div class="col-12 col-sm-6 col-md-3">
                    <q-btn unelevated color="positive" label="Success" class="full-width touch-target ms-focusable" aria-label="Show success toast" @click="toast('positive', 'Saved successfully.')" />
                  </div>
                  <div class="col-12 col-sm-6 col-md-3">
                    <q-btn unelevated color="warning" label="Warning" class="full-width touch-target ms-focusable" aria-label="Show warning toast" @click="toast('warning', 'Check the highlighted fields.')" />
                  </div>
                  <div class="col-12 col-sm-6 col-md-3">
                    <q-btn unelevated color="negative" label="Error" class="full-width touch-target ms-focusable" aria-label="Show error toast" @click="toast('negative', 'Something went wrong.')" />
                  </div>
                  <div class="col-12 col-sm-6 col-md-3">
                    <q-btn unelevated color="info" label="Info" class="full-width touch-target ms-focusable" aria-label="Show info toast" @click="toast('info', 'New updates are available.')" />
                  </div>
                </div>
              </div>
            </q-card-section>
          </q-card>
        </div>
      </q-page>
    </q-page-container>

    <PatientBottomNav />
  </q-layout>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import logoUrl from 'src/assets/logo.png'
import PatientBottomNav from 'src/components/PatientBottomNav.vue'
import MsToastHost from 'src/components/MsToastHost.vue'
import { emitMsToast } from 'src/utils/toastBus'

const $q = useQuasar()
const highContrast = ref(false)
const largeText = ref(false)
const darkMode = ref(false)

const readBool = (key: string) => {
  const raw = localStorage.getItem(key)
  return raw === '1' || raw === 'true'
}

const persistBool = (key: string, value: boolean) => {
  localStorage.setItem(key, value ? '1' : '0')
}

const toggleHighContrast = () => { highContrast.value = !highContrast.value }
const toggleLargeText = () => { largeText.value = !largeText.value }
const toggleDarkMode = () => { darkMode.value = !darkMode.value }

const toast = (type: 'positive' | 'negative' | 'warning' | 'info', message: string) => {
  emitMsToast({ type, message, timeoutMs: 2500 })
}

const cssVar = (name: string) => getComputedStyle(document.documentElement).getPropertyValue(name).trim()

watch(highContrast, (val) => persistBool('ms_patient_high_contrast', val))
watch(largeText, (val) => persistBool('ms_patient_large_text', val))
watch(darkMode, (val) => {
  persistBool('ms_patient_dark_mode', val)
  $q.dark.set(val)
})

onMounted(() => {
  highContrast.value = readBool('ms_patient_high_contrast')
  largeText.value = readBool('ms_patient_large_text')
  darkMode.value = readBool('ms_patient_dark_mode')
  $q.dark.set(darkMode.value)
})
</script>

<style scoped>
.patient-bg {
  --ms-bg: #f8fafb;
  --ms-card: #ffffff;
  --ms-text: #0f172a;
  --ms-muted: #5b6472;
  --ms-border: rgba(15, 23, 42, 0.08);
  --ms-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
  --ms-shadow-hover: 0 16px 40px rgba(15, 23, 42, 0.10);
  --ms-focus: rgba(38, 166, 154, 0.55);
  background: var(--ms-bg);
  color: var(--ms-text);
  min-height: 100vh;
}

.ms-dark {
  --ms-bg: #0b1220;
  --ms-card: #111a2e;
  --ms-text: #e6edf6;
  --ms-muted: #aeb9c8;
  --ms-border: rgba(230, 237, 246, 0.12);
  --ms-shadow: 0 10px 28px rgba(0, 0, 0, 0.35);
  --ms-shadow-hover: 0 18px 44px rgba(0, 0, 0, 0.45);
  --ms-focus: rgba(255, 255, 255, 0.8);
}

.high-contrast {
  --ms-bg: #ffffff;
  --ms-card: #ffffff;
  --ms-text: #000000;
  --ms-muted: #000000;
  --ms-border: #000000;
  --ms-shadow: none;
  --ms-shadow-hover: none;
  --ms-focus: #000000;
}

.large-text {
  font-size: 18px;
}

.ms-card {
  background: var(--ms-card);
  border: 1px solid var(--ms-border);
  border-radius: 20px;
  box-shadow: var(--ms-shadow);
}

.section {
  padding-top: 10px;
}

.token-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
}

.token {
  border: 1px solid var(--ms-border);
  border-radius: 16px;
  padding: 12px;
  background: var(--ms-card);
}

.token-label {
  font-size: 12px;
  color: var(--ms-muted);
}

.token-swatch {
  width: 100%;
  height: 44px;
  border-radius: 12px;
  border: 1px solid var(--ms-border);
  margin-top: 10px;
}

.token-value {
  font-size: 12px;
  color: var(--ms-muted);
  margin-top: 10px;
  word-break: break-word;
}

.touch-target {
  min-height: 44px;
}

.ms-focusable:focus-visible {
  outline: 3px solid var(--ms-focus);
  outline-offset: 2px;
}

.ms-banner {
  background: rgba(38, 166, 154, 0.08);
  border: 1px solid rgba(38, 166, 154, 0.25);
  color: var(--ms-text);
}

.ms-chip {
  border-radius: 999px;
}

.time-slot-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.time-slot-btn {
  border-radius: 14px;
  border: 1px solid var(--ms-border);
  background: var(--ms-card);
  transition: transform 160ms ease, background-color 160ms ease, border-color 160ms ease;
}

.time-slot-btn.is-selected {
  border-color: rgba(38, 166, 154, 0.6);
  background: rgba(38, 166, 154, 0.12);
  transform: translateY(-1px);
}

.time-slot-btn.is-disabled {
  opacity: 0.55;
}

@media (max-width: 600px) {
  .token-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .time-slot-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (min-width: 601px) and (max-width: 1024px) {
  .token-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
