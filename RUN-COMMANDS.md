# Operations Runbook — Maple Ridge Loan-Risk API

Every command runs from the project root. Under each heading, paste the exact command and only the output lines that matter (the image id, the health answer, the scored response, the log line, the 413).

## 1. Build the image

### The following commnad should be run in the project root directory, where the Dockerfile is.

    docker build -t loan-risk-api:v1 .

## 2. Run with configuration from a file; health check; one scored application

### Run the command using the variable saved in .env.example file.

    docker run -d --name loan-risk-api --env-file .env.example -p 8000:8000 loan-risk-api:v1

### Scoring an application after building the container

    $body = @{
        applicant_age = 35
        employment_status = "employed"
        annual_income = 65000
        credit_score = 720
        loan_amount = 15000
        loan_term_months = 36
        interest_rate = 8.5
        debt_to_income_pct = 25.0
        home_ownership = "rent"
        previous_defaults = 0
    } | ConvertTo-Json

    $response = Invoke-RestMethod `
        -Uri "http://localhost:8000/predict" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body

    $response | ConvertTo-Json

### If you want to try a different threshold

```
  $threshold = 0.35

  $response = Invoke-RestMethod `
      -Uri "http://localhost:8000/predict?threshold=$threshold" `
      -Method POST `
      -ContentType "application/json" `
      -Body $body
```

### Saving the request ID that will used on the next step

    $requestId = $response.request_id
    Write-Output $requestId

## 3. Read the logs from outside the container; find one decision by its request id

### Run the commands

- docker logs loan-risk-api
- docker logs --tail 20 loan-risk-api
- docker logs loan-risk-api 2>&1 | Select-String -SimpleMatch $requestId
- $response | Select-Object request_id, default_prediction, default_probability, model_version

## 4. Change MAX_BATCH by configuration alone (no rebuild) and prove it

### I changed MAX_BATCH to 12 and I will check for a batch size equal to 13

- Recording the orginal image ID:
  - $imageIdBefore = docker image inspect loan-risk-api:v1 --format '{{.Id}}'
  - Write-Output $imageIdBefore
- Change the MAX_BATCH:
  - $envPath = ".env.example"
  - $content = Get-Content $envPath
  - $content = $content -replace '^\s*MAX_BATCH\s*=.*$', 'MAX_BATCH=12'
  - Set-Content -Path $envPath -Value $content
- Verifying if MAX_BATCH was changed:
  - Get-Content .env.example | Select-String '^MAX_BATCH='
- Stoping and removing container:
  - docker stop loan-risk-api
  - docker rm loan-risk-api
- Starting a new container:
  - docker run -d --name loan-risk-api --env-file .env.example -p 8000:8000 loan-risk-api:v1
- Verifying a new batch limit.

  ```
  $application = @{
        applicant_age = 35
        employment_status = "employed"
        annual_income = 65000
        credit_score = 720
        loan_amount = 15000
        loan_term_months = 36
        interest_rate = 8.5
        debt_to_income_pct = 25.0
        home_ownership = "rent"
        previous_defaults = 0
  }

  $batch = ConvertTo-Json `
    -InputObject (@($application) * 13) `
    -Depth 5
  ```

- Submit the batch:

```
    try {
        $response = Invoke-RestMethod `
            -Uri "http://localhost:8000/predict/batch" `
            -Method POST `
            -ContentType "application/json" `
            -Body $batch

        Write-Output "HTTP Status: 200"
        $response | ConvertTo-Json -Depth 5
    }
    catch {
        Write-Output "HTTP Status: $([int]$_.Exception.Response.StatusCode)"
        Write-Output $_.ErrorDetails.Message
    }

```

- Checking if it is the same Docker image.

```
    $imageIdAfter = docker image inspect loan-risk-api:v1 --format '{{.Id}}'
    Write-Output "Image before: $imageIdBefore"
    Write-Output "Image after:  $imageIdAfter"
    Write-Output "Same image:   $($imageIdBefore -eq $imageIdAfter)"
```

## 5. Stop and clean up

- **Stopping container:** docker stop loan-risk-api
- **Removing container:** docker rm loan-risk-api
- **Check if container exists:** docker ps -a --filter "name=^/loan-risk-api$"
- **Checking Docker image:** docker images loan-risk-api:v1
- **Returning the MAX_BATCH to 500:**
  ```
  $envPath = ".env.example"
  $content = Get-Content $envPath
  $content = $content -replace '^\s*MAX_BATCH\s*=.*$', 'MAX_BATCH=500'
  Set-Content -Path $envPath -Value $content
  ```

## Common errors

| Message                                                                             | Cause                                                                                                                                            | Fix                                                                                                           |
| ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| failed to read dockerfile                                                           | Dockerfile is missing or the command is executed from the wrong directory.                                                                       | Navigate to the project root and run docker build -t loan-risk-api:v1 .                                       |
| Unable to find image 'loan-risk-api:v1' locally                                     | The image has not been built or has a different tag.                                                                                             | Run docker build -t loan-risk-api:v1 .                                                                        |
| port is already allocated                                                           | Another process or container is using port 8000.                                                                                                 | Stop the conflicting service or map another host port using -p 8001:8000.                                     |
| Conflict. The container name "/loan-risk-api" is already in use                     | A container with that name already exists.                                                                                                       | Run docker stop loan-risk-api followed by docker rm loan-risk-api.                                            |
| HTTP 422 Unprocessable Entity                                                       | The request body does not match the Pydantic schema. For batch predictions, the API expects a JSON array, not an object containing applications. | Submit [$application, ...] as a JSON array using ConvertTo-Json -InputObject (@($application) \* 3) -Depth 5. |
| HTTP 200 instead of expected HTTP 413                                               | The submitted batch does not exceed the configured MAX_BATCH.<br>The MAX_BATCH was changed to 12 the testing porpuse.                            | Check MAX_BATCH using docker inspect. For MAX_BATCH=12, submit 13 applications.                               |
| HTTP 413 Payload Too Large                                                          | The number of applications exceeds MAX_BATCH.                                                                                                    | Reduce the batch size or change MAX_BATCH in .env and recreate the container.                                 |
| HTTP 503 Service Unavailable                                                        | The model is not ready, potentially because an artifact is missing or loading failed.                                                            | Check docker logs loan-risk-api and verify the .joblib and .json files are included in the image.             |
| HTTP 404 Not Found                                                                  | The requested API route does not exist.                                                                                                          | Use /health, /predict, /predict/batch, or /docs. The root / may legitimately return 404.                      |
| ConvertTo-Json: A positional parameter cannot be found that accepts argument '\*13' | PowerShell treats \*13 as a separate command argument.                                                                                           | Use ConvertTo-Json -InputObject (@($application) \* 13) -Depth 5.                                             |
| docker logs: No such container                                                      | The container has been removed or its name is incorrect.                                                                                         | Run docker ps -a to identify existing containers.                                                             |
