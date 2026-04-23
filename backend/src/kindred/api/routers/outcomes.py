"""POST /v1/ask/outcome — agent reports how useful the /ask result was."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from kindred.api.deps import db_session
from kindred.api.schemas.outcomes import ReportOutcomeReq
from kindred.facilitator.outcomes import report_outcome

router = APIRouter()


@router.post("/outcome", status_code=200)
async def outcome(
    req: ReportOutcomeReq,
    session: AsyncSession = Depends(db_session),
):
    try:
        audit_id = UUID(req.audit_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await report_outcome(
        session, audit_id=audit_id, result=req.result,
        notes=req.notes, chosen_content_id=req.chosen_content_id,
    )
    return {"ok": True}
