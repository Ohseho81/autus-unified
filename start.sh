#!/bin/bash
# AUTUS 빠른 시작 스크립트

set -e

echo "🚀 AUTUS 서버 시작..."
echo ""

# 디렉토리 확인
if [ ! -f "backend/main.py" ]; then
    echo "❌ backend/main.py를 찾을 수 없습니다."
    echo "   autus-unified 폴더에서 실행해주세요."
    exit 1
fi

# 가상환경 확인/생성
if [ ! -d "venv" ]; then
    echo "📦 가상환경 생성 중..."
    python3 -m venv venv
fi

# 가상환경 활성화
source venv/bin/activate

# 의존성 설치
echo "📦 의존성 설치 중..."
pip install --quiet fastapi uvicorn pydantic python-dotenv python-multipart pyjwt httpx

echo ""
echo "✅ 설치 완료!"
echo ""
echo "🌐 서버 시작 중... http://localhost:8000"
echo "   API 문서: http://localhost:8000/docs"
echo "   Physics Map: frontend/physics-map-unified.html"
echo ""

# 서버 실행
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
