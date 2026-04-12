#!/bin/bash
# ================================================================
# AlphaBreak Health Check Script
# ================================================================
# External uptime monitor for https://alphabreak.vip
# Checks the /api/health endpoint; logs results and optionally
# sends Slack or AWS SES email notifications on failure.
#
# Install (cron every 5 minutes):
#   crontab -e
#   */5 * * * * /home/ubuntu/Securities_prediction_model/kubernetes/scripts/health-check.sh
#
# Optional environment variables:
#   SLACK_WEBHOOK_URL   — Slack incoming webhook URL for failure alerts
#   SES_ALERT_FROM      — SES verified sender email  (e.g. alerts@alphabreak.vip)
#   SES_ALERT_TO        — Recipient email address
#   AWS_DEFAULT_REGION   — AWS region for SES (default: us-east-2)
#
# Exit codes:
#   0 — healthy
#   1 — unhealthy (non-200 or timeout)
# ================================================================

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────
HEALTH_URL="https://alphabreak.vip/api/health"
TIMEOUT=10
LOG_FILE="/var/log/alphabreak-health.log"
TIMESTAMP=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

# ── Ensure log directory exists ──────────────────────────────────
LOG_DIR=$(dirname "$LOG_FILE")
if [ ! -d "$LOG_DIR" ]; then
    mkdir -p "$LOG_DIR" 2>/dev/null || true
fi

# ── Perform health check ────────────────────────────────────────
HTTP_CODE=0
RESPONSE=""
CURL_EXIT=0

RESPONSE=$(curl -s -o /dev/null -w "%{http_code}|%{time_total}" \
    --max-time "$TIMEOUT" \
    "$HEALTH_URL" 2>&1) || CURL_EXIT=$?

if [ "$CURL_EXIT" -ne 0 ]; then
    HTTP_CODE=0
    RESP_TIME="timeout"
else
    HTTP_CODE=$(echo "$RESPONSE" | cut -d'|' -f1)
    RESP_TIME=$(echo "$RESPONSE" | cut -d'|' -f2)
fi

# ── Evaluate result ─────────────────────────────────────────────
if [ "$HTTP_CODE" = "200" ]; then
    STATUS="HEALTHY"
    EXIT_CODE=0
else
    STATUS="UNHEALTHY"
    EXIT_CODE=1
fi

# ── Log ─────────────────────────────────────────────────────────
LOG_LINE="$TIMESTAMP | $STATUS | http=$HTTP_CODE | time=${RESP_TIME}s"
echo "$LOG_LINE" >> "$LOG_FILE" 2>/dev/null || echo "$LOG_LINE" >&2

# ── Notifications (only on failure) ─────────────────────────────
if [ "$STATUS" = "UNHEALTHY" ]; then
    ALERT_MSG="AlphaBreak HEALTH CHECK FAILED\nTime: $TIMESTAMP\nHTTP Code: $HTTP_CODE\nResponse Time: ${RESP_TIME}s\nURL: $HEALTH_URL"

    # Slack webhook
    if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
        PAYLOAD=$(printf '{"text":"%s"}' "$(echo -e "$ALERT_MSG" | sed 's/"/\\"/g')")
        curl -s -X POST -H 'Content-Type: application/json' \
            -d "$PAYLOAD" \
            "$SLACK_WEBHOOK_URL" >/dev/null 2>&1 || true
    fi

    # AWS SES email
    if [ -n "${SES_ALERT_FROM:-}" ] && [ -n "${SES_ALERT_TO:-}" ]; then
        REGION="${AWS_DEFAULT_REGION:-us-east-2}"
        aws ses send-email \
            --region "$REGION" \
            --from "$SES_ALERT_FROM" \
            --destination "ToAddresses=$SES_ALERT_TO" \
            --message "Subject={Data='AlphaBreak Health Alert',Charset='UTF-8'},Body={Text={Data='$(echo -e "$ALERT_MSG")',Charset='UTF-8'}}" \
            >/dev/null 2>&1 || true
    fi
fi

exit $EXIT_CODE
