# ICSYF Backend Server

**ICSYF (I Can See Your Feelings)** - 감정 기반 정서 관리 플랫폼 백엔드 서버

FastAPI 기반으로 구축된 AI 통합 백엔드 시스템입니다.

---

## 📌 주요 기능

### 1. 사용자 인증
- 회원가입 & 로그인 (JWT 토큰 기반)
- 비밀번호 암호화 (bcrypt)
- 사용자 프로필 관리
- 동물 캐릭터 선택 시스템 (6종)

### 2. 감정 일기
- CRUD 기능 (작성, 조회, 수정, 삭제)
- 하루 1개 일기 제한
- 날짜별/월별 조회
- AI 감정 분석 및 추천 (통합 예정)

### 3. AI 챗봇
- 6가지 동물 캐릭터 대화 (강아지, 고양이, 곰, 토끼, 너구리, 햄스터)
- 실시간 감정 분석 (OpenAI API)
- 캐릭터별 맞춤 말투

### 4. 챗봇 대화 저장
- 대화방 생성 및 관리 (CRUD)
- 메시지 이력 저장 및 조회
- 캐릭터 변경 이력 추적
- 대화 종료 시 감정 분석 결과 저장

### 5. AI 추천 시스템
- RAG 기반 스마트 추천 (도서, 음악, 식사)
- FAISS 벡터 DB 활용
- 감정 기반 반대 감정 찾기

### 6. 커뮤니티 (익명 게시판)
- 6개 게시판 (자유, 비밀, 정보, 칭찬, 위로, 고민)
- 완전 익명 시스템 (게시글별 익명 번호 부여)
- 댓글/대댓글 (2단계)
- 좋아요 기능 (게시글, 댓글)
- 검색 기능 (제목+내용, 카테고리별)
- 성능 최적화 (N+1 쿼리 해결)

---

## 🛠 기술 스택

| Category | Technology |
|----------|-----------|
| **Web Framework** | FastAPI + Uvicorn |
| **Database** | MySQL 8.0 + SQLAlchemy ORM |
| **Vector DB** | FAISS |
| **Authentication** | JWT (python-jose, passlib, bcrypt) |
| **Validation** | Pydantic |
| **AI/ML** | OpenAI API |

---

## 🏗 프로젝트 구조

```
BE/
├── main.py                  # FastAPI 앱 진입점
├── app/
│   ├── core/                # 설정, 보안, 의존성
│   │   ├── config.py        # 환경 변수 관리
│   │   ├── deps.py          # 공통 의존성
│   │   └── security.py      # JWT, 비밀번호 해싱
│   ├── api/                 # API 엔드포인트
│   │   ├── auth.py          # 회원가입, 로그인
│   │   ├── user.py          # 프로필, 캐릭터 설정
│   │   ├── diary.py         # 감정 일기 CRUD
│   │   ├── chat.py          # AI 챗봇, 추천, 대화 CRUD
│   │   └── community.py     # 커뮤니티 게시판/댓글 CRUD
│   ├── crud/                # Database CRUD 로직
│   │   ├── user.py
│   │   ├── diary.py
│   │   ├── chat.py
│   │   └── community.py
│   ├── db/                  # Database 설정
│   │   ├── database.py      # DB 연결 및 세션
│   │   └── models.py        # SQLAlchemy 모델 (User, Diary, Chat, Message, Board, Comment, Likes)
│   └── schemas/             # Pydantic 스키마
│       ├── user.py
│       ├── diary.py
│       ├── chat.py
│       └── community.py
├── ai_core/                 # AI 핵심 기능
│   ├── llm.py               # OpenAI API
│   ├── vector_db.py         # FAISS 벡터 DB
│   └── recommendation.py    # RAG 기반 추천
├── prompt/
│   └── characters.py        # 캐릭터 프롬프트
├── data/                    # 추천 데이터
├── create_tables.py         # DB 테이블 생성
├── requirements.txt
└── .env
```

---

## ⚙️ 설치 및 실행

### 1. 가상환경 활성화
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 2. 패키지 설치
```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정
`.env` 파일을 생성하고 다음 내용을 설정:
```env
# MySQL Database
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=capstone
DB_USER=root
DB_PASSWORD=your_password

# JWT Configuration
JWT_SECRET_KEY=your-secret-key-min-32-characters
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=10080

# OpenAI API
OPENAI_API_KEY=your-openai-api-key
```

### 4. DB 테이블 생성
```bash
python create_tables.py
```

### 5. 서버 실행
```bash
uvicorn main:app --reload
```

**접속 URL:**
- API 서버: http://localhost:8000
- Swagger 문서: http://localhost:8000/docs
- ReDoc 문서: http://localhost:8000/redoc

---

## 📡 API 엔드포인트

### 인증 API
```
POST /auth/signup    - 회원가입
POST /auth/login     - 로그인 (JWT 토큰 반환)
```

### 사용자 프로필 API
```
GET   /user/profile     - 프로필 조회 (JWT 필수)
PATCH /user/profile     - 프로필 수정 (person_name, nick_name, email, phone, birth, gender)
PATCH /user/password    - 비밀번호 변경 (current_password, new_password)
PATCH /user/character   - 캐릭터 변경 (JWT 필수)
```

### 일기 API
```
POST   /diary/                        - 일기 작성 (emotion, recommend_content 선택적)
GET    /diary/list                    - 일기 목록 (페이징)
GET    /diary/calendar/{year}/{month} - 월별 일기
GET    /diary/by-date/{diary_date}    - 특정 날짜 일기
GET    /diary/{diary_id}              - 일기 상세 조회
PUT    /diary/{diary_id}              - 일기 수정
DELETE /diary/{diary_id}              - 일기 삭제
```

### 챗봇 대화 API
```
POST   /chat/start                  - 대화방 생성
GET    /chat/list                   - 대화 목록 (최근 활동순)
GET    /chat/{chat_id}              - 대화 상세 조회 (메시지 포함)
PATCH  /chat/{chat_id}/title        - 제목 수정
PATCH  /chat/{chat_id}/complete     - 대화 종료 (감정/추천 저장)
DELETE /chat/{chat_id}              - 대화 삭제
POST   /chat/{chat_id}/message      - 메시지 저장
```

### 챗봇 대화 API
```
POST   /chat/start                  - 대화방 생성
GET    /chat/list                   - 대화 목록 (최근 활동순)
GET    /chat/{chat_id}              - 대화 상세 조회 (메시지 포함)
PATCH  /chat/{chat_id}/title        - 제목 수정
PATCH  /chat/{chat_id}/complete     - 대화 종료 (감정/추천 저장)
DELETE /chat/{chat_id}              - 대화 삭제
POST   /chat/{chat_id}/message      - 메시지 저장
```

### AI API
```
POST /api/chat           - AI 챗봇 (감정 분석 + 공감 응답)
POST /api/recommend      - RAG 기반 추천
POST /api/analyze-diary  - 일기 감정 분석
```

### 커뮤니티 API
```
POST   /community/board                   - 게시글 작성
GET    /community/board/list              - 게시글 목록 (카테고리, 검색)
GET    /community/board/{board_id}        - 게시글 상세 (댓글 포함)
PUT    /community/board/{board_id}        - 게시글 수정
DELETE /community/board/{board_id}        - 게시글 삭제
POST   /community/board/{board_id}/like   - 게시글 좋아요 토글
POST   /community/comment                 - 댓글/대댓글 작성
PUT    /community/comment/{comment_id}    - 댓글 수정
DELETE /community/comment/{comment_id}    - 댓글 삭제
POST   /community/comment/{comment_id}/like - 댓글 좋아요 토글
```

---

## 💡 사용 예시

### 1. 회원가입
```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "test1234",
    "person_name": "홍길동",
    "nick_name": "길동이",
    "email": "test@example.com",
    "phone": "010-1234-5678",
    "birth": "1995-05-15",
    "gender": "male"
  }'
```

### 2. 로그인
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "test1234"
  }'
```

### 3. 캐릭터 설정
```bash
curl -X PATCH http://localhost:8000/user/character \
  -H "Authorization: Bearer {JWT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "character": "dog",
    "character_name": "뽀삐"
  }'
```

### 4. 일기 작성 (기본)
```bash
curl -X POST http://localhost:8000/diary/ \
  -H "Authorization: Bearer {JWT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "오늘의 일기",
    "content": "오늘은 정말 행복한 하루였다.",
    "diary_date": "2025-01-15"
  }'
```

### 4-1. 일기 작성 (AI 분석 결과 포함)
```bash
curl -X POST http://localhost:8000/diary/ \
  -H "Authorization: Bearer {JWT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "오늘의 일기",
    "content": "오늘은 정말 행복한 하루였다.",
    "diary_date": "2025-01-15",
    "emotion": "기쁨",
    "recommend_content": {
      "도서": [{"title": "행복한 책", "author": "작가"}],
      "음악": [{"title": "좋은 노래", "artist": "가수"}],
      "식사": [{"name": "맛있는 음식", "description": "설명"}]
    }
  }'
```

### 5. AI 챗봇
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "sentence": "오늘 너무 기분이 좋아!",
    "character": "강아지"
  }'
```

### 6. 챗봇 대화 저장
```bash
# 대화방 생성
curl -X POST http://localhost:8000/chat/start \
  -H "Authorization: Bearer {JWT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"title": "오늘의 대화"}'

# 메시지 저장 (캐릭터 정보는 User 테이블에서 자동 조회)
curl -X POST http://localhost:8000/chat/1/message \
  -H "Authorization: Bearer {JWT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "안녕?",
    "bot_response": "왈왈! 반가워!"
  }'

# 대화 목록 조회
curl -X GET http://localhost:8000/chat/list \
  -H "Authorization: Bearer {JWT_TOKEN}"

# 대화 상세 조회 (메시지 포함)
curl -X GET http://localhost:8000/chat/1 \
  -H "Authorization: Bearer {JWT_TOKEN}"
```

---

## 🐳 Docker 배포

### Docker Compose 실행
```bash
# 빌드 및 시작
docker-compose up -d --build

# 로그 확인
docker logs -f icsyf-be-server

# 테이블 생성
docker exec -it icsyf-be-server python create_tables.py

# 재시작
docker-compose restart

# 중지
docker-compose down
```

### 프로덕션 서버
- **API Base URL**: http://175.123.55.182:7777
- **API 문서**: http://175.123.55.182:7777/docs
- **MySQL 포트**: 7306

---

## 🎯 주요 특징

### 보안
- JWT 기반 인증
- bcrypt 비밀번호 암호화
- 본인 데이터만 접근 가능
- 환경 변수로 민감정보 관리

### 최적화
- DB 연결 풀 (pool_size=10, max_overflow=20)
- 중복 체크 쿼리 최적화 (3쿼리 → 1쿼리)
- 에러 처리 완비 (모든 API/CRUD)
- emotion 검증 (6가지 감정만 허용)
- recommend_content 검증 (3가지 카테고리만 허용)

### AI 통합
- OpenAI API 감정 분석
- FAISS 벡터 DB 활용
- RAG 기반 스마트 추천
- 캐릭터별 맞춤 응답

### 캐릭터 시스템
- 6가지 동물 캐릭터 (dog, cat, bear, rabbit, racoon, hamster)
- 영어-한글 자동 매핑
- 사용자별 캐릭터 저장 및 변경 가능
- 메시지 저장 시 User 테이블에서 캐릭터 정보 자동 조회
- 메시지별 캐릭터 정보 저장 (변경 이력 추적)

### 대화 이력 관리
- 대화방 단위 관리 (Chat ↔ Message 1:N 관계)
- 메시지 순서 보장 (message_order)
- 최근 활동순 정렬 (COALESCE 활용)
- Cascade 삭제 (대화 삭제 시 메시지 자동 삭제)
- 대화 종료 시 감정 분석 결과 저장

---

## 📝 개발 노트

### 핵심 감정 6가지
기쁨, 슬픔, 분노, 불안, 설렘, 무기력

### 데이터 구조
- **emotion**: 문자열 (단일 감정)
- **recommend_content**: JSON ({"도서": [...], "음악": [...], "식사": [...]})
- **Chat**: 대화방 (title, emotion, recommend_content, last_message_date)
- **Message**: 메시지 (user_message, bot_response, character, character_name, message_order)

### 코드 품질
- ✅ 모든 API에 예외 처리
- ✅ Pydantic 검증으로 입력값 안전성 확보
- ✅ 한글 에러 메시지
- ✅ RESTful API 설계

---

## 🔗 관련 링크

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [SQLAlchemy 공식 문서](https://docs.sqlalchemy.org/)
- [OpenAI API 문서](https://platform.openai.com/docs)

---

## 📄 License

This project is for educational purposes (Capstone Project).

---

## 👥 Team

**캡스톤 프로젝트 - ICSYF Team**
