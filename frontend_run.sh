#!/bin/bash

# 로컬 IP 주소 가져오기 (macOS/Linux에서 동작)
LOCAL_IP=$(ifconfig | grep -E "inet ([0-9]{1,3}\.){3}[0-9]{1,3}" | grep -v 127.0.0.1 | awk '{print $2}' | head -n 1)

# 기본 포트 설정
PORT=${PORT:-3000}
# API URL 설정 - 로컬 IP 사용
API_URL=${API_URL:-http://$LOCAL_IP:8000}
# 호스트 설정 (0.0.0.0은 모든 네트워크 인터페이스에서 접속 가능)
HOST=${HOST:-0.0.0.0}

# 데이터 디렉토리 생성
mkdir -p data

# 현재 디렉토리 확인
if [ ! -d "frontend" ]; then
    echo "frontend 디렉토리가 없습니다!"
    exit 1
fi

cd frontend

# 필요한 패키지 설치
if [ ! -d "node_modules" ]; then
    echo "node_modules가 없습니다. npm install을 실행합니다..."
    npm install
fi

# 환경 변수 설정 및 프론트엔드 실행
echo "프론트엔드를 $HOST:$PORT에서 실행합니다..."
echo "API 서버 URL: $API_URL"
echo "모바일에서 접속하려면: http://$LOCAL_IP:$PORT"

# React 앱을 모든 인터페이스에서 접속 가능하게 실행
HOST=$HOST REACT_APP_API_URL=$API_URL npm start -- --host $HOST --port $PORT 