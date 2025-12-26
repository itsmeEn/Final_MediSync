<template>
  <div class="verification-page safe-area-top safe-area-bottom">
    <div class="verification-container">
      <div class="verification-card">
        <div class="text-center">
          <h4>Account Verification</h4>
          <p>Please upload a document to verify your identity</p>
        </div>

        <div class="upload-section">
          <div class="form-group">
            <label for="verification-document">Upload Verification Document</label>
            <input
              id="verification-document"
              type="file"
              accept=".pdf,.jpg,.jpeg,.png"
              @change="handleFileChange"
              class="file-input"
            />
            <small>Accepted formats: PDF, JPG, PNG (Max 5MB)</small>
          </div>

          <div v-if="verificationDocument" class="uploaded-file">
            <div class="file-chip">
              <span>{{ verificationDocument.name }}</span>
              <button @click="verificationDocument = null" class="remove-btn">×</button>
            </div>
          </div>
        </div>

        <div class="verification-options">
          <p>Choose how you'd like to proceed with verification:</p>

          <div class="button-row">
            <div class="button-group">
              <button
                class="btn btn-primary"
                :disabled="!verificationDocument || verifying"
                @click="verifyNow"
              >
                {{ verifying ? 'Verifying...' : 'Verify Now' }}
              </button>
              <p class="button-caption">Upload document and verify immediately</p>
            </div>

            <div class="button-group">
              <button class="btn btn-secondary" :disabled="verifying" @click="verifyLater">
                {{ verifying ? 'Processing...' : 'Verify Later' }}
              </button>
              <p class="button-caption">Skip verification for now</p>
            </div>
          </div>
        </div>

        <div class="text-center">
          <button class="btn btn-link" @click="$router.push('/role-selection')">
            Back to Registration
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { api } from '../boot/axios';
import type { AxiosError } from 'axios';

const router = useRouter();
const $q = useQuasar();

interface User {
  id: number;
  email: string;
  full_name: string;
  role: string;
  is_verified: boolean;
  verification_status: string;
}

const verificationDocument = ref<File | null>(null);
const verifying = ref(false);

const handleFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files[0]) {
    verificationDocument.value = target.files[0];
  }
};

onMounted(() => {
  // Check if user is logged in
  const user = localStorage.getItem('user');
  if (!user) {
    void router.push('/login');
  } else {
    const userData = JSON.parse(user);
    // If user is already verified or pending, redirect to dashboard
    if (userData.verification_status === 'approved' || userData.verification_status === 'pending') {
      void redirectToDashboard(userData.role);
    }
  }
});

const getCurrentUser = (): User | null => {
  const userStr = localStorage.getItem('user');
  return userStr ? JSON.parse(userStr) : null;
};

const redirectToDashboard = async (role: string) => {
  console.log('Redirecting to dashboard for role:', role);
  const normalizedRole = role.toLowerCase();
  
  try {
    switch (normalizedRole) {
      case 'doctor':
        await router.push('/doctor-dashboard');
        break;
      case 'nurse':
        await router.push('/nurse-dashboard');
        break;
      case 'patient':
        await router.push('/patient-dashboard');
        break;
      case 'admin':
        // Assuming admin dashboard exists or redirect to specific page
        await router.push('/admin-dashboard'); 
        break;
      default:
        console.warn('Unknown role, redirecting to home:', role);
        await router.push('/');
    }
  } catch (error) {
    console.error('Navigation error:', error);
  }
};

const verifyNow = async () => {
  if (!verificationDocument.value) {
    $q.notify({
      type: 'negative',
      message: 'Please upload a verification document first',
      position: 'top',
      timeout: 3000,
    });
    return;
  }

  verifying.value = true;

  try {
    const formData = new FormData();
    formData.append('verification_document', verificationDocument.value);

    // Upload verification document and capture updated user
    const uploadRes = await api.post('/users/verification/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
        Authorization: `Bearer ${localStorage.getItem('access_token')}`,
      },
    });
    const uploadedUser = (uploadRes?.data && uploadRes.data.user) ? uploadRes.data.user : null;
    if (uploadedUser) {
      localStorage.setItem('user', JSON.stringify(uploadedUser));
    }

    // Submit verification request (may return 200 or 400 if already exists)
    const verifyRes = await api.post(
      '/users/verification/verify-now/',
      {},
      {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
      },
    );
    const verifiedUser = (verifyRes?.data && verifyRes.data.user) ? verifyRes.data.user : null;
    if (verifiedUser) {
      localStorage.setItem('user', JSON.stringify(verifiedUser));
    }

    $q.notify({
      type: 'info',
      message:
        'Verification request submitted successfully. Kindly wait for the admin to verify the uploaded file.',
      position: 'top',
      timeout: 4000,
    });

    // Short delay to ensure local storage is set and notification is seen
    setTimeout(() => {
      void (async () => {
        const user = getCurrentUser();
        if (user && user.role) {
          await redirectToDashboard(user.role);
        } else {
          console.error('User or role missing after verification');
          await router.push('/');
        }
      })();
    }, 1000);
    
  } catch (error: unknown) {
    console.error('Verification error:', error);
    // Try to surface server-provided error details without using 'any'
    const axiosErr = error as AxiosError;
    const data = axiosErr.response?.data as Record<string, unknown> | undefined;
    let serverMsg: string | undefined;
    if (data) {
      const maybeError = data['error'];
      const maybeMessage = data['message'];
      if (typeof maybeError === 'string') serverMsg = maybeError;
      else if (typeof maybeMessage === 'string') serverMsg = maybeMessage;
    }
    const errorMessage = serverMsg || (axiosErr.message || 'Verification failed. Please try again.');

    // If duplicate request exists, treat as success and redirect
    if (serverMsg && /already exists/i.test(serverMsg)) {
      $q.notify({
        type: 'info',
        message: 'A verification request is already pending. We will redirect you now.',
        position: 'top',
        timeout: 3000,
      });
      // Optionally refresh profile to persist latest status
      try {
        const profileRes = await api.get('/users/profile/', {
          headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
        });
        const refreshedUser = (profileRes?.data && profileRes.data.user) ? profileRes.data.user : null;
        if (refreshedUser) {
          localStorage.setItem('user', JSON.stringify(refreshedUser));
        }
      } catch (e) {
        console.warn('Profile refresh failed:', e);
      }
      const user = getCurrentUser();
      if (user) {
        await redirectToDashboard(user.role);
      }
      return;
    }

    $q.notify({
      type: 'negative',
      message: `Error: ${errorMessage}`,
      position: 'top',
      timeout: 4000,
    });
  } finally {
    verifying.value = false;
  }
};

const verifyLater = async () => {
  verifying.value = true;

  try {
    if (verificationDocument.value) {
      const formData = new FormData();
      formData.append('verification_document', verificationDocument.value);

      const uploadRes = await api.post('/users/verification/upload/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
      });
      const uploadedUser = (uploadRes?.data && uploadRes.data.user) ? uploadRes.data.user : null;
      if (uploadedUser) {
        localStorage.setItem('user', JSON.stringify(uploadedUser));
      }
    }

    $q.notify({
      type: 'info',
      message: 'Document uploaded. Kindly wait for the admin to verify the uploaded file.',
      position: 'top',
      timeout: 4000,
    });

    const user = getCurrentUser();
    if (user) {
      await redirectToDashboard(user.role);
    }
  } catch (error: unknown) {
    console.error('Verification error:', error);
    const axiosErr = error as AxiosError;
    const data = axiosErr.response?.data as Record<string, unknown> | undefined;
    let serverMsg: string | undefined;
    if (data) {
      const maybeError = data['error'];
      const maybeMessage = data['message'];
      if (typeof maybeError === 'string') serverMsg = maybeError;
      else if (typeof maybeMessage === 'string') serverMsg = maybeMessage;
    }
    const errorMessage = serverMsg || (axiosErr.message || 'Failed to save document. Please try again.');
    $q.notify({
      type: 'negative',
      message: `Error: ${errorMessage}`,
      position: 'top',
      timeout: 4000,
    });
  } finally {
    verifying.value = false;
  }
};
</script>

<style scoped>
.verification-page {
  min-height: 100vh;
  background-color: white;
  background-size: cover;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  position: relative;
}

.verification-page::before {
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

.verification-container {
  width: 100%;
  max-width: 600px;
  position: relative;
  z-index: 1;
}

.verification-card {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  padding: 40px;
  transition: all 0.3s ease;
  overflow: hidden;
  position: relative;
}

.verification-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #286660, #6ca299, #b8d2ce);
  border-radius: 16px 16px 0 0;
}

.text-center {
  text-align: center;
}

.text-center h4 {
  margin: 0 0 10px 0;
  color: #333;
  font-size: 24px;
  font-weight: 600;
}

.text-center p {
  margin: 0 0 20px 0;
  color: #666;
  font-size: 16px;
}

.upload-section {
  margin-bottom: 30px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: #333;
  font-weight: 500;
}

.file-input {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 16px;
  box-sizing: border-box;
}

.form-group small {
  color: #666;
  font-size: 14px;
}

.uploaded-file {
  display: flex;
  justify-content: center;
  margin-top: 15px;
}

.file-chip {
  background: #1e7668;
  color: white;
  padding: 8px 16px;
  border-radius: 20px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.remove-btn {
  background: none;
  border: none;
  color: white;
  font-size: 18px;
  cursor: pointer;
  padding: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.verification-options {
  border-top: 1px solid #e0e0e0;
  padding-top: 20px;
  margin-bottom: 20px;
}

.verification-options p {
  margin: 0 0 20px 0;
  color: #333;
  font-size: 16px;
}

.button-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.button-group {
  text-align: center;
}

.btn {
  width: 100%;
  padding: 12px;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.3s;
  margin-bottom: 8px;
}

.btn-primary {
  background: #1e7668;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #6ca299;
}

.btn-primary:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #5a6268;
}

.btn-secondary:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.btn-link {
  background: none;
  color: #1e7668;
  text-decoration: underline;
  cursor: pointer;
}

.btn-link:hover {
  color: #6ca299;
}

.button-caption {
  margin: 0;
  color: #666;
  font-size: 14px;
}

@media (max-width: 768px) {
  .verification-page {
    padding: 8px;
    /* Ensure content doesn't overlap with safe areas */
    padding-top: max(8px, var(--safe-area-inset-top));
    padding-bottom: max(8px, var(--safe-area-inset-bottom));
    padding-left: max(8px, var(--safe-area-inset-left));
    padding-right: max(8px, var(--safe-area-inset-right));
  }

  .verification-container {
    max-width: 100%;
  }

  .verification-card {
    padding: 16px;
    margin: 0;
    border-radius: 12px;
  }

  .text-center h4 {
    font-size: 18px;
    margin-bottom: 8px;
  }

  .text-center p {
    font-size: 13px;
    margin-bottom: 16px;
  }

  .upload-section {
    margin-bottom: 20px;
  }

  .form-group {
    margin-bottom: 12px;
  }

  .form-group label {
    margin-bottom: 4px;
    font-size: 14px;
  }

  .file-input {
    padding: 10px;
    font-size: 14px;
    border-radius: 6px;
  }

  .form-group small {
    font-size: 12px;
  }

  .verification-options {
    padding-top: 16px;
    margin-bottom: 16px;
  }

  .verification-options p {
    font-size: 14px;
    margin-bottom: 16px;
  }

  .button-row {
    grid-template-columns: 1fr;
    gap: 12px;
    margin-bottom: 16px;
  }

  .btn {
    padding: 10px;
    font-size: 14px;
    border-radius: 6px;
    min-height: 48px; /* Touch-friendly button height */
  }

  .file-input {
    padding: 14px 12px;
    font-size: 16px;
    min-height: 48px; /* Touch-friendly input height */
  }

  .form-group label {
    font-size: 16px;
    margin-bottom: 10px;
  }

  .button-caption {
    font-size: 13px;
    line-height: 1.3;
  }
}

@media (max-width: 480px) {
  .verification-page {
    padding: 8px;
  }

  .verification-card {
    padding: 16px;
  }

  .text-center h4 {
    font-size: 18px;
  }

  .verification-options p {
    font-size: 14px;
  }

  .btn {
    padding: 16px;
    font-size: 15px;
  }
}
</style>
