from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user_id
from app.schemas.user import UserResponse, CharacterUpdateRequest, UserProfileUpdateRequest, PasswordChangeRequest
from app.db.models import User
from app.core.security import verify_password, get_password_hash

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


@router.patch("/profile", response_model=UserResponse)
def update_profile(
    profile_data: UserProfileUpdateRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """사용자 프로필 업데이트 (person_name, nick_name, email, phone, birth, gender)

    닉네임과 이메일은 중복 체크 (본인 제외)
    비밀번호 변경은 PATCH /user/password 사용
    """

    user = db.query(User).filter(User.user_id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다"
        )

    # 닉네임 중복 체크 (본인 제외)
    if profile_data.nick_name != user.nick_name:
        existing_user = db.query(User).filter(
            User.nick_name == profile_data.nick_name,
            User.user_id != user_id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 사용 중인 닉네임입니다"
            )

    # 이메일 중복 체크 (본인 제외)
    if profile_data.email != user.email:
        existing_user = db.query(User).filter(
            User.email == profile_data.email,
            User.user_id != user_id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 사용 중인 이메일입니다"
            )

    # 프로필 업데이트
    user.person_name = profile_data.person_name
    user.nick_name = profile_data.nick_name
    user.email = profile_data.email
    user.phone = profile_data.phone
    user.birth = profile_data.birth
    user.gender = profile_data.gender

    db.commit()
    db.refresh(user)

    return user


@router.patch("/password", response_model=UserResponse)
def change_password(
    password_data: PasswordChangeRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """비밀번호 변경

    현재 비밀번호 확인 후 새 비밀번호로 변경
    """

    user = db.query(User).filter(User.user_id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다"
        )

    # 현재 비밀번호 확인
    if not verify_password(password_data.current_password, user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 비밀번호가 일치하지 않습니다"
        )

    # 새 비밀번호로 업데이트
    user.password = get_password_hash(password_data.new_password)

    db.commit()
    db.refresh(user)

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

    # 캐릭터 및 캐릭터 이름 업데이트
    user.character = character_data.character
    user.character_name = character_data.character_name

    db.commit()
    db.refresh(user)

    return user
