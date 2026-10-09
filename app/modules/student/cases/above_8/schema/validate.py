from typing import Any

from pydantic import BaseModel, model_validator


class EmptyStrToNoneMixin(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def empty_str_to_none(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        return {key: (None if value == "" else value) for key, value in data.items()}


OTHERS_SENTINEL = "others"


def is_blank(value: Any) -> bool:
    return value is None or value == ""


def is_others(value: Any) -> bool:
    return not is_blank(value) and str(value).strip().lower() == OTHERS_SENTINEL


def is_present(value: Any) -> bool:
    if is_blank(value):
        return False
    if value == [] or value == {}:
        return False
    return True


def require_fields(model: BaseModel, names: tuple[str, ...], when: str) -> None:
    missing = [name for name in names if is_blank(getattr(model, name))]
    if missing:
        raise ValueError(f"{', '.join(missing)} required when {when}")


def reject_fields(model: BaseModel, names: tuple[str, ...], when: str) -> None:
    present = [name for name in names if is_present(getattr(model, name))]
    if present:
        raise ValueError(f"{', '.join(present)} must not be set when {when}")
