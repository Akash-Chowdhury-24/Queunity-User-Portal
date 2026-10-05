from pydantic import BaseModel, EmailStr, Field


class ParentLoginModel(BaseModel):
    email: EmailStr
    password: str


class ParentRegisterModel(BaseModel):
    firstName: str
    lastName: str
    email: EmailStr
    password: str


class ParentForgotPasswordModel(BaseModel):
    email: EmailStr


class ParentResetPasswordModel(BaseModel):
    token: str = Field(min_length=1)
    newPassword: str = Field(min_length=8)
