import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from src.api.app import app

client = TestClient(app)


@pytest.fixture
def mock_novel_parser_agent():
    with patch("src.api.routes.NovelParserAgent") as mock:
        agent_instance = AsyncMock()
        agent_instance.parse = AsyncMock(return_value={
            "characters": [
                {"name": "张三", "description": "主角"}
            ],
            "scenes": [
                {"scene_id": 1, "description": "开场"}
            ],
            "plot_points": []
        })
        mock.return_value = agent_instance
        yield mock


@pytest.fixture
def mock_llm_factory():
    with patch("src.api.routes.LLMFactory") as mock:
        mock.create_llm = MagicMock(return_value=MagicMock())
        yield mock


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "anime-generation-api"}


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data


def test_upload_novel_success(mock_novel_parser_agent, mock_llm_factory):
    response = client.post(
        "/api/v1/novels/upload",
        json={
            "novel_text": "这是一个测试小说，内容足够长来满足最小长度要求。" * 10,
            "mode": "enhanced"
        }
    )
    
    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "processing"
    assert "message" in data


def test_upload_novel_invalid_text():
    response = client.post(
        "/api/v1/novels/upload",
        json={
            "novel_text": "短",
            "mode": "enhanced"
        }
    )
    
    assert response.status_code == 422


def test_upload_novel_invalid_mode():
    response = client.post(
        "/api/v1/novels/upload",
        json={
            "novel_text": "这是一个测试小说，内容足够长来满足最小长度要求。" * 10,
            "mode": "invalid_mode"
        }
    )
    
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_progress_not_found():
    task_id = uuid4()
    response = client.get(f"/api/v1/novels/{task_id}/progress")
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_progress_success(mock_novel_parser_agent, mock_llm_factory):
    upload_response = client.post(
        "/api/v1/novels/upload",
        json={
            "novel_text": "这是一个测试小说，内容足够长来满足最小长度要求。" * 10,
            "mode": "simple"
        }
    )
    
    assert upload_response.status_code == 202
    task_id = upload_response.json()["task_id"]
    
    import time
    time.sleep(0.5)
    
    progress_response = client.get(f"/api/v1/novels/{task_id}/progress")
    
    assert progress_response.status_code == 200
    data = progress_response.json()
    assert data["task_id"] == task_id
    assert "status" in data
    assert "progress" in data
