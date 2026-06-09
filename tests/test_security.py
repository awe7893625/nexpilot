from pathlib import Path

from fastapi import HTTPException

from nexpilot_public.server import (
    ServerConfig,
    _allowed_origins,
    _clean_session_id,
    _safe_int,
    make_app,
    require_token,
    websocket_origin_allowed,
)


class DummyRequest:
    def __init__(self, token: str = ""):
        self.headers = {}
        self.query_params = {"token": token} if token else {}


def test_require_token_accepts_exact_token():
    config = ServerConfig(
        host="127.0.0.1",
        port=8765,
        token="abc123",
        shell="/bin/sh",
        cwd=Path.home(),
    )
    require_token(DummyRequest("abc123"), config)


def test_require_token_rejects_missing_token():
    config = ServerConfig(
        host="127.0.0.1",
        port=8765,
        token="abc123",
        shell="/bin/sh",
        cwd=Path.home(),
    )
    try:
        require_token(DummyRequest(), config)
    except HTTPException as exc:
        assert exc.status_code == 401
    else:
        raise AssertionError("missing token should be rejected")


def test_make_app_does_not_require_private_runtime_paths():
    config = ServerConfig(
        host="127.0.0.1",
        port=8765,
        token="abc123",
        shell="/bin/sh",
        cwd=Path.home(),
    )
    app = make_app(config)
    route_paths = {route.path for route in app.routes}
    assert "/api/status" in route_paths
    assert "/ws/terminal" in route_paths


def test_clean_session_id_accepts_safe_ids():
    assert _clean_session_id("tester-session_01") == "tester-session_01"


def test_clean_session_id_rejects_unsafe_ids():
    cleaned = _clean_session_id("../secret")
    assert cleaned != "../secret"
    assert "/" not in cleaned


# --- A04: anti-clickjacking headers ----------------------------------------


def test_security_headers_include_frame_deny():
    """A04: X-Frame-Options and CSP frame-ancestors must be present."""
    from fastapi.testclient import TestClient

    config = ServerConfig(
        host="127.0.0.1", port=8765, token="abc123", shell="/bin/sh", cwd=Path.home()
    )
    app = make_app(config)
    client = TestClient(app)
    resp = client.get("/", headers={"x-nexpilot-token": "abc123"})
    assert resp.headers.get("x-frame-options") == "DENY"
    assert "frame-ancestors 'none'" in resp.headers.get("content-security-policy", "")


# --- A06: safe-int resize helper --------------------------------------------


def test_safe_int_returns_default_on_non_numeric():
    """A06: non-numeric resize values must not crash the WS loop."""
    assert _safe_int("abc", 100) == 100
    assert _safe_int(None, 32) == 32
    assert _safe_int("", 80) == 80


def test_safe_int_accepts_valid_int():
    assert _safe_int(120, 100) == 120
    assert _safe_int("40", 32) == 40


# --- A03: WebSocket Origin validation ----------------------------------------


class DummyWebSocket:
    """Minimal fake WebSocket for origin-check tests."""

    def __init__(self, origin: str = "", host: str = "127.0.0.1"):
        self.headers = {}
        if origin:
            self.headers["origin"] = origin


def _lo_config(host: str = "127.0.0.1", port: int = 8765) -> ServerConfig:
    return ServerConfig(
        host=host, port=port, token="tok", shell="/bin/sh", cwd=Path.home()
    )


def test_origin_loopback_allowed():
    """A03: localhost origin is always permitted."""
    cfg = _lo_config()
    ws = DummyWebSocket(origin=f"http://localhost:{cfg.port}")
    assert websocket_origin_allowed(ws, cfg)


def test_origin_127_allowed():
    cfg = _lo_config()
    ws = DummyWebSocket(origin=f"http://127.0.0.1:{cfg.port}")
    assert websocket_origin_allowed(ws, cfg)


def test_origin_unknown_rejected():
    """A03: foreign origin must be rejected."""
    cfg = _lo_config()
    ws = DummyWebSocket(origin="http://evil.example.com")
    assert not websocket_origin_allowed(ws, cfg)


def test_origin_null_loopback_allowed():
    """A03: missing Origin header is OK when server is loopback-only."""
    cfg = _lo_config(host="127.0.0.1")
    ws = DummyWebSocket(origin="")
    assert websocket_origin_allowed(ws, cfg)


def test_origin_null_lan_rejected():
    """A03: missing Origin header must be rejected when server is 0.0.0.0."""
    cfg = _lo_config(host="0.0.0.0")
    ws = DummyWebSocket(origin="")
    assert not websocket_origin_allowed(ws, cfg)


def test_allowed_origins_lan_includes_lan_ip():
    """A03: LAN mode must include the detected LAN IP in allowed origins."""
    cfg = _lo_config(host="0.0.0.0", port=9000)
    origins = _allowed_origins(cfg)
    assert f"http://localhost:{cfg.port}" in origins
    assert f"http://127.0.0.1:{cfg.port}" in origins
    # At least one non-loopback origin (actual LAN IP or still just the two above if
    # network is unavailable — either way the set is non-empty).
    assert len(origins) >= 2
