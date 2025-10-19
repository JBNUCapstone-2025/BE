from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.db.models import User
from app.schemas.user import UserSignupRequest
from app.core.security import get_password_hash


def get_user_by_username(db: Session, username: str):
    """username으로 유저 조회"""
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str):
    """email으로 유저 조회"""
    return db.query(User).filter(User.email == email).first()


def get_user_by_nickname(db: Session, nick_name: str):
    """nickname으로 유저 조회"""
    return db.query(User).filter(User.nick_name == nick_name).first()


def check_duplicate_user(db: Session, username: str, email: str, nick_name: str):
    """
    유저 중복 체크 (최적화: 1번의 쿼리로 username, email, nickname 동시 검증)

    Returns:
        User 객체 또는 None
    """
    return db.query(User).filter(
        or_(
            User.username == username,
            User.email == email,
            User.nick_name == nick_name
        )
    ).first()


def create_user(db: Session, user_data: UserSignupRequest):
    """새로운 유저 생성"""
    try:
        hashed_password = get_password_hash(user_data.password)

        db_user = User(
            username=user_data.username,
            password=hashed_password,
            person_name=user_data.person_name,
            nick_name=user_data.nick_name,
            email=user_data.email,
            phone=user_data.phone
        )

        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        return db_user
    except Exception as e:
        db.rollback()
        raise
