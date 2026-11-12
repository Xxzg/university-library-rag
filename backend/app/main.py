"""FastAPI 应用入口。启动：cd backend && uvicorn app.main:app --reload --port 8000"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import auth_router, chat, documents, sessions, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时建表（SQLite 首次运行自动创建）
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="高校图书馆智能问答系统",
    description="基于 LangChain + RAG 的馆藏文献检索增强问答系统",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(users.router)
app.include_router(documents.router)
app.include_router(sessions.router)
app.include_router(chat.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
