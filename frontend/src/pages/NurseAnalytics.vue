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
            <div class="row q-gutter-md">
              <q-btn
                color="primary"
                icon="refresh"
                label="Refresh Data"
                @click="refreshAnalytics"
                unelevated
              />
              <q-btn
                color="secondary"
                icon="picture_as_pdf"
                label="Download Report"
                @click="generatePDFReport"
                unelevated
              />
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
              <div class="analytics-panels-container structured-grid">
                <div class="analytics-panel medication-panel">
                  <h4 class="panel-title">Medication Analysis</h4>
                  <div class="panel-content">
                    <!-- Filter Bar: top medications selector -->
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
                              text: 'Most Prescribed Medications',
                              font: { size: 16, weight: 'bold' }
                            }
                          }
                        }" 
                      />
                    </div>
                    <div v-else class="empty-data">
                      <div class="empty-state">
                        <q-icon name="medication" size="48px" color="grey-5" />
                        <p>No medication analysis data available</p>
                        <p class="empty-subtitle">
                          Data will appear here once medication patterns are analyzed
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                <div class="analytics-panel demographics-panel">
                  <h4 class="panel-title">Patient Demographics (Age)</h4>
                  <div class="panel-content">
                    <div v-if="analyticsData.patient_demographics" class="demographics-charts">
                      <div class="chart-section">
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
                        </div>
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
                </div>

                <div class="analytics-panel gender-panel">
                  <h4 class="panel-title">Patient Demographics (Gender)</h4>
                  <div class="panel-content">
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

                <div class="analytics-panel trends-panel">
                  <h4 class="panel-title">Health Trends</h4>
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
                    </div>
                    <div v-else class="empty-data">
                      <div class="empty-state">
                        <q-icon name="trending_up" size="48px" color="grey-5" />
                        <p>No health trends data available</p>
                        <p class="empty-subtitle">Health trend analysis will appear here</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div class="analytics-panel volume-panel prediction-panel">
                  <h4 class="panel-title">Patient Volume Prediction</h4>
                  <div class="panel-content">
                    <!-- Filter Bar: time range selector -->
                    <div class="filter-bar q-mb-sm">
                      <div class="row items-center q-gutter-sm">
                        <div class="col-auto text-subtitle2">Time Range</div>
                        <div class="col-auto">
                          <q-btn-toggle
                            v-model="timeRangeNurse"
                            toggle-color="primary"
                            size="sm"
                            :options="[
                              { label: '3M', value: '3m' },
                              { label: '6M', value: '6m' },
                              { label: '12M', value: '12m' },
                              { label: 'All', value: 'all' }
                            ]"
                          />
                        </div>
                      </div>
                    </div>
                    <div v-if="analyticsData.volume_prediction" class="volume-prediction-content">
                      <div class="chart-container">
                        <Line 
                          :data="volumePredictionChartData" 
                          :options="{
                            ...chartOptions,
                            plugins: {
                              ...chartOptions.plugins,
                              title: {
                                display: true,
                                text: 'Predicted vs Actual Patient Volume',
                                font: { size: 16, weight: 'bold' }
                              },
                              legend: {
                                display: true,
                                position: 'bottom'
                              }
                            }
                          }" 
                        />
                      </div>
                    </div>
                    <div v-else class="empty-data">
                      <div class="empty-state">
                        <q-icon name="analytics" size="48px" color="grey-5" />
                        <p>No volume prediction data available</p>
                        <p class="empty-subtitle">Patient volume forecasting will appear here</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </q-card-section>
          </q-card>
        </div>

        <div class="dashboard-sidebar-section">
          <div class="analytics-sidebar-panel">
            <q-card bordered flat class="ai-summary-card">
              <q-card-section class="actions-row">
                <q-btn color="primary" label="Generate PDF Report" icon="picture_as_pdf" size="md" @click="generatePDFReport" class="sidebar-btn" />
                <q-btn color="secondary" label="Refresh Data" icon="refresh" size="md" @click="refreshAnalytics" class="sidebar-btn" />
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
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useQuasar } from 'quasar';
import { api } from '../boot/axios';
import NurseHeader from 'src/components/NurseHeader.vue';
import NurseSidebar from 'src/components/NurseSidebar.vue';
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

const $q = useQuasar();

const rightDrawerOpen = ref(false);

// Filters
const timeRangeNurse = ref<'3m' | '6m' | '12m' | 'all'>('3m');
const topMedCount = ref<number>(5);

const limitByRange = (len: number): number => {
  switch (timeRangeNurse.value) {
    case '3m':
      return Math.min(3, len);
    case '6m':
      return Math.min(6, len);
    case '12m':
      return Math.min(12, len);
    case 'all':
    default:
      return len;
  }
};

interface MedicationAnalysis {
  medication_pareto_data?: Array<{
    medication: string;
    frequency: number;
    cumulative_percentage: number;
  }>;
}

interface PatientDemographics {
  age_distribution?: { [key: string]: number };
  gender_proportions?: { [key: string]: number };
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

interface MedicineSearchResult {
  id: number | string;
  medicine_name?: string;
  name?: string;
  stock_quantity?: number;
  current_stock?: number;
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
      sections.push(['Medication Highlights', `• Top meds: ${top}.`].join('\n'));
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
  const medications = medsAll
    .slice()
    .sort((a, b) => Number(b.frequency || 0) - Number(a.frequency || 0))
    .slice(0, topMedCount.value);
  
  return {
    labels: medications.map(med => med.medication),
    datasets: [
      {
        label: 'Prescriptions',
        data: medications.map(med => med.frequency),
        backgroundColor: [
          '#9c27b0',
          '#2196f3',
          '#4caf50',
          '#ff9800',
          '#f44336',
        ],
        borderColor: [
          '#7b1fa2',
          '#1976d2',
          '#388e3c',
          '#f57c00',
          '#d32f2f',
        ],
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
  
  return {
    labels: Object.keys(genders),
    datasets: [
      {
        data: Object.values(genders),
        backgroundColor: ['#2196f3', '#e91e63'],
        borderColor: ['#1976d2', '#c2185b'],
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
  
  return {
    labels: Object.keys(ageGroups),
    datasets: [
      {
        label: 'Patients',
        data: Object.values(ageGroups),
        backgroundColor: '#4caf50',
        borderColor: '#388e3c',
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
  
  return {
    labels: conditions.map(condition => condition.medical_condition),
    datasets: [
      {
        label: 'Cases',
        data: conditions.map(condition => condition.count),
        backgroundColor: '#ff9800',
        borderColor: '#f57c00',
        borderWidth: 1,
      },
    ],
  };
});

const volumePredictionChartData = computed(() => {
  if (!analyticsData.value.volume_prediction) {
    return { labels: [], datasets: [] };
  }
  
  const data = analyticsData.value.volume_prediction;
  
  if (data.forecasted_data && Array.isArray(data.forecasted_data)) {
    const count = limitByRange(data.forecasted_data.length);
    const sliced = data.forecasted_data.slice(0, count);
    const labels = sliced.map((item) => item.date);
    const predictedVolume = sliced.map((item) => item.predicted_volume);
    const actualVolume = sliced.map((item) => item.actual_volume !== undefined ? item.actual_volume : null);
    
    return {
      labels,
      datasets: [
        {
          label: 'Predicted Volume',
          data: predictedVolume,
          borderColor: '#2196f3',
          backgroundColor: 'rgba(33, 150, 243, 0.1)',
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointRadius: 4,
          pointBackgroundColor: '#2196f3',
        },
        {
          label: 'Actual Volume',
          data: actualVolume,
          borderColor: '#4caf50',
          backgroundColor: 'rgba(76, 175, 80, 0.1)',
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointRadius: 4,
          pointBackgroundColor: '#4caf50',
        },
      ],
    };
  }
  
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
  const predictedVolume = [45, 52, 48, 55, 60, 58];
  const actualVolume = [42, 50, 46, 52, 58, 56];
  
  return {
    labels: months,
    datasets: [
      {
        label: 'Predicted Volume',
        data: predictedVolume,
        borderColor: '#2196f3',
        backgroundColor: 'rgba(33, 150, 243, 0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: '#2196f3',
      },
      {
        label: 'Actual Volume',
        data: actualVolume,
        borderColor: '#4caf50',
        backgroundColor: 'rgba(76, 175, 80, 0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: '#4caf50',
      },
    ],
  };
});

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
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
      const [patientsResponse, doctorsResponse, medicinesResponse] = await Promise.all([
        api.get(`/users/nurse/patients/?search=${encodeURIComponent(searchValue)}`),
        api.get(`/operations/available-doctors/?search=${encodeURIComponent(searchValue)}`),
        api.get(`/operations/medicine-inventory/?search=${encodeURIComponent(searchValue)}`),
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
        ...(doctorsResponse.data || []).map((item: DoctorSearchResult) => ({
          type: 'doctor',
          data: {
            id: item.id,
            name: item.full_name || item.name || 'Unknown Doctor',
            specialization: item.specialization || 'General',
          },
        })),
        ...(medicinesResponse.data || []).map((item: MedicineSearchResult) => ({
          type: 'medicine',
          data: {
            id: item.id,
            name: item.medicine_name || item.name || 'Unknown Medicine',
            stock: item.stock_quantity || item.current_stock || 0,
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
    const response = await api.get('/analytics/nurse/');
    const data = response.data?.data || {};

    if (data.volume_prediction && !data.volume_prediction.forecasted_data) {
      const cmp = data.volume_prediction.comparison_data as Array<{
        date: string;
        Forecasted?: number;
        forecasted?: number;
        Actual?: number;
      }>;
      if (Array.isArray(cmp)) {
        data.volume_prediction.forecasted_data = cmp.map((item) => ({
          date: item.date,
          predicted_volume: Number(item.Forecasted ?? item.forecasted ?? 0),
          actual_volume: typeof item.Actual !== 'undefined' ? Number(item.Actual) : undefined,
        }));
      }
    }

    if (!data.volume_prediction) {
      data.volume_prediction = {
        evaluation_metrics: {
          mae: 3.2,
          rmse: 4.8,
        },
        forecasted_data: [
          { date: '2024-01', predicted_volume: 45, actual_volume: 42 },
          { date: '2024-02', predicted_volume: 52, actual_volume: 50 },
          { date: '2024-03', predicted_volume: 48, actual_volume: 46 },
          { date: '2024-04', predicted_volume: 55, actual_volume: 52 },
          { date: '2024-05', predicted_volume: 60, actual_volume: 58 },
          { date: '2024-06', predicted_volume: 58, actual_volume: 56 },
        ],
      };
    }

    analyticsData.value = data;
    console.log('Nurse analytics loaded:', analyticsData.value);
  } catch (error) {
    console.error('Failed to fetch nurse analytics:', error);
    analyticsData.value = {
      medication_analysis: {
        medication_pareto_data: [
          { medication: 'Paracetamol', frequency: 45, cumulative_percentage: 32.1 },
          { medication: 'Ibuprofen', frequency: 32, cumulative_percentage: 54.9 },
          { medication: 'Amoxicillin', frequency: 28, cumulative_percentage: 74.9 },
          { medication: 'Aspirin', frequency: 22, cumulative_percentage: 90.6 },
          { medication: 'Metformin', frequency: 18, cumulative_percentage: 100.0 },
        ],
      },
      patient_demographics: {
        age_distribution: {
          '0-18': 15,
          '19-35': 45,
          '36-50': 30,
          '51-65': 25,
          '65+': 20,
        },
        gender_proportions: {
          Male: 52,
          Female: 48,
        },
      },
      health_trends: {
        top_illnesses_by_week: [
          { medical_condition: 'Common Cold', count: 12, date_of_admission: '2024-01-15' },
          { medical_condition: 'Hypertension', count: 8, date_of_admission: '2024-01-15' },
          { medical_condition: 'Diabetes', count: 6, date_of_admission: '2024-01-15' },
          { medical_condition: 'Allergies', count: 4, date_of_admission: '2024-01-15' },
          { medical_condition: 'Asthma', count: 3, date_of_admission: '2024-01-15' },
        ],
      },
      volume_prediction: {
        evaluation_metrics: {
          mae: 3.2,
          rmse: 4.8,
        },
        forecasted_data: [
          { date: '2024-01', predicted_volume: 45, actual_volume: 42 },
          { date: '2024-02', predicted_volume: 52, actual_volume: 50 },
          { date: '2024-03', predicted_volume: 48, actual_volume: 46 },
          { date: '2024-04', predicted_volume: 55, actual_volume: 52 },
          { date: '2024-05', predicted_volume: 60, actual_volume: 58 },
          { date: '2024-06', predicted_volume: 58, actual_volume: 56 },
        ],
      },
    };

    $q.notify({
      type: 'warning',
      message: 'Failed to load latest analytics data. Displaying mock data.',
      position: 'top',
      timeout: 3000,
    });
  }
};

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

const refreshAnalytics = async () => {
  $q.notify({
    type: 'info',
    message: 'Refreshing analytics data...',
    position: 'top',
    timeout: 1000,
  });
  await fetchNurseAnalytics();
  $q.notify({
    type: 'positive',
    message: 'Analytics data refreshed!',
    position: 'top',
    timeout: 1000,
  });
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
  backdrop-filter: blur(10px);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 20px;
}
.verification-card {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
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
  background: #f8f9fa;
}

.page-container-with-fixed-header {
  background: #f8f9fa;
  min-height: 100vh;
  position: relative;
}

.greeting-section {
  padding: 24px 24px 0 24px;
  background: transparent;
}
.greeting-card {
  background: #fff;
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
  background: #fdfdfd;
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

/* Main Charts Grid (LEFT SIDE) */
.analytics-panels-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-areas:
    'surge volume'
    'trends trends'
    'demographics gender';
  gap: 20px;
}
.analytics-panel {
  padding: 24px;
  background-color: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  border: 1px solid #e0e0e0;
  min-height: 350px;
  display: flex;
  flex-direction: column;
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
.medication-panel {
  grid-area: surge;
}
.volume-panel,
.prediction-panel {
  grid-area: volume;
}
.trends-panel {
  grid-area: trends;
}
.demographics-panel {
  grid-area: demographics;
}
.gender-panel {
  grid-area: gender;
}

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
  .analytics-panels-container {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 768px) {
  .greeting-section {
    padding: 16px 16px 0 16px;
  }
  .analytics-layout-container {
    padding: 16px;
  }
  /* Charts become single column on small screens */
  .analytics-panels-container {
    grid-template-columns: 1fr;
    grid-template-areas:
      'surge'
      'volume'
      'trends'
      'demographics'
      'gender';
  }
  .analytics-panel {
    min-height: 300px;
  }
  .chart-container {
    height: 200px;
  }
}
</style>