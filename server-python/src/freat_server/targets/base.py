from dataclasses import dataclass
from typing import Literal, Protocol

from frida.core import Session


@dataclass
class TargetInfo:
    pid: int
    name: str
    provider: Literal["local", "remote", "usb", "proton"]
    extras: dict


class TargetProvider(Protocol):
    def discover(self) -> list[TargetInfo]: ...

    def attach(self, pid: int) -> Session: ...
