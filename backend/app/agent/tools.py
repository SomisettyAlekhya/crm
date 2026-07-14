"""
Tools available to the LangGraph HCP-interaction agent.

Each tool is a plain Python function decorated with @tool (LangChain's tool
decorator) so it can either be invoked directly by graph nodes (as done in
this project) or bound to an LLM for tool-calling if you later want the
agent to choose tools autonomously rather than via the deterministic router
in graph.py.

The 5 tools implemented (minimum required: 5, first two are mandatory):

1. log_interaction        -- REQUIRED. Create a new HCP interaction record.
2. edit_interaction       -- REQUIRED. Modify a previously logged interaction.
3. get_hcp_profile        -- Look up an HCP's profile + interaction history.
4. schedule_followup      -- Create/attach a follow-up reminder to an interaction.
5. generate_call_prep_summary -- Summarize past interactions before a visit.
"""
from langchain_core.tools import tool
from app import database as db
from app.agent.llm import summarize_interaction


@tool
def log_interaction_tool(
    hcp_name: str,
    interaction_type: str,
    raw_notes: str,
    date: str = "",
    time: str = "",
    attendees: str = "",
    materials_shared: list | None = None,
    samples_distributed: list | None = None,
    manual_sentiment: str | None = None,
    outcomes: str = "",
    followup_actions: str = "",
) -> dict:
    """
    Log a new interaction with a Healthcare Professional (HCP).

    Core required inputs are `hcp_name`, `interaction_type`, and `raw_notes`.
    Everything else is optional and mirrors the structured "Log HCP
    Interaction" form: date/time, attendees, materials shared, samples
    distributed, a rep-observed sentiment override, outcomes, and follow-up
    actions -- all of which get folded into the AI summarization context so
    the derived summary reflects the whole interaction, not just the free
    notes.

    Given the HCP's name, the interaction channel (e.g. 'In-person visit',
    'Phone call', 'Email', 'Conference'), and free-text notes describing what
    happened, this tool:
      1. Resolves the HCP record (or flags it as unknown).
      2. Sends the combined notes (raw notes + outcomes + follow-up actions)
         to the LLM layer (Groq gemma2-9b-it) to produce a structured
         summary: short summary, sentiment, topics/products discussed,
         number of samples dropped, and whether a follow-up is required
         (with a suggested date).
      3. If the rep manually selected a sentiment or logged explicit
         samples/materials, those override the AI-derived values.
      4. Generates a short list of AI-suggested follow-up actions (e.g.
         scheduling a next visit, sending requested materials, advisory
         board invites for top-tier HCPs) for the frontend's "AI Suggested
         Follow-ups" panel.
      5. Persists the resulting structured interaction record.

    Returns the newly created interaction record, including the AI-derived
    fields, so the frontend can show the rep exactly what was captured.
    """
    hcp = db.find_hcp_by_name(hcp_name)

    context_parts = [raw_notes]
    if outcomes:
        context_parts.append(f"Outcome: {outcomes}")
    if followup_actions:
        context_parts.append(f"Follow-up requested: {followup_actions}")
    ai_fields = summarize_interaction(" ".join(context_parts))

    sentiment = manual_sentiment.capitalize() if manual_sentiment else ai_fields["sentiment"]

    samples_distributed = samples_distributed or []
    samples_total = sum(s.get("quantity", 1) if isinstance(s, dict) else 1 for s in samples_distributed)
    samples_count = samples_total or ai_fields["samples_dropped"]

    followup_required = bool(followup_actions) or ai_fields["followup_required"]

    record = db.create_interaction({
        "hcp_id": hcp["id"] if hcp else None,
        "hcp_name": hcp["name"] if hcp else hcp_name,
        "interaction_type": interaction_type,
        "raw_notes": raw_notes,
        "date": date,
        "time": time,
        "attendees": attendees,
        "materials_shared": materials_shared or [],
        "samples_distributed": samples_distributed,
        "outcomes": outcomes,
        "followup_actions": followup_actions,
        "summary": ai_fields["summary"],
        "sentiment": sentiment,
        "topics_discussed": ai_fields["topics_discussed"],
        "samples_dropped": samples_count,
        "followup_required": followup_required,
        "followup_date": ai_fields["suggested_followup_date"],
        "source": "chat" if not date and not attendees else "form",
        "model_used": ai_fields["model_used"],
    })

    record["suggested_followups"] = _generate_suggested_followups(hcp, record)
    return record


def _generate_suggested_followups(hcp: dict | None, record: dict) -> list[str]:
    """
    Heuristic generator for the "AI Suggested Follow-ups" panel shown next
    to the structured form -- short, actionable next-step suggestions
    derived from the logged interaction (mirrors what a real LLM call would
    return, without requiring an API key).
    """
    suggestions = []
    if record.get("followup_required"):
        when = record.get("followup_date") or "in 2 weeks"
        suggestions.append(f"Schedule follow-up meeting {when}")
    topics = record.get("topics_discussed") or []
    for topic in topics[:1]:
        if topic and topic != "General product discussion":
            suggestions.append(f"Send {topic} efficacy data / brochure")
    if hcp and hcp.get("tier") == "A":
        suggestions.append(f"Add {hcp['name']} to advisory board invite list")
    if not suggestions:
        suggestions.append("No immediate follow-up action suggested")
    return suggestions


@tool
def edit_interaction_tool(interaction_id: int, updates: dict) -> dict | None:
    """
    Edit a previously logged interaction.

    Accepts the interaction's ID and a dict of fields to update (any subset
    of: interaction_type, raw_notes, summary, sentiment, manual_sentiment,
    outcomes, topics_discussed, samples_dropped, followup_required,
    followup_date). If `raw_notes` is part of the update, the tool re-runs
    the LLM summarization so the derived fields (summary/sentiment/topics/
    samples/follow-up) stay consistent with the edited notes -- exactly
    like the initial logging flow, so an edited note never leaves stale
    AI-derived fields behind. A `manual_sentiment` update always takes
    precedence over the AI-derived sentiment, letting a rep correct the
    inferred read on the HCP.

    Returns the updated record, or None if no interaction with that ID exists.
    """
    if "raw_notes" in updates and updates["raw_notes"]:
        ai_fields = summarize_interaction(updates["raw_notes"])
        updates = {
            **updates,
            "summary": ai_fields["summary"],
            "sentiment": ai_fields["sentiment"],
            "topics_discussed": ai_fields["topics_discussed"],
            "samples_dropped": ai_fields["samples_dropped"],
            "followup_required": ai_fields["followup_required"],
            "followup_date": ai_fields["suggested_followup_date"],
        }

    if updates.get("manual_sentiment"):
        updates["sentiment"] = updates.pop("manual_sentiment").capitalize()

    return db.update_interaction(interaction_id, updates)


@tool
def get_hcp_profile_tool(hcp_name: str) -> dict | None:
    """
    Retrieve an HCP's profile (specialty, hospital, tier, phone) along with
    their full interaction history, sorted most-recent first. Useful for a
    rep who wants a quick reference before or during a call, or for the
    agent to resolve which HCP a chat message is referring to.
    """
    hcp = db.find_hcp_by_name(hcp_name)
    if not hcp:
        return None
    history = db.list_interactions(hcp_id=hcp["id"])
    return {**hcp, "interaction_history": history}


@tool
def schedule_followup_tool(interaction_id: int, followup_date: str, note: str = "") -> dict | None:
    """
    Attach or update a follow-up reminder on an existing interaction. Takes
    the interaction ID, an ISO date (YYYY-MM-DD) for the follow-up, and an
    optional note (e.g. "bring updated efficacy data"). Marks the
    interaction as requiring follow-up and stores the date/note so it can
    surface in the rep's task list.
    """
    return db.update_interaction(interaction_id, {
        "followup_required": True,
        "followup_date": followup_date,
        "followup_note": note,
    })


@tool
def generate_call_prep_summary_tool(hcp_name: str) -> dict | None:
    """
    Generate a "call prep" briefing for an upcoming visit to a given HCP:
    pulls their profile and last 5 interactions, and asks the LLM layer to
    produce a short briefing covering relationship sentiment trend, last
    topics discussed, open follow-ups, and a suggested talking point for the
    next visit. Designed to be called right before a rep walks into a
    meeting.
    """
    hcp = db.find_hcp_by_name(hcp_name)
    if not hcp:
        return None
    history = db.list_interactions(hcp_id=hcp["id"])[:5]
    if not history:
        return {
            "hcp": hcp,
            "briefing": f"No prior interactions on file with {hcp['name']}. "
                        f"This will be a first touchpoint -- lead with an "
                        f"introduction and needs assessment.",
            "open_followups": [],
        }

    combined_notes = " | ".join(h.get("summary", "") for h in history)
    briefing_input = (
        f"HCP: {hcp['name']} ({hcp['specialty']}). Recent interaction "
        f"summaries: {combined_notes}"
    )
    ai_fields = summarize_interaction(briefing_input)
    open_followups = [h for h in history if h.get("followup_required")]

    return {
        "hcp": hcp,
        "briefing": ai_fields["summary"],
        "sentiment_trend": ai_fields["sentiment"],
        "last_topics": ai_fields["topics_discussed"],
        "open_followups": open_followups,
    }


ALL_TOOLS = [
    log_interaction_tool,
    edit_interaction_tool,
    get_hcp_profile_tool,
    schedule_followup_tool,
    generate_call_prep_summary_tool,
]
