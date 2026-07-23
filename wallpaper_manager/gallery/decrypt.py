"""Decrypt helpers ported from WallpaperGallery (wallpaper.061129.xyz blob format)."""

from __future__ import annotations

import base64

DECRYPT_MAP = {
    "0": "5",
    "1": "6",
    "2": "7",
    "3": "8",
    "4": "9",
    "5": "0",
    "6": "1",
    "7": "2",
    "8": "3",
    "9": "4",
    "Q": "A",
    "W": "B",
    "E": "C",
    "R": "D",
    "T": "E",
    "Y": "F",
    "U": "G",
    "I": "H",
    "O": "I",
    "P": "J",
    "A": "K",
    "S": "L",
    "D": "M",
    "F": "N",
    "G": "O",
    "H": "P",
    "J": "Q",
    "K": "R",
    "L": "S",
    "Z": "T",
    "X": "U",
    "C": "V",
    "V": "W",
    "B": "X",
    "N": "Y",
    "M": "Z",
    "q": "a",
    "w": "b",
    "e": "c",
    "r": "d",
    "t": "e",
    "y": "f",
    "u": "g",
    "i": "h",
    "o": "i",
    "p": "j",
    "a": "k",
    "s": "l",
    "d": "m",
    "f": "n",
    "g": "o",
    "h": "p",
    "j": "q",
    "k": "r",
    "l": "s",
    "z": "t",
    "x": "u",
    "c": "v",
    "v": "w",
    "b": "x",
    "n": "y",
    "m": "z",
    "-": "+",
    "_": "/",
    ".": "=",
}

ENCRYPT_MAP = {v: k for k, v in DECRYPT_MAP.items()}


def decrypt_blob(encrypted: str) -> str:
    """Decrypt a v1.* blob into a UTF-8 JSON string."""
    prefix = "v1."
    if not encrypted.startswith(prefix):
        raise ValueError("blob must start with v1.")
    data = encrypted[len(prefix) :]
    reversed_data = data[::-1]
    mapped = "".join(DECRYPT_MAP.get(c, c) for c in reversed_data)
    return base64.b64decode(mapped).decode("utf-8")


def encrypt_blob(plain_json: str) -> str:
    """Test helper — inverse of decrypt_blob."""
    mapped = base64.b64encode(plain_json.encode("utf-8")).decode("ascii")
    remapped = "".join(ENCRYPT_MAP.get(c, c) for c in mapped)
    return "v1." + remapped[::-1]
