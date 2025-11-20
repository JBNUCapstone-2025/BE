from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


# ========== Board Schemas ==========

class BoardCreateRequest(BaseModel):
    category: str = Field(..., description="게시판 카테고리 (free, secret, info, praise, comfort, worry)")
    title: str = Field(..., min_length=1, max_length=20, description="제목 (최대 20자)")
    content: str = Field(..., min_length=1, description="내용 (최소 1자)")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        valid_categories = ["free", "secret", "info", "praise", "comfort", "worry"]
        if v not in valid_categories:
            raise ValueError(f'카테고리는 {", ".join(valid_categories)} 중 하나여야 합니다')
        return v

    @field_validator("title", "content")
    def strip_whitespace(cls, v):
        if not v or not v.strip():
            raise ValueError("공백만 입력할 수 없습니다")
        return v.strip()


class BoardUpdateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=20, description="제목 (최대 20자)")
    content: str = Field(..., min_length=1, description="내용 (최소 1자)")

    @field_validator("title", "content")
    def strip_whitespace(cls, v):
        if not v or not v.strip():
            raise ValueError("공백만 입력할 수 없습니다")
        return v.strip()


class BoardListItemResponse(BaseModel):
    board_id: int
    category: str
    title: str
    content_preview: str  # 20자 미리보기
    likes_count: int
    comment_count: int
    is_liked: bool
    is_mine: bool
    is_edited: bool
    create_date: datetime

    class Config:
        from_attributes = True


class CommentResponse(BaseModel):
    comment_id: int
    content: str
    anonymous_number: int  # 익명1, 익명2
    is_author: bool  # 글쓴이 여부
    is_mine: bool  # 본인 작성 여부
    is_liked: bool
    is_edited: bool
    likes_count: int
    create_date: datetime
    replies: List["CommentResponse"] = []  # 대댓글

    class Config:
        from_attributes = True


class BoardDetailResponse(BaseModel):
    board_id: int
    category: str
    title: str
    content: str  # 전체 내용
    likes_count: int
    comment_count: int
    is_liked: bool
    is_mine: bool
    is_edited: bool
    create_date: datetime
    comments: List[CommentResponse] = []

    class Config:
        from_attributes = True


# ========== Comment Schemas ==========

class CommentCreateRequest(BaseModel):
    board_id: int
    parent_comment_id: Optional[int] = None
    content: str = Field(..., min_length=1, description="댓글 내용 (최소 1자)")

    @field_validator("parent_comment_id", mode='before')
    @classmethod
    def convert_zero_to_none(cls, v):
        """0을 null로 변환 (Swagger UI 호환성)"""
        if v == 0:
            return None
        return v

    @field_validator("content")
    @classmethod
    def strip_whitespace(cls, v):
        if not v or not v.strip():
            raise ValueError("공백만 입력할 수 없습니다")
        return v.strip()


class CommentUpdateRequest(BaseModel):
    content: str = Field(..., min_length=1, description="댓글 내용 (최소 1자)")

    @field_validator("content")
    def strip_whitespace(cls, v):
        if not v or not v.strip():
            raise ValueError("공백만 입력할 수 없습니다")
        return v.strip()


# ========== Like Schemas ==========

class LikeResponse(BaseModel):
    """좋아요 토글 응답"""
    is_liked: bool  # 현재 좋아요 상태
    likes_count: int  # 현재 좋아요 수

    class Config:
        from_attributes = True
