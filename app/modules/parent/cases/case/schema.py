from datetime import date, datetime
from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.modules.parent.cases.evidence.schema import EvidenceOut
from app.modules.parent.cases.schema.enums import (
    AnonymityLevel,
    AreaType,
    CaseStatus,
    CharityInvolvement,
    CharityType,
    LocationType,
    PoliceInvolvement,
    PrivacyLevel,
    ResolutionDesired,
)
from app.modules.parent.cases.schema.validate import (
    EmptyStrToNoneMixin,
    is_blank,
    is_others,
    reject_fields,
    require_fields,
)
from app.modules.parent.cases.suspect.schema import SuspectOut
from app.modules.parent.cases.witness.schema import WitnessOut

INCIDENT_TIME_PATTERN = r"^([01]\d|2[0-3]):[0-5]\d$"


class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"


class GradeSimpleOut(BaseModel):
    id: str
    gradeName: str

    model_config = ConfigDict(from_attributes=True)


class CaseVictimOut(BaseModel):
    id: str
    publicId: str
    firstName: str
    lastName: str
    email: str
    dateOfBirth: date | None = None
    gender: Gender | None = None
    photoUrl: str | None = None
    above8Years: bool
    gradeId: str | None = None
    grade: GradeSimpleOut | None = None
    schoolId: str | None = None
    parentId: str | None = None
    country: str | None = None
    addressLine1: str | None = None
    addressLine2: str | None = None
    landmark: str | None = None
    city: str | None = None
    state: str | None = None
    zipCode: str | None = None
    createdAt: datetime
    updatedAt: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("dateOfBirth", mode="before")
    @classmethod
    def coerce_date_of_birth(cls, value):
        if isinstance(value, datetime):
            return value.date()
        return value


CHARITY_ALREADY_INFORMED_FIELDS = ("charityId", "charityNameFallback")
CHARITY_INFORM_NOW_FIELDS = ("charityTypeRequested", "charityInvolvementReason")
POLICE_REPORTED_FIELDS = (
    "policeReportNumber",
    "policeOfficerName",
    "policeStationDepartment",
    "policeReportDate",
    "policeReportImageUrl",
)


class CaseStage1Create(EmptyStrToNoneMixin):
    caseName: str = Field(min_length=1)
    schoolId: str | None = None
    otherSchoolName: str | None = None
    victimId: str = Field(min_length=1)
    offenseId: str = Field(min_length=1)
    offenseSubCategoryId: str = Field(min_length=1)
    incidentDate: date
    incidentTime: str = Field(pattern=INCIDENT_TIME_PATTERN)
    locationType: LocationType
    areaType: AreaType | None = None
    areaDescription: str | None = None
    gradeId: str | None = None
    anonymityLevel: AnonymityLevel
    privacyLevel: PrivacyLevel

    @model_validator(mode="after")
    def validate_stage_1(self):
        if is_others(self.schoolId):
            require_fields(self, ("otherSchoolName",), "schoolId is others")
            self.schoolId = None
        elif not is_blank(self.schoolId):
            reject_fields(self, ("otherSchoolName",), "schoolId is set")
        else:
            require_fields(self, ("otherSchoolName",), "schoolId is not set")

        # if self.locationType == LocationType.WITHIN_SCHOOL:
        #     if self.areaType is None:
        #         raise ValueError("areaType required when locationType is WITHIN_SCHOOL")
        # else:
        #     reject_fields(
        #         self,
        #         ("areaType", "areaDescription", "gradeId"),
        #         "locationType is OUTSIDE_SCHOOL",
        #     )

        if self.areaType == AreaType.OTHER:
            require_fields(self, ("areaDescription",), "areaType is OTHER")
            reject_fields(self, ("gradeId",), "areaType is OTHER")
        elif self.areaType is not None:
            reject_fields(self, ("areaDescription",), "areaType is not OTHER")

        return self


class CaseStage5Update(EmptyStrToNoneMixin):
    charityInvolvement: CharityInvolvement
    charityId: str | None = None
    charityNameFallback: str | None = None
    charityTypeRequested: CharityType | None = None
    charityInvolvementReason: str | None = None
    policeInvolvement: PoliceInvolvement
    policeReportNumber: str | None = None
    policeOfficerName: str | None = None
    policeStationDepartment: str | None = None
    policeReportDate: date | None = None
    policeReportImageUrl: str | None = None

    @model_validator(mode="after")
    def validate_stage_5(self):
        if self.charityInvolvement == CharityInvolvement.ALREADY_INFORMED:
            charity_id_set = not is_blank(self.charityId)
            fallback_set = not is_blank(self.charityNameFallback)
            if charity_id_set == fallback_set:
                raise ValueError(
                    "Exactly one of charityId or charityNameFallback must be set "
                    "when charityInvolvement is ALREADY_INFORMED"
                )
            reject_fields(
                self,
                CHARITY_INFORM_NOW_FIELDS,
                "charityInvolvement is ALREADY_INFORMED",
            )
        elif self.charityInvolvement == CharityInvolvement.INFORM_NOW:
            require_fields(
                self,
                ("charityTypeRequested",),
                "charityInvolvement is INFORM_NOW",
            )
            reject_fields(
                self,
                CHARITY_ALREADY_INFORMED_FIELDS,
                "charityInvolvement is INFORM_NOW",
            )
        else:
            reject_fields(
                self,
                CHARITY_ALREADY_INFORMED_FIELDS + CHARITY_INFORM_NOW_FIELDS,
                f"charityInvolvement is {self.charityInvolvement.value}",
            )

        if self.policeInvolvement == PoliceInvolvement.ALREADY_REPORTED:
            require_fields(
                self,
                ("policeReportNumber",),
                "policeInvolvement is ALREADY_REPORTED",
            )
        else:
            reject_fields(
                self,
                POLICE_REPORTED_FIELDS,
                f"policeInvolvement is {self.policeInvolvement.value}",
            )

        return self


class CaseStage6Update(EmptyStrToNoneMixin):
    resolutionDesired: ResolutionDesired


class CaseOut(BaseModel):
    id: str
    caseName: str
    schoolId: str | None = None
    otherSchoolName: str | None = None
    victimId: str | None = None
    victim: CaseVictimOut | None = None
    offenseId: str
    offenseSubCategoryId: str
    incidentDate: date
    incidentTime: str
    locationType: LocationType
    areaType: AreaType | None = None
    areaDescription: str | None = None
    gradeId: str | None = None
    grade: GradeSimpleOut | None = None
    anonymityLevel: AnonymityLevel
    privacyLevel: PrivacyLevel
    charityInvolvement: CharityInvolvement | None = None
    charityId: str | None = None
    charityNameFallback: str | None = None
    charityTypeRequested: CharityType | None = None
    charityInvolvementReason: str | None = None
    policeInvolvement: PoliceInvolvement | None = None
    policeReportNumber: str | None = None
    policeOfficerName: str | None = None
    policeStationDepartment: str | None = None
    policeReportDate: datetime | None = None
    policeReportImageUrl: str | None = None
    resolutionDesired: ResolutionDesired | None = None
    draft: bool
    status: CaseStatus | None = None
    currentStage: int = Field(ge=1, le=6)
    hasEvidence: bool
    suspects: list[SuspectOut] = Field(default_factory=list)
    witnesses: list[WitnessOut] = Field(default_factory=list)
    evidence: list[EvidenceOut] = Field(default_factory=list)
    createdAt: datetime
    updatedAt: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("incidentDate", mode="before")
    @classmethod
    def coerce_incident_date(cls, value):
        if isinstance(value, datetime):
            return value.date()
        return value

    @field_validator("suspects", "witnesses", "evidence", mode="before")
    @classmethod
    def coerce_empty_relations(cls, value):
        return value or []
