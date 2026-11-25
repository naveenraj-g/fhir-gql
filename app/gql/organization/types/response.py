"""
GraphQL object (output) type for the Organization resource.

One canonical, genuinely FHIR R4-shaped Organization - the same shape regardless of which
connector (internal, medplum, ...) is active. The type, and every nested datatype it uses
(Coding, Identifier, Address, ...), is derived from the generated Pydantic model
`app.schemas.fhir_resources.Organization` by `app.gql.fhir_types`, so it carries every element
HL7 defines with HL7's own descriptions; nothing is declared by hand here.
"""

from app.gql.fhir_types import output_type
from app.schemas.fhir_resources import Organization

# The GraphQL type for a FHIR R4 Organization (named `FhirOrganizationType`). Resolvers return the
# raw FHIR dict a connector produced; the type's fields read it by FHIR element name.
FhirOrganizationType = output_type(Organization)
