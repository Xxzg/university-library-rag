"""会话历史路由：创建 / 列表 / 详情（恢复上下文）/ 重命名 / 删除。全部按用户隔离。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import ChatSession, Message, User
from app.schemas import (
    MessageOut,
    SessionCreateIn,
    SessionDetailOut,
    SessionOut,
    SessionRenameIn,
)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _get_owned_session(session_id: int, user: User, db: Session) -> ChatSession:
    s = db.get(ChatSession, session_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")
    return s


@router.post("", response_model=SessionOut, status_code=201)
def create_session(
    body: SessionCreateIn | None = None,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    title = body.title if body and body.title else "新对话"
    s = ChatSession(user_id=current.id, title=title)
    db.add(s)
    db.commit()
    db.refresh(s)
    return SessionOut(
        id=s.id, title=s.title,
        created_at=s.created_at, updated_at=s.updated_at, message_count=0,
    )


@router.get("", response_model=list[SessionOut])
def list_sessions(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    out = []
    for s in sessions:
        out.append(
            SessionOut(
                id=s.id, title=s.title,
                created_at=s.created_at, updated_at=s.updated_at,
                message_count=len(s.messages),
            )
        )
    return out


@router.get("/{session_id}", response_model=SessionDetailOut)
def get_session_detail(
    session_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = _get_owned_session(session_id, current, db)
    return SessionDetailOut(
        id=s.id, title=s.title,
        created_at=s.created_at, updated_at=s.updated_at,
        message_count=len(s.messages),
        messages=[MessageOut.model_validate(m) for m in s.messages],
    )


@router.put("/{session_id}", response_model=SessionOut)
def rename_session(
    session_id: int,
    body: SessionRenameIn,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = _get_owned_session(session_id, current, db)
    s.title = body.title
    db.commit()
    db.refresh(s)
    return SessionOut(
        id=s.id, title=s.title,
        created_at=s.created_at, updated_at=s.updated_at,
        message_count=len(s.messages),
    )


@router.delete("/{session_id}", status_code=204)
def delete_session(
    session_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = _get_owned_session(session_id, current, db)
    db.delete(s)
    db.commit()
