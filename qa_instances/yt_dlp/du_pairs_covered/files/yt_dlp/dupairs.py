from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import dataclass

from .utils.networking import normalize_url


_WORD_RE = re.compile(r"[A-Za-z]{2,}")
_NUM_RE = re.compile(r"\d+")


@dataclass(frozen=True)
class _Msg:
    url: str
    words: tuple[str, ...]
    nums: tuple[int, ...]


def analyze_payload(payload: str) -> int:
    """
    Intentionally branchy function to generate dynamic def-use pairs.
    """
    raw = payload.strip()
    url = normalize_url("https://example.com/" + raw.replace(" ", "%20"))

    words = tuple(w.lower() for w in _WORD_RE.findall(raw))
    nums = tuple(int(n) for n in _NUM_RE.findall(raw))
    msg = _Msg(url=url, words=words, nums=nums)

    score = 0
    seen = set()

    for i, w in enumerate(msg.words):
        if w in seen:
            score -= i
            continue
        seen.add(w)

        h = hashlib.blake2s((w + msg.url).encode("utf-8"), digest_size=8).digest()
        chunk = int.from_bytes(h[:2], "big")
        score += (chunk % (i + 3))

        if (chunk & 0b111) == 0:
            score ^= (chunk >> 3)
        elif (chunk & 0b11) == 0b11:
            score += len(w) * 7
        else:
            score -= len(msg.url) % 13

    total = 1
    for n in msg.nums:
        total = (total * (n + 1)) % 65521

    blob = json.dumps({"u": msg.url, "w": msg.words, "n": msg.nums, "s": score, "t": total}, sort_keys=True).encode("utf-8")
    b64 = base64.urlsafe_b64encode(blob).rstrip(b"=")

    digest = hashlib.sha256(b64).digest()
    a = int.from_bytes(digest[:4], "big")
    b = int.from_bytes(digest[4:8], "big")

    if (a ^ b) & 1:
        out = (a + 3 * b + score) & 0xFFFFFFFF
    else:
        out = (b + 5 * a - total) & 0xFFFFFFFF

    # Re-definitions to make DU harder
    score = (score + (out & 0xFF)) % 997
    total = (total + (out >> 8)) % 1009

    return (out ^ (score << 10) ^ (total << 1)) % 65536

