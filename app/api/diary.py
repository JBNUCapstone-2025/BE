from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta
from typing import List
import openai
from app.core.deps import get_db, get_current_user_id
from app.schemas.diary import (
    DiaryCreateRequest, DiaryCreateResponse, DiaryResponse,
    DiaryUpdateRequest, DiaryListResponse, DiaryCalendarResponse
)
from app.crud.diary import (
    create_diary, get_diary_by_id, get_diary_by_date,
    get_diaries_by_user, get_diaries_by_month,
    update_diary, delete_diary
)
from app.db.models import User

# AI 기능 import
from ai_core.llm import extract_emotion, get_embedding
from ai_core.recommendation import get_smart_recommendation

router = APIRouter(prefix="/diary", tags=["Diary"])


@router.post("/", response_model=DiaryCreateResponse, status_code=status.HTTP_201_CREATED)
def create_diary_endpoint(
    diary: DiaryCreateRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """일기 작성"""
    # 같은 날짜에 이미 일기가 있는지 확인
    existing_diary = get_diary_by_date(db, user_id, diary.diary_date)
    if existing_diary:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{diary.diary_date} 날짜에 이미 일기가 존재합니다"
        )

    new_diary = create_diary(db, user_id, diary)

    # 일기 작성 시 챌린지 기회 증가 (오늘 또는 어제 일기만)
    user = db.query(User).filter(User.user_id == user_id).first()
    if user:
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        # 오늘 또는 어제 일기만 챌린지 기회 부여
        if diary.diary_date in [today, yesterday]:
            user.available_challenges += 1
            user.last_diary_date = today  # 실제 작성 날짜 기록

        db.commit()

    return {"message": "일기가 작성되었습니다", "diary": new_diary}


@router.get("/list", response_model=List[DiaryListResponse])
def get_diary_list(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """일기 목록 조회 (최신순)"""
    # 파라미터 검증
    if skip < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="skip은 0 이상이어야 합니다"
        )
    if limit < 1 or limit > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="limit은 1에서 1000 사이여야 합니다"
        )

    diaries = get_diaries_by_user(db, user_id, skip, limit)
    return diaries


@router.get("/calendar/{year}/{month}", response_model=DiaryCalendarResponse)
def get_diary_calendar(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """월별 일기 조회 (달력용)"""
    # 년도 검증
    if year < 1900 or year > 2100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="년도는 1900에서 2100 사이여야 합니다"
        )
    # 월 검증
    if month < 1 or month > 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="월은 1에서 12 사이여야 합니다"
        )

    diaries = get_diaries_by_month(db, user_id, year, month)
    return {"year": year, "month": month, "diaries": diaries}


@router.get("/by-date/{diary_date}", response_model=DiaryResponse)
def get_diary_by_date_endpoint(
    diary_date: str,  # YYYY-MM-DD 형식
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """특정 날짜의 일기 조회"""
    try:
        date_obj = datetime.strptime(diary_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식을 사용하세요"
        )

    diary = get_diary_by_date(db, user_id, date_obj)
    if not diary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{diary_date} 날짜의 일기를 찾을 수 없습니다"
        )
    return diary


@router.get("/{diary_id}", response_model=DiaryResponse)
def get_diary_detail(
    diary_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """일기 상세 조회"""
    diary = get_diary_by_id(db, diary_id, user_id)
    if not diary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="일기를 찾을 수 없습니다"
        )
    return diary


@router.put("/{diary_id}", response_model=DiaryResponse)
def update_diary_endpoint(
    diary_id: int,
    diary_update: DiaryUpdateRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """일기 수정"""
    # 날짜를 변경하는 경우, 해당 날짜에 이미 다른 일기가 있는지 확인
    if diary_update.diary_date is not None:
        existing_diary = get_diary_by_date(db, user_id, diary_update.diary_date)
        # 같은 날짜에 다른 일기가 있고, 그게 현재 수정하려는 일기가 아닌 경우
        if existing_diary and existing_diary.diary_id != diary_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{diary_update.diary_date} 날짜에 이미 일기가 존재합니다"
            )

    updated_diary = update_diary(db, diary_id, user_id, diary_update)
    if not updated_diary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="일기를 찾을 수 없습니다"
        )
    return updated_diary


@router.delete("/{diary_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_diary_endpoint(
    diary_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """일기 삭제"""
    success = delete_diary(db, diary_id, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="일기를 찾을 수 없습니다"
        )
    return None


@router.post("/{diary_id}/complete", response_model=DiaryResponse)
async def complete_diary(
    diary_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    일기 완성 - AI 감정 분석 및 추천
    1. 일기 내용에서 감정 추출
    2. 감정 기반 스마트 추천 (도서 2개, 음악 2개, 식사 2개)
    3. Diary 테이블에 emotion, recommend_content 저장

    **주의: 이미 완성된 일기는 재분석 불가**
    """
    try:
        # 1. 일기 조회
        diary = get_diary_by_id(db, diary_id, user_id)
        if not diary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="일기를 찾을 수 없습니다"
            )

        # 2. 이미 완성된 일기인지 체크
        if diary.emotion is not None or diary.recommend_content is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 완성된 일기입니다"
            )

        # 3. 감정 추출
        emotion = extract_emotion(diary.content)

        # 4. 감정 임베딩 생성 (필요 시)
        emotion_vector = get_embedding(emotion)
        if emotion_vector is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="감정 분석에 실패했습니다"
            )

        # 5. 의미 기반 스마트 추천
        selected_books = get_smart_recommendation(
            user_text=diary.content,
            emotion=emotion,
            category="도서",
            top_k=2
        )

        selected_music = get_smart_recommendation(
            user_text=diary.content,
            emotion=emotion,
            category="음악",
            top_k=2
        )

        selected_food = get_smart_recommendation(
            user_text=diary.content,
            emotion=emotion,
            category="식사",
            top_k=2
        )

        # 6. 감정별 메시지 생성
        emotion_messages = {
            "기쁨": "오늘 정말 좋은 하루를 보내셨네요! 이 기분을 더 오래 간직할 수 있는 콘텐츠를 추천해드려요.",
            "설렘": "설레는 마음이 느껴지네요! 이 기분을 더욱 풍성하게 만들어줄 콘텐츠를 준비했어요.",
            "보통": "평온한 하루를 보내셨네요. 이 평화로움을 유지할 수 있는 콘텐츠예요.",
            "슬픔": "힘든 하루였군요. 위로가 되는 콘텐츠로 마음을 다독여보세요.",
            "분노": "화가 많이 나셨나봐요. 스트레스를 해소할 수 있는 콘텐츠를 준비했어요.",
            "불안": "불안한 마음이 느껴지네요. 마음을 진정시킬 수 있는 콘텐츠를 추천드려요."
        }

        message = emotion_messages.get(emotion, "오늘 하루의 감정을 바탕으로 추천을 준비했어요.")

        # 7. recommend_content 생성 (첫 번째 추천만 저장)
        recommend_content = {}
        if selected_books:
            recommend_content["book"] = selected_books[0].get("title", "")
        if selected_music:
            recommend_content["music"] = selected_music[0].get("title", "")
        if selected_food:
            recommend_content["food"] = selected_food[0].get("title", "")

        # 8. DB 저장
        diary.emotion = emotion
        diary.recommend_content = recommend_content
        db.commit()
        db.refresh(diary)

        # 9. 응답 (분석 결과 포함)
        response_data = DiaryResponse.model_validate(diary)
        # 추가 정보를 response에 포함 (Pydantic 모델 외부)
        return {
            **response_data.model_dump(),
            "analysis": {
                "emotion": emotion,
                "message": message,
                "books": selected_books,
                "music": selected_music,
                "food": selected_food
            }
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
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터베이스 오류가 발생했습니다: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"일기 분석 중 오류가 발생했습니다: {str(e)}"
        )
