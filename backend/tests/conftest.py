"""Общие фикстуры для тестов.

Стратегия: используем существующую БД `messenger` и уникальные username
на каждый тест (uuid4) — чтобы тесты не мешали друг другу и не требовали
отдельной тестовой БД. Все чаты/сообщения, созданные в рамках теста,
относятся к тестовому пользователю и не пересекаются с seed-данными.
"""
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def unique_username() -> str:
    return f"testuser_{uuid.uuid4().hex[:12]}"


def _register(client: TestClient, username: str, password: str = "secret123") -> dict:
    r = client.post("/auth/register", json={"username": username, "password": password})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture()
def user(client: TestClient, unique_username: str) -> dict:
    """Свежий зарегистрированный пользователь. Ключи: id, username, token, refresh_token."""
    return _register(client, unique_username)


@pytest.fixture()
def user_factory(client: TestClient):
    """Фабрика: user_factory() -> нового пользователя."""
    def make(username: str | None = None, password: str = "secret123") -> dict:
        return _register(client, username or f"testuser_{uuid.uuid4().hex[:12]}", password)
    return make


def auth_headers(user: dict) -> dict:
    return {"Authorization": f"Bearer {user['token']}"}
