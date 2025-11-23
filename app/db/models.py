from sqlalchemy import Column, Integer, String, DateTime, Enum, JSON, Text, Date, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"

class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"

class User(Base):
    __tablename__ = "User"

    # 기본 키
    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 로그인 정보
    username = Column(String(50), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)  # bcrypt 해싱된 비밀번호

    # 개인 정보
    person_name = Column(String(50), nullable=False)
    nick_name = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    birth = Column(Date, nullable=False)
    gender = Column(Enum(Gender), nullable=False)

    # 타임스탬프
    create_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    update_date = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 감정 데이터 (월별 결산용 JSON 형식)
    emotion = Column(JSON, nullable=True)

    # 선택한 캐릭터 (강아지, 고양이, 곰, 너구리, 토끼, 햄스터, 여우)
    character = Column(String(20), nullable=True)
    character_name = Column(String(20), nullable=True)  # 사용자가 캐릭터에게 붙이는 이름

    # 권한
    role = Column(Enum(UserRole), default=UserRole.MEMBER, nullable=False)

    # 챌린지 관련 필드
    mileage = Column(Integer, default=0, nullable=False)  # 마일리지
    current_continent_id = Column(Integer, nullable=True)  # 현재 진행 중인 대륙 (NULL이면 미시작)
    challenge_start_date = Column(DateTime(timezone=True), nullable=True)  # 챌린지 시작일 (3개월 리셋용)
    available_challenges = Column(Integer, default=0, nullable=False)  # 사용 가능한 챌린지 횟수
    last_challenge_date = Column(Date, nullable=True)  # 마지막 챌린지 수행 날짜
    last_diary_date = Column(Date, nullable=True)  # 마지막 일기 작성 날짜 (챌린지 기회 리셋용)

    # 관계 설정
    diaries = relationship("Diary", back_populates="user", cascade="all, delete-orphan")
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    boards = relationship("Board", back_populates="user", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="user", cascade="all, delete-orphan")
    board_likes = relationship("BoardLike", back_populates="user", cascade="all, delete-orphan")
    comment_likes = relationship("CommentLike", back_populates="user", cascade="all, delete-orphan")
    challenges = relationship("Challenge", back_populates="user", cascade="all, delete-orphan")


class Diary(Base):
    __tablename__ = "Diary"

    # 기본 키
    diary_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 외래 키
    user_id = Column(Integer, ForeignKey("User.user_id"), nullable=False, index=True)

    # 일기 내용
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)

    # AI 분석 결과 (AI API 연동 전까지 null)
    emotion = Column(String(20), nullable=True)  # "기쁨", "슬픔", "분노", "불안", "설렘", "무기력"
    recommend_content = Column(JSON, nullable=True)  # {"book": "제목"} or {"music": "제목"} or {"food": "제목"} (1개만)

    # 일기 날짜 (달력 표시용)
    diary_date = Column(Date, nullable=False, index=True)

    # 타임스탬프
    create_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    update_date = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 관계 설정
    user = relationship("User", back_populates="diaries")


class Chat(Base):
    __tablename__ = "Chat"

    # 기본 키
    chat_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 외래 키
    user_id = Column(Integer, ForeignKey("User.user_id"), nullable=False, index=True)

    # 대화 정보
    title = Column(String(200), nullable=False, default="새 대화")

    # AI 분석 결과 (대화 종료 시 저장)
    emotion = Column(String(20), nullable=True)  # "기쁨", "슬픔", "분노", "불안", "설렘", "무기력"
    recommend_content = Column(JSON, nullable=True)  # {"book": "제목"} or {"music": "제목"} or {"food": "제목"} (1개만)

    # 최근 대화순 정렬용
    last_message_date = Column(DateTime(timezone=True), nullable=True, index=True)

    # 타임스탬프
    create_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # 관계 설정
    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan", order_by="Message.message_order")


class Message(Base):
    __tablename__ = "Message"

    # 기본 키
    message_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 외래 키
    chat_id = Column(Integer, ForeignKey("Chat.chat_id"), nullable=False, index=True)

    # 메시지 내용
    user_message = Column(Text, nullable=False)
    bot_response = Column(Text, nullable=False)

    # 캐릭터 정보 (메시지 전송 당시의 캐릭터)
    character = Column(String(20), nullable=False)  # dog, cat, bear, rabbit, racoon, hamster
    character_name = Column(String(20), nullable=False)  # 사용자가 캐릭터에게 붙인 이름

    # 메시지 순서
    message_order = Column(Integer, nullable=False)

    # 타임스탬프
    create_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # 관계 설정
    chat = relationship("Chat", back_populates="messages")


class Board(Base):
    __tablename__ = "Board"

    # 기본 키
    board_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 외래 키
    user_id = Column(Integer, ForeignKey("User.user_id", ondelete="CASCADE"), nullable=False, index=True)

    # 게시글 정보
    category = Column(String(20), nullable=False, index=True)
    title = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)

    # 캐싱 필드
    likes_count = Column(Integer, default=0, nullable=False)
    comment_count = Column(Integer, default=0, nullable=False)

    # 수정 여부
    is_edited = Column(Boolean, default=False, nullable=False)

    # 타임스탬프
    create_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    update_date = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 관계 설정
    user = relationship("User", back_populates="boards")
    comments = relationship("Comment", back_populates="board", cascade="all, delete-orphan")
    likes = relationship("BoardLike", back_populates="board", cascade="all, delete-orphan")


class Comment(Base):
    __tablename__ = "Comment"

    # 기본 키
    comment_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 외래 키
    board_id = Column(Integer, ForeignKey("Board.board_id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("User.user_id", ondelete="CASCADE"), nullable=False, index=True)
    parent_comment_id = Column(Integer, ForeignKey("Comment.comment_id", ondelete="CASCADE"), nullable=True, index=True)

    # 댓글 내용
    content = Column(Text, nullable=False)

    # 캐싱 필드
    likes_count = Column(Integer, default=0, nullable=False)

    # 수정 여부
    is_edited = Column(Boolean, default=False, nullable=False)

    # 타임스탬프
    create_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    update_date = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 관계 설정
    user = relationship("User", back_populates="comments")
    board = relationship("Board", back_populates="comments")
    parent = relationship("Comment", remote_side=[comment_id], backref="replies")
    likes = relationship("CommentLike", back_populates="comment", cascade="all, delete-orphan")


class BoardLike(Base):
    __tablename__ = "BoardLike"

    # 기본 키
    like_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 외래 키
    board_id = Column(Integer, ForeignKey("Board.board_id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("User.user_id"), nullable=False, index=True)

    # 타임스탬프
    create_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # 관계 설정
    user = relationship("User", back_populates="board_likes")
    board = relationship("Board", back_populates="likes")

    # UNIQUE 제약 (중복 좋아요 방지)
    __table_args__ = (
        UniqueConstraint('board_id', 'user_id', name='uq_board_like'),
    )


class CommentLike(Base):
    __tablename__ = "CommentLike"

    # 기본 키
    like_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 외래 키
    comment_id = Column(Integer, ForeignKey("Comment.comment_id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("User.user_id"), nullable=False, index=True)

    # 타임스탬프
    create_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # 관계 설정
    user = relationship("User", back_populates="comment_likes")
    comment = relationship("Comment", back_populates="likes")

    # UNIQUE 제약 (중복 좋아요 방지)
    __table_args__ = (
        UniqueConstraint('comment_id', 'user_id', name='uq_comment_like'),
    )


class Continent(Base):
    __tablename__ = "Continent"

    # 기본 키
    continent_id = Column(Integer, primary_key=True)  # 1~6 고정

    # 대륙 정보
    continent_name = Column(String(50), nullable=False)  # 아시아, 유럽, 아프리카 등
    display_order = Column(Integer, nullable=False)  # 화면 표시 순서

    # 관계 설정
    challenges = relationship("Challenge", back_populates="continent")


class Challenge(Base):
    __tablename__ = "Challenge"

    # 기본 키
    challenge_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 외래 키
    user_id = Column(Integer, ForeignKey("User.user_id", ondelete="CASCADE"), nullable=False, index=True)
    continent_id = Column(Integer, ForeignKey("Continent.continent_id"), nullable=False, index=True)

    # 챌린지 정보
    challenge_number = Column(Integer, nullable=False)  # 이 대륙에서 몇 번째 챌린지인지 (1~10)
    challenge_type = Column(String(20), nullable=False)  # basic, book, music, food
    challenge_text = Column(Text, nullable=False)  # 실제 챌린지 내용
    source_diary_date = Column(Date, nullable=True)  # 챌린지 생성 시 기준이 된 일기의 날짜 (재선택 시 동일 일기 기준 유지용)

    # 사용자 제출 내용
    content = Column(Text, nullable=True)  # 사용자가 작성한 내용

    # 완료 상태
    is_completed = Column(Boolean, default=False, nullable=False)
    completed_date = Column(Date, nullable=True)

    # 타임스탬프
    create_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # 관계 설정
    user = relationship("User", back_populates="challenges")
    continent = relationship("Continent", back_populates="challenges")

    # UNIQUE 제약 (한 대륙에서 같은 번호 중복 방지)
    __table_args__ = (
        UniqueConstraint('user_id', 'continent_id', 'challenge_number', name='uq_user_continent_challenge'),
    )
