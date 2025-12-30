from fastapi.testclient import TestClient
import sys
import os

# 현재 위치보다 한 단계 위(부모 디렉토리)를 파이썬 경로에 추가
# 그래야 app.main을 불러올 수 있습니다.
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from src.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}