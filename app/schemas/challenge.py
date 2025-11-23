from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from typing import Optional, List

# ===== 대륙 스키마 =====

class ContinentResponse(BaseModel):
    continent_id: int
    continent_name: str
    display_order: int

    class Config:
        from_attributes = True


# ===== 챌린지 선택 요청 =====

class ChallengeSelectRequest(BaseModel):
    challenge_type: str = Field(..., description="basic(기본) 또는 recommend(추천)")

    @field_validator('challenge_type')
    @classmethod
    def validate_challenge_type(cls, v):
        allowed = ['basic', 'recommend']
        if v not in allowed:
            raise ValueError(f'challenge_type은 {allowed} 중 하나여야 합니다')
        return v


# ===== 챌린지 완료 요청 =====

class ChallengeCompleteRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000, description="사용자가 작성한 챌린지 내용")


# ===== 챌린지 응답 =====

class ChallengeResponse(BaseModel):
    challenge_id: int
    continent_id: int
    continent_name: Optional[str] = None  # JOIN으로 가져올 경우
    challenge_number: int
    challenge_type: str
    challenge_text: str
    content: Optional[str] = None
    is_completed: bool
    completed_date: Optional[date] = None
    create_date: datetime

    class Config:
        from_attributes = True


# ===== 대륙 진행도 응답 =====

class ContinentProgressResponse(BaseModel):
    continent_id: int
    continent_name: str
    total_challenges: int  # 현재까지 선택한 챌린지 수 (최대 10)
    completed_challenges: int  # 완료한 챌린지 수
    basic_remaining: int  # 남은 기본 챌린지 횟수 (최대 5)
    can_select_basic: bool  # 기본 챌린지 선택 가능 여부
    is_completed: bool  # 대륙 완료 여부 (10개 모두 완료)


# ===== 전체 챌린지 현황 응답 =====

class ChallengeStatusResponse(BaseModel):
    current_continent_id: Optional[int] = None  # 현재 진행 중인 대륙 (NULL이면 미시작)
    available_challenges: int  # 사용 가능한 챌린지 횟수
    last_challenge_date: Optional[date] = None  # 마지막 챌린지 수행 날짜
    mileage: int  # 현재 마일리지
    challenge_start_date: Optional[datetime] = None  # 챌린지 시작일
    days_until_reset: Optional[int] = None  # 리셋까지 남은 일수
    total_completed: int  # 전체 완료한 챌린지 수
    continents: List[ContinentProgressResponse]  # 각 대륙별 진행 상황


# ===== 챌린지 목록 응답 =====

class ChallengeListResponse(BaseModel):
    challenges: List[ChallengeResponse]
    total: int
    basic_remaining: int  # 이 대륙에서 남은 기본 챌린지 수 (최대 5)
    can_select_basic: bool  # 기본 챌린지 선택 가능 여부
