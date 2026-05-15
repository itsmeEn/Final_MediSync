<template>
  <div class="risk-layer-grid">
    <q-card class="analytics-panel integrated-card themed-card risk-card">
      <q-card-section>
        <div class="card-header">
          <div>
            <div class="integrated-card-title">Patient demographics</div>
            <div class="card-subtitle">Age distribution &amp; gender breakdown</div>
          </div>
        </div>
        <div class="demographics-split">
          <div class="placeholder-chart">
            <div class="chart-shell" role="img" aria-label="Patient demographics bar chart">
              <canvas ref="demographicsBarCanvas" class="chart-canvas" />
            </div>
            <div class="sr-only">
              Age groups: {{ ageGroupsText }}
            </div>
          </div>
          <div class="donut-chart">
            <div class="chart-shell" role="img" aria-label="Gender proportions donut chart">
              <canvas ref="genderDonutCanvas" class="chart-canvas" />
            </div>
            <div class="legend">
              <div v-for="item in genderLegend" :key="item.label" class="legend-row">
                <span class="dot" :style="{ backgroundColor: item.color }" aria-hidden="true" />
                <span class="legend-label">{{ item.label }}</span>
                <span class="legend-value">{{ item.value }}%</span>
              </div>
            </div>
            <div class="sr-only">
              Gender proportions: {{ genderText }}
            </div>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <div class="right-stack">
      <q-card class="analytics-panel integrated-card themed-card risk-card">
        <q-card-section>
          <div class="card-header">
            <div>
              <div class="integrated-card-title">Risk assessment</div>
              <div class="card-subtitle">
                Overall risk: {{ riskLabelLower }} - {{ riskConfidence.toFixed(2) }}% confidence
              </div>
            </div>
            <div class="row items-center q-gutter-xs">
              <q-chip :color="confidenceChip.color" text-color="white" dense>
                {{ confidenceChip.label }}
              </q-chip>
              <q-icon name="info" size="18px" class="cursor-pointer text-grey-7" />
              <q-tooltip>{{ methodologyNote }}</q-tooltip>
            </div>
          </div>

          <div class="risk-content">
            <div class="risk-gauge">
              <div class="chart-shell gauge-shell" role="img" aria-label="AI risk level semi-circle chart">
                <canvas ref="riskGaugeCanvas" class="chart-canvas" />
              </div>
              <div class="gauge-meta">
                <div class="gauge-title">AI risk level</div>
                <div class="gauge-score">{{ Math.round(riskScore) }}%</div>
              </div>
              <div class="sr-only">
                AI risk level is {{ Math.round(riskScore) }} percent with confidence {{ riskConfidence }} percent.
              </div>
            </div>

            <div class="recommended">
              <div class="recommended-title">Recommended action</div>
              <div class="recommended-text">
                {{ recommendedAction }}
              </div>
              <div class="recommended-meta">
                <div class="meta-row">
                  <span class="meta-label">Chi-Square</span>
                  <span class="meta-value">{{ chiSquare.toFixed(2) }}</span>
                </div>
                <div class="meta-row">
                  <span class="meta-label">P-value</span>
                  <span class="meta-value">{{ pValue.toFixed(4) }}</span>
                </div>
              </div>
            </div>
          </div>
        </q-card-section>
      </q-card>

      <q-card class="analytics-panel integrated-card themed-card suggestions-card">
        <q-card-section>
          <div class="card-header">
            <div>
              <div class="integrated-card-title">AI suggestions</div>
              <div class="card-subtitle">Role-specific recommendations</div>
            </div>
          </div>

          <div class="suggestions">
            <div v-for="group in suggestionGroups" :key="group.key" class="suggestion-group">
              <div class="group-title">
                <span class="dot" :style="{ backgroundColor: group.color }" aria-hidden="true" />
                <span class="group-label">{{ group.label }}</span>
              </div>
              <ul class="group-list">
                <li v-for="item in group.items" :key="item" class="group-item">
                  {{ item }}
                </li>
              </ul>
            </div>
          </div>
        </q-card-section>
      </q-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { Chart, registerables } from 'chart.js';

Chart.register(...registerables);

type RiskData = {
  confidence: number;
  risk_score: number;
  recommended_action: string;
  chi_square: number;
  p_value: number;
  demographics: {
    age_groups: Array<{ label: string; value: number }>;
    gender: Array<{ label: string; value: number; color: string }>;
  };
  ai_suggestions: {
    high: string[];
    medium: string[];
    low: string[];
  };
  methodology_note: string;
};

const sampleRiskData: RiskData = {
  confidence: 78.4,
  risk_score: 66,
  recommended_action:
    'Follow-up within 24-48 hours and review trends. Consider preventive screening for high-risk patients.',
  chi_square: 3.842,
  p_value: 0.0502,
  demographics: {
    age_groups: [
      { label: '0-18', value: 12 },
      { label: '19-35', value: 38 },
      { label: '36-50', value: 27 },
      { label: '51-65', value: 22 },
      { label: '65+', value: 16 },
    ],
    gender: [
      { label: 'Male', value: 54, color: '#3b82f6' },
      { label: 'Female', value: 44, color: '#ef4444' },
      { label: 'Other', value: 2, color: '#22c55e' },
    ],
  },
  ai_suggestions: {
    high: ['Schedule immediate cardiac screening for flagged patients', 'Review medication compliance in hypertension cohort'],
    medium: ['Increase follow-up frequency for diabetic patients', 'Coordinate with nursing team on post-discharge monitoring'],
    low: ['Update patient education materials on preventive care'],
  },
  methodology_note:
    'Confidence levels are validated against a 30% hold-out test set to ensure prediction legitimacy and clinical transparency.',
};

const props = defineProps<{ riskData?: RiskData }>();
const riskData = computed(() => props.riskData || sampleRiskData);

const riskConfidence = computed(() => {
  const n = Number(riskData.value.confidence);
  if (!Number.isFinite(n)) return 0;
  return Math.max(0, Math.min(100, n));
});

const riskScore = computed(() => {
  const n = Number(riskData.value.risk_score);
  if (!Number.isFinite(n)) return 0;
  return Math.max(0, Math.min(100, n));
});

const confidenceChip = computed(() => {
  const c = riskConfidence.value;
  if (c > 70) return { label: 'High', color: 'positive' as const };
  if (c >= 40) return { label: 'Medium', color: 'warning' as const };
  return { label: 'Low', color: 'negative' as const };
});

const riskLabelLower = computed(() => {
  const s = riskScore.value;
  if (s >= 70) return 'high';
  if (s >= 40) return 'moderate';
  return 'low';
});

const recommendedAction = computed(() => String(riskData.value.recommended_action || '').trim() || 'No recommendation available.');
const chiSquare = computed(() => Number(riskData.value.chi_square) || 0);
const pValue = computed(() => Number(riskData.value.p_value) || 0);
const methodologyNote = computed(() => String(riskData.value.methodology_note || '').trim() || sampleRiskData.methodology_note);

const genderLegend = computed(() => riskData.value.demographics.gender);
const ageGroupsText = computed(() => riskData.value.demographics.age_groups.map((a) => `${a.label}=${a.value}`).join(', '));
const genderText = computed(() => riskData.value.demographics.gender.map((g) => `${g.label}=${g.value}%`).join(', '));

const suggestionGroups = computed(() => [
  { key: 'high', label: 'High priority', color: '#ef4444', items: riskData.value.ai_suggestions.high || [] },
  { key: 'medium', label: 'Medium priority', color: '#f59e0b', items: riskData.value.ai_suggestions.medium || [] },
  { key: 'low', label: 'Low priority', color: '#22c55e', items: riskData.value.ai_suggestions.low || [] },
]);

const demographicsBarCanvas = ref<HTMLCanvasElement | null>(null);
const genderDonutCanvas = ref<HTMLCanvasElement | null>(null);
const riskGaugeCanvas = ref<HTMLCanvasElement | null>(null);

let demographicsBarChart: Chart | null = null;
let genderDonutChart: Chart | null = null;
let riskGaugeChart: Chart | null = null;

const buildDemographicsBar = () => {
  if (!demographicsBarCanvas.value) return;
  demographicsBarChart?.destroy();
  demographicsBarChart = null;
  const ctx = demographicsBarCanvas.value.getContext('2d');
  if (!ctx) return;

  const labels = riskData.value.demographics.age_groups.map((a) => a.label);
  const values = riskData.value.demographics.age_groups.map((a) => a.value);

  demographicsBarChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Patients',
          data: values,
          backgroundColor: 'rgba(59, 130, 246, 0.35)',
          borderColor: 'rgba(59, 130, 246, 0.9)',
          borderWidth: 1,
          borderRadius: 8,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (t) => {
              const v = typeof t.parsed?.y === 'number' ? t.parsed.y : null;
              return v != null ? `Patients: ${v}` : 'Patients: N/A';
            },
          },
        },
      },
      scales: {
        x: { grid: { display: false } },
        y: {
          beginAtZero: true,
          ticks: { precision: 0 },
          grid: { color: 'rgba(0,0,0,0.06)' },
        },
      },
    },
  });
};

const buildGenderDonut = () => {
  if (!genderDonutCanvas.value) return;
  genderDonutChart?.destroy();
  genderDonutChart = null;
  const ctx = genderDonutCanvas.value.getContext('2d');
  if (!ctx) return;

  const labels = riskData.value.demographics.gender.map((g) => g.label);
  const values = riskData.value.demographics.gender.map((g) => g.value);
  const colors = riskData.value.demographics.gender.map((g) => g.color);

  genderDonutChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [
        {
          data: values,
          backgroundColor: colors,
          borderWidth: 0,
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
            label: (t) => {
              const label = String(t.label || 'Value');
              const v = typeof t.parsed === 'number' ? t.parsed : null;
              return v != null ? `${label}: ${v}%` : `${label}: N/A`;
            },
          },
        },
      },
    },
  });
};

const buildRiskGauge = () => {
  if (!riskGaugeCanvas.value) return;
  riskGaugeChart?.destroy();
  riskGaugeChart = null;
  const ctx = riskGaugeCanvas.value.getContext('2d');
  if (!ctx) return;

  const score = riskScore.value;
  const remaining = Math.max(0, 100 - score);

  const color = score >= 70 ? '#ef4444' : score >= 40 ? '#f59e0b' : '#22c55e';

  riskGaugeChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Risk', 'Remaining'],
      datasets: [
        {
          data: [score, remaining],
          backgroundColor: [color, 'rgba(148, 163, 184, 0.35)'],
          borderWidth: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      rotation: -90,
      circumference: 180,
      cutout: '72%',
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (t) => {
              const label = String(t.label || 'Value');
              const v = typeof t.parsed === 'number' ? t.parsed : null;
              return v != null ? `${label}: ${v.toFixed(1)}%` : `${label}: N/A`;
            },
          },
        },
      },
    },
  });
};

const rebuildAll = () => {
  buildDemographicsBar();
  buildGenderDonut();
  buildRiskGauge();
};

onMounted(() => {
  rebuildAll();
});

watch(
  () => riskData.value,
  () => {
    rebuildAll();
  },
  { deep: true }
);

onUnmounted(() => {
  demographicsBarChart?.destroy();
  genderDonutChart?.destroy();
  riskGaugeChart?.destroy();
  demographicsBarChart = null;
  genderDonutChart = null;
  riskGaugeChart = null;
});
</script>

<style scoped>
.analytics-panel {
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  color: #0f172a;
}

.analytics-panel :deep(.q-card__section) {
  padding: 24px;
}

.risk-layer-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  align-items: start;
}

.right-stack {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.risk-card {
  min-height: 290px;
}

.suggestions-card {
  min-height: 290px;
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.card-subtitle {
  font-size: 12px;
  color: #64748b;
}

.demographics-split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.chart-shell {
  position: relative;
  height: 170px;
  border-radius: 12px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  overflow: hidden;
}

.chart-canvas {
  width: 100%;
  height: 100%;
}

.donut-chart {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.legend {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 0 2px;
}

.legend-row {
  display: grid;
  grid-template-columns: 14px 1fr auto;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #0f172a;
}

.legend-label {
  opacity: 0.9;
}

.legend-value {
  color: #64748b;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  display: inline-block;
}

.risk-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  align-items: start;
}

.gauge-shell {
  height: 160px;
}

.risk-gauge {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.gauge-meta {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 0 2px;
}

.gauge-title {
  font-size: 12px;
  color: #64748b;
}

.gauge-score {
  font-size: 20px;
  font-weight: 800;
  color: #0f172a;
}

.recommended {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
}

.recommended-title {
  font-size: 12px;
  font-weight: 700;
  color: #0f172a;
}

.recommended-text {
  font-size: 12px;
  color: #334155;
  line-height: 1.4;
}

.recommended-meta {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 2px;
}

.meta-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

.meta-label {
  color: #64748b;
}

.meta-value {
  color: #0f172a;
  font-weight: 700;
}

.suggestions {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.group-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 6px;
}

.group-list {
  margin: 0;
  padding-left: 16px;
  color: #334155;
  font-size: 12px;
  line-height: 1.5;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}

@media (max-width: 1200px) {
  .risk-layer-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .demographics-split {
    grid-template-columns: 1fr;
  }
  .risk-content {
    grid-template-columns: 1fr;
  }
}
</style>
