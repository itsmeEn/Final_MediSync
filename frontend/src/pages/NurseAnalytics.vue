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
                  <q-card class="analytics-panel integrated-card medication-panel themed-card" :style="cardStyle('nurse.card.medication')">
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
                    </q-card-section>
                  </q-card>

                  <q-card class="analytics-panel integrated-card volume-panel prediction-panel themed-card" :style="cardStyle('nurse.card.volume')">
                    <q-card-section>
                      <div class="integrated-card-title">Patient Volume Prediction</div>
                      <div class="panel-content">
                        <div v-if="analyticsData.volume_prediction" class="volume-prediction-content">
                          <PatientVolumeComparisonChart :forecasted-data="analyticsData.volume_prediction?.forecasted_data || []" />
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

                <q-card class="analytics-panel integrated-card trends-panel themed-card" :style="cardStyle('nurse.card.trends')">
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

                <q-card class="analytics-panel integrated-card demographics-panel themed-card" :style="cardStyle('nurse.card.demographics')">
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
            <q-card bordered flat class="ai-summary-card themed-card" :style="cardStyle('nurse.card.ai')">
              <q-card-section class="actions-row">
                <q-btn color="accent" label="Customize Colors" icon="palette" size="md" @click="showCardColorCustomizer = true" class="sidebar-btn" />
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

      <CardColorConfigurator
        v-model="showCardColorCustomizer"
        :cards="cardCustomizerCards"
      />

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
import CardColorConfigurator from 'src/components/analytics/CardColorConfigurator.vue';
import PatientVolumeComparisonChart from 'src/components/analytics/PatientVolumeComparisonChart.vue';
import { useCardTheme } from 'src/composables/useCardTheme';
import { Bar, Doughnut } from 'vue-chartjs';
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
const { cardStyle } = useCardTheme();

const showCardColorCustomizer = ref(false);
const cardCustomizerCards = [
  { id: 'nurse.card.medication', label: 'Medication Analysis' },
  { id: 'nurse.card.volume', label: 'Patient Volume Prediction' },
  { id: 'nurse.card.trends', label: 'Health Trends' },
  { id: 'nurse.card.demographics', label: 'Patient Demographics' },
  { id: 'nurse.card.ai', label: 'AI Summary' },
];

const rightDrawerOpen = ref(false);

// Filters
const topMedCount = ref<number>(5);

interface MedicationAnalysis {
  medication_pareto_data?: Array<{
    medication: string;
    frequency?: number;
    prescriptions?: number;
    count?: number;
    cumulative_percentage?: number;
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
        label: 'Prescriptions',
        data: medications.map(med => medCount(med)),
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
      api.get('/analytics/patient-volume/'),
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

// REMOVED: showZoomedData, hideZoomedData, viewMedicationAnalysis, viewDemographics, viewHealthTrends, viewVolumePrediction methods

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
