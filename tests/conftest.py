"""Common fixtures and helpers for Elgato Light tests."""

import hashlib
import struct
from collections.abc import AsyncGenerator, Callable, Generator
from inspect import signature
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import aiohttp
import pytest
from aioresponses import aioresponses
from aioresponses import core as aioresponses_core
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from elgato import Elgato
from elgato import firmware as firmware_module

# Elgato signs its images with a key we obviously do not have, so tests sign
# their own and hang it in an unused signature slot.
TEST_SIGNING_KEY_ID = 9

AIOHTTP_REQUIRES_STREAM_WRITER = (
    "stream_writer" in signature(aiohttp.ClientResponse.__init__).parameters
)
AIOHTTP_STREAM_WRITER_STUB = SimpleNamespace(output_size=0)


class AioresponsesClientResponse(aioresponses_core.ClientResponse):
    """Backwards-compatible ClientResponse for aioresponses."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize and provide a stream_writer for aiohttp 3.14+."""
        if AIOHTTP_REQUIRES_STREAM_WRITER:
            kwargs.setdefault("stream_writer", AIOHTTP_STREAM_WRITER_STUB)
        super().__init__(*args, **kwargs)


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    """Load a fixture file by name."""
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


@pytest.fixture
def responses() -> Generator[aioresponses, None, None]:
    """Yield an aioresponses instance that patches aiohttp client sessions."""
    with aioresponses() as mocker:
        yield mocker


@pytest.fixture(scope="session", autouse=True)
def setup_aioresponses_aiohttp_compat() -> Generator[None, None, None]:
    """Patch aioresponses ClientResponse for aiohttp compatibility in tests."""
    if not AIOHTTP_REQUIRES_STREAM_WRITER:
        yield
        return

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(aioresponses_core, "ClientResponse", AioresponsesClientResponse)
    try:
        yield
    finally:
        monkeypatch.undo()


@pytest.fixture
async def elgato() -> AsyncGenerator[Elgato, None]:
    """Yield an Elgato client wired to example.com with default settings."""
    async with aiohttp.ClientSession() as session:
        yield Elgato("example.com", session=session)


@pytest.fixture
def make_firmware(monkeypatch: pytest.MonkeyPatch) -> Callable[..., bytes]:
    """Yield a factory building firmware images signed with a throwaway key."""
    private_key = Ed25519PrivateKey.generate()
    monkeypatch.setitem(
        firmware_module.SIGNING_KEYS,
        TEST_SIGNING_KEY_ID,
        private_key.public_key().public_bytes_raw(),
    )

    # pylint: disable-next=too-many-arguments
    def build(  # noqa: PLR0913
        *,
        board_type: int = 201,
        build_number: int = 151,
        version: tuple[int, int, int] = (1, 0, 4),
        payload: bytes = b"\x00" * 256,
        magic: int = firmware_module.HEADER_MAGIC,
        header_version: int = firmware_module.HEADER_VERSION,
        identifier: bytes = firmware_module.HEADER_IDENTIFIER,
        payload_size: int | None = None,
        payload_offset: int = firmware_module.HEADER_SIZE,
        reserved: int = 0,
        signing_key_id: int = TEST_SIGNING_KEY_ID,
        signed: bool = True,
    ) -> bytes:
        """Build a firmware image, warts optional."""
        header = bytearray(firmware_module.HEADER_SIZE)
        struct.pack_into("<HH", header, 0, magic, header_version)
        header[4 : 4 + len(identifier)] = identifier
        header[45] = board_type
        struct.pack_into("<HHHH", header, 46, *version, build_number)
        struct.pack_into(
            "<I", header, 54, len(payload) if payload_size is None else payload_size
        )
        struct.pack_into("<HHH", header, 58, payload_offset, reserved, signing_key_id)

        digest = hashlib.sha512(bytes(header[:64]) + payload).digest()
        header[64:128] = private_key.sign(digest) if signed else bytes(64)

        return bytes(header) + payload

    return build
