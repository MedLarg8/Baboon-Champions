from fastapi import HTTPException

from app.services.riot import RiotApiError


def riot_http_exception(exc: RiotApiError) -> HTTPException:
    headers = (
        {"Retry-After": str(exc.retry_after_seconds)}
        if exc.retry_after_seconds is not None
        else None
    )
    return HTTPException(status_code=exc.status_code, detail=exc.detail, headers=headers)
