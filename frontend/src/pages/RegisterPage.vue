<template>
  <div class="register-page safe-area-top safe-area-bottom">
    <div class="register-container">
      <div class="register-card">
        <div class="register-header">
          <h2>Create Account</h2>
          <p>{{ roleTitle }} Registration</p>
        </div>

        <div class="register-form">
          <form @submit.prevent="onRegister">
            <!-- Common Fields -->
            <div class="form-row">
              <div class="form-group">
                <label for="full_name">Full Name *</label>
                <input
                  id="full_name"
                  v-model="formData.full_name"
                  type="text"
                  required
                  placeholder="Enter your full name"
                />
              </div>
              <div class="form-group">
                <label for="email">Email Address *</label>
                <input
                  id="email"
                  v-model="formData.email"
                  type="email"
                  required
                  placeholder="Enter your email"
                />
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label for="date_of_birth">Date of Birth</label>
                <input id="date_of_birth" v-model="formData.date_of_birth" type="date" />
              </div>
              <div class="form-group">
                <label for="gender">Gender</label>
                <select id="gender" v-model="formData.gender">
                  <option value="">Select gender</option>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                  <option value="other">Other</option>
                </select>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label for="password">Password *</label>
                <input
                  id="password"
                  v-model="formData.password"
                  :type="showPassword ? 'text' : 'password'"
                  required
                  placeholder="Enter password (min 8 chars, alphanumeric)"
                />
                <button type="button" class="toggle-password" @click="showPassword = !showPassword">
                  {{ showPassword ? 'Hide' : 'Show' }}
                </button>
                <div class="password-strength" :class="passwordStrengthClass">
                  {{ passwordStrengthText }}
                </div>
              </div>
              <div class="form-group">
                <label for="password2">Confirm Password *</label>
                <input
                  id="password2"
                  v-model="formData.password2"
                  :type="showPassword2 ? 'text' : 'password'"
                  required
                  placeholder="Confirm your password"
                />
                <button
                  type="button"
                  class="toggle-password"
                  @click="showPassword2 = !showPassword2"
                >
                  {{ showPassword2 ? 'Hide' : 'Show' }}
                </button>
                <div v-if="passwordMatchText" class="password-match" :class="passwordMatchClass">
                  {{ passwordMatchText }}
                </div>
              </div>
            </div>

            <!-- Role-specific Fields -->
            <div class="role-specific-fields">
              <div class="form-row">
                <div class="form-group">
                  <HospitalSelection v-model="selectedHospitalId" @loaded="onHospitalsLoaded" />
                </div>
              </div>

              <div v-if="role === 'doctor'" class="form-row">
                <div class="form-group">
                  <label for="license_number">Medical License Number *</label>
                  <input
                    id="license_number"
                    v-model="formData.license_number"
                    type="text"
                    required
                    placeholder="Enter your medical license number"
                  />
                </div>
                <div class="form-group">
                  <label for="specialization">Specialization *</label>
                  <select
                    id="specialization"
                    v-model="formData.specialization"
                    required
                  >
                    <option value="">Select specialization</option>
                    <option v-for="spec in specializationOptions" :key="spec" :value="spec">
                      {{ spec }}
                    </option>
                  </select>
                </div>
              </div>

              <div v-if="role === 'nurse'" class="form-row">
                <div class="form-group">
                  <label for="nurse_license">Nursing License Number *</label>
                  <input
                    id="nurse_license"
                    v-model="formData.license_number"
                    type="text"
                    required
                    placeholder="Enter your nursing license number"
                  />
                </div>
                <div class="form-group">
                  <label for="department">Department Selection *</label>
                  <select
                    id="department"
                    v-model="formData.department"
                    required
                  >
                    <option value="">Select department</option>
                    <option value="OPD">Outpatient Department (OPD)</option>
                    <option value="OPD Pharmacy">OPD Pharmacy</option>
                  </select>
                </div>
              </div>
            </div>

            <button type="submit" :disabled="loading" class="register-btn">
              {{ loading ? 'Creating Account...' : 'Create Account' }}
            </button>
          </form>
        </div>

        <div class="register-footer">
          <p>
            Already have an account?
            <button @click="$router.push('/login')" class="link-btn">Sign In</button>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useQuasar } from 'quasar';
import { api } from '../boot/axios';
import type { AxiosError } from 'axios';
import HospitalSelection from '../components/HospitalSelection.vue';

interface RegistrationFormData {
  full_name: string;
  email: string;
  date_of_birth: string;
  gender: string;
  password: string;
  password2: string;
  license_number: string;
  specialization: string;
  department: string;
}

// Remove unused HospitalItem interface

const router = useRouter();
const route = useRoute();
const $q = useQuasar();

// Type guard for API error payloads
const hasError = (d: unknown): d is { error?: string } =>
  typeof d === 'object' && d !== null && 'error' in d;

const role = ref('');
const loading = ref(false);
const showPassword = ref(false);
const showPassword2 = ref(false);

// Hospital dropdown state (hooks-like via Composition API)
const selectedHospitalId = ref<string | number>('');
// Event handler for HospitalSelection load
const onHospitalsLoaded = (items: Array<{id:number; official_name:string; address:string}>) => {
  console.debug('[RegisterPage] Hospitals loaded:', items.length);
};

// Password strength
const passwordStrengthClass = ref('');
const passwordStrengthText = ref('');
const passwordMatchClass = computed(() => {
  const p = formData.value.password || '';
  const c = formData.value.password2 || '';
  if (!p || !c) return '';
  return p === c ? 'match' : 'mismatch';
});
const passwordMatchText = computed(() => {
  const p = formData.value.password || '';
  const c = formData.value.password2 || '';
  if (!p || !c) return '';
  return p === c ? 'Passwords match' : 'Passwords do not match';
});

const formData = ref<RegistrationFormData>({
  full_name: '',
  email: '',
  date_of_birth: '',
  gender: '',
  password: '',
  password2: '',
  license_number: '',
  specialization: '',
  department: '',
});

const roleTitle = computed(() => {
  switch (role.value) {
    case 'doctor':
      return 'Doctor';
    case 'nurse':
      return 'Nurse';
    case 'patient':
      return 'Patient';
    default:
      return '';
  }
});

// Fetch active hospitals on mount
// (Legacy fetchHospitals removed; HospitalSelection handles fetching/persistence)
onMounted(() => {
  role.value = String(route.params.role || '').toLowerCase();
  if (role.value === 'doctor') {
    void loadSpecializations();
  }
});

// Specializations dropdown options
const specializationOptions = ref<string[]>([]);
const specializationLoading = ref(false);
const specializationError = ref<string | null>(null);

const loadSpecializations = async () => {
  if (specializationLoading.value) return;
  specializationLoading.value = true;
  specializationError.value = null;
  try {
    const resp = await api.get('/users/specializations/');
    const specs = Array.isArray(resp.data?.specializations) ? resp.data.specializations : [];
    specializationOptions.value = specs;
    // If nothing loaded, keep dropdown usable with an empty list
  } catch (e) {
    specializationOptions.value = [];
    specializationError.value = 'Failed to load specializations';
    console.error('[RegisterPage] Failed to load specializations:', e);
  } finally {
    specializationLoading.value = false;
  }
};

// Load specializations when role switches to doctor
watch(role, (newRole) => {
  if (newRole === 'doctor' && specializationOptions.value.length === 0) {
    void loadSpecializations();
  }
});

// Password strength calculation
const calculatePasswordStrength = (password: string) => {
  if (!password) {
    passwordStrengthText.value = '';
    passwordStrengthClass.value = '';
    return;
  }

  let score = 0;
  const feedback = [];

  // Length check
  if (password.length >= 8) score += 1;
  else feedback.push('at least 8 characters');

  // Lowercase check
  if (/[a-z]/.test(password)) score += 1;
  else feedback.push('lowercase letters');

  // Uppercase check
  if (/[A-Z]/.test(password)) score += 1;
  else feedback.push('uppercase letters');

  // Number check
  if (/\d/.test(password)) score += 1;
  else feedback.push('numbers');

  // Special character check
  if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) score += 1;
  else feedback.push('special characters');

  // Determine strength
  if (score <= 2) {
    passwordStrengthText.value = 'Weak password';
    passwordStrengthClass.value = 'weak';
  } else if (score <= 3) {
    passwordStrengthText.value = 'Medium password';
    passwordStrengthClass.value = 'medium';
  } else {
    passwordStrengthText.value = 'Strong password';
    passwordStrengthClass.value = 'strong';
  }

  // Add feedback for weak passwords
  if (score <= 2 && feedback.length > 0) {
    passwordStrengthText.value += ` - needs ${feedback.slice(0, 2).join(', ')}`;
  }
};

watch(() => formData.value.password, (val) => calculatePasswordStrength(val));

// Submit handler
const onRegister = async () => {
  if (!selectedHospitalId.value) {
    $q.notify({ type: 'negative', message: 'Please select your hospital.' });
    return;
  }

  // Nurse-specific validation: ensure department is selected
  if (role.value === 'nurse' && !String(formData.value.department || '').trim()) {
    $q.notify({ type: 'negative', message: 'Please select your department.' });
    return;
  }

  loading.value = true;
  try {
    const payload: Record<string, unknown> = {
      email: formData.value.email,
      full_name: formData.value.full_name,
      role: role.value,
      date_of_birth: formData.value.date_of_birth,
      gender: formData.value.gender,
      password: formData.value.password,
      password2: formData.value.password2,
      hospital_id: Number(selectedHospitalId.value),
    };

    if (role.value === 'doctor') {
      payload.license_number = formData.value.license_number;
      payload.specialization = formData.value.specialization;
    } else if (role.value === 'nurse') {
      payload.license_number = formData.value.license_number;
      payload.department = formData.value.department;
    }

// Server-side validation: verify hospital selection ownership when admin is authenticated
const adminToken = localStorage.getItem('admin_access_token');
if (adminToken) {
  try {
    await api.post(
      '/admin/verify-hospital-selection/',
      { hospital_id: Number(selectedHospitalId.value) },
      { headers: { Authorization: `Bearer ${adminToken}` } },
    );
  } catch {
    $q.notify({ type: 'negative', message: 'Hospital verification failed. Please contact admin.' });
    loading.value = false;
    return;
  }
}
    const response = await api.post('/users/register/', payload);
    const { tokens, user } = response.data;

    // Persist tokens and user
    localStorage.setItem('access_token', tokens.access);
    localStorage.setItem('refresh_token', tokens.refresh);
    localStorage.setItem('user', JSON.stringify(user));

    $q.notify({ type: 'positive', message: 'Account created successfully.' });
    await router.push('/verification');
  } catch (err) {
    const axiosErr = err as AxiosError;
    const respData = axiosErr.response?.data;
    let msg = 'Registration failed';
    if (hasError(respData) && typeof respData.error === 'string') {
      msg = respData.error;
    }
    $q.notify({ type: 'negative', message: msg });
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.register-page {
  min-height: 100vh;
  background-color: white;
  background-size: cover;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  position: relative;
}

.register-page::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.25) 0%,
    rgba(248, 249, 250, 0.15) 50%,
    rgba(240, 242, 245, 0.08) 100%
  );
  z-index: 0;
  pointer-events: none;
}

.register-page > * {
  position: relative;
  z-index: 1;
}

.register-container {
  width: 100%;
  max-width: 600px;
}

.register-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  padding: 40px;
}

.register-header {
  text-align: center;
  margin-bottom: 30px;
}

.register-header h2 {
  margin: 0 0 10px 0;
  color: #333;
  font-size: 28px;
  font-weight: 600;
}

.register-header p {
  margin: 0;
  color: #666;
  font-size: 18px;
}

.register-form {
  margin-bottom: 20px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: #333;
  font-weight: 500;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 16px;
  box-sizing: border-box;
  font-family: inherit;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #1e7668;
  box-shadow: 0 0 0 2px rgba(30, 118, 104, 0.2);
}

.form-group textarea {
  resize: vertical;
  min-height: 80px;
}

.toggle-password {
  margin-top: 8px;
  background: none;
  border: none;
  color: #1e7668;
  cursor: pointer;
  font-size: 14px;
}

.password-strength {
  margin-top: 8px;
  font-size: 12px;
  font-weight: 500;
  transition: color 0.3s ease;
}

.password-strength.weak {
  color: #e74c3c;
}

.password-strength.medium {
  color: #f39c12;
}

.password-strength.strong {
  color: #27ae60;
}

.password-match {
  margin-top: 8px;
  font-size: 12px;
  font-weight: 500;
  transition: color 0.3s ease;
}

.password-match.match {
  color: #27ae60;
}

.password-match.mismatch {
  color: #e74c3c;
}

.role-specific-fields {
  border-top: 1px solid #eee;
  padding-top: 20px;
  margin-top: 20px;
}

.register-btn {
  width: 100%;
  padding: 12px;
  background: #1e7668;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.3s;
}

.register-btn:hover:not(:disabled) {
  background: #6ca299;
}

.register-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.register-footer {
  text-align: center;
  padding-top: 20px;
  border-top: 1px solid #eee;
}

.register-footer p {
  margin: 0;
  color: #666;
}

.link-btn {
  background: none;
  border: none;
  color: #1e7668;
  cursor: pointer;
  font-size: 14px;
  text-decoration: underline;
}

.link-btn:hover {
  color: #6ca299;
}

@media (max-width: 768px) {
  .register-page {
    padding: 8px;
    min-height: 100vh;
    /* Ensure content doesn't overlap with safe areas and navigation */
    padding-top: max(80px, calc(var(--safe-area-inset-top) + 60px));
    padding-bottom: max(8px, var(--safe-area-inset-bottom));
    padding-left: max(8px, var(--safe-area-inset-left));
    padding-right: max(8px, var(--safe-area-inset-right));
    /* Adjust alignment for mobile to start from top */
    align-items: flex-start;
  }

  .register-container {
    max-width: 100%;
  }

  .register-card {
    padding: 16px;
    margin: 0;
    border-radius: 12px;
  }

  .register-header {
    margin-bottom: 20px;
  }

  .register-header h2 {
    font-size: 20px;
    margin-bottom: 6px;
  }

  .register-header p {
    font-size: 14px;
  }

  .form-row {
    grid-template-columns: 1fr;
    gap: 12px;
    margin-bottom: 12px;
  }

  .form-group {
    margin-bottom: 12px;
  }

  .form-group label {
    margin-bottom: 4px;
    font-size: 14px;
  }

  .form-group input,
  .form-group select,
  .form-group textarea {
    padding: 10px;
    font-size: 14px;
    border-radius: 6px;
  }

  .register-btn {
    padding: 10px;
    font-size: 14px;
    border-radius: 6px;
  }

  .register-footer {
    padding-top: 16px;
  }

  .register-footer p {
    font-size: 13px;
  }

  .link-btn {
    font-size: 13px;
  }

  .toggle-password {
    font-size: 12px;
  }

  .password-strength {
    font-size: 11px;
  }

  .password-match {
    font-size: 11px;
  }
}
</style>
