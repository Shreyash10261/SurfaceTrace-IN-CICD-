"""Test helpers and test data generators for SurfaceTrace-IN.

Owned by Shreyash.
Provides make_valid_v3() as specified in the blueprint reference code.
"""
from __future__ import annotations

import base64
import hashlib
import os


def make_valid_v3() -> str:
    """Generate a random cryptographically valid Tor v3 onion address for testing."""
    key, version = os.urandom(32), b"\x03"
    checksum = hashlib.sha3_256(b".onion checksum" + key + version).digest()[:2]
    return base64.b32encode(key + checksum + version).decode().lower() + ".onion"


def make_tampered_v3(valid_address: str) -> str:
    """Tamper with a valid v3 address to invalidate its checksum."""
    name = valid_address.removesuffix(".onion")
    # Invert one character in the public key area
    chars = list(name)
    chars[5] = "a" if chars[5] != "a" else "b"
    return "".join(chars) + ".onion"

