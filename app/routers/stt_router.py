from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pathlib import Path
from datetime import datetime
import shutil
import uuid
from app.services.stt_service import transcribe_audio_file

router = APIRouter(prefix="/api/stt", tags=["STT"])

# Static 디렉토리 경로
BASE_DIR = Path(__file__).resolve().parent.parent.parent
STT_DIR = BASE_DIR / "app" / "static" / "stt"

# 메모리 저장소 (main.py에서 공유)
transcripts_store = {}

@router.post("")
async def upload_stt(
    machine_id: str = Form(...),
    index: int = Form(...),
    audio_file: UploadFile = File(...)
):
    # 파일 저장
    file_ext = Path(audio_file.filename).suffix or ".wav"
    unique_name = f"{machine_id}_{index}_{uuid.uuid4().hex}{file_ext}"
    audio_path = STT_DIR / unique_name
    
    with open(audio_path, "wb") as f:
        shutil.copyfileobj(audio_file.file, f)
    
    # STT 처리
    try:
        transcript = transcribe_audio_file(str(audio_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT 처리 실패: {str(e)}")
    
    # 메모리에 저장
    key = f"{machine_id}_{index}"
    transcripts_store[key] = transcript
    
    audio_url = f"http://localhost:8000/static/stt/{unique_name}"
    created_at = datetime.utcnow().isoformat() + "Z"
    
    return {
        "machine_id": machine_id,
        "index": index,
        "transcript": transcript,
        "audio_url": audio_url,
        "created_at": created_at
    }
