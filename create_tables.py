"""
데이터베이스 테이블 생성 스크립트
"""
from app.db.database import init_db

if __name__ == "__main__":
    print("Creating database tables...")
    init_db()
    print("✅ Tables created successfully!")
