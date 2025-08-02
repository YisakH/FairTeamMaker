#!/bin/bash

# 기본 포트 설정
PORT=${PORT:-8000}
# 호스트 설정: 0.0.0.0은 모든 네트워크 인터페이스에서 리스닝
HOST=${HOST:-0.0.0.0}

# 필요한 패키지 확인 및 설치
if ! command -v uvicorn &> /dev/null; then
    echo "uvicorn이 설치되어 있지 않습니다. 설치 중..."
    pip install uvicorn
fi

# 데이터 디렉토리 생성
mkdir -p data

# 서버 실행
echo "서버를 $HOST:$PORT에서 실행합니다..."
uvicorn app.main:app --host $HOST --port $PORT 
