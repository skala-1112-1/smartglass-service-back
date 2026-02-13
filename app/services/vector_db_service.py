from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, func
from sqlalchemy.orm import sessionmaker, declarative_base
from pgvector.sqlalchemy import Vector
from sentence_transformers import SentenceTransformer


# ====================================================================
# [Vector DB (pgVector) 향후 활용 계획 및 구현 예정 기능]
#
# 1. 이미지 유사도 검색 (Similarity Search)
#    - "이 화면과 비슷한 과거 화면을 찾아줘"
#    - 원리: 현재 캡처된 모니터의 벡터값과 DB에 저장된 벡터값들의 코사인 거리(Cosine Distance)를 비교하여 가장 가까운 N개 추출.
#
# 2. 이상 징후 탐지 (Anomaly Detection)
#    - "모니터가 켜져 있긴 한데, 평소(바탕화면)와 많이 달라!" (예: 블루스크린, 에러 창, 경고 화면)
#    - 원리: 정상 상태일 때의 '평균 벡터값'을 구해두고, 새로 들어온 벡터값이 평균에서 너무 멀리 떨어져 있으면(Outlier) 관리자에게 알림.
#
# 3. 동일 객체 재식별 (Re-identification)
#    - "지금 화면에 잡힌 저 텀블러, 어제 잡혔던 그 텀블러랑 같은 걸까?"
#    - 원리: 텀블러의 특징(색상, 형태)이 벡터로 압축되어 있으므로, 벡터 거리가 매우 가깝다면 동일한 물건으로 간주.
#
# 4. 시계열 상태 군집화 (Time-series Clustering)
#    - "사용자가 주로 어떤 화면(어두운 화면/밝은 화면/특정 프로그램)을 띄워놓고 작업할까?"
#    - 원리: 저장된 벡터들을 K-Means 등으로 군집화(Clustering)하여 패턴 분석.
# ====================================================================


# DB 연결 (포트 5433 유지)
DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/postgres"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class KnowledgeBase(Base):
    """
    전문 용어, 통번역 데이터, 보고서용 문서 조각을 저장하는 테이블
    """
    __tablename__ = "knowledge_base"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # category: 'TERM'(용어), 'TRANS'(번역), 'DOC'(보고서 문서)
    category = Column(String(50)) 
    
    # source: 파일명이나 출처 (예: '2024_manual.pdf', 'user_input')
    source = Column(String(255))
    
    # content: 실제 텍스트 내용 (질문이나 문서의 본문)
    content = Column(Text)
    
    # answer: (선택) 통번역이나 용어집일 경우 짝이 되는 정답/번역문
    metadata_info = Column(Text, nullable=True) 

    # ★ 중요: 한국어 텍스트 임베딩 모델(MiniLM)은 384차원입니다.
    embedding = Column(Vector(384))

# 테이블 생성
Base.metadata.create_all(bind=engine)

def save_knowledge(category, source, content, embedding, metadata_info=None):
    session = SessionLocal()
    try:
        doc = KnowledgeBase(
            category=category,
            source=source,
            content=content,
            metadata_info=metadata_info,
            embedding=embedding
        )
        session.add(doc)
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


## 텍스트 임베딩


# 전역 변수로 모델 로드 (최초 1회만)
_text_model = None

def get_text_model():
    global _text_model
    if _text_model is None:
        print("[MODEL] 텍스트 임베딩 모델 로딩 중... (multilingual-MiniLM-L12-v2)")
        # 한국어와 영어를 동시에 잘하는 가볍고 빠른 모델입니다.
        _text_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    return _text_model

def get_embedding(text: str):
    """
    문자열을 입력받아 384차원의 실수 리스트(Vector)로 변환
    """
    model = get_text_model()
    # numpy array -> list 변환
    vector = model.encode(text).tolist()
    return vector


## 업로드 및 API 검색