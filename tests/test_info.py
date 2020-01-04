"""Tests for retreiving information from the Elgato Key Light device."""
import aiohttp
import pytest
from elgato import Elgato, Info

from . import load_fixture


@pytest.mark.asyncio
async def test_info(aresponses):
    """Test getting Elgato Key Light device information."""
    aresponses.add(
        "example.com:9123",
        "/elgato/accessory-info",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("info.json"),
        ),
    )
    async with aiohttp.ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        info: Info = await elgato.info()
        assert info
        assert info.display_name == "Frenck"
        assert info.firmware_build_number == 192
        assert info.firmware_version == "1.0.3"
        assert info.hardware_board_type == 53
        assert info.product_name == "Elgato Key Light"
        assert info.serial_number == "CN11A1A00001"
