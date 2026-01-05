"""Process Production model.

This module defines classes for Home-Based (HB) and Non-Home-Based (NHB) production modeling
within the Trip End Model (TEM) framework. It provides methods for reading input data,
applying trip rates, mode-time splits, adjustments, and exporting results.
"""

# -*- coding: utf-8 -*-
from __future__ import annotations

# Built-Ins
import logging
import math

# Builtins
import warnings
from pathlib import Path
from typing import Sequence

# Third Party
# Third party imports
import caf.base as cb
import caf.toolkit as ctk
import pandas as pd
from caf.base.segmentation import SegmentationWarning

# Local Imports
from caf.tem import utils
from caf.tem.inputs import (
    AttractionModelPaths,
    HBProdParams,
    HBProdProto,
    Landuse,
    NHBProdParams,
    ProductionModelPaths,
)

# pylint: disable=,too-few-public-methods
LOG = logging.getLogger(__name__)


class HBProductionModel(utils.SharedProdAttrMethods[HBProdProto]):
    """
    Home-Based (HB) Production Model for the Trip End Model (TEM).

    This class handles the estimation of home-based trip productions by reading population
    and trip rate data, applying segmentation and adjustment factors, multiplying population
    by trip rates, applying mode-time splits, and exporting results.

    Parameters
    ----------
    model : ProductionModelPaths
        Paths for exporting HB production model data.
    population : dict[int, Landuse]
        Mapping of year to population land use data.
    trip_rates_path : Path
        Path to the production trip rates DVector file.
    trip_rate_adjustment_path : Path
        Path to adjustment factors for trip rates.
    mts_path : Path
        Path to mode-time split (MTS) DVector file.
    mts_adjustment_path : Path
        Path to adjustment factors for MTS.
    tem_segmentation : cb.Segmentation
        Segmentation object for TEM output.
    translation : pd.DataFrame
        DataFrame for translating zone identifiers.
    phi_factors_path : Path, optional
        Path to phi factor files for return-home calculations.
    mts_return_home_path : Path, optional
        Path to MTS return-home DVector file.
    mts_return_home_adj_factor_path : Path, optional
        Path to adjustment factors for MTS return-home.
    """

    def __init__(
        self,
        *,
        params: HBProdParams,
        tem_segmentation: cb.Segmentation,
        model: ProductionModelPaths,
        population: dict[int, Landuse],
        translation: pd.DataFrame,
    ):
        # ## Assign ## #
        super().__init__(params, tem_segmentation=tem_segmentation)
        self.model = model
        self.population = population
        self.years = list(self.population.keys())
        self.tem_segmentation = tem_segmentation
        self.model_zoning = self.model.model_zoning
        self.agg_zoning = self.model.agg_zoning
        self.zone_trans = translation

    def run(
        self,
        *,
        export_pure_production: bool = True,
        export_mts_production: bool = True,
        export_tem_segmentation: bool = True,
        export_reports: bool = True,
        mts_geo_constraint: cb.ZoningSystem | None = None,
        return_tripends: bool = False,
    ) -> None:
        """
        Run the HB Production model for each year.

        This refactor extracts the per-year work into `_run_year` so that `run`
        focuses on configuration and orchestration (reduced local variables).
        """

        start_time = ctk.timing.current_milli_time()
        LOG.info("Starting HB Production Model")

        # If all exports are False, then the function is redundant
        if not (
            export_pure_production
            or export_tem_segmentation
            or export_mts_production
            or export_reports
        ):
            # End timing
            LOG.info("All exports set to False. Run not executed.")
            LOG.info("HB Production Model Finished")
            return None

        # ## READ INPUTS ## #
        # Read in the trip rates DVector file. Trip rates are not year dependent.
        # mypy
        if self.model.export_paths is None or self.model.report_paths is None:
            raise ValueError("model export and report paths are required")
        LOG.info(f"Loading trip rates from {self.params.triprates}")
        trip_rates = cb.DVector.load(self.params.triprates)
        LOG.info(f"Loading mts from {self.params.mts}")
        mts = cb.DVector.load(self.params.mts)
        # Read in the adjustment factors, if passed
        trip_rate_adj_factors: cb.DVector | None = None
        if self.params.tr_adj is not None:
            LOG.info("Loading the trip rates adjustment factors")
            trip_rate_adj_factors = cb.DVector.load(self.params.tr_adj)
        mts_adj_factors: cb.DVector | None = None
        if self.params.mts_adj is not None:
            LOG.info(f"Loading the MTS adjustment factors from {self.params.mts_adj}")
            mts_adj_factors = cb.DVector.load(self.params.mts_adj)

        # Generate the productions for each year
        for year in self.years:
            year_start_time = ctk.timing.current_milli_time()
            self._run_year(
                year=year,
                trip_rates=trip_rates,
                mts=mts,
                trip_rate_adj_factors=trip_rate_adj_factors,
                mts_adj_factors=mts_adj_factors,
                export_pure_production=export_pure_production,
                export_mts_production=export_mts_production,
                export_tem_segmentation=export_tem_segmentation,
                export_reports=export_reports,
                mts_geo_constraint=mts_geo_constraint,
                return_tripends=return_tripends,
            )
            time_taken = ctk.timing.time_taken(
                year_start_time, ctk.timing.current_milli_time()
            )
            LOG.info("HB Productions in year %s took: %s\n", year, time_taken)

        # End timing
        time_taken = ctk.timing.time_taken(start_time, ctk.timing.current_milli_time())
        LOG.info("HB Production Model took:%s", time_taken)
        LOG.info("HB Production Model Finished")

        return None

    def _run_year(
        self,
        *,
        year: int,
        trip_rates: cb.DVector,
        mts: cb.DVector,
        trip_rate_adj_factors: cb.DVector | None,
        mts_adj_factors: cb.DVector | None,
        export_pure_production: bool,
        export_mts_production: bool,
        export_tem_segmentation: bool,
        export_reports: bool,
        mts_geo_constraint: cb.ZoningSystem | None,
        return_tripends: bool,
    ) -> None:
        """Process a single year of HB productions (keyword-only parameters)."""
        population = self.population[year].read_landuse(
            translation=self.zone_trans, model_zoning=self.model_zoning
        )

        # 1) Pure production -> returns TEM-segmented input
        tem_seged = self._create_and_save_pure_production(
            year=year,
            population=population,
            trip_rates=trip_rates,
            trip_rate_adj_factors=trip_rate_adj_factors,
            export_pure_production=export_pure_production,
            export_reports=export_reports,
        )

        # 2) MTS + TEM production -> returns TEM production
        tem_production = self._create_and_save_mts_and_tem_production(
            year=year,
            tem_seged=tem_seged,
            mts=mts,
            mts_adj_factors=mts_adj_factors,
            export_mts_production=export_mts_production,
            export_reports=export_reports,
            export_tem_segmentation=export_tem_segmentation,
            mts_geo_constraint=mts_geo_constraint,
        )

        # 3) Optional return-home
        if return_tripends:
            self._create_and_save_return_home_production(
                year=year, tem_production=tem_production
            )

    def _create_and_save_pure_production(
        self,
        *,
        year: int,
        population: cb.DVector,
        trip_rates: cb.DVector,
        trip_rate_adj_factors: cb.DVector | None,
        export_pure_production: bool,
        export_reports: bool,
    ) -> cb.DVector:
        """Create pure production, optionally save and report, and return TEM-segmented DVector."""
        pure_production = self._create_pure_production(
            population=population, trip_rates=trip_rates
        )
        pure_production_adj = self._adjust_production(
            production=pure_production, adj_factors=trip_rate_adj_factors
        )

        if export_pure_production:
            if self.model.export_paths is None:
                raise ValueError("No export paths.")
            LOG.info(
                "Saving pure hb production trip ends to %s.",
                self.model.export_paths.pure_demand[year],
            )
            pure_production.save(self.model.export_paths.pure_demand[year])
            pure_production_adj.save(self.model.export_paths.pure_demand_adj[year])

        if export_reports:
            if self.model.report_paths is None:
                raise ValueError("No report paths.")
            LOG.info(
                "Writing pure hb production reports to %s", self.model.report_paths.pure_demand
            )
            utils.write_reports(
                pure_production.aggregate_comp_zones(self.model_zoning),
                self.model.report_paths.pure_demand,
                year,
            )
            utils.write_reports(
                pure_production_adj.aggregate_comp_zones(self.model_zoning),
                self.model.report_paths.pure_demand_adj,
                year,
            )

        tem_seged = pure_production_adj.aggregate(
            list(self.tem_segmentation.overlap(pure_production.segmentation))
        )
        return tem_seged

    def _create_and_save_mts_and_tem_production(
        self,
        *,
        year: int,
        tem_seged: cb.DVector,
        mts: cb.DVector,
        mts_adj_factors: cb.DVector | None,
        export_mts_production: bool,
        export_reports: bool,
        export_tem_segmentation: bool,
        mts_geo_constraint: cb.ZoningSystem | None,
    ) -> cb.DVector:
        """Apply MTS, optionally save and report, aggregate to TEM segmentation and return it."""
        mts_production = self._create_mts_production(pure_production=tem_seged, mts=mts)
        mts_production_adj = self._adjust_mts_production(
            mts_production=mts_production,
            adj_factors=mts_adj_factors,
            geo_constraint=mts_geo_constraint,
        )

        if export_mts_production:
            if self.model.export_paths is None:
                raise ValueError("No export paths.")
            LOG.info(
                "Saving hb mts prodcution trip ends to %s",
                self.model.export_paths.mts_demand[year],
            )
            mts_production.save(self.model.export_paths.mts_demand[year])
            mts_production_adj.save(self.model.export_paths.mts_demand_adj[year])

        if export_reports:
            if self.model.report_paths is None:
                raise ValueError("No report paths.")
            LOG.info(
                "Writing mts hb production reports to %s", self.model.report_paths.mts_demand
            )
            utils.write_reports(
                mts_production.aggregate_comp_zones(self.model_zoning),
                self.model.report_paths.mts_demand,
                year,
            )
            utils.write_reports(
                mts_production_adj.aggregate_comp_zones(self.model_zoning),
                self.model.report_paths.mts_demand_adj,
                year,
            )

        LOG.info("Aggregating to TEM Output Segmentation")
        tem_production = mts_production.aggregate(self.tem_segmentation)

        if export_tem_segmentation:
            if self.model.export_paths is None:
                raise ValueError("No export paths.")
            LOG.info(
                "Saving tem segmented hb production trip ends to %s",
                self.model.export_paths.tem_segmented_from_home[year],
            )
            tem_production.save(self.model.export_paths.tem_segmented_from_home[year])

        if export_reports:
            if self.model.report_paths is None:
                raise ValueError("No report paths.")
            LOG.info(
                "Writing tem segmented reports to %s",
                self.model.report_paths.tem_segmented_from_home,
            )
            utils.write_reports(
                tem_production.aggregate_comp_zones(self.model_zoning),
                self.model.report_paths.tem_segmented_from_home,
                year,
            )

        return tem_production

    def _create_and_save_return_home_production(
        self, *, year: int, tem_production: cb.DVector
    ) -> None:
        """Create return-home production outputs and save them."""
        tem_return_home_prod = self.create_tem_return_home(
            tem=tem_production, geo_constraint=self.model_zoning
        )
        tem_return_home_prod_ = tem_return_home_prod.rename_segment(
            {"p_return": "p", "tp_return": "tp"}
        )
        if self.model.export_paths is None:
            raise ValueError("No export paths.")
        LOG.info(
            "Saving hb production return home trip ends to %s",
            self.model.export_paths.tem_segmented_return_home[year],
        )
        tem_return_home_prod_.save(self.model.export_paths.tem_segmented_return_home[year])

    # # # FUNCTIONS # # #

    def _create_pure_production(
        self, *, population: cb.DVector, trip_rates: cb.DVector
    ) -> cb.DVector:
        """
        Create pure production by multiplying population by trip rates.

        Parameters
        ----------
        population : cb.DVector
            Population land use vector.
        trip_rates : cb.DVector
            Trip rates vector.

        Returns
        -------
        cb.DVector
            Pure production vector.
        """
        LOG.info("Calculating pure hb production")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=SegmentationWarning)
            pure_production = population * trip_rates

        return pure_production

    def _adjust_production(self, *, production, adj_factors):
        """
        Adjust pure production using adjustment factors.

        Parameters
        ----------
        production : cb.DVector
            Pure production vector.
        adj_factors : cb.DVector or None
            Adjustment factors.

        Returns
        -------
        cb.DVector
            Adjusted production vector.
        """
        if adj_factors is None:
            return production

        LOG.info(" Adjusting pure production given trip rate adjustments")
        production_adj = production * adj_factors

        return production_adj

    def _create_mts_production(
        self, *, pure_production: cb.DVector, mts: cb.DVector
    ) -> cb.DVector:
        """
        Apply mode-time split to pure production.

        Parameters
        ----------
        pure_production : cb.DVector
            Pure production vector.
        mts : cb.DVector
            Mode-time split vector.

        Returns
        -------
        cb.DVector
            MTS production vector.
        """
        LOG.info("Applying mode time splits")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=SegmentationWarning)
            mts_production = pure_production * mts

        return mts_production

    def _adjust_mts_production(
        self,
        *,
        mts_production: cb.DVector,
        adj_factors: cb.DVector | None,
        geo_constraint: cb.ZoningSystem | None = None,
    ) -> cb.DVector:
        """
        Adjust MTS production using adjustment factors and optional geographic constraint.

        Parameters
        ----------
        mts_production : cb.DVector
            MTS production vector.
        adj_factors : cb.DVector or None
            Adjustment factors.
        geo_constraint : cb.ZoningSystem, optional
            Zoning system for constraining adjustment.

        Returns
        -------
        cb.DVector
            Adjusted MTS production vector.
        """
        if adj_factors is None:
            return mts_production

        LOG.info("Adjusting mode time split")
        adj_factors.fill(0, 1)
        adj = mts_production * adj_factors
        numerator = mts_production.aggregate(["p"])
        denominator = adj.aggregate(["p"])
        if geo_constraint is not None:
            if isinstance(mts_production.zoning_system, Sequence):
                if geo_constraint not in mts_production.zoning_system:
                    raise ValueError("Geo constraint must be contained in the zoning system")
            numerator = numerator.aggregate_comp_zones(geo_constraint)
            denominator = denominator.aggregate_comp_zones(geo_constraint)
        adj = adj * (numerator / denominator)
        mts_production_adj = adj

        if not math.isclose(mts_production.sum(), mts_production_adj.sum()):
            warnings.warn(
                "MTS adjustments have changed the total triprates."
                f"Before = {mts_production.sum()}, after = {mts_production_adj.sum()}"
            )

        return mts_production_adj


class NHBProductionModel:
    """
    Non-Home-Based (NHB) Production Model for the Trip End Model (TEM).

    This class sets up and validates arguments for the NHB production model, reads input data,
    applies trip rates and mode-time splits, and exports results.

    Parameters
    ----------
    hb_attraction_model : AttractionModelPaths
        Paths to HB attraction model outputs for balancing.
    model : ProductionModelPaths
        Paths for exporting NHB production model data.
    trip_rates_path : Path
        Path to NHB production trip rates.
    balance_production : Any
        Balancing configuration or object.
    mts_path : str
        Path to NHB production time split.
    return_segmentation : Any
        Segmentation object for return trips.
    """

    def __init__(
        self,
        *,
        hb_attraction_model: AttractionModelPaths,
        model: ProductionModelPaths,
        params: NHBProdParams,
        return_segmentation: cb.Segmentation,
    ) -> None:
        ## Assign

        self.hb_attraction_model: AttractionModelPaths = hb_attraction_model
        if self.hb_attraction_model.export_paths is None:
            raise ValueError("Mypy whining.")
        self.hb_attraction_paths = (
            self.hb_attraction_model.export_paths.tem_segmented_from_home
        )
        self.trip_rates_path: Path = params.triprates
        self.mts_path: Path = params.mts
        self.years: list[int] = list(self.hb_attraction_paths.keys())
        self.model: ProductionModelPaths = model
        self.return_segmentation: cb.Segmentation = return_segmentation
        self.model_zoning: cb.ZoningSystem = self.model.model_zoning
        self.agg_zoning: cb.ZoningSystem = self.model.agg_zoning

    def run(
        self,
        export_pure_demand: bool = True,
        export_tem_segmentation: bool = True,
        export_reports: bool = True,
    ) -> None:
        """
        Run the NHB Production model for each year.

        Steps:
            - Reads HB attraction data.
            - Removes time period segmentation.
            - Reads NHB trip rates.
            - Multiplies HB attractions by NHB trip rates to create pure NHB demand.
            - Exports pure demand and reports if requested.
            - Applies mode-time splits (MTS).
            - Exports TEM-segmented production if requested.

        Parameters
        ----------
        export_pure_demand : bool
            Export pure NHB demand to disk.
        export_tem_segmentation : bool
            Export TEM-segmented NHB production to disk.
        export_reports : bool
            Output reports during processing.
        """

        # ## START ## #
        if self.model.export_paths is None or self.model.report_paths is None:
            raise ValueError("model export and report paths are required")
        # ## READ INPUTS ## #
        LOG.info(f"Loading the trip rates data from {self.trip_rates_path}")
        trip_rates = cb.DVector.load(self.trip_rates_path)

        LOG.info("Loading the mode time split data from {self.mts_path}")
        mts = cb.DVector.load(self.mts_path)

        # Generate the nhb productions for each year
        for year in self.years:
            # ## READ HB ATTRACTION ## #
            hbattr = self._read_hb_attraction(year=year)

            # ## PURE PRODUCTION ## #
            pure_production = self._create_pure_production(
                hbattr=hbattr, trip_rates=trip_rates
            )

            if export_pure_demand:
                LOG.info(
                    f"Saving pure nhb production trip ends to {self.model.export_paths.pure_demand[year]}"
                )
                pure_production.save(self.model.export_paths.pure_demand[year])
            if export_reports:
                LOG.info(
                    f"Writing reports for nhb productions to {self.model.report_paths.pure_demand}"
                )
                utils.write_reports(
                    pure_production.aggregate_comp_zones(self.model_zoning),
                    self.model.report_paths.pure_demand,
                    year,
                )

            # ## MODE TIME SPLIT ## #
            mts_production = self._create_mts_production(
                pure_production=pure_production, mts=mts
            )

            # ## TEM SEGMENTATION ## #
            # For nhb prod post mts is already tem segmentation

            if export_tem_segmentation:
                LOG.info(
                    f"Saving nhb production trip ends to {self.model.export_paths.tem_segmented_from_home[year]}"
                )
                mts_production.save(self.model.export_paths.tem_segmented_from_home[year])

    def _read_hb_attraction(self, *, year: int) -> cb.DVector:
        """
        Read and process the TEM-segmented HB Attraction file for a given year.

        Removes time period from segmentation and renames segments for NHB processing.

        Parameters
        ----------
        year : int
            Year key.

        Returns
        -------
        cb.DVector
            Processed HB attraction vector.
        """
        assert self.hb_attraction_model.export_paths is not None
        LOG.info(
            f"Loading hb_attraction trip ends from {self.hb_attraction_model.export_paths.tem_segmented_from_home[year]}"
        )
        hbattr = cb.DVector.load(
            self.hb_attraction_model.export_paths.tem_segmented_from_home[year]
        )
        if hbattr.segmentation != self.return_segmentation:
            hbattr = hbattr.aggregate(self.return_segmentation)
        segs = hbattr.segmentation.names
        if "tp" in segs:
            segs.remove("tp")
            hbattr = hbattr.aggregate(segs)
        hbattr = hbattr.rename_segment({"p": "p_hb", "m": "m_hb"})

        return hbattr

    def _create_pure_production(
        self, *, hbattr: cb.DVector, trip_rates: cb.DVector
    ) -> cb.DVector:
        """
        Create pure NHB production by multiplying HB attractions by NHB trip rates.

        Parameters
        ----------
        hbattr : cb.DVector
            HB attraction vector.
        trip_rates : cb.DVector
            NHB trip rates vector.

        Returns
        -------
        cb.DVector
            Pure NHB production vector.
        """
        LOG.info("Multiplying hb attractions by trip rates to produce nhb productions.")
        pure_prod: cb.DVector | None = None
        for p in hbattr.segmentation.get_segment("p_hb").int_values:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=SegmentationWarning)
                pure_prod_p = hbattr.filter_segment_value(
                    "p_hb", p, keep_filtered=False
                ) * trip_rates.filter_segment_value("p_hb", p)

            segs = pure_prod_p.segmentation.names
            segs.remove("m_hb")
            pure_prod_p = pure_prod_p.aggregate(segs)
            pure_prod_p = pure_prod_p.rename_segment({"p_nhb": "p", "m_nhb": "m"})
            if pure_prod is None:
                pure_prod = pure_prod_p
            else:
                pure_prod += pure_prod_p
        assert pure_prod is not None
        return pure_prod

    def _create_mts_production(
        self, *, pure_production: cb.DVector, mts: cb.DVector
    ) -> cb.DVector:
        """
        Apply mode-time split to pure NHB production.

        Parameters
        ----------
        pure_production : cb.DVector
            Pure NHB production vector.
        mts : cb.DVector
            Mode-time split vector.

        Returns
        -------
        cb.DVector
            MTS NHB production vector.
        """
        LOG.info("Applying mode time splits to pure nhb productions.")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=SegmentationWarning)
            mts_production = pure_production * mts
        if not math.isclose(mts_production.sum(), pure_production.sum()):
            warnings.warn(
                f"mts has changed the total. Pre-mts={pure_production.sum()}"
                f"post-mts={mts_production.sum()}.",
                stacklevel=2,
            )
        return mts_production
