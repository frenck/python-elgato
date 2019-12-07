"""Tests for retreiving information from the Elgato Key Light device."""
import aiohttp
import pytest
from elgato import Elgato, State

from . import load_fixture


@pytest.mark.asyncio
async def test_state(event_loop, aresponses):
    """Test getting Elgato Key Light state."""
    aresponses.add(
        "example.com:9123",
        "/elgato/lights",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("state.json"),
        ),
    )
    async with aiohttp.ClientSession(loop=event_loop) as session:
        elgato = Elgato("example.com", session=session, loop=event_loop,)
        state: State = await elgato.state()
        assert state
        assert state.brightness == 21
        assert state.on
        assert state.temperature == 297


@pytest.mark.asyncio
async def test_change_state(event_loop, aresponses):
    """Test changing Elgato Key Light State."""

    async def response_handler(request):
        data = await request.json()
        assert data == {
            "numberOfLights": 1,
            "lights": [{"on": 1, "brightness": 100, "temperature": 100}],
        }
        return aresponses.Response(
            status=200, headers={"Content-Type": "application/json"}, text="{}",
        )

    aresponses.add("example.com:9123", "/elgato/lights", "PUT", response_handler)

    async with aiohttp.ClientSession(loop=event_loop) as session:
        elgato = Elgato("example.com", session=session, loop=event_loop,)
        await elgato.light(on=True, brightness=100, temperature=100)
