from datetime import date
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form
from pydantic import ValidationError
from starlette.status import HTTP_200_OK, HTTP_201_CREATED

from app.common.general_schema import TokenPayload
from app.common.get_current_user import get_current_user
from app.core.exceptions import APIException
from app.modules.parent.cases.common import OptionalUploadFile, reshape_validation_errors
from app.modules.parent.child.controller import (
    create_child_controller,
    get_all_children_controller,
    get_child_by_id_controller,
    get_school_by_public_id_controller,
    remove_child_controller,
    update_child_controller,
)
from app.modules.parent.child.schema import ChildCreateModel, ChildUpdateModel, Gender

parentSchoolLookupRouter = APIRouter()
parentChildrenRouter = APIRouter()
CurrentUser = Annotated[TokenPayload, Depends(get_current_user)]


def _validated(model, **fields):
    try:
        return model(**fields)
    except ValidationError as exc:
        raise APIException(
            status_code=422,
            message="Validation error",
            errors=reshape_validation_errors(exc),
        ) from exc


@parentSchoolLookupRouter.get("/{school_public_id}", status_code=HTTP_200_OK)
async def get_school_by_public_id(school_public_id: str, current_user: CurrentUser):
    return await get_school_by_public_id_controller(school_public_id, current_user)


@parentChildrenRouter.get("", status_code=HTTP_200_OK)
async def get_all_children(current_user: CurrentUser):
    return await get_all_children_controller(current_user)


@parentChildrenRouter.get("/{child_id}", status_code=HTTP_200_OK)
async def get_child_by_id(child_id: str, current_user: CurrentUser):
    return await get_child_by_id_controller(child_id, current_user)


@parentChildrenRouter.post("", status_code=HTTP_201_CREATED)
async def create_child(
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    schoolPublicId: Annotated[str, Form()],
    firstName: Annotated[str, Form()],
    lastName: Annotated[str, Form()],
    email: Annotated[str, Form()],
    dateOfBirth: Annotated[date, Form()],
    gradeId: Annotated[str, Form()],
    gender: Annotated[Gender, Form()],
    photo: Annotated[OptionalUploadFile, File()] = None,
):
    payload = _validated(
        ChildCreateModel,
        schoolPublicId=schoolPublicId,
        firstName=firstName,
        lastName=lastName,
        email=email,
        dateOfBirth=dateOfBirth,
        gradeId=gradeId,
        gender=gender,
    )
    return await create_child_controller(payload, photo, current_user, background_tasks)


@parentChildrenRouter.put("/{child_id}", status_code=HTTP_200_OK)
async def update_child(
    child_id: str,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    schoolPublicId: Annotated[str | None, Form()] = None,
    firstName: Annotated[str | None, Form()] = None,
    lastName: Annotated[str | None, Form()] = None,
    dateOfBirth: Annotated[str | None, Form()] = None,
    gradeId: Annotated[str | None, Form()] = None,
    gender: Annotated[str | None, Form()] = None,
    photo: Annotated[OptionalUploadFile, File()] = None,
):
    payload = _validated(
        ChildUpdateModel,
        schoolPublicId=schoolPublicId,
        firstName=firstName,
        lastName=lastName,
        dateOfBirth=dateOfBirth,
        gradeId=gradeId,
        gender=gender,
    )
    return await update_child_controller(child_id, payload, photo, current_user, background_tasks)


@parentChildrenRouter.delete("/{child_id}", status_code=HTTP_200_OK)
async def remove_child(child_id: str, current_user: CurrentUser):
    return await remove_child_controller(child_id, current_user)
