/**
 * Smart Alerts
 * ============
 * Rule-based price/indicator alerts. UI lives in the Account > Smart Alerts
 * sub-tab and is also launched from the Security Analysis chart toolbar.
 *
 * Reuses:
 *   - apiRequest(endpoint, method, body)  — app.js
 *   - showSnackbar(msg, type)             — app.js
 *   - .modal-overlay / .modal-content     — styles.css
 *   - .toggle switch                      — styles.css
 */
const Alerts = (() => {
    const state = {
        rules: [],
        firings: [],
        metadata: null,  // {fields, operators, cooldowns, max_rules, max_conditions}
        editingRuleId: null,
    };

    // ── Metadata (loaded once) ─────────────────────────────────────────────
    async function loadMetadata() {
        if (state.metadata) return state.metadata;
        try {
            const res = await apiRequest('/api/alerts/fields');
            if (res.ok) state.metadata = await res.json();
        } catch (e) {
            console.error('Alerts: loadMetadata failed', e);
        }
        return state.metadata;
    }

    // ── List rules + firings ───────────────────────────────────────────────
    async function loadList() {
        await loadMetadata();
        const container = document.getElementById('accountSection-alerts');
        if (!container) return;

        container.innerHTML = `
            <div class="alerts-header">
                <div>
                    <h3 style="margin:0;">Smart Alerts</h3>
                    <p style="color:#888;margin:4px 0 0;font-size:13px;">
                        Get notified when price or indicators hit your conditions.
                        Up to ${(state.metadata && state.metadata.max_rules) || 10} rules per account.
                    </p>
                </div>
                <button class="btn btn-primary" id="newAlertBtn">+ New Alert</button>
            </div>
            <div id="alertsList" class="alerts-list">
                <div style="color:#888;padding:20px;">Loading…</div>
            </div>
            <div class="widget-card" style="margin-top:20px;">
                <div class="widget-header">
                    <h4 style="margin:0;">Recent Firings</h4>
                </div>
                <div id="alertsFirings" class="alerts-firings"></div>
            </div>
        `;
        document.getElementById('newAlertBtn').addEventListener('click', () => openCreateModal());

        try {
            const [rulesRes, firingsRes] = await Promise.all([
                apiRequest('/api/alerts'),
                apiRequest('/api/alerts/firings?limit=20'),
            ]);
            if (rulesRes.ok) {
                const data = await rulesRes.json();
                state.rules = data.rules || [];
                renderRules();
            }
            if (firingsRes.ok) {
                const data = await firingsRes.json();
                state.firings = data.firings || [];
                renderFirings();
            }
        } catch (e) {
            console.error('Alerts: loadList failed', e);
            showSnackbar('Failed to load alerts', 'error');
        }
    }

    function renderRules() {
        const list = document.getElementById('alertsList');
        if (!list) return;

        if (state.rules.length === 0) {
            list.innerHTML = `
                <div class="empty-state empty-state--fill" style="padding:40px 20px;text-align:center;">
                    <p style="color:#888;">No alerts yet. Create one to get notified when your conditions fire.</p>
                </div>
            `;
            return;
        }

        list.innerHTML = state.rules.map(renderRuleRow).join('');
        list.querySelectorAll('[data-action]').forEach(btn => {
            btn.addEventListener('click', handleRuleAction);
        });
    }

    function renderRuleRow(rule) {
        const conds = (rule.conditions || []).map(c => {
            const label = fieldLabel(c.field);
            return `${label} ${c.op} ${c.value}`;
        }).join(' AND ');
        const last = rule.last_triggered_at
            ? `Last fired: ${new Date(rule.last_triggered_at).toLocaleString()}`
            : 'Never fired';
        const statusClass = rule.is_active ? 'active' : 'inactive';
        return `
            <div class="alert-rule alert-rule--${statusClass}" data-rule-id="${rule.id}">
                <div class="alert-rule__main">
                    <div class="alert-rule__name">
                        <strong>${escapeHtml(rule.name)}</strong>
                        <span class="alert-rule__ticker">${escapeHtml(rule.ticker)}</span>
                    </div>
                    <div class="alert-rule__conditions">${escapeHtml(conds)}</div>
                    <div class="alert-rule__meta">${last}</div>
                </div>
                <div class="alert-rule__actions">
                    <label class="toggle">
                        <input type="checkbox" data-action="toggle" data-rule-id="${rule.id}" ${rule.is_active ? 'checked' : ''}>
                        <span class="toggle-slider"></span>
                    </label>
                    <button class="btn btn-sm" data-action="edit" data-rule-id="${rule.id}">Edit</button>
                    <button class="btn btn-sm btn-danger" data-action="delete" data-rule-id="${rule.id}">Delete</button>
                </div>
            </div>
        `;
    }

    function renderFirings() {
        const el = document.getElementById('alertsFirings');
        if (!el) return;
        if (state.firings.length === 0) {
            el.innerHTML = '<div style="color:#888;padding:16px;">No firings yet.</div>';
            return;
        }
        el.innerHTML = `
            <table class="alerts-firings-table">
                <thead>
                    <tr><th>Rule</th><th>Ticker</th><th>When</th><th>Matched</th></tr>
                </thead>
                <tbody>
                ${state.firings.map(f => `
                    <tr>
                        <td>${escapeHtml(f.rule_name)}</td>
                        <td>${escapeHtml(f.ticker)}</td>
                        <td>${new Date(f.fired_at).toLocaleString()}</td>
                        <td>${escapeHtml(JSON.stringify(f.matched_values))}</td>
                    </tr>
                `).join('')}
                </tbody>
            </table>
        `;
    }

    // ── Actions ────────────────────────────────────────────────────────────
    async function handleRuleAction(e) {
        const action = e.currentTarget.dataset.action;
        const ruleId = parseInt(e.currentTarget.dataset.ruleId, 10);
        const rule = state.rules.find(r => r.id === ruleId);
        if (!rule) return;

        if (action === 'toggle') {
            const isActive = e.currentTarget.checked;
            try {
                const res = await apiRequest(`/api/alerts/${ruleId}/toggle`, 'POST', { is_active: isActive });
                if (res.ok) {
                    rule.is_active = isActive;
                    showSnackbar(`Alert ${isActive ? 'enabled' : 'paused'}`, 'success');
                    renderRules();
                } else {
                    e.currentTarget.checked = !isActive;
                    showSnackbar('Failed to toggle alert', 'error');
                }
            } catch (err) {
                e.currentTarget.checked = !isActive;
                showSnackbar('Network error', 'error');
            }
        } else if (action === 'edit') {
            openCreateModal(rule.ticker, rule);
        } else if (action === 'delete') {
            if (!confirm(`Delete alert "${rule.name}"?`)) return;
            try {
                const res = await apiRequest(`/api/alerts/${ruleId}`, 'DELETE');
                if (res.ok) {
                    state.rules = state.rules.filter(r => r.id !== ruleId);
                    renderRules();
                    showSnackbar('Alert deleted', 'success');
                } else {
                    showSnackbar('Failed to delete alert', 'error');
                }
            } catch (err) {
                showSnackbar('Network error', 'error');
            }
        }
    }

    // ── Create / Edit modal ────────────────────────────────────────────────
    async function openCreateModal(prefillTicker, existingRule) {
        await loadMetadata();
        if (!state.metadata) {
            showSnackbar('Alerts unavailable', 'error');
            return;
        }
        state.editingRuleId = existingRule ? existingRule.id : null;

        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.id = 'alertModalOverlay';
        overlay.innerHTML = `
            <div class="modal-content" style="max-width:560px;">
                <div class="modal-header">
                    <h3 style="margin:0;">${existingRule ? 'Edit' : 'New'} Smart Alert</h3>
                    <button class="modal-close" type="button">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="alertForm">
                        <div style="margin-bottom:12px;">
                            <label>Name</label>
                            <input type="text" id="alertName" class="profile-input" maxlength="120"
                                   placeholder="e.g. AAPL oversold" required>
                        </div>
                        <div style="margin-bottom:12px;">
                            <label>Ticker</label>
                            <input type="text" id="alertTicker" class="profile-input"
                                   placeholder="AAPL" maxlength="12" required
                                   style="text-transform:uppercase;">
                        </div>
                        <div style="margin-bottom:12px;">
                            <label>Conditions (all must be true)</label>
                            <div id="alertConditions"></div>
                            <button type="button" id="addConditionBtn" class="btn btn-sm"
                                    style="margin-top:8px;">+ Add condition</button>
                        </div>
                        <div style="margin-bottom:12px;">
                            <label>Cooldown</label>
                            <select id="alertCooldown" class="profile-input">
                                ${state.metadata.cooldowns.map(c =>
                                    `<option value="${c.seconds}">${c.label}</option>`
                                ).join('')}
                            </select>
                        </div>
                        <div style="display:flex;gap:20px;margin-bottom:16px;">
                            <label style="display:flex;align-items:center;gap:8px;">
                                <input type="checkbox" id="alertEmail" checked> Email
                            </label>
                            <label style="display:flex;align-items:center;gap:8px;">
                                <input type="checkbox" id="alertInApp" checked> In-app
                            </label>
                        </div>
                        <div class="auth-error" id="alertError" style="color:#f66;margin-bottom:8px;"></div>
                        <div style="display:flex;gap:8px;justify-content:flex-end;">
                            <button type="button" class="btn" id="alertCancelBtn">Cancel</button>
                            <button type="submit" class="btn btn-primary">
                                ${existingRule ? 'Save changes' : 'Create alert'}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);

        const closeModal = () => overlay.remove();
        overlay.querySelector('.modal-close').addEventListener('click', closeModal);
        overlay.querySelector('#alertCancelBtn').addEventListener('click', closeModal);
        overlay.addEventListener('click', (e) => { if (e.target === overlay) closeModal(); });

        const conditionsEl = overlay.querySelector('#alertConditions');
        const addConditionBtn = overlay.querySelector('#addConditionBtn');

        function renderConditionRow(existing) {
            if (conditionsEl.children.length >= state.metadata.max_conditions) {
                showSnackbar(`Max ${state.metadata.max_conditions} conditions`, 'warning');
                return;
            }
            const row = document.createElement('div');
            row.className = 'alert-condition-row';
            row.innerHTML = `
                <select class="profile-input alert-field">
                    ${state.metadata.fields.map(f =>
                        `<option value="${f.key}" ${existing && existing.field === f.key ? 'selected' : ''}>${f.label}</option>`
                    ).join('')}
                </select>
                <select class="profile-input alert-op">
                    ${state.metadata.operators.map(op =>
                        `<option value="${op}" ${existing && existing.op === op ? 'selected' : ''}>${op}</option>`
                    ).join('')}
                </select>
                <input type="number" step="any" class="profile-input alert-value"
                       value="${existing ? existing.value : ''}" placeholder="value" required>
                <button type="button" class="btn btn-sm btn-danger alert-remove-cond">&times;</button>
            `;
            row.querySelector('.alert-remove-cond').addEventListener('click', () => {
                if (conditionsEl.children.length > 1) row.remove();
            });
            conditionsEl.appendChild(row);
        }

        addConditionBtn.addEventListener('click', () => renderConditionRow());

        // Prefill
        if (existingRule) {
            overlay.querySelector('#alertName').value = existingRule.name;
            overlay.querySelector('#alertTicker').value = existingRule.ticker;
            overlay.querySelector('#alertCooldown').value = existingRule.cooldown_seconds;
            overlay.querySelector('#alertEmail').checked = existingRule.email_enabled;
            overlay.querySelector('#alertInApp').checked = existingRule.in_app_enabled;
            (existingRule.conditions || []).forEach(c => renderConditionRow(c));
        } else {
            overlay.querySelector('#alertCooldown').value = 86400;
            if (prefillTicker) overlay.querySelector('#alertTicker').value = prefillTicker;
            renderConditionRow();
        }

        overlay.querySelector('#alertForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const errEl = overlay.querySelector('#alertError');
            errEl.textContent = '';

            const conditions = [];
            overlay.querySelectorAll('.alert-condition-row').forEach(row => {
                const field = row.querySelector('.alert-field').value;
                const op = row.querySelector('.alert-op').value;
                const value = parseFloat(row.querySelector('.alert-value').value);
                if (!isNaN(value)) conditions.push({ field, op, value });
            });
            if (conditions.length === 0) {
                errEl.textContent = 'At least one condition required';
                return;
            }

            const payload = {
                name: overlay.querySelector('#alertName').value.trim(),
                ticker: overlay.querySelector('#alertTicker').value.trim().toUpperCase(),
                conditions,
                cooldown_seconds: parseInt(overlay.querySelector('#alertCooldown').value, 10),
                email_enabled: overlay.querySelector('#alertEmail').checked,
                in_app_enabled: overlay.querySelector('#alertInApp').checked,
                is_active: true,
            };

            try {
                const url = existingRule ? `/api/alerts/${existingRule.id}` : '/api/alerts';
                const method = existingRule ? 'PUT' : 'POST';
                const res = await apiRequest(url, method, payload);
                const data = await res.json();
                if (!res.ok) {
                    errEl.textContent = data.error || 'Failed to save';
                    return;
                }
                showSnackbar(existingRule ? 'Alert updated' : 'Alert created', 'success');
                closeModal();
                loadList();
            } catch (err) {
                errEl.textContent = 'Network error';
            }
        });
    }

    // ── Helpers ────────────────────────────────────────────────────────────
    function fieldLabel(key) {
        if (!state.metadata) return key;
        const f = state.metadata.fields.find(x => x.key === key);
        return f ? f.label : key;
    }

    function escapeHtml(s) {
        if (s == null) return '';
        return String(s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
    }

    return { loadList, openCreateModal };
})();

window.Alerts = Alerts;
