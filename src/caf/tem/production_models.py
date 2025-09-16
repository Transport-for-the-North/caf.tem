"""Process Production model."""

# -*- coding: utf-8 -*-
from __future__ import annotations

# Builtins
import os
import math
import warnings
import logging
import gc
import copy
from collections import namedtuple
from pathlib import Path
import pandas as pd


# Third party imports
import caf.base as cb
from caf.base.segmentation import SegmentationError, SegmentationWarning
import caf.toolkit as ctk
from caf.tem import utils

from caf.tem.inputs import ProductionModelPaths, AttractionModelPaths, Landuse

# pylint: disable =too-many-instance-attributes,too-many-positional-arguments,too-many-locals,too-many-arguments,too-few-public-methods

purpose = cb.segments.SegmentsSuper("p").get_segment()
p_return = purpose.copy()
p_return.name = "p_return"

purpose_hb = purpose.copy()
purpose_hb.values = {i: j for i, j in purpose_hb.values.items() if i < 10}
purpose_hb.name = "p_hb"

purpose_nhb = purpose.copy()
purpose_nhb.values = {i: j for i, j in purpose_nhb.values.items() if i > 10}
purpose_nhb.name = "p_nhb"

time_period = cb.segments.SegmentsSuper("tp").get_segment().copy()
time_period_return = time_period.copy()
time_period_return.name = "tp_return"

mode = cb.segments.SegmentsSuper("m").get_segment().copy()
mode_hb = mode.copy()
mode_hb.name = "m_hb"

mode_nhb = mode.copy()
mode_nhb.name = "m_nhb"

Tuples = namedtuple("segtuple", ["p_return", "p_hb", "p_nhb", "m_hb", "m_nhb", "tp_return"])

SegTuple = Tuples(
    p_return=p_return,
    p_hb=purpose_hb,
    p_nhb=purpose_nhb,
    m_hb=mode_hb,
    m_nhb=mode_nhb,
    tp_return=time_period_return,
)
custom_segments = Tuples._fields


def filter_segments(custom_seg_list, df):
    """
    Filters segment objects by keeping only values present in df_reshaped.

    Parameters
    ----------
    custom_seg_list : list
        List of segment objects (each having .name and .values attributes).
    df : pd.DataFrame
        DataFrame to filter categories against.

    Returns
    -------
    list
        List of filtered segment copies.
    """
    filtered_seg_list = []
    for seg in custom_seg_list:
        seg_copy = copy.deepcopy(seg)
        col_name = seg_copy.name
        seg_unique = set(df[col_name].unique())
        seg_copy.values = {i: j for i, j in seg_copy.values.items() if i in seg_unique}
        filtered_seg_list.append(seg_copy)

    return filtered_seg_list


class HBProductionModel:
    """
    The Home-Based (HB) Production Model class of caf.tem

    Paramaters
    ----------
    model : caf.tem.ProductionModelPaths
        The HB Production Model paths for exporting data.
        These are automatically created in the Trip End Model (TEM), of which this HB Production Model is a child.

    population_paths : Dict[int, os.PathLike]
        Dictionary of {year: population_data_path} pairs.
        Population data should be in DVector format with either .dvec or .hdf extension.

    pop_trans_path : os.Pathlike
        The path to the translation vector between the zoning of the input population DVector and the Trip End Model's Output Zoning.
        The translation vector should be a .csv file.

    trip_rates_path : os.PathLike
        The path to the production trip rates.
        Trip rates data should be in DVector format with either .dvec or .hdf extension.

    trip_rates_adjustment_path : os.PathLike
        TODO description

    mts_path : os.PathLike
        The path to HB production mode-time splits (MTS).
        MTS data should be in DVector format with either .dvec or .hdf extension.

    mts_adjustment_path : os.PathLike
        TODO description

    tem_segmentation : list[str]
        TODO


    """

    def __init__(
        self,
        model: ProductionModelPaths,
        population: dict[int, Landuse],
        trip_rates_path: os.PathLike,
        trip_rate_adjustment_path: os.PathLike,
        mts_path: os.PathLike,
        mts_adjustment_path: os.PathLike,
        tem_segmentation: cb.Segmentation,
        translation: pd.DataFrame,
        phi_factors_path: os.PathLike | None = None,
        mts_return_home_path: os.PathLike | None = None,
        mts_return_home_adj_factor_path: os.PathLike | None = None,
    ):
        """
        - Assigns class attributes
        """
        self.model = model
        self.population = population
        self.trip_rates_path = trip_rates_path
        self.mts_path = mts_path
        self.years = list(self.population.keys())
        self.tem_segmentation = tem_segmentation
        self.trip_rate_adjustment_path = trip_rate_adjustment_path
        self.model_zoning = cb.ZoningSystem.get_zoning(self.model.model_zoning)
        self.agg_zoning = cb.ZoningSystem.get_zoning(self.model.agg_zoning)
        self.phi_factors_path = phi_factors_path
        self.mts_return_home_path = mts_return_home_path
        self.mts_adjust_path = mts_adjustment_path
        self.mts_return_home_adj_factor_path = mts_return_home_adj_factor_path
        self.zone_trans = translation

        _log_fname = "HBProductionModel_log.log"
        logger_name = f"placeholder.{self.__class__.__name__}"
        self._logger = logging.getLogger(logger_name)

    def run(
        self,
        export_pure_production: bool = True,
        export_mts_production: bool = True,
        export_tem_segmentation: bool = True,
        export_reports: bool = True,
        mts_geo_constraint: cb.ZoningSystem = None,
        return_tripends: bool = False,
    ) -> None:
        """
        Runs the HB Production model.

        Completes the following steps for each year:
            - Reads in the land use population data given in the constructor.
            - Reads in the trip rates data given in the constructor.
            - Multiplies the population and trip rates on relevant segments,
              producing "pure demand".
            - Optionally writes out a pickled DVector of "pure demand" at
              self.export_paths.pure_production[year]
            - Optionally writes out a number of "pure demand" reports, if
              reports is True.
            - Reads in the mode-time splits given in the constructor.
            - Multiplies the "pure demand" and mode-time splits on relevant
              segments, producing "fully segmented demand".
            - Optionally writes out a pickled DVector of "fully segmented demand"
              at self.export_paths.fully_segmented[year] if export_fully_segmented
              is True.
            - Aggregates this demand into self._tem_segmentation_name segmentation,
              producing "notem segmented demand".
            - Optionally writes out a number of "notem segmented demand"
              reports, if reports is True.
            - Optionally writes out a pickled DVector of "notem segmented demand"
              at self.export_paths.notem_segmented[year] if export_notem_segmentation
              is True.
            - Finally, returns "notem segmented demand" as a DVector.

        Parameters
        ----------
        export_pure_production:
            Whether to export the pure demand to disk or not.
            Will be written out to: self.export_paths.pure_production[year]

        export_mts_production:
            Whether to export production trip-ends after mode time splits are applied.

        export_tem_segmentation:
            Whether to export the notem segmented demand to disk or not.
            Will be written out to: self.export_paths.notem_segmented[year]

        export_return_home_productions:
            Weather to process return home Productions

        export_reports:
            Whether to output reports while running. All reports will be
            written out to self.report_home.

        Returns
        -------
        None
        """

        # ## START ## #
        start_time = ctk.timing.current_milli_time()
        self._logger.info("Starting HB Production Model")

        # If all exports are False, then the function is redundant
        if not (
            export_pure_production
            or export_tem_segmentation
            or export_mts_production
            or export_reports
        ):
            # End timing TODO move to a function rather than have here, similarly at end of run() method
            self._logger.info(
                "All exports set to False. Run not executed."
            )  # TODO consider running anyway in case user wants to debug.
            end_time = ctk.timing.current_milli_time()
            time_taken = ctk.timing.time_taken(start_time, end_time)
            self._logger.info("HB Production Model took:%s", time_taken)
            self._logger.info("HB Production Model Finished")
            return None

        # ## READ INPUTS ## #
        # Read in the trip rates DVector file. Trip rates are not year dependent.
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
                pure_production.save(self.model.export_paths.pure_demand[year])
                pure_production_adj.save(self.model.export_paths.pure_demand_adj[year])
            if export_reports:
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
                mts_production.save(self.model.export_paths.mts_demand[year])
                mts_production_adj.save(self.model.export_paths.mts_demand_adj[year])
            if export_reports:
                utils.write_reports(mts_production, self.model.report_paths.mts_demand, year)
                utils.write_reports(
                    mts_production_adj, self.model.report_paths.mts_demand_adj, year
                )
            # No longer need Pure Production

            # ## TEM SEGMENTATION ## #
            tem_production = self._create_tem_production(mts_production_adj)
            # Export tem productions
            if export_tem_segmentation:
                # if return_tripends:
                tem_production.save(self.model.export_paths.tem_segmented_from_home[year])
                # else:
                # tem_production.save(self.model.export_paths.tem_segmented[year])
            if export_reports:
                utils.write_reports(
                    mts_production, self.model.report_paths.tem_segmented_from_home, year
                )
            if return_tripends:
                tem_return_home_prod = self._create_tem_return_home_production(tem_production)
                tem_return_home_prod_ = tem_return_home_prod.rename_segment(
                    {"p_return": "p", "tp_return": "tp"}
                )
                tem_return_home_prod_.save(
                    self.model.export_paths.tem_segmented_return_home[year]
                )

            year_end_time = ctk.timing.current_milli_time()
            time_taken = ctk.timing.time_taken(year_start_time, year_end_time)
            self._logger.info("HB Productions in year %s took: %s\n", year, time_taken)

        # End timing
        end_time = ctk.timing.current_milli_time()
        time_taken = ctk.timing.time_taken(start_time, end_time)
        self._logger.info("HB Production Model took:%s", time_taken)
        self._logger.info("HB Production Model Finished")

        return None

    # # # FUNCTIONS # # #

    def _read_trip_rates(self) -> cb.DVector:
        trip_rates = cb.DVector.load(self.trip_rates_path)
        return trip_rates

    def _read_mts(self) -> cb.DVector:
        """
        - Reads the mode-time split (MTS) DVector, from the path given in the constructor
        - Translates the MTS DVector zoning system to the TEM Model zoning system
        """
        mts = cb.DVector.load(self.mts_path)
        # Ensure zoning system of mts matches the TEM Model zoning system
        # zoning_system = cb.ZoningSystem.get_zoning(self.model._zoning_system)
        # mts = mts.translate_zoning(zoning_system, check_totals=False, no_factors=True)

        return mts

    def _read_mts_return_home(self, normalize: bool = True) -> cb.DVector:
        """
        Reads the mode-time split (MTS) DVector, converts it into a normalized share (rho),
        and aligns it with the TEM Model zoning system.

        Parameters
        ----------
        normalize : bool, default=True
            If True, normalize trips within (tfn_at, hh_type, p_return, tp_return).
            If False, normalize trips within (tfn_at, hh_type, p_return).

        Returns
        -------
        cb.DVector
            A DVector containing normalized mode-time splits reshaped by tfn_at.
        """
        # Load the raw DVector
        trips = cb.DVector.load(self.mts_return_home_path)
        trips_data = trips.data.reset_index()

        # Extract segmentation
        segs = trips.segmentation.naming_order
        custom_seg = [seg for seg in segs if seg in custom_segments]
        enum_seg = [seg for seg in segs if seg not in custom_segments]

        # Filter only relevant custom segments
        custom_seg_list = [getattr(SegTuple, seg_name) for seg_name in custom_seg]
        custom_seg_list_filtered = filter_segments(custom_seg_list, trips_data)

        # Reshape 1..20 columns into long format
        mts_data = trips_data.melt(
            id_vars=["hh_type", "p_return", "m", "tp_return"],
            value_vars=list(range(1, 21)),
            var_name="tfn_at",
            value_name="trips",
        )

        # Compute group totals depending on normalization setting
        group_cols = ["tfn_at", "hh_type", "p_return"] + (["tp_return"] if normalize else [])
        mts_data["total_trips"] = mts_data.groupby(group_cols)["trips"].transform("sum")

        # Normalize to proportions
        mts_data["rho"] = mts_data["trips"] / mts_data["total_trips"]

        # Pivot back to wide format (tfn_at as columns, rho as values)
        by_mode_reshaped = mts_data.pivot_table(
            index=["hh_type", "p_return", "tp_return", "m"],
            columns="tfn_at",
            values="rho",
            aggfunc="sum",
        )

        # Wrap result into a new DVector
        mts = cb.DVector(
            segmentation=cb.Segmentation(
                cb.SegmentationInput(
                    enum_segments=enum_seg,
                    naming_order=segs,
                    custom_segments=custom_seg_list_filtered,
                )
            ),
            import_data=by_mode_reshaped,
            zoning_system=trips.zoning_system,
        )

        return mts

    def _read_trip_rate_adjustment(self):
        """Reads in trip rates adjustment factors"""
        if self.trip_rate_adjustment_path is None:
            return None

        self._logger.info("Loading the trip rates adjustment factors")
        adj_factors = cb.DVector.load(self.trip_rate_adjustment_path)

        return adj_factors

    def _read_mts_adjustment(self):
        """Reads in MTS adjustment factors"""
        if self.mts_adjust_path is None:
            return None

        self._logger.info("Loading the MTS adjustment factors")
        adj_factors = cb.DVector.load(self.mts_adjust_path)

        return adj_factors

    def _read_mts_return_home_adjustment(self):
        """Reads in MTS adjustment factors"""
        if self.mts_adjust_path is None:
            return None

        self._logger.info("Loading the MTS adjustment factors for return home")
        adj_factors = cb.DVector.load(self.mts_return_home_adj_factor_path)

        return adj_factors

    def _create_pure_production(
        self, population: cb.DVector, trip_rates: cb.DVector
    ) -> cb.DVector:
        """Creates Pure Production
        - Multiplies the population landuse by the trip rates, creating pure production
        """
        self._logger.info(" Calculating pure production")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=SegmentationWarning)
            pure_production = population * trip_rates

        return pure_production

    def _adjust_production(self, production, adj_factors):
        """Adjusts the Pure Production
        -
        """
        if adj_factors is None:
            return production

        self._logger.info(" Adjusting pure production given trip rate adjustments")
        production_adj = production * adj_factors

        return production_adj

    def _create_mts_production(
        self, pure_production: cb.DVector, mts: cb.DVector
    ) -> cb.DVector:
        """
        - Multiplies the Pure Production by the mode-time split DVector, as passed into the constructor
        """
        self._logger.info(" Applying mode time split")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=SegmentationWarning)
            mts_production = pure_production * mts

        return mts_production

    def _adjust_mts_production(
        self,
        mts_production: cb.DVector,
        adj_factors: cb.DVector,
        geo_constraint: cb.ZoningSystem = None,
    ) -> cb.DVector:
        """ """
        if adj_factors is None:
            return mts_production

        self._logger.info(" Adjusting mode time split")
        adj_factors.fill(0, 1)
        adj = mts_production * adj_factors
        numerator = mts_production.aggregate(["p"])
        denominator = adj.aggregate(["p"])
        if geo_constraint is not None:
            if geo_constraint not in mts_production.zoning_system:
                raise ValueError("Geo constraint must be contained in the zoning system")
            numerator = numerator.aggregate_comp_zones(geo_constraint)
            denominator = denominator.aggregate_comp_zones(geo_constraint)
        adj = adj * (numerator / denominator)
        mts_production_adj = adj

        return mts_production_adj

    def _adjust_mts_production_return_home(
        self,
        mts_production: cb.DVector,
        adj_factors: cb.DVector,
        geo_constraint: cb.ZoningSystem = None,
    ) -> cb.DVector:
        """ """
        if adj_factors is None:
            return mts_production

        self._logger.info(" Adjusting mode time split")
        adj_factors.fill(0, 1)
        adj = mts_production * adj_factors

        numerator = mts_production.aggregate(["p_return"])
        denominator = adj.aggregate(["p_return"])
        if geo_constraint is not None:
            if geo_constraint not in mts_production.zoning_system:
                raise ValueError("Geo constraint must be contained in the zoning system")
            numerator = numerator.aggregate_comp_zones(geo_constraint)
            denominator = denominator.aggregate_comp_zones(geo_constraint)
        adj = adj * (numerator / denominator)
        mts_production_adj = adj

        return mts_production_adj

    def _create_tem_production(self, mts_production: cb.DVector) -> cb.DVector:
        """TEM Production
        - Aggregates MTS Production to TEM Segmentation
        """
        self._logger.info(" Aggregating to TEM Output Segmentation")
        tem_production = mts_production.aggregate(self.tem_segmentation)

        return tem_production

    def _create_tem_return_home_production(self, tem_production: cb.DVector):
        self._logger.info("Processing return home trips")

        # Reading one Phi factor Dvec to get its segmentation
        phi_segmentation = self._read_phi_factor_dvec(1).segmentation.naming_order

        aggregation_segments = list(
            s
            for s in (
                set(self.tem_segmentation)
                ^ set(phi_segmentation)
                # symmetric difference: keep segments that are in only one of the two
            )
            if s
            not in {"m", "tp"}  # manually exclude 'm' and 'tp' even if they are not common
        )

        tem_return_home_tripends_productions = self.return_home_trip_ends(
            tem_production, aggregation_segments
        )
        mts_return_home = self._read_mts_return_home(normalize=True)

        # Check if 'tp_return' exists in either segmentation
        tp_in_tem = "tp_return" in tem_production.segmentation.naming_order
        tp_in_mts = "tp_return" in mts_return_home.segmentation.naming_order

        if not (tp_in_tem or tp_in_mts):
            raise SegmentationError(
                "Segment 'tp_return' (Return Time Period) must be present in either the phi factor DVector or the mode-time split DVector."
            )

        tem_return_home_tripends_production_mts = (
            tem_return_home_tripends_productions * mts_return_home
        )
        mts_return_home_adj = self._read_mts_return_home_adjustment()

        tem_return_home_tripends_production_adj = self._adjust_mts_production_return_home(
            tem_return_home_tripends_production_mts,
            mts_return_home_adj,
            cb.ZoningSystem.get_zoning("gor"),
        )

        return tem_return_home_tripends_production_adj

    def _read_phi_factor_dvec(self, p: int):
        """
        Reads a phi factor DVector file for the given purpose segment.

        Parameters
        ----------
        p : int
            Purpose segment value (e.g., 1 to 8).

        Returns
        -------
        cb.DVector
            Loaded phi factor DVector.

        """
        phi_factors_file_path = Path(
            os.path.join(self.phi_factors_path, f"phi_factors_P_p{p}_reg_phi.dvec")
        )

        if not phi_factors_file_path.exists():
            raise FileNotFoundError(
                f"[ERROR] Phi factor file not found: {phi_factors_file_path}"
            )

        phi_factor = cb.DVector.load(phi_factors_file_path)
        return phi_factor

    def return_home_trip_ends(self, tem_production, agg_segments):
        """
        Computes return-home trip ends by applying phi factors to filtered production vectors,
        then aggregating over the specified segment groups.

        Parameters
        ----------
        tem_production : cb.DVector
            The production DVector containing 'p' as a segment.

        agg_segments : list[str]
            List of segment names to aggregate over (e.g., ['p_return', 'tp_return']).

        Returns
        -------
        cb.DVector
            Aggregated return-home trip ends across all purpose segments.
        """
        trip_ends = None

        for p_val in range(1, 9):
            # Load phi factor for this purpose
            phi = self._read_phi_factor_dvec(p_val)

            # Filter production DVector by current purpose value, keep 'p' segment
            tem_filtered = tem_production.filter_segment_value("p", p_val, keep_filtered=True)

            # Multiply and aggregate
            result = tem_filtered * phi
            result = result.aggregate(segs=agg_segments)

            # Accumulate results
            if trip_ends is None:
                trip_ends = result
            else:
                trip_ends += result

            # Clean up memory
            del phi, tem_filtered, result
            gc.collect()

        return trip_ends


class NHBProductionModel:
    """
    Sets up and validates arguments for the NHB Production model.

    Parameters
    ----------
    hb_attraction_paths:
        Dictionary of {year: notem_segmented_HB_attractions_data} pairs.
        These paths should come from nd.HBAttraction model and should
        be pickled Dvector paths.

    population_paths:
        Dictionary of {year: land_use_population_data} pairs.

    trip_rates_path:
        The path to the NHB production trip rates.
        Should have the columns as defined in:
        NHBProductionModel._target_cols['nhb_trip_rate']

    mts_path:
        The path to NHB production time split.
        Should have the columns as defined in:
        NHBProductionModel._target_cols['tp']

    export_home:
        Path to export NHB Production outputs.

    constraint_paths:
        Dictionary of {year: constraint_path} pairs.
        Must contain the same keys as land_use_paths, but it can contain
        more (any extras will be ignored).
        If set - will be used to constrain the productions - a report will
        be written before and after.

    process_count:
        The number of processes to create in the Pool. Typically this
        should not exceed the number of cores available.
        Defaults to consts.PROCESS_COUNT.
    """

    def __init__(
        self,
        hb_attraction_model: AttractionModelPaths,  # HB Attraction Paths for balancing - not user input - assume these are pure attraction.
        model: ProductionModelPaths,
        trip_rates_path: os.PathLike,
        balance_production,
        mts_path: str,
        return_segmentation,
    ) -> None:

        _log_fname = "HBProductionModel_log.log"
        """The Home-Based Production Model of NoTEM

        The production model can be ran by calling the class run() method.

        Attributes
        ----------
        population_paths: Dict[int, os.PathLike]:
            Dictionary of {year: land_use_employment_data} pairs. As passed
            into the constructor.

        trip_rates_path: str
            The path to the production trip rates. As passed into the constructor.

        mts_path: str
            The path to production mode-time splits. As passed into the
            constructor.

        constraint_paths: Dict[int, os.PathLike]
            Dictionary of {year: constraint_path} pairs. As passed into the
            constructor.

        process_count: int
            The number of processes to create in the Pool. As passed into the
            constructor.

        years: List[int]
            A list of years that the model will run for. Derived from the keys of
            land_use_paths

        See HBProductionModelPaths for documentation on:
            "path_years, export_home, report_home, export_paths, report_paths"
        """

        ## Assign
        self.hb_attraction_model = hb_attraction_model
        self.hb_attraction_paths = hb_attraction_model.export_paths.tem_segmented_from_home
        self.trip_rates_path = trip_rates_path
        self.mts_path = mts_path
        self.balance_production = balance_production
        self.years = list(self.hb_attraction_paths.keys())
        self.model = model
        self.return_segmentation = return_segmentation
        self.model_zoning = cb.ZoningSystem.get_zoning(self.model.model_zoning)
        self.agg_zoning = cb.ZoningSystem.get_zoning(self.model.agg_zoning)

        _log_fname = "NHBProductionModel_log.log"
        logger_name = f"placeholder.{self.__class__.__name__}"
        # log_file_path = Path(self.model.export_home) / _log_fname
        self._logger = logging.getLogger(logger_name)

    #
    def run(
        self,
        export_nhb_pure_demand: bool = True,
        # export_fully_segmented: bool = False,
        export_notem_segmentation: bool = True,
        export_reports: bool = True,
    ) -> None:
        """
        Runs the NHB Production model.

        Completes the following steps for each year:
            - Reads in the notem segmented HB attractions compressed pickle
              given in the constructor.
            - Removes time period segmentation from the above data.
            - Reads in the land use population data given in the constructor,
              extracts the mapping of msoa_zone_id to tfn_at.
            - Reads in the NHB trip rates data given in the constructor.
            - Multiplies the HB attractions and NHB trip rates on relevant segments,
              producing "pure NHB demand".
            - Optionally writes out a pickled DVector of "pure NHB demand" at
              self.export_paths.pure_demand[year]
            - Optionally writes out a number of "pure demand" reports, if
              reports is True.
            - Reads in the time splits given in the constructor.
            - Multiplies the "pure NHB demand" and time splits on relevant
              segments, producing "fully segmented demand".
            - Optionally writes out a pickled DVector of "fully segmented demand"
              at self.export_paths.fully_segmented[year] if export_fully_segmented
              is True.
            - Renames nhb_p and nhb_m as p and m respectively,
              producing "notem segmented demand".
            - Optionally writes out a number of "notem segmented demand"
              reports, if reports is True.
            - Optionally writes out a pickled DVector of "notem segmented demand"
              at self.export_paths.notem_segmented[year] if export_notem_segmentation
              is True.

        Parameters
        ----------
        export_nhb_pure_demand:
            Whether to export the pure NHB demand to disk or not.
            Will be written out to: self.export_paths.pure_demand[year]

        export_fully_segmented:
            Whether to export the fully segmented demand to disk or not.
            Will be written out to: self.export_paths.fully_segmented[year]

        export_notem_segmentation:
            Whether to export the notem segmented demand to disk or not.
            Will be written out to: self.export_paths.notem_segmented[year]

        export_reports:
            Whether to output reports while running. All reports will be
            written out to self.report_home.

        Returns
        -------
        None
        """

        # ## START ## #

        # ## READ INPUTS ## #
        trip_rates = self._read_trip_rates()

        mts = self._read_mts()

        # Generate the nhb productions for each year
        for year in self.years:

            # ## READ HB ATTRACTION ## #
            hbattr = self._read_hb_attraction(year)

            # ## PURE PRODUCTION ## #
            pure_production = self._create_pure_production(hbattr, trip_rates)

            if export_nhb_pure_demand:
                pure_production.save(self.model.export_paths.pure_demand[year])
            if export_reports:
                pass  # self._write_reports(pure_production) # TODO this should be a utils function

            # ## MODE TIME SPLIT ## #
            mts_production = self._create_mts_production(pure_production, mts)

            # ## TEM SEGMENTATION ## #
            # For nhb prod post mts is already tem segmentation

            if export_notem_segmentation:
                mts_production.save(self.model.export_paths.tem_segmented_from_home[year])

    # # # FUNCTIONS # # #

    def _read_trip_rates(self) -> cb.DVector:
        """
        - TODO
        """
        self._logger.info("Loading the trip rates data")
        trip_rates = cb.DVector.load(self.trip_rates_path)

        return trip_rates

    def _read_mts(self) -> cb.DVector:
        """
        - Reads the mode-time split (MTS) DVector, from the path given in the constructor
        - Translates the MTS DVector zoning system to the TEM Model zoning system
        """
        self._logger.info("Loading the mode time split data")
        mts = cb.DVector.load(self.mts_path)

        return mts

    def _read_hb_attraction(self, year: int) -> cb.DVector:
        """
        - Reads the TEM Segmented HB Attraction file, as written by the HB Attraction model
        - Removes time period from the HB Attraction DVector segmentation
        - Changes the purpose and mode segmentations, to explicit home-based purpose and home-based mode segmentations
        """
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
        - TODO
        """
        pure_prod = None
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

        return pure_prod

    def _create_mts_production(
        self, pure_production: cb.DVector, mts: cb.DVector
    ) -> cb.DVector:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=SegmentationWarning)
            mts_production = pure_production * mts
        if not math.isclose(mts_production.sum(), pure_production.sum()):
            warnings.warn("mts has changed the total.")
        return mts_production

    def _generate_nhb_productions(
        self,
        hb_attractions: cb.DVector,
    ) -> cb.DVector:
        """
        -
        Applies NHB trip rates to hb_attractions

        Parameters
        ----------
        hb_attractions:
            Dvector containing the data to apply the trip rates to.

        Returns
        -------
        pure_NHB_demand:
            Returns the product of HB attractions and NHB trip rate Dvector
            ie., pure NHB demand
        """

        # Define the zoning and segmentations we want to use
        nhb_trip_rate_seg = cb.Segmentation(self.tem_segs.trip_rates)
        pure_seg = cb.Segmentation(self.tem_segs.prod_pure)

        # Reading NHB trip rates
        trip_rates_dvec = cb.DVector.load(self.trip_rates_path)
        if trip_rates_dvec.segmentation != nhb_trip_rate_seg:
            raise cb.segmentation.SegmentationError(
                "Unexpected segmentation in trip rates DVector."
            )

        # Multiply
        return (hb_attractions * trip_rates_dvec).aggregate(pure_seg)
