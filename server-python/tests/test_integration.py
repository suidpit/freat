import json
from pathlib import Path
import pytest
from pytest_mock import MockFixture
import pytest_asyncio
from unittest.mock import AsyncMock

import subprocess

from freat_server.hub import Hub, DataType, ScanType

@pytest_asyncio.fixture(scope="function")
async def test_hub():
    idle_proc = subprocess.Popen(["cat"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    hub = Hub()
    await hub.attach(idle_proc.pid)
    yield hub
    idle_proc.kill()

@pytest.mark.asyncio
async def test_hello(test_hub: Hub, mocker: MockFixture):
    assert test_hub.agent
    mock_websocket = mocker.AsyncMock()
    await test_hub.handle_message(mock_websocket, json.dumps({"command": "hello", "uuid": "1234567890"}))
    mock_websocket.send.assert_awaited_once_with(json.dumps({"event": "hello", "data": "hello from the agent!", "uuid": "1234567890"}))

@pytest.mark.timeout(5)
@pytest.mark.asyncio
async def test_scan(test_hub: Hub, mocker: MockFixture):
    assert test_hub.agent
    assert await test_hub.agent.run_scan_test()

@pytest.mark.asyncio
async def test_enumerate_processes(test_hub: Hub, mocker: MockFixture):
    assert test_hub.agent
    mock_websocket = mocker.AsyncMock()
    test_proc = subprocess.Popen(["cat"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    await test_hub.handle_message(mock_websocket, json.dumps({"command": "list-processes", "uuid": "1234567890"}))
    sent_data = mock_websocket.send.await_args[0][0]
    assert any(proc["pid"] == test_proc.pid for proc in json.loads(sent_data)["data"])
