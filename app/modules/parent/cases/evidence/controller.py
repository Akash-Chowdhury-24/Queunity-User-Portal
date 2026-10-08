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
from app.modules.parent.cases.common import (
    EVIDENCE_FOLDER,
    get_case_or_404,
    get_current_parent,
    next_stage,
    parse_json_string_list,
    reshape_validation_errors,
    upload_images,
)
from app.modules.parent.cases.evidence.schema import EvidenceCreate, EvidenceUpdate


def _validate_create(case_id: str, file_urls: list[str], description: str | None) -> EvidenceCreate:
    try:
        return EvidenceCreate(
            caseId=case_id,
            fileUrls=file_urls,
            description=description,
        )
    except ValidationError as exc:
        raise APIException(
            status_code=422,
            message="Validation error",
            errors=reshape_validation_errors(exc),
        ) from exc


def _validate_update(file_urls: list[str] | None, description: str | None) -> EvidenceUpdate:
    try:
        return EvidenceUpdate(fileUrls=file_urls, description=description)
    except ValidationError as exc:
        raise APIException(
            status_code=422,
            message="Validation error",
            errors=reshape_validation_errors(exc),
        ) from exc


async def _get_evidence_for_case(case_id: str, evidence_id: str):
    evidence = await prisma.evidence.find_unique(where={"id": evidence_id})
    if not evidence or evidence.caseId != case_id:
        raise APIException(status_code=404, message="Evidence not found")
    return evidence


async def _sync_has_evidence(case_id: str, current_stage: int) -> None:
    remaining = await prisma.evidence.count(where={"caseId": case_id})
    await prisma.case.update(
        where={"id": case_id},
        data={
            "hasEvidence": remaining > 0,
            "currentStage": next_stage(current_stage, 4) if remaining > 0 else current_stage,
        },
    )


async def create_evidence_controller(
    case_id: str,
    current_user: TokenPayload,
    description: str | None = None,
    files: list[UploadFile] | None = None,
):
    parent = await get_current_parent(current_user)
    case = await get_case_or_404(case_id, parent.id)

    uploaded = await upload_images(files, EVIDENCE_FOLDER)
    try:
        payload = _validate_create(case_id, uploaded, description)
        evidence = await prisma.evidence.create(
            data={
                "caseId": case_id,
                "fileUrls": payload.fileUrls,
                "description": payload.description,
            }
        )
    except Exception:
        await delete_images(uploaded)
        raise

    if not evidence:
        await delete_images(uploaded)
        raise APIException(status_code=500, message="Failed to create evidence")

    await _sync_has_evidence(case_id, case.currentStage)
    return success_response(message="Evidence created successfully", data=evidence)


async def get_all_evidence_controller(
    current_user: TokenPayload, case_id: str, query: ListQuery
):
    parent = await get_current_parent(current_user)
    await get_case_or_404(case_id, parent.id)
    where = merge_filters(
        {"caseId": case_id},
        text_search(query.search, "description"),
    )
    evidence, total = await asyncio.gather(
        prisma.evidence.find_many(
            where=where,
            order={"createdAt": "asc"},
            **prisma_paging(query.skip, query.limit),
        ),
        prisma.evidence.count(where=where),
    )
    return success_response(
        message="Evidence fetched successfully",
        data=paginated_data(evidence, total, query.skip, query.limit),
    )


async def get_evidence_by_id_controller(
    current_user: TokenPayload, case_id: str, evidence_id: str
):
    parent = await get_current_parent(current_user)
    await get_case_or_404(case_id, parent.id)
    evidence = await _get_evidence_for_case(case_id, evidence_id)
    return success_response(message="Evidence fetched successfully", data=evidence)


async def update_evidence_controller(
    case_id: str,
    evidence_id: str,
    current_user: TokenPayload,
    description: str | None = None,
    existing_file_urls: str | None = None,
    files: list[UploadFile] | None = None,
):
    parent = await get_current_parent(current_user)
    case = await get_case_or_404(case_id, parent.id)
    existing = await _get_evidence_for_case(case_id, evidence_id)

    kept_urls = parse_json_string_list(existing_file_urls)
    if kept_urls is not None:
        existing_set = set(existing.fileUrls or [])
        unknown_urls = [url for url in kept_urls if url not in existing_set]
        if unknown_urls:
            raise APIException(status_code=400, message="Existing file urls contains URLs that do not belong to this evidence record")
    uploaded = await upload_images(files, EVIDENCE_FOLDER)

    if kept_urls is None and not uploaded:
        file_urls = None
    else:
        file_urls = (kept_urls if kept_urls is not None else list(existing.fileUrls or [])) + uploaded

    try:
        payload = _validate_update(file_urls, description)
        update_data = payload.model_dump(exclude_none=True)
        if "fileUrls" in update_data:
            update_data["fileUrls"] = {"set": update_data["fileUrls"]}
        updated = await prisma.evidence.update(
            where={"id": evidence_id},
            data=update_data,
        )
    except Exception:
        await delete_images(uploaded)
        raise

    if not updated:
        await delete_images(uploaded)
        raise APIException(status_code=500, message="Failed to update evidence")

    old_urls = set(existing.fileUrls or [])
    new_urls = set(updated.fileUrls or [])
    await delete_images(list(old_urls - new_urls))

    await prisma.case.update(
        where={"id": case_id},
        data={"currentStage": next_stage(case.currentStage, 4)},
    )
    return success_response(message="Evidence updated successfully", data=updated)


async def delete_evidence_controller(
    current_user: TokenPayload, case_id: str, evidence_id: str
):
    parent = await get_current_parent(current_user)
    await get_case_or_404(case_id, parent.id)
    await _get_evidence_for_case(case_id, evidence_id)

    deleted = await prisma.evidence.delete(where={"id": evidence_id})
    if not deleted:
        raise APIException(status_code=500, message="Failed to delete evidence")

    await delete_images(deleted.fileUrls or [])
    remaining = await prisma.evidence.count(where={"caseId": case_id})
    await prisma.case.update(
        where={"id": case_id},
        data={"hasEvidence": remaining > 0},
    )
    return success_response(message="Evidence deleted successfully", data=deleted)
