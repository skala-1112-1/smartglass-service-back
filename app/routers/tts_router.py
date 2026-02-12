from fastapi import APIRouter, HTTPException
from pathlib import Path
from app.services.checklist_service import get_checklist
from app.services.tts_service import text_to_speech

router = APIRouter(prefix="/api/tts", tags=["TTS"])

# Static 디렉토리 경로
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TTS_DIR = BASE_DIR / "app" / "static" / "tts"

@router.get("/machine")
async def get_tts_voices(machine_id: str):
    items = get_checklist(machine_id)
    print(items)
    if not items:
        raise HTTPException(status_code=404, detail="체크리스트를 찾을 수 없습니다")
    
    voices = []
    machine_tts_dir = TTS_DIR / machine_id
    machine_tts_dir.mkdir(parents=True, exist_ok=True)
    
    for item in items:
        idx = item["index"]
        mp3_path = machine_tts_dir / f"{idx}.mp3"
        
        # 캐시 확인
        if not mp3_path.exists():
            text_to_speech(item["todo"], str(mp3_path))
        
        voice_url = f"http://localhost:8000/static/tts/{machine_id}/{idx}.mp3"
        voices.append({"index": idx, "voice_url": voice_url})
    
    return {"machine_id": machine_id, "voices": voices}
