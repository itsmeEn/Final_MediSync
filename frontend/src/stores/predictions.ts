import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from 'src/boot/axios'
 
export type RiskAction = {
  id?: string | null
  text: string
  priority?: 'High' | 'Medium' | 'Low' | 'high' | 'medium' | 'low' | null
  owner?: string | null
  due_by?: string | null
  review_by?: string | null
  success_metric?: string | null
}
 
export type RiskTraceability = {
  generated_at?: string | null
  inputs?: Array<{
    source: string
    range?: string | null
    filters?: string[] | null
  }> | null
  model?: {
    name?: string | null
    version?: string | null
    params?: Record<string, unknown> | null
  } | null
}

export type RiskEntry = {
  id?: string | null
  title?: string | null
  description?: string | null
  impact?: number | null
  likelihood?: number | null
  business_criticality?: number | null
  confidence?: number | null
  confidence_label?: string | null
  traceability?: RiskTraceability | null
  recommended_actions?: RiskAction[] | null
}

export type RiskAssessment = {
  overall_risk?: string | null
  confidence?: number | null
  confidence_label?: string | null
  chi_square?: number | null
  p_value?: number | null
  data_sources?: string[] | null
  methodology?: string | null
  assumptions?: string[] | null
  traceability?: RiskTraceability | null
  risks?: RiskEntry[] | null
  recommended_actions?: Array<string | RiskAction> | null
}
 
type RiskAssessmentEnvelope = {
  risk_assessment: RiskAssessment
  version: number
  updated_at: string | null
  updated_by_role: string | null
}
 
type ConflictState = {
  serverVersion: number
  serverState: RiskAssessment
  updatedAt: string | null
  updatedByRole: string | null
}
 
export const usePredictionsStore = defineStore('predictions', () => {
  const riskAssessment = ref<RiskAssessment | null>(null)
  const version = ref<number>(0)
  const updatedAt = ref<string | null>(null)
  const updatedByRole = ref<string | null>(null)
 
  const loading = ref(false)
  const error = ref<string | null>(null)
  const conflict = ref<ConflictState | null>(null)
  const isUpdating = ref(false)
 
  const clientRole = ref<string | null>(null)
  const ws = ref<WebSocket | null>(null)
 
  const hasRealtime = computed(() => ws.value != null && ws.value.readyState === WebSocket.OPEN)
 
  const isPlainObject = (v: unknown): v is Record<string, unknown> =>
    v != null && typeof v === 'object' && !Array.isArray(v)

  const applyEnvelope = (env: RiskAssessmentEnvelope) => {
    riskAssessment.value = env.risk_assessment
    version.value = env.version
    updatedAt.value = env.updated_at
    updatedByRole.value = env.updated_by_role
  }
 
  const fetchRiskAssessment = async () => {
    loading.value = true
    error.value = null
    try {
      const resp = await api.get('/analytics/risk-assessment/')
      const data = resp.data?.data as Partial<RiskAssessmentEnvelope> | undefined
      const risk: RiskAssessment =
        data?.risk_assessment && typeof data.risk_assessment === 'object' ? data.risk_assessment : {}
      const env: RiskAssessmentEnvelope = {
        risk_assessment: risk,
        version: typeof data?.version === 'number' ? data.version : Number(data?.version || 0),
        updated_at: typeof data?.updated_at === 'string' ? data.updated_at : null,
        updated_by_role: typeof data?.updated_by_role === 'string' ? data.updated_by_role : null,
      }
      applyEnvelope(env)
      conflict.value = null
    } catch {
      error.value = 'Failed to load risk assessment state'
    } finally {
      loading.value = false
    }
  }
 
  const updateRiskAssessment = async (next: RiskAssessment) => {
    if (isUpdating.value) return
    isUpdating.value = true
    error.value = null
    conflict.value = null
    try {
      const resp = await api.put('/analytics/risk-assessment/', {
        version: version.value,
        risk_assessment: next,
      })
      const data = resp.data?.data as Partial<RiskAssessmentEnvelope> | undefined
      const risk: RiskAssessment =
        data?.risk_assessment && typeof data.risk_assessment === 'object' ? data.risk_assessment : next
      const env: RiskAssessmentEnvelope = {
        risk_assessment: risk,
        version: typeof data?.version === 'number' ? data.version : Number(data?.version || version.value),
        updated_at: typeof data?.updated_at === 'string' ? data.updated_at : null,
        updated_by_role: typeof data?.updated_by_role === 'string' ? data.updated_by_role : clientRole.value,
      }
      applyEnvelope(env)
    } catch (e: unknown) {
      const err = e as { response?: { status?: number; data?: unknown } }
      const status = err.response?.status
      if (status === 409) {
        const respData = err.response?.data
        const wrapped = isPlainObject(respData) ? respData.data : undefined
        const d = isPlainObject(wrapped) ? wrapped : {}
        conflict.value = {
          serverVersion: Number(d['server_version'] || 0),
          serverState: isPlainObject(d['server_state']) ? d['server_state'] : {},
          updatedAt: typeof d['updated_at'] === 'string' ? d['updated_at'] : null,
          updatedByRole: typeof d['updated_by_role'] === 'string' ? d['updated_by_role'] : null,
        }
        error.value = 'Conflict detected: another role updated this module.'
      } else {
        error.value = 'Failed to update risk assessment state'
      }
    } finally {
      isUpdating.value = false
    }
  }
 
  const connectRealtime = (role: string) => {
    clientRole.value = role
    if (ws.value && (ws.value.readyState === WebSocket.OPEN || ws.value.readyState === WebSocket.CONNECTING)) return
 
    const base = new URL(api.defaults.baseURL || `http://${window.location.hostname}:8000`)
    const protocol = base.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = base.hostname
    const port = base.port ? `:${base.port}` : ''
    const wsUrl = `${protocol}//${host}${port}/ws/predictions/`
 
    const socket = new WebSocket(wsUrl)
    ws.value = socket
 
    socket.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg?.type !== 'risk_assessment_update') return
        const payload = msg?.data || {}
        const env: RiskAssessmentEnvelope = {
          risk_assessment: (payload.risk_assessment && typeof payload.risk_assessment === 'object' ? payload.risk_assessment : {}) as RiskAssessment,
          version: Number(payload.version || 0),
          updated_at: typeof payload.updated_at === 'string' ? payload.updated_at : null,
          updated_by_role: typeof payload.updated_by_role === 'string' ? payload.updated_by_role : null,
        }
        if (env.version >= version.value) {
          applyEnvelope(env)
        }
      } catch {
        void 0
      }
    }
 
    socket.onclose = () => {
      ws.value = null
    }
  }
 
  const disconnectRealtime = () => {
    if (!ws.value) return
    try {
      ws.value.close()
    } catch {
      void 0
    } finally {
      ws.value = null
    }
  }
 
  return {
    riskAssessment,
    version,
    updatedAt,
    updatedByRole,
    loading,
    error,
    conflict,
    isUpdating,
    hasRealtime,
    fetchRiskAssessment,
    updateRiskAssessment,
    connectRealtime,
    disconnectRealtime,
  }
})
