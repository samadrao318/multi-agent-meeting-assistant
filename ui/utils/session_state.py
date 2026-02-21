"""
ui/utils/session_state.py
Centralized session state management.
"""
import uuid, logging, copy
from datetime import datetime
from typing import Any, Optional
import streamlit as st

logger = logging.getLogger(__name__)

DEFAULTS: dict[str, Any] = {
    "thread_id":             None,
    "session_started":       None,
    "supervisor":            None,
    "model":                 None,
    "initialized":           False,
    "agent_running":         False,
    "init_error":            None,
    "messages":              [],
    "pending_user_input":    None,
    "hitl_pending":          False,
    "hitl_interrupt_id":     None,
    "hitl_action_requests":  [],
    "hitl_final_decisions":  None,
    "hitl_decision_map":     {},
    "enable_hitl":           True,
    "current_page":          "chat",
    "meetings":              [],
    "emails_sent":           [],
    "system_logs":           [],
    "show_examples":         True,
    "last_refresh":          None,
    "last_saved_meeting_id": None,
}


def init_session_state() -> None:
    for key, default in DEFAULTS.items():
        if key not in st.session_state:
            if key == "thread_id":
                st.session_state[key] = _new_thread()
            elif key == "session_started":
                st.session_state[key] = datetime.now().isoformat()
            elif isinstance(default, (list, dict)):
                st.session_state[key] = copy.deepcopy(default)
            else:
                st.session_state[key] = default


def _new_thread() -> str:
    return f"thread_{uuid.uuid4().hex[:10]}"


def get_agent_config() -> dict:
    return {"configurable": {"thread_id": st.session_state.thread_id}}


def new_thread_after_hitl() -> None:
    """
    FIX: 400 error — HITL ke baad tool_calls/tool_results ka mismatch hota hai.
    Naya thread start karo taake conversation history saaf ho jaye.
    """
    st.session_state.thread_id = _new_thread()
    add_log("New thread started after HITL (prevents 400 tool_call mismatch)")


# ── MESSAGES ──────────────────────────────────────────────────────────────────
def add_message(role: str, content: str, metadata: Optional[dict] = None) -> None:
    if not content or not str(content).strip():
        return
    st.session_state.messages.append({
        "id":        uuid.uuid4().hex[:8],
        "role":      role,
        "content":   str(content).strip(),
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "date":      datetime.now().strftime("%Y-%m-%d"),
        "metadata":  metadata or {},
    })

def get_messages() -> list:
    return st.session_state.get("messages", [])

def clear_messages() -> None:
    st.session_state.messages = []


# ── LOGS ──────────────────────────────────────────────────────────────────────
def add_log(message: str, level: str = "INFO") -> None:
    entry = {
        "id":        uuid.uuid4().hex[:6],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "level":     level,
        "message":   message,
    }
    logs = st.session_state.get("system_logs", [])
    logs.append(entry)
    if len(logs) > 500:
        logs = logs[-500:]
    st.session_state.system_logs = logs
    {"INFO": logger.info, "WARNING": logger.warning, "ERROR": logger.error}.get(
        level, logger.info
    )(f"[Session] {message}")


# ── HITL ──────────────────────────────────────────────────────────────────────
def set_hitl_interrupt(interrupt_id: str, action_requests: list) -> None:
    st.session_state.hitl_pending         = True
    st.session_state.hitl_interrupt_id    = interrupt_id
    st.session_state.hitl_action_requests = action_requests
    st.session_state.hitl_decision_map    = {}
    st.session_state.hitl_final_decisions = None
    add_log(f"HITL: {len(action_requests)} action(s) awaiting approval", "WARNING")

def record_hitl_decision(action_idx: int, decision: str) -> None:
    if "hitl_decision_map" not in st.session_state:
        st.session_state.hitl_decision_map = {}
    st.session_state.hitl_decision_map[action_idx] = decision
    add_log(f"HITL decision [{action_idx}]: {decision}")

def submit_hitl_decisions() -> list:
    dm  = st.session_state.get("hitl_decision_map", {})
    ars = st.session_state.get("hitl_action_requests", [])
    decisions = [{"type": dm.get(i, "reject")} for i in range(len(ars))]
    st.session_state.hitl_final_decisions = decisions
    return decisions

def reset_hitl() -> None:
    st.session_state.hitl_pending         = False
    st.session_state.hitl_interrupt_id    = None
    st.session_state.hitl_action_requests = []
    st.session_state.hitl_final_decisions = None
    st.session_state.hitl_decision_map    = {}

def all_hitl_decided() -> bool:
    ars = st.session_state.get("hitl_action_requests", [])
    dm  = st.session_state.get("hitl_decision_map", {})
    return bool(ars) and len(dm) == len(ars)


# ── SESSION ───────────────────────────────────────────────────────────────────
def clear_session() -> None:
    st.session_state.messages           = []
    st.session_state.agent_running      = False
    st.session_state.pending_user_input = None
    st.session_state.thread_id          = _new_thread()
    st.session_state.session_started    = datetime.now().isoformat()
    st.session_state.last_saved_meeting_id = None
    reset_hitl()
    add_log("Session cleared")

def reinit_agent() -> None:
    st.session_state.initialized   = False
    st.session_state.supervisor    = None
    st.session_state.model         = None
    st.session_state.init_error    = None
    st.session_state.agent_running = False
    add_log("Agent marked for re-init")

def sync_data_from_files() -> None:
    try:
        from ui.services.meeting_tracker import load_meetings, load_emails
        st.session_state.meetings    = load_meetings()
        st.session_state.emails_sent = load_emails()
    except Exception as e:
        add_log(f"sync_data error: {e}", "ERROR")