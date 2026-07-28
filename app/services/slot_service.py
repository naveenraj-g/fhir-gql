"""
Business logic service for the Slot resource.

SlotService sits between the router/resolvers and SlotClient. It owns:
  - `schedule` reference validation (existence + tenant match) on manual
    create, via the shared `validate_reference` helper — the sibling
    project never validated this reference at all.
  - `service_category`/`service_type`/`specialty` smart-defaulting: when
    omitted on manual create (or on /generate), they're copied from the
    parent Schedule's own (already-derived) stored values rather than left
    empty or requiring the caller to retype them.
  - Availability-aware bulk generation (`generate()`): reads the Schedule's
    PractitionerRole actor's `availability[]` (`available_times` = declared
    weekly hours, `not_available_times` = leave/exceptions) and only
    creates Slots inside those declared windows, for matching days within
    the requested range — not a blind fixed-interval fill across the whole
    range like the sibling project's version. Also skips any computed
    window that overlaps an already-existing Slot on the Schedule (a
    duplicate-slot guard the sibling doesn't have), so `generate()` is
    safely re-callable to extend a date range.
  - Empty-patch rejection (422) on update().

This still lives directly in SlotService (`ScheduleClient` +
`PractitionerRoleClient` injected, same DI shape used repeatedly), not the
app/workflows/ tier (see dev-docs/13-workflow-orchestration.md) —
consistent with the same call made for Schedule's own derivation logic.
"""

# typing.List/Tuple (not lowercase list[]/tuple[]) are used deliberately in
# this file's own annotations: this class defines a method named `list`,
# and Python's lazy annotation evaluation resolves a bare `list[...]`
# generic used elsewhere in the class body to that method instead of the
# builtin, raising "'function' object is not subscriptable" (same issue
# hit and documented in app/services/schedule_service.py).
from datetime import date, datetime, time, timedelta
from typing import List, Optional, Tuple

from fastapi import HTTPException, status

from app.auth.models import AuthUser
from app.fhir_client.practitioner_role import PractitionerRoleClient
from app.fhir_client.schedule import ScheduleClient
from app.fhir_client.slot import SlotClient
from app.schemas.slot.input import ListSlotsSchema, SlotCreateSchema, SlotGenerateSchema, SlotPatchSchema
from app.services.tenant_scope import validate_reference

# Day-of-week codes in datetime.weekday() order (0=Monday..6=Sunday),
# matching the DayOfWeek enum's wire values used across this project.
_DAY_CODES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# Page size used when paginating through a Schedule's existing Slots for
# the duplicate-generation guard.
_EXISTING_SLOTS_PAGE_SIZE = 200


def _strip_ids(entries: Optional[List[dict]]) -> List[dict]:
    """Drop the fhir-server row `id` when copying a Schedule's sub-array onto a new Slot."""
    return [{k: v for k, v in entry.items() if k != "id"} for entry in (entries or [])]


def _parse_time(value: Optional[str]) -> Optional[time]:
    """Parse an HH:MM:SS string into a `time`, or None if unset/unparsable."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%H:%M:%S").time()
    except ValueError:
        return None


def _overlaps_any(start: datetime, end: datetime, periods: List[Tuple[datetime, datetime]]) -> bool:
    """True if [start, end) overlaps any [period_start, period_end) in `periods`."""
    return any(start < period_end and end > period_start for period_start, period_end in periods)


class SlotService:
    """
    Application service for Slot CRUD and bulk-generation use cases.

    Instantiated per-request by the DI container (SlotContainer) via
    Factory provider, so it holds no shared state between requests.
    """

    def __init__(
        self,
        client: SlotClient,
        schedule_client: ScheduleClient,
        practitioner_role_client: PractitionerRoleClient,
    ) -> None:
        """
        Args:
            client:                   The SlotClient injected by the DI container.
            schedule_client:          Validates `schedule` references and supplies the
                                      parent Schedule's stored service_category/service_type/
                                      specialty defaults, plus its planning_horizon/actor
                                      data for generate().
            practitioner_role_client: Supplies the Schedule's PractitionerRole actor's
                                      `availability` for generate().
        """
        self._client = client
        self._schedule_client = schedule_client
        self._practitioner_role_client = practitioner_role_client

    async def create(self, dto: SlotCreateSchema, actor: AuthUser, accept: str | None = None) -> dict:
        """
        Create a single Slot, validating `schedule` and defaulting
        `service_category`/`service_type`/`specialty` from the parent
        Schedule's own stored values when the caller omits them.

        Raises:
            HTTPException(422): If `schedule` is malformed.
            HTTPException(404): If `schedule` doesn't exist, or belongs to a different tenant.
        """
        schedule_dict = await validate_reference(
            dto.schedule,
            resource_type="Schedule",
            get_by_id=self._schedule_client.get_by_id,
            actor=actor,
            field_name="schedule",
        )

        payload = dto.model_dump(exclude_none=True, mode="json")
        if dto.service_category is None:
            payload["service_category"] = _strip_ids(schedule_dict.get("service_category"))
        if dto.service_type is None:
            payload["service_type"] = _strip_ids(schedule_dict.get("service_type"))
        if dto.specialty is None:
            payload["specialty"] = _strip_ids(schedule_dict.get("specialty"))

        return await self._client.create(payload, actor, accept=accept)

    async def get_by_id(self, slot_id: int, actor: AuthUser, accept: str | None = None) -> dict:
        """Fetch a single Slot by its numeric ID."""
        return await self._client.get_by_id(slot_id, accept=accept)

    async def list(self, filters: ListSlotsSchema, actor: AuthUser, accept: str | None = None) -> dict:
        """Return a paginated, optionally filtered list of Slot resources."""
        return await self._client.list(
            accept=accept,
            status=filters.status,
            schedule_id=filters.schedule_id,
            user_id=filters.user_id,
            org_id=filters.org_id,
            start_after=filters.start_after,
            start_before=filters.start_before,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def update(self, slot_id: int, dto: SlotPatchSchema, actor: AuthUser, accept: str | None = None) -> dict:
        """
        Partially update a Slot's scalar fields.

        Raises:
            HTTPException(422): If the patch body is empty.
        """
        payload = dto.model_dump(exclude_none=True, mode="json")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one field must be provided for update.",
            )
        return await self._client.patch(slot_id, payload, actor, accept=accept)

    async def delete(self, slot_id: int, actor: AuthUser) -> None:
        """Permanently delete a Slot resource."""
        await self._client.delete(slot_id)

    # ── Availability-aware bulk generation ────────────────────────────────────

    async def _fetch_existing_windows(self, schedule_id: int) -> List[Tuple[datetime, datetime]]:
        """Page through every existing Slot on `schedule_id` and collect its (start, end) window."""
        windows: List[Tuple[datetime, datetime]] = []
        offset = 0
        while True:
            result = await self._client.list(schedule_id=schedule_id, limit=_EXISTING_SLOTS_PAGE_SIZE, offset=offset)
            page = result.get("data", [])
            for item in page:
                start_str, end_str = item.get("start"), item.get("end")
                if start_str and end_str:
                    windows.append((datetime.fromisoformat(start_str), datetime.fromisoformat(end_str)))
            if len(page) < _EXISTING_SLOTS_PAGE_SIZE:
                return windows
            offset += _EXISTING_SLOTS_PAGE_SIZE

    async def generate(self, dto: SlotGenerateSchema, actor: AuthUser) -> dict:
        """
        Availability-aware bulk Slot generation for a Schedule.

        The Schedule's provider actor must be a PractitionerRole with at
        least one `availability[].available_times` entry declared — slots
        are only created inside those declared weekly windows, for
        matching days within [generation_start, generation_end], excluding
        declared `not_available_times` periods and any window that overlaps
        an already-existing Slot on the Schedule.

        Raises:
            HTTPException(404): If the Schedule doesn't exist.
            HTTPException(422): If `generation_start` precedes the Schedule's own
                `planning_horizon_start`, or the Schedule's actor isn't a
                PractitionerRole with usable availability declared.
        """
        schedule_dict = await self._schedule_client.get_by_id(dto.schedule_id)

        generation_start = dto.generation_start
        generation_end = dto.generation_end

        horizon_start_str = schedule_dict.get("planning_horizon_start")
        if horizon_start_str and generation_start < datetime.fromisoformat(horizon_start_str):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"generation_start is before the Schedule's planning_horizon_start ({horizon_start_str}).",
            )
        horizon_end_str = schedule_dict.get("planning_horizon_end")
        if horizon_end_str:
            horizon_end = datetime.fromisoformat(horizon_end_str)
            if generation_end > horizon_end:
                generation_end = horizon_end

        actors = schedule_dict.get("actor") or []
        provider_actor = next((a for a in actors if a.get("reference_type") == "PractitionerRole"), None)
        if provider_actor is None or provider_actor.get("reference_id") is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cannot auto-generate slots: the Schedule's actor is not a PractitionerRole with declared availability.",
            )

        practitioner_role = await self._practitioner_role_client.get_by_id(provider_actor["reference_id"])

        available_windows: List[Tuple[str, time, time]] = []
        not_available_periods: List[Tuple[datetime, datetime]] = []
        for group in practitioner_role.get("availability") or []:
            for entry in group.get("available_times") or []:
                start_t = _parse_time(entry.get("available_start_time"))
                end_t = _parse_time(entry.get("available_end_time"))
                if start_t is None or end_t is None:
                    continue
                for day in entry.get("days_of_week") or []:
                    available_windows.append((day, start_t, end_t))
            for entry in group.get("not_available_times") or []:
                start_str, end_str = entry.get("during_start"), entry.get("during_end")
                if start_str and end_str:
                    not_available_periods.append((datetime.fromisoformat(start_str), datetime.fromisoformat(end_str)))

        if not available_windows:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cannot auto-generate slots: the Schedule's PractitionerRole has no availability.available_times declared.",
            )

        existing_windows = await self._fetch_existing_windows(dto.schedule_id)
        duration = timedelta(minutes=dto.slot_duration_minutes)
        tzinfo = generation_start.tzinfo

        computed_windows: List[Tuple[datetime, datetime]] = []
        skipped_count = 0
        current_date: date = generation_start.date()
        while current_date <= generation_end.date():
            day_code = _DAY_CODES[current_date.weekday()]
            for day, start_t, end_t in available_windows:
                if day != day_code:
                    continue
                window_start = max(datetime.combine(current_date, start_t, tzinfo=tzinfo), generation_start)
                window_end = min(datetime.combine(current_date, end_t, tzinfo=tzinfo), generation_end)
                cursor = window_start
                while cursor + duration <= window_end:
                    slot_start, slot_end = cursor, cursor + duration
                    if _overlaps_any(slot_start, slot_end, not_available_periods):
                        pass  # excluded by declared leave — not a "skip", just not a candidate
                    elif _overlaps_any(slot_start, slot_end, existing_windows):
                        skipped_count += 1
                    else:
                        computed_windows.append((slot_start, slot_end))
                    cursor += duration
            current_date += timedelta(days=1)

        if dto.service_category is not None:
            resolved_category = [entry.model_dump(exclude_none=True) for entry in dto.service_category]
        else:
            resolved_category = _strip_ids(schedule_dict.get("service_category"))
        if dto.service_type is not None:
            resolved_type = [entry.model_dump(exclude_none=True) for entry in dto.service_type]
        else:
            resolved_type = _strip_ids(schedule_dict.get("service_type"))
        if dto.specialty is not None:
            resolved_specialty = [entry.model_dump(exclude_none=True) for entry in dto.specialty]
        else:
            resolved_specialty = _strip_ids(schedule_dict.get("specialty"))

        generated_ids: List[int] = []
        errors: List[str] = []
        for slot_start, slot_end in computed_windows:
            slot_payload = {
                "schedule": f"Schedule/{dto.schedule_id}",
                "status": "free",
                "start": slot_start.isoformat(),
                "end": slot_end.isoformat(),
                "overbooked": dto.overbooked or False,
                "service_category": resolved_category,
                "service_type": resolved_type,
                "specialty": resolved_specialty,
            }
            if dto.comment is not None:
                slot_payload["comment"] = dto.comment
            if dto.appointment_type_code is not None:
                slot_payload["appointment_type_system"] = dto.appointment_type_system
                slot_payload["appointment_type_code"] = dto.appointment_type_code
                slot_payload["appointment_type_display"] = dto.appointment_type_display
                slot_payload["appointment_type_text"] = dto.appointment_type_text
            if dto.user_id is not None:
                slot_payload["user_id"] = dto.user_id
            if dto.org_id is not None:
                slot_payload["org_id"] = dto.org_id

            try:
                created = await self._client.create(slot_payload, actor)
                generated_ids.append(created["id"])
            except HTTPException as exc:
                errors.append(f"{slot_start.isoformat()}-{slot_end.isoformat()}: {exc.detail}")

        return {
            "schedule_id": dto.schedule_id,
            "generated_count": len(generated_ids),
            "skipped_count": skipped_count,
            "failed_count": len(errors),
            "slot_ids": generated_ids,
            "generation_start": dto.generation_start.isoformat(),
            "generation_end": dto.generation_end.isoformat(),
            "slot_duration_minutes": dto.slot_duration_minutes,
            "errors": errors,
        }
