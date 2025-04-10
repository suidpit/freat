#!/usr/bin/env python3
import asyncio
import json
import logging
import websockets
import frida
from enum import Enum
import argparse
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class CommandType(Enum):
    ATTACH = "attach"
    DETACH = "detach"
    SCAN_MEMORY = "scan_memory"
    READ_MEMORY = "read_memory"
    GET_MEMORY_MAPS = "get_memory_maps"
    GET_SCAN_RESULTS = "get_scan_results"
    GET_PROCESSES = "get_processes"
    WRITE_MEMORY = "write_memory"

class FreatServer:
    def __init__(self, host="127.0.0.1", port=8888):
        self.host = host
        self.port = port
        self.sessions = {}  
        self.scripts = {}   

    async def handle_client(self, websocket):
        client_id = id(websocket)
        logger.info(f"New client connected: {client_id}")
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.process_command(websocket, client_id, data)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "status": "error",
                        "error": "Invalid JSON format"
                    }))
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
                    await websocket.send(json.dumps({
                        "status": "error",
                        "error": str(e)
                    }))
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")
        finally:
            
            await self.cleanup_session(client_id)

    async def cleanup_session(self, client_id):
        """Clean up Frida resources when a client disconnects"""
        if client_id in self.scripts:
            try:
                self.scripts[client_id].unload()
            except:
                pass
            del self.scripts[client_id]
        
        if client_id in self.sessions:
            try:
                self.sessions[client_id].detach()
            except:
                pass
            del self.sessions[client_id]
        logger.info(f"Cleanup session: {client_id}")

    async def process_command(self, websocket, client_id, data):
        """Process incoming commands from clients"""
        if "command" not in data:
            await websocket.send(json.dumps({
                "status": "error",
                "error": "Missing 'command' field",
                "command": None
            }))
            return
        
        command = data["command"]
        
        try:
            if command == CommandType.ATTACH.value:
                await self.handle_attach(websocket, client_id, data)
            elif command == CommandType.DETACH.value:
                await self.handle_detach(websocket, client_id, command)
            elif command == CommandType.SCAN_MEMORY.value:
                await self.handle_scan_memory(websocket, client_id, data)
            elif command == CommandType.READ_MEMORY.value:
                await self.handle_read_memory(websocket, client_id, data)
            elif command == CommandType.GET_MEMORY_MAPS.value:
                await self.handle_get_memory_maps(websocket, client_id, command)
            elif command == CommandType.GET_SCAN_RESULTS.value:
                await self.handle_get_scan_results(websocket, client_id, data)
            elif command == CommandType.GET_PROCESSES.value:
                await self.handle_get_processes(websocket, client_id, command)
            elif command == CommandType.WRITE_MEMORY.value:
                await self.handle_write_memory(websocket, client_id, data)
            else:
                await websocket.send(json.dumps({
                    "status": "error",
                    "error": f"Unknown command: {command}",
                    "command": command
                }))
        except Exception as e:
            logger.error(f"Error executing command {command}: {str(e)}")
            await websocket.send(json.dumps({
                "status": "error",
                "error": str(e),
                "command": command
            }))

    async def handle_attach(self, websocket, client_id, data):
        """Attach to a process by name or PID"""
        command = data["command"]
        
        if "target" not in data:
            await websocket.send(json.dumps({
                "status": "error",
                "error": "Missing 'target' field",
                "command": command
            }))
            return
        
        target = data["target"]
        
        try:
            
            await self.cleanup_session(client_id)
            
            
            if isinstance(target, int) or target.isdigit():
                print("Attaching to process with PID: ", target)
                pid = int(target)
                session = frida.attach(pid)
            else:
                print("Attaching to process with name: ", target)
                device = frida.get_local_device()
                pid = device.get_process(target).pid
                session = frida.attach(pid)
            
            
            with open("_agent.js", "r") as f:
                script_source = f.read()
            
            script = session.create_script(script_source)
            script.load()
            
            
            self.sessions[client_id] = session
            self.scripts[client_id] = script
            
            await websocket.send(json.dumps({
                "status": "success",
                "message": f"Attached to process {pid}",
                "command": command
            }))
        except frida.ProcessNotFoundError:
            await websocket.send(json.dumps({
                "status": "error",
                "error": f"Process not found: {target}",
                "command": command
            }))
        except Exception as e:
            logger.error(f"Error attaching to process: {str(e)}")
            await websocket.send(json.dumps({
                "status": "error",
                "error": str(e),
                "command": command
            }))

    async def handle_detach(self, websocket, client_id, command):
        """Detach from the current process"""
        if client_id not in self.sessions:
            await websocket.send(json.dumps({
                "status": "error",
                "error": "Not attached to any process",
                "command": command
            }))
            return
        
        
        await self.cleanup_session(client_id)
        print(f"Detached from process {client_id}")
        
        await websocket.send(json.dumps({
            "status": "success",
            "message": "Detached from process",
            "command": command
        }))

    async def handle_scan_memory(self, websocket, client_id, data):
        """Scan memory for a value"""
        command = data["command"]
        
        if client_id not in self.scripts:
            await websocket.send(json.dumps({
                "status": "error",
                "error": "Not attached to any process",
                "command": command
            }))
            return
        
        if "value" not in data:
            await websocket.send(json.dumps({
                "status": "error",
                "error": "Missing 'value' field",
                "command": command
            }))
            return
        
        target_value = data["value"]
        scan_type = data.get("scan_type", "first")  
        width = data.get("width", 4)
        signed = data.get("signed", False)
        
        try:
            script = self.scripts[client_id]
            
            # Add timing logs for memory scanning operations
            start_time = time.time()
            logger.info(f"Starting memory scan: type={scan_type}, value={target_value}, width={width}, signed={signed}")
            if isinstance(target_value, str):
                result = script.exports.scan_strings(target_value)
            else:
                if scan_type == "first":
                    result = script.exports.first_scan(target_value, width, signed)
                elif scan_type == "next":
                    result = script.exports.next_scan(target_value)
                else:
                    await websocket.send(json.dumps({
                        "status": "error",
                        "error": f"Invalid scan_type: {scan_type}. Must be 'first' or 'next'",
                        "command": command
                    }))
                    return
            end_time = time.time()
            scan_duration = end_time - start_time
            logger.info(f"Memory scan completed in {scan_duration:.2f} seconds")
            
            await websocket.send(json.dumps({
                "status": "success",
                "result": result,
                "command": command
            }))
        except Exception as e:
            logger.error(f"Error scanning memory: {str(e)}")
            await websocket.send(json.dumps({
                "status": "error",
                "error": str(e),
                "command": command
            }))

    async def handle_read_memory(self, websocket, client_id, data):
        """Read memory at a specific address"""
        command = data["command"]
        
        if client_id not in self.scripts:
            await websocket.send(json.dumps({
                "status": "error",
                "error": "Not attached to any process",
                "command": command
            }))
            return
        
        if "address" not in data:
            await websocket.send(json.dumps({
                "status": "error",
                "error": "Missing 'address' field",
                "command": command
            }))
            return
        
        address = data["address"]
        width = data.get("width", 4)
        signed = data.get("signed", False)
        is_string = data.get("is_string", False)
        max_length = data.get("max_length", 256)
        
        try:
            script = self.scripts[client_id]
            
            
            if is_string:
                result = script.exports.read_string(address, max_length)
            else:
                result = script.exports.read(address, width, signed)
            
            await websocket.send(json.dumps({
                "status": "success",
                "result": result,
                "command": command
            }))
        except Exception as e:
            logger.error(f"Error reading memory: {str(e)}")
            await websocket.send(json.dumps({
                "status": "error",
                "error": str(e),
                "command": command
            }))

    async def handle_get_memory_maps(self, websocket, client_id, command):
        """Get memory maps of the attached process"""
        if client_id not in self.scripts:
            await websocket.send(json.dumps({
                "status": "error",
                "error": "Not attached to any process",
                "command": command
            }))
            return
        
        try:
            script = self.scripts[client_id]
            
            result = script.exports.get_memory_maps()
            
            await websocket.send(json.dumps({
                "status": "success",
                "result": result,
                "command": command
            }))
        except Exception as e:
            logger.error(f"Error getting memory maps: {str(e)}")
            await websocket.send(json.dumps({
                "status": "error",
                "error": str(e),
                "command": command
            }))

    async def handle_get_scan_results(self, websocket, client_id, data):
        """Get paginated scan results"""
        command = data["command"]
        
        if client_id not in self.scripts:
            await websocket.send(json.dumps({
                "status": "error",
                "error": "Not attached to any process",
                "command": command
            }))
            return
        
        page = data.get("page", 1)
        page_size = data.get("page_size", 100)
        
        try:
            script = self.scripts[client_id]
            
            result = script.exports.get_scan_results(page, page_size)
            
            await websocket.send(json.dumps({
                "status": "success",
                "result": result,
                "command": command
            }))
        except Exception as e:
            logger.error(f"Error getting scan results: {str(e)}")
            await websocket.send(json.dumps({
                "status": "error",
                "error": str(e),
                "command": command
            }))

    async def handle_get_processes(self, websocket, client_id, command):
        """Get all running processes"""
        try:
            device = frida.get_local_device()
            processes = device.enumerate_processes()

            process_list = []
            for process in processes:
                process_info = {
                    "pid": int(process.pid),
                    "name": process.name,
                }
                process_list.append(process_info)

            await websocket.send(json.dumps({
                "status": "success",
                "result": process_list,
                "command": command
            }))
        except Exception as e:
            logger.error(f"Error getting processes: {str(e)}")
            await websocket.send(json.dumps({
                "status": "error",
                "error": str(e),
                "command": command
            }))

    async def handle_write_memory(self, websocket, client_id, data):
        """Write memory at a specific address"""
        command = data["command"]
        
        if client_id not in self.scripts:
            await websocket.send(json.dumps({
                "status": "error",
                "error": "Not attached to any process",
                "command": command
            }))
            return
        
        address = data["address"]
        value = data["value"]
        width = data.get("width", 4)
        signed = data.get("signed", False)
        
        try:
            script = self.scripts[client_id]
            script.exports.write(address, value, width, signed)
            
            await websocket.send(json.dumps({
                "status": "success",
                "message": "Memory written successfully",
                "command": command
            }))
        except Exception as e:
            logger.error(f"Error writing memory: {str(e)}")
            await websocket.send(json.dumps({
                "status": "error",
                "error": str(e),
                "command": command
            }))
        



async def main():
    parser = argparse.ArgumentParser(description="Freat Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8888, help="Port to bind to")
    args = parser.parse_args()
    
    server = FreatServer(args.host, args.port)
    
    async with websockets.serve(server.handle_client, args.host, args.port):
        logger.info(f"Freat server started on ws://{args.host}:{args.port}")
        
        try:
            
            await asyncio.Future()  
        except KeyboardInterrupt:
            logger.info("Server shutting down...")

if __name__ == "__main__":
    asyncio.run(main()) 