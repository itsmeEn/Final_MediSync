<template>
  <div class="patient-volume">
    <AnalyticsChartContainer>
      <canvas ref="canvasEl" width="400" height="200"></canvas>
    </AnalyticsChartContainer>
    <div class="summary-stats q-mt-sm">
      <div class="stat-item">
        <span class="stat-label">Predicted Volume (latest)</span>
        <span class="stat-value">{{ latestVolumeOutput.predicted != null ? formatNumber(latestVolumeOutput.predicted) : 'N/A' }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">Actual Volume (latest)</span>
        <span class="stat-value">{{ latestVolumeOutput.actual != null ? formatNumber(latestVolumeOutput.actual) : 'N/A' }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import AnalyticsChartContainer from 'src/components/analytics/AnalyticsChartContainer.vue';
import { Chart, registerables } from 'chart.js';

Chart.register(...registerables);

type ForecastPoint = {
  date: string;
  predicted_volume: number | string;
  actual_volume?: number | string | null;
  ci_lower?: number | string | null;
  ci_upper?: number | string | null;
  point_confidence?: number | string | null;
  point_confidence_rating?: string | null;
};

const props = defineProps<{
  forecastedData: ForecastPoint[];
}>();

const formatNumber = (n: number) => new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(n);
const toNum = (v: unknown): number => {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
};

const formatMonthYear = (raw: string) => {
  const s = String(raw || '').trim();
  const m = s.match(/^(\d{4})-(\d{2})/);
  if (!m) return s;
  const year = Number(m[1]);
  const month = Number(m[2]);
  if (!Number.isFinite(year) || !Number.isFinite(month) || month < 1 || month > 12) return s;
  const dt = new Date(Date.UTC(year, month - 1, 1));
  return new Intl.DateTimeFormat('en-US', { month: 'long', year: 'numeric' }).format(dt);
};

const latestVolumeOutput = computed(() => {
  const vp = props.forecastedData;
  if (Array.isArray(vp) && vp.length > 0) {
    const last = vp[vp.length - 1]!;
    const predicted = toNum(last.predicted_volume);
    const actual = last.actual_volume !== undefined && last.actual_volume !== null && Number.isFinite(Number(last.actual_volume))
      ? Number(last.actual_volume)
      : null;
    return { label: formatMonthYear(last.date), predicted, actual };
  }
  return { label: null, predicted: null, actual: null };
});

const canvasEl = ref<HTMLCanvasElement | null>(null);
let chartInstance: Chart | null = null;

const buildDatasets = (forecastedData: ForecastPoint[]) => {
  if (Array.isArray(forecastedData) && forecastedData.length > 0) {
    const labels = forecastedData.map((item) => formatMonthYear(item.date));
    const predicted = forecastedData.map((item) => toNum(item.predicted_volume));
    const actual = forecastedData.map((item) =>
      item.actual_volume !== undefined && item.actual_volume !== null && Number.isFinite(Number(item.actual_volume))
        ? Number(item.actual_volume)
        : NaN
    );
    const lower = forecastedData.map((item) =>
      item.ci_lower !== undefined && item.ci_lower !== null && Number.isFinite(Number(item.ci_lower))
        ? Number(item.ci_lower)
        : NaN
    );
    const upper = forecastedData.map((item) =>
      item.ci_upper !== undefined && item.ci_upper !== null && Number.isFinite(Number(item.ci_upper))
        ? Number(item.ci_upper)
        : NaN
    );
    const hasBand = lower.some((v) => Number.isFinite(v)) && upper.some((v) => Number.isFinite(v));
    return { labels, predicted, actual, lower, upper, hasBand };
  }

  const labels = [
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
  ];
  const predicted = [45, 52, 48, 55, 60, 58, 62, 59, 57, 54, 50, 47];
  const actual = [42, 50, 46, 52, 58, 56, 60, 57, 55, 52, 48, 45];
  return { labels, predicted, actual, lower: [], upper: [], hasBand: false };
};

const createChart = () => {
  if (!canvasEl.value) return;

  if (chartInstance) {
    chartInstance.destroy();
    chartInstance = null;
  }

  const ctx = canvasEl.value.getContext('2d');
  if (!ctx) return;

  const { labels, predicted, actual, lower, upper, hasBand } = buildDatasets(props.forecastedData);

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        ...(hasBand
          ? [
              {
                label: 'CI Lower (95%)',
                data: lower,
                borderColor: 'rgba(33, 150, 243, 0)',
                backgroundColor: 'rgba(33, 150, 243, 0)',
                pointRadius: 0,
                borderWidth: 0,
                fill: false,
                tension: 0.4,
              },
              {
                label: 'Confidence Band (95%)',
                data: upper,
                borderColor: 'rgba(33, 150, 243, 0)',
                backgroundColor: 'rgba(33, 150, 243, 0.18)',
                pointRadius: 0,
                borderWidth: 0,
                fill: '-1',
                tension: 0.4,
              },
            ]
          : []),
        {
          label: 'Predicted Volume (Projection)',
          data: predicted,
          borderColor: 'rgba(33, 150, 243, 1)',
          backgroundColor: 'rgba(33, 150, 243, 0.1)',
          borderWidth: 2,
          fill: false,
          tension: 0.4,
          pointRadius: 4,
          pointBackgroundColor: 'rgba(33, 150, 243, 1)',
          borderDash: [6, 4],
          pointStyle: 'triangle',
        },
        {
          label: 'Actual Volume (Current)',
          data: actual,
          borderColor: 'rgba(76, 175, 80, 1)',
          backgroundColor: 'rgba(76, 175, 80, 0.1)',
          borderWidth: 2,
          fill: false,
          tension: 0.4,
          pointRadius: 4,
          pointBackgroundColor: 'rgba(76, 175, 80, 1)',
          pointStyle: 'circle',
          spanGaps: true,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false,
      },
      plugins: {
        title: {
          display: true,
          text: 'Patient Volume: Actual vs Predicted',
        },
        legend: {
          display: true,
          position: 'bottom',
        },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const label = ctx.dataset?.label || 'Value';
              const y = ctx.parsed?.y;
              const base = typeof y === 'number' && Number.isFinite(y) ? `${label}: ${formatNumber(y)}` : `${label}: N/A`;
              if (!Array.isArray(props.forecastedData) || !props.forecastedData.length) return base;
              if (label !== 'Predicted Volume (Projection)') return base;
              const pt = props.forecastedData[ctx.dataIndex];
              const lo = pt?.ci_lower;
              const hi = pt?.ci_upper;
              const extra: string[] = [base];
              const pcRaw = pt?.point_confidence;
              const pc = pcRaw != null && Number.isFinite(Number(pcRaw)) ? Number(pcRaw) : null;
              const pcLabel = typeof pt?.point_confidence_rating === 'string' ? pt?.point_confidence_rating : null;
              if (pc != null) extra.push(`Confidence: ${pc.toFixed(1)}%${pcLabel ? ` (${pcLabel})` : ''}`);
              if (lo == null || hi == null) return extra;
              const loN = Number(lo);
              const hiN = Number(hi);
              if (!Number.isFinite(loN) || !Number.isFinite(hiN)) return extra;
              extra.push(`95% CI: ${formatNumber(loN)} - ${formatNumber(hiN)}`);
              return extra;
            },
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: 'Number of Patients',
          },
        },
        x: {
          title: {
            display: true,
            text: 'Time Period',
          },
        },
      },
    },
  });
};

watch(
  () => props.forecastedData,
  async () => {
    await nextTick();
    createChart();
  },
  { deep: true }
);

onMounted(() => {
  createChart();
});

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.destroy();
    chartInstance = null;
  }
});
</script>

<style scoped>
.patient-volume {
  display: flex;
  flex-direction: column;
}

.summary-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 20px;
  margin-top: 16px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 20px;
  background: #ffffff;
  border-radius: 10px;
  border: 1px solid #e5e7eb;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  text-align: center;
}

.summary-stats .stat-label {
  font-size: 14px;
  color: #374151;
  margin-bottom: 6px;
  font-weight: 600;
}

.summary-stats .stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #1f2937;
}
</style>
