"""
GraphQL transport layer.

This package is a second transport in front of the exact same service layer
the REST routers (app/routers/*.py) use — no business logic lives here.
See app/gql/schema.py for how the FastAPI-mountable GraphQL router is built,
and ARCHITECTURE.md for the reasoning behind adding GraphQL on top of REST.
"""
