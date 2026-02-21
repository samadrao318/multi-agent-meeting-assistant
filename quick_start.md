# ⚡ Quick Start Guide
## Multi-Agent Meeting & Email Automation System

---

## Before You Start — What You Need

| Requirement | Details |
|-------------|---------|
| Python | 3.12 or higher |
| Azure OpenAI | Active resource with a deployed model |
| Google Cloud | Only needed for Calendar and Gmail features |

> The **Data Agent** (contacts) works immediately with only Azure OpenAI. You can demo the full chat and contact features without any Google setup.

---

## Step 1 — Install

**Option A — uv (recommended, much faster):**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
cd your_project_folder
uv sync
```

**Option B — pip:**
```bash
cd your_project_folder
python -m venv .venv

# Windows:
.venv\Scripts\activate

# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

---

## Step 2 — Azure OpenAI Credentials

Create a file named `.env` in the project root folder (same level as `requirements.txt`):

```
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-4
```

**Where to get each value:**

`AZURE_OPENAI_ENDPOINT`
→ Azure Portal → Your OpenAI resource → Overview → copy the Endpoint URL

`AZURE_OPENAI_API_KEY`
→ Same resource → Keys and Endpoint → copy Key 1

`AZURE_OPENAI_DEPLOYMENT`
→ Same resource → Model Deployments → copy your deployment name (e.g. gpt-4, gpt-4o)

---

## Step 3 — Google APIs (Optional)

Skip this if you only need contacts and chat. Come back when you want real Calendar and Gmail features.

**Enable APIs:**
1. Go to [console.cloud.google.com](https://console.cloud.google.com/)
2. Create or select a project
3. Click APIs & Services → Library
4. Search and enable: **Google Calendar API**
5. Search and enable: **Gmail API**

**Create credentials:**
1. Click APIs & Services → Credentials
2. Click Create Credentials → OAuth 2.0 Client ID
3. If asked, set up consent screen — choose External type, add your email
4. Application type: **Desktop app** → give any name → Create
5. Click **Download JSON**
6. Rename the file to exactly: `credentials.json`
7. Move it to your project root folder

**First-time Google login:**
The first time you use Calendar or Gmail, a browser window opens automatically.
Sign in → Click Allow → `token.json` is created. You only do this once.

---

## Step 4 — Contacts File

```bash
mkdir -p data
```

Create `data/contacts.csv`:
```
email,name,designation
alice@company.com,Alice Smith,Product Manager
bob@company.com,Bob Johnson,Software Engineer
carol@company.com,Carol White,Designer
john@company.com,John Doe,Team Lead
```

Columns must be in this order: `email`, `name`, `designation`
You can edit this file directly anytime — the Data Agent always reads the latest version.

---

## Step 5 — Launch

**Web UI (recommended):**
```bash
streamlit run ui/app.py
```

Open browser: **http://localhost:8501**

**Terminal interface:**
```bash
python -m app.main
```

---

## First Launch Checklist

When the app opens for the first time:

- [ ] Header shows 🟢 **Azure Connected** badge
- [ ] Header shows 🟢 **Agent Ready** badge
- [ ] Google badge shows 🟢 if you added `credentials.json`, or 🟡 if skipped
- [ ] Sidebar shows your session Thread ID
- [ ] HITL toggle is ON by default

If the Agent badge is red, check the Settings tab → Connections for the exact error.

---

## Navigation — 5 Tabs

```
| 💬 Chat | 📅 Meeting Scheduler | 📊 Status Dashboard | 📜 History & Logs | ⚙️ Settings |
```

| Tab | What you do here |
|-----|-----------------|
| 💬 Chat | Type natural language requests — agents respond in real-time |
| 📅 Meeting Scheduler | Fill a form → save meeting → send email invites in one click |
| 📊 Status Dashboard | See all meetings and emails, update statuses |
| 📜 History & Logs | Browse full history, search, filter, download CSVs |
| ⚙️ Settings | Check connections, toggle HITL, run diagnostics |

---

## Try These First

Open the Chat tab and test each command:

**Test 1 — Contacts (no Google needed)**
```
Show me all contacts
```
Expected: lists your contacts from contacts.csv

**Test 2 — Search**
```
Search for engineers
```
Expected: returns contacts where designation includes engineer

**Test 3 — Add contact**
```
Add contact: test@company.com, Test User, QA Engineer
```
Expected: new row added to contacts.csv

**Test 4 — Calendar (needs Google)**
```
Schedule a meeting tomorrow at 2pm for 1 hour
```
Expected: HITL panel appears → you approve → event created on Google Calendar

**Test 5 — Email (needs Google)**
```
Send an email to alice@company.com about the project status update
```
Expected: HITL panel appears → you approve → email sent via Gmail

---

## HITL Approval — Step by Step

When you run a command that needs Calendar or Gmail, the agent pauses and shows this:

```
⚠️ Human Approval Required

Action 1: send_email
To:       alice@company.com
Subject:  Project Status Update
Body:     Dear Alice, here is the latest update...

[ ✅ Approve ]   [ ❌ Reject ]
```

**What to do:**
1. Read the action details
2. Click **Approve** — card turns green
3. Click **Submit Decisions and Continue**
4. Agent resumes and executes the approved action
5. Record is saved to `data/emails_sent.json`

**If you click Reject:** nothing is sent, nothing is saved for that action.
**Cancel button:** discards all pending actions at once.

---

## Meeting Scheduler — Step by Step

1. Click the **📅 Meeting Scheduler** tab
2. Fill in the form:
   - Title (required)
   - Date — defaults to tomorrow
   - Start and end time
   - Location or meeting link (optional)
   - Select attendees from the dropdown (loaded from your contacts)
   - Add extra emails if needed
   - Email subject and body — or leave blank to auto-generate
3. Click **Schedule & Send Email**
4. What happens:
   - Meeting record saved to `data/meetings_status.json` immediately
   - Email record saved per attendee
   - If HITL is ON, approval panel appears — approve to send emails
   - Google Calendar event is created
   - Confirmation shown with attendee count
5. Meeting appears in the history table below with status: Pending

---

## Sidebar Controls

| Control | What it does |
|---------|-------------|
| 🟢/🔴 Status badges | Shows if Azure, Google, and Agent are connected |
| Thread ID | Unique ID for current session — changes on Clear Chat |
| HITL Toggle | ON = approve before emails/calendar · OFF = execute automatically |
| Clear Chat | Resets conversation history, creates new thread, keeps agent running |
| Reinit | Re-initializes the AI agent — use after changing .env or toggling HITL |

---

## Common Problems

**"Azure credentials missing" error at startup**
Your `.env` file is either not in the right folder or has wrong values.
→ Check the file is in the project root (same folder as `requirements.txt`)
→ No quotes around values, no spaces around the `=` sign
→ Click Reinit in sidebar after fixing

**Agent badge is red after startup**
→ Open Settings tab → Connections — the exact error message is shown there
→ Click Reinit in sidebar

**Calendar or Email gives an error**
→ Make sure `credentials.json` is in the project root
→ Settings tab → Connections → click Test button
→ If token expired: delete `token.json`, try any Calendar command, re-authorize in browser

**HITL panel never shows up**
→ Check HITL toggle in sidebar is ON (blue)
→ Click Reinit to apply

**Meetings showing but status not updating**
→ Click the Save button after changing the dropdown in the table
→ Or use the Status Dashboard tab → Update Meeting Status section

**Port 8501 already in use**
```bash
streamlit run ui/app.py --server.port 8502
```

**ModuleNotFoundError at startup**
```bash
pip install -r requirements.txt --upgrade
```

---

## Data Files

After running the app, your data folder contains:

```
data/
├── contacts.csv            Edit directly — auto-read by Data Agent
├── meetings_status.json    Auto-created — all meeting records
└── emails_sent.json        Auto-created — all email records
```

You can download CSV exports of all three from the **History & Logs** tab at any time.

---

## Run Both Interfaces Together

The Streamlit UI and the terminal interface share the same backend and data files. You can run both at the same time:

```bash
# Terminal 1
streamlit run ui/app.py

# Terminal 2
python -m app.main
```

Actions in one interface do not affect the other's session, but both read and write to the same `data/` folder.

---

## Useful Commands Summary

```bash
# Launch web UI
streamlit run ui/app.py

# Launch on different port
streamlit run ui/app.py --server.port 8502

# Launch terminal interface
python -m app.main

# Install / update packages
pip install -r requirements.txt --upgrade

# Verify packages installed correctly
python -c "import streamlit; import langchain; import langgraph; print('All OK')"
```

---

For full documentation see [README.md](README.md)