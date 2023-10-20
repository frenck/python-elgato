"""Tests for retrieving information from the Elgato Light device."""
from __future__ import annotations

import pytest
from aiohttp import ClientResponse, ClientSession
from aresponses import Response, ResponsesMockServer

from elgato import Elgato, ElgatoError, State

from . import load_fixture


async def test_state_temperature(aresponses: ResponsesMockServer) -> None:
    """Test getting Elgato Light state in temperature mode."""
    aresponses.add(
        "example.com:9123",
        "/elgato/lights",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("state-temperature.json"),
        ),
    )
    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        state: State = await elgato.state()
        assert state
        assert state.brightness == 21
        assert state.hue is None
        assert state.on
        assert state.saturation is None
        assert state.temperature == 297


async def test_state_color(aresponses: ResponsesMockServer) -> None:
    """Test getting Elgato Light state in color mode."""
    aresponses.add(
        "example.com:9123",
        "/elgato/lights",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("state-color.json"),
        ),
    )
    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        state: State = await elgato.state()
        assert state
        assert state.brightness == 50
        assert state.hue == 358.0
        assert state.on
        assert state.saturation == 6.0
        assert state.temperature is None


async def test_change_state_temperature(aresponses: ResponsesMockServer) -> None:
    """Test changing Elgato Light State in temperature mode."""

    async def response_handler(request: ClientResponse) -> Response:
        """Response handler for this test."""
        data = await request.json()
        assert data == {
            "numberOfLights": 1,
            "lights": [{"on": 1, "brightness": 100, "temperature": 200}],
        }
        return aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text="{}",
        )

    aresponses.add("example.com:9123", "/elgato/lights", "PUT", response_handler)

    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        await elgato.light(on=True, brightness=100, temperature=200)


async def test_change_state_color(aresponses: ResponsesMockServer) -> None:
    """Test changing Elgato Light State in color mode."""

    async def response_handler(request: ClientResponse) -> Response:
        """Response handler for this test."""
        data = await request.json()
        assert data == {
            "numberOfLights": 1,
            "lights": [{"on": 1, "brightness": 100, "hue": 10.1, "saturation": 20.2}],
        }
        return aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text="{}",
        )

    aresponses.add("example.com:9123", "/elgato/lights", "PUT", response_handler)

    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        await elgato.light(on=True, brightness=100, hue=10.1, saturation=20.2)


@pytest.mark.parametrize(
    ("state", "message"),
    [
        (
            {"hue": 10.1, "temperature": 10},
            "Cannot set temperature together with hue or saturation",
        ),
        (
            {"saturation": 10.1, "temperature": 10},
            "Cannot set temperature together with hue or saturation",
        ),
        (
            {"brightness": -1},
            "Brightness not between 0 and 100",
        ),
        (
            {"brightness": 101},
            "Brightness not between 0 and 100",
        ),
        (
            {"hue": -1},
            "Hue not between 0 and 360",
        ),
        (
            {"hue": 360.1},
            "Hue not between 0 and 360",
        ),
        (
            {"saturation": -1},
            "Saturation not between 0 and 100",
        ),
        (
            {"saturation": 100.1},
            "Saturation not between 0 and 100",
        ),
        (
            {"temperature": 142},
            "Color temperature out of range",
        ),
        (
            {"temperature": 345},
            "Color temperature out of range",
        ),
        (
            {},
            "No parameters to set, light not adjusted",
        ),
    ],
)
async def test_change_state_errors(state: dict[str, int | float], message: str) -> None:
    """Test changing Elgato Light State with invalid values."""
    elgato = Elgato("example.com")
    with pytest.raises(ElgatoError, match=message):
        await elgato.light(**state)  # type: ignore[arg-type]
