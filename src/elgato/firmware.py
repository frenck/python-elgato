"""Firmware images for Elgato Lights.

Elgato wraps every firmware image in a small container: a 128-byte header
followed by the payload. The header names the board the image belongs to and
carries an Ed25519 signature over the payload. The light checks that signature
itself and refuses anything that fails, so the checks here only exist to fail
early, before a light erases a flash slot for an image it will reject.
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field
from typing import Self

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .exceptions import ElgatoFirmwareError

HEADER_SIZE = 128
HEADER_MAGIC = 0x00CE
HEADER_VERSION = 1
HEADER_IDENTIFIER = b"Elgato Firmware - (c) Elgato Systems GmbH"

# Verification keys, not signing keys. Every light carries these in plain text
# and Elgato signs every shipped image with slot 2. Slots 1 and 3 exist in the
# firmware but nothing published uses them, so their keys are unknown here.
SIGNING_KEYS = {
    2: bytes.fromhex(
        "cce130fdefb4f2b335baed0c8a54323288c37ab51f1622c8b33cb78e7c6b21e8"
    ),
}

BOARD_TYPES = {
    53: "Elgato Key Light",
    54: "Eve Light Strip",
    57: "Elgato Light Strip Prototype",
    70: "Elgato Light Strip",
    200: "Elgato Key Light Air",
    201: "Elgato Ring Light",
    202: "Elgato Key Light Mini",
    205: "Elgato Key Light MK.2",
    206: "Elgato Light Strip Pro",
    210: "Elgato Key Light Neo",
    214: "Elgato Key Light Air MK.2",
}


@dataclass(frozen=True)
class FirmwareVersion:
    """A firmware build for a specific Elgato board.

    Attributes
    ----------
        board_type: The board this firmware belongs to.
        build_number: An integer with the build number of the firmware.
        version: String containing the firmware version.

    """

    board_type: int
    build_number: int
    version: str

    @property
    def board_name(self) -> str:
        """Return the marketing name of the board this firmware belongs to."""
        return BOARD_TYPES.get(self.board_type, f"Unknown board {self.board_type}")

    @property
    def full_version(self) -> str:
        """Return the version the way Elgato writes it, as '1.0.4 (240)'."""
        return f"{self.version} ({self.build_number})"

    @classmethod
    def from_header(cls, header: bytes) -> Self:
        """Read the version out of a firmware header.

        The first 128 bytes of an image are enough to name the build. That is
        all a version check needs, and it says nothing about the payload; use
        FirmwareImage.from_bytes when the payload matters.

        Args:
        ----
            header: At least the first 128 bytes of a firmware image.

        Returns:
        -------
            A FirmwareVersion describing the build in the header.

        Raises:
        ------
            ElgatoFirmwareError: The bytes are not an Elgato firmware header.

        """
        if len(header) < HEADER_SIZE:
            msg = f"Firmware is shorter than the {HEADER_SIZE} byte header"
            raise ElgatoFirmwareError(msg)

        magic, header_version = struct.unpack_from("<HH", header)
        if magic != HEADER_MAGIC:
            msg = f"Firmware has bad magic 0x{magic:04X}, expected 0x{HEADER_MAGIC:04X}"
            raise ElgatoFirmwareError(msg)

        if header_version != HEADER_VERSION:
            msg = f"Firmware has unsupported header version {header_version}"
            raise ElgatoFirmwareError(msg)

        if header[4:45] != HEADER_IDENTIFIER:
            msg = "Firmware is missing the Elgato identification string"
            raise ElgatoFirmwareError(msg)

        major, minor, patch, build_number = struct.unpack_from("<HHHH", header, 46)

        return cls(
            board_type=header[45],
            build_number=build_number,
            version=f"{major}.{minor}.{patch}",
        )


@dataclass(frozen=True)
class FirmwareImage(FirmwareVersion):
    """A parsed and verified Elgato firmware image.

    Attributes
    ----------
        data: The complete image, header included, as the device wants it.

    """

    data: bytes = field(repr=False)

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        """Parse and verify a firmware image.

        Args:
        ----
            data: The complete firmware file, header included.

        Returns:
        -------
            A FirmwareImage, safe to hand to an Elgato Light device.

        Raises:
        ------
            ElgatoFirmwareError: The data is not an Elgato firmware image, or
                its signature does not hold up.

        """
        header = FirmwareVersion.from_header(data)

        (payload_size,) = struct.unpack_from("<I", data, 54)
        payload_offset, reserved, signing_key_id = struct.unpack_from("<HHH", data, 58)

        # A device reads a fixed header and rejects a non-zero reserved field.
        # Accepting either here would mean verifying a signature over bytes the
        # device never hashes, which is worse than not checking at all.
        if payload_offset != HEADER_SIZE:
            msg = f"Firmware payload starts at {payload_offset}, expected {HEADER_SIZE}"
            raise ElgatoFirmwareError(msg)

        if reserved:
            msg = f"Firmware has a non-zero reserved field ({reserved})"
            raise ElgatoFirmwareError(msg)

        if payload_offset + payload_size != len(data):
            msg = (
                f"Firmware declares {payload_offset + payload_size} bytes "
                f"but is {len(data)} bytes"
            )
            raise ElgatoFirmwareError(msg)

        if (key := SIGNING_KEYS.get(signing_key_id)) is None:
            msg = f"Firmware is signed with unknown key {signing_key_id}"
            raise ElgatoFirmwareError(msg)

        # The signature covers a digest of the header up to the signature
        # itself, followed by the payload. Not the file as a whole.
        payload = data[payload_offset : payload_offset + payload_size]
        digest = hashlib.sha512(data[:64] + payload).digest()

        try:
            Ed25519PublicKey.from_public_bytes(key).verify(data[64:128], digest)
        except InvalidSignature as exception:
            msg = "Firmware signature is invalid"
            raise ElgatoFirmwareError(msg) from exception

        return cls(
            board_type=header.board_type,
            build_number=header.build_number,
            version=header.version,
            data=data,
        )
