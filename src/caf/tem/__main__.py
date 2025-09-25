import logging

import caf.toolkit as ctk

import caf.tem as ct
from caf.tem.inputs import MainConfig

LOG = logging.getLogger(__name__)


def main(params: MainConfig):
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
        if params.run_hb_prod:
            HBProd = model.HBProductionModel(
                population=params.pop,
                trip_rates_path=params.hb_prod_triprates,
                mode_time_splits_path=params.hb_prod_mts,
                adjustment_path=params.hb_prod_tr_adj,
                mts_adj_path=params.hb_prod_mts_adjustment,
                phi_factors_path=params.hb_prod_phi_factors,
                mts_return_home_path=params.hb_prod_mts_return,
                mts_return_home_adj_factor_path=params.hb_prod_mts_return_adj,
            )
            LOG.info("###### hb production model ######")
            HBProd.run(
                export_pure_production=params.export_pure,
                export_mts_production=params.export_mts,
                export_tem_segmentation=params.export_tem,
                export_reports=params.export_reports,
                mts_geo_constraint=params.mts_geo_constraint,
                return_tripends=params.return_home,
            )
        if params.run_hb_attr:
            HBAttr = model.AttractionModel(
                trip_rates_paths=params.hb_attr_triprates,
                emp_landuse=params.emp,
                hh_landuse=params.hh,
                mode_time_splits_path=params.hb_attr_mts,
                balance_production=params.balance_hb,
                trip_rate_adjustment_path=params.hb_attr_tr_adj,
                mode_time_splits_adjustment_path=params.hb_attr_mts_adj,
                mts_uni_path=params.hb_attr_mts_uni,
                mts_return_home_path=params.hb_attr_mts_return,
                mts_return_home_adj_factor_path=params.hb_attr_mts_return_adj,
                phi_factors_path=params.hb_attr_phi_factors,
            )
            LOG.info("###### hb attraction model ######")
            HBAttr.run(
                export_pure_attractions=params.export_pure,
                export_tem_segmentation=params.export_tem,
                export_reports=params.export_reports,
                mts_geo_constraint=params.mts_geo_constraint,
                return_tripends=params.return_home,
            )
        if params.run_nhb_prod:
            NHBProd = model.NHBProductionModel(
                trip_rates_path=params.nhb_prod_triprates,
                mode_time_splits_path=params.nhb_prod_mts,
                balance_production=params.balance_nhb,
            )
            LOG.info("###### nhb production model ######")
            NHBProd.run(
                export_pure_demand=params.export_pure,
                export_tem_segmentation=params.export_tem,
                export_reports=params.export_reports,
            )

        if params.run_nhb_attr:
            NHBAttr = model.AttractionModel(
                trip_rates_paths=params.nhb_attr_triprates,
                emp_landuse=params.emp,
                hh_landuse=params.hh,
                mode_time_splits_path=params.nhb_attr_mts,
                balance_production=params.balance_nhb,
                trip_rate_adjustment_path=params.nhb_attr_tr_adj,
                mode_time_splits_adjustment_path=params.nhb_attr_mts_adj,
                mts_uni_path=params.nhb_attr_mts_uni,
                origin="nhb",
            )
            LOG.info("###### nhb attraction model ######")
            NHBAttr.run(
                export_pure_attractions=params.export_pure,
                export_tem_segmentation=params.export_tem,
                export_reports=params.export_reports,
                mts_geo_constraint=params.mts_geo_constraint,
                return_tripends=False,
            )
