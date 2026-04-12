// Dashboard Widget Manager
// Handles data fetching, rendering, and auto-refresh for all 4 dashboard widgets.

const Dashboard = {
    charts: {},
    refreshTimers: {},
    data: {},
    currentTimeframe: 'daily', // Default timeframe for market sentiment chart
    currentSectorTimeframe: 'weekly', // Default timeframe for sector charts

    // ──────────────────────────────────────────────────────────
    // INITIALIZATION
    // ──────────────────────────────────────────────────────────

    init() {
        this.loadAllWidgets();
        this.setupAutoRefresh();
        this.setupEventListeners();
        this.setupTimeframeSelector();
    },

    async loadAllWidgets() {
        await Promise.allSettled([
            this.loadMarketSentiment(),
            this.loadSectorSentiment(),
            this.loadIndexSentiment(),
            this.loadCommoditiesCrypto(),
        ]);
    },

    setupAutoRefresh() {
        // Sentiment widgets: every 5 minutes
        this.refreshTimers.sentiment = setInterval(() => {
            this.loadMarketSentiment();
            this.loadSectorSentiment();
            this.loadIndexSentiment();
        }, 5 * 60 * 1000);

        // Commodities/crypto: every 1 minute
        this.refreshTimers.commodities = setInterval(() => {
            this.loadCommoditiesCrypto();
        }, 60 * 1000);
    },

    setupEventListeners() {
        const sectorSelector = document.getElementById('sectorSelector');
        if (sectorSelector) {
            sectorSelector.addEventListener('change', (e) => {
                this.filterSectors(e.target.value);
            });
        }

        // Sector timeframe selector
        const sectorTimeframeRadios = document.querySelectorAll('input[name="sectorTimeframe"]');
        sectorTimeframeRadios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.currentSectorTimeframe = e.target.value;
                this.updateCurrentSectorChart();
            });
        });

        document.querySelectorAll('.asset-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                this.switchAssetChart(e.target.dataset.asset);
            });
        });
    },

    setupTimeframeSelector() {
        const radios = document.querySelectorAll('input[name="chartTimeframe"]');
        radios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.currentTimeframe = e.target.value;
                this.updateMarketSentimentChart();
            });
        });
    },

    updateMarketSentimentChart() {
        const data = this.data.marketSentiment;
        if (!data) return;

        // Don't render if container is hidden (landing page) — will re-render when visible
        const container = document.getElementById('marketSentimentChart');
        if (container && container.offsetParent === null) {
            this._sentimentPending = true;
            return;
        }

        // Get the appropriate chart data based on timeframe
        let chartData = [];
        let timeUnit = 'day';
        let timeFormat = 'MMM d';
        let peaks = [];
        let troughs = [];

        switch (this.currentTimeframe) {
            case 'daily':
                chartData = data.daily_chart_data || data.weekly_chart_data || [];
                timeUnit = 'day';
                timeFormat = 'MMM d';
                // No peaks/troughs for daily (calculated on weekly)
                break;
            case 'weekly':
                chartData = data.weekly_chart_data || [];
                timeUnit = 'week';
                timeFormat = 'MMM d';
                // Peaks and troughs only for weekly view
                peaks = data.peaks || [];
                troughs = data.troughs || [];
                break;
            case 'hourly':
                chartData = data.hourly_chart_data || [];
                timeUnit = 'hour';
                timeFormat = 'MMM d HH:mm';
                // No peaks/troughs for hourly
                break;
            case '10min':
                chartData = data.ten_min_chart_data || [];
                timeUnit = 'minute';
                timeFormat = 'HH:mm';
                // No peaks/troughs for 10min
                break;
        }

        if (chartData.length > 0) {
            this.renderCandlestickChart(
                'marketSentimentChart',
                chartData,
                peaks,
                troughs,
                timeUnit,
                timeFormat
            );
        } else {
            // No data for this timeframe — clear the chart
            if (typeof AlphaCharts !== 'undefined') {
                AlphaCharts.destroy('marketSentimentChart');
            }
        }
    },

    // ──────────────────────────────────────────────────────────
    // WIDGET 1: Market Sentiment
    // ──────────────────────────────────────────────────────────

    async loadMarketSentiment() {
        try {
            const response = await apiRequest('/api/dashboard/market-sentiment');
            if (!response.ok) throw new Error('Failed to load market sentiment');
            const data = await response.json();
            this.data.marketSentiment = data;
            this.renderMarketSentiment(data);
        } catch (error) {
            this.renderWidgetError('widgetMarketSentiment', 'Market data unavailable');
        }
    },

    renderMarketSentiment(data) {
        const sentimentClass = data.sentiment.toLowerCase();

        // Big label
        const label = document.getElementById('marketSentimentLabel');
        label.textContent = data.sentiment;
        label.className = 'sentiment-label ' + sentimentClass;

        // Badge
        const badge = document.getElementById('marketSentimentBadge');
        badge.textContent = data.sentiment;
        badge.className = 'widget-badge ' + sentimentClass;

        // Confidence
        document.getElementById('marketSentimentConfidence').textContent =
            Math.round(data.confidence * 100) + '% confidence';

        // Indicator chips (clickable links to indicator guide)
        const indicatorsEl = document.getElementById('marketSentimentIndicators');
        indicatorsEl.innerHTML = '';
        if (data.indicators) {
            Object.entries(data.indicators).forEach(([name, info]) => {
                const chip = document.createElement('a');
                chip.className = 'indicator-chip ' + info.signal;
                chip.textContent = name.toUpperCase() + ': ' + info.signal;
                chip.title = (info.description || '') + ' (click to view in Indicator Guide)';

                // Create link to indicator guide
                const indicatorId = `indicator-${name.toLowerCase().replace(/[^a-z0-9]/g, '-')}`;
                chip.href = '#';
                chip.style.cursor = 'pointer';
                chip.addEventListener('click', (e) => {
                    e.preventDefault();
                    // Switch to indicators tab
                    document.querySelector('[data-tab="indicators"]').click();
                    // Wait for tab to load, then scroll to indicator
                    setTimeout(() => {
                        const indicatorCard = document.getElementById(indicatorId);
                        if (indicatorCard) {
                            indicatorCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            // Flash highlight
                            indicatorCard.classList.add('highlight-flash');
                            setTimeout(() => indicatorCard.classList.remove('highlight-flash'), 2000);
                        }
                    }, 100);
                });

                indicatorsEl.appendChild(chip);
            });
        }

        // CBOE context
        const contextEl = document.getElementById('marketSentimentContext');
        if (data.cboe_context) {
            contextEl.innerHTML =
                '<span class="indicator-chip">Options Sentiment: ' + data.cboe_context.pcr_regime + '</span>' +
                '<span class="indicator-chip">Market Type: ' + (data.market_type || 'unknown') + '</span>';
        } else {
            contextEl.innerHTML =
                '<span class="indicator-chip">Market Type: ' + (data.market_type || 'unknown') + '</span>';
        }

        // Chart — use selected timeframe
        this.updateMarketSentimentChart();

        // Timestamp
        document.getElementById('marketSentimentUpdated').textContent =
            'Updated: ' + new Date(data.last_updated).toLocaleTimeString();
    },

    // ──────────────────────────────────────────────────────────
    // WIDGET 2: Sector Sentiment
    // ──────────────────────────────────────────────────────────

    async loadSectorSentiment() {
        try {
            const response = await apiRequest('/api/dashboard/sector-sentiment');
            if (!response.ok) throw new Error('Failed to load sector sentiment');
            const data = await response.json();
            this.data.sectorSentiment = data;
            this.renderSectorSentiment(data);
        } catch (error) {
            this.renderWidgetError('widgetSectorSentiment', 'Sector data unavailable');
        }
    },

    renderSectorSentiment(data) {
        // Populate selector
        const selector = document.getElementById('sectorSelector');
        selector.innerHTML = '<option value="all">All Sectors</option>';
        data.sectors.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.name;
            opt.textContent = s.name;
            selector.appendChild(opt);
        });

        // Render sector pills with mini charts
        const grid = document.getElementById('sectorGrid');
        grid.innerHTML = '';
        data.sectors.forEach((sector, index) => {
            const pill = document.createElement('div');
            const sentimentClass = sector.sentiment.toLowerCase();
            pill.className = 'sector-pill ' + sentimentClass;

            const canvasId = `sectorMiniChart_${index}`;
            pill.innerHTML = `
                <div class="sector-pill-content">
                    <div class="sector-pill-info">
                        <div class="sector-pill-name">${sector.name}</div>
                        <div class="sector-pill-sentiment">${sector.sentiment}</div>
                    </div>
                    <div class="sector-pill-chart">
                        <canvas id="${canvasId}"></canvas>
                    </div>
                </div>
            `;
            pill.addEventListener('click', () => {
                this.showSectorChart(sector);
            });
            grid.appendChild(pill);

            // Render mini sparkline chart
            if (sector.weekly_chart_data && sector.weekly_chart_data.length > 0) {
                this.renderSectorMiniChart(canvasId, sector.weekly_chart_data, sentimentClass);
            }
        });

        document.getElementById('sectorSentimentUpdated').textContent =
            'Updated: ' + new Date(data.last_updated).toLocaleTimeString();
    },

    renderSectorMiniChart(canvasId, chartData, sentimentClass) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        const recentData = chartData.slice(-10);
        const closes = recentData.map(d => d.close);

        let color = '#888';
        if (sentimentClass === 'bullish') color = '#26a69a';
        else if (sentimentClass === 'bearish') color = '#ef5350';
        else if (sentimentClass === 'neutral') color = '#f0b90b';

        // Raw canvas sparkline — too small for Lightweight Charts
        this.renderMiniSparkline(canvasId, closes, sentimentClass === 'bearish' ? 'negative' : 'positive');
    },

    showSectorChart(sector) {
        this.currentSector = sector; // Store current sector for timeframe switching
        const container = document.getElementById('sectorChartContainer');
        container.style.display = 'block';
        this.updateCurrentSectorChart();
        // Update VIX & Index widget to react to sector selection
        this.updateIndexWidgetForSector(sector);
    },

    updateCurrentSectorChart() {
        if (!this.currentSector) return;

        const sector = this.currentSector;
        let chartData = [];
        let timeUnit = 'week';
        let timeFormat = 'MMM d';

        // Select chart data based on timeframe
        switch (this.currentSectorTimeframe) {
            case 'hourly':
                chartData = sector.hourly_chart_data || [];
                timeUnit = 'hour';
                timeFormat = 'MMM d HH:mm';
                break;
            case 'daily':
                chartData = sector.daily_chart_data || [];
                timeUnit = 'day';
                timeFormat = 'MMM d';
                break;
            case 'weekly':
            default:
                chartData = sector.weekly_chart_data || [];
                timeUnit = 'week';
                timeFormat = 'MMM d';
                break;
        }

        if (chartData.length > 0) {
            this.renderSectorCandlestickChart(
                'sectorChart',
                chartData,
                sector.name,
                timeUnit,
                timeFormat
            );
        }
    },

    renderSectorCandlestickChart(canvasId, chartData, sectorName, timeUnit = 'week', timeFormat = 'MMM d') {
        if (typeof AlphaCharts === 'undefined') return;
        const hasOHLC = chartData[0] && chartData[0].open !== undefined;

        if (hasOHLC) {
            // Compute SMA 20 inline
            const enriched = chartData.map((d, i) => {
                let sma = null;
                if (i >= 19) {
                    let sum = 0;
                    for (let j = i - 19; j <= i; j++) sum += chartData[j].close;
                    sma = sum / 20;
                }
                return { ...d, sma_20: sma };
            });
            AlphaCharts.quickCandlestick(canvasId, enriched, { height: 250, showVolume: false });
        } else {
            AlphaCharts.quickLine(canvasId, chartData, { keys: ['close'], labels: [sectorName], colors: ['#2962ff'], height: 250 });
        }
    },

    filterSectors(sectorName) {
        if (sectorName === 'all') {
            document.querySelectorAll('.sector-pill').forEach(p => p.style.display = '');
            document.getElementById('sectorChartContainer').style.display = 'none';
            // Reset VIX & Index widget to default state
            this.updateIndexWidgetForSector(null);
        } else {
            const sector = this.data.sectorSentiment.sectors.find(s => s.name === sectorName);
            if (sector) this.showSectorChart(sector);
        }
    },

    // ──────────────────────────────────────────────────────────
    // WIDGET 3: VIX & Index Sentiment
    // ──────────────────────────────────────────────────────────

    async loadIndexSentiment() {
        try {
            const response = await apiRequest('/api/dashboard/index-sentiment');
            if (!response.ok) throw new Error('Failed to load index sentiment');
            const data = await response.json();
            this.data.indexSentiment = data;
            this.renderIndexSentiment(data);
        } catch (error) {
            this.renderWidgetError('widgetIndexSentiment', 'Index data unavailable');
        }
    },

    renderIndexSentiment(data) {
        // VIX - New layout with market type prominent
        if (data.vix) {
            // Market type label (prominent)
            const fearLabel = document.getElementById('vixFearLabel');
            fearLabel.textContent = data.vix.fear_level;
            fearLabel.className = 'vix-market-type ' + this.vixFearClass(data.vix.fear_level);

            // VIX number (secondary)
            document.getElementById('vixValue').textContent = data.vix.value.toFixed(1);

            // Description
            document.getElementById('vixDescription').textContent = data.vix.description;

            // VIX Sparkline
            if (data.vix.history && data.vix.history.length > 1) {
                this.renderMiniSparkline('vixSparkline', data.vix.history, this.vixFearClass(data.vix.fear_level));
            }
        }

        // Index cards with mini sparklines
        const grid = document.getElementById('indexSentimentGrid');
        grid.innerHTML = '';
        if (data.indices) {
            data.indices.forEach((idx, i) => {
                const card = document.createElement('div');
                card.className = 'index-card';
                const changeClass = idx.weekly_change_pct >= 0 ? 'positive' : 'negative';
                const changeSign = idx.weekly_change_pct >= 0 ? '+' : '';
                const priceText = idx.current_price
                    ? '$' + idx.current_price.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })
                    : '--';
                const canvasId = 'indexSparkline' + i;
                card.innerHTML =
                    '<div class="index-card-content">' +
                        '<div class="index-info">' +
                            '<div class="index-name">' + idx.name + '</div>' +
                            '<div class="index-sentiment-badge ' + idx.sentiment.toLowerCase() + '">' + idx.sentiment + '</div>' +
                            '<div class="index-price">' + priceText + '</div>' +
                            '<div class="index-change ' + changeClass + '">' + changeSign + idx.weekly_change_pct.toFixed(1) + '%</div>' +
                        '</div>' +
                        '<div class="index-chart-container">' +
                            '<canvas id="' + canvasId + '" width="60" height="30"></canvas>' +
                        '</div>' +
                    '</div>';
                grid.appendChild(card);

                // Render sparkline after card is in DOM
                if (idx.history && idx.history.length > 1) {
                    setTimeout(() => {
                        this.renderMiniSparkline(canvasId, idx.history, changeClass);
                    }, 0);
                }
            });
        }

        // Inverse ETFs
        const invSection = document.getElementById('inverseEtfSentiment');
        if (data.inverse_etfs) {
            const inv = data.inverse_etfs;
            const invClass = inv.sentiment.toLowerCase();
            invSection.innerHTML =
                '<span class="widget-badge ' + invClass + '">' + inv.sentiment + '</span>' +
                '<p style="margin-top:6px;font-size:0.8rem;color:var(--text-secondary)">' + inv.description + '</p>';
        }

        document.getElementById('indexSentimentUpdated').textContent =
            'Updated: ' + new Date(data.last_updated).toLocaleTimeString();
    },

    renderMiniSparkline(canvasId, data, colorClass) {
        const canvas = document.getElementById(canvasId);
        if (!canvas || !data || data.length < 2) return;

        const ctx = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;

        // Determine color based on class or trend
        let color = '#00d4aa'; // Default green
        if (colorClass === 'negative' || colorClass === 'elevated' || colorClass === 'extreme') {
            color = '#ef5350'; // Red
        } else if (colorClass === 'low') {
            color = '#26a69a'; // Teal (calm)
        }

        // Clear canvas
        ctx.clearRect(0, 0, width, height);

        // Calculate min/max for scaling
        const min = Math.min(...data);
        const max = Math.max(...data);
        const range = max - min || 1;
        const padding = 2;

        // Draw line
        ctx.beginPath();
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.lineJoin = 'round';

        data.forEach((val, i) => {
            const x = padding + (i / (data.length - 1)) * (width - padding * 2);
            const y = height - padding - ((val - min) / range) * (height - padding * 2);
            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        ctx.stroke();

        // Draw end dot
        const lastX = width - padding;
        const lastY = height - padding - ((data[data.length - 1] - min) / range) * (height - padding * 2);
        ctx.beginPath();
        ctx.arc(lastX, lastY, 2, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
    },

    vixFearClass(level) {
        if (level.includes('Very Low') || level.includes('Low')) return 'low';
        if (level.includes('Normal')) return 'normal';
        if (level.includes('Elevated')) return 'elevated';
        if (level.includes('Extreme')) return 'extreme';
        return 'normal';
    },

    updateIndexWidgetForSector(sector) {
        const widgetTitle = document.querySelector('#widgetIndexSentiment .widget-title');
        const indexCards = document.querySelectorAll('.index-card');

        if (!sector) {
            // Reset to default state
            widgetTitle.textContent = 'VIX & Index Sentiment';
            indexCards.forEach(card => {
                card.style.opacity = '1';
                card.style.border = '';
            });
            return;
        }

        // Update title to show selected sector
        widgetTitle.textContent = `VIX & Index Sentiment - ${sector.name}`;

        // Highlight indices based on sector sentiment correlation
        indexCards.forEach(card => {
            const indexSentimentBadge = card.querySelector('.index-sentiment-badge');
            if (!indexSentimentBadge) return;

            const indexSentiment = indexSentimentBadge.textContent.trim().toLowerCase();
            const sectorSentiment = sector.sentiment.toLowerCase();

            // Highlight if sentiments match
            if (indexSentiment === sectorSentiment) {
                card.style.border = '2px solid var(--accent)';
                card.style.opacity = '1';
            } else {
                card.style.border = '';
                card.style.opacity = '0.6';
            }
        });

        // Add sector correlation info to VIX section
        const vixDescription = document.getElementById('vixDescription');
        if (vixDescription && this.data.indexSentiment) {
            const matchingIndices = this.data.indexSentiment.indices
                .filter(idx => idx.sentiment.toLowerCase() === sector.sentiment.toLowerCase())
                .map(idx => idx.name);

            let correlationText = '';
            if (matchingIndices.length > 0) {
                correlationText = ` <span style="color: var(--accent); font-weight: 600;">Correlated indices: ${matchingIndices.join(', ')}</span>`;
            } else {
                correlationText = ` <span style="color: var(--text-secondary);">No indices match ${sector.name} sentiment (${sector.sentiment})</span>`;
            }

            // Append to existing VIX description
            const originalDescription = this.data.indexSentiment.vix?.description || '';
            vixDescription.innerHTML = originalDescription + correlationText;
        }
    },

    // ──────────────────────────────────────────────────────────
    // WIDGET 4: Commodities & Crypto
    // ──────────────────────────────────────────────────────────

    async loadCommoditiesCrypto() {
        try {
            const response = await apiRequest('/api/dashboard/commodities-crypto');
            if (!response.ok) throw new Error('Failed to load commodity/crypto data');
            const data = await response.json();
            this.data.commoditiesCrypto = data;
            this.renderCommoditiesCrypto(data);
        } catch (error) {
            this.renderWidgetError('widgetCommoditiesCrypto', 'Price data unavailable');
        }
    },

    renderCommoditiesCrypto(data) {
        // Summary cards
        const grid = document.getElementById('assetSummaryGrid');
        grid.innerHTML = '';

        data.assets.forEach((asset, i) => {
            const card = document.createElement('div');
            card.className = 'asset-summary-card' + (i === 0 ? ' active' : '');
            card.dataset.symbol = asset.symbol;
            const changeClass = asset.change_24h_pct >= 0 ? 'positive' : 'negative';
            const changeSign = asset.change_24h_pct >= 0 ? '+' : '';
            const priceText = asset.current_price ? '$' + this.formatPrice(asset.current_price) : '--';
            card.innerHTML =
                '<div class="asset-name">' + asset.name + '</div>' +
                '<div class="asset-price">' + priceText + '</div>' +
                '<div class="asset-change ' + changeClass + '">' + changeSign + asset.change_24h_pct.toFixed(1) + '%</div>' +
                '<div class="asset-tlev">TLEV: ' + asset.tlev_signal + '</div>';
            card.addEventListener('click', () => this.switchAssetChart(asset.symbol));
            grid.appendChild(card);
        });

        // Render first asset chart
        if (data.assets.length > 0) {
            this.renderAssetChart(data.assets[0]);
        }

        document.getElementById('commodityCryptoUpdated').textContent =
            'Updated: ' + new Date(data.last_updated).toLocaleTimeString();
    },

    switchAssetChart(symbol) {
        // Update tab active states
        document.querySelectorAll('.asset-tab').forEach(t => {
            t.classList.toggle('active', t.dataset.asset === symbol);
        });
        document.querySelectorAll('.asset-summary-card').forEach(c => {
            c.classList.toggle('active', c.dataset.symbol === symbol);
        });

        // Find asset data and render chart
        if (this.data.commoditiesCrypto) {
            const asset = this.data.commoditiesCrypto.assets.find(a => a.symbol === symbol);
            if (asset) this.renderAssetChart(asset);
        }
    },

    renderAssetChart(asset) {
        if (typeof AlphaCharts === 'undefined') return;
        const chartData = asset.hourly_chart_data;
        if (!chartData || chartData.length === 0) return;
        AlphaCharts.quickCandlestick('commodityCryptoChart', chartData, { height: 200, showVolume: false, ticker: asset.symbol });
    },

    // ──────────────────────────────────────────────────────────
    // CANDLESTICK CHART (Market Sentiment + Earnings)
    // ──────────────────────────────────────────────────────────

    renderCandlestickChart(canvasId, chartData, peaks, troughs, timeUnit = 'week', timeFormat = 'MMM d') {
        if (typeof AlphaCharts === 'undefined') return;
        AlphaCharts.quickCandlestick(canvasId, chartData, { height: 250, showVolume: false });
    },

    // ──────────────────────────────────────────────────────────
    // SHARED LINE CHART HELPER
    // ──────────────────────────────────────────────────────────

    renderLineChart(canvasId, chartData, valueKeys, labels, colors) {
        if (typeof AlphaCharts === 'undefined') return;
        AlphaCharts.quickLine(canvasId, chartData, { keys: valueKeys, labels, colors, height: 200 });
    },

    // ──────────────────────────────────────────────────────────
    // ERROR HANDLING
    // ──────────────────────────────────────────────────────────

    renderWidgetError(widgetId, message) {
        const widget = document.getElementById(widgetId);
        if (!widget) return;
        const body = widget.querySelector('.widget-body');
        if (body) {
            body.innerHTML = '<div class="widget-loading">' + message + '</div>';
        }
    },

    // ──────────────────────────────────────────────────────────
    // UTILITY
    // ──────────────────────────────────────────────────────────

    formatPrice(price) {
        if (price >= 1000) {
            return price.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 });
        }
        return price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    },
};

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (typeof apiRequest !== 'undefined') {
        Dashboard.init();
    } else {
        // If app.js hasn't loaded yet, wait for it
        const checkReady = setInterval(() => {
            if (typeof apiRequest !== 'undefined') {
                clearInterval(checkReady);
                Dashboard.init();
            }
        }, 100);
        // Give up after 5 seconds
        setTimeout(() => clearInterval(checkReady), 5000);
    }
});
