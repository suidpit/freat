import json
from pathlib import Path
import pytest
from pytest_mock import MockFixture
from unittest.mock import AsyncMock

import subprocess

from freat_server.hub import Hub

TARGET_PROGRAM_DIR = Path(__file__).parent /  "target_program"


@pytest.fixture(scope="module")
def compiled_executable():
    compile_command = "gcc -o target target.c"
    try:
        subprocess.run(compile_command.split(), cwd=TARGET_PROGRAM_DIR, check=True)
    except Exception as e:
        pytest.fail(f"Compilation failed: {e}")

    yield TARGET_PROGRAM_DIR / "target"
    Path(TARGET_PROGRAM_DIR / "target").unlink(missing_ok=True)

@pytest.fixture(scope="function")
def target_process(compiled_executable):
    process = subprocess.Popen([compiled_executable], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
    yield process
    if process.poll() is None:
        try:
            process.terminate()
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()


@pytest.mark.asyncio
async def test_hello(target_process: subprocess.Popen, mocker: MockFixture):
    mock_websocket = mocker.AsyncMock()
    hub = Hub()
    await hub.attach(target_process.pid)
    await hub.handle_message(mock_websocket, json.dumps({"command": "hello", "uuid": "1234567890"}))
    mock_websocket.send.assert_awaited_once_with(json.dumps({"event": "hello", "data": "hello from the agent!", "uuid": "1234567890"}))

@pytest.mark.asyncio
async def test_hello_not_attached(target_process: subprocess.Popen, mocker: MockFixture):
    mock_websocket = mocker.AsyncMock()
    hub = Hub()
    await hub.handle_message(mock_websocket, json.dumps({"command": "hello", "uuid": "1234567890"}))
    mock_websocket.send.assert_awaited_once_with(json.dumps({"event": "error", "data": "Agent is not initialized", "uuid": "1234567890"}))
