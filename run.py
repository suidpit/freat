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


def get_version() -> str:
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip().lstrip("v") if result.returncode == 0 else "0.0.0"


def cmd_build(platforms: set[str] = {"macos", "linux", "windows"}):
    """Build release package for the specified platforms."""

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

    print("\n→ Exporting Godot project...")
    godot_path = find_godot_executable()
    if not godot_path:
        print("❌ ERROR: Godot executable not found")
        print("   Please install Godot 4.4+ or set it in PATH")
        sys.exit(1)

    version = get_version()
    outputs: list[Path] = []

    # macOS
    if "macos" in platforms:
        app_path = BUILD_DIR / "Freat.app"
        run_cmd(
            f'{godot_path} --headless --export-release "macOS" {app_path}',
            cwd=GUI_DIR, wait=True, shell=True,
        )
        if not app_path.exists():
            print("❌ ERROR: macOS Godot export failed")
            sys.exit(1)
        macos_zip = DIST_DIR / f"Freat-v{version}-macOS.zip"
        shutil.make_archive(str(macos_zip.with_suffix("")), "zip", BUILD_DIR, "Freat.app")
        outputs.append(macos_zip)
        print(f"✓ macOS: {macos_zip.name}")

    # Linux
    if "linux" in platforms:
        linux_binary = BUILD_DIR / "Freat.x86_64"
        run_cmd(
            f'{godot_path} --headless --export-release "Linux" {linux_binary}',
            cwd=GUI_DIR, wait=True, shell=True,
        )
        if not linux_binary.exists():
            print("❌ ERROR: Linux Godot export failed")
            sys.exit(1)
        linux_tar = DIST_DIR / f"Freat-v{version}-Linux.tar.gz"
        shutil.make_archive(str(linux_tar.with_suffix("").with_suffix("")), "gztar",
                            BUILD_DIR, "Freat.x86_64")
        outputs.append(linux_tar)
        print(f"✓ Linux: {linux_tar.name}")

    # Windows
    if "windows" in platforms:
        win_binary = BUILD_DIR / "Freat.exe"
        run_cmd(
            f'{godot_path} --headless --export-release "Windows Desktop" {win_binary}',
            cwd=GUI_DIR, wait=True, shell=True,
        )
        if not win_binary.exists():
            print("❌ ERROR: Windows Godot export failed")
            sys.exit(1)
        win_zip = DIST_DIR / f"Freat-v{version}-Windows.zip"
        shutil.make_archive(str(win_zip.with_suffix("")), "zip", BUILD_DIR, "Freat.exe")
        outputs.append(win_zip)
        print(f"✓ Windows: {win_zip.name}")

    print()
    print("=" * 50)
    print("✅ Build Complete!")
    print("=" * 50)
    print()
    for out in outputs:
        size_mb = out.stat().st_size / (1024 * 1024)
        print(f"  {out.name} ({size_mb:.1f} MB)")
    print()


def main():
    parser = argparse.ArgumentParser(description="freat - an instrumentation toolkit")
    subparser = parser.add_subparsers(dest="command", required=True)
    subparser.add_parser(
        "dev", help="Run all components in live-reload development mode"
    )
    subparser.add_parser("test", help="Run the test suite")
    build_parser = subparser.add_parser("build", help="Build release package for distribution")
    build_parser.add_argument(
        "--platform",
        nargs="+",
        choices=["macos", "linux", "windows"],
        default=["macos", "linux", "windows"],
        help="Platforms to build (default: all)",
    )

    args = parser.parse_args()

    match args.command:
        case "dev":
            cmd_dev()
        case "test":
            cmd_test()
        case "build":
            cmd_build(set(args.platform))
        case _:
            print("Invalid command")


if __name__ == "__main__":
    main()
