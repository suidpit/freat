import frida
from frida.core import Session

from freat_server.targets.base import TargetInfo


class RemoteTargetProvider:
    def __init__(self, remote_host: str, remote_port: int):
        self.remote_host = remote_host
        self.remote_port = remote_port
        try:
            self.remote_device = frida.get_device_manager().add_remote_device(
                f"{self.remote_host}:{self.remote_port}"
            )
        except Exception as e:
            raise ValueError(f"Failed to connect to remote device: {e}")

    def discover(self) -> list[TargetInfo]:
        processes = []
        for process in self.remote_device.enumerate_processes():
            processes.append(TargetInfo(process.pid, process.name, "remote", {}))
        return processes

    def attach(self, pid: int) -> Session:
        session = self.remote_device.attach(pid)
        return session
