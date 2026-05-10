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
};

const props = defineProps<{
  forecastedData: ForecastPoint[];
}>();

const formatNumber = (n: number) => new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(n);
const toNum = (v: unknown): number => {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
};

const latestVolumeOutput = computed(() => {
  const vp = props.forecastedData;
  if (Array.isArray(vp) && vp.length > 0) {
    const last = vp[vp.length - 1]!;
    const predicted = toNum(last.predicted_volume);
    const actual = last.actual_volume !== undefined && last.actual_volume !== null && Number.isFinite(Number(last.actual_volume))
      ? Number(last.actual_volume)
      : null;
    return { label: last.date, predicted, actual };
  }
  return { label: null, predicted: null, actual: null };
});

const canvasEl = ref<HTMLCanvasElement | null>(null);
let chartInstance: Chart | null = null;

const buildDatasets = (forecastedData: ForecastPoint[]) => {
  if (Array.isArray(forecastedData) && forecastedData.length > 0) {
    const labels = forecastedData.map((item) => item.date);
    const predicted = forecastedData.map((item) => toNum(item.predicted_volume));
    const actual = forecastedData.map((item) =>
      item.actual_volume !== undefined && item.actual_volume !== null && Number.isFinite(Number(item.actual_volume))
        ? Number(item.actual_volume)
        : NaN
    );
    return { labels, predicted, actual };
  }

  const labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
  const predicted = [45, 52, 48, 55, 60, 58];
  const actual = [42, 50, 46, 52, 58, 56];
  return { labels, predicted, actual };
};

const createChart = () => {
  if (!canvasEl.value) return;

  if (chartInstance) {
    chartInstance.destroy();
    chartInstance = null;
  }

  const ctx = canvasEl.value.getContext('2d');
  if (!ctx) return;

  const { labels, predicted, actual } = buildDatasets(props.forecastedData);

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
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
              return typeof y === 'number' && Number.isFinite(y) ? `${label}: ${formatNumber(y)}` : `${label}: N/A`;
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
