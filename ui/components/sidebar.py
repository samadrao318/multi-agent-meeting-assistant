"""
ui/components/sidebar.py
Sidebar — FIX: collapse/expand button + status indicators always visible.
"""
import os
import streamlit as st
from ui.utils.session_state import clear_session, reinit_agent, add_log, sync_data_from_files


def render_sidebar() -> None:
    with st.sidebar:
        _render_logo()
        _render_status()
        st.divider()
        _render_controls()
        st.divider()
        _render_stats()
        st.divider()
        _render_footer()


def _render_logo():
    st.markdown("""
    <div style="background:linear-gradient(135deg,#0f2027,#203a43,#2c5364);
        border-radius:12px;padding:18px 16px;text-align:center;margin-bottom:16px;
        box-shadow:0 4px 15px rgba(0,0,0,0.2);">
        <div style="font-size:2.4rem;margin-bottom:4px;">🤖</div>
        <div style="font-family:'Georgia',serif;font-size:1rem;font-weight:700;
            color:#e0e8ff;letter-spacing:0.5px;">Multi-Agent System</div>
        <div style="font-size:0.7rem;color:#7fa8c9;margin-top:2px;
            letter-spacing:1px;text-transform:uppercase;">AI Automation Platform</div>
    </div>
    """, unsafe_allow_html=True)


def _status_row(label: str, ok: bool, warn_msg: str = "") -> None:
    icon  = "🟢" if ok else ("🟡" if warn_msg else "🔴")
    color = "#2ecc71" if ok else ("#f39c12" if warn_msg else "#e74c3c")
    sub   = "Connected" if ok else (warn_msg or "Disconnected")
    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;
        padding:6px 10px;background:#f8fafc;border-radius:8px;margin-bottom:6px;
        border:1px solid #e8edf5;">
        <span style="font-size:0.85rem;font-weight:600;color:#2d3748;">{icon} {label}</span>
        <span style="font-size:0.75rem;color:{color};font-weight:600;">{sub}</span>
    </div>
    """, unsafe_allow_html=True)


def _render_status():
    st.markdown("""<div style="font-size:0.7rem;font-weight:700;color:#888;
        text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">
        System Status</div>""", unsafe_allow_html=True)

    azure_ok  = bool(
        os.getenv("AZURE_OPENAI_ENDPOINT") and
        os.getenv("AZURE_OPENAI_API_KEY") and
        os.getenv("AZURE_OPENAI_DEPLOYMENT")
    )
    google_ok = os.path.exists("credentials.json")
    agent_ok  = st.session_state.get("initialized", False)
    init_err  = st.session_state.get("init_error")

    _status_row("Azure OpenAI", azure_ok)
    _status_row("Google APIs",  google_ok, "No Credentials" if not google_ok else "")
    _status_row("AI Agent",     agent_ok,  "Not Ready"      if not agent_ok  else "")

    if agent_ok:
        dep = os.getenv("AZURE_OPENAI_DEPLOYMENT","?")
        st.caption(f"Model: `{dep}`")
    elif init_err:
        with st.expander("⚠️ Init Error", expanded=False):
            st.error(init_err[:300])

    tid = st.session_state.get("thread_id","—")
    st.markdown(f"""
    <div style="background:#f0f4f8;border-radius:6px;padding:6px 10px;
        font-size:0.75rem;color:#4a5568;margin-top:4px;font-family:monospace;">
        🔑 {tid}</div>
    """, unsafe_allow_html=True)


def _render_controls():
    st.markdown("""<div style="font-size:0.7rem;font-weight:700;color:#888;
        text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">
        Controls</div>""", unsafe_allow_html=True)

    hitl_val = st.toggle(
        "🤝 Human-in-the-Loop",
        value=st.session_state.get("enable_hitl", True),
        help="Agent pauses for approval before sending emails / creating events.",
        key="hitl_toggle_sidebar",
    )
    if hitl_val != st.session_state.get("enable_hitl", True):
        st.session_state.enable_hitl = hitl_val
        reinit_agent()
        add_log(f"HITL toggled: {'enabled' if hitl_val else 'disabled'}")
        st.rerun()

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🗑️ Clear Chat", use_container_width=True, help="Clear messages & start new thread"):
            clear_session(); sync_data_from_files(); st.rerun()
    with c2:
        if st.button("🔄 Reinit", use_container_width=True, help="Re-initialize AI agent"):
            reinit_agent(); st.rerun()

    # Show HITL status notice
    if st.session_state.get("hitl_pending"):
        st.markdown("""
        <div style="background:#fef3c7;border:1px solid #f59e0b;border-radius:8px;
            padding:8px 12px;margin-top:8px;font-size:0.8rem;color:#92400e;
            text-align:center;font-weight:600;">
            ⏸️ Awaiting Your Approval
        </div>
        """, unsafe_allow_html=True)


def _render_stats():
    st.markdown("""<div style="font-size:0.7rem;font-weight:700;color:#888;
        text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">
        Quick Stats</div>""", unsafe_allow_html=True)

    meetings = st.session_state.get("meetings", [])
    emails   = st.session_state.get("emails_sent", [])
    messages = st.session_state.get("messages", [])
    pending  = sum(1 for m in meetings if m.get("status")=="Pending")
    approved = sum(1 for m in meetings if m.get("status")=="Approved")

    stats = [
        ("📅","Meetings",  len(meetings)),
        ("📧","Emails",    len(emails)),
        ("🟡","Pending",   pending),
        ("🟢","Approved",  approved),
        ("💬","Messages",  len(messages)),
    ]
    cols = st.columns(2)
    for i, (icon, label, val) in enumerate(stats):
        with cols[i % 2]:
            st.markdown(f"""
            <div style="background:#f8fafc;border:1px solid #e8edf5;border-radius:8px;
                padding:8px 6px;text-align:center;margin-bottom:6px;">
                <div style="font-size:1.1rem;">{icon}</div>
                <div style="font-size:1.2rem;font-weight:700;color:#1a365d;">{val}</div>
                <div style="font-size:0.65rem;color:#718096;text-transform:uppercase;
                    letter-spacing:0.5px;">{label}</div>
            </div>
            """, unsafe_allow_html=True)


def _render_footer():
    st.markdown("""
    <div style="text-align:center;padding:8px 0;">
        <div style="font-size:0.7rem;color:#a0aec0;">v2.0 · Production Ready</div>
        <div style="font-size:0.65rem;color:#cbd5e0;margin-top:2px;">
            LangChain · LangGraph · Azure OpenAI</div>
    </div>
    """, unsafe_allow_html=True)