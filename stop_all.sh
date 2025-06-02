#!/bin/bash

echo "백엔드 서버 (Uvicorn/FastAPI) 종료 시도 중..."

# 포트 8000에서 실행 중인 프로세스 종료 (Uvicorn 기본 포트)
PIDS_PORT_8000=$(lsof -t -i:8000 -sTCP:LISTEN)
if [ -n "$PIDS_PORT_8000" ]; then
    echo "포트 8000에서 실행 중인 프로세스 발견: $PIDS_PORT_8000"
    kill -9 $PIDS_PORT_8000
    echo "포트 8000의 백엔드 서버 프로세스가 종료되었습니다."
else
    echo "포트 8000에서 실행 중인 프로세스를 찾지 못했습니다."
fi

# run_server.sh 스크립트 프로세스 종료
# 스크립트가 다른 프로세스를 실행하고 종료되는 경우, 이 방법만으로는 자식 프로세스가 종료되지 않을 수 있습니다.
PIDS_RUN_SERVER=$(pgrep -f "run_server.sh")
if [ -n "$PIDS_RUN_SERVER" ]; then
    echo "run_server.sh 프로세스 발견: $PIDS_RUN_SERVER"
    kill -9 $PIDS_RUN_SERVER
    echo "run_server.sh 프로세스가 종료되었습니다."
else
    echo "run_server.sh 프로세스를 찾지 못했습니다."
fi

# Uvicorn 관련 프로세스 직접 검색 및 종료 (app.main:app는 일반적인 실행 인자)
# 실제 실행 인자에 따라 'uvicorn app.main:app' 부분을 수정해야 할 수 있습니다.
PIDS_UVICORN=$(pgrep -f "uvicorn app.main:app")
if [ -n "$PIDS_UVICORN" ]; then
    echo "Uvicorn 프로세스 발견 (패턴: uvicorn app.main:app): $PIDS_UVICORN"
    kill -9 $PIDS_UVICORN
    echo "Uvicorn 프로세스가 종료되었습니다."
else
    echo "Uvicorn 프로세스 (패턴: uvicorn app.main:app)를 찾지 못했습니다."
fi

echo "---"
echo "프론트엔드 개발 서버 종료 시도 중..."
echo "참고: 아래는 일반적인 Node.js 기반 프론트엔드 서버를 가정합니다."
echo "만약 다른 방식으로 프론트엔드를 실행 중이거나 다른 포트를 사용한다면 이 부분을 수정해주세요."

# 프론트엔드가 실행될 수 있는 일반적인 포트 목록
FRONTEND_PORTS=(3000 8080 5173 3001) # React, Vue, Angular 등에서 자주 사용되는 포트
for PORT in "${FRONTEND_PORTS[@]}"; do
    PIDS_FRONTEND=$(lsof -t -i:$PORT -sTCP:LISTEN)
    if [ -n "$PIDS_FRONTEND" ]; then
        echo "포트 $PORT 에서 실행 중인 프론트엔드 프로세스 발견: $PIDS_FRONTEND"
        kill -9 $PIDS_FRONTEND
        echo "포트 $PORT 의 프론트엔드 서버 프로세스가 종료되었습니다."
    else
        echo "포트 $PORT 에서 실행 중인 프론트엔드 프로세스를 찾지 못했습니다."
    fi
done

# 일반적인 node 개발 서버 프로세스 이름으로도 검색 (예: npm start, yarn dev)
# pgrep의 -f 옵션은 전체 커맨드 라인에서 패턴을 찾습니다.
PIDS_NODE_DEV=$(pgrep -f "node .* (start|dev|serve|build)")
if [ -n "$PIDS_NODE_DEV" ]; then
    echo "Node.js 개발 서버 프로세스 발견: $PIDS_NODE_DEV"
    kill -9 $PIDS_NODE_DEV
    echo "Node.js 개발 서버 프로세스가 종료되었습니다."
else
    echo "일반적인 패턴의 Node.js 개발 서버 프로세스를 찾지 못했습니다."
fi

echo "---"
echo "모든 종료 시도가 완료되었습니다."
echo "프로세스가 정상적으로 종료되었는지 확인해주세요."

# 스크립트에 실행 권한 부여 (최초 생성 시)
# chmod +x stop_all.sh 
# 위 명령어는 터미널에서 직접 실행하여 권한을 부여해야 합니다. 