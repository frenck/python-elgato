"""Tests for installing firmware on an Elgato Light device."""

import re
from collections.abc import Callable
from typing import Any

import pytest
from aioresponses import CallbackResult, aioresponses

from elgato import Elgato, FirmwareImage
from elgato.elgato import FIRMWARE_CHUNK_SIZE
from elgato.exceptions import ElgatoFirmwareError

from .conftest import load_fixture

PREPARE_URL = "http://example.com:9123/elgato/firmware-update/prepare"
DATA_URL = re.compile(r"^http://example\.com:9123/elgato/firmware-update/data\?offset=")
EXECUTE_URL = "http://example.com:9123/elgato/firmware-update/execute"

# Three chunks, the last one deliberately short.
PAYLOAD = bytes(range(256)) * 33


def mock_device(
    responses: aioresponses,
    *,
    info: str = "info-key-light.json",
    settings: str = "settings-keylight.json",
) -> None:
    """Answer the calls an update makes before it sends a single byte."""
    responses.get(
        "http://example.com:9123/elgato/accessory-info",
        status=200,
        body=load_fixture(info),
        content_type="application/json",
    )
    responses.get(
        "http://example.com:9123/elgato/lights/settings",
        status=200,
        body=load_fixture(settings),
        content_type="application/json",
    )


async def test_update_firmware(
    responses: aioresponses,
    make_firmware: Callable[..., bytes],
) -> None:
    """Test installing a firmware image on an Elgato Light device."""
    image = FirmwareImage.from_bytes(make_firmware(board_type=53, payload=PAYLOAD))
    chunks: list[tuple[int, bytes]] = []
    progress: list[tuple[int, int]] = []

    def collect(url: str, **kwargs: Any) -> CallbackResult:
        offset = int(str(url).rpartition("=")[2])
        chunks.append((offset, bytes(kwargs["data"])))
        sent = offset + len(chunks[-1][1])
        return CallbackResult(status=200 if sent == len(image.data) else 202)

    mock_device(responses)
    responses.put(PREPARE_URL, status=200, body="")
    responses.put(DATA_URL, callback=collect, repeat=True)
    responses.post(EXECUTE_URL, status=200, body="")

    async with Elgato("example.com") as elgato:
        await elgato.update_firmware(
            image,
            on_progress=lambda *args: progress.append(args),
        )

    assert [offset for offset, _ in chunks] == [
        0,
        FIRMWARE_CHUNK_SIZE,
        FIRMWARE_CHUNK_SIZE * 2,
    ]
    assert b"".join(chunk for _, chunk in chunks) == image.data
    assert progress[-1] == (len(image.data), len(image.data))
    assert len(progress) == len(chunks)


async def test_update_firmware_wrong_board(
    responses: aioresponses,
    make_firmware: Callable[..., bytes],
) -> None:
    """Test refusing a firmware image built for another light."""
    mock_device(responses)
    image = FirmwareImage.from_bytes(make_firmware(board_type=201))

    async with Elgato("example.com") as elgato:
        with pytest.raises(ElgatoFirmwareError, match="Elgato Ring Light"):
            await elgato.update_firmware(image)


async def test_update_firmware_low_battery(
    responses: aioresponses,
    make_firmware: Callable[..., bytes],
) -> None:
    """Test refusing to update a light that is about to run out of power."""
    mock_device(
        responses,
        info="info-key-light-mini.json",
        settings="settings-key-light-mini.json",
    )
    responses.get(
        "http://example.com:9123/elgato/battery-info",
        status=200,
        body=load_fixture("battery-info-low.json"),
        content_type="application/json",
    )
    image = FirmwareImage.from_bytes(make_firmware(board_type=202))

    async with Elgato("example.com") as elgato:
        with pytest.raises(ElgatoFirmwareError, match="Battery is at 11%"):
            await elgato.update_firmware(image)


async def test_update_firmware_on_battery_power(
    responses: aioresponses,
    make_firmware: Callable[..., bytes],
) -> None:
    """Test a light with a healthy battery is allowed to update."""
    mock_device(
        responses,
        info="info-key-light-mini.json",
        settings="settings-key-light-mini.json",
    )
    responses.get(
        "http://example.com:9123/elgato/battery-info",
        status=200,
        body=load_fixture("battery-info.json"),
        content_type="application/json",
    )
    responses.put(PREPARE_URL, status=200, body="")
    responses.put(DATA_URL, status=200, body="", repeat=True)
    responses.post(EXECUTE_URL, status=200, body="")
    image = FirmwareImage.from_bytes(make_firmware(board_type=202))

    async with Elgato("example.com") as elgato:
        await elgato.update_firmware(image)


async def test_prepare_rejected(
    responses: aioresponses,
    make_firmware: Callable[..., bytes],
) -> None:
    """Test the device turning down an image before it starts."""
    mock_device(responses)
    responses.put(
        PREPARE_URL,
        status=400,
        body='{"errors":[{"message":"Firmware file size is too small","code":101}]}',
        content_type="application/json",
    )
    image = FirmwareImage.from_bytes(make_firmware(board_type=53))

    async with Elgato("example.com") as elgato:
        with pytest.raises(ElgatoFirmwareError, match="size is too small"):
            await elgato.update_firmware(image)


async def test_chunk_rejected(
    responses: aioresponses,
    make_firmware: Callable[..., bytes],
) -> None:
    """Test the device turning down the image it was being sent."""
    mock_device(responses)
    responses.put(PREPARE_URL, status=200, body="")
    responses.put(
        DATA_URL,
        status=400,
        body='{"errors":[{"message":"Firmware signature invalid","code":104}]}',
        content_type="application/json",
        repeat=True,
    )
    image = FirmwareImage.from_bytes(make_firmware(board_type=53))

    async with Elgato("example.com") as elgato:
        with pytest.raises(ElgatoFirmwareError, match="offset 0: Firmware sig"):
            await elgato.update_firmware(image)


async def test_chunk_retried(
    responses: aioresponses,
    make_firmware: Callable[..., bytes],
) -> None:
    """Test a chunk the device fumbles once is simply sent again."""
    attempts = 0

    def flaky(_url: str, **_kwargs: object) -> CallbackResult:
        nonlocal attempts
        attempts += 1
        return CallbackResult(status=200 if attempts > 1 else 408)

    mock_device(responses)
    responses.put(PREPARE_URL, status=200, body="")
    responses.put(DATA_URL, callback=flaky, repeat=True)
    responses.post(EXECUTE_URL, status=200, body="")
    image = FirmwareImage.from_bytes(make_firmware(board_type=53))

    async with Elgato("example.com") as elgato:
        await elgato.update_firmware(image)

    assert attempts == 2


async def test_chunk_rejected_outright(
    responses: aioresponses,
    make_firmware: Callable[..., bytes],
) -> None:
    """Test a status the device is not going to change its mind about."""
    mock_device(responses)
    responses.put(PREPARE_URL, status=200, body="")
    responses.put(DATA_URL, status=503, body="", repeat=True)
    image = FirmwareImage.from_bytes(make_firmware(board_type=53))

    async with Elgato("example.com") as elgato:
        with pytest.raises(ElgatoFirmwareError, match="returned HTTP 503"):
            await elgato.update_firmware(image)


async def test_execute_rejected(
    responses: aioresponses,
    make_firmware: Callable[..., bytes],
) -> None:
    """Test the device refusing to boot what it was just given."""
    mock_device(responses)
    responses.put(PREPARE_URL, status=200, body="")
    responses.put(DATA_URL, status=200, body="", repeat=True)
    responses.post(
        EXECUTE_URL,
        status=400,
        body=(
            '{"errors":[{"message":"Invalid command. Please run '
            'firmware-update/prepare first","code":-1}]}'
        ),
        content_type="application/json",
    )
    image = FirmwareImage.from_bytes(make_firmware(board_type=53))

    async with Elgato("example.com") as elgato:
        with pytest.raises(ElgatoFirmwareError, match="run firmware-update/prep"):
            await elgato.update_firmware(image)
