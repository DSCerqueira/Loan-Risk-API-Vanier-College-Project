from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LoanApplication(BaseModel):

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"example": {
            "applicant_age": 35, "employment_status": "employed",
            "annual_income": 65000.0, "credit_score": 700,
            "loan_amount": 15000.0, "loan_term_months": 36,
            "interest_rate": 9.5, "debt_to_income_pct": 28.5,
            "home_ownership": "rent", "previous_defaults": 0
        }}
    )
    

    applicant_age: int = Field(ge=18, le=120, description="Applicant age in years (18–120).")
    employment_status: Literal["employed", "self-employed", "retired", "unemployed"] = Field(description="Normalized employment status.")
    annual_income: float = Field(gt=0.0, allow_inf_nan=False, description="Annual income; required even though training used imputation.")
    credit_score: int | None = Field(default=None,ge=300, le=850, description="Credit score between 300 and 850; null is allowed.")
    loan_amount: float = Field(gt=0.0, allow_inf_nan=False, description="Requested loan amount.")
    loan_term_months: int = Field(gt=0, description="Loan term in months.")
    interest_rate: float = Field(ge=0.0, allow_inf_nan=False, description="Annual interest rate in percent.")
    debt_to_income_pct: float = Field(ge=0.0, le=100.0, allow_inf_nan=False, description="Debt-to-income ratio as a percentage (0–100).")
    home_ownership: Literal["rent", "mortgage", "own"] = Field(description="Housing ownership category.")
    previous_defaults: int = Field(ge=0, description="Number of previous defaults.")



class RiskResponse(BaseModel):

    request_id: str = Field(description="Unique UUID4 identifier for this prediction.")
    default_prediction: Literal["high-risk", "low-risk"] = Field(description="Risk verdict at the applied threshold.")
    default_probability: float = Field(ge=0.0, le=1.0, description="Estimated default probability rounded to three decimal places.")
    model_version: int = Field(description="Version of the loaded model.")
    threshold_used: float = Field(gt=0.0, lt=1.0, description="Operating threshold applied to this prediction.")

class BatchVerdict(BaseModel):
    default_prediction: Literal["high-risk", "low-risk"] = Field(description="Risk verdict for one application.")
    default_probability: float = Field(ge=0.0, le=1.0, description="Default probability rounded to three decimals.")

class BatchResponse(BaseModel):
    request_id: str = Field(description="Unique UUID4 identifier for the batch request.")
    count: int = Field(ge=1, description="Number of applications scored.")
    model_version: int = Field(description="Version of the loaded model.")
    threshold_used: float = Field(gt=0.0, lt=1.0, description="Threshold applied to every batch record.")
    predictions: list[BatchVerdict] = Field(description="Predictions in the same order as the input records.")


