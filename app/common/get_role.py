
from app.common.general_schema import TokenPayload
from app.core.database import prisma
from app.core.exceptions import APIException


async def get_role(role_id: str):
  return await prisma.role.find_unique(
    where = {
      "id" : role_id
    },
  )
  
def action_allowed_with_role(userRole, module : str, action : str) :
  if userRole.name.lower() == "admin".lower() :
    return True
  
  permissions = userRole.permissions or []
  
  return any(
        permission.get("module") == module
        and permission.get(action) is True
        for permission in permissions
    )


async def determine_user_access(roleId : str, module : str, action : str) :
  role = await get_role(roleId)
  if not role:
    raise APIException(status_code=403, message=f"You are not authorized to perform {action} on {module}")
  
  if not action_allowed_with_role(role, module, action):
    raise APIException(status_code=403, message=f"You are not authorized to perform {action} on {module}")
  
  return True


def action_allowed_with_above8_years(above8Years : bool, module : str, action : str, permissions : list) :
  return any(
        permission.get("above8Years") is above8Years
        and permission.get("module") == module
        and permission.get(action) is True
        for permission in permissions
    )


async def determine_student_access(user : TokenPayload, module : str, action : str, permissions : list) :
  if not action_allowed_with_above8_years(user.above8Years, module, action, permissions):
    raise APIException(status_code=403, message=f"You are not authorized to perform {action} on {module}")

  return True


