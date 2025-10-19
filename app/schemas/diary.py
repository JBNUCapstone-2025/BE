from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from typing import Optional, Dict, List, Any


# 일기 작성 요청 스키마
class DiaryCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="일기 제목")
    content: str = Field(..., min_length=1, description="일기 내용")
    diary_date: date = Field(..., description="일기 날짜 (YYYY-MM-DD)")
    emotion: Optional[str] = Field(None, description="AI 분석 감정 결과 (기쁨, 슬픔, 분노, 불안, 설렘, 무기력)")
    recommend_content: Optional[Dict[str, List[Any]]] = Field(None, description="AI 추천 콘텐츠 (도서, 음악, 식사)")

    @field_validator('emotion')
    @classmethod
    def validate_emotion(cls, v):
        if v is not None:
            valid_emotions = ["기쁨", "슬픔", "분노", "불안", "설렘", "무기력"]
            if v not in valid_emotions:
                raise ValueError(f'감정은 {", ".join(valid_emotions)} 중 하나여야 합니다')
        return v

    @field_validator('recommend_content')
    @classmethod
    def validate_recommend_content(cls, v):
        if v is not None:
            valid_categories = ["도서", "음악", "식사"]
            for key in v.keys():
                if key not in valid_categories:
                    raise ValueError(f'추천 카테고리는 {", ".join(valid_categories)} 중 하나여야 합니다')
        return v


# 일기 수정 요청 스키마
class DiaryUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="일기 제목")
    content: Optional[str] = Field(None, min_length=1, description="일기 내용")
    diary_date: Optional[date] = Field(None, description="일기 날짜 (YYYY-MM-DD)")


# 일기 응답 스키마
class DiaryResponse(BaseModel):
    diary_id: int
    user_id: int
    title: str
    content: str
    emotion: Optional[str] = Field(None, description="AI 분석 감정 결과 (기쁨, 슬픔, 분노, 불안, 설렘, 무기력)")
    recommend_content: Optional[Dict[str, List[Any]]] = Field(None, description="AI 추천 콘텐츠 (도서, 음악, 식사)")
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


# 달력용 응답 스키마 (월별 일기 목록)
class DiaryCalendarResponse(BaseModel):
    year: int
    month: int
    diaries: List[DiaryListResponse]
