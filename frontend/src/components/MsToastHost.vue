<template>
  <div class="ms-toast-host" aria-label="Toast notifications">
    <TransitionGroup name="ms-toast" tag="div" class="ms-toast-stack">
      <div v-for="t in toasts" :key="t.id" class="ms-toast-outer">
        <div
          class="ms-toast"
          :class="`is-${t.type}`"
          role="status"
          aria-live="polite"
          :style="{ transform: `translateX(${t.dx}px)` }"
          @pointerdown="onPointerDown(t.id, $event)"
          @pointermove="onPointerMove(t.id, $event)"
          @pointerup="onPointerUp(t.id, $event)"
          @pointercancel="onPointerCancel(t.id)"
        >
          <div class="ms-toast-body">{{ t.message }}</div>
          <button class="ms-toast-close" type="button" aria-label="Dismiss notification" @click="dismiss(t.id)">
            <span aria-hidden="true">×</span>
          </button>
        </div>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { msToastBus, type MsToastPayload, type MsToastType } from 'src/utils/toastBus'

type ToastItem = {
  id: string
  type: MsToastType
  message: string
  timeoutMs: number
  timerId: number | null
  dx: number
  startX: number | null
  pointerId: number | null
}

const toasts = ref<ToastItem[]>([])

const clearTimer = (t: ToastItem) => {
  if (t.timerId !== null) {
    window.clearTimeout(t.timerId)
    t.timerId = null
  }
}

const dismiss = (id: string) => {
  const idx = toasts.value.findIndex((t) => t.id === id)
  if (idx === -1) return
  clearTimer(toasts.value[idx]!)
  toasts.value.splice(idx, 1)
}

const addToast = (payload: MsToastPayload & { id: string }) => {
  const timeoutMs = typeof payload.timeoutMs === 'number' ? payload.timeoutMs : 2500
  const item: ToastItem = {
    id: payload.id,
    type: payload.type,
    message: payload.message,
    timeoutMs,
    timerId: null,
    dx: 0,
    startX: null,
    pointerId: null
  }
  item.timerId = window.setTimeout(() => dismiss(item.id), item.timeoutMs)
  toasts.value = [item, ...toasts.value].slice(0, 3)
}

const handleEvent = (evt: Event) => {
  const e = evt as CustomEvent<MsToastPayload & { id: string }>
  const detail = e.detail
  if (!detail?.id || !detail?.message) return
  addToast(detail)
}

const getToastById = (id: string) => toasts.value.find((t) => t.id === id) ?? null

const onPointerDown = (id: string, e: PointerEvent) => {
  const t = getToastById(id)
  if (!t) return
  t.startX = e.clientX
  t.pointerId = e.pointerId
  clearTimer(t)
  try { (e.currentTarget as HTMLElement | null)?.setPointerCapture(e.pointerId) } catch (err) { void err }
}

const onPointerMove = (id: string, e: PointerEvent) => {
  const t = getToastById(id)
  if (!t || t.pointerId !== e.pointerId || t.startX === null) return
  const delta = e.clientX - t.startX
  const clamped = Math.max(-140, Math.min(140, delta))
  t.dx = clamped
}

const onPointerUp = (id: string, e: PointerEvent) => {
  const t = getToastById(id)
  if (!t || t.pointerId !== e.pointerId) return
  const shouldDismiss = Math.abs(t.dx) >= 80
  t.startX = null
  t.pointerId = null
  if (shouldDismiss) {
    dismiss(id)
    return
  }
  t.dx = 0
  t.timerId = window.setTimeout(() => dismiss(t.id), t.timeoutMs)
}

const onPointerCancel = (id: string) => {
  const t = getToastById(id)
  if (!t) return
  t.startX = null
  t.pointerId = null
  t.dx = 0
  t.timerId = window.setTimeout(() => dismiss(t.id), t.timeoutMs)
}

onMounted(() => {
  msToastBus.addEventListener('ms-toast', handleEvent as EventListener)
})

onUnmounted(() => {
  msToastBus.removeEventListener('ms-toast', handleEvent as EventListener)
  toasts.value.forEach(clearTimer)
})
</script>

<style scoped>
.ms-toast-host {
  position: fixed;
  z-index: 5000;
  top: calc(env(safe-area-inset-top, 0px) + 12px);
  left: 50%;
  transform: translateX(-50%);
  width: min(520px, calc(100vw - 24px));
  pointer-events: none;
}

.ms-toast-stack {
  display: grid;
  gap: 10px;
}

.ms-toast-outer {
  pointer-events: none;
}

.ms-toast {
  pointer-events: auto;
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: 10px;
  min-height: 44px;
  padding: 12px 12px 12px 14px;
  border-radius: 16px;
  background: var(--ms-card, #ffffff);
  color: var(--ms-text, #0f172a);
  border: 1px solid var(--ms-border, rgba(15, 23, 42, 0.12));
  box-shadow: var(--ms-shadow, 0 10px 28px rgba(15, 23, 42, 0.10));
  transition: transform 180ms ease, opacity 180ms ease;
  touch-action: pan-y;
}

.ms-toast-body {
  font-size: 14px;
  line-height: 1.25;
}

.ms-toast-close {
  min-width: 44px;
  min-height: 44px;
  border-radius: 12px;
  border: 1px solid transparent;
  background: transparent;
  color: inherit;
  font-size: 22px;
  line-height: 1;
}

.ms-toast-close:focus-visible {
  outline: 3px solid var(--ms-focus, rgba(38, 166, 154, 0.55));
  outline-offset: 2px;
}

.ms-toast.is-positive {
  border-color: rgba(46, 125, 50, 0.35);
}

.ms-toast.is-negative {
  border-color: rgba(198, 40, 40, 0.4);
}

.ms-toast.is-warning {
  border-color: rgba(245, 124, 0, 0.45);
}

.ms-toast.is-info {
  border-color: rgba(2, 136, 209, 0.35);
}

.ms-toast-enter-active,
.ms-toast-leave-active {
  transition: opacity 180ms ease, transform 180ms ease;
}

.ms-toast-enter-from,
.ms-toast-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
