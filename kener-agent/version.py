def get_version() -> str:
    """
    Return the version string for the agent.
    """
    try:
        import importlib.metadata as importlib_metadata
    except ImportError:
        import importlib_metadata  # type: ignore

    try:
        return importlib_metadata.version("kener-agent")
    except importlib_metadata.PackageNotFoundError:
        # fallback for running from source
        try:
            import tomllib
            with open("pyproject.toml", "rb") as f:
                data = tomllib.load(f)
                return data["project"]["version"]
        except Exception:
            return "unknown"