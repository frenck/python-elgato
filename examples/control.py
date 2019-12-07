# pylint: disable=W0621
"""Asynchronous Python client for Elgato Key Lights."""

import asyncio

from elgato import Elgato, Info, State


async def main(loop):
    """Show example on controlling your Elgato Key Light device."""
    async with Elgato("elgato-key-light.local", loop=loop) as elgato:
        info: Info = await elgato.info()
        print(info)

        state: State = await elgato.state()
        print(state)

        # Toggle the Key Light
        await elgato.light(on=(not state.on))


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))
