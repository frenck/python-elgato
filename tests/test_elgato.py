"""Tests for the Elgato Lights Library."""

# pylint: disable=protected-access

import pytest
from aiohttp import ClientSession
from aioresponses import aioresponses

from elgato import Elgato
from elgato.exceptions import ElgatoConnectionError, ElgatoError


async def test_json_request(responses: aioresponses) -> None:
    """Test JSON response is handled correctly."""
    responses.get(
        "http://example.com:9123/elgato/test",
        status=200,
        body='{"status": "ok"}',
        content_type="application/json",
    )
    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        response = await elgato._request("test")
        assert response == '{"status": "ok"}'
        await elgato.close()


async def test_internal_session(responses: aioresponses) -> None:
    """Test JSON response is handled correctly."""
    responses.get(
        "http://example.com:9123/elgato/test",
        status=200,
        body='{"status": "ok"}',
        content_type="application/json",
    )
    async with Elgato("example.com") as elgato:
        response = await elgato._request("test")
        assert response == '{"status": "ok"}'


async def test_put_request(responses: aioresponses) -> None:
    """Test PUT requests are handled correctly."""
    responses.put(
        "http://example.com:9123/elgato/test",
        status=200,
        body='{"status": "ok"}',
        content_type="application/json",
    )
    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        response = await elgato._request("test", method="PUT", data={})
        assert response == '{"status": "ok"}'


async def test_post_request(responses: aioresponses) -> None:
    """Test POST requests are handled correctly."""
    responses.post(
        "http://example.com:9123/elgato/test",
        status=200,
        body='{"status": "ok"}',
        content_type="application/json",
    )
    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        response = await elgato._request("test", method="POST", data={})
        assert response == '{"status": "ok"}'


async def test_request_port(responses: aioresponses) -> None:
    """Test the Elgato Light running on non-standard port."""
    responses.get(
        "http://example.com:3333/elgato/test",
        status=200,
        body='{"status": "ok"}',
        content_type="application/json",
    )
    async with ClientSession() as session:
        elgato = Elgato("example.com", port=3333, session=session)
        response = await elgato._request("test")
        assert response == '{"status": "ok"}'


async def test_timeout(responses: aioresponses) -> None:
    """Test request timeout from the Elgato Light."""
    responses.get(
        "http://example.com:9123/elgato/test",
        exception=TimeoutError(),
    )
    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session, request_timeout=1)
        with pytest.raises(ElgatoConnectionError):
            assert await elgato._request("test")


async def test_http_error400(responses: aioresponses) -> None:
    """Test HTTP 404 response handling."""
    responses.get(
        "http://example.com:9123/elgato/test",
        status=404,
        body="OMG PUPPIES!",
        content_type="text/plain",
    )
    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        with pytest.raises(ElgatoError):
            assert await elgato._request("test")


async def test_light_on(responses: aioresponses) -> None:
    """Test controlling an Elgato Light."""
    responses.put(
        "http://example.com:9123/elgato/lights",
        status=200,
        body='{"status": "ok"}',
        content_type="application/json",
    )
    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        await elgato.light(on=True, brightness=100, temperature=275)


async def test_light_off(responses: aioresponses) -> None:
    """Test turning off an Elgato Light."""
    responses.put(
        "http://example.com:9123/elgato/lights",
        status=200,
        body='{"status": "ok"}',
        content_type="application/json",
    )
    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        await elgato.light(on=False)


async def test_light_no_on_off(responses: aioresponses) -> None:
    """Test controlling an Elgato Light without turning it on/off."""
    responses.put(
        "http://example.com:9123/elgato/lights",
        status=200,
        body='{"status": "ok"}',
        content_type="application/json",
    )
    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        await elgato.light(brightness=50)
