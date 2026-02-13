# SmartGlass Factory Inspection API

스마트글래스 기반 공장 설비 점검을 위한 백엔드 API 서버

## 주요 기능

1. **체크리스트 관리** - PostgreSQL 기반 기계별 점검 항목 관리
2. **TTS 음성 생성** - OpenAI TTS로 점검 항목 음성 변환
3. **STT 음성 인식** - Whisper 모델 기반 음성 텍스트 변환
4. **리포트 생성** - GPT 기반 점검 리포트 자동 생성
5. **AI 객체 탐지** - 실시간 카메라 영상 분석 및 자동 점검
6. **Redis 캐싱** - 실시간 감지 상태 및 체크리스트 캐싱
7. **벡터 DB** - pgvector 기반 지식베이스 검색

## 설치 방법

### 1. 사전 요구사항

- Python 3.9 이상
- Docker & Docker Compose
- ffmpeg (음성 처리용)

#### macOS
```bash
brew install ffmpeg
```

#### Ubuntu
```bash
sudo apt update
```

### 2. 가상환경 생성 및 활성화

```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
```

### 3. 패키지 설치

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. 데이터베이스 & Redis 실행

```bash
# Docker Compose로 PostgreSQL, Redis, pgAdmin 실행
docker-compose up -d

# pgvector 확장 활성화
docker exec -it smartglass-postgres psql -U postgres -d postgres -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 5. 데이터베이스 초기화

```bash
# 체크리스트 데이터 초기화
PYTHONPATH=. python app/init_db.py
```

### 6. 환경 변수 설정

`.env.example` 을 복사하여 활용하세요.
OPENAI_API_KEY에는 보유한 api key를 넣어야 합니다.

```
OPENAI_API_KEY=your_actual_api_key_here
```

## 실행 방법

```bash
# 가상환경 활성화
source venv/bin/activate

# FastAPI 서버 실행
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

서버가 실행되면:
- **API 서버**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs  
- **pgAdmin**: http://localhost:5050 (admin@smartglass.com / admin123)
- **Redis**: localhost:6379
- **PostgreSQL**: localhost:5433

## 핵심 API 엔드포인트

### 🔍 실시간 AI 탐지
```bash
# Monitor ON 감지시 체크리스트 자동 업데이트 (Camera → AI → Redis → DB)
GET /api/detections/live
```

### 📋 체크리스트 관리
```bash
# 기계별 체크리스트 조회
GET /api/checklist/{machine_id}

# 체크리스트 항목 업데이트  
PUT /api/checklist/{machine_id}/{item_index}
```

### 🎤 음성 처리
```bash
# TTS: 체크리스트를 음성으로 변환
GET /api/tts/machine?machine_id=1

# STT: 음성을 텍스트로 변환
POST /api/stt
```

### 📊 리포트 생성
```bash
# GPT 기반 점검 리포트 자동 생성
POST /api/reports/generate
```

### 🗂️ 벡터 DB
```bash
# PDF 업로드 및 벡터화
POST /api/vecdb/upload

# 유사도 검색
POST /api/vecdb/search
```

**전체 API 문서**: http://localhost:8000/docs

## 프로젝트 구조

```
smartglass-service-back/
├── app/
│   ├── main.py              # FastAPI 애플리케이션
│   ├── database.py          # PostgreSQL 연결
│   ├── models.py            # SQLAlchemy 모델
│   ├── init_db.py           # DB 초기화
│   ├── cache/               # Redis 캐시 시스템
│   │   ├── client.py        # Redis 클라이언트
│   │   ├── keys.py          # 캐시 키 관리
│   │   └── services/        # 캐시 서비스
│   ├── routers/             # API 라우터
│   │   ├── checklist_router.py
│   │   ├── detection_router.py
│   │   ├── stt_router.py
│   │   ├── tts_router.py
│   │   ├── report_router.py
│   │   └── vector_DB_router.py
│   ├── services/            # 비즈니스 로직
│   │   ├── checklist_service.py
│   │   ├── detection_service.py  # AI 객체 탐지
│   │   ├── stt_service.py        # Whisper STT
│   │   └── tts_service.py        # OpenAI TTS
│   └── static/              # 정적 파일
│       ├── tts/             # TTS 음성 캐시
│       ├── stt/             # STT 업로드
│       ├── det/             # 탐지 결과
│       └── vecdb/           # 벡터 DB 파일
├── docker-compose.yml       # PostgreSQL, Redis, pgAdmin
├── requirements.txt
├── .env
└── README.md
```

## 시스템 특징

### 🤖 AI 통합 시스템
- **실시간 모니터 감지**: OwlViT + CLIP 모델로 Monitor ON/OFF 자동 탐지
- **자동 체크리스트 업데이트**: Monitor ON 5초 지속시 Redis → PostgreSQL 자동 업데이트
- **음성 인터페이스**: OpenAI TTS + Whisper STT로 핸즈프리 작업 지원

### 🚀 성능 최적화
- **Redis 캐싱**: 실시간 감지 상태 및 체크리스트 고속 캐싱
- **파일 캐싱**: TTS 음성 파일 중복 생성 방지
- **벡터 검색**: pgvector 기반 고속 유사도 검색

### 🔧 개발/배포
- **Docker 기반**: PostgreSQL, Redis, pgAdmin 컨테이너화
- **핫 리로드**: uvicorn --reload로 개발 생산성 향상
- **모듈화 설계**: 라우터/서비스/캐시 계층 분리

## 주요 의존성

- **AI**: transformers (OwlViT, CLIP), torch, openai-whisper
- **DB**: PostgreSQL, pgvector, Redis, SQLAlchemy
- **API**: FastAPI, uvicorn
- **미디어**: opencv-python, ffmpeg, pydub
