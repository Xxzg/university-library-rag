"""ORM 数据模型：用户 / 文献 / 会话 / 消息。"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def now_local() -> datetime:
    """本地时间（服务器时区，北京 UTC+8）。存 SQLite 为 naive datetime，
    前端 new Date() 按本地时区解析显示正确，避免 UTC→本地转换的 8 小时偏差。"""
    return datetime.now()


class User(Base):
    """系统用户。role: student=学生 / teacher=教师 / admin=管理员"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(16), default="student", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_local)

    sessions: Mapped[list["ChatSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Document(Base):
    """馆藏文献。status: pending=待处理 / processing=处理中 / done=已入库 / failed=失败"""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(256), index=True)
    filename: Mapped[str] = mapped_column(String(256))
    file_type: Mapped[str] = mapped_column(String(16))  # pdf/docx/txt/md
    file_path: Mapped[str] = mapped_column(String(512))
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    error_msg: Mapped[str] = mapped_column(Text, default="")
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_local)


class ChatSession(Base):
    """一次多轮问答会话。"""

    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(128), default="新对话")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_local)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_local, onupdate=now_local)

    user: Mapped["User"] = relationship(back_populates="sessions")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="session", cascade="all, delete-orphan",
        order_by="Message.id",
    )


class Message(Base):
    """会话内的一条消息。citations 保存 AI 回答的溯源引用快照（JSON）。"""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # user / assistant
    content: Mapped[str] = mapped_column(Text)
    citations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_local)

    session: Mapped["ChatSession"] = relationship(back_populates="messages")
