"""Security headers on every response, a request-size cap, and a per-address limit for the API."""
import base64
import hashlib
import json
import re
from pathlib import Path

from starlette.datastructures import MutableHeaders

from .ratelimit import api_limiter

_INLINE_SCRIPT = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", re.S | re.I)


def inline_script_hashes(dist: Path) -> list[str]:
    """CSP hashes for the small inline scripts in the built pages, so no other inline script can run."""
    found = set()
    for page in dist.rglob("*.html"):
        for body in _INLINE_SCRIPT.findall(page.read_text(encoding="utf-8")):
            if body.strip():
                text = body.replace("\r\n", "\n").replace("\r", "\n")  # browsers hash the parsed text
                found.add("'sha256-" + base64.b64encode(hashlib.sha256(text.encode()).digest()).decode() + "'")
    return sorted(found)


def build_csp(script_hashes: list[str], connect_extra: list[str], production: bool) -> str:
    parts = [
        "default-src 'self'",
        "script-src " + " ".join(["'self'", *script_hashes]),
        # Vue sets inline style values; Google Fonts serves the brand fonts' CSS
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com",
        "img-src 'self' data: blob:",
        "connect-src " + " ".join(["'self'", *connect_extra]),
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
    if production:
        parts.append("upgrade-insecure-requests")
    return "; ".join(parts)


class SecurityMiddleware:
    def __init__(self, app, *, csp: str, hsts: bool, max_body: int):
        self.app = app
        self.csp = csp
        self.hsts = hsts
        self.max_body = max_body

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path: str = scope["path"]
        is_api = path.startswith("/api/")

        if is_api and path != "/api/health":
            ip = (scope.get("client") or ("unknown", 0))[0]
            if not api_limiter.hit(ip):
                return await self._reject(send, 429, "Too many requests from your network. Wait a minute and try again.")

        if scope["method"] in ("POST", "PUT", "PATCH", "DELETE"):
            headers = dict(scope["headers"])
            length = headers.get(b"content-length")
            if length is not None:
                try:
                    if int(length) > self.max_body:
                        return await self._reject(send, 413, "That request is too large.")
                except ValueError:
                    return await self._reject(send, 400, "Bad request.")
            elif headers.get(b"transfer-encoding"):
                # a streamed body could dodge the size cap; every real browser sends Content-Length
                return await self._reject(send, 411, "Please send a Content-Length header.")

        https = scope.get("scheme") == "https"

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                h = MutableHeaders(scope=message)
                h["X-Content-Type-Options"] = "nosniff"
                h["X-Frame-Options"] = "DENY"
                h["Referrer-Policy"] = "strict-origin-when-cross-origin"
                h["Cross-Origin-Opener-Policy"] = "same-origin"
                h["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=(), usb=(), browsing-topics=()"
                if path != "/api/docs":  # the local-only API docs page loads its viewer from a CDN
                    h["Content-Security-Policy"] = self.csp
                if self.hsts or https:
                    h["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
                if is_api:
                    h["Cache-Control"] = "no-store"
                elif path.endswith("/") or path.endswith(".html"):
                    h["Cache-Control"] = "no-cache"
                if is_api or path.startswith(("/admin", "/seller")):
                    h["X-Robots-Tag"] = "noindex, nofollow"
            await send(message)

        await self.app(scope, receive, send_with_headers)

    @staticmethod
    async def _reject(send, status: int, detail: str):
        body = json.dumps({"detail": detail}).encode()
        await send({"type": "http.response.start", "status": status, "headers": [
            (b"content-type", b"application/json"), (b"content-length", str(len(body)).encode()),
            (b"x-content-type-options", b"nosniff"), (b"cache-control", b"no-store"),
        ]})
        await send({"type": "http.response.body", "body": body})
