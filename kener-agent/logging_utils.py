import logging

def setup_logging(log_level: str = "INFO", log_file: str = None) -> None:
    """
    Set up logging with the specified log level and a standard format.
    Optionally log to a file as well as the console.

    Args:
        log_level: The logging level as a string (e.g., 'DEBUG', 'INFO').
        log_file: Optional path to a log file.
    """
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        print(f"Invalid log level: {log_level}. Defaulting to INFO.")
        numeric_level = logging.INFO

    log_format = "%(asctime)s [%(levelname)s] %(message)s"
    handlers = [logging.StreamHandler()]

    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            handlers.append(file_handler)
        except Exception as e:
            print(f"Failed to set up file logging: {e}")

    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        handlers=handlers
    )
    logging.debug("Logging initialized at level: %s", log_level)
    if log_file:
        logging.debug("Logging to file: %s", log_file)