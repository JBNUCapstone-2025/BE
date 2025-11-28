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


# 대화 종료 시 카테고리 선택 요청 스키마
class ChatCompleteRequest(BaseModel):
    category: str = Field(..., description="추천 카테고리 (book, music, food 중 하나)")

    @field_validator('category')
    @classmethod
    def validate_category(cls, v):
        valid_categories = ["book", "music", "food"]
        if v not in valid_categories:
            raise ValueError(f'카테고리는 {", ".join(valid_categories)} 중 하나여야 합니다')
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
    recommend_content: Optional[Dict[str, Any]] = None
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
    recommend_content: Optional[Dict[str, Any]] = None
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
