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
        model = ct.TEM(
            model_years=params.model_years,
            scenario=params.scenario,
            output_zoning=params.output_zoning,
            agg_zoning=params.agg_zoning,
            iteration_name=params.iteration_name,
            export_home=params.export_home,
            return_segmentation=params.return_segmentation,
            trans_file=params.trans_file,
        )
        if params.run_options.run_hb_prod:
            hb_prod = model.hb_production_model(
                population=params.pop, params=params.hb_prod_params
            )
            LOG.info("###### hb production model ######")
            hb_prod.run(
                export_pure_production=params.export_pure,
                export_mts_production=params.export_mts,
                export_tem_segmentation=params.export_tem,
                export_reports=params.export_reports,
                mts_geo_constraint=params.mts_geo_constraint,
                return_tripends=params.run_options.return_home,
            )
        if params.run_options.run_hb_attr:
            hb_attr = model.attraction_model(
                emp_landuse=params.emp, hh_landuse=params.hh, params=params.hb_attr_params
            )
            LOG.info("###### hb attraction model ######")
            hb_attr.run(
                export_pure_attractions=params.export_pure,
                export_tem_segmentation=params.export_tem,
                export_reports=params.export_reports,
                mts_geo_constraint=params.mts_geo_constraint,
                return_tripends=params.run_options.return_home,
            )
        if params.run_options.run_nhb_prod:
            nhb_prod = model.nhb_production_model(params=params.nhb_prod_params)
            LOG.info("###### nhb production model ######")
            nhb_prod.run(
                export_pure_demand=params.export_pure,
                export_tem_segmentation=params.export_tem,
                export_reports=params.export_reports,
            )

        if params.run_options.run_nhb_attr:
            nhb_attr = model.attraction_model(
                emp_landuse=params.emp,
                hh_landuse=params.hh,
                params=params.nhb_attr_params,
                origin="nhb",
            )
            LOG.info("###### nhb attraction model ######")
            nhb_attr.run(
                export_pure_attractions=params.export_pure,
                export_tem_segmentation=params.export_tem,
                export_reports=params.export_reports,
                mts_geo_constraint=params.mts_geo_constraint,
                return_tripends=False,
            )




def main(arg: MainConfig | str | Path | None = None) -> None:
    """Entry point for the console script and programmatic usage.

    Usage (CLI):
        caf.tem /path/to/config.yml

    The only CLI argument accepted is the path to the config YAML file.
    """
    # Called programmatically with a MainConfig instance
    if isinstance(arg, MainConfig):
        _run_from_params(arg)
        return

    # Called programmatically with a path string/Path
    if isinstance(arg, (str, Path)):
        params = MainConfig.load_yaml(arg)
        _run_from_params(params)
        return

    # Called as console script: parse CLI
    parser = argparse.ArgumentParser(description="Run CAF TEM from a config file")
    parser.add_argument(
        "config",
        metavar="CONFIG",
        type=Path,
        help="Path to the YAML configuration file",
    )
    parsed = parser.parse_args(sys.argv[1:])
    try:
        params = MainConfig.load_yaml(str(parsed.config))
    except Exception as exc:  # pragma: no cover - surface configuration errors
        LOG.exception("Failed to load configuration: %s", exc)
        parser.error(str(exc))

    _run_from_params(params)
