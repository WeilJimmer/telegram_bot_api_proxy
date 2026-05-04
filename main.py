import uvicorn
from fastapi import FastAPI
from app.router import router

app = FastAPI(
    title="Telegram Bot API Proxy",
    description="隱藏 Bot Token 的 Telegram Bot API 代理伺服器",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)