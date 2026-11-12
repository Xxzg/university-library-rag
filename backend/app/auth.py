"""认证与权限：JWT 令牌、密码哈希（PBKDF2）、三级角色 RBAC。

角色层级：student(1) < teacher(2) < admin(3)
- student：问答、查看自己的历史
- teacher：+ 上传/删除文献
- admin  ：+ 用户管理
"""
import hashlib
import hmac
import os
import time

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User

ROLE_LEVEL = {"student": 1, "teacher": 2, "admin": 3}
_PBKDF2_ROUNDS = 100_000

security = HTTPBearer(auto_error=False)


# ---------- 密码 ----------

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
    return f"{salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split("$")
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), _PBKDF2_ROUNDS
        )
        return hmac.compare_digest(dk.hex(), dk_hex)
    except (ValueError, AttributeError):
        return False


# ---------- JWT ----------

def create_access_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "username": user.username,
        "exp": int(time.time()) + settings.access_token_expire_minutes * 60,
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if cred is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或缺少令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(cred.credentials, settings.secret_key, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效令牌")

    user = db.get(User, int(payload.get("sub", 0)))
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


def require_role(min_role: str):
    """依赖工厂：要求当前用户角色不低于 min_role。"""

    def checker(user: User = Depends(get_current_user)) -> User:
        if ROLE_LEVEL.get(user.role, 0) < ROLE_LEVEL[min_role]:
            raise HTTPException(
                status_code=403,
                detail=f"权限不足，需要 {min_role} 及以上角色",
            )
        return user

    return checker
