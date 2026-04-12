// AlphaBreak Onboarding — tooltip walkthrough + checklist banner

const Onboarding = (() => {
    const STORAGE_KEY = 'onboardingComplete';
    const CHECKLIST_KEY = 'onboardingChecklist';

    // ── Stage 1: Tooltip walkthrough steps ──────────────────────────────────
    const steps = [
        {
            target: '#analyzeSearchInput',
            title: 'Search any ticker',
            text: 'Type a stock symbol (like AAPL or TSLA) to get a full AI-powered analysis — price, fundamentals, technicals, and more.',
            position: 'bottom',
            tab: 'watchlist',
        },
        {
            target: '#analyzeStatsGrid',
            title: 'Your analysis at a glance',
            text: '22 key metrics — P/E, EPS, market cap, margins, ROE — all in one view. No more switching between tabs or tools.',
            position: 'bottom',
            tab: 'watchlist',
            fallback: '.analyze-stats-grid',
        },
        {
            target: '#aiBriefSection',
            title: 'AI does the heavy lifting',
            text: 'The AI Brief synthesizes price action, trend breaks, technicals, analyst consensus, earnings, and institutional ownership into plain English.',
            position: 'top',
            tab: 'watchlist',
            fallback: '.ai-brief-card',
        },
        {
            target: '[data-tab="aidashboard"]',
            title: 'AI Dashboard',
            text: 'See market-wide AI signals, regime classification, sector analysis, and run the AI screener on any ticker.',
            position: 'right',
        },
        {
            target: '[data-tab="portfolio"]',
            title: 'Track your trades',
            text: 'Paper trade with $100K. Track positions, P&L, and get performance analytics including Sharpe ratio and drawdown.',
            position: 'right',
        },
        {
            target: '[data-tab="pricing"]',
            title: 'Unlock Pro features',
            text: 'Auto-detected trendlines, seasonality heatmaps, short interest, dividend analysis, and more — upgrade when you\'re ready.',
            position: 'right',
        },
    ];

    let currentStep = 0;
    let overlay = null;
    let tooltip = null;
    let spotlight = null;

    function isComplete() {
        return localStorage.getItem(STORAGE_KEY) === 'true';
    }

    function markComplete() {
        localStorage.setItem(STORAGE_KEY, 'true');
    }

    // ── Build DOM elements ──────────────────────────────────────────────────
    function createElements() {
        // Overlay
        overlay = document.createElement('div');
        overlay.className = 'onboarding-overlay';
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) next();
        });

        // Spotlight cutout
        spotlight = document.createElement('div');
        spotlight.className = 'onboarding-spotlight';

        // Tooltip
        tooltip = document.createElement('div');
        tooltip.className = 'onboarding-tooltip';
        tooltip.innerHTML = `
            <div class="onboarding-tooltip-header">
                <span class="onboarding-step-count"></span>
                <button class="onboarding-skip">Skip tour</button>
            </div>
            <h3 class="onboarding-tooltip-title"></h3>
            <p class="onboarding-tooltip-text"></p>
            <div class="onboarding-tooltip-actions">
                <button class="btn btn-ghost btn-sm onboarding-prev">Back</button>
                <button class="btn btn-primary btn-sm onboarding-next">Next</button>
            </div>
        `;

        tooltip.querySelector('.onboarding-skip').addEventListener('click', finish);
        tooltip.querySelector('.onboarding-prev').addEventListener('click', prev);
        tooltip.querySelector('.onboarding-next').addEventListener('click', next);

        document.body.appendChild(overlay);
        document.body.appendChild(spotlight);
        document.body.appendChild(tooltip);
    }

    function removeElements() {
        if (overlay) overlay.remove();
        if (tooltip) tooltip.remove();
        if (spotlight) spotlight.remove();
        overlay = tooltip = spotlight = null;
    }

    // ── Navigation ──────────────────────────────────────────────────────────
    function showStep(index) {
        const step = steps[index];
        if (!step) { finish(); return; }

        // Switch tab if needed
        if (step.tab && typeof state !== 'undefined' && state.activeTab !== step.tab) {
            const link = document.querySelector(`[data-tab="${step.tab}"]`);
            if (link) link.click();
        }

        // Find target element
        let target = document.querySelector(step.target);
        if (!target && step.fallback) target = document.querySelector(step.fallback);

        // Update tooltip content
        tooltip.querySelector('.onboarding-step-count').textContent = `${index + 1} of ${steps.length}`;
        tooltip.querySelector('.onboarding-tooltip-title').textContent = step.title;
        tooltip.querySelector('.onboarding-tooltip-text').textContent = step.text;

        const prevBtn = tooltip.querySelector('.onboarding-prev');
        const nextBtn = tooltip.querySelector('.onboarding-next');
        prevBtn.style.display = index === 0 ? 'none' : '';
        nextBtn.textContent = index === steps.length - 1 ? 'Get Started' : 'Next';

        // Position tooltip and spotlight
        if (target) {
            positionTooltip(target, step.position);
        } else {
            // Target not found — center tooltip
            spotlight.style.display = 'none';
            tooltip.style.top = '50%';
            tooltip.style.left = '50%';
            tooltip.style.transform = 'translate(-50%, -50%)';
            tooltip.removeAttribute('data-position');
        }

        overlay.classList.add('active');
        tooltip.classList.add('active');
    }

    function positionTooltip(target, position) {
        const rect = target.getBoundingClientRect();
        const pad = 8;

        // Spotlight around target
        spotlight.style.display = 'block';
        spotlight.style.top = `${rect.top - 4}px`;
        spotlight.style.left = `${rect.left - 4}px`;
        spotlight.style.width = `${rect.width + 8}px`;
        spotlight.style.height = `${rect.height + 8}px`;

        // Reset transform
        tooltip.style.transform = '';
        tooltip.removeAttribute('data-position');
        tooltip.setAttribute('data-position', position);

        // Position tooltip relative to target
        switch (position) {
            case 'bottom':
                tooltip.style.top = `${rect.bottom + pad + 8}px`;
                tooltip.style.left = `${rect.left + rect.width / 2}px`;
                tooltip.style.transform = 'translateX(-50%)';
                break;
            case 'top':
                tooltip.style.top = `${rect.top - pad - 8}px`;
                tooltip.style.left = `${rect.left + rect.width / 2}px`;
                tooltip.style.transform = 'translate(-50%, -100%)';
                break;
            case 'right':
                tooltip.style.top = `${rect.top + rect.height / 2}px`;
                tooltip.style.left = `${rect.right + pad + 8}px`;
                tooltip.style.transform = 'translateY(-50%)';
                break;
            case 'left':
                tooltip.style.top = `${rect.top + rect.height / 2}px`;
                tooltip.style.left = `${rect.left - pad - 8}px`;
                tooltip.style.transform = 'translate(-100%, -50%)';
                break;
        }

        // Clamp to viewport
        requestAnimationFrame(() => {
            const tr = tooltip.getBoundingClientRect();
            if (tr.right > window.innerWidth - 16) {
                tooltip.style.left = `${window.innerWidth - tr.width - 16}px`;
                tooltip.style.transform = 'translateY(-50%)';
            }
            if (tr.left < 16) {
                tooltip.style.left = '16px';
                tooltip.style.transform = position === 'top' ? 'translateY(-100%)' : '';
            }
            if (tr.bottom > window.innerHeight - 16) {
                tooltip.style.top = `${window.innerHeight - tr.height - 16}px`;
            }
        });

        // Scroll target into view
        target.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    function next() {
        currentStep++;
        if (currentStep >= steps.length) {
            finish();
        } else {
            showStep(currentStep);
        }
    }

    function prev() {
        if (currentStep > 0) {
            currentStep--;
            showStep(currentStep);
        }
    }

    function finish() {
        markComplete();
        removeElements();
        initChecklist(); // transition to Stage 2
    }

    // ── Start tour ──────────────────────────────────────────────────────────
    function startTour() {
        currentStep = 0;
        createElements();
        showStep(0);
    }

    // ═══════════════════════════════════════════════════════════════════════
    // Stage 2: Checklist Banner
    // ═══════════════════════════════════════════════════════════════════════

    const checklistItems = [
        { id: 'search_ticker', label: 'Search your first ticker', event: 'onboarding:searched' },
        { id: 'add_watchlist', label: 'Add a ticker to your watchlist', event: 'onboarding:watchlisted' },
        { id: 'create_journal', label: 'Create a journal entry', event: 'onboarding:journaled' },
        { id: 'visit_dashboard', label: 'Check the AI Dashboard', event: 'onboarding:dashboard' },
        { id: 'visit_portfolio', label: 'Explore your portfolio', event: 'onboarding:portfolio' },
    ];

    function getChecklistState() {
        try {
            return JSON.parse(localStorage.getItem(CHECKLIST_KEY)) || {};
        } catch { return {}; }
    }

    function saveChecklistState(state) {
        localStorage.setItem(CHECKLIST_KEY, JSON.stringify(state));
    }

    function checkItem(id) {
        const s = getChecklistState();
        if (s[id]) return; // already checked
        s[id] = true;
        saveChecklistState(s);
        renderChecklist();
    }

    function allChecklistDone() {
        const s = getChecklistState();
        return checklistItems.every(item => s[item.id]);
    }

    function renderChecklist() {
        let banner = document.getElementById('onboardingChecklist');
        if (!banner) return;

        const s = getChecklistState();
        const done = checklistItems.filter(i => s[i.id]).length;

        if (allChecklistDone() || localStorage.getItem('onboardingChecklistDismissed') === 'true') {
            banner.style.display = 'none';
            return;
        }

        banner.style.display = '';
        const progress = (done / checklistItems.length) * 100;

        banner.innerHTML = `
            <div class="checklist-header">
                <span class="checklist-title">Getting Started</span>
                <span class="checklist-progress-text">${done}/${checklistItems.length} complete</span>
                <button class="checklist-dismiss" title="Dismiss">&times;</button>
            </div>
            <div class="checklist-progress-bar">
                <div class="checklist-progress-fill" style="width: ${progress}%"></div>
            </div>
            <div class="checklist-items">
                ${checklistItems.map(item => `
                    <label class="checklist-item ${s[item.id] ? 'checked' : ''}">
                        <span class="checklist-check">${s[item.id] ? '&#10003;' : ''}</span>
                        <span class="checklist-label">${item.label}</span>
                    </label>
                `).join('')}
            </div>
        `;

        banner.querySelector('.checklist-dismiss').addEventListener('click', () => {
            localStorage.setItem('onboardingChecklistDismissed', 'true');
            banner.style.display = 'none';
        });
    }

    function initChecklist() {
        if (!isComplete()) return; // tour not done yet
        if (allChecklistDone() || localStorage.getItem('onboardingChecklistDismissed') === 'true') return;

        // Create banner if it doesn't exist
        let banner = document.getElementById('onboardingChecklist');
        if (!banner) {
            banner = document.createElement('div');
            banner.id = 'onboardingChecklist';
            banner.className = 'onboarding-checklist';
            const main = document.querySelector('.main-content');
            if (main) main.prepend(banner);
        }

        renderChecklist();

        // Listen for custom events
        checklistItems.forEach(item => {
            document.addEventListener(item.event, () => checkItem(item.id));
        });

        // Auto-detect tab visits
        const origSetTab = () => {
            if (typeof state !== 'undefined') {
                if (state.activeTab === 'aidashboard') checkItem('visit_dashboard');
                if (state.activeTab === 'portfolio') checkItem('visit_portfolio');
            }
        };

        // Poll tab changes (lightweight — checks every 2s)
        setInterval(origSetTab, 2000);
    }

    // ═══════════════════════════════════════════════════════════════════════
    // Stage 3: Empty state prompts
    // ═══════════════════════════════════════════════════════════════════════

    function initEmptyStates() {
        // Inject helpful prompts into known empty containers
        injectEmptyState('journalEntryList', 'No journal entries yet', 'Log your first trade and get an AI-scored review of your entry, exit, and timing.');
        injectEmptyState('watchlistResults', 'Your watchlist is empty', 'Search for a ticker above and click the star to add it to your watchlist.');
        injectEmptyState('portfolioHoldings', 'No positions yet', 'Start paper trading with $100K — test strategies risk-free.');
    }

    function injectEmptyState(containerId, title, subtitle) {
        const container = document.getElementById(containerId);
        if (!container) return;

        // Watch for empty state
        const observer = new MutationObserver(() => {
            const existing = container.querySelector('.onboarding-empty-state');
            const hasContent = container.children.length > (existing ? 1 : 0);
            if (!hasContent && !existing) {
                const el = document.createElement('div');
                el.className = 'onboarding-empty-state';
                el.innerHTML = `<p class="empty-state-title">${title}</p><p class="empty-state-sub">${subtitle}</p>`;
                container.appendChild(el);
            } else if (hasContent && existing) {
                existing.remove();
            }
        });
        observer.observe(container, { childList: true });
    }

    // ── Public API ──────────────────────────────────────────────────────────
    function init() {
        // Only run for authenticated users
        if (typeof Auth === 'undefined' || !Auth.isAuthenticated) return;

        if (!isComplete()) {
            // First time — start the tour
            startTour();
        } else {
            // Tour done — show checklist if not dismissed
            initChecklist();
        }

        initEmptyStates();
    }

    // Fire checklist events from other modules
    function trackSearch() { document.dispatchEvent(new Event('onboarding:searched')); }
    function trackWatchlist() { document.dispatchEvent(new Event('onboarding:watchlisted')); }
    function trackJournal() { document.dispatchEvent(new Event('onboarding:journaled')); }

    return {
        init,
        startTour,
        trackSearch,
        trackWatchlist,
        trackJournal,
        checkItem,
    };
})();

window.Onboarding = Onboarding;
