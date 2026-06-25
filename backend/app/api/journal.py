"""Trade journal endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.state import AppState

from .deps import get_state

router = APIRouter(prefix="/journal", tags=["journal"])


class JournalIn(BaseModel):
    text: str
    tags: list[str] = []


@router.get("")
def list_entries(state: AppState = Depends(get_state)) -> dict:
    return {"entries": [e.as_dict() for e in state.journal.entries()]}


@router.post("")
def add_entry(payload: JournalIn, state: AppState = Depends(get_state)) -> dict:
    entry = state.journal.add(payload.text, payload.tags)
    return entry.as_dict()
