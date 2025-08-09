#!/bin/bash

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}  FairTeamMaker 서버 상태 확인${NC}"
echo -e "${BLUE}=====================================${NC}"

# 서비스 상태 확인 함수
check_service_status() {
    local service_name=$1
    local pattern=$2
    local port=$3
    local pid_file=$4
    
    echo -e "${YELLOW}📍 $service_name 상태:${NC}"
    
    # PID 파일에서 프로세스 확인
    local pid_from_file=""
    if [ -f "$pid_file" ]; then
        pid_from_file=$(cat "$pid_file" 2>/dev/null)
    fi
    
    # 패턴으로 프로세스 검색
    local pids=$(pgrep -f "$pattern" 2>/dev/null || echo "")
    
    # 포트 사용 확인
    local port_pid=""
    if command -v lsof >/dev/null 2>&1; then
        port_pid=$(lsof -ti :$port 2>/dev/null || echo "")
    fi
    
    # 상태 분석
    if [ ! -z "$pids" ]; then
        echo -e "  ${GREEN}✅ 실행 중${NC}"
        echo -e "  📋 PID(s): $pids"
        
        # PID 파일과 실제 PID 비교
        if [ ! -z "$pid_from_file" ] && [[ "$pids" == *"$pid_from_file"* ]]; then
            echo -e "  📄 PID 파일: $pid_from_file (일치)"
        elif [ ! -z "$pid_from_file" ]; then
            echo -e "  📄 PID 파일: $pid_from_file (${RED}불일치${NC})"
        else
            echo -e "  📄 PID 파일: 없음"
        fi
        
        # 포트 확인
        if [ ! -z "$port_pid" ]; then
            if [[ "$pids" == *"$port_pid"* ]]; then
                echo -e "  🌐 포트 $port: ${GREEN}사용 중${NC} (PID: $port_pid)"
            else
                echo -e "  🌐 포트 $port: ${YELLOW}다른 프로세스가 사용 중${NC} (PID: $port_pid)"
            fi
        else
            echo -e "  🌐 포트 $port: ${RED}사용 안됨${NC}"
        fi
        
        # 메모리 사용량 (가능한 경우)
        if command -v ps >/dev/null 2>&1; then
            for pid in $pids; do
                local mem_info=$(ps -p $pid -o pid,ppid,%cpu,%mem,etime,cmd --no-headers 2>/dev/null || echo "")
                if [ ! -z "$mem_info" ]; then
                    echo -e "  💾 프로세스 정보:"
                    echo -e "     $mem_info"
                fi
            done
        fi
        
    else
        echo -e "  ${RED}❌ 실행 안됨${NC}"
        
        # PID 파일이 있는 경우
        if [ ! -z "$pid_from_file" ]; then
            echo -e "  📄 PID 파일: $pid_from_file (${RED}프로세스 없음${NC})"
        fi
        
        # 포트 확인
        if [ ! -z "$port_pid" ]; then
            echo -e "  🌐 포트 $port: ${YELLOW}다른 프로세스가 사용 중${NC} (PID: $port_pid)"
        else
            echo -e "  🌐 포트 $port: 사용 안됨"
        fi
    fi
    
    echo
}

# URL 접근성 확인 함수
check_url_accessibility() {
    local url=$1
    local service_name=$2
    
    if command -v curl >/dev/null 2>&1; then
        local response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$url" 2>/dev/null || echo "000")
        
        if [ "$response" = "200" ]; then
            echo -e "  🌐 URL 접근: ${GREEN}성공${NC} ($url)"
        elif [ "$response" = "000" ]; then
            echo -e "  🌐 URL 접근: ${RED}연결 실패${NC} ($url)"
        else
            echo -e "  🌐 URL 접근: ${YELLOW}HTTP $response${NC} ($url)"
        fi
    else
        echo -e "  🌐 URL 접근: ${YELLOW}curl 없음${NC} (확인 불가)"
    fi
}

# 백엔드 서버 상태 확인
check_service_status "백엔드 서버" "uvicorn.*app.main:app" "8000" ".backend.pid"
check_url_accessibility "http://localhost:8000" "백엔드"
check_url_accessibility "http://localhost:8000/docs" "백엔드 API 문서"

# 프론트엔드 서버 상태 확인
check_service_status "프론트엔드 서버" "npm.*start" "3000" ".frontend.pid"
check_url_accessibility "http://localhost:3000" "프론트엔드"

# 시스템 리소스 확인
echo -e "${YELLOW}💻 시스템 리소스:${NC}"

# 메모리 사용량
if command -v free >/dev/null 2>&1; then
    mem_info=$(free -h | grep "Mem:")
    echo -e "  🧠 메모리: $mem_info"
fi

# 디스크 사용량 (현재 디렉토리)
if command -v df >/dev/null 2>&1; then
    disk_info=$(df -h . | tail -1 | awk '{print $3 "/" $2 " (" $5 " 사용)"}')
    echo -e "  💾 디스크: $disk_info"
fi

# CPU 로드 (가능한 경우)
if [ -f /proc/loadavg ]; then
    load_avg=$(cat /proc/loadavg | awk '{print $1, $2, $3}')
    echo -e "  ⚡ CPU 로드: $load_avg"
fi

echo

# 로그 파일 상태
echo -e "${YELLOW}📋 로그 파일:${NC}"

check_log_file() {
    local log_file=$1
    local service_name=$2
    
    if [ -f "$log_file" ]; then
        local size=$(du -h "$log_file" 2>/dev/null | cut -f1)
        local lines=$(wc -l < "$log_file" 2>/dev/null || echo "0")
        echo -e "  📄 $service_name: ${GREEN}$log_file${NC} ($size, $lines 줄)"
        
        # 최근 에러 확인
        local error_count=$(grep -i "error\|exception\|traceback" "$log_file" 2>/dev/null | wc -l || echo "0")
        if [ "$error_count" -gt 0 ]; then
            echo -e "    ${RED}⚠️  최근 에러: $error_count 개${NC}"
        fi
    else
        echo -e "  📄 $service_name: ${RED}$log_file 없음${NC}"
    fi
}

check_log_file "backend.log" "백엔드"
check_log_file "frontend.log" "프론트엔드"
check_log_file "nohup.out" "시스템"
check_log_file "frontend/front.log" "프론트엔드 (구버전)"

echo
echo -e "${BLUE}=====================================${NC}"

# 전체 상태 요약
backend_running=$(pgrep -f "uvicorn.*app.main:app" 2>/dev/null || echo "")
frontend_running=$(pgrep -f "npm.*start" 2>/dev/null || echo "")

if [ ! -z "$backend_running" ] && [ ! -z "$frontend_running" ]; then
    echo -e "${GREEN}✅ 모든 서비스가 정상 실행 중입니다!${NC}"
elif [ ! -z "$backend_running" ]; then
    echo -e "${YELLOW}⚠️  백엔드만 실행 중입니다.${NC}"
elif [ ! -z "$frontend_running" ]; then
    echo -e "${YELLOW}⚠️  프론트엔드만 실행 중입니다.${NC}"
else
    echo -e "${RED}❌ 모든 서비스가 중지되어 있습니다.${NC}"
fi

echo -e "${BLUE}=====================================${NC}"
echo
echo -e "${YELLOW}📋 관리 명령어:${NC}"
echo -e "  - 서버 시작: ${BLUE}./start_all.sh${NC}"
echo -e "  - 서버 종료: ${BLUE}./stop_all.sh${NC}"
echo -e "  - 로그 확인: ${BLUE}tail -f backend.log${NC} 또는 ${BLUE}tail -f frontend.log${NC}"
echo -e "  - 실시간 상태: ${BLUE}watch -n 2 ./status.sh${NC}"