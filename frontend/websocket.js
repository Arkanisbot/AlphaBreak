// AlphaBreak — WebSocket Client
// Real-time data streaming via Socket.IO

const AlphaSocket = (() => {
    let socket = null;
    let _alertCallback = null;
    const _tickerCallbacks = {};  // ticker -> callback

    /**
     * Connect to the SocketIO server.
     * Sends JWT token (if available) as a query parameter for authentication.
     */
    function connect() {
        if (socket && socket.connected) return;

        const token = localStorage.getItem('authToken') || '';
        const opts = {
            transports: ['websocket', 'polling'],
            reconnection: true,
            reconnectionAttempts: Infinity,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 10000,
        };
        if (token) {
            opts.query = { token };
        }

        // Connect to same origin (works in dev and prod)
        socket = io(opts);

        socket.on('connect', () => {
            if (window.DEBUG) console.log('[AlphaSocket] connected, sid:', socket.id);
            _setStatus(true);

            // Re-subscribe to any active tickers after reconnect
            Object.keys(_tickerCallbacks).forEach(ticker => {
                socket.emit('subscribe_ticker', { ticker });
            });
        });

        socket.on('disconnect', (reason) => {
            if (window.DEBUG) console.log('[AlphaSocket] disconnected:', reason);
            _setStatus(false);
        });

        socket.on('connect_error', (err) => {
            console.warn('[AlphaSocket] connect_error:', err.message);
            _setStatus(false);
        });

        // Price updates routed to the per-ticker callback
        socket.on('price_update', (data) => {
            const cb = _tickerCallbacks[data.ticker];
            if (cb) cb(data);
        });

        // Trade-signal alerts
        socket.on('alert', (data) => {
            if (_alertCallback) _alertCallback(data);
        });
    }

    /**
     * Subscribe to real-time price updates for a ticker.
     * @param {string}   ticker   - e.g. 'AAPL'
     * @param {function} callback - called with { ticker, price, change, change_pct, volume, timestamp }
     */
    function subscribeTicker(ticker, callback) {
        ticker = ticker.toUpperCase();
        _tickerCallbacks[ticker] = callback;
        if (socket && socket.connected) {
            socket.emit('subscribe_ticker', { ticker });
        }
    }

    /**
     * Unsubscribe from a ticker room.
     * @param {string} ticker
     */
    function unsubscribeTicker(ticker) {
        ticker = ticker.toUpperCase();
        delete _tickerCallbacks[ticker];
        if (socket && socket.connected) {
            socket.emit('unsubscribe_ticker', { ticker });
        }
    }

    /**
     * Listen for trade-signal alerts.
     * @param {function} callback - called with alert data object
     */
    function onAlert(callback) {
        _alertCallback = callback;
        if (socket && socket.connected) {
            socket.emit('subscribe_alerts', {});
        }
    }

    /**
     * Update the connection status indicator in the header.
     * @param {boolean} connected
     */
    function _setStatus(connected) {
        const dot = document.getElementById('wsStatusDot');
        if (!dot) return;
        dot.classList.toggle('ws-connected', connected);
        dot.classList.toggle('ws-disconnected', !connected);
        dot.title = connected ? 'Live connection active' : 'Disconnected — reconnecting...';
    }

    /**
     * Check if the socket is currently connected.
     * @returns {boolean}
     */
    function isConnected() {
        return !!(socket && socket.connected);
    }

    return { connect, subscribeTicker, unsubscribeTicker, onAlert, isConnected };
})();

// Auto-connect when the page loads
document.addEventListener('DOMContentLoaded', () => AlphaSocket.connect());
