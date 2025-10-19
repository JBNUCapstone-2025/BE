from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from app.core.config import settings

# 데이터베이스 엔진 생성
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # 연결 재사용 전 ping 테스트
    pool_recycle=settings.DB_POOL_RECYCLE,  # 연결 재활용 시간 (초)
    pool_size=settings.DB_POOL_SIZE,  # 기본 연결 풀 크기
    max_overflow=settings.DB_MAX_OVERFLOW,  # 추가 가능한 최대 연결 수
    echo=not settings.is_production  # 개발 환경에서만 SQL 로그 출력
)

# 세션 팩토리 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 모델 베이스 클래스
Base = declarative_base()


# 모든 테이블 생성
def init_db():
    """데이터베이스 테이블 초기화"""
    from app.db import models  # models를 import해서 User, Diary 등록
    Base.metadata.create_all(bind=engine)
