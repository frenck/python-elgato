"""Tests for the Elgato CLI."""

# pylint: disable=redefined-outer-name
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import click
import pytest
from typer.main import get_command
from typer.testing import CliRunner
from zeroconf import ServiceStateChange

from elgato.cli import cli
from elgato.exceptions import ElgatoConnectionError, ElgatoError

if TYPE_CHECKING:
    from syrupy.assertion import SnapshotAssertion


@pytest.fixture(autouse=True)
def stable_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force deterministic Rich rendering for stable snapshots."""
    monkeypatch.setenv("COLUMNS", "100")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("TERM", "dumb")


@pytest.fixture
def runner() -> CliRunner:
    """Return a CLI runner for invoking the Typer app."""
    return CliRunner()


def mock_elgato_class(
    *,
    info_data: dict | None = None,
    state_data: dict | None = None,
) -> MagicMock:
    """Return a MagicMock that stands in for the Elgato class."""
    client = AsyncMock()

    if info_data is not None:
        mock_info = MagicMock()
        for key, value in info_data.items():
            setattr(mock_info, key, value)
        client.info.return_value = mock_info

    if state_data is not None:
        mock_state = MagicMock()
        for key, value in state_data.items():
            setattr(mock_state, key, value)
        client.state.return_value = mock_state

    instance = AsyncMock()
    instance.__aenter__.return_value = client
    instance.__aexit__.return_value = None

    return MagicMock(return_value=instance)


@pytest.fixture
def key_light_info() -> dict:
    """Return sample Key Light device info."""
    wifi = MagicMock()
    wifi.ssid = "Frenck-IoT"
    wifi.rssi = -48
    wifi.frequency = 2400
    return {
        "product_name": "Elgato Key Light",
        "serial_number": "CN11A1A00001",
        "display_name": "Frenck",
        "firmware_version": "1.0.3",
        "firmware_build_number": 218,
        "hardware_board_type": 53,
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "features": ["lights"],
        "wifi": wifi,
    }


@pytest.fixture
def light_state_on() -> dict:
    """Return sample light state (on, temperature mode)."""
    return {
        "on": True,
        "brightness": 80,
        "temperature": 230,
        "hue": None,
        "saturation": None,
    }


@pytest.fixture
def light_state_off() -> dict:
    """Return sample light state (off)."""
    return {
        "on": False,
        "brightness": 0,
        "temperature": 200,
        "hue": None,
        "saturation": None,
    }


def test_cli_structure(snapshot: SnapshotAssertion) -> None:
    """The CLI exposes the expected commands and options."""
    group = get_command(cli)
    assert isinstance(group, click.Group)
    structure = {
        name: sorted(param.name for param in subcommand.params)
        for name, subcommand in sorted(group.commands.items())
    }
    assert structure == snapshot


def test_info(
    runner: CliRunner,
    key_light_info: dict,
    snapshot: SnapshotAssertion,
) -> None:
    """Info command prints a device information table."""
    mock_cls = mock_elgato_class(info_data=key_light_info)
    with patch("elgato.cli.Elgato", mock_cls):
        result = runner.invoke(cli, ["info", "--host", "example.com"])
    assert result.exit_code == 0
    assert result.stdout == snapshot


def test_info_json(
    runner: CliRunner,
    key_light_info: dict,
    snapshot: SnapshotAssertion,
) -> None:
    """Info command emits JSON when --json is given."""
    mock_cls = mock_elgato_class(info_data=key_light_info)
    with patch("elgato.cli.Elgato", mock_cls):
        result = runner.invoke(cli, ["info", "--host", "example.com", "--json"])
    assert result.exit_code == 0
    assert result.stdout == snapshot


def test_state_on(
    runner: CliRunner,
    light_state_on: dict,
    snapshot: SnapshotAssertion,
) -> None:
    """State command prints a table when the light is on."""
    mock_cls = mock_elgato_class(state_data=light_state_on)
    with patch("elgato.cli.Elgato", mock_cls):
        result = runner.invoke(cli, ["state", "--host", "example.com"])
    assert result.exit_code == 0
    assert result.stdout == snapshot


def test_state_off(
    runner: CliRunner,
    light_state_off: dict,
    snapshot: SnapshotAssertion,
) -> None:
    """State command prints a table when the light is off."""
    mock_cls = mock_elgato_class(state_data=light_state_off)
    with patch("elgato.cli.Elgato", mock_cls):
        result = runner.invoke(cli, ["state", "--host", "example.com"])
    assert result.exit_code == 0
    assert result.stdout == snapshot


def test_state_json(
    runner: CliRunner,
    light_state_on: dict,
    snapshot: SnapshotAssertion,
) -> None:
    """State command emits JSON when --json is given."""
    mock_cls = mock_elgato_class(state_data=light_state_on)
    with patch("elgato.cli.Elgato", mock_cls):
        result = runner.invoke(cli, ["state", "--host", "example.com", "--json"])
    assert result.exit_code == 0
    assert result.stdout == snapshot


def test_on(runner: CliRunner) -> None:
    """On command turns the light on."""
    mock_cls = mock_elgato_class()
    with patch("elgato.cli.Elgato", mock_cls):
        result = runner.invoke(cli, ["on", "--host", "example.com"])
    assert result.exit_code == 0
    assert "Light turned on." in result.stdout
    client = mock_cls.return_value.__aenter__.return_value
    client.light.assert_called_once_with(on=True, brightness=None, temperature=None)


def test_on_with_options(runner: CliRunner) -> None:
    """On command passes brightness and temperature."""
    mock_cls = mock_elgato_class()
    with patch("elgato.cli.Elgato", mock_cls):
        result = runner.invoke(
            cli,
            [
                "on",
                "--host",
                "example.com",
                "--brightness",
                "80",
                "--temperature",
                "200",
            ],
        )
    assert result.exit_code == 0
    client = mock_cls.return_value.__aenter__.return_value
    client.light.assert_called_once_with(on=True, brightness=80, temperature=200)


def test_off(runner: CliRunner) -> None:
    """Off command turns the light off."""
    mock_cls = mock_elgato_class()
    with patch("elgato.cli.Elgato", mock_cls):
        result = runner.invoke(cli, ["off", "--host", "example.com"])
    assert result.exit_code == 0
    assert "Light turned off." in result.stdout
    client = mock_cls.return_value.__aenter__.return_value
    client.light.assert_called_once_with(on=False)


def test_identify(runner: CliRunner) -> None:
    """Identify command calls identify on the device."""
    mock_cls = mock_elgato_class()
    with patch("elgato.cli.Elgato", mock_cls):
        result = runner.invoke(cli, ["identify", "--host", "example.com"])
    assert result.exit_code == 0
    assert "blinking" in result.stdout
    client = mock_cls.return_value.__aenter__.return_value
    client.identify.assert_called_once()


def test_restart(runner: CliRunner) -> None:
    """Restart command calls restart on the device."""
    mock_cls = mock_elgato_class()
    with patch("elgato.cli.Elgato", mock_cls):
        result = runner.invoke(cli, ["restart", "--host", "example.com"])
    assert result.exit_code == 0
    assert "restarting" in result.stdout
    client = mock_cls.return_value.__aenter__.return_value
    client.restart.assert_called_once()


def _make_service_info(
    *,
    server: str = "elgato-key-light-1234.local.",
    addresses: list[str] | None = None,
    port: int = 9123,
    properties: dict[bytes, bytes] | None = None,
) -> MagicMock:
    """Create a mock AsyncServiceInfo."""
    info = MagicMock()
    info.server = server
    info.port = port
    info.parsed_scoped_addresses.return_value = addresses or ["192.168.1.100"]
    info.properties = properties or {b"md": b"Elgato Key Light"}
    info.async_request = AsyncMock(return_value=True)
    return info


def _mock_zeroconf() -> tuple[MagicMock, MagicMock]:
    """Create mock AsyncZeroconf and browser instances."""
    mock_zc = MagicMock()
    mock_zc.zeroconf = MagicMock()
    mock_zc.async_close = AsyncMock()
    mock_browser = MagicMock(async_cancel=AsyncMock())
    return mock_zc, mock_browser


def test_scan(runner: CliRunner) -> None:
    """Scan command discovers and displays Elgato devices."""
    service_info = _make_service_info()
    mock_zc, mock_browser = _mock_zeroconf()

    original_sleep = asyncio.sleep

    async def interrupt_sleep(seconds: float) -> None:
        """Let short sleeps pass, interrupt the scan loop."""
        if seconds >= 0.5:
            raise KeyboardInterrupt
        await original_sleep(seconds)

    def create_browser(_zc: MagicMock, _types: list[str], handlers: list) -> MagicMock:
        handlers[0](
            zeroconf=_zc,
            service_type="_elg._tcp.local.",
            name="Elgato Key Light._elg._tcp.local.",
            state_change=ServiceStateChange.Added,
        )
        return mock_browser

    with (
        patch("elgato.cli.AsyncZeroconf", return_value=mock_zc),
        patch("elgato.cli.AsyncServiceBrowser", side_effect=create_browser),
        patch("elgato.cli.AsyncServiceInfo", return_value=service_info),
        patch("asyncio.sleep", side_effect=interrupt_sleep),
    ):
        result = runner.invoke(cli, ["scan", "--quiet"])

    assert result.exit_code == 0


def test_scan_ignores_non_added_states(runner: CliRunner) -> None:
    """Scan command ignores service state changes that are not Added."""
    mock_zc, mock_browser = _mock_zeroconf()

    original_sleep = asyncio.sleep

    async def interrupt_sleep(seconds: float) -> None:
        """Interrupt the scan loop immediately."""
        if seconds >= 0.5:
            raise KeyboardInterrupt
        await original_sleep(seconds)

    def create_browser(_zc: MagicMock, _types: list[str], handlers: list) -> MagicMock:
        handlers[0](
            zeroconf=_zc,
            service_type="_elg._tcp.local.",
            name="test._elg._tcp.local.",
            state_change=ServiceStateChange.Removed,
        )
        return mock_browser

    with (
        patch("elgato.cli.AsyncZeroconf", return_value=mock_zc),
        patch("elgato.cli.AsyncServiceBrowser", side_effect=create_browser),
        patch("asyncio.sleep", side_effect=interrupt_sleep),
    ):
        result = runner.invoke(cli, ["scan", "--quiet"])

    assert result.exit_code == 0


def test_connection_error_handler(
    capsys: pytest.CaptureFixture[str],
    snapshot: SnapshotAssertion,
) -> None:
    """Connection error handler prints a panel and exits with 1."""
    handler = cli.error_handlers[ElgatoConnectionError]
    with pytest.raises(SystemExit) as exc_info:
        handler(ElgatoConnectionError("unreachable"))
    assert exc_info.value.code == 1
    assert capsys.readouterr().out == snapshot


def test_elgato_error_handler(
    capsys: pytest.CaptureFixture[str],
    snapshot: SnapshotAssertion,
) -> None:
    """Generic error handler prints a panel and exits with 1."""
    handler = cli.error_handlers[ElgatoError]
    with pytest.raises(SystemExit) as exc_info:
        handler(ElgatoError("something went wrong"))
    assert exc_info.value.code == 1
    assert capsys.readouterr().out == snapshot
