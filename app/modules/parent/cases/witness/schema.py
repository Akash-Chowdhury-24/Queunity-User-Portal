from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.parent.cases.schema.details import (
    PhysicalDetails,
    PhysicalDetailsInput,
    VehicleDetails,
    VehicleDetailsInput,
)
from app.modules.parent.cases.schema.enums import (
    PersonRelationship,
    PersonType,
    RelationshipToVictim,
    WasPresent,
    WitnessCoverage,
    WitnessReliability,
)
from app.modules.parent.cases.schema.validate import (
    EmptyStrToNoneMixin,
    reject_fields,
    require_fields,
)

WITNESS_SCHOOLMATE_FIELDS = (
    "grade",
    "studentName",
    "witnessCoverage",
    "witnessReliability",
    "witnessStatement",
    "relationshipToVictim",
)
WITNESS_EXTERNAL_FIELDS = (
    "extSchoolName",
    "extSchoolCity",
    "extSchoolState",
    "gender",
    "grade",
    "age",
    "howIdentified",
    "studentDetails",
)
WITNESS_OTHERS_FIELDS = (
    "organization",
    "personType",
    "personName",
    "age",
    "gender",
    "relationshipWithStudent",
    "contact",
    "howConnectedToIncident",
    "wasPresent",
)
WITNESS_UNKNOWN_FIELDS = ("physicalDetails", "vehicleDetails", "behaviorObserved")
WITNESS_KNOWN_ONLY_FIELDS = tuple(
    dict.fromkeys(
        ("relationship",)
        + WITNESS_SCHOOLMATE_FIELDS
        + WITNESS_EXTERNAL_FIELDS
        + WITNESS_OTHERS_FIELDS
    )
)


class WitnessBase(EmptyStrToNoneMixin):
    isKnown: bool
    relationship: PersonRelationship | None = None
    grade: str | None = None
    studentName: str | None = None
    witnessCoverage: WitnessCoverage | None = None
    witnessReliability: WitnessReliability | None = None
    witnessStatement: str | None = None
    relationshipToVictim: RelationshipToVictim | None = None
    extSchoolName: str | None = None
    extSchoolCity: str | None = None
    extSchoolState: str | None = None
    gender: str | None = None
    age: int | None = Field(default=None, ge=0, le=120)
    howIdentified: str | None = None
    studentDetails: str | None = None
    organization: str | None = None
    personType: PersonType | None = None
    personName: str | None = None
    relationshipWithStudent: str | None = None
    contact: str | None = None
    howConnectedToIncident: str | None = None
    wasPresent: WasPresent | None = None
    physicalDetails: PhysicalDetailsInput | None = None
    vehicleDetails: VehicleDetailsInput | None = None
    behaviorObserved: str | None = None

    @model_validator(mode="after")
    def validate_witness_shape(self):
        if not self.isKnown:
            reject_fields(self, WITNESS_KNOWN_ONLY_FIELDS, "isKnown is false")
            return self

        if self.relationship is None:
            raise ValueError("relationship required when isKnown is true")

        reject_fields(self, WITNESS_UNKNOWN_FIELDS, "isKnown is true")

        if self.relationship == PersonRelationship.SCHOOLMATE:
            require_fields(
                self,
                (
                    "grade",
                    "studentName",
                    "witnessCoverage",
                    "witnessReliability",
                    "relationshipToVictim",
                ),
                "relationship is SCHOOLMATE",
            )
            reject_fields(
                self,
                (
                    "extSchoolName",
                    "extSchoolCity",
                    "extSchoolState",
                    "gender",
                    "age",
                    "howIdentified",
                    "studentDetails",
                )
                + WITNESS_OTHERS_FIELDS,
                "relationship is SCHOOLMATE",
            )
        elif self.relationship == PersonRelationship.EXTERNAL_STUDENT:
            require_fields(
                self,
                ("extSchoolName", "extSchoolCity", "extSchoolState"),
                "relationship is EXTERNAL_STUDENT",
            )
            reject_fields(
                self,
                (
                    "studentName",
                    "witnessCoverage",
                    "witnessReliability",
                    "witnessStatement",
                    "relationshipToVictim",
                    "organization",
                    "personType",
                    "personName",
                    "relationshipWithStudent",
                    "contact",
                    "howConnectedToIncident",
                    "wasPresent",
                ),
                "relationship is EXTERNAL_STUDENT",
            )
        else:
            require_fields(
                self,
                ("personName", "personType", "wasPresent"),
                "relationship is OTHERS",
            )
            reject_fields(
                self,
                (
                    "grade",
                    "studentName",
                    "witnessCoverage",
                    "witnessReliability",
                    "witnessStatement",
                    "relationshipToVictim",
                    "extSchoolName",
                    "extSchoolCity",
                    "extSchoolState",
                    "howIdentified",
                    "studentDetails",
                ),
                "relationship is OTHERS",
            )

        return self


class WitnessCreate(WitnessBase):
    caseId: str = Field(min_length=1)


class WitnessUpdate(WitnessBase):
    pass


class WitnessOut(BaseModel):
    id: str
    caseId: str
    isKnown: bool
    relationship: PersonRelationship | None = None
    grade: str | None = None
    studentName: str | None = None
    witnessCoverage: WitnessCoverage | None = None
    witnessReliability: WitnessReliability | None = None
    witnessStatement: str | None = None
    relationshipToVictim: RelationshipToVictim | None = None
    extSchoolName: str | None = None
    extSchoolCity: str | None = None
    extSchoolState: str | None = None
    gender: str | None = None
    age: int | None = None
    howIdentified: str | None = None
    studentDetails: str | None = None
    organization: str | None = None
    personType: PersonType | None = None
    personName: str | None = None
    relationshipWithStudent: str | None = None
    contact: str | None = None
    howConnectedToIncident: str | None = None
    wasPresent: WasPresent | None = None
    physicalDetails: PhysicalDetails | None = None
    vehicleDetails: VehicleDetails | None = None
    behaviorObserved: str | None = None
    createdAt: datetime
    updatedAt: datetime

    model_config = ConfigDict(from_attributes=True)
