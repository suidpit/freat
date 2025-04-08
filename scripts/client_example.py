#!/usr/bin/env python3
import asyncio
import json
import websockets
import argparse
import time

async def freat_client(process_target, host="127.0.0.1", port=8888):
    uri = f"ws://{host}:{port}"
    
    async with websockets.connect(
        uri,
        ping_interval=30,  # Send ping every 30 seconds
        ping_timeout=60    # Wait 60 seconds for pong before closing
    ) as websocket:
        print(f"Connected to server at {uri}")
        
        # Attach to a process
        print(f"Attempting to attach to process: {process_target}")
        
        # Check if the target is a PID (integer)
        try:
            pid = int(process_target)
            target = pid  # Send as integer
        except ValueError:
            target = process_target  # Send as string (process name)
            
        await websocket.send(json.dumps({
            "command": "attach",
            "target": target
        }))
        
        response = await websocket.recv()
        response_data = json.loads(response)
        
        if response_data["status"] == "error":
            print(f"Error: {response_data['error']}")
            return
        
        print(f"Successfully attached to process: {process_target}")
        
        # Get memory maps
        print("Fetching memory maps...")
        await websocket.send(json.dumps({
            "command": "get_memory_maps"
        }))
        
        response = await websocket.recv()
        response_data = json.loads(response)
        
        if response_data["status"] == "error":
            print(f"Error fetching memory maps: {response_data['error']}")
        else:
            print("Memory maps:")
            for i, memory_map in enumerate(response_data["result"]):
                print(f"{i+1}. {memory_map['name']} at {memory_map['base_address']} ({memory_map['protection']})")
        
        # Track if a scan has been performed
        scan_performed = False
        
        # Interactive mode
        try:
            while True:
                print("\nCommands:")
                print("1. Scan memory for value")
                if scan_performed:
                    print("2. Next scan with new value")
                print("3. Read memory at address")
                print("4. Get scan results")
                print("5. Detach and exit")
                
                choice = input("Enter choice (1-5): ")
                
                if choice == "1":
                    value_type = input("Value type (number/string): ").lower()
                    if value_type == "number":
                        value = int(input("Enter value to scan for: "))
                        width = int(input("Width (1, 2, 4, or 8): "))
                        signed = input("Signed (yes/no): ").lower() == "yes"
                        
                        await websocket.send(json.dumps({
                            "command": "scan_memory",
                            "value": value,
                            "width": width,
                            "signed": signed,
                            "scan_type": "first"
                        }))
                    else:
                        value = input("Enter string to scan for: ")
                        
                        await websocket.send(json.dumps({
                            "command": "scan_memory",
                            "value": value,
                            "scan_type": "first"
                        }))
                    
                    response = await websocket.recv()
                    response_data = json.loads(response)
                    
                    if response_data["status"] == "error":
                        print(f"Error scanning memory: {response_data['error']}")
                    else:
                        count = response_data["result"]
                        print(f"Found {count} addresses matching the value")
                        scan_performed = True
                        
                        # Start a background task to display scan results
                        asyncio.create_task(display_scan_results(websocket))
                
                elif choice == "2" and scan_performed:
                    value_type = input("Value type (number/string): ").lower()
                    if value_type == "number":
                        value = int(input("Enter new value to scan for: "))
                        await websocket.send(json.dumps({
                            "command": "scan_memory",
                            "value": value,
                            "scan_type": "next"
                        }))
                    else:
                        value = input("Enter new string to scan for: ")
                        await websocket.send(json.dumps({
                            "command": "scan_memory",
                            "value": value,
                            "scan_type": "next"
                        }))
                    
                    response = await websocket.recv()
                    response_data = json.loads(response)
                    
                    if response_data["status"] == "error":
                        print(f"Error scanning memory: {response_data['error']}")
                    else:
                        count = response_data["result"]
                        print(f"Found {count} addresses matching the new value")
                
                elif choice == "3":
                    address = input("Enter address to read (e.g., 0x12345678): ")
                    read_type = input("Read type (number/string): ").lower()
                    
                    if read_type == "number":
                        width = int(input("Width (1, 2, 4, or 8): "))
                        signed = input("Signed (yes/no): ").lower() == "yes"
                        
                        await websocket.send(json.dumps({
                            "command": "read_memory",
                            "address": address,
                            "width": width,
                            "signed": signed
                        }))
                    else:
                        max_length = int(input("Max string length: "))
                        
                        await websocket.send(json.dumps({
                            "command": "read_memory",
                            "address": address,
                            "is_string": True,
                            "max_length": max_length
                        }))
                    
                    response = await websocket.recv()
                    response_data = json.loads(response)
                    
                    if response_data["status"] == "error":
                        print(f"Error reading memory: {response_data['error']}")
                    else:
                        print(f"Value at {address}: {response_data['result']}")
                
                elif choice == "4":
                    page = int(input("Enter page number (1-based): "))
                    page_size = int(input("Enter page size: "))
                    
                    await websocket.send(json.dumps({
                        "command": "get_scan_results",
                        "page": page,
                        "page_size": page_size
                    }))
                    
                    response = await websocket.recv()
                    response_data = json.loads(response)
                    
                    if response_data["status"] == "error":
                        print(f"Error getting scan results: {response_data['error']}")
                    else:
                        result = response_data["result"]
                        print(f"Page {result['page']} of {result['totalPages']} (Total: {result['total']} addresses)")
                        print(f"Showing {len(result['results'])} results:")
                        
                        for i, item in enumerate(result['results']):
                            print(f"{i+1}. Address: {item['address']}, Value: {item['value']}")
                
                elif choice == "5":
                    break
                
                else:
                    print("Invalid choice. Please try again.")
        
        except KeyboardInterrupt:
            print("\nInterrupted by user.")
        
        # Detach from process
        print("Detaching from process...")
        await websocket.send(json.dumps({
            "command": "detach"
        }))
        
        response = await websocket.recv()
        response_data = json.loads(response)
        
        if response_data["status"] == "error":
            print(f"Error detaching: {response_data['error']}")
        else:
            print("Successfully detached from process.")

async def display_scan_results(websocket):
    """Background task to display scan results every 100ms"""
    try:
        while True:
            # Request the first 50 results
            await websocket.send(json.dumps({
                "command": "get_scan_results",
                "page": 1,
                "page_size": 50
            }))
            
            response = await websocket.recv()
            response_data = json.loads(response)
            
            if response_data["status"] == "error":
                print(f"Error getting scan results: {response_data['error']}")
                break
            else:
                result = response_data["result"]
                print(f"\nScan Results (Page {result['page']} of {result['totalPages']}, Total: {result['total']} addresses)")
                print(f"Showing {len(result['results'])} results:")
                
                for i, item in enumerate(result['results']):
                    print(f"{i+1}. Address: {item['address']}, Value: {item['value']}")
            
            # Wait for 100ms before next update
            await asyncio.sleep(0.1)
    except Exception as e:
        print(f"Error in display_scan_results: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Freat client example')
    parser.add_argument('process', help='Process name or PID to attach to')
    parser.add_argument('--host', default='127.0.0.1', help='Server host (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=8888, help='Server port (default: 8888)')
    
    args = parser.parse_args()
    
    try:
        asyncio.run(freat_client(args.process, args.host, args.port))
    except KeyboardInterrupt:
        print("\nClient terminated by user.")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 