from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import dataclass

from .utils.networking import normalize_url


_TOKEN_RE = re.compile(r"(?i)\\btoken=([a-z0-9_-]{8,})\\b")


@dataclass(frozen=True)
class _Context:
    token: str
    url: str
    salt: str


class BaseHandler:
    def process(self, ctx: _Context) -> int:  # pragma: no cover
        raise NotImplementedError


class _JsonishHandler(BaseHandler):
    def process(self, ctx: _Context) -> int:
        payload = json.dumps({"t": ctx.token, "u": ctx.url, "s": ctx.salt}, sort_keys=True).encode("utf-8")
        digest = hashlib.sha256(payload).digest()
        return int.from_bytes(digest[:2], "big")


class _B64Handler(BaseHandler):
    def process(self, ctx: _Context) -> int:
        blob = f"{ctx.salt}:{ctx.token}:{ctx.url}".encode("utf-8")
        b = base64.urlsafe_b64encode(blob).rstrip(b"=")
        digest = hashlib.sha1(b).digest()
        return int.from_bytes(digest[-2:], "big")


class _UrlHandler(BaseHandler):
    def process(self, ctx: _Context) -> int:
        u = normalize_url(ctx.url)
        digest = hashlib.md5((u + ctx.token + ctx.salt).encode("utf-8")).digest()
        return int.from_bytes(digest[5:7], "big")


def _select_handler(ctx: _Context) -> BaseHandler:
    # A deliberately non-trivial, stable dispatch decision:
    # - Extract a mixed-source score (token/url/salt) using multiple encodings.
    # - Use bit tests + modular arithmetic to choose a concrete handler.
    t = ctx.token.encode("utf-8")
    u = ctx.url.encode("utf-8")
    s = ctx.salt.encode("utf-8")

    h1 = hashlib.blake2s(t + b"|" + s, digest_size=8).digest()
    h2 = hashlib.blake2b(u + b"|" + s, digest_size=8).digest()
    score = int.from_bytes(h1, "big") ^ int.from_bytes(h2, "big")

    if (score & 0b10101) == 0b00101:
        return _UrlHandler()
    if (score % 7) in (0, 3, 5):
        return _B64Handler()
    return _JsonishHandler()


def run_dispatch(payload: str) -> int:
    """
    Entry point for QA test. The question asks about the dynamic-dispatch target
    of the `.process(...)` call inside this function.
    """
    m = _TOKEN_RE.search(payload)
    token = (m.group(1) if m else "missingtok").lower()

    # Normalize and salt in a way that is deterministic but not obviously tied
    # to one handler branch without careful reasoning.
    url = normalize_url("https://example.com/" + payload.strip().replace(" ", "%20"))
    salt = hashlib.sha256((token + "::" + url).encode("utf-8")).hexdigest()[:12]

    ctx = _Context(token=token, url=url, salt=salt)
    handler = _select_handler(ctx)

    # IMPORTANT: this is the dynamic-dispatch call site referenced by the QA.
    out = handler.process(ctx)

    # Post-mix the result so the return value doesn't reveal the chosen handler.
    return (out * 257 + len(ctx.url) + len(ctx.token)) % 65536
