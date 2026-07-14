# HCP CRM — Log Interaction Module

A field-rep-facing CRM module for logging interactions with Healthcare
Professionals (HCPs), built as a life-sciences CRM feature. The core screen
— **Log Interaction** — lets a rep capture a visit either through a
**structured form** or a **conversational chat interface**, both backed by
the same LangGraph agent and tools.

> **No API key. No database setup.** This submission runs entirely
> in-memory / offline so it can be cloned and run immediately. See
> [Design notes: why no key/DB](#design-notes-why-no-api-key--database) below.

---

## Tech stack

| Layer            | Choice                                            |
|------------------|----------------------------------------------------|
| Frontend         | React 18 + Redux Toolkit                          |
| Backend          | Python + FastAPI                                  |
| AI agent         | LangGraph                                         |
| LLMs (designed for) | Groq — `gemma2-9b-it` (primary), `llama-3.3-70b-versatile` (fallback for longer chat context) |
| Database (designed for) | MySQL / PostgreSQL                          |
| Font             | Google Inter                                      |

---

## Project structure

```
hcp-crm/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI app + router registration
│   │   ├── database.py            # In-memory mock "database" layer
│   │   ├── models.py              # Pydantic request/response schemas
│   │   ├── agent/
│   │   │   ├── state.py           # LangGraph shared state schema
│   │   │   ├── tools.py           # The 5 LangGraph tools
│   │   │   ├── graph.py           # StateGraph wiring + router + slot-filling
│   │   │   └── llm.py             # Groq wrapper w/ offline heuristic fallback
│   │   └── routes/
│   │       ├── hcps.py            # GET HCP directory / profile
│   │       ├── interactions.py    # Structured-form CRUD + follow-up + call-prep
│   │       └── chat.py            # Conversational endpoint (session-based)
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── public/index.html          # Loads Google Inter
    ├── src/
    │   ├── App.jsx                # Sidebar shell
    │   ├── index.js / index.css
    │   ├── api/api.js             # fetch() wrapper for the backend
    │   ├── store/
    │   │   ├── store.js
    │   │   └── slices/
    │   │       ├── interactionSlice.js  # HCPs + interactions + form thunks
    │   │       └── chatSlice.js         # chat messages + session id
    │   └── components/
    │       ├── LogInteractionScreen.jsx # mode toggle: form vs chat
    │       ├── StructuredForm.jsx
    │       ├── ChatInterface.jsx
    │       └── InteractionList.jsx
    └── package.json
```

---

## How to run

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs (Swagger UI) will be available at `http://localhost:8000/docs`.

No `.env` file is required. If you later add a real `GROQ_API_KEY`
environment variable, `app/agent/llm.py` will automatically start routing
summarization calls through Groq instead of the offline heuristic — no
other code changes needed.

### Frontend

```bash
cd frontend
npm install
npm start
```

Runs on `http://localhost:3000` and talks to the backend at
`http://localhost:8000` by default (override with `REACT_APP_API_URL`).

---

## Sidebar screens

All sidebar items are functional (client-side view switching, no extra
routing library needed):

- **Log Interaction** — described above.
- **HCP Directory** — browse/search all HCPs; selecting one calls
  `get_hcp_profile_tool` and shows their full interaction history.
- **Call Prep** — pick an HCP and generate a pre-visit briefing via
  `generate_call_prep_summary_tool`.
- **Follow-ups** — lists every interaction currently flagged
  `followup_required`, soonest due date first, with a "Mark Done" button
  that calls `edit_interaction_tool` to clear the flag.
- **Reports** — a simple session rollup (total interactions, samples
  distributed, pending follow-ups, sentiment breakdown, interactions per
  HCP) computed from the same `/api/interactions` data.

## The Log Interaction screen

Matches the target layout: the **Interaction Details** form and the **AI
Assistant** chat panel sit side by side, both feeding the same backend tools
— so every one of the 5 tools is reachable from *either* surface, not just
chat.

- **Structured Form (left)** — HCP name (with **View Profile** and
  **Call Prep** buttons next to it), interaction type, date/time,
  attendees, topics discussed (with a "Summarize from Voice Note" preview
  button), materials shared, samples distributed, an observed/inferred
  sentiment override, outcomes, follow-up actions (with a **Schedule
  Follow-up** button + date), and an **AI Suggested Follow-ups** list that
  appears after logging.
- **AI Assistant (right)** — a chat box where the rep just describes what
  happened in plain language ("Met Dr. Carter, discussed Cardiozen, dropped
  8 samples") or asks for a profile, follow-up, or call prep. The LangGraph
  agent extracts the HCP, interaction type, and notes across as many turns
  as needed before logging.
- Both surfaces call the **same backend tools**, so results are identical in
  shape regardless of entry method:

  | Tool | Structured form | Chat |
  |---|---|---|
  | `log_interaction` | "Log Interaction" button | e.g. "Met Dr. Carter, discussed Cardiozen, dropped 8 samples" |
  | `edit_interaction` | "Edit" on any item in Recent Interactions | e.g. "edit interaction 1, change notes to..." |
  | `get_hcp_profile` | "View Profile" button next to HCP Name | e.g. "tell me about Dr. Patel" |
  | `schedule_followup` | "Schedule Follow-up" button + date picker | e.g. "schedule a follow-up for interaction 1 on 2026-08-01" |
  | `generate_call_prep_summary` | "Call Prep" button next to HCP Name | e.g. "call prep for Dr. Gomez" |

- A running **Recent Interactions** list below both panels shows everything
  logged in the session, each with an inline **Edit** action.

---

## LangGraph agent: role & tools

### Role of the agent

The LangGraph agent is the single reasoning layer sitting between "what the
rep says or fills in" and "what gets written to the CRM." Its job is to:

1. **Classify intent** — is this turn about logging a new interaction,
   editing one, looking up an HCP's profile, scheduling a follow-up, or
   prepping for a call?
2. **Fill in missing information conversationally** — if the rep hasn't
   said who the HCP is or what channel was used, the agent asks exactly one
   clarifying question at a time instead of failing or asking everything at
   once.
3. **Delegate to the right tool** once it has what it needs, and turn the
   tool's structured output back into a natural-language reply for the chat
   UI.
4. **Keep AI-derived fields consistent** — any time raw notes are
   created *or edited*, the same summarization step runs, so summaries,
   sentiment, and follow-up flags never go stale relative to the notes.

The graph (see `backend/app/agent/graph.py`) has this shape:

```
classify_intent → (router) → collect_slots → log_interaction → END
                           → edit_interaction → END
                           → get_hcp_profile → END
                           → schedule_followup → END
                           → call_prep_summary → END
```

### The 5 tools (`backend/app/agent/tools.py`)

1. **`log_interaction_tool`** *(required)* — Takes `hcp_name`,
   `interaction_type`, and `raw_notes`. Resolves the HCP record, then sends
   the raw notes to the LLM layer (`gemma2-9b-it` via Groq, or the offline
   heuristic fallback) to derive: a short summary, sentiment
   (Positive/Neutral/Negative), topics/products discussed (entity
   extraction over known product keywords), number of samples dropped, and
   whether a follow-up is required (with a suggested date parsed from
   phrases like "next week" / "next month"). Persists the full structured
   record.

2. **`edit_interaction_tool`** *(required)* — Takes an `interaction_id` and
   a dict of field updates. If `raw_notes` is among the updates, it re-runs
   the exact same LLM summarization used at creation time, so summary /
   sentiment / topics / samples / follow-up stay in sync with the edited
   text rather than silently going stale.

3. **`get_hcp_profile_tool`** — Looks up an HCP by name and returns their
   profile (specialty, hospital, tier, phone) plus their full interaction
   history, most recent first. Powers "who is Dr. Patel" / profile lookups
   in chat.

4. **`schedule_followup_tool`** — Attaches or updates a follow-up reminder
   (date + note) on a specific interaction, independent of whether it was
   originally logged with one.

5. **`generate_call_prep_summary_tool`** — Pulls an HCP's last 5
   interactions, feeds the combined summaries back through the LLM layer to
   produce a short pre-visit briefing (sentiment trend, last topics
   discussed, open follow-ups), so a rep can prep for a visit in seconds.

---

## Design notes: why no API key / database

Per the submission instructions, this repo is built to run **with zero API
keys and zero database provisioning**:

- **LLM layer** (`app/agent/llm.py`) is written against the real Groq API
  (`gemma2-9b-it` primary, `llama-3.3-70b-versatile` fallback) with a single
  clearly-marked function, `_call_groq`, as the integration seam. If
  `GROQ_API_KEY` isn't set (the default for this submission), every call
  transparently falls back to a small deterministic heuristic (sentence
  extraction for summaries, keyword/regex matching for topics, samples, and
  follow-up dates, keyword scoring for sentiment) so the whole pipeline —
  routing, slot-filling, tool calls, structured output — still runs exactly
  as it would with a real model, just without real generative text.
- **Database layer** (`app/database.py`) implements the same
  repository-function interface a SQLAlchemy/Postgres layer would
  (`create_interaction`, `list_interactions`, `update_interaction`, etc.)
  but backs it with in-memory Python dicts, seeded with a handful of sample
  HCPs. Every other module (routes, tools, graph) only ever imports these
  functions, so pointing the app at real MySQL/Postgres later is a
  single-file change.

---

## What we understood from the task

The task asks for the **HCP interaction logging module** of a life-sciences
CRM: a screen flexible enough for reps to log a visit either by filling out
a form or by just talking to an assistant, with an AI agent underneath that
turns messy real-world descriptions ("stopped by, she was excited about the
new data, left some samples, wants a call back in two weeks") into clean,
structured, queryable CRM records — and that same agent should expose
composable tools (logging, editing, profile lookup, follow-ups, call prep)
rather than being a single monolithic "chatbot" bolted onto the form.
