"""
GraphQL object (output) type for the Location resource.

Derived from the generated Pydantic model `app.schemas.fhir_resources.Location` by
`app.gql.fhir_types`, exactly like Organization (see app.gql.organization.types.response). The
nested datatypes it shares with Organization (Coding, Address, Reference, ...) are one GraphQL
type each, because both resources draw them from the same generated models.
"""

from app.gql.fhir_types import output_type
from app.schemas.fhir_resources import Location

# The GraphQL type for a FHIR R4 Location (named `FhirLocationType`).
FhirLocationType = output_type(Location)
