<template>
  <q-dialog v-model="open" persistent>
    <q-card style="width: 880px; max-width: 96vw;">
      <q-card-section class="row items-center q-pb-none">
        <div class="text-h6">Customize Card Colors</div>
        <q-space />
        <q-btn icon="close" flat round dense @click="open = false" />
      </q-card-section>

      <q-card-section class="q-pt-sm">
        <q-tabs v-model="mode" dense>
          <q-tab name="light" label="Light Mode" />
          <q-tab name="dark" label="Dark Mode" />
        </q-tabs>

        <q-separator class="q-mt-sm q-mb-md" />

        <div class="config-grid">
          <div
            v-for="c in cards"
            :key="c.id"
            class="config-row"
          >
            <div class="config-title">
              <div class="text-weight-medium">{{ c.label }}</div>
              <div class="text-caption text-grey-7">{{ c.id }}</div>
            </div>

            <div class="config-controls">
              <q-select
                dense
                outlined
                :options="paletteOptions"
                option-label="label"
                option-value="value"
                emit-value
                map-options
                label="Palette"
                :model-value="paletteSelection[c.id] ?? 'default'"
                @update:model-value="(v) => onSelectPalette(c.id, String(v))"
                style="min-width: 180px;"
              />

              <q-input
                dense
                outlined
                label="Custom Color"
                :model-value="customValue(c.id)"
                @update:model-value="(v) => onCustomInput(c.id, String(v))"
                :error="Boolean(errors[c.id])"
                :error-message="errors[c.id] || ''"
                placeholder="#RRGGBB or rgb(r,g,b)"
                style="min-width: 220px;"
              />

              <q-btn
                dense
                outline
                color="primary"
                label="Reset"
                @click="resetCard(c.id)"
              />
            </div>

            <div class="config-preview">
              <div
                class="preview-swatch"
                :style="previewStyle(c.id)"
              >
                <div class="preview-title">Aa</div>
                <div class="preview-caption">Text</div>
              </div>
              <div class="text-caption text-grey-7 q-mt-xs">
                Contrast: {{ previewRatio(c.id) }}
              </div>
            </div>
          </div>
        </div>
      </q-card-section>

      <q-separator />

      <q-card-actions align="between">
        <q-btn flat color="negative" label="Reset All" @click="resetAll" />
        <div class="row items-center q-gutter-sm">
          <q-btn outline color="primary" label="Export" @click="exportConfig" />
          <q-btn outline color="primary" label="Import" @click="importConfig" />
          <q-btn color="primary" label="Done" @click="open = false" />
        </div>
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useCardThemeStore, type ThemeMode } from 'src/stores/cardTheme'
import { parseColorToRgb } from 'src/utils/colorTheme'

type CardItem = { id: string; label: string }

const props = defineProps<{
  modelValue: boolean
  cards: CardItem[]
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
}>()

const $q = useQuasar()
const store = useCardThemeStore()

const open = computed({
  get: () => props.modelValue,
  set: (v: boolean) => emit('update:modelValue', v),
})

const mode = ref<ThemeMode>('light')

const paletteOptions = computed(() => store.palette)

const errors = ref<Record<string, string>>({})
const paletteSelection = ref<Record<string, string>>({})

watch(
  () => [props.modelValue, props.cards],
  () => {
    const next: Record<string, string> = {}
    props.cards.forEach((c) => {
      next[c.id] = 'default'
    })
    paletteSelection.value = { ...next, ...paletteSelection.value }
    errors.value = {}
  },
  { immediate: true }
)

const currentStoredValue = (cardId: string) => {
  const cfg = store.state.cards[cardId] || {}
  return mode.value === 'light' ? (cfg.lightBg || '') : (cfg.darkBg || '')
}

const customValue = (cardId: string) => currentStoredValue(cardId)

const onSelectPalette = (cardId: string, paletteValue: string) => {
  paletteSelection.value = { ...paletteSelection.value, [cardId]: paletteValue }
  errors.value = { ...errors.value, [cardId]: '' }
  store.applyPalette(cardId, paletteValue)
}

const onCustomInput = (cardId: string, value: string) => {
  const rgb = parseColorToRgb(value)
  if (!rgb) {
    errors.value = { ...errors.value, [cardId]: 'Invalid color. Use #RRGGBB or rgb(r,g,b).' }
    return
  }
  errors.value = { ...errors.value, [cardId]: '' }
  store.setCardBg(cardId, mode.value, value.trim())
}

const resetCard = (cardId: string) => {
  errors.value = { ...errors.value, [cardId]: '' }
  paletteSelection.value = { ...paletteSelection.value, [cardId]: 'default' }
  store.resetCard(cardId)
}

const resetAll = () => {
  errors.value = {}
  store.resetAll()
}

const preview = (cardId: string) => store.resolveVars(cardId, mode.value === 'dark')

const previewStyle = (cardId: string) => {
  const v = preview(cardId)
  return {
    background: v.bg,
    color: v.fg,
    border: `1px solid ${v.border}`,
  }
}

const previewRatio = (cardId: string) => {
  const v = preview(cardId)
  return v.ratio.toFixed(2)
}

const exportConfig = () => {
  const json = store.exportJson()
  void navigator.clipboard?.writeText(json)
  $q.notify({ type: 'positive', message: 'Theme JSON copied to clipboard', position: 'top' })
}

const importConfig = () => {
  $q.dialog({
    title: 'Import Theme JSON',
    message: 'Paste a previously exported theme JSON.',
    prompt: {
      model: '',
      type: 'textarea',
      isValid: (v: string) => v.trim().length > 0,
    },
    cancel: true,
    ok: { label: 'Import', color: 'primary' },
  }).onOk((raw: string) => {
    const ok = store.importJson(raw)
    if (ok) $q.notify({ type: 'positive', message: 'Theme imported', position: 'top' })
    else $q.notify({ type: 'negative', message: 'Invalid theme JSON', position: 'top' })
  })
}
</script>

<style scoped>
.config-grid {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.config-row {
  display: grid;
  grid-template-columns: 1.3fr 2fr 0.7fr;
  gap: 14px;
  align-items: center;
}
.config-title {
  min-width: 0;
}
.config-controls {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}
.config-preview {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}
.preview-swatch {
  width: 120px;
  height: 64px;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  transition: background-color 250ms ease, color 250ms ease, border-color 250ms ease;
}
.preview-title {
  font-weight: 800;
  font-size: 16px;
  line-height: 1;
}
.preview-caption {
  font-size: 12px;
  opacity: 0.9;
}

@media (max-width: 860px) {
  .config-row {
    grid-template-columns: 1fr;
    align-items: stretch;
  }
  .config-preview {
    align-items: flex-start;
  }
}
</style>

