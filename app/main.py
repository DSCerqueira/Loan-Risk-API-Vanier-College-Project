from fastapi import FastAPI, HTTPException, Query

from app import service
from app.schemas import BatchResponse, LoanApplication, RiskResponse

API_VERSION = "1.0"


app = FastAPI(
    title="Loan Default Risk API",
    version=API_VERSION,
    description="Predict loan default risk using a validated logistic regression pipeline. Applicant data is not written to prediction logs.",
)

service.load_artifacts()

def require_ready():
    if not service.is_ready():
        raise HTTPException(status_code=503, detail=service.NOT_READY_REASON)

def log_prediction(request_id, verdict, probability, threshold, version):
    service.logger.info(
        "request_id=%s verdict=%s probability=%.3f threshold=%.6f model_version=%s",
        request_id, verdict, probability, threshold, version,
    )


@app.get("/health", tags=["Service"], summary="Check model readiness")
def health():
    require_ready()
    return {"status": "ok", **service.status()}


@app.get("/version", tags=["Service"], summary="Get API and model versions")
def version():
    return {"api_version": API_VERSION, **service.status()}


@app.post("/predict", response_model=RiskResponse, tags=["Predictions"], summary="Score one loan application")
def predict(application: LoanApplication, threshold: float | None = Query(default=None, gt=0, lt=1, description="Optional operating threshold override.")):
    require_ready()
    result = service.predict_one(application.model_dump(), threshold)
    request_id = service.new_request_id()
    log_prediction(request_id, result["default_prediction"], result["default_probability"], result["threshold_used"], result["model_version"])
    return RiskResponse(request_id=request_id, **result)



@app.post("/predict/batch", response_model=BatchResponse, tags=["Predictions"], summary="Score a batch of loan applications")
def batch_endpoint(applications: list[LoanApplication], threshold: float | None = Query(default=None, gt=0, lt=1, description="Optional operating threshold override.")):
    require_ready()
    if not applications:
        raise HTTPException(status_code=422, detail="Batch must contain at least one application")
    if len(applications) > service.MAX_BATCH:
        raise HTTPException(status_code=413, detail=f"Batch maximum is {service.MAX_BATCH} applications")
    applied, predictions = service.predict_many([application.model_dump() for application in applications], threshold)
    request_id = service.new_request_id()
    # One INFO log entry for the batch; never log application inputs.
    for_prediction = predictions[0]  # representative verdict/probability for request-level logging
    log_prediction(request_id, for_prediction["default_prediction"], for_prediction["default_probability"], applied, service.METADATA["version"])
    return BatchResponse(request_id=request_id, count=len(predictions), model_version=service.METADATA["version"], threshold_used=applied, predictions=predictions)


