import asyncio

from fastapi import status

from app.common.pagination import (
    merge_filters,
    paginated_data,
    prisma_paging,
    text_search,
)
from app.core.database import prisma
from app.core.exceptions import APIException


async def _ensure_country(country_id: str):
    country = await prisma.country.find_unique(where={"id": country_id})
    if not country:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Country with ID {country_id} not found",
        )
    return country


async def _ensure_state(state_id: str):
    state = await prisma.state.find_unique(where={"id": state_id})
    if not state:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"State with ID {state_id} not found",
        )
    return state


async def _ensure_city(city_id: str):
    city = await prisma.city.find_unique(where={"id": city_id})
    if not city:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"City with ID {city_id} not found",
        )
    return city


async def list_countries(skip: int | None = None, limit: int | None = None):
    countries, total = await asyncio.gather(
        prisma.country.find_many(
            order={"name": "asc"},
            **prisma_paging(skip, limit),
        ),
        prisma.country.count(),
    )
    return paginated_data(countries, total, skip, limit)


async def get_country_by_id(country_id: str):
    return await _ensure_country(country_id)


async def list_states_for_country(
    country_id: str, skip: int | None = None, limit: int | None = None
):
    await _ensure_country(country_id)
    where = {"countryId": country_id}
    states, total = await asyncio.gather(
        prisma.state.find_many(
            where=where,
            order={"name": "asc"},
            **prisma_paging(skip, limit),
        ),
        prisma.state.count(where=where),
    )
    return paginated_data(states, total, skip, limit)


async def get_state_by_id(state_id: str):
    return await _ensure_state(state_id)


async def list_cities_for_state(
    state_id: str, skip: int | None = None, limit: int | None = None
):
    await _ensure_state(state_id)
    where = {"stateId": state_id}
    cities, total = await asyncio.gather(
        prisma.city.find_many(
            where=where,
            order={"name": "asc"},
            **prisma_paging(skip, limit),
        ),
        prisma.city.count(where=where),
    )
    return paginated_data(cities, total, skip, limit)


async def get_city_by_id(city_id: str):
    return await _ensure_city(city_id)


async def search_countries(
    q: str, skip: int | None = None, limit: int | None = None
):
    where = text_search(q, "name", "iso2", "iso3", "phoneCode")
    countries, total = await asyncio.gather(
        prisma.country.find_many(
            where=where,
            order={"name": "asc"},
            **prisma_paging(skip, limit),
        ),
        prisma.country.count(where=where),
    )
    return paginated_data(countries, total, skip, limit)


async def search_states(q: str, skip: int | None = None, limit: int | None = None):
    where = merge_filters(text_search(q, "name", "stateCode"))
    states, total = await asyncio.gather(
        prisma.state.find_many(
            where=where,
            order={"name": "asc"},
            **prisma_paging(skip, limit),
        ),
        prisma.state.count(where=where),
    )
    return paginated_data(states, total, skip, limit)


async def search_cities(q: str, skip: int | None = None, limit: int | None = None):
    where = text_search(q, "name")
    cities, total = await asyncio.gather(
        prisma.city.find_many(
            where=where,
            order={"name": "asc"},
            **prisma_paging(skip, limit),
        ),
        prisma.city.count(where=where),
    )
    return paginated_data(cities, total, skip, limit)