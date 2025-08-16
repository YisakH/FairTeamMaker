from pydantic import BaseModel
from typing import List, Dict, Optional, Literal, Any
from datetime import date

class Participant(BaseModel):
    name: str

class Group(BaseModel):
    members: List[str]

class CooccurrenceInfo(BaseModel):
    count: int
    probability: float
    last_occurrence: Optional[str] = None
    last_week: Optional[int] = None
    weeks_ago: Optional[int] = None
    time_decay_weight: float
    occurrence_dates: Optional[List[str]] = None

class TeamGenerationRequest(BaseModel):
    participants: List[str]
    window_days: int = 60
    lam: float = 0.7
    method: str = "simulated_annealing"
    sa_params: Dict[str, Any] = None
    accumulate_same_day: bool = False

class TeamGenerationResponse(BaseModel):
    groups: List[List[str]]
    cooccurrence_info: Dict[str, Dict[str, CooccurrenceInfo]]
    method_used: str

class AttendanceUpdate(BaseModel):
    name: str
    attending: bool

# 조 생성 기록 조회를 위한 모델 추가
class TeamHistoryItem(BaseModel):
    date: str
    groups: List[List[str]]
    method_used: str
    lambda_value: float
    participants_count: int

class TeamHistoryResponse(BaseModel):
    history: List[TeamHistoryItem]

class DeleteHistoryRequest(BaseModel):
    date: str

# 오늘 데이터 삭제 응답 모델
class TodayDataDeleteResponse(BaseModel):
    message: str
    stats: Dict[str, int] 