"""
ui/services/email_service.py

ARCHITECTURE (simple & correct):
  - Chat UI:    Agent tool ne email bheja → sirf record save karo (supervisor=None)
  - Scheduler:  Direct Gmail API → record save karo
  - HITL approve: Agent tool ne email bheja → sirf record save karo (supervisor=None)
  - HITL reject: Kuch send mat karo → rejected record save karo

send_and_save_email() ke parameters:
  supervisor=None, agent_config=None → record only (agent already sent)
  supervisor=None, agent_config=None, approval_status="rejected" → rejected record
  force_gmail=True → directly Gmail API se send karo (scheduler use karta hai)
"""
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


def send_and_save_email(
    to: str,
    subject: str,
    body: str,
    source: str = "agent",
    approval_status: str = "approved",
    meeting_id: Optional[str] = None,
    supervisor=None,        # unused — kept for backward compat
    agent_config=None,      # unused — kept for backward compat
    force_gmail: bool = False,  # True → directly use Gmail API
) -> dict:
    """
    Returns: {sent, saved, record_id, error}
    """
    from ui.services.meeting_tracker import save_email_record, load_emails
    from ui.utils.session_state import add_log, sync_data_from_files

    result = {"sent": False, "saved": False, "record_id": None, "error": None}

    # Validate
    if not to or not str(to).strip():
        result["error"] = "missing_recipient"
        add_log("email_service: no recipient", "WARNING")
        return result

    to      = str(to).strip()
    subject = (str(subject) if subject else "").strip() or "Email from Agent"
    body    = (str(body) if body else "").strip()

    # Dedup — same to+subject+status within 30s
    try:
        cutoff = (datetime.now() - timedelta(seconds=30)).isoformat()
        for e in load_emails():
            if (
                e.get("to","").strip()      == to
                and e.get("subject","").strip() == subject
                and e.get("sent_at","")         >= cutoff
                and e.get("status","").lower()  == approval_status.lower()
            ):
                add_log(f"email_service: dedup skip → {to}", "INFO")
                result["error"] = "duplicate"
                result["saved"] = True
                return result
    except Exception as exc:
        add_log(f"email_service: dedup error — {exc}", "WARNING")

    # Determine delivery_status
    if approval_status == "rejected":
        delivery_status = "rejected"

    elif approval_status == "pending":
        delivery_status = "pending"

    elif approval_status == "approved":
        if force_gmail:
            # Directly use Gmail API (scheduler path)
            delivery_status = _send_via_gmail(to, subject, body)
        else:
            # Chat/HITL path: agent already sent it via tool
            # We are just recording the fact
            delivery_status = "sent"
    else:
        delivery_status = "pending"

    result["sent"] = delivery_status in ("sent", "delivered")

    # Always save
    try:
        record = save_email_record(
            to=to, subject=subject, body=body,
            status=delivery_status, source=source, meeting_id=meeting_id,
        )
        sync_data_from_files()
        result["saved"]     = True
        result["record_id"] = record.get("id") if isinstance(record, dict) else None
        add_log(
            f"Email | to={to} | status={delivery_status} | "
            f"approval={approval_status} | src={source}"
        )
    except Exception as exc:
        result["error"] = f"save_failed:{exc}"
        add_log(f"email_service: save error — {exc}", "ERROR")

    return result


def _send_via_gmail(to: str, subject: str, body: str) -> str:
    """
    Send directly via Gmail API (same credentials the agent uses).
    Returns 'sent' | 'failed' | 'no_credentials'
    """
    try:
        # Try to use same gmail service the agent uses
        from app.agents.email.tools import get_gmail_service
        service = get_gmail_service()
        if not service:
            logger.warning("Gmail service not available")
            return _send_via_smtp(to, subject, body)

        import base64
        from email.mime.text import MIMEText
        msg = MIMEText(body, "plain", "utf-8")
        msg["To"]      = to
        msg["Subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()
        logger.info(f"Gmail sent: to={to}")
        return "sent"

    except ImportError:
        # Fallback to SMTP if gmail tools not importable
        return _send_via_smtp(to, subject, body)
    except Exception as exc:
        logger.error(f"Gmail send failed: to={to} — {exc}")
        return _send_via_smtp(to, subject, body)


def _send_via_smtp(to: str, subject: str, body: str) -> str:
    """
    SMTP fallback. Set in .env:
      SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASS, SMTP_FROM
    Returns: 'sent' | 'failed' | 'no_credentials'
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    host = os.getenv("SMTP_HOST","").strip()
    port = int(os.getenv("SMTP_PORT","587") or "587")
    user = os.getenv("SMTP_USER","").strip()
    pw   = os.getenv("SMTP_PASS","").strip()
    frm  = os.getenv("SMTP_FROM", user).strip()

    if not host or not user or not pw:
        logger.warning("SMTP not configured")
        return "no_credentials"

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = frm
        msg["To"]      = to
        msg.attach(MIMEText(body, "plain", "utf-8"))
        with smtplib.SMTP(host, port, timeout=15) as srv:
            srv.ehlo(); srv.starttls(); srv.login(user, pw)
            srv.sendmail(frm, [to], msg.as_string())
        logger.info(f"SMTP sent: to={to}")
        return "sent"
    except Exception as exc:
        logger.error(f"SMTP failed to={to}: {exc}")
        return "failed"