import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException

# 1. process_video_detection: 기존 파일 처리용
# 2. run_realtime_inspection: 새로운 실시간 카메라용
from app.services.detection_service import process_video_detection, run_realtime_inspection

router = APIRouter(prefix="/api/detections", tags=["Detections"])

# Static 디렉토리 경로 설정 (기존 로직 유지)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DET_DIR = BASE_DIR / "app" / "static" / "det"
DET_DIR.mkdir(parents=True, exist_ok=True)

# --- [신규 기능] 실시간 카메라 연동 API ---
@router.get("/live")
async def live_inspection():
    """
    실제 카메라(웹캠)를 켜서 핸드폰, 정수기, 텀블러를 실시간으로 점검합니다.
    """
    try:
        # 서비스의 실시간 함수 호출
        results = run_realtime_inspection(camera_index=0)
        
        return {
            "status": "success",
            "message": "실시간 점검이 완료되었습니다.",
            "data": results  # {'Cell Phone': True, 'Water Purifier': False, ...}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"실시간 탐지 실패: {str(e)}")


# --- [기존 기능] 영상 파일 업로드 처리 API ---
@router.post("/process")
async def process_detection(video_file: UploadFile = File(...)):
    """
    업로드된 영상 파일 내에서 객체를 탐지하는 기존 로직
    """
    input_name = f"input_{uuid.uuid4().hex}.mp4"
    output_name = f"result_{uuid.uuid4().hex}.mp4"
    input_path = DET_DIR / input_name
    output_path = DET_DIR / output_name
    
    # 1. 업로드된 파일 저장
    try:
        with open(input_path, "wb") as f:
            shutil.copyfileobj(video_file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 저장 실패: {str(e)}")
    
    try:
        # 2. 서비스의 파일 처리 함수 호출
        result = process_video_detection(str(input_path), str(output_path))
        
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        return {
            "message": result.get("message", "탐지 성공"),
            "video_url": f"http://localhost:8000/static/det/{output_name}",
            "stats": {
                "processed_frames": result.get("processed_frames", 0),
                "total_detections": result.get("total_detections", 0)
            }
        }
        
    except Exception as e:
        if output_path.exists(): 
            output_path.unlink()
        raise HTTPException(status_code=500, detail=f"탐지 실패: {str(e)}")
    
    finally:
        # 3. 원본 입력 파일 삭제 (정리)
        if input_path.exists():
            input_path.unlink()


# === 체크리스트 감지 상태 관리 API ===

from app.cache.services.detection_cache import detection_cache_service


@router.post("/checklist/detect")
async def process_checklist_detection(machine_id: str, item_index: int, is_detected: bool):
    """
    체크리스트 감지 결과 처리
    
    Args:
        machine_id: 기계 ID (예: "1", "2", "3")  
        item_index: 체크리스트 아이템 번호 (예: 1, 2, 3)
        is_detected: AI 감지 결과 (True/False)
        
    Returns:
        감지 처리 결과 (첫 감지/지속 감지/DB 업데이트/감지 해제)
    """
    try:
        result = detection_cache_service.process_detection(machine_id, item_index, is_detected)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"감지 처리 실패: {str(e)}")


@router.get("/checklist/status")
async def get_checklist_detection_status(machine_id: str, item_index: int):
    """
    체크리스트 감지 상태 조회
    
    Args:
        machine_id: 기계 ID
        item_index: 체크리스트 아이템 번호
        
    Returns:
        현재 감지 상태 (idle/detecting/completed)
    """
    try:
        status = detection_cache_service.get_detection_status(machine_id, item_index)
        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"상태 조회 실패: {str(e)}")


@router.delete("/checklist/clear")  
async def clear_detection_flags(machine_id: str, item_index: int):
    """
    체크리스트 감지 플래그 초기화 (관리용)
    
    Args:
        machine_id: 기계 ID
        item_index: 체크리스트 아이템 번호
        
    Returns:
        플래그 초기화 결과
    """
    try:
        result = detection_cache_service.clear_detection_flags(machine_id, item_index)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"플래그 초기화 실패: {str(e)}")


@router.get("/checklist/logs/{machine_id}")
async def get_detection_logs(machine_id: str, date: str = None):
    """
    감지 로그 조회
    
    Args:
        machine_id: 기계 ID
        date: 날짜 (YYYY-MM-DD, 선택사항)
        
    Returns:
        감지 로그 목록
    """
    try:
        logs = detection_cache_service.get_detection_logs(machine_id, date)
        return {
            "success": True,
            "data": {
                "machine_id": machine_id,
                "date": date,
                "logs": logs,
                "total": len(logs)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 조회 실패: {str(e)}")