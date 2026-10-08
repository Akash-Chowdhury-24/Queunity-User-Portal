import asyncio

from fastapi import BackgroundTasks

from app.common.general_schema import TokenPayload
from app.common.pagination import (
    ListQuery,
    merge_filters,
    paginated_data,
    prisma_paging,
    text_search,
)
from app.common.response import success_response
from app.core.database import prisma
from app.core.exceptions import APIException
from app.modules.student.cases.below_8.common import get_below8_student, get_case_or_404
from app.modules.student.cases.below_8.notifications import (
    case_notification_recipients,
    send_case_notification_emails,
)
from app.modules.student.cases.below_8.schema import CaseCreateModel, CaseUpdateModel


def _queue_case_notifications(
    background_tasks: BackgroundTasks, student, case, action: str
) -> None:
    recipients = case_notification_recipients(student)
    if recipients:
        background_tasks.add_task(
            send_case_notification_emails, recipients, student, case, action
        )


async def create_case_controller(
    payload: CaseCreateModel,
    current_user: TokenPayload,
    background_tasks: BackgroundTasks,
):
    student = await get_below8_student(current_user)
    case = await prisma.case.create(
        data={
            **payload.model_dump(mode="json"),
            "victimId": student.id,
            "schoolId": student.schoolId,
            "gradeId": student.gradeId,
            "draft": False,
            "status": "PENDING",
        }
    )
    if not case:
        raise APIException(status_code=500, message="Failed to create case")

    _queue_case_notifications(background_tasks, student, case, "reported")
    return success_response(message="Case created successfully", data=case)


async def update_case_controller(
    case_id: str,
    payload: CaseUpdateModel,
    current_user: TokenPayload,
    background_tasks: BackgroundTasks,
):
    student = await get_below8_student(current_user)
    await get_case_or_404(case_id, student.id)

    data = payload.model_dump(mode="json", exclude_none=True)
    if not data:
        raise APIException(status_code=400, message="No fields provided to update")

    case = await prisma.case.update(where={"id": case_id}, data=data)
    if not case:
        raise APIException(status_code=500, message="Failed to update case")

    _queue_case_notifications(background_tasks, student, case, "updated")
    return success_response(message="Case updated successfully", data=case)


async def get_case_by_id_controller(case_id: str, current_user: TokenPayload):
    student = await get_below8_student(current_user)
    case = await get_case_or_404(case_id, student.id)
    return success_response(message="Case fetched successfully", data=case)


async def get_all_cases_controller(current_user: TokenPayload, query: ListQuery):
    student = await get_below8_student(current_user)
    where = merge_filters(
        {"victimId": student.id},
        text_search(query.search, "caseName", "caseDescription"),
    )
    cases, total = await asyncio.gather(
        prisma.case.find_many(
            where=where,
            order={"createdAt": "desc"},
            **prisma_paging(query.skip, query.limit),
        ),
        prisma.case.count(where=where),
    )
    return success_response(
        message="Cases fetched successfully",
        data=paginated_data(cases, total, query.skip, query.limit),
    )


async def delete_case_controller(case_id: str, current_user: TokenPayload):
    student = await get_below8_student(current_user)
    await get_case_or_404(case_id, student.id)
    deleted = await prisma.case.delete(where={"id": case_id})
    if not deleted:
        raise APIException(status_code=500, message="Failed to delete case")
    return success_response(message="Case deleted successfully", data=deleted)
