"""Pytest configuration and fixtures."""

import pytest
from httpx import ASGITransport, AsyncClient
from hypothesis import settings, Verbosity

from app.main import app

# Configure Hypothesis for faster test runs
# Use 'fast' profile for CI/quick runs, 'default' for thorough testing
settings.register_profile("fast", max_examples=10, deadline=None)
settings.register_profile("ci", max_examples=25, deadline=None)
settings.register_profile("thorough", max_examples=100, deadline=None)

# Load the fast profile by default for quicker feedback
settings.load_profile("fast")


@pytest.fixture
async def client() -> AsyncClient:
    """Create an async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
