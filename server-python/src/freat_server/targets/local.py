import frida
from frida.core import Session

from freat_server.targets.base import TargetInfo


class LocalTargetProvider:
    def __init__(self):
        try:
            self.local_device = frida.get_device_manager().get_local_device()
        except Exception as e:
            raise ValueError(f"Failed to connect to remote device: {e}")

    def discover(self) -> list[TargetInfo]:
        processes = []
        for process in self.local_device.enumerate_processes():
            processes.append(TargetInfo(process.pid, process.name, "local", {}))
        return processes

    def attach(self, pid: int) -> Session:
        session = self.local_device.attach(pid)
        return session
