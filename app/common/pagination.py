from typing import Any, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel

T = TypeVar("T")


class ListQuery(BaseModel):
    skip: int | None = None
    limit: int | None = None
    search: str | None = None


class PaginatedData(BaseModel, Generic[T]):
    items: list[T]
    total: int
    skip: int
    limit: int


def list_query(
    skip: int | None = Query(default=None, ge=0),
    limit: int | None = Query(default=None, ge=1, le=100),
    search: str | None = Query(
        default=None,
        description="Case-insensitive search across relevant fields",
    ),
) -> ListQuery:
    return ListQuery(skip=skip, limit=limit, search=search)


def prisma_paging(skip: int | None = None, limit: int | None = None) -> dict[str, int]:
    args: dict[str, int] = {}
    if skip:
        args["skip"] = skip
    if limit is not None:
        args["take"] = limit
    return args


def contains(term: str) -> dict[str, str]:
    return {"contains": term, "mode": "insensitive"}


def text_search(
    search: str | None,
    *fields: str,
    extra: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    term = (search or "").strip()
    if not term:
        return None

    clauses: list[dict[str, Any]] = [{field: contains(term)} for field in fields]
    if extra:
        clauses.extend(extra)

    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"OR": clauses}


def merge_filters(*parts: dict[str, Any] | None) -> dict[str, Any] | None:
    filters = [part for part in parts if part]
    if not filters:
        return None
    if len(filters) == 1:
        return filters[0]
    return {"AND": filters}


def paginated_data(
    items: list[Any],
    total: int,
    skip: int | None,
    limit: int | None,
) -> dict[str, Any]:
    return {
        "items": items,
        "total": total,
        "skip": skip or 0,
        "limit": limit if limit is not None else total,
    }
