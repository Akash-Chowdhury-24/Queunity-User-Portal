from app.modules.student.auth.contoller import (
  student_forgot_password_controller,
  student_login_controller,
  student_register_controller,
  student_reset_password_controller,
)
from app.modules.student.auth.schema import (
  StudentForgotPasswordModel,
  StudentLoginModel,
  StudentRegisterModel,
  StudentResetPasswordModel,
)
from fastapi import APIRouter


authRouter = APIRouter()

@authRouter.post("/login")
async def student_login(payload: StudentLoginModel):
  return await student_login_controller(payload)

@authRouter.post("/register")
async def student_register(payload: StudentRegisterModel):
  return await student_register_controller(payload)

@authRouter.post("/forget-password")
async def student_forgot_password(payload: StudentForgotPasswordModel):
  return await student_forgot_password_controller(payload)

@authRouter.post("/reset-password")
async def student_reset_password(payload: StudentResetPasswordModel):
  return await student_reset_password_controller(payload)
