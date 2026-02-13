from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from app.routers import checklist_router, tts_router, stt_router, report_router, detection_router, vector_DB_router

app = FastAPI(title="Factory Inspection API")

# 경로 설정
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "app" / "static"
TTS_DIR = STATIC_DIR / "tts"
STT_DIR = STATIC_DIR / "stt"
DET_DIR = STATIC_DIR / "det"
VECDB_DIR = STATIC_DIR / "vecDB"

for d in [TTS_DIR, STT_DIR, DET_DIR, VECDB_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Static 파일 마운트
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(checklist_router.router)
app.include_router(tts_router.router)
app.include_router(stt_router.router)
app.include_router(report_router.router)
app.include_router(detection_router.router)
app.include_router(vector_DB_router.router)

@app.get("/")
async def root():
    return {"message": "Factory Inspection API", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
