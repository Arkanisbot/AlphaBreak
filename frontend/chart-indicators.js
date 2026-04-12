// ============================================================================
// AlphaBreak Chart Indicators — Sub-pane indicators + client-side calculations
// ============================================================================
// Adds RSI, MACD, Stochastic, VWAP as proper chart sub-panes below main chart.
// All calculations done client-side from OHLCV data — no extra API calls.

const ChartIndicators = (() => {

    // ── Indicator Calculation Functions ──────────────────────────────────

    function calcRSI(closes, period = 14) {
        const rsi = new Array(closes.length).fill(null);
        if (closes.length < period + 1) return rsi;

        let avgGain = 0, avgLoss = 0;
        for (let i = 1; i <= period; i++) {
            const diff = closes[i] - closes[i - 1];
            if (diff > 0) avgGain += diff;
            else avgLoss -= diff;
        }
        avgGain /= period;
        avgLoss /= period;

        rsi[period] = avgLoss === 0 ? 100 : 100 - (100 / (1 + avgGain / avgLoss));

        for (let i = period + 1; i < closes.length; i++) {
            const diff = closes[i] - closes[i - 1];
            avgGain = (avgGain * (period - 1) + (diff > 0 ? diff : 0)) / period;
            avgLoss = (avgLoss * (period - 1) + (diff < 0 ? -diff : 0)) / period;
            rsi[i] = avgLoss === 0 ? 100 : 100 - (100 / (1 + avgGain / avgLoss));
        }
        return rsi;
    }

    function _ema(data, period) {
        const result = new Array(data.length).fill(null);
        const k = 2 / (period + 1);
        let first = 0, count = 0;
        for (let i = 0; i < data.length; i++) {
            if (data[i] != null) { first += data[i]; count++; }
            if (count === period) {
                result[i] = first / period;
                for (let j = i + 1; j < data.length; j++) {
                    if (data[j] != null) {
                        result[j] = data[j] * k + result[j - 1] * (1 - k);
                    }
                }
                break;
            }
        }
        return result;
    }

    function calcMACD(closes, fast = 12, slow = 26, signal = 9) {
        const emaFast = _ema(closes, fast);
        const emaSlow = _ema(closes, slow);
        const macdLine = new Array(closes.length).fill(null);

        for (let i = 0; i < closes.length; i++) {
            if (emaFast[i] != null && emaSlow[i] != null) {
                macdLine[i] = emaFast[i] - emaSlow[i];
            }
        }

        const signalLine = _ema(macdLine, signal);
        const histogram = new Array(closes.length).fill(null);
        for (let i = 0; i < closes.length; i++) {
            if (macdLine[i] != null && signalLine[i] != null) {
                histogram[i] = macdLine[i] - signalLine[i];
            }
        }

        return { macd: macdLine, signal: signalLine, histogram };
    }

    function calcStochastic(highs, lows, closes, kPeriod = 14, dPeriod = 3) {
        const kValues = new Array(closes.length).fill(null);

        for (let i = kPeriod - 1; i < closes.length; i++) {
            let highest = -Infinity, lowest = Infinity;
            for (let j = i - kPeriod + 1; j <= i; j++) {
                if (highs[j] > highest) highest = highs[j];
                if (lows[j] < lowest) lowest = lows[j];
            }
            const range = highest - lowest;
            kValues[i] = range === 0 ? 50 : ((closes[i] - lowest) / range) * 100;
        }

        // %D is SMA of %K
        const dValues = new Array(closes.length).fill(null);
        for (let i = kPeriod - 1 + dPeriod - 1; i < closes.length; i++) {
            let sum = 0;
            for (let j = 0; j < dPeriod; j++) {
                sum += kValues[i - j];
            }
            dValues[i] = sum / dPeriod;
        }

        return { k: kValues, d: dValues };
    }

    function calcVWAP(highs, lows, closes, volumes) {
        const vwap = new Array(closes.length).fill(null);
        let cumVol = 0, cumTP = 0;

        for (let i = 0; i < closes.length; i++) {
            const tp = (highs[i] + lows[i] + closes[i]) / 3;
            cumVol += volumes[i];
            cumTP += tp * volumes[i];
            vwap[i] = cumVol > 0 ? cumTP / cumVol : null;
        }
        return vwap;
    }

    // ── Theme colors for indicators ─────────────────────────────────────

    const COLORS = {
        rsi: '#2962FF',
        rsiOverbought: 'rgba(239, 83, 80, 0.3)',
        rsiOversold: 'rgba(38, 166, 154, 0.3)',
        macdLine: '#2962FF',
        macdSignal: '#FF6D00',
        macdHistUp: 'rgba(38, 166, 154, 0.6)',
        macdHistDown: 'rgba(239, 83, 80, 0.6)',
        stochK: '#2962FF',
        stochD: '#FF6D00',
        vwap: '#E040FB',
        paneBackground: '#131722',
        paneBorder: 'rgba(42, 46, 57, 0.8)',
        textColor: '#8b95a5',
        gridColor: 'rgba(42, 46, 57, 0.5)',
    };

    // ── Create an indicator sub-pane ────────────────────────────────────

    function _createPane(container, height, label) {
        const wrapper = document.createElement('div');
        wrapper.className = 'indicator-pane';
        wrapper.style.height = height + 'px';
        wrapper.style.width = '100%';
        wrapper.style.position = 'relative';
        wrapper.style.borderTop = `1px solid ${COLORS.paneBorder}`;
        container.appendChild(wrapper);

        // Label
        const labelEl = document.createElement('div');
        labelEl.className = 'indicator-pane-label';
        labelEl.textContent = label;
        labelEl.style.cssText = `position:absolute;top:4px;left:8px;z-index:5;
            font-size:10px;font-weight:600;color:${COLORS.textColor};
            text-transform:uppercase;letter-spacing:0.5px;pointer-events:none;`;
        wrapper.appendChild(labelEl);

        const chart = LightweightCharts.createChart(wrapper, {
            layout: {
                background: { type: 'solid', color: COLORS.paneBackground },
                textColor: COLORS.textColor,
                fontSize: 10,
            },
            grid: {
                vertLines: { color: COLORS.gridColor },
                horzLines: { color: COLORS.gridColor },
            },
            rightPriceScale: {
                borderColor: COLORS.gridColor,
                scaleMargins: { top: 0.12, bottom: 0.08 },
            },
            timeScale: { visible: false },
            handleScroll: false,
            handleScale: false,
            crosshair: {
                mode: LightweightCharts.CrosshairMode.Normal,
                vertLine: { visible: true, color: '#5c6578', width: 1, style: 2 },
                horzLine: { visible: true, color: '#5c6578', width: 1, style: 2 },
            },
        });

        return { chart, wrapper, label: labelEl };
    }

    // ── Render RSI Pane ─────────────────────────────────────────────────

    function renderRSI(containerId, chartData, mainChart) {
        const container = document.getElementById(containerId);
        if (!container || !chartData?.length) return null;

        const closes = chartData.map(d => d.close);
        const rsiValues = calcRSI(closes, 14);

        const pane = _createPane(container, 100, 'RSI (14)');

        // Overbought/oversold bands
        const overboughtLine = pane.chart.addLineSeries({
            color: COLORS.rsiOverbought,
            lineWidth: 1,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            crosshairMarkerVisible: false,
            lastValueVisible: false,
            priceLineVisible: false,
        });
        const oversoldLine = pane.chart.addLineSeries({
            color: COLORS.rsiOversold,
            lineWidth: 1,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            crosshairMarkerVisible: false,
            lastValueVisible: false,
            priceLineVisible: false,
        });

        // RSI line
        const rsiSeries = pane.chart.addLineSeries({
            color: COLORS.rsi,
            lineWidth: 2,
            crosshairMarkerVisible: true,
            lastValueVisible: true,
            priceLineVisible: false,
        });

        const timeData = chartData.map(d => _toTime(d.timestamp));

        const rsiLineData = rsiValues
            .map((v, i) => v != null ? { time: timeData[i], value: v } : null)
            .filter(Boolean);

        const obData = timeData.map(t => ({ time: t, value: 70 }));
        const osData = timeData.map(t => ({ time: t, value: 30 }));

        overboughtLine.setData(obData);
        oversoldLine.setData(osData);
        rsiSeries.setData(rsiLineData);

        // Fixed scale 0-100
        pane.chart.priceScale('right').applyOptions({
            autoScale: false,
            scaleMargins: { top: 0.05, bottom: 0.05 },
        });
        rsiSeries.applyOptions({ autoscaleInfoProvider: () => ({ priceRange: { minValue: 0, maxValue: 100 } }) });

        // Sync time scale with main chart
        _syncTimeScale(mainChart, pane.chart);

        return { pane, series: rsiSeries };
    }

    // ── Render MACD Pane ─────────────────────────────────────────────────

    function renderMACD(containerId, chartData, mainChart) {
        const container = document.getElementById(containerId);
        if (!container || !chartData?.length) return null;

        const closes = chartData.map(d => d.close);
        const { macd, signal, histogram } = calcMACD(closes, 12, 26, 9);

        const pane = _createPane(container, 120, 'MACD (12, 26, 9)');

        // Histogram
        const histSeries = pane.chart.addHistogramSeries({
            priceScaleId: '',
            priceFormat: { type: 'price', precision: 4, minMove: 0.0001 },
        });

        // MACD line
        const macdSeries = pane.chart.addLineSeries({
            color: COLORS.macdLine,
            lineWidth: 2,
            crosshairMarkerVisible: true,
            lastValueVisible: true,
            priceLineVisible: false,
        });

        // Signal line
        const signalSeries = pane.chart.addLineSeries({
            color: COLORS.macdSignal,
            lineWidth: 1,
            crosshairMarkerVisible: false,
            lastValueVisible: true,
            priceLineVisible: false,
        });

        const timeData = chartData.map(d => _toTime(d.timestamp));

        const histData = histogram
            .map((v, i) => v != null ? {
                time: timeData[i],
                value: v,
                color: v >= 0 ? COLORS.macdHistUp : COLORS.macdHistDown,
            } : null)
            .filter(Boolean);

        const macdData = macd
            .map((v, i) => v != null ? { time: timeData[i], value: v } : null)
            .filter(Boolean);

        const signalData = signal
            .map((v, i) => v != null ? { time: timeData[i], value: v } : null)
            .filter(Boolean);

        histSeries.setData(histData);
        macdSeries.setData(macdData);
        signalSeries.setData(signalData);

        _syncTimeScale(mainChart, pane.chart);

        return { pane, series: { macd: macdSeries, signal: signalSeries, histogram: histSeries } };
    }

    // ── Render Stochastic Pane ───────────────────────────────────────────

    function renderStochastic(containerId, chartData, mainChart) {
        const container = document.getElementById(containerId);
        if (!container || !chartData?.length) return null;

        const highs = chartData.map(d => d.high);
        const lows = chartData.map(d => d.low);
        const closes = chartData.map(d => d.close);
        const { k, d } = calcStochastic(highs, lows, closes, 14, 3);

        const pane = _createPane(container, 100, 'Stochastic (14, 3)');

        // Overbought/oversold
        const obLine = pane.chart.addLineSeries({
            color: COLORS.rsiOverbought, lineWidth: 1,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false,
        });
        const osLine = pane.chart.addLineSeries({
            color: COLORS.rsiOversold, lineWidth: 1,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false,
        });

        // %K and %D lines
        const kSeries = pane.chart.addLineSeries({
            color: COLORS.stochK, lineWidth: 2,
            crosshairMarkerVisible: true, lastValueVisible: true, priceLineVisible: false,
        });
        const dSeries = pane.chart.addLineSeries({
            color: COLORS.stochD, lineWidth: 1,
            crosshairMarkerVisible: false, lastValueVisible: true, priceLineVisible: false,
        });

        const timeData = chartData.map(d => _toTime(d.timestamp));

        obLine.setData(timeData.map(t => ({ time: t, value: 80 })));
        osLine.setData(timeData.map(t => ({ time: t, value: 20 })));
        kSeries.setData(k.map((v, i) => v != null ? { time: timeData[i], value: v } : null).filter(Boolean));
        dSeries.setData(d.map((v, i) => v != null ? { time: timeData[i], value: v } : null).filter(Boolean));

        kSeries.applyOptions({ autoscaleInfoProvider: () => ({ priceRange: { minValue: 0, maxValue: 100 } }) });

        _syncTimeScale(mainChart, pane.chart);

        return { pane, series: { k: kSeries, d: dSeries } };
    }

    // ── Add VWAP Overlay (on main chart, not sub-pane) ──────────────────

    function addVWAP(instance, chartData) {
        if (!instance || !chartData?.length) return null;

        const highs = chartData.map(d => d.high);
        const lows = chartData.map(d => d.low);
        const closes = chartData.map(d => d.close);
        const volumes = chartData.map(d => d.volume || 0);
        const vwapValues = calcVWAP(highs, lows, closes, volumes);

        const series = instance.chart.addLineSeries({
            color: COLORS.vwap,
            lineWidth: 2,
            lineStyle: LightweightCharts.LineStyle.Solid,
            crosshairMarkerVisible: true,
            lastValueVisible: true,
            priceLineVisible: false,
            title: 'VWAP',
        });

        const data = vwapValues
            .map((v, i) => v != null ? { time: _toTime(chartData[i].timestamp), value: v } : null)
            .filter(Boolean);

        series.setData(data);
        instance.overlays.vwap = series;
        return series;
    }

    // ── Time scale sync ─────────────────────────────────────────────────

    function _syncTimeScale(mainChart, paneChart) {
        mainChart.timeScale().subscribeVisibleLogicalRangeChange(range => {
            if (range) {
                try { paneChart.timeScale().setVisibleLogicalRange(range); } catch (e) {}
            }
        });
    }

    // ── Time conversion (mirrors AlphaCharts._toTime) ───────────────────

    function _toTime(timestamp) {
        if (typeof timestamp === 'string') {
            const datePart = timestamp.substring(0, 10);
            const parts = datePart.split('-');
            if (parts.length === 3 && parts[0].length === 4) {
                const y = parseInt(parts[0]);
                const m = parseInt(parts[1]);
                const d = parseInt(parts[2]);
                const timePart = timestamp.substring(11, 19);
                if (!timePart || timePart === '00:00:00' || timePart === '') {
                    return { year: y, month: m, day: d };
                }
                return Math.floor(new Date(timestamp).getTime() / 1000);
            }
        }
        if (typeof timestamp === 'number') return timestamp;
        return Math.floor(new Date(timestamp).getTime() / 1000);
    }

    // ── Resize all indicator panes ──────────────────────────────────────

    function resizePanes(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        const panes = container.querySelectorAll('.indicator-pane');
        panes.forEach(pane => {
            const charts = pane.querySelectorAll('canvas');
            // Lightweight Charts handles internal resize via container width
        });
    }

    // ── Destroy indicator panes ─────────────────────────────────────────

    function destroyPanes(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        const panes = container.querySelectorAll('.indicator-pane');
        panes.forEach(pane => pane.remove());
    }

    return {
        calcRSI, calcMACD, calcStochastic, calcVWAP,
        renderRSI, renderMACD, renderStochastic, addVWAP,
        destroyPanes, resizePanes,
    };
})();

window.ChartIndicators = ChartIndicators;
