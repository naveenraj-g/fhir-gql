"""
Slot-specific enumeration types.

Scoped to the FHIR R4 Slot resource. Shared code sets live in
app.schemas.enums and are imported from there.

Reference: https://hl7.org/fhir/R4/slot.html
"""

from enum import Enum


class SlotStatus(str, Enum):
    """
    FHIR Slot.status — the free/busy status of the slot itself.

    Values defined by https://hl7.org/fhir/R4/valueset-slotstatus.html:
      busy              — the slot is busy.
      free              — the slot is free for scheduling.
      busy_unavailable  — the slot is busy and cannot be scheduled (wire value "busy-unavailable").
      busy_tentative    — the slot has been tentatively reserved (wire value "busy-tentative").
      entered_in_error  — this instance should not be treated as valid (wire value "entered-in-error").
    """

    busy = "busy"
    free = "free"
    busy_unavailable = "busy-unavailable"
    busy_tentative = "busy-tentative"
    entered_in_error = "entered-in-error"
