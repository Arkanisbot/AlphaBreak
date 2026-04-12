// ============================================================================
// AlphaBreak Chart Drawing Tools — Canvas overlay for user annotations
// ============================================================================
// Supports: Trendline, Horizontal Line, Fibonacci Retracement, Rectangle
// Drawings are saved per ticker in localStorage.

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

    const TOOLS = {
        trendline: { cursor: 'crosshair', points: 2, label: 'Trendline' },
        hline: { cursor: 'crosshair', points: 1, label: 'Horizontal Line' },
        fibonacci: { cursor: 'crosshair', points: 2, label: 'Fibonacci' },
        rectangle: { cursor: 'crosshair', points: 2, label: 'Rectangle' },
    };

    const COLORS = {
        line: '#2962FF',
        hline: '#FF6D00',
        fib: '#AB47BC',
        rect: 'rgba(41, 98, 255, 0.15)',
        rectBorder: '#2962FF',
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

    function _bindEvents() {
        _unbindEvents();

        _boundClick = (e) => _handleClick(e);
        _boundMove = (e) => _handleMove(e);
        _boundKey = (e) => { if (e.key === 'Escape') cancelTool(); };

        canvas.addEventListener('click', _boundClick);
        canvas.addEventListener('mousemove', _boundMove);
        document.addEventListener('keydown', _boundKey);
    }

    function _unbindEvents() {
        if (_boundClick && canvas) canvas.removeEventListener('click', _boundClick);
        if (_boundMove && canvas) canvas.removeEventListener('mousemove', _boundMove);
        if (_boundKey) document.removeEventListener('keydown', _boundKey);
    }

    function _handleClick(e) {
        if (!currentTool || !activeChart || !drawState) return;

        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // Convert pixel to price/time coordinates
        const coord = _pixelToCoord(x, y);
        if (!coord) return;

        drawState.points.push(coord);
        drawState.phase++;

        const needed = TOOLS[currentTool].points;
        if (drawState.phase >= needed) {
            // Drawing complete
            const drawing = {
                type: currentTool,
                points: drawState.points,
                color: COLORS[currentTool === 'trendline' ? 'line' : currentTool === 'hline' ? 'hline' : currentTool === 'fibonacci' ? 'fib' : 'rectBorder'],
                id: Date.now(),
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
            const coord = _pixelToCoord(x, y);
            if (coord) {
                _render();
                _drawPreview(drawState.points[0], coord);
            }
        }
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
        }
    }

    function _drawPreview(startCoord, endCoord) {
        const color = 'rgba(41, 98, 255, 0.6)';

        switch (currentTool) {
            case 'trendline': _drawLine([startCoord, endCoord], color, 2); break;
            case 'fibonacci': _drawFibonacci([startCoord, endCoord], color); break;
            case 'rectangle': _drawRectangle([startCoord, endCoord], color); break;
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

    function clearDrawings() {
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

    // ── Toolbar ─────────────────────────────────────────────────────────

    function createToolbar(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        let toolbar = container.querySelector('.chart-drawing-toolbar');
        if (toolbar) toolbar.remove();

        toolbar = document.createElement('div');
        toolbar.className = 'chart-drawing-toolbar';
        toolbar.innerHTML = `
            <button class="draw-tool-btn" data-tool="trendline" title="Draw Trendline (T)">
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
            <div class="draw-tool-divider"></div>
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
            switch (e.key.toLowerCase()) {
                case 't': setTool('trendline'); break;
                case 'h': if (!e.ctrlKey) setTool('hline'); break;
                case 'f': if (!e.ctrlKey) setTool('fibonacci'); break;
                case 'r': if (!e.ctrlKey) setTool('rectangle'); break;
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
        clearDrawings, undoLast, destroy, bindChartUpdates,
    };
})();

window.ChartDrawings = ChartDrawings;
