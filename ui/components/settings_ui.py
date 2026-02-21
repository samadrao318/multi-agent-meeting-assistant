"""
ui/components/settings_ui.py
Settings page — connections, agent config, diagnostics.
"""
import os
import sys
import streamlit as st
from ui.utils.session_state import add_log, reinit_agent, sync_data_from_files


def render_settings() -> None:
    st.markdown("""
    <h2 style="font-family:'Georgia',serif; color:#1a365d;
               margin:0 0 4px 0; font-size:1.5rem;">⚙️ Settings</h2>
    <p style="color:#718096; font-size:0.875rem; margin:0 0 16px 0;">
        Connection status, agent configuration, and diagnostics.
    </p>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs([
        "🔌 Connections", "🤖 Agent Config", "🔬 Diagnostics", "ℹ️ About",
    ])
    with tab1: _render_connections()
    with tab2: _render_agent_config()
    with tab3: _render_diagnostics()
    with tab4: _render_about()


def _render_connections() -> None:
    st.markdown("#### ☁️ Azure OpenAI")
    endpoint   = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    api_key    = os.getenv("AZURE_OPENAI_API_KEY", "")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")

    col1, col2, col3 = st.columns(3)
    for col, label, val in [
        (col1, "Endpoint",   (endpoint[:40] + '...') if len(endpoint) > 40 else (endpoint or '❌ Not set')),
        (col2, "API Key",    '✅ ' + '•' * 8 + api_key[-4:] if api_key else '❌ Not set'),
        (col3, "Deployment", deployment or '❌ Not set'),
    ]:
        col.markdown(f"""
        <div style="background:#f8fafc; border-radius:8px; padding:10px 14px; border:1px solid #e2e8f0;">
            <div style="font-size:0.75rem; color:#718096; font-weight:600; text-transform:uppercase;">{label}</div>
            <div style="font-size:0.82rem; color:#2d3748; margin-top:4px; word-break:break-all;">{val}</div>
        </div>
        """, unsafe_allow_html=True)

    if endpoint and api_key and deployment:
        st.success("✅ Azure OpenAI credentials found.")
    else:
        missing = []
        if not endpoint:   missing.append("AZURE_OPENAI_ENDPOINT")
        if not api_key:    missing.append("AZURE_OPENAI_API_KEY")
        if not deployment: missing.append("AZURE_OPENAI_DEPLOYMENT")
        st.error(f"❌ Missing in .env file: `{'`, `'.join(missing)}`")
        st.code(
            "# Add these to your .env file:\n"
            "AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/\n"
            "AZURE_OPENAI_API_KEY=your-api-key\n"
            "AZURE_OPENAI_DEPLOYMENT=gpt-4",
            language="bash",
        )

    st.divider()
    st.markdown("#### 🔑 Google APIs (Calendar & Gmail)")
    cred_exists  = os.path.exists("credentials.json")
    token_exists = os.path.exists("token.json")

    gcol1, gcol2 = st.columns(2)
    with gcol1:
        if cred_exists:  st.success("✅ `credentials.json` found")
        else:            st.error("❌ `credentials.json` not found")
    with gcol2:
        if token_exists: st.success("✅ `token.json` found (OAuth authorized)")
        else:            st.warning("⚠️ `token.json` not found — will be created on first use")

    if not cred_exists:
        with st.expander("📖 How to get credentials.json"):
            st.markdown("""
            1. Go to [Google Cloud Console](https://console.cloud.google.com/)
            2. Create or select a project
            3. Enable **Google Calendar API** and **Gmail API**
            4. Go to **APIs & Services → Credentials**
            5. Click **Create Credentials → OAuth 2.0 Client ID**
            6. Choose **Desktop Application**
            7. Download the JSON and rename it `credentials.json`
            8. Place it in your project root and restart the app
            """)

    if cred_exists:
        if st.button("🧪 Test Google Calendar Connection", type="primary"):
            with st.spinner("Testing Google Calendar API..."):
                try:
                    import subprocess
                    result = subprocess.run(
                        [sys.executable, "-c",
                         "import sys; sys.path.insert(0, '.'); "
                         "from app.agents.calendar.tools import get_calendar_service; "
                         "s = get_calendar_service(); print('SUCCESS' if s else 'FAILED')"],
                        capture_output=True, text=True, timeout=20,
                    )
                    if "SUCCESS" in result.stdout:
                        st.success("✅ Google Calendar connected successfully!")
                        add_log("Google Calendar test: PASS")
                    else:
                        st.error(f"❌ Test failed:\n```\n{result.stderr[:400]}\n```")
                        add_log("Google Calendar test: FAIL", "ERROR")
                except subprocess.TimeoutExpired:
                    st.warning("⚠️ Test timed out. Google OAuth browser window may have opened.")
                except Exception as e:
                    st.error(f"❌ Test error: {e}")


def _render_agent_config() -> None:
    st.markdown("#### 🤝 Human-in-the-Loop (HITL)")
    current_hitl = st.session_state.get("enable_hitl", True)
    new_hitl = st.toggle("Enable Human-in-the-Loop Approvals", value=current_hitl,
                         help="When ON: agent pauses before sending emails or creating calendar events.",
                         key="hitl_toggle_settings")

    if new_hitl:
        st.markdown("""
        <div style="background:#f0fdf4; border-left:4px solid #22c55e; border-radius:8px;
                    padding:12px 16px; margin:8px 0;">
            <strong style="color:#166534;">🤝 HITL Enabled</strong><br>
            <span style="color:#15803d; font-size:0.85rem;">
                Agent will pause and ask for your approval before sending emails or creating calendar events.
            </span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:#fef2f2; border-left:4px solid #ef4444; border-radius:8px;
                    padding:12px 16px; margin:8px 0;">
            <strong style="color:#991b1b;">⚡ HITL Disabled</strong><br>
            <span style="color:#b91c1c; font-size:0.85rem;">
                Agent will execute all actions automatically. Use with caution.
            </span>
        </div>
        """, unsafe_allow_html=True)

    if new_hitl != current_hitl:
        st.session_state.enable_hitl = new_hitl
        reinit_agent()
        add_log(f"HITL changed to: {'enabled' if new_hitl else 'disabled'}")
        st.info("🔄 Agent will reinitialize with new settings.")
        st.rerun()

    st.divider()
    st.markdown("#### 🔄 Agent Management")
    col1, col2 = st.columns(2)

    with col1:
        agent_ok = st.session_state.get("initialized", False)
        init_err = st.session_state.get("init_error")
        if agent_ok:  st.success("✅ Agent is initialized and ready")
        else:
            st.error("❌ Agent is not initialized")
            if init_err: st.error(f"Last error: {init_err}")
        if st.button("🔄 Re-initialize Agent", type="primary", use_container_width=True):
            reinit_agent()
            st.success("Agent will reinitialize on next interaction.")
            add_log("Agent re-init triggered from settings")
            st.rerun()

    with col2:
        thread_id = st.session_state.get("thread_id", "—")
        started   = st.session_state.get("session_started", "—")
        msg_count = len(st.session_state.get("messages", []))
        st.markdown(f"""
        <div style="background:#f8fafc; border-radius:8px; padding:12px 14px; border:1px solid #e2e8f0;">
            <div style="font-size:0.75rem; color:#718096; font-weight:600; margin-bottom:8px;">SESSION INFO</div>
            <div style="font-size:0.82rem; color:#2d3748;">
                🔑 Thread: <code>{thread_id}</code><br>
                🕐 Started: {str(started)[:16]}<br>
                💬 Messages: {msg_count}
            </div>
        </div>
        """, unsafe_allow_html=True)


def _render_diagnostics() -> None:
    st.markdown("#### 🔬 System Diagnostics")
    if st.button("▶️ Run Diagnostics", type="primary"):
        results = []

        py_ver = sys.version.split()[0]
        py_ok  = tuple(int(x) for x in py_ver.split(".")[:2]) >= (3, 10)
        results.append(("Python Version", py_ok, py_ver, "Need 3.10+"))

        for module, pkg_name in [
            ("streamlit", "streamlit"), ("langchain", "langchain"),
            ("langgraph", "langgraph"), ("langchain_openai", "langchain-openai"),
            ("pandas", "pandas"), ("dotenv", "python-dotenv"), ("google.auth", "google-auth"),
        ]:
            try:
                mod = __import__(module)
                ver = getattr(mod, "__version__", "installed")
                results.append((f"Package: {pkg_name}", True, ver, ""))
            except ImportError:
                results.append((f"Package: {pkg_name}", False, "NOT FOUND", f"pip install {pkg_name}"))

        for path, desc in [
            (".env", ".env credentials file"),
            ("credentials.json", "Google OAuth credentials"),
            ("data/", "Data directory"),
        ]:
            exists = os.path.exists(path)
            results.append((f"File: {desc}", exists, "✓ Found" if exists else "✗ Missing", ""))

        for label, ok, detail, hint in results:
            icon   = "✅" if ok else "❌"
            color  = "#f0fdf4" if ok else "#fef2f2"
            border = "#22c55e" if ok else "#ef4444"
            hint_html = (f"<br><span style='color:#6b7280; font-size:0.75rem;'>→ {hint}</span>"
                         if hint and not ok else "")
            st.markdown(f"""
            <div style="background:{color}; border-left:3px solid {border}; border-radius:6px;
                        padding:8px 12px; margin:4px 0;
                        display:flex; align-items:center; justify-content:space-between;">
                <span style="font-size:0.85rem; font-weight:600;">{icon} {label}</span>
                <span style="font-size:0.8rem; color:#4b5563;">{detail}{hint_html}</span>
            </div>
            """, unsafe_allow_html=True)


def _render_about() -> None:
    st.markdown("""
    #### 🤖 Multi-Agent Meeting & Email Automation System

    **Version:** 1.0.0 · **Status:** Production Ready ✅

    ---

    ##### 🏗️ Architecture

    | Agent | Capability |
    |-------|-----------|
    | 🎯 Supervisor | Orchestrates all sub-agents |
    | 📅 Calendar Agent | Google Calendar: create, read events |
    | 📧 Email Agent | Gmail: send emails |
    | 💾 Data Agent | CSV contacts: read, search, add |

    ##### 💾 Storage Files
    - `data/meetings_status.json` — All meeting records
    - `data/emails_sent.json` — All email records
    - `data/contacts.csv` — Contact database

    ##### 🔗 Resources
    - [Azure OpenAI Portal](https://portal.azure.com/)
    - [Google Cloud Console](https://console.cloud.google.com/)
    - [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
    - [Streamlit Docs](https://docs.streamlit.io/)
    """)