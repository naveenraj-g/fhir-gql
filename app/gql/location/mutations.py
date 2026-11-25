"""
Mutation fields for the Location resource — same genuinely FHIR R4-shaped
input/output regardless of which connector (internal, medplum, ...) is
actually active. Mirrors app.gql.organization.mutations exactly. The input is a FHIR R4 Location and is sent to the
backend as-is: `internal` (fhir-server) takes a FHIR body for create and a
plain partial-object merge-patch for update, `medplum` needs an RFC 6902
JSON Patch array for update — that PATCH difference is the only write
translation left (see app.connectors.base.LocationWireTranslator and
app.gql.location's package docstring).
"""

from typing import Annotated

import strawberry

from app.connectors.translator_registry import active_location_translator
from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.fhir_types import input_to_dict
from app.gql.location.types.input import (
    FhirLocationInput,
    FhirLocationPatchInput,
)
from app.gql.location.types.response import FhirLocationType
from app.gql.permissions import require_gql_permission
from app.schemas.fhir_resources import Location, LocationPatch


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
        # The input object back to the FHIR document it stands for, checked against the model
        # (a ValidationError becomes a GraphQL error) before it is sent to the backend.
        data = input_to_dict(input)
        Location.model_validate(data)
        raw = await connector.post(
            translator.list_path(),
            translator.to_wire_create(data),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return translator.from_wire(raw)

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
            FhirLocationPatchInput,
            strawberry.argument(description="Fields to update, in FHIR R4 shape."),
        ],
    ) -> FhirLocationType:
        """Update a Location by FHIR id — mirrors PATCH /Location/{id}."""
        actor = require_gql_permission(info, "location", "update")
        connector = get_container(info).core.fhir_client()
        translator = active_location_translator()
        # The merge-patch the caller supplied, as a FHIR fragment, checked against the patch model.
        data = input_to_dict(input)
        LocationPatch.model_validate(data)
        raw = await connector.patch(
            translator.item_path(id),
            translator.to_wire_patch(data),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return translator.from_wire(raw)

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
