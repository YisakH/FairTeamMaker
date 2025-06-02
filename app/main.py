from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .models import (
    Participant,
    TeamGenerationRequest,
    TeamGenerationResponse,
    CooccurrenceInfo,
    TeamHistoryItem,
    TeamHistoryResponse,
    DeleteHistoryRequest,
    TodayDataDeleteResponse
)
from .team_generator import TeamGenerator
from typing import List, Dict, Any
import json
import os
from datetime import date, datetime

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
TEAM_HISTORY_FILE = "data/team_history.json"

# 전역 TeamGenerator 인스턴스
team_generator = TeamGenerator(team_history_file=TEAM_HISTORY_FILE)

# 파일이 존재하지 않으면 생성
def ensure_file_exists(file_path: str, default_content):
    if not os.path.exists(file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding='utf-8') as f:
            json.dump(default_content, f, indent=2, ensure_ascii=False)

# 서버 시작 시 필요한 파일 초기화
@app.on_event("startup")
async def startup_event():
    ensure_file_exists(PARTICIPANTS_FILE, [])
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
    except Exception as e:
        print(f"참가자 파일 정렬 중 오류 발생: {e}")

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
    except json.JSONDecodeError:
        print(f"경고: {PARTICIPANTS_FILE}이 비어있거나 잘못된 형식입니다. 빈 목록으로 초기화합니다.")
        ensure_file_exists(PARTICIPANTS_FILE, [])
        return []

@app.post("/participants")
async def add_participant(participant: Participant):
    """새로운 참가자를 추가합니다."""
    participants = await get_participants()

    if participant.name in participants:
        raise HTTPException(status_code=400, detail="이미 존재하는 참가자입니다.")

    participants.append(participant.name)
    participants.sort()
    with open(PARTICIPANTS_FILE, "w", encoding='utf-8') as f:
        json.dump(participants, f, indent=2, ensure_ascii=False)

    return {"message": f"참가자 {participant.name}이(가) 추가되었습니다."}

@app.delete("/participants/{name}")
async def remove_participant(name: str):
    """참가자를 제거합니다."""
    participants = await get_participants()

    if name not in participants:
        raise HTTPException(status_code=404, detail="참가자를 찾을 수 없습니다.")

    participants.remove(name)
    with open(PARTICIPANTS_FILE, "w", encoding='utf-8') as f:
        json.dump(participants, f, indent=2, ensure_ascii=False)

    return {"message": f"참가자 {name}이(가) 제거되었습니다."}

@app.get("/attending")
async def get_attending() -> List[str]:
    """항상 전체 참가자 목록을 반환합니다 (모든 참가자가 참석한 것으로 간주)."""
    return await get_participants()

@app.get("/cooccurrence")
async def get_cooccurrence_info(lam: float = 0.7) -> Dict[str, Dict[str, CooccurrenceInfo]]:
    """모든 참가자 쌍의 공동 참여 정보를 반환합니다."""
    participants = await get_participants()
    if not participants:
        return {}
    team_generator.load_past_cooccurrence(participants)
    return team_generator.get_cooccurrence_info(participants, lam)

@app.post("/generate")
async def generate_teams(request: TeamGenerationRequest) -> TeamGenerationResponse:
    """새로운 팀을 생성합니다. 항상 모든 등록된 참가자를 대상으로 합니다."""
    
    current_participants = await get_participants()
    if not current_participants:
        raise HTTPException(status_code=400, detail="팀을 생성할 참가자가 없습니다. 먼저 참가자를 등록해주세요.")

    # 팀 생성 전 과거 데이터 로드
    team_generator.load_past_cooccurrence(current_participants, request.window_days)
    
    method_used = request.method
    
    # 참가자 수에 따른 메서드 강제 변경 로직 (main.py에서 담당)
    if len(current_participants) < 4:
         method_used = "weighted_random"
    elif len(current_participants) < 8 and method_used == "simulated_annealing":
        method_used = "weighted_random"
    
    sa_params = request.sa_params or {} 
        
    if method_used == "weighted_random":
        # 직접 _generate_groups_weighted_random 호출
        groups = team_generator._generate_groups_weighted_random(current_participants, request.lam)
    else:  # simulated_annealing
        # SA를 위한 cooccurrence_counts 준비
        cooccurrence_counts = team_generator._get_cooccurrence_counts(current_participants)
        # 직접 _simulated_annealing 호출
        groups = team_generator._simulated_annealing(
            current_participants, 
            cooccurrence_counts,
            lam=request.lam,
            initial_temp=sa_params.get("initial_temp", 100.0),
            cooling_rate=sa_params.get("cooling_rate", 0.995),
            temp_min=sa_params.get("temp_min", 0.1),
            max_iter=int(sa_params.get("max_iter", 5000))
        )
    
    # 조 생성 기록 저장 (cooccurrence_info를 만들기 전에 저장해야, 다음 load 시 반영 가능)
    await save_team_history(groups, method_used, request.lam, len(current_participants))

    # 최신 팀 기록을 포함하여 cooccurrence 정보 다시 로드 및 생성
    # save_team_history 이후에 load_past_cooccurrence를 다시 호출하여 방금 생성된 팀 정보를 반영
    team_generator.load_past_cooccurrence(current_participants, request.window_days) 
    cooccurrence_info = team_generator.get_cooccurrence_info(current_participants, request.lam)
        
    return TeamGenerationResponse(
        groups=groups,
        cooccurrence_info=cooccurrence_info,
        method_used=method_used
    )

async def save_team_history(groups: List[List[str]], method_used: str, lambda_value: float, participants_count: int):
    """조 생성 기록을 저장합니다."""
    try:
        with open(TEAM_HISTORY_FILE, "r", encoding='utf-8') as f:
            history = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        history = []
    
    current_time = datetime.now().isoformat()
    
    history.append({
        "date": current_time,
        "groups": groups,
        "method_used": method_used,
        "lambda_value": lambda_value,
        "participants_count": participants_count
    })
    
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

@app.delete("/team-history/{date_iso_string}")
async def delete_team_history(date_iso_string: str):
    """특정 시간의 조 생성 기록을 삭제합니다. (ISO 형식의 시간 문자열 사용)"""
    try:
        with open(TEAM_HISTORY_FILE, "r", encoding='utf-8') as f:
            history = json.load(f)
        
        original_length = len(history)
        filtered_history = [item for item in history if item["date"] != date_iso_string]
        
        if len(filtered_history) == original_length:
            raise HTTPException(status_code=404, detail=f"날짜 {date_iso_string}의 조 생성 기록을 찾을 수 없습니다.")

        with open(TEAM_HISTORY_FILE, "w", encoding='utf-8') as f:
            json.dump(filtered_history, f, indent=2, ensure_ascii=False)
        
        return {"message": f"시간 {date_iso_string}의 조 생성 기록이 삭제되었습니다."}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="조 생성 기록 파일이 없습니다.")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="조 생성 기록 파일을 파싱할 수 없습니다.")

@app.delete("/team-history")
async def delete_all_team_history():
    """모든 조 생성 기록을 삭제합니다."""
    try:
        with open(TEAM_HISTORY_FILE, "w", encoding='utf-8') as f:
            json.dump([], f, indent=2, ensure_ascii=False)
        
        return {"message": "모든 조 생성 기록이 삭제되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"조 생성 기록 삭제 중 오류가 발생했습니다: {str(e)}")

@app.delete("/today-data")
async def delete_today_data() -> TodayDataDeleteResponse:
    """오늘 날짜의 가장 최근에 생성된 조 데이터를 삭제합니다."""
    today_str = date.today().isoformat()
    print(f"[정보] 오늘 날짜: {today_str}")
    
    deleted_history_item_info = None
    try:
        with open(TEAM_HISTORY_FILE, "r", encoding='utf-8') as f:
            history = json.load(f)
        
        today_history_items = []
        other_history_items = []
        
        for item in history:
            item_date_str = item["date"]
            try:
                parsed_item_date = datetime.fromisoformat(item_date_str).date().isoformat()
                if parsed_item_date == today_str:
                    today_history_items.append(item)
                else:
                    other_history_items.append(item)
            except ValueError:
                other_history_items.append(item)
        
        if today_history_items:
            today_history_items.sort(key=lambda x: x["date"], reverse=True)
            deleted_history_item = today_history_items[0]
            deleted_history_item_info = {"date": deleted_history_item["date"], "groups_count": len(deleted_history_item.get("groups",[]))}
            
            print(f"[정보] 팀 히스토리에서 가장 최근 생성된 항목 삭제 대상: {deleted_history_item['date']}")
            filtered_history = other_history_items + today_history_items[1:]
        else:
            filtered_history = other_history_items
            print(f"[정보] 오늘 생성된 팀 히스토리 없음")
        
        with open(TEAM_HISTORY_FILE, "w", encoding='utf-8') as f:
            json.dump(filtered_history, f, indent=2, ensure_ascii=False)
            
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[오류] 팀 히스토리 파일 처리 중: {str(e)}")
        return TodayDataDeleteResponse(
            message=f"오늘({today_str}) 조 데이터 삭제 중 오류 발생.",
            stats={
                "deleted_history_items": 0,
                "deleted_cooccurrence_items": 0 
            }
        )

    deleted_cooccurrence_count = 0
    
    return TodayDataDeleteResponse(
        message=f"오늘({today_str}) 날짜의 가장 최근 생성된 조 데이터가 삭제되었습니다." + (f" (삭제된 기록: {deleted_history_item_info['date']})" if deleted_history_item_info else ""),
        stats={
            "deleted_history_items": 1 if deleted_history_item_info else 0,
            "deleted_cooccurrence_items": deleted_cooccurrence_count
        }
    )

@app.get("/has-today-data")
async def check_today_data() -> Dict[str, Any]:
    """오늘 날짜에 생성된 팀 데이터가 있는지 확인합니다."""
    today_str = date.today().isoformat()
    try:
        with open(TEAM_HISTORY_FILE, "r", encoding='utf-8') as f:
            history = json.load(f)
        
        has_data_today = False
        for item in history:
            item_date_str = item.get("date")
            if item_date_str:
                try:
                    parsed_item_date = datetime.fromisoformat(item_date_str).date().isoformat()
                    if parsed_item_date == today_str:
                        has_data_today = True
                        break
                except ValueError:
                    print(f"경고: 잘못된 날짜 형식의 히스토리 항목 발견 - {item_date_str}")
                    continue
        
        return {"has_today_data": has_data_today}
    except (FileNotFoundError, json.JSONDecodeError):
        return {"has_today_data": False, "message": "팀 히스토리 파일을 찾을 수 없거나 분석할 수 없습니다."}
    except Exception as e:
        print(f"오늘 데이터 확인 중 오류 발생: {str(e)}")
        return {"has_today_data": False, "error": str(e)} 