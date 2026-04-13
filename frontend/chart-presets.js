// ============================================================================
// AlphaBreak Chart Presets + Saved Layouts
// ============================================================================
// Two cooperating modules:
//
//   ChartPresets   — one-click curated indicator stacks. The four presets are
//                    intentionally non-generic: each combines standard
//                    indicators with at least one AlphaBreak-proprietary
//                    signal (auto-trendlines, regime, dark-pool panel, etc.)
//                    so the bundle can't be replicated on TradingView/TOS.
//
//   ChartLayouts   — auto-saves the chart toolbar checkbox state per ticker
//                    to localStorage and restores it on the next visit. No
//                    explicit "save" action needed; the layout follows the
//                    user around.
//
// Both are wired against the existing toolbar checkbox IDs so they're
// completely independent of the underlying chart implementation.
// ============================================================================

const ChartPresets = (() => {

    // The exhaustive list of toggleable chart features. Adding a new toggle?
    // Add it here and the preset reset/save/restore logic picks it up
    // automatically.
    const ALL_TOGGLES = [
        'toggleTrendlines',
        'toggleSMA',
        'toggleBB',
        'toggleVWAP',
        'toggleCompare',
        'togglePatterns',
        'toggleRSI',
        'toggleMACD',
        'toggleStoch',
        'toggleATR',
        'toggleADX',
        'toggleOBV',
        'toggleSupertrend',
        'toggleKeltner',
        'toggleIchimoku',
        'toggleVPVR',
        'toggleSqueeze',
    ];

    // Each preset declares which toggles should end up CHECKED. Anything not
    // in the list is unchecked. Use the `notes` field for the tooltip the
    // dropdown shows on hover — keep it short, this is the user's elevator
    // pitch for why they'd pick this stack.
    const PRESETS = {
        trendBreak: {
            label: 'Trend Break Stack',
            tagline: 'Auto-trendlines + Supertrend + ADX + ATR',
            notes: 'AlphaBreak\'s auto-detected trendlines + trend-following confirmation. Best for breakout entries.',
            toggles: ['toggleTrendlines', 'toggleSupertrend', 'toggleADX', 'toggleATR'],
        },
        volumeFlow: {
            label: 'Volume Flow Stack',
            tagline: 'VPVR + OBV + VWAP',
            notes: 'Volume-by-price + on-balance volume + VWAP. Pairs with the dark pool panel below the chart.',
            toggles: ['toggleVPVR', 'toggleOBV', 'toggleVWAP'],
        },
        regimeAware: {
            label: 'Regime-Aware Stack',
            tagline: 'Trendlines (regime badge) + RSI + MACD + BB',
            notes: 'Lets the regime badge tell you which momentum signals to trust. Best for swing trading.',
            toggles: ['toggleTrendlines', 'toggleRSI', 'toggleMACD', 'toggleBB'],
        },
        aiConfluence: {
            label: 'AI Confluence Stack',
            tagline: 'Trendlines + Supertrend + Ichimoku + Squeeze Momentum',
            notes: 'Stacks the trendline AI score on top of three independent trend signals. High-conviction setups only.',
            toggles: ['toggleTrendlines', 'toggleSupertrend', 'toggleIchimoku', 'toggleSqueeze'],
        },
    };

    // Apply a preset by name. Resets every known toggle then enables only
    // the ones in the preset's list. Each toggled checkbox dispatches a
    // 'change' event so the existing analyze.js handlers fire and rerender
    // the chart — we don't poke at the chart instance directly.
    function apply(name) {
        const preset = PRESETS[name];
        if (!preset) return;

        for (const id of ALL_TOGGLES) {
            const el = document.getElementById(id);
            if (!el) continue;
            const shouldBeOn = preset.toggles.includes(id);
            if (el.checked !== shouldBeOn) {
                el.checked = shouldBeOn;
                el.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }
    }

    function list() {
        return Object.entries(PRESETS).map(([key, p]) => ({ key, ...p }));
    }

    // Render the preset dropdown into a host element. Returns the menu node
    // so the caller can position it. Closes on outside click.
    function attachDropdown(triggerBtn) {
        if (!triggerBtn) return null;

        let menu = null;
        const close = () => {
            menu?.remove();
            menu = null;
            document.removeEventListener('click', onOutside, true);
        };
        const onOutside = (e) => {
            if (!menu?.contains(e.target) && e.target !== triggerBtn && !triggerBtn.contains(e.target)) close();
        };

        triggerBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (menu) { close(); return; }

            menu = document.createElement('div');
            menu.className = 'chart-preset-menu';
            menu.innerHTML = list().map(p => `
                <button class="chart-preset-item" data-preset="${p.key}" title="${p.notes}">
                    <div class="chart-preset-item-label">${p.label}</div>
                    <div class="chart-preset-item-tagline">${p.tagline}</div>
                </button>
            `).join('');

            menu.addEventListener('click', (ev) => {
                const item = ev.target.closest('.chart-preset-item');
                if (!item) return;
                apply(item.dataset.preset);
                close();
            });

            // Position below the trigger button
            const rect = triggerBtn.getBoundingClientRect();
            menu.style.position = 'absolute';
            menu.style.top = (rect.bottom + window.scrollY + 4) + 'px';
            menu.style.left = (rect.left + window.scrollX) + 'px';
            menu.style.zIndex = '1000';

            document.body.appendChild(menu);
            // Defer outside-click binding so the click that opened the menu
            // doesn't immediately close it.
            setTimeout(() => document.addEventListener('click', onOutside, true), 0);
        });
    }

    return { apply, list, attachDropdown, PRESETS, ALL_TOGGLES };
})();

window.ChartPresets = ChartPresets;


// ============================================================================
// ChartLayouts — per-ticker auto-persisted toolbar state
// ============================================================================
// Strategy: snapshot every known toggle plus the active period/interval into
// localStorage under `chartLayout_<TICKER>`. Restore on ticker change. Save
// fires on every toggle change with a 200ms debounce so we don't thrash
// localStorage during preset application (which fires 17 events back-to-back).

const ChartLayouts = (() => {

    const STORAGE_PREFIX = 'chartLayout_';
    let currentTicker = null;
    let saveTimer = null;
    let initialized = false;

    function _snapshot() {
        const state = { toggles: {}, savedAt: Date.now() };
        for (const id of ChartPresets.ALL_TOGGLES) {
            const el = document.getElementById(id);
            if (el) state.toggles[id] = el.checked;
        }
        // Active period/interval — pulled from the .active button if present
        const periodBtn = document.querySelector('#analyzeChartPeriods button.active');
        if (periodBtn) {
            state.period = periodBtn.dataset.period;
            state.interval = periodBtn.dataset.interval;
        }
        return state;
    }

    function _save() {
        if (!currentTicker) return;
        try {
            localStorage.setItem(STORAGE_PREFIX + currentTicker, JSON.stringify(_snapshot()));
        } catch (e) { /* quota or disabled — silent */ }
    }

    function _scheduleSave() {
        if (saveTimer) clearTimeout(saveTimer);
        saveTimer = setTimeout(_save, 200);
    }

    function _load(ticker) {
        try {
            const raw = localStorage.getItem(STORAGE_PREFIX + ticker);
            return raw ? JSON.parse(raw) : null;
        } catch (e) { return null; }
    }

    // Restore the saved layout for `ticker`. Returns true if a layout was
    // applied so the caller can skip its default loadout.
    function restore(ticker) {
        const layout = _load(ticker);
        if (!layout?.toggles) return false;

        for (const [id, want] of Object.entries(layout.toggles)) {
            const el = document.getElementById(id);
            if (!el) continue;
            if (el.checked !== want) {
                el.checked = want;
                el.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }
        return true;
    }

    // Bind the auto-save listener once. Subsequent calls are no-ops.
    function init() {
        if (initialized) return;
        initialized = true;
        for (const id of ChartPresets.ALL_TOGGLES) {
            const el = document.getElementById(id);
            if (el) el.addEventListener('change', _scheduleSave);
        }
    }

    function setTicker(ticker) {
        currentTicker = ticker;
    }

    function clear(ticker) {
        try { localStorage.removeItem(STORAGE_PREFIX + (ticker || currentTicker)); } catch (e) {}
    }

    return { init, restore, setTicker, clear };
})();

window.ChartLayouts = ChartLayouts;
