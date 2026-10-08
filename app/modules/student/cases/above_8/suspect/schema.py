from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.student.cases.above_8.schema.details import (
    PhysicalDetails,
    PhysicalDetailsInput,
    VehicleDetails,
    VehicleDetailsInput,
)
from app.modules.student.cases.above_8.schema.enums import (
    PersonRelationship,
    PersonType,
)
from app.modules.student.cases.above_8.schema.validate import (
    EmptyStrToNoneMixin,
    reject_fields,
    require_fields,
)

SUSPECT_SCHOOLMATE_FIELDS = (
    "grade",
    "studentName",
    "studentImageUrl",
    "studentDetails",
)
SUSPECT_EXTERNAL_FIELDS = (
    "extSchoolName",
    "extSchoolCity",
    "extSchoolState",
    "studentName",
    "grade",
    "gender",
    "studentImageUrl",
    "studentDetails",
    "howIdentified",
)
SUSPECT_OTHERS_FIELDS = (
    "organization",
    "personType",
    "personName",
    "age",
    "gender",
    "relationshipWithStudent",
    "contact",
    "howKnowThisPerson",
    "wasOnSchoolGrounds",
    "whereOnCampusSeen",
)
SUSPECT_UNKNOWN_FIELDS = ("physicalDetails", "vehicleDetails", "behaviorObserved")
SUSPECT_KNOWN_ONLY_FIELDS = tuple(
    dict.fromkeys(
        ("relationship",)
        + SUSPECT_SCHOOLMATE_FIELDS
        + SUSPECT_EXTERNAL_FIELDS
        + SUSPECT_OTHERS_FIELDS
    )
)


class SuspectBase(EmptyStrToNoneMixin):
    isKnown: bool
    relationship: PersonRelationship | None = None
    grade: str | None = None
    studentName: str | None = None
    studentImageUrl: str | None = None
    studentDetails: str | None = None
    extSchoolName: str | None = None
    extSchoolCity: str | None = None
    extSchoolState: str | None = None
    gender: str | None = None
    howIdentified: str | None = None
    organization: str | None = None
    personType: PersonType | None = None
    personName: str | None = None
    age: int | None = Field(default=None, ge=0, le=120)
    relationshipWithStudent: str | None = None
    contact: str | None = None
    howKnowThisPerson: str | None = None
    wasOnSchoolGrounds: bool | None = None
    whereOnCampusSeen: str | None = None
    physicalDetails: PhysicalDetailsInput | None = None
    vehicleDetails: VehicleDetailsInput | None = None
    behaviorObserved: str | None = None

    @model_validator(mode="after")
    def validate_suspect_shape(self):
        if not self.isKnown:
            reject_fields(self, SUSPECT_KNOWN_ONLY_FIELDS, "isKnown is false")
            return self

        if self.relationship is None:
            raise ValueError("relationship required when isKnown is true")

        reject_fields(self, SUSPECT_UNKNOWN_FIELDS, "isKnown is true")

        if self.relationship == PersonRelationship.SCHOOLMATE:
            require_fields(
                self,
                ("grade", "studentName"),
                "relationship is SCHOOLMATE",
            )
            reject_fields(
                self,
                (
                    "extSchoolName",
                    "extSchoolCity",
                    "extSchoolState",
                    "gender",
                    "howIdentified",
                )
                + SUSPECT_OTHERS_FIELDS,
                "relationship is SCHOOLMATE",
            )
        elif self.relationship == PersonRelationship.EXTERNAL_STUDENT:
            require_fields(
                self,
                ("extSchoolName", "extSchoolCity", "extSchoolState", "studentName"),
                "relationship is EXTERNAL_STUDENT",
            )
            reject_fields(
                self,
                (
                    "organization",
                    "personType",
                    "personName",
                    "age",
                    "relationshipWithStudent",
                    "contact",
                    "howKnowThisPerson",
                    "wasOnSchoolGrounds",
                    "whereOnCampusSeen",
                ),
                "relationship is EXTERNAL_STUDENT",
            )
        else:
            require_fields(
                self,
                ("personName", "personType"),
                "relationship is OTHERS",
            )
            reject_fields(
                self,
                (
                    "grade",
                    "studentName",
                    "studentImageUrl",
                    "studentDetails",
                    "extSchoolName",
                    "extSchoolCity",
                    "extSchoolState",
                    "howIdentified",
                ),
                "relationship is OTHERS",
            )
            if self.wasOnSchoolGrounds is True:
                require_fields(
                    self,
                    ("whereOnCampusSeen",),
                    "wasOnSchoolGrounds is true",
                )
            else:
                reject_fields(
                    self,
                    ("whereOnCampusSeen",),
                    "wasOnSchoolGrounds is not true",
                )

        return self


class SuspectCreate(SuspectBase):
    caseId: str = Field(min_length=1)


class SuspectUpdate(SuspectBase):
    pass


class SuspectOut(BaseModel):
    id: str
    caseId: str
    isKnown: bool
    relationship: PersonRelationship | None = None
    grade: str | None = None
    studentName: str | None = None
    studentImageUrl: str | None = None
    studentDetails: str | None = None
    extSchoolName: str | None = None
    extSchoolCity: str | None = None
    extSchoolState: str | None = None
    gender: str | None = None
    howIdentified: str | None = None
    organization: str | None = None
    personType: PersonType | None = None
    personName: str | None = None
    age: int | None = None
    relationshipWithStudent: str | None = None
    contact: str | None = None
    howKnowThisPerson: str | None = None
    wasOnSchoolGrounds: bool | None = None
    whereOnCampusSeen: str | None = None
    physicalDetails: PhysicalDetails | None = None
    vehicleDetails: VehicleDetails | None = None
    behaviorObserved: str | None = None
    createdAt: datetime
    updatedAt: datetime

    model_config = ConfigDict(from_attributes=True)
