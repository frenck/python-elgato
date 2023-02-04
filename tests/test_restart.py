"""Tests for restarting the Elgato Light device."""

from aiohttp import ClientSession
from aresponses import ResponsesMockServer

from elgato import Elgato


async def test_restart(aresponses: ResponsesMockServer) -> None:
    """Test restarting the Elgato Light."""
    aresponses.add(
        "example.com:9123",
        "/elgato/restart",
        "POST",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text="",
        ),
    )

    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        await elgato.restart()
