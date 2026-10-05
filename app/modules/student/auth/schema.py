from pydantic import BaseModel, EmailStr, Field


class StudentLoginModel(BaseModel):
    email: EmailStr
    password: str


class StudentRegisterModel(BaseModel):
    firstName: str
    lastName: str
    email: EmailStr
    password: str
    above8Years: bool


class StudentForgotPasswordModel(BaseModel):
    email: EmailStr


class StudentResetPasswordModel(BaseModel):
    token: str = Field(min_length=1)
    newPassword: str = Field(min_length=8)
