from pydantic import BaseModel


class ReportOutcomeReq(BaseModel):
    audit_id: str
    result: str
    notes: str = ""
    chosen_content_id: str | None = None
