from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# API 라우터 import
from app.api import auth, diary, chat, user

app = FastAPI(
    title="ICSYF AI Integrated API",
    description="감정 기반 정서 관리 플랫폼 통합 API (AI + Backend)",
    version="2.0.0"
)

# CORS 설정
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    # 프로덕션 환경 추가
    "http://175.123.55.182:7777",  # 서버 IP
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 origin 허용 (개발 중)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(diary.router)
app.include_router(chat.router)


@app.get("/")
def read_root():
    """API 서버 상태 확인"""
    return {
        "message": "✅ ICSYF AI 통합 서버가 성공적으로 실행되었습니다!",
        "version": "2.0.0",
        "features": [
            "AI 챗봇 (감정 분석 + 캐릭터 대화)",
            "AI 추천 시스템 (도서, 음악, 식사)",
            "사용자 인증 (회원가입, 로그인)",
            "다이어리 관리 (작성, 조회, 수정, 삭제)",
            "AI 일기 분석 및 추천"
        ],
        "docs": "/docs"
    }