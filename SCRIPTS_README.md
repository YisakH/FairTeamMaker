# FairTeamMaker 통합 관리 스크립트

프론트엔드와 백엔드 서버를 통합으로 관리할 수 있는 스크립트들입니다.

## 📋 스크립트 목록

### 🚀 `start_all.sh` - 통합 서버 시작
모든 서버(백엔드 + 프론트엔드)를 한 번에 시작합니다.

```bash
./start_all.sh
```

**기능:**
- 기존 프로세스 자동 종료
- 포트 충돌 검사
- 백엔드 서버 시작 (기본: localhost:8000)
- 프론트엔드 서버 시작 (기본: localhost:3000)
- 상태 확인 및 PID 저장
- 로그 파일 분리 (backend.log, frontend.log)

**환경 변수 지원:**
```bash
BACKEND_HOST=0.0.0.0 BACKEND_PORT=8080 FRONTEND_PORT=3001 ./start_all.sh
```

### 🛑 `stop_all.sh` - 통합 서버 종료
모든 서버를 안전하게 종료합니다.

```bash
./stop_all.sh              # 일반 종료
./stop_all.sh --force      # 강제 종료
```

**기능:**
- PID 파일 기반 종료
- 패턴 매칭으로 남은 프로세스 정리
- 강제 종료 옵션 지원
- 포트 점유 프로세스 정리
- 로그 파일 정리 옵션

### 📊 `status.sh` - 서버 상태 확인
현재 서버들의 상태를 자세히 확인합니다.

```bash
./status.sh                # 상태 확인
watch -n 2 ./status.sh     # 실시간 모니터링
```

**확인 항목:**
- 프로세스 실행 상태 및 PID
- 포트 사용 현황
- 메모리/CPU 사용량
- URL 접근성 (curl 필요)
- 로그 파일 상태 및 에러 개수

## 🔧 사용법

### 1. 처음 시작하기
```bash
# 실행 권한 부여 (최초 1회)
chmod +x start_all.sh stop_all.sh status.sh

# 서버 시작
./start_all.sh
```

### 2. 일상적인 관리
```bash
# 상태 확인
./status.sh

# 서버 재시작
./stop_all.sh
./start_all.sh

# 또는 한 번에
./stop_all.sh && ./start_all.sh
```

### 3. 문제 해결
```bash
# 강제 종료 후 재시작
./stop_all.sh --force
./start_all.sh

# 로그 확인
tail -f backend.log
tail -f frontend.log

# 실시간 상태 모니터링
watch -n 2 ./status.sh
```

## 📁 파일 구조

```
FairTeamMaker/
├── start_all.sh          # 통합 시작 스크립트
├── stop_all.sh           # 통합 종료 스크립트
├── status.sh             # 상태 확인 스크립트
├── .backend.pid          # 백엔드 PID 파일 (자동 생성)
├── .frontend.pid         # 프론트엔드 PID 파일 (자동 생성)
├── backend.log           # 백엔드 로그 (자동 생성)
├── frontend.log          # 프론트엔드 로그 (자동 생성)
├── run_server.sh         # 기존 백엔드 전용 스크립트
└── frontend_run.sh       # 기존 프론트엔드 전용 스크립트
```

## 🌐 기본 접속 주소

- **백엔드 API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **프론트엔드**: http://localhost:3000

## 🔧 커스터마이징

### 포트 변경
```bash
# 환경 변수로 포트 설정
BACKEND_PORT=8080 FRONTEND_PORT=3001 ./start_all.sh
```

### 호스트 변경
```bash
# 외부 접속 허용
BACKEND_HOST=0.0.0.0 FRONTEND_HOST=0.0.0.0 ./start_all.sh
```

### API URL 설정
```bash
# 프론트엔드에서 사용할 API URL
API_URL=http://myserver.com:8000 ./start_all.sh
```

## 🐛 문제 해결

### 포트가 이미 사용 중인 경우
```bash
# 포트 사용 프로세스 확인
lsof -i :8000
lsof -i :3000

# 강제 종료 후 재시작
./stop_all.sh --force
./start_all.sh
```

### 프로세스가 종료되지 않는 경우
```bash
# 패턴으로 프로세스 확인
ps aux | grep uvicorn
ps aux | grep npm

# 수동 종료
pkill -f "uvicorn.*app.main:app"
pkill -f "npm.*start"
```

### 로그 확인
```bash
# 실시간 로그 확인
tail -f backend.log
tail -f frontend.log

# 에러 로그 필터링
grep -i error backend.log
grep -i error frontend.log
```

## 💡 팁

1. **실시간 모니터링**: `watch -n 2 ./status.sh`로 2초마다 상태 자동 갱신
2. **백그라운드 실행**: 모든 서버는 백그라운드에서 실행되므로 터미널을 닫아도 계속 동작
3. **로그 관리**: 로그 파일이 너무 커지면 주기적으로 정리 (`> backend.log`)
4. **개발 모드**: 백엔드는 `--reload` 옵션으로 실행되어 코드 변경 시 자동 재시작
5. **환경 분리**: 개발/운영 환경별로 다른 포트 사용 권장

---

**참고**: 기존의 `run_server.sh`와 `frontend_run.sh`는 개별 서버용으로 계속 사용 가능합니다.