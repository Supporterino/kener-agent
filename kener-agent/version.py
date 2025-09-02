import logging

def get_version() -> str:
    """
    Return the version string for the agent.
    Tries importlib.metadata, then pyproject.toml, then returns 'unknown'.
    """
    try:
        try:
            import importlib.metadata as importlib_metadata
            logging.debug("Using importlib.metadata for version lookup.")
        except ImportError:
            import importlib_metadata  # type: ignore
            logging.debug("Using backported importlib_metadata for version lookup.")

        try:
            version = importlib_metadata.version("kener-agent")
            logging.debug("Found version via importlib: %s", version)
            return version
        except importlib_metadata.PackageNotFoundError:
            logging.warning("Package 'kener-agent' not found in importlib metadata.")

        # fallback for running from source
        try:
            import tomllib
            logging.debug("Trying to read version from pyproject.toml.")
            with open("pyproject.toml", "rb") as f:
                data = tomllib.load(f)
                version = data["project"]["version"]
                logging.debug("Found version in pyproject.toml: %s", version)
                return version
        except Exception as e:
            logging.error("Failed to read version from pyproject.toml: %s", e)

    except Exception as e:
        logging.error("Unexpected error while getting version: %s", e)

    logging.warning("Could not determine version, returning 'unknown'.")
    return "unknown"