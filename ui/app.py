"""
ui/app.py
Multi-Agent Meeting & Email Automation System
Main Streamlit Application Entry Point.

Run: streamlit run ui/app.py
"""
import os
import sys
import logging

# ── PATH SETUP ────────────────────────────────────────────────────────────────
_UI_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT   = os.path.dirname(_UI_DIR)
for _p in [_ROOT, _UI_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
import streamlit as st

if "force_sidebar" not in st.session_state:
    st.session_state.force_sidebar = True

st.set_page_config(
    page_title="AI Multi-Agent System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded" if st.session_state.force_sidebar else "collapsed",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": "Multi-Agent Meeting & Email Automation System v2.0",
    },
)

# ── GLOBAL CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Source+Sans+3:wght@400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Source Sans 3', 'Segoe UI', sans-serif;
}
.block-container {
    padding-top: 1rem !important;
    padding-bottom: 1rem !important;
    max-width: 1400px;
}
#MainMenu, footer {
        visibility: hidden;
    }
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
    border-right: 1px solid #e2e8f0;
}
[data-testid="stSidebar"] .block-container {
    padding-top: 1rem !important;
}
[data-testid="collapsedControl"] {
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    background: white !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 50% !important;
    width: 32px !important;
    height: 32px !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.08) !important;
    z-index: 999 !important;
}
[data-testid="collapsedControl"]:hover {
    background: #f1f5f9 !important;
    border-color: #2563eb !important;
}
[data-testid="collapsedControl"] svg {
    color: #2563eb !important;
}
.stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1e3a5f, #2563eb) !important;
    border: none !important;
    color: white !important;
}
.stForm {
    background: white;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
    padding: 20px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}
[data-testid="metric-container"] {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 12px 16px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.05);
}
.streamlit-expanderHeader {
    background: #f8fafc !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
[data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid #e2e8f0;
}
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    border-radius: 8px !important;
    border: 1px solid #e2e8f0 !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #2563eb !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.1) !important;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    background: #f8fafc;
    border-radius: 10px;
    padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
}
.stTabs [aria-selected="true"] {
    background: white !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.1) !important;
}
.stSuccess, .stError, .stWarning, .stInfo { border-radius: 10px !important; }
#MainMenu, footer, header { visibility: hidden; }
hr { border: none; border-top: 1px solid #e2e8f0; margin: 12px 0; }
.stSpinner > div {
    border-color: #2563eb transparent transparent transparent !important;
}
</style>
""", unsafe_allow_html=True)

# ── IMPORTS ───────────────────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

from ui.utils.session_state import init_session_state, add_log, sync_data_from_files
from ui.services.meeting_tracker import get_meetings_stats, get_emails_stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── SESSION + DATA ────────────────────────────────────────────────────────────
init_session_state()
sync_data_from_files()


# ── AGENT INIT ────────────────────────────────────────────────────────────────
def _try_init_agent() -> None:
    if st.session_state.get("initialized"):
        return
    azure_ready = bool(
        os.getenv("AZURE_OPENAI_ENDPOINT") and
        os.getenv("AZURE_OPENAI_API_KEY") and
        os.getenv("AZURE_OPENAI_DEPLOYMENT")
    )
    if not azure_ready:
        add_log("Azure credentials missing", "ERROR")
        st.session_state.init_error = "Azure OpenAI credentials missing from .env"
        return
    try:
        with st.spinner("⚙️ Initializing AI agents..."):
            from ui.services.agent_runner import initialize_agent
            model, supervisor = initialize_agent(
                enable_hitl=st.session_state.get("enable_hitl", True)
            )
            st.session_state.model       = model
            st.session_state.supervisor  = supervisor
            st.session_state.initialized = True
            st.session_state.init_error  = None
            add_log("Agent initialized ✅")
    except EnvironmentError as e:
        st.session_state.init_error = str(e); add_log(f"Env error: {e}", "ERROR")
    except ImportError as e:
        st.session_state.init_error = f"Import error: {e}"; add_log(f"Import error: {e}", "ERROR")
    except RuntimeError as e:
        st.session_state.init_error = str(e); add_log(f"Runtime error: {e}", "ERROR")
    except Exception as e:
        st.session_state.init_error = f"Unexpected: {str(e)[:200]}"
        add_log(f"Init error: {e}", "ERROR")
        logger.error("Agent init failed", exc_info=True)


_try_init_agent()


# ── HEADER ────────────────────────────────────────────────────────────────────
def _render_header() -> None:
    azure_ok   = bool(os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_API_KEY"))
    google_ok  = os.path.exists("credentials.json")
    agent_ok   = st.session_state.get("initialized", False)
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "Not configured")

    def badge(ok, ok_label, fail_label, warn=False):
        if ok:
            return (f'<span style="background:#dcfce7;color:#166534;padding:3px 10px;'
                    f'border-radius:20px;font-size:0.75rem;font-weight:700;">🟢 {ok_label}</span>')
        elif warn:
            return (f'<span style="background:#fef9c3;color:#854d0e;padding:3px 10px;'
                    f'border-radius:20px;font-size:0.75rem;font-weight:700;">🟡 {fail_label}</span>')
        else:
            return (f'<span style="background:#fee2e2;color:#991b1b;padding:3px 10px;'
                    f'border-radius:20px;font-size:0.75rem;font-weight:700;">🔴 {fail_label}</span>')

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0f2027 0%,#203a43 50%,#1a365d 100%);
        border-radius:16px;padding:20px 28px;margin-bottom:16px;
        box-shadow:0 8px 32px rgba(0,0,0,0.2);
        display:flex;align-items:center;justify-content:space-between;
        flex-wrap:wrap;gap:12px;">
        <div>
            <div style="font-family:'Playfair Display','Georgia',serif;font-size:1.4rem;
                font-weight:700;color:#e8f4fd;letter-spacing:0.3px;line-height:1.2;">
                🤖 AI Multi-Agent Automation System</div>
            <div style="font-size:0.8rem;color:#7fa8c9;margin-top:4px;">
                Calendar · Email · Contacts · Human-in-the-Loop</div>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
            {badge(azure_ok,  "Azure Connected",  "Azure Missing")}
            {badge(google_ok, "Google Connected", "No Google Creds", warn=True)}
            {badge(agent_ok,  "Agent Ready",      "Agent Not Ready")}
            <span style="background:#1e3a5f;color:#93c5fd;padding:3px 10px;
                border-radius:20px;font-size:0.75rem;font-weight:700;">
                ⚡ {deployment}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


_render_header()


# ── METRICS ───────────────────────────────────────────────────────────────────
def _render_metrics() -> None:
    mtg       = get_meetings_stats()
    em        = get_emails_stats()
    msg_count = len(st.session_state.get("messages", []))
    hitl_on   = st.session_state.get("enable_hitl", True)

    cols = st.columns(6)
    cols[0].metric("📅 Meetings", mtg["total"])
    cols[1].metric("🟢 Approved", mtg["approved"])
    cols[2].metric("🟡 Pending",  mtg["pending"])
    cols[3].metric("📧 Emails",   em["total"])
    cols[4].metric("💬 Messages", msg_count)
    cols[5].metric("🤝 HITL",     "ON" if hitl_on else "OFF")


_render_metrics()
st.divider()

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
from ui.components.sidebar import render_sidebar
render_sidebar()

# ── INIT ERROR ────────────────────────────────────────────────────────────────
init_error = st.session_state.get("init_error")
if init_error and not st.session_state.get("initialized"):
    if "Azure" in init_error or "credentials" in init_error.lower():
        st.error(
            f"❌ **Azure OpenAI Setup Required** — {init_error}\n\n"
            "Add `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, "
            "`AZURE_OPENAI_DEPLOYMENT` to `.env` then click **🔄 Reinit**."
        )
    else:
        with st.expander("⚠️ Agent init error", expanded=False):
            st.error(init_error)

# ── MAIN TABS ─────────────────────────────────────────────────────────────────
from ui.components.chat_ui           import render_chat, run_agent_if_needed
from ui.components.meeting_form      import render_meeting_form
from ui.components.status_dashboard  import render_dashboard
from ui.components.logs_ui           import render_logs
from ui.components.settings_ui       import render_settings
from ui.components.email_replies_ui  import render_email_replies   # ✅ NEW

tab_chat, tab_sched, tab_dash, tab_replies, tab_logs, tab_settings = st.tabs([
    "💬 Chat Interface",
    "📅 Meeting Scheduler",
    "📊 Status Dashboard",
    "📬 Email Replies",        # ✅ NEW TAB
    "📜 History & Logs",
    "⚙️ Settings",
])

with tab_chat:
    render_chat()
    if st.session_state.get("agent_running"):
        run_agent_if_needed()

with tab_sched:
    render_meeting_form()

with tab_dash:
    render_dashboard()

with tab_replies:                  # ✅ NEW
    render_email_replies()

with tab_logs:
    render_logs()

with tab_settings:
    render_settings()