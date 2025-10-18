from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.core.security import verify_token

# HTTP Bearer 스키마
security = HTTPBearer()


def get_db() -> Generator:
    """
    데이터베이스 세션 의존성
    각 요청마다 새로운 DB 세션을 생성하고 요청 종료 시 자동으로 닫습니다.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    """
    JWT 토큰에서 현재 사용자 ID 추출

    Args:
        credentials: HTTP Bearer 토큰

    Returns:
        int: 사용자 ID

    Raises:
        HTTPException: 토큰이 유효하지 않거나 만료된 경우
    """
    token = credentials.credentials
    payload = verify_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않거나 만료된 토큰입니다"
        )

    user_id = payload.get("userId")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰 페이로드가 유효하지 않습니다"
        )

    return user_id
