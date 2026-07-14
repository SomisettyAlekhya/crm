"""
Shared state object passed between nodes in the LangGraph graph.

LangGraph works over a typed dict (or Pydantic model) that every node reads
from and writes back to. Keeping it here (rather than inline in graph.py)
makes it easy for both the chat-mode and form-mode entry points to share the
same schema.
"""
from typing import TypedDict, Optional, Literal


class AgentState(TypedDict, total=False):
    # --- Routing ---
    intent: Optional[Literal[
        "log_interaction", "edit_interaction", "get_hcp_profile",
        "schedule_followup", "call_prep_summary", "unknown",
    ]]

    # --- Raw input ---
    user_message: str                 # latest chat message (chat mode)
    mode: Literal["chat", "form"]

    # --- Slots being filled during conversational logging ---
    hcp_name: Optional[str]
    hcp_id: Optional[int]
    interaction_type: Optional[str]   # e.g. "In-person visit", "Call", "Email"
    raw_notes: Optional[str]
    interaction_id: Optional[int]     # set when editing an existing interaction

    # --- Tool outputs ---
    tool_name: Optional[str]
    tool_result: Optional[dict]

    # --- Conversation bookkeeping ---
    missing_fields: list[str]
    reply: Optional[str]
    done: bool
