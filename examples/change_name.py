# pylint: disable=W0621
"""Asynchronous Python client for Elgato Lights."""

import asyncio

from elgato import Elgato, Info


async def main():
    """Show example of programmatically change the display name of a Elgato Light."""
    async with Elgato("elgato-key-light.local") as elgato:
        # Current name
        info: Info = await elgato.info()
        print(info.display_name)

        # Change the name
        await elgato.display_name("New name")

        # New name
        info: Info = await elgato.info()
        print(info.display_name)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
