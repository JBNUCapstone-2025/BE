# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, diary

app = FastAPI(
    title="ICSYF API",
    description="감정 기반 정서 관리 플랫폼 API",
    version="1.0.0"
)

# 🔐 CORS 설정 (개발용: 필요한 오리진만 남기세요)
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,     # 개발 단계라면 ["*"]도 가능
    allow_credentials=True,
    allow_methods=["*"],       # OPTIONS 포함
    allow_headers=["*"],       # Content-Type, Authorization 등
)

# 🧭 라우터 등록
# (1) auth.py 내부 APIRouter에 prefix="/auth"가 이미 있다면 그대로 둡니다.
# (2) 없다면 아래 include_router에서 prefix="/auth"를 지정하세요.
app.include_router(auth.router)                 # auth.py에 prefix가 있는 경우
# app.include_router(auth.router, prefix="/auth")  # auth.py에 prefix가 없는 경우

app.include_router(diary.router)

@app.get("/")
def read_root():
    return {"message": "✅ FastAPI 서버가 성공적으로 실행되었습니다!"}
