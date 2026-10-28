# Maple Ridge Loan-Risk API

A FastAPI service for a credit union to estimate loan-default probability using a trained Logistic Regression pipeline. It provides single and batch predictions, a configurable decision threshold, and model health/version information. Predictions support human loan review; they must not be used as automatic approval or rejection decisions.

## Requirements

- Python 3.11 or 3.12 (use a compatible environment with **scikit-learn 1.7.2** for the shipped model).
- Docker Desktop to build and run the container.
- Postman to import and execute the API collection.
- The packages listed in `requirements.txt`.

No paid service, account, or subscription is required for the local workflow.

## Setup on a clean machine

From the project root, in Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env.example
```

Check that `.env.example` points to `models/loan_default_model_v1.joblib` and `models/loan_default_model_v1.json`. The default batch limit is `MAX_BATCH=500` and can be changed through `.env.example`. Use Python and package versions compatible with the saved model.

## Reproduce the model

Run the notebooks in order, from the `notebooks/` directory, with the project data available:

1. `01_data_audit.ipynb` — inspects and cleans the source dataset; produces `data/loan_applications_cleaned_dataset.csv`.
2. `02_train_evaluate.ipynb` — trains and evaluates the Logistic Regression pipeline, selects its operating threshold, and exports `models/loan_default_model_v1.joblib` and `models/loan_default_model_v1.json`.
3. `03_explainability.ipynb` — reconstructs the held-out test split and produces coefficient, SHAP, and optional permutation-importance analyses; it does **not** retrain the model.

The training notebook uses a stratified 80/20 development/test split with `random_state=42`. Reproduction requires the same source data and row order.

## Run the service locally

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open the interactive API documentation at `http://127.0.0.1:8000/docs`. `GET /health` returns HTTP **200** with `status: ok` and model status details when the model and metadata are valid. If either artifact is missing, incompatible, or fails verification, the service reports HTTP **503** (model not ready) rather than serving predictions.

## Run the tests

```powershell
python -m pytest tests/ -v
```

Expected result: **15 passing tests** (7 unit tests and 8 API tests). They cover successful predictions, batch behavior, validation errors, model unavailability, threshold handling, and privacy-conscious logging. The API tests use an in-process test client; no running Uvicorn server is needed.

## Run the container

Start Docker Desktop, then run from the project root:

```powershell
docker build -t loan-risk-api:v1 .
docker run -d --name loan-risk-api --env-file .env.example -p 8000:8000 loan-risk-api:v1
Invoke-RestMethod http://localhost:8000/health
```

The health request should return `status: ok` when the model artifacts load correctly. If a container with this name already exists, stop and remove it before starting another. Rebuild the image after code changes; recreate the container after changing environment settings.

## Benchmark the running service

With the API running locally or in Docker, execute:

```powershell
python benchmark.py
```

The benchmark is intended to report request timing and/or throughput against the running service. The exact printed metrics depend on the project's `benchmark.py` implementation and runtime; inspect its output rather than assuming fixed performance numbers.

## Run the Postman collection

Start the Docker container and confirm `/health` succeeds. In Postman, import `postman/loan_risk_api.postman_collection.json` (Collection v2.1), confirm `baseUrl` is `http://localhost:8000`, then run the requests in order using the Collection Runner:

1. `GET /health` — expects 200.
2. `POST /predict` — expects 200 and a prediction response.
3. `POST /predict/batch` — expects 200 and ordered predictions for a **top-level JSON array**.
4. `POST /predict` with invalid income — expects 422.

Each request includes HTTP-status and response-body assertions. An earlier run passed **6 of 8 assertions**; the batch request returned 422 and needs its validation response checked before claiming a fully passing collection. If the error concerns `credit_score: null`, verify that the container was rebuilt from the current schema.

## Input contract

`POST /predict` accepts one JSON object with these fields:

| Field                | Validation                                                 |
| -------------------- | ---------------------------------------------------------- |
| `applicant_age`      | Integer from 18 to 120                                     |
| `employment_status`  | `employed`, `self-employed`, `retired`, or `unemployed`    |
| `annual_income`      | Finite number greater than 0; **required, cannot be null** |
| `credit_score`       | Integer from 300 to 850, or **null** (optional)            |
| `loan_amount`        | Finite number greater than 0                               |
| `loan_term_months`   | Positive integer                                           |
| `interest_rate`      | Finite number ≥ 0                                          |
| `debt_to_income_pct` | Finite number from 0 to 100                                |
| `home_ownership`     | `rent`, `mortgage`, or `own`                               |
| `previous_defaults`  | Nonnegative integer                                        |

Extra fields are rejected (`extra="forbid"`), and invalid inputs return HTTP **422**. `POST /predict/batch` accepts a top-level JSON array of the same objects, not an `applications` wrapper; an empty array returns 422 and a batch exceeding `MAX_BATCH` returns **413**. Both prediction endpoints accept an optional `threshold` query parameter strictly between 0 and 1. Responses include a generated `request_id` for tracing, without logging applicant input values. The single response includes the default probability, `high-risk`/`low-risk` classification, model version, and threshold used; batch responses include the corresponding prediction list and count.
