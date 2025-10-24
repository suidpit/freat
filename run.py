import argparse
import atexit
import os
import shutil
import subprocess
from pathlib import Path

processes: list[subprocess.Popen] = []

AGENT_DIR = str(Path(__file__).parent / "server-python" / "agent")
HUB_DIR = str(Path(__file__).parent / "server-python")
GUI_DIR = str(Path(__file__).parent / "client-godot")


def cleanup():
    """Make sure all the spawned subprocesses are terminated on exit."""
    for p in processes:
        if p.poll() is None:
            print(f"Terminating PID {p.pid}")
            p.terminate()
            p.wait()


atexit.register(cleanup)


def run_cmd(
    cmd: str, cwd: str = ".", wait=True, cleanup=True, shell=False
) -> subprocess.Popen:
    """Helper to run a shell command."""
    print(f"[{cwd}]$ {cmd}")
    if shell:
        p = subprocess.Popen(cmd, shell=True, cwd=cwd)
    else:
        p = subprocess.Popen(cmd.split(), shell=False, cwd=cwd)
    if cleanup:
        processes.append(p)
    if wait:
        p.wait()
    return p


def find_godot_executable() -> str | None:
    """Find the path to the Godot executable."""
    godot_path = shutil.which("godot")
    if godot_path is not None:
        return godot_path
    if os.name == "darwin":
        return "/Applications/Godot.app/Contents/MacOS/Godot"
    return None


def cmd_dev():
    """Run all components in live-reload development mode."""
    print("--- Starting Agent (watch mode) ---")
    run_cmd("npm run watch", cwd=AGENT_DIR, wait=False)

    print("--- Starting Server (live reload) ---")
    run_cmd("uv run watchfiles python main.py", cwd=HUB_DIR, wait=False)

    godot_path = find_godot_executable()
    if not godot_path:
        print("[!] Godot executable not found. Running the headless server...")
        try:
            while True:
                pass
        except KeyboardInterrupt:
            print("Stopping all services...")
            return
    else:
        try:
            print("--- Starting the Godot Editor ---")
            run_cmd(f"{godot_path} --path . --editor", cwd=GUI_DIR, wait=True)
            print("Godot editor closed. Stopping all services...")
        except KeyboardInterrupt:
            print("Stopping all services...")

def cmd_test():
    """Run the test suite"""
    print("--- Building Agent ---")
    run_cmd("npm run build", cwd=AGENT_DIR, wait=True)
    print("--- Running tests ---")
    run_cmd("uv run pytest", cwd=HUB_DIR, wait=True)

def main():
    parser = argparse.ArgumentParser(description="freat - an instrumentation toolkit")
    subparser = parser.add_subparsers(dest="command", required=True)
    subparser.add_parser(
        "dev", help="Run all components in live-reload development mode"
    )
    subparser.add_parser("test", help="Run the test suite")

    args = parser.parse_args()

    match args.command:
        case "dev":
            cmd_dev()
        case "test":
            cmd_test()
        case _:
            print("Invalid command")


if __name__ == "__main__":
    main()
