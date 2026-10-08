from typing import Annotated

from fastapi import APIRouter, Depends, File, Form
from starlette.status import HTTP_200_OK, HTTP_201_CREATED

from app.common.general_schema import TokenPayload
from app.common.get_current_user import get_current_user
from app.common.pagination import ListQuery, list_query
from app.modules.student.cases.above_8.common import OptionalUploadFiles
from app.modules.student.cases.above_8.witness.controller import (
    create_witness_controller,
    delete_witness_controller,
    get_all_witnesses_controller,
    get_witness_by_id_controller,
    update_witness_controller,
)

studentWitnessesRouter = APIRouter()
CurrentUser = Annotated[TokenPayload, Depends(get_current_user)]


@studentWitnessesRouter.post("", status_code=HTTP_201_CREATED)
async def create_witness(
    case_id: str,
    current_user: CurrentUser,
    payload: Annotated[str, Form()],
    physicalFiles: Annotated[
        OptionalUploadFiles,
        File(description="Physical appearance photos. Stored URLs are returned on physicalDetails.files."),
    ] = None,
    vehicleFiles: Annotated[
        OptionalUploadFiles,
        File(description="Vehicle photos. Stored URLs are returned on vehicleDetails.files."),
    ] = None,
):
    return await create_witness_controller(
        case_id,
        payload,
        current_user,
        physical_files=physicalFiles,
        vehicle_files=vehicleFiles,
    )


@studentWitnessesRouter.get("", status_code=HTTP_200_OK)
async def get_all_witnesses(
    case_id: str,
    current_user: CurrentUser,
    query: Annotated[ListQuery, Depends(list_query)],
):
    return await get_all_witnesses_controller(current_user, case_id, query)


@studentWitnessesRouter.get("/{witness_id}", status_code=HTTP_200_OK)
async def get_witness_by_id(case_id: str, witness_id: str, current_user: CurrentUser):
    return await get_witness_by_id_controller(current_user, case_id, witness_id)


@studentWitnessesRouter.patch("/{witness_id}", status_code=HTTP_200_OK)
async def update_witness(
    case_id: str,
    witness_id: str,
    current_user: CurrentUser,
    payload: Annotated[str, Form()],
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
    return await update_witness_controller(
        case_id,
        witness_id,
        payload,
        current_user,
        physical_files=physicalFiles,
        vehicle_files=vehicleFiles,
        existing_physical_file_urls=existingPhysicalFileUrls,
        existing_vehicle_file_urls=existingVehicleFileUrls,
    )


@studentWitnessesRouter.delete("/{witness_id}", status_code=HTTP_200_OK)
async def delete_witness(case_id: str, witness_id: str, current_user: CurrentUser):
    return await delete_witness_controller(current_user, case_id, witness_id)
