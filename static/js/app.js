/* ══════════════════════════════════════════════════════════════
   Criminal Recognition System v2.0 — Firebase-powered App Logic
   ══════════════════════════════════════════════════════════════ */

// ── Firebase Config (loaded from backend) ──────────────────────
let firebaseAuth = null;

// ── State ──────────────────────────────────────────────────────
let authToken = localStorage.getItem('crs_token') || null;
let currentUser = JSON.parse(localStorage.getItem('crs_user') || 'null');
let currentPage = 'dashboard';
let selectedFile = null;
let selectedPersonId = null;
let personSearchTimeout = null;

// ── Init ───────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    initTheme();

    // Fetch Firebase config from backend (no hardcoded keys!)
    try {
        const res = await fetch('/api/config/firebase');
        if (!res.ok) throw new Error('Failed to load Firebase config');
        const firebaseConfig = await res.json();
        firebase.initializeApp(firebaseConfig);
        firebaseAuth = firebase.auth();
    } catch (e) {
        console.error('Firebase init failed:', e);
        document.body.innerHTML = '<div style="padding:40px;text-align:center;color:#ef4444;font-size:18px;">⚠️ Failed to initialize Firebase. Check server configuration.</div>';
        return;
    }

    // Listen for Firebase auth state changes
    firebaseAuth.onAuthStateChanged(async (user) => {
        if (user && currentUser) {
            // Already have a session
            showApp();
            loadDashboard();
        } else if (user && !currentUser) {
            // Firebase user exists but no local session — recreate
            try {
                const idToken = await user.getIdToken();
                await createBackendSession(idToken);
                showApp();
                loadDashboard();
            } catch (e) {
                showLogin();
            }
        } else {
            showLogin();
        }
    });
});

// ── Theme ──────────────────────────────────────────────────────
function initTheme() {
    const savedTheme = 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    localStorage.setItem('crs_theme', savedTheme);
    updateThemeIcon(savedTheme);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('crs_theme', newTheme);
    updateThemeIcon(newTheme);
}

function updateThemeIcon(theme) {
    const iconDark = document.getElementById('themeIconDark');
    const iconLight = document.getElementById('themeIconLight');
    if (iconDark && iconLight) {
        if (theme === 'dark') {
            iconDark.style.display = 'none';
            iconLight.style.display = 'block';
        } else {
            iconDark.style.display = 'block';
            iconLight.style.display = 'none';
        }
    }
}

// ── API Client ─────────────────────────────────────────────────
async function api(url, options = {}) {
    const headers = { ...(options.headers || {}) };

    // Get fresh Firebase token for every request
    if (firebaseAuth.currentUser) {
        try {
            const freshToken = await firebaseAuth.currentUser.getIdToken();
            authToken = freshToken;
            localStorage.setItem('crs_token', freshToken);
            headers['Authorization'] = `Bearer ${freshToken}`;
        } catch (e) {
            if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
        }
    } else if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }

    if (!(options.body instanceof FormData) && options.body) {
        headers['Content-Type'] = 'application/json';
    }

    try {
        const res = await fetch(url, { ...options, headers });
        if (res.status === 401) {
            handleLogout();
            throw new Error('Session expired');
        }
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(err.detail || 'Request failed');
        }
        return await res.json();
    } catch (e) {
        if (e.message !== 'Session expired') showToast(e.message, 'error');
        throw e;
    }
}

// ── Auth (Firebase) ────────────────────────────────────────────
async function handleLogin() {
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    const btn = document.getElementById('loginBtn');
    const errorEl = document.getElementById('loginError');

    btn.disabled = true;
    btn.textContent = 'Authenticating...';
    errorEl.style.display = 'none';

    try {
        // Sign in with Firebase
        const userCredential = await firebaseAuth.signInWithEmailAndPassword(email, password);
        const idToken = await userCredential.user.getIdToken();

        // Create session on backend
        await createBackendSession(idToken);

        showApp();
        loadDashboard();
        showToast(`Welcome, ${currentUser.full_name}!`, 'success');
    } catch (e) {
        let msg = e.message;
        if (msg.includes('user-not-found')) msg = 'No officer account found with this email.';
        else if (msg.includes('wrong-password') || msg.includes('invalid-credential')) msg = 'Invalid password. Please try again.';
        else if (msg.includes('too-many-requests')) msg = 'Too many login attempts. Try again later.';
        errorEl.textContent = msg;
        errorEl.style.display = 'block';
    } finally {
        btn.disabled = false;
        btn.textContent = 'Authenticate';
    }
}

async function createBackendSession(idToken) {
    const res = await fetch('/api/auth/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_token: idToken }),
    });
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Session creation failed');
    }
    const data = await res.json();
    authToken = data.access_token;
    currentUser = data.officer;
    localStorage.setItem('crs_token', authToken);
    localStorage.setItem('crs_user', JSON.stringify(currentUser));
}

function handleLogout() {
    firebaseAuth.signOut();
    authToken = null;
    currentUser = null;
    localStorage.removeItem('crs_token');
    localStorage.removeItem('crs_user');
    showLogin();
}

function showLogin() {
    document.getElementById('loginPage').style.display = 'flex';
    document.getElementById('appShell').style.display = 'none';
}

function showApp() {
    document.getElementById('loginPage').style.display = 'none';
    document.getElementById('appShell').style.display = 'flex';
    updateUserInfo();
}

function updateUserInfo() {
    if (!currentUser) return;
    const nameEl = document.getElementById('userAvatar');
    const roleEl = document.getElementById('userRole');
    if (nameEl) nameEl.textContent = currentUser.full_name ? currentUser.full_name.charAt(0).toUpperCase() : 'U';
    if (roleEl) roleEl.textContent = currentUser.role || 'officer';
}

// ── Navigation ─────────────────────────────────────────────────
function navigate(page) {
    currentPage = page;
    document.querySelectorAll('.page-section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

    const pageEl = document.getElementById(`page-${page}`);
    if (pageEl) pageEl.classList.add('active');

    const navEl = document.querySelector(`.nav-item[data-page="${page}"]`);
    if (navEl) navEl.classList.add('active');

    switch (page) {
        case 'dashboard': loadDashboard(); break;
        case 'persons': loadPersons(); break;
        case 'audit': loadAuditLogs(); break;
    }
}

// ── Dashboard ──────────────────────────────────────────────────
async function loadDashboard() {
    try {
        const data = await api('/api/dashboard/stats');
        document.getElementById('statPersons').textContent = data.total_persons;
        document.getElementById('statRecords').textContent = data.total_records;
        document.getElementById('statSearches').textContent = data.total_searches;
        document.getElementById('statOfficers').textContent = data.total_officers;

        // Risk chart
        const riskData = {};
        for (const [key, val] of Object.entries(data.risk_distribution || {})) {
            riskData[key + ' Risk'] = val;
        }
        renderBarChart('riskChartCanvas', riskData, {
            'High Risk': '#cc1e38',
            'Medium Risk': '#de9b16',
            'Low Risk': '#1fa353',
        });

        // Status chart
        renderBarChart('statusChartCanvas', data.status_distribution || {}, {
            'Convicted': '#cc1e38',
            'Most Wanted': '#ef4444',
            'Under Investigation': '#de9b16',
            'Clean': '#1fa353',
            'Released': '#3b82f6',
        });

        // Most Wanted section
        renderMostWanted(data.most_wanted || []);

        // Recent Activity
        renderRecentActivity(data.recent_activity);

        // Latest Detections
        renderLatestDetections(data.latest_detections || []);
    } catch (e) { /* handled by api() */ }
}

// ── Dashboard Charts ───────────────────────────────────────
let riskChartInstance = null;
let statusChartInstance = null;

function renderBarChart(canvasId, data, colors) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || !data) return;

    if (canvasId === 'riskChartCanvas' && riskChartInstance) riskChartInstance.destroy();
    if (canvasId === 'statusChartCanvas' && statusChartInstance) statusChartInstance.destroy();

    const labels = Object.keys(data);
    const values = Object.values(data);
    const bgColors = labels.map(label => colors[label] || '#3b82f6');

    const plugins = typeof ChartDataLabels !== 'undefined' ? [ChartDataLabels] : [];

    const config = {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: bgColors,
                barPercentage: 0.8,
                categoryPercentage: 0.9
            }]
        },
        plugins: plugins,
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { enabled: true },
                datalabels: {
                    color: '#fff',
                    anchor: 'end',
                    align: 'start',
                    offset: 4,
                    font: { weight: 'bold', size: 11 },
                    formatter: Math.round
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255,255,255,0.05)', drawBorder: false },
                    ticks: { color: '#94a3b8', font: { size: 11 } }
                },
                y: {
                    grid: { display: false, drawBorder: false },
                    ticks: { color: '#94a3b8', font: { size: 12 } }
                }
            }
        }
    };

    const instance = new Chart(ctx, config);
    if (canvasId === 'riskChartCanvas') riskChartInstance = instance;
    if (canvasId === 'statusChartCanvas') statusChartInstance = instance;
}

function renderMostWanted(wanted) {
    const grid = document.getElementById('mostWantedGrid');
    if (!wanted || wanted.length === 0) {
        grid.innerHTML = '<div class="empty-state" style="padding:20px;">No most wanted subjects registered.</div>';
        return;
    }
    grid.innerHTML = wanted.map(p => {
        const avatarHtml = p.image_path ? `<img src="${p.image_path}" alt="${p.full_name}" style="width:100%; height:100%; object-fit:cover; border-radius:50%;">` : (p.full_name || '?').charAt(0);
        return `
        <div class="most-wanted-card" onclick="viewPersonDetail('${p.id}')">
            <div class="mw-avatar">${avatarHtml}</div>
            <div class="mw-info">
                <div class="mw-name">${p.full_name}</div>
                <div class="mw-location">📍 ${p.last_seen_location || 'Unknown'}</div>
                <span class="badge badge-risk-high">${p.record_status || 'Wanted'}</span>
            </div>
        </div>
    `}).join('');
}

function renderRecentActivity(activities) {
    const tbody = document.getElementById('recentActivityTable');
    if (!activities || !activities.length) {
        tbody.innerHTML = '<tr><td colspan="4" class="empty-state"><div class="empty-text">No recent activity</div></td></tr>';
        return;
    }

    tbody.innerHTML = activities.slice(0, 8).map(a => {
        let timeStr = '—';
        if (a.timestamp) {
            const d = new Date(a.timestamp);
            const mm = String(d.getMonth() + 1).padStart(2, '0');
            const dd = String(d.getDate()).padStart(2, '0');
            const yy = String(d.getFullYear()).slice(-2);
            const hh = String(d.getHours()).padStart(2, '0');
            const min = String(d.getMinutes()).padStart(2, '0');
            timeStr = `${dd}-${mm}-${yy} ${hh}:${min}`;
        }

        const actionClass = a.action_type === 'Search' ? 'badge-action-search' :
                            a.action_type === 'Login' ? 'badge-risk-low' :
                            a.action_type === 'Delete' ? 'badge-risk-high' : 'badge-action-search';

        return `
            <tr>
                <td>${timeStr}</td>
                <td>${a.officer_name}</td>
                <td><span class="badge ${actionClass}">${a.action_type}</span></td>
                <td>${a.details || '—'}</td>
            </tr>
        `;
    }).join('');
}

function renderLatestDetections(detections) {
    const container = document.getElementById('latestDetectionsContent');
    if (!detections || detections.length === 0) {
        container.innerHTML = '<div class="empty-state" style="padding:20px;">No face detections recorded yet.</div>';
        return;
    }
    container.innerHTML = detections.map(d => {
        let timeStr = '—';
        if (d.timestamp) {
            const dt = new Date(d.timestamp);
            timeStr = dt.toLocaleDateString() + ' ' + dt.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
        }
        return `
            <div class="detection-item" ${d.person_id ? `onclick="viewPersonDetail('${d.person_id}')" style="cursor:pointer;"` : ''}>
                <div class="detection-icon">🎯</div>
                <div class="detection-info">
                    <div class="detection-details">${d.details || 'Face match detected'}</div>
                    <div class="detection-meta">${d.officer_name} — ${timeStr}</div>
                </div>
            </div>
        `;
    }).join('');
}

// ── Face Search ────────────────────────────────────────────────
function switchSearchTab(tab) {
    document.querySelectorAll('#searchTabs .tab').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');

    if (tab === 'upload') {
        document.getElementById('uploadTab').style.display = 'block';
        document.getElementById('cameraTab').style.display = 'none';
        stopWebcam();
    } else {
        document.getElementById('uploadTab').style.display = 'none';
        document.getElementById('cameraTab').style.display = 'block';
        startWebcam();
    }
}

function handleDragOver(e) { e.preventDefault(); document.getElementById('uploadZone').classList.add('drag-over'); }
function handleDragLeave(e) { document.getElementById('uploadZone').classList.remove('drag-over'); }
function handleDrop(e) {
    e.preventDefault();
    document.getElementById('uploadZone').classList.remove('drag-over');
    if (e.dataTransfer.files.length > 0) processFile(e.dataTransfer.files[0]);
}
function handleFileSelect(e) { if (e.target.files.length > 0) processFile(e.target.files[0]); }

function processFile(file) {
    if (!file.type.match(/^image\/(jpeg|png|webp)$/)) {
        showToast('Please upload a JPG, PNG, or WebP image', 'error');
        return;
    }
    selectedFile = file;
    const preview = document.getElementById('uploadPreview');
    const reader = new FileReader();
    reader.onload = (e) => {
        preview.src = e.target.result;
        preview.style.display = 'block';
        document.querySelector('#uploadZone .upload-icon').style.display = 'none';
        document.querySelector('#uploadZone .upload-text').style.display = 'none';
    };
    reader.readAsDataURL(file);
    document.getElementById('searchBtn').disabled = false;
}

// Webcam
let webcamStream = null;
async function startWebcam() {
    try {
        webcamStream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
        const video = document.getElementById('webcamVideo');
        video.srcObject = webcamStream;
        video.style.display = 'block';
        document.getElementById('capturePreview').style.display = 'none';
    } catch (e) {
        showToast('Camera access denied or unavailable', 'error');
    }
}

function stopWebcam() {
    if (webcamStream) {
        webcamStream.getTracks().forEach(t => t.stop());
        webcamStream = null;
    }
}

function captureWebcam() {
    const video = document.getElementById('webcamVideo');
    const canvas = document.getElementById('webcamCanvas');
    const capturePreview = document.getElementById('capturePreview');

    if (!webcamStream) { showToast('Camera not active', 'error'); return; }

    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    canvas.getContext('2d').drawImage(video, 0, 0);

    stopWebcam();
    video.style.display = 'none';

    const dataUrl = canvas.toDataURL('image/jpeg', 0.95);
    capturePreview.src = dataUrl;
    capturePreview.style.display = 'block';

    canvas.toBlob((blob) => {
        selectedFile = new File([blob], 'capture.jpg', { type: 'image/jpeg' });
        document.getElementById('searchBtn').disabled = false;
    }, 'image/jpeg', 0.95);

    showToast('Photo captured! Click "Initialize Scan" to search.', 'success');
}

function retakePhoto() {
    document.getElementById('capturePreview').style.display = 'none';
    selectedFile = null;
    document.getElementById('searchBtn').disabled = true;
    startWebcam();
}

async function performSearch() {
    if (!selectedFile) return;

    const btn = document.getElementById('searchBtn');
    const resultsDiv = document.getElementById('searchResults');
    btn.disabled = true;
    btn.textContent = 'Analyzing...';
    resultsDiv.innerHTML = '<div class="loading-overlay"><div class="spinner"></div><span>Detecting faces and searching database...</span></div>';

    try {
        const formData = new FormData();
        formData.append('image', selectedFile);
        formData.append('threshold', document.getElementById('searchThreshold').value);
        formData.append('max_results', document.getElementById('searchMaxResults').value);

        const data = await api('/api/search/face', { method: 'POST', body: formData });

        // Liveness check
        renderLivenessCheck(data.liveness_check);

        if (data.matches.length === 0) {
            // NO MATCH — show "Add to Database" button
            resultsDiv.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🔍</div>
                    <div class="empty-text">No Matches Found</div>
                    <div class="empty-subtext">No persons in the database matched the uploaded face above the confidence threshold (${(data.threshold_used * 100).toFixed(0)}%).</div>
                    <button class="btn btn-primary" style="margin-top:16px;" onclick="addUnmatchedToDatabase()">
                        ➕ Add Subject to Database
                    </button>
                </div>
            `;
            document.getElementById('resultCount').style.display = 'none';
        } else {
            document.getElementById('resultCount').style.display = 'inline-flex';
            document.getElementById('resultCount').textContent = `${data.total_matches} match${data.total_matches > 1 ? 'es' : ''}`;
            document.getElementById('resultCount').className = 'badge badge-action-search';

            resultsDiv.innerHTML = data.matches.map(m => {
                const confClass = m.confidence > 70 ? 'confidence-high' : m.confidence > 40 ? 'confidence-medium' : 'confidence-low';
                const confColor = m.confidence > 70 ? 'var(--accent-red)' : m.confidence > 40 ? 'var(--accent-amber)' : 'var(--accent-emerald)';
                const riskClass = m.risk_level ? m.risk_level.toLowerCase() : 'low';
                const statusBadge = getStatusBadge(m.record_status);
                
                // Criminal records summary
                let crimesSummary = '';
                if (m.criminal_records && m.criminal_records.length > 0) {
                    const crimeTypes = m.criminal_records.map(r => r.crime_type).filter(Boolean);
                    crimesSummary = `
                        <div class="match-crimes">
                            <span style="font-size:11px;color:var(--text-muted);">📋 Crimes:</span>
                            ${crimeTypes.map(ct => `<span class="badge badge-risk-high" style="font-size:10px;padding:2px 6px;">${ct}</span>`).join(' ')}
                        </div>
                    `;
                }

                return `
                    <div class="match-result" onclick="viewPersonDetail('${m.person_id}', ${m.confidence})">
                        <div class="match-header">
                            <div class="match-name">${m.full_name}</div>
                            <div class="match-confidence ${confClass}">${m.confidence.toFixed(1)}%</div>
                        </div>
                        <div class="match-meta">
                            ${statusBadge}
                            <div class="risk-indicator">
                                <div class="risk-dot ${riskClass}"></div>
                                <span style="font-size:12px;color:var(--text-secondary);">${m.risk_level || 'N/A'} Risk</span>
                            </div>
                            <span class="match-meta-item">📅 ${m.date_of_birth || 'N/A'}</span>
                            <span class="match-meta-item">🌍 ${m.nationality || 'N/A'}</span>
                            <span class="match-meta-item">📍 ${m.last_seen_location || 'N/A'}</span>
                        </div>
                        ${crimesSummary}
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width:${m.confidence}%;background:${confColor};"></div>
                        </div>
                    </div>
                `;
            }).join('');
        }
    } catch (e) {
        resultsDiv.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">❌</div>
                <div class="empty-text">Search Failed</div>
                <div class="empty-subtext">${e.message}</div>
            </div>
        `;
    } finally {
        btn.disabled = false;
        btn.textContent = 'Initialize Scan';
    }
}

function addUnmatchedToDatabase() {
    // Open the add person modal, optionally pre-filling the photo
    openAddPersonModal();
    // If we have a selected file, set it as the photo input
    if (selectedFile) {
        showToast('Upload the same image (or a better one) in the photo field to register this subject.', 'info');
    }
}

function renderLivenessCheck(liveness) {
    if (!liveness) return;
    const card = document.getElementById('livenessCard');
    card.style.display = 'block';

    const statusEl = document.getElementById('livenessStatus');
    statusEl.textContent = liveness.passed ? 'Passed' : 'Warning';
    statusEl.className = `badge ${liveness.passed ? 'badge-risk-low' : 'badge-risk-medium'}`;

    const checksEl = document.getElementById('livenessChecks');
    if (liveness.checks && liveness.checks.length > 0) {
        checksEl.innerHTML = liveness.checks.map(c => `
            <div class="liveness-check-item ${c.passed ? 'passed' : 'failed'}">
                <div class="liveness-status">
                    ${c.passed ? '✅' : '❌'} ${c.name}
                </div>
                <div style="font-size:11px;color:var(--text-muted);margin-top:4px;">${c.detail}</div>
                <div style="font-size:11px;color:var(--text-secondary);margin-top:2px;">Score: ${c.score}</div>
            </div>
        `).join('');
    } else {
        checksEl.innerHTML = '<div style="padding:10px;color:var(--text-muted);">No detailed checks available.</div>';
    }
}

// ── Person Detail ──────────────────────────────────────────────
async function viewPersonDetail(personId, confidence) {
    selectedPersonId = personId;
    navigate('person-detail');
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

    const content = document.getElementById('personDetailContent');
    content.innerHTML = '<div class="loading-overlay"><div class="spinner"></div><span>Loading person details...</span></div>';

    try {
        const person = await api(`/api/persons/${personId}`);
        const riskClass = (person.risk_level || 'low').toLowerCase();
        const confClass = confidence > 70 ? 'confidence-high' : confidence > 40 ? 'confidence-medium' : 'confidence-low';
        const initials = person.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
        const avatarHtml = person.image_path ? `<img src="${person.image_path}" alt="${person.full_name}" style="width:100%; height:100%; object-fit:cover; border-radius:50%;">` : `${initials}`;

        content.innerHTML = `
            <!-- Left Panel -->
            <div class="person-photo-section">
                <div class="card">
                    <div class="person-photo">${avatarHtml}</div>
                    ${confidence ? `
                        <div class="person-confidence ${confClass}">${confidence.toFixed(1)}%</div>
                        <div class="person-confidence-label">Match Confidence</div>
                    ` : ''}
                    <div style="display:flex;flex-direction:column;gap:8px;align-items:center;">
                        <div class="risk-indicator" style="justify-content:center;">
                            <div class="risk-dot ${riskClass}"></div>
                            <span style="font-weight:600;">${person.risk_level || 'N/A'} Risk</span>
                        </div>
                        ${getStatusBadge(person.record_status)}
                    </div>
                    <div style="margin-top:20px;">
                        <button class="btn btn-primary" style="width:100%" onclick="openAddRecordModal()">
                            ➕ Add Record
                        </button>
                    </div>
                </div>

                <div class="card" style="margin-top:16px;">
                    <div class="card-title" style="margin-bottom:12px;">📋 Identity</div>
                    <div style="display:flex;flex-direction:column;gap:8px;">
                        <div class="info-item">
                            <div class="info-label">Full Name</div>
                            <div class="info-value">${person.full_name}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Date of Birth</div>
                            <div class="info-value">${person.date_of_birth || 'N/A'}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Gender</div>
                            <div class="info-value">${person.gender || 'N/A'}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Nationality</div>
                            <div class="info-value">${person.nationality || 'N/A'}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Address</div>
                            <div class="info-value">${person.address || 'N/A'}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Last Seen Location</div>
                            <div class="info-value" style="color:var(--accent-amber);">📍 ${person.last_seen_location || 'N/A'}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Government ID</div>
                            <div class="info-value">${person.government_id_number || 'N/A'}</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Right Panel -->
            <div>
                <div class="card" style="margin-bottom:20px;">
                    <div class="card-header">
                        <div class="card-title">📜 Criminal History</div>
                        <span class="badge badge-action-search">${(person.criminal_records || []).length} record${(person.criminal_records || []).length !== 1 ? 's' : ''}</span>
                    </div>
                    ${person.criminal_records && person.criminal_records.length > 0 ? `
                        <div class="timeline">
                            ${person.criminal_records.map(r => `
                                <div class="timeline-item">
                                    <div class="timeline-crime-type">
                                        ⚖️ ${r.crime_type}
                                        ${r.conviction_status ? `<span class="badge ${getConvictionBadgeClass(r.conviction_status)}">${r.conviction_status}</span>` : ''}
                                    </div>
                                    ${r.crime_description ? `<p style="font-size:13px;color:var(--text-secondary);margin-bottom:10px;">${r.crime_description}</p>` : ''}
                                    <div class="timeline-details">
                                        <div class="timeline-detail-item">
                                            <div class="timeline-detail-label">Case Number</div>
                                            <div>${r.case_number || 'N/A'}</div>
                                        </div>
                                        <div class="timeline-detail-item">
                                            <div class="timeline-detail-label">Date of Offense</div>
                                            <div>${r.date_of_offense || 'N/A'}</div>
                                        </div>
                                        <div class="timeline-detail-item">
                                            <div class="timeline-detail-label">Arrest Date</div>
                                            <div>${r.arrest_date || 'N/A'}</div>
                                        </div>
                                        <div class="timeline-detail-item">
                                            <div class="timeline-detail-label">Sentence</div>
                                            <div>${r.sentence_details || 'N/A'}</div>
                                        </div>
                                        <div class="timeline-detail-item">
                                            <div class="timeline-detail-label">Agency</div>
                                            <div>${r.law_enforcement_agency || 'N/A'}</div>
                                        </div>
                                        <div class="timeline-detail-item">
                                            <div class="timeline-detail-label">Court</div>
                                            <div>${r.court_name || 'N/A'}</div>
                                        </div>
                                    </div>
                                    ${r.officer_notes ? `
                                        <div style="margin-top:10px;padding:10px;background:var(--bg-input);border-radius:var(--radius-sm);font-size:12px;color:var(--text-muted);">
                                            📝 ${r.officer_notes}
                                        </div>
                                    ` : ''}
                                </div>
                            `).join('')}
                        </div>
                    ` : `
                        <div class="empty-state" style="padding:30px;">
                            <div class="empty-icon">📋</div>
                            <div class="empty-text">No Criminal Records</div>
                            <div class="empty-subtext">This person has no criminal records on file.</div>
                        </div>
                    `}
                </div>
            </div>
        `;
    } catch (e) {
        content.innerHTML = `<div class="empty-state"><div class="empty-icon">❌</div><div class="empty-text">Failed to Load</div><div class="empty-subtext">${e.message}</div></div>`;
    }
}

// ── Persons Database ───────────────────────────────────────────
let selectedPersonIds = new Set();
let deleteMode = false;
let loadedPersonIds = [];

function toggleDeleteMode() {
    deleteMode = !deleteMode;
    const modeBtn = document.getElementById('deleteModeBtn');
    const actionBar = document.getElementById('deleteActionBar');

    if (deleteMode) {
        modeBtn.style.opacity = '1';
        modeBtn.style.boxShadow = '0 0 20px rgba(239, 68, 68, 0.5)';
        actionBar.style.display = 'flex';
        showToast('Delete Mode ON — click on cards to select them', 'warning');
    } else {
        modeBtn.style.opacity = '0.7';
        modeBtn.style.boxShadow = '';
        actionBar.style.display = 'none';
        selectedPersonIds.clear();
        document.querySelectorAll('.person-card.selected').forEach(c => c.classList.remove('selected'));
    }
    updateDeleteUI();
}

function updateDeleteUI() {
    const countEl = document.getElementById('selectedCount');
    const confirmBtn = document.getElementById('confirmDeleteBtn');
    const barText = document.getElementById('deleteBarText');
    countEl.textContent = selectedPersonIds.size;
    if (selectedPersonIds.size > 0) {
        confirmBtn.style.display = 'inline-flex';
        barText.textContent = `${selectedPersonIds.size} subject(s) selected for deletion`;
    } else {
        confirmBtn.style.display = 'none';
        barText.textContent = 'Select subjects to remove by clicking on their cards';
    }
}

function handlePersonCardClick(personId) {
    if (deleteMode) {
        if (selectedPersonIds.has(personId)) selectedPersonIds.delete(personId);
        else selectedPersonIds.add(personId);
        const card = document.getElementById(`person-card-${personId}`);
        if (card) card.classList.toggle('selected', selectedPersonIds.has(personId));
        updateDeleteUI();
    } else {
        viewPersonDetail(personId);
    }
}

function selectAllPersons() {
    loadedPersonIds.forEach(id => {
        selectedPersonIds.add(id);
        const card = document.getElementById(`person-card-${id}`);
        if (card) card.classList.add('selected');
    });
    updateDeleteUI();
}

function deselectAllPersons() {
    selectedPersonIds.clear();
    document.querySelectorAll('.person-card.selected').forEach(c => c.classList.remove('selected'));
    updateDeleteUI();
}

async function deleteSelectedPersons() {
    if (selectedPersonIds.size === 0) return;
    const count = selectedPersonIds.size;
    const confirmed = confirm(
        `DELETE ${count} PERSON(S)?\n\nThis will permanently delete:\n${count} person record(s)\nAll associated criminal records\nAll associated photos & face data\n\nThis action CANNOT be undone. Continue?`
    );
    if (!confirmed) return;

    try {
        const result = await api('/api/persons/bulk-delete', {
            method: 'POST',
            body: JSON.stringify({ person_ids: Array.from(selectedPersonIds) }),
        });
        showToast(`${result.deleted_count} person(s) deleted: ${result.deleted_names.join(', ')}`, 'success');
        selectedPersonIds.clear();
        updateDeleteUI();
        toggleDeleteMode();
        loadPersons();
        loadDashboard();
    } catch (e) { /* handled by api() */ }
}

async function loadPersons() {
    const grid = document.getElementById('personsGrid');
    grid.innerHTML = '<div class="loading-overlay"><div class="spinner"></div><span>Loading persons...</span></div>';

    try {
        const search = document.getElementById('personSearchInput').value;
        const status = document.getElementById('personStatusFilter').value;
        const risk = document.getElementById('personRiskFilter').value;
        let url = '/api/persons?limit=50';
        if (search) url += `&search=${encodeURIComponent(search)}`;
        if (status) url += `&status=${encodeURIComponent(status)}`;
        if (risk) url += `&risk=${encodeURIComponent(risk)}`;

        const data = await api(url);
        loadedPersonIds = data.persons.map(p => p.id);

        if (!data.persons.length) {
            grid.innerHTML = '<div class="empty-state"><div class="empty-icon">📁</div><div class="empty-text">No Subjects Found</div></div>';
            return;
        }

        grid.innerHTML = data.persons.map(p => {
            const riskClass = (p.risk_level || 'low').toLowerCase();
            const initials = p.full_name ? p.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) : '?';
            const avatarHtml = p.image_path ? `<img src="${p.image_path}" alt="${p.full_name}" style="width:100%; height:100%; object-fit:cover; border-radius:50%;">` : `${initials}`;
            const statusBadge = getStatusBadge(p.record_status);

            return `
                <div class="person-card ${selectedPersonIds.has(p.id) ? 'selected' : ''}"
                     id="person-card-${p.id}"
                     onclick="handlePersonCardClick('${p.id}')">
                    <div class="person-card-header">
                        <div class="person-card-avatar">${avatarHtml}</div>
                        <div style="flex:1">
                            <div class="person-card-name">${p.full_name}</div>
                            <div style="font-size:11px;color:var(--text-muted);">
                                ${p.nationality || 'N/A'} | ${p.date_of_birth || 'N/A'}
                            </div>
                        </div>
                        <div class="risk-dot ${riskClass}" title="${p.risk_level || 'N/A'} Risk"></div>
                    </div>
                    <div class="person-card-body">
                        ${statusBadge}
                        ${p.has_embedding ? '<span class="badge badge-risk-low" style="font-size:10px;">Face Data ✓</span>' : ''}
                    </div>
                </div>
            `;
        }).join('');

    } catch (e) { /* handled by api() */ }
}

function debouncePersonSearch() {
    clearTimeout(personSearchTimeout);
    personSearchTimeout = setTimeout(loadPersons, 300);
}

// ── Audit Log ──────────────────────────────────────────────────
async function loadAuditLogs() {
    const tbody = document.getElementById('auditTableBody');
    tbody.innerHTML = '<tr><td colspan="5">Loading logs...</td></tr>';

    try {
        const actionFilter = document.getElementById('auditActionFilter').value;
        let url = '/api/audit?limit=100';
        if (actionFilter) url += `&action_type=${encodeURIComponent(actionFilter)}`;

        const data = await api(url);

        if (!data.logs.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No audit logs found.</td></tr>';
            return;
        }

        tbody.innerHTML = data.logs.map(log => {
            let timeStr = '—';
            if (log.timestamp) {
                const d = new Date(log.timestamp);
                timeStr = d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
            }
            const actionClass = log.action_type === 'Search' ? 'badge-action-search' :
                                log.action_type === 'Login' ? 'badge-risk-low' :
                                log.action_type === 'Delete' ? 'badge-risk-high' : 'badge-action-search';

            return `
                <tr>
                    <td>${timeStr}</td>
                    <td>${log.officer_name}</td>
                    <td><span class="badge ${actionClass}">${log.action_type}</span></td>
                    <td>${log.person_name || (log.person_id ? 'ID: ' + log.person_id.slice(0, 8) : '—')}</td>
                    <td>${log.details || '—'}</td>
                </tr>
            `;
        }).join('');

    } catch (e) { /* handled */ }
}

// ── Modals ─────────────────────────────────────────────────────
function openAddPersonModal() {
    document.getElementById('addPersonModal').classList.add('active');
}

function openAddRecordModal() {
    if (!selectedPersonId) { showToast('No subject selected', 'error'); return; }
    document.getElementById('recordPersonId').value = selectedPersonId;
    document.getElementById('addRecordModal').classList.add('active');
}

function closeModal(id) {
    document.getElementById(id).classList.remove('active');
}

async function submitAddPerson() {
    const name = document.getElementById('personFullName').value;
    if (!name) { showToast('Legal name is required', 'error'); return; }

    const formData = new FormData();
    formData.append('full_name', name);
    formData.append('date_of_birth', document.getElementById('personDob').value || '');
    formData.append('gender', document.getElementById('personGender').value || '');
    formData.append('nationality', document.getElementById('personNationality').value || '');
    formData.append('address', document.getElementById('personAddress').value || '');
    formData.append('government_id_number', document.getElementById('personGovId').value || '');
    formData.append('last_seen_location', document.getElementById('personLastSeen').value || '');
    formData.append('record_status', document.getElementById('personRecordStatus').value || 'Clean');
    formData.append('risk_level', document.getElementById('personRiskLevel').value || 'Low');

    const photoInput = document.getElementById('personPhoto');
    if (photoInput.files.length > 0) {
        for (let i = 0; i < photoInput.files.length; i++) {
            formData.append('photos', photoInput.files[i]);
        }
    }

    try {
        await api('/api/persons', { method: 'POST', body: formData });
        showToast('Subject registered successfully', 'success');
        closeModal('addPersonModal');
        document.getElementById('addPersonForm').reset();
        loadPersons();
        loadDashboard();
    } catch (e) { /* handled */ }
}

async function submitAddRecord() {
    const personId = document.getElementById('recordPersonId').value;
    const crimeType = document.getElementById('recordCrimeType').value;
    if (!crimeType) { showToast('Crime classification is required', 'error'); return; }

    const payload = {
        person_id: personId,
        crime_type: crimeType,
        crime_description: document.getElementById('recordCrimeDescription').value || null,
        case_number: document.getElementById('recordCaseNumber').value || null,
        date_of_offense: document.getElementById('recordDateOfOffense').value || null,
        arrest_date: document.getElementById('recordArrestDate').value || null,
        conviction_status: document.getElementById('recordConvictionStatus').value || null,
        sentence_details: document.getElementById('recordSentenceDetails').value || null,
        law_enforcement_agency: document.getElementById('recordAgency').value || null,
        court_name: document.getElementById('recordCourtName').value || null,
        officer_notes: document.getElementById('recordOfficerNotes').value || null,
        update_record_status: document.getElementById('recordUpdateStatus').value || null,
        update_risk_level: document.getElementById('recordUpdateRisk').value || null,
    };

    try {
        await api('/api/records', {
            method: 'POST',
            body: JSON.stringify(payload),
        });
        showToast('Criminal record added', 'success');
        closeModal('addRecordModal');
        document.getElementById('addRecordForm').reset();
        viewPersonDetail(personId);
    } catch (e) { /* handled */ }
}

// ── Export ──────────────────────────────────────────────────────
async function exportExcel() {
    try {
        let token = authToken;
        if (firebaseAuth.currentUser) {
            token = await firebaseAuth.currentUser.getIdToken();
        }
        const res = await fetch('/api/export/excel', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) throw new Error('Export failed');
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `criminal_records_export.xlsx`;
        a.click();
        URL.revokeObjectURL(url);
        showToast('Export downloaded!', 'success');
    } catch (e) {
        showToast('Export failed: ' + e.message, 'error');
    }
}

// ── Utilities ──────────────────────────────────────────────────
function getStatusBadge(status) {
    const map = {
        'Clean': 'badge-risk-low',
        'Under Investigation': 'badge-risk-medium',
        'Convicted': 'badge-risk-high',
        'Released': 'badge-action-search',
        'Most Wanted': 'badge-risk-high',
        'Absconding': 'badge-risk-high',
        'Wanted': 'badge-risk-high',
    };
    const cls = map[status] || 'badge-action-search';
    return `<span class="badge ${cls}">${status || 'N/A'}</span>`;
}

function getConvictionBadgeClass(status) {
    const map = {
        'Convicted': 'badge-risk-high',
        'Pending Trial': 'badge-risk-medium',
        'Acquitted': 'badge-risk-low',
        'Dismissed': 'badge-risk-low',
        'On Appeal': 'badge-risk-medium',
        'Wanted': 'badge-risk-high',
        'Absconding': 'badge-risk-high',
        'Killed in Encounter': 'badge-risk-high',
        'Killed in Operation': 'badge-risk-high',
        'Released': 'badge-action-search',
        'Deceased': 'badge-action-search',
        'Case closed (deceased)': 'badge-action-search',
        'Under Investigation': 'badge-risk-medium',
    };
    return map[status] || 'badge-action-search';
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}
