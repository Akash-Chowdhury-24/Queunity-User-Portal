import asyncio

from fastapi import UploadFile

from app.common.general_schema import TokenPayload
from app.common.pagination import (
    ListQuery,
    contains,
    merge_filters,
    paginated_data,
    prisma_paging,
    text_search,
)
from app.common.response import success_response
from app.common.s3 import delete_image, upload_image
from app.core.database import prisma
from app.core.exceptions import APIException
from app.modules.parent.cases.case.schema import (
    CaseStage1Create,
    CaseStage5Update,
    CaseStage6Update,
)
from app.modules.parent.cases.common import (
    CASE_INCLUDE,
    POLICE_REPORT_FOLDER,
    date_to_datetime,
    delete_case_files,
    ensure_charity_exists,
    ensure_stage1_references,
    get_case_or_404,
    get_current_parent,
    has_upload,
    next_stage,
    parent_cases_filter,
    public_case,
    to_prisma_data,
)
from app.modules.parent.cases.schema.enums import CaseStatus, PoliceInvolvement
from app.modules.parent.cases.schema.validate import is_others


def _stage1_data(payload: CaseStage1Create) -> dict:
    data = to_prisma_data(payload)
    data["incidentDate"] = date_to_datetime(payload.incidentDate)
    if is_others(data.get("schoolId")):
        data["schoolId"] = None
    return data


async def create_case_controller(payload: CaseStage1Create, current_user: TokenPayload):
    parent = await get_current_parent(current_user)
    await ensure_stage1_references(
        payload.schoolId,
        payload.offenseId,
        payload.offenseSubCategoryId,
        payload.victimId,
        parent.id,
        payload.gradeId,
    )

    case = await prisma.case.create(
        data={
            **_stage1_data(payload),
            "draft": True,
            "status": None,
            "currentStage": 1,
            "hasEvidence": False,
        },
        include=CASE_INCLUDE,
    )
    if not case:
        raise APIException(status_code=500, message="Failed to create case")

    return success_response(message="Case created successfully", data=public_case(case))


async def update_case_stage1_controller(
    case_id: str,
    payload: CaseStage1Create,
    current_user: TokenPayload,
):
    parent = await get_current_parent(current_user)
    case = await get_case_or_404(case_id, parent.id)
    await ensure_stage1_references(
        payload.schoolId,
        payload.offenseId,
        payload.offenseSubCategoryId,
        payload.victimId,
        parent.id,
        payload.gradeId,
    )

    updated = await prisma.case.update(
        where={"id": case_id},
        data={
            **_stage1_data(payload),
            "currentStage": next_stage(case.currentStage, 1),
        },
        include=CASE_INCLUDE,
    )
    if not updated:
        raise APIException(status_code=500, message="Failed to update case")

    return success_response(
        message="Case stage 1 updated successfully", data=public_case(updated)
    )


async def update_case_stage5_controller(
    case_id: str,
    payload: CaseStage5Update,
    police_report_image: UploadFile | None,
    current_user: TokenPayload,
):
    parent = await get_current_parent(current_user)
    case = await get_case_or_404(case_id, parent.id)
    await ensure_charity_exists(payload.charityId)

    new_image_url = None
    if has_upload(police_report_image):
        if payload.policeInvolvement != PoliceInvolvement.ALREADY_REPORTED:
            raise APIException(
                status_code=400,
                message="policeReportImage is only allowed when policeInvolvement is ALREADY_REPORTED",
            )
        new_image_url = await upload_image(police_report_image, folder=POLICE_REPORT_FOLDER)

    update_payload = payload
    if new_image_url:
        update_payload = payload.model_copy(update={"policeReportImageUrl": new_image_url})

    data = to_prisma_data(update_payload)
    data["policeReportDate"] = date_to_datetime(update_payload.policeReportDate)
    data["currentStage"] = next_stage(case.currentStage, 5)

    try:
        updated = await prisma.case.update(where={"id": case_id}, data=data)
    except Exception:
        if new_image_url:
            await delete_image(new_image_url)
        raise

    if not updated:
        if new_image_url:
            await delete_image(new_image_url)
        raise APIException(status_code=500, message="Failed to update case")

    old_image = case.policeReportImageUrl
    if old_image and old_image != updated.policeReportImageUrl:
        await delete_image(old_image)

    return success_response(
        message="Case stage 5 updated successfully", data=public_case(updated)
    )


async def update_case_stage6_controller(
    case_id: str,
    payload: CaseStage6Update,
    current_user: TokenPayload,
):
    parent = await get_current_parent(current_user)
    case = await get_case_or_404(case_id, parent.id)

    if case.charityInvolvement is None or case.policeInvolvement is None:
        raise APIException(
            status_code=400,
            message="Complete stage 5 (charity and police involvement) before submitting the case",
        )

    data = {
        "resolutionDesired": payload.resolutionDesired.value,
        "draft": False,
        "currentStage": 6,
    }
    if case.status is None:
        data["status"] = CaseStatus.PENDING.value

    updated = await prisma.case.update(
        where={"id": case_id},
        data=data,
        include=CASE_INCLUDE,
    )
    if not updated:
        raise APIException(status_code=500, message="Failed to submit case")

    message = (
        "Case submitted successfully"
        if case.draft
        else "Case stage 6 updated successfully"
    )
    return success_response(message=message, data=public_case(updated))


async def get_case_by_id_controller(current_user: TokenPayload, case_id: str):
    parent = await get_current_parent(current_user)
    case = await get_case_or_404(case_id, parent.id, include_children=True)
    return success_response(message="Case fetched successfully", data=public_case(case))


async def get_all_cases_controller(
    current_user: TokenPayload,
    query: ListQuery,
    status: CaseStatus | None = None,
    draft: bool | None = None,
    school_id: str | None = None,
    charity_id: str | None = None,
    offense_id: str | None = None,
    offense_sub_category_id: str | None = None,
    victim_id: str | None = None,
):
    parent = await get_current_parent(current_user)

    filters: dict = {}
    if status is not None:
        filters["status"] = status.value
    if draft is not None:
        filters["draft"] = draft
    if school_id is not None:
        filters["schoolId"] = school_id
    if charity_id is not None:
        filters["charityId"] = charity_id
    if offense_id is not None:
        filters["offenseId"] = offense_id
    if offense_sub_category_id is not None:
        filters["offenseSubCategoryId"] = offense_sub_category_id
    if victim_id is not None:
        filters["victimId"] = victim_id

    term = (query.search or "").strip()
    where = merge_filters(
        parent_cases_filter(parent.id),
        filters or None,
        text_search(
            query.search,
            "caseName",
            "otherSchoolName",
            "areaDescription",
            "policeReportNumber",
            "policeOfficerName",
            "policeStationDepartment",
            "charityNameFallback",
            extra=(
                [
                    {"grade": {"is": {"gradeName": contains(term)}}},
                    {"school": {"is": {"name": contains(term)}}},
                    {"offense": {"is": {"offenseName": contains(term)}}},
                    {
                        "offenseSubCategory": {
                            "is": {"offenseSubCategoryName": contains(term)}
                        }
                    },
                    {"charity": {"is": {"name": contains(term)}}},
                    {"victim": {"is": {"firstName": contains(term)}}},
                    {"victim": {"is": {"lastName": contains(term)}}},
                ]
                if term
                else None
            ),
        ),
    )

    cases, total = await asyncio.gather(
        prisma.case.find_many(
            where=where,
            include=CASE_INCLUDE,
            order={"createdAt": "desc"},
            **prisma_paging(query.skip, query.limit),
        ),
        prisma.case.count(where=where),
    )
    return success_response(
        message="Cases fetched successfully",
        data=paginated_data(
            [public_case(case) for case in cases], total, query.skip, query.limit
        ),
    )


async def delete_case_controller(current_user: TokenPayload, case_id: str):
    parent = await get_current_parent(current_user)
    await get_case_or_404(case_id, parent.id)

    deleted = await prisma.case.delete(
        where={"id": case_id},
        include=CASE_INCLUDE,
    )
    if not deleted:
        raise APIException(status_code=500, message="Failed to delete case")

    await delete_case_files(deleted)
    return success_response(message="Case deleted successfully", data=public_case(deleted))
