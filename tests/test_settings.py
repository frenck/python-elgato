"""Tests for retrieving information from the Elgato Light device."""

from aiohttp import ClientSession
from aresponses import ResponsesMockServer

from elgato import Elgato, Settings

from . import load_fixture


async def test_settings_keylight(aresponses: ResponsesMockServer) -> None:
    """Test getting Elgato Light device settings."""
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


async def test_settings_led_strip(aresponses: ResponsesMockServer) -> None:
    """Test getting Elgato Led Strip device settings."""
    aresponses.add(
        "example.com:9123",
        "/elgato/lights/settings",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("settings-strip.json"),
        ),
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


async def test_settings_key_light_mini(aresponses: ResponsesMockServer) -> None:
    """Test getting Elgato Light Mini device settings.

    This device has a battery
    """
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
