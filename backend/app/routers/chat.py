"""问答路由：SSE 流式 RAG 问答，问题与回答（含溯源引用）自动落库。"""
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import ChatSession, Message, User
from app.schemas import ChatRequest
from app.services.rag import stream_answer

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("")
async def chat(
    body: ChatRequest,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.get(ChatSession, body.session_id)
    if not session or session.user_id != current.id:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 落库用户问题
    user_msg = Message(session_id=session.id, role="user", content=body.question)
    db.add(user_msg)

    # 首轮对话自动以问题开头作为会话标题
    if session.title == "新对话":
        session.title = body.question[:30]
    db.commit()

    # 历史消息（不含刚插入的这条）传入 RAG 链路
    history = [
        {"role": m.role, "content": m.content}
        for m in session.messages
        if m.id != user_msg.id
    ]

    async def event_stream():
        answer_parts: list[str] = []
        citations: list | None = None
        try:
            async for sse_line in stream_answer(body.question, history):
                # sse_line: "data: {...}\n\n"
                payload = json.loads(sse_line.removeprefix("data: ").strip())
                event = payload.get("event")
                if event == "delta":
                    answer_parts.append(payload.get("content", ""))
                elif event == "citation":
                    citations = payload.get("citations")
                elif event == "error":
                    # 错误也记录到会话，方便排查
                    answer_parts.append(f"[系统提示] {payload.get('message', '未知错误')}")
                yield sse_line
        finally:
            # 无论成功失败，AI 回复（或错误提示）落库
            if answer_parts:
                ai_msg = Message(
                    session_id=session.id,
                    role="assistant",
                    content="".join(answer_parts),
                    citations=citations,
                )
                db.add(ai_msg)
                db.commit()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
