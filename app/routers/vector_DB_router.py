from fastapi import APIRouter, UploadFile, File, Form, Depends
from pathlib import Path
from sqlalchemy.orm import Session
from pypdf import PdfReader
import io

from app.services.vector_db_service import SessionLocal, KnowledgeBase, save_knowledge, get_embedding


# Static 디렉토리 경로
BASE_DIR = Path(__file__).resolve().parent.parent.parent
VECDB_DIR = BASE_DIR / "app" / "static" / "vecDB"

router = APIRouter(prefix="/api/vecDB", tags=["Knowledge Base (RAG)"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 1. 전문 용어 / 통번역 데이터 등록 ---
@router.post("/term")
async def add_term(
    term: str = Form(..., description="용어 또는 원문"),
    description: str = Form(..., description="설명 또는 번역문"),
    category: str = Form("TERM", description="TERM(용어) 또는 TRANS(번역)")
):
    """
    [전문 용어/번역 등록]
    예: term="Vector DB", description="고차원 데이터를 저장하는 데이터베이스"
    """
    # 1. 벡터 생성
    vector = get_embedding(term)
    
    # 2. DB 저장
    save_knowledge(
        category=category,
        source="user_input",
        content=term,          # 검색 대상(Key)
        metadata_info=description, # 보여줄 내용(Value)
        embedding=vector
    )
    return {"message": "등록 완료", "term": term}

# --- 2. 보고서용 문서(PDF) 업로드 및 파싱 ---
@router.post("/upload-doc")
async def upload_document(file: UploadFile = File(...)):
    """
    [문서 파싱] PDF를 업로드하면 텍스트를 추출하고, 문단 단위로 쪼개서 벡터 DB에 저장합니다.
    """
    content = await file.read()
    filename = file.filename
    
    # PDF 텍스트 추출
    reader = PdfReader(io.BytesIO(content))
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"
    
    # ★ 청킹(Chunking): 긴 글을 벡터화하기 좋게 500자 단위로 자릅니다.
    chunk_size = 500
    chunks = [full_text[i:i+chunk_size] for i in range(0, len(full_text), chunk_size)]
    
    saved_count = 0
    for chunk in chunks:
        if len(chunk.strip()) < 10: continue # 너무 짧은 건 무시
        
        vector = get_embedding(chunk)
        save_knowledge(
            category="DOC",
            source=filename,
            content=chunk, # 문서 내용 조각
            metadata_info="",
            embedding=vector
        )
        saved_count += 1
        
    return {"message": f"문서 처리 완료. {saved_count}개의 조각으로 저장되었습니다."}

# --- 3. 지식 검색 (보고서 작성 도우미) ---
@router.get("/search")
def search_knowledge(query: str, db: Session = Depends(get_db)):
    """
    [검색] "벡터 DB란 뭐야?" 라고 물으면, 저장된 문서와 용어집에서 가장 유사한 내용을 찾아줍니다.
    """
    # 1. 질문을 벡터로 변환
    query_vector = get_embedding(query)
    
    # 2. 벡터 유사도 검색 (L2 Distance 또는 Cosine Distance)
    # pgvector에서는 embedding 컬럼과 비교 연산자를 사용합니다.
    # <=> : Cosine Distance (가장 많이 씀)
    results = db.query(KnowledgeBase).order_by(
        KnowledgeBase.embedding.cosine_distance(query_vector)
    ).limit(3).all()
    
    return [
        {
            "score": "High", # 실제 거리값 계산 가능
            "category": res.category,
            "source": res.source,
            "content": res.content,       # 찾은 원문
            "info": res.metadata_info     # 용어 설명이나 번역문
        }
        for res in results
    ]