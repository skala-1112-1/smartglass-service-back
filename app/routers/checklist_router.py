from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.checklist_service import get_checklist, update_checklist_item

router = APIRouter(prefix="/api/checklists", tags=["Checklists"])

class ChecklistUpdateRequest(BaseModel):
    done: bool

@router.get("/machine")
async def get_machine_checklist(machine_id: str):
    items = get_checklist(machine_id)
    if not items:
        raise HTTPException(status_code=404, detail="체크리스트를 찾을 수 없습니다")
    return {"machine_id": machine_id, "items": items}

@router.put("/machine/item")
async def update_checklist_item_status(machine_id: str, item_index: int, req: ChecklistUpdateRequest):
    success = update_checklist_item(machine_id, item_index, req.done)
    if not success:
        raise HTTPException(status_code=404, detail="해당 기계 또는 체크리스트 항목을 찾을 수 없습니다")
    
    # 업데이트된 체크리스트 반환
    updated_items = get_checklist(machine_id)
    return {
        "machine_id": machine_id,
        "items": updated_items
    }
