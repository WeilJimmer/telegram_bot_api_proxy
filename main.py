import uvicorn
from fastapi import FastAPI
from app.router import router
from app.settings import SERVER_HOST, SERVER_PORT

app = FastAPI(
    title="Telegram Bot API Proxy",
    description="A Telegram Bot API proxy server that hides bot tokens and supports access control.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("main:app", host=SERVER_HOST, port=SERVER_PORT, reload=False)