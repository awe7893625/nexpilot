from pathlib import Path

from fastapi import HTTPException

from nexpilot_public.server import ServerConfig, make_app, require_token


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
