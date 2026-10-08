from typing import Annotated

from fastapi import APIRouter, Depends, File, Form
from starlette.status import HTTP_200_OK, HTTP_201_CREATED

from app.common.general_schema import TokenPayload
from app.common.get_current_user import get_current_user
from app.common.pagination import ListQuery, list_query
from app.modules.parent.cases.common import OptionalUploadFiles
from app.modules.parent.cases.evidence.controller import (
    create_evidence_controller,
    delete_evidence_controller,
    get_all_evidence_controller,
    get_evidence_by_id_controller,
    update_evidence_controller,
)

parentEvidenceRouter = APIRouter()
CurrentUser = Annotated[TokenPayload, Depends(get_current_user)]


@parentEvidenceRouter.post("", status_code=HTTP_201_CREATED)
async def create_evidence(
    case_id: str,
    current_user: CurrentUser,
    description: Annotated[str | None, Form()] = None,
    files: Annotated[OptionalUploadFiles, File()] = None,
):
    return await create_evidence_controller(
        case_id,
        current_user,
        description=description,
        files=files,
    )


@parentEvidenceRouter.get("", status_code=HTTP_200_OK)
async def get_all_evidence(
    case_id: str,
    current_user: CurrentUser,
    query: Annotated[ListQuery, Depends(list_query)],
):
    return await get_all_evidence_controller(current_user, case_id, query)


@parentEvidenceRouter.get("/{evidence_id}", status_code=HTTP_200_OK)
async def get_evidence_by_id(case_id: str, evidence_id: str, current_user: CurrentUser):
    return await get_evidence_by_id_controller(current_user, case_id, evidence_id)


@parentEvidenceRouter.patch("/{evidence_id}", status_code=HTTP_200_OK)
async def update_evidence(
    case_id: str,
    evidence_id: str,
    current_user: CurrentUser,
    description: Annotated[str | None, Form()] = None,
    existingFileUrls: Annotated[str | None, Form()] = None,
    files: Annotated[OptionalUploadFiles, File()] = None,
):
    return await update_evidence_controller(
        case_id,
        evidence_id,
        current_user,
        description=description,
        existing_file_urls=existingFileUrls,
        files=files,
    )


@parentEvidenceRouter.delete("/{evidence_id}", status_code=HTTP_200_OK)
async def delete_evidence(case_id: str, evidence_id: str, current_user: CurrentUser):
    return await delete_evidence_controller(current_user, case_id, evidence_id)
