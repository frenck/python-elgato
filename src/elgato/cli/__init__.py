"""Command-line interface for Elgato Lights."""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Annotated

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from zeroconf import ServiceStateChange, Zeroconf
from zeroconf.asyncio import (
    AsyncServiceBrowser,
    AsyncServiceInfo,
    AsyncZeroconf,
)

from elgato.elgato import Elgato
from elgato.exceptions import ElgatoConnectionError, ElgatoError

from .async_typer import AsyncTyper

cli = AsyncTyper(
    help="Control Elgato Light devices from the command line.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()

Host = Annotated[
    str,
    typer.Option(
        help="Hostname or IP address of the Elgato Light",
        prompt="Host",
        show_default=False,
        envvar="ELGATO_HOST",
    ),
]
Port = Annotated[
    int,
    typer.Option(
        help="Port of the Elgato Light API",
        envvar="ELGATO_PORT",
    ),
]
JsonFlag = Annotated[
    bool,
    typer.Option(
        "--json",
        help="Emit machine-readable JSON output",
    ),
]


@cli.error_handler(ElgatoConnectionError)
def connection_error_handler(_: ElgatoConnectionError) -> None:
    """Handle connection errors."""
    message = """
    Could not connect to the Elgato Light device. Please check the
    hostname/IP address and ensure the device is powered on and
    reachable on the network.
    """
    panel = Panel(
        message,
        expand=False,
        title="Connection error",
        border_style="red bold",
    )
    console.print(panel)
    sys.exit(1)


@cli.error_handler(ElgatoError)
def elgato_error_handler(err: ElgatoError) -> None:
    """Handle generic Elgato errors."""
    panel = Panel(
        str(err),
        expand=False,
        title="Elgato error",
        border_style="red bold",
    )
    console.print(panel)
    sys.exit(1)


def emit_json(payload: object) -> None:
    """Emit a payload as indented JSON on stdout."""
    typer.echo(json.dumps(payload, indent=2))


@cli.command("info")
async def info(
    host: Host,
    port: Port = 9123,
    output_json: JsonFlag = False,
) -> None:
    """Show device information."""
    async with Elgato(host, port=port) as elgato:
        device_info = await elgato.info()

    if output_json:
        emit_json(
            {
                "product_name": device_info.product_name,
                "serial_number": device_info.serial_number,
                "display_name": device_info.display_name,
                "firmware_version": device_info.firmware_version,
                "firmware_build_number": device_info.firmware_build_number,
                "hardware_board_type": device_info.hardware_board_type,
                "mac_address": device_info.mac_address,
                "features": device_info.features,
            }
        )
        return

    table = Table(title=f"Elgato Light — {device_info.display_name}")
    table.add_column("Property", style="cyan bold")
    table.add_column("Value")
    table.add_row("Product", device_info.product_name)
    table.add_row("Serial number", device_info.serial_number)
    table.add_row("Display name", device_info.display_name)
    firmware = (
        f"{device_info.firmware_version} (build {device_info.firmware_build_number})"
    )
    table.add_row("Firmware", firmware)
    table.add_row("Hardware board", str(device_info.hardware_board_type))
    if device_info.mac_address:
        table.add_row("MAC address", device_info.mac_address)
    if device_info.wifi:
        table.add_row("Wi-Fi SSID", device_info.wifi.ssid)
        table.add_row("Wi-Fi RSSI", f"{device_info.wifi.rssi} dBm")
        table.add_row("Wi-Fi frequency", f"{device_info.wifi.frequency} MHz")
    console.print(table)


@cli.command("state")
async def state(
    host: Host,
    port: Port = 9123,
    output_json: JsonFlag = False,
) -> None:
    """Show the current light state."""
    async with Elgato(host, port=port) as elgato:
        light_state = await elgato.state()

    if output_json:
        payload: dict[str, object] = {
            "on": light_state.on,
            "brightness": light_state.brightness,
        }
        if light_state.temperature is not None:
            payload["temperature"] = light_state.temperature
        if light_state.hue is not None:
            payload["hue"] = light_state.hue
        if light_state.saturation is not None:
            payload["saturation"] = light_state.saturation
        emit_json(payload)
        return

    status = (
        "[green bold]on[/green bold]" if light_state.on else "[red bold]off[/red bold]"
    )
    table = Table(title="Light State")
    table.add_column("Property", style="cyan bold")
    table.add_column("Value")
    table.add_row("Power", status)
    table.add_row("Brightness", f"{light_state.brightness}%")
    if light_state.temperature is not None:
        table.add_row("Temperature", f"{light_state.temperature} mired")
    if light_state.hue is not None:
        table.add_row("Hue", f"{light_state.hue}°")
    if light_state.saturation is not None:
        table.add_row("Saturation", f"{light_state.saturation}%")
    console.print(table)


@cli.command("on")
async def turn_on(
    host: Host,
    port: Port = 9123,
    brightness: Annotated[
        int | None,
        typer.Option("--brightness", "-b", help="Brightness (0-100)", min=0, max=100),
    ] = None,
    temperature: Annotated[
        int | None,
        typer.Option(
            "--temperature",
            "-t",
            help="Color temperature in mired (143-344)",
            min=143,
            max=344,
        ),
    ] = None,
) -> None:
    """Turn on the light, optionally setting brightness and temperature."""
    async with Elgato(host, port=port) as elgato:
        await elgato.light(
            on=True,
            brightness=brightness,
            temperature=temperature,
        )
    console.print("[green]Light turned on.[/green]")


@cli.command("off")
async def turn_off(
    host: Host,
    port: Port = 9123,
) -> None:
    """Turn off the light."""
    async with Elgato(host, port=port) as elgato:
        await elgato.light(on=False)
    console.print("[yellow]Light turned off.[/yellow]")


@cli.command("identify")
async def identify(
    host: Host,
    port: Port = 9123,
) -> None:
    """Identify the light by making it blink."""
    async with Elgato(host, port=port) as elgato:
        await elgato.identify()
    console.print("[cyan]Light is blinking to identify itself.[/cyan]")


@cli.command("restart")
async def restart(
    host: Host,
    port: Port = 9123,
) -> None:
    """Restart the light device."""
    async with Elgato(host, port=port) as elgato:
        await elgato.restart()
    console.print("[yellow]Device is restarting.[/yellow]")


@cli.command("scan")
async def scan(
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress status messages"),
    ] = False,
) -> None:
    """Scan the network for Elgato Light devices.

    Uses mDNS/Zeroconf to discover Elgato devices advertising the
    _elg._tcp service. Press Ctrl-C to stop scanning.
    """
    zeroconf = AsyncZeroconf()
    background_tasks: set[asyncio.Future[None]] = set()
    seen: set[str] = set()

    table = Table(
        title="\n\nFound Elgato Lights",
        header_style="cyan bold",
        show_lines=True,
    )
    table.add_column("Host")
    table.add_column("Addresses")
    table.add_column("Port")
    table.add_column("Model")

    def on_service_state_change(
        zeroconf: Zeroconf,
        service_type: str,
        name: str,
        state_change: ServiceStateChange,
    ) -> None:
        """Handle service state changes."""
        if state_change is not ServiceStateChange.Added:
            return
        future = asyncio.ensure_future(
            display_service_info(zeroconf, service_type, name),
        )
        background_tasks.add(future)
        future.add_done_callback(background_tasks.discard)

    async def display_service_info(
        zc: Zeroconf,
        service_type: str,
        name: str,
    ) -> None:
        """Retrieve and display service info."""
        service_info = AsyncServiceInfo(service_type, name)
        if not await service_info.async_request(zc, 3000):
            return

        hostname = str(service_info.server or "").rstrip(".")
        if not hostname or hostname in seen:
            return
        seen.add(hostname)

        props = service_info.properties or {}
        model = (props.get(b"md") or b"").decode()
        addresses = ", ".join(service_info.parsed_scoped_addresses())
        port = str(service_info.port or 9123)

        if not quiet:
            console.print(
                f"[cyan bold]Found: {hostname} ({model})[/cyan bold]",
            )

        table.add_row(hostname, addresses, port, model or "N/A")

    if not quiet:
        console.print("[green]Scanning for Elgato Lights...[/green]")
        console.print("[red]Press Ctrl-C to stop\n[/red]")

    with Live(table, console=console, refresh_per_second=4):
        browser = AsyncServiceBrowser(
            zeroconf.zeroconf,
            ["_elg._tcp.local."],
            handlers=[on_service_state_change],
        )
        try:
            while True:  # noqa: ASYNC110
                await asyncio.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            if not quiet:
                console.print(
                    "\n[green]Scan stopped.[/green]",
                )
            await browser.async_cancel()
            await asyncio.gather(*background_tasks, return_exceptions=True)
            await zeroconf.async_close()
