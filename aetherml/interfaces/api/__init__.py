"""FastAPI-based REST API for AetherML.

Thin HTTP layer over ``aetherml.run_pipeline()``.  No business logic
lives here — request validation, auth, and rate-limiting are delegated
to FastAPI middleware.

Usage::

    uvicorn aetherml.interfaces.api.app:app
"""
