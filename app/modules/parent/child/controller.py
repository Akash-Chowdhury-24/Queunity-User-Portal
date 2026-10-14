from datetime import datetime, time

from fastapi import BackgroundTasks, UploadFile
from prisma.errors import UniqueViolationError

from app.common.general_schema import TokenPayload
from app.common.response import success_response
from app.common.s3 import delete_image, upload_image
from app.common.student_public_id import generate_student_public_id
from app.core.database import prisma
from app.core.exceptions import APIException
from app.core.security import hash_password
from app.modules.parent.cases.common import has_upload
from app.modules.parent.child.schema import ChildCreateModel, ChildUpdateModel
from app.modules.parent.child.utils import (
    generate_password,
    public_child,
    public_school,
    send_child_created_notifications,
    send_school_enrollment_email,
    today_ist,
)

PARENT_ROLE = "parent"
STUDENT_PHOTO_FOLDER = "students"
CHILD_INCLUDE = {"school": True, "grade": True}
PUBLIC_ID_ATTEMPTS = 5


async def _get_parent(current_user: TokenPayload):
    if current_user.role != PARENT_ROLE:
        raise APIException(status_code=403, message="Only parents can manage children")

    parent = await prisma.parent.find_unique(where={"id": current_user.id})
    if not parent:
        raise APIException(status_code=401, message="Parent not found")
    return parent


async def _get_school_by_public_id(public_id: str, *, include_grades: bool = False):
    school = await prisma.school.find_unique(
        where={"publicId": public_id.strip().upper()},
        include={"grades": {"order_by": {"gradeName": "asc"}}} if include_grades else None,
    )
    if not school:
        raise APIException(status_code=404, message="No school found with this public ID")
    return school


async def _get_grade_for_school(grade_id: str, school_id: str):
    grade = await prisma.grade.find_unique(where={"id": grade_id})
    if not grade:
        raise APIException(status_code=404, message="Grade not found")
    if grade.schoolId != school_id:
        raise APIException(status_code=400, message="Grade does not belong to the selected school")
    return grade


async def _get_child_or_404(child_id: str, parent_id: str):
    child = await prisma.student.find_first(
        where={"id": child_id, "parentId": parent_id},
        include=CHILD_INCLUDE,
    )
    if not child:
        raise APIException(status_code=404, message="Child not found")
    return child


def _is_unique_violation_on(err: UniqueViolationError, field: str) -> bool:
    meta = getattr(err, "meta", None)
    target = meta.get("target") if isinstance(meta, dict) else None
    return field in str(target or "") or field in str(err)


async def _create_student(data: dict):
    for attempt in range(1, PUBLIC_ID_ATTEMPTS + 1):
        public_id = generate_student_public_id(data["firstName"], data["lastName"], data["email"])
        try:
            return await prisma.student.create(
                data={**data, "publicId": public_id},
                include=CHILD_INCLUDE,
            )
        except UniqueViolationError as err:
            if _is_unique_violation_on(err, "email"):
                raise APIException(
                    status_code=409, message="A student with this email already exists"
                ) from err
            if _is_unique_violation_on(err, "publicId") and attempt < PUBLIC_ID_ATTEMPTS:
                continue
            raise
    raise APIException(status_code=500, message="Could not generate a unique student ID")


async def get_school_by_public_id_controller(school_public_id: str, current_user: TokenPayload):
    await _get_parent(current_user)
    school = await _get_school_by_public_id(school_public_id, include_grades=True)
    return success_response(
        message="School fetched successfully",
        data=public_school(school, include_grades=True),
    )


async def get_all_children_controller(current_user: TokenPayload):
    parent = await _get_parent(current_user)
    children = await prisma.student.find_many(
        where={"parentId": parent.id},
        include=CHILD_INCLUDE,
        order={"createdAt": "desc"},
    )
    return success_response(
        message="Children fetched successfully",
        data=[public_child(child) for child in children],
    )


async def get_child_by_id_controller(child_id: str, current_user: TokenPayload):
    parent = await _get_parent(current_user)
    child = await _get_child_or_404(child_id, parent.id)
    return success_response(message="Child fetched successfully", data=public_child(child))


async def create_child_controller(
    payload: ChildCreateModel,
    photo: UploadFile | None,
    current_user: TokenPayload,
    background_tasks: BackgroundTasks,
):
    parent = await _get_parent(current_user)

    if await prisma.student.find_first(
        where={"email": {"equals": payload.email, "mode": "insensitive"}}
    ):
        raise APIException(status_code=409, message="A student with this email already exists")

    school = await _get_school_by_public_id(payload.schoolPublicId)
    await _get_grade_for_school(payload.gradeId, school.id)

    photo_url = await upload_image(photo, folder=STUDENT_PHOTO_FOLDER) if has_upload(photo) else None
    temporary_password = generate_password()

    try:
        child = await _create_student(
            {
                "firstName": payload.firstName,
                "lastName": payload.lastName,
                "email": payload.email,
                "dateOfBirth": datetime.combine(payload.dateOfBirth, time.min),
                "gender": payload.gender.value,
                "photoUrl": photo_url,
                "passwordHash": hash_password(temporary_password),
                "admissionYear": today_ist().year,
                "schoolId": school.id,
                "gradeId": payload.gradeId,
                "parentId": parent.id,
            }
        )
    except Exception:
        await delete_image(photo_url)
        raise

    background_tasks.add_task(
        send_child_created_notifications, parent, child, temporary_password
    )
    return success_response(message="Child added successfully", data=public_child(child))


async def update_child_controller(
    child_id: str,
    payload: ChildUpdateModel,
    photo: UploadFile | None,
    current_user: TokenPayload,
    background_tasks: BackgroundTasks,
):
    parent = await _get_parent(current_user)
    child = await _get_child_or_404(child_id, parent.id)

    data: dict = {}
    target_school_id = child.schoolId
    school_changed = False

    if payload.schoolPublicId:
        target_school = await _get_school_by_public_id(payload.schoolPublicId)
        if target_school.id != child.schoolId:
            if not payload.gradeId:
                raise APIException(
                    status_code=400,
                    message="gradeId is required when moving the child to a different school",
                )
            target_school_id = target_school.id
            school_changed = True
            data["schoolId"] = target_school.id

    if payload.gradeId:
        if not target_school_id:
            raise APIException(
                status_code=400,
                message="Send schoolPublicId along with gradeId, the child is not enrolled in a school",
            )
        await _get_grade_for_school(payload.gradeId, target_school_id)
        data["gradeId"] = payload.gradeId

    if payload.firstName is not None:
        data["firstName"] = payload.firstName
    if payload.lastName is not None:
        data["lastName"] = payload.lastName
    if payload.gender is not None:
        data["gender"] = payload.gender.value
    if payload.dateOfBirth is not None:
        data["dateOfBirth"] = datetime.combine(payload.dateOfBirth, time.min)

    new_photo_url = None
    if has_upload(photo):
        new_photo_url = await upload_image(photo, folder=STUDENT_PHOTO_FOLDER)
        data["photoUrl"] = new_photo_url

    if not data:
        raise APIException(status_code=400, message="No fields provided to update")

    try:
        updated = await prisma.student.update(
            where={"id": child.id},
            data=data,
            include=CHILD_INCLUDE,
        )
    except Exception:
        await delete_image(new_photo_url)
        raise

    if new_photo_url and child.photoUrl:
        await delete_image(child.photoUrl)

    if school_changed:
        background_tasks.add_task(send_school_enrollment_email, updated.school, updated, parent)

    return success_response(message="Child updated successfully", data=public_child(updated))


async def remove_child_controller(child_id: str, current_user: TokenPayload):
    parent = await _get_parent(current_user)
    child = await _get_child_or_404(child_id, parent.id)

    # Unlink only: the student keeps their account, school enrollment and cases.
    updated = await prisma.student.update(
        where={"id": child.id},
        data={"parentId": None},
        include=CHILD_INCLUDE,
    )
    return success_response(
        message="Child removed from your account",
        data=public_child(updated),
    )
