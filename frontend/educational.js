// ============================================================================
// Educational Content — AI Briefs, Tooltips, Guide Panels
// Hooks into Reports, Earnings, and Options tabs
// ============================================================================

const Educational = {
    // ── Init: observe when tabs render data and inject content ────────────
    init() {
        this.observeReports();
        this.observeEarnings();
        this.observeOptions();
    },

    // ── REPORTS TAB ──────────────────────────────────────────────────────
    observeReports() {
        const tbody = document.getElementById('reportTableBody');
        if (!tbody) return;

        // Inject brief + guide containers once
        this.injectReportContainers();

        // Watch for table renders
        const observer = new MutationObserver(() => {
            if (Reports?.currentReport) {
                this.renderReportBrief(Reports.currentReport);
                this.addReportTooltips();
            }
        });
        observer.observe(tbody, { childList: true });
    },

    injectReportContainers() {
        const widget = document.getElementById('reportsWidgetBody');
        if (!widget || document.getElementById('reportAiBrief')) return;

        // AI Brief — insert at top of collapsible body
        const brief = document.createElement('div');
        brief.id = 'reportAiBrief';
        brief.className = 'card analyze-section analyze-ai-brief';
        brief.style.margin = '12px 16px';
        brief.innerHTML = `
            <div class="ai-brief-header">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
                    <path d="M12 2a4 4 0 014 4v1a4 4 0 01-8 0V6a4 4 0 014-4z"></path>
                    <path d="M6 10v2a6 6 0 0012 0v-2"></path>
                    <path d="M12 18v4M8 22h8"></path>
                </svg>
                <h3>AI Analysis</h3>
            </div>
            <div class="ai-brief-body" id="reportAiBriefBody"><p class="muted">Loading report analysis...</p></div>
        `;
        widget.insertBefore(brief, widget.firstChild);

        // Guide panel — insert after the report-header-row
        const headerRow = widget.querySelector('.report-header-row');
        if (headerRow) {
            const guide = document.createElement('div');
            guide.className = 'section-guide';
            guide.id = 'reportGuide';
            guide.style.margin = '0 16px 12px';
            guide.innerHTML = `<div class="guide-content">
                <p><strong>How to read this report:</strong></p>
                <ul>
                    <li><strong>Probability</strong> — The ML model's confidence that the current trend will break. Above 80% is the minimum shown; above 90% is high-conviction.</li>
                    <li><strong>Direction</strong> — <strong class="positive">Bullish</strong> means the model predicts an upward break; <strong class="negative">Bearish</strong> predicts a downward break.</li>
                    <li><strong>Indicators</strong> — RSI and CCI values that triggered the signal. RSI &lt; 30 = oversold (potential bounce); CCI &lt; -100 = extreme selling pressure.</li>
                    <li><strong>Options IV</strong> — Implied volatility. High IV means the market expects big moves. <span class="positive">Low IV</span> = cheap options (good for buyers). <span class="negative">High IV</span> = expensive options (good for sellers).</li>
                    <li><strong>ALERT badge</strong> — The stock has been flagged in multiple consecutive reports, increasing conviction.</li>
                    <li><strong>Frequency</strong> — Daily = swing trades (days-weeks). Hourly = day trades (hours). 10min = scalps (minutes).</li>
                </ul>
                <p class="guide-note">Click any row to expand a detailed chart with indicator breakdown. These signals feed into the automated portfolio manager.</p>
            </div>`;
            // Add guide toggle to report-header-right
            const headerRight = widget.querySelector('.report-header-right');
            if (headerRight) {
                const btn = document.createElement('button');
                btn.className = 'guide-toggle-btn';
                btn.dataset.guide = 'reportGuide';
                btn.textContent = '?';
                btn.addEventListener('click', () => {
                    guide.classList.toggle('hidden');
                    btn.classList.toggle('active');
                });
                headerRight.prepend(btn);
            }
            guide.classList.add('hidden');
            headerRow.after(guide);
        }
    },

    renderReportBrief(data) {
        const el = document.getElementById('reportAiBriefBody');
        if (!el) return;

        const secs = data.securities || [];
        const total = data.securities_count || secs.length;
        const alerts = data.alerts_count || 0;
        const freq = (data.frequency || 'daily').toLowerCase();

        if (total === 0) {
            el.innerHTML = '<p>No securities currently above the 80% trend break threshold. The market may be in a period of consolidation.</p>';
            return;
        }

        const bullish = secs.filter(s => s.break_direction === 'bullish').length;
        const bearish = secs.filter(s => s.break_direction === 'bearish').length;
        const topSec = secs[0];

        const sentences = [];
        sentences.push(`The ${freq} scan detected <strong>${total} securities</strong> with 80%+ trend break probability.`);

        if (bullish > 0 && bearish > 0) {
            sentences.push(`<strong class="positive">${bullish} bullish</strong> and <strong class="negative">${bearish} bearish</strong> signals.`);
        } else if (bullish > 0) {
            sentences.push(`All <strong class="positive">${bullish} signals are bullish</strong> — the market is showing broad upward momentum.`);
        } else {
            sentences.push(`All <strong class="negative">${bearish} signals are bearish</strong> — broad selling pressure detected.`);
        }

        if (alerts > 0) {
            sentences.push(`<strong>${alerts} active alert${alerts > 1 ? 's' : ''}</strong> — these tickers have been flagged in consecutive reports, indicating persistent trend pressure.`);
        }

        if (topSec) {
            const prob = (topSec.break_probability * 100).toFixed(0);
            const dir = topSec.break_direction || 'neutral';
            sentences.push(`Highest conviction: <strong>${topSec.ticker}</strong> at ${prob}% probability (${dir}).`);
        }

        // Sector concentration
        const sectorCounts = {};
        secs.forEach(s => { if (s.sector) sectorCounts[s.sector] = (sectorCounts[s.sector] || 0) + 1; });
        const topSector = Object.entries(sectorCounts).sort((a, b) => b[1] - a[1])[0];
        if (topSector && topSector[1] > 1) {
            sentences.push(`${topSector[0]} is the most active sector with ${topSector[1]} signals.`);
        }

        el.innerHTML = `<p>${sentences.join(' ')}</p>`;
    },

    addReportTooltips() {
        document.querySelectorAll('.prob-badge').forEach(badge => {
            const pct = parseFloat(badge.textContent);
            if (pct >= 95) badge.title = 'Very high conviction (95%+). The model is extremely confident in this trend break. Consider this a strong signal.';
            else if (pct >= 90) badge.title = 'High conviction (90-95%). Strong trend break signal with good indicator agreement.';
            else badge.title = 'Moderate conviction (80-90%). The trend break is likely but not certain. Look for confirming signals.';
        });
        document.querySelectorAll('.iv-indicator').forEach(el => {
            if (!el.title) {
                const val = el.querySelector('.iv-value')?.textContent;
                if (val && val !== '--') {
                    const iv = parseInt(val);
                    if (iv > 60) el.title = `IV at ${val} is elevated. Options are expensive — the market expects a big move. Better for selling premium.`;
                    else if (iv > 35) el.title = `IV at ${val} is moderate. Options are fairly priced relative to historical norms.`;
                    else el.title = `IV at ${val} is low. Options are cheap — good for buying calls/puts if you expect movement.`;
                }
            }
        });
    },

    // ── EARNINGS TAB ─────────────────────────────────────────────────────
    observeEarnings() {
        const tbody = document.getElementById('earningsTableBody');
        if (!tbody) return;

        this.injectEarningsContainers();

        const observer = new MutationObserver(() => {
            this.renderEarningsBrief();
            this.addEarningsTooltips();
        });
        observer.observe(tbody, { childList: true });
    },

    injectEarningsContainers() {
        const widget = document.getElementById('earningsWidgetBody');
        if (!widget || document.getElementById('earningsAiBrief')) return;

        // AI Brief
        const brief = document.createElement('div');
        brief.id = 'earningsAiBrief';
        brief.className = 'card analyze-section analyze-ai-brief';
        brief.style.margin = '12px 16px';
        brief.innerHTML = `
            <div class="ai-brief-header">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
                    <path d="M12 2a4 4 0 014 4v1a4 4 0 01-8 0V6a4 4 0 014-4z"></path>
                    <path d="M6 10v2a6 6 0 0012 0v-2"></path>
                    <path d="M12 18v4M8 22h8"></path>
                </svg>
                <h3>AI Analysis</h3>
                <button class="guide-toggle-btn" id="earningsGuideToggle">?</button>
            </div>
            <div class="ai-brief-body" id="earningsAiBriefBody"><p class="muted">Loading earnings analysis...</p></div>
        `;
        widget.insertBefore(brief, widget.firstChild);

        // Guide panel
        const guide = document.createElement('div');
        guide.className = 'section-guide hidden';
        guide.id = 'earningsTabGuide';
        guide.style.margin = '0 16px 12px';
        guide.innerHTML = `<div class="guide-content">
            <p><strong>How to read the earnings calendar:</strong></p>
            <ul>
                <li><strong>EPS Estimate</strong> — What Wall Street analysts expect the company to earn per share. This is the consensus average.</li>
                <li><strong>EPS Actual</strong> — What the company actually reported. Appears after the earnings release.</li>
                <li><strong>Surprise %</strong> — The difference between actual and estimated. <strong class="positive">Positive surprises</strong> (beats) typically drive the stock higher. <strong class="negative">Negative surprises</strong> (misses) often cause selloffs.</li>
                <li><strong>Status</strong> — "Upcoming" means not yet reported. "Reported" means results are in.</li>
                <li><strong>ES=F Futures bar</strong> — E-mini S&P 500 futures show pre-market and after-hours sentiment. If futures are red, the broader market is under pressure regardless of individual earnings.</li>
            </ul>
            <p class="guide-note">Companies that consistently beat estimates tend to outperform. Look for patterns — a stock that beats 4 quarters in a row has strong execution.</p>
        </div>`;
        brief.after(guide);

        document.getElementById('earningsGuideToggle')?.addEventListener('click', () => {
            guide.classList.toggle('hidden');
            document.getElementById('earningsGuideToggle')?.classList.toggle('active');
        });
    },

    renderEarningsBrief() {
        const el = document.getElementById('earningsAiBriefBody');
        if (!el) return;

        const rows = document.querySelectorAll('#earningsTableBody tr');
        if (!rows || rows.length === 0) {
            el.innerHTML = '<p>No earnings data loaded yet.</p>';
            return;
        }

        let upcoming = 0, reported = 0, beats = 0, misses = 0;
        const tickers = [];

        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            if (cells.length < 6) return;
            const status = cells[5]?.textContent?.trim().toLowerCase();
            const ticker = cells[1]?.textContent?.trim();
            const surprise = cells[4]?.textContent?.trim();

            if (status?.includes('upcoming')) {
                upcoming++;
                if (ticker) tickers.push(ticker);
            } else if (status?.includes('reported')) {
                reported++;
                if (surprise && !surprise.includes('--')) {
                    const val = parseFloat(surprise);
                    if (val > 0) beats++;
                    else if (val < 0) misses++;
                }
            }
        });

        const sentences = [];
        if (upcoming > 0) sentences.push(`<strong>${upcoming} companies</strong> have upcoming earnings reports.`);
        if (reported > 0) {
            sentences.push(`Of ${reported} reported, <strong class="positive">${beats} beat</strong> estimates and <strong class="negative">${misses} missed</strong>.`);
            if (beats > misses) sentences.push('The earnings season is trending positive — more companies are exceeding expectations.');
            else if (misses > beats) sentences.push('Earnings season is showing weakness — more misses than beats suggests headwinds.');
        }
        if (tickers.length > 0 && tickers.length <= 5) {
            sentences.push(`Watch for: ${tickers.map(t => `<strong>${t}</strong>`).join(', ')}.`);
        }

        const futuresPrice = document.getElementById('futuresChange')?.textContent?.trim();
        if (futuresPrice && futuresPrice !== '--') {
            const isNeg = futuresPrice.includes('-');
            sentences.push(`S&P 500 futures are ${isNeg ? '<strong class="negative">negative</strong> — markets facing pressure' : '<strong class="positive">positive</strong> — markets in a risk-on mood'}.`);
        }

        el.innerHTML = `<p>${sentences.length > 0 ? sentences.join(' ') : 'Earnings data loaded. Review the calendar below for upcoming and recent reports.'}</p>`;
    },

    addEarningsTooltips() {
        document.querySelectorAll('#earningsTableBody td:nth-child(3)').forEach(td => {
            if (!td.title) td.title = 'EPS Estimate: The average analyst forecast for earnings per share. Set by sell-side analysts covering this stock.';
        });
        document.querySelectorAll('#earningsTableBody td:nth-child(4)').forEach(td => {
            if (!td.title) td.title = 'EPS Actual: The reported earnings per share. Compare to estimate — a beat often drives the stock up in after-hours.';
        });
        document.querySelectorAll('#earningsTableBody td:nth-child(5)').forEach(td => {
            const text = td.textContent?.trim();
            if (text && text !== '--' && !td.title) {
                const val = parseFloat(text);
                if (val > 5) td.title = `Strong beat (+${val.toFixed(1)}%). Significantly exceeded expectations — watch for gap-up.`;
                else if (val > 0) td.title = `Beat (+${val.toFixed(1)}%). Exceeded expectations — generally positive for the stock.`;
                else if (val < -5) td.title = `Big miss (${val.toFixed(1)}%). Significantly below expectations — watch for gap-down.`;
                else if (val < 0) td.title = `Miss (${val.toFixed(1)}%). Below expectations — may pressure the stock.`;
            }
        });
    },

    // ── OPTIONS TAB ──────────────────────────────────────────────────────
    observeOptions() {
        const tbody = document.getElementById('optionsTableBody');
        if (!tbody) return;

        this.injectOptionsContainers();

        const observer = new MutationObserver(() => {
            this.renderOptionsBrief();
            this.addOptionsTooltips();
        });
        observer.observe(tbody, { childList: true });
    },

    injectOptionsContainers() {
        const widget = document.getElementById('optionsWidgetBody');
        if (!widget || document.getElementById('optionsAiBrief')) return;

        // AI Brief
        const brief = document.createElement('div');
        brief.id = 'optionsAiBrief';
        brief.className = 'card analyze-section analyze-ai-brief';
        brief.style.margin = '12px 16px';
        brief.innerHTML = `
            <div class="ai-brief-header">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
                    <path d="M12 2a4 4 0 014 4v1a4 4 0 01-8 0V6a4 4 0 014-4z"></path>
                    <path d="M6 10v2a6 6 0 0012 0v-2"></path>
                    <path d="M12 18v4M8 22h8"></path>
                </svg>
                <h3>AI Analysis</h3>
                <button class="guide-toggle-btn" id="optionsTabGuideToggle">?</button>
            </div>
            <div class="ai-brief-body" id="optionsAiBriefBody"><p class="muted">Run an options analysis to see the AI brief.</p></div>
        `;
        widget.insertBefore(brief, widget.firstChild);

        // Guide panel
        const guide = document.createElement('div');
        guide.className = 'section-guide hidden';
        guide.id = 'optionsTabGuide';
        guide.style.margin = '0 16px 12px';
        guide.innerHTML = `<div class="guide-content">
            <p><strong>How to read options analysis:</strong></p>
            <ul>
                <li><strong>Fair Value</strong> — Theoretical price calculated using Black-Scholes and Binomial Tree models. Compares to market price to find mispricing.</li>
                <li><strong class="positive">UNDERPRICED</strong> — Market price is below fair value. Potential buying opportunity if you agree with the direction.</li>
                <li><strong class="negative">OVERPRICED</strong> — Market price is above fair value. May be a candidate for selling premium or avoiding.</li>
                <li><strong>FAIR</strong> — Market price is close to theoretical value. No significant mispricing detected.</li>
                <li><strong>IV (Implied Volatility)</strong> — How much movement the market expects. Higher IV = more expensive options. Compare to historical IV to judge if options are cheap or expensive.</li>
                <li><strong>Delta</strong> — How much the option price moves per $1 move in the stock. Delta 0.50 = ATM. Delta 0.80 = deep ITM. Delta 0.20 = OTM.</li>
            </ul>
            <p class="guide-note">The recommended strategy at the top is based on trend direction and volatility conditions. Always consider your risk tolerance and position sizing.</p>
        </div>`;
        brief.after(guide);

        document.getElementById('optionsTabGuideToggle')?.addEventListener('click', () => {
            guide.classList.toggle('hidden');
            document.getElementById('optionsTabGuideToggle')?.classList.toggle('active');
        });
    },

    renderOptionsBrief() {
        const el = document.getElementById('optionsAiBriefBody');
        if (!el) return;

        const rows = document.querySelectorAll('#optionsTableBody tr');
        if (!rows || rows.length === 0) return;

        let calls = 0, puts = 0, underpriced = 0, overpriced = 0, fair = 0;
        let totalIV = 0, ivCount = 0;
        const underpricedTickers = [];

        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            if (cells.length < 8) return;
            const type = cells[0]?.textContent?.trim().toLowerCase();
            const rec = cells[7]?.textContent?.trim().toUpperCase();
            const iv = cells[5]?.textContent?.trim();

            if (type === 'call') calls++;
            else if (type === 'put') puts++;

            if (rec?.includes('UNDERPRICED')) { underpriced++; underpricedTickers.push(`${cells[0].textContent} $${cells[1].textContent}`); }
            else if (rec?.includes('OVERPRICED')) overpriced++;
            else fair++;

            if (iv && iv !== '--') {
                const ivVal = parseFloat(iv);
                if (!isNaN(ivVal)) { totalIV += ivVal; ivCount++; }
            }
        });

        const avgIV = ivCount > 0 ? (totalIV / ivCount).toFixed(1) : null;
        const total = calls + puts;

        const sentences = [];
        sentences.push(`Analyzed <strong>${total} options</strong> (${calls} calls, ${puts} puts).`);

        if (underpriced > 0) sentences.push(`<strong class="positive">${underpriced} underpriced</strong> (trading below fair value — potential buying opportunities).`);
        if (overpriced > 0) sentences.push(`<strong class="negative">${overpriced} overpriced</strong> (trading above fair value — consider selling premium or avoiding).`);
        if (fair > 0) sentences.push(`${fair} are fairly valued.`);

        if (avgIV) {
            const ivNum = parseFloat(avgIV);
            if (ivNum > 50) sentences.push(`Average IV is elevated at ${avgIV}% — options are expensive. Favor selling strategies (covered calls, credit spreads).`);
            else if (ivNum > 30) sentences.push(`Average IV is moderate at ${avgIV}%. Options are reasonably priced.`);
            else sentences.push(`Average IV is low at ${avgIV}% — options are cheap. Favor buying strategies (long calls/puts, debit spreads).`);
        }

        if (underpricedTickers.length > 0 && underpricedTickers.length <= 3) {
            sentences.push(`Best opportunities: ${underpricedTickers.map(t => `<strong>${t}</strong>`).join(', ')}.`);
        }

        // Strategy from the page
        const strategyName = document.getElementById('strategyName')?.textContent?.trim();
        if (strategyName) {
            sentences.push(`Recommended strategy: <strong>${strategyName}</strong>.`);
        }

        el.innerHTML = `<p>${sentences.join(' ')}</p>`;
    },

    addOptionsTooltips() {
        document.querySelectorAll('#optionsTableBody td:nth-child(5)').forEach(td => {
            if (!td.title) td.title = 'Fair Value: Theoretical price from Black-Scholes/Binomial models. Compare to Last Price to find mispricing.';
        });
        document.querySelectorAll('#optionsTableBody td:nth-child(6)').forEach(td => {
            const text = td.textContent?.trim();
            if (text && text !== '--' && !td.title) {
                const val = parseFloat(text);
                if (val > 0.5) td.title = `IV at ${(val * 100).toFixed(0)}% is high. The market expects significant movement. Options are expensive — better for selling premium.`;
                else if (val > 0.25) td.title = `IV at ${(val * 100).toFixed(0)}% is moderate. Options are fairly priced.`;
                else td.title = `IV at ${(val * 100).toFixed(0)}% is low. Options are cheap — good for buying if you expect a move.`;
            }
        });
        document.querySelectorAll('#optionsTableBody td:nth-child(7)').forEach(td => {
            const text = td.textContent?.trim();
            if (text && text !== '--' && !td.title) {
                const val = parseFloat(text);
                if (Math.abs(val) > 0.7) td.title = `Delta ${val.toFixed(2)} — Deep in-the-money. Moves almost dollar-for-dollar with the stock. High premium, low leverage.`;
                else if (Math.abs(val) > 0.4) td.title = `Delta ${val.toFixed(2)} — Near the money. Good balance of premium and leverage. Most liquid strike.`;
                else td.title = `Delta ${val.toFixed(2)} — Out-of-the-money. Cheap but lower probability of profit. Higher leverage but more likely to expire worthless.`;
            }
        });
        document.querySelectorAll('#optionsTableBody td:nth-child(8)').forEach(td => {
            const text = td.textContent?.trim().toUpperCase();
            if (text.includes('UNDERPRICED') && !td.title) td.title = 'This option is trading below its theoretical fair value. The market may be underestimating volatility or direction — potential buying opportunity.';
            else if (text.includes('OVERPRICED') && !td.title) td.title = 'This option is trading above its theoretical fair value. The market may be overpricing risk — consider selling premium or avoiding.';
            else if (text.includes('FAIR') && !td.title) td.title = 'This option is fairly priced — market price is close to theoretical value. No significant edge from mispricing.';
        });
    },
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => Educational.init());
