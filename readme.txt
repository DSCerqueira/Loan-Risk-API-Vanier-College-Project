STARTER KIT - Final Project, 420-974-VA AI Model Deployment
============================================================

Rename this folder LastName-FirstName-FP. It is the folder you will zip and submit.
It contains no working code, no notebook, and no model. Files marked "you write"
have numbered TODO markers; remove each marker as you complete it.

WHAT IS HERE
------------
readme.txt              this file; delete it before you zip
requirements.txt        you complete: pin every version (scikit-learn 1.7.2)
.env.example            given: the three configuration values (MODEL_PATH, METADATA_PATH, MAX_BATCH)
.dockerignore           you complete: what must never enter the image
Dockerfile              you write: 7 TODO lines
README.md               you write: setup and run instructions for a stranger
RUN-COMMANDS.md         you write: the operations runbook (commands + the output lines that matter)
benchmark.py            given, do not edit: measures your running container over HTTP
check_submission.py     given, do not edit: the pre-flight check the grader runs first

app/
  __init__.py           given (empty)
  schemas.py            you write: LoanApplication, RiskResponse, BatchResponse (5 TODOs)
  service.py            you write: cleaning functions, verified loader, predict_one, predict_many (8 TODOs)
  main.py               you write: the routes (6 TODOs)

data/
  loan_applications.csv the client's export, as received - do not edit it and never upload it anywhere

models/                 empty; your notebook writes loan_default_model_v1.joblib and .json here
notebooks/              empty; you create 01_data_audit, 02_train_evaluate, 03_explainability
tests/
  conftest.py           given: lets pytest find app/ and the artifact pair
  test_units.py         you write
  test_api.py           you write
postman/                empty; export your collection here as loan_risk_api.postman_collection.json
report/                 empty; your report goes here as LastName-FirstName-FP-Report.docx

HOW TO USE THE TWO GIVEN SCRIPTS
--------------------------------
python benchmark.py          with your container running on port 8000; prints latency,
                             batch saving, and requests per second for your report
python check_submission.py   from this folder, virtual environment active, no server running;
                             every line must be PASS before you zip; paste the output in Appendix B

Read Final-Project-Description for the full requirements.
