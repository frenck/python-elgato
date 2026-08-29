"""Tests for reading Elgato Light firmware images."""

from collections.abc import Callable

import pytest

from elgato import FirmwareImage, FirmwareVersion
from elgato.exceptions import ElgatoFirmwareError
from elgato.firmware import HEADER_SIZE


async def test_image(make_firmware: Callable[..., bytes]) -> None:
    """Test reading a firmware image."""
    data = make_firmware(board_type=202, build_number=240, version=(1, 0, 4))
    image = FirmwareImage.from_bytes(data)

    assert image.board_type == 202
    assert image.board_name == "Elgato Key Light Mini"
    assert image.build_number == 240
    assert image.version == "1.0.4"
    assert image.full_version == "1.0.4 (240)"
    assert image.data == data


async def test_image_hides_its_payload(make_firmware: Callable[..., bytes]) -> None:
    """Test a firmware image keeps a megabyte of payload out of its repr."""
    image = FirmwareImage.from_bytes(make_firmware())
    assert "data=" not in repr(image)


async def test_unknown_board(make_firmware: Callable[..., bytes]) -> None:
    """Test a board Elgato had not built yet still reads."""
    image = FirmwareImage.from_bytes(make_firmware(board_type=222))
    assert image.board_name == "Unknown board 222"


async def test_version_from_header(make_firmware: Callable[..., bytes]) -> None:
    """Test reading a version out of a header alone."""
    header = make_firmware(board_type=53, build_number=222)[:HEADER_SIZE]
    version = FirmwareVersion.from_header(header)

    assert version.board_type == 53
    assert version.full_version == "1.0.4 (222)"


async def test_too_short(make_firmware: Callable[..., bytes]) -> None:
    """Test rejecting something too short to even hold a header."""
    with pytest.raises(ElgatoFirmwareError, match="shorter than"):
        FirmwareImage.from_bytes(make_firmware()[:64])


async def test_bad_magic(make_firmware: Callable[..., bytes]) -> None:
    """Test rejecting an image that is not an Elgato firmware."""
    with pytest.raises(ElgatoFirmwareError, match="bad magic"):
        FirmwareImage.from_bytes(make_firmware(magic=0x4B50))


async def test_bad_header_version(make_firmware: Callable[..., bytes]) -> None:
    """Test rejecting a header layout we do not know."""
    with pytest.raises(ElgatoFirmwareError, match="header version 2"):
        FirmwareImage.from_bytes(make_firmware(header_version=2))


async def test_bad_identifier(make_firmware: Callable[..., bytes]) -> None:
    """Test rejecting an image without the Elgato identification string."""
    with pytest.raises(ElgatoFirmwareError, match="identification string"):
        FirmwareImage.from_bytes(make_firmware(identifier=b"E" * 41))


async def test_size_mismatch(make_firmware: Callable[..., bytes]) -> None:
    """Test rejecting an image that is not as long as it claims."""
    with pytest.raises(ElgatoFirmwareError, match="declares 1152 bytes"):
        FirmwareImage.from_bytes(make_firmware(payload_size=1024))


async def test_unknown_signing_key(make_firmware: Callable[..., bytes]) -> None:
    """Test rejecting an image signed with a key no light carries."""
    with pytest.raises(ElgatoFirmwareError, match="unknown key 3"):
        FirmwareImage.from_bytes(make_firmware(signing_key_id=3))


async def test_bad_signature(make_firmware: Callable[..., bytes]) -> None:
    """Test rejecting an image whose signature does not hold up."""
    with pytest.raises(ElgatoFirmwareError, match="signature is invalid"):
        FirmwareImage.from_bytes(make_firmware(signed=False))


async def test_tampered_payload(make_firmware: Callable[..., bytes]) -> None:
    """Test a single flipped bit in the payload is enough to fail."""
    data = bytearray(make_firmware(payload=b"\x11" * 512))
    data[HEADER_SIZE + 400] ^= 0x01

    with pytest.raises(ElgatoFirmwareError, match="signature is invalid"):
        FirmwareImage.from_bytes(bytes(data))


async def test_payload_offset(make_firmware: Callable[..., bytes]) -> None:
    """Test rejecting an image whose payload does not follow the header.

    A device reads a fixed header, so a different offset would mean verifying
    a signature over bytes it never hashes.
    """
    with pytest.raises(ElgatoFirmwareError, match="starts at 256"):
        FirmwareImage.from_bytes(make_firmware(payload_offset=256))


async def test_reserved_field(make_firmware: Callable[..., bytes]) -> None:
    """Test rejecting an image with a reserved field the device refuses."""
    with pytest.raises(ElgatoFirmwareError, match="non-zero reserved field"):
        FirmwareImage.from_bytes(make_firmware(reserved=1))
