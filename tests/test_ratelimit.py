"""Pure-logic tests for the in-process rate limiter (deterministic via an injected clock)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from avix.api import ratelimit

# Small, explicit limits so the trigger points are obvious (and prove config-driven behaviour).
CFG = {"trust_forwarded_for": False, "limits": {
    "checker": {"limit": 3, "window_seconds": 60},
    "export":  {"limit": 2, "window_seconds": 60},
}}


def setup_function(_):
    ratelimit.configure(CFG)   # inject test config + clear counters


def teardown_module(_):
    ratelimit.configure(None)  # restore file-backed config for any later importers


def test_under_threshold_allowed():
    for i in range(3):
        allowed, retry = ratelimit.check("checker", "1.1.1.1", now=100 + i)
        assert allowed and retry == 0


def test_over_threshold_blocked_with_retry_after():
    for i in range(3):
        ratelimit.check("checker", "ip", now=100 + i)
    allowed, retry = ratelimit.check("checker", "ip", now=103)
    assert allowed is False
    assert retry >= 1   # a positive Retry-After hint


def test_window_reset_reallows():
    for i in range(3):
        ratelimit.check("checker", "ip", now=100 + i)
    assert ratelimit.check("checker", "ip", now=103)[0] is False
    # once the window has fully passed, the key is allowed again
    assert ratelimit.check("checker", "ip", now=100 + 61)[0] is True


def test_keys_are_per_ip_independent():
    for i in range(3):
        ratelimit.check("checker", "A", now=100 + i)
    assert ratelimit.check("checker", "A", now=103)[0] is False
    assert ratelimit.check("checker", "B", now=103)[0] is True   # different IP, fresh budget


def test_routes_are_independent():
    for i in range(3):
        ratelimit.check("checker", "ip", now=100 + i)
    assert ratelimit.check("checker", "ip", now=103)[0] is False
    assert ratelimit.check("export", "ip", now=103)[0] is True   # different route, own budget


def test_config_driven_limit():
    # export limit is 2 in this config -> 3rd request blocks (proves not hard-coded)
    assert ratelimit.check("export", "ip", now=100)[0] is True
    assert ratelimit.check("export", "ip", now=100)[0] is True
    assert ratelimit.check("export", "ip", now=100)[0] is False


def test_unknown_route_is_unlimited():
    for _ in range(50):
        assert ratelimit.check("not-configured", "ip", now=100)[0] is True
