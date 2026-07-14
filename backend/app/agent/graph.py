"""
The LangGraph agent that powers the "Log Interaction" screen's conversational
mode (and, internally, backs the structured-form mode too, so both paths
converge on the exact same tool layer -- see tools.py).

Graph shape
-----------

        ┌──────────────┐
        │  classify_intent  │  <- decides which of the 5 tools this
        └───────┬───────┘     turn is about, from the user's message
                │
      ┌─────────┼──────────────────────┬───────────────────┬───────────────┐
      ▼         ▼                      ▼                    ▼               ▼
 collect_slots  edit_interaction  get_hcp_profile   schedule_followup  call_prep_summary
      │
      ▼ (once all required slots present)
 log_interaction
      │
      ▼
   respond  ──► END

`collect_slots` is what makes the chat interface feel conversational: if the
rep just types "Met Dr. Carter today, she seemed positive about Cardiozen,
dropped 10 samples" in one go, every slot is filled and the agent logs
immediately. If they only say "Log a visit with Dr. Patel", the agent asks
one follow-up question at a time (interaction type, then notes) before
calling the log_interaction tool -- identical end state to filling out the
structured form field by field.
"""
from langgraph.graph import StateGraph, END
from app.agent.state import AgentState
from app.agent.tools import (
    log_interaction_tool,
    edit_interaction_tool,
    get_hcp_profile_tool,
    schedule_followup_tool,
    generate_call_prep_summary_tool,
)
import re
from datetime import datetime, timedelta

REQUIRED_SLOTS = ["hcp_name", "interaction_type", "raw_notes"]
INTERACTION_TYPE_KEYWORDS = {
    "in-person visit": ["in person", "in-person", "visited", "met", "office visit"],
    "phone call": ["call", "phone", "rang"],
    "email": ["email", "e-mail", "sent a message"],
    "conference": ["conference", "congress", "symposium", "event"],
}


def _classify_intent(state: AgentState) -> AgentState:
    text = (state.get("user_message") or "").lower()
    has_interaction_ref = _extract_interaction_id(text) is not None

    if has_interaction_ref and any(k in text for k in ["edit", "update", "change", "correct", "fix"]):
        state["intent"] = "edit_interaction"
    elif any(k in text for k in ["prep", "before i see", "briefing", "getting ready"]):
        state["intent"] = "call_prep_summary"
    elif has_interaction_ref and any(k in text for k in ["follow up", "follow-up", "followup", "remind", "schedule"]):
        # Only treat this as "schedule a follow-up on an existing record" when
        # the message actually references an interaction number (e.g.
        # "interaction 1"). Otherwise phrases like "...follow up next month"
        # inside a brand-new interaction description would get misrouted
        # away from log_interaction.
        state["intent"] = "schedule_followup"
    elif any(k in text for k in ["profile", "history", "who is", "tell me about"]):
        state["intent"] = "get_hcp_profile"
    else:
        state["intent"] = "log_interaction"
    return state


# Words that commonly follow "Dr." in casual sentences but are NOT part of
# the HCP's name (this is what caused "Dr. Carter in person" to be parsed
# as "Dr. Carter In").
_NAME_STOPWORDS = {
    "in", "on", "at", "today", "yesterday", "this", "she", "he", "they",
    "was", "is", "said", "and", "discussed", "about", "regarding", "for",
    "to", "with", "about", "seemed", "we", "i",
}


def _extract_hcp_name(text: str) -> str | None:
    # Find where "Dr" / "Dr." starts (case-insensitive), then only look at
    # capitalized word(s) immediately after it -- this keeps "in person",
    # "today", etc. from being swept into the name.
    prefix = re.search(r"dr\.?\s*", text, re.IGNORECASE)
    if not prefix:
        return None
    rest = text[prefix.end():]

    # Prefer proper-cased words (e.g. "Carter", "Emily Carter").
    cased_match = re.match(r"[A-Z][a-zA-Z'-]*(?:\s+[A-Z][a-zA-Z'-]*)?", rest)
    if cased_match:
        return f"Dr. {cased_match.group(0)}"

    # Fallback for all-lowercase input, but stop at common stopwords so we
    # never grab a following verb/preposition as part of the name.
    words = re.findall(r"[a-zA-Z']+", rest)
    if not words or words[0].lower() in _NAME_STOPWORDS:
        return None
    name_words = [words[0]]
    if len(words) > 1 and words[1].lower() not in _NAME_STOPWORDS:
        name_words.append(words[1])
    return "Dr. " + " ".join(w.capitalize() for w in name_words)


def _extract_interaction_id(text: str) -> int | None:
    match = re.search(r"interaction\s*#?\s*(\d+)", text, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _extract_date(text: str) -> str | None:
    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if match:
        return match.group(0)
    lower = text.lower()
    if "next week" in lower:
        return (datetime.utcnow() + timedelta(days=7)).date().isoformat()
    if "next month" in lower:
        return (datetime.utcnow() + timedelta(days=30)).date().isoformat()
    return None


def _extract_interaction_type(text: str) -> str | None:
    lower = text.lower()
    for label, keywords in INTERACTION_TYPE_KEYWORDS.items():
        if any(k in lower for k in keywords):
            return label.title()
    return None


def _collect_slots(state: AgentState) -> AgentState:
    text = state.get("user_message", "")

    if not state.get("hcp_name"):
        name = _extract_hcp_name(text)
        if name:
            state["hcp_name"] = name

    if not state.get("interaction_type"):
        itype = _extract_interaction_type(text)
        if itype:
            state["interaction_type"] = itype

    # Once we know who/what channel, treat the rest of the running message(s)
    # as the note content to summarize.
    if state.get("hcp_name") and state.get("interaction_type"):
        state["raw_notes"] = ((state.get("raw_notes") or "") + " " + text).strip()

    missing = [slot for slot in REQUIRED_SLOTS if not state.get(slot)]
    state["missing_fields"] = missing

    if missing:
        prompts = {
            "hcp_name": "Which HCP is this interaction with?",
            "interaction_type": "What type of interaction was it (in-person visit, phone call, email, or conference)?",
            "raw_notes": "Great -- what happened during the interaction? (topics discussed, samples dropped, reactions, etc.)",
        }
        state["reply"] = prompts[missing[0]]
        state["done"] = False
    else:
        state["done"] = True
    return state


def _run_log_interaction(state: AgentState) -> AgentState:
    result = log_interaction_tool.invoke({
        "hcp_name": state["hcp_name"],
        "interaction_type": state["interaction_type"],
        "raw_notes": state["raw_notes"],
    })
    state["tool_name"] = "log_interaction"
    state["tool_result"] = result
    state["reply"] = (
        f"Logged your {state['interaction_type'].lower()} with {result['hcp_name']}. "
        f"Summary: {result['summary']} "
        f"({'Follow-up suggested for ' + result['followup_date'] if result['followup_required'] else 'No follow-up needed'}.)"
    )
    state["done"] = True
    return state


def _run_edit_interaction(state: AgentState) -> AgentState:
    text = state.get("user_message", "")
    interaction_id = state.get("interaction_id") or _extract_interaction_id(text)

    if not interaction_id:
        state["reply"] = "Which interaction number would you like to edit? (e.g. 'edit interaction 3')"
        state["intent"] = "edit_interaction"
        state["done"] = False
        return state

    state["interaction_id"] = interaction_id
    # Everything after the "interaction <id>" reference is treated as the
    # new note content, e.g. "edit interaction 1, change notes to: ...".
    notes_match = re.search(r"interaction\s*#?\s*\d+\D*(.*)", text, re.IGNORECASE)
    new_notes = notes_match.group(1).strip(" :,-") if notes_match else ""

    updates = {}
    if new_notes:
        updates["raw_notes"] = new_notes
    if state.get("interaction_type"):
        updates["interaction_type"] = state["interaction_type"]

    if not updates:
        state["reply"] = f"What should I change about interaction #{interaction_id}?"
        state["done"] = False
        return state

    result = edit_interaction_tool.invoke({"interaction_id": interaction_id, "updates": updates})
    state["tool_name"] = "edit_interaction"
    state["tool_result"] = result
    state["reply"] = (
        f"Updated interaction #{interaction_id}. New summary: {result['summary']}"
        if result else f"I couldn't find interaction #{interaction_id} to edit."
    )
    state["done"] = True
    return state


def _run_get_hcp_profile(state: AgentState) -> AgentState:
    name = state.get("hcp_name") or _extract_hcp_name(state.get("user_message", ""))
    result = get_hcp_profile_tool.invoke({"hcp_name": name or ""})
    state["tool_name"] = "get_hcp_profile"
    state["tool_result"] = result
    state["reply"] = (
        f"{result['name']} ({result['specialty']}, {result['hospital']}) has "
        f"{len(result['interaction_history'])} logged interaction(s)."
        if result else f"I couldn't find an HCP matching '{name}'."
    )
    state["done"] = True
    return state


def _run_schedule_followup(state: AgentState) -> AgentState:
    text = state.get("user_message", "")
    interaction_id = state.get("interaction_id") or _extract_interaction_id(text)
    followup_date = state.get("followup_date") or _extract_date(text)

    if not interaction_id:
        state["reply"] = "Which interaction number is this follow-up for? (e.g. 'interaction 1')"
        state["intent"] = "schedule_followup"
        state["done"] = False
        return state

    if not followup_date:
        state["interaction_id"] = interaction_id
        state["reply"] = "What date should the follow-up be? (YYYY-MM-DD, or 'next week' / 'next month')"
        state["intent"] = "schedule_followup"
        state["done"] = False
        return state

    result = schedule_followup_tool.invoke({
        "interaction_id": interaction_id,
        "followup_date": followup_date,
        "note": "",
    })
    state["tool_name"] = "schedule_followup"
    state["tool_result"] = result
    state["reply"] = (
        f"Follow-up scheduled for {result['followup_date']}."
        if result else f"I couldn't find interaction #{interaction_id} to schedule a follow-up on."
    )
    state["done"] = True
    return state


def _run_call_prep(state: AgentState) -> AgentState:
    name = state.get("hcp_name") or _extract_hcp_name(state.get("user_message", ""))
    result = generate_call_prep_summary_tool.invoke({"hcp_name": name or ""})
    state["tool_name"] = "call_prep_summary"
    state["tool_result"] = result
    state["reply"] = result["briefing"] if result else f"No profile found for '{name}'."
    state["done"] = True
    return state


def _route(state: AgentState) -> str:
    intent = state.get("intent", "log_interaction")
    return {
        "log_interaction": "collect_slots",
        "edit_interaction": "edit_interaction",
        "get_hcp_profile": "get_hcp_profile",
        "schedule_followup": "schedule_followup",
        "call_prep_summary": "call_prep_summary",
    }.get(intent, "collect_slots")


def _after_slots(state: AgentState) -> str:
    return "log_interaction" if state.get("done") else END


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("classify_intent", _classify_intent)
    graph.add_node("collect_slots", _collect_slots)
    graph.add_node("log_interaction", _run_log_interaction)
    graph.add_node("edit_interaction", _run_edit_interaction)
    graph.add_node("get_hcp_profile", _run_get_hcp_profile)
    graph.add_node("schedule_followup", _run_schedule_followup)
    graph.add_node("call_prep_summary", _run_call_prep)

    graph.set_entry_point("classify_intent")
    graph.add_conditional_edges("classify_intent", _route, {
        "collect_slots": "collect_slots",
        "edit_interaction": "edit_interaction",
        "get_hcp_profile": "get_hcp_profile",
        "schedule_followup": "schedule_followup",
        "call_prep_summary": "call_prep_summary",
    })
    graph.add_conditional_edges("collect_slots", _after_slots, {
        "log_interaction": "log_interaction",
        END: END,
    })
    graph.add_edge("log_interaction", END)
    graph.add_edge("edit_interaction", END)
    graph.add_edge("get_hcp_profile", END)
    graph.add_edge("schedule_followup", END)
    graph.add_edge("call_prep_summary", END)

    return graph.compile()


compiled_graph = build_graph()


def run_agent_turn(user_message: str, session_state: dict) -> dict:
    """
    Entry point called by the /chat route. `session_state` carries over
    slot-filling progress between turns of the same conversation (kept
    server-side, keyed by a session id, in routes/chat.py).
    """
    state: AgentState = {**session_state, "user_message": user_message, "mode": "chat"}
    result = compiled_graph.invoke(state)
    return result
