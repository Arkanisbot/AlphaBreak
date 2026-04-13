// ============================================================================
// AlphaBreak Chart Drawing Tools — Canvas overlay for user annotations
// ============================================================================
// Supports: Trendline, Horizontal Line, Fibonacci Retracement, Rectangle,
//           Parallel Channel, Measure, Text Annotation
// Drawings are saved per ticker in localStorage.
//
// Hold Shift while clicking to snap the y-coordinate to the nearest OHLC price
// of the candle under the cursor.

const ChartDrawings = (() => {
    const STORAGE_PREFIX = 'chartDrawings_';
    let activeChart = null;
    let canvas = null;
    let ctx = null;
    let drawings = [];
    let currentTool = null;
    let drawState = null; // { phase, points }
    let hoveredDrawing = null;
    let ticker = '';
    let shiftHeld = false;

    const TOOLS = {
        trendline: { cursor: 'crosshair', points: 2, label: 'Trendline' },
        hline: { cursor: 'crosshair', points: 1, label: 'Horizontal Line' },
        fibonacci: { cursor: 'crosshair', points: 2, label: 'Fibonacci' },
        rectangle: { cursor: 'crosshair', points: 2, label: 'Rectangle' },
        parallelChannel: { cursor: 'crosshair', points: 3, label: 'Parallel Channel' },
        measure: { cursor: 'crosshair', points: 2, label: 'Measure' },
        text: { cursor: 'text', points: 1, label: 'Text Annotation' },
    };

    const COLORS = {
        line: '#2962FF',
        hline: '#FF6D00',
        fib: '#AB47BC',
        rect: 'rgba(41, 98, 255, 0.15)',
        rectBorder: '#2962FF',
        channel: '#26C6DA',
        channelFill: 'rgba(38, 198, 218, 0.10)',
        measure: '#FFEB3B',
        measureFill: 'rgba(255, 235, 59, 0.10)',
        textAnnotation: '#FFD54F',
        handle: '#ffffff',
        hover: '#FFD54F',
        text: '#8b95a5',
    };

    const FIB_LEVELS = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1];

    // ── Initialize drawing layer on a chart ─────────────────────────────

    function init(containerId, chartInstance, tickerSymbol) {
        destroy(); // clean up previous

        const container = document.getElementById(containerId);
        if (!container || !chartInstance) return;

        activeChart = chartInstance;
        ticker = tickerSymbol || '';

        // Create transparent canvas overlay
        canvas = document.createElement('canvas');
        canvas.className = 'chart-drawing-canvas';
        canvas.style.cssText = `position:absolute;top:0;left:0;width:100%;height:100%;
            z-index:20;pointer-events:none;`;

        // Insert into the chart's first child (the main chart div)
        const chartDiv = container.children[0];
        if (chartDiv) {
            chartDiv.style.position = 'relative';
            chartDiv.appendChild(canvas);
        }

        ctx = canvas.getContext('2d');
        _resizeCanvas();

        // Load saved drawings
        drawings = _loadDrawings();

        window.addEventListener('resize', _resizeCanvas);
        _render();
    }

    // ── Activate a drawing tool ─────────────────────────────────────────

    function setTool(toolName) {
        if (!TOOLS[toolName]) {
            currentTool = null;
            drawState = null;
            if (canvas) canvas.style.pointerEvents = 'none';
            _updateToolbarState();
            return;
        }

        currentTool = toolName;
        drawState = { phase: 0, points: [] };
        if (canvas) {
            canvas.style.pointerEvents = 'all';
            canvas.style.cursor = TOOLS[toolName].cursor;
        }

        _bindEvents();
        _updateToolbarState();
    }

    function cancelTool() {
        currentTool = null;
        drawState = null;
        if (canvas) {
            canvas.style.pointerEvents = 'none';
            canvas.style.cursor = 'default';
        }
        _unbindEvents();
        _updateToolbarState();
        _render();
    }

    // ── Event handlers ──────────────────────────────────────────────────

    let _boundClick = null;
    let _boundMove = null;
    let _boundKey = null;
    let _boundKeyUp = null;

    function _bindEvents() {
        _unbindEvents();

        _boundClick = (e) => _handleClick(e);
        _boundMove = (e) => _handleMove(e);
        _boundKey = (e) => {
            if (e.key === 'Escape') cancelTool();
            if (e.key === 'Shift') shiftHeld = true;
        };
        _boundKeyUp = (e) => { if (e.key === 'Shift') shiftHeld = false; };

        canvas.addEventListener('click', _boundClick);
        canvas.addEventListener('mousemove', _boundMove);
        document.addEventListener('keydown', _boundKey);
        document.addEventListener('keyup', _boundKeyUp);
    }

    function _unbindEvents() {
        if (_boundClick && canvas) canvas.removeEventListener('click', _boundClick);
        if (_boundMove && canvas) canvas.removeEventListener('mousemove', _boundMove);
        if (_boundKey) document.removeEventListener('keydown', _boundKey);
        if (_boundKeyUp) document.removeEventListener('keyup', _boundKeyUp);
        shiftHeld = false;
    }

    // Default stroke color per tool — used when finalizing a drawing.
    function _defaultColorFor(tool) {
        switch (tool) {
            case 'trendline': return COLORS.line;
            case 'hline': return COLORS.hline;
            case 'fibonacci': return COLORS.fib;
            case 'rectangle': return COLORS.rectBorder;
            case 'parallelChannel': return COLORS.channel;
            case 'measure': return COLORS.measure;
            case 'text': return COLORS.textAnnotation;
            default: return COLORS.line;
        }
    }

    function _handleClick(e) {
        if (!currentTool || !activeChart || !drawState) return;

        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // Convert pixel to price/time coordinates, with optional shift-snap.
        let coord = _pixelToCoord(x, y);
        if (!coord) return;
        if (e.shiftKey || shiftHeld) coord = _snapToPrice(coord);

        drawState.points.push(coord);
        drawState.phase++;

        const needed = TOOLS[currentTool].points;
        if (drawState.phase >= needed) {
            // Text tool: prompt for label content before persisting.
            let label = null;
            if (currentTool === 'text') {
                label = window.prompt('Annotation text:', '');
                if (label == null || label.trim() === '') {
                    cancelTool();
                    _render();
                    return;
                }
            }

            const drawing = {
                type: currentTool,
                points: drawState.points,
                color: _defaultColorFor(currentTool),
                id: Date.now(),
                label,
            };
            drawings.push(drawing);
            _saveDrawings();
            cancelTool();
        }

        _render();
    }

    function _handleMove(e) {
        if (!ctx || !canvas) return;

        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // Show preview while drawing
        if (currentTool && drawState && drawState.points.length > 0) {
            let coord = _pixelToCoord(x, y);
            if (!coord) return;
            if (e.shiftKey || shiftHeld) coord = _snapToPrice(coord);
            _render();
            _drawPreview(drawState.points, coord);
        }
    }

    // Snap the price of a coord to the nearest OHLC of the candle under the
    // cursor. Uses chartData from the active chart instance.
    function _snapToPrice(coord) {
        const data = activeChart?.chartData;
        if (!data || !data.length || !coord) return coord;

        // Find nearest candle by x-coordinate.
        const xPx = activeChart.chart.timeScale().timeToCoordinate(coord.time);
        if (xPx == null) return coord;

        let nearest = null, bestDist = Infinity;
        for (const d of data) {
            const t = _toTime(d.timestamp);
            const px = activeChart.chart.timeScale().timeToCoordinate(t);
            if (px == null) continue;
            const dist = Math.abs(px - xPx);
            if (dist < bestDist) { bestDist = dist; nearest = d; }
        }
        if (!nearest) return coord;

        // Snap price to whichever OHLC is closest.
        const candidates = [nearest.open, nearest.high, nearest.low, nearest.close];
        let snapped = candidates[0], snapDist = Math.abs(coord.price - snapped);
        for (const p of candidates) {
            const d = Math.abs(coord.price - p);
            if (d < snapDist) { snapDist = d; snapped = p; }
        }
        return { ...coord, price: snapped };
    }

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

    // ── Coordinate conversion ───────────────────────────────────────────

    function _pixelToCoord(x, y) {
        if (!activeChart?.chart) return null;

        const chart = activeChart.chart;
        const timeScale = chart.timeScale();
        const priceScale = chart.priceScale('right');

        // Get time from x coordinate
        const time = timeScale.coordinateToTime(x);
        if (!time) return null;

        // Get price from y coordinate using the candle series
        const price = activeChart.candleSeries.coordinateToPrice(y);
        if (price == null || isNaN(price)) return null;

        return { time, price, x, y };
    }

    function _coordToPixel(coord) {
        if (!activeChart?.chart) return null;

        const chart = activeChart.chart;
        const x = chart.timeScale().timeToCoordinate(coord.time);
        const y = activeChart.candleSeries.priceToCoordinate(coord.price);

        if (x == null || y == null) return null;
        return { x, y };
    }

    // ── Rendering ───────────────────────────────────────────────────────

    function _render() {
        if (!ctx || !canvas) return;
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Draw all saved drawings
        for (const drawing of drawings) {
            _drawShape(drawing, drawing === hoveredDrawing);
        }
    }

    function _drawShape(drawing, isHovered) {
        const color = isHovered ? COLORS.hover : drawing.color;

        switch (drawing.type) {
            case 'trendline': _drawLine(drawing.points, color, 2); break;
            case 'hline': _drawHLine(drawing.points[0], color); break;
            case 'fibonacci': _drawFibonacci(drawing.points, color); break;
            case 'rectangle': _drawRectangle(drawing.points, color); break;
            case 'parallelChannel': _drawParallelChannel(drawing.points, color); break;
            case 'measure': _drawMeasure(drawing.points, color); break;
            case 'text': _drawTextAnnotation(drawing.points[0], drawing.label, color); break;
        }
    }

    function _drawPreview(committedPoints, cursorCoord) {
        const color = 'rgba(41, 98, 255, 0.6)';
        const startCoord = committedPoints[0];

        switch (currentTool) {
            case 'trendline':
                _drawLine([startCoord, cursorCoord], color, 2);
                break;
            case 'fibonacci':
                _drawFibonacci([startCoord, cursorCoord], color);
                break;
            case 'rectangle':
                _drawRectangle([startCoord, cursorCoord], color);
                break;
            case 'parallelChannel':
                if (committedPoints.length === 1) {
                    // Phase 1 → 2: previewing the base line.
                    _drawLine([startCoord, cursorCoord], color, 2);
                } else if (committedPoints.length === 2) {
                    // Phase 2 → 3: base line committed, previewing parallel offset.
                    _drawParallelChannel([committedPoints[0], committedPoints[1], cursorCoord], color);
                }
                break;
            case 'measure':
                _drawMeasure([startCoord, cursorCoord], color);
                break;
            case 'text':
                _drawTextAnnotation(cursorCoord, '(text...)', color);
                break;
        }
    }

    function _drawLine(points, color, width) {
        if (points.length < 2) return;
        const p1 = _coordToPixel(points[0]);
        const p2 = _coordToPixel(points[1]);
        if (!p1 || !p2) return;

        ctx.strokeStyle = color;
        ctx.lineWidth = width;
        ctx.setLineDash([]);
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();

        // Draw handles
        _drawHandle(p1.x, p1.y);
        _drawHandle(p2.x, p2.y);
    }

    function _drawHLine(point, color) {
        if (!point) return;
        const y = activeChart.candleSeries.priceToCoordinate(point.price);
        if (y == null) return;

        ctx.strokeStyle = color;
        ctx.lineWidth = 1;
        ctx.setLineDash([6, 3]);
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(canvas.width, y);
        ctx.stroke();
        ctx.setLineDash([]);

        // Price label
        ctx.font = '10px Inter, sans-serif';
        ctx.fillStyle = color;
        ctx.textAlign = 'right';
        ctx.fillText(`$${point.price.toFixed(2)}`, canvas.width - 5, y - 4);
    }

    function _drawFibonacci(points, color) {
        if (points.length < 2) return;
        const p1 = _coordToPixel(points[0]);
        const p2 = _coordToPixel(points[1]);
        if (!p1 || !p2) return;

        const priceRange = points[1].price - points[0].price;
        const xLeft = Math.min(p1.x, p2.x) - 20;
        const xRight = Math.max(canvas.width, Math.max(p1.x, p2.x) + 20);

        for (const level of FIB_LEVELS) {
            const price = points[0].price + priceRange * level;
            const y = activeChart.candleSeries.priceToCoordinate(price);
            if (y == null) continue;

            const alpha = level === 0 || level === 1 ? 0.6 : 0.35;
            ctx.strokeStyle = color;
            ctx.globalAlpha = alpha;
            ctx.lineWidth = 1;
            ctx.setLineDash(level === 0.5 ? [6, 3] : []);
            ctx.beginPath();
            ctx.moveTo(xLeft, y);
            ctx.lineTo(xRight, y);
            ctx.stroke();

            // Label
            ctx.globalAlpha = 0.8;
            ctx.font = '10px Inter, sans-serif';
            ctx.fillStyle = color;
            ctx.textAlign = 'left';
            ctx.fillText(`${(level * 100).toFixed(1)}% — $${price.toFixed(2)}`, xLeft + 4, y - 4);
        }

        ctx.globalAlpha = 1;
        ctx.setLineDash([]);

        // Fill between 0.382 and 0.618 (golden zone)
        const y382 = activeChart.candleSeries.priceToCoordinate(points[0].price + priceRange * 0.382);
        const y618 = activeChart.candleSeries.priceToCoordinate(points[0].price + priceRange * 0.618);
        if (y382 != null && y618 != null) {
            ctx.fillStyle = color;
            ctx.globalAlpha = 0.06;
            ctx.fillRect(xLeft, Math.min(y382, y618), xRight - xLeft, Math.abs(y618 - y382));
            ctx.globalAlpha = 1;
        }
    }

    function _drawRectangle(points, color) {
        if (points.length < 2) return;
        const p1 = _coordToPixel(points[0]);
        const p2 = _coordToPixel(points[1]);
        if (!p1 || !p2) return;

        const x = Math.min(p1.x, p2.x);
        const y = Math.min(p1.y, p2.y);
        const w = Math.abs(p2.x - p1.x);
        const h = Math.abs(p2.y - p1.y);

        ctx.fillStyle = COLORS.rect;
        ctx.fillRect(x, y, w, h);
        ctx.strokeStyle = color;
        ctx.lineWidth = 1;
        ctx.strokeRect(x, y, w, h);
    }

    // ── Parallel Channel ────────────────────────────────────────────────
    // points[0..1] are the base line; points[2] supplies a perpendicular
    // offset that the parallel line is drawn at.
    function _drawParallelChannel(points, color) {
        if (points.length < 2) return;
        const p1 = _coordToPixel(points[0]);
        const p2 = _coordToPixel(points[1]);
        if (!p1 || !p2) return;

        // Draw base line first.
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.setLineDash([]);
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();
        _drawHandle(p1.x, p1.y);
        _drawHandle(p2.x, p2.y);

        if (points.length < 3) return;
        const p3 = _coordToPixel(points[2]);
        if (!p3) return;

        // Project p3 onto the perpendicular of the base line through p1
        // to get the offset vector. We then translate p1/p2 by that vector.
        const vx = p2.x - p1.x;
        const vy = p2.y - p1.y;
        const len2 = vx * vx + vy * vy;
        if (len2 === 0) return;
        const wx = p3.x - p1.x;
        const wy = p3.y - p1.y;
        const t = (wx * vx + wy * vy) / len2;
        const projX = p1.x + t * vx;
        const projY = p1.y + t * vy;
        const offX = p3.x - projX;
        const offY = p3.y - projY;

        const p1b = { x: p1.x + offX, y: p1.y + offY };
        const p2b = { x: p2.x + offX, y: p2.y + offY };

        ctx.beginPath();
        ctx.moveTo(p1b.x, p1b.y);
        ctx.lineTo(p2b.x, p2b.y);
        ctx.stroke();
        _drawHandle(p1b.x, p1b.y);
        _drawHandle(p2b.x, p2b.y);

        // Light fill between the two parallel lines.
        ctx.fillStyle = COLORS.channelFill;
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.lineTo(p2b.x, p2b.y);
        ctx.lineTo(p1b.x, p1b.y);
        ctx.closePath();
        ctx.fill();
    }

    // ── Measure tool ────────────────────────────────────────────────────
    // Two-point ruler showing absolute price delta, % change, and bar count.
    function _drawMeasure(points, color) {
        if (points.length < 2) return;
        const p1 = _coordToPixel(points[0]);
        const p2 = _coordToPixel(points[1]);
        if (!p1 || !p2) return;

        const priceDelta = points[1].price - points[0].price;
        const pctDelta = points[0].price !== 0 ? (priceDelta / points[0].price) * 100 : 0;
        const isUp = priceDelta >= 0;
        const labelColor = isUp ? '#26a69a' : '#ef5350';

        // Translucent box covering the price range.
        const xLo = Math.min(p1.x, p2.x);
        const xHi = Math.max(p1.x, p2.x);
        const yLo = Math.min(p1.y, p2.y);
        const yHi = Math.max(p1.y, p2.y);
        ctx.fillStyle = isUp ? 'rgba(38, 166, 154, 0.10)' : 'rgba(239, 83, 80, 0.10)';
        ctx.fillRect(xLo, yLo, xHi - xLo, yHi - yLo);

        // Diagonal connector.
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.setLineDash([4, 3]);
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();
        ctx.setLineDash([]);

        _drawHandle(p1.x, p1.y);
        _drawHandle(p2.x, p2.y);

        // Bar count: best-effort using time delta in seconds against the
        // average bar interval in chartData. Falls back to "—" if unknown.
        const bars = _estimateBarCount(points[0].time, points[1].time);

        const lines = [
            `${isUp ? '▲' : '▼'} ${priceDelta >= 0 ? '+' : ''}${priceDelta.toFixed(2)}`,
            `${pctDelta >= 0 ? '+' : ''}${pctDelta.toFixed(2)}%`,
            bars != null ? `${bars} bars` : '',
        ].filter(Boolean);

        const boxX = (p1.x + p2.x) / 2 + 8;
        const boxY = (p1.y + p2.y) / 2 - 8;
        const boxW = 95;
        const boxH = lines.length * 14 + 6;

        ctx.fillStyle = 'rgba(19, 23, 34, 0.92)';
        ctx.strokeStyle = labelColor;
        ctx.lineWidth = 1;
        ctx.fillRect(boxX, boxY, boxW, boxH);
        ctx.strokeRect(boxX, boxY, boxW, boxH);

        ctx.fillStyle = labelColor;
        ctx.font = 'bold 11px Inter, sans-serif';
        ctx.textAlign = 'left';
        ctx.textBaseline = 'top';
        for (let i = 0; i < lines.length; i++) {
            ctx.fillText(lines[i], boxX + 6, boxY + 4 + i * 14);
        }
    }

    function _estimateBarCount(t1, t2) {
        const data = activeChart?.chartData;
        if (!data || data.length < 2) return null;
        const toSec = (t) => {
            if (typeof t === 'object' && t !== null && 'year' in t) {
                return new Date(t.year, t.month - 1, t.day).getTime() / 1000;
            }
            return Number(t);
        };
        const s1 = toSec(t1);
        const s2 = toSec(t2);
        if (!isFinite(s1) || !isFinite(s2)) return null;

        // Average bar interval from the first 10 candles.
        const samples = Math.min(10, data.length - 1);
        let sumGap = 0, n = 0;
        for (let i = 1; i <= samples; i++) {
            const ta = _toTime(data[i - 1].timestamp);
            const tb = _toTime(data[i].timestamp);
            const a = toSec(ta), b = toSec(tb);
            if (isFinite(a) && isFinite(b) && b > a) { sumGap += (b - a); n++; }
        }
        if (n === 0) return null;
        const avg = sumGap / n;
        return Math.max(0, Math.round(Math.abs(s2 - s1) / avg));
    }

    // ── Text Annotation ─────────────────────────────────────────────────
    function _drawTextAnnotation(point, label, color) {
        if (!point) return;
        const p = _coordToPixel(point);
        if (!p) return;

        // Marker dot.
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
        ctx.fill();

        // Connector + label box, anchored top-right of the marker.
        const text = label || '';
        ctx.font = 'bold 11px Inter, sans-serif';
        const metrics = ctx.measureText(text);
        const padX = 6, padY = 4;
        const boxW = metrics.width + padX * 2;
        const boxH = 16;
        const boxX = p.x + 10;
        const boxY = p.y - boxH - 6;

        ctx.strokeStyle = color;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(p.x, p.y);
        ctx.lineTo(boxX, boxY + boxH);
        ctx.stroke();

        ctx.fillStyle = 'rgba(19, 23, 34, 0.92)';
        ctx.fillRect(boxX, boxY, boxW, boxH);
        ctx.strokeRect(boxX, boxY, boxW, boxH);

        ctx.fillStyle = color;
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';
        ctx.fillText(text, boxX + padX, boxY + boxH / 2);
    }

    function _drawHandle(x, y) {
        ctx.fillStyle = COLORS.handle;
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = '#2962FF';
        ctx.lineWidth = 1.5;
        ctx.stroke();
    }

    // ── Canvas management ───────────────────────────────────────────────

    function _resizeCanvas() {
        if (!canvas || !canvas.parentElement) return;
        const rect = canvas.parentElement.getBoundingClientRect();
        canvas.width = rect.width * window.devicePixelRatio;
        canvas.height = rect.height * window.devicePixelRatio;
        ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
        canvas.style.width = rect.width + 'px';
        canvas.style.height = rect.height + 'px';
        _render();
    }

    // ── Persistence ─────────────────────────────────────────────────────

    function _saveDrawings() {
        if (!ticker) return;
        const serializable = drawings.map(d => ({
            type: d.type,
            points: d.points.map(p => ({ time: p.time, price: p.price })),
            color: d.color,
            id: d.id,
        }));
        localStorage.setItem(STORAGE_PREFIX + ticker, JSON.stringify(serializable));
    }

    function _loadDrawings() {
        if (!ticker) return [];
        try {
            return JSON.parse(localStorage.getItem(STORAGE_PREFIX + ticker)) || [];
        } catch { return []; }
    }

    function clearDrawings({ skipConfirm = false } = {}) {
        if (drawings.length === 0) return;
        if (!skipConfirm && !window.confirm(`Delete all ${drawings.length} drawing${drawings.length === 1 ? '' : 's'} on ${ticker}?`)) return;
        drawings = [];
        _saveDrawings();
        _render();
    }

    function undoLast() {
        if (drawings.length === 0) return;
        drawings.pop();
        _saveDrawings();
        _render();
    }

    // Duplicate the last drawing with a small offset so the copy is visible.
    // Offset is computed from the visible price/time range so it scales with
    // the chart instead of vanishing on zoomed-out views.
    function cloneLast() {
        if (drawings.length === 0 || !activeChart?.chart) return;
        const last = drawings[drawings.length - 1];

        const visiblePrice = activeChart.candleSeries.priceScale().getVisibleRange?.();
        const priceSpan = visiblePrice && isFinite(visiblePrice.from) && isFinite(visiblePrice.to)
            ? Math.abs(visiblePrice.to - visiblePrice.from)
            : Math.abs(last.points[0].price * 0.02);
        const priceOffset = priceSpan * 0.04;

        const visibleTime = activeChart.chart.timeScale().getVisibleRange?.();
        let timeOffsetSec = 0;
        if (visibleTime?.from && visibleTime?.to) {
            const toSec = (t) => typeof t === 'object' && 'year' in t
                ? new Date(t.year, t.month - 1, t.day).getTime() / 1000
                : Number(t);
            timeOffsetSec = (toSec(visibleTime.to) - toSec(visibleTime.from)) * 0.04;
        }

        const offsetTime = (t) => {
            if (typeof t === 'object' && 'year' in t) {
                const date = new Date(t.year, t.month - 1, t.day);
                date.setDate(date.getDate() + Math.max(1, Math.round(timeOffsetSec / 86400) || 1));
                return { year: date.getFullYear(), month: date.getMonth() + 1, day: date.getDate() };
            }
            return Number(t) + (timeOffsetSec || 60);
        };

        const cloned = {
            type: last.type,
            color: last.color,
            label: last.label,
            id: Date.now(),
            points: last.points.map(p => ({
                time: offsetTime(p.time),
                price: p.price + priceOffset,
            })),
        };
        drawings.push(cloned);
        _saveDrawings();
        _render();
    }

    // ── Toolbar ─────────────────────────────────────────────────────────

    function createToolbar(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        let toolbar = container.querySelector('.chart-drawing-toolbar');
        if (toolbar) toolbar.remove();

        toolbar = document.createElement('div');
        toolbar.className = 'chart-drawing-toolbar';
        toolbar.innerHTML = `
            <button class="draw-tool-btn" data-tool="trendline" title="Trendline (T) — hold Shift to snap to OHLC">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><line x1="4" y1="20" x2="20" y2="4"></line></svg>
            </button>
            <button class="draw-tool-btn" data-tool="hline" title="Horizontal Line (H)">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><line x1="2" y1="12" x2="22" y2="12"></line></svg>
            </button>
            <button class="draw-tool-btn" data-tool="fibonacci" title="Fibonacci Retracement (F)">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><line x1="2" y1="4" x2="22" y2="4"></line><line x1="2" y1="9" x2="22" y2="9"></line><line x1="2" y1="15" x2="22" y2="15"></line><line x1="2" y1="20" x2="22" y2="20"></line></svg>
            </button>
            <button class="draw-tool-btn" data-tool="rectangle" title="Rectangle (R)">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="5" width="18" height="14" rx="1"></rect></svg>
            </button>
            <button class="draw-tool-btn" data-tool="parallelChannel" title="Parallel Channel (P) — 3 clicks: 2 for base line, 1 for offset">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="18" x2="20" y2="6"></line><line x1="6" y1="22" x2="22" y2="11"></line></svg>
            </button>
            <button class="draw-tool-btn" data-tool="measure" title="Measure (M) — price Δ, % change, bar count">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 17l6-6 4 4 8-8"></path><polyline points="14 7 21 7 21 14"></polyline></svg>
            </button>
            <button class="draw-tool-btn" data-tool="text" title="Text Annotation (A)">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 7V5h16v2"></path><line x1="9" y1="20" x2="15" y2="20"></line><line x1="12" y1="5" x2="12" y2="20"></line></svg>
            </button>
            <div class="draw-tool-divider"></div>
            <button class="draw-tool-btn draw-tool-clone" data-action="clone" title="Clone Last Drawing (D)">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
            </button>
            <button class="draw-tool-btn draw-tool-undo" data-action="undo" title="Undo Last (Ctrl+Z)">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"></polyline><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path></svg>
            </button>
            <button class="draw-tool-btn draw-tool-clear" data-action="clear" title="Clear All Drawings">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6l-2 14H7L5 6"></path><path d="M10 11v6"></path><path d="M14 11v6"></path></svg>
            </button>
        `;

        // Position toolbar on left side of chart
        container.style.position = 'relative';
        container.insertBefore(toolbar, container.firstChild);

        // Event delegation
        toolbar.addEventListener('click', (e) => {
            const btn = e.target.closest('.draw-tool-btn');
            if (!btn) return;

            const tool = btn.dataset.tool;
            const action = btn.dataset.action;

            if (action === 'undo') { undoLast(); return; }
            if (action === 'clone') { cloneLast(); return; }
            if (action === 'clear') { clearDrawings(); return; }

            if (tool) {
                if (currentTool === tool) {
                    cancelTool();
                } else {
                    setTool(tool);
                }
            }
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;
            // Skip when a modifier other than ctrl-Z is held — Shift is the snap modifier.
            if (e.altKey || e.metaKey) return;
            switch (e.key.toLowerCase()) {
                case 't': if (!e.ctrlKey) setTool('trendline'); break;
                case 'h': if (!e.ctrlKey) setTool('hline'); break;
                case 'f': if (!e.ctrlKey) setTool('fibonacci'); break;
                case 'r': if (!e.ctrlKey) setTool('rectangle'); break;
                case 'p': if (!e.ctrlKey) setTool('parallelChannel'); break;
                case 'm': if (!e.ctrlKey) setTool('measure'); break;
                case 'a': if (!e.ctrlKey) setTool('text'); break;
                case 'd': if (!e.ctrlKey) cloneLast(); break;
                case 'z': if (e.ctrlKey) undoLast(); break;
            }
        });

        return toolbar;
    }

    function _updateToolbarState() {
        if (!canvas) return;
        const container = canvas.closest('[id]')?.parentElement;
        if (!container) return;

        container.querySelectorAll('.draw-tool-btn[data-tool]').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tool === currentTool);
        });
    }

    // ── Re-render on chart scroll/zoom ──────────────────────────────────

    function bindChartUpdates(chartInstance) {
        if (!chartInstance?.chart) return;

        chartInstance.chart.timeScale().subscribeVisibleLogicalRangeChange(() => {
            requestAnimationFrame(() => _render());
        });

        // Also re-render on crosshair moves (for smooth updates)
        chartInstance.chart.subscribeCrosshairMove(() => {
            if (drawings.length > 0) {
                requestAnimationFrame(() => _render());
            }
        });
    }

    // ── Destroy ─────────────────────────────────────────────────────────

    function destroy() {
        _unbindEvents();
        if (canvas) canvas.remove();
        canvas = null;
        ctx = null;
        activeChart = null;
        currentTool = null;
        drawState = null;
        drawings = [];
    }

    return {
        init, setTool, cancelTool, createToolbar,
        clearDrawings, undoLast, cloneLast, destroy, bindChartUpdates,
    };
})();

window.ChartDrawings = ChartDrawings;
