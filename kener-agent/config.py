from pathlib import Path
from typing import Optional, Dict, Any
import yaml
import logging

CONFIG_DIR = Path.home() / ".config" / "kener-agent"
CONFIG_FILE = CONFIG_DIR / "config.yml"

def save_config(host: str, port: int, token: str, folder: str) -> None:
    """
    Save a simple config (single instance) to the config file.
    """
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        cfg = {"host": host, "port": port, "token": token, "folder": folder}
        with open(CONFIG_FILE, "w") as f:
            yaml.safe_dump(cfg, f, default_flow_style=False)
        logging.info("Configuration saved to %s", CONFIG_FILE)
        logging.debug("Saved config: %s", cfg)
    except Exception as e:
        logging.error("Failed to save config: %s", e)
        raise

def save_instance(
    name: str,
    host: str,
    port: int,
    token: str,
    folder: str,
    set_default: bool = False,
) -> None:
    """
    Save an instance configuration under a given name.
    Optionally set as default.
    """
    if not name or not host or not token or not folder:
        logging.error("Missing required fields for saving instance.")
        raise ValueError("All fields (name, host, token, folder) are required.")

    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r") as f:
                cfg = yaml.safe_load(f) or {}
        else:
            cfg = {}

        cfg.setdefault("instances", {})
        cfg["instances"][name] = {
            "host": host,
            "port": port,
            "token": token,
            "folder": folder,
        }

        if set_default or "default" not in cfg:
            cfg["default"] = name

        with open(CONFIG_FILE, "w") as f:
            yaml.safe_dump(cfg, f, default_flow_style=False)

        logging.info("Instance '%s' saved to %s", name, CONFIG_FILE)
        logging.debug("Saved instance config: %s", cfg)
        if set_default:
            logging.info("Instance '%s' set as default", name)
    except Exception as e:
        logging.error("Failed to save instance: %s", e)
        raise

def load_config(instance: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration for a given instance.
    If no instance is specified, load the default.
    """
    if not CONFIG_FILE.exists():
        logging.error("Config file not found at %s", CONFIG_FILE)
        raise FileNotFoundError(f"No config found at {CONFIG_FILE}. Run `login` first.")

    try:
        with open(CONFIG_FILE, "r") as f:
            cfg = yaml.safe_load(f) or {}
    except Exception as e:
        logging.error("Failed to read config file: %s", e)
        raise

    instances = cfg.get("instances", {})
    if not instances:
        logging.error("No instances defined in config.")
        raise ValueError("No instances defined in config. Run `login` first.")

    if instance:
        if instance not in instances:
            logging.error("Instance '%s' not found in config.", instance)
            raise ValueError(f"Instance '{instance}' not found in config.")
        logging.debug("Loaded config for instance '%s': %s", instance, instances[instance])
        return instances[instance]

    default_instance = cfg.get("default")
    if not default_instance or default_instance not in instances:
        logging.error("No default instance set or default instance missing.")
        raise ValueError("No default instance set. Please set one with `set-default`.")
    logging.debug("Loaded config for default instance '%s': %s", default_instance, instances[default_instance])
    return instances[default_instance]

def set_default_instance(name: str) -> None:
    """
    Set the default instance by name.
    """
    if not CONFIG_FILE.exists():
        logging.error("Config file not found at %s", CONFIG_FILE)
        raise FileNotFoundError(f"No config found at {CONFIG_FILE}. Run `login` first.")

    try:
        with open(CONFIG_FILE, "r") as f:
            cfg = yaml.safe_load(f) or {}
    except Exception as e:
        logging.error("Failed to read config file: %s", e)
        raise

    if "instances" not in cfg or name not in cfg["instances"]:
        logging.error("Instance '%s' not found in config.", name)
        raise ValueError(f"Instance '{name}' not found in config.")

    cfg["default"] = name
    try:
        with open(CONFIG_FILE, "w") as f:
            yaml.safe_dump(cfg, f, default_flow_style=False)
        logging.info("Default instance set to '%s'", name)
        logging.debug("Config after setting default: %s", cfg)
    except Exception as e:
        logging.error("Failed to set default instance: %s", e)
        raise

def list_instances() -> Dict[str, Any]:
    """
    Return all configured instances and the default.
    """
    if not CONFIG_FILE.exists():
        logging.error("Config file not found at %s", CONFIG_FILE)
        raise FileNotFoundError(f"No config found at {CONFIG_FILE}.")

    try:
        with open(CONFIG_FILE, "r") as f:
            cfg = yaml.safe_load(f) or {}
    except Exception as e:
        logging.error("Failed to read config file: %s", e)
        raise

    instances = cfg.get("instances", {})
    default_instance = cfg.get("default")
    logging.debug("Listing instances: %s, default: %s", instances, default_instance)
    return {"instances": instances, "default": default_instance}