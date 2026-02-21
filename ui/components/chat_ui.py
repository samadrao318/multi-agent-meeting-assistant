"""
ui/components/chat_ui.py
FIXES:
- Meeting save: email_subject + email_body har jagah save hoti hai
- Email: force_gmail=False chat/HITL path pe (agent already sends)
- HITL approve pe meeting "Approved", reject pe "Rejected"
- 400 error fix: new_thread_after_hitl() after HITL resume
- Resume ke baad naya meeting nahi banta (LLM response ignore)
"""
import datetime as _dt
import streamlit as st

from ui.utils.session_state import (
    add_message, get_messages, add_log, get_agent_config,
    set_hitl_interrupt, reset_hitl, sync_data_from_files,
    new_thread_after_hitl,
)
from ui.services.agent_runner import (
    stream_agent, resume_agent, extract_email_info_from_action,
)
from ui.services.meeting_tracker import (
    add_meeting, load_meetings, update_meeting_status,
)
from ui.services.email_service import send_and_save_email


def render_chat() -> None:
    from ui.components.hitl_panel import render_hitl_panel

    st.markdown("""
    <h2 style="font-family:'Georgia',serif;color:#1a365d;margin:0;font-size:1.5rem;">
        \U0001f4ac Chat with AI Agents</h2>
    <p style="color:#718096;font-size:0.875rem;margin:2px 0 0 0;">
        Natural language \u2014 schedule meetings, send emails, manage contacts</p>
    """, unsafe_allow_html=True)

    if not st.session_state.get("initialized"):
        st.warning("\u26a0\ufe0f Agent not initialized. Check `.env` credentials and click **\U0001f504 Reinit**.")
        return

    if st.session_state.get("hitl_pending"):
        msgs = get_messages()
        last = next((m["content"] for m in reversed(msgs) if m["role"] == "user"), None)
        if last:
            st.markdown(
                f'<div style="background:#fef9c3;border:1px solid #fde68a;border-radius:10px;'
                f'padding:10px 16px;margin-bottom:14px;font-size:0.82rem;color:#92400e;">'
                f'\U0001f4ac <strong>Your request:</strong> '
                f'{last[:140]}{"..." if len(last) > 140 else ""}</div>',
                unsafe_allow_html=True,
            )
        submitted = render_hitl_panel()
        if submitted:
            _process_hitl_resume()
        return

    _render_examples()
    _render_history()
    _render_input()


def _render_examples() -> None:
    if not st.session_state.get("show_examples", True):
        return
    examples = [
        "\U0001f4cb Show me all contacts",
        "\U0001f50d Search for engineers",
        "\U0001f4c5 Schedule meeting tomorrow 2pm",
        "\U0001f4e7 Send email to team",
        "\u2795 Add contact: alice@example.com",
        "\U0001f4c6 Check calendar this week",
    ]
    with st.expander("\U0001f4a1 Quick Prompts", expanded=len(get_messages()) == 0):
        cols = st.columns(3)
        for i, ex in enumerate(examples):
            if cols[i % 3].button(ex, key=f"qp_{i}", use_container_width=True):
                _submit(" ".join(ex.split(" ")[1:]))


def _render_history() -> None:
    msgs    = get_messages()
    running = st.session_state.get("agent_running", False)

    with st.container(height=440):
        if not msgs and not running:
            st.markdown(
                '<div style="display:flex;flex-direction:column;align-items:center;'
                'justify-content:center;height:360px;gap:12px;">'
                '<div style="font-size:3rem;opacity:0.3;">\U0001f916</div>'
                '<div style="color:#a0aec0;font-size:0.95rem;text-align:center;">'
                'Start a conversation with your AI agents.<br>'
                '<span style="font-size:0.82rem;">Calendar \u00b7 Email \u00b7 Contacts</span>'
                '</div></div>',
                unsafe_allow_html=True,
            )
            return

        for msg in msgs:
            r  = msg["role"]
            c  = msg["content"]
            ts = msg.get("timestamp", "")

            if r == "user":
                st.markdown(
                    f'<div style="display:flex;justify-content:flex-end;margin:8px 0;'
                    f'align-items:flex-end;gap:8px;">'
                    f'<div style="background:linear-gradient(135deg,#1e3a5f,#2563eb);color:white;'
                    f'padding:10px 16px;border-radius:18px 18px 4px 18px;max-width:72%;'
                    f'font-size:0.88rem;line-height:1.5;">{c}'
                    f'<div style="font-size:0.68rem;opacity:0.7;text-align:right;margin-top:4px;">{ts}</div>'
                    f'</div><div style="font-size:1.3rem;flex-shrink:0;">\U0001f464</div></div>',
                    unsafe_allow_html=True,
                )
            elif r == "assistant":
                st.markdown(
                    f'<div style="display:flex;justify-content:flex-start;margin:8px 0;'
                    f'align-items:flex-end;gap:8px;">'
                    f'<div style="font-size:1.3rem;flex-shrink:0;">\U0001f916</div>'
                    f'<div style="background:#f7f9fc;color:#1a202c;padding:10px 16px;'
                    f'border-radius:18px 18px 18px 4px;max-width:72%;font-size:0.88rem;'
                    f'line-height:1.6;border:1px solid #e2e8f0;">'
                    f'{c.replace(chr(10), "<br>")}'
                    f'<div style="font-size:0.68rem;color:#a0aec0;margin-top:4px;">{ts}</div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
            elif r == "system":
                st.markdown(
                    f'<div style="text-align:center;margin:6px 0;">'
                    f'<span style="background:#edf2f7;color:#4a5568;padding:4px 14px;'
                    f'border-radius:20px;font-size:0.78rem;font-style:italic;">{c}</span></div>',
                    unsafe_allow_html=True,
                )
            elif r == "tool":
                st.markdown(
                    f'<div style="text-align:center;margin:4px 0;">'
                    f'<span style="background:#e0f2fe;color:#0369a1;padding:3px 12px;'
                    f'border-radius:20px;font-size:0.75rem;">\u2699\ufe0f {c}</span></div>',
                    unsafe_allow_html=True,
                )

        if running:
            st.session_state["_stream_ph"] = st.empty()


def _render_input() -> None:
    ui = st.chat_input(
        "Message your AI agents...",
        key="chat_main_input",
        disabled=st.session_state.get("agent_running", False),
    )
    if ui and ui.strip():
        _submit(ui.strip())


def _submit(text: str) -> None:
    if not text:
        return
    add_message("user", text)
    st.session_state.agent_running = True
    st.session_state.show_examples = False
    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# AGENT RUN
# ─────────────────────────────────────────────────────────────────────────────
def run_agent_if_needed() -> None:
    if not st.session_state.get("agent_running"):
        return

    supervisor = st.session_state.get("supervisor")
    if not supervisor:
        add_message("assistant", "\u274c Agent not initialized. Check Settings.")
        st.session_state.agent_running = False
        st.rerun()
        return

    msgs = [m for m in get_messages() if m["role"] == "user"]
    if not msgs:
        st.session_state.agent_running = False
        return

    user_input  = msgs[-1]["content"]
    config      = get_agent_config()
    full_resp   = ""
    interrupted = False
    tool_calls  = []
    cal_used    = False

    CAL_TOOLS = {
        "create_event", "schedule_meeting", "create_meeting", "add_event",
        "calendar_create", "book_meeting", "create_calendar_event", "schedule_event",
    }

    ph = st.session_state.pop("_stream_ph", None) or st.empty()
    ph.markdown(_thinking(), unsafe_allow_html=True)

    try:
        for event in stream_agent(supervisor, user_input, config):
            etype = event.get("type")

            if etype == "message":
                full_resp += event["content"]
                ph.markdown(_streaming(full_resp), unsafe_allow_html=True)

            elif etype == "tool_use":
                tname = event.get("tool", "")
                tool_calls.append(tname)
                ph.markdown(_tool_bubble(tname), unsafe_allow_html=True)
                if tname.lower() in CAL_TOOLS:
                    cal_used = True
                    inp = event.get("input") or event.get("args") or {}
                    if inp:
                        _save_meeting_from_tool(inp, user_input)

            elif etype == "email_sent":
                to      = event.get("to", "")
                subject = event.get("subject", "")
                body    = event.get("body", "")
                mtg_id  = st.session_state.get("last_saved_meeting_id")
                if to and subject:
                    result = send_and_save_email(
                        to=to, subject=subject, body=body,
                        source="agent", approval_status="approved",
                        meeting_id=mtg_id,
                        force_gmail=True,
                    )
                    add_log(f"Agent email recorded: sent={result['sent']} to={to}")

            elif etype == "meeting_saved":
                _save_meeting_from_event(event)

            elif etype == "interrupt":
                interrupted = True
                if full_resp:
                    add_message("assistant", full_resp)
                    full_resp = ""
                for t in tool_calls:
                    add_message("tool", f"Tool used: {t}")
                set_hitl_interrupt(event["id"], event["action_requests"])
                add_message("system", "\u23f8\ufe0f Agent paused \u2014 awaiting your approval")
                break

            elif etype == "error":
                add_message("assistant", f"\u26a0\ufe0f {event['content']}")
                add_log(f"Agent error: {event['content']}", "ERROR")
                break

    except Exception as e:
        add_message("assistant", f"\u274c Unexpected error: {str(e)[:200]}")
        add_log(f"run_agent error: {e}", "ERROR")
    finally:
        ph.empty()

    if not interrupted and full_resp:
        for t in tool_calls:
            add_message("tool", f"Tool used: {t}")
        add_message("assistant", full_resp)
        if cal_used:
            _save_meeting_from_response(full_resp, user_input)

    st.session_state.agent_running = False
    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# HITL RESUME
# ─────────────────────────────────────────────────────────────────────────────
def _process_hitl_resume() -> None:
    decisions       = st.session_state.get("hitl_final_decisions", [])
    interrupt_id    = st.session_state.get("hitl_interrupt_id")
    action_requests = st.session_state.get("hitl_action_requests", [])
    supervisor      = st.session_state.get("supervisor")
    meeting_id      = st.session_state.get("last_saved_meeting_id")

    if not interrupt_id or not supervisor:
        reset_hitl()
        st.rerun()
        return

    any_approved = False

    for decision, req in zip(decisions, action_requests):
        is_approved     = (decision or {}).get("type") == "approve"
        approval_status = "approved" if is_approved else "rejected"
        if is_approved:
            any_approved = True

        for info in extract_email_info_from_action([req]):
            to   = info.get("to", "")
            subj = info.get("subject", "")
            body = info.get("body", "")
            if not to and not subj:
                continue
            result = send_and_save_email(
                to=to or "Unknown",
                subject=subj or "Meeting Invitation",
                body=body or "",
                source="agent",
                approval_status=approval_status,
                meeting_id=meeting_id,
                force_gmail=True,
            )
            lbl = (
                "\U0001f4e7 Email sent"     if result["sent"] else
                "\u274c Email rejected" if not is_approved else
                "\u26a0\ufe0f Save hua"
            )
            add_message("system", f"{lbl} \u2192 {to or '?'}")
            add_log(f"HITL {approval_status} | sent={result['sent']} | to={to}")

    if meeting_id:
        new_status = "Approved" if any_approved else "Rejected"
        update_meeting_status(meeting_id, new_status)
        add_log(f"Meeting {meeting_id[:8]} -> {new_status} (HITL)")

    sync_data_from_files()
    reset_hitl()
    new_thread_after_hitl()
    config = get_agent_config()

    full_resp = ""
    ph = st.empty()
    ph.markdown(_resuming(), unsafe_allow_html=True)

    try:
        for event in resume_agent(supervisor, interrupt_id, decisions, config):
            etype = event.get("type")

            if etype == "message":
                full_resp += event["content"]
                ph.markdown(_streaming(full_resp), unsafe_allow_html=True)

            elif etype == "email_sent":
                to      = event.get("to", "")
                subject = event.get("subject", "")
                body    = event.get("body", "")
                if to and subject:
                    result = send_and_save_email(
                        to=to, subject=subject, body=body,
                        source="agent", approval_status="approved",
                        meeting_id=meeting_id,
                        force_gmail=True,
                    )
                    add_log(f"Resume email recorded: sent={result['sent']} to={to}")

            elif etype == "meeting_saved":
                add_log("Resume: meeting_saved ignored (already saved before HITL)")

            elif etype == "tool_use":
                add_log(f"Resume: tool_use '{event.get('tool','')}' ignored (post-HITL)")

            elif etype == "error":
                add_message("assistant", f"\u26a0\ufe0f {event['content']}")
                add_log(f"Resume error: {event['content']}", "ERROR")
                break

    except Exception as e:
        add_message("assistant", f"\u274c Error after approval: {str(e)[:200]}")
        add_log(f"resume exception: {e}", "ERROR")
    finally:
        ph.empty()

    if full_resp:
        add_message("assistant", full_resp)

    sync_data_from_files()
    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# BUBBLES
# ─────────────────────────────────────────────────────────────────────────────
def _thinking() -> str:
    return (
        '<div style="display:flex;justify-content:flex-start;margin:8px 0;align-items:flex-end;gap:8px;">'
        '<div style="font-size:1.3rem;flex-shrink:0;">\U0001f916</div>'
        '<div style="background:#f0f4ff;color:#1e40af;padding:10px 16px;border-radius:18px 18px 18px 4px;'
        'font-size:0.88rem;border:1px solid #bfdbfe;">'
        '<span style="display:inline-block;animation:pulse 1.2s infinite;">\U0001f914 Thinking...</span>'
        '</div></div>'
        '<style>@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}</style>'
    )


def _resuming() -> str:
    return (
        '<div style="display:flex;justify-content:flex-start;margin:8px 0;align-items:flex-end;gap:8px;">'
        '<div style="font-size:1.3rem;flex-shrink:0;">\U0001f916</div>'
        '<div style="background:#f0fdf4;color:#166534;padding:10px 16px;border-radius:18px 18px 18px 4px;'
        'font-size:0.88rem;border:1px solid #a7f3d0;">'
        '\U0001f504 Resuming with your decisions...</div></div>'
    )


def _streaming(text: str) -> str:
    return (
        '<div style="display:flex;justify-content:flex-start;margin:8px 0;align-items:flex-end;gap:8px;">'
        '<div style="font-size:1.3rem;flex-shrink:0;">\U0001f916</div>'
        '<div style="background:#f7f9fc;color:#1a202c;padding:10px 16px;'
        'border-radius:18px 18px 18px 4px;max-width:72%;font-size:0.88rem;'
        'line-height:1.6;border:1px solid #e2e8f0;">'
        f'{text.replace(chr(10), "<br>")}<span style="opacity:0.5;">\u258c</span>'
        '</div></div>'
    )


def _tool_bubble(tool: str) -> str:
    return (
        '<div style="display:flex;justify-content:flex-start;margin:8px 0;align-items:flex-end;gap:8px;">'
        '<div style="font-size:1.3rem;flex-shrink:0;">\U0001f916</div>'
        '<div style="background:#fef3c7;color:#92400e;padding:8px 16px;'
        'border-radius:18px 18px 18px 4px;font-size:0.82rem;border:1px solid #fde68a;">'
        f'\u2699\ufe0f Using: <strong>{tool}</strong>...</div></div>'
    )


# ─────────────────────────────────────────────────────────────────────────────
# MEETING HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _default_email_body(title: str, date_val: str, start: str, end: str, loc: str) -> str:
    return (
        f"Dear Attendee,\n\nYou are invited to:\n\n"
        f"\U0001f4c5 {title}\n\U0001f4c6 {date_val}\n\U0001f550 {start} - {end}\n"
        f"\U0001f4cd {loc or 'To be confirmed'}\n\n"
        f"Please confirm your attendance.\n\nBest regards,\nMeeting Organizer"
    )


def _is_duplicate_meeting(title: str, date_val: str) -> bool:
    cutoff = (_dt.datetime.now() - _dt.timedelta(seconds=30)).isoformat()
    for m in load_meetings():
        if (
            m.get("title", "").strip() == title
            and m.get("date", "")       == date_val
            and m.get("created_at", "") >= cutoff
        ):
            return True
    return False


def _save_meeting_from_event(event: dict) -> None:
    title    = (event.get("title", "") or "").strip() or "Meeting from Agent"
    date_val = event.get("date", "") or str(_dt.date.today())
    if _is_duplicate_meeting(title, date_val):
        return
    start = event.get("start", "")    or "00:00"
    end   = event.get("end", "")      or "01:00"
    loc   = event.get("location", "") or ""
    atts  = event.get("attendees")    or []
    subj  = event.get("email_subject", "") or f"Meeting Invitation: {title}"
    body  = event.get("email_body", "")    or _default_email_body(title, date_val, start, end, loc)
    mtg = add_meeting(
        title=title, date=date_val, start_time=start, end_time=end,
        location=loc, attendees=atts,
        email_subject=subj, email_body=body,
        status="Pending", source="agent",
    )
    if mtg and mtg.get("id"):
        st.session_state["last_saved_meeting_id"] = mtg["id"]
    sync_data_from_files()
    add_log(f"Meeting saved (event): {title} on {date_val}")


def _save_meeting_from_tool(inp: dict, user_input: str = "") -> None:
    def _f(*keys):
        for k in keys:
            if inp.get(k):
                return str(inp[k])
        return ""

    title    = (_f("title", "summary", "name", "event_title") or "Meeting from Agent").strip()
    date_val = _f("date", "start_date", "day") or str(_dt.date.today())
    start    = _f("start_time", "start_datetime", "start", "time") or "00:00"
    end      = _f("end_time", "end_datetime", "end") or "01:00"
    loc      = _f("location", "place", "venue")

    for v_name, v in [("date_val", date_val), ("start", start), ("end", end)]:
        if "T" in str(v):
            parts = str(v).split("T")
            if v_name == "date_val":
                date_val = parts[0]
            elif v_name == "start":
                start = parts[1][:5] if len(parts) > 1 else start
            else:
                end = parts[1][:5] if len(parts) > 1 else end

    atts = inp.get("attendees") or inp.get("guests") or inp.get("participants") or []
    if isinstance(atts, str):
        atts = [a.strip() for a in atts.split(",") if a.strip()]

    if _is_duplicate_meeting(title, str(date_val)):
        return

    subj = f"Meeting Invitation: {title}"
    body = _default_email_body(title, str(date_val), start, end, loc)

    mtg = add_meeting(
        title=title, date=str(date_val), start_time=str(start), end_time=str(end),
        location=loc, attendees=atts,
        email_subject=subj, email_body=body,
        status="Pending", source="agent",
    )
    if mtg and mtg.get("id"):
        st.session_state["last_saved_meeting_id"] = mtg["id"]
    sync_data_from_files()
    add_log(f"Meeting saved (tool): {title} on {date_val}")


def _save_meeting_from_response(response: str, user_input: str = "") -> None:
    import re
    low = response.lower()
    if not any(k in low for k in ["scheduled", "created", "booked", "calendar event", "event created"]):
        return

    title = None
    for pat in [
        r'(?:titled|called|named)["\s]+([^"\'<\n]{3,60})',
        r'"([^"]{3,60})"',
        r"'([^']{3,60})'",
    ]:
        m = re.search(pat, response, re.IGNORECASE)
        if m:
            title = m.group(1).strip().rstrip(".,")
            break
    if not title:
        title = re.split(r'[.!?\n]', user_input)[0].strip()[:60] or "Meeting from Agent"

    date_val = str(_dt.date.today())
    dm = re.search(r'(\d{4}-\d{2}-\d{2})|(tomorrow)|(today)', response, re.IGNORECASE)
    if dm:
        raw = dm.group(0).lower()
        if raw == "tomorrow":
            date_val = str(_dt.date.today() + _dt.timedelta(days=1))
        elif raw == "today":
            date_val = str(_dt.date.today())
        elif re.match(r'\d{4}-\d{2}-\d{2}', raw):
            date_val = raw

    start = "00:00"
    tm = re.search(r'(\d{1,2}:\d{2}\s*(?:am|pm)?|\d{1,2}\s*(?:am|pm))', response, re.IGNORECASE)
    if tm:
        raw_t = tm.group(1).strip().lower()
        try:
            if ":" in raw_t and ("am" in raw_t or "pm" in raw_t):
                start = _dt.datetime.strptime(raw_t.replace(" ", ""), "%I:%M%p").strftime("%H:%M")
            elif "am" in raw_t or "pm" in raw_t:
                start = _dt.datetime.strptime(raw_t.replace(" ", ""), "%I%p").strftime("%H:%M")
            elif ":" in raw_t:
                start = raw_t[:5]
        except Exception:
            pass

    if _is_duplicate_meeting(title, date_val):
        return

    subj = f"Meeting Invitation: {title}"
    body = _default_email_body(title, date_val, start, "01:00", "")

    mtg = add_meeting(
        title=title, date=date_val, start_time=start, end_time="01:00",
        location="", attendees=[],
        email_subject=subj, email_body=body,
        status="Pending", source="agent",
    )
    if mtg and mtg.get("id"):
        st.session_state["last_saved_meeting_id"] = mtg["id"]
    sync_data_from_files()
    add_log(f"Meeting saved (response): {title} on {date_val}")