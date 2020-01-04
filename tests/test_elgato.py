"""Tests for the Elgato Key Lights Library."""
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
        response = await elgato._request("test", data={})
        assert response["status"] == "ok"


@pytest.mark.asyncio
async def test_request_port(aresponses):
    """Test the Elgato Key Light running on non-standard port."""
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
    """Test request timeout from the Elgato Key Light."""
    # Faking a timeout by sleeping
    async def response_handler(_):
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
