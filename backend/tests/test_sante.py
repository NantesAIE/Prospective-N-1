from fastapi.testclient import TestClient

from prospective.main import app


def test_sante():
    reponse = TestClient(app).get("/api/sante")
    assert reponse.status_code == 200
    assert reponse.json()["statut"] == "ok"
