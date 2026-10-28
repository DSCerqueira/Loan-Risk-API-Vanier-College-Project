import logging

import pytest
from fastapi.testclient import TestClient

from app import service
from app.main import app

client = TestClient(app)



def test_health_ready(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True
    assert body["model_version"] == 1


def test_predict_success(client, applicant):
    response = client.post("/predict", json=applicant)
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["request_id"], str) and len(body["request_id"]) == 32
    assert body["default_prediction"] in {"high-risk", "low-risk"}
    assert 0 <= body["default_probability"] <= 1
    assert body["threshold_used"] == service.THRESHOLD


def test_batch_success_preserves_order(client, applicant):
    second = {**applicant, "previous_defaults": 2, "credit_score": 400}
    response = client.post("/predict/batch", json=[applicant, second])
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert body["model_version"] == 1
    assert len(body["predictions"]) == 2
    expected = [service.predict_one(row) for row in (applicant, second)]
    assert body["predictions"] == [
        {"default_prediction": row["default_prediction"], "default_probability": row["default_probability"]}
        for row in expected
    ]


def test_invalid_annual_income_returns_422(client, applicant):
    invalid = {**applicant, "annual_income": None}
    response = client.post("/predict", json=invalid)
    assert response.status_code == 422
    assert any("annual_income" in error["loc"] for error in response.json()["detail"])


def test_batch_above_limit_returns_413(client, applicant, monkeypatch):
    monkeypatch.setattr(service, "MAX_BATCH", 2)
    response = client.post("/predict/batch", json=[applicant] * 3)
    assert response.status_code == 413
    assert response.json() == {"detail": "Batch maximum is 2 applications"}


def test_model_unavailable_returns_503(client, applicant, monkeypatch):
    monkeypatch.setattr(service, "model", None)
    monkeypatch.setattr(service, "NOT_READY_REASON", "Model unavailable for test")
    response = client.post("/predict", json=applicant)
    assert response.status_code == 503
    assert response.json()["detail"] == "Model unavailable for test"


def test_null_credit_score_and_empty_batch(client, applicant):
    valid = {**applicant, "credit_score": None}
    response = client.post("/predict", json=valid)
    assert response.status_code == 200
    empty = client.post("/predict/batch", json=[])
    assert empty.status_code == 422
    assert empty.json()["detail"] == "Batch must contain at least one application"


def test_prediction_log_contains_request_id_but_not_inputs(client, applicant, caplog):
    with caplog.at_level(logging.INFO, logger="loan-risk-api"):
        response = client.post("/predict", json=applicant)
    assert response.status_code == 200
    request_id = response.json()["request_id"]
    matching = [record.getMessage() for record in caplog.records
                if record.name == "loan-risk-api" and request_id in record.getMessage()]
    assert len(matching) == 1
    message = matching[0]
    assert "request_id=" in message
    # Check distinctive synthetic values; not short numeric tokens that may occur in thresholds.
    for sensitive in ("65000", "15000", "720", "employed", "rent"):
        assert sensitive not in message