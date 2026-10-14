from datetime import date, datetime
from enum import Enum
from typing import Optional
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"


def _today() -> date:
    return datetime.now(ZoneInfo("Asia/Kolkata")).date()


def _empty_to_none(value):
    if isinstance(value, str) and not value.strip():
        return None
    return value


def _check_date_of_birth(value: date | None) -> date | None:
    if value is not None and value >= _today():
        raise ValueError("dateOfBirth must be in the past")
    return value


class ChildCreateModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    schoolPublicId: str = Field(min_length=1)
    firstName: str = Field(min_length=1)
    lastName: str = Field(min_length=1)
    email: EmailStr
    dateOfBirth: date
    gradeId: str = Field(min_length=1)
    gender: Gender

    @field_validator("schoolPublicId")
    @classmethod
    def normalize_school_public_id(cls, value: str) -> str:
        return value.upper()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("dateOfBirth")
    @classmethod
    def validate_date_of_birth(cls, value: date) -> date:
        return _check_date_of_birth(value)


class ChildUpdateModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    schoolPublicId: Optional[str] = None
    firstName: Optional[str] = Field(default=None, min_length=1)
    lastName: Optional[str] = Field(default=None, min_length=1)
    dateOfBirth: Optional[date] = None
    gradeId: Optional[str] = None
    gender: Optional[Gender] = None

    @field_validator(
        "schoolPublicId",
        "firstName",
        "lastName",
        "dateOfBirth",
        "gradeId",
        "gender",
        mode="before",
    )
    @classmethod
    def empty_str_to_none(cls, value):
        return _empty_to_none(value)

    @field_validator("schoolPublicId")
    @classmethod
    def normalize_school_public_id(cls, value: str | None) -> str | None:
        return value.upper() if value else value

    @field_validator("dateOfBirth")
    @classmethod
    def validate_date_of_birth(cls, value: date | None) -> date | None:
        return _check_date_of_birth(value)
