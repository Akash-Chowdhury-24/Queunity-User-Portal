from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _reject_payload_file_urls(data: Any) -> Any:
    if not isinstance(data, dict) or "files" not in data:
        return data
    files = data.get("files")
    if files:
        raise ValueError(
            "Do not send file URLs here. Upload raw files via physicalFiles or vehicleFiles"
        )
    return {key: value for key, value in data.items() if key != "files"}


class PhysicalAppearance(BaseModel):
    height: str | None = None
    build: str | None = None
    skinTone: str | None = None
    clothingType: str | None = None
    hair: str | None = None
    eyes: str | None = None
    mouth: str | None = None
    shoulder: str | None = None
    handsAndArms: str | None = None
    torso: str | None = None
    legs: str | None = None
    feet: str | None = None
    accessories: str | None = None
    additionalInfo: str | None = None

    model_config = ConfigDict(extra="ignore")


class VehicleAppearance(BaseModel):
    vehicleType: str | None = None
    color: str | None = None
    brand: str | None = None
    model: str | None = None
    markings: str | None = None
    damage: str | None = None
    registrationNumber: str | None = None
    additionalInfo: str | None = None
    directionOfTravel: str | None = None
    lastSeenLocation: str | None = None

    model_config = ConfigDict(extra="ignore")


class PhysicalDetailsInput(PhysicalAppearance):
    @model_validator(mode="before")
    @classmethod
    def reject_file_urls(cls, data: Any) -> Any:
        return _reject_payload_file_urls(data)


class VehicleDetailsInput(VehicleAppearance):
    @model_validator(mode="before")
    @classmethod
    def reject_file_urls(cls, data: Any) -> Any:
        return _reject_payload_file_urls(data)


class PhysicalDetails(PhysicalAppearance):
    files: list[str] = Field(default_factory=list)


class VehicleDetails(VehicleAppearance):
    files: list[str] = Field(default_factory=list)
