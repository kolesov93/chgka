import asyncio

import main


async def _preflight(origin):
    sent = []
    received = False

    async def receive():
        nonlocal received
        if received:
            return {"type": "http.disconnect"}
        received = True
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    await main.fastapi_app(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "OPTIONS",
            "scheme": "http",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": [
                (b"origin", origin.encode("ascii")),
                (b"access-control-request-method", b"GET"),
            ],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        },
        receive,
        send,
    )
    response_start = next(
        message for message in sent if message["type"] == "http.response.start"
    )
    headers = {
        name.decode("latin-1"): value.decode("latin-1")
        for name, value in response_start["headers"]
    }
    return response_start["status"], headers


def test_fastapi_cors_accepts_only_configured_origin():
    allowed_status, allowed_headers = asyncio.run(
        _preflight("http://localhost:5173")
    )
    denied_status, denied_headers = asyncio.run(
        _preflight("http://localhost:5174")
    )

    assert allowed_status == 200
    assert allowed_headers["access-control-allow-origin"] == "http://localhost:5173"
    assert denied_status == 400
    assert "access-control-allow-origin" not in denied_headers


def test_socketio_uses_the_same_origin_allowlist():
    assert main.sio.eio.cors_allowed_origins == list(main.APP_CONFIG.allowed_origins)
