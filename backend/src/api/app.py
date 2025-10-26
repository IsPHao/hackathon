from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
import os

from .routes import router
from .config import api_config

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

# Mount static files directory for video access
# Only expose the videos subdirectory for security (not temp/, character/, etc.)
exposed_media_path = api_config.get_exposed_media_path()
os.makedirs(exposed_media_path, exist_ok=True)
app.mount(api_config.media_url_prefix, StaticFiles(directory=exposed_media_path), name="static")
logger.info(f"Mounted static files directory: {exposed_media_path} -> {api_config.media_url_prefix}")
logger.info(f"Media root: {api_config.get_media_root_path()}, Exposed subdir: {api_config.exposed_media_subdir}")

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
