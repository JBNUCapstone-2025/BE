from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.models import Challenge, User, Continent, Diary
from app.core.constants import (
    CHALLENGE_POOL,
    MAX_BASIC_CHALLENGES_PER_CONTINENT,
    CHALLENGES_PER_CONTINENT,
    RESET_DAYS,
    MILEAGE_MIN,
    MILEAGE_MAX,
    CHALLENGES_FOR_MILEAGE
)
from datetime import date, datetime, timedelta
from typing import Optional, List
import random


# ===== 챌린지 리셋 체크 =====

def delete_old_incomplete_challenges(db: Session, user_id: int):
    """
    어제 이전에 선택한 미완료 챌린지 자동 삭제
    - 선택하고 완료 안한 챌린지는 다음날 자정에 사라짐
    """
    # 오늘 00:00:00
    today_start = datetime.combine(date.today(), datetime.min.time())

    # 오늘 이전에 생성된 미완료 챌린지 삭제
    deleted = db.query(Challenge).filter(
        Challenge.user_id == user_id,
        Challenge.is_completed == False,
        Challenge.create_date < today_start
    ).delete()

    return deleted


def check_and_reset_daily_challenges(db: Session, user: User):
    """
    일기 작성 날짜 기준으로 available_challenges 리셋
    - 일기 작성일로부터 2일 이상 지나면 0으로 리셋
    - 예: 1/23 일기 작성 → 1/24 자정까지 유효 → 1/25 되면 리셋
    """
    # 어제 이전 미완료 챌린지 삭제
    delete_old_incomplete_challenges(db, user.user_id)

    # available_challenges 리셋
    if user.last_diary_date:
        days_passed = (date.today() - user.last_diary_date).days
        if days_passed > 1:  # 2일 이상 지나면
            user.available_challenges = 0


def should_reset_challenges(db: Session, user: User) -> bool:
    """
    챌린지를 리셋해야 하는지 체크
    - 90일 경과
    - 60개 완료
    """
    if not user.challenge_start_date:
        return False

    # 90일 경과 체크
    days_passed = (datetime.now() - user.challenge_start_date).days
    if days_passed >= RESET_DAYS:
        return True

    # 60개 완료 체크
    total_completed = get_total_completed_count(db, user.user_id)
    if total_completed >= 60:
        return True

    return False


def reset_challenges(db: Session, user: User):
    """
    챌린지 완전 초기화
    """
    # 모든 챌린지 삭제 (CASCADE로 자동 삭제됨)
    db.query(Challenge).filter(Challenge.user_id == user.user_id).delete()

    # User 필드 초기화
    user.current_continent_id = None
    user.challenge_start_date = None
    user.available_challenges = 0
    user.last_challenge_date = None
    # mileage는 유지 (리셋하지 않음)

    db.commit()


# ===== 챌린지 선택 =====

def select_challenge(
    db: Session,
    user_id: int,
    continent_id: int,
    challenge_type: str
) -> Challenge:
    """
    챌린지 선택 (랜덤)
    - 기본 챌린지: 중복 방지 (이미 선택한 것 제외)
    - 추천 챌린지: 중복 허용 (계속 랜덤)
    """
    user = db.query(User).filter(User.user_id == user_id).first()

    # 실제 저장될 타입 (basic 또는 book/music/food)
    actual_type = challenge_type
    source_diary_date = None  # 기준 일기 날짜

    # 기본 챌린지 사용 횟수 체크
    basic_count = db.query(Challenge).filter(
        Challenge.user_id == user_id,
        Challenge.continent_id == continent_id,
        Challenge.challenge_type == 'basic'
    ).count()

    if challenge_type == 'basic' and basic_count >= MAX_BASIC_CHALLENGES_PER_CONTINENT:
        raise ValueError(f"기본 챌린지는 대륙당 최대 {MAX_BASIC_CHALLENGES_PER_CONTINENT}개까지만 선택 가능합니다")

    # 챌린지 텍스트 선택
    if challenge_type == 'basic':
        # 기본 챌린지: 이미 선택한 것 제외
        selected_texts = db.query(Challenge.challenge_text).filter(
            Challenge.user_id == user_id,
            Challenge.continent_id == continent_id,
            Challenge.challenge_type == 'basic'
        ).all()
        selected_texts = [t[0] for t in selected_texts]

        available = [c for c in CHALLENGE_POOL['basic'] if c not in selected_texts]
        if not available:
            raise ValueError("선택 가능한 기본 챌린지가 없습니다")

        challenge_text = random.choice(available)
        source_diary_date = None  # basic 챌린지는 일기 기준 없음
    else:
        # 추천 챌린지: 오늘 일기의 추천 타입에 따라 (book/music/food 결정)
        recommend_type, diary_date = get_today_recommend_type(db, user_id)
        actual_type = recommend_type  # 실제 타입은 book/music/food
        challenge_text = random.choice(CHALLENGE_POOL[recommend_type])
        source_diary_date = diary_date  # 기준이 된 일기 날짜 저장

    # challenge_number 계산 (이 대륙에서 몇 번째인지)
    challenge_number = db.query(Challenge).filter(
        Challenge.user_id == user_id,
        Challenge.continent_id == continent_id
    ).count() + 1

    # Challenge 생성
    new_challenge = Challenge(
        user_id=user_id,
        continent_id=continent_id,
        challenge_number=challenge_number,
        challenge_type=actual_type,  # basic 또는 book/music/food
        challenge_text=challenge_text,
        source_diary_date=source_diary_date  # 기준 일기 날짜 저장
    )

    db.add(new_challenge)

    # User 필드 업데이트
    user.available_challenges -= 1
    user.last_challenge_date = date.today()

    # 첫 챌린지 선택 시 시작일 기록
    if not user.challenge_start_date:
        user.challenge_start_date = datetime.now()

    # 현재 대륙 설정 (미설정 시)
    if not user.current_continent_id:
        user.current_continent_id = continent_id

    db.commit()
    db.refresh(new_challenge)

    return new_challenge


# ===== 오늘 일기의 추천 타입 가져오기 =====

def get_today_recommend_type(db: Session, user_id: int) -> tuple[str, date]:
    """
    챌린지에 매핑할 일기의 recommend_content 추출
    - 일기-챌린지 기회는 2일치만 유효 (어제, 오늘)
    - available_challenges와 오늘 선택한 챌린지 개수를 비교하여 일기 선택
    - 반환: (category, diary_date) 튜플

    available_challenges=2: 어제, 오늘 둘 다 있음
      - 첫 번째 챌린지 → 어제 일기
      - 두 번째 챌린지 → 오늘 일기

    available_challenges=1:
      - last_diary_date == 어제 → 어제 일기만 있음
      - last_diary_date == 오늘 → 오늘 일기만 있음
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    yesterday = date.today() - timedelta(days=1)
    today = date.today()

    # 오늘 선택한 챌린지 개수
    today_selected_count = db.query(Challenge).filter(
        Challenge.user_id == user_id,
        func.date(Challenge.create_date) == today
    ).count()

    # 어제, 오늘 일기 조회
    yesterday_diary = db.query(Diary).filter(
        Diary.user_id == user_id,
        Diary.diary_date == yesterday
    ).first()

    today_diary = db.query(Diary).filter(
        Diary.user_id == user_id,
        Diary.diary_date == today
    ).first()

    # 사용할 일기와 날짜 결정
    selected_diary = None
    selected_date = None

    # available_challenges=2: 어제, 오늘 둘 다 있음
    if user.available_challenges == 2:
        # 첫 번째 챌린지 → 어제 일기
        if today_selected_count == 0:
            if not yesterday_diary:
                raise ValueError("어제 일기를 찾을 수 없습니다")
            selected_diary = yesterday_diary
            selected_date = yesterday
        # 두 번째 챌린지 → 오늘 일기
        else:
            if not today_diary:
                raise ValueError("오늘 일기를 찾을 수 없습니다")
            selected_diary = today_diary
            selected_date = today

    # available_challenges=1: last_diary_date로 판단
    elif user.available_challenges == 1:
        if user.last_diary_date == yesterday and yesterday_diary:
            selected_diary = yesterday_diary
            selected_date = yesterday
        elif user.last_diary_date == today and today_diary:
            selected_diary = today_diary
            selected_date = today
        else:
            raise ValueError("일기를 찾을 수 없습니다")

    # available_challenges=0: 에러
    else:
        raise ValueError("챌린지 기회가 없습니다. 일기를 먼저 작성해주세요")

    # 1개 카테고리만 있으므로 키를 바로 반환
    content = selected_diary.recommend_content
    category = list(content.keys())[0]

    # 검증
    if category not in ['book', 'music', 'food']:
        raise ValueError(f"잘못된 추천 카테고리입니다: {category}")

    return category, selected_date


# ===== 챌린지 완료 =====

def complete_challenge(
    db: Session,
    user_id: int,
    challenge_id: int,
    content: str
) -> Challenge:
    """
    챌린지 완료
    - 5개 완료마다 마일리지 지급
    - 10개 완료 시 대륙 완료 (사용자가 다음 대륙 명시적으로 선택)
    """
    challenge = db.query(Challenge).filter(
        Challenge.challenge_id == challenge_id,
        Challenge.user_id == user_id
    ).first()

    if not challenge:
        raise ValueError("챌린지를 찾을 수 없습니다")

    if challenge.is_completed:
        raise ValueError("이미 완료한 챌린지입니다")

    # 챌린지 완료 처리
    challenge.is_completed = True
    challenge.content = content
    challenge.completed_date = date.today()

    # DB에 flush하여 is_completed 변경사항 즉시 반영
    db.flush()

    user = db.query(User).filter(User.user_id == user_id).first()

    # 전체 완료 개수 확인 (방금 완료한 것 포함)
    total_completed = db.query(Challenge).filter(
        Challenge.user_id == user_id,
        Challenge.is_completed == True
    ).count()

    # 5개 완료마다 마일리지 지급
    if total_completed % CHALLENGES_FOR_MILEAGE == 0:
        mileage_amount = random.randint(MILEAGE_MIN, MILEAGE_MAX)
        user.mileage += mileage_amount

    # 대륙별 완료 개수 확인
    completed_count = db.query(Challenge).filter(
        Challenge.user_id == user_id,
        Challenge.continent_id == challenge.continent_id,
        Challenge.is_completed == True
    ).count()

    # 10개 완료 시 대륙 클리어 (사용자가 다음 대륙 선택 가능하도록)
    if completed_count >= CHALLENGES_PER_CONTINENT:
        user.current_continent_id = None  # 대륙 초기화하여 새로운 대륙 선택 가능

    db.commit()
    db.refresh(challenge)

    return challenge


# ===== 챌린지 조회 =====

def get_challenge(db: Session, user_id: int, challenge_id: int) -> Optional[Challenge]:
    """챌린지 단일 조회"""
    return db.query(Challenge).filter(
        Challenge.challenge_id == challenge_id,
        Challenge.user_id == user_id
    ).first()


def get_challenges_by_continent(
    db: Session,
    user_id: int,
    continent_id: int
) -> List[Challenge]:
    """대륙별 챌린지 목록 조회"""
    return db.query(Challenge).filter(
        Challenge.user_id == user_id,
        Challenge.continent_id == continent_id
    ).order_by(Challenge.challenge_number).all()


def get_all_challenges(db: Session, user_id: int) -> List[Challenge]:
    """전체 챌린지 목록 조회"""
    return db.query(Challenge).filter(
        Challenge.user_id == user_id
    ).order_by(Challenge.continent_id, Challenge.challenge_number).all()


# ===== 통계 조회 =====

def get_continent_progress(db: Session, user_id: int, continent_id: int) -> dict:
    """대륙별 진행 상황"""
    challenges = get_challenges_by_continent(db, user_id, continent_id)

    total = len(challenges)
    completed = sum(1 for c in challenges if c.is_completed)
    basic_used = sum(1 for c in challenges if c.challenge_type == 'basic')
    basic_remaining = MAX_BASIC_CHALLENGES_PER_CONTINENT - basic_used

    return {
        "total_challenges": total,
        "completed_challenges": completed,
        "basic_remaining": basic_remaining,
        "can_select_basic": basic_remaining > 0,
        "is_completed": completed >= CHALLENGES_PER_CONTINENT
    }


def get_total_completed_count(db: Session, user_id: int) -> int:
    """전체 완료한 챌린지 수"""
    return db.query(Challenge).filter(
        Challenge.user_id == user_id,
        Challenge.is_completed == True
    ).count()


def get_days_until_reset(user: User) -> Optional[int]:
    """리셋까지 남은 일수"""
    if not user.challenge_start_date:
        return None

    elapsed = (datetime.now() - user.challenge_start_date).days
    remaining = RESET_DAYS - elapsed

    return max(0, remaining)
