from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .models import (
    Participant,
    TeamGenerationRequest,
    TeamGenerationResponse,
    CooccurrenceInfo,
    AttendanceUpdate,
    TeamHistoryItem,
    TeamHistoryResponse,
    DeleteHistoryRequest,
    TodayDataDeleteResponse
)
from .team_generator import TeamGenerator
from typing import List, Dict, Any
import json
import os
from datetime import date

app = FastAPI(title="Team Generator API")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 파일 경로 설정
PARTICIPANTS_FILE = "data/participants.json"
ATTENDING_FILE = "data/attending_participants.json"
TEAM_HISTORY_FILE = "data/team_history.json"

# 전역 TeamGenerator 인스턴스
team_generator = TeamGenerator(team_history_file=TEAM_HISTORY_FILE)

# 파일이 존재하지 않으면 생성
def ensure_file_exists(file_path: str, default_content):
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding='utf-8') as f:
            json.dump(default_content, f, indent=2, ensure_ascii=False)

# 서버 시작 시 필요한 파일 초기화
@app.on_event("startup")
async def startup_event():
    ensure_file_exists(PARTICIPANTS_FILE, [])
    ensure_file_exists(ATTENDING_FILE, [])
    ensure_file_exists(TEAM_HISTORY_FILE, [])
    
    # 기존 파일 데이터 정렬
    try:
        # 참가자 목록 정렬
        with open(PARTICIPANTS_FILE, "r", encoding='utf-8') as f:
            participants = json.load(f)
        if participants:
            participants.sort()
            with open(PARTICIPANTS_FILE, "w", encoding='utf-8') as f:
                json.dump(participants, f, indent=2, ensure_ascii=False)
                
        # 참석자 목록 정렬
        with open(ATTENDING_FILE, "r", encoding='utf-8') as f:
            attending = json.load(f)
        if attending:
            attending.sort()
            with open(ATTENDING_FILE, "w", encoding='utf-8') as f:
                json.dump(attending, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"파일 정렬 중 오류 발생: {e}")

@app.get("/")
async def root():
    return {"message": "Team Generator API"}

@app.get("/participants")
async def get_participants() -> List[str]:
    """현재 등록된 모든 참가자 목록을 반환합니다."""
    try:
        with open(PARTICIPANTS_FILE, "r", encoding='utf-8') as f:
            participants = json.load(f)
        return participants
    except FileNotFoundError:
        ensure_file_exists(PARTICIPANTS_FILE, [])
        return []

@app.post("/participants")
async def add_participant(participant: Participant):
    """새로운 참가자를 추가합니다."""
    # 참가자 목록 불러오기
    try:
        with open(PARTICIPANTS_FILE, "r", encoding='utf-8') as f:
            participants = json.load(f)
    except FileNotFoundError:
        participants = []

    # 중복 확인
    if participant.name in participants:
        raise HTTPException(status_code=400, detail="이미 존재하는 참가자입니다.")

    # 참가자 목록에 추가
    participants.append(participant.name)
    # 이름순으로 정렬
    participants.sort()
    with open(PARTICIPANTS_FILE, "w", encoding='utf-8') as f:
        json.dump(participants, f, indent=2, ensure_ascii=False)

    # 참가자가 추가되었으므로 특별한 추가 처리는 필요 없음
    # team_history.json에서 자동으로 공동 참여 데이터를 생성함

    return {"message": f"참가자 {participant.name}이(가) 추가되었습니다."}

@app.delete("/participants/{name}")
async def remove_participant(name: str):
    """참가자를 제거합니다."""
    # 참가자 목록 불러오기
    try:
        with open(PARTICIPANTS_FILE, "r", encoding='utf-8') as f:
            participants = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="참가자 데이터가 없습니다.")

    # 참가자 확인 및 제거
    if name not in participants:
        raise HTTPException(status_code=404, detail="참가자를 찾을 수 없습니다.")

    participants.remove(name)
    # 정렬은 필요 없지만 일관성을 위해 여기서도 정렬 유지
    participants.sort()
    with open(PARTICIPANTS_FILE, "w", encoding='utf-8') as f:
        json.dump(participants, f, indent=2, ensure_ascii=False)

    # 참석자 목록에서도 제거
    try:
        with open(ATTENDING_FILE, "r", encoding='utf-8') as f:
            attending = json.load(f)
        if name in attending:
            attending.remove(name)
            with open(ATTENDING_FILE, "w", encoding='utf-8') as f:
                json.dump(attending, f, indent=2, ensure_ascii=False)
    except FileNotFoundError:
        pass

    # 참가자가 제거되었으므로 특별한 추가 처리는 필요 없음
    # team_history.json에서 자동으로 공동 참여 데이터를 생성함

    return {"message": f"참가자 {name}이(가) 제거되었습니다."}

@app.get("/attending")
async def get_attending() -> List[str]:
    """현재 참석 중인 참가자 목록을 반환합니다."""
    try:
        with open(ATTENDING_FILE, "r", encoding='utf-8') as f:
            attending = json.load(f)
        return attending
    except FileNotFoundError:
        ensure_file_exists(ATTENDING_FILE, [])
        return []

@app.post("/attendance")
async def update_attendance(update: AttendanceUpdate):
    """참가자의 참석 여부를 업데이트합니다."""
    # 참가자 목록 확인
    try:
        with open(PARTICIPANTS_FILE, "r", encoding='utf-8') as f:
            participants = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="참가자 데이터가 없습니다.")

    if update.name not in participants:
        raise HTTPException(status_code=404, detail="존재하지 않는 참가자입니다.")

    # 참석자 목록 불러오기
    try:
        with open(ATTENDING_FILE, "r", encoding='utf-8') as f:
            attending = json.load(f)
    except FileNotFoundError:
        attending = []

    # 참석 여부 업데이트
    if update.attending and update.name not in attending:
        attending.append(update.name)
    elif not update.attending and update.name in attending:
        attending.remove(update.name)

    # 참석자 목록 정렬 후 저장
    attending.sort()
    with open(ATTENDING_FILE, "w", encoding='utf-8') as f:
        json.dump(attending, f, indent=2, ensure_ascii=False)

    return {"message": f"참가자 {update.name}의 참석 여부가 업데이트되었습니다."}

@app.post("/reset-attendance")
async def reset_attendance():
    """모든 참가자의 참석 여부를 초기화합니다."""
    with open(ATTENDING_FILE, "w", encoding='utf-8') as f:
        json.dump([], f, indent=2, ensure_ascii=False)
    return {"message": "모든 참가자의 참석 여부가 초기화되었습니다."}

@app.get("/cooccurrence")
async def get_cooccurrence_info(lam: float = 0.7) -> Dict[str, Dict[str, CooccurrenceInfo]]:
    """모든 참가자 쌍의 공동 참여 정보를 반환합니다."""
    participants = await get_participants()
    team_generator.load_past_cooccurrence_from_history(participants)
    return team_generator.get_cooccurrence_info(participants, lam)

@app.post("/generate")
async def generate_teams(request: TeamGenerationRequest) -> TeamGenerationResponse:
    """새로운 팀을 생성합니다."""
    # 과거 데이터 로드
    team_generator.load_past_cooccurrence_from_history(request.participants, request.window_days)
    
    # 팀 생성 방법 선택
    method_used = request.method
    
    # 참가자가 너무 적은 경우 weighted_random 방식으로 강제 변경
    if len(request.participants) < 8 and method_used == "simulated_annealing":
        method_used = "weighted_random"
    
    # SA 파라미터 설정
    sa_params = {}
    if request.sa_params:
        sa_params = request.sa_params
    
    # 방법에 따른 팀 생성
    if method_used == "weighted_random" or len(request.participants) < 8:
        groups = team_generator._generate_groups_weighted_random(request.participants, request.lam)
    else:  # simulated_annealing
        cooccurrence_counts = team_generator._get_cooccurrence_counts(request.participants)
        groups = team_generator._simulated_annealing(
            request.participants, 
            cooccurrence_counts,
            lam=request.lam,
            initial_temp=sa_params.get("initial_temp", 100.0),
            cooling_rate=sa_params.get("cooling_rate", 0.995),
            temp_min=sa_params.get("temp_min", 0.1),
            max_iter=int(sa_params.get("max_iter", 5000))
        )
    
    # 공동 참여 정보는 team_history.json에 저장되므로 별도 업데이트 불필요
    cooccurrence_info = team_generator.get_cooccurrence_info(request.participants, request.lam)
    
    # 조 생성 기록 저장
    await save_team_history(groups, method_used, request.lam, len(request.participants))
    
    return TeamGenerationResponse(
        groups=groups,
        cooccurrence_info=cooccurrence_info,
        method_used=method_used
    )

# 조 생성 기록 저장 함수
async def save_team_history(groups: List[List[str]], method_used: str, lambda_value: float, participants_count: int):
    """조 생성 기록을 저장합니다."""
    try:
        # 기존 기록 불러오기
        with open(TEAM_HISTORY_FILE, "r", encoding='utf-8') as f:
            history = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        history = []
    
    # 현재 날짜와 시간
    from datetime import datetime
    current_time = datetime.now().isoformat()
    
    # 새 기록 추가
    history.append({
        "date": current_time,
        "groups": groups,
        "method_used": method_used,
        "lambda_value": lambda_value,
        "participants_count": participants_count
    })
    
    # 파일에 저장
    with open(TEAM_HISTORY_FILE, "w", encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

@app.get("/team-history")
async def get_team_history() -> TeamHistoryResponse:
    """조 생성 기록을 조회합니다."""
    try:
        with open(TEAM_HISTORY_FILE, "r", encoding='utf-8') as f:
            history = json.load(f)
        return {"history": history}
    except (FileNotFoundError, json.JSONDecodeError):
        ensure_file_exists(TEAM_HISTORY_FILE, [])
        return {"history": []}

@app.delete("/team-history/{date}")
async def delete_team_history(date: str):
    """특정 날짜의 조 생성 기록을 삭제합니다."""
    try:
        with open(TEAM_HISTORY_FILE, "r", encoding='utf-8') as f:
            history = json.load(f)
        
        # 해당 날짜의 기록 필터링
        filtered_history = [item for item in history if item["date"] != date]
        
        # 필터링된 기록 저장
        with open(TEAM_HISTORY_FILE, "w", encoding='utf-8') as f:
            json.dump(filtered_history, f, indent=2, ensure_ascii=False)
        
        # cooccurrence 데이터에서도 해당 날짜 데이터 삭제
        try:
            # 날짜 형식 변환 (ISO 8601 전체 → 날짜만)
            try:
                from datetime import datetime
                parsed_date = datetime.fromisoformat(date).date().isoformat()
            except ValueError:
                # 이미 날짜 형식이거나 변환할 수 없는 경우
                parsed_date = date
            
            print(f"[디버깅] 삭제 대상 날짜: {parsed_date}")
            
            # cooccurrence 데이터 로드
            with open(COOCCURRENCE_FILE, "r", encoding='utf-8') as f:
                cooccurrence_data = json.load(f)
            
            # 해당 날짜 데이터 삭제
            modified_count = 0
            for p in cooccurrence_data:
                for q in list(cooccurrence_data.get(p, {}).keys()):
                    if q in cooccurrence_data[p]:
                        before_len = len(cooccurrence_data[p][q])
                        cooccurrence_data[p][q] = [d for d in cooccurrence_data[p][q] if not d.startswith(parsed_date)]
                        after_len = len(cooccurrence_data[p][q])
                        modified_count += (before_len - after_len)
            
            print(f"[디버깅] 공동참여 데이터에서 {modified_count}개 항목 삭제됨")
            
            # 저장
            with open(COOCCURRENCE_FILE, "w", encoding='utf-8') as f:
                json.dump(cooccurrence_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[디버깅] cooccurrence 데이터 삭제 중 오류: {str(e)}")
        
        return {"message": f"날짜 {date}의 조 생성 기록이 삭제되었습니다."}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="조 생성 기록 파일이 없습니다.")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="조 생성 기록 파일을 파싱할 수 없습니다.")

@app.delete("/team-history")
async def delete_all_team_history():
    """모든 조 생성 기록을 삭제합니다."""
    try:
        # 빈 기록으로 초기화
        with open(TEAM_HISTORY_FILE, "w", encoding='utf-8') as f:
            json.dump([], f, indent=2, ensure_ascii=False)
        
        # cooccurrence 데이터도 초기화
        try:
            # 현재 참가자 목록 가져오기
            with open(PARTICIPANTS_FILE, "r", encoding='utf-8') as f:
                participants = json.load(f)
            
            # 빈 구조 생성 (완전히 삭제하지 않고, 참가자는 유지한 채 기록만 삭제)
            empty_cooccurrence = {}
            for p in participants:
                empty_cooccurrence[p] = {}
                for q in participants:
                    if p != q:
                        empty_cooccurrence[p][q] = []
            
            with open(COOCCURRENCE_FILE, "w", encoding='utf-8') as f:
                json.dump(empty_cooccurrence, f, indent=2, ensure_ascii=False)
                
            print(f"[디버깅] 모든 공동참여 데이터가 초기화되었습니다.")
        except Exception as e:
            print(f"[디버깅] cooccurrence 데이터 초기화 중 오류: {str(e)}")
        
        return {"message": "모든 조 생성 기록이 삭제되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"조 생성 기록 삭제 중 오류가 발생했습니다: {str(e)}")

@app.delete("/today-data")
async def delete_today_data() -> TodayDataDeleteResponse:
    """오늘 날짜의 가장 최근에 생성된 조 데이터를 삭제합니다."""
    today_str = date.today().isoformat()
    print(f"[디버깅] 오늘 날짜: {today_str}")
    
    # 팀 히스토리에서 오늘 날짜의 가장 최근 데이터 삭제
    deleted_history_item = None
    try:
        with open(TEAM_HISTORY_FILE, "r", encoding='utf-8') as f:
            history = json.load(f)
        
        # 오늘 날짜 기록 찾기
        today_history_items = []
        other_history_items = []
        
        for item in history:
            item_date = item["date"]
            try:
                # ISO 형식 날짜 변환
                from datetime import datetime
                parsed_date = datetime.fromisoformat(item_date).date().isoformat()
                if parsed_date == today_str:
                    today_history_items.append(item)
                else:
                    other_history_items.append(item)
            except ValueError:
                # 날짜 파싱 오류 시 항목 유지
                other_history_items.append(item)
        
        # 오늘 데이터가 있으면 가장 최근 것 삭제
        if today_history_items:
            # 최신 순으로 정렬 (date 필드 기준)
            today_history_items.sort(key=lambda x: x["date"], reverse=True)
            # 첫 번째 항목(최신)을 삭제 대상으로 지정
            deleted_history_item = today_history_items[0]
            # 삭제 대상 제외하고 나머지 저장
            filtered_history = other_history_items + today_history_items[1:]
            
            print(f"[디버깅] 팀 히스토리에서 가장 최근 생성된 항목 삭제: {deleted_history_item['date']}")
        else:
            filtered_history = other_history_items
            print(f"[디버깅] 오늘 생성된 팀 히스토리 없음")
        
        # 필터링된 기록 저장
        with open(TEAM_HISTORY_FILE, "w", encoding='utf-8') as f:
            json.dump(filtered_history, f, indent=2, ensure_ascii=False)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[디버깅] 팀 히스토리 파일 처리 중 오류: {str(e)}")
    
    # cooccurrence 데이터에서 오늘 데이터의 가장 최근 항목 삭제
    deleted_cooccurrence_count = 0
    
    if deleted_history_item:
        try:
            # 삭제된 팀 구성에서 참가자 추출
            deleted_participants = set()
            for group in deleted_history_item["groups"]:
                for participant in group:
                    deleted_participants.add(participant)
            
            with open(COOCCURRENCE_FILE, "r", encoding='utf-8') as f:
                cooccurrence_data = json.load(f)
            
            # 삭제된 참가자들에 대해서만 오늘 날짜 데이터 중 가장 최근 항목 삭제
            for p in deleted_participants:
                if p not in cooccurrence_data:
                    continue
                    
                for q in deleted_participants:
                    if p == q or q not in cooccurrence_data[p]:
                        continue
                    
                    # 오늘 날짜 데이터 찾기
                    today_dates = [d for d in cooccurrence_data[p][q] if d == today_str]
                    
                    # 오늘 데이터가 있으면 가장 최근 항목(마지막 항목) 삭제
                    if today_dates:
                        before_len = len(cooccurrence_data[p][q])
                        # 모든 오늘 날짜 데이터 제거
                        other_dates = [d for d in cooccurrence_data[p][q] if d != today_str]
                        
                        # 마지막 항목 하나를 제외하고 다시 추가
                        if len(today_dates) > 1:
                            other_dates.extend(today_dates[:-1])
                        
                        cooccurrence_data[p][q] = other_dates
                        after_len = len(cooccurrence_data[p][q])
                        deleted_cooccurrence_count += (before_len - after_len)
            
            # 저장
            with open(COOCCURRENCE_FILE, "w", encoding='utf-8') as f:
                json.dump(cooccurrence_data, f, indent=2, ensure_ascii=False)
                
            print(f"[디버깅] 공동참여 데이터에서 {deleted_cooccurrence_count}개 항목 삭제됨")
        except Exception as e:
            print(f"[디버깅] cooccurrence 데이터 처리 중 오류: {str(e)}")
    
    return TodayDataDeleteResponse(
        message=f"오늘({today_str}) 날짜의 가장 최근에 생성된 조 데이터가 삭제되었습니다.",
        stats={
            "deleted_history_items": 1 if deleted_history_item else 0,
            "deleted_cooccurrence_items": deleted_cooccurrence_count
        }
    )

@app.get("/has-today-data")
async def check_today_data():
    """오늘 날짜에 생성된 팀 데이터가 있는지 확인합니다."""
    try:
        with open(COOCCURRENCE_FILE, "r", encoding='utf-8') as f:
            data = json.load(f)
        
        today_str = date.today().isoformat()
        has_today_data = False
        
        # 오늘 날짜의 데이터가 있는지 확인
        for person in data:
            for other in data.get(person, {}):
                dates = data[person][other]
                if today_str in dates:
                    has_today_data = True
                    break
            if has_today_data:
                break
        
        return {"has_today_data": has_today_data}
    except FileNotFoundError:
        return {"has_today_data": False}
    except Exception as e:
        return {"has_today_data": False, "error": str(e)} 