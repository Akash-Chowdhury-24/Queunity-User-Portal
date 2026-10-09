from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends
from starlette.status import HTTP_200_OK, HTTP_201_CREATED

from app.common.general_schema import TokenPayload
from app.common.get_current_user import get_current_user
from app.common.pagination import ListQuery, list_query
from app.modules.student.cases.below_8.controller import (
    create_case_controller,
    delete_case_controller,
    get_all_cases_controller,
    get_case_by_id_controller,
    update_case_controller,
)
from app.modules.student.cases.below_8.schema import CaseCreateModel, CaseUpdateModel

studentBelow8CasesRouter = APIRouter()
CurrentUser = Annotated[TokenPayload, Depends(get_current_user)]


@studentBelow8CasesRouter.post("", status_code=HTTP_201_CREATED)
async def create_case(
    payload: CaseCreateModel,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
):
    return await create_case_controller(payload, current_user, background_tasks)


@studentBelow8CasesRouter.get("", status_code=HTTP_200_OK)
async def get_all_cases(
    current_user: CurrentUser,
    query: Annotated[ListQuery, Depends(list_query)],
):
    return await get_all_cases_controller(current_user, query)


@studentBelow8CasesRouter.get("/{case_id}", status_code=HTTP_200_OK)
async def get_case_by_id(case_id: str, current_user: CurrentUser):
    return await get_case_by_id_controller(case_id, current_user)


@studentBelow8CasesRouter.patch("/{case_id}", status_code=HTTP_200_OK)
async def update_case(
    case_id: str,
    payload: CaseUpdateModel,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
):
    return await update_case_controller(case_id, payload, current_user, background_tasks)


@studentBelow8CasesRouter.delete("/{case_id}", status_code=HTTP_200_OK)
async def delete_case(case_id: str, current_user: CurrentUser):
    return await delete_case_controller(case_id, current_user)
