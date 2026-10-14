from datetime import date, datetime, timedelta
from app.common.general_schema import TokenPayload
from app.core.database import prisma
from app.core.exceptions import APIException

STUDENT_ROLE = "student"


async def get_below8_student(current_user: TokenPayload):
    if current_user.role != STUDENT_ROLE:
        raise APIException(status_code=403, message="Only students can access cases")

    student = await prisma.student.find_unique(
        where={"id": current_user.id},
        include={"parent": True, "school": True},
    )
    if not student:
        raise APIException(status_code=401, message="Student not found")

    today = date.today()
    dob = student.dateOfBirth.date()
    
    isStudentAbove8Years = (
        dob < date(today.year - 8, today.month, today.day)
    )
    if isStudentAbove8Years:
        raise APIException(status_code=403, message="These cases are only available to students 8 years old or below")
    return student


async def get_case_or_404(case_id: str, victim_id: str):
    case = await prisma.case.find_first(where={"id": case_id, "victimId": victim_id})
    if not case:
        raise APIException(status_code=404, message="Case not found")
    return case
