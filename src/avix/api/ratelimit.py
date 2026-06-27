"""Minimal in-process rate limiter (stdlib only — no new dependency).

Per-(route, client-IP) sliding-window log: each key keeps a deque of recent request
timestamps; a request is allowed if fewer than `limit` remain inside `window_seconds`.

Caveats (documented; future gates): the counter lives in ONE process and RESETS ON
RESTART; it is not shared across instances. Client IP is read from request.client.host;
X-Forwarded-For is NOT trusted unless config sets trust_forwarded_for (off by default)."""
import time
import threading
from collections import deque, defaultdict
from pathlib import Path
import yaml
from fastapi import Request, HTTPException

from .. import config

_LOCK = threading.Lock()
_HITS = defaultdict(deque)   # (route_key, client_ip) -> deque[float timestamps]
_CFG = None                  # cached config dict (None => (re)load from file)


def load_limits(path=None) -> dict:
    p = Path(path) if path else (config.CONFIG_DIR / "ratelimit.yaml")
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _cfg() -> dict:
    global _CFG
    if _CFG is None:
        _CFG = load_limits()
    return _CFG


def configure(cfg):
    """Inject a config dict (tests). Pass None to reload from file. Also clears counters."""
    global _CFG
    _CFG = cfg
    reset()


def reset():
    """Clear all counters (tests / between smoke sub-blocks)."""
    with _LOCK:
        _HITS.clear()


def _client_ip(request: Request) -> str:
    cfg = _cfg()
    if cfg.get("trust_forwarded_for"):
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check(route_key: str, client_ip: str, now: float | None = None):
    """Return (allowed: bool, retry_after_seconds: int). Unknown routes are unlimited."""
    rule = _cfg().get("limits", {}).get(route_key)
    if not rule:
        return True, 0
    limit = int(rule["limit"])
    window = float(rule["window_seconds"])
    t = time.monotonic() if now is None else now
    key = (route_key, client_ip)
    with _LOCK:
        dq = _HITS[key]
        cutoff = t - window
        while dq and dq[0] <= cutoff:
            dq.popleft()
        if len(dq) >= limit:
            retry = int(dq[0] + window - t) + 1
            return False, max(retry, 1)
        dq.append(t)
        if not dq:                 # never empty here, but keep the map from growing on edge
            _HITS.pop(key, None)
        return True, 0


def rate_limit(route_key: str):
    """FastAPI dependency factory. On limiter-internal error, fail OPEN for availability —
    the export route stays protected by its token regardless, so this never weakens export."""
    def dependency(request: Request):
        try:
            allowed, retry = check(route_key, _client_ip(request))
        except Exception:
            return  # fail open
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please slow down and try again shortly.",
                headers={"Retry-After": str(retry)},
            )
    return dependency
