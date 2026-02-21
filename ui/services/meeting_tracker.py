"""
ui/services/meeting_tracker.py
JSON persistence — atomic writes. Single data directory for ALL records.
"""
import json, os, uuid, logging
from datetime import datetime
from typing import Optional

logger   = logging.getLogger(__name__)
DATA_DIR = "data"
MEETINGS = os.path.join(DATA_DIR, "meetings_status.json")
EMAILS   = os.path.join(DATA_DIR, "emails_sent.json")


def _ensure():
    os.makedirs(DATA_DIR, exist_ok=True)

def _load(path: str) -> list:
    _ensure()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, list) else []
    except Exception as e:
        logger.error(f"Load {path}: {e}")
        return []

def _save(path: str, data: list) -> None:
    _ensure()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    os.replace(tmp, path)


# ── MEETINGS ──────────────────────────────────────────────────────────────────
def load_meetings() -> list:
    return _load(MEETINGS)

def add_meeting(
    title: str, date: str, start_time: str, end_time: str,
    location: str = "", attendees: list = None,
    email_subject: str = "", email_body: str = "",
    status: str = "Pending", source: str = "scheduler",
) -> dict:
    meetings = load_meetings()
    m = {
        "id": uuid.uuid4().hex, "title": title, "date": str(date),
        "start_time": str(start_time), "end_time": str(end_time),
        "location": location or "", "attendees": attendees or [],
        "email_subject": email_subject or "", "email_body": email_body or "",
        "status": status, "source": source,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    meetings.append(m)
    _save(MEETINGS, meetings)
    logger.info(f"Meeting saved: {title}")
    return m

def update_meeting_status(meeting_id: str, status: str) -> bool:
    meetings = load_meetings()
    for m in meetings:
        if m.get("id") == meeting_id:
            m["status"] = status
            m["updated_at"] = datetime.now().isoformat()
            _save(MEETINGS, meetings)
            return True
    return False

def delete_meeting(meeting_id: str) -> bool:
    meetings = load_meetings()
    updated  = [m for m in meetings if m.get("id") != meeting_id]
    if len(updated) < len(meetings):
        _save(MEETINGS, updated)
        return True
    return False

def get_meetings_stats() -> dict:
    m = load_meetings()
    return {
        "total":    len(m),
        "approved": sum(1 for x in m if x.get("status") == "Approved"),
        "pending":  sum(1 for x in m if x.get("status") == "Pending"),
        "rejected": sum(1 for x in m if x.get("status") == "Rejected"),
    }


# ── EMAILS ────────────────────────────────────────────────────────────────────
def load_emails() -> list:
    return _load(EMAILS)

def save_email_record(
    to: str, subject: str, body: str = "",
    status: str = "sent", source: str = "agent",
    meeting_id: Optional[str] = None,
) -> dict:
    emails = load_emails()
    r = {
        "id":           uuid.uuid4().hex,
        "to":           to,
        "subject":      subject,
        "body_preview": body[:200] if body else "",
        "body":         body or "",
        "status":       status,
        "source":       source,
        "meeting_id":   meeting_id,
        "sent_at":      datetime.now().isoformat(),
    }
    emails.append(r)
    _save(EMAILS, emails)
    logger.info(f"Email saved: to={to} status={status}")
    return r

def delete_email_record(email_id: str) -> bool:
    emails = load_emails()
    updated = [e for e in emails if e.get("id") != email_id]
    if len(updated) < len(emails):
        _save(EMAILS, updated)
        return True
    return False

def save_bulk_emails(
    recipients: list, subject: str, body: str = "",
    meeting_id: Optional[str] = None,
    source: str = "scheduler", status: str = "sent",
) -> list:
    return [
        save_email_record(str(t).strip(), subject, body, status, source, meeting_id)
        for t in recipients if t and str(t).strip()
    ]

def get_emails_stats() -> dict:
    e = load_emails()
    return {
        "total":          len(e),
        "sent":           sum(1 for x in e if x.get("status","").lower() in ("sent","delivered")),
        "rejected":       sum(1 for x in e if x.get("status","").lower() == "rejected"),
        "failed":         sum(1 for x in e if x.get("status","").lower() == "failed"),
        "from_chat":      sum(1 for x in e if x.get("source") == "agent"),
        "from_hitl":      sum(1 for x in e if x.get("source") == "hitl"),
        "from_scheduler": sum(1 for x in e if x.get("source") == "scheduler"),
    }