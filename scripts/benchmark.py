#!/usr/bin/env python3
import asyncio
import json
import websockets
import argparse
import time
import statistics
from typing import Dict, List, Any

class BenchmarkResult:
    def __init__(self):
        self.attach_times: List[float] = []
        self.scan_times: List[float] = []
        self.get_results_times: List[float] = []
        self.total_times: List[float] = []

    def add_result(self, attach_time: float, scan_time: float, get_results_time: float):
        self.attach_times.append(attach_time)
        self.scan_times.append(scan_time)
        self.get_results_times.append(get_results_time)
        self.total_times.append(attach_time + scan_time + get_results_time)

    def print_summary(self):
        print("\n=== Benchmark Results ===")
        print(f"Number of iterations: {len(self.attach_times)}")
        print(f"Attach time (avg): {statistics.mean(self.attach_times):.4f} seconds")
        print(f"Scan time (avg): {statistics.mean(self.scan_times):.4f} seconds")
        print(f"Get results time (avg): {statistics.mean(self.get_results_times):.4f} seconds")
        print(f"Total time per iteration (avg): {statistics.mean(self.total_times):.4f} seconds")
        
        if len(self.attach_times) > 1:
            print(f"Attach time (std dev): {statistics.stdev(self.attach_times):.4f} seconds")
            print(f"Scan time (std dev): {statistics.stdev(self.scan_times):.4f} seconds")
            print(f"Get results time (std dev): {statistics.stdev(self.get_results_times):.4f} seconds")
            print(f"Total time per iteration (std dev): {statistics.stdev(self.total_times):.4f} seconds")

async def benchmark_iteration(
    websocket, 
    pid: int, 
    scan_value: Any, 
    scan_width: int = 4, 
    scan_signed: bool = False,
    page_size: int = 50
) -> Dict[str, float]:
    """Run a single benchmark iteration and return timing results"""
    results = {}
    
    # Attach to process
    attach_start = time.time()
    await websocket.send(json.dumps({
        "command": "attach",
        "target": pid
    }))
    
    response = await websocket.recv()
    response_data = json.loads(response)
    
    if response_data["status"] == "error":
        raise Exception(f"Error attaching to process: {response_data['error']}")
    
    attach_end = time.time()
    results["attach_time"] = attach_end - attach_start
    
    # Scan for value
    scan_start = time.time()
    await websocket.send(json.dumps({
        "command": "scan_memory",
        "value": scan_value,
        "width": scan_width,
        "signed": scan_signed,
        "scan_type": "first"
    }))
    
    response = await websocket.recv()
    response_data = json.loads(response)
    
    if response_data["status"] == "error":
        raise Exception(f"Error scanning memory: {response_data['error']}")
    
    scan_end = time.time()
    results["scan_time"] = scan_end - scan_start
    
    # Get scan results
    get_results_start = time.time()
    await websocket.send(json.dumps({
        "command": "get_scan_results",
        "page": 1,
        "page_size": page_size
    }))
    
    response = await websocket.recv()
    response_data = json.loads(response)
    
    if response_data["status"] == "error":
        raise Exception(f"Error getting scan results: {response_data['error']}")
    
    get_results_end = time.time()
    results["get_results_time"] = get_results_end - get_results_start
    
    # Detach from process
    await websocket.send(json.dumps({
        "command": "detach"
    }))
    
    response = await websocket.recv()
    response_data = json.loads(response)
    
    if response_data["status"] == "error":
        print(f"Warning: Error detaching: {response_data['error']}")
    
    return results

async def run_benchmark(
    pid: int, 
    scan_value: Any, 
    iterations: int = 50, 
    host: str = "127.0.0.1", 
    port: int = 8888,
    scan_width: int = 4,
    scan_signed: bool = False,
    page_size: int = 50
):
    uri = f"ws://{host}:{port}"
    benchmark_results = BenchmarkResult()
    
    print(f"Starting benchmark with {iterations} iterations")
    print(f"Target PID: {pid}")
    print(f"Scan value: {scan_value}")
    print(f"Scan width: {scan_width}")
    print(f"Scan signed: {scan_signed}")
    print(f"Page size: {page_size}")
    
    for i in range(iterations):
        print(f"\nIteration {i+1}/{iterations}")
        
        try:
            async with websockets.connect(
                uri,
                ping_interval=30,
                ping_timeout=60
            ) as websocket:
                results = await benchmark_iteration(
                    websocket, 
                    pid, 
                    scan_value, 
                    scan_width, 
                    scan_signed,
                    page_size
                )
                
                benchmark_results.add_result(
                    results["attach_time"],
                    results["scan_time"],
                    results["get_results_time"]
                )
                
                print(f"  Attach time: {results['attach_time']:.4f} seconds")
                print(f"  Scan time: {results['scan_time']:.4f} seconds")
                print(f"  Get results time: {results['get_results_time']:.4f} seconds")
                print(f"  Total time: {sum(results.values()):.4f} seconds")
                
        except Exception as e:
            print(f"Error in iteration {i+1}: {str(e)}")
    
    benchmark_results.print_summary()
    
    # Request timing statistics from the server
    print("\nRequesting timing statistics from server...")
    try:
        async with websockets.connect(
            uri,
            ping_interval=30,
            ping_timeout=60
        ) as websocket:
            await websocket.send(json.dumps({
                "command": "get_timing_stats"
            }))
            
            response = await websocket.recv()
            response_data = json.loads(response)
            
            if response_data["status"] == "error":
                print(f"Error getting timing statistics: {response_data['error']}")
            else:
                print("\n=== Server Timing Statistics ===")
                for command, stats in response_data["result"].items():
                    print(f"Command: {command}")
                    print(f"  Count: {stats['count']}")
                    print(f"  Average time: {stats['avg_time']:.6f} seconds")
                    print(f"  Min time: {stats['min_time']:.6f} seconds")
                    print(f"  Max time: {stats['max_time']:.6f} seconds")
                    if "std_dev" in stats:
                        print(f"  Standard deviation: {stats['std_dev']:.6f} seconds")
                    print("")
    except Exception as e:
        print(f"Error requesting timing statistics: {str(e)}")

def load_config(config_file: str) -> Dict[str, Any]:
    """Load configuration from JSON file"""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"Error loading config file: {str(e)}")
        return {}

def main():
    parser = argparse.ArgumentParser(description='Freat benchmarking tool')
    parser.add_argument('--config', default='benchmark_config.json', help='Path to configuration file (default: benchmark_config.json)')
    parser.add_argument('--pid', type=int, help='Process ID to attach to (overrides config file)')
    parser.add_argument('--scan-value', help='Value to scan for (overrides config file)')
    parser.add_argument('--iterations', type=int, help='Number of iterations (overrides config file)')
    parser.add_argument('--host', help='Server host (overrides config file)')
    parser.add_argument('--port', type=int, help='Server port (overrides config file)')
    parser.add_argument('--scan-width', type=int, choices=[1, 2, 4, 8], help='Scan width (overrides config file)')
    parser.add_argument('--scan-signed', action='store_true', help='Use signed values for scanning (overrides config file)')
    parser.add_argument('--page-size', type=int, help='Page size for scan results (overrides config file)')
    
    args = parser.parse_args()
    
    # Load configuration from file
    config = load_config(args.config)
    
    # Override config with command line arguments
    pid = args.pid if args.pid is not None else config.get('pid')
    scan_value = args.scan_value if args.scan_value is not None else config.get('scan_value')
    iterations = args.iterations if args.iterations is not None else config.get('iterations', 50)
    host = args.host if args.host is not None else config.get('host', '127.0.0.1')
    port = args.port if args.port is not None else config.get('port', 8888)
    scan_width = args.scan_width if args.scan_width is not None else config.get('scan_width', 4)
    scan_signed = args.scan_signed if args.scan_signed else config.get('scan_signed', False)
    page_size = args.page_size if args.page_size is not None else config.get('page_size', 50)
    
    # Validate required parameters
    if pid is None:
        print("Error: PID is required. Specify it in the config file or with --pid")
        return
    
    if scan_value is None:
        print("Error: Scan value is required. Specify it in the config file or with --scan-value")
        return
    
    # Convert scan value to appropriate type
    try:
        scan_value = int(scan_value)
    except ValueError:
        pass  # Keep as string if not an integer
    
    try:
        asyncio.run(run_benchmark(
            pid,
            scan_value,
            iterations,
            host,
            port,
            scan_width,
            scan_signed,
            page_size
        ))
    except KeyboardInterrupt:
        print("\nBenchmark terminated by user.")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 