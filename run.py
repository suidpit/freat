import argparse
import atexit
import shutil
import subprocess
import sys
from pathlib import Path

processes: list[subprocess.Popen] = []

PROJECT_ROOT = Path(__file__).parent
AGENT_DIR = str(PROJECT_ROOT / "server-python" / "agent")
HUB_DIR = str(PROJECT_ROOT / "server-python")
GUI_DIR = str(PROJECT_ROOT / "client-godot")
BUILD_DIR = PROJECT_ROOT / "build"
DIST_DIR = PROJECT_ROOT / "dist"


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
    if sys.platform == "darwin":
        return "/Applications/Godot.app/Contents/MacOS/Godot"
    return None


def cmd_dev():
    """Run all components in live-reload development mode."""
    print("--- Starting Agent (watch mode) ---")
    run_cmd("npm run watch", cwd=AGENT_DIR, wait=False)

    print("--- Starting Server (live reload) ---")
    run_cmd("uv run watchfiles freat-server", cwd=HUB_DIR, wait=False)

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


def cmd_build():
    """Build release package for distribution."""

    print("=" * 50)
    print("Building Freat Release Package")
    print("=" * 50)
    print()

    print("→ Cleaning build directories...")
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    BUILD_DIR.mkdir(parents=True)
    DIST_DIR.mkdir(parents=True)
    print("✓ Build directories cleaned")

    print("\n→ Building Frida agent...")
    run_cmd("npm install", cwd=AGENT_DIR, wait=True)
    run_cmd("npm run build", cwd=AGENT_DIR, wait=True)

    agent_js = Path(HUB_DIR) / "src" / "freat_server" / "_agent.js"
    if not agent_js.exists():
        print("❌ ERROR: Agent build failed - _agent.js not found")
        sys.exit(1)
    print("✓ Agent built successfully")

    print("\n→ Exporting Godot project...")
    godot_path = find_godot_executable()
    if not godot_path:
        print("❌ ERROR: Godot executable not found")
        print("   Please install Godot 4.4+ or set it in PATH")
        sys.exit(1)

    app_path = BUILD_DIR / "Freat.app"
    export_cmd = f'{godot_path} --headless --export-release "macOS" {app_path}'
    run_cmd(export_cmd, cwd=GUI_DIR, wait=True, shell=True)

    if not app_path.exists():
        print("❌ ERROR: Godot export failed")
        sys.exit(1)
    print("✓ Godot project exported")

    print("\n→ Building Python package...")
    run_cmd("uv build", cwd=HUB_DIR, wait=True)

    dist_dir = Path(HUB_DIR) / "dist"
    wheels = list(dist_dir.glob("*.whl"))
    if not wheels:
        print("❌ ERROR: No wheel file found in dist/")
        sys.exit(1)

    wheel_file = wheels[0]
    print(f"✓ Python package built: {wheel_file.name}")
    print(f"   Install separately with: pip install {wheel_file}")

    print("\n→ Creating DMG...")

    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        capture_output=True,
        text=True,
    )
    version = result.stdout.strip().lstrip("v") if result.returncode == 0 else "0.0.0"

    dmg_name = f"Freat-v{version}-macOS.dmg"
    dmg_path = DIST_DIR / dmg_name

    hdiutil_cmd = f'hdiutil create -volname "Freat" -srcfolder "{app_path}" -ov -format UDZO "{dmg_path}"'
    run_cmd(hdiutil_cmd, wait=True, shell=True, cleanup=False)

    if not dmg_path.exists():
        print("❌ ERROR: DMG creation failed")
        sys.exit(1)

    print(f"✓ DMG created: {dmg_path}")

    dmg_size = dmg_path.stat().st_size / (1024 * 1024)
    print()
    print("=" * 50)
    print("✅ Build Complete!")
    print("=" * 50)
    print()
    print(f"Output: {dmg_path}")
    print(f"Size: {dmg_size:.1f} MB")
    print()
    print("📦 To use Freat:")
    print(f"   1. Install server: pip install {wheel_file}")
    print("   2. Start server: freat-server")
    print("   3. Launch GUI from DMG")
    print()


def main():
    parser = argparse.ArgumentParser(description="freat - an instrumentation toolkit")
    subparser = parser.add_subparsers(dest="command", required=True)
    subparser.add_parser(
        "dev", help="Run all components in live-reload development mode"
    )
    subparser.add_parser("test", help="Run the test suite")
    subparser.add_parser("build", help="Build release package for distribution")

    args = parser.parse_args()

    match args.command:
        case "dev":
            cmd_dev()
        case "test":
            cmd_test()
        case "build":
            cmd_build()
        case _:
            print("Invalid command")


if __name__ == "__main__":
    main()
