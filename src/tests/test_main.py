from fastapi.testclient import TestClient

from src.main import app


client = TestClient(app)


def test_main():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"data": {"status": "ok"}, "error": None}
