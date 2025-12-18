"""Main module for running code."""

# Built-Ins
import logging

# Third Party
import caf.toolkit as ctk

# Local Imports
import caf.tem as ct
from caf.tem.inputs import MainConfig

LOG = logging.getLogger(__name__)


def main(params: MainConfig):
    """
    Run TEM model.

    Parameters
    ----------
    params : MainConfig
        The config class for the TEM run. See MainConfig docs.
    """
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
