"""
In-memory mock 'database' layer.

Design intent
-------------
The production system is meant to run on MySQL/PostgreSQL. To make this
project runnable by anyone WITHOUT provisioning a real database or setting
any credentials, this module implements the exact same access pattern
(simple repository functions returning dict-shaped "rows") backed by
Python data structures in memory.

If you want to point this at a real Postgres/MySQL instance, replace the
functions in this file with SQLAlchemy queries -- the rest of the app
(routes, agent tools) only imports these functions and never touches
storage directly, so the swap is isolated to this one file.
"""
from datetime import datetime
from itertools import count
from typing import Optional

_hcp_id_counter = count(1)
_interaction_id_counter = count(1)

# Seed a handful of Healthcare Professionals so the demo has data to work with.
HCPS: dict[int, dict] = {}
INTERACTIONS: dict[int, dict] = {}


def _seed():
    seed_hcps = [
        {"name": "Dr. Emily Carter", "specialty": "Cardiology", "hospital": "St. Luke's Medical Center", "tier": "A", "phone": "555-0142"},
        {"name": "Dr. Raj Patel", "specialty": "Endocrinology", "hospital": "Northshore Clinic", "tier": "B", "phone": "555-0198"},
        {"name": "Dr. Maria Gomez", "specialty": "Oncology", "hospital": "Riverside Hospital", "tier": "A", "phone": "555-0177"},
        {"name": "Dr. Alan Wong", "specialty": "General Practice", "hospital": "Downtown Health", "tier": "C", "phone": "555-0111"},
    ]
    for hcp in seed_hcps:
        create_hcp(hcp["name"], hcp["specialty"], hcp["hospital"], hcp["tier"], hcp["phone"])


def create_hcp(name: str, specialty: str, hospital: str, tier: str = "B", phone: str = "") -> dict:
    hcp_id = next(_hcp_id_counter)
    record = {
        "id": hcp_id,
        "name": name,
        "specialty": specialty,
        "hospital": hospital,
        "tier": tier,
        "phone": phone,
        "created_at": datetime.utcnow().isoformat(),
    }
    HCPS[hcp_id] = record
    return record


def list_hcps() -> list[dict]:
    return list(HCPS.values())


def get_hcp(hcp_id: int) -> Optional[dict]:
    return HCPS.get(hcp_id)


def find_hcp_by_name(name: str) -> Optional[dict]:
    name_lower = name.strip().lower()
    for hcp in HCPS.values():
        if name_lower in hcp["name"].lower():
            return hcp
    return None


def create_interaction(data: dict) -> dict:
    interaction_id = next(_interaction_id_counter)
    record = {
        "id": interaction_id,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        **data,
    }
    INTERACTIONS[interaction_id] = record
    return record


def list_interactions(hcp_id: Optional[int] = None) -> list[dict]:
    values = list(INTERACTIONS.values())
    if hcp_id is not None:
        values = [v for v in values if v.get("hcp_id") == hcp_id]
    return sorted(values, key=lambda r: r["id"], reverse=True)


def get_interaction(interaction_id: int) -> Optional[dict]:
    return INTERACTIONS.get(interaction_id)


def update_interaction(interaction_id: int, updates: dict) -> Optional[dict]:
    record = INTERACTIONS.get(interaction_id)
    if not record:
        return None
    record.update(updates)
    record["updated_at"] = datetime.utcnow().isoformat()
    return record


def delete_interaction(interaction_id: int) -> bool:
    return INTERACTIONS.pop(interaction_id, None) is not None


_seed()
