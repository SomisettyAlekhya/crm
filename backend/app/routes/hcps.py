from fastapi import APIRouter, HTTPException
from app import database as db
from app.agent.tools import get_hcp_profile_tool

router = APIRouter(prefix="/api/hcps", tags=["hcps"])


@router.get("")
def get_all_hcps():
    return db.list_hcps()


@router.get("/profile")
def get_hcp_profile_by_name(name: str):
    """
    Used by the structured form's "View Profile" button next to HCP Name --
    calls the exact same `get_hcp_profile` LangGraph tool that chat-mode
    uses, so both entry points exercise the same tool.
    """
    result = get_hcp_profile_tool.invoke({"hcp_name": name})
    if not result:
        raise HTTPException(status_code=404, detail=f"No HCP found matching '{name}'")
    return result


@router.get("/{hcp_id}")
def get_hcp(hcp_id: int):
    hcp = db.get_hcp(hcp_id)
    if not hcp:
        raise HTTPException(status_code=404, detail="HCP not found")
    history = db.list_interactions(hcp_id=hcp_id)
    return {**hcp, "interaction_history": history}
