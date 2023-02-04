# pylint: disable=W0621
"""Asynchronous Python client for Elgato Lights."""

import asyncio

from elgato import Elgato


async def main() -> None:
    """Show example of programmatically change the display name of a Elgato Light."""
    async with Elgato("elgato-key-light.local") as elgato:
        # Current name
        await elgato.info()

        # Change the name
        await elgato.display_name("New name")

        # New name
        await elgato.info()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
