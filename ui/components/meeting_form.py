"""
ui/components/meeting_form.py
Meeting Scheduler.
FIX: Email sirf Approve karne pe jati hai (Schedule karne pe nahi)
FIX: Approve pe original invitation email body use hoti hai
"""
import os, csv
import streamlit as st
from datetime import date, time, timedelta
from ui.utils.session_state import add_log, add_message, get_agent_config, sync_data_from_files
from ui.services.meeting_tracker import add_meeting, load_meetings, update_meeting_status, delete_meeting
from ui.services.email_service import send_and_save_email


def _load_contacts() -> list:
    p = "data/contacts.csv"
    if not os.path.exists(p): return []
    try:
        with open(p,"r",encoding="utf-8") as f: return list(csv.DictReader(f))
    except Exception as e: add_log(f"contact load: {e}","ERROR"); return []

def _parse_emails(text: str) -> list:
    return [p.strip() for p in text.split(",") if "@" in p and "." in p]

def _default_body(title, d, s, e, loc) -> str:
    return (
        f"Dear Attendee,\n\nYou are invited to:\n\n"
        f"📅 {title}\n📆 {d}\n🕐 {s} – {e}\n"
        f"📍 {loc or 'To be confirmed'}\n\n"
        f"Please confirm your attendance.\n\nBest regards,\nMeeting Organizer"
    )


def render_meeting_form() -> None:
    st.markdown("""
    <h2 style="font-family:'Georgia',serif;color:#1a365d;margin:0 0 4px 0;font-size:1.5rem;">
        📅 Meeting Scheduler</h2>
    <p style="color:#718096;font-size:0.875rem;margin:0 0 12px 0;">
        Schedule meetings and send email invitations to attendees.</p>
    """, unsafe_allow_html=True)
    t1, t2 = st.tabs(["📝 New Meeting", "📋 Meeting History"])
    with t1: _render_form()
    with t2: _render_history()


def _render_form() -> None:
    contacts = _load_contacts()
    opts = [f"{c.get('name','?')} <{c.get('email','')}>".strip()
            for c in contacts if c.get("email")]

    with st.form("meeting_form", clear_on_submit=False):
        st.markdown("#### 📋 Meeting Details")
        c1, c2 = st.columns(2)
        with c1:
            title        = st.text_input("Meeting Title *", placeholder="Q4 Planning", key="mf_title")
            meeting_date = st.date_input("Date *", value=date.today()+timedelta(days=1),
                                         min_value=date.today(), key="mf_date")
            location     = st.text_input("Location / Link",
                                         placeholder="Room B or meet.google.com/...", key="mf_loc")
        with c2:
            tc1, tc2   = st.columns(2)
            start_time = tc1.time_input("Start *", value=time(10,0), key="mf_start")
            end_time   = tc2.time_input("End *",   value=time(11,0), key="mf_end")
            if opts:
                selected = st.multiselect("Attendees from Contacts", opts, key="mf_sel")
            else:
                selected = []
                st.info("💡 No contacts yet — add in History & Logs → Contacts tab.")
            extra = st.text_input("Additional Emails",
                                  placeholder="alice@x.com, bob@x.com", key="mf_extra")

        st.markdown("#### 📧 Email Invitation")
        ec1, _ = st.columns([4,1])
        subject = ec1.text_input("Subject", placeholder="Leave blank to auto-generate", key="mf_subj")
        body    = st.text_area("Body", height=130,
                               placeholder="Leave blank to auto-generate...", key="mf_body")

        # INFO: Email hamesha Approve karne pe jayegi
        st.info("ℹ️ Email invitation automatically sends when you **Approve** the meeting in Meeting History.")

        st.markdown("---")
        ba, bb, bc = st.columns(3)
        btn_check = ba.form_submit_button("🔍 Check Availability", use_container_width=True)
        btn_sched = bb.form_submit_button("📅 Schedule Only",      use_container_width=True)
        btn_all   = bc.form_submit_button("📅 Schedule & Send Later", use_container_width=True, type="primary")

    # Collect attendees
    attendees = []
    for sel in selected:
        if "<" in sel and ">" in sel:
            em = sel.split("<")[1].rstrip(">").strip()
            if em: attendees.append(em)
    attendees = list(dict.fromkeys(attendees + _parse_emails(extra)))

    if btn_check:
        _check_avail(title, meeting_date, start_time, end_time)
    elif btn_sched:
        if not title.strip(): st.error("⚠️ Meeting title is required."); return
        if start_time >= end_time: st.error("⚠️ End time must be after start time."); return
        subj = subject.strip() or f"Meeting Invitation: {title}"
        bod  = body.strip()    or _default_body(title, meeting_date, start_time, end_time, location)
        _save_meeting(title, meeting_date, start_time, end_time,
                      location, attendees, subj, bod)
    elif btn_all:
        if not title.strip(): st.error("⚠️ Meeting title is required."); return
        if start_time >= end_time: st.error("⚠️ End time must be after start time."); return
        subj = subject.strip() or f"Meeting Invitation: {title}"
        bod  = body.strip()    or _default_body(title, meeting_date, start_time, end_time, location)
        # ✅ FIX: Email nahi bhejte — sirf save karte hain, Approve pe jayegi
        _save_meeting(title, meeting_date, start_time, end_time,
                      location, attendees, subj, bod)
        for k in ["mf_title","mf_date","mf_loc","mf_start","mf_end",
                  "mf_sel","mf_extra","mf_subj","mf_body"]:
            st.session_state.pop(k, None)
        st.rerun()


def _check_avail(title, meeting_date, start_time, end_time) -> None:
    from ui.services.agent_runner import stream_agent
    sup = st.session_state.get("supervisor")
    if not sup:
        st.info(f"📅 {meeting_date} {start_time}–{end_time} — agent not connected."); return
    with st.spinner("🔍 Checking..."):
        for ev in stream_agent(sup,
            f"Check calendar on {meeting_date} from {start_time} to {end_time}.",
            get_agent_config()):
            if ev.get("type") == "message":   st.info(f"📅 {ev['content']}"); break
            elif ev.get("type") == "error":   st.warning(ev.get("content","")); break


def _save_meeting(title, meeting_date, start_time, end_time,
                  location, attendees, subject, body) -> None:
    """Meeting ko Pending status mein save karta hai. Email Approve pe jayegi."""
    mtg = add_meeting(
        title=title, date=str(meeting_date),
        start_time=str(start_time), end_time=str(end_time),
        location=location, attendees=attendees,
        email_subject=subject, email_body=body,
        status="Pending", source="scheduler",
    )
    sync_data_from_files()
    add_log(f"Meeting saved (Pending): {title} on {meeting_date}")
    st.success(f"✅ **'{title}'** scheduled for **{meeting_date}**! — Go to **Meeting History** to Approve & Send email.")
    if location:  st.caption(f"📍 {location}")
    if attendees: st.caption(f"👥 {', '.join(attendees)}")
    add_message("system", f"📅 '{title}' scheduled on {meeting_date} — Pending approval")


# ─────────────────────────────────────────────────────────────────────────────
# HISTORY
# ─────────────────────────────────────────────────────────────────────────────
def _render_history() -> None:
    meetings = load_meetings()
    if not meetings:
        st.info("📭 No meetings yet."); return

    c1, c2, c3 = st.columns([2,2,4])
    sf  = c1.selectbox("Status", ["All","Pending","Approved","Rejected"],
                       key="hist_sf", label_visibility="collapsed")
    src = c2.selectbox("Source", ["All Sources","Via Scheduler","Via Chat/Agent"],
                       key="hist_src", label_visibility="collapsed")
    q   = c3.text_input("Search", placeholder="🔍 Title or attendee...",
                        key="hist_q", label_visibility="collapsed")

    filtered = meetings[:]
    if sf != "All":              filtered = [m for m in filtered if m.get("status")==sf]
    if src=="Via Scheduler":     filtered = [m for m in filtered if m.get("source")=="scheduler"]
    elif src=="Via Chat/Agent":  filtered = [m for m in filtered if m.get("source") in ("agent","chat")]
    if q:
        ql = q.lower()
        filtered = [m for m in filtered
                    if ql in m.get("title","").lower()
                    or any(ql in a.lower() for a in m.get("attendees",[]))]
    filtered = sorted(filtered, key=lambda x: x.get("created_at",""), reverse=True)
    st.caption(f"Showing **{len(filtered)}** of **{len(meetings)}** meetings")

    ICON = {"Approved":"🟢","Pending":"🟡","Rejected":"🔴"}
    for m in filtered:
        mid    = m["id"]
        status = m.get("status","Pending")
        atts   = m.get("attendees",[])
        att_str= ", ".join(atts[:3])+(f" +{len(atts)-3} more" if len(atts)>3 else "")
        src_lbl= {"scheduler":"📋","agent":"🤖","chat":"🤖"}.get(m.get("source",""),"📋")

        with st.expander(
            f"{ICON.get(status,'⚪')} {src_lbl}  **{m.get('title','—')}**"
            f"  ·  {m.get('date','—')}  ·  {m.get('start_time','—')}–{m.get('end_time','—')}"
            f"  ·  *{status}*", expanded=False):

            d1,d2,d3,d4 = st.columns(4)
            d1.metric("Status",    f"{ICON.get(status,'⚪')} {status}")
            d2.metric("Date",      m.get("date","—"))
            d3.metric("Time",      f"{m.get('start_time','—')}–{m.get('end_time','—')}")
            d4.metric("Attendees", len(atts))
            if m.get("location"):      st.write(f"📍 **Location:** {m['location']}")
            if att_str:                st.write(f"👥 **Attendees:** {att_str}")
            if m.get("email_subject"): st.write(f"📧 **Subject:** {m['email_subject']}")
            if m.get("email_body"):
                with st.expander("📄 Email Body"):
                    st.text(m["email_body"])
            st.caption(f"Source: {m.get('source','—')} | Created: {m.get('created_at','')[:16]} | ID: {mid[:16]}")
            st.divider()
            ac, rc, dc = st.columns([2,2,1])

            # ✅ APPROVE button — original invitation email bhejta hai
            if ac.button(
                "✅ Approved" if status=="Approved" else "✅ Approve",
                key=f"app_{mid}", use_container_width=True,
                disabled=(status=="Approved"), type="primary" if status=="Pending" else "secondary"):
                update_meeting_status(mid, "Approved")
                sync_data_from_files()
                if atts:
                    sent = _send_invitation_emails(m)
                    st.success(f"✅ Approved! 📧 Email sent to {sent}/{len(atts)} attendees.")
                else:
                    st.success("✅ Approved! (No attendees to email)")
                st.rerun()

            # ❌ REJECT button — cancellation notice bhejta hai
            if rc.button(
                "❌ Rejected" if status=="Rejected" else "❌ Reject",
                key=f"rej_{mid}", use_container_width=True, disabled=(status=="Rejected")):
                update_meeting_status(mid, "Rejected")
                sync_data_from_files()
                if atts:
                    _send_rejection_email(m)
                    st.error(f"❌ Rejected. Cancellation notice sent to {len(atts)} attendees.")
                else:
                    st.error("❌ Rejected.")
                st.rerun()

            if dc.button("🗑️", key=f"del_{mid}", use_container_width=True, help="Delete"):
                delete_meeting(mid); sync_data_from_files(); st.rerun()


def _send_invitation_emails(meeting: dict) -> int:
    """
    Approve hone pe original invitation email bhejta hai.
    Returns: sent_count
    """
    atts    = meeting.get("attendees", [])
    subject = meeting.get("email_subject", f"Meeting Invitation: {meeting.get('title','Meeting')}")
    body    = meeting.get("email_body", "")

    # Agar body missing ho to default generate karo
    if not body:
        body = _default_body(
            meeting.get("title","Meeting"),
            meeting.get("date",""),
            meeting.get("start_time",""),
            meeting.get("end_time",""),
            meeting.get("location",""),
        )

    sent_count = 0
    for to in atts:
        res = send_and_save_email(
            to=to, subject=subject, body=body,
            source="scheduler", approval_status="approved",
            meeting_id=meeting.get("id"),
            force_gmail=True,
        )
        if res["sent"]:
            sent_count += 1
            add_log(f"Invitation email sent to {to} for meeting: {meeting.get('title')}")
        elif res.get("error") != "duplicate":
            add_log(f"Invitation email FAILED to {to} — {res.get('error')}", "WARNING")

    return sent_count


def _send_rejection_email(meeting: dict) -> None:
    """Reject hone pe cancellation notice bhejta hai."""
    atts  = meeting.get("attendees", [])
    title = meeting.get("title", "Meeting")
    d     = meeting.get("date", "")
    s     = meeting.get("start_time", "")
    e     = meeting.get("end_time", "")

    subj = f"❌ Cancelled: {title}"
    bod  = (
        f"Dear Attendee,\n\nThe following meeting has been cancelled:\n\n"
        f"📅 {title}\n📆 {d}\n🕐 {s}–{e}\n\n"
        f"We apologize for any inconvenience.\n\nBest regards,\nMeeting Organizer"
    )

    for to in atts:
        res = send_and_save_email(
            to=to, subject=subj, body=bod,
            source="scheduler", approval_status="rejected",
            meeting_id=meeting.get("id"),
            force_gmail=False,
        )
        add_log(f"Rejection email to={to} sent={res['sent']}")