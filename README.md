# 🤖 Multi-Agent Meeting & Email Automation System

A complete, production-ready AI automation platform built with **LangChain**, **LangGraph**, **Azure OpenAI**, and **Google APIs**. Features a true sub-agent architecture, Human-in-the-Loop approval system, and a professional Streamlit web interface.

**Version:** 1.0.0 &nbsp;|&nbsp; **Python:** 3.12+ &nbsp;|&nbsp; **Status:** Production Ready ✅

---

## 🎯 What This System Does

This platform lets you automate your entire meeting and email workflow through AI:

- **Talk naturally** — "Schedule a team meeting tomorrow at 2pm and send invites to all engineers"
- **Use structured forms** — fill a form, click one button, meeting is created and emails are sent
- **Stay in control** — Human-in-the-Loop asks for your approval before any critical action
- **Track everything** — every meeting and email is saved, searchable, and exportable
- **Check replies** — see who replied to your meeting invitations and their availability

Two interfaces are available — both use the exact same backend agents:

| Interface | How to run | Best for |
|-----------|-----------|---------|
| Streamlit Web UI | `streamlit run ui/app.py` | Daily use, demos, team sharing |
| Terminal Interface | `python -m app.main` | Power users, scripting |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     User Interface Layer                        │
│                                                                 │
│   Streamlit Web UI (ui/)          Terminal (app/main.py)        │
│   6 Tabs: Chat · Scheduler ·      Interactive loop with         │
│   Dashboard · Email Replies ·     full HITL support             │
│   Logs · Settings                                               │
└──────────────────────────┬──────────────────────────────────────┘
                           │  supervisor.stream()
                           │  Command(resume=...)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Supervisor Agent (LangGraph)                   │
│          app/supervisor/supervisor_agent.py                     │
│                                                                 │
│   Receives every message · Decides routing · Manages HITL       │
└──────────┬─────────────────┬──────────────────┬────────────────┘
           │                 │                  │
           ▼                 ▼                  ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐
│  📅 Calendar │   │  📧 Email    │   │  💾 Data Agent       │
│  Agent       │   │  Agent       │   │                      │
│              │   │              │   │  contacts.csv        │
│  Google      │   │  Gmail       │   │  read · search · add │
│  Calendar    │   │  API v1      │   │                      │
│  API v3      │   │              │   │  No Google creds     │
│              │   │              │   │  required            │
└──────────────┘   └──────────────┘   └──────────────────────┘
           │                 │
           ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│              Human-in-the-Loop (when enabled)                   │
│                                                                 │
│   Agent pauses → Approval panel → You Approve / Reject          │
│   Approved: record saved + action executed                      │
│   Rejected: nothing happens                                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Persistent Storage                           │
│                                                                 │
│   data/meetings_status.json     data/emails_sent.json           │
│   data/contacts.csv                                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
project_root/
│
├── app/                                ← Backend (original — do not modify)
│   ├── main.py                         Terminal interface
│   ├── core/
│   │   ├── config.py                   Pydantic settings
│   │   └── llm_factory.py              Azure OpenAI initialization
│   ├── agents/
│   │   ├── calendar/
│   │   │   ├── tools.py                Google Calendar tools
│   │   │   └── agent.py                Calendar sub-agent
│   │   ├── email/
│   │   │   ├── tools.py                Gmail tools (get_gmail_service)
│   │   │   └── agent.py                Email sub-agent
│   │   └── data/
│   │       ├── tools.py                CSV read/write tools
│   │       └── agent.py                Data sub-agent
│   └── supervisor/
│       └── supervisor_agent.py         Orchestrator — coordinates all agents
│
├── ui/                                 ← Streamlit Web UI
│   ├── app.py                          Main entry point (6 tabs)
│   ├── components/
│   │   ├── chat_ui.py                  Chat + streaming + HITL display
│   │   ├── meeting_form.py             Structured meeting scheduler
│   │   ├── hitl_panel.py               Approve/Reject panel
│   │   ├── status_dashboard.py         Meetings & emails overview
│   │   ├── email_replies_ui.py         Email replies tracker (Gmail threads)
│   │   ├── logs_ui.py                  History, contacts, system logs
│   │   ├── settings_ui.py              Settings & diagnostics
│   │   └── sidebar.py                  Status & session controls
│   ├── services/
│   │   ├── agent_runner.py             Wraps supervisor.stream()
│   │   ├── meeting_tracker.py          JSON persistence (atomic writes)
│   │   └── email_service.py            Email send + record service
│   └── utils/
│       └── session_state.py            Centralized session management
│
├── data/                               ← Auto-created on first run
│   ├── contacts.csv                    Contact database
│   ├── meetings_status.json            All meeting records
│   └── emails_sent.json                All email records
│
├── .env                                ← Your credentials (never commit!)
├── .env.example                        Credentials template
├── credentials.json                    Google OAuth (download from GCP)
├── token.json                          Auto-created after Google login
├── requirements.txt
├── README.md
└── QUICK_START.md
```

---

## ✨ Features

### Multi-Agent Architecture (True Sub-Agent Pattern)

Each agent is independent and specialized. The supervisor routes intelligently:

| Agent | Capability | Requires |
|-------|-----------|---------|
| Supervisor | Orchestrates all sub-agents, manages HITL | Azure OpenAI |
| Calendar Agent | Create events, check availability | Google Calendar API |
| Email Agent | Send emails, compose templates | Gmail API |
| Data Agent | Read/search/add contacts from CSV | Nothing extra |

### Human-in-the-Loop (HITL)

Built-in safety checkpoint before any critical action:

- **What triggers it:** Sending emails, creating calendar events
- **What does not:** Reading contacts, searching, checking availability
- **How it works:** Agent pauses → approval card appears → you approve/reject → agent continues
- **Data safety:** Email records are saved the moment you approve — before Gmail even sends

Toggle HITL ON/OFF from the sidebar at any time without restarting the app.

### Streamlit Web UI

Professional tab-based interface:

```
| 💬 Chat | 📅 Meeting Scheduler | 📊 Status Dashboard | 📬 Email Replies | 📜 History & Logs | ⚙️ Settings |
```

**💬 Chat Tab**
- Real-time streaming responses as the agent generates text
- Message bubbles with timestamps
- Tool usage indicators (which agent is working)
- Quick-prompt buttons for common actions
- HITL approval panel appears inline

**📅 Meeting Scheduler Tab**
- Form inputs: title, date, time range, location, attendees, email subject and body
- Attendees auto-loaded from contacts.csv
- Meeting saved as Pending — email sent only when Approved in Meeting History
- History table with color-coded status: 🟢 Approved · 🟡 Pending · 🔴 Rejected
- Search, filter, inline status update, delete

**📊 Status Dashboard Tab**
- Summary metrics: total, approved, pending, rejected, emails sent
- Color-highlighted meetings table
- Email log with source tracking (Chat / Scheduler / HITL)
- Inline status updates

**📬 Email Replies Tab**
- Fetch replies from Gmail using thread-based lookup (accurate)
- Time filters: Last 1 Hour · Last 24 Hours · Last 2 Days · Last 1 Week · All
- Two sections: Pending Replies (no response yet) · Replies Received
- Availability detection: ✅ Available · ❌ Not Available · 🤔 Maybe · 📬 Replied
- Fetch triggered manually — no unnecessary API calls

**📜 History & Logs Tab**
- Meetings history — full details, CSV export
- Emails sent — source filter, CSV export
- Contacts — searchable, CSV export
- System logs — level filter (INFO/WARNING/ERROR), clearable

**⚙️ Settings Tab**
- Azure connection status with masked API key
- Google APIs status and connection test
- HITL configuration
- Agent re-initialization
- Full diagnostics checker

### Meeting Status Tracking

Every meeting has a status that you control:

| Status | Meaning |
|--------|---------|
| 🟡 Pending | Scheduled, waiting for approval — email not sent yet |
| 🟢 Approved | Meeting confirmed — invitation email sent to attendees |
| 🔴 Rejected | Meeting declined — cancellation notice sent to attendees |

### Email Reply Tracking

Track who responded to your meeting invitations:

- Uses Gmail thread ID to find exact replies (not subject matching)
- Automatically detects availability from reply content
- Filter by time range to focus on recent invitations
- Two clear groups: who replied and who has not replied yet

### Production-Ready Features

- Atomic file writes — no data corruption on crash
- Auto-backup of corrupted JSON files
- Classified error messages (rate limit, auth error, timeout — each handled differently)
- Session management with unique thread IDs
- Structured system logging with level filtering
- CSV exports for all data tables

---

## 💬 Usage Examples

### Example 1 — Data Agent (no Google credentials needed)

```
You: Show me all contacts
Agent: Found 3 contacts:
  · Alice Smith (alice@company.com) — Product Manager
  · Bob Johnson (bob@company.com) — Software Engineer
  · Carol White (carol@company.com) — Designer

You: Search for engineers
Agent: Found 1 match — Bob Johnson (bob@company.com)

You: Add contact: dave@company.com, Dave Wilson, DevOps Engineer
Agent: Contact added successfully.
```

### Example 2 — Schedule meeting with HITL approval

```
You: Schedule a project review tomorrow at 2pm for 1 hour

HITL panel appears:

  Action 1: create_calendar_event
  Title:    Project Review
  Date:     Tomorrow
  Time:     14:00 – 15:00

  [ ✅ Approve ]   [ ❌ Reject ]

You approve → Submit

Agent: Project review created on your Google Calendar.
       Meeting record saved with status: Pending
```

### Example 3 — Complex multi-step task

```
You: Schedule meeting Friday 3pm and send invites to all engineers

Agent flow:
  Step 1 → Data Agent finds all engineers in contacts
  Step 2 → Calendar Agent creates event (HITL approval)
  Step 3 → Email Agent sends invitations (HITL approval)

After approvals:
  meetings_status.json — new entry, status: Pending
  emails_sent.json — one entry per engineer, meeting_id linked
```

### Example 4 — Meeting Scheduler form (no typing needed)

```
1. Open Meeting Scheduler tab
2. Fill: Title, Date, Time, Location
3. Select attendees from contacts dropdown
4. Click "Schedule & Send Later"

Result:
  ✅ Meeting saved as Pending
  ✅ Go to Meeting History → click Approve
  ✅ Invitation email sent to all attendees via Gmail
```

### Example 5 — Check who replied to your invitations

```
1. Open Email Replies tab
2. Select time filter: Last 24 Hours
3. Click "📥 Fetch Replies"

Result:
  ⏳ Pending Replies (2) — Bob, Carol have not replied
  ✅ Replies Received (1) — Alice replied: "I am available, see you then!"
                            Badge: ✅ Available
```

---

## 🚀 Quick Start

```bash
# Install
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your Azure OpenAI credentials

# Launch
streamlit run ui/app.py
```

Full step-by-step setup → [QUICK_START.md](QUICK_START.md)

---

## 🔧 Configuration

### Azure OpenAI (Required)

```env
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-4
```

### Google APIs (Optional)

Download `credentials.json` from Google Cloud Console (OAuth 2.0, Desktop App type) with Calendar API and Gmail API enabled. Place in project root.

### Contacts Database

```csv
email,name,designation
alice@company.com,Alice Smith,Product Manager
bob@company.com,Bob Johnson,Software Engineer
```

File: `data/contacts.csv`

---

## 🛠️ Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| LLM | Azure OpenAI (GPT-4) | Latest |
| Agent Framework | LangChain | 0.3+ |
| Graph Engine | LangGraph | 0.2+ |
| Web UI | Streamlit | 1.38+ |
| Calendar | Google Calendar API | v3 |
| Email | Gmail API | v1 |
| Data | Pandas + CSV | 2.2+ |
| Storage | JSON (atomic writes) | — |
| Config | Pydantic Settings | 2.4+ |
| Auth | Google OAuth 2.0 | — |
| Runtime | Python | 3.12+ |

---

## 🔒 Security

- All credentials loaded from `.env` — nothing hardcoded
- Google OAuth 2.0 — password never stored
- `.gitignore` protects `.env`, `credentials.json`, `token.json`
- HITL approval prevents accidental bulk sends
- API key displayed masked in Settings

---

## 🚨 Troubleshooting

| Problem | Solution |
|---------|----------|
| Agent not initializing | Check `.env` has all 3 Azure values, click Reinit in sidebar |
| Calendar/Gmail not working | Confirm `credentials.json` in project root, run connection test in Settings |
| HITL panel not appearing | Check HITL toggle is ON in sidebar, click Reinit |
| Meetings not saving | Check `data/` folder is writable, see System Logs for errors |
| Email replies not loading | Confirm Gmail credentials, check that emails were actually sent via Gmail |
| Port 8501 in use | `streamlit run ui/app.py --server.port 8502` |
| Import errors | `pip install -r requirements.txt --upgrade` |
| Terminal not found | Run from project root: `python -m app.main` |

---

## 📝 Requirements Checklist

**Backend**
- ✅ True sub-agent pattern — Supervisor coordinates 3 independent agents
- ✅ Calendar Agent with Google Calendar API
- ✅ Email Agent with Gmail API
- ✅ Data Agent with CSV (email, name, designation)
- ✅ Human-in-the-Loop for emails and calendar events
- ✅ Streaming responses
- ✅ Structured logging

**Streamlit UI**
- ✅ Tab-based professional interface (6 tabs)
- ✅ Chat with real-time streaming
- ✅ Meeting scheduler form with Pending → Approve → Send flow
- ✅ HITL approval panel with approve/reject per action
- ✅ Meeting status tracking (Approved/Pending/Rejected)
- ✅ Email replies tracker with Gmail thread lookup
- ✅ Availability detection from reply content
- ✅ Time-based reply filtering
- ✅ Email history with source tracking
- ✅ History and logs with CSV export
- ✅ Settings with diagnostics
- ✅ Atomic data persistence
- ✅ Session management with thread IDs
- ✅ Modular component architecture

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

Built with LangChain 0.3 · LangGraph 0.2 · Azure OpenAI · Streamlit 1.38 · Python 3.12