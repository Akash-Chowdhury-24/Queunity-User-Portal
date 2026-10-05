from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")

class APIResponse(BaseModel, Generic[T]):
    success : bool
    message : str
    data : T | None = None
    errors : Any | None = None


def success_response(
    data: T | None = None,
    message: str ="Successful"
) -> APIResponse[T]:
    return APIResponse(
        success=True,
        message=message,
        data=data,
        errors=None
    )
    
def error_response(
    errors : Any = None,
    message : str = "Something went wrong"
) -> APIResponse[None]:
    return APIResponse(
        success=False,
        message=message,
        data=None,
        errors=errors
    )

