"""用户管理路由（仅管理员）：列表 / 角色分配 / 删除。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_role
from app.database import get_db
from app.models import User
from app.schemas import RoleUpdateIn, UserOut

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(
    _: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return db.query(User).order_by(User.id).all()


@router.put("/{user_id}/role", response_model=UserOut)
def update_role(
    user_id: int,
    body: RoleUpdateIn,
    current: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == current.id and body.role != "admin":
        raise HTTPException(status_code=400, detail="不能降低自己的管理员角色")
    user.role = body.role
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    current: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == current.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    db.delete(user)
    db.commit()
