import json
import logging
import os
import uuid
from pathlib import Path

import joblib
import pandas as pd, numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("loan-risk-api")

REQUIRED_METADATA = ("version", "features", "operating_threshold")


def normalize_employment(value):

    if not isinstance(value, str):
        return None
    normalized = "-".join(value.strip().lower().split()).replace("_", "-")
    return normalized if normalized in {"employed", "self-employed", "retired", "unemployed"} else None


def parse_percent(value):

    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        result = float(value.strip().removesuffix("%").strip() if isinstance(value, str) else value)
        return result if np.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def load_env(path=".env.example"):
    path = Path(path)
    if not path.is_file():
        return
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env()

MODEL_PATH = Path(os.environ.get("MODEL_PATH", "models/loan_default_model_v1.joblib"))
METADATA_PATH = Path(os.environ.get("METADATA_PATH", "models/loan_default_model_v1.json"))
MAX_BATCH = int(os.environ.get("MAX_BATCH", "500"))

model = None
METADATA = {}
THRESHOLD = None
FEATURES = []
NOT_READY_REASON = "artifacts not loaded yet"


def verify_artifacts(candidate, metadata):

    if not isinstance(metadata, dict):
        return "Metadata must be a JSON object"
    for key in REQUIRED_METADATA:
        if key not in metadata:
            return f"Required metadata key missing: {key}"
    features = metadata["features"]
    if not isinstance(features, list) or not features or not all(isinstance(f, str) for f in features) or len(set(features)) != len(features):
        return "Metadata features must be a nonempty list of unique strings"
    fitted = getattr(candidate, "feature_names_in_", None)
    if fitted is None or features != list(fitted):
        return "Metadata features differ from pipeline.feature_names_in_"
    if not callable(getattr(candidate, "predict_proba", None)):
        return "Model does not support predict_proba"
    try:
        threshold = float(metadata["operating_threshold"])
    except (TypeError, ValueError):
        return "Operating threshold is not numeric"
    if not np.isfinite(threshold) or not 0 < threshold < 1:
        return "Operating threshold must be strictly between 0 and 1"
    if MAX_BATCH < 1:
        return "MAX_BATCH must be a positive integer"
    return None


def load_artifacts():

    global model, METADATA, THRESHOLD, FEATURES, NOT_READY_REASON
    model, METADATA, THRESHOLD, FEATURES = None, {}, None, []
    NOT_READY_REASON = "artifacts not loaded yet"
    try:
        candidate = joblib.load(MODEL_PATH)
        metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        problem = verify_artifacts(candidate, metadata)
        if problem:
            NOT_READY_REASON = problem
            logger.error("Model artifacts rejected: %s", problem)
            return
        model = candidate
        METADATA = metadata
        THRESHOLD = float(metadata["operating_threshold"])
        FEATURES = list(metadata["features"])
        NOT_READY_REASON = None
        logger.info("Model artifacts ready version=%s", METADATA["version"])
    except Exception as exc:
        NOT_READY_REASON = f"Unable to load model artifacts: {type(exc).__name__}: {exc}"
        logger.error("Model artifacts rejected: %s", NOT_READY_REASON)
        return


def is_ready():
    return model is not None


def status():

    return {
        "model_loaded": is_ready(),
        "model_version": METADATA.get("version"),
        "operating_threshold": THRESHOLD,
        "not_ready_reason": NOT_READY_REASON,
    }


def new_request_id():
    return uuid.uuid4().hex


def _frame(records):

    return pd.DataFrame.from_records(records).loc[:, FEATURES]

def resolve_threshold(threshold):
    applied = THRESHOLD if threshold is None else float(threshold)
    if applied is None or not np.isfinite(applied) or not 0 < applied < 1:
        raise ValueError("Threshold must be strictly between 0 and 1")
    return applied

def predict_one(application_dict, threshold=None):

    if not is_ready():
        raise RuntimeError(NOT_READY_REASON)
    applied = resolve_threshold(threshold)
    probability = float(model.predict_proba(_frame([application_dict]))[0, 1])
    return {
        "default_prediction": "high-risk" if probability >= applied else "low-risk",
        "default_probability": round(probability, 3),
        "model_version": METADATA["version"],
        "threshold_used": applied,
    }


def predict_many(application_dicts, threshold=None):

    if not is_ready():
        raise RuntimeError(NOT_READY_REASON)
    if not application_dicts:
        raise ValueError("Batch must contain at least one application")
    if len(application_dicts) > MAX_BATCH:
        raise OverflowError(f"Batch maximum is {MAX_BATCH} applications")
    applied = resolve_threshold(threshold)
    probabilities = model.predict_proba(_frame(application_dicts))[:, 1]
    predictions = [
        {"default_prediction": "high-risk" if float(p) >= applied else "low-risk", "default_probability": round(float(p), 3)}
        for p in probabilities
    ]
    return applied, predictions
