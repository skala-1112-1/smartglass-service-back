from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.services.checklist_service import get_checklist, update_checklist_item
from app.database import get_db
from app.models import Checklist

router = APIRouter(prefix="/api/checklists", tags=["Checklists"])

class ChecklistUpdateRequest(BaseModel):
    done: bool

class ChecklistCreateRequest(BaseModel):
    item_index: int
    todo: str
    done: Optional[bool] = False
    summary: Optional[str] = None

@router.get("/machine")
async def get_machine_checklist(machine_id: str, db: Session = Depends(get_db)):
    """데이터베이스에서 특정 기계의 체크리스트를 조회합니다."""
    items = get_checklist(machine_id, db)
    if not items:
        raise HTTPException(status_code=404, detail="체크리스트를 찾을 수 없습니다")
    return {"machine_id": machine_id, "items": items}

@router.put("/machine/item")
async def update_checklist_item_status(
    machine_id: str, 
    item_index: int, 
    req: ChecklistUpdateRequest,
    db: Session = Depends(get_db)
):
    """체크리스트 항목의 완료 상태를 업데이트합니다."""
    success = update_checklist_item(machine_id, item_index, req.done, db)
    if not success:
        raise HTTPException(status_code=404, detail="해당 기계 또는 체크리스트 항목을 찾을 수 없습니다")
    
    # 업데이트된 체크리스트 반환
    updated_items = get_checklist(machine_id, db)
    return {
        "machine_id": machine_id,
        "items": updated_items
    }

@router.post("/machine")
async def create_checklist_item(machine_id: str, req: ChecklistCreateRequest, db: Session = Depends(get_db)):
    """새로운 체크리스트 항목을 생성합니다."""
    try:
        # 중복 체크 (같은 machine_id와 item_index가 있는지)
        existing = db.query(Checklist).filter(
            Checklist.machine_id == machine_id,
            Checklist.item_index == req.item_index
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400, 
                detail=f"Machine ID '{machine_id}'의 item_index '{req.item_index}'가 이미 존재합니다."
            )
        
        # 새 체크리스트 항목 생성
        new_item = Checklist(
            machine_id=machine_id,
            item_index=req.item_index,
            todo=req.todo,
            done=req.done,
            summary=req.summary
        )
        
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        
        return {
            "message": "체크리스트 항목이 생성되었습니다.",
            "item": new_item.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"체크리스트 생성 중 오류가 발생했습니다: {str(e)}")

@router.post("/bulk")
async def create_multiple_checklist_items(machine_id: str, items: list[ChecklistCreateRequest], db: Session = Depends(get_db)):
    """여러 체크리스트 항목을 한 번에 생성합니다."""
    try:
        created_items = []
        
        for req in items:
            # 중복 체크
            existing = db.query(Checklist).filter(
                Checklist.machine_id == machine_id,
                Checklist.item_index == req.item_index
            ).first()
            
            if not existing:  # 중복이 아닐 때만 생성
                new_item = Checklist(
                    machine_id=machine_id,
                    item_index=req.item_index,
                    todo=req.todo,
                    done=req.done,
                    summary=req.summary
                )
                db.add(new_item)
                created_items.append(new_item)
        
        db.commit()
        
        # 결과 조회
        result_items = []
        for item in created_items:
            db.refresh(item)
            result_items.append(item.to_dict())
        
        return {
            "message": f"{len(result_items)}개의 체크리스트 항목이 생성되었습니다.",
            "items": result_items
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"일괄 생성 중 오류가 발생했습니다: {str(e)}")
