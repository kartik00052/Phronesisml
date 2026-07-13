"""Phronesis REST API — thin HTTP layer over the Phronesis SDK.

No business logic lives here — request validation, error mapping, and
middleware are handled by FastAPI.  Run with::

    uvicorn Phronesis.interfaces.api.app:app --reload
"""
