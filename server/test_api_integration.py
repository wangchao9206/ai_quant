from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_generate_endpoint():
    payload = {"text": "当10日均线上穿30日均线时买入"}
    response = client.post("/api/strategies/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "code" in data
    assert "config" in data
    assert data["config"]["fast_period"] == 10
    assert data["config"]["slow_period"] == 30
    print("API Test Passed!")

if __name__ == "__main__":
    test_generate_endpoint()
