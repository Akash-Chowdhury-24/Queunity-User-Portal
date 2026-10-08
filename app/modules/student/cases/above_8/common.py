import json
from datetime import date, datetime, time, timezone
from enum import Enum
from typing import Annotated, Any

from fastapi import UploadFile
from pydantic import BaseModel, BeforeValidator, ValidationError, WithJsonSchema

from app.common.general_schema import TokenPayload
from app.common.s3 import delete_images, upload_image, upload_multiple_images
from app.core.database import prisma
from app.core.exceptions import APIException
from app.modules.student.cases.above_8.schema.validate import is_others
from prisma import Json

STUDENT_ROLE = "student"

SENSITIVE_STUDENT_FIELDS = {
    "passwordHash",
    "resetPasswordTokenHash",
    "resetPasswordTokenExpiresAt",
}

CASE_VICTIM_INCLUDE = {
    "victim": {"include": {"grade": True}},
}

CASE_INCLUDE = {
    **CASE_VICTIM_INCLUDE,
    "grade": True,
    "suspects": True,
    "witnesses": True,
    "evidence": True,
    "charity": True,
    "offense": True,
    "offenseSubCategory": True,
}

POLICE_REPORT_FOLDER = "case_police_reports"
SUSPECT_IMAGE_FOLDER = "suspect_images"
SUSPECT_PHYSICAL_FOLDER = "suspect_physical"
SUSPECT_VEHICLE_FOLDER = "suspect_vehicle"
WITNESS_PHYSICAL_FOLDER = "witness_physical"
WITNESS_VEHICLE_FOLDER = "witness_vehicle"
EVIDENCE_FOLDER = "case_evidence"


async def get_above8_student(current_user: TokenPayload):
    if current_user.role != STUDENT_ROLE:
        raise APIException(status_code=403, message="Only students can access cases")

    # The token can outlive a change to the student's record, so re-check above8Years from the DB.
    student = await prisma.student.find_unique(where={"id": current_user.id})
    if not student:
        raise APIException(status_code=401, message="Student not found")
    if not student.above8Years:
        raise APIException(
            status_code=403,
            message="These cases are only available to students above 8 years old",
        )
    return student


def public_case(case: Any) -> Any:
    if case is None:
        return None
    return case.model_dump(exclude={"victim": SENSITIVE_STUDENT_FIELDS})


def reshape_validation_errors(exc: ValidationError) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for err in exc.errors():
        loc = err.get("loc", ())
        field_parts = [str(part) for part in loc]
        errors.append(
            {
                "field": ".".join(field_parts),
                "message": err.get("msg"),
                "type": err.get("type"),
            }
        )
    return errors


def parse_json_object(raw: str, field_name: str = "payload") -> dict[str, Any]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise APIException(
            status_code=400,
            message=f"Invalid JSON in {field_name}",
        ) from exc

    if not isinstance(data, dict):
        raise APIException(status_code=400, message=f"{field_name} must be a JSON object")
    return data


def parse_json_string_list(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    cleaned = raw.strip()
    if not cleaned or cleaned.lower() in ("string", "null", "none", "[]"):
        return None

    # 1. Try parsing JSON array: ["url1", "url2"]
    if cleaned.startswith("[") and cleaned.endswith("]"):
        try:
            data = json.loads(cleaned)
            if isinstance(data, list) and all(isinstance(item, str) for item in data):
                items = [item.strip() for item in data if item.strip() and item.strip().lower() != "string"]
                return items or None
        except json.JSONDecodeError:
            pass

    # 2. Try parsing single quoted JSON string: "url"
    if cleaned.startswith('"') and cleaned.endswith('"'):
        try:
            data = json.loads(cleaned)
            if isinstance(data, str) and data.strip() and data.strip().lower() != "string":
                return [data.strip()]
        except json.JSONDecodeError:
            pass

    # 3. Fallback: Support single raw URL or comma/newline-separated URLs (ideal for Swagger testing)
    urls = [
        part.strip().strip('"\'')
        for part in cleaned.replace("\n", ",").split(",")
        if part.strip().strip('"\'') and part.strip().strip('"\'').lower() != "string"
    ]
    return urls or None


def to_prisma_data(payload: BaseModel, *, exclude: set[str] | None = None) -> dict[str, Any]:
    def convert(value: Any) -> Any:
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return date_to_datetime(value)
        if isinstance(value, dict):
            return {key: convert(item) for key, item in value.items()}
        if isinstance(value, list):
            return [convert(item) for item in value]
        return value

    return {key: convert(value) for key, value in payload.model_dump(exclude=exclude).items()}


def as_json(value: Any) -> Json | None:
    if value is None:
        return None
    return Json(value)


def apply_json_details(data: dict[str, Any], *keys: str) -> dict[str, Any]:
    # Prisma JSON fields reject Python None; omit the key so the column stays NULL.
    for key in keys:
        wrapped = as_json(data.get(key))
        if wrapped is None:
            data.pop(key, None)
        else:
            data[key] = wrapped
    return data


def person_write_data(
    payload: BaseModel,
    case_id: str,
    *,
    creating: bool = False,
    physical_urls: list[str] | None = None,
    vehicle_urls: list[str] | None = None,
) -> dict[str, Any]:
    data = to_prisma_data(payload, exclude={"caseId"})
    if data.get("physicalDetails") is not None or physical_urls:
        data["physicalDetails"] = merge_detail_files(
            data.get("physicalDetails"), physical_urls or []
        )
    if data.get("vehicleDetails") is not None or vehicle_urls:
        data["vehicleDetails"] = merge_detail_files(
            data.get("vehicleDetails"), vehicle_urls or []
        )
    data = apply_json_details(data, "physicalDetails", "vehicleDetails")
    if creating:
        data["case"] = {"connect": {"id": case_id}}
        data = {key: value for key, value in data.items() if value is not None}
    return data


def date_to_datetime(value: date | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def has_upload(file: UploadFile | None) -> bool:
    return bool(file is not None and file.filename)


def _is_empty_upload_value(value: Any) -> bool:
    return value is None or value == "" or value == b""


def coerce_empty_upload(value: Any) -> Any:
    # Swagger/curl send unused file fields as empty strings, not omitted files.
    return None if _is_empty_upload_value(value) else value


def coerce_empty_uploads(value: Any) -> Any:
    value = coerce_empty_upload(value)
    if not isinstance(value, (list, tuple)):
        return value
    files = [item for item in value if not _is_empty_upload_value(item)]
    return files or None


OptionalUploadFile = Annotated[
    UploadFile | None,
    BeforeValidator(coerce_empty_upload),
    WithJsonSchema(
        {
            "anyOf": [
                {"type": "string", "format": "binary"},
                {"type": "null"},
            ]
        }
    ),
]
OptionalUploadFiles = Annotated[
    list[UploadFile] | None,
    BeforeValidator(coerce_empty_uploads),
    WithJsonSchema(
        {
            "type": "array",
            "items": {"type": "string", "format": "binary"},
        }
    ),
]


async def upload_images(files: list[UploadFile] | None, folder: str) -> list[str]:
    return await upload_multiple_images(files, folder)


def detail_file_urls(details: Any) -> list[str]:
    if not details:
        return []
    if isinstance(details, dict):
        files = details.get("files") or []
    else:
        files = getattr(details, "files", None) or []
    return [url for url in files if url]


def merge_detail_files(details: Any, extra_urls: list[str]) -> dict[str, Any] | None:
    if not details and not extra_urls:
        return None

    data = dict(details) if isinstance(details, dict) else (
        details.model_dump() if isinstance(details, BaseModel) else {}
    )
    existing = [url for url in (data.get("files") or []) if url]
    data["files"] = existing + extra_urls
    return data


def person_file_urls(record: Any) -> list[str]:
    urls: list[str] = []
    student_image = getattr(record, "studentImageUrl", None)
    if student_image:
        urls.append(student_image)
    urls.extend(detail_file_urls(getattr(record, "physicalDetails", None)))
    urls.extend(detail_file_urls(getattr(record, "vehicleDetails", None)))
    return urls


async def delete_person_files(record: Any) -> None:
    await delete_images(person_file_urls(record))


async def delete_case_files(case) -> None:
    urls: list[str] = []
    if case.policeReportImageUrl:
        urls.append(case.policeReportImageUrl)
    for suspect in case.suspects or []:
        urls.extend(person_file_urls(suspect))
    for witness in case.witnesses or []:
        urls.extend(person_file_urls(witness))
    for evidence in case.evidence or []:
        urls.extend(evidence.fileUrls or [])
    await delete_images(urls)


async def get_case_or_404(case_id: str, victim_id: str, *, include_children: bool = False):
    case = await prisma.case.find_first(
        where={"id": case_id, "victimId": victim_id},
        include=CASE_INCLUDE if include_children else None,
    )
    if not case:
        raise APIException(status_code=404, message="Case not found")
    return case


def next_stage(current_stage: int, completed_stage: int) -> int:
    return max(current_stage, completed_stage)


async def ensure_stage1_references(
    school_id: str | None,
    offense_id: str,
    offense_sub_category_id: str,
    victim: Any,
    grade_id: str | None = None,
) -> None:
    if school_id and not is_others(school_id):
        school = await prisma.school.find_unique(where={"id": school_id})
        if not school:
            raise APIException(status_code=404, message="School not found")

    offense = await prisma.offense.find_unique(where={"id": offense_id})
    if not offense:
        raise APIException(status_code=404, message="Offense not found")

    sub_category = await prisma.offensesubcategory.find_unique(
        where={"id": offense_sub_category_id}
    )
    if not sub_category:
        raise APIException(status_code=404, message="Offense sub category not found")

    if sub_category.offenseId != offense_id:
        raise APIException(
            status_code=400,
            message="Offense sub category does not belong to the selected offense",
        )

    if school_id and not is_others(school_id) and victim.schoolId != school_id:
        raise APIException(
            status_code=400,
            message="You do not belong to the selected school",
        )

    if not grade_id:
        return

    if not school_id or is_others(school_id):
        raise APIException(
            status_code=400,
            message="gradeId is only allowed when a school is selected",
        )

    grade = await prisma.grade.find_unique(where={"id": grade_id})
    if not grade:
        raise APIException(status_code=404, message="Grade not found")
    if grade.schoolId != school_id:
        raise APIException(
            status_code=400,
            message="Grade does not belong to the selected school",
        )


async def ensure_charity_exists(charity_id: str | None) -> None:
    if not charity_id:
        return
    charity = await prisma.charity.find_unique(where={"id": charity_id})
    if not charity:
        raise APIException(status_code=404, message="Charity not found")


def combined_detail_urls(
    existing_details: Any,
    new_urls: list[str],
    *,
    keep_existing: bool,
    keep_urls_json: str | None = None,
    field_name: str = "existingFileUrls",
) -> list[str]:
    if not keep_existing:
        return list(new_urls)

    existing_urls = detail_file_urls(existing_details)
    requested = parse_json_string_list(keep_urls_json)
    if requested is None:
        return existing_urls + new_urls

    existing_set = set(existing_urls)
    unknown = [url for url in requested if url not in existing_set]
    if unknown:
        raise APIException(
            status_code=400,
            message=f"{field_name} contains URLs that are not on this record",
        )
    return requested + new_urls


async def attach_person_uploads(
    raw: dict[str, Any],
    *,
    student_image: UploadFile | None = None,
    physical_files: list[UploadFile] | None = None,
    vehicle_files: list[UploadFile] | None = None,
    student_folder: str = SUSPECT_IMAGE_FOLDER,
    physical_folder: str,
    vehicle_folder: str,
    allow_student_image: bool = True,
) -> tuple[dict[str, Any], list[str], list[str], list[str]]:
    is_known = bool(raw.get("isKnown"))
    uploaded: list[str] = []
    physical_requested = any(has_upload(file) for file in (physical_files or []))
    vehicle_requested = any(has_upload(file) for file in (vehicle_files or []))

    if has_upload(student_image) and (not allow_student_image or not is_known):
        raise APIException(
            status_code=400,
            message="studentImage is only allowed for a known schoolmate or external student",
        )
    if (physical_requested or vehicle_requested) and is_known:
        raise APIException(
            status_code=400,
            message="physicalFiles and vehicleFiles are only allowed when isKnown is false",
        )

    try:
        if has_upload(student_image):
            url = await upload_image(student_image, folder=student_folder)
            uploaded.append(url)
            raw["studentImageUrl"] = url

        physical_urls = await upload_images(physical_files, physical_folder)
        uploaded.extend(physical_urls)
        vehicle_urls = await upload_images(vehicle_files, vehicle_folder)
        uploaded.extend(vehicle_urls)
    except Exception:
        await delete_images(uploaded)
        raise

    return raw, uploaded, physical_urls, vehicle_urls
