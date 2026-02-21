"""
ui/components/logs_ui.py
History & Logs — meetings, emails (with delete button), contacts, system logs.
FIX: Email tab mein har row mein delete button added.
"""
import os, csv
import streamlit as st
import pandas as pd
from ui.services.meeting_tracker import load_meetings, load_emails, delete_email_record
from ui.utils.session_state import add_log, sync_data_from_files


def _load_contacts() -> list:
    p = "data/contacts.csv"
    if not os.path.exists(p): return []
    try:
        with open(p,"r",encoding="utf-8") as f: return list(csv.DictReader(f))
    except Exception as e:
        add_log(f"contact load error: {e}","ERROR"); return []


def render_logs() -> None:
    st.markdown("""
    <h2 style="font-family:'Georgia',serif;color:#1a365d;margin:0 0 4px 0;font-size:1.5rem;">
        📜 History & Logs</h2>
    <p style="color:#718096;font-size:0.875rem;margin:0 0 16px 0;">
        Unified audit trail — all meetings and emails from Chat and Scheduler.</p>
    """, unsafe_allow_html=True)
    t1, t2, t3, t4 = st.tabs([
        "📅 Meetings History", "📧 Emails Sent",
        "👥 Contacts", "🖥️ System Logs",
    ])
    with t1: _render_meetings()
    with t2: _render_emails()
    with t3: _render_contacts()
    with t4: _render_logs()


# ─────────────────────────────────────────────────────────────────────────────
# MEETINGS
# ─────────────────────────────────────────────────────────────────────────────
def _render_meetings() -> None:
    meetings = load_meetings()
    sc = sum(1 for m in meetings if m.get("source")=="scheduler")
    ac = sum(1 for m in meetings if m.get("source") in ("agent","chat"))

    hc1, hc2 = st.columns([6,1])
    hc1.markdown(
        f"**{len(meetings)} total** &nbsp;·&nbsp; "
        f"<span style='color:#059669;font-size:0.85rem;'>📋 Scheduler: {sc}</span>"
        f"&nbsp;·&nbsp;"
        f"<span style='color:#2563eb;font-size:0.85rem;'>🤖 Agent: {ac}</span>",
        unsafe_allow_html=True,
    )
    if hc2.button("🔄", key="ref_mtg", help="Refresh"):
        sync_data_from_files(); st.rerun()

    if not meetings:
        st.info("📭 No meetings yet."); return

    cs, cf, csr = st.columns([3,2,2])
    search   = cs.text_input("Search", placeholder="Title, attendee, location...", key="lmtg_q")
    status_f = cf.selectbox("Status", ["All","Pending","Approved","Rejected"], key="lmtg_st")
    source_f = csr.selectbox("Source", ["All Sources","📋 Scheduler","🤖 Agent/Chat"], key="lmtg_src")

    filtered = meetings[:]
    if search:
        ql = search.lower()
        filtered = [m for m in filtered
                    if ql in m.get("title","").lower()
                    or any(ql in a.lower() for a in m.get("attendees",[]))
                    or ql in m.get("location","").lower()]
    if status_f != "All":       filtered = [m for m in filtered if m.get("status")==status_f]
    if source_f=="📋 Scheduler": filtered = [m for m in filtered if m.get("source")=="scheduler"]
    elif source_f=="🤖 Agent/Chat": filtered = [m for m in filtered if m.get("source") in ("agent","chat")]
    filtered = sorted(filtered, key=lambda x: x.get("created_at",""), reverse=True)

    SI = {"Approved":"🟢","Pending":"🟡","Rejected":"🔴"}
    SL = {"scheduler":"📋 Scheduler","agent":"🤖 Agent","chat":"🤖 Agent"}
    rows = []
    for m in filtered:
        s = m.get("status","Pending")
        rows.append({
            "Status":    SI.get(s,"⚪")+" "+s,
            "Source":    SL.get(m.get("source",""),"—"),
            "Title":     m.get("title","") or "—",
            "Date":      m.get("date","") or "—",
            "Time":      f"{m.get('start_time','') or '—'}–{m.get('end_time','') or '—'}",
            "Location":  (m.get("location","") or "—")[:30],
            "Attendees": ", ".join(m.get("attendees",[])) or "—",
            "Created":   m.get("created_at","")[:16] or "—",
            "ID":        m.get("id","")[:12] or "—",
        })

    df = pd.DataFrame(rows)
    def _hl(row):
        s = row["Status"]
        if "Approved" in s: return ["background-color:#f0fdf4"]*len(row)
        if "Rejected" in s: return ["background-color:#fef2f2"]*len(row)
        if "Pending"  in s: return ["background-color:#fefce8"]*len(row)
        return [""]*len(row)
    st.dataframe(df.style.apply(_hl, axis=1),
                 use_container_width=True, height=420, hide_index=True)
    st.caption(f"Showing {len(filtered)} of {len(meetings)} meetings")
    st.download_button("⬇️ Export CSV", df.to_csv(index=False),
                       "meetings_history.csv","text/csv", key="dl_mtg")


# ─────────────────────────────────────────────────────────────────────────────
# EMAILS — with delete button
# ─────────────────────────────────────────────────────────────────────────────
def _render_emails() -> None:
    emails = load_emails()

    eh1, eh2 = st.columns([5,1])
    eh1.caption(f"Total **{len(emails)}** email records")
    if eh2.button("🔄 Refresh", key="ref_email"):
        sync_data_from_files(); st.rerun()

    if not emails:
        st.info("📭 No emails recorded yet."); return

    # Filters
    fs1, fs2, fs3 = st.columns([3,2,2])
    search   = fs1.text_input("Search", placeholder="To, subject...", key="lemail_q")
    status_f = fs2.selectbox("Status", ["All","sent","rejected","failed","pending"], key="lemail_st")
    source_f = fs3.selectbox("Source", ["All","Agent (Chat)","Scheduler","HITL"], key="lemail_src")
    src_map  = {"All":None,"Agent (Chat)":"agent","Scheduler":"scheduler","HITL":"hitl"}

    filtered = emails[:]
    if search:
        ql = search.lower()
        filtered = [e for e in filtered
                    if ql in e.get("to","").lower() or ql in e.get("subject","").lower()]
    if status_f != "All":
        filtered = [e for e in filtered
                    if e.get("status","").lower() == status_f.lower()]
    src = src_map.get(source_f)
    if src:
        filtered = [e for e in filtered if e.get("source") == src]
    filtered = sorted(filtered, key=lambda x: x.get("sent_at",""), reverse=True)

    st.caption(f"Showing **{len(filtered)}** of {len(emails)} emails")

    if not filtered:
        st.info("📭 No emails match filters."); return

    # ── Email cards with delete button ────────────────────────────────────────
    BADGE = {
        "sent":     ("📤","#dbeafe","#1d4ed8","Sent"),
        #"delivered":("✅","#dcfce7","#166534","Delivered"),
        "rejected": ("❌","#fee2e2","#991b1b","Rejected"),
        "failed":   ("❌","#fee2e2","#991b1b","Failed"),
        "pending":  ("⏳","#fef9c3","#854d0e","Pending"),
    }
    SRC_LABEL = {"agent":"🤖 Chat","scheduler":"📋 Scheduler","hitl":"🤝 HITL"}

    for e in filtered:
        eid    = e.get("id","")
        status = e.get("status","sent").lower()
        icon, bg, color, label = BADGE.get(status, ("❓","#f3f4f6","#374151", status.title()))
        to_val = e.get("to","—")
        subj   = e.get("subject","—")
        sent_at= e.get("sent_at","")[:16]
        src_lbl= SRC_LABEL.get(e.get("source","agent"),"—")
        mid    = e.get("meeting_id","")

        col_card, col_del = st.columns([11, 1])
        with col_card:
            st.markdown(f"""
            <div style="background:{bg};border:1px solid {color}30;border-radius:10px;
                padding:10px 16px;margin:4px 0;display:flex;align-items:center;
                gap:12px;flex-wrap:wrap;">
                <span style="font-size:1.1rem;">{icon}</span>
                <div style="flex:1;min-width:0;">
                    <div style="font-weight:600;font-size:0.85rem;color:#1a202c;
                        white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                        📬 {to_val}</div>
                    <div style="font-size:0.8rem;color:#4a5568;margin-top:2px;
                        white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                        📋 {subj}</div>
                </div>
                <div style="text-align:right;flex-shrink:0;">
                    <span style="background:{color}20;color:{color};padding:3px 10px;
                        border-radius:20px;font-size:0.75rem;font-weight:700;">{label}</span>
                    <div style="font-size:0.72rem;color:#718096;margin-top:4px;">
                        {src_lbl} · {sent_at}</div>
                    {"<div style='font-size:0.7rem;color:#a0aec0;'>🔗 Meeting linked</div>" }
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col_del:
            st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
            if st.button("🗑️", key=f"del_email_{eid}", help="Delete this email record",
                         use_container_width=True):
                if delete_email_record(eid):
                    sync_data_from_files()
                    add_log(f"Email record deleted: {eid[:8]}")
                    st.rerun()

    # Export
    export = [{
        "Status": e.get("status",""), "Sent At": e.get("sent_at","")[:16],
        "To": e.get("to",""), "Subject": e.get("subject",""),
        "Source": e.get("source",""), "Meeting Linked": "Yes" if e.get("meeting_id") else "No",
        "Body Preview": (e.get("body_preview","") or "")[:80],
    } for e in filtered]
    st.download_button("⬇️ Export CSV", pd.DataFrame(export).to_csv(index=False),
                       "emails_history.csv","text/csv", key="dl_emails")


# ─────────────────────────────────────────────────────────────────────────────
# CONTACTS
# ─────────────────────────────────────────────────────────────────────────────
def _render_contacts() -> None:
    os.makedirs("data", exist_ok=True)
    fp = "data/contacts.csv"
    df = pd.read_csv(fp) if os.path.exists(fp) else pd.DataFrame(columns=["email","name","designation"])
    st.markdown("### 📇 Contacts Manager")
    edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, height=400, key="contacts_ed")
    st.caption(f"Total Contacts: {len(edited)}")
    cc1, cc2 = st.columns(2)
    with cc1:
        if st.button("💾 Save Contacts", use_container_width=True):
            edited.to_csv(fp, index=False)
            st.success("Contacts saved!")
    with cc2:
        st.download_button("⬇️ Export CSV", edited.to_csv(index=False),
                           "contacts_export.csv","text/csv",
                           use_container_width=True, key="dl_contacts")


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM LOGS
# ─────────────────────────────────────────────────────────────────────────────
def _render_logs() -> None:
    logs = st.session_state.get("system_logs", [])
    lc1, lc2, lc3 = st.columns([3,2,1])
    lc1.markdown(f"**{len(logs)} log entries**")
    lvl_f = lc2.selectbox("Level", ["All","INFO","WARNING","ERROR"], key="log_lvl")
    if lc3.button("🗑️ Clear", key="clear_logs", use_container_width=True):
        st.session_state.system_logs = []; st.rerun()

    if not logs:
        st.info("📭 No system logs yet."); return

    filtered = logs[:] if lvl_f=="All" else [l for l in logs if l.get("level")==lvl_f]
    filtered = list(reversed(filtered))
    ICON = {"INFO":"ℹ️","WARNING":"⚠️","ERROR":"❌"}
    rows = [{"Time":e.get("timestamp",""),
             "Level":f"{ICON.get(e.get('level','INFO'),'•')} {e.get('level','INFO')}",
             "Message":e.get("message","")} for e in filtered]
    df = pd.DataFrame(rows)
    def _clvl(row):
        s = row["Level"]
        if "ERROR"   in s: return ["","background-color:#fef2f2;color:#991b1b","background-color:#fef2f2"]
        elif "WARNING" in s: return ["","background-color:#fefce8;color:#92400e","background-color:#fefce8"]
        return ["","",""]
    st.dataframe(df.style.apply(_clvl, axis=1),
                 use_container_width=True, height=450, hide_index=True)
    st.caption(f"Showing {len(filtered)} of {len(logs)} log entries")