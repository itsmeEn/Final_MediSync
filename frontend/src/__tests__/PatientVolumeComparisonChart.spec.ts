import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';

vi.mock('chart.js', () => {
  class ChartMock {
    static register = vi.fn();
    static defaults = { devicePixelRatio: 1 };
    static lastConfig: unknown = null;
    constructor(_ctx: unknown, config: unknown) {
      ChartMock.lastConfig = config;
    }
    destroy() {}
  }

  return {
    Chart: ChartMock,
    registerables: [],
  };
});

import PatientVolumeComparisonChart from '../components/analytics/PatientVolumeComparisonChart.vue';
import { Chart } from 'chart.js';

describe('PatientVolumeComparisonChart.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // @ts-expect-error - test shim
    HTMLCanvasElement.prototype.getContext = vi.fn(() => ({}));
  });

  it('renders identical output for the same dataset and builds a stable chart config', () => {
    const forecastedData = [
      { date: '2024-01', predicted_volume: 45, actual_volume: 42 },
      { date: '2024-02', predicted_volume: 52, actual_volume: 50 },
    ];

    const w1 = mount(PatientVolumeComparisonChart, {
      props: { forecastedData },
    });
    const html1 = w1.html();

    const w2 = mount(PatientVolumeComparisonChart, {
      props: { forecastedData },
    });
    const html2 = w2.html();

    expect(html1).toBe(html2);

    const cfg = (Chart as unknown as { lastConfig: unknown }).lastConfig;
    expect(cfg).not.toBeNull();

    const typedCfg = cfg as {
      type: string;
      data: {
        labels: string[];
        datasets: Array<{ label: string; borderColor: string; borderDash?: number[] }>;
      };
      options: {
        plugins: {
          title: { text: string };
          legend: { position: string };
          tooltip: { callbacks: { label: unknown } };
        };
      };
    };

    expect(typedCfg.type).toBe('line');
    expect(typedCfg.data.labels).toEqual(['2024-01', '2024-02']);
    expect(typedCfg.data.datasets.length).toBeGreaterThanOrEqual(2);
    const [pred, actual] = typedCfg.data.datasets;
    if (!pred || !actual) {
      throw new Error('Expected at least two datasets in chart config');
    }
    expect(pred.label).toBe('Predicted Volume (Projection)');
    expect(pred.borderColor).toBe('rgba(33, 150, 243, 1)');
    expect(pred.borderDash).toEqual([6, 4]);
    expect(actual.label).toBe('Actual Volume (Current)');
    expect(actual.borderColor).toBe('rgba(76, 175, 80, 1)');
    expect(actual.borderDash).toBeUndefined();
    expect(typedCfg.options.plugins.title.text).toBe('Patient Volume: Actual vs Predicted');
    expect(typedCfg.options.plugins.legend.position).toBe('bottom');
    expect(typeof typedCfg.options.plugins.tooltip.callbacks.label).toBe('function');
  });
});
