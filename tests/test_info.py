"""Tests for retrieving information from the Elgato Key Light device."""

from aiohttp import ClientResponse, ClientSession
from aresponses import Response, ResponsesMockServer

from elgato import Elgato, Info

from . import load_fixture


async def test_info_key_light(aresponses: ResponsesMockServer) -> None:
    """Test getting Elgato Key Light device information."""
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
    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        info: Info = await elgato.info()
        assert info
        assert info.display_name == "Frenck"
        assert info.features == ["lights"]
        assert info.firmware_build_number == 218
        assert info.firmware_version == "1.0.3"
        assert info.hardware_board_type == 53
        assert info.mac_address == "AA:BB:CC:DD:EE:FF"
        assert info.product_name == "Elgato Key Light"
        assert info.serial_number == "CN11A1A00001"
        assert info.wifi
        assert info.wifi.frequency == 2400
        assert info.wifi.rssi == -48
        assert info.wifi.ssid == "Frenck-IoT"


async def test_info_key_light_air(aresponses: ResponsesMockServer) -> None:
    """Test getting Elgato Key Light Air device information."""
    aresponses.add(
        "example.com:9123",
        "/elgato/accessory-info",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("info-key-light-air.json"),
        ),
    )
    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        info: Info = await elgato.info()
        assert info
        assert not info.display_name
        assert info.features == ["lights"]
        assert info.firmware_build_number == 195
        assert info.firmware_version == "1.0.3"
        assert info.hardware_board_type == 200
        assert info.mac_address is None
        assert info.product_name == "Elgato Key Light Air"
        assert info.serial_number == "CW44J2A03032"
        assert info.wifi is None


async def test_info_light_strip(aresponses: ResponsesMockServer) -> None:
    """Test getting Elgato Light Strip device information."""
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
    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        info: Info = await elgato.info()
        assert info
        assert info.display_name == "Elgato Light"
        assert info.features == ["lights"]
        assert info.firmware_build_number == 211
        assert info.firmware_version == "1.0.4"
        assert info.hardware_board_type == 70
        assert info.mac_address is None
        assert info.product_name == "Elgato Light Strip"
        assert info.serial_number == "EW52J1A00082"
        assert info.wifi is None


async def test_change_display_name(aresponses: ResponsesMockServer) -> None:
    """Test changing the display name of an Elgato Light."""

    async def response_handler(request: ClientResponse) -> Response:
        """Response handler for this test."""
        data = await request.json()
        assert data == {"displayName": "OMG PUPPIES"}
        return aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text="",
        )

    aresponses.add(
        "example.com:9123",
        "/elgato/accessory-info",
        "PUT",
        response_handler,
    )

    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        await elgato.display_name("OMG PUPPIES")


async def test_missing_display_name(aresponses: ResponsesMockServer) -> None:
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
    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        info: Info = await elgato.info()
        assert info
        assert info.display_name == "Elgato Light"
