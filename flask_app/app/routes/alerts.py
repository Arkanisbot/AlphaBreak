"""
Smart Alerts Routes
===================
CRUD for user-defined rule-based alerts on price and indicators.
All routes require JWT auth and are per-user scoped.
"""

import logging
from flask import Blueprint, g, jsonify, request

from app import limiter
from app.services import alert_service
from app.utils.auth import log_request
from app.utils.database import db_manager, get_user_by_public_id
from app.utils.jwt_auth import require_jwt

logger = logging.getLogger(__name__)

alerts_bp = Blueprint('alerts', __name__)


def _get_user_id():
    user = get_user_by_public_id(g.user_id)
    return user['id'] if user else None


@alerts_bp.route('/alerts', methods=['GET'])
@limiter.limit("60/minute")
@log_request
@require_jwt
def list_alerts():
    user_id = _get_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 404
    rules = alert_service.list_rules(db_manager, user_id)
    return jsonify({
        'rules': rules,
        'count': len(rules),
        'limit': alert_service.MAX_RULES_PER_USER,
    })


@alerts_bp.route('/alerts', methods=['POST'])
@limiter.limit("30/minute")
@log_request
@require_jwt
def create_alert():
    user_id = _get_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 404

    payload = request.get_json(silent=True) or {}
    rule, err = alert_service.create_rule(db_manager, user_id, payload)
    if err:
        return jsonify({'error': err}), 400
    return jsonify({'rule': rule}), 201


@alerts_bp.route('/alerts/<int:rule_id>', methods=['PUT'])
@limiter.limit("30/minute")
@log_request
@require_jwt
def update_alert(rule_id):
    user_id = _get_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 404

    payload = request.get_json(silent=True) or {}
    rule, err = alert_service.update_rule(db_manager, rule_id, user_id, payload)
    if err:
        status = 404 if err == 'Rule not found' else 400
        return jsonify({'error': err}), status
    return jsonify({'rule': rule})


@alerts_bp.route('/alerts/<int:rule_id>', methods=['DELETE'])
@limiter.limit("30/minute")
@log_request
@require_jwt
def delete_alert(rule_id):
    user_id = _get_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 404
    if not alert_service.delete_rule(db_manager, rule_id, user_id):
        return jsonify({'error': 'Rule not found'}), 404
    return jsonify({'success': True})


@alerts_bp.route('/alerts/<int:rule_id>/toggle', methods=['POST'])
@limiter.limit("60/minute")
@log_request
@require_jwt
def toggle_alert(rule_id):
    user_id = _get_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 404

    payload = request.get_json(silent=True) or {}
    is_active = payload.get('is_active')
    if is_active is None:
        return jsonify({'error': 'is_active required'}), 400

    if not alert_service.toggle_rule(db_manager, rule_id, user_id, is_active):
        return jsonify({'error': 'Rule not found'}), 404
    return jsonify({'success': True, 'is_active': bool(is_active)})


@alerts_bp.route('/alerts/firings', methods=['GET'])
@limiter.limit("30/minute")
@log_request
@require_jwt
def list_firings():
    user_id = _get_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 404

    rule_id = request.args.get('rule_id', type=int)
    limit = request.args.get('limit', 50, type=int)
    firings = alert_service.list_firings(db_manager, user_id, rule_id=rule_id, limit=limit)
    return jsonify({'firings': firings, 'count': len(firings)})


@alerts_bp.route('/alerts/fields', methods=['GET'])
@log_request
def list_fields():
    """Public metadata — used by the frontend to populate the condition dropdown."""
    return jsonify({
        'fields': [
            {'key': k, 'label': alert_service.FIELD_LABELS.get(k, k)}
            for k in sorted(alert_service.ALLOWED_FIELDS)
        ],
        'operators': sorted(alert_service.ALLOWED_OPS),
        'cooldowns': [
            {'seconds': 3600, 'label': '1 hour'},
            {'seconds': 14400, 'label': '4 hours'},
            {'seconds': 86400, 'label': '1 day'},
            {'seconds': 0, 'label': 'Until I reset it'},
        ],
        'max_rules': alert_service.MAX_RULES_PER_USER,
        'max_conditions': alert_service.MAX_CONDITIONS_PER_RULE,
    })
