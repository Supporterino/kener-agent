import argparse
from dataclasses import fields
import logging
from logging_utils import setup_logging
from cli import cmd_login, cmd_apply, cmd_set_default, cmd_list, cmd_version, cmd_list_monitors
from .types import Monitor

def main():
    parser = argparse.ArgumentParser(prog="kener-agent", description="Kener Agent CLI")
    parser.add_argument('--log-level', default='INFO', help='Set log level (DEBUG, INFO, WARNING, ERROR)')
    parser.add_argument('--log-file', help='Optional log file path')
    subparsers = parser.add_subparsers(dest="command", required=True)

    # login command
    login_parser = subparsers.add_parser(
        "login", help="Save API connection settings for an instance"
    )
    login_parser.add_argument(
        "--name", required=True, help="Name of the instance (e.g. dev, prod)"
    )
    login_parser.add_argument("--host", required=True, help="API host, e.g., 10.10.3.1")
    login_parser.add_argument(
        "--port", type=int, default=3000, help="API port, default 3000"
    )
    login_parser.add_argument(
        "--token", required=True, help="Bearer token for API authentication"
    )
    login_parser.add_argument(
        "--folder", required=True, help="Folder containing YAML files to process"
    )
    login_parser.add_argument(
        "--default", action="store_true", help="Set this instance as default"
    )
    login_parser.set_defaults(func=cmd_login)

    # apply command
    apply_parser = subparsers.add_parser("apply", help="Apply monitors from YAML files")
    apply_parser.add_argument("--instance", help="Instance to use (overrides default)")
    apply_parser.add_argument("--folder", help="Optional override folder")
    apply_parser.set_defaults(func=cmd_apply)

    # set-default command
    def_parser = subparsers.add_parser("set-default", help="Set the default instance")
    def_parser.add_argument("name", help="Instance name to set as default")
    def_parser.set_defaults(func=cmd_set_default)

    # list command
    list_parser = subparsers.add_parser("list", help="List all configured instances")
    list_parser.set_defaults(func=cmd_list)

    # list monitors command
    possible_columns = [f.name for f in fields(Monitor)]
    list_monitor_parser = subparsers.add_parser("list-monitors", help="List all configured monitors of an instance")
    list_monitor_parser.add_argument("--columns", nargs="+", help=f"Columns to display. Possible: {', '.join(possible_columns)}", choices=possible_columns, default=["tag", "name", "category_name", "description", "type_data"])
    list_monitor_parser.set_defaults(func=cmd_list_monitors)

    # version
    version_parser = subparsers.add_parser("version", help="Print agent version")
    version_parser.set_defaults(func=cmd_version)

    args = parser.parse_args()
    setup_logging(args.log_level, getattr(args, "log_file", None))
    logging.debug("Parsed arguments: %s", args)

    if not hasattr(args, "func"):
        logging.error("No command specified. Use --help for usage.")
        parser.print_help()
        return

    try:
        logging.debug("Dispatching to command: %s", args.command)
        args.func(args)
    except Exception as e:
        logging.exception("An unexpected error occurred while executing the command: %s", e)
        print(f"Error: {e}")

if __name__ == "__main__":
    main()