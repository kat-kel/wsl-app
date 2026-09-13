import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from app.config import get_settings

API_KEY_HEADER_NAME = "X-API-Key"

api_key_header = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)


def require_write_access(
    api_key: Annotated[str | None, Depends(api_key_header)],
) -> None:
    if api_key is not None:
        # compare_digest needs bytes: it raises TypeError on non-ASCII str input.
        presented = api_key.encode("utf-8")
        if any(
            secrets.compare_digest(presented, accepted.encode("utf-8"))
            for accepted in get_settings().write_api_key_list
        ):
            return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid API key",
    )
