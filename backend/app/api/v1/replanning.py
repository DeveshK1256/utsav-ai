from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.replanning import (
    ChangeRequestSchema,
    ChangeProposalResponseSchema,
    PatchChangeProposalSchema
)
from backend.app.services.replanning_service import ReplanningService

router = APIRouter(prefix="/events/{id}/changes", tags=["Replanning (Plan B)"])


@router.get("", response_model=List[ChangeProposalResponseSchema])
def list_change_proposals(
    id: str,
    db: Session = Depends(get_db)
):
    """
    Lists all change proposals for the specified event.
    """
    from backend.app.models.models import ChangeEvent
    changes = db.query(ChangeEvent).filter(ChangeEvent.event_id == id).order_by(ChangeEvent.created_at.desc()).all()
    results = []
    for c in changes:
        try:
            results.append(ReplanningService.get_change_proposal(db, event_id=id, change_id=c.id))
        except Exception:
            pass
    return results


@router.post("", response_model=ChangeProposalResponseSchema, status_code=status.HTTP_201_CREATED)
def submit_change_event(
    id: str,
    payload: ChangeRequestSchema,
    db: Session = Depends(get_db)
):
    """
    Submits a change event (guest count, vendor cancel, date move, budget cut, venue unavailable).
    Computes deterministic diffs and returns proposal without mutating database (unless later accepted).
    """
    try:
        proposal = ReplanningService.create_change_proposal(db, event_id=id, change_req=payload)
        return proposal
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Replanning error: {str(e)}")


@router.get("/{change_id}", response_model=ChangeProposalResponseSchema)
def get_change_proposal(
    id: str,
    change_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves an existing change proposal diff and explanation.
    """
    try:
        return ReplanningService.get_change_proposal(db, event_id=id, change_id=change_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{change_id}/accept", response_model=ChangeProposalResponseSchema)
def accept_change_proposal(
    id: str,
    change_id: str,
    db: Session = Depends(get_db)
):
    """
    Explicit user confirmation to accept and atomically apply the proposal to the database.
    Mutates budget, tasks, sub-events, logs event, and promotes next queued change.
    """
    try:
        return ReplanningService.accept_change(db, event_id=id, change_id=change_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Accept error: {str(e)}")


@router.post("/{change_id}/reject", response_model=ChangeProposalResponseSchema)
def reject_change_proposal(
    id: str,
    change_id: str,
    db: Session = Depends(get_db)
):
    """
    Explicit user rejection of a change proposal. Database remains untouched.
    """
    try:
        return ReplanningService.reject_change(db, event_id=id, change_id=change_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Reject error: {str(e)}")


@router.patch("/{change_id}", response_model=ChangeProposalResponseSchema)
def patch_change_proposal(
    id: str,
    change_id: str,
    payload: PatchChangeProposalSchema,
    db: Session = Depends(get_db)
):
    """
    Allows user manual edits/overrides to proposal diffs prior to acceptance.
    """
    try:
        return ReplanningService.patch_change(db, event_id=id, change_id=change_id, patch_data=payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Patch error: {str(e)}")
