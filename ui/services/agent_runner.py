"""
ui/services/agent_runner.py
Wraps LangGraph supervisor — streaming, HITL, email/meeting detection.

FIXES:
- email_sent: targs se to/subject/body properly extract (wider field names)
- meeting_saved: email_subject + email_body bhi yield karo
- extract_email_info_from_action: nested args/input dono check karo
- _field: list/dict values bhi handle karo
"""
import os, sys, logging, re
from datetime import datetime
from typing import Generator, Optional

logger = logging.getLogger(__name__)


def _ensure_path():
    ui_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root   = os.path.dirname(ui_dir)
    for p in [root, ui_dir]:
        if p not in sys.path:
            sys.path.insert(0, p)

_ensure_path()


# ─────────────────────────────────────────────────────────────────────────────
# INIT
# ─────────────────────────────────────────────────────────────────────────────
def initialize_agent(enable_hitl: bool = True) -> tuple:
    from dotenv import load_dotenv
    load_dotenv()
    ep  = os.getenv("AZURE_OPENAI_ENDPOINT",   "").strip()
    key = os.getenv("AZURE_OPENAI_API_KEY",    "").strip()
    dep = os.getenv("AZURE_OPENAI_DEPLOYMENT", "").strip()
    if not ep:  raise EnvironmentError("AZURE_OPENAI_ENDPOINT missing from .env")
    if not key: raise EnvironmentError("AZURE_OPENAI_API_KEY missing from .env")
    if not dep: raise EnvironmentError("AZURE_OPENAI_DEPLOYMENT missing from .env")

    from app.core.llm_factory import create_llm
    model = create_llm()
    if model is None:
        raise ValueError("create_llm() returned None")

    from app.supervisor.supervisor_agent import create_supervisor_agent
    supervisor = create_supervisor_agent(model, enable_hitl=enable_hitl)
    if supervisor is None:
        raise ValueError("create_supervisor_agent() returned None")

    return model, supervisor


# ─────────────────────────────────────────────────────────────────────────────
# FIELD EXTRACTOR — wider coverage, handles list/dict/str
# ─────────────────────────────────────────────────────────────────────────────
def _field(args: dict, names: list, default: str = "") -> str:
    """
    args dict mein se pehla matching key ka value return karo.
    List → join, dict → str, else str().
    """
    if not isinstance(args, dict):
        return default
    for n in names:
        val = args.get(n)
        if val is None:
            continue
        if isinstance(val, list):
            # attendees list → join, ya pehla element
            joined = ", ".join(str(v) for v in val if v)
            if joined:
                return joined
        elif isinstance(val, dict):
            return str(val)
        else:
            s = str(val).strip()
            if s:
                return s
    return default


def _extract_email_fields(targs: dict) -> dict:
    """
    Tool args se email fields extract karo.
    Agent alag alag field names use karta hai — sab cover karo.
    """
    to      = _field(targs, ["to", "recipient", "email", "address",
                              "to_email", "receiver", "dest"])
    subject = _field(targs, ["subject", "title", "sub", "email_subject",
                              "subj", "topic"])
    body    = _field(targs, ["body", "message", "content", "text",
                              "email_body", "msg", "html_body", "plain_body",
                              "body_text", "email_content"])
    return {"to": to, "subject": subject, "body": body}


def _extract_meeting_fields(targs: dict) -> dict:
    """
    Tool args se meeting fields extract karo.
    ISO datetime split bhi handle karo.
    """
    title    = _field(targs, ["title", "summary", "name", "event_title",
                               "meeting_title", "event_name"])
    date_val = _field(targs, ["date", "start_date", "day", "event_date"])
    start    = _field(targs, ["start_time", "start_datetime", "start",
                               "begin_time", "from_time"])
    end      = _field(targs, ["end_time", "end_datetime", "end",
                               "finish_time", "to_time"])
    loc      = _field(targs, ["location", "place", "room", "venue", "where"])

    # ISO datetime split: "2024-01-15T10:00:00" → date="2024-01-15", time="10:00"
    for raw, is_date in [(date_val, True), (start, False), (end, False)]:
        if "T" in str(raw):
            parts = str(raw).split("T")
            if is_date:
                date_val = parts[0]
            elif not is_date and raw == start:
                start = parts[1][:5] if len(parts) > 1 else start
            else:
                end = parts[1][:5] if len(parts) > 1 else end

    # Attendees — list ya comma string
    atts = targs.get("attendees") or targs.get("guests") or targs.get("participants") or []
    if isinstance(atts, str):
        atts = [a.strip() for a in atts.split(",") if a.strip()]

    # Email body for meeting invite
    email_body = (
        f"Dear Attendee,\n\nYou are invited to:\n\n"
        f"📅 {title}\n📆 {date_val}\n🕐 {start} – {end}\n"
        f"📍 {loc or 'To be confirmed'}\n\n"
        f"Please confirm your attendance.\n\nBest regards,\nMeeting Organizer"
    )

    return {
        "title":         title,
        "date":          date_val,
        "start":         start,
        "end":           end,
        "location":      loc,
        "attendees":     atts,
        "email_subject": f"Meeting Invitation: {title}" if title else "Meeting Invitation",
        "email_body":    email_body,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STREAM
# ─────────────────────────────────────────────────────────────────────────────
def stream_agent(supervisor, user_input: str, config: dict) -> Generator[dict, None, None]:
    """
    Yields events:
      {type: "message",      content: str}
      {type: "tool_use",     tool: str, args: dict, input: dict}
      {type: "email_sent",   to, subject, body, tool}
      {type: "meeting_saved",title, date, start, end, location, attendees,
                             email_subject, email_body, tool}
      {type: "interrupt",    id, action_requests}
      {type: "error",        content: str, recoverable: bool}
    """
    if not supervisor:
        yield {"type": "error", "content": "Agent not initialized.", "recoverable": False}
        return
    if not (user_input or "").strip():
        yield {"type": "error", "content": "Empty input.", "recoverable": True}
        return

    pending_tc: dict = {}

    try:
        for step in supervisor.stream(
            {"messages": [{"role": "user", "content": user_input.strip()}]},
            config,
            stream_mode="updates",
        ):
            if not step:
                continue

            for node_name, update in step.items():

                # ── INTERRUPT check ──────────────────────────────────────────
                if isinstance(update, (list, tuple)) and update:
                    try:
                        intr = update[0]
                        if hasattr(intr, "value") and isinstance(intr.value, dict):
                            if "action_requests" in intr.value:
                                iid = getattr(intr, "id", f"intr_{datetime.now().timestamp()}")
                                yield {
                                    "type":            "interrupt",
                                    "id":              iid,
                                    "action_requests": intr.value["action_requests"],
                                }
                    except Exception as e:
                        logger.warning(f"Interrupt parse: {e}")
                    continue

                if not isinstance(update, dict):
                    continue

                # ── MESSAGES ─────────────────────────────────────────────────
                for msg in update.get("messages", []):
                    if not hasattr(msg, "type"):
                        continue

                    # AI message
                    if msg.type == "ai":
                        if msg.content and str(msg.content).strip():
                            yield {"type": "message", "content": str(msg.content).strip()}

                        # Collect tool_calls for later matching
                        for tc in getattr(msg, "tool_calls", []) or []:
                            try:
                                tid = (tc.get("id","")   if isinstance(tc, dict) else getattr(tc, "id",   ""))
                                tn  = (tc.get("name","") if isinstance(tc, dict) else getattr(tc, "name", ""))
                                ta  = (tc.get("args",{}) if isinstance(tc, dict) else getattr(tc, "args", {}))
                                if tid:
                                    pending_tc[tid] = {"tool": tn, "args": ta or {}}
                            except Exception:
                                pass

                    # Tool result message
                    elif msg.type == "tool":
                        tname   = getattr(msg, "name",         "") or ""
                        tcid    = getattr(msg, "tool_call_id",  "") or ""
                        tresult = str(getattr(msg, "content",   "") or "")
                        targs   = {}

                        if tcid and tcid in pending_tc:
                            targs = pending_tc.pop(tcid).get("args", {})

                        # Always yield tool_use so UI shows spinner
                        yield {"type": "tool_use", "tool": tname, "args": targs, "input": targs}

                        tname_low = tname.lower()
                        tresult_low = tresult.lower()

                        # ── EMAIL detection ──────────────────────────────────
                        is_email = any(kw in tname_low for kw in
                                       ["email", "send", "gmail", "mail", "notify"])
                        res_ok   = any(kw in tresult_low for kw in
                                       ["success", "sent", "delivered", "ok", "true",
                                        "message id", "id:", "accepted", "messageid", "done"])

                        if is_email and (res_ok or targs):
                            ef = _extract_email_fields(targs)
                            logger.info(f"email_sent event: to={ef['to']} subject={ef['subject']}")
                            yield {
                                "type":    "email_sent",
                                "to":      ef["to"],
                                "subject": ef["subject"],
                                "body":    ef["body"],
                                "tool":    tname,
                            }

                        # ── CALENDAR/MEETING detection ───────────────────────
                        is_cal = (not is_email) and any(kw in tname_low for kw in
                                  ["calendar", "event", "schedule", "meeting",
                                   "create_event", "add_event", "book"])
                        cal_ok = any(kw in tresult_low for kw in
                                     ["success", "created", "scheduled", "confirmed",
                                      "event id", "eventid", "ok", "done", "true"])

                        if is_cal and (cal_ok or targs):
                            mf = _extract_meeting_fields(targs)
                            logger.info(f"meeting_saved event: title={mf['title']} date={mf['date']}")
                            yield {
                                "type":         "meeting_saved",
                                "title":        mf["title"],
                                "date":         mf["date"],
                                "start":        mf["start"],
                                "end":          mf["end"],
                                "location":     mf["location"],
                                "attendees":    mf["attendees"],
                                "email_subject": mf["email_subject"],
                                "email_body":    mf["email_body"],
                                "tool":         tname,
                            }

    except StopIteration:
        pass
    except Exception as e:
        logger.error(f"stream_agent error: {e}", exc_info=True)
        yield _err(str(e))


# ─────────────────────────────────────────────────────────────────────────────
# RESUME (after HITL)
# ─────────────────────────────────────────────────────────────────────────────
def resume_agent(supervisor, interrupt_id: str, decisions: list,
                 config: dict) -> Generator[dict, None, None]:
    """Resume after HITL decisions. Sirf message aur email_sent yield karo."""
    if not supervisor:
        yield {"type": "error", "content": "Agent not initialized.", "recoverable": False}
        return
    try:
        from langgraph.types import Command
    except ImportError:
        yield {"type": "error", "content": "LangGraph not available.", "recoverable": False}
        return

    pending_tc: dict = {}
    try:
        for step in supervisor.stream(
            Command(resume={interrupt_id: {"decisions": decisions}}),
            config,
            stream_mode="updates",
        ):
            if not step:
                continue

            for node_name, update in step.items():
                if not isinstance(update, dict):
                    continue

                for msg in update.get("messages", []):
                    if not hasattr(msg, "type"):
                        continue

                    if msg.type == "ai":
                        if msg.content and str(msg.content).strip():
                            yield {"type": "message", "content": str(msg.content).strip()}
                        for tc in getattr(msg, "tool_calls", []) or []:
                            try:
                                tid = (tc.get("id","")   if isinstance(tc, dict) else getattr(tc, "id",   ""))
                                tn  = (tc.get("name","") if isinstance(tc, dict) else getattr(tc, "name", ""))
                                ta  = (tc.get("args",{}) if isinstance(tc, dict) else getattr(tc, "args", {}))
                                if tid:
                                    pending_tc[tid] = {"tool": tn, "args": ta or {}}
                            except Exception:
                                pass

                    elif msg.type == "tool":
                        tname   = getattr(msg, "name",         "") or ""
                        tcid    = getattr(msg, "tool_call_id",  "") or ""
                        tresult = str(getattr(msg, "content",   "") or "")
                        targs   = {}
                        if tcid and tcid in pending_tc:
                            targs = pending_tc.pop(tcid).get("args", {})

                        tname_low   = tname.lower()
                        tresult_low = tresult.lower()

                        # Resume mein sirf email yield karo — meeting nahi (chat_ui handle karti hai)
                        is_email = any(kw in tname_low for kw in
                                       ["email", "send", "gmail", "mail", "notify"])
                        res_ok   = any(kw in tresult_low for kw in
                                       ["success", "sent", "delivered", "ok", "true",
                                        "message id", "id:", "accepted", "messageid", "done"])

                        if is_email and (res_ok or targs):
                            ef = _extract_email_fields(targs)
                            logger.info(f"resume email_sent: to={ef['to']}")
                            yield {
                                "type":    "email_sent",
                                "to":      ef["to"],
                                "subject": ef["subject"],
                                "body":    ef["body"],
                                "tool":    tname,
                            }

    except StopIteration:
        pass
    except Exception as e:
        logger.error(f"resume_agent error: {e}", exc_info=True)
        yield {"type": "error",
               "content": f"Error after approval: {str(e)[:200]}",
               "recoverable": True}


# ─────────────────────────────────────────────────────────────────────────────
# HITL — extract email info from action_requests
# ─────────────────────────────────────────────────────────────────────────────
def extract_email_info_from_action(action_requests: list) -> list:
    """
    action_requests list se email info extract karo.
    Har req ka structure: {tool_name, args} ya {tool_name, input} ya nested.
    """
    results = []
    for req in action_requests:
        if not isinstance(req, dict):
            # Object attribute access bhi try karo
            try:
                req = {
                    "tool_name": getattr(req, "tool_name", "") or getattr(req, "name", ""),
                    "args":      getattr(req, "args",      {}) or getattr(req, "input", {}),
                }
            except Exception:
                continue

        tool = (req.get("tool_name") or req.get("name") or req.get("tool") or "").lower()

        # Email tool check
        if not any(kw in tool for kw in ["email", "send", "gmail", "mail", "notify"]):
            continue

        # Args — multiple possible keys
        args = (
            req.get("args") or
            req.get("input") or
            req.get("parameters") or
            req.get("kwargs") or
            {}
        )
        if not isinstance(args, dict):
            args = {}

        ef = _extract_email_fields(args)

        # Agar to empty hai, req level pe check karo
        if not ef["to"]:
            ef["to"] = _field(req, ["to", "recipient", "email", "address"])
        if not ef["subject"]:
            ef["subject"] = _field(req, ["subject", "title"])

        results.append({
            "to":      ef["to"],
            "subject": ef["subject"],
            "body":    ef["body"],
            "tool":    req.get("tool_name") or req.get("name") or "",
        })

    return results


# ─────────────────────────────────────────────────────────────────────────────
# MISC HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def detect_email_sent_in_response(content: str) -> Optional[dict]:
    low = content.lower()
    kws = ["email sent", "message sent", "sent successfully",
           "email has been sent", "successfully sent", "mail sent"]
    if not any(k in low for k in kws):
        return None
    emails = re.findall(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", content)
    result = {}
    if emails:
        result["to"] = emails[0]
    m = re.search(r"subject[:\s]+['\"]?([^'\"\n]+)['\"]?", content, re.IGNORECASE)
    if m:
        result["subject"] = m.group(1).strip()[:100]
    return result or {"to": "Unknown", "subject": "Email from Agent"}


def _err(msg: str) -> dict:
    low = msg.lower()
    if "credentials" in low or "token" in low:
        content = "Google credentials error. Reconnect in Settings."
    elif "rate limit" in low or "429" in msg:
        content = "Azure OpenAI rate limit. Please wait."
    elif "timeout" in low:
        content = "Request timed out. Try again."
    else:
        content = f"Agent error: {msg[:200]}"
    return {"type": "error", "content": content, "recoverable": True}