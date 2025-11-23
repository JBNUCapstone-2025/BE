# ICSYF Backend 프로젝트 구조

## 현재 폴더 구조

```
BE/
├── main.py                    # FastAPI 메인 애플리케이션
├── create_tables.py           # DB 테이블 생성 스크립트
├── requirements.txt           # Python 의존성
├── .env                       # 환경 변수
├── README.md                  # 프로젝트 문서
├── CLAUDE.md                  # 개발 가이드 (상세)
├── STRUCTURE.md               # 이 파일
│
├── app/                       # Backend 애플리케이션
│   ├── core/                  # 설정, 보안, 의존성
│   │   ├── config.py          # 환경 변수 관리
│   │   ├── deps.py            # 공통 의존성 (get_db, get_current_user_id)
│   │   ├── security.py        # JWT, 비밀번호 해싱
│   │   └── constants.py       # 챌린지 풀, 대륙 정보
│   │
│   ├── api/                   # API 라우터
│   │   ├── auth.py            # 회원가입, 로그인
│   │   ├── user.py            # 프로필, 캐릭터 설정
│   │   ├── diary.py           # 감정 일기 CRUD
│   │   ├── chat.py            # AI 챗봇, 추천, 대화 CRUD
│   │   ├── community.py       # 커뮤니티 게시판/댓글 CRUD
│   │   └── challenge.py       # 챌린지 시스템 API
│   │
│   ├── crud/                  # Database CRUD 로직
│   │   ├── user.py            # 사용자 CRUD
│   │   ├── diary.py           # 일기 CRUD
│   │   ├── chat.py            # 대화/메시지 CRUD
│   │   ├── community.py       # 게시판/댓글 CRUD
│   │   └── challenge.py       # 챌린지 선택/완료/리셋 로직
│   │
│   ├── db/                    # 데이터베이스
│   │   ├── database.py        # DB 연결 및 세션
│   │   └── models.py          # SQLAlchemy 모델 (User, Diary, Chat, Board, Challenge 등)
│   │
│   └── schemas/               # Pydantic 스키마
│       ├── user.py            # 사용자 요청/응답 스키마
│       ├── diary.py           # 일기 요청/응답 스키마
│       ├── chat.py            # 대화 요청/응답 스키마
│       ├── community.py       # 커뮤니티 요청/응답 스키마
│       └── challenge.py       # 챌린지 요청/응답 스키마
│
├── ai_core/                   # AI 핵심 기능
│   ├── llm/                   # 언어 모델
│   │   ├── __init__.py
│   │   └── llm_utils.py       # OpenAI API 감정 분석, 응답 생성
│   │
│   ├── recommendation/        # 추천 시스템
│   │   ├── __init__.py
│   │   ├── content_recommender.py    # 스마트 추천
│   │   └── rag_recommender.py        # RAG 기반 추천
│   │
│   └── vector_db/             # 벡터 데이터베이스
│       ├── __init__.py
│       └── vector_db.py       # FAISS 벡터 검색
│
├── data/                      # 데이터 파일
│   ├── recommendation_data.py # 추천 데이터
│   ├── emotion_data.pkl       # 감정 벡터
│   └── vector_db.faiss        # FAISS 인덱스
│
└── prompt/                    # 프롬프트 템플릿
    ├── __init__.py
    └── characters.py          # 캐릭터 정의 (6가지 동물 캐릭터)
```

## 주요 모듈 설명

### app/core/ - 핵심 설정
- **config.py**: 환경 변수 관리 (DB, JWT, OpenAI API)
- **deps.py**: 공통 의존성 주입 (get_db, get_current_user_id)
- **security.py**: JWT 토큰 생성/검증, 비밀번호 해싱
- **constants.py**: 챌린지 풀, 대륙 정보, 설정값

### app/api/ - API 엔드포인트 (7개 라우터)
- **auth.py**: 회원가입, 로그인, 로그아웃
- **user.py**: 프로필 조회/수정, 비밀번호 변경, 캐릭터 설정
- **diary.py**: 일기 CRUD (7개 엔드포인트)
- **chat.py**: AI 챗봇, 추천, 대화 CRUD (10개 엔드포인트)
- **community.py**: 게시판/댓글 CRUD, 좋아요 (9개 엔드포인트)
- **challenge.py**: 챌린지 시스템 (7개 엔드포인트)

### app/crud/ - Database 로직
- **user.py**: 사용자 생성, 조회, 수정
- **diary.py**: 일기 CRUD 로직
- **chat.py**: 대화방/메시지 CRUD 로직
- **community.py**: 게시판/댓글 CRUD, 익명 번호 부여
- **challenge.py**: 챌린지 선택/완료, 마일리지 지급, 리셋 로직

### app/db/ - 데이터베이스
- **database.py**: MySQL 연결 풀, 세션 관리
- **models.py**: 10개 테이블 (User, Diary, Chat, Message, Board, Comment, BoardLike, CommentLike, Continent, Challenge)

### app/schemas/ - Pydantic 검증
- 요청/응답 스키마 정의
- 입력값 검증 (감정 6가지, 카테고리 등)

### ai_core/ - AI 핵심 기능
- **llm/**: OpenAI API 감정 분석, 공감 응답 생성
- **vector_db/**: FAISS 벡터 검색 (반대 감정 찾기)
- **recommendation/**: RAG 기반 추천 (도서, 음악, 식사)

## 데이터베이스 테이블 (10개)

1. **User**: 사용자 정보, 캐릭터, 챌린지 필드
2. **Diary**: 일기, AI 감정 분석 결과, 추천 콘텐츠
3. **Chat**: 대화방, 감정 분석 결과
4. **Message**: 메시지 이력, 캐릭터 변경 추적
5. **Board**: 게시글 (6개 카테고리)
6. **Comment**: 댓글/대댓글 (2단계)
7. **BoardLike**: 게시글 좋아요
8. **CommentLike**: 댓글 좋아요
9. **Continent**: 6개 대륙 정보
10. **Challenge**: 사용자별 챌린지 (60개)

## 주요 특징

### 1. 계층화된 구조
- **app/core/**: 설정, 보안, 공통 로직
- **app/api/**: FastAPI 라우터 (비즈니스 로직 최소화)
- **app/crud/**: 순수 DB CRUD 로직
- **app/schemas/**: Pydantic 검증

### 2. AI 모듈 분리
- **ai_core/**: AI 기능만 독립적으로 관리
- 패키지 구조로 명확한 의존성
- 테스트 및 확장 용이

### 3. 보안 및 최적화
- JWT 기반 인증
- bcrypt 비밀번호 암호화
- DB 연결 풀 (pool_size=10)
- N+1 쿼리 최적화

## Import 경로 예시

```python
# API에서 CRUD 호출
from app.crud import diary as crud_diary
from app.schemas.diary import DiaryCreateRequest
from app.core.deps import get_db, get_current_user_id

# AI 기능 사용
from ai_core.llm import extract_emotion
from ai_core.vector_db import find_dissimilar_emotion_key
from ai_core.recommendation import get_smart_recommendation

# 데이터 파일 참조
from data.recommendation_data import RECOMMENDATIONS
```

## 개발 가이드

자세한 개발 가이드는 **CLAUDE.md** 참고
- API 엔드포인트 전체 목록
- 테스트 예시 (curl)
- 주요 로직 설명
- 최적화 방법
