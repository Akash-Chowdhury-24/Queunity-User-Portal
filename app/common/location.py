from fastapi import status

from app.core.database import prisma
from app.core.exceptions import APIException

LOCATION_INCLUDE = {
    "country": True,
    "state": True,
    "city": True,
}


async def validate_location_ids(
    country_id: str | None = None,
    state_id: str | None = None,
    city_id: str | None = None,
) -> dict[str, str | None]:
    """Validate optional location IDs and enforce city -> state -> country hierarchy."""
    country = None
    state = None
    city = None

    if country_id:
        country = await prisma.country.find_unique(where={"id": country_id})
        if not country:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Country not found",
            )

    if state_id:
        state = await prisma.state.find_unique(where={"id": state_id})
        if not state:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="State not found",
            )
        if country_id and state.countryId != country_id:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="State does not belong to the selected country",
            )
        if not country_id:
            country_id = state.countryId

    if city_id:
        city = await prisma.city.find_unique(where={"id": city_id})
        if not city:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="City not found",
            )
        if state_id and city.stateId != state_id:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="City does not belong to the selected state",
            )
        if not state_id:
            state_id = city.stateId
            state = await prisma.state.find_unique(where={"id": state_id})
            if state and not country_id:
                country_id = state.countryId
        elif state and city.stateId != state.id:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="City does not belong to the selected state",
            )

    if city_id and not state_id:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="stateId is required when cityId is provided",
        )
    if state_id and not country_id:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="countryId is required when stateId is provided",
        )

    if state and country_id and state.countryId != country_id:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="State does not belong to the selected country",
        )

    return {
        "countryId": country_id,
        "stateId": state_id,
        "cityId": city_id,
    }


def location_name_search(term: str | None) -> dict | None:
    """Prisma filter for searching related country/state/city names."""
    cleaned = (term or "").strip()
    if not cleaned:
        return None
    contains = {"contains": cleaned, "mode": "insensitive"}
    return {
        "OR": [
            {"country": {"is": {"name": contains}}},
            {"country": {"is": {"iso2": contains}}},
            {"country": {"is": {"iso3": contains}}},
            {"state": {"is": {"name": contains}}},
            {"state": {"is": {"stateCode": contains}}},
            {"city": {"is": {"name": contains}}},
        ]
    }


def serialize_location_relation(entity) -> dict | None:
    if entity is None:
        return None
    return entity.model_dump()


def location_search_extra(term: str | None) -> list[dict] | None:
    """OR clauses for text_search extra= from location_name_search."""
    loc_filter = location_name_search(term)
    if not loc_filter:
        return None
    return loc_filter.get("OR")