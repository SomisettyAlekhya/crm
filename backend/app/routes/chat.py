from fastapi import APIRouter
from app.models import ChatMessageIn
from app.agent.graph import run_agent_turn

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Server-side per-session slot-filling memory. A real deployment would back
# this with Redis / the SQL database keyed by user+session; in-memory is
# sufficient for this demo (no DB / API key requirement).
_SESSIONS: dict[str, dict] = {}


@router.post("")
def chat_turn(payload: ChatMessageIn):
    session_state = _SESSIONS.get(payload.session_id, {})
    try:
        result = run_agent_turn(payload.message, session_state)
    except Exception as exc:
        # Any unexpected error still returns a normal JSON response (rather
        # than letting the exception crash the connection), so the browser
        # always gets a real, CORS-safe response instead of a generic
        # "Failed to fetch". The session is reset so the conversation isn't
        # stuck in a broken state.
        _SESSIONS[payload.session_id] = {}
        return {
            "reply": "Sorry, I hit a snag processing that -- could you rephrase, "
                     "or start a new conversation?",
            "tool_used": None,
            "tool_result": None,
            "done": True,
            "error": str(exc),
        }

    # Persist slot-filling progress for the next turn unless the tool
    # completed (then reset so the next message starts a fresh intent).
    if result.get("done"):
        _SESSIONS[payload.session_id] = {}
    else:
        _SESSIONS[payload.session_id] = {
            k: v for k, v in result.items()
            if k in ("hcp_name", "interaction_type", "raw_notes", "intent", "interaction_id")
        }

    return {
        "reply": result.get("reply"),
        "tool_used": result.get("tool_name"),
        "tool_result": result.get("tool_result"),
        "done": result.get("done", False),
    }


@router.post("/reset/{session_id}")
def reset_session(session_id: str):
    _SESSIONS.pop(session_id, None)
    return {"reset": True}
