"""
BuildemUp† — API layer.

Thin HTTP endpoint wrappers around Component 1 (and later components).
Uses the Python standard library (http.server) so we have zero framework
dependencies. Production deployment on Railway can swap to Flask/FastAPI
later without touching the engine layer.
"""
