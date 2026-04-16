"""Tests for retrieving battery information from the Elgato Key Light device."""

import pytest
from aiohttp import ClientSession
from aioresponses import aioresponses

from elgato import BatteryInfo, BatteryStatus, Elgato, ElgatoNoBatteryError, PowerSource

from .conftest import load_fixture


async def test_battery_info_no_battery(responses: aioresponses) -> None:
    """Test getting battery information from an Elgato device without battery."""
    responses.get(
        "http://example.com:9123/elgato/lights/settings",
        status=200,
        body=load_fixture("settings-keylight.json"),
        content_type="application/json",
    )
    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        assert await elgato.has_battery() is False
        with pytest.raises(
            ElgatoNoBatteryError,
            match=r"The Elgato light does not have a battery\.",
        ):
            await elgato.battery()


async def test_battery_info(responses: aioresponses) -> None:
    """Test getting battery information from Elgato Key Light Mini device."""
    responses.get(
        "http://example.com:9123/elgato/lights/settings",
        status=200,
        body=load_fixture("settings-key-light-mini.json"),
        content_type="application/json",
    )
    responses.get(
        "http://example.com:9123/elgato/battery-info",
        status=200,
        body=load_fixture("battery-info.json"),
        content_type="application/json",
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


async def test_battery_bypass_no_battery(responses: aioresponses) -> None:
    """Test enabling battery bypass on an Elgato device without battery."""
    responses.get(
        "http://example.com:9123/elgato/lights/settings",
        status=200,
        body=load_fixture("settings-keylight.json"),
        content_type="application/json",
    )
    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        assert await elgato.has_battery() is False
        with pytest.raises(
            ElgatoNoBatteryError,
            match=r"The Elgato light does not have a battery\.",
        ):
            await elgato.battery_bypass(on=True)


async def test_battery_bypass(responses: aioresponses) -> None:
    """Test changing battery bypass / studio mode."""
    responses.get(
        "http://example.com:9123/elgato/lights/settings",
        status=200,
        body=load_fixture("settings-key-light-mini.json"),
        content_type="application/json",
    )
    responses.put(
        "http://example.com:9123/elgato/lights/settings",
        status=200,
        body="{}",
        content_type="application/json",
    )
    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        await elgato.battery_bypass(on=True)
