from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.parent.cases.schema.validate import EmptyStrToNoneMixin


class EvidenceCreate(EmptyStrToNoneMixin):
    caseId: str = Field(min_length=1)
    fileUrls: list[str] = Field(default_factory=list)
    description: str | None = None

    @model_validator(mode="after")
    def require_files_or_description(self):
        if not self.fileUrls and not self.description:
            raise ValueError("At least one of fileUrls or description is required")
        return self


class EvidenceUpdate(EmptyStrToNoneMixin):
    fileUrls: list[str] | None = None
    description: str | None = None

    @model_validator(mode="after")
    def require_update_payload(self):
        if self.fileUrls is None and self.description is None:
            raise ValueError("At least one of fileUrls or description must be provided")
        return self


class EvidenceOut(BaseModel):
    id: str
    caseId: str
    fileUrls: list[str] = Field(default_factory=list)
    description: str | None = None
    createdAt: datetime
    updatedAt: datetime

    model_config = ConfigDict(from_attributes=True)
