"""
GraphQL input types for the Location resource, derived from the generated Pydantic models by
`app.gql.fhir_types` (see app.gql.organization.types.input for the same pattern).
"""

from app.gql.fhir_types import input_type
from app.schemas.fhir_resources import Location, LocationPatch

# Create input (`createFhirLocation`).
FhirLocationInput = input_type(Location)
# Update input (`updateFhirLocation`): the same elements, all optional at the top level.
FhirLocationPatchInput = input_type(LocationPatch, name="FhirLocationPatchInput")
