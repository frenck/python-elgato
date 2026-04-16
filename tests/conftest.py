"""Common fixtures and helpers for Elgato Light tests."""

from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import aiohttp
import pytest
from aioresponses import aioresponses

from elgato import Elgato

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    """Load a fixture file by name."""
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


@pytest.fixture
def responses() -> Generator[aioresponses, None, None]:
    """Yield an aioresponses instance that patches aiohttp client sessions."""
    with aioresponses() as mocker:
        yield mocker


@pytest.fixture
async def elgato() -> AsyncGenerator[Elgato, None]:
    """Yield an Elgato client wired to example.com with default settings."""
    async with aiohttp.ClientSession() as session:
        yield Elgato("example.com", session=session)
