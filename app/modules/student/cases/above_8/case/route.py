from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from pydantic import ValidationError
from starlette.status import HTTP_200_OK, HTTP_201_CREATED

from app.common.general_schema import TokenPayload
from app.common.get_current_user import get_current_user
from app.common.pagination import ListQuery, list_query
from app.core.exceptions import APIException
from app.modules.student.cases.above_8.case.controller import (
    create_case_controller,
    delete_case_controller,
    get_all_cases_controller,
    get_case_by_id_controller,
    update_case_stage1_controller,
    update_case_stage5_controller,
    update_case_stage6_controller,
)
from app.modules.student.cases.above_8.case.schema import (
    CaseStage1Create,
    CaseStage5Update,
    CaseStage6Update,
)
from app.modules.student.cases.above_8.common import reshape_validation_errors
from app.modules.student.cases.above_8.schema.enums import (
    CaseStatus,
    CharityInvolvement,
    CharityType,
    PoliceInvolvement,
)

studentCasesRouter = APIRouter()
CurrentUser = Annotated[TokenPayload, Depends(get_current_user)]


@studentCasesRouter.post("", status_code=HTTP_201_CREATED)
async def create_case(payload: CaseStage1Create, current_user: CurrentUser):
    return await create_case_controller(payload, current_user)


@studentCasesRouter.get("", status_code=HTTP_200_OK)
async def get_all_cases(
    current_user: CurrentUser,
    query: Annotated[ListQuery, Depends(list_query)],
    status: CaseStatus | None = Query(
        default=None,
        description="Filter by PENDING or RESOLVED",
    ),
    draft: bool | None = Query(
        default=None,
        description="true for in-progress cases, false for submitted cases",
    ),
    schoolId: str | None = Query(default=None),
    charityId: str | None = Query(default=None),
    offenseId: str | None = Query(default=None),
    offenseSubCategoryId: str | None = Query(default=None),
):
    return await get_all_cases_controller(
        current_user,
        query,
        status=status,
        draft=draft,
        school_id=schoolId,
        charity_id=charityId,
        offense_id=offenseId,
        offense_sub_category_id=offenseSubCategoryId,
    )


@studentCasesRouter.get("/{case_id}", status_code=HTTP_200_OK)
async def get_case_by_id(case_id: str, current_user: CurrentUser):
    return await get_case_by_id_controller(current_user, case_id)


@studentCasesRouter.patch("/{case_id}/stage1", status_code=HTTP_200_OK)
async def update_case_stage1(
    case_id: str,
    payload: CaseStage1Create,
    current_user: CurrentUser,
):
    return await update_case_stage1_controller(case_id, payload, current_user)


@studentCasesRouter.patch("/{case_id}/stage5", status_code=HTTP_200_OK)
async def update_case_stage5(
    case_id: str,
    current_user: CurrentUser,
    charityInvolvement: Annotated[CharityInvolvement, Form()],
    policeInvolvement: Annotated[PoliceInvolvement, Form()],
    charityId: Annotated[str | None, Form()] = None,
    charityNameFallback: Annotated[str | None, Form()] = None,
    charityTypeRequested: Annotated[CharityType | None, Form()] = None,
    charityInvolvementReason: Annotated[str | None, Form()] = None,
    policeReportNumber: Annotated[str | None, Form()] = None,
    policeOfficerName: Annotated[str | None, Form()] = None,
    policeStationDepartment: Annotated[str | None, Form()] = None,
    policeReportDate: Annotated[str | None, Form()] = None,
    policeReportImageUrl: Annotated[str | None, Form()] = None,
    policeReportImage: Annotated[UploadFile | None, File()] = None,
):
    parsed_date = None
    if policeReportDate:
        try:
            parsed_date = date.fromisoformat(policeReportDate)
        except ValueError as exc:
            raise APIException(
                status_code=400,
                message="policeReportDate must be a valid ISO date (YYYY-MM-DD)",
            ) from exc

    try:
        payload = CaseStage5Update(
            charityInvolvement=charityInvolvement,
            charityId=charityId,
            charityNameFallback=charityNameFallback,
            charityTypeRequested=charityTypeRequested,
            charityInvolvementReason=charityInvolvementReason,
            policeInvolvement=policeInvolvement,
            policeReportNumber=policeReportNumber,
            policeOfficerName=policeOfficerName,
            policeStationDepartment=policeStationDepartment,
            policeReportDate=parsed_date,
            policeReportImageUrl=policeReportImageUrl,
        )
    except ValidationError as exc:
        raise APIException(
            status_code=422,
            message="Validation error",
            errors=reshape_validation_errors(exc),
        ) from exc

    return await update_case_stage5_controller(
        case_id, payload, policeReportImage, current_user
    )


@studentCasesRouter.patch("/{case_id}/stage6", status_code=HTTP_200_OK)
async def update_case_stage6(
    case_id: str,
    payload: CaseStage6Update,
    current_user: CurrentUser,
):
    return await update_case_stage6_controller(case_id, payload, current_user)


@studentCasesRouter.delete("/{case_id}", status_code=HTTP_200_OK)
async def delete_case(case_id: str, current_user: CurrentUser):
    return await delete_case_controller(current_user, case_id)
