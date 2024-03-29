"""Tests for retrieving battery information from the Elgato Key Light device."""

import pytest
from aiohttp import ClientResponse, ClientSession
from aresponses import Response, ResponsesMockServer

from elgato import BatteryInfo, BatteryStatus, Elgato, ElgatoNoBatteryError, PowerSource

from . import load_fixture


async def test_battery_info_no_battery(aresponses: ResponsesMockServer) -> None:
    """Test getting battery information from a Elgato device without battery."""
    aresponses.add(
        "example.com:9123",
        "/elgato/lights/settings",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("settings-keylight.json"),
        ),
    )
    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        assert await elgato.has_battery() is False
        with pytest.raises(
            ElgatoNoBatteryError,
            match="The Elgato light does not have a battery.",
        ):
            await elgato.battery()


async def test_battery_info(aresponses: ResponsesMockServer) -> None:
    """Test getting battery information from Elgato Key Light Mini device."""
    aresponses.add(
        "example.com:9123",
        "/elgato/lights/settings",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("settings-key-light-mini.json"),
        ),
    )
    aresponses.add(
        "example.com:9123",
        "/elgato/battery-info",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("battery-info.json"),
        ),
    )
    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        battery: BatteryInfo = await elgato.battery()
        assert battery
        assert battery.charge_current == 3.01
        assert battery.charge_power == 12.66
        assert battery.charge_voltage == 4.21
        assert battery.input_charge_current == 3008
        assert battery.input_charge_power == 12658
        assert battery.input_charge_voltage == 4208
        assert battery.level == 78.57
        assert battery.power_source == PowerSource.MAINS
        assert battery.status == BatteryStatus.CHARGING


async def test_battery_bypass_no_battery(aresponses: ResponsesMockServer) -> None:
    """Test enabling battery bypass on a Elgato device without battery."""
    aresponses.add(
        "example.com:9123",
        "/elgato/lights/settings",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("settings-keylight.json"),
        ),
    )
    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        assert await elgato.has_battery() is False
        with pytest.raises(
            ElgatoNoBatteryError,
            match="The Elgato light does not have a battery.",
        ):
            await elgato.battery_bypass(on=True)


async def test_battery_bypass(aresponses: ResponsesMockServer) -> None:
    """Test changing battery bypass / studio mode."""
    aresponses.add(
        "example.com:9123",
        "/elgato/lights/settings",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("settings-key-light-mini.json"),
        ),
    )

    async def response_handler(request: ClientResponse) -> Response:
        """Response handler for this test."""
        data = await request.json()
        assert data == {"battery": {"bypass": 1}}
        return aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text="{}",
        )

    aresponses.add(
        "example.com:9123",
        "/elgato/lights/settings",
        "PUT",
        response_handler,
    )

    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        await elgato.battery_bypass(on=True)
