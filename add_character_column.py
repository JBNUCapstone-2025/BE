"""
Add character column to User table
"""
from sqlalchemy import text
from app.db.database import engine

def add_character_column():
    """User 테이블에 character 컬럼 추가"""
    with engine.connect() as conn:
        try:
            # character 컬럼 추가
            conn.execute(text(
                "ALTER TABLE User ADD COLUMN `character` VARCHAR(20) NULL AFTER emotion"
            ))
            conn.commit()
            print("character 컬럼이 성공적으로 추가되었습니다!")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("character 컬럼이 이미 존재합니다.")
            else:
                print(f"에러 발생: {e}")

if __name__ == "__main__":
    add_character_column()
