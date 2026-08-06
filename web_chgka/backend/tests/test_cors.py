import asyncio
import json

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


async def _socketio_handshake(origin):
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

    await main.app(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/socket.io/",
            "raw_path": b"/socket.io/",
            "query_string": b"EIO=4&transport=polling",
            "headers": [
                (b"origin", origin.encode("ascii")),
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
    body = b"".join(
        message.get("body", b"")
        for message in sent
        if message["type"] == "http.response.body"
    )
    if response_start["status"] == 200 and body.startswith(b"0{"):
        sid = json.loads(body[1:])["sid"]
        engineio_socket = main.sio.eio.sockets.pop(sid)
        await engineio_socket.close(wait=False, abort=True)
    return response_start["status"], headers, body


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


def test_socketio_origin_gate_accepts_only_configured_origin():
    async def run_checks():
        allowed = await _socketio_handshake("http://localhost:5173")
        denied = await _socketio_handshake("http://localhost:5174")
        return allowed, denied

    (
        (allowed_status, _allowed_headers, allowed_body),
        (denied_status, denied_headers, denied_body),
    ) = asyncio.run(run_checks())

    assert allowed_status == 200
    assert allowed_body.startswith(b"0{")
    assert denied_status == 400
    assert "access-control-allow-origin" not in denied_headers
    assert b"not an accepted origin" in denied_body
