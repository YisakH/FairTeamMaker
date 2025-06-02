from pydantic import BaseModel
from typing import List, Dict, Optional, Literal, Any
# from datetime import date # date는 현재 모델에서 직접 사용되지 않음

class Participant(BaseModel):
    name: str

# Group 모델은 현재 직접 사용되지 않으므로 삭제
# class Group(BaseModel):
#     members: List[str]

class CooccurrenceInfo(BaseModel):
    count: int
    probability: float
    last_occurrence: Optional[str] = None # str | None 과 동일

class TeamGenerationRequest(BaseModel):
    # participants: List[str] # 항상 전체 참가자를 사용하므로 요청에서 제거
    window_days: int = 60
    lam: float = 0.7
    method: Literal["simulated_annealing", "weighted_random"] = "simulated_annealing" # 사용 가능한 메서드 명시
    sa_params: Optional[Dict[str, Any]] = None # Optional 명시
    # accumulate_same_day: bool = False # 관련 로직 제거됨

class TeamGenerationResponse(BaseModel):
    groups: List[List[str]]
    cooccurrence_info: Dict[str, Dict[str, CooccurrenceInfo]]
    method_used: str

# AttendanceUpdate 모델은 관련 엔드포인트가 삭제되어 더 이상 사용되지 않으므로 삭제
# class AttendanceUpdate(BaseModel):
#     name: str
#     attending: bool

# 조 생성 기록 조회를 위한 모델
class TeamHistoryItem(BaseModel):
    date: str # ISO 8601 형식의 날짜-시간 문자열
    groups: List[List[str]]
    method_used: str
    lambda_value: float
    participants_count: int

class TeamHistoryResponse(BaseModel):
    history: List[TeamHistoryItem]

class DeleteHistoryRequest(BaseModel):
    date: str # 삭제할 히스토리 항목의 정확한 date 문자열 (ISO 형식)

# 오늘 데이터 삭제 응답 모델
class TodayDataDeleteResponse(BaseModel):
    message: str
    stats: Dict[str, int] 