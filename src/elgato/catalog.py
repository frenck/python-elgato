"""Firmware catalog for Elgato Lights.

Elgato does not run a firmware download service. Every image ships inside the
Control Center application, and new firmware only arrives with a new Control
Center release. The macOS build is a plain zip archive, so the images can be
read straight out of it.

Reading the whole archive to answer "is there anything newer" would be
wasteful, so this walks it over HTTP range requests instead. Against an
archive of sixteen megabytes, reading the versions of every model costs about
two hundred kilobytes and pulling one image about six hundred. Checking
whether any of that changed costs twelve, which is the number that matters:
it is the one a poller pays.
"""

from __future__ import annotations

import asyncio
import socket
import struct
import zlib
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import TYPE_CHECKING, Self

import orjson
from aiohttp.client import ClientError, ClientSession
from aiohttp.hdrs import METH_GET, METH_HEAD

from .exceptions import ElgatoConnectionError, ElgatoFirmwareError
from .firmware import HEADER_SIZE, FirmwareImage, FirmwareVersion

if TYPE_CHECKING:
    from collections.abc import Iterator

    from multidict import CIMultiDictProxy

CATALOG_URL = "https://gc-updates.elgato.com/"
CATALOG_PRODUCT = "cc-mac"

# Firmware images sit next to the other application resources.
FIRMWARE_MEMBER = "/Resources/Firmware_"

# Zip end of central directory record. It sits at the end of an archive,
# behind a comment of up to 64 KiB.
EOCD_SIGNATURE = b"PK\x05\x06"
EOCD_MAX_SIZE = 65557
CENTRAL_SIGNATURE = b"PK\x01\x02"
COMPRESSION_STORED = 0
COMPRESSION_DEFLATE = 8

# Enough for a local file header plus a useful bite of compressed data. The
# firmware header we are after is the first 128 bytes of that data.
LOCAL_HEADER_WINDOW = 4096


def _local_data_offset(window: bytes) -> int:
    """Return where a member's data starts, relative to its local header."""
    name_size, extra_size = struct.unpack_from("<HH", window, 26)
    return 30 + name_size + extra_size


def _decompress(data: bytes, compression: int, *, limit: int = 0) -> bytes:
    """Inflate archive data, or hand it back when it is stored uncompressed.

    Args:
    ----
        data: The raw bytes as they sit in the archive.
        compression: The compression method the archive index named.
        limit: Stop after this many bytes, or 0 for all of them.

    """
    if compression == COMPRESSION_STORED:
        return data[:limit] if limit else data

    if compression != COMPRESSION_DEFLATE:
        msg = f"Control Center archive uses unsupported compression {compression}"
        raise ElgatoFirmwareError(msg)

    return zlib.decompressobj(-zlib.MAX_WBITS).decompress(data, limit)


@dataclass(frozen=True)
class _ArchiveMember:
    """A firmware image inside the Control Center archive."""

    name: str
    header_offset: int
    compressed_size: int
    compression: int


def _walk_index(index: bytes) -> Iterator[_ArchiveMember]:
    """Walk a zip central directory, yielding the firmware images in it.

    Args:
    ----
        index: The raw central directory of the archive.

    """
    offset = 0
    while index[offset : offset + 4] == CENTRAL_SIGNATURE:
        (compression,) = struct.unpack_from("<H", index, offset + 10)
        (compressed_size,) = struct.unpack_from("<I", index, offset + 20)
        name_size, extra_size, comment_size = struct.unpack_from(
            "<HHH", index, offset + 28
        )
        (header_offset,) = struct.unpack_from("<I", index, offset + 42)
        name = index[offset + 46 : offset + 46 + name_size].decode()
        offset += 46 + name_size + extra_size + comment_size

        if FIRMWARE_MEMBER in name and name.endswith(".bin"):
            yield _ArchiveMember(
                name=name,
                header_offset=header_offset,
                compressed_size=compressed_size,
                compression=compression,
            )


@dataclass
class FirmwareCatalog:
    """The firmware Elgato currently ships for its lights."""

    session: ClientSession | None = None
    request_timeout: int = 30

    _close_session: bool = False
    _archive_url: str = ""
    _archive_size: int = 0
    _members: dict[int, _ArchiveMember] = field(default_factory=dict)
    _versions: dict[int, FirmwareVersion] = field(default_factory=dict)

    async def versions(self, *, refresh: bool = False) -> dict[int, FirmwareVersion]:
        """Get the newest firmware Elgato ships, per board type.

        The result is cached, so asking twice is free. A refresh re-reads the
        small release index Elgato publishes and only walks the archive again
        when Elgato has actually shipped a new Control Center. On every other
        day that is a single request of about twelve kilobytes, which is what
        makes a daily check practical.

        Args:
        ----
            refresh: Check whether Elgato published a new Control Center.

        Returns:
        -------
            A dictionary of board type to the newest FirmwareVersion for it.

        """
        if self._versions and not refresh:
            return dict(self._versions)

        published = await self._published_archive()

        if published != self._archive_url or not self._versions:
            self._archive_url = published
            self._members = {}
            self._versions = {}
            await self._read_index()

        return dict(self._versions)

    async def latest(self, board_type: int) -> FirmwareVersion:
        """Get the newest firmware Elgato ships for a board type.

        Args:
        ----
            board_type: The board, as reported by `Info.hardware_board_type`.

        Returns:
        -------
            The newest FirmwareVersion Elgato ships for that board.

        Raises:
        ------
            ElgatoFirmwareError: Elgato ships no firmware for this board.

        """
        versions = await self.versions()
        if (version := versions.get(board_type)) is None:
            msg = f"Elgato ships no firmware for board type {board_type}"
            raise ElgatoFirmwareError(msg)

        return version

    async def download(self, board_type: int) -> FirmwareImage:
        """Download the newest firmware Elgato ships for a board type.

        Args:
        ----
            board_type: The board, as reported by `Info.hardware_board_type`.

        Returns:
        -------
            A verified FirmwareImage, ready to install.

        Raises:
        ------
            ElgatoFirmwareError: Elgato ships no firmware for this board, or
                the downloaded image does not verify.

        """
        await self.latest(board_type)
        member = self._members[board_type]

        window = await self._read(member.header_offset, LOCAL_HEADER_WINDOW)
        data_offset = member.header_offset + _local_data_offset(window)
        compressed = await self._read(data_offset, member.compressed_size)

        return FirmwareImage.from_bytes(_decompress(compressed, member.compression))

    async def _published_archive(self) -> str:
        """Find the Control Center release Elgato currently publishes."""
        _, _, body = await self._request(CATALOG_URL)

        try:
            # pylint: disable-next=no-member
            return str(orjson.loads(body)[CATALOG_PRODUCT]["downloadURL"])
        # pylint: disable-next=no-member
        except (orjson.JSONDecodeError, KeyError, TypeError) as exception:
            msg = "Elgato published no Control Center release to read firmware from"
            raise ElgatoFirmwareError(msg) from exception

    async def _read_index(self) -> None:
        """Read the archive index and the firmware header of every image."""
        _, headers, _ = await self._request(self._archive_url, method=METH_HEAD)
        self._archive_size = int(headers["Content-Length"])

        tail_size = min(self._archive_size, EOCD_MAX_SIZE)
        tail = await self._read(self._archive_size - tail_size, tail_size)

        if (eocd := tail.rfind(EOCD_SIGNATURE)) == -1:
            msg = "Control Center archive has no readable index"
            raise ElgatoFirmwareError(msg)

        index_size, index_offset = struct.unpack_from("<II", tail, eocd + 12)
        index = await self._read(index_offset, index_size)

        for member in _walk_index(index):
            # The board type comes out of the firmware header itself, so a
            # model Elgato adds later needs no changes here.
            version = FirmwareVersion.from_header(await self._read_header(member))
            self._versions[version.board_type] = version
            self._members[version.board_type] = member

    async def _read_header(self, member: _ArchiveMember) -> bytes:
        """Read the firmware header out of an image in the archive."""
        window = await self._read(member.header_offset, LOCAL_HEADER_WINDOW)
        return _decompress(
            window[_local_data_offset(window) :],
            member.compression,
            limit=HEADER_SIZE,
        )

    async def _read(self, start: int, length: int) -> bytes:
        """Read a byte range out of the Control Center archive.

        Args:
        ----
            start: Offset of the first byte wanted.
            length: How many bytes to read.

        Returns:
        -------
            Exactly the bytes that were asked for.

        Raises:
        ------
            ElgatoFirmwareError: The server ignored the range and sent
                something other than the slice that was asked for.

        """
        end = start + length - 1
        status, _, body = await self._request(
            self._archive_url,
            headers={"Range": f"bytes={start}-{end}"},
        )

        # A server that ignores Range answers 200 with the whole archive.
        # Every offset after this one would then read the wrong bytes, and
        # the sixteen megabytes this is built to avoid arrive anyway. Say so
        # rather than quietly parse nonsense.
        if status != HTTPStatus.PARTIAL_CONTENT:
            msg = "Elgato served the Control Center archive without byte ranges"
            raise ElgatoFirmwareError(msg)

        return body

    async def _request(
        self,
        url: str,
        *,
        method: str = METH_GET,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, CIMultiDictProxy[str], bytes]:
        """Handle a request to Elgato's servers.

        Args:
        ----
            url: The full URL to request.
            method: HTTP method to use.
            headers: Extra headers to send, such as a byte range.

        Returns:
        -------
            The response status, headers and body.

        Raises:
        ------
            ElgatoConnectionError: An error occurred while talking to Elgato.

        """
        if self.session is None:
            self.session = ClientSession()
            self._close_session = True

        try:
            async with asyncio.timeout(self.request_timeout):
                response = await self.session.request(
                    method,
                    url,
                    headers={"User-Agent": "PythonElgato", **(headers or {})},
                )
                response.raise_for_status()
                body = await response.read()
        except TimeoutError as exception:
            msg = "Timeout occurred while connecting to Elgato"
            raise ElgatoConnectionError(msg) from exception
        except (ClientError, socket.gaierror) as exception:
            msg = "Error occurred while communicating with Elgato"
            raise ElgatoConnectionError(msg) from exception

        return response.status, response.headers, body

    async def close(self) -> None:
        """Close open client session."""
        if self.session and self._close_session:
            await self.session.close()

    async def __aenter__(self) -> Self:
        """Async enter.

        Returns
        -------
            The FirmwareCatalog object.

        """
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        """Async exit.

        Args:
        ----
            _exc_info: Exec type.

        """
        await self.close()
