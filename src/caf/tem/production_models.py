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
import os
import warnings
from pathlib import Path
from typing import Sequence

# Third Party
# Third party imports
import caf.base as cb
import caf.toolkit as ctk
import pandas as pd
from caf.base.segmentation import SegmentationWarning
from caf.nts.utils import Tuples

# Local Imports
from caf.tem import utils
from caf.tem.inputs import (
    AttractionModelPaths,
    Landuse,
    ProductionModelPaths,
)

# pylint: disable =too-many-instance-attributes,too-many-positional-arguments,too-many-locals,too-many-arguments,too-few-public-methods

custom_segments = Tuples._fields


class HBProductionModel:
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
    trip_rates_path : os.PathLike
        Path to the production trip rates DVector file.
    trip_rate_adjustment_path : os.PathLike
        Path to adjustment factors for trip rates.
    mts_path : os.PathLike
        Path to mode-time split (MTS) DVector file.
    mts_adjustment_path : os.PathLike
        Path to adjustment factors for MTS.
    tem_segmentation : cb.Segmentation
        Segmentation object for TEM output.
    translation : pd.DataFrame
        DataFrame for translating zone identifiers.
    phi_factors_path : os.PathLike, optional
        Path to phi factor files for return-home calculations.
    mts_return_home_path : os.PathLike, optional
        Path to MTS return-home DVector file.
    mts_return_home_adj_factor_path : os.PathLike, optional
        Path to adjustment factors for MTS return-home.
    """

    def __init__(
        self,
        model: ProductionModelPaths,
        population: dict[int, Landuse],
        trip_rates_path: os.PathLike,
        trip_rate_adjustment_path: os.PathLike | None,
        mts_path: os.PathLike,
        mts_adjustment_path: os.PathLike | None,
        tem_segmentation: cb.Segmentation,
        translation: pd.DataFrame,
        phi_factors_path: Path | None = None,
        mts_return_home_path: os.PathLike | None = None,
        mts_return_home_adj_factor_path: os.PathLike | None = None,
    ):
        # ## Assign ## #
        self.model = model
        self.population = population
        self.trip_rates_path = trip_rates_path
        self.mts_path = mts_path
        self.years = list(self.population.keys())
        self.tem_segmentation = tem_segmentation
        self.trip_rate_adjustment_path = trip_rate_adjustment_path
        self.model_zoning = self.model.model_zoning
        self.agg_zoning = self.model.agg_zoning
        self.phi_factors_path = phi_factors_path
        self.mts_return_home_path = mts_return_home_path
        self.mts_adjust_path = mts_adjustment_path
        self.mts_return_home_adj_factor_path = mts_return_home_adj_factor_path
        self.zone_trans = translation
        self.shared_methods = utils.SharedProdAttrMethods(self)
        self.logger = logging.getLogger(__name__)

    def run(
        self,
        export_pure_production: bool = True,
        export_mts_production: bool = True,
        export_tem_segmentation: bool = True,
        export_reports: bool = True,
        mts_geo_constraint: cb.ZoningSystem | None = None,
        return_tripends: bool = False,
    ) -> None:
        """
        Run the HB Production model for each year.

        Steps:
            - Reads population and trip rates.
            - Multiplies population by trip rates to create pure production.
            - Applies adjustment factors.
            - Exports pure production and reports if requested.
            - Applies mode-time splits (MTS) and adjustments.
            - Exports MTS production and reports if requested.
            - Aggregates to TEM segmentation and exports if requested.
            - Optionally processes return-home trip ends.

        Parameters
        ----------
        export_pure_production : bool
            Export pure production to disk.
        export_mts_production : bool
            Export MTS production to disk.
        export_tem_segmentation : bool
            Export TEM-segmented production to disk.
        export_reports : bool
            Output reports during processing.
        mts_geo_constraint : cb.ZoningSystem, optional
            Zoning system for constraining MTS adjustment.
        return_tripends : bool
            Whether to process return-home productions.

        Returns
        -------
        None
        """

        # ## START ## #
        start_time = ctk.timing.current_milli_time()
        self.logger.info("Starting HB Production Model")

        # If all exports are False, then the function is redundant
        if not (
            export_pure_production
            or export_tem_segmentation
            or export_mts_production
            or export_reports
        ):
            # End timing
            self.logger.info("All exports set to False. Run not executed.")
            end_time = ctk.timing.current_milli_time()
            time_taken = ctk.timing.time_taken(start_time, end_time)
            self.logger.info("HB Production Model took:%s", time_taken)
            self.logger.info("HB Production Model Finished")
            return None

        # ## READ INPUTS ## #
        # Read in the trip rates DVector file. Trip rates are not year dependent.
        # mypy
        assert self.model.export_paths is not None
        assert self.model.report_paths is not None
        trip_rates: cb.DVector = self._read_trip_rates()
        # Read in the MTS dvec file. MTS is not year dependent.
        mts: cb.DVector = self._read_mts()
        # Read in the adjustment factors, if passed
        trip_rate_adj_factors: cb.DVector = self._read_trip_rate_adjustment()
        mts_adj_factors: cb.DVector = self._read_mts_adjustment()

        # Generate the productions for each year
        for year in self.years:
            year_start_time = ctk.timing.current_milli_time()

            # ## READ INPUTS ## #
            # Read in the population land use for the given year
            population = self.population[year].read_landuse(
                translation=self.zone_trans, model_zoning=self.model_zoning
            )

            # ## PURE PRODUCTION ## #
            # Creat pure productions
            pure_production = self._create_pure_production(population, trip_rates)
            # Adjust rate
            pure_production_adj = self._adjust_production(
                pure_production, trip_rate_adj_factors
            )
            # Export pure productions
            if export_pure_production:
                self.logger.info(
                    f"Saving pure hb production trip ends to {self.model.export_paths.pure_demand[year]}."
                )
                pure_production.save(self.model.export_paths.pure_demand[year])
                pure_production_adj.save(self.model.export_paths.pure_demand_adj[year])
            if export_reports:
                self.logger.info(
                    f"Writing pure hb production reports to {self.model.report_paths.pure_demand}"
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

            # ## MODE TIME SPLIT ## #
            tem_seged = pure_production_adj.aggregate(
                list(self.tem_segmentation.overlap(pure_production.segmentation))
            )
            del pure_production, pure_production_adj
            mts_production = self._create_mts_production(
                tem_seged, mts
            )  # Only carry on adj from here
            mts_production_adj = self._adjust_mts_production(
                mts_production, mts_adj_factors, geo_constraint=mts_geo_constraint
            )
            # Export mts production
            if export_mts_production:
                self.logger.info(
                    f"Saving hb mts prodcution trip ends to {self.model.export_paths.mts_demand[year]}"
                )
                mts_production.save(self.model.export_paths.mts_demand[year])
                mts_production_adj.save(self.model.export_paths.mts_demand_adj[year])
            if export_reports:
                self.logger.info(
                    f"Writing mts hb production reports to {self.model.report_paths.mts_demand}"
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
            # No longer need Pure Production

            # ## TEM SEGMENTATION ## #
            tem_production = self._create_tem_production(mts_production_adj)
            # Export tem productions
            if export_tem_segmentation:
                self.logger.info(
                    f"Saving tem segmented hb production trip ends to {self.model.export_paths.tem_segmented_from_home[year]}"
                )
                tem_production.save(self.model.export_paths.tem_segmented_from_home[year])
            if export_reports:
                self.logger.info(
                    f"Writing tem segmented reports to {self.model.report_paths.tem_segmented_from_home}"
                )
                utils.write_reports(
                    tem_production.aggregate_comp_zones(self.model_zoning),
                    self.model.report_paths.tem_segmented_from_home,
                    year,
                )
            if return_tripends:
                tem_return_home_prod = self.shared_methods.create_tem_return_home(
                    tem_production, mts_geo_constraint
                )
                tem_return_home_prod_ = tem_return_home_prod.rename_segment(
                    {"p_return": "p", "tp_return": "tp"}
                )
                self.logger.info(
                    f"Saving hb production return home trip ends to {self.model.export_paths.tem_segmented_return_home[year]}"
                )
                tem_return_home_prod_.save(
                    self.model.export_paths.tem_segmented_return_home[year]
                )

            year_end_time = ctk.timing.current_milli_time()
            time_taken = ctk.timing.time_taken(year_start_time, year_end_time)
            self.logger.info("HB Productions in year %s took: %s\n", year, time_taken)

        # End timing
        end_time = ctk.timing.current_milli_time()
        time_taken = ctk.timing.time_taken(start_time, end_time)
        self.logger.info("HB Production Model took:%s", time_taken)
        self.logger.info("HB Production Model Finished")

        return None

    # # # FUNCTIONS # # #

    def _read_trip_rates(self) -> cb.DVector:
        """
        Read the trip rates DVector from the specified path.

        Returns
        -------
        cb.DVector
            Loaded trip rates vector.
        """
        trip_rates = cb.DVector.load(self.trip_rates_path)
        return trip_rates

    def _read_mts(self) -> cb.DVector:
        """
        Read the mode-time split (MTS) DVector from the specified path.

        Returns
        -------
        cb.DVector
            Loaded MTS vector.
        """
        self.logger.info(f"Loading mts from {self.mts_path}")
        mts = cb.DVector.load(self.mts_path)

        return mts

    def _read_trip_rate_adjustment(self):
        """
        Read trip rate adjustment factors from the specified path.

        Returns
        -------
        cb.DVector or None
            Adjustment factors or None if not provided.
        """
        self.logger.info(
            f"Reading trip rate adjustments from {self.trip_rate_adjustment_path}"
        )
        if self.trip_rate_adjustment_path is None:
            return None

        self.logger.info("Loading the trip rates adjustment factors")
        adj_factors = cb.DVector.load(self.trip_rate_adjustment_path)

        return adj_factors

    def _read_mts_adjustment(self):
        """
        Read MTS adjustment factors from the specified path.

        Returns
        -------
        cb.DVector or None
            Adjustment factors or None if not provided.
        """
        if self.mts_adjust_path is None:
            return None

        self.logger.info(f"Loading the MTS adjustment factors from {self.mts_adjust_path}")
        adj_factors = cb.DVector.load(self.mts_adjust_path)

        return adj_factors

    def _create_pure_production(
        self, population: cb.DVector, trip_rates: cb.DVector
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
        self.logger.info("Calculating pure hb production")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=SegmentationWarning)
            pure_production = population * trip_rates

        return pure_production

    def _adjust_production(self, production, adj_factors):
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

        self.logger.info(" Adjusting pure production given trip rate adjustments")
        production_adj = production * adj_factors

        return production_adj

    def _create_mts_production(
        self, pure_production: cb.DVector, mts: cb.DVector
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
        self.logger.info("Applying mode time splits")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=SegmentationWarning)
            mts_production = pure_production * mts

        return mts_production

    def _adjust_mts_production(
        self,
        mts_production: cb.DVector,
        adj_factors: cb.DVector,
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

        self.logger.info("Adjusting mode time split")
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

    def _create_tem_production(self, mts_production: cb.DVector) -> cb.DVector:
        """
        Aggregate MTS production to TEM segmentation.

        Parameters
        ----------
        mts_production : cb.DVector
            MTS production vector.

        Returns
        -------
        cb.DVector
            TEM-segmented production vector.
        """
        self.logger.info("Aggregating to TEM Output Segmentation")
        tem_production = mts_production.aggregate(self.tem_segmentation)

        return tem_production


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
    trip_rates_path : os.PathLike
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
        hb_attraction_model: AttractionModelPaths,
        model: ProductionModelPaths,
        trip_rates_path: os.PathLike,
        balance_production,
        mts_path: os.PathLike,
        return_segmentation: cb.Segmentation,
    ) -> None:
        ## Assign
        self.hb_attraction_model: AttractionModelPaths = hb_attraction_model
        assert isinstance(self.hb_attraction_model.export_paths, dict)
        self.hb_attraction_paths = (
            self.hb_attraction_model.export_paths.tem_segmented_from_home
        )
        self.trip_rates_path: os.PathLike = trip_rates_path
        self.mts_path: os.PathLike = mts_path
        self.balance_production = balance_production
        self.years: list[int] = list(self.hb_attraction_paths.keys())
        self.model: ProductionModelPaths = model
        self.return_segmentation: cb.Segmentation = return_segmentation
        self.model_zoning: cb.ZoningSystem = self.model.model_zoning
        self.agg_zoning: cb.ZoningSystem = self.model.agg_zoning
        self.logger: logging.Logger = logging.getLogger(__name__)

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

        Returns
        -------
        None
        """

        # ## START ## #
        assert self.model.export_paths is not None
        assert self.model.report_paths is not None
        # ## READ INPUTS ## #
        trip_rates = self._read_trip_rates()

        mts = self._read_mts()

        # Generate the nhb productions for each year
        for year in self.years:
            # ## READ HB ATTRACTION ## #
            hbattr = self._read_hb_attraction(year)

            # ## PURE PRODUCTION ## #
            pure_production = self._create_pure_production(hbattr, trip_rates)

            if export_pure_demand:
                self.logger.info(
                    f"Saving pure nhb production trip ends to {self.model.export_paths.pure_demand[year]}"
                )
                pure_production.save(self.model.export_paths.pure_demand[year])
            if export_reports:
                self.logger.info(
                    f"Writing reports for nhb productions to {self.model.report_paths.pure_demand}"
                )
                utils.write_reports(
                    pure_production.aggregate_comp_zones(self.model_zoning),
                    self.model.report_paths.pure_demand,
                    year,
                )

            # ## MODE TIME SPLIT ## #
            mts_production = self._create_mts_production(pure_production, mts)

            # ## TEM SEGMENTATION ## #
            # For nhb prod post mts is already tem segmentation

            if export_tem_segmentation:
                self.logger.info(
                    f"Saving nhb production trip ends to {self.model.export_paths.tem_segmented_from_home[year]}"
                )
                mts_production.save(self.model.export_paths.tem_segmented_from_home[year])

    # # # FUNCTIONS # # #

    def _read_trip_rates(self) -> cb.DVector:
        """
        Read the NHB trip rates DVector from the specified path.

        Returns
        -------
        cb.DVector
            Loaded NHB trip rates vector.
        """
        self.logger.info(f"Loading the trip rates data from {self.trip_rates_path}")
        trip_rates = cb.DVector.load(self.trip_rates_path)

        return trip_rates

    def _read_mts(self) -> cb.DVector:
        """
        Read the mode-time split (MTS) DVector for NHB production.

        Returns
        -------
        cb.DVector
            Loaded MTS vector.
        """
        self.logger.info("Loading the mode time split data from {self.mts_path}")
        mts = cb.DVector.load(self.mts_path)

        return mts

    def _read_hb_attraction(self, year: int) -> cb.DVector:
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
        self.logger.info(
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
        self, hbattr: cb.DVector, trip_rates: cb.DVector
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
        self.logger.info(
            "Multiplying hb attractions by trip rates to produce nhb productions."
        )
        pure_prod: cb.DVector | None = None
        for p in hbattr.segmentation.get_segment("p_hb").int_values:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=SegmentationWarning)
                pure_prod_p = hbattr.filter_segment_value(
                    "p_hb", p, keep_filtered=False
                ) * trip_rates.filter_segment_value("p_hb", p)

            segs = pure_prod_p.segmentation.names
            # segs.remove("p_hb")
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
        self, pure_production: cb.DVector, mts: cb.DVector
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
        self.logger.info("Applying mode time splits to pure nhb productions.")
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
