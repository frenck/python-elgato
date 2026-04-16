"""Tests for retrieving information from the Elgato Light device."""

import pytest
from aiohttp import ClientSession
from aioresponses import aioresponses

from elgato import Elgato, ElgatoNoBatteryError, PowerOnBehavior, Settings

from .conftest import load_fixture


async def test_settings_keylight(responses: aioresponses) -> None:
    """Test getting Elgato Light device settings."""
    responses.get(
        "http://example.com:9123/elgato/lights/settings",
        status=200,
        body=load_fixture("settings-keylight.json"),
        content_type="application/json",
    )
    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        settings: Settings = await elgato.settings()
        assert settings
        assert settings.color_change_duration == 100
        assert settings.power_on_behavior == 1
        assert settings.power_on_brightness == 20
        assert settings.power_on_hue is None
        assert settings.power_on_saturation is None
        assert settings.power_on_temperature == 213
        assert settings.switch_off_duration == 300
        assert settings.switch_on_duration == 100
        assert settings.battery is None


async def test_settings_led_strip(responses: aioresponses) -> None:
    """Test getting Elgato Led Strip device settings."""
    responses.get(
        "http://example.com:9123/elgato/lights/settings",
        status=200,
        body=load_fixture("settings-strip.json"),
        content_type="application/json",
    )
    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        settings: Settings = await elgato.settings()
        assert settings
        assert settings.color_change_duration == 150
        assert settings.power_on_behavior == 2
        assert settings.power_on_brightness == 40
        assert settings.power_on_hue == 40.0
        assert settings.power_on_saturation == 15.0
        assert settings.power_on_temperature == 0
        assert settings.switch_off_duration == 400
        assert settings.switch_on_duration == 150
        assert settings.battery is None


async def test_settings_key_light_mini(responses: aioresponses) -> None:
    """Test getting Elgato Light Mini device settings.

    This device has a battery
    """
    responses.get(
        "http://example.com:9123/elgato/lights/settings",
        status=200,
        body=load_fixture("settings-key-light-mini.json"),
        content_type="application/json",
    )
    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        settings: Settings = await elgato.settings()
        assert settings
        assert settings.battery
        assert settings.battery.bypass is False
        assert settings.battery.energy_saving.disable_wifi is False
        assert settings.battery.energy_saving.enabled is False
        assert settings.battery.energy_saving.minimum_battery_level == 15
        assert settings.battery.energy_saving.adjust_brightness.brightness == 10
        assert settings.battery.energy_saving.adjust_brightness.enabled is False
        assert settings.color_change_duration == 100
        assert settings.power_on_behavior == 1
        assert settings.power_on_brightness == 20
        assert settings.power_on_hue is None
        assert settings.power_on_saturation is None
        assert settings.power_on_temperature == 230
        assert settings.switch_off_duration == 300
        assert settings.switch_on_duration == 100


async def test_battery_settings_keylight(responses: aioresponses) -> None:
    """Test getting Elgato Light battery settings."""
    responses.get(
        "http://example.com:9123/elgato/lights/settings",
        status=200,
        body=load_fixture("settings-keylight.json"),
        content_type="application/json",
    )
    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        with pytest.raises(ElgatoNoBatteryError):
            await elgato.battery_settings()


async def test_battery_settings_key_light_mini(responses: aioresponses) -> None:
    """Test getting Elgato Light Mini device battery settings.

    This device has a battery
    """
    responses.get(
        "http://example.com:9123/elgato/lights/settings",
        status=200,
        body=load_fixture("settings-key-light-mini.json"),
        content_type="application/json",
    )
    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        settings = await elgato.battery_settings()
        assert settings
        assert settings
        assert settings.bypass is False
        assert settings.energy_saving.disable_wifi is False
        assert settings.energy_saving.enabled is False
        assert settings.energy_saving.minimum_battery_level == 15
        assert settings.energy_saving.adjust_brightness.brightness == 10
        assert settings.energy_saving.adjust_brightness.enabled is False


async def test_energy_savings_no_battery(responses: aioresponses) -> None:
    """Test adjusting energy saving settings on an Elgato device without battery."""
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
            await elgato.energy_saving(on=True)


async def test_energy_savings_full(responses: aioresponses) -> None:
    """Test changing energy saving settings."""
    responses.get(
        "http://example.com:9123/elgato/lights/settings",
        status=200,
        body=load_fixture("settings-key-light-mini.json"),
        content_type="application/json",
        repeat=True,
    )
    responses.put(
        "http://example.com:9123/elgato/lights/settings",
        status=200,
        body="{}",
        content_type="application/json",
    )
    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        await elgato.energy_saving(
            adjust_brightness=True,
            brightness=42,
            disable_wifi=True,
            minimum_battery_level=21,
            on=True,
        )


async def test_energy_savings_no_changes(responses: aioresponses) -> None:
    """Test changing energy saving settings."""
    responses.get(
        "http://example.com:9123/elgato/lights/settings",
        status=200,
        body=load_fixture("settings-key-light-mini.json"),
        content_type="application/json",
        repeat=True,
    )
    responses.put(
        "http://example.com:9123/elgato/lights/settings",
        status=200,
        body="{}",
        content_type="application/json",
    )
    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        await elgato.energy_saving()


async def test_power_on_behavior_full(responses: aioresponses) -> None:
    """Test changing power on behavior settings."""
    responses.get(
        "http://example.com:9123/elgato/lights/settings",
        status=200,
        body=load_fixture("settings-keylight.json"),
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
        await elgato.power_on_behavior(
            behavior=PowerOnBehavior.USE_DEFAULTS,
            brightness=42,
            hue=21.0,
            temperature=242,
        )


async def test_power_on_behavior_no_changes(responses: aioresponses) -> None:
    """Test changing power on behavior settings."""
    responses.get(
        "http://example.com:9123/elgato/lights/settings",
        status=200,
        body=load_fixture("settings-key-light-mini.json"),
        content_type="application/json",
        repeat=True,
    )
    responses.put(
        "http://example.com:9123/elgato/lights/settings",
        status=200,
        body="{}",
        content_type="application/json",
    )
    async with ClientSession() as session:
        elgato = Elgato("example.com", session=session)
        await elgato.power_on_behavior()
