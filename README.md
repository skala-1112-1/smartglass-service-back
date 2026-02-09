# Factory Inspection API

공장 설비 점검을 위한 백엔드 API 서버

## 기능

1. **체크리스트 조회** - 기계별 점검 항목 제공
2. **TTS 음성 생성** - 점검 항목을 음성으로 변환 (캐시 지원)
3. **STT 음성 인식** - 점검 내용 음성 녹음 및 텍스트 변환
4. **리포트 생성** - GPT 기반 점검 리포트 자동 생성
5. **객체 탐지** - 비디오 분석 및 객체 탐지 (데모 모드)

## 설치 방법

### 1. 사전 요구사항

- Python 3.9 이상
- ffmpeg (음성 처리용)

#### macOS
```bash
brew install ffmpeg
```

#### Ubuntu
```bash
sudo apt update
sudo apt install -y ffmpeg
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

### 4. 환경 변수 설정

`.env` 파일에 OpenAI API 키를 설정하세요:

```
OPENAI_API_KEY=your_actual_api_key_here
```

## 실행 방법

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

또는

```bash
python -m app.main
```

서버가 실행되면 http://localhost:8000 에서 접근 가능합니다.

API 문서: http://localhost:8000/docs

## API 명세

### 1. POST /api/checklists/machine
체크리스트 조회

**Request:**
```json
{
  "machine_id": "1"
}
```

**Response:**
```json
{
  "machine_id": "1",
  "items": [
    {"index": 1, "todo": "전원 공급 상태 확인"},
    {"index": 2, "todo": "유압 시스템 점검"},
    {"index": 3, "todo": "안전 장치 작동 확인"},
    {"index": 4, "todo": "냉각수 레벨 확인"},
    {"index": 5, "todo": "벨트 장력 점검"}
  ]
}
```

---

### 2. GET /api/tts/machine?machine_id=1
TTS 음성 파일 생성 및 조회 (캐시 지원)

**Query Parameters:**
- `machine_id`: 기계 ID (예: "1", "M-001")

**Response:**
```json
{
  "machine_id": "1",
  "voices": [
    {"index": 1, "voice_url": "http://localhost:8000/static/tts/1/1.mp3"},
    {"index": 2, "voice_url": "http://localhost:8000/static/tts/1/2.mp3"},
    {"index": 3, "voice_url": "http://localhost:8000/static/tts/1/3.mp3"},
    {"index": 4, "voice_url": "http://localhost:8000/static/tts/1/4.mp3"},
    {"index": 5, "voice_url": "http://localhost:8000/static/tts/1/5.mp3"}
  ]
}
```

**특징:**
- 이미 생성된 음성 파일은 재생성하지 않고 캐시된 파일 반환
- OpenAI TTS API 사용

---

### 3. POST /api/stt
음성 파일 업로드 및 STT 변환

**Request:** (multipart/form-data)
- `machine_id`: 기계 ID (예: "1")
- `index`: 체크리스트 항목 번호 (예: 1)
- `audio_file`: 음성 파일 (wav, webm, mp3 등)

**Response:**
```json
{
  "machine_id": "1",
  "index": 1,
  "transcript": "전원 공급 상태 정상입니다",
  "audio_url": "http://localhost:8000/static/stt/1_1_abc123.wav",
  "created_at": "2025-01-30T12:34:56Z"
}
```

**특징:**
- Whisper 모델 사용 (CPU/GPU 자동 선택)
- 업로드된 음성 파일은 `static/stt/`에 저장
- transcript는 메모리에 저장되어 리포트 생성에 사용

---

### 4. POST /api/reports/generate
점검 리포트 생성

**Request:**
```json
{
  "machine_id": "1"
}
```

**Response:**
```json
{
  "inspection_id": "INSP-A3F2",
  "report_md": "## 기계 1 점검 리포트\n\n### ✅ 점검 완료 항목\n1. 전원 공급 상태 확인: 전원 공급 상태 정상입니다\n\n### ⚠️ 점검 미완료 항목\n2. 유압 시스템 점검\n3. 안전 장치 작동 확인\n4. 냉각수 레벨 확인\n5. 벨트 장력 점검\n\n### 종합 의견\n총 5개 항목 중 1개 완료, 4개 미완료. 전원 공급 상태는 정상으로 확인되었으나, 미완료 항목에 대한 점검이 완료되어야 종합적인 안전 상태를 평가할 수 있습니다."
}
```

**특징:**
- GPT-3.5-turbo 사용하여 리포트 자동 생성
- 점검 완료/미완료 항목 구분
- 안전 상태 평가 포함
- Markdown 형식으로 반환

---

### 5. POST /api/detections/process
비디오 객체 탐지 (AI 기반)

**Request:** (multipart/form-data)
- `video_file`: 비디오 파일 (mp4, avi 등)

**Response:**
```
"http://localhost:8000/static/det/result_abc123.mp4"
```

**특징:**
- Zero-shot 객체 탐지 (OWL-ViT 모델)
- 공장 기계 자동 탐지 및 박스 표시
- 진한 파란색 박스로 시각화
- 화면 전체 탐지 방지 (특정 기계만 탐지)
- 처리된 비디오 URL을 문자열로 반환

## 배포

### zip 파일로 배포

```bash
# 가상환경 비활성화
deactivate

# 프로젝트 압축
cd ..
zip -r Factory.zip Factory -x "Factory/venv/*" "Factory/__pycache__/*" "Factory/.git/*"
```

### 배포된 환경에서 실행

```bash
unzip Factory.zip
cd Factory
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
# .env 파일 수정 (API 키 입력)
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 디렉토리 구조

```
Factory/
├── app/
│   ├── main.py              # FastAPI 메인 애플리케이션
│   ├── services/
│   │   ├── stt_service.py   # STT (Whisper)
│   │   ├── tts_service.py   # TTS (OpenAI)
│   │   ├── checklist_service.py  # 체크리스트 & 리포트
│   │   └── detection_service.py  # 객체 탐지 (데모)
│   └── static/
│       ├── tts/             # TTS 음성 파일 캐시
│       ├── stt/             # STT 업로드 파일
│       └── det/             # 객체 탐지 결과 비디오
├── requirements.txt
├── .env
└── README.md
```

## 주의사항

- OpenAI API 키가 필요합니다 (.env 파일에 설정)
- ffmpeg가 시스템에 설치되어 있어야 합니다
- STT 처리는 CPU/GPU 모드로 동작하며, 첫 실행 시 Whisper 모델을 다운로드합니다
- 객체 탐지는 OWL-ViT 모델을 사용하며, 첫 실행 시 모델을 다운로드합니다 (약 1~2분 소요)
