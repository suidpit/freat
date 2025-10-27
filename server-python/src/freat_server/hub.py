import asyncio
import json

import frida
from importlib import resources
from enum import Enum

from frida.core import Script, ScriptExportsAsync
from typing import Any, Awaitable, Protocol

class ScanSize(Enum):
    U8 = 0
    U16 = 1
    U32 = 2
    U64 = 3
    FLOAT = 4
    DOUBLE = 5

class ScanType(Enum):
    EXACT = 0
    LESS_THAN = 1
    GREATER_THAN = 2

class Agent(Protocol):
    """
    Defines the interface for the Frida agent script.
    """
    def hello(self) -> Awaitable[Any]: ...
    def first_scan(self, value: int, scan_size: int, scan_type: int) -> Awaitable[int]: ...
    def next_scan(self, value: int, scan_size: int, scan_type: int) -> Awaitable[int]: ...
    def run_scan_test(self) -> Awaitable[bool]: ...

class Hub:
    """
    The console. Manages the Frida session, the application state (watch/freeze lists),
    and all the connected UI clients.
    """

    def __init__(self, user_config: dict = {}):
        self.session = None
        self.agent: Agent | None = None
        # TODO: implement support for other devices
        self.device = frida.get_local_device()
        self.clients = set()
        self.watch_list = {}
        self.freeze_list = {}
        self.polling_task: asyncio.Task | None = None
        self.user_config = user_config
        self.agent_js = self._load_agent_script()
        self.loop = asyncio.get_event_loop()

    def _load_agent_script(self) -> str:
        print("Loading agent script...")
        try:
            return (resources.files("freat_server") / "_agent.js").read_text()
        except FileNotFoundError:
            print("=" * 50)
            print("CRITICAL: Agent script not found.")
            print("Please check the installation and try again.")
            print("=" * 50)
            raise FileNotFoundError("Agent script not found.")
        except Exception as e:
            print(f"Error loading agent script: {e}")
            raise

    def register_client(self, client):
        print(f"New client connected ({len(self.clients) + 1} total)")
        self.clients.add(client)

    def unregister_client(self, client):
        self.clients.remove(client)
        print(f"Client disconnected ({len(self.clients)} remaining)")

    async def broadcast(self, message: dict):
        """Sends a JSON message to all connected clients."""
        await asyncio.gather(
            *[client.send(json.dumps(message)) for client in self.clients]
        )

    # Core Frida Logic

    async def attach(self, pid: int):
        """Attaches to a new process. Right now, it only supports the local device."""
        print(f"Attaching to {pid}...")
        if not self.agent_js:
            await self.broadcast({"event": "error", "data": "Agent script not found."})
            return

        try:
            # If we're already attached, we detach.
            if self.session:
                self.detach()

            self.session = frida.attach(pid)
            self.session.on(
                "detached", lambda reason: self.detach_sync(reason)
            )

            script = self.session.create_script(self.agent_js)
            script.on("message", lambda message, data: print(message, data))
            script.load()
            self.agent = script.exports_async
            self.polling_task = asyncio.create_task(self._poll_loop())
            await self.broadcast({"event": "status", "data": f"Attached to {pid}"})
            print(f"Attached to {pid}.")
        except Exception as e:
            print(f"Error attaching to {pid}: {e}")
            await self.broadcast(
                {"event": "error", "data": f"Error attaching to {pid}: {e}"}
            )
    def detach_sync(self, reason):
        if not self.loop.is_closed():
            self.loop.create_task(self.detach(reason))


    async def detach(self, reason = None):
        """Detaches from the current process."""
        if reason:
            print(f"Detaching due to {reason}")
        else:
            print("Detaching.")
        if self.polling_task:
            self.polling_task.cancel()
            self.polling_task = None

        if self.session:
            self.session.detach()

        self.session = None
        self.agent = None
        await self.broadcast({"event": "status", "data": "Detached"})


    async def _poll_loop(self):
        """
        Polls the agent for updates, such as new values in watched memory addresses.
        """
        while True:
            try:
                watch_job = self.watch_list.copy()
                freeze_job = self.freeze_list.copy()

                if not self.agent:
                    print("Pool loop: no agent. Breaking.")
                    break

                await asyncio.sleep(0.1)
            except frida.InvalidOperationError:
                print("Polling failed. Breaking")
                break
            except Exception as e:
                print(f"Polling failed: {e}")
                break

    async def handle_message(self, websocket, message_str: str):
        """Dispatches commands coming from the UI."""
        try:
            msg = json.loads(message_str)
            command = msg.get("command")
            params = msg.get("params", {})
            request_uuid = msg.get("uuid")

            if command == "attach":
                self.attach(params["pid"])
            else:
                if self.agent is None:
                    raise AssertionError("Agent is not initialized")
                match command:
                    case "hello":
                        response = await self.agent.hello()
                        to_send = {"event": "hello", "data": response}
                    case "list-processes":
                        response = [{"pid": proc.pid, "name": proc.name} for proc in self.device.enumerate_processes()]
                        to_send = {"event": "get-processes", "data": response}
                    case "first-scan":
                        response = await self.agent.first_scan(params["value"], params["scan_size"], params["scan_type"])
                        to_send = {"event": "first-scan", "data": response}
                    case "next-scan":
                        response = await self.agent.next_scan(params["value"], params["scan_size"], params["scan_type"])
                        to_send = {"event": "next-scan", "data": response}
                    case _:
                        print(f"Unknown command: {command}")
        except Exception as e:
            print(f"Failed to handle message: {e}")
            to_send = {"event": "error", "data": str(e)}
        finally:
            if to_send:
                to_send["uuid"] = request_uuid
                await websocket.send(json.dumps(to_send))
