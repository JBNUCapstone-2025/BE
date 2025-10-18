from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import openai
from typing import Optional

# AI 핵심 기능 import
from ai_core.llm import (
    extract_emotion,
    extract_recent_emotion,
    get_embedding,
    generate_empathetic_response,
    generate_recommendation_response
)
from ai_core.vector_db import find_dissimilar_emotion_key
from ai_core.recommendation import format_recommendation, get_smart_recommendation

router = APIRouter(prefix="/api", tags=["AI Chat & Recommendation"])


class ChatRequest(BaseModel):
    sentence: str
    character: str = "강아지"  # 기본값은 강아지


class RecommendRequest(BaseModel):
    type: str  # 도서, 음악, 식사
    character: str = "강아지"
    conversation_history: str = ""


class DiaryAnalysisRequest(BaseModel):
    diary: str
    class_type: str = "일반"


@router.post("/chat")
async def chat(request: ChatRequest):
    """
    AI 챗봇 - 감정 분석 및 공감 응답
    1. 문장에서 감정 추출
    2. 공감 기능이 강화된 응답 생성
    3. 감정 벡터를 만들어 벡터 DB에서 반대 감정 찾기
    4. 반대 감정 기반 콘텐츠 추천
    5. 캐릭터 말투로 응답 생성
    """
    try:
        # 1. 감정 추출
        emotion = extract_emotion(request.sentence)

        # 2. 공감 기능 강화 - 먼저 사용자의 감정에 공감
        empathy_response = generate_empathetic_response(
            character=request.character,
            user_sentence=request.sentence,
            user_emotion=emotion
        )

        return {
            "answer": empathy_response,
            "detected_emotion": emotion
        }

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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"챗봇 응답 생성 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/recommend")
async def recommend(request: RecommendRequest):
    """
    RAG 기반 지능형 추천 시스템
    1. 전체 대화 기록에서 최근 감정 분석
    2. 벡터 DB를 활용한 반대 감정 찾기
    3. 대화 내용과 가장 관련성 높은 콘텐츠 추천
    4. 캐릭터 말투로 응답 생성
    """
    try:
        # 1. 전체 대화에서 최근 감정 추출
        conversation = request.conversation_history or "평범한 하루"

        # 최근 감정 추출 (여러 감정이 있을 경우 가장 최근 것 선택)
        recent_emotion = extract_recent_emotion(conversation)

        # 2. 감정 임베딩 생성 후 벡터 DB에서 반대 감정 찾기
        emotion_vector = get_embedding(recent_emotion)
        if emotion_vector is None:
            # fallback
            opposite_emotion = "평온"
        else:
            opposite_emotion = find_dissimilar_emotion_key(emotion_vector)

        # 3. 의미 기반 스마트 추천
        selected = get_smart_recommendation(
            user_text=conversation,
            emotion=opposite_emotion,
            category=request.type,
            top_k=3
        )

        if not selected:
            return {
                "answer": f"{request.type} 추천 데이터가 없습니다.",
                "recommendation_data": {"error": "데이터 없음"}
            }

        recommendation_data = {
            "category": request.type,
            "current_emotion": recent_emotion,
            "recommended_emotion": opposite_emotion,
            "recommendation": selected[0] if selected else {},
            "all_recommendations": selected
        }

        # 4. 추천 정보 포맷팅
        formatted_rec = format_recommendation(request.type, recommendation_data)

        # 5. 캐릭터 말투로 추천 메시지 생성
        answer = generate_recommendation_response(
            character=request.character,
            category=request.type,
            recommendation_data=recommendation_data,
            formatted_recommendation=formatted_rec
        )

        return {
            "answer": answer,
            "recommendation_data": recommendation_data
        }

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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"추천 생성 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/analyze-diary")
async def analyze_diary(request: DiaryAnalysisRequest):
    """
    일기 분석 및 감정 기반 지능형 추천
    1. 일기에서 감정 추출
    2. 감정 벡터를 만들어 반대 감정 찾기
    3. 일기 내용과 가장 관련성 높은 콘텐츠를 의미 기반으로 추천
    """
    try:
        # 1. 감정 추출
        emotion = extract_emotion(request.diary)

        # 2. 감정 임베딩 생성 후 벡터 DB에서 반대 감정 찾기
        emotion_vector = get_embedding(emotion)
        if emotion_vector is None:
            return {"error": "감정 분석에 실패했습니다."}

        opposite_emotion = find_dissimilar_emotion_key(emotion_vector)

        # 3. 의미 기반 스마트 추천
        selected_books = get_smart_recommendation(
            user_text=request.diary,
            emotion=opposite_emotion,
            category="도서",
            top_k=2
        )

        selected_music = get_smart_recommendation(
            user_text=request.diary,
            emotion=opposite_emotion,
            category="음악",
            top_k=2
        )

        selected_food = get_smart_recommendation(
            user_text=request.diary,
            emotion=opposite_emotion,
            category="식사",
            top_k=2
        )

        # 4. 감정에 따른 메시지 생성
        emotion_messages = {
            "행복": "오늘 정말 좋은 하루를 보내셨네요! 이 기분을 더 오래 간직할 수 있는 콘텐츠를 추천해드려요.",
            "슬픔": "힘든 하루였군요. 위로가 되는 콘텐츠로 마음을 다독여보세요.",
            "분노": "화가 많이 나셨나봐요. 스트레스를 해소할 수 있는 콘텐츠를 준비했어요.",
            "평온": "평온한 하루를 보내셨네요. 이 평화로움을 유지할 수 있는 콘텐츠예요.",
            "불안": "불안한 마음이 느껴지네요. 마음을 진정시킬 수 있는 콘텐츠를 추천드려요."
        }

        message = emotion_messages.get(emotion, "오늘 하루의 감정을 바탕으로 추천을 준비했어요.")

        return {
            "emotion": emotion,
            "opposite_emotion": opposite_emotion,
            "message": message,
            "books": selected_books,
            "music": selected_music,
            "food": selected_food
        }

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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"일기 분석 중 오류가 발생했습니다: {str(e)}"
        )
