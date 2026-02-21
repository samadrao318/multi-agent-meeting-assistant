"""
ui/components/email_replies_ui.py
Email Replies Tracker.
- Uses Gmail threadId to fetch replies (correct approach)
- Time filters: 1 Hour, 24 Hours, 2 Days, 1 Week, All
- Two sections: Pending Replies | Replies Received
- English only
"""
import streamlit as st
from datetime import datetime, timedelta, timezone
from ui.utils.session_state import add_log
from ui.services.meeting_tracker import load_emails, load_meetings


# ─────────────────────────────────────────────────────────────────────────────
# GMAIL SERVICE
# ─────────────────────────────────────────────────────────────────────────────
def _get_gmail_service():
    try:
        from app.agents.email.tools import get_gmail_service
        return get_gmail_service()
    except Exception as e:
        add_log(f"Gmail service error: {e}", "ERROR")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# FIND SENT MESSAGE ID FROM GMAIL
# We need the Gmail message ID of our sent email to get its threadId
# ─────────────────────────────────────────────────────────────────────────────
def _find_sent_message(service, to_email: str, subject: str) -> dict:
    """
    Find the sent email in Gmail SENT folder to get its threadId.
    Returns: {message_id, thread_id} or {}
    """
    try:
        clean_subj = (subject
                      .replace("✅ ", "").replace("❌ ", "")
                      .replace("📅 ", "").strip())
        words      = clean_subj.split()
        short_subj = " ".join(words[:5]) if len(words) >= 5 else clean_subj

        # Search in SENT
        queries = [
            f'to:{to_email} subject:"{clean_subj}" in:sent',
            f'to:{to_email} subject:"{short_subj}" in:sent',
            f'to:{to_email} in:sent',
        ]

        for query in queries:
            result = service.users().messages().list(
                userId="me", q=query, maxResults=5
            ).execute()
            msgs = result.get("messages", [])
            if msgs:
                return {
                    "message_id": msgs[0]["id"],
                    "thread_id":  msgs[0]["threadId"],
                }
    except Exception as e:
        add_log(f"Find sent message error for {to_email}: {e}", "WARNING")
    return {}


# ─────────────────────────────────────────────────────────────────────────────
# FETCH REPLIES VIA THREAD ID
# ─────────────────────────────────────────────────────────────────────────────
def _fetch_replies_via_thread(service, thread_id: str, sent_msg_id: str, to_email: str) -> list:
    """
    Fetch all messages in the thread except the original sent message.
    These are the replies.
    """
    replies = []
    try:
        thread = service.users().threads().get(
            userId="me", id=thread_id, format="full"
        ).execute()

        for msg in thread.get("messages", []):
            msg_id = msg.get("id", "")
            # Skip the original sent message
            if msg_id == sent_msg_id:
                continue

            headers = {
                h["name"].lower(): h["value"]
                for h in msg.get("payload", {}).get("headers", [])
            }

            sender = headers.get("from", "")
            # Only include messages FROM the recipient (their reply)
            if to_email.lower() not in sender.lower():
                continue

            body     = _extract_body(msg.get("payload", {}))
            date_str = headers.get("date", "")
            try:
                dt             = datetime.strptime(date_str[:25].strip(), "%a, %d %b %Y %H:%M:%S")
                formatted_date = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                formatted_date = date_str[:25]

            replies.append({
                "id":      msg_id,
                "from":    sender,
                "subject": headers.get("subject", ""),
                "date":    formatted_date,
                "body":    body,
                "snippet": msg.get("snippet", "")[:300],
            })

    except Exception as e:
        add_log(f"Thread fetch error {thread_id}: {e}", "WARNING")

    return sorted(replies, key=lambda x: x.get("date", ""), reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# COMBINED: FIND SENT MSG → GET THREAD → EXTRACT REPLIES
# ─────────────────────────────────────────────────────────────────────────────
def _fetch_replies_for_email(service, subject: str, to_email: str) -> list:
    sent_info = _find_sent_message(service, to_email, subject)
    if not sent_info:
        add_log(f"Could not find sent email in Gmail for {to_email}", "WARNING")
        return []

    thread_id   = sent_info.get("thread_id", "")
    sent_msg_id = sent_info.get("message_id", "")
    if not thread_id:
        return []

    return _fetch_replies_via_thread(service, thread_id, sent_msg_id, to_email)


# ─────────────────────────────────────────────────────────────────────────────
# BODY EXTRACTOR
# ─────────────────────────────────────────────────────────────────────────────
def _extract_body(payload: dict) -> str:
    import base64
    mime      = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data", "")
    if body_data and "text/plain" in mime:
        try:
            return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
        except Exception:
            pass
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data", "")
            if data:
                try:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                except Exception:
                    pass
        if "parts" in part:
            nested = _extract_body(part)
            if nested:
                return nested
    return payload.get("snippet", "")


# ─────────────────────────────────────────────────────────────────────────────
# AVAILABILITY BADGE
# ─────────────────────────────────────────────────────────────────────────────
def _availability_badge(body: str) -> tuple:
    low = body.lower()
    unavailable_kw = [
        "not available", "unavailable", "can't make it", "cannot attend",
        "won't be able", "will not", "conflict", "busy", "sorry i can't",
        "regret", "decline", "unable",
    ]
    available_kw = [
        "i am available", "i'm available", "available", "works for me",
        "confirmed", "i'll attend", "i will attend", "yes", "sure",
        "sounds good", "perfect", "absolutely", "okay", "ok",
    ]
    maybe_kw = ["maybe", "might", "possibly", "not sure", "let me check", "will try"]

    if any(kw in low for kw in unavailable_kw):
        return (
            '<span style="background:#fee2e2;color:#dc2626;padding:3px 12px;'
            'border-radius:12px;font-size:0.78rem;font-weight:700;">❌ Not Available</span>',
            "unavailable",
        )
    elif any(kw in low for kw in available_kw):
        return (
            '<span style="background:#dcfce7;color:#16a34a;padding:3px 12px;'
            'border-radius:12px;font-size:0.78rem;font-weight:700;">✅ Available</span>',
            "available",
        )
    elif any(kw in low for kw in maybe_kw):
        return (
            '<span style="background:#fef9c3;color:#ca8a04;padding:3px 12px;'
            'border-radius:12px;font-size:0.78rem;font-weight:700;">🤔 Maybe</span>',
            "maybe",
        )
    else:
        return (
            '<span style="background:#f1f5f9;color:#64748b;padding:3px 12px;'
            'border-radius:12px;font-size:0.78rem;font-weight:700;">📬 Replied</span>',
            "replied",
        )


# ─────────────────────────────────────────────────────────────────────────────
# TIME FILTER HELPER
# ─────────────────────────────────────────────────────────────────────────────
def _filter_emails_by_time(sent_emails: list, time_filter: str) -> list:
    if time_filter == "All":
        return sent_emails

    now = datetime.now()
    delta_map = {
        "Last 1 Hour":   timedelta(hours=1),
        "Last 24 Hours": timedelta(hours=24),
        "Last 2 Days":   timedelta(days=2),
        "Last 1 Week":   timedelta(weeks=1),
    }
    delta = delta_map.get(time_filter)
    if not delta:
        return sent_emails

    cutoff = now - delta
    filtered = []
    for e in sent_emails:
        sent_at_str = e.get("sent_at", "")
        try:
            sent_dt = datetime.fromisoformat(sent_at_str[:19])
            if sent_dt >= cutoff:
                filtered.append(e)
        except Exception:
            filtered.append(e)  # If parse fails, include it
    return filtered


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RENDER
# ─────────────────────────────────────────────────────────────────────────────
def render_email_replies() -> None:
    st.markdown("""
    <h2 style="font-family:'Georgia',serif;color:#1a365d;margin:0 0 4px 0;font-size:1.5rem;">
        📬 Email Replies Tracker</h2>
    <p style="color:#718096;font-size:0.875rem;margin:0 0 12px 0;">
        Check replies from attendees for sent meeting invitations.</p>
    """, unsafe_allow_html=True)

    service = _get_gmail_service()
    if not service:
        st.error("❌ Gmail service not available. Please check Google credentials in Settings.")
        return

    all_emails  = load_emails()
    sent_emails = [
        e for e in all_emails
        if e.get("status", "").lower() in ("sent", "delivered")
        and "@" in e.get("to", "")
    ]

    if not sent_emails:
        st.info("No sent emails found. Send a meeting invitation first.")
        return

    sent_emails = sorted(sent_emails, key=lambda x: x.get("sent_at", ""), reverse=True)

    # ── TIME FILTER ───────────────────────────────────────────────────────────
    st.markdown("#### Filter by Send Time")
    time_options = ["All", "Last 1 Hour", "Last 24 Hours", "Last 2 Days", "Last 1 Week"]
    
    selected_filter = st.radio(
        "Time range",
        time_options,
        index=0,
        horizontal=True,
        key="reply_time_filter",
        label_visibility="collapsed",
    )

    filtered_emails = _filter_emails_by_time(sent_emails, selected_filter)

    if not filtered_emails:
        st.warning(f"No emails found in the selected time range: **{selected_filter}**")
        return

    st.caption(f"Showing **{len(filtered_emails)}** of **{len(sent_emails)}** sent emails")
    st.divider()

    # ── FETCH + CLEAR BUTTONS ─────────────────────────────────────────────────
    c1, c2 = st.columns([1, 1])
    fetch_clicked = c1.button(
        "📥 Fetch Replies", type="primary",
        use_container_width=True, key="fetch_replies_btn"
    )
    clear_clicked = c2.button(
        "🗑️ Clear Results",
        use_container_width=True, key="clear_replies_btn"
    )

    if clear_clicked:
        st.session_state.pop("_reply_data", None)
        st.session_state.pop("_reply_filter_used", None)
        st.rerun()

    if fetch_clicked:
        reply_data = {}
        progress   = st.progress(0, text="Fetching replies...")
        for idx, email_rec in enumerate(filtered_emails):
            to      = email_rec.get("to", "")
            subject = email_rec.get("subject", "")
            eid     = email_rec.get("id", "")
            progress.progress(
                (idx + 1) / len(filtered_emails),
                text=f"Checking replies for {to}..."
            )
            reply_data[eid] = _fetch_replies_for_email(service, subject, to)

        progress.empty()
        st.session_state["_reply_data"]        = reply_data
        st.session_state["_reply_filter_used"] = selected_filter
        add_log(f"Reply fetch complete: {len(filtered_emails)} emails checked ({selected_filter})")
        st.rerun()

    # ── NO DATA YET ───────────────────────────────────────────────────────────
    reply_data = st.session_state.get("_reply_data")
    if reply_data is None:
        st.markdown("""
        <div style="text-align:center;padding:40px;background:#f8fafc;
            border-radius:12px;border:2px dashed #cbd5e1;margin-top:16px;">
            <div style="font-size:2.5rem;margin-bottom:8px;">📥</div>
            <div style="color:#475569;font-size:1rem;font-weight:600;">
                Click <strong>"📥 Fetch Replies"</strong> to check for replies
            </div>
            <div style="color:#94a3b8;font-size:0.82rem;margin-top:4px;">
                Gmail threads will be searched for replies to your sent invitations
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── SPLIT INTO TWO GROUPS ────────────────────────────────────────────────
    meetings        = {m["id"]: m.get("title", "") for m in load_meetings()}
    pending_emails  = []
    received_emails = []

    for email_rec in filtered_emails:
        eid     = email_rec.get("id", "")
        if eid not in reply_data:
            continue
        replies = reply_data.get(eid, [])
        mtg_ttl = meetings.get(email_rec.get("meeting_id", ""), "")
        if replies:
            received_emails.append((email_rec, replies, mtg_ttl))
        else:
            pending_emails.append((email_rec, mtg_ttl))

    # ── STATS ─────────────────────────────────────────────────────────────────
    s1, s2, s3 = st.columns(3)
    s1.metric("📧 Total Checked",    len(filtered_emails))
    s2.metric("⏳ Pending Replies",  len(pending_emails))
    s3.metric("✅ Replies Received", len(received_emails))

    filter_used = st.session_state.get("_reply_filter_used", selected_filter)
    st.caption(f"Last fetched with filter: **{filter_used}**")
    st.divider()

    STATUS_ICON = {
        "available":   "🟢",
        "unavailable": "🔴",
        "maybe":       "🟡",
        "replied":     "📬",
    }

    # ── SECTION 1: PENDING REPLIES ────────────────────────────────────────────
    st.markdown(f"""
    <h3 style="color:#92400e;font-size:1.1rem;margin:0 0 10px 0;">
        ⏳ Pending Replies &nbsp;
        <span style="background:#fef3c7;color:#92400e;padding:2px 10px;
            border-radius:20px;font-size:0.82rem;">{len(pending_emails)}</span>
    </h3>
    """, unsafe_allow_html=True)

    if not pending_emails:
        st.success("All recipients have replied.")
    else:
        for email_rec, mtg_ttl in pending_emails:
            to      = email_rec.get("to", "—")
            subject = email_rec.get("subject", "—")
            sent_at = email_rec.get("sent_at", "")[:16]
            with st.expander(
                f"⏳  {to}  ·  {subject[:60]}{'...' if len(subject) > 60 else ''}  ·  {sent_at}"
            ):
                col1, col2, col3 = st.columns(3)
                col1.markdown(f"**To:** {to}")
                col2.markdown(f"**Sent:** {sent_at}")
                if mtg_ttl:
                    col3.markdown(f"**Meeting:** {mtg_ttl}")
                st.caption(f"**Subject:** {subject}")
                st.markdown(
                    '<p style="color:#94a3b8;text-align:center;padding:12px 0;">'
                    'No reply received yet.</p>',
                    unsafe_allow_html=True,
                )

    st.divider()

    # ── SECTION 2: REPLIES RECEIVED ───────────────────────────────────────────
    st.markdown(f"""
    <h3 style="color:#166534;font-size:1.1rem;margin:0 0 10px 0;">
        ✅ Replies Received &nbsp;
        <span style="background:#dcfce7;color:#166534;padding:2px 10px;
            border-radius:20px;font-size:0.82rem;">{len(received_emails)}</span>
    </h3>
    """, unsafe_allow_html=True)

    if not received_emails:
        st.info("No replies received yet.")
    else:
        for email_rec, replies, mtg_ttl in received_emails:
            to      = email_rec.get("to", "—")
            subject = email_rec.get("subject", "—")
            sent_at = email_rec.get("sent_at", "")[:16]

            latest_body        = replies[0]["body"] if replies else ""
            badge_html, status = _availability_badge(latest_body)
            icon               = STATUS_ICON.get(status, "📬")

            with st.expander(
                f"{icon}  {to}  ·  {subject[:60]}{'...' if len(subject) > 60 else ''}  ·  {sent_at}",
                expanded=(status in ("available", "unavailable")),
            ):
                col1, col2, col3 = st.columns(3)
                col1.markdown(f"**To:** {to}")
                col2.markdown(f"**Sent:** {sent_at}")
                if mtg_ttl:
                    col3.markdown(f"**Meeting:** {mtg_ttl}")
                st.caption(f"**Subject:** {subject}")
                st.divider()

                for reply in replies:
                    r_badge, _ = _availability_badge(reply["body"])
                    display    = (reply["snippet"] or reply["body"])[:350]
                    st.markdown(f"""
                    <div style="background:#f8fafc;border:1px solid #e2e8f0;
                        border-radius:10px;padding:12px 16px;margin:8px 0;">
                        <div style="display:flex;justify-content:space-between;
                            align-items:center;margin-bottom:8px;">
                            <div style="font-size:0.82rem;color:#475569;">
                                <strong>From:</strong> {reply['from']}
                                &nbsp;·&nbsp;
                                <strong>Date:</strong> {reply['date']}
                            </div>
                            {r_badge}
                        </div>
                        <div style="font-size:0.85rem;color:#1e293b;line-height:1.6;
                            background:white;padding:10px 12px;border-radius:6px;
                            border-left:3px solid #3b82f6;white-space:pre-wrap;">
                            {display}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    if len(reply["body"]) > 350:
                        with st.expander("View full reply"):
                            st.text(reply["body"])