#!/bin/bash

echo "=== Factory Inspection API 서버 시작 ==="
echo ""

# 가상환경 확인
if [ ! -d "factoryVenv" ]; then
    echo "가상환경이 없습니다. 먼저 다음 명령어를 실행하세요:"
    echo "  python3 -m venv factoryVenv"
    echo "  source factoryVenv/bin/activate"
    echo "  python -m pip install --upgrade pip"
    echo "  python -m pip install -r requirements.txt"
    exit 1
fi

# 가상환경 활성화
source factoryVenv/bin/activate

# 가상환경 활성화 확인
echo "가상환경 활성화 확인: $(which python)"
echo "*터미널에 표시가 안되어도 위에 위치가 가상환경이면 정상 실행"
echo ""

# .env 파일 확인
if [ ! -f ".env" ]; then
    echo "경고: .env 파일이 없습니다. OpenAI API 키를 설정하세요."
fi

# 서버 실행
echo "서버를 시작합니다..."
echo "API 문서: http://localhost:8000/docs"
echo ""
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
