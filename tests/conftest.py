import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
os.environ.setdefault("MODEL_PATH", "models/loan_default_model_v1.joblib")
os.environ.setdefault("METADATA_PATH", "models/loan_default_model_v1.json")
os.environ.setdefault("MAX_BATCH", "500")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["MODEL_PATH"] = str(ROOT / "models" / "loan_default_model_v1.joblib")
os.environ["METADATA_PATH"] = str(ROOT / "models" / "loan_default_model_v1.json")
os.environ["MAX_BATCH"] = "500"

from app import service  
from app.main import app  

@pytest.fixture
def applicant():
    """Synthetic, valid applicant; never copied from the training dataset."""
    return {
        "applicant_age": 35,
        "employment_status": "employed",
        "annual_income": 65000.0,
        "credit_score": 720,
        "loan_amount": 15000.0,
        "loan_term_months": 36,
        "interest_rate": 8.5,
        "debt_to_income_pct": 25.0,
        "home_ownership": "rent",
        "previous_defaults": 0,
    }


@pytest.fixture
def client():
    """In-process HTTP client: no Uvicorn or Docker required."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def restore_service_state():
    """Ensure monkeypatches and readiness tests cannot contaminate later tests."""
    if not service.is_ready():
        service.load_artifacts()
    yield