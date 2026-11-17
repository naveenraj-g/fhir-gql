"""
The Location resource on the GraphQL gateway. Mirrors app.gql.organization
exactly — see that package's docstring for the overall design (one canonical
FHIR R4-shaped resource, connector translators that only supply paths,
search wiring and the PATCH body shape, genuine FHIR R4 search on both
backends).

Location-specific points:
- queries.py has `getFhirLocation`, `searchFhirLocations` and
  `getFhirLocations`; the search adds the Location-only parameters
  `status`, `operational-status`, `organization`, and `near`
  (`latitude|longitude|distance|units`; each match then carries a
  `location-distance` extension, exposed on the search result).
- `Location.address` is 0..1 (Organization's is 0..*) and Location has no
  top-level `active`.
- Mutations need the `location:create` / `:update` / `:delete` permissions.
"""
