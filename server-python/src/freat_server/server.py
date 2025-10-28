import asyncio
import functools

import websockets

from freat_server.hub import Hub

APP_NAME = "freat"


async def websocket_handler(websocket, hub: Hub):
    """
    The handler called for each new UI connection.
    Registers the client and then listens for messages.
    """
    hub.register_client(websocket)
    try:
        async for message in websocket:
            await hub.handle_message(websocket, message)
    except websockets.ConnectionClosed:
        print("Client disconnected")
    finally:
        hub.unregister_client(websocket)


async def serve():
    hub = Hub()
    ws_handler = functools.partial(websocket_handler, hub=hub)

    print("Starting WebSocket server on ws://localhost:8765")
    async with websockets.serve(ws_handler, "localhost", 8765):
        await asyncio.Future()

def main():
    asyncio.run(serve())
