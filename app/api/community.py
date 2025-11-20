from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.deps import get_db, get_current_user_id
from app.db.models import User, Comment, UserRole, BoardLike, CommentLike
from app.crud import community as crud
from app.schemas.community import (
    BoardCreateRequest,
    BoardUpdateRequest,
    BoardListItemResponse,
    BoardDetailResponse,
    CommentCreateRequest,
    CommentUpdateRequest,
    CommentResponse,
    LikeResponse
)

router = APIRouter(prefix="/community", tags=["Community"])


# ========== 익명 번호 처리 Helper ==========

def assign_anonymous_numbers(comments: List[Comment], board_author_id: int) -> dict:
    """댓글 작성자들에게 익명 번호 부여 (등장 순서대로)"""
    user_id_to_number = {}
    counter = 1

    for comment in comments:
        if comment.user_id not in user_id_to_number:
            user_id_to_number[comment.user_id] = counter
            counter += 1

    return user_id_to_number


def build_comment_response(
    comment: Comment,
    current_user_id: int,
    board_author_id: int,
    anonymous_map: dict
) -> CommentResponse:
    """Comment 객체를 CommentResponse로 변환 (대댓글 재귀 처리)"""
    # 대댓글 처리
    replies_response = []
    if hasattr(comment, 'replies'):
        for reply in comment.replies:
            replies_response.append(
                build_comment_response(reply, current_user_id, board_author_id, anonymous_map)
            )

    return CommentResponse(
        comment_id=comment.comment_id,
        content=comment.content,
        anonymous_number=anonymous_map.get(comment.user_id, 0),
        is_author=(comment.user_id == board_author_id),
        is_mine=(comment.user_id == current_user_id),
        is_liked=crud.check_comment_liked(comment.board.query.session, comment.comment_id, current_user_id),
        is_edited=comment.is_edited,
        likes_count=comment.likes_count,
        create_date=comment.create_date,
        replies=replies_response
    )


# ========== Board APIs ==========

@router.post("/board", response_model=BoardDetailResponse)
def create_board(
    board_data: BoardCreateRequest,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """게시글 작성"""
    try:
        board = crud.create_board(db, current_user_id, board_data)

        return BoardDetailResponse(
            board_id=board.board_id,
            category=board.category,
            title=board.title,
            content=board.content,
            likes_count=board.likes_count,
            comment_count=board.comment_count,
            is_liked=False,
            is_mine=True,
            is_edited=board.is_edited,
            create_date=board.create_date,
            comments=[]
        )
    except Exception:
        raise HTTPException(status_code=500, detail="게시글 작성에 실패했습니다")


@router.get("/board/list", response_model=List[BoardListItemResponse])
def get_board_list(
    category: str = Query(..., description="게시판 카테고리 (free, secret, info, praise, comfort, worry)"),
    search: Optional[str] = Query(None, description="검색어 (최소 2글자)"),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """게시글 목록 조회 (카테고리별, 검색)"""
    try:
        boards = crud.get_board_list(db, category, search)

        # 모든 게시글 ID 수집
        board_ids = [b.board_id for b in boards]

        # 한 번에 좋아요 조회 (최적화)
        liked_board_ids = db.query(BoardLike.board_id).filter(
            BoardLike.board_id.in_(board_ids),
            BoardLike.user_id == current_user_id
        ).all()
        liked_set = set([like_id[0] for like_id in liked_board_ids])

        result = []
        for board in boards:
            result.append(BoardListItemResponse(
                board_id=board.board_id,
                category=board.category,
                title=board.title,
                content_preview=board.content[:20],  # 20자 미리보기
                likes_count=board.likes_count,
                comment_count=board.comment_count,
                is_liked=(board.board_id in liked_set),
                is_mine=(board.user_id == current_user_id),
                is_edited=board.is_edited,
                create_date=board.create_date
            ))

        return result
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="게시글 목록 조회에 실패했습니다")


@router.get("/board/{board_id}", response_model=BoardDetailResponse)
def get_board_detail(
    board_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """게시글 상세 조회 (댓글 포함)"""
    try:
        board = crud.get_board_by_id(db, board_id)
        if not board:
            raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다")

        # 댓글만 조회 (대댓글 제외)
        top_level_comments = [c for c in board.comments if c.parent_comment_id is None]

        # 전체 댓글 리스트 (대댓글 포함)
        all_comments = board.comments

        # 익명 번호 매핑
        anonymous_map = assign_anonymous_numbers(all_comments, board.user_id)

        # 모든 댓글 ID 수집
        all_comment_ids = [c.comment_id for c in all_comments]

        # 한 번에 좋아요 조회 (최적화)
        liked_comment_ids = db.query(CommentLike.comment_id).filter(
            CommentLike.comment_id.in_(all_comment_ids),
            CommentLike.user_id == current_user_id
        ).all()
        liked_set = set([like_id[0] for like_id in liked_comment_ids])

        # 댓글 응답 생성
        comments_response = []
        for comment in sorted(top_level_comments, key=lambda x: x.create_date, reverse=True):
            comments_response.append(
                CommentResponse(
                    comment_id=comment.comment_id,
                    content=comment.content,
                    anonymous_number=anonymous_map.get(comment.user_id, 0),
                    is_author=(comment.user_id == board.user_id),
                    is_mine=(comment.user_id == current_user_id),
                    is_liked=(comment.comment_id in liked_set),
                    is_edited=comment.is_edited,
                    likes_count=comment.likes_count,
                    create_date=comment.create_date,
                    replies=[
                        CommentResponse(
                            comment_id=reply.comment_id,
                            content=reply.content,
                            anonymous_number=anonymous_map.get(reply.user_id, 0),
                            is_author=(reply.user_id == board.user_id),
                            is_mine=(reply.user_id == current_user_id),
                            is_liked=(reply.comment_id in liked_set),
                            is_edited=reply.is_edited,
                            likes_count=reply.likes_count,
                            create_date=reply.create_date,
                            replies=[]
                        )
                        for reply in sorted(comment.replies, key=lambda x: x.create_date, reverse=True)
                    ]
                )
            )

        return BoardDetailResponse(
            board_id=board.board_id,
            category=board.category,
            title=board.title,
            content=board.content,
            likes_count=board.likes_count,
            comment_count=board.comment_count,
            is_liked=crud.check_board_liked(db, board.board_id, current_user_id),
            is_mine=(board.user_id == current_user_id),
            is_edited=board.is_edited,
            create_date=board.create_date,
            comments=comments_response
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="게시글 조회에 실패했습니다")


@router.put("/board/{board_id}", response_model=BoardDetailResponse)
def update_board(
    board_id: int,
    board_data: BoardUpdateRequest,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """게시글 수정 (본인만)"""
    try:
        board = crud.update_board(db, board_id, current_user_id, board_data)

        return BoardDetailResponse(
            board_id=board.board_id,
            category=board.category,
            title=board.title,
            content=board.content,
            likes_count=board.likes_count,
            comment_count=board.comment_count,
            is_liked=crud.check_board_liked(db, board.board_id, current_user_id),
            is_mine=True,
            is_edited=board.is_edited,
            create_date=board.create_date,
            comments=[]
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="게시글 수정에 실패했습니다")


@router.delete("/board/{board_id}")
def delete_board(
    board_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """게시글 삭제 (본인 또는 관리자)"""
    try:
        # 사용자 role 조회
        user = db.query(User).filter(User.user_id == current_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")

        crud.delete_board(db, board_id, current_user_id, user.role)
        return {"message": "게시글이 삭제되었습니다"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="게시글 삭제에 실패했습니다")


@router.post("/board/{board_id}/like", response_model=LikeResponse)
def toggle_board_like(
    board_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """게시글 좋아요 토글"""
    try:
        result = crud.toggle_board_like(db, board_id, current_user_id)
        return LikeResponse(**result)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="좋아요 처리에 실패했습니다")


# ========== Comment APIs ==========

@router.post("/comment", response_model=CommentResponse)
def create_comment(
    comment_data: CommentCreateRequest,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """댓글/대댓글 작성"""
    try:
        comment = crud.create_comment(db, current_user_id, comment_data)

        # 게시글 작성자 조회
        board = crud.get_board_by_id(db, comment.board_id)

        # 전체 댓글 조회하여 정확한 익명 번호 계산
        all_comments = board.comments
        anonymous_map = assign_anonymous_numbers(all_comments, board.user_id)

        return CommentResponse(
            comment_id=comment.comment_id,
            content=comment.content,
            anonymous_number=anonymous_map.get(comment.user_id, 0),  # 정확한 익명 번호
            is_author=(comment.user_id == board.user_id),
            is_mine=True,
            is_liked=False,
            is_edited=comment.is_edited,
            likes_count=comment.likes_count,
            create_date=comment.create_date,
            replies=[]
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="댓글 작성에 실패했습니다")


@router.put("/comment/{comment_id}", response_model=CommentResponse)
def update_comment(
    comment_id: int,
    comment_data: CommentUpdateRequest,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """댓글 수정 (본인만)"""
    try:
        comment = crud.update_comment(db, comment_id, current_user_id, comment_data)

        # 게시글 작성자 조회
        board = crud.get_board_by_id(db, comment.board_id)

        # 전체 댓글 조회하여 정확한 익명 번호 계산
        all_comments = board.comments
        anonymous_map = assign_anonymous_numbers(all_comments, board.user_id)

        return CommentResponse(
            comment_id=comment.comment_id,
            content=comment.content,
            anonymous_number=anonymous_map.get(comment.user_id, 0),  # 정확한 익명 번호
            is_author=(comment.user_id == board.user_id),
            is_mine=True,
            is_liked=crud.check_comment_liked(db, comment.comment_id, current_user_id),
            is_edited=comment.is_edited,
            likes_count=comment.likes_count,
            create_date=comment.create_date,
            replies=[]
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="댓글 수정에 실패했습니다")


@router.delete("/comment/{comment_id}")
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """댓글 삭제 (본인 또는 관리자)"""
    try:
        # 사용자 role 조회
        user = db.query(User).filter(User.user_id == current_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")

        crud.delete_comment(db, comment_id, current_user_id, user.role)
        return {"message": "댓글이 삭제되었습니다"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="댓글 삭제에 실패했습니다")


@router.post("/comment/{comment_id}/like", response_model=LikeResponse)
def toggle_comment_like(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """댓글 좋아요 토글"""
    try:
        result = crud.toggle_comment_like(db, comment_id, current_user_id)
        return LikeResponse(**result)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="좋아요 처리에 실패했습니다")
