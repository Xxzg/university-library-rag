"""初始化演示账号：admin / teacher / student。

运行：cd backend && venv/Scripts/python.exe scripts/seed.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth import hash_password  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import User  # noqa: E402

DEMO_ACCOUNTS = [
    ("admin", "admin123", "admin", "管理员（用户管理 + 全部权限）"),
    ("teacher", "teacher123", "teacher", "教师（可上传/删除文献）"),
    ("student", "student123", "student", "学生（问答 + 历史）"),
]


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for username, password, role, desc in DEMO_ACCOUNTS:
            if db.query(User).filter(User.username == username).first():
                print(f"[skip] {username} 已存在")
                continue
            db.add(User(username=username, password_hash=hash_password(password), role=role))
            print(f"[ok]   创建 {username} / {password} -> {desc}")
        db.commit()
    finally:
        db.close()
    print("\n种子数据完成。")
    print("登录页可用账号：admin/admin123, teacher/teacher123, student/student123")


if __name__ == "__main__":
    main()
