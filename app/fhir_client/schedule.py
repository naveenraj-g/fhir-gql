"""
FHIR client for Schedule resources.

Thin wrapper around the shared FhirClient that knows the fhir-server path
for the Schedule resource. No business logic lives here — all validation
and derivation (actor existence/tenant checks, cardinality rules,
service_category/service_type/specialty derivation) belongs in
ScheduleService. Same shape as app/fhir_client/organization.py.

Reference: https://hl7.org/fhir/R4/schedule.html
"""

from app.auth.models import AuthUser
from app.fhir_client.client import FhirClient
from app.core.logging import trace_methods

_PATH = "/schedules"


@trace_methods
class ScheduleClient:
    """
    Domain-specific HTTP client for Schedule resources.

    Delegates every request to the shared FhirClient singleton, which
    handles authentication headers, base-URL resolution, and error
    propagation.
    """

    def __init__(self, fhir: FhirClient) -> None:
        """
        Args:
            fhir: The singleton FhirClient — owns the httpx session and base URL config.
        """
        self._fhir = fhir

    async def create(self, data: dict, actor: AuthUser, accept: str | None = None) -> dict:
        """POST /schedules — create a new Schedule resource."""
        return await self._fhir.post(_PATH, data, actor, accept=accept)

    async def get_by_id(self, schedule_id: int, accept: str | None = None) -> dict:
        """GET /schedules/{schedule_id} — fetch a single Schedule by integer ID."""
        return await self._fhir.get(f"{_PATH}/{schedule_id}", accept=accept)

    async def list(self, accept: str | None = None, **params) -> dict:
        """
        GET /schedules — list Schedules with optional filters.

        Strips None values from **params — an omitted param means "no
        filter", not a literal `?key=None` sent to the fhir-server.
        """
        clean = {k: v for k, v in params.items() if v is not None}
        return await self._fhir.get(_PATH, params=clean, accept=accept)

    async def patch(self, schedule_id: int, data: dict, actor: AuthUser, accept: str | None = None) -> dict:
        """PATCH /schedules/{schedule_id} — partially update a Schedule."""
        return await self._fhir.patch(f"{_PATH}/{schedule_id}", data, actor, accept=accept)

    async def delete(self, schedule_id: int) -> None:
        """DELETE /schedules/{schedule_id} — permanently remove a Schedule."""
        await self._fhir.delete(f"{_PATH}/{schedule_id}")
