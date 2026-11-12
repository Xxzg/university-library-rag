"""Pydantic 请求/响应模型。"""
from datetime import datetime

from pydantic import BaseModel, Field


# ---- 认证 ----
class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class RegisterIn(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---- 用户管理 ----
class RoleUpdateIn(BaseModel):
    role: str = Field(pattern="^(student|teacher|admin)$")


# ---- 文献 ----
class DocumentOut(BaseModel):
    id: int
    title: str
    filename: str
    file_type: str
    file_size: int
    status: str
    chunk_count: int
    error_msg: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---- 会话与消息 ----
class SessionCreateIn(BaseModel):
    title: str = Field(default="新对话", max_length=128)


class SessionRenameIn(BaseModel):
    title: str = Field(min_length=1, max_length=128)


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    citations: list | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class SessionDetailOut(SessionOut):
    messages: list[MessageOut] = []


# ---- 问答 ----
class ChatRequest(BaseModel):
    session_id: int
    question: str = Field(min_length=1, max_length=2000)


class Citation(BaseModel):
    """溯源引用块，绑定答案中的 [n] 标记。"""

    index: int
    document_id: int
    title: str
    page: int | None = None
    chunk_index: int = 0
    snippet: str
    score: float = 0.0
