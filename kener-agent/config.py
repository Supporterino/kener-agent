from dataclasses import asdict
from pathlib import Path
from typing import Dict, Optional
import yaml
import logging
from .types import Config, ConfigInstance

CONFIG_DIR = Path.home() / ".config" / "kener-agent"
CONFIG_FILE = CONFIG_DIR / "config.yml"

def save_config_instance(
    name: str,
    host: str,
    port: int,
    token: str,
    folder: str,
    set_default: bool = False,
) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            data = yaml.safe_load(f) or {}
        config = Config.from_dict(data)
    else:
        config = Config()

    config.instances[name] = ConfigInstance(host, port, token, folder)
    if set_default or not config.default:
        config.default = name

    with open(CONFIG_FILE, "w") as f:
        yaml.safe_dump(config.to_dict(), f, default_flow_style=False)
    logging.info("Instance '%s' saved to %s", name, CONFIG_FILE)

def load_config(instance: Optional[str] = None) -> ConfigInstance:
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"No config found at {CONFIG_FILE}. Run `login` first.")
    with open(CONFIG_FILE, "r") as f:
        data = yaml.safe_load(f) or {}
    config = Config.from_dict(data)
    if not config.instances:
        raise ValueError("No instances defined in config. Run `login` first.")
    if instance:
        if instance not in config.instances:
            raise ValueError(f"Instance '{instance}' not found in config.")
        return config.instances[instance]
    if not config.default or config.default not in config.instances:
        raise ValueError("No default instance set. Please set one with `set-default`.")
    return config.instances[config.default]

def set_default_instance(name: str) -> None:
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"No config found at {CONFIG_FILE}. Run `login` first.")
    with open(CONFIG_FILE, "r") as f:
        data = yaml.safe_load(f) or {}
    config = Config.from_dict(data)
    if name not in config.instances:
        raise ValueError(f"Instance '{name}' not found in config.")
    config.default = name
    with open(CONFIG_FILE, "w") as f:
        yaml.safe_dump(config.to_dict(), f, default_flow_style=False)
    logging.info("Default instance set to '%s'", name)

def list_instances() -> Dict[str, object]:
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"No config found at {CONFIG_FILE}.")
    with open(CONFIG_FILE, "r") as f:
        data = yaml.safe_load(f) or {}
    config = Config.from_dict(data)
    return {
        "instances": {name: asdict(inst) for name, inst in config.instances.items()},
        "default": config.default
    }