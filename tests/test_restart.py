"""Tests for restarting the Elgato Light device."""

from aiohttp import ClientSession
from aioresponses import aioresponses

from elgato import Elgato


async def test_restart(responses: aioresponses) -> None:
    """Test restarting the Elgato Light."""
    responses.post(
        "http://example.com:9123/elgato/restart",
        status=200,
        body="",
        content_type="application/json",
    )
    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        await elgato.restart()
