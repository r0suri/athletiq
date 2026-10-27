"""Structured JSON logging shared by the whole application.

AWS Lambda Powertools emits one JSON object per log line, which CloudWatch Logs
Insights can query by field (e.g. `filter status_code >= 500`).
Rule: log request metadata (ids, route, status, latency), never request bodies.
"""

from aws_lambda_powertools import Logger

from app.core.config import get_settings

logger = Logger(service="athletiq", level=get_settings().log_level)
