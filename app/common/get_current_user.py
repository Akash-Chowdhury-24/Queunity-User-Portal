from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError

from app.common.general_schema import TokenPayload
from app.core.exceptions import APIException
from app.core.security import verify_token

security_scheme = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> TokenPayload:
    if not credentials or not credentials.credentials:
        raise APIException(status_code=401, message="Unauthorized no token provided")

    payload = verify_token(credentials.credentials)

    try:
        return TokenPayload.model_validate(payload)
    except ValidationError as exc:
        raise APIException(status_code=401, message="Invalid token") from exc
