<template>
  <q-card class="risk-card">
    <q-card-section class="risk-card__section">
      <div class="risk-card__header">
        <div class="risk-card__title">Risk assessment</div>
        <q-icon name="info" size="16px" class="risk-card__info" />
        <q-tooltip class="risk-card__tooltip">
          {{ transparencySummary }}
        </q-tooltip>
      </div>
      <div class="risk-card__subtitle">
        Overall risk: {{ overallRiskText }} – {{ confidenceText }} ({{ confidenceLabelText }}) confidence
      </div>

      <div class="risk-card__content">
        <div class="risk-card__left">
          <div class="risk-card__donut" role="img" aria-label="AI risk level donut chart">
            <div class="risk-card__donut-hole">
              <div class="risk-card__donut-value">{{ donutText }}</div>
              <div class="risk-card__donut-label">AI risk level</div>
            </div>
          </div>
        </div>

        <div class="risk-card__right">
          <div class="risk-card__rec-title">Recommended action</div>
          <ul class="risk-card__rec-list">
            <li v-for="a in actionItems" :key="a.key" class="risk-card__rec-item">
              <div class="risk-card__rec-line">
                <q-icon :name="a.icon" size="14px" :style="{ color: a.dotColor }" aria-hidden="true" />
                <q-chip
                  dense
                  square
                  class="risk-card__tag"
                  :style="{ backgroundColor: a.tagBg, color: a.tagText }"
                >
                  {{ a.tagLabel }}
                </q-chip>
                <span class="risk-card__rec-text">{{ a.text }}</span>
              </div>
              <div v-if="a.meta" class="risk-card__rec-meta">{{ a.meta }}</div>
            </li>
            <li v-if="!actionItems.length">No recommendations available.</li>
          </ul>
        </div>
      </div>

      <div class="risk-card__footer">
        <div class="risk-card__meta">Chi-Square: {{ chiSquareText }}</div>
        <div class="risk-card__meta">P-Value: {{ pValueText }}</div>
      </div>

      <q-expansion-item
        dense
        class="risk-card__exp"
        label="Identified risks"
        header-class="risk-card__exp-header"
        expand-separator
      >
        <div class="risk-card__exp-body">
          <div v-for="r in riskItems" :key="r.key" class="risk-card__risk">
            <div class="risk-card__risk-row">
              <q-icon :name="r.icon" size="16px" :style="{ color: r.dotColor }" aria-hidden="true" />
              <div class="risk-card__risk-title">{{ r.title }}</div>
              <q-chip dense square class="risk-card__pill" :style="{ backgroundColor: r.tagBg, color: r.tagText }">
                {{ r.confidenceText }} ({{ r.confidenceLabel }})
              </q-chip>
            </div>
            <div class="risk-card__risk-sub">{{ r.criteriaText }}</div>
          </div>
          <div v-if="!riskItems.length" class="risk-card__empty">No identified risks available.</div>
        </div>
      </q-expansion-item>

      <q-expansion-item
        dense
        class="risk-card__exp"
        label="Transparency"
        header-class="risk-card__exp-header"
        expand-separator
      >
        <div class="risk-card__exp-body">
          <div class="risk-card__kv">
            <div class="risk-card__k">Data sources</div>
            <ul class="risk-card__list">
              <li v-for="s in dataSources" :key="s">{{ s }}</li>
              <li v-if="!dataSources.length">Not available.</li>
            </ul>
          </div>
          <div class="risk-card__kv">
            <div class="risk-card__k">Methodology</div>
            <div class="risk-card__v">{{ methodologyText }}</div>
          </div>
          <div class="risk-card__kv">
            <div class="risk-card__k">Assumptions</div>
            <ul class="risk-card__list">
              <li v-for="a in assumptions" :key="a">{{ a }}</li>
              <li v-if="!assumptions.length">Not available.</li>
            </ul>
          </div>
        </div>
      </q-expansion-item>

      <q-expansion-item
        dense
        class="risk-card__exp"
        label="Traceability"
        header-class="risk-card__exp-header"
        expand-separator
      >
        <div class="risk-card__exp-body">
          <div class="risk-card__kv">
            <div class="risk-card__k">Model</div>
            <div class="risk-card__v">{{ modelText }}</div>
          </div>
          <div class="risk-card__kv">
            <div class="risk-card__k">Inputs</div>
            <ul class="risk-card__list">
              <li v-for="i in traceInputs" :key="i.key">{{ i.text }}</li>
              <li v-if="!traceInputs.length">Not available.</li>
            </ul>
          </div>
          <div class="risk-card__kv">
            <div class="risk-card__k">Generated</div>
            <div class="risk-card__v">{{ generatedAtText }}</div>
          </div>
        </div>
      </q-expansion-item>
    </q-card-section>
  </q-card>
</template>

<script setup lang="ts">
import { computed } from 'vue';

type Priority = 'high' | 'medium' | 'low';

type RiskActionObj = {
  id?: unknown;
  text?: unknown;
  priority?: unknown;
  owner?: unknown;
  due_by?: unknown;
  review_by?: unknown;
  success_metric?: unknown;
};
type RiskAction = string | RiskActionObj;

type RiskTraceability = {
  generated_at?: unknown;
  inputs?: unknown;
  model?: unknown;
};

type RiskEntry = {
  id?: unknown;
  title?: unknown;
  description?: unknown;
  impact?: unknown;
  likelihood?: unknown;
  business_criticality?: unknown;
  confidence?: unknown;
  confidence_label?: unknown;
  traceability?: unknown;
};

export type RiskAssessmentCardData = {
  overall_risk?: string | null;
  confidence?: number | null;
  confidence_label?: string | null;
  chi_square?: number | null;
  p_value?: number | null;
  data_sources?: string[] | null;
  methodology?: string | null;
  assumptions?: string[] | null;
  traceability?: RiskTraceability | null;
  risks?: RiskEntry[] | null;
  recommended_actions?: RiskAction[] | null;
};

const props = defineProps<{
  risk?: RiskAssessmentCardData | null;
}>();

const fallbackRisk: RiskAssessmentCardData = {
  overall_risk: 'moderate',
  confidence: 78.4,
  confidence_label: 'Medium',
  chi_square: 8.342,
  p_value: 0.0502,
  data_sources: [
    'PatientRecord (Admissions) — aggregated counts',
    'Psychiatric OPD Questionnaire — submitted symptom profiles',
    'Consultation Notes — follow-up indicators',
  ],
  methodology:
    'Confidence uses a 70/30 hold-out evaluation where available and a 95% CI calibration proxy for live forecasts. Risk priority combines impact, likelihood, and business criticality (1–5).',
  assumptions: [
    'Historical patterns approximate near-term clinic demand.',
    'Data completeness is sufficient for cohort-level decisions.',
    'Model drift is monitored via periodic recalibration checks.',
  ],
  traceability: {
    generated_at: new Date().toISOString(),
    inputs: [
      { source: 'PatientRecord', range: 'last_3_months', filters: ['department:OPD'] },
      { source: 'PsychiatricOpdQuestionnaire', range: 'last_3_months', filters: ['status:submitted'] },
      { source: 'ConsultationNotes', range: 'last_3_months', filters: ['has_followup:true'] },
    ],
    model: { name: 'SARIMAX', version: 'v1', params: { train_ratio: 0.7, ci_level: 0.95, seasonality: 'monthly' } },
  },
  risks: [
    {
      id: 'risk-1',
      title: 'High revisit risk in hypertension cohort',
      impact: 4,
      likelihood: 4,
      business_criticality: 5,
      confidence: 86.2,
      confidence_label: 'High',
    },
    {
      id: 'risk-2',
      title: 'Moderate service delay risk due to staffing constraints',
      impact: 3,
      likelihood: 3,
      business_criticality: 4,
      confidence: 67.5,
      confidence_label: 'Medium',
    },
  ],
  recommended_actions: [
    {
      id: 'act-1',
      text: 'Follow-up within 24–48 hours for flagged high-risk patients.',
      priority: 'High',
      owner: 'Nurse Supervisor',
      due_by: new Date(Date.now() + 36 * 60 * 60 * 1000).toISOString(),
      review_by: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
      success_metric: '≥90% of flagged patients contacted within 48 hours.',
    },
    {
      id: 'act-2',
      text: 'Review trend drivers (seasonality, staffing, holidays) and confirm mitigation plan.',
      priority: 'Medium',
      owner: 'Doctor-in-Charge',
      due_by: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString(),
      review_by: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString(),
      success_metric: 'Documented plan with 3 measurable mitigations.',
    },
    {
      id: 'act-3',
      text: 'Run preventive screening checklist for patients with repeated visits.',
      priority: 'Low',
      owner: 'Assigned Nurse',
      due_by: new Date(Date.now() + 5 * 24 * 60 * 60 * 1000).toISOString(),
      review_by: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
      success_metric: 'Screening completion rate ≥80% for eligible patients.',
    },
  ],
};

const risk = computed(() => props.risk || fallbackRisk);

const toConfidencePct = (raw: unknown): number | null => {
  if (typeof raw !== 'number' || !Number.isFinite(raw)) return null;
  if (raw >= 0 && raw <= 1) return raw * 100;
  return raw;
};

const overallRiskText = computed(() => {
  const v = risk.value.overall_risk;
  const s = typeof v === 'string' ? v.trim() : '';
  return s || 'N/A';
});

const confidenceText = computed(() => {
  const pct = toConfidencePct(risk.value.confidence);
  if (pct == null) return 'N/A';
  return `${pct.toFixed(2)}%`;
});

const confidenceLabelText = computed(() => {
  const raw = risk.value.confidence_label;
  const v = typeof raw === 'string' ? raw.trim() : '';
  if (v) return v;
  const pct = toConfidencePct(risk.value.confidence);
  if (pct == null) return 'N/A';
  if (pct >= 80) return 'High';
  if (pct >= 60) return 'Medium';
  return 'Low';
});

const donutText = computed(() => {
  const pct = toConfidencePct(risk.value.confidence);
  if (pct == null) return 'N/A';
  return `${Math.round(pct)}%`;
});

const formatNum = (v: unknown, digits: number): string => {
  if (typeof v !== 'number' || !Number.isFinite(v)) return 'N/A';
  return v.toFixed(digits);
};

const chiSquareText = computed(() => formatNum(risk.value.chi_square, 4));
const pValueText = computed(() => formatNum(risk.value.p_value, 4));

const dataSources = computed(() => (Array.isArray(risk.value.data_sources) ? risk.value.data_sources : []).filter((s) => typeof s === 'string' && s.trim()).map((s) => s.trim()));
const methodologyText = computed(() => {
  const v = risk.value.methodology;
  if (typeof v === 'string' && v.trim()) return v.trim();
  return 'Not available.';
});
const assumptions = computed(() => (Array.isArray(risk.value.assumptions) ? risk.value.assumptions : []).filter((s) => typeof s === 'string' && s.trim()).map((s) => s.trim()));

const isPlainObject = (v: unknown): v is Record<string, unknown> =>
  v != null && typeof v === 'object' && !Array.isArray(v);

const trace = computed(() => (isPlainObject(risk.value.traceability) ? risk.value.traceability : null));
const modelText = computed(() => {
  const t = trace.value;
  if (!t || !isPlainObject(t.model)) return 'Not available.';
  const m = t.model;
  const name = typeof m.name === 'string' ? m.name.trim() : '';
  const ver = typeof m.version === 'string' ? m.version.trim() : '';
  const parts: string[] = [];
  if (name) parts.push(name);
  if (ver) parts.push(ver);
  const params = isPlainObject(m.params) ? m.params : null;
  if (params) {
    const keys = Object.keys(params).slice(0, 6);
    if (keys.length) parts.push(`params: ${keys.join(', ')}`);
  }
  return parts.length ? parts.join(' • ') : 'Not available.';
});

const traceInputs = computed(() => {
  const t = trace.value;
  const inputs = t && Array.isArray(t.inputs) ? t.inputs : [];
  const out: Array<{ key: string; text: string }> = [];
  for (const it of inputs) {
    if (!isPlainObject(it)) continue;
    const src = typeof it.source === 'string' ? it.source.trim() : '';
    if (!src) continue;
    const range = typeof it.range === 'string' ? it.range.trim() : '';
    const filters = Array.isArray(it.filters) ? it.filters.filter((f) => typeof f === 'string' && f.trim()).slice(0, 3).map((f) => f.trim()) : [];
    const parts = [src];
    if (range) parts.push(range);
    if (filters.length) parts.push(filters.join(', '));
    const text = parts.join(' — ');
    out.push({ key: text, text });
  }
  return out;
});

const generatedAtText = computed(() => {
  const t = trace.value;
  const raw = t ? t.generated_at : null;
  const s = typeof raw === 'string' ? raw.trim() : '';
  if (!s) return 'Not available.';
  const d = new Date(s);
  if (!Number.isFinite(d.getTime())) return s;
  return d.toLocaleString();
});

const transparencySummary = computed(() => {
  const parts: string[] = [];
  parts.push(`Confidence: ${confidenceText.value} (${confidenceLabelText.value}).`);
  const ds = dataSources.value;
  if (ds.length) parts.push(`Sources: ${ds.slice(0, 2).join('; ')}${ds.length > 2 ? '…' : ''}.`);
  const mt = methodologyText.value;
  if (mt && mt !== 'Not available.') parts.push('Methodology and traceability available below.');
  return parts.join(' ');
});

const normalizePriority = (raw: unknown): Priority | null => {
  if (typeof raw !== 'string') return null;
  const v = raw.trim().toLowerCase();
  if (v === 'high' || v.includes('high')) return 'high';
  if (v === 'medium' || v.includes('medium')) return 'medium';
  if (v === 'low' || v.includes('low')) return 'low';
  return null;
};

const categorizePriority = (text: string): Priority => {
  const t = text.toLowerCase();
  if (
    t.includes('urgent') ||
    t.includes('immediate') ||
    t.includes('asap') ||
    t.includes('critical') ||
    t.includes('emergency')
  ) return 'high';
  if (
    t.includes('follow-up') ||
    t.includes('follow up') ||
    t.includes('review') ||
    t.includes('monitor') ||
    t.includes('schedule') ||
    t.includes('within 24') ||
    t.includes('within 48')
  ) return 'medium';
  return 'low';
};

const priorityVisual = (p: Priority) => {
  if (p === 'high') {
    return {
      tagLabel: 'High',
      dotColor: '#ef4444',
      icon: 'error',
      tagBg: 'rgba(239, 68, 68, 0.14)',
      tagText: '#b91c1c',
    };
  }
  if (p === 'medium') {
    return {
      tagLabel: 'Medium',
      dotColor: '#f59e0b',
      icon: 'warning',
      tagBg: 'rgba(245, 158, 11, 0.16)',
      tagText: '#b45309',
    };
  }
  return {
    tagLabel: 'Low',
    dotColor: '#22c55e',
    icon: 'check_circle',
    tagBg: 'rgba(34, 197, 94, 0.12)',
    tagText: '#166534',
  };
};

const isActionObj = (v: unknown): v is { text?: unknown; priority?: unknown } =>
  v != null && typeof v === 'object' && !Array.isArray(v);

const actionMeta = (v: unknown): string | null => {
  if (!isPlainObject(v)) return null;
  const owner = typeof v.owner === 'string' ? v.owner.trim() : '';
  const due = typeof v.due_by === 'string' ? v.due_by.trim() : '';
  const review = typeof v.review_by === 'string' ? v.review_by.trim() : '';
  const metric = typeof v.success_metric === 'string' ? v.success_metric.trim() : '';
  const parts: string[] = [];
  if (owner) parts.push(`Owner: ${owner}`);
  if (due) parts.push(`Due: ${formatWhen(due)}`);
  if (review) parts.push(`Review: ${formatWhen(review)}`);
  if (metric) parts.push(`Success: ${metric}`);
  return parts.length ? parts.join(' • ') : null;
};

function formatWhen(iso: string): string {
  const d = new Date(iso);
  if (!Number.isFinite(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { month: 'short', day: '2-digit' });
}

const actionItems = computed(() => {
  const raw = risk.value.recommended_actions;
  const list = Array.isArray(raw) ? raw : [];
  return list
    .map((a, idx) => {
      if (typeof a === 'string') {
        const text = a.trim();
        if (!text) return null;
        const priority = categorizePriority(text);
        return { key: `${idx}:${priority}:${text}`, text, meta: null as string | null, ...priorityVisual(priority) };
      }
      if (isActionObj(a)) {
        const rawText = a.text;
        const text = typeof rawText === 'string' ? rawText.trim() : '';
        if (!text) return null;
        const pr = normalizePriority(a.priority);
        const priority = pr || categorizePriority(text);
        return { key: `${idx}:${priority}:${text}`, text, meta: actionMeta(a), ...priorityVisual(priority) };
      }
      return null;
    })
    .filter((x): x is NonNullable<typeof x> => Boolean(x));
});

const confidenceVisual = (label: string) => {
  const v = label.trim().toLowerCase();
  if (v === 'high') return { tagBg: 'rgba(34, 197, 94, 0.12)', tagText: '#166534', dotColor: '#22c55e', icon: 'check_circle' };
  if (v === 'medium') return { tagBg: 'rgba(245, 158, 11, 0.16)', tagText: '#b45309', dotColor: '#f59e0b', icon: 'warning' };
  return { tagBg: 'rgba(239, 68, 68, 0.14)', tagText: '#b91c1c', dotColor: '#ef4444', icon: 'error' };
};

const riskItems = computed(() => {
  const raw = Array.isArray(risk.value.risks) ? risk.value.risks : [];
  const out: Array<{
    key: string;
    title: string;
    confidenceText: string;
    confidenceLabel: string;
    criteriaText: string;
    tagBg: string;
    tagText: string;
    dotColor: string;
    icon: string;
  }> = [];
  for (const it of raw) {
    if (!isPlainObject(it)) continue;
    const title = typeof it.title === 'string' ? it.title.trim() : '';
    if (!title) continue;
    const confNum = typeof it.confidence === 'number' && Number.isFinite(it.confidence) ? it.confidence : null;
    const confText = confNum != null ? `${confNum.toFixed(1)}%` : 'N/A';
    const lblRaw = typeof it.confidence_label === 'string' ? it.confidence_label.trim() : '';
    const lbl = lblRaw || (confNum != null ? (confNum >= 80 ? 'High' : confNum >= 60 ? 'Medium' : 'Low') : 'N/A');
    const impact = typeof it.impact === 'number' ? it.impact : null;
    const likelihood = typeof it.likelihood === 'number' ? it.likelihood : null;
    const crit = typeof it.business_criticality === 'number' ? it.business_criticality : null;
    const parts: string[] = [];
    if (impact != null) parts.push(`Impact ${impact}/5`);
    if (likelihood != null) parts.push(`Likelihood ${likelihood}/5`);
    if (crit != null) parts.push(`Criticality ${crit}/5`);
    const traceability = isPlainObject(it.traceability) ? it.traceability : null;
    if (traceability && isPlainObject(traceability.model)) {
      const m = traceability.model;
      const mn = typeof m.name === 'string' ? m.name.trim() : '';
      const mv = typeof m.version === 'string' ? m.version.trim() : '';
      const modelParts = [mn, mv].filter(Boolean);
      if (modelParts.length) parts.push(`Model ${modelParts.join(' ')}`);
    }
    if (traceability && Array.isArray(traceability.inputs)) {
      const inputs = traceability.inputs
        .filter((x) => isPlainObject(x) && typeof x.source === 'string' && x.source.trim())
        .slice(0, 3)
        .map((x) => (x as Record<string, unknown>).source as string);
      if (inputs.length) parts.push(`Inputs ${inputs.join(', ')}`);
    }
    const criteriaText = parts.length ? parts.join(' • ') : 'Criteria not available.';
    const vis = confidenceVisual(lbl);
    out.push({
      key: `${title}:${confText}:${lbl}`,
      title,
      confidenceText: confText,
      confidenceLabel: lbl,
      criteriaText,
      ...vis,
    });
  }
  return out;
});
</script>

<style scoped>
.risk-card {
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 14px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
}

.risk-card__section {
  padding: 14px 14px 10px 14px;
}

.risk-card__header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.risk-card__title {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.2px;
  color: #0f172a;
  text-transform: none;
}

.risk-card__info {
  color: #94a3b8;
  cursor: pointer;
  margin-left: auto;
}

.risk-card__tooltip {
  font-size: 12px;
  max-width: 360px;
  white-space: normal;
}

.risk-card__subtitle {
  margin-top: 4px;
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
}

.risk-card__content {
  margin-top: 10px;
  display: flex;
  gap: 12px;
  align-items: center;
}

.risk-card__left {
  width: 46%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.risk-card__right {
  width: 54%;
}

.risk-card__donut {
  width: 112px;
  height: 112px;
  border-radius: 999px;
  background: conic-gradient(
    #22c55e 0deg 220deg,
    #f59e0b 220deg 290deg,
    #ef4444 290deg 360deg
  );
  display: grid;
  place-items: center;
}

.risk-card__donut-hole {
  width: 76px;
  height: 76px;
  border-radius: 999px;
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  text-align: center;
}

.risk-card__donut-value {
  font-size: 18px;
  font-weight: 900;
  color: #0f172a;
  line-height: 1;
}

.risk-card__donut-label {
  margin-top: 3px;
  font-size: 10px;
  font-weight: 700;
  color: #64748b;
  line-height: 1.1;
}

.risk-card__rec-title {
  font-size: 11px;
  font-weight: 800;
  color: #0f172a;
}

.risk-card__rec-list {
  margin: 6px 0 0 0;
  padding-left: 0;
  font-size: 10.5px;
  font-weight: 600;
  color: #475569;
  line-height: 1.35;
}

.risk-card__rec-item {
  list-style: none;
  margin: 0 0 6px 0;
}

.risk-card__rec-line {
  display: flex;
  align-items: center;
  gap: 8px;
}

.risk-card__tag {
  font-size: 10px;
  font-weight: 900;
  border-radius: 8px;
  padding: 0 8px;
}

.risk-card__rec-text {
  font-size: 10.5px;
  font-weight: 650;
  color: #475569;
  line-height: 1.35;
}

.risk-card__rec-meta {
  margin-left: 0;
  margin-top: 4px;
  font-size: 10px;
  font-weight: 650;
  color: #94a3b8;
  line-height: 1.3;
}

.risk-card__footer {
  margin-top: 10px;
  padding-top: 8px;
  display: flex;
  justify-content: space-between;
  gap: 10px;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
}

.risk-card__meta {
  font-size: 10px;
  font-weight: 700;
  color: #64748b;
  white-space: nowrap;
}

.risk-card__exp {
  margin-top: 6px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 12px;
  overflow: hidden;
}

.risk-card__exp-header {
  font-size: 11px;
  font-weight: 800;
  color: #0f172a;
}

.risk-card__exp-body {
  padding: 10px 12px;
  font-size: 10.5px;
  font-weight: 600;
  color: #475569;
}

.risk-card__kv {
  margin-bottom: 10px;
}

.risk-card__k {
  font-size: 10px;
  font-weight: 900;
  color: #0f172a;
  margin-bottom: 4px;
}

.risk-card__v {
  font-size: 10.5px;
  font-weight: 600;
  color: #475569;
  line-height: 1.35;
}

.risk-card__list {
  margin: 0;
  padding-left: 16px;
}

.risk-card__risk {
  padding: 8px 0;
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
}

.risk-card__risk:last-child {
  border-bottom: none;
}

.risk-card__risk-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.risk-card__risk-title {
  font-size: 10.5px;
  font-weight: 800;
  color: #0f172a;
  flex: 1;
  min-width: 0;
}

.risk-card__pill {
  font-size: 10px;
  font-weight: 900;
  border-radius: 8px;
  padding: 0 8px;
}

.risk-card__risk-sub {
  margin-top: 4px;
  font-size: 10px;
  font-weight: 650;
  color: #94a3b8;
  line-height: 1.3;
}

.risk-card__empty {
  font-size: 10.5px;
  font-weight: 650;
  color: #94a3b8;
}
</style>
