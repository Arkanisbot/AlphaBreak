// ============================================================================
// AlphaBreak Achievements — Streak tracking + badges
// ============================================================================
// Tracks user activity in localStorage and awards badges for milestones.
// All data is client-side — no API calls. Streaks are calculated from
// recorded activity dates; badges are earned by hitting thresholds.
//
// Call Achievements.recordLogin() on each authenticated session start.
// Call Achievements.recordAnalysis() each time a ticker is analyzed.
// Call Achievements.recordJournal() each time a journal entry is created.
// Call Achievements.render() when the Achievements sub-tab is shown.
// ============================================================================

const Achievements = (() => {

    const STORAGE_KEY = 'alphabreak_achievements';

    // ── Badge definitions ───────────────────────────────────────────
    // Each badge has a test function that receives the stats object.
    const BADGES = [
        // Login streaks
        { id: 'login_3',    icon: '🔥', name: 'Warming Up',       desc: '3-day login streak',          test: s => s.loginStreak >= 3 },
        { id: 'login_7',    icon: '🔥', name: 'On Fire',          desc: '7-day login streak',          test: s => s.loginStreak >= 7 },
        { id: 'login_30',   icon: '🏆', name: 'Iron Discipline',  desc: '30-day login streak',         test: s => s.loginStreak >= 30 },
        // Analysis milestones
        { id: 'analyze_1',  icon: '🔍', name: 'First Look',       desc: 'Analyzed your first ticker',  test: s => s.totalAnalyses >= 1 },
        { id: 'analyze_10', icon: '🔍', name: 'Market Scout',     desc: '10 tickers analyzed',         test: s => s.totalAnalyses >= 10 },
        { id: 'analyze_50', icon: '📊', name: 'Research Machine',  desc: '50 tickers analyzed',         test: s => s.totalAnalyses >= 50 },
        { id: 'analyze_100',icon: '🧠', name: 'Deep Diver',       desc: '100 tickers analyzed',        test: s => s.totalAnalyses >= 100 },
        // Journal milestones
        { id: 'journal_1',  icon: '📝', name: 'First Entry',      desc: 'Created first journal entry', test: s => s.totalJournals >= 1 },
        { id: 'journal_10', icon: '📝', name: 'Consistent Logger', desc: '10 journal entries',          test: s => s.totalJournals >= 10 },
        { id: 'journal_50', icon: '📖', name: 'Trade Historian',   desc: '50 journal entries',          test: s => s.totalJournals >= 50 },
        // Journal streaks
        { id: 'jstreak_3',  icon: '✏️',  name: 'Journal Habit',    desc: '3-day journaling streak',     test: s => s.journalStreak >= 3 },
        { id: 'jstreak_7',  icon: '✏️',  name: 'Disciplined Trader',desc: '7-day journaling streak',    test: s => s.journalStreak >= 7 },
        // Unique tickers
        { id: 'tickers_5',  icon: '🌐', name: 'Diversified',      desc: 'Analyzed 5 unique tickers',   test: s => s.uniqueTickers >= 5 },
        { id: 'tickers_20', icon: '🌐', name: 'Sector Scanner',   desc: 'Analyzed 20 unique tickers',  test: s => s.uniqueTickers >= 20 },
    ];

    // ── Data persistence ────────────────────────────────────────────

    function _load() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            return raw ? JSON.parse(raw) : _defaults();
        } catch (e) { return _defaults(); }
    }

    function _save(data) {
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(data)); } catch (e) {}
    }

    function _defaults() {
        return {
            loginDates: [],       // ISO date strings of login days
            analysisDates: [],    // ISO date strings of analysis days
            journalDates: [],     // ISO date strings of journal days
            totalAnalyses: 0,
            totalJournals: 0,
            uniqueTickers: 0,
            tickerSet: [],        // Array of unique tickers analyzed
            earnedBadges: [],     // Badge IDs earned (with timestamp)
        };
    }

    function _today() {
        return new Date().toISOString().slice(0, 10);
    }

    function _calcStreak(dates) {
        if (!dates.length) return 0;
        const sorted = [...new Set(dates)].sort().reverse();
        const today = _today();
        // Must include today or yesterday to have an active streak
        if (sorted[0] !== today) {
            const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
            if (sorted[0] !== yesterday) return 0;
        }
        let streak = 1;
        for (let i = 0; i < sorted.length - 1; i++) {
            const curr = new Date(sorted[i]);
            const prev = new Date(sorted[i + 1]);
            const diff = (curr - prev) / 86400000;
            if (diff === 1) streak++;
            else break;
        }
        return streak;
    }

    function _addDate(arr, date) {
        if (!arr.includes(date)) {
            arr.push(date);
            // Keep last 365 days only
            if (arr.length > 365) arr.shift();
        }
    }

    // ── Stats computation ───────────────────────────────────────────

    function _computeStats(data) {
        return {
            loginStreak: _calcStreak(data.loginDates),
            analysisStreak: _calcStreak(data.analysisDates),
            journalStreak: _calcStreak(data.journalDates),
            totalAnalyses: data.totalAnalyses || 0,
            totalJournals: data.totalJournals || 0,
            uniqueTickers: (data.tickerSet || []).length,
            loginDays: (data.loginDates || []).length,
        };
    }

    function _checkNewBadges(data) {
        const stats = _computeStats(data);
        const earned = data.earnedBadges || [];
        const earnedIds = new Set(earned.map(b => b.id));
        let newBadges = [];

        for (const badge of BADGES) {
            if (!earnedIds.has(badge.id) && badge.test(stats)) {
                const entry = { id: badge.id, earnedAt: new Date().toISOString() };
                earned.push(entry);
                newBadges.push(badge);
            }
        }

        data.earnedBadges = earned;
        return newBadges;
    }

    // ── Public recording methods ────────────────────────────────────

    function recordLogin() {
        const data = _load();
        _addDate(data.loginDates, _today());
        const newBadges = _checkNewBadges(data);
        _save(data);
        if (newBadges.length && typeof showSnackbar === 'function') {
            showSnackbar(`Badge earned: ${newBadges[0].name}!`, 'success');
        }
    }

    function recordAnalysis(ticker) {
        const data = _load();
        _addDate(data.analysisDates, _today());
        data.totalAnalyses = (data.totalAnalyses || 0) + 1;
        if (ticker) {
            const t = ticker.toUpperCase();
            if (!data.tickerSet) data.tickerSet = [];
            if (!data.tickerSet.includes(t)) data.tickerSet.push(t);
        }
        const newBadges = _checkNewBadges(data);
        _save(data);
        if (newBadges.length && typeof showSnackbar === 'function') {
            showSnackbar(`Badge earned: ${newBadges[0].name}!`, 'success');
        }
    }

    function recordJournal() {
        const data = _load();
        _addDate(data.journalDates, _today());
        data.totalJournals = (data.totalJournals || 0) + 1;
        const newBadges = _checkNewBadges(data);
        _save(data);
        if (newBadges.length && typeof showSnackbar === 'function') {
            showSnackbar(`Badge earned: ${newBadges[0].name}!`, 'success');
        }
    }

    // ── Rendering ───────────────────────────────────────────────────

    function render() {
        const data = _load();
        const stats = _computeStats(data);
        const earnedIds = new Set((data.earnedBadges || []).map(b => b.id));

        // Badges grid
        const grid = document.getElementById('achievementsBadges');
        if (grid) {
            grid.innerHTML = BADGES.map(badge => {
                const earned = earnedIds.has(badge.id);
                return `
                    <div class="achievement-badge ${earned ? 'earned' : 'locked'}" title="${badge.desc}">
                        <span class="achievement-icon">${badge.icon}</span>
                        <span class="achievement-name">${badge.name}</span>
                        <span class="achievement-desc">${badge.desc}</span>
                    </div>
                `;
            }).join('');
        }

        // Streaks display
        const streaks = document.getElementById('achievementsStreaks');
        if (streaks) {
            streaks.innerHTML = `
                <div class="streak-row">
                    <span class="streak-label">Login Streak</span>
                    <span class="streak-value">${stats.loginStreak} day${stats.loginStreak !== 1 ? 's' : ''}</span>
                    <span class="streak-bar" style="width:${Math.min(stats.loginStreak / 30 * 100, 100)}%"></span>
                </div>
                <div class="streak-row">
                    <span class="streak-label">Journal Streak</span>
                    <span class="streak-value">${stats.journalStreak} day${stats.journalStreak !== 1 ? 's' : ''}</span>
                    <span class="streak-bar" style="width:${Math.min(stats.journalStreak / 7 * 100, 100)}%"></span>
                </div>
                <div class="streak-stats">
                    <div><strong>${stats.totalAnalyses}</strong><br><span class="muted-text">Analyses</span></div>
                    <div><strong>${stats.uniqueTickers}</strong><br><span class="muted-text">Tickers</span></div>
                    <div><strong>${stats.totalJournals}</strong><br><span class="muted-text">Journals</span></div>
                    <div><strong>${stats.loginDays}</strong><br><span class="muted-text">Days Active</span></div>
                </div>
            `;
        }
    }

    return { recordLogin, recordAnalysis, recordJournal, render, BADGES };
})();

window.Achievements = Achievements;
