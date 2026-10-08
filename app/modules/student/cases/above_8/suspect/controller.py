import asyncio

from fastapi import UploadFile
from pydantic import ValidationError

from app.common.general_schema import TokenPayload
from app.common.pagination import (
    ListQuery,
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
    SUSPECT_IMAGE_FOLDER,
    SUSPECT_PHYSICAL_FOLDER,
    SUSPECT_VEHICLE_FOLDER,
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
from app.modules.student.cases.above_8.suspect.schema import SuspectCreate, SuspectUpdate


def _validate_create(raw: dict, case_id: str) -> SuspectCreate:
    try:
        return SuspectCreate.model_validate({**raw, "caseId": case_id})
    except ValidationError as exc:
        raise APIException(
            status_code=422,
            message="Validation error",
            errors=reshape_validation_errors(exc),
        ) from exc


def _validate_update(raw: dict) -> SuspectUpdate:
    try:
        return SuspectUpdate.model_validate(raw)
    except ValidationError as exc:
        raise APIException(
            status_code=422,
            message="Validation error",
            errors=reshape_validation_errors(exc),
        ) from exc


async def _get_suspect_for_case(case_id: str, suspect_id: str):
    suspect = await prisma.suspect.find_unique(where={"id": suspect_id})
    if not suspect or suspect.caseId != case_id:
        raise APIException(status_code=404, message="Suspect not found")
    return suspect


async def create_suspect_controller(
    case_id: str,
    payload_json: str,
    current_user: TokenPayload,
    student_image: UploadFile | None = None,
    physical_files: list[UploadFile] | None = None,
    vehicle_files: list[UploadFile] | None = None,
):
    student = await get_above8_student(current_user)
    case = await get_case_or_404(case_id, student.id)

    raw = parse_json_object(payload_json)
    raw, uploaded, physical_urls, vehicle_urls = await attach_person_uploads(
        raw,
        student_image=student_image,
        physical_files=physical_files,
        vehicle_files=vehicle_files,
        student_folder=SUSPECT_IMAGE_FOLDER,
        physical_folder=SUSPECT_PHYSICAL_FOLDER,
        vehicle_folder=SUSPECT_VEHICLE_FOLDER,
        allow_student_image=True,
    )

    try:
        payload = _validate_create(raw, case_id)
        suspect = await prisma.suspect.create(
            data=person_write_data(
                payload,
                case_id,
                creating=True,
                physical_urls=physical_urls,
                vehicle_urls=vehicle_urls,
            )
        )
    except Exception:
        await delete_images(uploaded)
        raise

    if not suspect:
        await delete_images(uploaded)
        raise APIException(status_code=500, message="Failed to create suspect")

    await prisma.case.update(
        where={"id": case_id},
        data={"currentStage": next_stage(case.currentStage, 2)},
    )
    return success_response(message="Suspect created successfully", data=suspect)


async def get_all_suspects_controller(
    current_user: TokenPayload, case_id: str, query: ListQuery
):
    student = await get_above8_student(current_user)
    await get_case_or_404(case_id, student.id)
    where = merge_filters(
        {"caseId": case_id},
        text_search(
            query.search,
            "studentName",
            "personName",
            "organization",
            "contact",
            "extSchoolName",
            "extSchoolCity",
            "extSchoolState",
            "studentDetails",
            "behaviorObserved",
            "howIdentified",
            "howKnowThisPerson",
            "whereOnCampusSeen",
            "grade",
            "gender",
        ),
    )
    suspects, total = await asyncio.gather(
        prisma.suspect.find_many(
            where=where,
            order={"createdAt": "asc"},
            **prisma_paging(query.skip, query.limit),
        ),
        prisma.suspect.count(where=where),
    )
    return success_response(
        message="Suspects fetched successfully",
        data=paginated_data(suspects, total, query.skip, query.limit),
    )


async def get_suspect_by_id_controller(
    current_user: TokenPayload, case_id: str, suspect_id: str
):
    student = await get_above8_student(current_user)
    await get_case_or_404(case_id, student.id)
    suspect = await _get_suspect_for_case(case_id, suspect_id)
    return success_response(message="Suspect fetched successfully", data=suspect)


async def update_suspect_controller(
    case_id: str,
    suspect_id: str,
    payload_json: str,
    current_user: TokenPayload,
    student_image: UploadFile | None = None,
    physical_files: list[UploadFile] | None = None,
    vehicle_files: list[UploadFile] | None = None,
    existing_physical_file_urls: str | None = None,
    existing_vehicle_file_urls: str | None = None,
):
    student = await get_above8_student(current_user)
    case = await get_case_or_404(case_id, student.id)
    existing = await _get_suspect_for_case(case_id, suspect_id)

    raw = parse_json_object(payload_json)
    raw, uploaded, physical_urls, vehicle_urls = await attach_person_uploads(
        raw,
        student_image=student_image,
        physical_files=physical_files,
        vehicle_files=vehicle_files,
        student_folder=SUSPECT_IMAGE_FOLDER,
        physical_folder=SUSPECT_PHYSICAL_FOLDER,
        vehicle_folder=SUSPECT_VEHICLE_FOLDER,
        allow_student_image=True,
    )

    try:
        payload = _validate_update(raw)
        update_data = person_write_data(
            payload,
            case_id,
            physical_urls=combined_detail_urls(
                existing.physicalDetails,
                physical_urls,
                keep_existing=payload.physicalDetails is not None,
                keep_urls_json=existing_physical_file_urls,
                field_name="existingPhysicalFileUrls",
            ),
            vehicle_urls=combined_detail_urls(
                existing.vehicleDetails,
                vehicle_urls,
                keep_existing=payload.vehicleDetails is not None,
                keep_urls_json=existing_vehicle_file_urls,
                field_name="existingVehicleFileUrls",
            ),
        )
        updated = await prisma.suspect.update(
            where={"id": suspect_id},
            data=update_data,
        )
    except Exception:
        await delete_images(uploaded)
        raise

    if not updated:
        await delete_images(uploaded)
        raise APIException(status_code=500, message="Failed to update suspect")

    old_urls = set(person_file_urls(existing))
    new_urls = set(person_file_urls(updated))
    await delete_images(list(old_urls - new_urls))

    await prisma.case.update(
        where={"id": case_id},
        data={"currentStage": next_stage(case.currentStage, 2)},
    )
    return success_response(message="Suspect updated successfully", data=updated)


async def delete_suspect_controller(
    current_user: TokenPayload, case_id: str, suspect_id: str
):
    student = await get_above8_student(current_user)
    await get_case_or_404(case_id, student.id)
    await _get_suspect_for_case(case_id, suspect_id)

    deleted = await prisma.suspect.delete(where={"id": suspect_id})
    if not deleted:
        raise APIException(status_code=500, message="Failed to delete suspect")

    await delete_person_files(deleted)
    return success_response(message="Suspect deleted successfully", data=deleted)
