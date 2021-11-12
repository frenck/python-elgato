"""Tests for the Elgato Lights Library."""
# pylint: disable=protected-access
from __future__ import annotations

import asyncio

import aiohttp
import pytest

from elgato import Elgato
from elgato.exceptions import ElgatoConnectionError, ElgatoError


@pytest.mark.asyncio
async def test_json_request(aresponses):
    """Test JSON response is handled correctly."""
    aresponses.add(
        "example.com:9123",
        "/elgato/test",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text='{"status": "ok"}',
        ),
    )
    async with aiohttp.ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        response = await elgato._request("test")
        assert response["status"] == "ok"
        await elgato.close()


@pytest.mark.asyncio
async def test_internal_session(aresponses):
    """Test JSON response is handled correctly."""
    aresponses.add(
        "example.com:9123",
        "/elgato/test",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text='{"status": "ok"}',
        ),
    )
    async with Elgato("example.com") as elgato:
        response = await elgato._request("test")
        assert response["status"] == "ok"


@pytest.mark.asyncio
async def test_put_request(aresponses):
    """Test PUT requests are handled correctly."""
    aresponses.add(
        "example.com:9123",
        "/elgato/test",
        "PUT",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text='{"status": "ok"}',
        ),
    )
    async with aiohttp.ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        response = await elgato._request("test", method=aiohttp.hdrs.METH_PUT, data={})
        assert response["status"] == "ok"


@pytest.mark.asyncio
async def test_post_request(aresponses):
    """Test POST requests are handled correctly."""
    aresponses.add(
        "example.com:9123",
        "/elgato/test",
        "POST",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text='{"status": "ok"}',
        ),
    )
    async with aiohttp.ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        response = await elgato._request("test", method=aiohttp.hdrs.METH_POST, data={})
        assert response["status"] == "ok"


@pytest.mark.asyncio
async def test_request_port(aresponses):
    """Test the Elgato Light running on non-standard port."""
    aresponses.add(
        "example.com:3333",
        "/elgato/test",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text='{"status": "ok"}',
        ),
    )

    async with aiohttp.ClientSession() as session:
        elgato = Elgato("example.com", port=3333, session=session)
        response = await elgato._request("test")
        assert response["status"] == "ok"


@pytest.mark.asyncio
async def test_timeout(aresponses):
    """Test request timeout from the Elgato Light."""
    # Faking a timeout by sleeping
    async def response_handler(_):
        """Response handler for this test."""
        await asyncio.sleep(2)
        return aresponses.Response(body="Goodmorning!")

    aresponses.add("example.com:9123", "/elgato/test", "GET", response_handler)

    async with aiohttp.ClientSession() as session:
        elgato = Elgato("example.com", session=session, request_timeout=1)
        with pytest.raises(ElgatoConnectionError):
            assert await elgato._request("test")


@pytest.mark.asyncio
async def test_http_error400(aresponses):
    """Test HTTP 404 response handling."""
    aresponses.add(
        "example.com:9123",
        "/elgato/test",
        "GET",
        aresponses.Response(text="OMG PUPPIES!", status=404),
    )

    async with aiohttp.ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        with pytest.raises(ElgatoError):
            assert await elgato._request("test")


@pytest.mark.asyncio
async def test_unexpected_response(aresponses):
    """Test unexpected response handling."""
    aresponses.add(
        "example.com:9123",
        "/elgato/test",
        "GET",
        aresponses.Response(text="OMG PUPPIES!", status=200),
    )

    async with aiohttp.ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        with pytest.raises(ElgatoError):
            assert await elgato._request("test")


@pytest.mark.asyncio
async def test_light_on(aresponses):
    """Test controlling a Elgato Light."""
    # Handle to run asserts on request in
    async def response_handler(request):
        """Response handler for this test."""
        data = await request.json()
        assert data == {
            "numberOfLights": 1,
            "lights": [{"brightness": 100, "temperature": 275, "on": 1}],
        }
        return aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text='{"status": "ok"}',
        )

    aresponses.add(
        "example.com:9123",
        "/elgato/lights",
        "PUT",
        response_handler,
    )

    async with aiohttp.ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        await elgato.light(on=True, brightness=100, temperature=275)


@pytest.mark.asyncio
async def test_light_off(aresponses):
    """Test turning off an Elgato Light."""
    # Handle to run asserts on request in
    async def response_handler(request):
        """Response handler for this test."""
        data = await request.json()
        assert data == {
            "numberOfLights": 1,
            "lights": [{"on": 0}],
        }
        return aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text='{"status": "ok"}',
        )

    aresponses.add(
        "example.com:9123",
        "/elgato/lights",
        "PUT",
        response_handler,
    )

    async with aiohttp.ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        await elgato.light(on=False)


@pytest.mark.asyncio
async def test_light_no_on_off(aresponses):
    """Test controlling an Elgato Light without turning it on/off."""
    # Handle to run asserts on request in
    async def response_handler(request):
        """Response handler for this test."""
        data = await request.json()
        assert data == {
            "numberOfLights": 1,
            "lights": [{"brightness": 50}],
        }
        return aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text='{"status": "ok"}',
        )

    aresponses.add(
        "example.com:9123",
        "/elgato/lights",
        "PUT",
        response_handler,
    )

    async with aiohttp.ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        await elgato.light(brightness=50)
