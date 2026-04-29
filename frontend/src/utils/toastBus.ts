export type MsToastType = 'positive' | 'negative' | 'warning' | 'info'

export type MsToastPayload = {
  id?: string
  type: MsToastType
  message: string
  timeoutMs?: number
}

export const msToastBus = new EventTarget()

export const emitMsToast = (payload: MsToastPayload) => {
  const id = payload.id ?? `${Date.now()}_${Math.random().toString(16).slice(2)}`
  msToastBus.dispatchEvent(new CustomEvent('ms-toast', { detail: { ...payload, id } }))
  return id
}
