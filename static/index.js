// Client-side rate limiting
const MAX_REQUESTS_PER_MINUTE = 3;
const RATE_LIMIT_WINDOW = 90000;
const MIN_DELAY_BETWEEN_REQUESTS = 20;
const STORAGE_KEY = 'gemini_request_history';

function getRequestHistory() {
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored) {
            const history = JSON.parse(stored);
            const now = Date.now();
            return history.filter(time => now - time < RATE_LIMIT_WINDOW);
        }
    } catch (e) {
        console.warn('Could not read request history from localStorage', e);
    }
    return [];
}

function saveRequestHistory(history) {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
    } catch (e) {
        console.warn('Could not save request history to localStorage', e);
    }
}

function canMakeRequest() {
    const now = Date.now();
    let requestHistory = getRequestHistory();
    requestHistory = requestHistory.filter(time => now - time < RATE_LIMIT_WINDOW);

    if (requestHistory.length >= MAX_REQUESTS_PER_MINUTE) {
        const oldestRequest = requestHistory[0];
        const waitTime = Math.ceil((RATE_LIMIT_WINDOW - (now - oldestRequest)) / 1000);
        return { allowed: false, waitTime: waitTime, remaining: MAX_REQUESTS_PER_MINUTE - requestHistory.length };
    }

    return { allowed: true, waitTime: 0, remaining: MAX_REQUESTS_PER_MINUTE - requestHistory.length };
}

function recordRequest() {
    const now = Date.now();
    let requestHistory = getRequestHistory();
    requestHistory = requestHistory.filter(time => now - time < RATE_LIMIT_WINDOW);
    requestHistory.push(now);
    saveRequestHistory(requestHistory);
}

function clearRateLimitHistory() {
    try {
        localStorage.removeItem(STORAGE_KEY);
        updateRateLimitDisplay();
        alert('Rate limit counter has been reset. You can now make requests again.');
    } catch (e) {
        console.warn('Could not clear rate limit history', e);
    }
}

function updateRateLimitDisplay() {
    const requestHistory = getRequestHistory();
    const count = requestHistory.length;
    const requestCountEl = document.getElementById('requestCount');
    const maxRequestsEl = document.getElementById('maxRequests');
    const rateLimitPanel = document.getElementById('rateLimitPanel');

    if (requestCountEl) requestCountEl.textContent = count;
    if (maxRequestsEl) maxRequestsEl.textContent = MAX_REQUESTS_PER_MINUTE;

    if (rateLimitPanel && !rateLimitPanel.classList.contains('collapsed')) {
        rateLimitPanel.classList.remove('warning', 'limit-reached');
        if (count >= MAX_REQUESTS_PER_MINUTE) {
            rateLimitPanel.classList.add('limit-reached');
        } else if (count >= MAX_REQUESTS_PER_MINUTE - 2) {
            rateLimitPanel.classList.add('warning');
        }
    }
}

// Rate limit toggle - panel hidden by default
document.addEventListener('DOMContentLoaded', function() {
    const toggleBtn = document.getElementById('rateLimitToggle');
    const rateLimitPanel = document.getElementById('rateLimitPanel');
    const clearBtn = document.getElementById('clearRateLimit');

    if (toggleBtn && rateLimitPanel) {
        toggleBtn.addEventListener('click', function() {
            rateLimitPanel.classList.toggle('collapsed');
            if (!rateLimitPanel.classList.contains('collapsed')) {
                updateRateLimitDisplay();
            }
        });
    }

    if (clearBtn) {
        clearBtn.addEventListener('click', clearRateLimitHistory);
    }

    updateRateLimitDisplay();
});
setInterval(updateRateLimitDisplay, 5000);

// File drop zone
const fileDropZone = document.getElementById('fileDropZone');
const productImageInput = document.getElementById('productImage');
const fileList = document.getElementById('fileList');

function updateFileList() {
    if (!productImageInput || !fileList) return;
    const files = productImageInput.files;
    fileList.innerHTML = '';
    for (let i = 0; i < files.length; i++) {
        const tag = document.createElement('span');
        tag.className = 'file-tag';
        tag.innerHTML = '<i class="fas fa-file-image"></i> ' + files[i].name.substring(0, 20) + (files[i].name.length > 20 ? '...' : '') + ' <i class="fas fa-times" data-index="' + i + '"></i>';
        tag.querySelector('.fa-times').addEventListener('click', function(e) {
            e.stopPropagation();
            const dt = new DataTransfer();
            for (let j = 0; j < files.length; j++) {
                if (j !== parseInt(this.dataset.index)) dt.items.add(files[j]);
            }
            productImageInput.files = dt.files;
            updateFileList();
        });
        fileList.appendChild(tag);
    }
}

if (fileDropZone && productImageInput) {
    ['dragenter', 'dragover'].forEach(e => {
        fileDropZone.addEventListener(e, (ev) => { ev.preventDefault(); fileDropZone.classList.add('dragover'); });
    });
    ['dragleave', 'drop'].forEach(e => {
        fileDropZone.addEventListener(e, (ev) => { ev.preventDefault(); fileDropZone.classList.remove('dragover'); });
    });
    fileDropZone.addEventListener('drop', (e) => {
        productImageInput.files = e.dataTransfer.files;
        updateFileList();
    });
    productImageInput.addEventListener('change', updateFileList);
}

// Helper to create alert HTML
function alertHTML(type, content) {
    return '<div class="alert-box alert-' + type + '">' + content + '</div>';
}

// Section headings to detect (case-insensitive)
const SECTION_HEADINGS = ['conclusion', 'verdict', 'summary', 'overall assessment', 'recommendation', 'recommendations', 'ingredient analysis', 'ingredients analysis', 'analysis', 'key findings'];

// Helper to check if a line is a section heading
function isSectionHeading(line) {
    const t = line.replace(/^[#*_**]+|\*+$|:+$/g, '').trim().toLowerCase();
    if (t.length > 80) return false;
    if (SECTION_HEADINGS.some(h => t === h || t.startsWith(h + ':') || t.startsWith(h + ' -'))) return true;
    if ((line.endsWith(':') || /^[*#_]+/.test(line)) && t.length < 50) return true;
    return false;
}

// Helper to check if text is conclusion/verdict (the main fit/not fit part)
function isConclusionSection(heading) {
    const t = heading.toLowerCase();
    return /conclusion|verdict|summary|overall|final (assessment|verdict)/i.test(t);
}

// Helper to detect verdict type for styling
function getVerdictType(text) {
    const t = text.toLowerCase();
    if (/not suitable|not recommended|avoid|unsafe|harmful|risk/i.test(t)) return 'unsuitable';
    if (/suitable with caution|use with caution|moderate|some concerns/i.test(t)) return 'caution';
    return 'suitable';
}

// Helper to format analysis - now handles HTML output from AI
function formatStructuredAnalysis(analysis) {
    const raw = (analysis || '').trim();
    if (!raw) return '';

    // If the analysis starts with HTML tags, return it as-is
    if (raw.startsWith('<h2>') || raw.startsWith('<h3>') || raw.includes('<p>') || raw.includes('<ul>')) {
        return raw;
    }

    // Fallback for plain text (legacy support)
    const lines = raw.split('\n').map(l => l.trim());
    let html = '';
    let sections = [];
    let currentSection = { heading: null, type: 'other', content: [] };
    let conclusionSection = null;

    function flushSection() {
        if (currentSection.content.length || currentSection.heading) {
            const isConclusion = isConclusionSection(currentSection.heading || '');
            if (isConclusion) {
                conclusionSection = { ...currentSection };
            } else {
                sections.push({ ...currentSection });
            }
        }
        currentSection = { heading: null, type: 'other', content: [] };
    }

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (!line) {
            if (currentSection.content.length && currentSection.content[currentSection.content.length - 1] !== '') {
                currentSection.content.push('');
            }
            continue;
        }

        if (isSectionHeading(line)) {
            flushSection();
            currentSection.heading = line.replace(/^[#*_**]+|\*+$|:+$/g, '').trim();
            continue;
        }

        currentSection.content.push(line);
    }
    flushSection();

    // If we didn't detect sections, treat whole thing as one section
    if (sections.length === 0 && !conclusionSection && raw) {
        const fullText = lines.join(' ');
        conclusionSection = { heading: 'Conclusion', content: [raw], type: 'conclusion' };
    } else if (conclusionSection) {
        // Merge conclusion content
        conclusionSection.content = conclusionSection.content.filter(c => c);
    }

    // Render conclusion FIRST and highlighted
    if (conclusionSection && conclusionSection.content.length) {
        const conclusionText = conclusionSection.content.join(' ').trim() || conclusionSection.content.join('\n');
        const verdictType = getVerdictType(conclusionText);
        html += '<div class="conclusion-box conclusion-' + verdictType + '">';
        html += '<div class="conclusion-header"><i class="fas fa-gavel"></i> ' + escapeHtml(conclusionSection.heading || 'Conclusion') + '</div>';
        html += '<div class="conclusion-body">' + formatSectionContent(conclusionSection.content) + '</div>';
        html += '</div>';
    }

    // Render other sections with clear headings
    sections.forEach(sec => {
        html += '<div class="analysis-section">';
        html += '<h4 class="analysis-heading"><i class="fas fa-folder-open"></i> ' + escapeHtml(sec.heading || 'Details') + '</h4>';
        html += '<div class="analysis-section-content">' + formatSectionContent(sec.content) + '</div>';
        html += '</div>';
    });

    return html;
}

function formatSectionContent(lines) {
    let out = '';
    let inList = false;
    const filtered = lines.filter(l => l !== undefined && l !== null);

    filtered.forEach(line => {
        const trimmed = String(line).trim();
        if (!trimmed) {
            if (inList) { out += '</ul>'; inList = false; }
            return;
        }

        if (/^[-•*]\s+/.test(trimmed) || /^\d+\.\s+/.test(trimmed)) {
            if (!inList) { out += '<ul>'; inList = true; }
            const text = trimmed.replace(/^[-•*]\s+/, '').replace(/^\d+\.\s+/, '');
            out += '<li>' + escapeHtml(text) + '</li>';
        } else {
            if (inList) { out += '</ul>'; inList = false; }
            out += '<p>' + escapeHtml(trimmed) + '</p>';
        }
    });
    if (inList) out += '</ul>';
    return out;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

let requestInProgress = false;

document.getElementById('uploadForm').addEventListener('submit', function(event) {
    event.preventDefault();
    if (requestInProgress) return;

    const productImage = document.getElementById('productImage').files;
    const ageBracket = document.getElementById('ageBracket').value;
    const output = document.getElementById('output');
    const submitButton = document.getElementById('submitBtn');
    const fileInput = document.getElementById('productImage');
    const ageSelect = document.getElementById('ageBracket');

    if (productImage.length === 0) {
        output.innerHTML = alertHTML('error', '<strong><i class="fas fa-exclamation-circle"></i> Please upload at least one image.</strong>');
        output.scrollIntoView({ behavior: 'smooth' });
        return;
    }

    const rateLimitCheck = canMakeRequest();
    const lastRequestTime = localStorage.getItem('last_request_time');

    if (lastRequestTime) {
        const timeSinceLast = (Date.now() - parseInt(lastRequestTime)) / 1000;
        if (timeSinceLast < MIN_DELAY_BETWEEN_REQUESTS) {
            const waitTime = Math.ceil(MIN_DELAY_BETWEEN_REQUESTS - timeSinceLast);
            output.innerHTML = alertHTML('warning',
                '<h4><i class="fas fa-clock"></i> Please Wait</h4>' +
                '<p>There is a <strong>' + MIN_DELAY_BETWEEN_REQUESTS + ' second</strong> minimum delay between requests.</p>' +
                '<p>Wait <strong id="min-delay-countdown">' + waitTime + '</strong> more seconds.</p>'
            );
            let remaining = waitTime;
            const interval = setInterval(() => {
                remaining--;
                const el = document.getElementById('min-delay-countdown');
                if (el) el.textContent = remaining;
                if (remaining <= 0) clearInterval(interval);
            }, 1000);
            return;
        }
    }

    if (!rateLimitCheck.allowed) {
        output.innerHTML = alertHTML('warning',
            '<h4><i class="fas fa-exclamation-triangle"></i> Too Many Requests</h4>' +
            '<p>You\'ve made <strong>' + MAX_REQUESTS_PER_MINUTE + '</strong> requests. Wait <strong id="client-countdown">' + rateLimitCheck.waitTime + '</strong> seconds.</p>'
        );
        let remaining = rateLimitCheck.waitTime;
        const interval = setInterval(() => {
            remaining--;
            const el = document.getElementById('client-countdown');
            if (el) el.textContent = remaining;
            if (remaining <= 0) {
                clearInterval(interval);
                const box = document.querySelector('#output .alert-box');
                if (box) box.innerHTML = '<p><i class="fas fa-check-circle"></i> Ready to analyze again!</p>';
            }
        }, 1000);
        return;
    }

    recordRequest();
    localStorage.setItem('last_request_time', Date.now().toString());

    submitButton.disabled = true;
    submitButton.innerHTML = '<div class="spinner" style="width:20px;height:20px;border-width:2px;"></div> <span>Analyzing...</span>';
    fileInput.disabled = true;
    ageSelect.disabled = true;

    let messageIndex = 0;
    const progressMessages = ['Extracting text...', 'Processing ingredients...', 'Analyzing with AI...', 'Generating recommendations...'];

    output.innerHTML = '<div class="result-card loading-state">' +
        '<div class="spinner"></div>' +
        '<p id="progress-message">Processing your image... This may take 30–90 seconds.</p>' +
        '<div style="margin-top:16px;height:4px;background:#e8f5e9;border-radius:2px;max-width:300px;margin-left:auto;margin-right:auto;">' +
        '<div id="progress-bar" style="width:0%;height:100%;background:#66bb6a;border-radius:2px;transition:width 0.3s;"></div></div></div>';

    const progressInterval = setInterval(() => {
        messageIndex = (messageIndex + 1) % progressMessages.length;
        const msg = document.getElementById('progress-message');
        if (msg) msg.textContent = progressMessages[messageIndex];
        const bar = document.getElementById('progress-bar');
        if (bar) {
            const w = parseInt(bar.style.width) || 0;
            if (w < 90) bar.style.width = Math.min(w + 10, 90) + '%';
        }
    }, 15000);

    const formData = new FormData();
    for (const file of productImage) formData.append('productImage', file);
    formData.append('ageBracket', ageBracket);

    // Include user profile data
    const loggedInUser = JSON.parse(localStorage.getItem('loggedInUser') || '{}');
    const profile = JSON.parse(localStorage.getItem('toddlerbites_profile') || '{}');
    
    formData.append('userName', loggedInUser.name || '');
    formData.append('userEmail', loggedInUser.email || '');
    formData.append('dietPreference', profile.dietPreference || 'none');
    formData.append('allergies', profile.allergies || '');

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000);

    fetch('/upload', { method: 'POST', body: formData, signal: controller.signal })
        .then(async res => {
            let data;
            try { data = await res.json(); } catch (e) { throw new Error('Server error: ' + (await res.text()) || 'Unknown'); }
            if (!res.ok) throw new Error(data.error || data.message || 'Request failed');
            return data;
        })
        .then(data => {
            clearTimeout(timeoutId);
            clearInterval(progressInterval);
            requestInProgress = false;
            submitButton.disabled = false;
            submitButton.innerHTML = '<i class="fas fa-search"></i> <span>Analyze Ingredients</span>';
            fileInput.disabled = false;
            ageSelect.disabled = false;
            updateRateLimitDisplay();

            if (data.error) {
                if (data.error.includes('Rate Limit') || data.error.includes('quota') || data.error.includes('429')) {
                    const m = data.error.match(/(\d+)\s*seconds?/i);
                    const waitTime = m ? parseInt(m[1]) : 60;
                    output.innerHTML = alertHTML('warning',
                        '<h4><i class="fas fa-exclamation-triangle"></i> Rate Limit Exceeded</h4>' +
                        '<p>Wait <strong id="countdown-timer">' + waitTime + '</strong> seconds before retrying.</p>'
                    );
                    let r = waitTime;
                    const iv = setInterval(() => {
                        r--;
                        const el = document.getElementById('countdown-timer');
                        if (el) el.textContent = r;
                        if (r <= 0) clearInterval(iv);
                    }, 1000);
                } else {
                    output.innerHTML = alertHTML('error', '<strong>Error:</strong> ' + data.error);
                }
                return;
            }

            // Structured result
            const ingredientsHtml = (data.ingredients || [])
                .filter(i => i.trim())
                .map(i => '<span class="ingredient-tag">' + escapeHtml(i.trim()) + '</span>')
                .join('');

            output.innerHTML = '<div class="result-card">' +
                '<div class="result-section">' +
                '<h3><i class="fas fa-check-circle"></i> Analysis Complete</h3>' +
                '<p class="card-desc" style="margin-bottom:16px;">Analysis for age bracket: <strong>' + escapeHtml(data.age_bracket) + ' years</strong></p>' +
                '</div>' +
                (ingredientsHtml ? '<div class="result-section">' +
                    '<h3><i class="fas fa-list"></i> Extracted Ingredients</h3>' +
                    '<div class="ingredients-grid">' + ingredientsHtml + '</div></div>' : '') +
                '<div class="result-section">' +
                '<h3><i class="fas fa-clipboard-list"></i> AI Analysis</h3>' +
                '<div class="analysis-content">' + formatStructuredAnalysis(data.analysis) + '</div>' +
                '</div></div>';
            output.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            if (typeof window.addRecentSearch === 'function') {
                window.addRecentSearch(data);
            }
        })
        .catch(error => {
            clearTimeout(timeoutId);
            clearInterval(progressInterval);
            requestInProgress = false;
            submitButton.disabled = false;
            submitButton.innerHTML = '<i class="fas fa-search"></i> <span>Analyze Ingredients</span>';
            fileInput.disabled = false;
            ageSelect.disabled = false;
            updateRateLimitDisplay();

            let msg = 'Failed to process your request.';
            let details = error.message || '';

            if (error.message && (error.message.includes('Rate Limit') || error.message.includes('quota') || error.message.includes('429'))) {
                const m = error.message.match(/(\d+)\s*seconds?/i);
                const waitTime = m ? parseInt(m[1]) : 60;
                output.innerHTML = alertHTML('warning',
                    '<h4><i class="fas fa-exclamation-triangle"></i> Rate Limit</h4>' +
                    '<p>Wait <strong id="countdown-timer-error">' + waitTime + '</strong> seconds.</p>'
                );
                let r = waitTime;
                const iv = setInterval(() => {
                    r--;
                    const el = document.getElementById('countdown-timer-error');
                    if (el) el.textContent = r;
                    if (r <= 0) clearInterval(iv);
                }, 1000);
                return;
            }
            if (error.name === 'AbortError' || /timeout|aborted/i.test(error.message)) {
                msg = 'Request timed out.';
                details = 'The AI analysis took too long. Please try again.';
            } else if (error.name === 'TypeError' && error.message.includes('fetch')) {
                msg = 'Network error.';
                details = 'Check your connection and ensure the server is running.';
            }

            output.innerHTML = alertHTML('error', '<strong>' + msg + '</strong><p style="margin-top:10px;">' + details + '</p>');
        });
});
