<template>
  <div class="patient-volume">
    <AnalyticsChartContainer>
      <canvas
        ref="canvasEl"
        width="400"
        height="200"
        role="img"
        aria-label="Patient volume prediction chart with a dashed predicted trend line and a shaded uncertainty band derived from 70/30 train-test validation metrics."
      ></canvas>
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

type EvaluationMetrics = {
  rmse?: number | string | null;
  mape?: number | string | null;
  train_ratio?: number | string | null;
};

const props = defineProps<{
  forecastedData: ForecastPoint[];
  evaluationMetrics?: EvaluationMetrics | null;
  bandOpacity?: number | null;
  bandColor?: string | null;
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
    const hasCI = lower.some((v) => Number.isFinite(v)) && upper.some((v) => Number.isFinite(v));

    const rmse = props.evaluationMetrics?.rmse != null && Number.isFinite(Number(props.evaluationMetrics?.rmse)) ? Number(props.evaluationMetrics?.rmse) : null;
    const mape = props.evaluationMetrics?.mape != null && Number.isFinite(Number(props.evaluationMetrics?.mape)) ? Number(props.evaluationMetrics?.mape) : null;
    const hasMetrics = rmse != null || mape != null;

    const moe: number[] = predicted.map((pv, idx) => {
      if (hasCI && Number.isFinite(lower[idx]!) && Number.isFinite(upper[idx]!)) {
        const width = (Number(upper[idx]!) - Number(lower[idx]!)) / 2;
        return Number.isFinite(width) ? Math.max(0, width) : 0;
      }
      if (!hasMetrics) return 0;
      const pvN = typeof pv === 'number' && Number.isFinite(pv) ? pv : 0;
      const fromRmse = rmse != null ? Math.max(0, rmse) : 0;
      const fromMape = mape != null ? Math.max(0, (Math.max(0, pvN) * mape) / 100.0) : 0;
      return Math.max(fromRmse, fromMape);
    });

    const anomalies = moe.map((m, idx) => {
      const pv = predicted[idx] ?? 0;
      const base = typeof pv === 'number' && Number.isFinite(pv) ? pv : 0;
      if (m <= 0) return false;
      if (base <= 0) return m > 0;
      const ratio = m / Math.max(1, base);
      return ratio > 1.25;
    });

    if (!hasCI && hasMetrics) {
      for (let i = 0; i < predicted.length; i++) {
        const pvRaw = predicted[i];
        const pv = typeof pvRaw === 'number' && Number.isFinite(pvRaw) ? pvRaw : 0;
        const mRaw = moe[i];
        const m = typeof mRaw === 'number' && Number.isFinite(mRaw) ? mRaw : 0;
        lower[i] = Math.max(0, pv - m);
        upper[i] = Math.max(0, pv + m);
      }
    }

    const hasBand = (hasCI || hasMetrics) && upper.some((v) => Number.isFinite(v));
    return { labels, predicted, actual, lower, upper, hasBand, moe, anomalies };
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
  return { labels, predicted, actual, lower: [], upper: [], hasBand: false, moe: [], anomalies: [] };
};

const createChart = () => {
  if (!canvasEl.value) return;

  if (chartInstance) {
    chartInstance.destroy();
    chartInstance = null;
  }

  const ctx = canvasEl.value.getContext('2d');
  if (!ctx) return;

  const { labels, predicted, actual, lower, upper, hasBand, moe, anomalies } = buildDatasets(props.forecastedData);
  const opacityRaw = props.bandOpacity != null && Number.isFinite(Number(props.bandOpacity)) ? Number(props.bandOpacity) : 0.25;
  const bandOpacity = Math.min(0.3, Math.max(0.2, opacityRaw));
  const bandBase = typeof props.bandColor === 'string' && props.bandColor.trim() ? props.bandColor.trim() : 'rgba(33, 150, 243, 1)';
  const bandNormal = bandBase.replace(/rgba\(([^)]+)\)/, (_m, inner) => {
    const parts = String(inner).split(',').map((x) => x.trim());
    const rgb = parts.slice(0, 3).join(', ');
    return `rgba(${rgb}, ${bandOpacity})`;
  });
  const bandAnomaly = 'rgba(244, 67, 54, 0.25)';
  const bandColors = anomalies.length ? anomalies.map((a) => (a ? bandAnomaly : bandNormal)) : bandNormal;

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
                backgroundColor: bandColors,
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
              const m = typeof moe?.[ctx.dataIndex] === 'number' && Number.isFinite(moe[ctx.dataIndex]!) ? moe[ctx.dataIndex]! : null;
              if (m != null && m > 0) extra.push(`Margin of error (±): ${formatNumber(m)}`);
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
