"""
데이터베이스 테이블 생성 스크립트
"""
from app.db.database import init_db, SessionLocal
from app.db.models import Continent
from app.core.constants import CONTINENTS

if __name__ == "__main__":
    print("데이터베이스 테이블 생성 중...")
    init_db()
    print("[완료] 테이블이 성공적으로 생성되었습니다!")

    # Continent 테이블 초기 데이터 삽입
    print("\n대륙 데이터 삽입 중...")
    db = SessionLocal()
    try:
        # 이미 데이터가 있는지 확인
        existing_count = db.query(Continent).count()
        if existing_count == 0:
            for continent_id, continent_name, display_order in CONTINENTS:
                continent = Continent(
                    continent_id=continent_id,
                    continent_name=continent_name,
                    display_order=display_order
                )
                db.add(continent)
            db.commit()
            print("[완료] 대륙 데이터가 성공적으로 삽입되었습니다!")
        else:
            print(f"[주의] 대륙 데이터가 이미 존재합니다 ({existing_count}개). 건너뜁니다...")
    except Exception as e:
        print(f"[오류] 대륙 데이터 삽입 중 오류 발생: {e}")
        db.rollback()
    finally:
        db.close()
