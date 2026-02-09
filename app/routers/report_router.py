from fastapi import APIRouter
from pydantic import BaseModel
import uuid
from app.services.checklist_service import generate_report
from app.routers.stt_router import transcripts_store

router = APIRouter(prefix="/api/reports", tags=["Reports"])

class ReportRequest(BaseModel):
    machine_id: str

@router.post("/generate")
async def create_report(req: ReportRequest):
    inspection_id = f"INSP-{uuid.uuid4().hex[:4].upper()}"
    report_md = generate_report(req.machine_id, transcripts_store)
    
    return {
        "inspection_id": inspection_id,
        "report_md": report_md
    }
