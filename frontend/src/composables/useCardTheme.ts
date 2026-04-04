import { computed } from 'vue'
import { useQuasar } from 'quasar'
import { useCardThemeStore } from 'src/stores/cardTheme'

export const useCardTheme = () => {
  const $q = useQuasar()
  const store = useCardThemeStore()

  const isDark = computed(() => $q.dark.isActive)

  const cardStyle = (cardId: string) => {
    const v = store.resolveVars(cardId, isDark.value)
    return {
      '--card-bg': v.bg,
      '--card-fg': v.fg,
      '--card-muted': v.muted,
      '--card-border': v.border,
      '--card-bg-hover': v.hoverBg,
      '--card-bg-active': v.activeBg,
    } as Record<string, string>
  }

  return {
    cardStyle,
    store,
    isDark,
  }
}

