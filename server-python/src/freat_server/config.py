import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import platformdirs


@dataclass
class TargetConfig:
    provider: Literal["local", "remote", "wine", "usb", "proton"] = "local"
    options: dict = field(default_factory=dict)


@dataclass
class FreatConfig:
    target: TargetConfig


def load_config() -> FreatConfig:
    config_file = Path(platformdirs.user_config_dir("freat")) / "config.toml"
    if config_file.exists():
        with open(config_file, "rb") as f:
            config = tomllib.load(f)
            target_config = TargetConfig(**config["target"])
            if target_config.provider == "remote":
                if not all(
                    key in target_config.options
                    for key in ["remote_host", "remote_port"]
                ):
                    raise ValueError("host and port are required for remote provider")
            elif target_config.provider == "wine":
                if "wine_prefix" not in target_config.options:
                    raise ValueError("wine_prefix is required for wine provider")
            return FreatConfig(target=target_config)
    else:
        return FreatConfig(target=TargetConfig())
