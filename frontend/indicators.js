// ============================================================================
// Indicator Guide — Loads and displays indicator explanations
// ============================================================================

const IndicatorGuide = {
    indicators: [],

    // Indicator display names and order
    // usedInMarketSentiment: true marks indicators shown in the Market Sentiment widget
    indicatorMeta: {
        'CCI': { name: 'CCI (Commodity Channel Index)', order: 1, usedInMarketSentiment: true },
        'RSI': { name: 'RSI (Relative Strength Index)', order: 2, usedInMarketSentiment: true },
        'SMA Crossover': { name: 'SMA Crossover (20/50)', order: 3, usedInMarketSentiment: true },
        'Stochastic': { name: 'Stochastic Oscillator', order: 4, usedInMarketSentiment: true },
        'ADX': { name: 'ADX (Average Directional Index)', order: 5 },
        'TLEV': { name: 'TLEV (Volume Momentum)', order: 6, usedInMarketSentiment: true },
        'VIX': { name: 'VIX (Volatility Index)', order: 7 },
        'PCR': { name: 'Put/Call Ratio', order: 8 },
    },

    async init() {
        await this.loadIndicators();
        this.renderIndicators();
    },

    async loadIndicators() {
        try {
            const response = await fetch('data/indicators.csv');
            if (!response.ok) throw new Error('Failed to load indicators CSV');

            const csvText = await response.text();
            this.indicators = this.parseCSV(csvText);
        } catch (error) {
            console.error('Failed to load indicator data:', error);
            this.indicators = [];
        }
    },

    parseCSV(csvText) {
        const lines = csvText.trim().split('\n');
        if (lines.length < 2) return [];

        const indicators = [];

        // Skip header row, parse data rows
        for (let i = 1; i < lines.length; i++) {
            const values = this.parseCSVLine(lines[i]);
            if (values.length >= 4) {
                indicators.push({
                    name: values[0].trim(),
                    bullish: values[1].trim(),
                    neutral: values[2].trim(),
                    bearish: values[3].trim(),
                });
            }
        }

        // Sort by order defined in indicatorMeta
        indicators.sort((a, b) => {
            const orderA = this.indicatorMeta[a.name]?.order || 99;
            const orderB = this.indicatorMeta[b.name]?.order || 99;
            return orderA - orderB;
        });

        return indicators;
    },

    parseCSVLine(line) {
        const values = [];
        let current = '';
        let inQuotes = false;

        for (let i = 0; i < line.length; i++) {
            const char = line[i];

            if (char === '"') {
                inQuotes = !inQuotes;
            } else if (char === ',' && !inQuotes) {
                values.push(current);
                current = '';
            } else {
                current += char;
            }
        }
        values.push(current);

        return values;
    },

    renderIndicators() {
        const container = document.getElementById('indicatorGuideContainer');
        if (!container) return;

        if (this.indicators.length === 0) {
            container.innerHTML = '<p class="indicator-error">Failed to load indicator data. Please try refreshing the page.</p>';
            return;
        }

        container.innerHTML = this.indicators.map(indicator => {
            const displayName = this.indicatorMeta[indicator.name]?.name || indicator.name;
            const meta = this.indicatorMeta[indicator.name];
            const isMarketSentiment = meta?.usedInMarketSentiment || false;

            // Create ID for linking (lowercase, remove spaces/special chars)
            const indicatorId = `indicator-${indicator.name.toLowerCase().replace(/[^a-z0-9]/g, '-')}`;
            const cardClass = isMarketSentiment ? 'indicator-card market-sentiment-indicator' : 'indicator-card';
            const badge = isMarketSentiment ? '<span class="market-sentiment-badge" title="Used in Market Sentiment widget">Market Sentiment</span>' : '';

            return `
                <div class="${cardClass}" id="${indicatorId}">
                    <div class="indicator-card-header">
                        <h3 class="indicator-card-title">${displayName}</h3>
                        ${badge}
                    </div>
                    <div class="indicator-card-body">
                        <div class="indicator-columns">
                            <div class="indicator-column bullish">
                                <div class="indicator-column-header">
                                    <span class="indicator-signal-badge bullish">Bullish</span>
                                </div>
                                <div class="indicator-column-content">
                                    <p>${indicator.bullish}</p>
                                </div>
                            </div>
                            <div class="indicator-column neutral">
                                <div class="indicator-column-header">
                                    <span class="indicator-signal-badge neutral">Neutral</span>
                                </div>
                                <div class="indicator-column-content">
                                    <p>${indicator.neutral}</p>
                                </div>
                            </div>
                            <div class="indicator-column bearish">
                                <div class="indicator-column-header">
                                    <span class="indicator-signal-badge bearish">Bearish</span>
                                </div>
                                <div class="indicator-column-content">
                                    <p>${indicator.bearish}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    },
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Only init if the indicators tab exists
    if (document.getElementById('indicatorsTab')) {
        IndicatorGuide.init();
    }
});

window.IndicatorGuide = IndicatorGuide;
