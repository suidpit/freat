import logging
import lzma
import socket
import subprocess
from pathlib import Path
from urllib.request import urlretrieve

import frida
import platformdirs
from frida.core import Session

from freat_server.targets.base import TargetInfo
from freat_server.targets.remote import RemoteTargetProvider

logger = logging.getLogger(__name__)


def get_free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class WineTargetProvider:
    def __init__(self, wine_prefix: str):
        logger.info(f"Initializing WineTargetProvider with prefix: {wine_prefix}")
        self.wine_prefix = wine_prefix
        self.data_dir = self._get_data_dir()
        self.server_path = (
            self.data_dir / f"frida-server-{frida.__version__}-windows-x86_64.exe"
        )
        self.server_port = get_free_port()
        logger.debug(f"Allocated port {self.server_port} for frida-server")
        self.server_process = None
        self._download_binaries()
        self._start_server()
        self.remote_target_provider = RemoteTargetProvider(
            "localhost", self.server_port
        )
        logger.info("WineTargetProvider initialized successfully")

    def download_file(self, url: str, path: Path):
        logger.info(f"Downloading {url}")
        urlretrieve(url, path)
        logger.debug(f"Downloaded to {path}")
        with lzma.open(path, "rb") as f_in:
            self.server_path.write_bytes(f_in.read())
        self.server_path.chmod(0o755)
        path.unlink()
        logger.debug(f"Extracted to {self.server_path}")

    def _get_data_dir(self) -> Path:
        path = Path(platformdirs.user_data_dir("freat-server"))
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _download_binaries(self):
        logger.debug("Checking for required binaries")

        if not self.server_path.exists():
            res = f"frida-server-{frida.__version__}-windows-x86_64.exe.xz"
            server_url = f"https://github.com/frida/frida/releases/download/{frida.__version__}/{res}"
            self.download_file(server_url, Path(res))
        else:
            logger.debug(f"Server already exists at {self.server_path}")

    def _start_server(self):
        logger.info(f"Starting frida-server on port {self.server_port}")
        self.server_process = subprocess.Popen(
            f"wine {self.server_path} --listen 127.0.0.1:{self.server_port}".split(" "),
            env={"WINEPREFIX": self.wine_prefix},
        )
        return_code = self.server_process.poll()
        if return_code is not None and return_code != 0:
            raise RuntimeError(f"Failed to start frida-server: {return_code}")
        logger.debug(f"frida-server started with PID {self.server_process.pid}")

    def discover(self) -> list[TargetInfo]:
        logger.debug("Discovering processes")
        targets = self.remote_target_provider.discover()
        logger.debug(f"Found {len(targets)} processes")
        return targets

    def attach(self, pid: int) -> Session:
        logger.info(f"Attaching to process {pid}")
        session = self.remote_target_provider.attach(pid)
        logger.debug(f"Successfully attached to process {pid}")
        return session
