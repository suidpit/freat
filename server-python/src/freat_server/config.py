from dataclasses import dataclass, field
from os import environ
from typing import Literal
from urllib.parse import urlparse


@dataclass
class TargetConfig:
    provider: Literal["local", "remote", "wine", "proton"] = "local"
    options: dict = field(default_factory=dict)

    @classmethod
    def from_uri(cls, uri: str) -> "TargetConfig":
        if uri in ["local", "proton"]:
            return cls(provider=uri)  # type: ignore[arg-type]

        parsed = urlparse(uri)
        provider = parsed.scheme

        if provider == "remote":
            host = parsed.hostname
            port = parsed.port
            return cls(provider=provider, options={"host": host, "port": port})

        elif provider == "wine":
            prefix = parsed.path
            return cls(provider=provider, options={"prefix": prefix})
        else:
            raise ValueError(f"Unsupported provider: {provider}")


@dataclass
class FreatConfig:
    target: TargetConfig


def load_config() -> FreatConfig:
    provider_config = environ.get("FREAT_PROVIDER", "local")
    return FreatConfig(target=TargetConfig.from_uri(provider_config))
