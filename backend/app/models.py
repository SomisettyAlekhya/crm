from pydantic import BaseModel
from typing import Optional


class HCPOut(BaseModel):
    id: int
    name: str
    specialty: str
    hospital: str
    tier: str
    phone: str


class SampleItem(BaseModel):
    name: str
    quantity: int = 1


class InteractionFormIn(BaseModel):
    """Payload from the structured form (left-hand 'Interaction Details' panel)."""
    hcp_name: str
    interaction_type: str
    raw_notes: str
    date: Optional[str] = None
    time: Optional[str] = None
    attendees: Optional[str] = None
    materials_shared: Optional[list[str]] = None
    samples_distributed: Optional[list[SampleItem]] = None
    manual_sentiment: Optional[str] = None  # user override of AI-inferred sentiment
    outcomes: Optional[str] = None
    followup_actions: Optional[str] = None


class InteractionUpdateIn(BaseModel):
    interaction_type: Optional[str] = None
    raw_notes: Optional[str] = None
    followup_required: Optional[bool] = None
    followup_date: Optional[str] = None
    outcomes: Optional[str] = None
    manual_sentiment: Optional[str] = None


class ChatMessageIn(BaseModel):
    session_id: str
    message: str


class FollowupIn(BaseModel):
    interaction_id: int
    followup_date: str
    note: Optional[str] = ""


class SummaryPreviewIn(BaseModel):
    raw_notes: str

