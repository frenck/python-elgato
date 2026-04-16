# pylint: disable=redefined-outer-name
"""Asynchronous Python client for Elgato Lights."""

import asyncio

from elgato import Elgato


async def main() -> None:
    """Show how to programmatically change the display name of an Elgato Light."""
    async with Elgato("elgato-key-light.local") as elgato:
        # Current name
        await elgato.info()

        # Change the name
        await elgato.display_name("New name")

        # New name
        await elgato.info()


if __name__ == "__main__":
    asyncio.run(main())
