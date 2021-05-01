# pylint: disable=W0621
"""Asynchronous Python client for Elgato Lights."""

import asyncio

from elgato import Elgato, Info, Settings, State


async def main():
    """Show example on controlling your Elgato Key device."""
    async with Elgato("elgato-key-light.local") as elgato:
        info: Info = await elgato.info()
        print(info)

        settings: Settings = await elgato.settings()
        print(settings)

        state: State = await elgato.state()
        print(state)

        # Toggle the light
        await elgato.light(on=(not state.on))


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
