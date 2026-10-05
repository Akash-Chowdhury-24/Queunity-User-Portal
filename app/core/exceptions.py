import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from prisma.errors import PrismaError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.common.response import error_response

logger = logging.getLogger("app")


class APIException(Exception):
    def __init__(
        self,
        status_code: int,
        message: str,
        errors: Any = None,
    ) -> None:
        self.status_code = status_code
        self.message = message
        self.errors = errors
        super().__init__(message)


# this is a helper function to convert the exception to a JSON response
def _json_error(status_code: int, message: str, errors: Any = None) -> JSONResponse:
    payload = error_response(message=message, errors=errors)
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


# this is a helper function to reshape the validation errors especially for pydantic validation errors
def _reshape_validation_errors(exc: RequestValidationError) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for err in exc.errors():
        loc = err.get("loc", ())
        field_parts = [str(part) for part in loc if part not in {"body", "query", "path", "header"}]
        errors.append(
            {
                "field": ".".join(field_parts) if field_parts else ".".join(str(part) for part in loc),
                "message": err.get("msg"),
                "type": err.get("type"),
            }
        )
    return errors


# this is a helper function to register the exception handlers
def register_exception_handlers(app: FastAPI) -> None:
    # this is a custom exception handler for the APIException
    @app.exception_handler(APIException)
    async def app_exception_handler(_request: Request, exc: APIException) -> JSONResponse:
        return _json_error(exc.status_code, exc.message, exc.errors)

    # this is a custom exception handler for the RequestValidationError 
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _json_error(422, "Validation error", _reshape_validation_errors(exc))

    # this is a custom exception handler for the StarletteHTTPException
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        errors = None if isinstance(exc.detail, str) else exc.detail
        return _json_error(exc.status_code, message, errors)

    # this is a custom exception handler for the PrismaError
    @app.exception_handler(PrismaError)
    async def prisma_exception_handler(_request: Request, exc: PrismaError) -> JSONResponse:
        logger.exception("Unhandled Prisma error")
        return _json_error(500, "Internal server error")

    # this is a custom exception handler for the Exception
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception")
        return _json_error(500, "Internal server error")
