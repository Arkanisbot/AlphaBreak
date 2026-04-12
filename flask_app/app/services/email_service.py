"""
Email Service
=============
Renders branded HTML email templates and sends via AWS SES.
Also handles SES bounce and complaint notifications.
"""

import os
import json
import logging
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

SES_FROM_EMAIL = os.getenv('SES_FROM_EMAIL', 'noreply@alphabreak.vip')
SES_REGION = os.getenv('AWS_SES_REGION', 'us-east-1')
SES_SANDBOX_MODE = os.getenv('SES_SANDBOX_MODE', 'true').lower() == 'true'

# Template directory
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')

# Initialize Jinja2 environment for email templates
_jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(['html']),
)


def render_template(template_name, context=None):
    """Render an email template with the given context."""
    ctx = context or {}
    ctx.setdefault('current_year', str(datetime.utcnow().year))
    template = _jinja_env.get_template(template_name)
    return template.render(**ctx)


def send_templated_email(to_email, template_name, context=None, subject=None):
    """
    Render an email template and send it via SES.

    Args:
        to_email: Recipient email address
        template_name: Template path relative to templates/ (e.g. 'email/trade_signal.html')
        context: Dict of template variables
        subject: Email subject line (falls back to template title block)

    Returns:
        dict with 'success' bool and 'message_id' or 'error'
    """
    ctx = context or {}

    try:
        html_body = render_template(template_name, ctx)
    except Exception as e:
        logger.error(f"Template render failed for {template_name}: {e}")
        return {'success': False, 'error': f'Template render failed: {e}'}

    # Build subject from context if not provided
    if not subject:
        subject = f"[AlphaBreak] {ctx.get('subject', 'Notification')}"

    # Plain text fallback
    text_body = ctx.get('text_body', ctx.get('body', subject))

    if SES_SANDBOX_MODE:
        logger.info(f"SES sandbox: would send '{subject}' to {to_email}")
        return {'success': True, 'message_id': 'sandbox', 'sandbox': True}

    try:
        import boto3
        client = boto3.client('ses', region_name=SES_REGION)

        response = client.send_email(
            Source=SES_FROM_EMAIL,
            Destination={'ToAddresses': [to_email]},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {
                    'Html': {'Data': html_body, 'Charset': 'UTF-8'},
                    'Text': {'Data': text_body, 'Charset': 'UTF-8'},
                }
            }
        )
        message_id = response.get('MessageId', '')
        logger.info(f"Email sent to {to_email}: {message_id}")
        return {'success': True, 'message_id': message_id}

    except Exception as e:
        logger.error(f"SES send failed to {to_email}: {e}")
        return {'success': False, 'error': str(e)}


def handle_bounce(message):
    """
    Process an SES bounce notification.
    Marks the user's email as bounced in the database to prevent future sends.

    Args:
        message: Parsed SNS bounce notification body (dict)

    Returns:
        Number of emails marked as bounced
    """
    bounce = message.get('bounce', {})
    bounce_type = bounce.get('bounceType', 'unknown')
    recipients = bounce.get('bouncedRecipients', [])

    if not recipients:
        logger.warning("Bounce notification with no recipients")
        return 0

    marked = 0
    from app.utils.database import db_manager

    for recipient in recipients:
        email = recipient.get('emailAddress', '').lower().strip()
        if not email:
            continue

        try:
            with db_manager.get_cursor(commit=True) as cursor:
                # Mark user email as bounced
                cursor.execute(
                    """UPDATE users SET email_bounced = TRUE, email_bounce_type = %s,
                       email_bounced_at = NOW() WHERE LOWER(email) = %s AND email_bounced = FALSE""",
                    (bounce_type, email)
                )
                if cursor.rowcount > 0:
                    marked += 1
                    logger.info(f"Marked email bounced: {email} (type={bounce_type})")

                # Disable email notifications for bounced users
                cursor.execute(
                    """UPDATE notification_preferences SET email_enabled = FALSE, updated_at = NOW()
                       WHERE user_id IN (SELECT id FROM users WHERE LOWER(email) = %s)""",
                    (email,)
                )
        except Exception as e:
            logger.error(f"Failed to process bounce for {email}: {e}")

    return marked


def handle_complaint(message):
    """
    Process an SES complaint notification.
    Unsubscribes the user from all email notifications.

    Args:
        message: Parsed SNS complaint notification body (dict)

    Returns:
        Number of users unsubscribed
    """
    complaint = message.get('complaint', {})
    recipients = complaint.get('complainedRecipients', [])

    if not recipients:
        logger.warning("Complaint notification with no recipients")
        return 0

    unsubscribed = 0
    from app.utils.database import db_manager

    for recipient in recipients:
        email = recipient.get('emailAddress', '').lower().strip()
        if not email:
            continue

        try:
            with db_manager.get_cursor(commit=True) as cursor:
                # Disable all email notifications
                cursor.execute(
                    """UPDATE notification_preferences SET email_enabled = FALSE, updated_at = NOW()
                       WHERE user_id IN (SELECT id FROM users WHERE LOWER(email) = %s)""",
                    (email,)
                )
                if cursor.rowcount > 0:
                    unsubscribed += 1

                # Mark as complained
                cursor.execute(
                    """UPDATE users SET email_complaint = TRUE, email_complaint_at = NOW()
                       WHERE LOWER(email) = %s""",
                    (email,)
                )
                logger.info(f"Processed complaint for: {email}")
        except Exception as e:
            logger.error(f"Failed to process complaint for {email}: {e}")

    return unsubscribed
