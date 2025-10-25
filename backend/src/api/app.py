from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from .routes import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="智能动漫生成系统 API",
    description="将小说文本转换为动漫视频的智能系统",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "anime-generation-api"}


@app.get("/")
async def root():
    return {
        "message": "智能动漫生成系统 API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
