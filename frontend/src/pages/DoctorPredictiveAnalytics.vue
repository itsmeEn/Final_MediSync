<template>
  <q-layout view="hHh Lpr fFf">
    <DoctorHeader @toggle-drawer="rightDrawerOpen = !rightDrawerOpen" />

    <DoctorSidebar 
      v-model="rightDrawerOpen"
      active-route="analytics"
    />

    <q-page-container class="page-container-with-fixed-header role-body-bg">
      <!-- Greeting Section -->
      <div class="greeting-section">
        <q-card class="greeting-card">
          <q-card-section class="greeting-content">
            <h2 class="greeting-text">
              Predictive Analytics Dashboard
            </h2>
            <p class="greeting-subtitle">
              AI-powered insights for clinical decision making - {{ currentDate }}
            </p>
          </q-card-section>
        </q-card>
      </div>

      <!-- Analytics Cards Section -->
      <div class="dashboard-cards-section" v-if="false">
        <div class="dashboard-cards-grid">
          <!-- Patient Demographics Card -->
          <q-card
            class="dashboard-card demographics-card zoom-card"
            @click="viewDemographics"
            @mouseenter="showZoomedData('demographics')"
            @mouseleave="hideZoomedData"
          >
            <q-card-section class="card-content">
              <div class="card-text">
                <div class="card-title">Patient Demographics</div>
                <div class="card-description">Age distribution and gender analysis</div>
              </div>
              <div class="card-icon">
                <q-icon name="people" size="2.5rem" />
              </div>
            </q-card-section>
            <!-- Zoomed Data Overlay -->
            <div class="zoomed-data-overlay" v-if="zoomedData.type === 'demographics'">
              <div class="zoomed-content">
                <h4>Patient Demographics Overview</h4>
                <div v-if="analyticsData.patient_demographics" class="zoomed-stats">
                  <div class="stat-row">
                    <span class="stat-label">Total Patients:</span>
                    <span class="stat-value">{{
                      analyticsData.patient_demographics?.total_patients ?? 'N/A'
                    }}</span>
                  </div>
                  <div class="stat-row">
                    <span class="stat-label">Average Age:</span>
                    <span class="stat-value"
                      >{{ analyticsData.patient_demographics?.average_age ?? 'N/A' }} years</span
                    >
                  </div>
                  <div class="stat-row">
                    <span class="stat-label">Gender Distribution:</span>
                    <div class="gender-stats">
                      <span
                        v-for="(percentage, gender) in analyticsData.patient_demographics?.gender_proportions || {}"
                        :key="gender"
                        class="gender-item"
                      >
                        {{ gender }}: {{ percentage }}%
                      </span>
                    </div>
                  </div>
                </div>
                <div v-else class="no-data">
                  <p>No demographics data available</p>
                </div>
              </div>
            </div>
          </q-card>

          <!-- Illness Prediction Card -->
          <q-card
            class="dashboard-card prediction-card zoom-card"
            @click="viewIllnessPrediction"
            @mouseenter="showZoomedData('prediction')"
            @mouseleave="hideZoomedData"
          >
            <q-card-section class="card-content">
              <div class="card-text">
                <div class="card-title">Illness Prediction</div>
                <div class="card-description">Statistical analysis and disease patterns</div>
              </div>
              <div class="card-icon">
                <q-icon name="psychology" size="2.5rem" />
              </div>
            </q-card-section>
            <!-- Zoomed Data Overlay -->
            <div class="zoomed-data-overlay" v-if="zoomedData.type === 'prediction'">
              <div class="zoomed-content">
                <h4>Illness Prediction Analysis</h4>
                <div v-if="analyticsData.illness_prediction" class="zoomed-stats">
                  <div class="stat-row">
                    <span class="stat-label">Chi-Square Statistic:</span>
                    <span class="stat-value">{{
                      analyticsData.illness_prediction?.chi_square_statistic ?? 'N/A'
                    }}</span>
                  </div>
                  <div class="stat-row">
                    <span class="stat-label">P-Value:</span>
                    <span class="stat-value">{{
                      analyticsData.illness_prediction?.p_value ?? 'N/A'
                    }}</span>
                  </div>
                  <div class="stat-row">
                    <span class="stat-label">Association Result:</span>
                    <span class="stat-value">{{
                      analyticsData.illness_prediction?.association_result ?? 'N/A'
                    }}</span>
                  </div>
                </div>
                <div v-else class="no-data">
                  <p>No prediction data available</p>
                </div>
              </div>
            </div>
          </q-card>

          <!-- Health Trends Card -->
          <q-card
            class="dashboard-card trends-card zoom-card"
            @click="viewHealthTrends"
            @mouseenter="showZoomedData('trends')"
            @mouseleave="hideZoomedData"
          >
            <q-card-section class="card-content">
              <div class="card-text">
                <div class="card-title">Health Trends</div>
                <div class="card-description">Top medical conditions and patterns</div>
              </div>
              <div class="card-icon">
                <q-icon name="trending_up" size="2.5rem" />
              </div>
            </q-card-section>
            <!-- Zoomed Data Overlay -->
            <div class="zoomed-data-overlay" v-if="zoomedData.type === 'trends'">
              <div class="zoomed-content">
                <h4>Health Trends Analysis</h4>
                <div v-if="analyticsData.health_trends" class="zoomed-stats">
                  <div class="stat-row">
                    <span class="stat-label">Top Conditions:</span>
                    <div class="conditions-list">
                      <span
                        v-for="condition in analyticsData.health_trends?.top_illnesses_by_week?.slice(
                          0,
                          3,
                        )"
                        :key="condition.medical_condition"
                        class="condition-item"
                      >
                        {{ condition.medical_condition }}: {{ condition.count }}
                      </span>
                    </div>
                  </div>
                  <div class="stat-row">
                    <span class="stat-label">Trend Analysis:</span>
                    <div class="trend-items">
                      <span
                        v-for="condition in analyticsData.health_trends?.trend_analysis?.increasing_conditions?.slice(
                          0,
                          2,
                        )"
                        :key="condition"
                        class="trend-item increasing"
                      >
                        {{ condition }} ↗
                      </span>
                    </div>
                  </div>
                </div>
                <div v-else class="no-data">
                  <p>No trends data available</p>
                </div>
              </div>
            </div>
          </q-card>

          <!-- Surge Prediction Card -->
          <q-card
            class="dashboard-card surge-card zoom-card"
            @click="viewSurgePrediction"
            @mouseenter="showZoomedData('surge')"
            @mouseleave="hideZoomedData"
          >
            <q-card-section class="card-content">
              <div class="card-text">
                <div class="card-title">Surge Prediction</div>
                <div class="card-description">Forecast illness outbreaks and capacity</div>
              </div>
              <div class="card-icon">
                <q-icon name="warning" size="2.5rem" />
              </div>
            </q-card-section>
            <!-- Zoomed Data Overlay -->
            <div class="zoomed-data-overlay" v-if="zoomedData.type === 'surge'">
              <div class="zoomed-content">
                <h4>Surge Prediction Analysis</h4>
                <div v-if="analyticsData.surge_prediction" class="zoomed-stats">
                  <div class="stat-row">
                    <span class="stat-label">Model Accuracy:</span>
                    <span class="stat-value"
                      >{{ analyticsData.surge_prediction?.model_accuracy ?? 'N/A' }}%</span
                    >
                  </div>
                  <div class="stat-row">
                    <span class="stat-label">Risk Factors:</span>
                    <div class="risk-factors">
                      <span
                        v-for="factor in surgeRiskFactors.slice(0, 2)"
                        :key="factor"
                        class="risk-item"
                      >
                        {{ factor }}
                      </span>
                    </div>
                  </div>
                </div>
                <div v-else class="no-data">
                  <p>No surge prediction data available</p>
                </div>
              </div>
            </div>
          </q-card>
        </div>
      </div>

      <!-- Analytics Data Display Section -->
      <div class="analytics-section">
        <q-card class="analytics-card">
          <q-card-section class="analytics-header" v-if="false">
            <h3 class="analytics-title">REAL-TIME ANALYTICS INSIGHTS</h3>
            <div class="analytics-actions">
              <q-btn
                color="primary"
                label="Generate PDF Report"
                icon="picture_as_pdf"
                size="md"
                @click="generatePDFReport"
                class="action-btn"
              />
              <q-btn
                color="secondary"
                label="Refresh Data"
                icon="refresh"
                size="md"
                @click="refreshAnalytics"
                class="action-btn"
              />
            </div>
          </q-card-section>

          <q-card-section class="analytics-content">
            <div class="kpi-grid">
              <q-card class="kpi-card themed-card" :style="cardStyle('doctor.kpi.forecast')">
                <q-card-section class="kpi-body">
                  <div class="kpi-label">Total Forecast Cases</div>
                  <div class="kpi-value">{{ formatNumber(surgeTotalCases) }}</div>
                  <div class="kpi-caption">next 3 months</div>
                </q-card-section>
              </q-card>
              <q-card class="kpi-card themed-card" :style="cardStyle('doctor.kpi.patients')">
                <q-card-section class="kpi-body">
                  <div class="kpi-label">Total Patients</div>
                  <div class="kpi-value">{{ analyticsData.patient_demographics?.total_patients ?? 'N/A' }}</div>
                  <div class="kpi-caption">to date</div>
                </q-card-section>
              </q-card>
              <q-card class="kpi-card themed-card" :style="cardStyle('doctor.kpi.age')">
                <q-card-section class="kpi-body">
                  <div class="kpi-label">Avg Patient Age</div>
                  <div class="kpi-value">{{ analyticsData.patient_demographics?.average_age ?? 'N/A' }}</div>
                  <div class="kpi-caption">years</div>
                </q-card-section>
              </q-card>
              <q-card class="kpi-card themed-card" :style="cardStyle('doctor.kpi.volume')">
                <q-card-section class="kpi-body">
                  <div class="kpi-label">Predicted Volume</div>
                  <div class="kpi-value">{{ latestVolumeOutput.predicted != null ? formatNumber(latestVolumeOutput.predicted) : 'N/A' }}</div>
                  <div class="kpi-caption">{{ latestVolumeOutput.label ?? 'latest' }}</div>
                </q-card-section>
              </q-card>
            </div>

            <div class="integrated-analytics-grid">
              <div class="integrated-main">
                <div class="integrated-top-row">
                  <q-card class="analytics-panel integrated-card themed-card" :style="cardStyle('doctor.card.surge')">
                    <q-card-section>
                      <div class="integrated-card-header">
                        <div class="integrated-card-title">Surge Prediction & Illness Forecast</div>
                      </div>
                      <div class="integrated-card-body">
                        <div v-if="analyticsData.surge_prediction || analyticsData.health_trends" class="analytics-data">
                          <div class="chart-container">
                            <canvas ref="surgeChart" width="400" height="200"></canvas>
                          </div>
                          <div class="summary-stats q-mt-sm">
                            <div class="stat-item">
                              <span class="stat-label">Total predicted cases</span>
                              <span class="stat-value">{{ formatNumber(surgeTotalCases) }}</span>
                            </div>
                          </div>

                          <div v-if="analyticsData.health_trends?.trend_analysis?.increasing_conditions" class="predicted-illnesses-section q-mt-sm">
                            <h5>Predicted Illness Outbreaks</h5>
                            <div class="illness-predictions">
                              <div
                                v-for="condition in analyticsData.health_trends.trend_analysis.increasing_conditions"
                                :key="condition"
                                class="illness-prediction-card"
                              >
                                <div class="illness-icon">
                                  <q-icon name="local_hospital" size="24px" color="warning" />
                                </div>
                                <div class="illness-details">
                                  <div class="illness-name">{{ condition }}</div>
                                  <div class="illness-trend">
                                    <q-icon name="trending_up" size="16px" color="negative" />
                                    <span class="trend-text">Increasing Trend</span>
                                  </div>
                                </div>
                              </div>
                            </div>
                          </div>

                          <div v-if="analyticsData.health_trends?.top_illnesses_by_week" class="current-illnesses-section q-mt-sm">
                            <h5>Current Top Illnesses</h5>
                            <div class="current-illnesses-list">
                              <div
                                v-for="illness in analyticsData.health_trends.top_illnesses_by_week.slice(0, 5)"
                                :key="illness.medical_condition"
                                class="current-illness-item"
                              >
                                <span class="illness-rank">{{ analyticsData.health_trends.top_illnesses_by_week.indexOf(illness) + 1 }}</span>
                                <span class="illness-name-text">{{ illness.medical_condition }}</span>
                                <span class="illness-count">{{ illness.count }} cases</span>
                              </div>
                            </div>
                          </div>
                        </div>
                        <div v-else class="empty-data">
                          <p>No surge prediction data available</p>
                        </div>
                      </div>
                    </q-card-section>
                  </q-card>

                  <q-card class="analytics-panel integrated-card themed-card" :style="cardStyle('doctor.card.volume')">
                    <q-card-section>
                      <div class="integrated-card-header">
                        <div class="integrated-card-title">Patient Volume Prediction</div>
                      </div>
                      <div class="integrated-card-body">
                        <div v-if="analyticsData.volume_prediction" class="analytics-data">
                          <PatientVolumeComparisonChart :forecasted-data="analyticsData.volume_prediction?.forecasted_data || []" />
                        </div>
                        <div v-else class="empty-data">
                          <p>No volume prediction data available</p>
                        </div>
                      </div>
                    </q-card-section>
                  </q-card>
                </div>

                <q-card class="analytics-panel integrated-card themed-card" :style="cardStyle('doctor.card.trends')">
                  <q-card-section>
                    <div class="integrated-card-header">
                      <div class="integrated-card-title">Health Trends</div>
                    </div>
                    <div class="integrated-card-body">
                      <div v-if="analyticsData.health_trends?.top_illnesses_by_week" class="analytics-data">
                        <div class="chart-container">
                          <canvas ref="trendsChart" width="400" height="200"></canvas>
                        </div>
                        <div class="trend-analysis q-mt-sm">
                          <div class="trend-section">
                            <h5>Increasing Conditions</h5>
                            <div class="trend-items">
                              <span
                                v-for="condition in analyticsData.health_trends.trend_analysis?.increasing_conditions"
                                :key="condition"
                                class="trend-item increasing"
                              >
                                {{ condition }}
                              </span>
                            </div>
                          </div>
                          <div class="trend-section">
                            <h5>Decreasing Conditions</h5>
                            <div class="trend-items">
                              <span
                                v-for="condition in analyticsData.health_trends.trend_analysis?.decreasing_conditions"
                                :key="condition"
                                class="trend-item decreasing"
                              >
                                {{ condition }}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                      <div v-else class="empty-data">
                        <p>No health trends data available</p>
                      </div>
                    </div>
                  </q-card-section>
                </q-card>

                <div class="integrated-bottom-row">
                  <q-card class="analytics-panel integrated-card themed-card" :style="cardStyle('doctor.card.demographics')">
                    <q-card-section>
                      <div class="integrated-card-header">
                        <div class="integrated-card-title">Patient Demographics</div>
                      </div>
                      <div class="integrated-card-body">
                        <div v-if="analyticsData.patient_demographics" class="analytics-data">
                          <div class="chart-container">
                            <canvas ref="ageChart" width="400" height="200"></canvas>
                          </div>
                          <div class="summary-stats q-mt-sm">
                            <div class="stat-item">
                              <span class="stat-label">Total Patients</span>
                              <span class="stat-value">{{ analyticsData.patient_demographics?.total_patients ?? 'N/A' }}</span>
                            </div>
                            <div class="stat-item">
                              <span class="stat-label">Average Age</span>
                              <span class="stat-value">{{ analyticsData.patient_demographics?.average_age ?? 'N/A' }} yrs</span>
                            </div>
                          </div>
                        </div>
                        <div v-else class="empty-data">
                          <p>No demographics data available</p>
                        </div>
                      </div>
                    </q-card-section>
                  </q-card>

                  <q-card class="analytics-panel integrated-card themed-card" :style="cardStyle('doctor.card.gender')">
                    <q-card-section>
                      <div class="integrated-card-header">
                        <div class="integrated-card-title">Gender Distribution</div>
                      </div>
                      <div class="integrated-card-body">
                        <div v-if="analyticsData.patient_demographics?.gender_proportions" class="analytics-data">
                          <div class="chart-container">
                            <canvas ref="genderChart" width="400" height="200"></canvas>
                          </div>
                        </div>
                        <div v-else class="empty-data">
                          <p>No gender distribution data available</p>
                        </div>
                      </div>
                    </q-card-section>
                  </q-card>
                </div>
              </div>

              <div class="analytics-sidebar-panel">
                <q-card bordered flat class="ai-summary-card themed-card" :style="cardStyle('doctor.card.ai')">
                  <q-card-section class="actions-row" aria-label="Analytics actions">
                    <q-badge v-if="analyticsSourceLabel" color="warning" text-color="black" :label="analyticsSourceLabel" class="q-mr-sm" />
                    <q-btn color="primary" label="Generate PDF Report" icon="picture_as_pdf" size="sm" @click="generatePDFReport" class="sidebar-btn" aria-label="Generate PDF Report" />
                    <q-btn color="secondary" label="Refresh Analytics Data" icon="refresh" size="sm" @click="refreshAnalytics" class="sidebar-btn" aria-label="Refresh Analytics Data" />
                    <q-btn color="accent" label="Customize Colors" icon="palette" size="sm" @click="showCardColorCustomizer = true" class="sidebar-btn" aria-label="Customize Colors" />
                  </q-card-section>
                  <q-separator class="q-my-xs" />
                  <q-card-section>
                    <div class="ai-summary-header">AI-SUMMARY GENERATED RESPONSE</div>
                    <div class="ai-summary-disclaimer">
                      <em>
                        Disclaimer: This is an automated, AI-generated recommendation that interprets the latest analytics findings based on the current data. It is intended to guide immediate resource allocation and strategic planning, not replace expert clinical judgment.
                      </em>
                    </div>
                    <div class="ai-summary-text">
                      {{ aiSummaryText }}
                    </div>
                    <div v-if="analyticsData.illness_prediction" class="q-mt-md">
                      <div class="data-item">
                        <div class="data-label">Chi-Square</div>
                        <div class="data-values">
                          <div class="value-item">{{ analyticsData.illness_prediction?.chi_square_statistic ?? 'N/A' }}</div>
                        </div>
                      </div>
                      <div class="data-item">
                        <div class="data-label">P-Value</div>
                        <div class="data-values">
                          <div class="value-item">{{ analyticsData.illness_prediction?.p_value ?? 'N/A' }}</div>
                        </div>
                      </div>
                      <div class="data-item">
                        <div class="data-label">Association</div>
                        <div class="data-values">
                          <div class="value-item">{{ analyticsData.illness_prediction?.association_result ?? 'N/A' }}</div>
                        </div>
                      </div>
                    </div>
                  </q-card-section>
                </q-card>
              </div>
            </div>

            <!-- AI Recommendations UI removed; recommendations are consolidated into generated PDF reports. -->

          </q-card-section>
        </q-card>
      </div>

      <CardColorConfigurator
        v-model="showCardColorCustomizer"
        :cards="cardCustomizerCards"
      />



      <router-view />
    </q-page-container>

    <!-- Notifications Modal -->
    <q-dialog v-model="showNotifications" persistent>
      <q-card style="width: 400px; max-width: 90vw">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">Notifications</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section>
          <div v-if="notifications.length === 0" class="text-center text-grey-6 q-py-lg">
            No notifications yet
          </div>
          <div v-else>
            <q-list>
              <q-item
                v-for="notification in notifications"
                :key="notification.id"
                clickable
                @click="handleNotificationClick(notification)"
                :class="{ unread: !notification.is_read }"
              >
                <q-item-section avatar>
                  <q-icon name="info" color="primary" />
                </q-item-section>
                <q-item-section>
                  <q-item-label>{{ notification.message }}</q-item-label>
                  <q-item-label caption class="text-grey-5">{{
                    formatTime(notification.created_at)
                  }}</q-item-label>
                </q-item-section>
                <q-item-section side v-if="!notification.is_read">
                  <q-badge color="red" rounded />
                </q-item-section>
              </q-item>
            </q-list>
          </div>
        </q-card-section>

        <q-card-actions align="right" v-if="notifications.length > 0">
          <q-btn flat label="Mark All Read" @click="markAllNotificationsRead" />
          <q-btn flat label="Close" color="primary" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-layout>
</template>

<script setup lang="ts">
import CardColorConfigurator from 'src/components/analytics/CardColorConfigurator.vue';
import PatientVolumeComparisonChart from 'src/components/analytics/PatientVolumeComparisonChart.vue';
import { useCardTheme } from 'src/composables/useCardTheme';
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue';
import { useQuasar } from 'quasar';
import { api } from '../boot/axios';
import { Chart, registerables } from 'chart.js';
import type { ChartDataset, TooltipItem } from 'chart.js';
import DoctorHeader from '../components/DoctorHeader.vue';
import DoctorSidebar from '../components/DoctorSidebar.vue';

// Register Chart.js components
Chart.register(...registerables);
Chart.defaults.devicePixelRatio = window.devicePixelRatio || 1;

const $q = useQuasar();
const { cardStyle } = useCardTheme();

const rightDrawerOpen = ref(false);
const showNotifications = ref(false);
const showCardColorCustomizer = ref(false);

const cardCustomizerCards = [
  { id: 'doctor.kpi.forecast', label: 'KPI: Total Forecast Cases' },
  { id: 'doctor.kpi.patients', label: 'KPI: Total Patients' },
  { id: 'doctor.kpi.age', label: 'KPI: Avg Patient Age' },
  { id: 'doctor.kpi.volume', label: 'KPI: Predicted Volume' },
  { id: 'doctor.card.surge', label: 'Surge Prediction & Illness Forecast' },
  { id: 'doctor.card.volume', label: 'Patient Volume Prediction' },
  { id: 'doctor.card.trends', label: 'Health Trends' },
  { id: 'doctor.card.demographics', label: 'Patient Demographics' },
  { id: 'doctor.card.gender', label: 'Gender Distribution' },
  { id: 'doctor.card.ai', label: 'AI Summary & Associations' },
];

// Chart refs
const ageChart = ref<HTMLCanvasElement | null>(null);
const genderChart = ref<HTMLCanvasElement | null>(null);
const trendsChart = ref<HTMLCanvasElement | null>(null);
const surgeChart = ref<HTMLCanvasElement | null>(null);
const modelAccuracyChart = ref<HTMLCanvasElement | null>(null);
const confidenceLevelChart = ref<HTMLCanvasElement | null>(null);
const monthlyIllnessChart = ref<HTMLCanvasElement | null>(null);

// Chart instances
let ageChartInstance: Chart | null = null;
let genderChartInstance: Chart | null = null;
let trendsChartInstance: Chart | null = null;
let surgeChartInstance: Chart | null = null;
let modelAccuracyChartInstance: Chart | null = null;
let confidenceLevelChartInstance: Chart | null = null;
let monthlyIllnessChartInstance: Chart | null = null;

// Analytics data interfaces
interface PatientDemographics {
  age_distribution?: { [key: string]: number };
  gender_proportions?: { [key: string]: number };
  total_patients?: number;
  average_age?: number;
}

interface IllnessPrediction {
  association_result?: string;
  chi_square_statistic?: number;
  p_value?: number;
  confidence_level?: number;
  significant_factors?: string[];
}

interface HealthTrends {
  top_illnesses_by_week?: Array<{
    medical_condition: string;
    count: number;
    date_of_admission: string;
  }>;
  trend_analysis?: {
    increasing_conditions?: string[];
    decreasing_conditions?: string[];
    stable_conditions?: string[];
  };
}

interface VolumePrediction {
  evaluation_metrics?: {
    mae: number;
    rmse: number;
  };
  forecasted_data?: Array<{
    date: string;
    predicted_volume: number;
    actual_volume?: number;
  }>;
}

interface SurgePrediction {
  forecasted_monthly_cases?: Array<{
    date: string;
    total_cases: number;
  }>;
  model_accuracy?: number;
  risk_factors?: string[];
}

interface MonthlyIllnessForecast {
  monthly_illness_forecast?: Array<{
    illness: string;
    month: string;
    predicted_cases: number;
    risk_level?: string;
    trend?: 'increasing' | 'decreasing' | 'stable';
  }>;
  evaluation_metrics?: {
    mae?: number;
    rmse?: number;
  };
}

interface AnalyticsData {
  patient_demographics: PatientDemographics | null;
  illness_prediction: IllnessPrediction | null;
  health_trends: HealthTrends | null;
  volume_prediction: VolumePrediction | null;
  surge_prediction: SurgePrediction | null;
  monthly_illness_forecast: MonthlyIllnessForecast | null;
}

// Analytics data
const analyticsData = ref<AnalyticsData>({
  patient_demographics: null,
  illness_prediction: null,
  health_trends: null,
  volume_prediction: null,
  surge_prediction: null,
  monthly_illness_forecast: null,
});

const analyticsDataSource = ref<'database' | 'mixed' | 'seed'>('database');

const analyticsSourceLabel = computed(() => {
  if (analyticsDataSource.value === 'seed') return 'Seed Data';
  if (analyticsDataSource.value === 'mixed') return 'Partial Seed Data';
  return '';
});

const doctorSeedData = (): AnalyticsData => ({
  patient_demographics: {
    age_distribution: { '0-18': 12, '19-35': 38, '36-50': 27, '51-65': 22, '65+': 16 },
    gender_proportions: { Male: 51, Female: 47, Other: 2 },
    total_patients: 115,
    average_age: 43,
  },
  illness_prediction: {
    chi_square_statistic: 6.21,
    p_value: 0.044,
    association_result: 'Statistically significant association detected.',
    confidence_level: 95,
    significant_factors: ['Age group', 'Seasonality'],
  },
  health_trends: {
    top_illnesses_by_week: [
      { medical_condition: 'Hypertension', count: 18, date_of_admission: '2026-05-01' },
      { medical_condition: 'Diabetes', count: 12, date_of_admission: '2026-05-01' },
      { medical_condition: 'URI', count: 9, date_of_admission: '2026-05-01' },
      { medical_condition: 'Asthma', count: 6, date_of_admission: '2026-05-01' },
      { medical_condition: 'Allergies', count: 5, date_of_admission: '2026-05-01' },
    ],
    trend_analysis: {
      increasing_conditions: ['URI', 'Allergies'],
      decreasing_conditions: ['Asthma'],
      stable_conditions: ['Hypertension', 'Diabetes'],
    },
  },
  volume_prediction: {
    forecasted_data: [
      { date: '2026-05', predicted_volume: 48, actual_volume: 46 },
      { date: '2026-06', predicted_volume: 52, actual_volume: 50 },
      { date: '2026-07', predicted_volume: 55, actual_volume: 53 },
      { date: '2026-08', predicted_volume: 51, actual_volume: 49 },
      { date: '2026-09', predicted_volume: 50, actual_volume: 48 },
    ],
  },
  surge_prediction: {
    forecasted_monthly_cases: [
      { date: '2026-05', total_cases: 22 },
      { date: '2026-06', total_cases: 28 },
      { date: '2026-07', total_cases: 31 },
      { date: '2026-08', total_cases: 27 },
      { date: '2026-09', total_cases: 24 },
      { date: '2026-10', total_cases: 26 },
    ],
    model_accuracy: 82,
    risk_factors: ['Seasonal variance', 'Local outbreaks', 'Staffing constraints'],
  },
  monthly_illness_forecast: {
    monthly_illness_forecast: [
      { illness: 'Hypertension', month: '2026-06', predicted_cases: 14, risk_level: 'moderate', trend: 'stable' },
      { illness: 'Diabetes', month: '2026-06', predicted_cases: 10, risk_level: 'moderate', trend: 'stable' },
      { illness: 'URI', month: '2026-06', predicted_cases: 12, risk_level: 'high', trend: 'increasing' },
    ],
  },
});

// AI Recommendations moved to PDF generation; UI state removed.


const surgeRiskFactors = computed(() => analyticsData.value.surge_prediction?.risk_factors ?? []);

// Latest predicted and actual volume (for display under chart)
const latestVolumeOutput = computed(() => {
  const vp = analyticsData.value.volume_prediction?.forecasted_data as
    | { date: string; predicted_volume: number | string; actual_volume?: number | string }[]
    | undefined;
  if (Array.isArray(vp) && vp.length > 0) {
    const last = vp[vp.length - 1]!;
    const predicted = toNum(last.predicted_volume);
    const actual = last.actual_volume !== undefined
      ? (Number.isFinite(Number(last.actual_volume)) ? Number(last.actual_volume) : null)
      : null;
    return { label: last.date, predicted, actual };
  }
  const sp = analyticsData.value.surge_prediction?.forecasted_monthly_cases as
    | { date: string; total_cases: number | string }[]
    | undefined;
  if (Array.isArray(sp) && sp.length > 0) {
    const last = sp[sp.length - 1]!;
    return { label: last.date, predicted: toNum(last.total_cases), actual: null };
  }
  return { label: null, predicted: null, actual: null };
});

// Total predicted cases across surge forecast
const surgeTotalCases = computed(() => {
  const sp = analyticsData.value.surge_prediction?.forecasted_monthly_cases || [];
  return sp.reduce((sum: number, item: { total_cases?: number | string }) => sum + Number(item.total_cases || 0), 0);
});

// Emerging illness text summary removed in favor of chart visualization

// Format numbers for readability (e.g., 12,345)
const formatNumber = (n: number) => new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(n);
// Safe numeric parsing helper
const toNum = (v: unknown): number => {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
};

// Time range controls removed; charts render full available datasets

watch(() => analyticsData.value, async () => {
  await nextTick();
  await createAllCharts();
}, { deep: true });


// Zoom functionality
const zoomedData = ref<{
  type: string | null;
  visible: boolean;
}>({
  type: null,
  visible: false,
});

// Real-time features are now handled by DoctorHeader component

// Notification system
const notifications = ref<
  {
    id: number;
    message: string;
    is_read: boolean;
    created_at: string;
  }[]
>([]);

// Notification interface
interface Notification {
  id: number;
  message: string;
  is_read: boolean;
  created_at: string;
}

// User profile data removed (not needed for greeting)

const currentDate = computed(() => {
  const now = new Date();
  return now.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
});



const fetchDoctorAnalytics = async () => {
  try {
    const [doctorResponse, volumeResponse] = await Promise.allSettled([
      api.get('/analytics/doctor/'),
      api.get('/analytics/patient-volume/'),
    ]);

    const source =
      doctorResponse.status === 'fulfilled' ? String(doctorResponse.value.data?.data_source || '') : '';
    analyticsDataSource.value =
      source === 'seed' ? 'seed' : source === 'mixed' ? 'mixed' : doctorResponse.status === 'fulfilled' ? 'database' : 'seed';

    const data: AnalyticsData =
      doctorResponse.status === 'fulfilled' && doctorResponse.value.data && typeof doctorResponse.value.data === 'object'
        ? (((doctorResponse.value.data as { data?: unknown }).data as AnalyticsData) || doctorSeedData())
        : doctorSeedData();

    const unifiedVolume =
      volumeResponse.status === 'fulfilled' ? volumeResponse.value.data?.data?.volume_prediction : null;

    if (unifiedVolume) {
      data.volume_prediction = unifiedVolume as VolumePrediction;
    }

    analyticsData.value = data;
    console.log('Doctor analytics loaded:', analyticsData.value);

    // Create charts after data is loaded
    try {
      await createAllCharts();
    } catch (e) {
      console.warn('Charts failed to render', e);
    }
  } catch (error) {
    console.error('Failed to fetch doctor analytics:', error);
    analyticsData.value = doctorSeedData();
    analyticsDataSource.value = 'seed';
    $q.notify({
      type: 'negative',
      message: 'Failed to load analytics data. Displaying seed data.',
      position: 'top',
      timeout: 3000,
    });
  }
};

// Doctor verification check removed; AI recommendations are only in PDF output.

// Doctor AI recommendations are no longer fetched client-side; included in PDF.

const viewDemographics = () => {
  $q.notify({
    type: 'info',
    message: 'Viewing Patient Demographics...',
    position: 'top',
    timeout: 2000,
  });
};

/**
 * Shows notification when illness prediction card is clicked
 * @returns {void}
 *
 * How it works:
 * 1. Displays an info notification to the user
 * 2. Indicates that illness prediction analysis is being viewed
 * 3. Auto-dismisses after 2 seconds
 *
 * Future enhancement: Could navigate to detailed prediction view
 */
const viewIllnessPrediction = () => {
  $q.notify({
    type: 'info',
    message: 'Viewing Illness Prediction Analysis...',
    position: 'top',
    timeout: 2000,
  });
};

/**
 * Shows notification when health trends card is clicked
 * @returns {void}
 *
 * How it works:
 * 1. Displays an info notification to the user
 * 2. Indicates that health trends are being viewed
 * 3. Auto-dismisses after 2 seconds
 *
 * Future enhancement: Could navigate to detailed trends view
 */
const viewHealthTrends = () => {
  $q.notify({
    type: 'info',
    message: 'Viewing Health Trends...',
    position: 'top',
    timeout: 2000,
  });
};

/**
 * Shows notification when surge prediction card is clicked
 * @returns {void}
 *
 * How it works:
 * 1. Displays an info notification to the user
 * 2. Indicates that surge prediction is being viewed
 * 3. Auto-dismisses after 2 seconds
 *
 * Future enhancement: Could navigate to detailed surge prediction view
 */
const viewSurgePrediction = () => {
  $q.notify({
    type: 'info',
    message: 'Viewing Surge Prediction...',
    position: 'top',
    timeout: 2000,
  });
};

/**
 * Generates and downloads a PDF report of doctor analytics
 * @returns {Promise<void>}
 *
 * How it works:
 * 1. Makes API call to /analytics/pdf/?type=doctor with blob response type
 * 2. Creates a Blob object from the response data
 * 3. Creates a temporary URL for the blob
 * 4. Creates a temporary anchor element for download
 * 5. Sets the filename with current date
 * 6. Programmatically clicks the anchor to trigger download
 * 7. Cleans up by removing the anchor and revoking the URL
 * 8. Shows success/error notifications
 *
 * The PDF contains comprehensive analytics data formatted for doctors
 */
const generatePDFReport = async () => {
  try {
    const response = await api.get('/analytics/pdf/?type=doctor', {
      responseType: 'blob',
    });

    const blob = new Blob([response.data], { type: 'application/pdf' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `doctor_analytics_report_${new Date().toISOString().split('T')[0]}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);

    $q.notify({
      type: 'positive',
      message: 'PDF report generated successfully!',
      position: 'top',
      timeout: 3000,
    });
  } catch (error) {
    console.error('Failed to generate PDF report:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to generate PDF report',
      position: 'top',
      timeout: 3000,
    });
  }
};

/**
 * Refreshes analytics data by fetching the latest data from the API
 * @returns {Promise<void>}
 *
 * How it works:
 * 1. Shows info notification that data is being refreshed
 * 2. Calls fetchDoctorAnalytics to get latest data from API
 * 3. Waits for the data to be loaded
 * 4. Shows success notification when refresh is complete
 *
 * This ensures users always have the most up-to-date analytics data
 */
const refreshAnalytics = async () => {
  $q.notify({
    type: 'info',
    message: 'Refreshing analytics data...',
    position: 'top',
    timeout: 2000,
  });

  await fetchDoctorAnalytics();

  $q.notify({
    type: 'positive',
    message: 'Analytics data refreshed!',
    position: 'top',
    timeout: 2000,
  });
};

/**
 * Creates age distribution chart
 * @returns {void}
 *
 * How it works:
 * 1. Gets the canvas element for age chart
 * 2. Destroys existing chart if it exists
 * 3. Creates new Chart.js bar chart with age distribution data
 * 4. Uses responsive design and proper styling
 */
const createAgeChart = () => {
  if (!ageChart.value || !analyticsData.value.patient_demographics?.age_distribution) return;

  if (ageChartInstance) {
    ageChartInstance.destroy();
  }

  const ctx = ageChart.value.getContext('2d');
  if (!ctx) return;

  const data = analyticsData.value.patient_demographics.age_distribution;

  ageChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: Object.keys(data),
      datasets: [
        {
          label: 'Number of Patients',
          data: Object.values(data),
          backgroundColor: [
            'rgba(54, 162, 235, 0.8)',
            'rgba(255, 99, 132, 0.8)',
            'rgba(255, 205, 86, 0.8)',
            'rgba(75, 192, 192, 0.8)',
            'rgba(153, 102, 255, 0.8)',
          ],
          borderColor: [
            'rgba(54, 162, 235, 1)',
            'rgba(255, 99, 132, 1)',
            'rgba(255, 205, 86, 1)',
            'rgba(75, 192, 192, 1)',
            'rgba(153, 102, 255, 1)',
          ],
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: 'Patient Age Distribution',
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            stepSize: 1,
          },
        },
      },
    },
  });
};

/**
 * Creates gender distribution chart
 * @returns {void}
 *
 * How it works:
 * 1. Gets the canvas element for gender chart
 * 2. Destroys existing chart if it exists
 * 3. Creates new Chart.js pie chart with gender distribution data
 * 4. Uses responsive design and proper styling
 */
const createGenderChart = () => {
  if (!genderChart.value || !analyticsData.value.patient_demographics?.gender_proportions) return;

  if (genderChartInstance) {
    genderChartInstance.destroy();
  }

  const ctx = genderChart.value.getContext('2d');
  if (!ctx) return;

  const data = analyticsData.value.patient_demographics.gender_proportions;
  const labels = Object.keys(data);
  const normalize = (s: string) => s.trim().toLowerCase();
  const colorFor = (label: string) => {
    const v = normalize(label);
    if (v === 'male') return { bg: 'rgba(33, 150, 243, 0.85)', border: 'rgba(25, 118, 210, 1)' };
    if (v === 'female') return { bg: 'rgba(233, 30, 99, 0.85)', border: 'rgba(194, 24, 91, 1)' };
    if (v === 'other' || v === 'others' || v === 'non-binary' || v === 'nonbinary') {
      return { bg: 'rgba(156, 39, 176, 0.85)', border: 'rgba(123, 31, 162, 1)' };
    }
    return { bg: 'rgba(96, 125, 139, 0.8)', border: 'rgba(69, 90, 100, 1)' };
  };
  const colors = labels.map(colorFor);

  genderChartInstance = new Chart(ctx, {
    type: 'pie',
    data: {
      labels,
      datasets: [
        {
          data: Object.values(data),
          backgroundColor: colors.map((c) => c.bg),
          borderColor: colors.map((c) => c.border),
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      devicePixelRatio: window.devicePixelRatio || 1,
      plugins: {
        title: {
          display: true,
          text: 'Gender Distribution',
        },
      },
    },
  });
};

/**
 * Creates health trends chart
 * @returns {void}
 *
 * How it works:
 * 1. Gets the canvas element for trends chart
 * 2. Destroys existing chart if it exists
 * 3. Creates new Chart.js bar chart with top medical conditions data
 * 4. Uses responsive design and proper styling
 */
const createTrendsChart = () => {
  if (!trendsChart.value || !analyticsData.value.health_trends?.top_illnesses_by_week) return;

  if (trendsChartInstance) {
    trendsChartInstance.destroy();
  }

  const ctx = trendsChart.value.getContext('2d');
  if (!ctx) return;

  const data = analyticsData.value.health_trends.top_illnesses_by_week.slice(0, 5);

  trendsChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.map((item) => item.medical_condition),
      datasets: [
        {
          label: 'Number of Cases',
          data: data.map((item) => item.count),
          backgroundColor: 'rgba(75, 192, 192, 0.8)',
          borderColor: 'rgba(75, 192, 192, 1)',
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: 'Top Medical Conditions',
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            stepSize: 1,
          },
        },
      },
    },
  });
};

/**
 * Creates surge prediction chart
 * @returns {void}
 *
 * How it works:
 * 1. Gets the canvas element for surge chart
 * 2. Destroys existing chart if it exists
 * 3. Creates new Chart.js line chart with forecasted cases data
 * 4. Uses responsive design and proper styling
 */
const createSurgeChart = () => {
  if (!surgeChart.value) return;

  if (surgeChartInstance) {
    surgeChartInstance.destroy();
  }

  const ctx = surgeChart.value.getContext('2d');
  if (!ctx) return;

  const raw: { date: string; total_cases: number | string }[] =
    analyticsData.value.surge_prediction?.forecasted_monthly_cases || [];
  const parseMonth = (m: string): number => {
    const d = new Date(m);
    if (!isNaN(d.getTime())) return d.getTime();
    const match = m.match(/^(\d{4})-(\d{1,2})/);
    if (match) {
      const y = Number(match[1]);
      const mm = Number(match[2]) - 1;
      return new Date(y, mm, 1).getTime();
    }
    return Number.MAX_SAFE_INTEGER;
  };
  const sorted = [...raw].sort((a: { date: string }, b: { date: string }) => parseMonth(a.date) - parseMonth(b.date));
  const data = sorted.length
    ? sorted
    : [
        { date: 'Jan', total_cases: 30 },
        { date: 'Feb', total_cases: 42 },
        { date: 'Mar', total_cases: 36 },
        { date: 'Apr', total_cases: 50 },
        { date: 'May', total_cases: 47 },
        { date: 'Jun', total_cases: 55 },
      ];

  surgeChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.map((item) => item.date),
      datasets: [
        {
          label: 'Total Predicted Cases',
          data: data.map((item) => toNum(item.total_cases)),
          borderColor: 'rgba(255, 99, 132, 1)',
          backgroundColor: 'rgba(255, 99, 132, 0.2)',
          borderWidth: 2,
          fill: true,
          tension: 0.4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: 'Surge Forecast: Total Cases',
        },
        legend: {
          position: 'bottom',
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          title: { display: true, text: 'Cases' },
        },
        x: {
          title: { display: true, text: 'Month' },
        },
      },
    },
  });
};

// Create stacked bar monthly illness forecast chart (3-month)
const createMonthlyIllnessChart = () => {
  const mif = analyticsData.value.monthly_illness_forecast?.monthly_illness_forecast;
  if (!monthlyIllnessChart.value || !Array.isArray(mif) || mif.length === 0) return;

  if (monthlyIllnessChartInstance) {
    monthlyIllnessChartInstance.destroy();
  }

  const ctx = monthlyIllnessChart.value.getContext('2d');
  if (!ctx) return;

  // Normalize months and build labels
  const parseMonth = (m: string): number => {
    const d = new Date(m);
    if (!isNaN(d.getTime())) return d.getTime();
    const match = m.match(/^(\d{4})-(\d{1,2})$/);
    if (match) {
      const y = Number(match[1]);
      const mm = Number(match[2]) - 1;
      return new Date(y, mm, 1).getTime();
    }
    return Number.MAX_SAFE_INTEGER; // push unknown format to end
  };

  const monthSet = new Set<string>();
  mif.forEach((x) => monthSet.add(x.month));
  let months = Array.from(monthSet).sort((a, b) => parseMonth(a) - parseMonth(b));
  // Limit to the next three months in the forecast
  months = months.slice(0, 3);

  // Group values by illness and month
  const illnessMap = new Map<string, Map<string, number>>();
  mif.forEach((x) => {
    const ill = x.illness;
    const month = x.month;
    const val = Number(x.predicted_cases || 0);
    if (!illnessMap.has(ill)) illnessMap.set(ill, new Map<string, number>());
    illnessMap.get(ill)!.set(month, val);
  });

  const COLORS = [
    'rgba(33, 150, 243, 1)',
    'rgba(76, 175, 80, 1)',
    'rgba(255, 193, 7, 1)',
    'rgba(244, 67, 54, 1)',
    'rgba(156, 39, 176, 1)',
    'rgba(0, 188, 212, 1)',
    'rgba(121, 85, 72, 1)',
    'rgba(63, 81, 181, 1)'
  ];

  const datasets: ChartDataset<'bar', number[]>[] = Array.from(illnessMap.entries()).map(([illness, monthVals], idx) => {
    const color = COLORS[idx % COLORS.length] || 'rgba(100, 100, 100, 1)';
    return {
      label: illness,
      data: months.map((m) => monthVals.get(m) ?? 0),
      backgroundColor: color.replace('1)', '0.6)'),
      borderColor: color,
      borderWidth: 1,
      type: 'bar',
      stack: 'cases',
    };
  });

  monthlyIllnessChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: months,
      datasets,
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: '3-Month Forecast: Cases by Illness',
        },
        legend: {
          position: 'bottom',
        },
        tooltip: {
          callbacks: {
            footer: (items: TooltipItem<'bar'>[]) => {
              try {
                const monthLabel = String(items[0]?.label || '');
                 if (!monthLabel) return '';
                 const idx = months.indexOf(monthLabel);
                const total = datasets.reduce((sum, ds) => {
                  const val = Array.isArray(ds.data) ? Number(ds.data[idx] || 0) : 0;
                  return sum + (isNaN(val) ? 0 : val);
                }, 0);
                return `Total: ${formatNumber(total)} cases`;
              } catch {
                return '';
              }
            },
          },
        },
      },
      scales: {
        x: {
          stacked: true,
          title: { display: true, text: 'Month' },
        },
        y: {
          stacked: true,
          beginAtZero: true,
          title: { display: true, text: 'Predicted Cases' },
        },
      },
    },
  });
};

// AI summary below disclaimer: concise synthesis of available analytics
const aiSummaryText = computed(() => {
  const d = analyticsData.value;
  const sections: string[] = [];

  // Surge Forecast (concise, human-readable)
  {
    const sp = d?.surge_prediction?.forecasted_monthly_cases || [];
    if (sp.length) {
      const totals = sp.map((m: { total_cases?: string | number }) => Number(m.total_cases || 0));
      const totalSum = totals.reduce((sum, n) => sum + n, 0);
      const first = totals[0] ?? null;
      const last = totals[totals.length - 1] ?? null;
      const min = Math.min(...totals);
      const max = Math.max(...totals);
      const trend = first != null && last != null ? (last > first ? 'increasing' : last < first ? 'decreasing' : 'stable') : null;
      
      const riskFactors = (d?.surge_prediction?.risk_factors || []).slice(0, 3).join(', ');

      const lines: string[] = [];
      lines.push(`• Trend: ${trend || 'stable'}; monthly range ${formatNumber(min)}–${formatNumber(max)}.`);
      lines.push(`• Total forecasted cases (${sp.length} months): ${formatNumber(totalSum)}.`);
      if (riskFactors) lines.push(`• Key risks: ${riskFactors}.`);
      sections.push(['Surge Forecast', ...lines].join('\n'));
    }
  }

  // Patient Volume (concise)
  {
    const vp = d?.volume_prediction?.forecasted_data || [];
    if (vp.length) {
      const predicted = vp.map((x: { predicted_volume?: number | string }) => Number(x.predicted_volume || 0));
      const actuals = vp
        .map((x) => (typeof x.actual_volume === 'number' ? Number(x.actual_volume) : NaN))
        .filter((n) => !Number.isNaN(n));
      const pAvg = Math.round(predicted.reduce((s, n) => s + n, 0) / predicted.length);
      const aAvg = actuals.length ? Math.round(actuals.reduce((s, n) => s + n, 0) / actuals.length) : null;
      const pFirst = predicted[0] ?? null;
      const pLast = predicted[predicted.length - 1] ?? null;
      const vTrend = pFirst != null && pLast != null ? (pLast > pFirst ? 'increasing' : pLast < pFirst ? 'decreasing' : 'stable') : null;
      const latest = vp[vp.length - 1]!;
      
      const lines: string[] = [];
      lines.push(`• Trend: ${vTrend || 'stable'}; avg predicted ${formatNumber(pAvg)}${aAvg != null ? `, avg actual ${formatNumber(aAvg)}` : ''}.`);
      lines.push(`• Latest (${latest.date}): predicted ${formatNumber(Number(latest.predicted_volume))}${typeof latest.actual_volume === 'number' ? `, actual ${formatNumber(Number(latest.actual_volume))}` : ''}.`);
      
      sections.push(['Patient Volume', ...lines].join('\n'));
    }
  }

  // Illness Forecast (top conditions + risk mix)
  {
    const mif = d?.monthly_illness_forecast?.monthly_illness_forecast || [];
    if (mif.length) {
      const sorted = [...mif].sort((a: { predicted_cases?: number }, b: { predicted_cases?: number }) => Number(b.predicted_cases || 0) - Number(a.predicted_cases || 0));
      const top = sorted.slice(0, 3).map((x: { illness: string; month: string; predicted_cases: number; trend?: string }) => `${x.illness} (${x.month}: ${formatNumber(Number(x.predicted_cases))}${x.trend ? `; ${x.trend}` : ''})`).join(', ');
      const high = mif.filter((x: { risk_level?: string }) => (x.risk_level || '').toLowerCase() === 'high').length;
      const med = mif.filter((x: { risk_level?: string }) => (x.risk_level || '').toLowerCase() === 'medium').length;
      const low = mif.filter((x: { risk_level?: string }) => (x.risk_level || '').toLowerCase() === 'low').length;
      
      const lines: string[] = [];
      lines.push(`• Top conditions: ${top}.`);
      lines.push(`• Risk mix: High ${high}, Medium ${med}, Low ${low}.`);
      
      sections.push(['Illness Forecast', ...lines].join('\n'));
    }
  }

  // Health Trends (increasing + weekly top)
  {
    const inc = d?.health_trends?.trend_analysis?.increasing_conditions || [];
    const weeklyTop = d?.health_trends?.top_illnesses_by_week || [];
    const lines: string[] = [];
    if (Array.isArray(inc) && inc.length) lines.push(`• Rising risks: ${inc.slice(0, 3).join(', ')}.`);
    if (Array.isArray(weeklyTop) && weeklyTop.length) {
      const topTriplet = weeklyTop.slice(0, 3).map((it: { medical_condition: string; count: number }) => `${it.medical_condition} (${formatNumber(it.count)})`).join(', ');
      lines.push(`• Top this week: ${topTriplet}.`);
    }
    if (lines.length) sections.push(['Health Trends', ...lines].join('\n'));
  }

  // Associations & Factors
  {
    const ia = d?.illness_prediction;
    if (ia) {
      const assoc = ia.association_result;
      const factorsArr = ia.significant_factors || [];
      const cleanFactorsArr = Array.isArray(factorsArr)
        ? factorsArr
            .map((s: string) => s.replace(/\s*\(p\s*<[^)]*\)\s*/gi, '').trim())
            .filter(Boolean)
        : [];
      const factors = cleanFactorsArr.length ? cleanFactorsArr.slice(0, 3).join(', ') : null;

      const lines: string[] = [];
      if (assoc) lines.push(`• Summary: ${assoc}.`);
      if (factors) lines.push(`• Contributing factors: ${factors}.`);
      sections.push(['Associations', ...lines].join('\n'));
    }
  }

  if (!sections.length) return 'Analytics results are not available yet.';
  return sections.join('\n\n');
});

/**
 * Creates model accuracy doughnut chart
 * @returns {void}
 *
 * How it works:
 * 1. Gets the canvas element for model accuracy chart
 * 2. Destroys existing chart if it exists
 * 3. Creates new Chart.js doughnut chart showing accuracy vs remaining
 */
const createModelAccuracyChart = () => {
  const accuracy = analyticsData.value.surge_prediction?.model_accuracy;
  if (!modelAccuracyChart.value || accuracy === undefined || accuracy === null) return;

  if (modelAccuracyChartInstance) {
    modelAccuracyChartInstance.destroy();
  }

  const ctx = modelAccuracyChart.value.getContext('2d');
  if (!ctx) return;

  const accValue = Math.max(0, Math.min(100, Number(accuracy)));
  const remaining = 100 - accValue;

  modelAccuracyChartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Accuracy', 'Remaining'],
      datasets: [
        {
          data: [accValue, remaining],
          backgroundColor: ['rgba(76, 175, 80, 0.85)', 'rgba(200, 200, 200, 0.35)'],
          borderColor: ['rgba(76, 175, 80, 1)', 'rgba(200, 200, 200, 0.8)'],
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: 'Model Accuracy',
        },
        legend: {
          position: 'bottom',
        },
      },
      cutout: '60%',
    },
  });
};


const createConfidenceLevelChart = () => {
  const confidence = analyticsData.value.illness_prediction?.confidence_level;
  if (!confidenceLevelChart.value || confidence === undefined || confidence === null) return;

  if (confidenceLevelChartInstance) {
    confidenceLevelChartInstance.destroy();
  }

  const ctx = confidenceLevelChart.value.getContext('2d');
  if (!ctx) return;

  const confValue = Math.max(0, Math.min(100, Number(confidence)));
  const remaining = 100 - confValue;

  confidenceLevelChartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Confidence', 'Remaining'],
      datasets: [
        {
          data: [confValue, remaining],
          backgroundColor: ['rgba(33, 150, 243, 0.85)', 'rgba(200, 200, 200, 0.35)'],
          borderColor: ['rgba(33, 150, 243, 1)', 'rgba(200, 200, 200, 0.8)'],
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: 'Prediction Confidence',
        },
        legend: {
          position: 'bottom',
        },
      },
      cutout: '60%',
    },
  });
};

const createAllCharts = async () => {
  await nextTick();

  try {
    createAgeChart();
    createGenderChart();
    createTrendsChart();
    createSurgeChart();
    createMonthlyIllnessChart();
    createModelAccuracyChart();
    createConfidenceLevelChart();
  } catch (error) {
    console.error('Error creating charts:', error);
  }
};


const loadNotifications = async (): Promise<void> => {
  try {
    console.log('📬 Loading doctor notifications...');

    const response = await api.get('/operations/notifications/');
    notifications.value = response.data || [];

    console.log('✅ Doctor notifications loaded:', notifications.value.length);
  } catch (error: unknown) {
    console.error('❌ Error loading doctor notifications:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to load notifications',
    });
  }
};

const handleNotificationClick = (notification: Notification): void => {
  // Mark as read
  notification.is_read = true;

  // Update on backend
  void markNotificationAsRead(notification.id);
};

const markNotificationAsRead = async (notificationId: number): Promise<void> => {
  try {
    await api.patch(`/operations/notifications/${notificationId}/mark-read/`);
  } catch (error) {
    console.error('Error marking notification as read:', error);
  }
};

const markAllNotificationsRead = async (): Promise<void> => {
  try {
    // Mark all notifications as read locally
    notifications.value.forEach((notification) => {
      notification.is_read = true;
    });

    // Mark all notifications as read on backend
    await api.post('/operations/notifications/mark-all-read/');

    $q.notify({
      type: 'positive',
      message: 'All notifications marked as read',
    });
  } catch (error) {
    console.error('Error marking notifications as read:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to mark notifications as read',
    });
  }
};

// Zoom functionality functions
const showZoomedData = (type: string): void => {
  zoomedData.value = {
    type: type,
    visible: true,
  };
};

const hideZoomedData = (): void => {
  zoomedData.value = {
    type: null,
    visible: false,
  };
};

const formatTime = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
};

// Helper functions for illness predictions removed; using static icons in template

// Removed severity helpers; UI no longer displays severity badges

// Storage sync for AI recommendations removed; PDF includes AI content.

onMounted(() => {
  // Load notifications
  void loadNotifications();

  // Fetch analytics data
  void fetchDoctorAnalytics();

  // Refresh notifications every 30 seconds
  setInterval(() => void loadNotifications(), 30000);
});

onUnmounted(() => {
  // No storage listeners to remove after AI UI removal
});
</script>

<style scoped>
/* Safe Area Support */
.safe-area-top {
  padding-top: env(safe-area-inset-top);
}

.safe-area-bottom {
  padding-bottom: env(safe-area-inset-bottom);
}

/* Ensure mobile header is always visible on mobile devices */
@media (max-width: 768px) {
  .mobile-header-layout {
    display: flex !important;
  }

  .header-toolbar {
    display: none !important;
  }

  /* Force header visibility on iOS */
  .prototype-header {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    z-index: 2000 !important;
    padding-top: max(env(safe-area-inset-top), 8px) !important;
  }

  /* Ensure main content doesn't overlap header */
  .q-page {
    padding-top: calc(env(safe-area-inset-top) + 120px) !important;
  }
}

/* Responsive Design - Mobile and Web Support */
@media (max-width: 768px) {
  .mobile-header-layout {
    display: flex !important;
  }

  .header-toolbar {
    display: none !important;
  }

  /* Mobile header positioning */
  .prototype-header {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    z-index: 2000 !important;
    padding-top: max(env(safe-area-inset-top), 8px) !important;
  }

  /* Ensure main content doesn't overlap header */
  .q-page {
    padding-top: calc(env(safe-area-inset-top) + 120px) !important;
  }
}

/* Desktop Header Layout */
@media (min-width: 769px) {
  .mobile-header-layout {
    display: none;
  }

  .prototype-header .header-toolbar {
    display: flex;
  }
}

/* Global Modal Safe Area Support */
@media (max-width: 768px) {
  :deep(.q-dialog) {
    padding: 0 !important;
    margin: 0 !important;
  }

  :deep(.q-dialog__inner) {
    padding: max(env(safe-area-inset-top), 20px) max(env(safe-area-inset-right), 8px)
      max(env(safe-area-inset-bottom), 8px) max(env(safe-area-inset-left), 8px) !important;
    margin: 0 !important;
    min-height: 100vh !important;
    display: flex !important;
    align-items: flex-start !important;
    justify-content: center !important;
    padding-top: max(env(safe-area-inset-top), 20px) !important;
  }

  :deep(.q-dialog__inner > div) {
    max-height: calc(
      100vh - max(env(safe-area-inset-top), 20px) - max(env(safe-area-inset-bottom), 8px)
    ) !important;
    width: 100% !important;
    max-width: calc(
      100vw - max(env(safe-area-inset-left), 8px) - max(env(safe-area-inset-right), 8px)
    ) !important;
    margin: 0 !important;
  }
}

@media (max-width: 480px) {
  :deep(.q-dialog__inner) {
    padding: max(env(safe-area-inset-top), 24px) max(env(safe-area-inset-right), 4px)
      max(env(safe-area-inset-bottom), 4px) max(env(safe-area-inset-left), 4px) !important;
  }

  :deep(.q-dialog__inner > div) {
    max-height: calc(
      100vh - max(env(safe-area-inset-top), 24px) - max(env(safe-area-inset-bottom), 4px)
    ) !important;
    max-width: calc(
      100vw - max(env(safe-area-inset-left), 4px) - max(env(safe-area-inset-right), 4px)
    ) !important;
  }
}

/* Modal Close Button Styles */
.modal-close-btn {
  padding: 4px;
  transition: all 0.2s ease;
}

/* Desktop close button styling */
@media (min-width: 769px) {
  .modal-close-btn {
    padding: 6px;
    min-width: 36px;
    min-height: 36px;
    font-size: 18px;
  }

  .modal-close-btn:hover {
    background: rgba(0, 0, 0, 0.1);
    border-radius: 50%;
  }
}

/* Mobile close button styling */
@media (max-width: 768px) {
  .modal-close-btn {
    padding: 8px !important;
    min-width: 44px !important;
    min-height: 44px !important;
    font-size: 20px !important;
    background: rgba(0, 0, 0, 0.1) !important;
    border-radius: 50% !important;
  }

  .modal-close-btn:hover {
    background: rgba(0, 0, 0, 0.2) !important;
  }
}

@media (max-width: 480px) {
  .modal-close-btn {
    padding: 10px !important;
    min-width: 48px !important;
    min-height: 48px !important;
    font-size: 22px !important;
    background: rgba(0, 0, 0, 0.1) !important;
    border-radius: 50% !important;
  }

  .modal-close-btn:hover {
    background: rgba(0, 0, 0, 0.2) !important;
  }
}

/* Mobile Header Layout */
.mobile-header-layout {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.header-top-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  min-height: 48px;
}

.header-bottom-row {
  padding: 0 16px 8px;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  justify-content: center;
}

/* Time and Weather Display Styles */
.time-display {
  display: flex;
  align-items: center;
  gap: 4px;
  color: white;
  font-size: 12px;
}

.weather-display {
  display: flex;
  align-items: center;
  gap: 4px;
  color: white;
  font-size: 12px;
}

.weather-loading,
.weather-error {
  display: flex;
  align-items: center;
  gap: 4px;
  color: white;
  font-size: 12px;
}

.time-text,
.weather-text {
  font-weight: 500;
}

.weather-location {
  font-size: 10px;
  opacity: 0.8;
}

/* Prototype Header Styles */
.prototype-header {
  background: #286660;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header-toolbar {
  padding: 0 24px;
  min-height: 64px;
}

.menu-toggle-btn {
  color: white;
  margin-right: 16px;
}

.header-left {
  flex: 1;
  display: flex;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 24px;
}

.search-container {
  width: 100%;
  max-width: 500px;
}

.search-input {
  background: white;
  border-radius: 8px;
}

.notification-btn {
  color: white;
}

.time-display,
.weather-display,
.weather-loading,
.weather-error {
  display: flex;
  align-items: center;
  gap: 8px;
  color: white;
  font-size: 14px;
}

/* Prototype Sidebar Styles */
.prototype-sidebar {
  background: white;
  border-right: 1px solid #e0e0e0;
}

.sidebar-content {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.logo-section {
  padding: 20px;
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo-container {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  color: #286660;
}

.menu-btn {
  color: #666;
}

.sidebar-user-profile {
  padding: 24px 20px;
  border-bottom: 1px solid #e0e0e0;
  text-align: center;
}

.profile-picture-container {
  position: relative;
  display: inline-block;
  margin-bottom: 16px;
}

.upload-btn {
  position: absolute;
  bottom: 0;
  right: 0;
  transform: translate(25%, 25%);
}

.verified-badge {
  position: absolute;
  bottom: 0;
  right: 0;
  background: white;
  border-radius: 50%;
}

.user-name {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin: 0 0 4px 0;
}

.user-role {
  font-size: 14px;
  color: #666;
  margin: 0 0 12px 0;
}

.navigation-menu {
  flex: 1;
  padding: 16px 0;
}

.nav-item {
  margin: 4px 16px;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.nav-item.active {
  background: #286660;
  color: white;
}

.nav-item.active .q-icon {
  color: white;
}

.nav-item:hover:not(.active) {
  background: #f5f5f5;
}

.logout-section {
  padding: 20px;
  border-top: 1px solid #e0e0e0;
}

.logout-btn {
  width: 100%;
  border-radius: 8px;
  font-weight: 600;
  text-transform: uppercase;
}

/* Page Container with Off-White Background */
.page-container-with-fixed-header {
  background: #ffffff;
  min-height: 100vh;
  position: relative;
}

/* Greeting Section */
.greeting-section {
  padding: 24px;
  background: transparent;
}

.greeting-card {
  background: #ffffff;
  border-radius: 15px;
  border: 1px solid rgba(0, 0, 0, 0.05);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  overflow: hidden;
  position: relative;
  width: 100%;
  max-width: none;
  margin: 0;
}

.greeting-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #286660, #6ca299, #b8d2ce);
  border-radius: 16px 16px 0 0;
}

.greeting-content {
  padding: 24px;
}

.greeting-text {
  font-size: 28px;
  font-weight: 700;
  color: #333;
  margin: 0 0 8px 0;
}

.greeting-subtitle {
  font-size: 16px;
  color: #666;
  margin: 0;
}

/* Dashboard Cards Section */
.dashboard-cards-section {
  padding: 24px;
}

.dashboard-cards-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

/* Glassmorphism Dashboard Cards */
.dashboard-card {
  background: transparent;
  border-radius: 16px;
  border: none;
  box-shadow: none;
  transition: all 0.3s ease;
  cursor: pointer;
  overflow: hidden;
  position: relative;
}

.dashboard-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #286660, #6ca299, #b8d2ce);
  border-radius: 16px 16px 0 0;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.dashboard-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.15);
  background: rgba(255, 255, 255, 0.35);
}

.dashboard-card:hover::before {
  opacity: 1;
}

.card-content {
  padding: 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
}

.card-text {
  flex: 1;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
  line-height: 1.3;
}

.card-description {
  font-size: 14px;
  color: #666;
  line-height: 1.4;
}

.card-icon {
  margin-left: 16px;
  color: #286660;
  opacity: 0.8;
  transition: all 0.3s ease;
}

.dashboard-card:hover .card-icon {
  opacity: 1;
  transform: scale(1.1);
}

/* Card-specific colors */
.demographics-card .card-icon {
  color: #2196f3;
}
.prediction-card .card-icon {
  color: #ff9800;
}
.trends-card .card-icon {
  color: #4caf50;
}
.surge-card .card-icon {
  color: #f44336;
}

/* Zoom functionality styles */
.zoom-card {
  position: relative;
}

.zoomed-data-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  padding: 20px;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: zoomIn 0.3s ease-out;
}

.zoomed-content {
  text-align: center;
  width: 100%;
}

.zoomed-content h4 {
  color: #286660;
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 16px;
}

.zoomed-stats {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stat-row {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-label {
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.stat-value {
  font-size: 14px;
  color: #286660;
  font-weight: 600;
}

.gender-stats,
.conditions-list,
.trend-items {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.gender-item,
.condition-item {
  background: rgba(40, 102, 96, 0.1);
  color: #286660;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
}

.trend-item {
  background: rgba(76, 175, 80, 0.1);
  color: #4caf50;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
}

.trend-item.increasing {
  background: rgba(76, 175, 80, 0.1);
  color: #4caf50;
}

.risk-factors {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.risk-item {
  background: rgba(244, 67, 54, 0.1);
  color: #f44336;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
}

.no-data {
  color: #999;
  font-size: 14px;
  font-style: italic;
}

@keyframes zoomIn {
  from {
    opacity: 0;
    transform: scale(0.9);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

/* Analytics Section */
.analytics-section {
  padding: 24px;
}

.analytics-card {
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(0, 0, 0, 0.05);
  width: 100%;
  max-width: none;
  margin: 0;
}

.analytics-header {
  text-align: center;
  margin-bottom: 32px;
  padding: 24px 24px 0 24px;
}

.analytics-content {
  padding: 0 24px 24px 24px;
}

.analytics-title {
  font-size: 24px;
  font-weight: 700;
  color: #333;
  margin: 0 0 24px 0;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.analytics-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
}

.action-btn {
  border-radius: 8px;
  font-weight: 500;
  padding: 12px 24px;
  min-width: 160px;
}

/* Analytics Panels */
.analytics-panels-container {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-top: 20px;
}

/* Structured Grid Layout for Analytics Panels */
.structured-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-areas:
    'surge volume'
    'trends trends'
    'demographics gender';
  gap: 20px;
}

/* Map panels to grid areas */
.surge-panel { grid-area: surge; }
.prediction-panel { grid-area: volume; }
.trends-panel { grid-area: trends; }
.demographics-panel { grid-area: demographics; }
 .gender-panel { grid-area: gender; }
 
.integrated-analytics-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
  align-items: start;
  margin-top: 16px;
}
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-top: 8px;
}
.kpi-card {
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  border: 1px solid var(--card-border, rgba(0, 0, 0, 0.05));
  background: var(--card-bg, #ffffff);
  color: var(--card-fg, #111827);
  transition: background-color 250ms ease, border-color 250ms ease, color 250ms ease;
}
.kpi-body { padding: 14px; }
.kpi-label { font-size: 11px; color: var(--card-muted, #607d8b); font-weight: 700; text-transform: uppercase; letter-spacing: 0.4px; }
.kpi-value { font-size: 22px; font-weight: 800; color: var(--card-fg, #143b38); margin-top: 6px; }
.kpi-caption { font-size: 12px; color: var(--card-muted, #78909c); margin-top: 4px; }

.themed-card {
  background: var(--card-bg, #ffffff) !important;
  color: var(--card-fg, #111827);
  border-color: var(--card-border, rgba(0, 0, 0, 0.05)) !important;
  transition: background-color 250ms ease, border-color 250ms ease, color 250ms ease;
}
.themed-card:hover {
  background: var(--card-bg-hover, var(--card-bg, #ffffff)) !important;
}
.themed-card:active {
  background: var(--card-bg-active, var(--card-bg, #ffffff)) !important;
}
.integrated-main {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.integrated-top-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
.integrated-bottom-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
.integrated-card {
  width: 100%;
}
.integrated-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.integrated-card-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--card-fg, #333);
}
.integrated-card-body {
  margin-top: 12px;
}
.analytics-sidebar-panel { align-self: stretch; display: flex; flex-direction: column; height: 100%; }
 
 /* Fixed Right Sidebar Styles */
.fixed-right-sidebar {
  position: fixed;
  top: 96px;
  right: 16px;
  width: 320px;
  z-index: 1100;
}
.sidebar-card { 
  border-radius: 12px; 
  box-shadow: 0 6px 20px rgba(0,0,0,0.12);
 }
.sidebar-actions { 
  display: flex; 
  gap: 12px; 
  margin-top: 8px; 
}
.sidebar-btn { 
  flex: 1; 
}
.ai-summary-header { 
  font-weight: 700; 
  color: #1f3d3a; 
  margin-bottom: 8px; 
  font-size: 16px; 
  letter-spacing: 0.2px; 
}
.ai-summary-content { 
  color: #143b38; 
  font-size: 15px; 
}

/* Summary card layout */
.ai-summary-card { 
  border-radius: 12px; 
  box-shadow: 0 3px 12px rgba(0,0,0,0.08); 
  background: #ffffff;
  border: 1px solid rgba(0,0,0,0.05);
  padding: 12px; 
  min-height: 180px; 
  margin-top: 10px; 
}
.actions-row { 
  display: flex; 
  gap: 8px; 
  margin-bottom: 6px; 
}
.ai-summary-disclaimer { 
  color: #546E7A; 
  font-size: 14px; 
  margin-bottom: 12px; 
  line-height: 1.5; 
}
.ai-summary-text { color: #143b38; font-size: 14px; line-height: 1.5; white-space: pre-wrap; } 

/* Responsive adjustments for grid and sidebar */
@media (max-width: 1200px) {
  .structured-grid {
    grid-template-columns: 1fr 1fr;
    grid-template-areas:
      'surge volume'
      'trends trends'
      'demographics gender';
  }
}

@media (max-width: 768px) {
  .structured-grid {
    grid-template-columns: 1fr;
    grid-template-areas:
      'surge'
      'volume'
      'trends'
      'demographics'
      'gender';
  }
  .integrated-analytics-grid { grid-template-columns: 1fr; }
  .kpi-grid { grid-template-columns: 1fr 1fr; }
  .integrated-top-row { grid-template-columns: 1fr; }
  .integrated-bottom-row { grid-template-columns: 1fr; }
}

.analytics-panel {
  background: var(--card-bg, #ffffff);
  border-radius: 12px;
  border: 1px solid var(--card-border, #e9ecef);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  padding: 20px;
  min-height: 300px;
  color: var(--card-fg, #111827);
}

canvas {
  filter: none !important;
  image-rendering: auto;
}

.panel-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin-bottom: 16px;
  text-align: center;
}

.panel-content {
  height: 100%;
}

.analytics-data {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.data-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.data-label {
  font-weight: 600;
  color: #333;
  font-size: 14px;
}

.data-values {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.value-item {
  font-size: 13px;
  color: #666;
  padding: 4px 8px;
  background: white;
  border-radius: 4px;
  border-left: 3px solid #286660;
}

.empty-data {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #666;
}

.empty-data p {
  margin-top: 12px;
  font-size: 14px;
}

/* Responsive Design */
@media (max-width: 768px) {
  .dashboard-cards-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
  }

  .analytics-panels-container {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .greeting-text {
    font-size: 24px;
  }

  .card-content {
    padding: 20px;
  }

  .card-title {
    font-size: 16px;
  }

  .card-description {
    font-size: 13px;
  }

  .analytics-actions {
    flex-direction: column;
    align-items: center;
  }

  .action-btn {
    width: 100%;
    max-width: 200px;
  }
}

@media (max-width: 480px) {
  .dashboard-cards-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .greeting-text {
    font-size: 20px;
  }

  .card-content {
    padding: 16px;
  }

  .card-title {
    font-size: 15px;
  }

  .card-description {
    font-size: 12px;
  }
}

/* Chart Styles */
.chart-container {
  position: relative;
  height: 300px;
  margin: 20px 0;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 15px;
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

/* Improve readability specifically for summary stats */
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

.trend-analysis {
  margin-top: 20px;
}

.trend-section {
  margin-bottom: 15px;
}

.trend-section h5 {
  color: #286660;
  margin-bottom: 10px;
  font-size: 14px;
}

.trend-items {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.trend-item {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.trend-item.increasing {
  background: rgba(255, 99, 132, 0.2);
  color: #ff6384;
  border: 1px solid rgba(255, 99, 132, 0.3);
}

.trend-item.decreasing {
  background: rgba(75, 192, 192, 0.2);
  color: #4bc0c0;
  border: 1px solid rgba(75, 192, 192, 0.3);
}

.model-info {
  margin-top: 15px;
  padding: 15px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
}

.accuracy-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.accuracy-label {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.8);
}

.accuracy-value {
  font-size: 16px;
  font-weight: bold;
  color: #286660;
}

.risk-factors {
  margin-top: 15px;
}

.risk-factors h5 {
  color: #286660;
  margin-bottom: 10px;
  font-size: 14px;
}

.risk-factors ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.risk-factors li {
  padding: 8px 12px;
  margin: 5px 0;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.9);
  border-left: 3px solid #ff6384;
}

/* Statistical Summary Styles */
.statistical-summary {
  margin-top: 20px;
}

.stat-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
  margin-bottom: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 15px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  transition: all 0.3s ease;
}

.stat-card:hover {
  background: rgba(255, 255, 255, 0.15);
  transform: translateY(-2px);
}

.stat-icon {
  font-size: 24px;
  margin-right: 15px;
}

.stat-content {
  flex: 1;
}

.stat-title {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 5px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-value {
  font-size: 18px;
  font-weight: bold;
  color: #286660;
}

.analysis-result {
  margin: 20px 0;
  padding: 15px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  border-left: 4px solid #286660;
}

.analysis-result h5 {
  color: #286660;
  margin-bottom: 10px;
  font-size: 14px;
}

.result-text {
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;
  line-height: 1.5;
  margin: 0;
}

.significant-factors {
  margin-top: 15px;
}

.significant-factors h5 {
  color: #286660;
  margin-bottom: 10px;
  font-size: 14px;
}

.factors-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.factor-item {
  padding: 6px 12px;
  background: rgba(40, 102, 96, 0.2);
  color: #286660;
  border-radius: 16px;
  font-size: 12px;
  font-weight: 500;
  border: 1px solid rgba(40, 102, 96, 0.3);
}

/* Illness Prediction Styles */
.predicted-illnesses-section {
  margin: 20px 0;
}

.predicted-illnesses-section h5 {
  color: #286660;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
}

.illness-predictions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.illness-prediction-card {
  display: flex;
  align-items: center;
  padding: 16px;
  background: white;
  border-radius: 12px;
  border-left: 4px solid #ff9800;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.illness-prediction-card:hover {
  transform: translateX(4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.illness-icon {
  margin-right: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.illness-details {
  flex: 1;
}

.illness-name {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}

.illness-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #f44336;
}

.trend-text {
  font-weight: 500;
}

.illness-severity {
  margin-left: 16px;
}

/* Current Illnesses Styles */
.current-illnesses-section {
  margin: 20px 0;
}

.current-illnesses-section h5 {
  color: #286660;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
}

.current-illnesses-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.current-illness-item {
  display: flex;
  align-items: center;
  padding: 12px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  transition: all 0.2s ease;
}

.current-illness-item:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
}

.illness-rank {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: #286660;
  color: white;
  border-radius: 50%;
  font-weight: 700;
  font-size: 14px;
  margin-right: 12px;
}

.illness-name-text {
  flex: 1;
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.illness-count {
  font-size: 13px;
  color: #666;
  font-weight: 600;
  background: #f5f5f5;
  padding: 4px 12px;
  border-radius: 12px;
}

/* Responsive Chart Styles */
@media (max-width: 768px) {
  .chart-container {
    height: 250px;
    margin: 15px 0;
    padding: 10px;
  }

  .summary-stats {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .stat-item {
    padding: 10px;
  }

  .trend-items {
    flex-direction: column;
  }

  .stat-row {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .stat-card {
    padding: 12px;
  }

  .factors-list {
    flex-direction: column;
  }

  .illness-prediction-card {
    flex-direction: column;
    align-items: flex-start;
    padding: 12px;
  }

  .illness-icon {
    margin-bottom: 8px;
  }

  .illness-severity {
    margin-left: 0;
    margin-top: 8px;
  }

  .illness-name {
    font-size: 14px;
  }

  .current-illness-item {
    padding: 10px;
  }

  .illness-rank {
    width: 28px;
    height: 28px;
    font-size: 12px;
  }

  .illness-name-text {
    font-size: 13px;
  }

  .illness-count {
    font-size: 12px;
    padding: 3px 10px;
  }
}

/* Profile Avatar Styles - Circular Design */
.profile-avatar {
  border: 3px solid #1e7668 !important;
  border-radius: 50% !important;
  overflow: hidden !important;
}

.profile-avatar img {
  border-radius: 50% !important;
  width: 100% !important;
  height: 100% !important;
  object-fit: cover !important;
}

.profile-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #1e7668;
  color: white;
  font-size: 24px;
  font-weight: bold;
  border-radius: 50%;
}

.upload-btn {
  position: absolute;
  bottom: -5px;
  right: -5px;
  background: #1e7668 !important;
  border-radius: 50% !important;
  width: 24px !important;
  height: 24px !important;
  min-height: 24px !important;
  padding: 0 !important;
}

.verified-badge {
  position: absolute;
  top: -5px;
  right: -5px;
  background: white;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}

/* Notification styles */
.unread {
  background-color: rgba(25, 118, 210, 0.05);
  border-left: 3px solid #1976d2;
}

.unread .q-item-label {
  font-weight: 600;
}

/* Desktop Layout - Show desktop header, hide mobile */
@media (min-width: 769px) {
  .mobile-header-layout {
    display: none;
  }

  .prototype-header .header-toolbar {
    display: flex;
  }
}

/* Mobile Layout - Hide desktop header, show mobile */
@media (max-width: 768px) {
  .prototype-header {
    padding-top: max(env(safe-area-inset-top), 8px);
  }

  .header-toolbar {
    display: none;
  }

  .mobile-header-layout {
    padding: 8px 12px;
    padding-top: max(env(safe-area-inset-top), 8px);
  }

  .header-top-row {
    padding: 4px 12px;
    min-height: 44px;
  }

  .header-bottom-row {
    padding: 0 12px 6px;
  }

  .header-info {
    gap: 8px;
  }

  .time-display,
  .weather-display,
  .weather-loading,
  .weather-error {
    font-size: 11px;
  }

  .time-text,
  .weather-text {
    font-size: 11px;
  }

  .weather-location {
    font-size: 9px;
  }

  /* Hide time display on mobile to save space */
  .time-display {
    display: none;
  }

  /* Make weather display more compact */
  .weather-display {
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
  }

  .weather-location {
    display: none;
  }
}

@media (max-width: 480px) {
  .prototype-header {
    padding-top: max(env(safe-area-inset-top), 12px);
  }

  .mobile-header-layout {
    padding: 6px 8px;
    padding-top: max(env(safe-area-inset-top), 12px);
  }

  .header-top-row {
    padding: 2px 8px;
    min-height: 40px;
  }

  .header-bottom-row {
    padding: 0 8px 4px;
  }

  .header-info {
    gap: 6px;
  }

  .time-display,
  .weather-display,
  .weather-loading,
  .weather-error {
    font-size: 10px;
  }

  .time-text,
  .weather-text {
    font-size: 10px;
  }

  /* Make weather even more compact */
  .weather-display {
    flex-direction: row;
    align-items: center;
    gap: 2px;
  }

  .weather-location {
    display: none;
  }
}


/* Forecast answer text */
.forecast-answer { margin-top: 8px; color: #546E7A; font-size: 14px; }

</style>
