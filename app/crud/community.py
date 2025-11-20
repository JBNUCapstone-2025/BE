from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from app.db.models import Board, Comment, BoardLike, CommentLike, User, UserRole
from app.schemas.community import BoardCreateRequest, BoardUpdateRequest, CommentCreateRequest, CommentUpdateRequest
from fastapi import HTTPException
from typing import Optional, List


# ========== Board CRUD ==========

def create_board(db: Session, user_id: int, board_data: BoardCreateRequest) -> Board:
    """게시글 작성"""
    board = Board(
        user_id=user_id,
        category=board_data.category,
        title=board_data.title,
        content=board_data.content
    )
    db.add(board)
    db.commit()
    db.refresh(board)
    return board


def get_board_list(
    db: Session,
    category: str,
    search: Optional[str] = None
) -> List[Board]:
    """게시글 목록 조회 (카테고리별, 검색)"""
    query = db.query(Board).filter(Board.category == category)

    # 검색어가 있으면 제목+내용 검색
    if search and search.strip():
        if len(search.strip()) < 2:
            raise HTTPException(status_code=400, detail="검색어는 최소 2글자 이상이어야 합니다")
        query = query.filter(
            or_(
                Board.title.contains(search.strip()),
                Board.content.contains(search.strip())
            )
        )

    # 최신순 정렬
    boards = query.order_by(desc(Board.create_date)).all()
    return boards


def get_board_by_id(db: Session, board_id: int) -> Optional[Board]:
    """게시글 상세 조회"""
    return db.query(Board).filter(Board.board_id == board_id).first()


def update_board(
    db: Session,
    board_id: int,
    user_id: int,
    board_data: BoardUpdateRequest
) -> Board:
    """게시글 수정 (본인만)"""
    board = get_board_by_id(db, board_id)
    if not board:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다")

    # 본인 확인
    if board.user_id != user_id:
        raise HTTPException(status_code=403, detail="본인의 게시글만 수정할 수 있습니다")

    board.title = board_data.title
    board.content = board_data.content
    board.is_edited = True

    db.commit()
    db.refresh(board)
    return board


def delete_board(db: Session, board_id: int, user_id: int, user_role: str):
    """게시글 삭제 (본인 또는 관리자)"""
    board = get_board_by_id(db, board_id)
    if not board:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다")

    # 본인 또는 관리자만 삭제 가능
    if board.user_id != user_id and user_role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="본인의 게시글만 삭제할 수 있습니다")

    db.delete(board)
    db.commit()


# ========== Comment CRUD ==========

def create_comment(db: Session, user_id: int, comment_data: CommentCreateRequest) -> Comment:
    """댓글/대댓글 작성"""
    # 게시글 존재 확인
    board = get_board_by_id(db, comment_data.board_id)
    if not board:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다")

    # 대댓글인 경우 검증
    if comment_data.parent_comment_id:
        parent = db.query(Comment).filter(Comment.comment_id == comment_data.parent_comment_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="부모 댓글을 찾을 수 없습니다")

        # 대댓글에 답글 달기 방지
        if parent.parent_comment_id is not None:
            raise HTTPException(status_code=400, detail="대댓글에는 답글을 달 수 없습니다")

    comment = Comment(
        board_id=comment_data.board_id,
        user_id=user_id,
        parent_comment_id=comment_data.parent_comment_id,
        content=comment_data.content
    )
    db.add(comment)

    # 게시글 댓글 수 증가
    board.comment_count += 1

    db.commit()
    db.refresh(comment)
    return comment


def get_comment_by_id(db: Session, comment_id: int) -> Optional[Comment]:
    """댓글 조회"""
    return db.query(Comment).filter(Comment.comment_id == comment_id).first()


def update_comment(
    db: Session,
    comment_id: int,
    user_id: int,
    comment_data: CommentUpdateRequest
) -> Comment:
    """댓글 수정 (본인만)"""
    comment = get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다")

    # 본인 확인
    if comment.user_id != user_id:
        raise HTTPException(status_code=403, detail="본인의 댓글만 수정할 수 있습니다")

    comment.content = comment_data.content
    comment.is_edited = True

    db.commit()
    db.refresh(comment)
    return comment


def delete_comment(db: Session, comment_id: int, user_id: int, user_role: str):
    """댓글 삭제 (본인 또는 관리자, CASCADE로 대댓글도 삭제)"""
    comment = get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다")

    # 본인 또는 관리자만 삭제 가능
    if comment.user_id != user_id and user_role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="본인의 댓글만 삭제할 수 있습니다")

    # 게시글 댓글 수 감소 (댓글 + 대댓글 모두 카운트)
    board = get_board_by_id(db, comment.board_id)
    if board:
        # 삭제할 댓글과 모든 대댓글 개수 계산
        reply_count = db.query(Comment).filter(Comment.parent_comment_id == comment_id).count()
        board.comment_count = max(0, board.comment_count - (1 + reply_count))

    db.delete(comment)
    db.commit()


# ========== Like 기능 ==========

def toggle_board_like(db: Session, board_id: int, user_id: int) -> dict:
    """게시글 좋아요 토글"""
    board = get_board_by_id(db, board_id)
    if not board:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다")

    # 기존 좋아요 확인
    existing_like = db.query(BoardLike).filter(
        BoardLike.board_id == board_id,
        BoardLike.user_id == user_id
    ).first()

    if existing_like:
        # 좋아요 취소
        db.delete(existing_like)
        board.likes_count = max(0, board.likes_count - 1)
        is_liked = False
    else:
        # 좋아요 추가
        new_like = BoardLike(board_id=board_id, user_id=user_id)
        db.add(new_like)
        board.likes_count += 1
        is_liked = True

    db.commit()
    db.refresh(board)

    return {
        "is_liked": is_liked,
        "likes_count": board.likes_count
    }


def toggle_comment_like(db: Session, comment_id: int, user_id: int) -> dict:
    """댓글 좋아요 토글"""
    comment = get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다")

    # 기존 좋아요 확인
    existing_like = db.query(CommentLike).filter(
        CommentLike.comment_id == comment_id,
        CommentLike.user_id == user_id
    ).first()

    if existing_like:
        # 좋아요 취소
        db.delete(existing_like)
        comment.likes_count = max(0, comment.likes_count - 1)
        is_liked = False
    else:
        # 좋아요 추가
        new_like = CommentLike(comment_id=comment_id, user_id=user_id)
        db.add(new_like)
        comment.likes_count += 1
        is_liked = True

    db.commit()
    db.refresh(comment)

    return {
        "is_liked": is_liked,
        "likes_count": comment.likes_count
    }


# ========== Helper 함수 ==========

def check_board_liked(db: Session, board_id: int, user_id: int) -> bool:
    """사용자가 게시글에 좋아요 눌렀는지 확인"""
    return db.query(BoardLike).filter(
        BoardLike.board_id == board_id,
        BoardLike.user_id == user_id
    ).first() is not None


def check_comment_liked(db: Session, comment_id: int, user_id: int) -> bool:
    """사용자가 댓글에 좋아요 눌렀는지 확인"""
    return db.query(CommentLike).filter(
        CommentLike.comment_id == comment_id,
        CommentLike.user_id == user_id
    ).first() is not None
