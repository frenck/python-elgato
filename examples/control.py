# pylint: disable=W0621
"""Asynchronous Python client for Elgato Lights."""

import asyncio

from elgato import Elgato, State


async def main() -> None:
    """Show example on controlling your Elgato Key device."""
    async with Elgato("elgato-key-light.local") as elgato:
        await elgato.info()

        await elgato.settings()

        state: State = await elgato.state()

        # Toggle the light
        await elgato.light(on=(not state.on))


if __name__ == "__main__":
    asyncio.run(main())
