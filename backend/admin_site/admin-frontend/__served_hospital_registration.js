// Configuration
const API_BASE_URL = 'http://127.0.0.1:8001/admin';

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
        const msg = (json && (json.error || JSON.stringify(json))) || `HTTP ${resp.status}`;
        throw new Error(msg);
    }
    return json;
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

function updateFileLabel(hasFile) {
    const label = document.querySelector('.file-upload-label');
    if (!label) return;
    label.classList.toggle('has-file', hasFile);
    const textEl = label.querySelector('.upload-text');
    if (textEl) textEl.textContent = hasFile ? 'File selected' : 'Click to upload license document';
}

function renderDataReview(hospital) {
    const review = document.getElementById('dataReview');
    if (!review) return;
    review.innerHTML = `
        <div class="row">
            <div class="col-4">Official Name</div>
            <div class="col-8">${hospital.official_name}</div>
        </div>
        <div class="row">
            <div class="col-4">Address</div>
            <div class="col-8">${hospital.address}</div>
        </div>
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
    const fileInput = document.getElementById('licenseDocument');
    if (fileInput) {
        fileInput.addEventListener('change', () => {
            updateFileLabel(fileInput.files && fileInput.files.length > 0);
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
