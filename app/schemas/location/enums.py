"""
Location-specific enumeration types.

These enums are scoped to the FHIR R4 Location resource. Shared code sets
(address use/type, contact point, identifier use) live in app.schemas.enums
and are imported from there.

Reference: https://hl7.org/fhir/R4/location.html
"""

from enum import Enum


class LocationStatus(str, Enum):
    """
    FHIR Location.status — whether the location is currently in active use.

    Values defined by https://hl7.org/fhir/R4/valueset-location-status.html:
      active    — the location is operational.
      suspended — the location is temporarily closed.
      inactive  — the location is no longer used.
    """

    active = "active"
    suspended = "suspended"
    inactive = "inactive"


class LocationMode(str, Enum):
    """
    FHIR Location.mode — whether this record represents a specific physical
    place or a kind/category of place.

    Values defined by https://hl7.org/fhir/R4/valueset-location-mode.html:
      instance — a specific, real physical location (the common case).
      kind     — a class of locations, not a specific one (e.g. "a bed").
    """

    instance = "instance"
    kind = "kind"
