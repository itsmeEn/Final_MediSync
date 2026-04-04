import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { parseColorToRgb, rgbToHex, ensureWcagAaText, deriveHoverAndActive } from 'src/utils/colorTheme'

export type ThemeMode = 'light' | 'dark'

export type CardColorConfig = {
  lightBg?: string
  darkBg?: string
}

export type CardThemeState = {
  version: number
  cards: Record<string, CardColorConfig>
}

const STORAGE_KEY = 'cardTheme.v1'

const DEFAULTS: CardThemeState = {
  version: 1,
  cards: {
    'doctor.kpi.forecast': { lightBg: '#ffffff', darkBg: '#111827' },
    'doctor.kpi.patients': { lightBg: '#ffffff', darkBg: '#111827' },
    'doctor.kpi.age': { lightBg: '#ffffff', darkBg: '#111827' },
    'doctor.kpi.volume': { lightBg: '#ffffff', darkBg: '#111827' },
    'doctor.card.surge': { lightBg: '#ffffff', darkBg: '#0b1220' },
    'doctor.card.volume': { lightBg: '#ffffff', darkBg: '#0b1220' },
    'doctor.card.trends': { lightBg: '#ffffff', darkBg: '#0b1220' },
    'doctor.card.demographics': { lightBg: '#ffffff', darkBg: '#0b1220' },
    'doctor.card.gender': { lightBg: '#ffffff', darkBg: '#0b1220' },
    'doctor.card.ai': { lightBg: '#ffffff', darkBg: '#0b1220' },

    'nurse.card.medication': { lightBg: '#ffffff', darkBg: '#0b1220' },
    'nurse.card.volume': { lightBg: '#ffffff', darkBg: '#0b1220' },
    'nurse.card.trends': { lightBg: '#ffffff', darkBg: '#0b1220' },
    'nurse.card.demographics': { lightBg: '#ffffff', darkBg: '#0b1220' },
    'nurse.card.ai': { lightBg: '#ffffff', darkBg: '#0b1220' },
  },
}

const safeParseState = (raw: string | null): CardThemeState | null => {
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw) as unknown
    if (!parsed || typeof parsed !== 'object') return null
    const obj = parsed as { version?: unknown; cards?: unknown }
    if (obj.version !== 1) return null
    if (!obj.cards || typeof obj.cards !== 'object') return null
    return { version: 1, cards: obj.cards as Record<string, CardColorConfig> }
  } catch {
    return null
  }
}

export const useCardThemeStore = defineStore('cardTheme', () => {
  const state = ref<CardThemeState>(DEFAULTS)

  const load = () => {
    const parsed = safeParseState(localStorage.getItem(STORAGE_KEY))
    if (parsed) state.value = { version: 1, cards: { ...DEFAULTS.cards, ...parsed.cards } }
  }

  const persist = () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state.value))
  }

  const setCardBg = (cardId: string, mode: ThemeMode, color: string) => {
    const cfg = state.value.cards[cardId] ? { ...state.value.cards[cardId] } : {}
    if (mode === 'light') cfg.lightBg = color
    else cfg.darkBg = color
    state.value.cards = { ...state.value.cards, [cardId]: cfg }
    persist()
  }

  const resetCard = (cardId: string) => {
    const next = { ...state.value.cards }
    if (DEFAULTS.cards[cardId]) next[cardId] = { ...DEFAULTS.cards[cardId] }
    else delete next[cardId]
    state.value.cards = next
    persist()
  }

  const resetAll = () => {
    state.value = { version: 1, cards: { ...DEFAULTS.cards } }
    persist()
  }

  const resolveVars = (cardId: string, isDark: boolean) => {
    const cfg = state.value.cards[cardId] || {}
    const raw = isDark ? cfg.darkBg || DEFAULTS.cards[cardId]?.darkBg : cfg.lightBg || DEFAULTS.cards[cardId]?.lightBg
    const bgRgb = parseColorToRgb(raw || '#ffffff') || parseColorToRgb('#ffffff')!
    const aa = ensureWcagAaText(bgRgb, 4.5)
    const hoverActive = deriveHoverAndActive(aa.bg)
    const muted = ensureWcagAaText(hoverActive.hover, 4.5)
    return {
      bg: rgbToHex(aa.bg),
      fg: rgbToHex(aa.fg),
      hoverBg: rgbToHex(hoverActive.hover),
      activeBg: rgbToHex(hoverActive.active),
      border: rgbToHex(hoverActive.border),
      muted: rgbToHex(muted.fg),
      ratio: aa.ratio,
    }
  }

  const palette = computed(() => {
    const items = [
      { label: 'Default', value: 'default', light: '#ffffff', dark: '#0b1220' },
      { label: 'Ocean', value: 'ocean', light: '#e6f4ff', dark: '#0b2a3a' },
      { label: 'Mint', value: 'mint', light: '#e7fbf3', dark: '#0b2e23' },
      { label: 'Sunset', value: 'sunset', light: '#fff1e6', dark: '#3a1b0b' },
      { label: 'Lavender', value: 'lavender', light: '#f2efff', dark: '#1b153a' },
      { label: 'Slate', value: 'slate', light: '#eef2f6', dark: '#111827' },
    ]
    return items
  })

  const applyPalette = (cardId: string, paletteValue: string) => {
    const p = palette.value.find((x) => x.value === paletteValue)
    if (!p) return
    setCardBg(cardId, 'light', p.light)
    setCardBg(cardId, 'dark', p.dark)
  }

  const exportJson = () => JSON.stringify(state.value, null, 2)

  const importJson = (raw: string) => {
    const parsed = safeParseState(raw)
    if (!parsed) return false
    state.value = { version: 1, cards: { ...DEFAULTS.cards, ...parsed.cards } }
    persist()
    return true
  }

  load()

  return {
    state,
    palette,
    resolveVars,
    setCardBg,
    applyPalette,
    resetCard,
    resetAll,
    exportJson,
    importJson,
  }
})

