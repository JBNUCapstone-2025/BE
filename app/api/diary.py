from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta
from typing import List
import openai
from app.core.deps import get_db, get_current_user_id
from app.schemas.diary import (
    DiaryCreateRequest, DiaryCreateResponse, DiaryResponse,
    DiaryUpdateRequest, DiaryListResponse, DiaryCalendarResponse,
    DiaryCompleteRequest, DiaryCompleteResponse
)
from app.crud.diary import (
    create_diary, get_diary_by_id, get_diary_by_date,
    get_diaries_by_user, get_diaries_by_month,
    update_diary
)
from app.db.models import User

# AI 기능 import
from ai_core.llm import extract_emotion
from ai_core.vector_db import get_recommendation_by_emotion

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
    """
    일기 수정 (제목, 내용만 수정 가능)

    **주의:**
    - complete 후에는 수정 불가
    - 날짜 변경 불가 (title, content만 수정 가능)
    """
    # 일기 조회
    diary = get_diary_by_id(db, diary_id, user_id)
    if not diary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="일기를 찾을 수 없습니다"
        )

    # complete 후에는 수정 불가
    if diary.emotion is not None or diary.recommend_content is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="완료된 일기는 수정할 수 없습니다"
        )

    # 날짜 변경 시도 시 에러
    if diary_update.diary_date is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="일기 날짜는 변경할 수 없습니다"
        )

    updated_diary = update_diary(db, diary_id, user_id, diary_update)
    if not updated_diary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="일기를 찾을 수 없습니다"
        )
    return updated_diary


@router.post("/{diary_id}/complete", response_model=DiaryCompleteResponse)
async def complete_diary(
    diary_id: int,
    request: DiaryCompleteRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    일기 분석 및 감정 기반 지능형 추천 (카테고리 선택)
    1. 일기에서 감정 추출
    2. 선택한 카테고리의 추천 콘텐츠 3개 생성
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

        # 4. 카테고리 매핑
        category_map = {
            "book": "도서",
            "music": "음악",
            "food": "음식"
        }
        selected_category_kr = category_map.get(request.category, "도서")

        # 5. RAG 기반 추천 (선택한 카테고리 1개만)
        recommendations = get_recommendation_by_emotion(
            emotion_query=emotion,
            conversation=diary.content,
            category=selected_category_kr,
            k=1
        )

        # 6. 감정별 메시지 생성
        emotion_messages = {
            "기쁨": "오늘 정말 행복한 하루를 보내셨네요! 이 좋은 기분을 더 오래 간직할 수 있는 콘텐츠를 추천해드릴게요.",
            "설렘": "두근거리는 하루였군요! 이 설레는 마음이 더 풍성해질 수 있도록 잘 어울리는 콘텐츠를 골라봤어요.",
            "보통": "무난하고 평온한 하루였네요. 지금의 안정된 기분을 부드럽게 이어갈 수 있는 콘텐츠를 추천해드릴게요.",
            "슬픔": "마음이 조금 무거운 하루였겠어요. 조금이라도 위로가 되는 따뜻한 콘텐츠를 준비했어요.",
            "분노": "많이 답답하고 화가 나는 일이 있었나봐요. 마음을 풀고 스트레스를 덜어낼 수 있는 콘텐츠를 추천해드릴게요.",
            "불안": "불안한 마음이 느껴져요. 긴장을 조금 내려놓고 마음이 편안해질 수 있는 콘텐츠를 골라드릴게요."
        }

        message = emotion_messages.get(emotion, "오늘 하루의 감정을 바탕으로 추천을 준비했어요.")

        # 7. recommend_content 생성 (전체 객체 DB 저장)
        recommend_content = {}
        if recommendations:
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
            recommend_content[request.category] = {
                "id": rec_doc.id if hasattr(rec_doc, 'id') else "",
                "metadata": metadata,
                "page_content": rec_doc.page_content,
                "type": "Document"
            }

        # 8. DB 저장
        diary.emotion = emotion
        diary.recommend_content = recommend_content
        db.commit()
        db.refresh(diary)

        # 9. 챌린지 기회 증가 (오늘 또는 어제 일기만)
        user = db.query(User).filter(User.user_id == user_id).first()
        if user:
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            if diary.diary_date in [today, yesterday]:
                user.available_challenges += 1
                user.last_diary_date = today
            db.commit()

        # 10. 응답 형식 (1개만)
        recommendation_data = None
        if recommendations:
            doc = recommendations[0]

            # metadata 복사 및 tags/dj_tags를 배열로 변환
            metadata = doc.metadata.copy()
            if "tags" in metadata and isinstance(metadata["tags"], str):
                import json
                metadata["tags"] = json.loads(metadata["tags"])
            if "dj_tags" in metadata and isinstance(metadata["dj_tags"], str):
                import json
                metadata["dj_tags"] = json.loads(metadata["dj_tags"])

            recommendation_data = {
                "id": doc.id if hasattr(doc, 'id') else "",
                "metadata": metadata,
                "page_content": doc.page_content,
                "type": "Document"
            }

        # 11. 응답
        return {
            "emotion": emotion,
            "message": message,
            "recommendation": {
                "category": selected_category_kr,  # 한글 카테고리
                "emotion": emotion,
                "recommendation": recommendation_data
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
