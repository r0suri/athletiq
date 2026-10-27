"""Resolve the authenticated user for a request.

Cognito mode (deployed): API Gateway's JWT authorizer has already verified the
token's signature, issuer, audience/client and expiry before Lambda runs. We read
the verified claims from the API Gateway event (passed through by Mangum) and never
parse the Authorization header ourselves.

Local mode (development and tests only): the user id comes from X-Dev-User-Id.
Settings refuse to load with AUTH_MODE=local outside local/test or inside Lambda.

Every data access uses CurrentUser.user_id to build DynamoDB keys, so a user can
only ever address their own items.
"""

import re
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.core.errors import UnauthorizedError

DEV_USER_HEADER = "X-Dev-User-Id"
_USER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


@dataclass(frozen=True)
class CurrentUser:
    user_id: str


def _verified_claims(request: Request) -> dict:
    event = request.scope.get("aws.event") or {}
    return (
        event.get("requestContext", {}).get("authorizer", {}).get("jwt", {}).get("claims", {}) or {}
    )


def get_current_user(
    request: Request, settings: Annotated[Settings, Depends(get_settings)]
) -> CurrentUser:
    if settings.auth_mode == "local":
        user_id = request.headers.get(DEV_USER_HEADER, "")
        if not _USER_ID_PATTERN.fullmatch(user_id):
            raise UnauthorizedError(
                f"Local auth mode: send a {DEV_USER_HEADER} header (letters, digits, - or _)."
            )
        return CurrentUser(user_id=user_id)

    sub = _verified_claims(request).get("sub", "")
    if not isinstance(sub, str) or not _USER_ID_PATTERN.fullmatch(sub):
        raise UnauthorizedError("Missing or invalid authentication.")
    return CurrentUser(user_id=sub)


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
