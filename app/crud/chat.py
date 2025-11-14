from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.models import Chat, Message, User
from app.schemas.chat import (
    ChatCreateRequest,
    ChatUpdateTitleRequest,
    ChatCompleteRequest,
    MessageCreateRequest
)
from datetime import datetime
from typing import List, Optional


def create_chat(db: Session, user_id: int, chat: ChatCreateRequest) -> Chat:
    """대화방 생성"""
    try:
        db_chat = Chat(
            user_id=user_id,
            title=chat.title or "새 대화"
        )
        db.add(db_chat)
        db.commit()
        db.refresh(db_chat)
        return db_chat
    except Exception as e:
        db.rollback()
        raise


def get_chat_by_id(db: Session, chat_id: int, user_id: int) -> Optional[Chat]:
    """대화방 ID로 조회 (본인 대화만)"""
    return db.query(Chat).filter(
        Chat.chat_id == chat_id,
        Chat.user_id == user_id
    ).first()


def get_chats_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Chat]:
    """사용자의 모든 대화 조회 (최근 대화순)"""
    # COALESCE: last_message_date가 NULL이면 create_date 사용
    return db.query(Chat).filter(
        Chat.user_id == user_id
    ).order_by(
        func.coalesce(Chat.last_message_date, Chat.create_date).desc()
    ).offset(skip).limit(limit).all()


def update_chat_title(db: Session, chat_id: int, user_id: int, title_update: ChatUpdateTitleRequest) -> Optional[Chat]:
    """대화 제목 수정"""
    try:
        db_chat = get_chat_by_id(db, chat_id, user_id)
        if not db_chat:
            return None

        db_chat.title = title_update.title
        db.commit()
        db.refresh(db_chat)
        return db_chat
    except Exception as e:
        db.rollback()
        raise


def update_chat_complete(db: Session, chat_id: int, user_id: int, complete_data: ChatCompleteRequest) -> Optional[Chat]:
    """대화 종료 시 감정 분석 결과 및 추천 콘텐츠 저장"""
    try:
        db_chat = get_chat_by_id(db, chat_id, user_id)
        if not db_chat:
            return None

        db_chat.emotion = complete_data.emotion
        db_chat.recommend_content = complete_data.recommend_content
        db.commit()
        db.refresh(db_chat)
        return db_chat
    except Exception as e:
        db.rollback()
        raise


def delete_chat(db: Session, chat_id: int, user_id: int) -> bool:
    """대화 삭제 (하드 삭제)"""
    try:
        db_chat = get_chat_by_id(db, chat_id, user_id)
        if not db_chat:
            return False

        db.delete(db_chat)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise


def get_next_message_order(db: Session, chat_id: int) -> int:
    """대화의 다음 메시지 순서 번호 구하기"""
    max_order = db.query(func.max(Message.message_order)).filter(
        Message.chat_id == chat_id
    ).scalar()
    return (max_order or 0) + 1


def create_message(db: Session, chat_id: int, user_id: int, message: MessageCreateRequest) -> Optional[Message]:
    """메시지 저장 (캐릭터 정보는 User 테이블에서 자동 조회)"""
    try:
        # 대화방이 존재하고 본인 것인지 확인
        db_chat = get_chat_by_id(db, chat_id, user_id)
        if not db_chat:
            return None

        # User 테이블에서 캐릭터 정보 조회
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return None

        # 캐릭터가 설정되지 않은 경우 에러 (API 레이어에서 처리)
        if not user.character or not user.character_name:
            raise ValueError("캐릭터가 설정되지 않았습니다")

        # 다음 메시지 순서 번호 구하기
        message_order = get_next_message_order(db, chat_id)

        # 메시지 생성 (User 테이블의 캐릭터 정보 사용)
        db_message = Message(
            chat_id=chat_id,
            user_message=message.user_message,
            bot_response=message.bot_response,
            character=user.character,
            character_name=user.character_name,
            message_order=message_order
        )
        db.add(db_message)

        # 대화방의 last_message_date 업데이트 (로컬 시간 사용)
        db_chat.last_message_date = datetime.now()

        db.commit()
        db.refresh(db_message)
        return db_message
    except Exception as e:
        db.rollback()
        raise


def get_messages_by_chat(db: Session, chat_id: int, user_id: int) -> Optional[List[Message]]:
    """대화의 모든 메시지 조회 (순서대로)"""
    # 대화방이 존재하고 본인 것인지 확인
    db_chat = get_chat_by_id(db, chat_id, user_id)
    if not db_chat:
        return None

    return db.query(Message).filter(
        Message.chat_id == chat_id
    ).order_by(Message.message_order.asc()).all()
