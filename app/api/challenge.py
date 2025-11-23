from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from app.core.deps import get_db, get_current_user_id
from app.schemas.challenge import (
    ChallengeSelectRequest,
    ChallengeCompleteRequest,
    ChallengeResponse,
    ChallengeListResponse,
    ChallengeStatusResponse,
    ContinentProgressResponse,
    ContinentResponse
)
from app.crud import challenge as crud_challenge
from app.db.models import User, Continent, Challenge
from app.core.constants import CONTINENTS
from datetime import date

router = APIRouter()


# ===== 챌린지 현황 조회 =====

@router.get("/status", response_model=ChallengeStatusResponse)
def get_challenge_status(
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    챌린지 전체 현황 조회
    - 현재 대륙, 사용 가능 챌린지 횟수, 마일리지 등
    - 각 대륙별 진행 상황
    """
    try:
        user = db.query(User).filter(User.user_id == current_user_id).first()

        # 일일 챌린지 기회 리셋 (다음날 0으로) + 미완료 챌린지 삭제
        crud_challenge.check_and_reset_daily_challenges(db, user)
        db.commit()

        # 전체 리셋 체크 (90일 또는 60개 완료)
        if crud_challenge.should_reset_challenges(db, user):
            crud_challenge.reset_challenges(db, user)
            db.refresh(user)

        # 전체 완료 수
        total_completed = crud_challenge.get_total_completed_count(db, current_user_id)

        # 각 대륙별 진행 상황
        continents_progress = []
        for continent_id, continent_name, _ in CONTINENTS:
            progress = crud_challenge.get_continent_progress(db, current_user_id, continent_id)
            continents_progress.append(
                ContinentProgressResponse(
                    continent_id=continent_id,
                    continent_name=continent_name,
                    total_challenges=progress["total_challenges"],
                    completed_challenges=progress["completed_challenges"],
                    basic_remaining=progress["basic_remaining"],
                    can_select_basic=progress["can_select_basic"],
                    is_completed=progress["is_completed"]
                )
            )

        # 리셋까지 남은 일수
        days_until_reset = crud_challenge.get_days_until_reset(user)

        return ChallengeStatusResponse(
            current_continent_id=user.current_continent_id,
            available_challenges=user.available_challenges,
            last_challenge_date=user.last_challenge_date,
            mileage=user.mileage,
            challenge_start_date=user.challenge_start_date,
            days_until_reset=days_until_reset,
            total_completed=total_completed,
            continents=continents_progress
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"챌린지 현황 조회 실패: {str(e)}")


# ===== 대륙 목록 조회 =====

@router.get("/continents", response_model=List[ContinentResponse])
def get_continents(db: Session = Depends(get_db)):
    """대륙 목록 조회"""
    try:
        continents = db.query(Continent).order_by(Continent.display_order).all()
        return continents
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"대륙 목록 조회 실패: {str(e)}")


# ===== 대륙별 챌린지 목록 조회 =====

@router.get("/continent/{continent_id}", response_model=ChallengeListResponse)
def get_continent_challenges(
    continent_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """특정 대륙의 챌린지 목록 조회"""
    try:
        if continent_id < 1 or continent_id > 6:
            raise HTTPException(status_code=400, detail="대륙 ID는 1~6 사이여야 합니다")

        challenges = crud_challenge.get_challenges_by_continent(db, current_user_id, continent_id)

        # continent_name 추가
        continent_name = next((name for cid, name, _ in CONTINENTS if cid == continent_id), None)

        challenge_responses = []
        for c in challenges:
            response = ChallengeResponse.from_orm(c)
            response.continent_name = continent_name
            challenge_responses.append(response)

        # 대륙 진행도 정보 가져오기
        progress = crud_challenge.get_continent_progress(db, current_user_id, continent_id)

        return ChallengeListResponse(
            challenges=challenge_responses,
            total=len(challenges),
            basic_remaining=progress["basic_remaining"],
            can_select_basic=progress["can_select_basic"]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"챌린지 목록 조회 실패: {str(e)}")


# ===== 챌린지 선택 =====

@router.post("/select/{continent_id}", response_model=ChallengeResponse)
def select_new_challenge(
    continent_id: int,
    request: ChallengeSelectRequest,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    새로운 챌린지 선택
    - 하루 1개만 가능
    - 사용 가능한 챌린지 횟수 필요 (일기 작성으로 충전)
    """
    try:
        user = db.query(User).filter(User.user_id == current_user_id).first()

        # 일일 챌린지 기회 리셋 + 미완료 챌린지 삭제
        crud_challenge.check_and_reset_daily_challenges(db, user)
        db.commit()

        # 전체 리셋 체크
        if crud_challenge.should_reset_challenges(db, user):
            crud_challenge.reset_challenges(db, user)
            db.refresh(user)

        # 대륙 ID 검증
        if continent_id < 1 or continent_id > 6:
            raise HTTPException(status_code=400, detail="대륙 ID는 1~6 사이여야 합니다")

        # 현재 진행 중인 대륙 체크
        if user.current_continent_id and user.current_continent_id != continent_id:
            raise HTTPException(
                status_code=400,
                detail=f"현재 진행 중인 대륙({user.current_continent_id})을 먼저 완료해주세요"
            )

        # 사용 가능한 챌린지 횟수 체크
        if user.available_challenges <= 0:
            raise HTTPException(status_code=400, detail="사용 가능한 챌린지 횟수가 없습니다. 일기를 작성해주세요")

        # 미완료 챌린지 체크 (선택만 하고 완료 안 한 챌린지가 있으면 선택 불가)
        incomplete_challenge = db.query(Challenge).filter(
            Challenge.user_id == current_user_id,
            Challenge.is_completed == False
        ).first()

        if incomplete_challenge:
            raise HTTPException(status_code=400, detail="미완료 챌린지가 있습니다. 먼저 완료해주세요")

        # 대륙 완료 체크 (10개 이미 선택했는지)
        current_count = db.query(Challenge).filter(
            Challenge.user_id == current_user_id,
            Challenge.continent_id == continent_id
        ).count()

        if current_count >= 10:
            raise HTTPException(status_code=400, detail="이미 이 대륙의 모든 챌린지를 선택했습니다")

        # 챌린지 선택
        challenge = crud_challenge.select_challenge(db, current_user_id, continent_id, request.challenge_type)

        # continent_name 추가
        continent_name = next((name for cid, name, _ in CONTINENTS if cid == continent_id), None)
        response = ChallengeResponse.from_orm(challenge)
        response.continent_name = continent_name

        return response

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"챌린지 선택 실패: {str(e)}")


# ===== 챌린지 완료 =====

@router.patch("/{challenge_id}/complete", response_model=ChallengeResponse)
def complete_challenge_endpoint(
    challenge_id: int,
    request: ChallengeCompleteRequest,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    챌린지 완료
    - 5개 완료마다 마일리지 지급
    - 10개 완료 시 다음 대륙으로
    """
    try:
        challenge = crud_challenge.complete_challenge(db, current_user_id, challenge_id, request.content)

        # continent_name 추가
        continent_name = next((name for cid, name, _ in CONTINENTS if cid == challenge.continent_id), None)
        response = ChallengeResponse.from_orm(challenge)
        response.continent_name = continent_name

        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"챌린지 완료 실패: {str(e)}")


# ===== 챌린지 상세 조회 =====

@router.get("/{challenge_id}", response_model=ChallengeResponse)
def get_challenge_detail(
    challenge_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """챌린지 상세 조회"""
    try:
        challenge = crud_challenge.get_challenge(db, current_user_id, challenge_id)

        if not challenge:
            raise HTTPException(status_code=404, detail="챌린지를 찾을 수 없습니다")

        # continent_name 추가
        continent_name = next((name for cid, name, _ in CONTINENTS if cid == challenge.continent_id), None)
        response = ChallengeResponse.from_orm(challenge)
        response.continent_name = continent_name

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"챌린지 조회 실패: {str(e)}")


# ===== 전체 챌린지 목록 조회 =====

@router.get("/", response_model=ChallengeListResponse)
def get_all_challenges_endpoint(
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """전체 챌린지 목록 조회"""
    try:
        challenges = crud_challenge.get_all_challenges(db, current_user_id)

        challenge_responses = []
        for c in challenges:
            continent_name = next((name for cid, name, _ in CONTINENTS if cid == c.continent_id), None)
            response = ChallengeResponse.from_orm(c)
            response.continent_name = continent_name
            challenge_responses.append(response)

        return ChallengeListResponse(
            challenges=challenge_responses,
            total=len(challenges)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"챌린지 목록 조회 실패: {str(e)}")
