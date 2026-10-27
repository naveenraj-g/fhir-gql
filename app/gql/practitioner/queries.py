"""
Query fields for the Practitioner resource — one canonical, genuinely FHIR
R4-shaped Practitioner regardless of which connector (internal, medplum,
...) is actually active. Mirrors app.gql.organization.queries/
app.gql.location.queries/app.gql.healthcare_service.queries exactly — see
those modules and app.gql.organization's package docstring for the
overall idea.
"""

from typing import Annotated

import strawberry

from app.connectors.translator_registry import active_practitioner_translator
from app.fhir.schemas.practitioner import FhirPractitionerResponse
from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.permissions import require_gql_permission
from app.gql.practitioner.types.response import FhirPractitionerType


def _entries_from_bundle(bundle: dict) -> list[dict]:
    """A FHIR search response is a Bundle regardless of backend — pull out
    each entry's resource. Falls back to treating the response itself as a
    single resource if it isn't a Bundle (defensive; both of today's
    connectors always return a Bundle for a collection GET)."""
    if bundle.get("resourceType") == "Bundle":
        return [entry["resource"] for entry in bundle.get("entry") or []]
    return [bundle]


@strawberry.type(description="Query fields for the Practitioner resource.")
class FhirPractitionerQuery:
    """Query fields for the Practitioner resource. Mixed into the root `Query` type in app/gql/schema.py."""

    @strawberry.field(
        description="Fetch a single Practitioner by its FHIR resource id, in genuine FHIR R4 shape. Requires the `practitioner:read` permission."
    )
    @translate_errors
    async def get_fhir_practitioner(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
    ) -> FhirPractitionerType:
        """Fetch a single Practitioner by FHIR id — mirrors GET /Practitioner/{id}."""
        actor = require_gql_permission(info, "practitioner", "read")
        connector = get_container(info).core.fhir_client()
        translator = active_practitioner_translator()
        raw = await connector.get(
            translator.item_path(id), accept=translator.accept, actor=actor
        )
        data = translator.from_wire(raw)
        return FhirPractitionerType.from_pydantic(
            FhirPractitionerResponse.model_validate(data)
        )

    @strawberry.field(
        description=(
            "Search Practitioners, in genuine FHIR R4 shape, with every "
            "FHIR R4 Practitioner search parameter "
            "(https://hl7.org/fhir/R4/practitioner.html#search) except "
            "`phonetic` — active, address, address-city, address-country, "
            "address-postalcode, address-state, address-use, "
            "communication, email, family, gender, given, identifier, "
            "name, phone, telecom — plus limit/offset pagination. "
            "Requires the `practitioner:read` permission."
        )
    )
    @translate_errors
    async def get_fhir_practitioners(
        self,
        info: strawberry.types.Info,
        name: Annotated[
            str | None,
            strawberry.argument(
                description="Matches any string field in HumanName."
            ),
        ] = None,
        family: Annotated[
            str | None,
            strawberry.argument(description="Partial match on family name."),
        ] = None,
        given: Annotated[
            str | None,
            strawberry.argument(description="Partial match on any given name."),
        ] = None,
        identifier: Annotated[
            str | None,
            strawberry.argument(
                description="Exact match on a business identifier value."
            ),
        ] = None,
        active: Annotated[
            bool | None,
            strawberry.argument(description="Filter by active status."),
        ] = None,
        gender: Annotated[
            str | None,
            strawberry.argument(description="male | female | other | unknown."),
        ] = None,
        communication: Annotated[
            str | None,
            strawberry.argument(
                description="Exact match on a communication language code."
            ),
        ] = None,
        telecom: Annotated[
            str | None,
            strawberry.argument(description="Exact match on any contact value."),
        ] = None,
        phone: Annotated[
            str | None,
            strawberry.argument(description="Exact match on a phone contact value."),
        ] = None,
        email: Annotated[
            str | None,
            strawberry.argument(description="Exact match on an email contact value."),
        ] = None,
        address: Annotated[
            str | None,
            strawberry.argument(
                description="Partial match against any Address sub-field (line, city, district, state, country, postalCode, text)."
            ),
        ] = None,
        address_city: Annotated[
            str | None,
            strawberry.argument(
                name="addressCity", description="Filter by address city — partial match."
            ),
        ] = None,
        address_state: Annotated[
            str | None,
            strawberry.argument(
                name="addressState",
                description="Filter by address state — partial match.",
            ),
        ] = None,
        address_postal_code: Annotated[
            str | None,
            strawberry.argument(
                name="addressPostalCode",
                description="Filter by address postal code — exact match.",
            ),
        ] = None,
        address_country: Annotated[
            str | None,
            strawberry.argument(
                name="addressCountry",
                description="Filter by address country — partial match.",
            ),
        ] = None,
        address_use: Annotated[
            str | None,
            strawberry.argument(
                name="addressUse", description="home | work | temp | old | billing."
            ),
        ] = None,
        limit: Annotated[
            int, strawberry.argument(description="Max results (default 50).")
        ] = 50,
        offset: Annotated[
            int, strawberry.argument(description="Pagination offset (default 0).")
        ] = 0,
    ) -> list[FhirPractitionerType]:
        """Search Practitioners — mirrors GET /Practitioner?name=...&active=..."""
        actor = require_gql_permission(info, "practitioner", "read")
        connector = get_container(info).core.fhir_client()
        translator = active_practitioner_translator()
        params = translator.list_params(
            name,
            family,
            given,
            identifier,
            active,
            gender,
            communication,
            telecom,
            phone,
            email,
            address,
            address_city,
            address_state,
            address_postal_code,
            address_country,
            address_use,
            limit,
            offset,
        )
        raw = await connector.get(
            translator.list_path(),
            params=params,
            accept=translator.accept,
            actor=actor,
        )
        resources = _entries_from_bundle(translator.from_wire(raw))
        return [
            FhirPractitionerType.from_pydantic(
                FhirPractitionerResponse.model_validate(r)
            )
            for r in resources
        ]
