#!/bin/bash

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}  FairTeamMaker 통합 서버 종료${NC}"
echo -e "${BLUE}=====================================${NC}"

# 강제 종료 옵션 확인
FORCE_KILL=false
if [ "$1" = "--force" ] || [ "$1" = "-f" ]; then
    FORCE_KILL=true
    echo -e "${YELLOW}[INFO]${NC} 강제 종료 모드가 활성화되었습니다."
fi

# PID 파일에서 프로세스 종료
stop_from_pid_file() {
    local pid_file=$1
    local service_name=$2
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if [ ! -z "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            echo -e "${YELLOW}[INFO]${NC} $service_name 서버 종료 중... (PID: $pid)"
            
            if [ "$FORCE_KILL" = true ]; then
                kill -9 "$pid" 2>/dev/null || true
            else
                kill "$pid" 2>/dev/null || true
                
                # 정상 종료 대기 (최대 10초)
                local count=0
                while kill -0 "$pid" 2>/dev/null && [ $count -lt 10 ]; do
                    sleep 1
                    count=$((count + 1))
                done
                
                # 여전히 실행 중이면 강제 종료
                if kill -0 "$pid" 2>/dev/null; then
                    echo -e "${YELLOW}[WARN]${NC} $service_name 서버가 정상 종료되지 않아 강제 종료합니다."
                    kill -9 "$pid" 2>/dev/null || true
                fi
            fi
            
            echo -e "${GREEN}[SUCCESS]${NC} $service_name 서버가 종료되었습니다."
        else
            echo -e "${YELLOW}[INFO]${NC} $service_name 서버가 이미 종료되었거나 PID가 유효하지 않습니다."
        fi
        rm -f "$pid_file"
    else
        echo -e "${YELLOW}[INFO]${NC} $service_name PID 파일을 찾을 수 없습니다."
    fi
}

# PID 파일을 통한 종료 시도
stop_from_pid_file ".backend.pid" "백엔드"
stop_from_pid_file ".frontend.pid" "프론트엔드"

# 패턴으로 남은 프로세스 찾아서 종료
stop_by_pattern() {
    local pattern=$1
    local service_name=$2
    
    local pids=$(pgrep -f "$pattern" 2>/dev/null || echo "")
    if [ ! -z "$pids" ]; then
        echo -e "${YELLOW}[INFO]${NC} 패턴으로 찾은 $service_name 프로세스들을 종료합니다: $pids"
        
        if [ "$FORCE_KILL" = true ]; then
            echo "$pids" | xargs kill -9 2>/dev/null || true
        else
            echo "$pids" | xargs kill 2>/dev/null || true
            sleep 2
            
            # 여전히 실행 중인 프로세스가 있으면 강제 종료
            local remaining_pids=$(pgrep -f "$pattern" 2>/dev/null || echo "")
            if [ ! -z "$remaining_pids" ]; then
                echo -e "${YELLOW}[WARN]${NC} 일부 $service_name 프로세스를 강제 종료합니다: $remaining_pids"
                echo "$remaining_pids" | xargs kill -9 2>/dev/null || true
            fi
        fi
        
        echo -e "${GREEN}[SUCCESS]${NC} 패턴으로 찾은 $service_name 프로세스들이 종료되었습니다."
    fi
}

# 패턴으로 남은 프로세스들 종료
echo -e "${YELLOW}[INFO]${NC} 남은 프로세스들을 패턴으로 검색하여 종료합니다..."

stop_by_pattern "uvicorn.*app.main:app" "백엔드"
stop_by_pattern "npm.*start" "프론트엔드"
stop_by_pattern "node.*react-scripts.*start" "React 개발서버"

# 포트 점유 프로세스 확인 및 종료 (선택사항)
cleanup_port() {
    local port=$1
    local service_name=$2
    
    local pid=$(lsof -ti :$port 2>/dev/null || echo "")
    if [ ! -z "$pid" ]; then
        echo -e "${YELLOW}[INFO]${NC} 포트 $port를 사용하는 $service_name 프로세스를 종료합니다 (PID: $pid)"
        
        if [ "$FORCE_KILL" = true ]; then
            kill -9 $pid 2>/dev/null || true
        else
            kill $pid 2>/dev/null || true
            sleep 1
            
            # 여전히 실행 중이면 강제 종료
            if kill -0 $pid 2>/dev/null; then
                kill -9 $pid 2>/dev/null || true
            fi
        fi
        
        echo -e "${GREEN}[SUCCESS]${NC} 포트 $port의 $service_name 프로세스가 종료되었습니다."
    fi
}

# 기본 포트들 정리 (필요시)
if [ "$FORCE_KILL" = true ]; then
    echo -e "${YELLOW}[INFO]${NC} 기본 포트들의 프로세스를 정리합니다..."
    cleanup_port 8000 "백엔드"
    cleanup_port 3000 "프론트엔드"
fi

# 로그 파일 정리 여부 묻기
if [ "$FORCE_KILL" != true ]; then
    echo
    echo -e "${YELLOW}로그 파일을 삭제하시겠습니까? (y/N):${NC}"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        rm -f backend.log frontend.log nohup.out front.log
        echo -e "${GREEN}[SUCCESS]${NC} 로그 파일들이 삭제되었습니다."
    fi
fi

# 최종 상태 확인
echo
echo -e "${BLUE}=====================================${NC}"
echo -e "${GREEN}  모든 서버가 종료되었습니다!${NC}"
echo -e "${BLUE}=====================================${NC}"

# 남은 프로세스가 있는지 확인
remaining_backend=$(pgrep -f "uvicorn.*app.main:app" 2>/dev/null || echo "")
remaining_frontend=$(pgrep -f "npm.*start" 2>/dev/null || echo "")

if [ ! -z "$remaining_backend" ] || [ ! -z "$remaining_frontend" ]; then
    echo -e "${YELLOW}[WARN]${NC} 일부 프로세스가 여전히 실행 중일 수 있습니다."
    echo -e "강제 종료를 원하시면: ${BLUE}./stop_all.sh --force${NC}"
else
    echo -e "${GREEN}✨ 모든 프로세스가 정상적으로 종료되었습니다!${NC}"
fi

echo
echo -e "${YELLOW}📋 유용한 명령어:${NC}"
echo -e "  - 서버 재시작: ${BLUE}./start_all.sh${NC}"
echo -e "  - 상태 확인: ${BLUE}./status.sh${NC}"