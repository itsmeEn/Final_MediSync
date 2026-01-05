// Configuration
// Allow overriding via window.ADMIN_API_BASE_URL or localStorage('admin_api_base_url')
const API_BASE_URL = (function() {
  const ls = (typeof localStorage !== 'undefined') ? localStorage.getItem('admin_api_base_url') : null;
  const win = (typeof window !== 'undefined') ? window.ADMIN_API_BASE_URL : null;
  return win || ls || 'http://localhost:8000/api/admin';
})();

// Simple fetch wrapper for hospital registration pages
async function apiCall(endpoint, method = 'GET', data = null, isForm = false) {
  const headers = { };
  const token = getAccessToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (!isForm) headers['Content-Type'] = 'application/json';

  const resp = await fetch(`${API_BASE_URL}${endpoint}`, {
      method,
      headers,
      body: isForm ? data : (data ? JSON.stringify(data) : null)
  });
  const contentType = resp.headers.get('content-type') || '';
  const json = contentType.includes('application/json') ? await resp.json() : null;
  if (!resp.ok) {
      const msg = (json && (json.error || json.message || JSON.stringify(json))) || `HTTP ${resp.status}`;
      throw new Error(msg);
  }
  return json;
}

// Simple toast utility
function showToast(title, message, type = 'info') {
    const toastEl = document.getElementById('toast');
    const toastTitle = document.getElementById('toastTitle');
    const toastMessage = document.getElementById('toastMessage');
    if (!toastEl) return;
    toastTitle.textContent = title;
    toastMessage.textContent = message;
    toastEl.classList.remove('text-bg-success', 'text-bg-danger', 'text-bg-info');
    if (type === 'success') toastEl.classList.add('text-bg-success');
    else if (type === 'error') toastEl.classList.add('text-bg-danger');
    else toastEl.classList.add('text-bg-info');
    const toast = new bootstrap.Toast(toastEl);
    toast.show();
}

function showLoading(show) {
    const el = document.getElementById('loadingSpinner');
    if (!el) return;
    el.classList.toggle('show', !!show);
}

function getAccessToken() {
    return localStorage.getItem('admin_access_token');
}

function goBack() {
    window.location.href = 'index.html';
}

function goBackToForm() {
    document.getElementById('verificationSection').style.display = 'none';
    document.getElementById('registrationForm').style.display = 'block';
    setStep(1);
}

function goToDashboard() {
    window.location.href = 'index.html';
}

function setStep(step) {
    const steps = [1,2,3];
    steps.forEach(s => {
        document.getElementById(`step${s}`).classList.remove('active', 'completed');
        if (s < step) document.getElementById(`step${s}`).classList.add('completed');
        if (s === step) document.getElementById(`step${s}`).classList.add('active');
    });
}

function updateFileLabel(input) {
    const label = input.parentElement.querySelector('.file-upload-label');
    if (!label) return;
    const hasFile = input.files && input.files.length > 0;
    label.classList.toggle('has-file', hasFile);
    const textEl = label.querySelector('.upload-text');
    if (textEl) {
        if (hasFile) {
            textEl.textContent = input.files[0].name;
        } else {
            if (input.id === 'hospitalLogo') {
                textEl.textContent = 'Click to upload hospital logo';
            } else {
                textEl.textContent = 'Click to upload license document';
            }
        }
    }
}

function clearLogo() {
    const input = document.getElementById('hospitalLogo');
    const preview = document.getElementById('logoPreview');
    if (input) {
        input.value = '';
        updateFileLabel(input);
    }
    if (preview) {
        preview.style.display = 'none';
        const img = preview.querySelector('img');
        if (img) img.src = '';
    }
}

function renderDataReview(hospital) {
    const review = document.getElementById('dataReview');
    if (!review) return;
    
    let logoHtml = '';
    if (hospital.logo) {
        // Assuming the backend returns the full URL or we construct it
        // The serializer returns 'logo' which is a FileField URL
        logoHtml = `
        <div class="row">
            <div class="col-4">Logo</div>
            <div class="col-8">
                <img src="${hospital.logo}" alt="Hospital Logo" style="max-height: 50px; max-width: 50px;" class="img-thumbnail">
            </div>
        </div>`;
    }

    review.innerHTML = `
        <div class="row">
            <div class="col-4">Official Name</div>
            <div class="col-8">${hospital.official_name}</div>
        </div>
        <div class="row">
            <div class="col-4">Address</div>
            <div class="col-8">${hospital.address}</div>
        </div>
        ${logoHtml}
        <div class="row">
            <div class="col-4">License ID</div>
            <div class="col-8">${hospital.license_id}</div>
        </div>
        <div class="row">
            <div class="col-4">Status</div>
            <div class="col-8"><span class="badge bg-secondary">${hospital.status}</span></div>
        </div>
    `;
}

async function activateHospital() {
    const accept = document.getElementById('acceptTerms').checked;
    if (!accept) {
        showToast('Notice', 'Please accept the terms before activation.', 'info');
        return;
    }
    try {
        showLoading(true);
        const resp = await apiCall('/hospital/activate/', 'POST', {
            terms_accepted: true,
            data_verified: true
        });
        showToast('Success', 'Hospital activated successfully!', 'success');
        setStep(3);
        document.getElementById('verificationSection').style.display = 'none';
        document.getElementById('successSection').style.display = 'block';
    } catch (e) {
        console.error(e);
        showToast('Error', e.message || 'Activation failed', 'error');
    } finally {
        showLoading(false);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Guard: must be logged in
    const token = getAccessToken();
    if (!token) {
        showToast('Info', 'Please login first', 'info');
        window.location.href = 'index.html';
        return;
    }

    // Enable/disable activate button based on checkbox
    const acceptTerms = document.getElementById('acceptTerms');
    const activateBtn = document.getElementById('activateBtn');
    if (acceptTerms && activateBtn) {
        acceptTerms.addEventListener('change', () => {
            activateBtn.disabled = !acceptTerms.checked;
        });
    }

    // File label update
    const licenseInput = document.getElementById('licenseDocument');
    if (licenseInput) {
        licenseInput.addEventListener('change', () => {
            updateFileLabel(licenseInput);
        });
    }

    // Logo upload handling
    const logoInput = document.getElementById('hospitalLogo');
    if (logoInput) {
        logoInput.addEventListener('change', function() {
            const file = this.files[0];
            if (!file) {
                clearLogo();
                return;
            }

            // Validation
            const validTypes = ['image/jpeg', 'image/png', 'image/svg+xml'];
            if (!validTypes.includes(file.type)) {
                showToast('Error', 'Invalid file type. Please upload PNG, JPG, or SVG.', 'error');
                this.value = '';
                clearLogo();
                return;
            }

            if (file.size > 2 * 1024 * 1024) { // 2MB
                showToast('Error', 'File too large. Maximum size is 2MB.', 'error');
                this.value = '';
                clearLogo();
                return;
            }

            updateFileLabel(this);

            // Preview
            const preview = document.getElementById('logoPreview');
            const logoImg = preview ? preview.querySelector('img') : null;
            if (logoImg) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    logoImg.src = e.target.result;
                    preview.style.display = 'block';
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // Form submit
    const form = document.getElementById('hospitalForm');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            try {
                showLoading(true);
                const fd = new FormData(form);
                const resp = await apiCall('/hospital/register/', 'POST', fd, true);
                const hospital = resp && resp.hospital ? resp.hospital : null;
                if (!hospital) throw new Error('Registration failed');
                showToast('Success', 'Registration successful. Review details.', 'success');
                setStep(2);
                renderDataReview(hospital);
                document.getElementById('registrationForm').style.display = 'none';
                document.getElementById('verificationSection').style.display = 'block';
            } catch (e) {
                console.error(e);
                showToast('Error', e.message || 'Registration failed', 'error');
            } finally {
                showLoading(false);
            }
        });
    }

    // Expose functions globally
    window.goBack = goBack;
    window.goBackToForm = goBackToForm;
    window.goToDashboard = goToDashboard;
    window.activateHospital = activateHospital;
});