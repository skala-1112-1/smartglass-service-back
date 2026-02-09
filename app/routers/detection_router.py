import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.detection_service import process_video_detection

router = APIRouter(prefix="/api/detections", tags=["Detections"])

# Static 디렉토리 경로 설정
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DET_DIR = BASE_DIR / "app" / "static" / "det"
DET_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/process")
async def process_detection(video_file: UploadFile = File(...)):
    """
    영상에서 가장자리 백색 기계를 탐지하는 API
    """
    input_name = f"input_{uuid.uuid4().hex}.mp4"
    output_name = f"result_{uuid.uuid4().hex}.mp4"
    input_path = DET_DIR / input_name
    output_path = DET_DIR / output_name
    
    # 업로드된 파일 저장
    with open(input_path, "wb") as f:
        shutil.copyfileobj(video_file.file, f)
    
    try:
        # detection_service의 탐지 함수 호출
        result = process_video_detection(str(input_path), str(output_path))
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        return {
            "message": result["message"],
            "video_url": f"http://localhost:8000/static/det/{output_name}",
            "stats": {
                "processed_frames": result["processed_frames"],
                "total_detections": result["total_detections"]
            }
        }
        
    except Exception as e:
        if output_path.exists(): 
            output_path.unlink()
        raise HTTPException(status_code=500, detail=f"탐지 실패: {str(e)}")
    
    finally:
        # 입력 파일 정리
        if input_path.exists():
            input_path.unlink()