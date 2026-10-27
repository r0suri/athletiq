# AthletIQ

AI-powered fitness and recovery intelligence. Log runs, rides, and strength sessions;
see weekly training load and trends; get explainable, heuristic recovery estimates and
AI coaching explanations grounded in your computed metrics.

> **Status:** Task 1, walking skeleton. A deployed `GET /v1/health` endpoint on
> API Gateway, Lambda, and FastAPI, plus Cognito and DynamoDB, all defined in AWS SAM.

## Architecture (current)

```
Client -> API Gateway (HTTP API, Cognito JWT authorizer) -> Lambda (FastAPI + Mangum) -> DynamoDB
```

- `GET /v1/health` is public. Every other `/v1/*` route requires a Cognito JWT,
  enforced at the gateway before Lambda is invoked.
- One Lambda runs the whole FastAPI app (Python 3.12, arm64).
- Configuration comes only from environment variables (`backend/app/core/config.py`).
- Logs are structured JSON via AWS Lambda Powertools with a 14-day retention.

## Prerequisites

AWS CLI v2, AWS SAM CLI, Python 3.12, and an AWS CLI profile (`aws configure sso`).

## Local development

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-dev.txt

cd backend
pytest                       # tests
ruff check . && ruff format --check .
uvicorn app.main:app --reload   # http://127.0.0.1:8000/v1/health  (docs at /docs)
```

## Deploy

```bash
sam validate --lint
sam build
sam deploy          # settings in samconfig.toml (stack: athletiq-dev, us-east-1)
```

The stack outputs `ApiUrl`, `UserPoolId`, `UserPoolClientId`, and `TableName`.

## Tear down

```bash
sam delete --stack-name athletiq-dev
```
