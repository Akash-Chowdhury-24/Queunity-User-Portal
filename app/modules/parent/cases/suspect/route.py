from typing import Annotated

from fastapi import APIRouter, Depends, File, Form
from starlette.status import HTTP_200_OK, HTTP_201_CREATED

from app.common.general_schema import TokenPayload
from app.common.get_current_user import get_current_user
from app.common.pagination import ListQuery, list_query
from app.modules.parent.cases.common import OptionalUploadFile, OptionalUploadFiles
from app.modules.parent.cases.suspect.controller import (
    create_suspect_controller,
    delete_suspect_controller,
    get_all_suspects_controller,
    get_suspect_by_id_controller,
    update_suspect_controller,
)

parentSuspectsRouter = APIRouter()
CurrentUser = Annotated[TokenPayload, Depends(get_current_user)]


@parentSuspectsRouter.post("", status_code=HTTP_201_CREATED)
async def create_suspect(
    case_id: str,
    current_user: CurrentUser,
    payload: Annotated[str, Form()],
    studentImage: Annotated[OptionalUploadFile, File()] = None,
    physicalFiles: Annotated[
        OptionalUploadFiles,
        File(description="Physical appearance photos. Stored URLs are returned on physicalDetails.files."),
    ] = None,
    vehicleFiles: Annotated[
        OptionalUploadFiles,
        File(description="Vehicle photos. Stored URLs are returned on vehicleDetails.files."),
    ] = None,
):
    return await create_suspect_controller(
        case_id,
        payload,
        current_user,
        student_image=studentImage,
        physical_files=physicalFiles,
        vehicle_files=vehicleFiles,
    )


@parentSuspectsRouter.get("", status_code=HTTP_200_OK)
async def get_all_suspects(
    case_id: str,
    current_user: CurrentUser,
    query: Annotated[ListQuery, Depends(list_query)],
):
    return await get_all_suspects_controller(current_user, case_id, query)


@parentSuspectsRouter.get("/{suspect_id}", status_code=HTTP_200_OK)
async def get_suspect_by_id(case_id: str, suspect_id: str, current_user: CurrentUser):
    return await get_suspect_by_id_controller(current_user, case_id, suspect_id)


@parentSuspectsRouter.patch("/{suspect_id}", status_code=HTTP_200_OK)
async def update_suspect(
    case_id: str,
    suspect_id: str,
    current_user: CurrentUser,
    payload: Annotated[str, Form()],
    studentImage: Annotated[OptionalUploadFile, File()] = None,
    physicalFiles: Annotated[
        OptionalUploadFiles,
        File(description="Physical appearance photos. Stored URLs are returned on physicalDetails.files."),
    ] = None,
    vehicleFiles: Annotated[
        OptionalUploadFiles,
        File(description="Vehicle photos. Stored URLs are returned on vehicleDetails.files."),
    ] = None,
    existingPhysicalFileUrls: Annotated[
        str | None,
        Form(description='JSON array of existing physical image URLs to keep, e.g. ["https://..."]. Omit to keep all.'),
    ] = None,
    existingVehicleFileUrls: Annotated[
        str | None,
        Form(description='JSON array of existing vehicle image URLs to keep, e.g. ["https://..."]. Omit to keep all.'),
    ] = None,
):
    return await update_suspect_controller(
        case_id,
        suspect_id,
        payload,
        current_user,
        student_image=studentImage,
        physical_files=physicalFiles,
        vehicle_files=vehicleFiles,
        existing_physical_file_urls=existingPhysicalFileUrls,
        existing_vehicle_file_urls=existingVehicleFileUrls,
    )


@parentSuspectsRouter.delete("/{suspect_id}", status_code=HTTP_200_OK)
async def delete_suspect(case_id: str, suspect_id: str, current_user: CurrentUser):
    return await delete_suspect_controller(current_user, case_id, suspect_id)
