from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user_id
from app.schemas.user import UserResponse, CharacterUpdateRequest
from app.db.models import User

router = APIRouter(prefix="/user", tags=["User Profile"])


@router.get("/profile", response_model=UserResponse)
def get_profile(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """현재 로그인한 사용자의 프로필 조회"""
    user = db.query(User).filter(User.user_id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다"
        )

    return user


@router.patch("/character", response_model=UserResponse)
def update_character(
    character_data: CharacterUpdateRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """사용자의 캐릭터 업데이트"""
    user = db.query(User).filter(User.user_id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다"
        )

    # 캐릭터 업데이트
    user.character = character_data.character
    db.commit()
    db.refresh(user)

    return user
