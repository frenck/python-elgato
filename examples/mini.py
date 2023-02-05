# pylint: disable=W0621
"""Asynchronous Python client for Elgato Lights."""

import asyncio

from elgato import Elgato


async def main() -> None:
    """Show example on how to work with an battery powered device."""
    async with Elgato("10.10.11.172") as elgato:
        # General device information
        print(await elgato.info())
        print(await elgato.settings())
        print(state := await elgato.state())

        # General battery information
        battery = await elgato.battery()
        print(f"Level: {battery.level} %")
        print(f"Power: {battery.charge_power}W")
        print(f"Voltage: {battery.charge_voltage}V")
        print(f"Current: {battery.charge_current}A")

        # Toggle the light
        await elgato.light(on=(not state.on))


if __name__ == "__main__":
    asyncio.run(main())
