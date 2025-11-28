from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from typing import Optional, Dict, List, Any, Union, Literal


# 일기 작성 요청 스키마 (emotion, recommend_content는 complete 시 자동 생성)
class DiaryCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="일기 제목")
    content: str = Field(..., min_length=1, description="일기 내용")
    diary_date: date = Field(..., description="일기 날짜 (YYYY-MM-DD)")


# 일기 수정 요청 스키마
class DiaryUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="일기 제목")
    content: Optional[str] = Field(None, min_length=1, description="일기 내용")
    diary_date: Optional[date] = Field(None, description="일기 날짜 (YYYY-MM-DD)")


# 일기 응답 스키마 (기본 - complete 전)
class DiaryResponse(BaseModel):
    diary_id: int
    user_id: int
    title: str
    content: str
    emotion: Optional[str] = Field(None, description="AI 분석 감정 결과 (기쁨, 슬픔, 분노, 불안, 설렘, 보통)")
    recommend_content: Optional[Dict[str, Any]] = Field(None, description="AI 추천 콘텐츠 (book, music, food 중 1개)")
    diary_date: date
    create_date: datetime
    update_date: datetime

    class Config:
        from_attributes = True


# 일기 목록 응답 스키마 (간단한 정보만)
class DiaryListResponse(BaseModel):
    diary_id: int
    title: str
    emotion: Optional[str] = None
    diary_date: date
    create_date: datetime

    class Config:
        from_attributes = True


# 일기 작성 응답 스키마
class DiaryCreateResponse(BaseModel):
    message: str
    diary: DiaryResponse


# 일기 완료 요청 스키마 (카테고리 선택)
class DiaryCompleteRequest(BaseModel):
    category: Literal["book", "music", "food"] = Field(..., description="추천 받을 카테고리 (book, music, food 중 1개)")


# 일기 완료 응답 스키마 (AI 분석 완료 후)
class DiaryCompleteResponse(BaseModel):
    emotion: str = Field(..., description="AI 분석 감정 결과")
    message: str = Field(..., description="감정별 공감 메시지")
    recommendation: Dict[str, Any] = Field(..., description="추천 정보 (category, emotion, recommendation, all_recommendations)")


# 달력용 응답 스키마 (월별 일기 목록)
class DiaryCalendarResponse(BaseModel):
    year: int
    month: int
    diaries: List[DiaryListResponse]
