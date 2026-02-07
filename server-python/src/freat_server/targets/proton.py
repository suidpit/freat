import logging
import os
from dataclasses import dataclass
from pathlib import Path

from frida.core import Session

from freat_server.targets.base import TargetInfo
from freat_server.targets.wine import WineTargetProvider

logger = logging.getLogger(__name__)

CONTAINER_PREFIX = "/run/host"


def _strip_container_prefix(path: str) -> str:
    if path.startswith(CONTAINER_PREFIX):
        return path[len(CONTAINER_PREFIX) :]
    return path


@dataclass
class ProtonGame:
    app_id: str
    name: str
    wine_prefix: str
    wine_binary: str


class ProtonTargetProvider:
    def __init__(self):
        self.selected_game: ProtonGame | None = None
        self.wine_provider: WineTargetProvider | None = None

    def discover_games(self) -> list[ProtonGame]:
        games: dict[str, ProtonGame] = {}
        uid = os.getuid()
        wine_runtime_dir = Path(f"/tmp/.wine-{uid}")

        if not wine_runtime_dir.exists():
            return []

        # wineserver creates socket dirs here when running,
        # but we need /proc to map back to the actual game
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit():
                continue
            try:
                exe = (entry / "exe").resolve()
                if "wineserver" not in exe.name:
                    continue
                environ = (entry / "environ").read_bytes().decode(errors="replace")
                env = dict(kv.split("=", 1) for kv in environ.split("\0") if "=" in kv)
                if env.get("STEAM_COMPAT_PROTON") != "1":
                    continue

                app_id = env.get("STEAM_COMPAT_APP_ID", "")
                if not app_id or app_id in games:
                    continue

                install_path = env.get("STEAM_COMPAT_INSTALL_PATH", "")
                wine_prefix = env.get("WINEPREFIX", "")
                wine_binary = env.get("WINELOADER", "")

                if not all([wine_prefix, wine_binary]):
                    continue

                # env vars come from inside pressure-vessel's container
                wine_binary = _strip_container_prefix(wine_binary)
                wine_prefix = _strip_container_prefix(wine_prefix)

                games[app_id] = ProtonGame(
                    app_id=app_id,
                    name=Path(install_path).name if install_path else app_id,
                    wine_prefix=wine_prefix,
                    wine_binary=wine_binary,
                )
            except (PermissionError, FileNotFoundError, ProcessLookupError):
                continue

        return list(games.values())

    def select_game(self, app_id: str):
        games = self.discover_games()
        game = next((g for g in games if g.app_id == app_id), None)
        if not game:
            raise ValueError(f"No running Proton game with app_id {app_id}")

        logger.info(f"Selected Proton game: {game.name} ({game.app_id})")
        self.selected_game = game
        self.wine_provider = WineTargetProvider(
            wine_prefix=game.wine_prefix,
            wine_binary=game.wine_binary,
        )

    def discover(self) -> list[TargetInfo]:
        if not self.wine_provider:
            return []
        return self.wine_provider.discover()

    def attach(self, pid: int) -> Session:
        if not self.wine_provider:
            raise RuntimeError("No game selected")
        return self.wine_provider.attach(pid)
