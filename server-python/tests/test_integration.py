import asyncio
import ctypes
import json
import subprocess

import pytest
import pytest_asyncio
from pytest_mock import MockFixture

from freat_server.config import TargetConfig
from freat_server.hub import Hub

test_config = TargetConfig()


@pytest_asyncio.fixture(scope="function")
async def test_hub():
    hub = Hub(test_config)
    await hub.attach(0)
    yield hub


@pytest.mark.asyncio
async def test_hello(test_hub: Hub, mocker: MockFixture):
    assert test_hub.agent
    mock_websocket = mocker.AsyncMock()
    await test_hub.handle_message(
        mock_websocket, json.dumps({"command": "hello", "uuid": "1234567890"})
    )
    mock_websocket.send.assert_awaited_once_with(
        json.dumps(
            {"event": "hello", "data": "hello from the agent!", "uuid": "1234567890"}
        )
    )


@pytest.mark.timeout(120)
@pytest.mark.asyncio
async def test_scan(test_hub: Hub, mocker: MockFixture):
    assert test_hub.agent
    assert await test_hub.agent.run_scan_test()


@pytest.mark.asyncio
async def test_enumerate_processes(test_hub: Hub, mocker: MockFixture):
    assert test_hub.agent
    mock_websocket = mocker.AsyncMock()
    test_proc = subprocess.Popen(["cat"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    await test_hub.handle_message(
        mock_websocket, json.dumps({"command": "list-processes", "uuid": "1234567890"})
    )
    sent_data = mock_websocket.send.await_args[0][0]
    assert any(proc["pid"] == test_proc.pid for proc in json.loads(sent_data)["data"])


@pytest.mark.timeout(30)
@pytest.mark.asyncio
async def test_watchpoint_write(test_hub: Hub, mocker: MockFixture):
    assert test_hub.agent

    # the test is performed against the python interpreter (pid 0) so we can use the ctypes
    val = ctypes.c_uint32(42)
    addr = hex(ctypes.addressof(val))

    hit_event = asyncio.Event()
    hit_data = {}

    async def capture_send(message_str):
        msg = json.loads(message_str)
        if msg.get("event") == "watchpoint-hit":
            hit_data.update(msg["data"])
            hit_event.set()

    mock_client = mocker.AsyncMock()
    mock_client.send = mocker.AsyncMock(side_effect=capture_send)
    test_hub.register_client(mock_client)

    # DataType.U32 = 2
    await test_hub.agent.set_watchpoint(addr, 2, "w")

    # this should trigger the watchpoint
    val.value = 99

    await asyncio.wait_for(hit_event.wait(), timeout=10)

    assert hit_data["address"] == addr
    assert hit_data["operation"] == "write"
    assert "pc" in hit_data
    assert "backtrace" in hit_data
    assert "disassembly" in hit_data
    assert len(hit_data["disassembly"]) > 0

    test_hub.unregister_client(mock_client)
