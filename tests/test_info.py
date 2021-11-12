"""Tests for retrieving information from the Elgato Key Light device."""
import aiohttp
import pytest

from elgato import Elgato, Info

from . import load_fixture


@pytest.mark.asyncio
async def test_info(aresponses):
    """Test getting Elgato Light device information."""
    aresponses.add(
        "example.com:9123",
        "/elgato/accessory-info",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("info-key-light.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        info: Info = await elgato.info()
        assert info
        assert info.display_name == "Frenck"
        assert info.features == ["lights"]
        assert info.firmware_build_number == 192
        assert info.firmware_version == "1.0.3"
        assert info.hardware_board_type == 53
        assert info.product_name == "Elgato Key Light"
        assert info.serial_number == "CN11A1A00001"


@pytest.mark.asyncio
async def test_change_display_name(aresponses):
    """Test changing the display name of an Elgato Light."""

    async def response_handler(request):
        """Response handler for this test."""
        data = await request.json()
        assert data == {"displayName": "OMG PUPPIES"}
        return aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text="",
        )

    aresponses.add(
        "example.com:9123", "/elgato/accessory-info", "PUT", response_handler
    )

    async with aiohttp.ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        await elgato.display_name("OMG PUPPIES")


@pytest.mark.asyncio
async def test_missing_display_name(aresponses):
    """Test ensure we can handle a missing display name."""
    aresponses.add(
        "example.com:9123",
        "/elgato/accessory-info",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("info-light-strip.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        info: Info = await elgato.info()
        assert info
        assert info.display_name == "Elgato Light"
