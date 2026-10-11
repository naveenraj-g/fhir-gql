"""
Shared pagination/ordering argument types for every resource's GraphQL list
query (`patients`, `organizations`, `locations`, etc.).

`sort`/`total_mode`/`limit`/`offset` are identical in shape and meaning
across every resource on fhir-server (same names, same semantics, same
defaults — see app/core/pagination.py's `ListParams` on fhir-server, which
every resource's list route depends on the same way). Only the resource's
actual *filters* differ, which is why those stay hand-written per resource
(e.g. app/gql/organization/types/filter.py's OrganizationFilterInput) rather
than living here.

Each is a plain type alias to an `Annotated[...]` — Strawberry reads the
description off the annotation at the point the parameter is declared, so
aliasing it here and importing it into a resolver's signature is exactly
equivalent to writing the Annotated[...] inline, just without repeating it
in every resource's queries.py.

Usage:
    from app.gql.common.pagination import LimitArg, OffsetArg, SortArg, TotalModeArg

    async def organizations(
        self, info, ...,
        sort: SortArg = None,
        total_mode: TotalModeArg = "accurate",
        limit: LimitArg = 50,
        offset: OffsetArg = 0,
    ) -> ...: ...
"""

from typing import Annotated

import strawberry

# Registers TotalMode as a GraphQL enum (side-effect import) — required
# before referencing TotalModeEnum below.
import app.gql.enums  # noqa: F401
from app.gql.enums import TotalModeEnum

SortArg = Annotated[
    str | None,
    strawberry.argument(
        description="Field to sort by. Prefix with '-' for descending order (e.g. '-created_at')."
    ),
]

TotalModeArg = Annotated[
    TotalModeEnum,
    strawberry.argument(
        description=(
            "'accurate' runs a COUNT(*) and returns the real total. "
            "'none' skips it entirely (total is returned as null) — use this "
            "on large tables when the caller only needs the current page."
        )
    ),
]

LimitArg = Annotated[int, strawberry.argument(description="Page size.")]

OffsetArg = Annotated[int, strawberry.argument(description="Number of rows to skip.")]

__all__ = ["LimitArg", "OffsetArg", "SortArg", "TotalModeArg"]
