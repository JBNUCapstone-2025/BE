from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import openai
from typing import Optional, List

# AI 핵심 기능 import
from ai_core.llm import (
    extract_emotion,
    extract_recent_emotion,
    get_embedding,
    generate_empathetic_response,
    generate_recommendation_response
)
from ai_core.vector_db import get_recommendation_by_emotion
from ai_core.recommendation import format_recommendation

# DB 및 스키마 import
from app.core.deps import get_db, get_current_user_id
from app.crud import chat as chat_crud
from app.schemas.chat import (
    ChatCreateRequest,
    ChatCreateResponse,
    ChatResponse,
    ChatListResponse,
    ChatDetailResponse,
    ChatUpdateTitleRequest,
    ChatCompleteRequest,
    MessageCreateRequest,
    MessageCreateResponse
)

# 통합 라우터
router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    sentence: str
    chat_id: Optional[int] = None  # 대화방 ID (없으면 자동 생성)


class ChatCompleteRequest(BaseModel):
    category: str  # "book", "music", "food" 중 하나

    @field_validator('category')
    @classmethod
    def validate_category(cls, v):
        allowed = ["book", "music", "food"]
        if v not in allowed:
            raise ValueError(f"category는 {allowed} 중 하나여야 합니다")
        return v


@router.post("/message")
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    AI 챗봇 - 감정 분석 및 공감 응답 (멀티턴 지원) + DB 자동 저장
    1. User 테이블에서 캐릭터 자동 조회
    2. 문장에서 감정 추출
    3. 공감 기능이 강화된 응답 생성
    4. 대화 이력 관리
    5. DB에 자동 저장 (대화방 없으면 자동 생성)
    """
    try:
        # 1. User 캐릭터 조회
        from app.crud.user import get_user_by_id
        user = get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다"
            )

        # 캐릭터 미설정 체크
        if not user.character or not user.character_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="캐릭터가 설정되지 않았습니다. 마이페이지에서 먼저 캐릭터를 설정해주세요."
            )

        # 캐릭터 영어 → 한글 변환
        from prompt.characters import CHARACTER_NAME_MAP
        character_korean = CHARACTER_NAME_MAP.get(user.character, "강아지")

        # 대화 이력 자동 로드 (DB에서 message_order 순으로)
        chat_history = []
        chat_id = request.chat_id

        if chat_id:
            # 기존 대화방이 종료되었는지 체크
            db_chat = chat_crud.get_chat_by_id(db, chat_id, user_id)
            if not db_chat:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="해당 대화를 찾을 수 없습니다"
                )
            if db_chat.emotion is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="종료된 대화입니다. 새 대화를 시작해주세요."
                )

            # DB에서 메시지 조회하여 히스토리 구성 (message_order 순)
            if db_chat.messages:
                sorted_messages = sorted(db_chat.messages, key=lambda x: x.message_order)
                for msg in sorted_messages:
                    chat_history.append({"role": "user", "content": msg.user_message})
                    chat_history.append({"role": "assistant", "content": msg.bot_response})

        # 2. 감정 추출
        emotion = extract_emotion(request.sentence)

        # 현재 사용자의 질문 chat_history에 저장
        chat_history.append({"role": "user", "content": request.sentence})

        # 3. 공감 기능 강화 - 먼저 사용자의 감정에 공감
        empathy_response = generate_empathetic_response(
            character=character_korean,
            user_sentence=request.sentence,
            user_emotion=emotion,
            chat_history=chat_history
        )

        # assistant의 문장 chat_history에 저장
        chat_history.append({"role": "assistant", "content": empathy_response})

        # 3. DB 저장
        # 대화방이 없으면 자동 생성
        if not chat_id:
            chat_create_req = ChatCreateRequest(title="새 대화")
            db_chat = chat_crud.create_chat(db, user_id, chat_create_req)
            chat_id = db_chat.chat_id

        # 메시지 저장
        message_req = MessageCreateRequest(
            user_message=request.sentence,
            bot_response=empathy_response
        )
        db_message = chat_crud.create_message(db, chat_id, user_id, message_req)

        if not db_message:
            # 대화방을 찾을 수 없는 경우 (삭제되었거나 권한 없음)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 대화를 찾을 수 없습니다"
            )

        return {
            "answer": empathy_response,
            "detected_emotion": emotion,
            "conversation_history": chat_history,
            "chat_id": chat_id,  # 대화방 ID 반환
            "message_id": db_message.message_id  # 메시지 ID 반환
        }

    except HTTPException:
        raise
    except openai.APIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OpenAI API 오류가 발생했습니다: {str(e)}"
        )
    except openai.RateLimitError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="API 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요"
        )
    except openai.AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI 서비스 인증 오류가 발생했습니다"
        )
    except ValueError as e:
        # 캐릭터 미설정 에러 처리
        if "캐릭터가 설정되지 않았습니다" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="캐릭터가 설정되지 않았습니다. 마이페이지에서 먼저 캐릭터를 설정해주세요."
            )
        raise
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터베이스 오류가 발생했습니다: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"챗봇 응답 생성 중 오류가 발생했습니다: {str(e)}"
        )


# ================== Chat CRUD 엔드포인트 ==================

@router.post("/start", response_model=ChatCreateResponse, status_code=status.HTTP_201_CREATED)
def start_chat(
    chat_data: ChatCreateRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    대화방 생성
    - title 없으면 "새 대화"로 자동 생성
    """
    try:
        db_chat = chat_crud.create_chat(db, user_id, chat_data)
        return ChatCreateResponse(
            message="대화방이 생성되었습니다",
            chat=ChatResponse.model_validate(db_chat)
        )
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터베이스 오류가 발생했습니다: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"대화 생성 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/list", response_model=List[ChatListResponse])
def get_chat_list(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    대화 목록 조회 (최근 대화순)
    - skip: 건너뛸 개수 (기본값: 0)
    - limit: 최대 조회 개수 (기본값: 100, 최대: 1000)
    """
    try:
        if skip < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="skip은 0 이상이어야 합니다"
            )
        if limit < 1 or limit > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="limit은 1~1000 사이여야 합니다"
            )

        chats = chat_crud.get_chats_by_user(db, user_id, skip, limit)
        return [ChatListResponse.model_validate(chat) for chat in chats]
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터베이스 오류가 발생했습니다: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"대화 목록 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/{chat_id}", response_model=ChatDetailResponse)
def get_chat_detail(
    chat_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    대화 상세 조회 (메시지 포함)
    """
    try:
        db_chat = chat_crud.get_chat_by_id(db, chat_id, user_id)
        if not db_chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 대화를 찾을 수 없습니다"
            )

        return ChatDetailResponse.model_validate(db_chat)
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터베이스 오류가 발생했습니다: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"대화 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.patch("/{chat_id}/title", response_model=ChatResponse)
def update_chat_title(
    chat_id: int,
    title_data: ChatUpdateTitleRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    대화 제목 수정
    """
    try:
        db_chat = chat_crud.update_chat_title(db, chat_id, user_id, title_data)
        if not db_chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 대화를 찾을 수 없습니다"
            )

        return ChatResponse.model_validate(db_chat)
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터베이스 오류가 발생했습니다: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"제목 수정 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/{chat_id}/complete", response_model=ChatResponse)
async def complete_chat(
    chat_id: int,
    request: ChatCompleteRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    대화 종료 - AI 자동 분석 및 저장
    1. 전체 대화 내용에서 감정 분석
    2. 감정 기반 추천 생성 (사용자가 선택한 카테고리)
    3. Chat 테이블에 저장

    **주의: 한 번만 가능, 이미 완료된 대화는 에러**

    **Request Body:**
    - category: "book", "music", "food" 중 하나
    """
    try:
        # 1. 대화 조회
        db_chat = chat_crud.get_chat_by_id(db, chat_id, user_id)
        if not db_chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 대화를 찾을 수 없습니다"
            )

        # 2. 이미 완료된 대화인지 체크
        if db_chat.emotion is not None or db_chat.recommend_content is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 완료된 대화입니다"
            )

        # 3. 메시지가 없으면 에러
        if not db_chat.messages or len(db_chat.messages) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="대화 내용이 없습니다"
            )

        # 4. 전체 대화 내용 생성
        conversation = "\n".join([
            f"사용자: {msg.user_message}\n봇: {msg.bot_response}"
            for msg in db_chat.messages
        ])

        # 5. 감정 분석
        emotion = extract_recent_emotion(conversation)

        # 6. 사용자가 선택한 카테고리로 추천 생성
        # 영어 → 한글 매핑
        category_map = {
            "book": "도서",
            "music": "음악",
            "food": "음식"
        }
        selected_category_kr = category_map.get(request.category, "도서")

        # 감정 기반 추천 (1개만)
        recommendations = get_recommendation_by_emotion(
            emotion_query=emotion,
            conversation=conversation,
            category=selected_category_kr,
            k=1
        )

        if not recommendations or len(recommendations) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="추천 생성에 실패했습니다"
            )

        # 7. recommend_content 생성 (모든 필드 포함)
        rec_doc = recommendations[0]

        # metadata 복사 및 tags/dj_tags를 배열로 변환
        metadata = rec_doc.metadata.copy()
        if "tags" in metadata and isinstance(metadata["tags"], str):
            import json
            metadata["tags"] = json.loads(metadata["tags"])
        if "dj_tags" in metadata and isinstance(metadata["dj_tags"], str):
            import json
            metadata["dj_tags"] = json.loads(metadata["dj_tags"])

        # 전체 Document 정보 저장
        recommend_content = {
            request.category: {
                "id": rec_doc.id if hasattr(rec_doc, 'id') else "",
                "metadata": metadata,
                "page_content": rec_doc.page_content,
                "type": "Document"
            }
        }

        # 8. DB 저장
        db_chat.emotion = emotion
        db_chat.recommend_content = recommend_content
        db.commit()
        db.refresh(db_chat)

        return ChatResponse.model_validate(db_chat)

    except HTTPException:
        raise
    except openai.APIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OpenAI API 오류가 발생했습니다: {str(e)}"
        )
    except openai.RateLimitError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="API 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요"
        )
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터베이스 오류가 발생했습니다: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"대화 완료 처리 중 오류가 발생했습니다: {str(e)}"
        )


@router.delete("/{chat_id}", status_code=status.HTTP_200_OK)
def delete_chat(
    chat_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    대화 삭제 (하드 삭제)
    """
    try:
        success = chat_crud.delete_chat(db, chat_id, user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 대화를 찾을 수 없습니다"
            )

        return {"message": "대화가 삭제되었습니다"}
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터베이스 오류가 발생했습니다: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"대화 삭제 중 오류가 발생했습니다: {str(e)}"
        )
