"""Tests for the firmware Elgato ships with Control Center."""

import io
import zipfile
from collections.abc import Callable

import pytest
from aiohttp import ClientSession
from aioresponses import CallbackResult, aioresponses

from elgato import FirmwareCatalog
from elgato.catalog import CATALOG_URL
from elgato.exceptions import ElgatoConnectionError, ElgatoFirmwareError

ARCHIVE_URL = "https://edge.elgato.com/egc/macos/eccm/1.9/ControlCenter.app.zip"
RESOURCES = "Elgato Control Center.app/Contents/Resources/"
DEFAULT_CATALOG = f'{{"cc-mac": {{"downloadURL": "{ARCHIVE_URL}"}}}}'


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
) -> list[str]:
    """Serve a Control Center archive, byte ranges and all.

    Returns
    -------
        A list that collects every range served, so a test can count them.

    """
    served: list[str] = []

    def serve(_url: str, **kwargs: object) -> CallbackResult:
        headers: dict[str, str] = kwargs["headers"]  # type: ignore[assignment]
        served.append(headers["Range"])
        start, _, end = headers["Range"].removeprefix("bytes=").partition("-")
        return CallbackResult(status=206, body=archive[int(start) : int(end) + 1])

    responses.get(
        CATALOG_URL,
        status=200,
        body=catalog if catalog is not None else DEFAULT_CATALOG,
        content_type="application/json",
        repeat=True,
    )
    responses.head(
        ARCHIVE_URL,
        status=200,
        headers={"Content-Length": str(len(archive))},
        repeat=True,
    )
    responses.get(ARCHIVE_URL, callback=serve, repeat=True)

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
    """Test the catalog only reads Elgato's servers once."""
    served = mock_elgato(responses, archive)

    async with FirmwareCatalog() as catalog:
        await catalog.versions()
        reads = len(served)
        await catalog.versions()

        assert len(served) == reads

        await catalog.versions(refresh=True)
        assert len(served) == reads * 2


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
