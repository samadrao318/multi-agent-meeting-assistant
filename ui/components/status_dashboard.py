"""ui/components/status_dashboard.py"""
import streamlit as st
import pandas as pd
from ui.services.meeting_tracker import load_meetings, load_emails, update_meeting_status, get_meetings_stats, get_emails_stats, save_email_record
from ui.utils.session_state import add_log, sync_data_from_files

def render_dashboard():
    st.markdown("""<h2 style="font-family:'Georgia',serif;color:#1a365d;margin:0 0 4px 0;font-size:1.5rem;">
        📊 Status Dashboard</h2>
        <p style="color:#718096;font-size:0.875rem;margin:0 0 16px 0;">Real-time overview of meetings and email activity.</p>""",
        unsafe_allow_html=True)
    c1,c2 = st.columns([6,1])
    with c2:
        if st.button("🔄 Refresh", use_container_width=True):
            sync_data_from_files(); st.rerun()
    _render_metrics()
    st.divider()
    tab1, tab2 = st.tabs(["📅 Meetings","🤖 Emails via Agent"])
    with tab1: _render_meetings_dashboard()
    with tab2: _render_agent_emails_dashboard()

def _render_metrics():
    mtg = get_meetings_stats(); em = get_emails_stats()
    cols = st.columns(7)
    def card(col, icon, label, val, color="#1a365d"):
        col.markdown(f"""<div style="background:white;border-radius:10px;padding:14px 10px;
            border:1px solid #e2e8f0;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
            <div style="font-size:1.4rem;">{icon}</div>
            <div style="font-size:1.5rem;font-weight:800;color:{color};line-height:1.2;margin-top:2px;">{val}</div>
            <div style="font-size:0.68rem;color:#718096;text-transform:uppercase;letter-spacing:0.5px;margin-top:2px;">{label}</div>
        </div>""", unsafe_allow_html=True)
    card(cols[0],"📅","Total Meetings", mtg["total"])
    card(cols[1],"🟢","Approved",       mtg["approved"], "#059669")
    card(cols[2],"🟡","Pending",         mtg["pending"],  "#d97706")
    card(cols[3],"🔴","Rejected",        mtg["rejected"], "#dc2626")
    card(cols[4],"📧","Total Emails",    em["total"])
    card(cols[5],"🤖","Via Agent",       em["from_chat"]+em["from_hitl"])
    card(cols[6],"📋","Via Scheduler",   em["from_scheduler"])

def _render_meetings_dashboard():
    meetings = load_meetings()
    if not meetings: st.info("📭 No meetings yet."); return
    c1,c2,c3,c4 = st.columns([2,2,2,3])
    with c1: sf  = st.selectbox("Status", ["All","Pending","Approved","Rejected"], key="dash_status")
    with c2: src = st.selectbox("Source", ["All","Via Agent","Via Scheduler"],      key="dash_source")
    with c3: srt = st.selectbox("Sort",   ["Date (Newest)","Date (Oldest)","Title A–Z"], key="dash_sort")
    with c4: q   = st.text_input("Search", placeholder="Title, attendee...", key="dash_search")
    filtered = meetings[:]
    if sf != "All":                filtered = [m for m in filtered if m.get("status")==sf]
    if src == "Via Agent":         filtered = [m for m in filtered if m.get("source") in ("chat","agent")]
    elif src == "Via Scheduler":   filtered = [m for m in filtered if m.get("source")=="scheduler"]
    if q:
        ql=q.lower()
        filtered=[m for m in filtered if ql in m.get("title","").lower() or any(ql in a.lower() for a in m.get("attendees",[]))]
    if srt=="Date (Newest)":   filtered=sorted(filtered,key=lambda x:x.get("date",""),reverse=True)
    elif srt=="Date (Oldest)": filtered=sorted(filtered,key=lambda x:x.get("date",""))
    elif srt=="Title A–Z":     filtered=sorted(filtered,key=lambda x:x.get("title","").lower())
    st.caption(f"Showing **{len(filtered)}** of {len(meetings)} meetings")
    if not filtered: st.warning("No meetings match filters."); return
    rows = []
    for m in filtered:
        rows.append({"🏷️ Status":m.get("status","Pending"),"📋 Title":m.get("title",""),
            "📅 Date":m.get("date",""),"🕐 Time":f"{m.get('start_time','')}–{m.get('end_time','')}",
            "📍 Location":m.get("location","—")[:30],"👥 Attendees":len(m.get("attendees",[])),
            "📂 Source":m.get("source","scheduler").title(),"🆔 ID":m.get("id","")[:12]})
    def hl(row):
        s=row["🏷️ Status"]
        if s=="Approved": return ["background-color:#f0fdf4"]*len(row)
        if s=="Pending":  return ["background-color:#fefce8"]*len(row)
        if s=="Rejected": return ["background-color:#fef2f2"]*len(row)
        return [""]*len(row)
    df = pd.DataFrame(rows)
    st.dataframe(df.style.apply(hl,axis=1), use_container_width=True, height=320, hide_index=True)
    st.markdown("##### ✏️ Update Meeting Status")
    uc1,uc2,uc3 = st.columns([4,2,1])
    opts = {m["id"]:f"{m['title']} ({m['date']})" for m in filtered}
    sel_id  = uc1.selectbox("Meeting", list(opts.keys()), format_func=lambda x:opts.get(x,x), key="dash_update_meeting", label_visibility="collapsed")
    new_st  = uc2.selectbox("Status",  ["Pending","Approved","Rejected"], key="dash_update_status", label_visibility="collapsed")
    if uc3.button("💾 Update", type="primary", use_container_width=True, key="dash_update_btn"):
        if update_meeting_status(sel_id, new_st):
            sync_data_from_files(); add_log(f"Dashboard: {sel_id[:8]} → {new_st}")
            st.success(f"✅ Updated to **{new_st}**"); st.rerun()
        else: st.error("Update failed.")

def _render_agent_emails_dashboard():
    all_emails = load_emails()
    agent_emails = [e for e in all_emails if e.get("source") in ("agent","hitl")]
    st.markdown("""<div style="background:#f0f4ff;border-radius:10px;padding:10px 16px;
        border-left:4px solid #3b82f6;margin-bottom:12px;font-size:0.85rem;color:#1e40af;">
        ℹ️ Emails attempted via Chat tab.
        <strong>✅ Sent</strong> = approved &amp; delivered.
        <strong>❌ Rejected</strong> = rejected in HITL panel.</div>""", unsafe_allow_html=True)
    q = st.text_input("Search", placeholder="Recipient or subject...", key="email_search_agent")
    filtered = agent_emails[:]
    if q:
        ql=q.lower()
        filtered=[e for e in filtered if ql in e.get("to","").lower() or ql in e.get("subject","").lower()]
    filtered=sorted(filtered,key=lambda x:x.get("sent_at",""),reverse=True)
    if filtered:
        st.caption(f"Showing **{len(filtered)}** of {len(agent_emails)} agent emails")
        _render_email_table(filtered, key_suffix="agent")
    else:
        st.info("📭 No agent emails yet.")
    st.divider()
    st.markdown("##### ➕ Manually Record a Missed Email")
    with st.form("manual_email_form"):
        c1,c2 = st.columns(2)
        manual_to      = c1.text_input("To (email)", placeholder="recipient@example.com")
        manual_subject = c2.text_input("Subject",    placeholder="Email subject")
        manual_status  = st.selectbox("Status", ["Sent","Rejected","Failed"])
        submitted = st.form_submit_button("💾 Save Email Record", type="primary", use_container_width=True)
    if submitted:
        if manual_to.strip() and manual_subject.strip():
            save_email_record(to=manual_to.strip(),subject=manual_subject.strip(),status=manual_status,source="agent")
            sync_data_from_files(); add_log(f"Manual email saved: {manual_to}"); st.success(f"✅ Saved — {manual_to}"); st.rerun()
        else: st.error("To and Subject are required.")

def _render_email_table(emails, key_suffix=""):
    rows=[]
    for e in emails[:100]:
        status=e.get("status","Sent")
        sd = "✅ Sent" if status.lower()=="sent" else ("❌ Rejected" if status.lower()=="rejected" else ("❌ Failed" if status.lower()=="failed" else f"⏳ {status}"))
        rows.append({"📅 Sent At":e.get("sent_at","")[:16],"📬 To":e.get("to",""),
            "📋 Subject":e.get("subject","")[:60],"✅ Status":sd,
            "🔗 Meeting":"✓" if e.get("meeting_id") else "—","📂 Source":e.get("source","agent").title()})
    df=pd.DataFrame(rows)
    def hl(row):
        s=row["✅ Status"]
        if "Sent" in s:     return ["background-color:#f0fdf4"]*len(row)
        if "Rejected" in s: return ["background-color:#fef2f2"]*len(row)
        if "Failed" in s:   return ["background-color:#fef2f2"]*len(row)
        return [""]*len(row)
    st.dataframe(df.style.apply(hl,axis=1), use_container_width=True, height=320, hide_index=True)
    csv=pd.DataFrame([{"sent_at":e.get("sent_at"),"to":e.get("to"),"subject":e.get("subject"),
        "status":e.get("status"),"source":e.get("source"),"meeting_id":e.get("meeting_id")} for e in emails]).to_csv(index=False)
    st.download_button("⬇️ Download CSV", csv, f"emails_{key_suffix}.csv","text/csv", key=f"dl_emails_{key_suffix}")