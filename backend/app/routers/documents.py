"""文献管理路由：上传（teacher+）/ 列表（全部登录用户）/ 删除（teacher+）。"""
import re
import time
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth import require_role
from app.config import settings
from app.database import get_db
from app.models import Document, User
from app.schemas import DocumentOut
from app.services.ingestion import SUPPORTED_TYPES, ingest_document, remove_document_from_store

router = APIRouter(prefix="/api/documents", tags=["documents"])

_SAFE_NAME = re.compile(r"[^\w\u4e00-\u9fff.-]")


@router.post("/upload", response_model=DocumentOut, status_code=201)
def upload_document(
    file: UploadFile,
    title: str | None = None,
    current: User = Depends(require_role("teacher")),
    db: Session = Depends(get_db),
):
    # 注意：title 作为额外表单字段，FastAPI 会自动解析 multipart 中的 title
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型 {suffix}，仅支持 {'/'.join(sorted(SUPPORTED_TYPES))}",
        )

    # 保存上传文件（文件名做安全化处理，避免路径穿越）
    safe_stem = _SAFE_NAME.sub("_", Path(file.filename).stem)[:80] or "doc"
    stored_name = f"{int(time.time())}_{safe_stem}{suffix}"
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / stored_name

    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件为空")
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件超过 50MB 限制")
    file_path.write_bytes(content)

    # 建立文献记录（processing）
    doc = Document(
        title=(title or Path(file.filename).stem)[:256],
        filename=quote(file.filename or stored_name),
        file_type=suffix.lstrip("."),
        file_path=str(file_path),
        file_size=len(content),
        status="processing",
        uploaded_by=current.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # 同步执行入库管线（毕设数据量小，无需任务队列）
    try:
        doc.chunk_count = ingest_document(doc.id, doc.title, doc.file_path)
        doc.status = "done"
    except Exception as e:
        doc.status = "failed"
        doc.error_msg = str(e)[:1000]
    db.commit()
    db.refresh(doc)
    return DocumentOut.model_validate(doc)


@router.get("", response_model=list[DocumentOut])
def list_documents(
    _: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    return db.query(Document).order_by(Document.created_at.desc()).all()


@router.delete("/{doc_id}", status_code=204)
def delete_document(
    doc_id: int,
    _: User = Depends(require_role("teacher")),
    db: Session = Depends(get_db),
):
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文献不存在")

    # 从向量库移除对应 chunk
    try:
        remove_document_from_store(doc_id)
    except Exception:
        pass  # 向量库清理失败不阻塞删除流程

    # 删除物理文件
    try:
        Path(doc.file_path).unlink(missing_ok=True)
    except OSError:
        pass

    db.delete(doc)
    db.commit()
