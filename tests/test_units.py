import pytest
import copy
import json
import joblib

from app import service

def test_predict_one_verdict_at_operating_threshold(applicant):
    result = service.predict_one(applicant)
    raw_probability = float(service.model.predict_proba(service._frame([applicant]))[0, 1])
    expected = "high-risk" if raw_probability >= service.THRESHOLD else "low-risk"
    assert result["default_prediction"] == expected
    assert result["threshold_used"] == service.THRESHOLD
    assert result["default_probability"] == round(raw_probability, 3)


def test_predict_one_response_shape(applicant):
    result = service.predict_one(applicant)
    assert set(result) == {"default_prediction", "default_probability", "model_version", "threshold_used"}
    assert result["default_prediction"] in {"high-risk", "low-risk"}
    assert isinstance(result["default_probability"], float)
    assert 0 <= result["default_probability"] <= 1
    assert result["model_version"] == service.METADATA["version"]


def test_predict_one_threshold_override_is_request_specific(applicant):
    before = service.predict_one(applicant)
    overridden = service.predict_one(applicant, threshold=0.9)
    after = service.predict_one(applicant)
    assert overridden["threshold_used"] == 0.9
    assert overridden["default_probability"] == before["default_probability"]
    assert before == after
    raw_probability = float(service.model.predict_proba(service._frame([applicant]))[0, 1])
    assert overridden["default_prediction"] == ("high-risk" if raw_probability >= 0.9 else "low-risk")


def test_normalize_employment_export_spellings():
    # Spellings supported by the current implementation, including whitespace, case and separators.
    cases = {
        "employed": "employed", " Employed ": "employed", "EMPLOYED": "employed",
        "self-employed": "self-employed", "Self_Employed": "self-employed",
        " self   employed ": "self-employed", "SELF-EMPLOYED": "self-employed",
        "retired": "retired", " RETIRED ": "retired",
        "unemployed": "unemployed", "UNEMPLOYED": "unemployed",
    }
    for raw, expected in cases.items():
        assert service.normalize_employment(raw) == expected, raw
    for invalid in (None, 123, "contractor", "", "unknown"):
        assert service.normalize_employment(invalid) is None


def test_parse_percent_supported_formats():
    for raw, expected in [(25, 25.0), (25.5, 25.5), ("25%", 25.0), (" 12.5 % ", 12.5), ("0", 0.0)]:
        assert service.parse_percent(raw) == expected
    for invalid in (None, "", "  ", "abc", "NaN", float("inf")):
        assert service.parse_percent(invalid) is None


def test_verify_artifacts_accepts_shipped_pair():
    candidate = joblib.load(service.MODEL_PATH)
    metadata = json.loads(service.METADATA_PATH.read_text(encoding="utf-8"))
    assert service.verify_artifacts(candidate, metadata) is None


def test_verify_artifacts_rejects_feature_mismatch():
    altered = copy.deepcopy(service.METADATA)
    altered["features"] = list(reversed(altered["features"]))
    assert "features differ" in service.verify_artifacts(service.model, altered)