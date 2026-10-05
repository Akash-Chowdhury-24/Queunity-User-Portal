from app.modules.parent.auth.controller import (
  parent_forgot_password_controller,
  parent_login_controller,
  parent_register_controller,
  parent_reset_password_controller,
)
from app.modules.parent.auth.schema import (
  ParentForgotPasswordModel,
  ParentLoginModel,
  ParentRegisterModel,
  ParentResetPasswordModel,
)
from fastapi import APIRouter


authRouter = APIRouter()

@authRouter.post("/login")
async def parent_login(payload: ParentLoginModel):
  return await parent_login_controller(payload)

@authRouter.post("/register")
async def parent_register(payload: ParentRegisterModel):
  return await parent_register_controller(payload)

@authRouter.post("/forget-password")
async def parent_forgot_password(payload: ParentForgotPasswordModel):
  return await parent_forgot_password_controller(payload)

@authRouter.post("/reset-password")
async def parent_reset_password(payload: ParentResetPasswordModel):
  return await parent_reset_password_controller(payload)
