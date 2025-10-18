from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    애플리케이션 설정
    환경 변수를 자동으로 로드합니다 (.env 파일)
    """

    # Database Configuration
    DB_HOST: str = "127.0.0.1"
    DB_PORT: str = "3306"
    DB_NAME: str = "capstone"
    DB_USER: str = "root"
    DB_PASSWORD: str = ""

    # JWT Configuration
    JWT_SECRET_KEY: str = "your-secret-key-change-this-in-production-min-32-characters"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days (60*24*7)

    # OpenAI API Configuration
    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None

    # Database URL 생성
    @property
    def database_url(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"

    class Config:
        env_file = ".env"
        case_sensitive = True


# 전역 설정 인스턴스
settings = Settings()
