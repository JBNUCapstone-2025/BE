from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, Dict, List, Any, Union, Literal


# 대화방 생성 요청 스키마
class ChatCreateRequest(BaseModel):
    title: Optional[str] = Field("새 대화", min_length=1, max_length=200, description="대화 제목")


# 대화 제목 수정 요청 스키마
class ChatUpdateTitleRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="대화 제목")


# 메시지 저장 요청 스키마
class MessageCreateRequest(BaseModel):
    user_message: str = Field(..., min_length=1, description="유저 메시지")
    bot_response: str = Field(..., min_length=1, description="봇 응답")
    # character, character_name은 User 테이블에서 자동으로 조회


# 대화 종료 시 감정/추천 저장 요청 스키마
class ChatCompleteRequest(BaseModel):
    emotion: str = Field(..., description="AI 분석 감정 결과 (기쁨, 슬픔, 분노, 불안, 설렘, 보통)")
    recommend_content: Union[
        Dict[Literal["book"], str],
        Dict[Literal["music"], str],
        Dict[Literal["food"], str]
    ] = Field(..., description="AI 추천 콘텐츠 (book, music, food 중 1개만)")

    @field_validator('emotion')
    @classmethod
    def validate_emotion(cls, v):
        valid_emotions = ["기쁨", "슬픔", "분노", "불안", "설렘", "보통"]
        if v not in valid_emotions:
            raise ValueError(f'감정은 {", ".join(valid_emotions)} 중 하나여야 합니다')
        return v


# 메시지 응답 스키마
class MessageResponse(BaseModel):
    message_id: int
    chat_id: int
    user_message: str
    bot_response: str
    character: str
    character_name: str
    message_order: int
    create_date: datetime

    class Config:
        from_attributes = True


# 대화방 응답 스키마 (기본)
class ChatResponse(BaseModel):
    chat_id: int
    user_id: int
    title: str
    emotion: Optional[str] = None
    recommend_content: Optional[Union[
        Dict[Literal["book"], str],
        Dict[Literal["music"], str],
        Dict[Literal["food"], str]
    ]] = None
    last_message_date: Optional[datetime] = None
    create_date: datetime

    class Config:
        from_attributes = True


# 대화 목록 응답 스키마 (간단한 정보만)
class ChatListResponse(BaseModel):
    chat_id: int
    title: str
    emotion: Optional[str] = None
    last_message_date: Optional[datetime] = None
    create_date: datetime

    class Config:
        from_attributes = True


# 대화 상세 응답 스키마 (메시지 포함)
class ChatDetailResponse(BaseModel):
    chat_id: int
    user_id: int
    title: str
    emotion: Optional[str] = None
    recommend_content: Optional[Union[
        Dict[Literal["book"], str],
        Dict[Literal["music"], str],
        Dict[Literal["food"], str]
    ]] = None
    last_message_date: Optional[datetime] = None
    create_date: datetime
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True


# 대화 생성 응답 스키마
class ChatCreateResponse(BaseModel):
    message: str
    chat: ChatResponse


# 메시지 생성 응답 스키마
class MessageCreateResponse(BaseModel):
    message: str
    data: MessageResponse
