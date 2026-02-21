"""ui/components/hitl_panel.py"""
import streamlit as st
from ui.utils.session_state import record_hitl_decision, submit_hitl_decisions, reset_hitl, all_hitl_decided, add_log

def render_hitl_panel() -> bool:
    if not st.session_state.get("hitl_pending"): return False
    action_requests = st.session_state.get("hitl_action_requests", [])
    if not action_requests: reset_hitl(); return False

    st.markdown("""<div style="background:linear-gradient(135deg,#fff8e1,#fff3cd);
        border:2px solid #f59e0b;border-radius:14px;padding:16px 20px 12px 20px;
        margin:12px 0 8px 0;box-shadow:0 4px 20px rgba(245,158,11,0.15);">
        <div style="display:flex;align-items:center;gap:10px;">
            <div style="font-size:1.8rem;">⚠️</div>
            <div>
                <div style="font-family:'Georgia',serif;font-size:1.1rem;font-weight:700;color:#92400e;">
                    Human Approval Required</div>
                <div style="font-size:0.82rem;color:#b45309;margin-top:2px;">
                    Review and approve or reject each action below.</div>
            </div>
        </div></div>""", unsafe_allow_html=True)

    for idx, req in enumerate(action_requests):
        _render_action_card(idx, req)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    _render_submit_section(len(action_requests))

    if st.session_state.get("_hitl_submitted"):
        st.session_state.pop("_hitl_submitted", None); return True
    return False

def _render_action_card(idx, req):
    tool_name = req.get("tool_name","Unknown Tool")
    args = req.get("args",{})
    decision_map = st.session_state.get("hitl_decision_map",{})
    current = decision_map.get(idx)
    tl = tool_name.lower()
    if any(k in tl for k in ["email","gmail","send","mail"]):
        icon,color,bg,border = "📧","#3b82f6","#eff6ff","#bfdbfe"
    elif any(k in tl for k in ["calendar","event","schedule","meeting"]):
        icon,color,bg,border = "📅","#059669","#f0fdf4","#a7f3d0"
    else:
        icon,color,bg,border = "🔧","#7c3aed","#faf5ff","#ddd6fe"
    bc = "#22c55e" if current=="approve" else ("#ef4444" if current=="reject" else border)
    st.markdown(f"""<div style="background:{bg};border:2px solid {bc};border-radius:12px;
        padding:14px 18px;margin:8px 0;">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
            <span style="font-size:1.3rem;">{icon}</span>
            <span style="font-family:'Georgia',serif;font-size:0.95rem;font-weight:700;color:{color};">
                Action {idx+1}: {tool_name}</span>
        </div>""", unsafe_allow_html=True)
    if args:
        for k,v in args.items(): _render_arg_row(k,v)
    else:
        st.markdown("<div style='font-size:0.82rem;color:#6b7280;font-style:italic;'>No arguments</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    col1,col2,col3 = st.columns([2,2,3])
    iid = st.session_state.get("hitl_interrupt_id","x")
    with col1:
        if st.button("✅ Approve", key=f"hitl_approve_{idx}_{iid}", use_container_width=True,
            type="primary" if current=="approve" else "secondary"):
            record_hitl_decision(idx,"approve"); add_log(f"Action {idx+1} ({tool_name}): APPROVED"); st.rerun()
    with col2:
        if st.button("❌ Reject", key=f"hitl_reject_{idx}_{iid}", use_container_width=True,
            type="primary" if current=="reject" else "secondary"):
            record_hitl_decision(idx,"reject"); add_log(f"Action {idx+1} ({tool_name}): REJECTED"); st.rerun()
    with col3:
        if current=="approve":   st.success("✅ Approved")
        elif current=="reject":  st.error("❌ Rejected")
        else:                    st.info("⏳ Awaiting decision")

def _render_arg_row(key, value):
    kd = key.replace("_"," ").title()
    if isinstance(value, list): vs = ", ".join(str(v) for v in value) if value else "—"
    elif isinstance(value, str) and len(value)>150: vs = value[:150]+"..."
    elif value is None: vs = "—"
    else: vs = str(value)
    st.markdown(f"""<div style="display:flex;gap:8px;margin:4px 0;font-size:0.82rem;">
        <span style="font-weight:600;color:#374151;min-width:90px;flex-shrink:0;">{kd}:</span>
        <span style="color:#4b5563;word-break:break-word;">{vs}</span></div>""", unsafe_allow_html=True)

def _render_submit_section(total):
    dm = st.session_state.get("hitl_decision_map",{})
    decided = len(dm)
    approved_count = sum(1 for d in dm.values() if d=="approve")
    rejected_count = sum(1 for d in dm.values() if d=="reject")
    remaining = total - decided
    c1,c2,c3 = st.columns(3)
    c1.metric("✅ Approved", approved_count)
    c2.metric("❌ Rejected", rejected_count)
    c3.metric("⏳ Remaining", remaining)
    if all_hitl_decided():
        if st.button("🚀 Submit Decisions & Continue Agent", type="primary", use_container_width=True, key="hitl_submit_final"):
            submit_hitl_decisions()
            st.session_state["_hitl_submitted"] = True
            add_log(f"HITL submitted: {approved_count} approved, {rejected_count} rejected")
            st.rerun()
    else:
        st.button(f"⏳ Please decide all {remaining} remaining action(s) first",
            disabled=True, use_container_width=True, key="hitl_submit_disabled")
    if st.button("🚫 Cancel & Discard All", key="hitl_cancel", use_container_width=True):
        reset_hitl()
        from ui.utils.session_state import add_message
        add_message("system","⚠️ HITL approval cancelled.")
        add_log("HITL cancelled","WARNING"); st.rerun()