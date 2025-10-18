from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from app.core.config import settings

# 데이터베이스 엔진 생성
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=True  # 프로덕션 환경에서는 False로 설정
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
