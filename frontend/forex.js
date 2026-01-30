// ============================================================================
// Forex Tab — Currency Correlation Analysis
// ============================================================================
// Displays forex pairs, correlations, and trend breaks.

const Forex = {
    charts: {},
    selectedPair: null,

    // ──────────────────────────────────────────────────────────
    // INITIALIZATION
    // ──────────────────────────────────────────────────────────

    init() {
        this.loadSummary();
        this.loadPairs();
        this.loadCorrelations();
        this.loadTrendBreaks();
        this.setupFilters();
    },

    setupFilters() {
        const strengthFilter = document.getElementById('forexStrengthFilter');
        if (strengthFilter) {
            strengthFilter.addEventListener('change', () => {
                this.loadCorrelations(strengthFilter.value);
            });
        }

        const pairFilter = document.getElementById('forexPairFilter');
        if (pairFilter) {
            pairFilter.addEventListener('change', () => {
                this.loadTrendBreaks(pairFilter.value);
            });
        }
    },

    // ──────────────────────────────────────────────────────────
    // SUMMARY
    // ──────────────────────────────────────────────────────────

    async loadSummary() {
        const container = document.getElementById('forexSummaryStats');
        if (!container) return;

        try {
            const response = await apiRequest('/api/forex/summary', 'GET');
            if (!response.ok) throw new Error('Failed to load forex summary');

            const data = await response.json();
            this.renderSummary(data);
        } catch (error) {
            container.innerHTML = `<p class="error">Failed to load summary: ${error.message}</p>`;
        }
    },

    renderSummary(data) {
        const container = document.getElementById('forexSummaryStats');
        if (!container) return;

        container.innerHTML = `
            <div class="forex-stat-card">
                <div class="forex-stat-value">${data.pairs_count || 0}</div>
                <div class="forex-stat-label">Currency Pairs</div>
            </div>
            <div class="forex-stat-card">
                <div class="forex-stat-value">${this.formatNumber(data.data_points || 0)}</div>
                <div class="forex-stat-label">Data Points</div>
            </div>
            <div class="forex-stat-card">
                <div class="forex-stat-value">${data.total_trend_breaks || 0}</div>
                <div class="forex-stat-label">Notable Movements</div>
            </div>
            <div class="forex-stat-card">
                <div class="forex-stat-value">${data.recent_breaks_7d || 0}</div>
                <div class="forex-stat-label">Recent (7d)</div>
            </div>
        `;

        // Pattern counts
        const patternContainer = document.getElementById('forexPatternCounts');
        if (patternContainer && data.pattern_counts) {
            const pc = data.pattern_counts;
            patternContainer.innerHTML = `
                <div class="pattern-bar">
                    <div class="pattern-segment strong" style="flex: ${pc.strong || 0};" title="Strong: ${pc.strong || 0}">
                        <span class="pattern-count">${pc.strong || 0}</span>
                    </div>
                    <div class="pattern-segment mid" style="flex: ${pc.mid || 0};" title="Mid: ${pc.mid || 0}">
                        <span class="pattern-count">${pc.mid || 0}</span>
                    </div>
                    <div class="pattern-segment weak" style="flex: ${pc.weak || 0};" title="Weak: ${pc.weak || 0}">
                        <span class="pattern-count">${pc.weak || 0}</span>
                    </div>
                </div>
                <div class="pattern-legend">
                    <span class="legend-item"><span class="legend-color strong"></span> Strong</span>
                    <span class="legend-item"><span class="legend-color mid"></span> Mid</span>
                    <span class="legend-item"><span class="legend-color weak"></span> Weak</span>
                </div>
            `;
        }
    },

    // ──────────────────────────────────────────────────────────
    // PAIRS LIST
    // ──────────────────────────────────────────────────────────

    async loadPairs() {
        const tbody = document.getElementById('forexPairsBody');
        const pairFilter = document.getElementById('forexPairFilter');
        if (!tbody) return;

        try {
            const response = await apiRequest('/api/forex/pairs', 'GET');
            if (!response.ok) throw new Error('Failed to load forex pairs');

            const data = await response.json();
            this.renderPairs(data.pairs || []);

            // Populate pair filter
            if (pairFilter && data.pairs) {
                pairFilter.innerHTML = '<option value="">All Pairs</option>' +
                    data.pairs.map(p => `<option value="${p.pair}">${p.pair}</option>`).join('');
            }
        } catch (error) {
            tbody.innerHTML = `<tr><td colspan="6" class="error">Failed to load pairs: ${error.message}</td></tr>`;
        }
    },

    renderPairs(pairs) {
        const tbody = document.getElementById('forexPairsBody');
        if (!tbody) return;

        if (pairs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="forex-empty">No forex pairs found. Run the data population script first.</td></tr>';
            return;
        }

        tbody.innerHTML = pairs.map(pair => {
            const yearsOfData = pair.data_start_date && pair.data_end_date
                ? ((new Date(pair.data_end_date) - new Date(pair.data_start_date)) / (365.25 * 24 * 60 * 60 * 1000)).toFixed(1)
                : '--';

            const modelStatus = pair.model_trained
                ? '<span class="status-badge trained">Trained</span>'
                : '<span class="status-badge pending">Pending</span>';

            return `
                <tr class="forex-pair-row" data-pair="${pair.pair}">
                    <td><strong>${pair.pair}</strong></td>
                    <td>${pair.base_currency} / ${pair.quote_currency}</td>
                    <td>${pair.data_start_date || '--'}</td>
                    <td>${this.formatNumber(pair.total_records || 0)}</td>
                    <td>${yearsOfData} years</td>
                    <td>${modelStatus}</td>
                </tr>
            `;
        }).join('');

        // Row click handler
        tbody.querySelectorAll('.forex-pair-row').forEach(row => {
            row.addEventListener('click', () => {
                const pair = row.dataset.pair;
                this.selectPair(pair);
            });
        });
    },

    async selectPair(pair) {
        this.selectedPair = pair;

        // Highlight selected row
        document.querySelectorAll('.forex-pair-row').forEach(row => {
            row.classList.toggle('selected', row.dataset.pair === pair);
        });

        // Load chart for selected pair
        await this.loadPairChart(pair);
    },

    // ──────────────────────────────────────────────────────────
    // CORRELATIONS
    // ──────────────────────────────────────────────────────────

    async loadCorrelations(strength = '') {
        const tbody = document.getElementById('forexCorrelationsBody');
        if (!tbody) return;

        try {
            let url = '/api/forex/correlations';
            if (strength) url += `?strength=${strength}`;

            const response = await apiRequest(url, 'GET');
            if (!response.ok) throw new Error('Failed to load correlations');

            const data = await response.json();
            this.renderCorrelations(data.correlations || [], data.thresholds);
        } catch (error) {
            tbody.innerHTML = `<tr><td colspan="6" class="error">Failed to load correlations: ${error.message}</td></tr>`;
        }
    },

    renderCorrelations(correlations, thresholds) {
        const tbody = document.getElementById('forexCorrelationsBody');
        if (!tbody) return;

        if (correlations.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="forex-empty">No correlations found. Train the model first.</td></tr>';
            return;
        }

        tbody.innerHTML = correlations.slice(0, 50).map(corr => {
            const absCorr = Math.abs(corr.correlation_all || 0);
            const corrPct = (absCorr * 100).toFixed(1);
            const strengthClass = corr.pattern_strength || 'weak';
            const corrSign = (corr.correlation_all || 0) >= 0 ? '+' : '';

            const leadLag = corr.lead_lag_days
                ? (corr.lead_lag_days > 0 ? `${corr.pair_a} leads by ${corr.lead_lag_days}d` : `${corr.pair_b} leads by ${Math.abs(corr.lead_lag_days)}d`)
                : 'Contemporaneous';

            return `
                <tr class="corr-row ${strengthClass}">
                    <td><strong>${corr.pair_a}</strong></td>
                    <td><strong>${corr.pair_b}</strong></td>
                    <td class="corr-value">${corrSign}${corrPct}%</td>
                    <td><span class="strength-badge ${strengthClass}">${strengthClass.toUpperCase()}</span></td>
                    <td>${leadLag}</td>
                    <td>${this.formatNumber(corr.data_points || 0)}</td>
                </tr>
            `;
        }).join('');

        // Update thresholds display
        if (thresholds) {
            const threshContainer = document.getElementById('forexThresholds');
            if (threshContainer) {
                threshContainer.innerHTML = `
                    <span class="threshold-item">Strong: ≥${(thresholds.strong_min * 100).toFixed(1)}%</span>
                    <span class="threshold-item">Mid: ${(thresholds.mid_min * 100).toFixed(1)}%-${(thresholds.strong_min * 100).toFixed(1)}%</span>
                    <span class="threshold-item">Weak: <${(thresholds.mid_min * 100).toFixed(1)}%</span>
                `;
            }
        }
    },

    // ──────────────────────────────────────────────────────────
    // TREND BREAKS
    // ──────────────────────────────────────────────────────────

    async loadTrendBreaks(pair = '') {
        const tbody = document.getElementById('forexTrendBreaksBody');
        if (!tbody) return;

        try {
            let url = '/api/forex/trend-breaks?days=90&limit=50';
            if (pair) url += `&pair=${encodeURIComponent(pair)}`;

            const response = await apiRequest(url, 'GET');
            if (!response.ok) throw new Error('Failed to load trend breaks');

            const data = await response.json();
            this.renderTrendBreaks(data.trend_breaks || []);
        } catch (error) {
            tbody.innerHTML = `<tr><td colspan="7" class="error">Failed to load trend breaks: ${error.message}</td></tr>`;
        }
    },

    renderTrendBreaks(breaks) {
        const tbody = document.getElementById('forexTrendBreaksBody');
        if (!tbody) return;

        if (breaks.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="forex-empty">No trend breaks found.</td></tr>';
            return;
        }

        tbody.innerHTML = breaks.map(brk => {
            const dirClass = brk.break_direction === 'bullish' ? 'positive' : 'negative';
            const probPct = ((brk.break_probability || 0) * 100).toFixed(1);

            const indicators = brk.indicators || {};
            const rsiDisplay = indicators.rsi != null ? indicators.rsi.toFixed(1) : '--';
            const cciDisplay = indicators.cci != null ? indicators.cci.toFixed(0) : '--';

            const movePct = brk.movement_pct != null
                ? `${brk.movement_pct >= 0 ? '+' : ''}${brk.movement_pct.toFixed(2)}%`
                : '--';

            return `
                <tr class="break-row">
                    <td><strong>${brk.pair}</strong></td>
                    <td>${brk.break_date || '--'}</td>
                    <td class="${dirClass}">${(brk.break_direction || '--').toUpperCase()}</td>
                    <td><span class="prob-badge">${probPct}%</span></td>
                    <td>${brk.price_at_break?.toFixed(5) || '--'}</td>
                    <td class="${brk.movement_pct >= 0 ? 'positive' : 'negative'}">${movePct}</td>
                    <td>RSI ${rsiDisplay} / CCI ${cciDisplay}</td>
                </tr>
            `;
        }).join('');
    },

    // ──────────────────────────────────────────────────────────
    // CHART
    // ──────────────────────────────────────────────────────────

    async loadPairChart(pair) {
        const canvas = document.getElementById('forexPairChart');
        const container = document.getElementById('forexChartContainer');
        if (!canvas || !container) return;

        container.style.display = 'block';

        try {
            const response = await apiRequest(`/api/forex/data/${encodeURIComponent(pair)}?days=365`, 'GET');
            if (!response.ok) throw new Error('Failed to load chart data');

            const data = await response.json();
            this.renderChart(pair, data.data || []);
        } catch (error) {
            console.error('Chart load failed:', error);
        }
    },

    renderChart(pair, data) {
        const canvas = document.getElementById('forexPairChart');
        if (!canvas || data.length === 0) return;

        // Destroy existing chart
        if (this.charts.forexChart) {
            this.charts.forexChart.destroy();
        }

        const ctx = canvas.getContext('2d');

        const chartData = data.reverse().map(d => ({
            x: new Date(d.date),
            y: d.close,
        }));

        this.charts.forexChart = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [{
                    label: pair,
                    data: chartData,
                    borderColor: '#4fc3f7',
                    backgroundColor: 'rgba(79, 195, 247, 0.1)',
                    fill: true,
                    tension: 0.1,
                    pointRadius: 0,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: true, labels: { color: '#8b95a5' } },
                    tooltip: {
                        backgroundColor: '#1c2030',
                        titleColor: '#e2e8f0',
                        bodyColor: '#8b95a5',
                    },
                },
                scales: {
                    x: {
                        type: 'time',
                        time: { unit: 'month' },
                        grid: { color: '#2a2e3960' },
                        ticks: { color: '#8b95a5' },
                    },
                    y: {
                        position: 'right',
                        grid: { color: '#2a2e3960' },
                        ticks: { color: '#8b95a5' },
                    },
                },
            },
        });

        // Update chart title
        const titleEl = document.getElementById('forexChartTitle');
        if (titleEl) titleEl.textContent = `${pair} - 1 Year`;
    },

    // ──────────────────────────────────────────────────────────
    // HELPERS
    // ──────────────────────────────────────────────────────────

    formatNumber(num) {
        if (num >= 1e6) return (num / 1e6).toFixed(1) + 'M';
        if (num >= 1e3) return (num / 1e3).toFixed(1) + 'K';
        return String(num);
    },
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('forexTab')) {
        // Wait for apiRequest to be available
        const checkReady = setInterval(() => {
            if (typeof apiRequest !== 'undefined') {
                clearInterval(checkReady);
                Forex.init();
            }
        }, 100);
        setTimeout(() => clearInterval(checkReady), 5000);
    }
});

window.Forex = Forex;
