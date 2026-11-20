from typing import Annotated

from fastapi import APIRouter, Query

from app.common.pagination import PaginatedData
from app.common.response import APIResponse, success_response
from app.modules.location import controller
from app.modules.location.schema import CityResponse, CountryResponse, StateResponse

locationRouter = APIRouter(tags=["Location"])


@locationRouter.get(
    "/countries/search",
    response_model=APIResponse[PaginatedData[CountryResponse]],
)
async def search_countries(
    q: Annotated[str, Query(min_length=1)],
    skip: int | None = Query(default=None, ge=0),
    limit: int | None = Query(default=None, ge=1, le=100),
):
    data = await controller.search_countries(q=q, skip=skip, limit=limit)
    return success_response(data=data, message="Countries retrieved successfully")


@locationRouter.get(
    "/countries",
    response_model=APIResponse[PaginatedData[CountryResponse]],
)
async def list_countries(
    skip: int | None = Query(default=None, ge=0),
    limit: int | None = Query(default=None, ge=1, le=100),
):
    data = await controller.list_countries(skip=skip, limit=limit)
    return success_response(data=data, message="Countries retrieved successfully")


@locationRouter.get(
    "/countries/{country_id}/states",
    response_model=APIResponse[PaginatedData[StateResponse]],
)
async def list_states_for_country(
    country_id: str,
    skip: int | None = Query(default=None, ge=0),
    limit: int | None = Query(default=None, ge=1, le=100),
):
    data = await controller.list_states_for_country(
        country_id, skip=skip, limit=limit
    )
    return success_response(data=data, message="States retrieved successfully")


@locationRouter.get(
    "/countries/{country_id}",
    response_model=APIResponse[CountryResponse],
)
async def get_country(country_id: str):
    country = await controller.get_country_by_id(country_id)
    return success_response(data=country, message="Country retrieved successfully")


@locationRouter.get(
    "/states/search",
    response_model=APIResponse[PaginatedData[StateResponse]],
)
async def search_states(
    q: Annotated[str, Query(min_length=1)],
    skip: int | None = Query(default=None, ge=0),
    limit: int | None = Query(default=None, ge=1, le=100),
):
    data = await controller.search_states(q=q, skip=skip, limit=limit)
    return success_response(data=data, message="States retrieved successfully")


@locationRouter.get(
    "/states/{state_id}/cities",
    response_model=APIResponse[PaginatedData[CityResponse]],
)
async def list_cities_for_state(
    state_id: str,
    skip: int | None = Query(default=None, ge=0),
    limit: int | None = Query(default=None, ge=1, le=100),
):
    data = await controller.list_cities_for_state(state_id, skip=skip, limit=limit)
    return success_response(data=data, message="Cities retrieved successfully")


@locationRouter.get(
    "/states/{state_id}",
    response_model=APIResponse[StateResponse],
)
async def get_state(state_id: str):
    state = await controller.get_state_by_id(state_id)
    return success_response(data=state, message="State retrieved successfully")


@locationRouter.get(
    "/cities/search",
    response_model=APIResponse[PaginatedData[CityResponse]],
)
async def search_cities(
    q: Annotated[str, Query(min_length=1)],
    skip: int | None = Query(default=None, ge=0),
    limit: int | None = Query(default=None, ge=1, le=100),
):
    data = await controller.search_cities(q=q, skip=skip, limit=limit)
    return success_response(data=data, message="Cities retrieved successfully")


@locationRouter.get(
    "/cities/{city_id}",
    response_model=APIResponse[CityResponse],
)
async def get_city(city_id: str):
    city = await controller.get_city_by_id(city_id)
    return success_response(data=city, message="City retrieved successfully")