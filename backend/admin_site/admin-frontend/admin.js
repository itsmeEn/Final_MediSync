// Configuration
// Allow overriding via window.ADMIN_API_BASE_URL or localStorage('admin_api_base_url'); default to 8000
const API_BASE_URL = (function() {
    try {
        const win = (typeof window !== 'undefined') ? window.ADMIN_API_BASE_URL : null;
        const ls = (typeof localStorage !== 'undefined') ? localStorage.getItem('admin_api_base_url') : null;
        const base = win || ls || 'http://localhost:8000/api/admin';
        return base.endsWith('/') ? base.slice(0, -1) : base; // normalize trailing slash
    } catch (_) {
        return 'http://localhost:8000/api/admin';
    }
})();
const ANALYTICS_BASE_URL = API_BASE_URL.replace('/api/admin', '/api/analytics');

// Global variables
let currentUser = null;
let verifications = [];
let selectedVerification = null;
let csrfToken = null;
let currentSection = 'dashboard';
let latencyChartInstance = null;
let successChartInstance = null;

// Get CSRF token
async function getCSRFToken() {
    if (csrfToken) {
        return csrfToken;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/csrf-token/`, {
            method: 'GET',
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            csrfToken = data.csrf_token;
            return csrfToken;
        }
    } catch (error) {
        console.error('Failed to get CSRF token:', error);
    }
    
    return null;
}

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    checkAuth();
    setupEventListeners();
    setupPasswordToggle();
});

// Password toggle functionality
function setupPasswordToggle() {
    const passwordInput = document.getElementById('password');
    const passwordToggleBtn = document.getElementById('passwordToggleBtn');
    
    if (passwordInput && passwordToggleBtn) {
        passwordToggleBtn.addEventListener('click', function() {
            const isPassword = passwordInput.type === 'password';
            passwordInput.type = isPassword ? 'text' : 'password';
            passwordToggleBtn.textContent = isPassword ? 'Hide' : 'Show';
        });
    }
}

// Check if user is authenticated
function checkAuth() {
    const token = localStorage.getItem('admin_access_token');
    if (token) {
        ensureHospitalRegistration().then((registered) => {
            if (registered) {
                showDashboard();
                loadDashboardData();
            }
        });
    } else {
        showLogin();
    }
}

// Setup event listeners
function setupEventListeners() {
    // Login form
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    // Filters
    const statusFilter = document.getElementById('statusFilter');
    const searchInput = document.getElementById('searchInput');
    
    if (statusFilter) {
        statusFilter.addEventListener('change', filterVerifications);
    }
    if (searchInput) {
        searchInput.addEventListener('input', filterVerifications);
    }

    // Time update
    updateTime();
    setInterval(updateTime, 1000);

    // Stress test button
    const runStressBtn = document.getElementById('runStressTestBtn');
    if (runStressBtn) {
        runStressBtn.addEventListener('click', runStressTest);
    }

    // Bottlenecks analyze button
    const analyzeBtn = document.getElementById('analyzeBottlenecksBtn');
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', loadBottleneckAnalytics);
    }

    // Settings: profile refresh
    const settingsRefreshBtn = document.getElementById('settingsRefreshBtn');
    if (settingsRefreshBtn) {
        settingsRefreshBtn.addEventListener('click', loadAdminSettingsProfile);
    }

    // Settings: save profile
    const settingsSaveBtn = document.getElementById('settingsSaveBtn');
    if (settingsSaveBtn) {
        settingsSaveBtn.addEventListener('click', saveAdminSettingsProfile);
    }

    // Settings: close panel
    const settingsCloseBtn = document.getElementById('settingsCloseBtn');
    if (settingsCloseBtn) {
        settingsCloseBtn.addEventListener('click', () => {
            navigateTo('dashboard');
            const focusTarget = document.getElementById('statusFilter') || document.getElementById('searchInput');
            if (focusTarget) focusTarget.focus();
        });
    }

    // Settings: change password
    const changePasswordBtn = document.getElementById('changePasswordBtn');
    if (changePasswordBtn) {
        changePasswordBtn.addEventListener('click', handleChangePassword);
    }

    // Settings: download users CSV
    const downloadUsersBtn = document.getElementById('downloadUsersBtn');
    if (downloadUsersBtn) {
        downloadUsersBtn.addEventListener('click', downloadUsersCSV);
    }
}

// Update time display
function updateTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('en-US', { 
        hour12: true, 
        hour: 'numeric', 
        minute: '2-digit', 
        second: '2-digit' 
    });
    
    const timeElement = document.getElementById('currentTime');
    if (timeElement) {
        timeElement.textContent = timeString;
    }
}


// Centralized navigation handler
function navigateTo(section) {
    currentSection = section;

    // Update active nav item
    document.querySelectorAll('.navigation-menu .nav-item').forEach(item => item.classList.remove('active'));
    const activeItem = document.querySelector(`.navigation-menu .nav-item[data-nav="${section}"]`);
    if (activeItem) activeItem.classList.add('active');

    // Sections map: which containers to show per section
    const sectionsMap = {
        dashboard: ['dashboardSection', 'verificationsSection', 'bottlenecksSection'],
        verifications: ['verificationsSection'],
        analytics: ['analyticsSection'],
        settings: ['settingsSection']
    };

    // Hide all sections first
    ['dashboardSection', 'verificationsSection', 'bottlenecksSection', 'analyticsSection', 'settingsSection']
        .forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });

    // Show the target sections
    const toShow = sectionsMap[section] || [];
    toShow.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'block';
    });

    // Data loading hooks
    if (section === 'dashboard') {
        // Refresh key stats and verifications list when returning to dashboard
        loadDashboardData();
        // Render bottlenecks analytics
        loadBottleneckAnalytics();
    } else if (section === 'verifications') {
        // Ensure verifications list is up-to-date
        loadVerifications();
    } else if (section === 'analytics') {
        // System performance cards removed; only show stress testing UI
        // Ensure stress test results container is cleared
        const container = document.getElementById('stressResultsContainer');
        if (container) container.innerHTML = '';
    }

    // Settings section: load profile on entry
    if (section === 'settings') {
        loadAdminSettingsProfile().catch(err => console.error('Failed to load settings profile:', err));
    }

    // Sidebar removed; no mobile toggle needed
}

// Load admin settings profile
async function loadAdminSettingsProfile() {
    try {
        const resp = await apiCall('/settings/profile/', 'GET');
        if (!resp) return;
        // Expect resp: { email, full_name, hospital } or { profile: {...} }
        const data = resp.profile || resp;
        document.getElementById('settingFullName').value = data.full_name || '';
        document.getElementById('settingEmail').value = data.email || '';
        const hosp = data.hospital || {};
        const hospName = hosp.official_name || '';
        const hospAddress = hosp.address || '';
        const hospNameEl = document.getElementById('settingHospitalName');
        const hospAddrEl = document.getElementById('settingHospitalAddress');
        if (hospNameEl) hospNameEl.value = hospName;
        if (hospAddrEl) hospAddrEl.value = hospAddress;
        // Sync header admin name
        currentUser = Object.assign({}, currentUser || {}, { full_name: data.full_name });
        updateAdminName();
        showToast('Success', 'Profile loaded', 'success');
    } catch (error) {
        console.error('Error loading admin profile:', error);
        showToast('Error', error.message || 'Failed to load profile', 'error');
    }
}

// Save admin settings profile
async function saveAdminSettingsProfile() {
    const fullNameEl = document.getElementById('settingFullName');
    const emailEl = document.getElementById('settingEmail');
    const hospNameEl = document.getElementById('settingHospitalName');
    const hospAddrEl = document.getElementById('settingHospitalAddress');

    const full_name = fullNameEl.value.trim();
    const email = emailEl.value.trim();
    const hospital_name = hospNameEl.value.trim();
    const hospital_address = (hospAddrEl?.value || '').trim();

    // Reset validation styles
    [fullNameEl, emailEl, hospNameEl, hospAddrEl].forEach(el => el && el.classList.remove('is-invalid'));

    // Basic input validation
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    let hasError = false;
    if (!full_name) {
        hasError = true;
        fullNameEl.classList.add('is-invalid');
    }
    if (!email || !emailPattern.test(email)) {
        hasError = true;
        emailEl.classList.add('is-invalid');
    }
    if (hasError) {
        showToast('Error', 'Please correct the highlighted fields', 'error');
        return;
    }

    showLoading(true);
    const saveBtn = document.getElementById('settingsSaveBtn');
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.setAttribute('aria-busy', 'true');
    }
    try {
        const resp = await apiCall('/settings/profile/', 'PATCH', { full_name, email, hospital_name, hospital_address });
        if (resp) {
            showToast('Success', 'Profile updated', 'success');
            // Refresh local display
            currentUser = Object.assign({}, currentUser || {}, { full_name, email });
            updateAdminName();
        }
    } catch (error) {
        console.error('Error saving admin profile:', error);
        showToast('Error', error.message || 'Failed to save profile', 'error');
    } finally {
        showLoading(false);
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.removeAttribute('aria-busy');
        }
    }
}

// Handle change password
async function handleChangePassword() {
    const current_password = document.getElementById('currentPassword').value;
    const new_password = document.getElementById('newPassword').value;

    if (!current_password || !new_password) {
        showToast('Error', 'Please enter current and new password', 'error');
        return;
    }

    showLoading(true);
    try {
        const resp = await apiCall('/settings/password/', 'POST', { current_password, new_password });
        if (resp && resp.success) {
            showToast('Success', 'Password updated', 'success');
            // Clear inputs
            document.getElementById('currentPassword').value = '';
            document.getElementById('newPassword').value = '';
        } else {
            showToast('Error', (resp && resp.error) || 'Failed to update password', 'error');
        }
    } catch (error) {
        console.error('Error updating password:', error);
        showToast('Error', error.message || 'Failed to update password', 'error');
    } finally {
        showLoading(false);
    }
}

// Download all users CSV (Super Admin only)
async function downloadUsersCSV() {
    try {
        const token = localStorage.getItem('admin_access_token');
        if (!token) {
            logout();
            return;
        }

        const url = `${API_BASE_URL}/users/export/`;
        const resp = await fetch(url, {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` },
        });

        if (!resp.ok) {
            let msg = `HTTP ${resp.status}`;
            try {
                const j = await resp.json();
                msg = j.error || JSON.stringify(j);
            } catch (_) {}
            throw new Error(msg);
        }

        const blob = await resp.blob();
        const blobUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = blobUrl;
        // Try to read filename from header; fallback
        const dispo = resp.headers.get('Content-Disposition') || '';
        let filename = 'users_export.csv';
        const m = dispo.match(/filename="?([^";]+)"?/i);
        if (m && m[1]) filename = m[1];
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(blobUrl);
        showToast('Success', 'Users CSV downloaded', 'success');
    } catch (error) {
        console.error('Error downloading users CSV:', error);
        showToast('Error', error.message || 'Failed to download CSV', 'error');
    }
}

// Hospital Users feature removed

// Load bottlenecks analytics via stress-test endpoint and render charts
async function loadBottleneckAnalytics() {
    try {
        const token = localStorage.getItem('admin_access_token');
        if (!token) return;

        const url = `${ANALYTICS_BASE_URL}/stress-test/?group=all&concurrency=4&requests=20`;
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        const payload = await response.json();
        if (!response.ok || !payload.success) {
            throw new Error(payload.message || 'Failed to load bottleneck analytics');
        }

        renderBottleneckCharts(payload.data);
    } catch (error) {
        console.error('Error loading bottleneck analytics:', error);
        showToast('Error', error.message || 'Failed to analyze modules', 'error');
    }
}

function renderBottleneckCharts(data) {
    const groups = data?.groups || {};
    const order = ['doctor', 'nurse', 'patient'];
    const labels = [];
    const avgLatency = [];
    const p95Latency = [];
    const successRate = [];

    order.forEach(key => {
        const s = groups[key]?.summary;
        if (s) {
            labels.push(key.charAt(0).toUpperCase() + key.slice(1));
            avgLatency.push(s.avg_latency_ms ?? 0);
            p95Latency.push(s.p95_latency_ms ?? 0);
            successRate.push(s.success_rate ?? 0);
        }
    });

    // Latency chart
    const latCtx = document.getElementById('latencyChart');
    if (latCtx) {
        if (latencyChartInstance) latencyChartInstance.destroy();
        latencyChartInstance = new Chart(latCtx, {
            type: 'bar',
            data: {
                labels,
                datasets: [
                    { label: 'Avg (ms)', data: avgLatency, backgroundColor: 'rgba(40,102,96,0.6)' },
                    { label: 'P95 (ms)', data: p95Latency, backgroundColor: 'rgba(255,159,64,0.7)' }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom' },
                    title: { display: true, text: 'Latency by Module' }
                },
                scales: {
                    y: { beginAtZero: true, title: { display: true, text: 'ms' } }
                }
            }
        });
    }

    // Success rate chart
    const sucCtx = document.getElementById('successChart');
    if (sucCtx) {
        if (successChartInstance) successChartInstance.destroy();
        successChartInstance = new Chart(sucCtx, {
            type: 'bar',
            data: {
                labels,
                datasets: [
                    { label: 'Success Rate (%)', data: successRate, backgroundColor: 'rgba(75,192,192,0.7)' }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom' },
                    title: { display: true, text: 'Reliability by Module' }
                },
                scales: {
                    y: { beginAtZero: true, max: 100, title: { display: true, text: '%' } }
                }
            }
        });
    }

    // Simple summary: highlight potential bottleneck by highest P95
    const summaryEl = document.getElementById('bottlenecksSummary');
    if (summaryEl && labels.length) {
        let maxIdx = 0;
        for (let i = 1; i < p95Latency.length; i++) {
            if (p95Latency[i] > p95Latency[maxIdx]) maxIdx = i;
        }
        const worst = labels[maxIdx];
        const p95 = p95Latency[maxIdx].toFixed(0);
        const sr = successRate[maxIdx]?.toFixed ? successRate[maxIdx].toFixed(1) : successRate[maxIdx];
        summaryEl.innerHTML = `<div class="alert alert-warning">Potential bottleneck: <strong>${worst}</strong> (P95 ~ ${p95} ms, Success ${sr}%).</div>`;
    }
}

// Run stress test via analytics API
async function runStressTest() {
    showLoading(true);
    try {
        const token = localStorage.getItem('admin_access_token');
        if (!token) {
            logout();
            return;
        }

        const group = document.getElementById('stressGroup')?.value || 'all';
        const concurrency = parseInt(document.getElementById('stressConcurrency')?.value || '8', 10);
        const requests = parseInt(document.getElementById('stressRequests')?.value || '30', 10);

        const url = `${ANALYTICS_BASE_URL}/stress-test/?group=${encodeURIComponent(group)}&concurrency=${concurrency}&requests=${requests}`;
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        const payload = await response.json();
        if (!response.ok || !payload.success) {
            throw new Error(payload.message || 'Stress test failed');
        }

        renderStressResults(payload.data);
        showToast('Success', 'Stress test completed', 'success');
    } catch (error) {
        console.error('Error running stress test:', error);
        showToast('Error', error.message || 'Failed to run stress test', 'error');
    } finally {
        showLoading(false);
    }
}

function renderStressResults(data) {
    const container = document.getElementById('stressResultsContainer');
    if (!container) return;

    const base = data?.base_url || '';
    const started = data?.started_at || '';
    const finished = data?.finished_at || '';
    const params = data?.params || {};
    const groups = data?.groups || {};

    let html = '';
    html += `<div class="alert alert-info">` +
            `Base: <code>${base}</code> &nbsp; ` +
            `Started: <code>${started}</code> &nbsp; ` +
            `Finished: <code>${finished}</code> &nbsp; ` +
            `Duration: <code>${data?.duration_ms || '–'} ms</code> &nbsp; ` +
            `Params: group=<code>${params.group}</code>, concurrency=<code>${params.concurrency}</code>, requests/endpoint=<code>${params.requests_per_endpoint}</code>` +
            `</div>`;

    // Group summaries
    Object.keys(groups).forEach(g => {
        const s = groups[g]?.summary || {};
        html += `<div class="card mb-3">` +
                `<div class="card-header"><strong>${g.charAt(0).toUpperCase() + g.slice(1)} Summary</strong></div>` +
                `<div class="card-body">` +
                `<div class="row">` +
                `<div class="col-md-3"><div><strong>Total Requests</strong></div><div>${s.total_requests ?? '–'}</div></div>` +
                `<div class="col-md-3"><div><strong>Success Rate</strong></div><div>${s.success_rate != null ? s.success_rate + '%' : '–'}</div></div>` +
                `<div class="col-md-2"><div><strong>Avg (ms)</strong></div><div>${s.avg_latency_ms ?? '–'}</div></div>` +
                `<div class="col-md-2"><div><strong>P95 (ms)</strong></div><div>${s.p95_latency_ms ?? '–'}</div></div>` +
                `<div class="col-md-2"><div><strong>Max (ms)</strong></div><div>${s.max_latency_ms ?? '–'}</div></div>` +
                `</div>` +
                `</div>` +
                `</div>`;

        // Endpoint table
        const eps = groups[g]?.endpoints || {};
        html += `<div class="table-responsive mb-4">` +
                `<table class="table table-sm">` +
                `<thead><tr>` +
                `<th>Endpoint</th><th>Requests</th><th>Success</th><th>Errors</th>` +
                `<th>Avg (ms)</th><th>P95 (ms)</th><th>Max (ms)</th><th>Status Dist</th>` +
                `</tr></thead><tbody>`;
        Object.keys(eps).forEach(ep => {
            const m = eps[ep] || {};
            const dist = m.status_distribution || {};
            const distStr = Object.keys(dist).map(k => `${k}:${dist[k]}`).join(', ');
            html += `<tr>` +
                    `<td><code>${ep}</code></td>` +
                    `<td>${m.requests ?? '–'}</td>` +
                    `<td>${m.success_count ?? '–'}</td>` +
                    `<td>${m.error_count ?? '–'}</td>` +
                    `<td>${m.avg_latency_ms ?? '–'}</td>` +
                    `<td>${m.p95_latency_ms ?? '–'}</td>` +
                    `<td>${m.max_latency_ms ?? '–'}</td>` +
                    `<td>${distStr || '–'}</td>` +
                    `</tr>`;
        });
        html += `</tbody></table></div>`;
    });

    container.innerHTML = html;
}

// Load system performance metrics
async function loadSystemPerformance() {
    showLoading(true);
    try {
        const token = localStorage.getItem('admin_access_token');
        if (!token) {
            logout();
            return;
        }

        const response = await fetch(`${ANALYTICS_BASE_URL}/performance/`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        const payload = await response.json();
        if (!response.ok || !payload.success) {
            throw new Error(payload.message || 'Failed to fetch performance metrics');
        }

        const data = payload.data || {};
        const cpu = data.cpu || {};
        const memory = data.memory || null;
        const processInfo = data.process || {};

        // CPU
        const cpuLoadEl = document.getElementById('cpuLoad');
        const cpuPercentEl = document.getElementById('cpuPercent');
        if (cpuLoadEl) {
            const l1 = cpu.load_1 != null ? cpu.load_1.toFixed(2) : '–';
            const l5 = cpu.load_5 != null ? cpu.load_5.toFixed(2) : '–';
            const l15 = cpu.load_15 != null ? cpu.load_15.toFixed(2) : '–';
            cpuLoadEl.textContent = `${l1} / ${l5} / ${l15}`;
        }
        if (cpuPercentEl) {
            cpuPercentEl.textContent = cpu.percent != null ? cpu.percent.toFixed(1) : '–';
        }

        // Memory
        const memUsageEl = document.getElementById('memoryUsage');
        const memPercentEl = document.getElementById('memoryPercent');
        if (memory && memUsageEl) {
            memUsageEl.textContent = `${formatBytes(memory.used)} / ${formatBytes(memory.total)}`;
        } else if (memUsageEl) {
            memUsageEl.textContent = 'Unavailable';
        }
        if (memPercentEl) {
            memPercentEl.textContent = memory && memory.percent != null ? memory.percent.toFixed(1) : '–';
        }

        // Uptime and timestamps
        const uptimeEl = document.getElementById('uptimeValue');
        const updatedAtEl = document.getElementById('perfUpdatedAt');
        if (uptimeEl) {
            uptimeEl.textContent = data.uptime_seconds != null ? formatUptime(data.uptime_seconds) : 'Unknown';
        }
        if (updatedAtEl && data.server_time) {
            const dt = new Date(data.server_time);
            updatedAtEl.textContent = dt.toLocaleString();
        }

        // Details
        const platformEl = document.getElementById('platformInfo');
        const psutilEl = document.getElementById('psutilAvailable');
        const procPidEl = document.getElementById('procPid');
        const procThreadsEl = document.getElementById('procThreads');
        const procRssEl = document.getElementById('procRss');
        if (platformEl) platformEl.textContent = data.platform || '–';
        if (psutilEl) psutilEl.textContent = data.psutil_available ? 'Yes' : 'No';
        if (procPidEl) procPidEl.textContent = processInfo.pid != null ? processInfo.pid : '–';
        if (procThreadsEl) procThreadsEl.textContent = processInfo.threads != null ? processInfo.threads : '–';
        if (procRssEl) procRssEl.textContent = processInfo.rss != null ? formatBytes(processInfo.rss) : '–';
    } catch (error) {
        console.error('Error loading system performance:', error);
        showToast('Error', 'Failed to load system performance', 'error');
    } finally {
        showLoading(false);
    }
}

function formatBytes(bytes) {
    if (!bytes && bytes !== 0) return '–';
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    const value = bytes / Math.pow(1024, i);
    return `${value.toFixed(1)} ${sizes[i]}`;
}

function formatUptime(seconds) {
    const s = Number(seconds);
    const d = Math.floor(s / (3600 * 24));
    const h = Math.floor((s % (3600 * 24)) / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = Math.floor(s % 60);
    const parts = [];
    if (d) parts.push(`${d}d`);
    if (h) parts.push(`${h}h`);
    if (m) parts.push(`${m}m`);
    parts.push(`${sec}s`);
    return parts.join(' ');
}

// Card click handlers
function showPendingVerifications() {
    const statusFilter = document.getElementById('statusFilter');
    if (statusFilter) {
        statusFilter.value = 'pending';
        navigateTo('verifications');
        filterVerifications();
    }
}

function showApprovedVerifications() {
    const statusFilter = document.getElementById('statusFilter');
    if (statusFilter) {
        statusFilter.value = 'approved';
        navigateTo('verifications');
        filterVerifications();
    }
}

function showDeclinedVerifications() {
    const statusFilter = document.getElementById('statusFilter');
    if (statusFilter) {
        statusFilter.value = 'declined';
        navigateTo('verifications');
        filterVerifications();
    }
}

function showArchivedVerifications() {
    const statusFilter = document.getElementById('statusFilter');
    if (statusFilter) {
        statusFilter.value = 'archived';
        navigateTo('verifications');
        filterVerifications();
    }
}

// Show login screen
function showLogin() {
    const loginScreen = document.getElementById('loginScreen');
    const dashboard = document.getElementById('dashboard');
    
    if (loginScreen) {
        loginScreen.style.display = 'flex';
    }
    if (dashboard) {
        dashboard.style.display = 'none';
    }
}

// Show dashboard
function showDashboard() {
    const loginScreen = document.getElementById('loginScreen');
    const dashboard = document.getElementById('dashboard');
    
    if (loginScreen) {
        loginScreen.style.display = 'none';
    }
    if (dashboard) {
        dashboard.style.display = 'block';
        
        // Set up greeting text
        const greetingText = document.getElementById('greetingText');
        const greetingSubtitle = document.getElementById('greetingSubtitle');
        const adminName = document.getElementById('adminName');
        
        if (greetingText && adminName) {
            const now = new Date();
            const hour = now.getHours();
            let timeOfDay = 'morning';
            if (hour >= 12 && hour < 18) timeOfDay = 'afternoon';
            else if (hour >= 18) timeOfDay = 'evening';
            
            greetingText.textContent = `Good ${timeOfDay}, Admin ${adminName.textContent}`;
        }
        
        if (greetingSubtitle) {
            const today = new Date().toLocaleDateString('en-US', { 
                weekday: 'long', 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
            });
            greetingSubtitle.textContent = `Manage your healthcare platform - ${today}`;
        }

        // Default view on login
        navigateTo('dashboard');
    }
}

// Handle login
async function handleLogin(event) {
    event.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    showLoading(true);
    
    try {
        const response = await fetch(`${API_BASE_URL}/login/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': await getCSRFToken()
            },
            body: JSON.stringify({ email, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            localStorage.setItem('admin_access_token', data.access);
            localStorage.setItem('admin_refresh_token', data.refresh);
            currentUser = data.admin_user;

            if (data.hospital_registration_required) {
                showToast('Info', 'Complete hospital registration to proceed.', 'info');
                window.location.href = 'hospital-registration.html';
                showLoading(false);
                return;
            }
            
            showToast('Success', 'Login successful!', 'success');
            showDashboard();
            loadDashboardData();
        } else {
            showToast('Error', data.error || 'Login failed', 'error');
        }
    } catch (error) {
        console.error('Login error:', error);
        showToast('Error', 'Network error. Please try again.', 'error');
    } finally {
        showLoading(false);
    }
}

// Logout
function logout() {
    localStorage.removeItem('admin_access_token');
    localStorage.removeItem('admin_refresh_token');
    currentUser = null;
    showLogin();
}

// Load dashboard data
async function loadDashboardData() {
    showLoading(true);
    
    try {
        await Promise.all([
            loadStats(),
            loadVerifications()
        ]);
        
        updateAdminName();
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        showToast('Error', 'Failed to load dashboard data', 'error');
    } finally {
        showLoading(false);
    }
}

// Load statistics
async function loadStats() {
    const response = await apiCall('/dashboard/stats/');
    if (response) {
        document.getElementById('pendingCount').textContent = response.pending;
        document.getElementById('approvedCount').textContent = response.approved;
        document.getElementById('declinedCount').textContent = response.declined;
        document.getElementById('archivedCount').textContent = response.archived;
    }
}

// Load verifications
async function loadVerifications() {
    const response = await apiCall('/verifications/');
    if (response) {
        verifications = response.verifications;
        renderVerificationsTable(verifications);
    }
}

// Render verifications table
function renderVerificationsTable(data) {
    const tbody = document.getElementById('verificationsTable');
    tbody.innerHTML = '';
    
    if (data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No verification requests found</td></tr>';
        return;
    }
    
    data.forEach(verification => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${verification.user_full_name}</td>
            <td>${verification.user_email}</td>
            <td><span class="badge bg-info">${verification.user_role}</span></td>
            <td>${getStatusBadge(verification.status)}</td>
            <td>${formatDate(verification.submitted_at)}</td>
            <td>${getActionButtons(verification)}</td>
        `;
        tbody.appendChild(row);
    });
}

// Get status badge
function getStatusBadge(status) {
    const colors = {
        'pending': 'warning',
        'approved': 'success',
        'declined': 'danger',
        'archived': 'secondary'
    };
    
    return `<span class="badge bg-${colors[status] || 'secondary'}">${status}</span>`;
}

// Get action buttons
function getActionButtons(verification) {
    let buttons = '';
    
    if (verification.status === 'pending') {
        buttons += `<button class="btn btn-success btn-sm btn-action" onclick="acceptVerification(${verification.id})">
            <i class="fas fa-check"></i> Accept
        </button>`;
        buttons += `<button class="btn btn-danger btn-sm btn-action" onclick="showDeclineModal(${verification.id})">
            <i class="fas fa-times"></i> Decline
        </button>`;
    }
    
                    buttons += `<button class="btn btn-primary btn-sm btn-action" onclick="viewDocument(${verification.id}).catch(console.error)">
                    <i class="fas fa-eye"></i> View
                </button>`;
    
    buttons += `<button class="btn btn-warning btn-sm btn-action" onclick="archiveVerification(${verification.id})">
        <i class="fas fa-archive"></i> Archive
    </button>`;
    
    return buttons;
}

// Accept verification
async function acceptVerification(id) {
    if (!confirm('Are you sure you want to approve this verification?')) {
        return;
    }
    
    showLoading(true);
    
    try {
        const response = await apiCall(`/verifications/${id}/accept/`, 'POST');
        if (response) {
            showToast('Success', 'Verification approved successfully', 'success');
            loadDashboardData();
        }
    } catch (error) {
        console.error('Error accepting verification:', error);
        showToast('Error', error.message || 'Failed to approve verification', 'error');
    } finally {
        showLoading(false);
    }
}

// Show decline modal
function showDeclineModal(id) {
    selectedVerification = verifications.find(v => v.id === id);
    document.getElementById('declineReason').value = '';
    document.getElementById('sendEmail').checked = true;
    
    const modal = new bootstrap.Modal(document.getElementById('declineModal'));
    modal.show();
}

// Confirm decline
async function confirmDecline() {
    const reason = document.getElementById('declineReason').value.trim();
    const sendEmail = document.getElementById('sendEmail').checked;
    
    if (!reason) {
        showToast('Error', 'Please provide a reason for declining', 'error');
        return;
    }
    
    if (!selectedVerification) {
        showToast('Error', 'No verification selected', 'error');
        return;
    }
    
    showLoading(true);
    
    try {
        const response = await apiCall(`/verifications/${selectedVerification.id}/decline/`, 'POST', {
            reason: reason,
            send_email: sendEmail
        });
        
        if (response) {
            showToast('Success', 'Verification declined successfully', 'success');
            
            const modal = bootstrap.Modal.getInstance(document.getElementById('declineModal'));
            modal.hide();
            
            loadDashboardData();
        }
    } catch (error) {
        console.error('Error declining verification:', error);
        showToast('Error', error.message || 'Failed to decline verification', 'error');
    } finally {
        showLoading(false);
        selectedVerification = null;
    }
}

// View document
async function viewDocument(id) {
    const verification = verifications.find(v => v.id === id);
    if (!verification) {
        showToast('Error', 'Verification not found', 'error');
        return;
    }
    
    // Update document info
    document.getElementById('documentInfo').innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <p><strong>Name:</strong> ${verification.user_full_name}</p>
                <p><strong>Email:</strong> ${verification.user_email}</p>
            </div>
            <div class="col-md-6">
                <p><strong>Role:</strong> ${verification.user_role}</p>
                <p><strong>Status:</strong> ${verification.status}</p>
            </div>
        </div>
    `;
    
    // Show document if available
    const iframe = document.getElementById('documentFrame');
    const documentInfo = document.getElementById('documentInfo');
    
    if (verification.verification_document) {
        // Show loading state
        iframe.style.display = 'none';
        documentInfo.innerHTML += '<div class="text-center mt-3"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div><p class="mt-2">Loading document...</p></div>';
        
        try {
            const token = localStorage.getItem('admin_access_token');
            if (!token) {
                throw new Error('No authentication token');
            }
            
            console.log('Fetching document for verification:', verification.id);
            console.log('Document URL:', `${API_BASE_URL}/verifications/${verification.id}/document/`);
            
            const response = await fetch(`${API_BASE_URL}/verifications/${verification.id}/document/`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                credentials: 'include'
            });
            
            console.log('Document response status:', response.status);
            console.log('Document response headers:', response.headers);
            
            if (response.ok) {
                const blob = await response.blob();
                console.log('Document blob size:', blob.size);
                
                if (blob.size > 0) {
                    const blobUrl = URL.createObjectURL(blob);
                    iframe.src = blobUrl;
                    iframe.style.display = 'block';
                    
                    // Remove loading state
                    const loadingDiv = documentInfo.querySelector('.text-center');
                    if (loadingDiv) {
                        loadingDiv.remove();
                    }
                } else {
                    throw new Error('Document is empty or corrupted');
                }
            } else {
                const errorText = await response.text();
                console.error('Document fetch error:', response.status, errorText);
                throw new Error(`Failed to fetch document: ${response.status} ${response.statusText}`);
            }
        } catch (error) {
            console.error('Error loading document:', error);
            iframe.style.display = 'none';
            
            // Remove loading state
            const loadingDiv = documentInfo.querySelector('.text-center');
            if (loadingDiv) {
                loadingDiv.remove();
            }
            
            // Add error message with fallback options
            documentInfo.innerHTML += `
                <div class="alert alert-danger mt-3">
                    <h6>Error</h6>
                    <p>Failed to load PDF document.</p>
                    <div class="mt-2">
                        <button class="btn btn-primary btn-sm me-2" onclick="viewDocument(${id})">Reload</button>
                        <button class="btn btn-secondary btn-sm" onclick="openDocumentInNewTab(${id})">Open in New Tab</button>
                    </div>
                </div>
            `;
        }
    } else {
        iframe.style.display = 'none';
        documentInfo.innerHTML += '<p class="text-muted mt-3">No document uploaded</p>';
    }
    
    const modal = new bootstrap.Modal(document.getElementById('documentModal'));
    modal.show();
}

// Open document in new tab as fallback
async function openDocumentInNewTab(id) {
    const verification = verifications.find(v => v.id === id);
    if (!verification) {
        showToast('Error', 'Verification not found', 'error');
        return;
    }
    
    if (!verification.verification_document) {
        showToast('Error', 'No document available', 'error');
        return;
    }
    
    try {
        const token = localStorage.getItem('admin_access_token');
        if (!token) {
            showToast('Error', 'No authentication token', 'error');
            return;
        }
        
        // Create a direct URL to the document endpoint
        const documentUrl = `${API_BASE_URL}/verifications/${verification.id}/document/`;
        
        // Open in new tab with authentication
        const newWindow = window.open('', '_blank');
        if (newWindow) {
            newWindow.location.href = documentUrl;
        } else {
            // Fallback: try to open with fetch and blob
            const response = await fetch(documentUrl, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (response.ok) {
                const blob = await response.blob();
                const blobUrl = URL.createObjectURL(blob);
                window.open(blobUrl, '_blank');
            } else {
                showToast('Error', 'Failed to open document', 'error');
            }
        }
    } catch (error) {
        console.error('Error opening document in new tab:', error);
        showToast('Error', 'Failed to open document', 'error');
    }
}

// Archive verification
async function archiveVerification(id) {
    if (!confirm('Are you sure you want to archive this verification?')) {
        return;
    }
    
    showLoading(true);
    
    try {
        const response = await apiCall(`/verifications/${id}/archive/`, 'POST');
        if (response) {
            showToast('Success', 'Verification archived successfully', 'success');
            loadDashboardData();
        }
    } catch (error) {
        console.error('Error archiving verification:', error);
        showToast('Error', error.message || 'Failed to archive verification', 'error');
    } finally {
        showLoading(false);
    }
}

// Filter verifications
function filterVerifications() {
    const statusFilter = document.getElementById('statusFilter').value;
    const searchQuery = document.getElementById('searchInput').value.toLowerCase();
    
    let filtered = verifications;
    
    // Filter by status
    if (statusFilter) {
        filtered = filtered.filter(v => v.status === statusFilter);
    }
    
    // Filter by search query
    if (searchQuery) {
        filtered = filtered.filter(v => 
            v.user_full_name.toLowerCase().includes(searchQuery) ||
            v.user_email.toLowerCase().includes(searchQuery)
        );
    }
    
    renderVerificationsTable(filtered);
}

// Update admin name
function updateAdminName() {
    if (currentUser) {
        document.getElementById('adminName').textContent = currentUser.full_name;
    }
}

// API call helper
async function apiCall(endpoint, method = 'GET', data = null) {
    const token = localStorage.getItem('admin_access_token');
    if (!token) {
        logout();
        return null;
    }
    
    const options = {
        method: method,
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
            'X-CSRFToken': await getCSRFToken()
        }
    };
    
    if (data && method !== 'GET') {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
        
        if (response.status === 401) {
            // Token expired, try to refresh
            const refreshed = await refreshToken();
            if (refreshed) {
                return apiCall(endpoint, method, data);
            } else {
                logout();
                return null;
            }
        }
        
        let responseData;
        try {
            responseData = await response.json();
        } catch (_) {
            responseData = null;
        }

        if (!response.ok) {
            const statusText = response.statusText || 'Error';
            const detail = (responseData && (responseData.error || responseData.message)) || '';
            const msg = `HTTP ${response.status} ${statusText}${detail ? ' — ' + detail : ''}`;
            throw new Error(msg);
        }

        return responseData;
    } catch (error) {
        if (error.name === 'TypeError' || /Failed to fetch/i.test(String(error))) {
            console.error('Network error calling API:', error);
            throw new Error('Network error — cannot reach admin API (check server at localhost:8000).');
        }
        console.error('API call error:', error);
        throw error;
    }
}

// Refresh token
async function refreshToken() {
    const refreshToken = localStorage.getItem('admin_refresh_token');
    if (!refreshToken) {
        return false;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/token/refresh/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': await getCSRFToken()
            },
            body: JSON.stringify({ refresh: refreshToken })
        });
        
        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('admin_access_token', data.access);
            return true;
        }
    } catch (error) {
        console.error('Token refresh error:', error);
    }
    
    return false;
}

// Show toast notification
function showToast(title, message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastTitle = document.getElementById('toastTitle');
    const toastMessage = document.getElementById('toastMessage');
    
    toastTitle.textContent = title;
    toastMessage.textContent = message;
    
    // Remove existing classes
    toast.className = 'toast';
    
    // Add type-specific classes
    if (type === 'success') {
        toast.classList.add('bg-success', 'text-white');
    } else if (type === 'error') {
        toast.classList.add('bg-danger', 'text-white');
    } else if (type === 'warning') {
        toast.classList.add('bg-warning', 'text-dark');
    } else {
        toast.classList.add('bg-info', 'text-white');
    }
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

// Show/hide loading
function showLoading(show) {
    const loading = document.getElementById('loading');
    if (show) {
        loading.classList.add('show');
    } else {
        loading.classList.remove('show');
    }
}

// Format date
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

async function ensureHospitalRegistration() {
    try {
        const statusResp = await apiCall('/hospital/status/', 'GET');
        if (statusResp && statusResp.hospital_registration_completed === false) {
            showToast('Info', 'Please complete hospital registration.', 'info');
            window.location.href = 'hospital-registration.html';
            return false;
        }
        return true;
    } catch (e) {
        console.error('Failed to get hospital status', e);
        // If status check fails, allow dashboard to avoid locking out admin unexpectedly
        return true;
    }
}
