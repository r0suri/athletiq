# AthletIQ

AI-powered fitness and recovery intelligence. Log runs, rides, and strength sessions;
see weekly training load and trends; get explainable, heuristic recovery estimates and
AI coaching explanations grounded in your computed metrics.

> **Status:** Increment 2. Health endpoint, deterministic analytics engine
> ([docs/analytics.md](docs/analytics.md)), and the workout and check-in API with
> Cognito-based authorization and a DynamoDB single-table repository.

## Architecture (current)

```
Client -> API Gateway (HTTP API, Cognito JWT authorizer) -> Lambda (FastAPI + Mangum) -> DynamoDB
```

- `GET /v1/health` is public. Every other `/v1/*` route requires a Cognito JWT,
  enforced at the gateway before Lambda is invoked.
- One Lambda runs the whole FastAPI app (Python 3.12, arm64).
- Configuration comes only from environment variables (`backend/app/core/config.py`).
- Logs are structured JSON via AWS Lambda Powertools with a 14-day retention.

## API (v1)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/v1/health` | public | Liveness |
| POST | `/v1/workouts` | JWT | Log a run, ride or strength workout |
| GET | `/v1/workouts?from=&to=&type=&limit=&cursor=` | JWT | Newest-first, cursor-paginated list |
| GET | `/v1/workouts/{id}` | JWT | One workout |
| DELETE | `/v1/workouts/{id}` | JWT | Delete a workout |
| PUT | `/v1/checkins/{date}` | JWT | Create or replace a daily wellness check-in |

Errors always use `{"error": {"code", "message", "details", "request_id"}}`.

## Authentication and authorization

- **Deployed (`AUTH_MODE=cognito`, the default):** API Gateway's JWT authorizer verifies
  the Cognito token before Lambda runs. The app reads the verified `sub` claim from the
  API Gateway event and never parses the `Authorization` header itself.
- **Local development (`AUTH_MODE=local`):** identity comes from an `X-Dev-User-Id`
  header. Settings validation refuses this mode unless `APP_ENV` is `local`/`test`,
  and refuses it inside AWS Lambda regardless of other settings.
- **Isolation:** every DynamoDB key is built from the authenticated user id
  (`PK = USER#<sub>`). Another user's workout returns `404`, and pagination cursors carry
  only a sort key, so a reused cursor cannot reach another user's partition.

## Data model (single table)

| Entity | PK | SK |
|---|---|---|
| Workout | `USER#<sub>` | `WORKOUT#<yyyy-mm-dd>#<ULID>` |
| Daily check-in | `USER#<sub>` | `CHECKIN#<yyyy-mm-dd>` |

Date-range listing is a single `Query` with `SK BETWEEN`; nothing scans the table
(enforced by `tests/integration/test_repository_no_scan.py`).

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
```

### Run the API locally (no AWS needed)

Terminal 1, a local DynamoDB-compatible server:

```bash
source .venv/bin/activate
moto_server -p 5001
```

Terminal 2, the API:

```bash
source .venv/bin/activate
cd backend
cp .env.example .env                  # local settings; .env is git-ignored
export AWS_ACCESS_KEY_ID=local AWS_SECRET_ACCESS_KEY=local
unset AWS_PROFILE                     # this terminal only; keeps local runs away from real AWS
python -m scripts.create_local_table
uvicorn app.main:app --reload         # http://127.0.0.1:8000/docs
```

Send `X-Dev-User-Id: alice` with each request (the `/docs` page has no header field,
so use curl for authenticated calls).

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
