"""Tests for the firmware Elgato ships with Control Center."""

# pylint: disable=protected-access,redefined-outer-name

import asyncio
import io
import zipfile
from collections.abc import Callable
from typing import Any
from unittest.mock import patch

import pytest
from aiohttp import ClientSession
from aioresponses import CallbackResult, aioresponses

from elgato import FirmwareCatalog
from elgato.catalog import CATALOG_URL
from elgato.exceptions import ElgatoConnectionError, ElgatoFirmwareError

ARCHIVE_URL = "https://edge.elgato.com/egc/macos/eccm/1.9/ControlCenter.app.zip"
RESOURCES = "Elgato Control Center.app/Contents/Resources/"
NEXT_ARCHIVE_URL = "https://edge.elgato.com/egc/macos/eccm/2.0/ControlCenter.app.zip"
DEFAULT_CATALOG = f'{{"cc-mac": {{"downloadURL": "{ARCHIVE_URL}"}}}}'
NEXT_CATALOG = f'{{"cc-mac": {{"downloadURL": "{NEXT_ARCHIVE_URL}"}}}}'


def build_archive(
    members: dict[str, bytes],
    *,
    compression: int = zipfile.ZIP_DEFLATED,
) -> bytes:
    """Build a Control Center archive holding the given files."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression) as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def mock_elgato(
    responses: aioresponses,
    archive: bytes,
    *,
    catalog: str | None = None,
    url: str = ARCHIVE_URL,
    repeat: bool = True,
) -> list[str]:
    """Serve a Control Center archive, byte ranges and all.

    Returns
    -------
        A list that collects every range served, so a test can count them.

    """
    served: list[str] = []

    def serve(_url: str, **kwargs: Any) -> CallbackResult:
        headers: dict[str, str] = kwargs["headers"]
        served.append(headers["Range"])
        start, _, end = headers["Range"].removeprefix("bytes=").partition("-")
        return CallbackResult(status=206, body=archive[int(start) : int(end) + 1])

    responses.get(
        CATALOG_URL,
        status=200,
        body=catalog if catalog is not None else DEFAULT_CATALOG,
        content_type="application/json",
        repeat=repeat,
    )
    responses.head(
        url,
        status=200,
        headers={"Content-Length": str(len(archive))},
        repeat=True,
    )
    responses.get(url, callback=serve, repeat=True)

    return served


@pytest.fixture
def archive(make_firmware: Callable[..., bytes]) -> bytes:
    """Yield an archive holding firmware for three lights, and other junk."""
    return build_archive(
        {
            f"{RESOURCES}Info.plist": b"<plist/>",
            f"{RESOURCES}Firmware_Key_Light.bin": make_firmware(
                board_type=53, build_number=222, version=(1, 0, 3)
            ),
            f"{RESOURCES}Firmware_Ring_Light.bin": make_firmware(
                board_type=201, build_number=151
            ),
            f"{RESOURCES}Firmware_Key_Light_Mini.bin": make_firmware(
                board_type=202, build_number=240
            ),
            f"{RESOURCES}Firmware_Notes.txt": b"not a firmware",
        }
    )


async def test_versions(responses: aioresponses, archive: bytes) -> None:
    """Test listing the firmware Elgato currently ships."""
    mock_elgato(responses, archive)

    async with FirmwareCatalog() as catalog:
        versions = await catalog.versions()

    assert sorted(versions) == [53, 201, 202]
    assert versions[53].full_version == "1.0.3 (222)"
    assert versions[53].board_name == "Elgato Key Light"
    assert versions[202].full_version == "1.0.4 (240)"


async def test_versions_are_cached(responses: aioresponses, archive: bytes) -> None:
    """Test the catalog reads the archive once and then leaves Elgato alone."""
    served = mock_elgato(responses, archive)

    async with FirmwareCatalog() as catalog:
        await catalog.versions()
        reads = len(served)
        assert reads

        await catalog.versions()
        assert len(served) == reads


async def test_refresh_without_a_new_release(
    responses: aioresponses,
    archive: bytes,
) -> None:
    """Test a refresh stops at the release index while nothing has changed.

    This is the case a daily check hits on all but a handful of days a year,
    so it must not walk the archive again.
    """
    served = mock_elgato(responses, archive)

    async with FirmwareCatalog() as catalog:
        versions = await catalog.versions()
        reads = len(served)

        assert await catalog.versions(refresh=True) == versions
        assert len(served) == reads


async def test_refresh_with_a_new_release(
    responses: aioresponses,
    archive: bytes,
    make_firmware: Callable[..., bytes],
) -> None:
    """Test a refresh picks up a Control Center that ships newer firmware."""
    newer = build_archive(
        {
            f"{RESOURCES}Firmware_Ring_Light.bin": make_firmware(
                board_type=201, build_number=160, version=(1, 0, 5)
            )
        }
    )
    mock_elgato(responses, archive, catalog=DEFAULT_CATALOG, repeat=False)
    mock_elgato(responses, newer, catalog=NEXT_CATALOG, url=NEXT_ARCHIVE_URL)

    async with FirmwareCatalog() as catalog:
        assert (await catalog.latest(201)).full_version == "1.0.4 (151)"

        await catalog.versions(refresh=True)
        assert (await catalog.latest(201)).full_version == "1.0.5 (160)"


async def test_latest(responses: aioresponses, archive: bytes) -> None:
    """Test asking for the firmware of a single board."""
    mock_elgato(responses, archive)

    async with FirmwareCatalog() as catalog:
        assert (await catalog.latest(201)).full_version == "1.0.4 (151)"


async def test_latest_unknown_board(responses: aioresponses, archive: bytes) -> None:
    """Test asking for a board Elgato ships no firmware for."""
    mock_elgato(responses, archive)

    async with FirmwareCatalog() as catalog:
        with pytest.raises(ElgatoFirmwareError, match="board type 70"):
            await catalog.latest(70)


async def test_download(
    responses: aioresponses,
    archive: bytes,
    make_firmware: Callable[..., bytes],
) -> None:
    """Test pulling one firmware image out of the archive."""
    mock_elgato(responses, archive)

    async with FirmwareCatalog() as catalog:
        image = await catalog.download(202)

    assert image.board_type == 202
    assert image.full_version == "1.0.4 (240)"
    assert image.data == make_firmware(board_type=202, build_number=240)


async def test_download_from_uncompressed_archive(
    responses: aioresponses,
    make_firmware: Callable[..., bytes],
) -> None:
    """Test an archive that stores its firmware without compressing it."""
    firmware = make_firmware(board_type=53)
    mock_elgato(
        responses,
        build_archive(
            {f"{RESOURCES}Firmware_Key_Light.bin": firmware},
            compression=zipfile.ZIP_STORED,
        ),
    )

    async with FirmwareCatalog() as catalog:
        assert (await catalog.download(53)).data == firmware


async def test_unsupported_compression(
    responses: aioresponses,
    make_firmware: Callable[..., bytes],
) -> None:
    """Test an archive packed in a way we cannot unpack."""
    mock_elgato(
        responses,
        build_archive(
            {f"{RESOURCES}Firmware_Key_Light.bin": make_firmware(board_type=53)},
            compression=zipfile.ZIP_BZIP2,
        ),
    )

    async with FirmwareCatalog() as catalog:
        with pytest.raises(ElgatoFirmwareError, match="unsupported compression"):
            await catalog.versions()


async def test_no_control_center_release(
    responses: aioresponses,
    archive: bytes,
) -> None:
    """Test Elgato not naming a Control Center release to read."""
    mock_elgato(responses, archive, catalog='{"sd-mac":{}}')

    async with FirmwareCatalog() as catalog:
        with pytest.raises(ElgatoFirmwareError, match="no Control Center release"):
            await catalog.versions()


async def test_unreadable_catalog(responses: aioresponses, archive: bytes) -> None:
    """Test Elgato answering with something that is not the catalog."""
    mock_elgato(responses, archive, catalog="<html>maintenance</html>")

    async with FirmwareCatalog() as catalog:
        with pytest.raises(ElgatoFirmwareError, match="no Control Center release"):
            await catalog.versions()


async def test_archive_without_index(responses: aioresponses) -> None:
    """Test something that is served as an archive but is not one."""
    mock_elgato(responses, b"not a zip file, sorry" * 16)

    async with FirmwareCatalog() as catalog:
        with pytest.raises(ElgatoFirmwareError, match="no readable index"):
            await catalog.versions()


async def test_connection_error(responses: aioresponses) -> None:
    """Test Elgato's servers being unreachable."""
    responses.get(CATALOG_URL, status=503, body="")

    async with FirmwareCatalog() as catalog:
        with pytest.raises(ElgatoConnectionError):
            await catalog.versions()


async def test_timeout(responses: aioresponses) -> None:
    """Test Elgato's servers taking their time."""
    responses.get(CATALOG_URL, exception=TimeoutError())

    async with FirmwareCatalog(request_timeout=1) as catalog:
        with pytest.raises(ElgatoConnectionError):
            await catalog.versions()


async def test_provided_session(responses: aioresponses, archive: bytes) -> None:
    """Test a session handed in from outside is left open."""
    mock_elgato(responses, archive)

    async with ClientSession() as session:
        catalog = FirmwareCatalog(session=session)
        await catalog.versions()
        await catalog.close()

        assert not session.closed


async def test_server_ignores_ranges(responses: aioresponses, archive: bytes) -> None:
    """Test a server that answers a range request with the whole archive.

    Every offset after the first would read the wrong bytes, so this has to
    fail loudly rather than parse whatever it got.
    """
    responses.get(
        CATALOG_URL,
        status=200,
        body=DEFAULT_CATALOG,
        content_type="application/json",
    )
    responses.head(
        ARCHIVE_URL,
        status=200,
        headers={"Content-Length": str(len(archive))},
    )
    responses.get(ARCHIVE_URL, status=200, body=archive, repeat=True)

    async with FirmwareCatalog() as catalog:
        with pytest.raises(ElgatoFirmwareError, match="without byte ranges"):
            await catalog.versions()


async def test_server_truncates_a_range(
    responses: aioresponses,
    archive: bytes,
) -> None:
    """Test a range that comes back short of what was asked for.

    The status says 206, so only the length gives it away. Callers index
    straight into the result, so a short read has to stop here.
    """

    def serve_short(_url: str, **kwargs: Any) -> CallbackResult:
        headers: dict[str, str] = kwargs["headers"]
        start, _, end = headers["Range"].removeprefix("bytes=").partition("-")
        return CallbackResult(status=206, body=archive[int(start) : int(end)])

    responses.get(
        CATALOG_URL,
        status=200,
        body=DEFAULT_CATALOG,
        content_type="application/json",
    )
    responses.head(
        ARCHIVE_URL,
        status=200,
        headers={"Content-Length": str(len(archive))},
    )
    responses.get(ARCHIVE_URL, callback=serve_short, repeat=True)

    async with FirmwareCatalog() as catalog:
        with pytest.raises(ElgatoFirmwareError, match=r"where \d+ were asked for"):
            await catalog.versions()


async def test_refresh_during_a_download(
    responses: aioresponses,
    make_firmware: Callable[..., bytes],
) -> None:
    """Test Elgato publishing a new release while an image is downloading.

    A download reads the archive in pieces. If a refresh swaps the archive
    out between two of them, the later pieces come from a different file at
    offsets that belong to the old one.
    """
    firmware = make_firmware(board_type=53, build_number=222, version=(1, 0, 3))
    first = build_archive({f"{RESOURCES}Firmware_Key_Light.bin": firmware})
    # Padding ahead of it, so the same member sits somewhere else entirely.
    second = build_archive(
        {
            f"{RESOURCES}Notes.txt": b"n" * 40_000,
            f"{RESOURCES}Firmware_Key_Light.bin": firmware,
        }
    )

    async with FirmwareCatalog() as catalog:
        served = mock_elgato(responses, first, catalog=DEFAULT_CATALOG, repeat=False)
        await catalog.versions()

        mock_elgato(responses, second, catalog=NEXT_CATALOG, url=NEXT_ARCHIVE_URL)
        refresh: asyncio.Task[Any] | None = None

        original_read = catalog._read

        async def read_and_meddle(start: int, length: int) -> bytes:
            """Let Elgato publish a new release mid download, once."""
            nonlocal refresh
            if refresh is None:
                refresh = asyncio.create_task(catalog.versions(refresh=True))
                await asyncio.sleep(0)
            return await original_read(start, length)

        with patch.object(catalog, "_read", read_and_meddle):
            image = await catalog.download(53)

        assert refresh is not None
        await refresh

        assert image.data == firmware
        assert served


async def test_download_for_a_board_elgato_skips(
    responses: aioresponses,
    archive: bytes,
) -> None:
    """Test asking for an image Elgato does not publish."""
    mock_elgato(responses, archive)

    async with FirmwareCatalog() as catalog:
        with pytest.raises(ElgatoFirmwareError, match="board type 70"):
            await catalog.download(70)
