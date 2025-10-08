from sqlalchemy import Column, Integer, String, DateTime, Enum, JSON
from sqlalchemy.sql import func
from app.db.database import Base
import enum

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"

class User(Base):
    __tablename__ = "User"

    # Primary Key
    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Login credentials
    username = Column(String(50), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)  # bcrypt hashed password

    # Personal information
    person_name = Column(String(50), nullable=False)
    nick_name = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=False)

    # Timestamps
    create_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    update_date = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Emotion data (JSON format for monthly summaries)
    emotion = Column(JSON, nullable=True)

    # Role
    role = Column(Enum(UserRole), default=UserRole.MEMBER, nullable=False)

    # Relationships will be added later
    # chatList - FK relationship to Chat table
    # diaryList - FK relationship to Diary table
