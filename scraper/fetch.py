import time
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from scraper.config import FROM_HEADER, RATE_LIMIT_SECONDS, USER_AGENT


class RobotsBlockedError(Exception):
    pass


_robots_cache: dict[str, RobotFileParser] = {}
_last_request_at: dict[str, float] = {}
_crawl_delay: dict[str, float] = {}


def _headers() -> dict[str, str]:
    return {"User-Agent": USER_AGENT, "From": FROM_HEADER}


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def _robots_for(origin: str) -> RobotFileParser:
    if origin in _robots_cache:
        return _robots_cache[origin]

    rp = RobotFileParser()
    robots_url = f"{origin}/robots.txt"
    try:
        resp = httpx.get(robots_url, headers=_headers(), timeout=15, follow_redirects=True)
    except httpx.HTTPError:
        rp.parse([])
    else:
        if resp.status_code == 200:
            rp.parse(resp.text.splitlines())
            delay = rp.crawl_delay(USER_AGENT) or rp.crawl_delay("*")
            if delay:
                _crawl_delay[origin] = float(delay)
        else:
            rp.parse([])

    _robots_cache[origin] = rp
    return rp


def _rate_limit(origin: str) -> None:
    delay = max(RATE_LIMIT_SECONDS, _crawl_delay.get(origin, 0.0))
    last = _last_request_at.get(origin)
    if last is not None:
        elapsed = time.monotonic() - last
        if elapsed < delay:
            time.sleep(delay - elapsed)
    _last_request_at[origin] = time.monotonic()


def fetch_with_cache(url: str, cache_path: Path, refetch: bool = False) -> str:
    if cache_path.exists() and not refetch:
        return cache_path.read_text(encoding="utf-8")

    origin = _origin(url)
    rp = _robots_for(origin)
    if not rp.can_fetch(USER_AGENT, url):
        raise RobotsBlockedError(f"robots.txt disallows {url}")

    _rate_limit(origin)
    resp = httpx.get(url, headers=_headers(), timeout=30, follow_redirects=True)
    resp.raise_for_status()

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(resp.text, encoding="utf-8")
    return resp.text
