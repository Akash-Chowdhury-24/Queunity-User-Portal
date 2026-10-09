from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class WhenItHappened(str, Enum):
    TODAY = "TODAY"
    YESTERDAY = "YESTERDAY"
    FEW_DAYS_AGO = "FEW_DAYS_AGO"


class WhereItHappened(str, Enum):
    CLASSROOM = "CLASSROOM"
    BATHROOM = "BATHROOM"
    PLAYGROUND = "PLAYGROUND"
    OTHERS = "OTHERS"


class CaseCreateModel(BaseModel):
    caseName: str = Field(min_length=1)
    caseDescription: str
    whenItHappened: WhenItHappened
    whereItHappened: WhereItHappened


class CaseUpdateModel(BaseModel):
    caseName: Optional[str] = Field(default=None, min_length=1)
    caseDescription: Optional[str] = None
    whenItHappened: Optional[WhenItHappened] = None
    whereItHappened: Optional[WhereItHappened] = None
