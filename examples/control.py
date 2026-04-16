# pylint: disable=redefined-outer-name
"""Asynchronous Python client for Elgato Lights."""

import asyncio

from elgato import Elgato, State


async def main() -> None:
    """Show example on controlling your Elgato Light device."""
    async with Elgato("elgato-key-light.local") as elgato:
        print(await elgato.info())

        print(await elgato.settings())

        state: State = await elgato.state()

        # Toggle the light
        await elgato.light(on=(not state.on))


if __name__ == "__main__":
    asyncio.run(main())
