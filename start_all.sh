#!/bin/bash

set -e  # Exit immediately if a command exits with a non-zero status

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}  FairTeamMaker 통합 서버 시작${NC}"
echo -e "${BLUE}=====================================${NC}"

# 환경 변수 설정
BACKEND_HOST=${BACKEND_HOST:-0.0.0.0}
BACKEND_PORT=${BACKEND_PORT:-8000}
FRONTEND_HOST=${FRONTEND_HOST:-0.0.0.0}
FRONTEND_PORT=${FRONTEND_PORT:-3000}

# 로그 파일 설정
BACKEND_LOG="backend.log"
FRONTEND_LOG="frontend.log"

# 데이터 디렉토리 생성
mkdir -p data

echo -e "${YELLOW}[INFO]${NC} 설정 정보:"
echo -e "  - 백엔드: $BACKEND_HOST:$BACKEND_PORT"
echo -e "  - 프론트엔드: $FRONTEND_HOST:$FRONTEND_PORT"
echo -e "  - 백엔드 로그: $BACKEND_LOG"
echo -e "  - 프론트엔드 로그: $FRONTEND_LOG"
echo

# 기존 프로세스 확인 및 종료
echo -e "${YELLOW}[INFO]${NC} 기존 프로세스 확인 중..."

# 백엔드 프로세스 종료
BACKEND_PID=$(pgrep -f "uvicorn.*app.main:app" || echo "")
if [ ! -z "$BACKEND_PID" ]; then
    echo -e "${YELLOW}[INFO]${NC} 기존 백엔드 프로세스 종료 중... (PID: $BACKEND_PID)"
    kill $BACKEND_PID || echo -e "${RED}[WARN]${NC} 백엔드 프로세스 종료 실패"
    sleep 2
fi

# 프론트엔드 프로세스 종료
FRONTEND_PID=$(pgrep -f "npm.*start" || echo "")
if [ ! -z "$FRONTEND_PID" ]; then
    echo -e "${YELLOW}[INFO]${NC} 기존 프론트엔드 프로세스 종료 중... (PID: $FRONTEND_PID)"
    kill $FRONTEND_PID || echo -e "${RED}[WARN]${NC} 프론트엔드 프로세스 종료 실패"
    sleep 2
fi

# 포트 확인
check_port() {
    local port=$1
    local service=$2
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${RED}[ERROR]${NC} 포트 $port가 이미 사용 중입니다 ($service). 다른 포트를 사용하거나 프로세스를 종료하세요."
        exit 1
    fi
}

check_port $BACKEND_PORT "백엔드"
check_port $FRONTEND_PORT "프론트엔드"

# 1. 백엔드 서버 시작
echo -e "${GREEN}[1/2]${NC} 백엔드 서버 시작 중..."

# uvicorn 설치 확인
if ! command -v uvicorn &> /dev/null; then
    echo -e "${YELLOW}[INFO]${NC} uvicorn이 설치되어 있지 않습니다. 설치 중..."
    pip install uvicorn
fi

# 백엔드 서버 백그라운드 실행
nohup uvicorn app.main:app --host $BACKEND_HOST --port $BACKEND_PORT > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

echo -e "${GREEN}[SUCCESS]${NC} 백엔드 서버 시작됨 (PID: $BACKEND_PID)"
sleep 3

# 백엔드 서버 상태 확인
if kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${GREEN}[INFO]${NC} 백엔드 서버가 정상적으로 실행 중입니다."
else
    echo -e "${RED}[ERROR]${NC} 백엔드 서버 시작에 실패했습니다. 로그를 확인하세요: $BACKEND_LOG"
    exit 1
fi

# 2. 프론트엔드 서버 시작
echo -e "${GREEN}[2/2]${NC} 프론트엔드 서버 시작 중..."

# 프론트엔드 디렉토리 확인
if [ ! -d "frontend" ]; then
    echo -e "${RED}[ERROR]${NC} frontend 디렉토리를 찾을 수 없습니다."
    exit 1
fi

cd frontend

# Node.js와 npm 확인
if ! command -v node &> /dev/null; then
    echo -e "${RED}[ERROR]${NC} Node.js가 설치되어 있지 않습니다."
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo -e "${RED}[ERROR]${NC} npm이 설치되어 있지 않습니다."
    exit 1
fi

# 의존성 설치
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}[INFO]${NC} node_modules를 찾을 수 없습니다. npm install 실행 중..."
    npm install
fi

# 프론트엔드 서버 백그라운드 실행
nohup env HOST=$FRONTEND_HOST PORT=$FRONTEND_PORT DANGEROUSLY_DISABLE_HOST_CHECK=true npm start > "../$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!

cd ..

echo -e "${GREEN}[SUCCESS]${NC} 프론트엔드 서버 시작됨 (PID: $FRONTEND_PID)"
sleep 5

# 프론트엔드 서버 상태 확인
if kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${GREEN}[INFO]${NC} 프론트엔드 서버가 정상적으로 실행 중입니다."
else
    echo -e "${RED}[ERROR]${NC} 프론트엔드 서버 시작에 실패했습니다. 로그를 확인하세요: $FRONTEND_LOG"
    exit 1
fi

# PID 저장
echo $BACKEND_PID > .backend.pid
echo $FRONTEND_PID > .frontend.pid

echo
echo -e "${BLUE}=====================================${NC}"
echo -e "${GREEN}  모든 서버가 성공적으로 시작되었습니다!${NC}"
echo -e "${BLUE}=====================================${NC}"
echo -e "${GREEN}🚀 백엔드:${NC} http://$BACKEND_HOST:$BACKEND_PORT"
echo -e "${GREEN}🌐 프론트엔드:${NC} http://$FRONTEND_HOST:$FRONTEND_PORT"
echo
echo -e "${YELLOW}📋 관리 명령어:${NC}"
echo -e "  - 서버 종료: ${BLUE}./stop_all.sh${NC}"
echo -e "  - 로그 확인: ${BLUE}tail -f $BACKEND_LOG${NC} 또는 ${BLUE}tail -f $FRONTEND_LOG${NC}"
echo -e "  - 상태 확인: ${BLUE}./status.sh${NC}"
echo
echo -e "${GREEN}✨ 모든 서비스가 준비되었습니다!${NC}"
