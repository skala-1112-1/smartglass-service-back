from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import os



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


# 1. DB 연결 설정
# 포맷: postgresql://아이디:비번@주소:포트/DB이름
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/vector_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# 2. 모델 정의 (테이블과 매핑)
class DetectionLog(Base):
    __tablename__ = "detection_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    object_name = Column(String)
    status = Column(String)
    confidence = Column(Float)
    # CLIP-ViT-Base-32는 512차원입니다.
    embedding = Column(Vector(512)) 

# 테이블 자동 생성 (이미 DBeaver로 만들었으면 생략 가능하지만 안전을 위해 둠)
Base.metadata.create_all(bind=engine)

# 3. 데이터 저장 함수
def save_detection_log(object_name, status, confidence, embedding_list):
    """
    탐지 결과를 DB에 저장합니다.
    embedding_list: List[float]
    """
    session = SessionLocal()
    try:
        log = DetectionLog(
            object_name=object_name,
            status=status,
            confidence=confidence,
            embedding=embedding_list
        )
        session.add(log)
        session.commit()
        # print(f"[DB] Saved: {object_name} ({status})")
    except Exception as e:
        print(f"[DB Error] {e}")
        session.rollback()
    finally:
        session.close()