<template>
  <q-card class="risk-card">
    <q-card-section class="risk-card__section">
      <div class="risk-card__header">
        <div class="risk-card__title">Risk assessment</div>
        <q-btn
          flat
          round
          dense
          icon="edit"
          size="sm"
          class="risk-card__edit"
          @click="openEdit"
          :disable="!canEdit"
          aria-label="Edit risk assessment"
        />
      </div>
      <div class="risk-card__subtitle">
        Overall risk: {{ overallRiskText }} – {{ confidenceText }} confidence
      </div>

      <div class="risk-card__content">
        <div class="risk-card__left">
          <div class="risk-card__donut" role="img" aria-label="AI risk level donut chart">
            <canvas ref="donutCanvas" class="risk-card__donut-canvas"></canvas>
            <div class="risk-card__donut-center" aria-hidden="true">
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
            </li>
            <li v-if="!actionItems.length">No recommendations available.</li>
          </ul>
        </div>
      </div>

      <div class="risk-card__footer">
        <div class="risk-card__meta">Chi-Square: {{ chiSquareText }}</div>
        <div class="risk-card__meta">P-Value: {{ pValueText }}</div>
      </div>
    </q-card-section>
  </q-card>

  <q-dialog v-model="editOpen" persistent>
    <q-card style="width: 560px; max-width: 92vw;">
      <q-card-section class="row items-center justify-between">
        <div class="text-h6">Edit Risk Assessment</div>
        <q-btn icon="close" flat round dense v-close-popup aria-label="Close" />
      </q-card-section>
      <q-separator />
      <q-card-section>
        <div class="row q-col-gutter-md">
          <div class="col-12 col-md-6">
            <q-select
              v-model="editOverallRisk"
              :options="overallRiskOptions"
              label="Overall risk"
              dense
              outlined
              emit-value
              map-options
            />
          </div>
          <div class="col-12 col-md-6">
            <q-input
              v-model.number="editConfidence"
              type="number"
              label="Confidence (%)"
              dense
              outlined
              :min="0"
              :max="100"
            />
          </div>
        </div>

        <div class="q-mt-md">
          <q-input
            v-model="editActionsText"
            type="textarea"
            autogrow
            dense
            outlined
            label="Recommended actions (one per line; optional prefix: High:, Medium:, Low:)"
          />
        </div>

        <div v-if="predictionsStore.conflict" class="q-mt-md">
          <q-banner dense class="bg-orange-1 text-orange-10">
            Conflict detected. Latest saved by {{ predictionsStore.conflict.updatedByRole || 'another role' }}.
          </q-banner>
        </div>
      </q-card-section>
      <q-separator />
      <q-card-actions align="right">
        <q-btn flat label="Cancel" v-close-popup />
        <q-btn
          unelevated
          color="primary"
          label="Save"
          :loading="predictionsStore.isUpdating"
          :disable="!canEdit"
          @click="saveEdit"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import { useQuasar } from 'quasar';
import { Chart, registerables } from 'chart.js';
import { usePredictionsStore } from 'src/stores/predictions';

Chart.register(...registerables);

type Priority = 'high' | 'medium' | 'low';

type RiskAction = string | { text?: unknown; priority?: unknown };

export type RiskAssessmentCardData = {
  overall_risk?: string | null;
  confidence?: number | null;
  chi_square?: number | null;
  p_value?: number | null;
  recommended_actions?: RiskAction[] | null;
};

const props = defineProps<{
  risk?: RiskAssessmentCardData | null;
}>();

const $q = useQuasar();
const predictionsStore = usePredictionsStore();

const fallbackRisk: RiskAssessmentCardData = {
  overall_risk: 'moderate',
  confidence: 78.4,
  chi_square: 8.342,
  p_value: 0.0502,
  recommended_actions: [
    { text: 'Follow-up within 24–48 hours.', priority: 'High' },
    { text: 'Review recent trends and symptom changes.', priority: 'Medium' },
    { text: 'Consider preventive screening for high-risk patients.', priority: 'Low' },
  ],
};

const risk = computed(() => props.risk || fallbackRisk);

const canEdit = computed(() => !predictionsStore.isUpdating);

const toConfidencePct = (raw: unknown): number | null => {
  if (typeof raw !== 'number' || !Number.isFinite(raw)) return null;
  if (raw >= 0 && raw <= 1) return raw * 100;
  return raw;
};

const normalizeOverallRisk = (raw: unknown): Priority | null => {
  if (typeof raw !== 'string') return null;
  const v = raw.trim().toLowerCase();
  if (v.includes('high')) return 'high';
  if (v.includes('medium') || v.includes('moderate')) return 'medium';
  if (v.includes('low')) return 'low';
  return null;
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

const actionItems = computed(() => {
  const raw = risk.value.recommended_actions;
  const list = Array.isArray(raw) ? raw : [];
  return list
    .map((a, idx) => {
      if (typeof a === 'string') {
        const text = a.trim();
        if (!text) return null;
        const priority = categorizePriority(text);
        return { key: `${idx}:${priority}:${text}`, text, ...priorityVisual(priority) };
      }
      if (isActionObj(a)) {
        const rawText = a.text;
        const text = typeof rawText === 'string' ? rawText.trim() : '';
        if (!text) return null;
        const pr = normalizePriority(a.priority);
        const priority = pr || categorizePriority(text);
        return { key: `${idx}:${priority}:${text}`, text, ...priorityVisual(priority) };
      }
      return null;
    })
    .filter((x): x is NonNullable<typeof x> => Boolean(x));
});

const riskSplit = computed(() => {
  const pct = toConfidencePct(risk.value.confidence);
  const p = pct != null ? Math.max(0, Math.min(100, pct)) : 0;
  const tier = normalizeOverallRisk(risk.value.overall_risk);
  const rest = 100 - p;
  if (tier === 'high') return { low: rest * 0.35, medium: rest * 0.25, high: p };
  if (tier === 'low') return { low: p, medium: rest * 0.3, high: rest * 0.7 };
  return { low: rest * 0.35, medium: p, high: rest * 0.65 };
});

const donutCanvas = ref<HTMLCanvasElement | null>(null);
let donutChart: Chart | null = null;

const renderDonut = () => {
  if (!donutCanvas.value) return;
  const ctx = donutCanvas.value.getContext('2d');
  if (!ctx) return;

  if (donutChart) {
    donutChart.destroy();
    donutChart = null;
  }

  const split = riskSplit.value;
  donutChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Low', 'Medium', 'High'],
      datasets: [
        {
          data: [split.low, split.medium, split.high],
          backgroundColor: ['rgba(34, 197, 94, 0.8)', 'rgba(245, 158, 11, 0.85)', 'rgba(239, 68, 68, 0.85)'],
          borderColor: ['#ffffff', '#ffffff', '#ffffff'],
          borderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '70%',
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (c) => {
              const label = String(c.label || 'Tier');
              const v = typeof c.parsed === 'number' ? c.parsed : Number(c.parsed);
              return Number.isFinite(v) ? `${label}: ${v.toFixed(1)}%` : `${label}: N/A`;
            },
          },
        },
      },
    },
  });
};

watch(riskSplit, async () => {
  await nextTick();
  renderDonut();
});

onMounted(() => {
  renderDonut();
});

onUnmounted(() => {
  if (donutChart) {
    donutChart.destroy();
    donutChart = null;
  }
});

const editOpen = ref(false);
const editOverallRisk = ref<string>('moderate');
const editConfidence = ref<number | null>(null);
const editActionsText = ref<string>('');

const overallRiskOptions = [
  { label: 'Low', value: 'low' },
  { label: 'Moderate', value: 'moderate' },
  { label: 'High', value: 'high' },
];

const actionLinesFromState = (actions: RiskAction[] | null | undefined): string => {
  const list = Array.isArray(actions) ? actions : [];
  const out: string[] = [];
  for (const a of list) {
    if (typeof a === 'string') {
      const t = a.trim();
      if (t) out.push(t);
      continue;
    }
    if (isActionObj(a)) {
      const text = typeof a.text === 'string' ? a.text.trim() : '';
      if (!text) continue;
      const pr = normalizePriority(a.priority);
      if (!pr) out.push(text);
      else out.push(`${pr === 'high' ? 'High' : pr === 'medium' ? 'Medium' : 'Low'}: ${text}`);
    }
  }
  return out.join('\n');
};

const openEdit = () => {
  const r = predictionsStore.riskAssessment || risk.value;
  editOverallRisk.value = typeof r?.overall_risk === 'string' ? r.overall_risk : 'moderate';
  editConfidence.value = toConfidencePct(r?.confidence) ?? null;
  editActionsText.value = actionLinesFromState(r?.recommended_actions);
  editOpen.value = true;
};

const parseActionsText = (raw: string): Array<{ text: string; priority?: 'High' | 'Medium' | 'Low' | null }> => {
  const lines = String(raw || '')
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);
  const out: Array<{ text: string; priority?: 'High' | 'Medium' | 'Low' | null }> = [];
  for (const line of lines) {
    const m = line.match(/^(high|medium|low)\s*:\s*(.+)$/i);
    if (m) {
      const pr = String(m[1] || '').toLowerCase();
      const text = String(m[2] || '').trim();
      if (!text) continue;
      out.push({
        text,
        priority: pr === 'high' ? 'High' : pr === 'medium' ? 'Medium' : 'Low',
      });
      continue;
    }
    out.push({ text: line });
  }
  return out;
};

const saveEdit = async () => {
  const nextConfidence = typeof editConfidence.value === 'number' && Number.isFinite(editConfidence.value)
    ? Math.max(0, Math.min(100, editConfidence.value))
    : null;

  const next = {
    overall_risk: String(editOverallRisk.value || '').trim() || null,
    confidence: nextConfidence,
    chi_square: predictionsStore.riskAssessment?.chi_square ?? null,
    p_value: predictionsStore.riskAssessment?.p_value ?? null,
    recommended_actions: parseActionsText(editActionsText.value),
  };

  await predictionsStore.updateRiskAssessment(next);

  if (predictionsStore.conflict) {
    const who = predictionsStore.conflict.updatedByRole || 'another role';
    $q.notify({
      type: 'warning',
      message: `Conflict detected. Latest saved by ${who}.`,
      position: 'top',
      timeout: 3500,
    });
    return;
  }

  if (predictionsStore.error) {
    $q.notify({
      type: 'negative',
      message: predictionsStore.error,
      position: 'top',
      timeout: 3000,
    });
    return;
  }

  editOpen.value = false;
  $q.notify({
    type: 'positive',
    message: 'Risk Assessment updated.',
    position: 'top',
    timeout: 2000,
  });
};
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
  justify-content: space-between;
  gap: 10px;
}

.risk-card__title {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.2px;
  color: #0f172a;
  text-transform: none;
}

.risk-card__edit {
  color: #64748b;
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
  position: relative;
}

.risk-card__donut-canvas {
  width: 112px;
  height: 112px;
  display: block;
}

.risk-card__donut-center {
  position: absolute;
  inset: 50% auto auto 50%;
  transform: translate(-50%, -50%);
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
  pointer-events: none;
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
</style>
