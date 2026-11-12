"""批量上传真实文献（httpx，UTF-8 标题，避免 shell curl 编码乱码）。

运行：cd backend && venv/Scripts/python.exe scripts/batch_upload.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

BASE = "http://127.0.0.1:8000"
TESTDOCS = Path(__file__).resolve().parents[1] / "data" / "testdocs"

# 跳过自动生成的模拟文献，只传真实馆藏文献
SKIP = {
    "信息检索导论_节选.pdf",
    "数字图书馆技术_节选.pdf",
    "图书馆学基础_节选.docx",
    "学术论文写作规范_节选.docx",
    "知识服务与智能问答.md",
}


def main():
    # 教师登录
    r = httpx.post(
        f"{BASE}/api/auth/login",
        json={"username": "teacher", "password": "teacher123"},
    )
    r.raise_for_status()
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    files = sorted(
        f for f in TESTDOCS.iterdir()
        if f.suffix.lower() in {".pdf", ".docx", ".txt", ".md"} and f.name not in SKIP
    )
    print(f"待上传 {len(files)} 篇真实文献\n")

    ok = fail = 0
    for f in files:
        title = f.stem  # UTF-8 文件名去扩展名
        with open(f, "rb") as fp:
            r = httpx.post(
                f"{BASE}/api/documents/upload",
                headers=headers,
                files={"file": (f.name, fp, "application/octet-stream")},
                data={"title": title},
                timeout=600,
            )
        try:
            d = r.json()
        except Exception:
            print(f"[失败] {f.name}: HTTP {r.status_code} {r.text[:100]}")
            fail += 1
            continue
        if d.get("status") == "done":
            print(f"[成功] {f.name[:40]:42} 状态={d['status']} 片段数={d['chunk_count']}")
            ok += 1
        else:
            print(f"[失败] {f.name[:40]:42} {d.get('error_msg','')[:80]}")
            fail += 1
    print(f"\n批量上传完成：成功 {ok}，失败 {fail}")


if __name__ == "__main__":
    main()
