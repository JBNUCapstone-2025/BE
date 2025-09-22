# app/main.py
from fastapi import FastAPI

# FastAPI 앱(서버) 인스턴스 생성
app = FastAPI()

# 루트 경로("/")로 GET 요청이 들어왔을 때 실행될 함수 정의
@app.get("/")
def read_root():
    # 서버의 루트 경로로 접속했을 때 간단한 메시지를 반환합니다.
    return {"message": "✅ FastAPI 서버가 성공적으로 실행되었습니다!"}