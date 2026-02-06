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
