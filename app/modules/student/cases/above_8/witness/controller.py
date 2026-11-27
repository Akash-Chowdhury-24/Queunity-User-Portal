import asyncio

from fastapi import UploadFile
from pydantic import ValidationError

from app.common.general_schema import TokenPayload
from app.common.location import LOCATION_INCLUDE, validate_location_ids
from app.common.pagination import (
    ListQuery,
    contains,
    merge_filters,
    paginated_data,
    prisma_paging,
    text_search,
)
from app.common.response import success_response
from app.common.s3 import delete_images
from app.core.database import prisma
from app.core.exceptions import APIException
from app.modules.student.cases.above_8.common import (
    WITNESS_PHYSICAL_FOLDER,
    WITNESS_VEHICLE_FOLDER,
    attach_person_uploads,
    combined_detail_urls,
    delete_person_files,
    get_above8_student,
    get_case_or_404,
    next_stage,
    parse_json_object,
    person_file_urls,
    person_write_data,
    reshape_validation_errors,
)
from app.modules.student.cases.above_8.schema.enums import PersonRelationship
from app.modules.student.cases.above_8.witness.schema import WitnessCreate, WitnessUpdate

WITNESS_INCLUDE = {**LOCATION_INCLUDE}


def _validate_create(raw: dict, case_id: str) -> WitnessCreate:
    try:
        return WitnessCreate.model_validate({**raw, "caseId": case_id})
    except ValidationError as exc:
        raise APIException(
            status_code=422,
            message="Validation error",
            errors=reshape_validation_errors(exc),
        ) from exc


def _validate_update(raw: dict) -> WitnessUpdate:
    try:
        return WitnessUpdate.model_validate(raw)
    except ValidationError as exc:
        raise APIException(
            status_code=422,
            message="Validation error",
            errors=reshape_validation_errors(exc),
        ) from exc


async def _get_witness_for_case(case_id: str, witness_id: str):
    witness = await prisma.witness.find_unique(
        where={"id": witness_id},
        include=WITNESS_INCLUDE,
    )
    if not witness or witness.caseId != case_id:
        raise APIException(status_code=404, message="Witness not found")
    return witness


async def _witness_write_data(payload, case_id: str, **kwargs) -> dict:
    data = person_write_data(payload, case_id, **kwargs)
    if payload.relationship == PersonRelationship.EXTERNAL_STUDENT:
        validated = await validate_location_ids(
            country_id=payload.countryId,
            state_id=payload.stateId,
            city_id=payload.cityId,
        )
        data.update(validated)
        data["extSchoolCity"] = None
        data["extSchoolState"] = None
    else:
        data["countryId"] = None
        data["stateId"] = None
        data["cityId"] = None
    return data


async def create_witness_controller(
    case_id: str,
    payload_json: str,
    current_user: TokenPayload,
    physical_files: list[UploadFile] | None = None,
    vehicle_files: list[UploadFile] | None = None,
):
    student = await get_above8_student(current_user)
    case = await get_case_or_404(case_id, student.id)

    raw = parse_json_object(payload_json)
    raw, uploaded, physical_urls, vehicle_urls = await attach_person_uploads(
        raw,
        physical_files=physical_files,
        vehicle_files=vehicle_files,
        physical_folder=WITNESS_PHYSICAL_FOLDER,
        vehicle_folder=WITNESS_VEHICLE_FOLDER,
        allow_student_image=False,
    )

    try:
        payload = _validate_create(raw, case_id)
        witness = await prisma.witness.create(
            data=await _witness_write_data(
                payload,
                case_id,
                creating=True,
                physical_urls=physical_urls,
                vehicle_urls=vehicle_urls,
            ),
            include=WITNESS_INCLUDE,
        )
    except Exception:
        await delete_images(uploaded)
        raise

    if not witness:
        await delete_images(uploaded)
        raise APIException(status_code=500, message="Failed to create witness")

    await prisma.case.update(
        where={"id": case_id},
        data={"currentStage": next_stage(case.currentStage, 3)},
    )
    return success_response(message="Witness created successfully", data=witness)


async def get_all_witnesses_controller(
    current_user: TokenPayload, case_id: str, query: ListQuery
):
    student = await get_above8_student(current_user)
    await get_case_or_404(case_id, student.id)
    term = (query.search or "").strip()
    where = merge_filters(
        {"caseId": case_id},
        text_search(
            query.search,
            "studentName",
            "personName",
            "organization",
            "contact",
            "extSchoolName",
            "witnessStatement",
            "studentDetails",
            "howIdentified",
            "howConnectedToIncident",
            "behaviorObserved",
            "grade",
            "gender",
            extra=(
                [
                    {"country": {"is": {"name": contains(term)}}},
                    {"state": {"is": {"name": contains(term)}}},
                    {"city": {"is": {"name": contains(term)}}},
                ]
                if term
                else None
            ),
        ),
    )
    witnesses, total = await asyncio.gather(
        prisma.witness.find_many(
            where=where,
            include=WITNESS_INCLUDE,
            order={"createdAt": "asc"},
            **prisma_paging(query.skip, query.limit),
        ),
        prisma.witness.count(where=where),
    )
    return success_response(
        message="Witnesses fetched successfully",
        data=paginated_data(witnesses, total, query.skip, query.limit),
    )


async def get_witness_by_id_controller(
    current_user: TokenPayload, case_id: str, witness_id: str
):
    student = await get_above8_student(current_user)
    await get_case_or_404(case_id, student.id)
    witness = await _get_witness_for_case(case_id, witness_id)
    return success_response(message="Witness fetched successfully", data=witness)


async def update_witness_controller(
    case_id: str,
    witness_id: str,
    payload_json: str,
    current_user: TokenPayload,
    physical_files: list[UploadFile] | None = None,
    vehicle_files: list[UploadFile] | None = None,
    existing_physical_file_urls: str | None = None,
    existing_vehicle_file_urls: str | None = None,
):
    student = await get_above8_student(current_user)
    case = await get_case_or_404(case_id, student.id)
    existing = await _get_witness_for_case(case_id, witness_id)

    raw = parse_json_object(payload_json)
    raw, uploaded, physical_urls, vehicle_urls = await attach_person_uploads(
        raw,
        physical_files=physical_files,
        vehicle_files=vehicle_files,
        physical_folder=WITNESS_PHYSICAL_FOLDER,
        vehicle_folder=WITNESS_VEHICLE_FOLDER,
        allow_student_image=False,
    )

    try:
        payload = _validate_update(raw)
        keep_existing = not payload.isKnown
        updated = await prisma.witness.update(
            where={"id": witness_id},
            data=await _witness_write_data(
                payload,
                case_id,
                physical_urls=combined_detail_urls(
                    existing.physicalDetails,
                    physical_urls,
                    keep_existing=keep_existing,
                    keep_urls_json=existing_physical_file_urls,
                    field_name="existingPhysicalFileUrls",
                ),
                vehicle_urls=combined_detail_urls(
                    existing.vehicleDetails,
                    vehicle_urls,
                    keep_existing=keep_existing,
                    keep_urls_json=existing_vehicle_file_urls,
                    field_name="existingVehicleFileUrls",
                ),
            ),
            include=WITNESS_INCLUDE,
        )
    except Exception:
        await delete_images(uploaded)
        raise

    if not updated:
        await delete_images(uploaded)
        raise APIException(status_code=500, message="Failed to update witness")

    old_urls = set(person_file_urls(existing))
    new_urls = set(person_file_urls(updated))
    await delete_images(list(old_urls - new_urls))

    await prisma.case.update(
        where={"id": case_id},
        data={"currentStage": next_stage(case.currentStage, 3)},
    )
    return success_response(message="Witness updated successfully", data=updated)


async def delete_witness_controller(
    current_user: TokenPayload, case_id: str, witness_id: str
):
    student = await get_above8_student(current_user)
    await get_case_or_404(case_id, student.id)
    await _get_witness_for_case(case_id, witness_id)

    deleted = await prisma.witness.delete(where={"id": witness_id})
    if not deleted:
        raise APIException(status_code=500, message="Failed to delete witness")

    await delete_person_files(deleted)
    return success_response(message="Witness deleted successfully", data=deleted)
