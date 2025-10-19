from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.deps import get_db
from app.core.security import verify_password, create_access_token
from app.schemas.user import UserSignupRequest, UserSignupResponse, UserLoginRequest, UserLoginResponse
from app.crud.user import create_user, get_user_by_username, check_duplicate_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=UserSignupResponse, status_code=status.HTTP_201_CREATED)
def signup(user: UserSignupRequest, db: Session = Depends(get_db)):
    """회원가입 - 최적화된 중복 체크 (3쿼리 → 1쿼리)"""
    # 중복 체크 (1번의 쿼리로 username, email, nickname 동시 검증)
    existing_user = check_duplicate_user(db, user.username, user.email, user.nick_name)

    if existing_user:
        # 어떤 필드가 중복되었는지 확인하여 구체적인 에러 메시지 제공
        if existing_user.username == user.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 사용 중인 아이디입니다"
            )
        elif existing_user.email == user.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 사용 중인 이메일입니다"
            )
        elif existing_user.nick_name == user.nick_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 사용 중인 닉네임입니다"
            )

    # 유저 생성
    new_user = create_user(db, user)
    return {"message": "회원가입이 완료되었습니다", "user": new_user}


@router.post("/login", response_model=UserLoginResponse)
def login(user_login: UserLoginRequest, db: Session = Depends(get_db)):
    """로그인"""
    # 유저 조회
    user = get_user_by_username(db, user_login.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 올바르지 않습니다"
        )

    # 비밀번호 검증
    if not verify_password(user_login.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 올바르지 않습니다"
        )

    # JWT 토큰 생성
    access_token = create_access_token(data={"sub": user.username, "userId": user.user_id})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }
