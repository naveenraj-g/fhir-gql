"""
Mutation fields for the Location resource — same genuinely FHIR R4-shaped
input/output regardless of which connector (internal, medplum, ...) is
actually active; each connector's translator maps this shape onto its own
write conventions. Mirrors app.gql.organization.mutations exactly — see
that module and app.gql.organization's package docstring, and
app.connectors.base.LocationWireTranslator's docstring for why write
translation is NOT a pass-through for `internal` the way reads are.
"""

from typing import Annotated

import strawberry

from app.connectors.translator_registry import active_location_translator
from app.fhir.schemas.location import FhirLocationResponse
from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.location.types.input import FhirLocationInput
from app.gql.location.types.response import FhirLocationType
from app.gql.permissions import require_gql_permission


@strawberry.type(description="Mutation fields for the Location resource.")
class FhirLocationMutation:
    """Mutation fields for the Location resource. Mixed into the root `Mutation` type in app/gql/schema.py."""

    @strawberry.mutation(
        description=(
            "Create a new Location from a genuine FHIR R4 payload. "
            "Requires the `location:create` permission."
        )
    )
    @translate_errors
    async def create_fhir_location(
        self,
        info: strawberry.types.Info,
        input: Annotated[
            FhirLocationInput,
            strawberry.argument(
                description="The Location to create, in FHIR R4 shape."
            ),
        ],
    ) -> FhirLocationType:
        """Create a new Location — mirrors POST /Location."""
        actor = require_gql_permission(info, "location", "create")
        connector = get_container(info).core.fhir_client()
        translator = active_location_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json")
        raw = await connector.post(
            translator.list_path(),
            translator.to_wire_create(data),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirLocationType.from_pydantic(
            FhirLocationResponse.model_validate(translator.from_wire(raw))
        )

    @strawberry.mutation(
        description=(
            "Partially update a Location from a genuine FHIR R4 payload — "
            "only supplied fields are written. Requires the "
            "`location:update` permission."
        )
    )
    @translate_errors
    async def update_fhir_location(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
        input: Annotated[
            FhirLocationInput,
            strawberry.argument(description="Fields to update, in FHIR R4 shape."),
        ],
    ) -> FhirLocationType:
        """Update a Location by FHIR id — mirrors PATCH /Location/{id}."""
        actor = require_gql_permission(info, "location", "update")
        connector = get_container(info).core.fhir_client()
        translator = active_location_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json")
        raw = await connector.patch(
            translator.item_path(id),
            translator.to_wire_patch(data),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirLocationType.from_pydantic(
            FhirLocationResponse.model_validate(translator.from_wire(raw))
        )

    @strawberry.mutation(
        description=(
            "Permanently delete a Location by its FHIR resource id. "
            "Irreversible. Requires the `location:delete` permission. "
            "Returns true on success."
        )
    )
    @translate_errors
    async def delete_fhir_location(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
    ) -> bool:
        """Delete a Location by FHIR id — mirrors DELETE /Location/{id}."""
        actor = require_gql_permission(info, "location", "delete")
        connector = get_container(info).core.fhir_client()
        translator = active_location_translator()
        await connector.delete(translator.item_path(id), actor=actor)
        return True
