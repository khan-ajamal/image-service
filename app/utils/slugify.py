"""Filename slugification utility."""

from __future__ import annotations

import re
import unicodedata
from pathlib import PurePosixPath


def slugify(text: str) -> str:
    """Convert *text* to a URL-friendly slug.

    * Unicode → ASCII (via NFKD normalisation)
    * Lower-cased
    * Non-alphanumeric characters (except ``-``) replaced with ``-``
    * Consecutive hyphens collapsed
    * Leading / trailing hyphens stripped
    """
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")


def slugify_filename(filename: str) -> str:
    """Slugify a filename while preserving its extension.

    >>> slugify_filename("My Vacation Photo (2).PNG")
    'my-vacation-photo-2.png'
    """
    p = PurePosixPath(filename)
    # PurePosixPath(".png") has stem=".png" and suffix="", so handle dot-files
    if p.suffix:
        name = slugify(p.stem)
        ext = p.suffix.lower()
    elif p.stem.startswith("."):
        # Dot-file with no real stem (e.g. ".png") — treat everything after dot as ext
        name = ""
        ext = p.stem.lower()
    else:
        name = slugify(p.stem)
        ext = ""

    if not name:
        name = "untitled"
    return f"{name}{ext}"
