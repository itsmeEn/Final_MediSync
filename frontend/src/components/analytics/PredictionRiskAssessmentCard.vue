<template>
  <q-card class="analytics-panel integrated-card themed-card">
    <q-card-section>
      <div class="row items-center justify-between q-mb-sm">
        <div class="integrated-card-title">Risk Assessment</div>
        <q-chip v-if="confidenceBadge" :color="confidenceBadge.color" text-color="white" dense>
          {{ confidenceBadge.label }}
        </q-chip>
      </div>

      <div class="row items-center q-gutter-sm q-mb-sm">
        <div class="text-subtitle2">Confidence</div>
        <div class="text-subtitle2 text-weight-medium">{{ confidenceText }}</div>
        <q-space />
        <q-icon name="info" size="18px" class="cursor-pointer text-grey-7" />
        <q-tooltip>{{ methodologyNote }}</q-tooltip>
      </div>

      <q-linear-progress
        v-if="typeof risk?.overall_confidence === 'number'"
        :value="Math.max(0, Math.min(1, risk.overall_confidence / 100))"
        rounded
        size="10px"
        :color="confidenceBadge?.color || 'primary'"
        class="q-mb-md"
        aria-label="Overall confidence level"
      />

      <div class="row q-col-gutter-md q-mb-md">
        <div class="col-12 col-md-4">
          <div class="metric-card">
            <div class="metric-label">Risk Tier</div>
            <div class="metric-value">{{ risk?.risk_tier || 'N/A' }}</div>
          </div>
        </div>
        <div class="col-12 col-md-4">
          <div class="metric-card">
            <div class="metric-label">Risk Score</div>
            <div class="metric-value">{{ typeof risk?.risk_score === 'number' ? `${risk.risk_score.toFixed(1)} / 100` : 'N/A' }}</div>
          </div>
        </div>
        <div class="col-12 col-md-4">
          <div class="metric-card">
            <div class="metric-label">Confidence Rating</div>
            <div class="metric-value">{{ risk?.overall_confidence_rating || 'N/A' }}</div>
          </div>
        </div>
      </div>

      <div class="row q-col-gutter-md">
        <div class="col-12 col-md-6">
          <div class="chart-title">Risk Trend (APE%)</div>
          <div class="chart-box">
            <canvas ref="trendCanvas" aria-label="Risk trend line chart" role="img"></canvas>
          </div>
          <div class="sr-only">{{ trendAltText }}</div>
        </div>

        <div class="col-12 col-md-6">
          <div class="chart-title">Confidence Distribution (APE Histogram)</div>
          <div class="chart-box">
            <canvas ref="histCanvas" aria-label="Confidence distribution histogram" role="img"></canvas>
          </div>
          <div class="sr-only">{{ histAltText }}</div>
        </div>
      </div>

      <div class="q-mt-md">
        <div class="chart-title">Risk Severity Heatmap (per prediction point)</div>
        <div class="heatmap" role="table" aria-label="Risk severity heatmap">
          <div class="heatmap-row heatmap-header" role="row">
            <div class="heatmap-cell heatmap-corner" role="columnheader"></div>
            <div
              v-for="x in heatmap.x_labels"
              :key="x"
              class="heatmap-cell heatmap-col"
              role="columnheader"
            >
              {{ x }}
            </div>
          </div>
          <div v-for="(y, yi) in heatmap.y_labels" :key="y" class="heatmap-row" role="row">
            <div class="heatmap-cell heatmap-rowlabel" role="rowheader">{{ y }}</div>
            <div
              v-for="(x, xi) in heatmap.x_labels"
              :key="`${y}:${x}`"
              class="heatmap-cell"
              role="cell"
              :style="{ backgroundColor: heatColor(heatmap.values[yi]?.[xi] || 0, y) }"
            >
              <q-tooltip>
                {{ y }} at {{ x }}: {{ (heatmap.values[yi]?.[xi] || 0) ? 'Yes' : 'No' }}
              </q-tooltip>
            </div>
          </div>
        </div>
        <div class="sr-only">{{ heatmapAltText }}</div>
      </div>

      <div class="q-mt-md">
        <div class="text-subtitle2 text-weight-medium q-mb-xs">Drivers</div>
        <ul class="list">
          <li v-for="f in (risk?.factors || [])" :key="f">{{ f }}</li>
          <li v-if="!risk?.factors?.length">No driver metadata available.</li>
        </ul>
      </div>

      <div class="q-mt-md">
        <div class="text-subtitle2 text-weight-medium q-mb-xs">Recommended Actions</div>
        <ul class="list">
          <li v-for="a in (risk?.recommended_actions || [])" :key="a">{{ a }}</li>
          <li v-if="!risk?.recommended_actions?.length">No recommendations available.</li>
        </ul>
      </div>
    </q-card-section>
  </q-card>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import { Chart, registerables } from 'chart.js';

Chart.register(...registerables);

type Heatmap = {
  x_labels: string[];
  y_labels: string[];
  values: number[][];
};

type RiskAssessment = {
  overall_confidence?: number | null;
  overall_confidence_rating?: string | null;
  risk_score?: number | null;
  risk_tier?: string | null;
  factors?: string[];
  recommended_actions?: string[];
  risk_trend?: Array<{
    date?: string | null;
    absolute_percentage_error?: number | null;
    point_confidence?: number | null;
    point_confidence_rating?: string | null;
  }>;
  confidence_histogram?: Array<{ label: string; count: number }>;
  risk_severity_heatmap?: Heatmap;
};

const props = defineProps<{
  risk: RiskAssessment | null;
  methodologyNote: string;
}>();

const trendCanvas = ref<HTMLCanvasElement | null>(null);
const histCanvas = ref<HTMLCanvasElement | null>(null);
let trendChart: Chart | null = null;
let histChart: Chart | null = null;

const confidenceBadge = computed(() => {
  const rating = (props.risk?.overall_confidence_rating || '').toLowerCase();
  if (rating === 'high') return { label: 'High Confidence', color: 'positive' as const };
  if (rating === 'medium') return { label: 'Medium Confidence', color: 'warning' as const };
  if (rating === 'low') return { label: 'Low Confidence', color: 'negative' as const };
  return null;
});

const confidenceText = computed(() => {
  const v = props.risk?.overall_confidence;
  const rating = props.risk?.overall_confidence_rating;
  if (typeof v === 'number' && Number.isFinite(v)) return `${v.toFixed(1)}% (${rating || 'N/A'})`;
  return 'N/A';
});

const heatmap = computed<Heatmap>(() => {
  const hm = props.risk?.risk_severity_heatmap;
  if (hm && Array.isArray(hm.x_labels) && Array.isArray(hm.y_labels) && Array.isArray(hm.values)) return hm;
  return { x_labels: [], y_labels: [], values: [] };
});

const heatColor = (v: number, yLabel: string) => {
  if (!v) return 'rgba(243, 244, 246, 1)';
  const y = yLabel.toLowerCase();
  if (y === 'high') return 'rgba(239, 68, 68, 0.35)';
  if (y === 'medium') return 'rgba(245, 158, 11, 0.35)';
  return 'rgba(34, 197, 94, 0.35)';
};

const trendAltText = computed(() => {
  const pts = props.risk?.risk_trend || [];
  if (!pts.length) return 'Risk trend chart unavailable.';
  const last = pts[pts.length - 1];
  return `Risk trend over ${pts.length} points. Latest APE is ${last?.absolute_percentage_error ?? 'N/A'}%.`;
});

const histAltText = computed(() => {
  const bins = props.risk?.confidence_histogram || [];
  if (!bins.length) return 'Confidence distribution histogram unavailable.';
  const top = bins.slice().sort((a, b) => b.count - a.count)[0];
  return `Histogram distribution across ${bins.length} bins. Largest bin is ${top?.label} with ${top?.count ?? 0} points.`;
});

const heatmapAltText = computed(() => {
  const hm = heatmap.value;
  if (!hm.x_labels.length || !hm.y_labels.length) return 'Risk severity heatmap unavailable.';
  return `Heatmap with ${hm.y_labels.length} severity rows across ${hm.x_labels.length} prediction points.`;
});

const createTrendChart = () => {
  if (!trendCanvas.value) return;
  const ctx = trendCanvas.value.getContext('2d');
  if (!ctx) return;
  if (trendChart) {
    trendChart.destroy();
    trendChart = null;
  }

  const pts = (props.risk?.risk_trend || []).filter((p) => typeof p.date === 'string');
  const labels = pts.map((p) => String(p.date));
  const ape = pts.map((p) => (typeof p.absolute_percentage_error === 'number' ? p.absolute_percentage_error : null));
  const conf = pts.map((p) => (typeof p.point_confidence === 'number' ? p.point_confidence : null));

  trendChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'APE (%)',
          data: ape,
          borderColor: 'rgba(239, 68, 68, 1)',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          borderWidth: 2,
          fill: false,
          tension: 0.35,
          pointRadius: 3,
        },
        {
          label: 'Point Confidence (%)',
          data: conf,
          borderColor: 'rgba(33, 150, 243, 1)',
          backgroundColor: 'rgba(33, 150, 243, 0.1)',
          borderWidth: 2,
          fill: false,
          tension: 0.35,
          pointRadius: 3,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { position: 'bottom' },
        tooltip: {
          callbacks: {
            label: (c) => {
              const label = c.dataset?.label || 'Value';
              const y = c.parsed?.y;
              return typeof y === 'number' && Number.isFinite(y) ? `${label}: ${y.toFixed(2)}` : `${label}: N/A`;
            },
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { callback: (v) => String(v) },
        },
      },
    },
  });
};

const createHistChart = () => {
  if (!histCanvas.value) return;
  const ctx = histCanvas.value.getContext('2d');
  if (!ctx) return;
  if (histChart) {
    histChart.destroy();
    histChart = null;
  }

  const bins = props.risk?.confidence_histogram || [];
  const labels = bins.map((b) => b.label);
  const counts = bins.map((b) => b.count);

  histChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Count',
          data: counts,
          backgroundColor: 'rgba(33, 150, 243, 0.25)',
          borderColor: 'rgba(33, 150, 243, 1)',
          borderWidth: 1,
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
            label: (c) => {
              const y = c.parsed?.y;
              return typeof y === 'number' && Number.isFinite(y) ? `Count: ${y}` : 'Count: N/A';
            },
          },
        },
      },
      scales: {
        y: { beginAtZero: true, ticks: { precision: 0 } },
      },
    },
  });
};

const refreshCharts = async () => {
  await nextTick();
  createTrendChart();
  createHistChart();
};

watch(
  () => props.risk,
  async () => {
    await refreshCharts();
  },
  { deep: true }
);

onMounted(() => {
  void refreshCharts();
});

onUnmounted(() => {
  if (trendChart) {
    trendChart.destroy();
    trendChart = null;
  }
  if (histChart) {
    histChart.destroy();
    histChart = null;
  }
});
</script>

<style scoped>
.chart-box {
  position: relative;
  height: 220px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 10px;
  background: #ffffff;
}

.chart-title {
  font-weight: 700;
  color: #374151;
  margin-bottom: 8px;
}

.metric-card {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 12px;
  background: #ffffff;
  text-align: center;
}

.metric-label {
  font-size: 12px;
  color: #6b7280;
  font-weight: 600;
}

.metric-value {
  font-size: 18px;
  color: #111827;
  font-weight: 800;
  margin-top: 4px;
}

.list {
  margin: 0;
  padding-left: 18px;
}

.heatmap {
  overflow-x: auto;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #ffffff;
}

.heatmap-row {
  display: grid;
  grid-template-columns: 120px repeat(auto-fit, minmax(64px, 1fr));
}

.heatmap-header {
  position: sticky;
  top: 0;
  background: #f9fafb;
  z-index: 1;
}

.heatmap-cell {
  border-right: 1px solid #e5e7eb;
  border-bottom: 1px solid #e5e7eb;
  padding: 10px 8px;
  text-align: center;
  font-size: 12px;
  color: #374151;
  min-height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.heatmap-rowlabel {
  font-weight: 700;
  background: #f9fafb;
}

.heatmap-col {
  font-weight: 700;
  background: #f9fafb;
}

.heatmap-corner {
  background: #f9fafb;
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
  border: 0;
}
</style>
