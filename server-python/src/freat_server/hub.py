import asyncio
import json
import typing
from enum import Enum
from importlib import resources
from typing import Any, Awaitable, Protocol

import frida

from freat_server.targets.remote import RemoteTargetProvider


class DataType(Enum):
    U8 = 0
    U16 = 1
    U32 = 2
    U64 = 3
    FLOAT = 4
    DOUBLE = 5
    STRING = 6


class ScanType(Enum):
    EXACT = 0
    GREATER_THAN = 1
    LESS_THAN = 2


class Agent(Protocol):
    """
    Defines the interface for the Frida agent script.
    """

    def hello(self) -> Awaitable[Any]: ...
    def first_scan(
        self, value: int, data_type: str, scan_type: int
    ) -> Awaitable[int]: ...
    def next_scan(self, value: int, scan_type: int) -> Awaitable[int]: ...
    def undo_scan(self) -> Awaitable[None]: ...
    def get_scan_results(self, count: int) -> Awaitable[dict[str, int]]: ...
    def read_batch(
        self, addresses: list[tuple[str, str]]
    ) -> Awaitable[dict[str, Any]]: ...
    def write_batch(self, writes: list[tuple[str, Any, str]]) -> Awaitable[None]: ...
    def write_value(
        self, ptr: str, value: Any, data_type: DataType
    ) -> Awaitable[None]: ...
    def run_scan_test(self) -> Awaitable[bool]: ...


class Hub:
    """
    The console. Manages the Frida session, the application state (watch/freeze lists),
    and all the connected UI clients.
    """

    def __init__(self, user_config: dict = {}):
        self.session = None
        self.agent: Agent | None = None
        self.target_provider = RemoteTargetProvider(
            user_config.get("remote_host", "localhost"),
            user_config.get("remote_port", 27042),
        )
        self.clients = set()
        self.watch_list: set[tuple[str, str]] = set()
        self.freeze_list: list[tuple[str, Any, str]] = []
        self.polling_task: asyncio.Task | None = None
        self.user_config = user_config
        self.agent_js = self._load_agent_script()
        self.loop = asyncio.get_event_loop()
        self.top_results_count = 100

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
        """Attaches to a new process via the configured target provider."""
        print(f"Attaching to {pid}...")
        if not self.agent_js:
            await self.broadcast({"event": "error", "data": "Agent script not found."})
            return

        try:
            # If we're already attached, we detach.
            if self.session:
                await self.detach()

            self.session = self.target_provider.attach(pid)
            self.session.on("detached", lambda reason: self.detach_sync(reason))

            script = self.session.create_script(self.agent_js)
            script.on("message", lambda message, data: print(message, data))
            script.load()
            self.agent = typing.cast(Agent, script.exports_async)
            self.polling_task = asyncio.create_task(self._poll_loop())
            await self.broadcast({"event": "attach", "data": pid})
            print(f"Attached to {pid}.")
        except Exception as e:
            print(f"Error attaching to {pid}: {e}")
            await self.broadcast(
                {"event": "error", "data": f"Error attaching to {pid}: {e}"}
            )

    def detach_sync(self, reason):
        if not self.loop.is_closed():
            self.loop.create_task(self.detach(reason))

    async def detach(self, reason=None):
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
        await self.broadcast({"event": "status", "data": "detached"})

    async def _poll_loop(self):
        """
        Polls the agent for updates, such as new values in watched memory addresses.
        """
        while True:
            try:
                if not self.agent:
                    print("Pool loop: no agent. Breaking.")
                    break

                if self.watch_list:
                    watch_job = list(self.watch_list)
                    response = await self.agent.read_batch(watch_job)
                    await self.broadcast({"event": "watch", "data": response})

                if self.freeze_list:
                    await self.agent.write_batch(self.freeze_list)

                current_scan_top_results = await self.agent.get_scan_results(
                    self.top_results_count
                )
                if current_scan_top_results:
                    await self.broadcast(
                        {
                            "event": "current-scan-results",
                            "data": current_scan_top_results,
                        }
                    )

                await asyncio.sleep(0.1)
            except frida.InvalidOperationError:
                print("Polling failed. Breaking")
                break
            except Exception as e:
                print(f"Polling failed: {e}")
                break

    async def handle_message(self, websocket, message_str: str):
        """Dispatches commands coming from the UI."""
        to_send = None
        request_uuid = "<uuid-unset>"
        try:
            msg = json.loads(message_str)
            command = msg.get("command")
            params = msg.get("params", {})
            request_uuid = msg.get("uuid")

            if command == "attach":
                await self.attach(params["pid"])
            elif command == "list-processes":
                response = [
                    {"pid": proc.pid, "name": proc.name}
                    for proc in self.target_provider.discover()
                ]
                to_send = {"event": "list-processes", "data": response}
            elif command == "status":
                response = "attached" if self.agent else "detached"
                to_send = {"event": "status", "data": response}
            else:
                if self.agent is None:
                    raise AssertionError("Agent is not initialized")
                match command:
                    case "hello":
                        response = await self.agent.hello()
                        to_send = {"event": "hello", "data": response}
                    case "first-scan":
                        response = await self.agent.first_scan(
                            params["value"], params["data_type"], params["scan_type"]
                        )
                        to_send = {"event": "first-scan", "data": response}
                    case "next-scan":
                        response = await self.agent.next_scan(
                            params["value"], params["scan_type"]
                        )
                        to_send = {"event": "next-scan", "data": response}
                    case "undo-scan":
                        response = await self.agent.undo_scan()
                        to_send = {"event": "undo-scan", "data": response}
                    case "add-to-watch-list":
                        self.watch_list.add((params["address"], params["data_type"]))
                    case "remove-from-watch-list":
                        self.watch_list.discard(
                            (params["address"], params["data_type"])
                        )
                    case "add-to-freeze-list":
                        self.freeze_list.append(
                            (params["address"], params["value"], params["data_type"])
                        )
                    case "remove-from-freeze-list":
                        self.freeze_list = [
                            (addr, val, dt)
                            for addr, val, dt in self.freeze_list
                            if addr != params["address"]
                        ]
                    case "write-value":
                        response = await self.agent.write_value(
                            params["address"], params["value"], params["data_type"]
                        )
                    case _:
                        print(f"Unknown command: {command}")
        except Exception as e:
            print(f"Failed to handle message: {e}")
            to_send = {"event": "error", "data": str(e)}
        finally:
            if to_send:
                to_send["uuid"] = request_uuid
                await websocket.send(json.dumps(to_send))
