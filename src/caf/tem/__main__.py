"""CLI entrypoint for running the TEM using a single config file path.

This module provides a backward-compatible `main` function that also supports being
invoked as a console script (see `pyproject.toml`). When called with no argument it
reads a single positional CLI argument (path to a YAML config file) and runs the
model. When called programmatically with a `MainConfig` instance, it behaves like
the previous implementation.
"""

# Built-Ins
import argparse
import logging
import sys
from pathlib import Path

# Third Party
import caf.toolkit as ctk

# Local Imports
import caf.tem as ct
from caf.tem.inputs import MainConfig

LOG = logging.getLogger(__name__)


def _run_from_params(params: MainConfig) -> None:
    """Run TEM given a validated MainConfig instance."""
    details = ctk.ToolDetails(__package__, ct.__version__)
    with ctk.LogHelper(__package__, details, log_file=params.export_home / "tem.log"):
        ct.run(params)


def main() -> None:
    """Entry point for the console script and programmatic usage.

    Usage (CLI):
        caf.tem /path/to/config.yml

    The only CLI argument accepted is the path to the config YAML file.
    """

    # Called as console script: parse CLI
    parser = argparse.ArgumentParser(description="Run CAF TEM from a config file")
    parser.add_argument(
        "config",
        type=_file_path,
        help="Path to the YAML configuration file",
    )
    parsed = parser.parse_args()
    try:
        params = MainConfig.load_yaml(parsed.config)
    except Exception as exc:  # pragma: no cover - surface configuration errors
        LOG.exception("Failed to load configuration: %s", exc)
        parser.error(str(exc))

    _run_from_params(params)


if __name__ == "__main__":
    main()
