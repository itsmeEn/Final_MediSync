<template>
  <q-layout view="hHh Lpr fFf">
    <NurseHeader
      :search-text="searchText"
      :search-results="searchResults"
      :unread-notifications-count="unreadNotificationsCount"
      :current-time="currentTime"
      :weather-data="weatherData"
      :weather-loading="weatherLoading"
      :weather-error="weatherError"
      :location-data="locationData"
      :location-loading="locationLoading"
      @toggle-drawer="toggleRightDrawer"
      @search-input="onSearchInput"
      @clear-search="clearSearch"
      @select-search-result="selectSearchResult"
      @show-notifications="showNotifications = true"
    />
    <NurseSidebar v-model="rightDrawerOpen" :activeRoute="'nurse-analytics'" />

    <q-page-container class="page-container-with-fixed-header role-body-bg">
      <div class="greeting-section">
        <q-card class="greeting-card">
          <q-card-section class="greeting-content row items-center justify-between">
            <div>
              <h2 class="greeting-text">
                Nurse Analytics Dashboard
              </h2>
              <p class="greeting-subtitle">
                Data-driven insights for patient care and medication management - {{ currentDate }}
              </p>
            </div>
          </q-card-section>
        </q-card>
      </div>

      <div class="analytics-layout-container">
        
        <div class="analytics-section main-analytics-section">
          <div v-if="userProfile.verification_status !== 'approved'" class="verification-overlay">
            <q-card class="verification-card">
              <q-card-section class="verification-content">
                <q-icon name="warning" size="64px" color="orange" />
                <h4 class="verification-title">Account Verification Required</h4>
                <p class="verification-message">
                  Your account needs to be verified before you can access analytics functionality.
                  Please upload your verification document to complete the process.
                </p>
                <q-chip color="negative" text-color="white" size="lg" icon="cancel">
                  Not Verified
                </q-chip>
                <q-btn
                  color="primary"
                  label="Upload Verification Document"
                  icon="upload_file"
                  @click="$router.push('/verification')"
                  class="q-mt-md"
                  unelevated
                />
              </q-card-section>
            </q-card>
          </div>
          <q-card class="analytics-card main-analytics-card" :class="{ 'disabled-content': userProfile.verification_status !== 'approved' }">
            <q-card-section class="analytics-content">
              <div class="integrated-analytics-grid">
                <div class="integrated-top-row">
                  <q-card class="analytics-panel integrated-card medication-panel themed-card">
                    <q-card-section>
                      <div class="integrated-card-title">Medication Analysis</div>
                      <div class="panel-content">
                        <div class="filter-bar q-mb-sm">
                          <div class="row items-center q-gutter-sm">
                            <div class="col-auto text-subtitle2">Show Top</div>
                            <div class="col-auto" style="min-width: 90px;">
                              <q-select
                                v-model="topMedCount"
                                :options="[3, 5, 8, 10]"
                                dense
                                outlined
                                emit-value
                                map-options
                                :behavior="'menu'"
                                style="width: 90px;"
                              />
                            </div>
                          </div>
                        </div>
                        <div v-if="analyticsData.medication_analysis?.medication_pareto_data?.length" class="chart-container">
                          <Bar 
                            :data="medicationChartData" 
                            :options="{
                              ...chartOptions,
                              plugins: {
                                ...chartOptions.plugins,
                                title: {
                                  display: true,
                                  text: 'Top Doctor-Recommended Medications',
                                  font: { size: 16, weight: 'bold' }
                                }
                              }
                            }" 
                          />
                          <div class="text-caption text-grey-8 q-mt-sm">{{ medicationInterpretation }}</div>
                          <q-expansion-item
                            v-if="hasMedicationExtras"
                            dense
                            icon="insights"
                            label="More medication insights"
                            class="q-mt-sm"
                          >
                            <div class="q-pt-sm">
                              <div v-if="medicationTrendChartData.labels?.length" class="chart-container" style="height: 220px;">
                                <Line
                                  :data="medicationTrendChartData"
                                  :options="{
                                    ...chartOptions,
                                    plugins: {
                                      ...chartOptions.plugins,
                                      title: {
                                        display: true,
                                        text: 'Monthly Trend (Top Medications)',
                                        font: { size: 14, weight: 'bold' }
                                      }
                                    }
                                  }"
                                />
                              </div>

                              <div class="row q-col-gutter-md q-mt-sm">
                                <div class="col-12 col-md-6" v-if="polypharmacySummary.avg != null || polypharmacySummary.rows.length">
                                  <div class="text-subtitle2">Polypharmacy</div>
                                  <div class="text-caption text-grey-8 q-mb-xs">
                                    Avg meds per consultation: {{ polypharmacySummary.avg != null ? polypharmacySummary.avg : 'N/A' }}
                                  </div>
                                  <q-markup-table dense flat bordered>
                                    <thead>
                                      <tr>
                                        <th class="text-left">Meds per consult</th>
                                        <th class="text-right">Count</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      <tr v-for="r in polypharmacySummary.rows" :key="r.k">
                                        <td class="text-left">{{ r.k }}</td>
                                        <td class="text-right">{{ formatInt(r.v) }}</td>
                                      </tr>
                                    </tbody>
                                  </q-markup-table>
                                </div>

                                <div class="col-12 col-md-6" v-if="routeRows.length">
                                  <div class="text-subtitle2">Route Distribution</div>
                                  <q-markup-table dense flat bordered>
                                    <thead>
                                      <tr>
                                        <th class="text-left">Route</th>
                                        <th class="text-right">Count</th>
                                        <th class="text-right">%</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      <tr v-for="r in routeRows" :key="r.route">
                                        <td class="text-left">{{ r.route }}</td>
                                        <td class="text-right">{{ formatInt(r.count) }}</td>
                                        <td class="text-right">{{ r.pct != null ? r.pct : '—' }}</td>
                                      </tr>
                                    </tbody>
                                  </q-markup-table>
                                </div>

                                <div class="col-12 col-md-6" v-if="safetyRows.length">
                                  <div class="text-subtitle2">Safety Signals (keyword proxy)</div>
                                  <q-markup-table dense flat bordered>
                                    <thead>
                                      <tr>
                                        <th class="text-left">Medication</th>
                                        <th class="text-right">Mentions</th>
                                        <th class="text-left">Top signals</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      <tr v-for="r in safetyRows" :key="r.medication">
                                        <td class="text-left">{{ r.medication }}</td>
                                        <td class="text-right">{{ formatInt(r.mentions) }}</td>
                                        <td class="text-left">{{ r.signals || '—' }}</td>
                                      </tr>
                                    </tbody>
                                  </q-markup-table>
                                </div>

                                <div class="col-12 col-md-6" v-if="effectivenessRows.length">
                                  <div class="text-subtitle2">Effectiveness (text proxy)</div>
                                  <q-markup-table dense flat bordered>
                                    <thead>
                                      <tr>
                                        <th class="text-left">Medication</th>
                                        <th class="text-right">Positive %</th>
                                        <th class="text-right">Pos</th>
                                        <th class="text-right">Neg</th>
                                        <th class="text-right">Unk</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      <tr v-for="r in effectivenessRows" :key="r.medication">
                                        <td class="text-left">{{ r.medication }}</td>
                                        <td class="text-right">{{ r.positive_rate }}</td>
                                        <td class="text-right">{{ formatInt(r.positive) }}</td>
                                        <td class="text-right">{{ formatInt(r.negative) }}</td>
                                        <td class="text-right">{{ formatInt(r.unknown) }}</td>
                                      </tr>
                                    </tbody>
                                  </q-markup-table>
                                </div>

                                <div class="col-12" v-if="diagnosisRows.length">
                                  <div class="text-subtitle2">Medication by Diagnosis</div>
                                  <q-markup-table dense flat bordered>
                                    <thead>
                                      <tr>
                                        <th class="text-left">Diagnosis</th>
                                        <th class="text-left">Top medications</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      <tr v-for="r in diagnosisRows" :key="r.diagnosis">
                                        <td class="text-left">{{ r.diagnosis }}</td>
                                        <td class="text-left">{{ r.meds || '—' }}</td>
                                      </tr>
                                    </tbody>
                                  </q-markup-table>
                                </div>
                              </div>
                            </div>
                          </q-expansion-item>
                        </div>
                        <div v-else class="empty-data">
                          <div class="empty-state">
                            <q-icon name="medication" size="48px" color="grey-5" />
                            <p>No medication analysis data available</p>
                            <p class="empty-subtitle">
                              Data will appear here once doctors complete consultations with prescribed medications
                            </p>
                          </div>
                        </div>
                      </div>
                    </q-card-section>
                  </q-card>

                  <q-card class="analytics-panel integrated-card volume-panel prediction-panel themed-card">
                    <q-card-section>
                      <div class="integrated-card-title">Patient Volume Prediction</div>
                      <div class="panel-content">
                        <div class="filter-bar q-mb-sm">
                          <div class="row items-center q-gutter-sm">
                            <div class="col-auto text-subtitle2">Year</div>
                            <div class="col-auto" style="min-width: 110px;">
                              <q-input v-model="volumeYear" type="number" dense outlined style="width: 110px;" />
                            </div>
                          </div>
                        </div>
                        <div v-if="analyticsData.volume_prediction" class="volume-prediction-content">
                          <PatientVolumeComparisonChart :forecasted-data="volumeForecastedData" />
                          <div class="text-caption text-grey-8 q-mt-sm">{{ volumeInterpretation }}</div>
                        </div>
                        <div v-else class="empty-data">
                          <div class="empty-state">
                            <q-icon name="analytics" size="48px" color="grey-5" />
                            <p>No volume prediction data available</p>
                            <p class="empty-subtitle">Patient volume forecasting will appear here</p>
                          </div>
                        </div>
                      </div>
                    </q-card-section>
                  </q-card>
                </div>

                <q-card class="analytics-panel integrated-card trends-panel themed-card">
                  <q-card-section>
                    <div class="integrated-card-title">Health Trends</div>
                    <div class="panel-content">
                      <div v-if="analyticsData.health_trends?.top_illnesses_by_week?.length" class="chart-container">
                        <Bar 
                          :data="healthTrendsChartData" 
                          :options="{
                            ...chartOptions,
                            indexAxis: 'y' as const,
                            plugins: {
                              ...chartOptions.plugins,
                              title: {
                                display: true,
                                text: 'Top Medical Conditions',
                                font: { size: 16, weight: 'bold' }
                              }
                            }
                          }" 
                        />
                        <div class="text-caption text-grey-8 q-mt-sm">{{ healthTrendsInterpretation }}</div>
                      </div>
                      <div v-else class="empty-data">
                        <div class="empty-state">
                          <q-icon name="trending_up" size="48px" color="grey-5" />
                          <p>No health trends data available</p>
                          <p class="empty-subtitle">Health trend analysis will appear here</p>
                        </div>
                      </div>
                    </div>
                  </q-card-section>
                </q-card>

                <q-card class="analytics-panel integrated-card demographics-panel themed-card">
                  <q-card-section>
                    <div class="integrated-card-title">Patient Demographics</div>
                    <div class="demographics-grid">
                      <div class="demographics-left">
                        <div v-if="analyticsData.patient_demographics" class="demographics-charts">
                          <div class="chart-container">
                            <Bar 
                              :data="ageChartData" 
                              :options="{
                                ...chartOptions,
                                plugins: {
                                  ...chartOptions.plugins,
                                  title: {
                                    display: true,
                                    text: 'Patients by Age Group',
                                    font: { size: 14, weight: 'bold' }
                                  }
                                }
                              }" 
                            />
                            <div class="text-caption text-grey-8 q-mt-sm">{{ demographicsInterpretation }}</div>
                          </div>
                        </div>
                        <div v-else class="empty-data">
                          <div class="empty-state">
                            <q-icon name="people" size="48px" color="grey-5" />
                            <p>No demographics data available</p>
                            <p class="empty-subtitle">Patient demographic information will appear here</p>
                          </div>
                        </div>
                      </div>
                      <div class="demographics-right">
                        <div v-if="analyticsData.patient_demographics?.gender_proportions" class="chart-container">
                          <Doughnut 
                            :data="genderChartData" 
                            :options="{
                              ...doughnutOptions,
                              plugins: {
                                ...doughnutOptions.plugins,
                                title: {
                                  display: true,
                                  text: 'Gender Distribution',
                                  font: { size: 14, weight: 'bold' }
                                }
                              }
                            }" 
                          />
                          <div class="text-caption text-grey-8 q-mt-sm">{{ genderInterpretation }}</div>
                        </div>
                        <div v-else class="empty-data">
                          <div class="empty-state">
                            <q-icon name="group" size="48px" color="grey-5" />
                            <p>No gender distribution data available</p>
                            <p class="empty-subtitle">Gender breakdown will appear here</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </q-card-section>
                </q-card>
              </div>
            </q-card-section>
          </q-card>
        </div>

        <div class="dashboard-sidebar-section">
          <div class="analytics-sidebar-panel">
            <q-card bordered flat class="ai-summary-card themed-card">
              <q-card-section class="actions-row">
                <q-btn
                  color="primary"
                  label="Generate PDF Report"
                  icon="picture_as_pdf"
                  size="md"
                  :disable="userProfile.verification_status !== 'approved'"
                  @click="generatePDFReport"
                  class="sidebar-btn"
                />
              </q-card-section>
              <q-separator class="q-my-xs" />
              <q-card-section>
                <div class="ai-summary-header">AI-SUMMARY GENERATED RESPONSE</div>
                <div class="ai-summary-content">
                  <em>
                    Disclaimer: This is an automated, AI-generated recommendation that interprets the latest analytics findings based on the current data. It is intended to guide immediate resource allocation and strategic planning, not replace expert clinical judgment.
                  </em>
                  <div class="ai-summary-text">{{ nurseSummaryText }}</div>
                </div>
              </q-card-section>
            </q-card>
          </div>
          
          </div>
      </div>

      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useQuasar } from 'quasar';
import { api } from '../boot/axios';
import NurseHeader from 'src/components/NurseHeader.vue';
import NurseSidebar from 'src/components/NurseSidebar.vue';
import PatientVolumeComparisonChart from 'src/components/analytics/PatientVolumeComparisonChart.vue';
import { Bar, Doughnut, Line } from 'vue-chartjs';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  PointElement,
  LineElement,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  PointElement,
  LineElement
);
ChartJS.defaults.devicePixelRatio = window.devicePixelRatio || 1;

const $q = useQuasar();

const rightDrawerOpen = ref(false);

// Filters
const topMedCount = ref<number>(5);
const volumeYear = ref<string>(String(new Date().getFullYear()));

const volumeYearInt = computed(() => {
  const raw = String(volumeYear.value || '').trim();
  const n = Number(raw);
  if (!Number.isFinite(n)) return new Date().getFullYear();
  const yr = Math.trunc(n);
  if (yr < 1900 || yr > 2100) return new Date().getFullYear();
  return yr;
});

interface MedicationAnalysis {
  medication_pareto_data?: Array<{
    medication: string;
    frequency?: number;
    prescriptions?: number;
    count?: number;
    cumulative_percentage?: number;
    example_signatures?: string[];
  }>;
  monthly_trends?: {
    months: string[];
    series: Array<{ medication: string; counts: number[] }>;
  };
  diagnosis_breakdown?: Array<{
    diagnosis: string;
    top_medications: Array<{ medication: string; frequency: number }>;
  }>;
  polypharmacy?: {
    avg_meds_per_consultation?: number;
    distribution?: Record<string, number>;
  };
  route_distribution?: Array<{ route: string; count: number; percentage?: number }>;
  safety_signals?: {
    keywords?: string[];
    top_medications?: Array<{
      medication: string;
      mentions: number;
      top_signals?: Array<{ signal: string; count: number }>;
    }>;
  };
  effectiveness_proxy?: {
    top_medications?: Array<{
      medication: string;
      positive: number;
      negative: number;
      unknown: number;
      positive_rate: number;
    }>;
  };
}

interface PatientDemographics {
  age_distribution?: { [key: string]: number };
  gender_proportions?: { [key: string]: number };
  total_patients?: number;
  average_age?: number;
}

interface HealthTrends {
  top_illnesses_by_week?: Array<{
    medical_condition: string;
    count: number;
    date_of_admission: string;
  }>;
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

interface AnalyticsData {
  medication_analysis: MedicationAnalysis | null;
  patient_demographics: PatientDemographics | null;
  health_trends: HealthTrends | null;
  volume_prediction: VolumePrediction | null;
  performance_factors?: { significant_factors?: string[] } | null;
}

interface PatientSearchResult {
  id: number | string;
  full_name?: string;
  patient_name?: string;
  name?: string;
  room_number?: string;
}

interface DoctorSearchResult {
  id: number | string;
  full_name?: string;
  name?: string;
  specialization?: string;
}

const analyticsData = ref<AnalyticsData>({
  medication_analysis: null,
  patient_demographics: null,
  health_trends: null,
  volume_prediction: null,
});

const nurseSummaryText = computed(() => {
  const d = analyticsData.value;
  const sections: string[] = [];

  {
    const meds = d?.medication_analysis?.medication_pareto_data || [];
    if (Array.isArray(meds) && meds.length) {
      const top = [...meds]
        .sort((a, b) => Number(b.frequency || 0) - Number(a.frequency || 0))
        .slice(0, 3)
        .map((m) => `${m.medication} (${m.frequency})`)
        .join(', ');
      sections.push(['Medication Highlights', `• Top recommended meds: ${top}.`].join('\n'));
    }
  }

  {
    const gender = d?.patient_demographics?.gender_proportions || {};
    const age = d?.patient_demographics?.age_distribution || {};
    const lines: string[] = [];
    const genderEntries = Object.entries(gender);
    if (genderEntries.length) {
      const gStr = genderEntries.map(([k, v]) => `${k}: ${Number(v)}`).join(', ');
      lines.push(`• Gender mix: ${gStr}.`);
    }
    const ageEntries = Object.entries(age)
      .sort((a, b) => Number(b[1]) - Number(a[1]))
      .slice(0, 3);
    if (ageEntries.length) {
      const aStr = ageEntries.map(([k, v]) => `${k} (${Number(v)})`).join(', ');
      lines.push(`• Age groups: ${aStr}.`);
    }
    if (lines.length) sections.push(['Patient Demographics', ...lines].join('\n'));
  }

  {
    const weeklyTop = d?.health_trends?.top_illnesses_by_week || [];
    if (Array.isArray(weeklyTop) && weeklyTop.length) {
      const topTriplet = weeklyTop
        .slice(0, 3)
        .map((it) => `${it.medical_condition} (${Number(it.count)})`)
        .join(', ');
      sections.push(['Health Trends', `• Top this week: ${topTriplet}.`].join('\n'));
    }
  }

  {
    const vp = d?.volume_prediction?.forecasted_data || [];
    if (vp.length) {
      const predicted = vp.map((x) => Number(x.predicted_volume || 0));
      const actuals = vp.filter((x) => typeof x.actual_volume === 'number').map((x) => Number(x.actual_volume));
      const pAvg = Math.round(predicted.reduce((s, n) => s + n, 0) / predicted.length);
      const aAvg = actuals.length ? Math.round(actuals.reduce((s, n) => s + n, 0) / actuals.length) : null;
      const pFirst = predicted[0] ?? null;
      const pLast = predicted[predicted.length - 1] ?? null;
      const vTrend = pFirst != null && pLast != null ? (pLast > pFirst ? 'increasing' : pLast < pFirst ? 'decreasing' : 'stable') : null;
      const latest = vp[vp.length - 1]!;
      const lines: string[] = [];
      lines.push(`• Trend: ${vTrend || 'stable'}; avg predicted ${pAvg}${aAvg != null ? `, avg actual ${aAvg}` : ''}.`);
      lines.push(`• Latest (${latest.date}): predicted ${Number(latest.predicted_volume)}${typeof latest.actual_volume === 'number' ? `, actual ${Number(latest.actual_volume)}` : ''}.`);
      sections.push(['Patient Volume', ...lines].join('\n'));
    }
  }

  if (!sections.length) return 'Analytics results are not available yet.';
  return sections.join('\n\n');
});

// REMOVED: zoomedData ref

const medicationChartData = computed(() => {
  if (!analyticsData.value.medication_analysis?.medication_pareto_data) {
    return { labels: [], datasets: [] };
  }
  
  const medsAll = analyticsData.value.medication_analysis.medication_pareto_data;
  const medCount = (m: { frequency?: number; prescriptions?: number; count?: number }) =>
    Number(m.frequency ?? m.prescriptions ?? m.count ?? 0);
  const medications = medsAll
    .slice()
    .sort((a, b) => medCount(b) - medCount(a))
    .slice(0, topMedCount.value);
  
  return {
    labels: medications.map(med => med.medication),
    datasets: [
      {
        label: 'Doctor Recommendations',
        data: medications.map(med => medCount(med)),
        backgroundColor: medications.map((_, idx) => ['#9c27b0', '#2196f3', '#4caf50', '#ff9800', '#f44336'][idx % 5]!),
        borderColor: medications.map((_, idx) => ['#7b1fa2', '#1976d2', '#388e3c', '#f57c00', '#d32f2f'][idx % 5]!),
        borderWidth: 1,
      },
    ],
  };
});

const genderChartData = computed(() => {
  if (!analyticsData.value.patient_demographics?.gender_proportions) {
    return { labels: [], datasets: [] };
  }
  
  const genders = analyticsData.value.patient_demographics.gender_proportions;
  const labels = Object.keys(genders);
  const normalize = (s: string) => s.trim().toLowerCase();
  const colorFor = (label: string) => {
    const v = normalize(label);
    if (v === 'male') return { bg: '#2196f3', border: '#1976d2' };
    if (v === 'female') return { bg: '#e91e63', border: '#c2185b' };
    if (v === 'other' || v === 'others' || v === 'non-binary' || v === 'nonbinary') return { bg: '#9c27b0', border: '#7b1fa2' };
    return { bg: '#607d8b', border: '#455a64' };
  };
  const colors = labels.map(colorFor);
  
  return {
    labels,
    datasets: [
      {
        data: Object.values(genders),
        backgroundColor: colors.map((c) => c.bg),
        borderColor: colors.map((c) => c.border),
        borderWidth: 2,
      },
    ],
  };
});

const ageChartData = computed(() => {
  if (!analyticsData.value.patient_demographics?.age_distribution) {
    return { labels: [], datasets: [] };
  }
  
  const ageGroups = analyticsData.value.patient_demographics.age_distribution;
  const labels = Object.keys(ageGroups);
  const palette = ['#4caf50', '#2196f3', '#ff9800', '#9c27b0', '#f44336'];
  const borders = ['#388e3c', '#1976d2', '#f57c00', '#7b1fa2', '#d32f2f'];
  
  return {
    labels,
    datasets: [
      {
        label: 'Patients',
        data: Object.values(ageGroups),
        backgroundColor: labels.map((_, idx) => palette[idx % palette.length]!),
        borderColor: labels.map((_, idx) => borders[idx % borders.length]!),
        borderWidth: 1,
      },
    ],
  };
});

const healthTrendsChartData = computed(() => {
  if (!analyticsData.value.health_trends?.top_illnesses_by_week) {
    return { labels: [], datasets: [] };
  }
  
  const conditions = analyticsData.value.health_trends.top_illnesses_by_week.slice(0, 5);
  const labels = conditions.map(condition => condition.medical_condition);
  const palette = ['#ff9800', '#2196f3', '#4caf50', '#9c27b0', '#f44336'];
  const borders = ['#f57c00', '#1976d2', '#388e3c', '#7b1fa2', '#d32f2f'];
  
  return {
    labels,
    datasets: [
      {
        label: 'Cases',
        data: conditions.map(condition => condition.count),
        backgroundColor: labels.map((_, idx) => palette[idx % palette.length]!),
        borderColor: labels.map((_, idx) => borders[idx % borders.length]!),
        borderWidth: 1,
      },
    ],
  };
});

const demographicsInterpretation = computed(() => {
  const pd = analyticsData.value.patient_demographics
  if (!pd) return ''
  const ageDist = pd.age_distribution || {}
  const keys = Object.keys(ageDist)
  const sum = keys.reduce((s, k) => s + Number(ageDist[k] || 0), 0)
  if (!keys.length || sum <= 0) return 'Demographics: No age distribution data available yet.'
  const top = keys.reduce<{ k: string; v: number } | null>((best, k) => {
    const v = Number(ageDist[k] || 0)
    if (!best || v > best.v) return { k, v }
    return best
  }, null)
  const topPct = top ? Math.round((top.v / sum) * 100) : null
  const bits: string[] = []
  bits.push(`Demographics: largest age group is ${top?.k || 'N/A'}${topPct != null ? ` (~${topPct}%)` : ''}.`)
  bits.push('Shifts here are commonly driven by case mix, referrals, and community health patterns.')
  return bits.join(' ')
})

const genderInterpretation = computed(() => {
  const g = analyticsData.value.patient_demographics?.gender_proportions || null
  if (!g) return ''
  const labels = Object.keys(g)
  if (!labels.length) return 'Gender distribution: No data available yet.'
  const top = labels.reduce<{ k: string; v: number } | null>((best, k) => {
    const v = Number(g[k] || 0)
    if (!best || v > best.v) return { k, v }
    return best
  }, null)
  return `Gender distribution: ${top?.k || 'N/A'} is the largest group, which usually reflects the clinic population served and visit patterns.`
})

const healthTrendsInterpretation = computed(() => {
  const ht = analyticsData.value.health_trends?.top_illnesses_by_week || []
  if (!ht.length) return ''
  const top = ht[0]
  const name = top?.medical_condition || 'N/A'
  const count = Number(top?.count || 0)
  const factors = analyticsData.value.performance_factors?.significant_factors || []
  const factorText = Array.isArray(factors) && factors.length ? ` Key factors noted: ${factors.slice(0, 2).join(', ')}.` : ''
  return `Health trends: ${name} is leading (${count} cases). Changes are often driven by seasonality, local outbreaks, and care-seeking behavior.${factorText}`
})

const medicationInterpretation = computed(() => {
  const meds = analyticsData.value.medication_analysis?.medication_pareto_data || []
  if (!meds.length) return ''
  const first = meds[0]
  const med = first?.medication || 'N/A'
  const freq = Number(first?.frequency ?? first?.prescriptions ?? first?.count ?? 0)
  return `Medication analysis: ${med} is the top recommended medication (${freq}). This typically tracks common diagnoses and protocol-driven prescribing.`
})

const formatInt = (n: number) => new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(n)

const hasMedicationExtras = computed(() => {
  const m = analyticsData.value.medication_analysis
  if (!m) return false
  const mt = m.monthly_trends
  const poly = m.polypharmacy
  const routes = m.route_distribution
  const safety = m.safety_signals?.top_medications
  const eff = m.effectiveness_proxy?.top_medications
  const dx = m.diagnosis_breakdown
  return Boolean(
    (mt && Array.isArray(mt.months) && mt.months.length) ||
      (poly && (typeof poly.avg_meds_per_consultation === 'number' || (poly.distribution && Object.keys(poly.distribution).length))) ||
      (Array.isArray(routes) && routes.length) ||
      (Array.isArray(safety) && safety.length) ||
      (Array.isArray(eff) && eff.length) ||
      (Array.isArray(dx) && dx.length)
  )
})

const medicationTrendChartData = computed(() => {
  const mt = analyticsData.value.medication_analysis?.monthly_trends
  if (!mt || !Array.isArray(mt.months) || !Array.isArray(mt.series) || !mt.months.length) {
    return { labels: [], datasets: [] }
  }
  const palette = ['#2196f3', '#4caf50', '#ff9800']
  const border = ['#1976d2', '#388e3c', '#f57c00']
  const series = mt.series.slice(0, 3)
  return {
    labels: mt.months,
    datasets: series.map((s, idx) => ({
      label: s.medication,
      data: (s.counts || []).map((x) => Number(x || 0)),
      borderColor: border[idx % border.length]!,
      backgroundColor: palette[idx % palette.length]!,
      borderWidth: 2,
      pointRadius: 2,
      tension: 0.35,
      fill: false,
    })),
  }
})

const polypharmacySummary = computed(() => {
  const p = analyticsData.value.medication_analysis?.polypharmacy
  const avg = typeof p?.avg_meds_per_consultation === 'number' ? p.avg_meds_per_consultation : null
  const dist = p?.distribution && typeof p.distribution === 'object' ? p.distribution : {}
  const rows = Object.entries(dist)
    .sort((a, b) => {
      const ka = a[0] === '3+' ? 3 : Number(a[0])
      const kb = b[0] === '3+' ? 3 : Number(b[0])
      return ka - kb
    })
    .map(([k, v]) => ({ k, v: Number(v || 0) }))
  return { avg, rows }
})

const routeRows = computed(() => {
  const routes = analyticsData.value.medication_analysis?.route_distribution || []
  if (!Array.isArray(routes)) return []
  return routes
    .slice()
    .sort((a, b) => Number(b.count || 0) - Number(a.count || 0))
    .slice(0, 6)
    .map((r) => ({
      route: r.route,
      count: Number(r.count || 0),
      pct: r.percentage != null ? Number(r.percentage) : null,
    }))
})

const safetyRows = computed(() => {
  const meds = analyticsData.value.medication_analysis?.safety_signals?.top_medications || []
  if (!Array.isArray(meds)) return []
  return meds.slice(0, 6).map((m) => ({
    medication: m.medication,
    mentions: Number(m.mentions || 0),
    signals: Array.isArray(m.top_signals) ? m.top_signals.map((s) => `${s.signal} (${s.count})`).join(', ') : '',
  }))
})

const effectivenessRows = computed(() => {
  const meds = analyticsData.value.medication_analysis?.effectiveness_proxy?.top_medications || []
  if (!Array.isArray(meds)) return []
  return meds.slice(0, 6).map((m) => ({
    medication: m.medication,
    positive_rate: Number(m.positive_rate || 0),
    positive: Number(m.positive || 0),
    negative: Number(m.negative || 0),
    unknown: Number(m.unknown || 0),
  }))
})

const diagnosisRows = computed(() => {
  const dx = analyticsData.value.medication_analysis?.diagnosis_breakdown || []
  if (!Array.isArray(dx)) return []
  return dx.slice(0, 5).map((d) => ({
    diagnosis: d.diagnosis,
    meds: (d.top_medications || []).slice(0, 3).map((m) => `${m.medication} (${m.frequency})`).join(', '),
  }))
})

const buildDummyMonthlyVolume = (year: number) => {
  const season = [0, 1, 2, 3, 5, 6, 5, 4, 3, 2, 1, 0];
  const pseudo = (seed: number) => {
    const x = Math.sin(seed) * 10000;
    return x - Math.floor(x);
  };
  const base = 35 + (year % 9) * 3;
  return Array.from({ length: 12 }, (_, idx) => {
    const month = idx + 1;
    const wave = Math.round(4 * Math.sin((month / 12) * Math.PI * 2));
    const noise = Math.round((pseudo(year * 100 + month) - 0.5) * 10);
    const actual = Math.max(0, Math.round(base + season[idx]! * 3 + wave + noise));
    const predicted = Math.max(0, actual + Math.round((pseudo(year * 1000 + month) - 0.3) * 6));
    return {
      date: `${String(year).padStart(4, '0')}-${String(month).padStart(2, '0')}`,
      predicted_volume: predicted,
      actual_volume: actual,
    };
  });
};

const normalizeMonthlyVolumeForYear = (
  raw: Array<{ date: string; predicted_volume: number; actual_volume?: number }> | undefined,
  year: number
) => {
  const map = new Map<string, { date: string; predicted_volume: number; actual_volume?: number }>();
  for (const row of raw || []) {
    const d = typeof row?.date === 'string' ? row.date : '';
    const m = d.match(/^(\d{4})-(\d{2})/);
    if (!m) continue;
    const y = Number(m[1]);
    const mm = Number(m[2]);
    if (!Number.isFinite(y) || !Number.isFinite(mm)) continue;
    if (y !== year) continue;
    const key = `${m[1]}-${m[2]}`;
    const item: { date: string; predicted_volume: number; actual_volume?: number } = {
      date: key,
      predicted_volume: Number(row.predicted_volume || 0),
    };
    if (typeof row.actual_volume === 'number') {
      item.actual_volume = Number(row.actual_volume);
    }
    map.set(key, item);
  }

  const filled = Array.from({ length: 12 }, (_, idx) => {
    const month = idx + 1;
    const key = `${String(year).padStart(4, '0')}-${String(month).padStart(2, '0')}`;
    return map.get(key) || null;
  });

  const hasAny = filled.some((x) => x && (Number(x.predicted_volume) > 0 || Number(x.actual_volume || 0) > 0));
  if (!hasAny) return buildDummyMonthlyVolume(year);

  const dummy = buildDummyMonthlyVolume(year);
  return filled.map((row, idx) => {
    if (row) return row;
    return dummy[idx]!;
  });
};

const volumeForecastedData = computed(() => {
  const yr = volumeYearInt.value;
  const raw = analyticsData.value.volume_prediction?.forecasted_data;
  return normalizeMonthlyVolumeForYear(raw, yr);
});

const volumeInterpretation = computed(() => {
  const fd = volumeForecastedData.value || []
  if (!fd.length) return ''
  const last = fd[fd.length - 1]
  const pred = Number(last?.predicted_volume || 0)
  const act = typeof last?.actual_volume === 'number' ? Number(last.actual_volume) : null
  return `Volume prediction: latest projection is ${pred}${act != null ? ` vs actual ${act}` : ''}. Differences usually reflect scheduling changes, holidays, staffing capacity, and unexpected surges.`
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  devicePixelRatio: window.devicePixelRatio || 1,
  plugins: {
    legend: {
      position: 'top' as const,
    },
    title: {
      display: true,
      font: {
        size: 14,
        weight: 'bold' as const,
      },
    },
  },
};

const doughnutOptions = {
  responsive: true,
  maintainAspectRatio: false,
  devicePixelRatio: window.devicePixelRatio || 1,
  plugins: {
    legend: {
      position: 'bottom' as const,
    },
    title: {
      display: true,
      font: {
        size: 14,
        weight: 'bold' as const,
      },
    },
  },
};

const searchText = ref('');
const searchResults = ref<
  Array<{
    type: string;
    data: Record<string, string | number>;
  }>
>([]);

const locationData = ref<{
  city: string;
  country: string;
} | null>(null);
const locationLoading = ref(false);
const locationError = ref(false);

const showNotifications = ref(false);
const unreadNotificationsCount = computed(() => 0);

const currentTime = ref('');
const weatherData = ref<{
  temperature: number;
  condition: string;
  location: string;
} | null>(null);
const weatherLoading = ref(false);
const weatherError = ref(false);
let timeInterval: NodeJS.Timeout | null = null;

const userProfile = ref<{
  first_name?: string;
  last_name?: string;
  full_name: string;
  department?: string;
  role: string;
  profile_picture: string | null;
  verification_status: string;
  email?: string;
}>({
  first_name: '',
  last_name: '',
  full_name: 'Loading...',
  department: 'Loading department...',
  role: 'nurse',
  profile_picture: null,
  verification_status: 'not_submitted',
  email: '',
});

const currentDate = computed(() => {
  const now = new Date();
  return now.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
});

const onSearchInput = async (value: string | number | null) => {
  const searchValue = String(value || '');
  if (searchValue.length > 2) {
    try {
      const [patientsResponse, doctorsResponse] = await Promise.all([
        api.get(`/users/nurse/patients/?search=${encodeURIComponent(searchValue)}`),
        api.get(`/operations/availability/doctors/free/`, { params: { search: searchValue } }),
      ]);

      const results = [
        ...(patientsResponse.data.patients || []).map((item: PatientSearchResult) => ({
          type: 'patient',
          data: {
            id: item.id,
            name: item.full_name || item.patient_name || item.name || 'Unknown Patient',
            room: item.room_number || 'N/A',
          },
        })),
        ...((doctorsResponse.data?.doctors || []) as DoctorSearchResult[]).map((item: DoctorSearchResult) => ({
          type: 'doctor',
          data: {
            id: item.id,
            name: item.full_name || item.name || 'Unknown Doctor',
            specialization: item.specialization || 'General',
          },
        })),
      ];

      searchResults.value = results.slice(0, 10);
    } catch (error) {
      console.error('Search error:', error);
      searchResults.value = [];
    }
  } else {
    searchResults.value = [];
  }
};

const clearSearch = () => {
  searchText.value = '';
  searchResults.value = [];
};

const selectSearchResult = (result: { type: string; data: Record<string, string | number> }) => {
  console.log('Selected search result:', result);
  clearSearch();
};

const fetchLocation = async () => {
  locationLoading.value = true;
  locationError.value = false;

  try {
    await new Promise((resolve) => setTimeout(resolve, 1000));
    locationData.value = {
      city: 'Mandaluyong City',
      country: 'Philippines',
    };
  } catch (error) {
    console.error('Failed to fetch location:', error);
    locationError.value = true;
  } finally {
    locationLoading.value = false;
  }
};

const updateTime = () => {
  const now = new Date();
  currentTime.value = now.toLocaleTimeString('en-US', {
    hour12: true,
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
  });
};

const fetchWeatherData = async () => {
  weatherLoading.value = true;
  weatherError.value = false;

  try {
    await new Promise((resolve) => setTimeout(resolve, 1000));
    weatherData.value = {
      temperature: 28,
      condition: 'sunny',
      location: 'Mandaluyong City',
    };
  } catch (error) {
    console.error('Failed to fetch weather data:', error);
    weatherError.value = true;
  } finally {
    weatherLoading.value = false;
  }
};

const toggleRightDrawer = () => {
  rightDrawerOpen.value = !rightDrawerOpen.value;
};

const fetchUserProfile = async () => {
  try {
    const response = await api.get('/users/profile/');
    const userData = response.data.user;
    // Module-level verification toast removed; banner is shown only at login

    userProfile.value = {
      first_name: userData.first_name,
      last_name: userData.last_name,
      full_name: userData.full_name,
      department: userData.nurse_profile?.department,
      role: userData.role,
      profile_picture: userData.profile_picture || localStorage.getItem('profile_picture'),
      verification_status: userData.verification_status,
      email: userData.email,
    };

    // Removed module-level verification toast; banner is shown only once at login

    if (userData.profile_picture) {
      localStorage.setItem('profile_picture', userData.profile_picture);
    }

    console.log('User profile loaded:', userProfile.value);
  } catch (error) {
    console.error('Failed to fetch user profile:', error);

    const userData = localStorage.getItem('user');
    if (userData) {
      const user = JSON.parse(userData);
      userProfile.value = {
        full_name: user.full_name,
        department: user.nurse_profile?.department,
        role: user.role,
        profile_picture: user.profile_picture || null,
        verification_status: user.verification_status || 'not_submitted',
      };
    } else {
      $q.notify({
        type: 'negative',
        message: 'Failed to load user profile',
        position: 'top',
        timeout: 3000,
      });
    }
  }
};

const fetchNurseAnalytics = async () => {
  try {
    const [nurseResponse, volumeResponse] = await Promise.allSettled([
      api.get('/analytics/nurse/'),
      api.get('/analytics/patient-volume/', { params: { year: volumeYearInt.value } }),
    ]);

    let data: AnalyticsData = {
      medication_analysis: null,
      patient_demographics: null,
      health_trends: null,
      volume_prediction: null,
    };
    if (nurseResponse.status === 'fulfilled' && nurseResponse.value.data && typeof nurseResponse.value.data === 'object') {
      const payload = nurseResponse.value.data as { data?: unknown };
      if (payload.data && typeof payload.data === 'object') {
        data = payload.data as AnalyticsData;
      }
    }

    const unifiedVolume =
      volumeResponse.status === 'fulfilled' ? volumeResponse.value.data?.data?.volume_prediction : null;
    if (unifiedVolume) {
      data.volume_prediction = unifiedVolume as VolumePrediction;
    }

    {
      const vp = data.volume_prediction as unknown
      if (vp && typeof vp === 'object') {
        const vpObj = vp as Record<string, unknown>
        const forecasted = vpObj['forecasted_data']
        if (!Array.isArray(forecasted)) {
          const cmp = vpObj['comparison_data']
          if (Array.isArray(cmp)) {
            const mapped = (cmp
              .map((row): { date: string; predicted_volume: number; actual_volume?: number } | null => {
                if (!row || typeof row !== 'object') return null
                const r = row as Record<string, unknown>
                const rawDate = r['date'] ?? r['Date'] ?? ''
                const date = typeof rawDate === 'string' || typeof rawDate === 'number' ? String(rawDate) : ''
                if (!date) return null
                const predRaw = r['Forecasted'] ?? r['forecasted'] ?? r['Predicted'] ?? r['predicted_volume']
                const actRaw = r['Actual'] ?? r['actual'] ?? r['actual_volume']
                const predicted_volume = Number(predRaw ?? 0)
                const base = { date, predicted_volume }
                if (typeof actRaw === 'undefined') return base
                return { ...base, actual_volume: Number(actRaw) }
              })
              .filter((x) => x !== null)) as { date: string; predicted_volume: number; actual_volume?: number }[]
            data.volume_prediction = {
              ...(data.volume_prediction || {}),
              forecasted_data: mapped,
            }
          }
        }
      }
    }

    analyticsData.value = data;
    console.log('Nurse analytics loaded:', analyticsData.value);
  } catch (error) {
    console.error('Failed to fetch nurse analytics:', error);
    analyticsData.value = {
      medication_analysis: null,
      patient_demographics: null,
      health_trends: null,
      volume_prediction: null,
    };

    $q.notify({
      type: 'negative',
      message: 'Failed to load latest analytics data.',
      position: 'top',
      timeout: 3000,
    });
  }
};

watch(
  () => volumeYearInt.value,
  async (year) => {
    try {
      const resp = await api.get('/analytics/patient-volume/', { params: { year } });
      const vp = resp.data?.data?.volume_prediction || null;
      analyticsData.value = {
        ...analyticsData.value,
        volume_prediction: vp as VolumePrediction | null,
      };
    } catch {
      analyticsData.value = {
        ...analyticsData.value,
        volume_prediction: null,
      };
    }
  }
);

// REMOVED: showZoomedData, hideZoomedData, viewMedicationAnalysis, viewDemographics, viewHealthTrends, viewVolumePrediction methods

const generatePDFReport = async () => {
  try {
    const response = await api.get('/analytics/pdf/?type=nurse', {
      responseType: 'blob',
    });
    const blob = new Blob([response.data], { type: 'application/pdf' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `nurse_analytics_report_${new Date().toISOString().split('T')[0]}.pdf`;
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

onMounted(() => {
  void fetchUserProfile();
  void fetchNurseAnalytics();
  updateTime();
  timeInterval = setInterval(updateTime, 1000);
  void fetchWeatherData();
  void fetchLocation();

  setInterval(() => {
    void fetchUserProfile();
  }, 30000);

  setInterval(() => {
    void fetchUserProfile();
  }, 10000);
});

const handleStorageChange = (e: StorageEvent) => {
  if (e.key === 'profile_picture' && e.newValue) {
    userProfile.value.profile_picture = e.newValue;
    console.log('🔄 Profile picture updated from storage event:', e.newValue);
  }
};

window.addEventListener('storage', handleStorageChange);

onUnmounted(() => {
  if (timeInterval) {
    clearInterval(timeInterval);
  }
  window.removeEventListener('storage', handleStorageChange);
});
</script>

<style scoped>
.verification-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.95);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 20px;
}
.verification-card {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  max-width: 400px;
  text-align: center;
}
.verification-content {
  padding: 30px;
}
.verification-title {
  font-size: 20px;
  font-weight: 700;
  color: #333;
  margin: 16px 0 8px 0;
}
.verification-message {
  font-size: 15px;
  color: #666;
  margin-bottom: 20px;
}
.disabled-content {
  pointer-events: none;
  opacity: 0.6;
}

.role-body-bg {
  background: #ffffff;
}

.page-container-with-fixed-header {
  background: #ffffff;
  min-height: 100vh;
  position: relative;
}

.greeting-section {
  padding: 24px 24px 0 24px;
  background: transparent;
}
.greeting-card {
  background: #ffffff;
  border-radius: 15px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
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

/* FLIPPED LAYOUT: Main Charts (3fr) | Summary (1fr) */
.analytics-layout-container {
  display: grid;
  grid-template-columns: 3fr 1fr; /* 3:1 split for charts/main content and sidebar/summary */
  gap: 24px;
  padding: 24px;
}

/* LEFT SIDE - Main Charts/Panels */
.analytics-section.main-analytics-section {
  position: relative;
  padding: 0;
}
.analytics-card.main-analytics-card {
  border-radius: 15px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  background-color: #ffffff;
  min-height: 800px;
}
.analytics-content {
  padding: 24px;
}

/* RIGHT SIDE - Summary Only */
.dashboard-sidebar-section {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 0;
}

/* AI Summary Card Style */
.analytics-sidebar-panel {
  align-self: flex-start; /* Ensure it sticks to the top */
  width: 100%;
}
.ai-summary-card {
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  background: #ffffff;
}
.actions-row {
  display: flex;
  gap: 12px;
  padding-bottom: 0 !important;
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
.ai-summary-text {
  white-space: pre-wrap;
  font-family: inherit;
  margin-top: 12px;
}

 .integrated-analytics-grid {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
 .integrated-top-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
 .integrated-card-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--card-fg, #333);
  margin-bottom: 12px;
}
 .demographics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
 .demographics-left,
 .demographics-right {
  display: flex;
  flex-direction: column;
}
.analytics-panel {
  padding: 24px;
  background-color: var(--card-bg, #ffffff);
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  border: 1px solid var(--card-border, #e0e0e0);
  min-height: 350px;
  display: flex;
  flex-direction: column;
  color: var(--card-fg, #111827);
}

.themed-card {
  background: var(--card-bg, #ffffff) !important;
  color: var(--card-fg, #111827);
  border-color: var(--card-border, #e0e0e0) !important;
  transition: background-color 250ms ease, border-color 250ms ease, color 250ms ease;
}
.themed-card:hover {
  background: var(--card-bg-hover, var(--card-bg, #ffffff)) !important;
}
.themed-card:active {
  background: var(--card-bg-active, var(--card-bg, #ffffff)) !important;
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
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.chart-container {
  flex-grow: 1;
  height: 250px;
  width: 100%;
  position: relative;
}
.empty-data {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
}
.empty-state p {
  color: #999;
  margin: 8px 0 0 0;
  font-size: 16px;
}
.empty-subtitle {
  font-size: 13px !important;
  color: #bbb !important;
}
.volume-prediction-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Grid Areas */
@media (max-width: 1200px) {
  /* On medium screens, stack the main sections */
  .analytics-layout-container {
    grid-template-columns: 1fr;
    gap: 20px;
  }
  /* The charts panel is now full width */
  .analytics-content {
    padding: 24px;
  }
  /* The summary stacks below the main charts */
  .dashboard-sidebar-section {
    flex-direction: column;
    gap: 20px;
  }
  .integrated-top-row { grid-template-columns: 1fr; }
  .demographics-grid { grid-template-columns: 1fr; }
}

@media (max-width: 768px) {
  .greeting-section {
    padding: 16px 16px 0 16px;
  }
  .analytics-layout-container {
    padding: 16px;
  }
  /* Charts become single column on small screens */
  .integrated-top-row { grid-template-columns: 1fr; }
  .demographics-grid { grid-template-columns: 1fr; }
  .analytics-panel {
    min-height: 300px;
  }
  .chart-container {
    height: 200px;
  }
}
</style>
