"""Process Attraction model.

This module defines the AttractionModel class, which estimates and balances trip attractions
for a trip end model. It handles reading input data, applying trip rates, segmenting and
balancing attractions, and exporting results for further analysis.
"""

# -*- coding: utf-8 -*-
# Allow class self type hinting
from __future__ import annotations

# Built-Ins
import logging

# Builtins
import os
import warnings
from typing import Sequence

# Third Party
import caf.base as cb
import caf.toolkit as ctk

# Third party imports
import pandas as pd
from caf.base.segmentation import SegmentationWarning

# Local Imports
from caf.tem import utils
from caf.tem.inputs import (
    AttractionModelPaths,
    AttrParams,
    AttrProto,
    Landuse,
    ProductionModelPaths,
)

LOG = logging.getLogger(__name__)


# pylint: disable="too-few-public-methods"
class AttractionModel(utils.SharedProdAttrMethods[AttrProto]):  # pylint:disable=too-many-instance-attributes
    """
    Estimate and balances trip attractions.

    This class reads land use and trip rate data, applies segmentation and adjustment factors,
    multiplies land use by trip rates to estimate attractions, applies mode-time splits,
    balances attractions to productions, and exports results.

    Parameters
    ----------
    production_model : ProductionModelPaths
        Paths to files or configurations required for the production-side modeling.

    model : AttractionModelPaths
        Paths to input and output resources required by the attraction model.

    trip_rates_paths : dict[int, os.PathLike]
        A dictionary mapping purposes to trip rate DVector file paths.

    trip_rate_adj_path : os.PathLike
        Path to the file containing adjustment factors for trip balancing or calibration.

    balance_production : BalancingZones or bool
        Either a `BalancingZones` object specifying zone-level production constraints,
        or a boolean indicating whether to apply production balancing.

    emp_landuse : dict[int, Landuse]
        Mapping of years to employment-based land use data used for estimating attractions.

    hh_landuse : dict[int, Landuse]
        Mapping of years to household-based land use data for modeling return-home or home-based trips.

    mts_path : os.PathLike
        Path to the mode time split (MTS) file.

    mts_adjustment_path : os.PathLike
        Path to the MTS adjustment factors file, used to adjust trips.

    tem_segmentation : cb.Segmentation
        The final return segmentation.

    mts_uni_path : os.PathLike
        Path to the file containing university-specific MTS data.

    model_zoning : cb.ZoningSystem
        Zoning system used for core modeling (e.g., small area zones, LSOAs, or custom units).

    agg_zoning : cb.ZoningSystem
        Higher-level zoning system used for aggregating outputs (e.g., LA districts or GORs).

    translation : pd.DataFrame
        A DataFrame used to map or translate zone/system identifiers across different zoning systems
        (e.g., from model zones to aggregated zones).

    phi_factors_path : os.PathLike, optional
        Path to the phi factor DVectors used for return home trip generation.

    mts_return_home_path : os.PathLike, optional
        Path to the MTS return-home trip data file.

    mts_return_home_adj_factor_path : os.PathLike, optional
        Path to the file containing return-home adjustment factors.
    """

    def __init__(  # pylint:disable=too-many-arguments,too-many-positional-arguments,too-many-locals
        self,
        params: AttrParams,
        tem_segmentation: cb.Segmentation,
        production_model: ProductionModelPaths,
        model: AttractionModelPaths,
        emp_landuse: dict[int, Landuse],
        hh_landuse: dict[int, Landuse],
        model_zoning: cb.ZoningSystem,
        agg_zoning: cb.ZoningSystem,
        translation: pd.DataFrame,
    ):
        super().__init__(params, tem_segmentation)
        self.production_model = production_model
        self.model = model
        self.trip_rates_paths = params.triprates
        self.emp_landuse = emp_landuse
        self.hh_landuse = hh_landuse
        self.years = list(self.hh_landuse.keys())
        self.tem_segmentation = tem_segmentation
        self.balance_production = params.balance
        self.mts_uni_path = params.mts_uni
        self.model_zoning = model_zoning
        self.agg_zoning = agg_zoning
        self.zone_trans = translation

    def run(  # pylint:disable=too-many-positional-arguments,too-many-locals,too-many-branches
        self,
        export_pure_attractions: bool = True,
        export_tem_segmentation: bool = True,
        export_reports: bool = True,
        mts_geo_constraint: cb.ZoningSystem | None = None,
        return_tripends: bool = False,
    ) -> None:
        """
        Run the HB/NHB Attraction Model.

        For each year, reads input data, applies trip rates, computes attractions,
        applies mode-time splits, balances to productions, and exports results.

        Parameters
        ----------
        export_pure_attractions : bool, default True
            Whether to export the pure attractions to disk.
        export_tem_segmentation : bool, default True
            Whether to export the TEM segmented demand to disk.
        export_reports : bool, default True
            Whether to output reports while running.
        mts_geo_constraint : cb.ZoningSystem or None, default None
            Aggregate zoning to constrain post-MTS adjustment.
        return_tripends : bool, default False
            Whether to produce return home trip ends.

        Returns
        -------
        None
        """
        # ## START ## #

        # ## TEM PRE-REQUISITES ## #
        # If all exports are False, then the run() function is redundant.
        start_time = ctk.timing.current_milli_time()
        LOG.info("Starting attraction Model")
        assert self.production_model.export_paths is not None
        assert self.production_model.report_paths is not None
        assert self.model.export_paths is not None
        assert self.model.report_paths is not None

        if not (export_pure_attractions or export_tem_segmentation or export_reports):
            LOG.info("All exports set to False. Run not executed.")
            end_time = ctk.timing.current_milli_time()
            time_taken = ctk.timing.time_taken(start_time, end_time)
            LOG.info("HB Production Model took:%s", time_taken)
            LOG.info("HB Production Model Finished")
            return None

        # Ensure production balance file exists... (if balance_production is True)
        for year in self.model.path_years:
            if not os.path.exists(
                self.production_model.export_paths.tem_segmented_from_home_pm[year]
            ):
                if not os.path.exists(
                    self.production_model.export_paths.tem_segmented_from_home[year]
                ):
                    raise FileNotFoundError(
                        "The TEM Segmented Productions file is not found. Run the Home Based Production Model to create this file first."
                    )

        # ## CONSTANTS ## #
        report_paths = self.model.report_paths
        export_paths = self.model.export_paths

        # ## READ INPUTS ## #
        # Read in the trip rates DVector files for each purpose. Trip rates are not year dependent.
        trip_rates: dict[int, cb.DVector] = {
            p: self._read_trip_rate(p) for p in self.params.triprates
        }
        # Read in the MTS dvec file. MTS is not year dependent.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=SegmentationWarning)
            mts: cb.DVector = cb.DVector.load(self.params.mts)
            # Read in the adjustment factors, if passed
            adj_factors_dict = self._read_adj_factors()
            if self.params.mts_uni is not None:
                mts_uni = cb.DVector.load(self.mts_uni_path)

                mts_uni = cb.DVector.concat_to_comp_zoning(
                    {
                        0: mts.filter_segment_value("p", 3, keep_filtered=True),
                        1: mts_uni,
                        2: mts_uni,
                    },
                    "uni",
                )
            else:
                mts_uni = None

        # For each year the model is running for...
        for year in self.years:
            # Read in the landuses dvec files specific to the year.
            landuses: dict[str, cb.DVector] = {
                "emp": self.emp_landuse[year]
                .read_landuse(
                    translation=self.zone_trans, model_zoning=self.model_zoning
                )
                .add_segments(["total"]),
                "hh": self.hh_landuse[year]
                .read_landuse(
                    translation=self.zone_trans,
                    init_zoning=cb.ZoningSystem.get_zoning("lsoa_2021"),
                    model_zoning=self.model_zoning,
                )
                .add_segments(["total"]),
            }

            # ## PURE ATTRACTION ## #
            # Create a dictionary of attractions by purpose
            attr_dict: dict[int, cb.DVector] = self._create_attr_dict(
                landuses, trip_rates
            )
            # Adjust trip rate
            attr_dict_adj = self._adjust_attraction_dict(
                attr_dict, adj_factors_dict["tr"]
            )
            # No longer need landuses for the given year
            del landuses
            # Export Pure Attractions
            if export_pure_attractions:
                self._export_pure_attractions(attr_dict, year)
                self._export_pure_attractions(attr_dict_adj, year, adj=True)

            # ## MODE TIME SPLIT ## #
            # Create a dictionary of attractions, with mode time split applied, by purpose
            mts_dict = self._create_mts_dict(attr_dict_adj, mts, mts_uni)
            # Tests to the MTS dict created
            self._check_mts_dict(attr_dict_adj, mts_dict)
            # Apply mts adjustment
            mts_dict_adj = self._adjust_mts_dict(
                mts_dict, adj_factors_dict["mts"], geo_constraint=mts_geo_constraint
            )
            if export_pure_attractions:
                self._export_mts_attractions(mts_dict, year)
                self._export_mts_attractions(mts_dict_adj, year, adj=True)
            # No longer need dictionary of attractions by purpose
            del attr_dict, attr_dict_adj

            # ## SPLIT PRODUCTION SEGMENTATION ## #
            # Load the Adjusted TEM Production from the HB/NHB Production Model Output
            if os.path.exists(
                self.production_model.export_paths.tem_segmented_from_home[year]
            ):
                tem_production = cb.DVector.load(
                    self.production_model.export_paths.tem_segmented_from_home[year]
                )
            if os.path.exists(
                self.production_model.export_paths.tem_segmented_from_home_pm[year]
            ):
                tem_production_pm = cb.DVector.load(
                    self.production_model.export_paths.tem_segmented_from_home_pm[year]
                )
            if (
                mts_dict_adj.keys()
                != tem_production.segmentation.get_segment("p").values.keys()
            ):
                mts_dict_adj = {i + 10: j for i, j in mts_dict_adj.items()}
            # Apply the split_by_other method to the mts DVectors, given the tem_production
            seg_dict = self._create_seg_dict(mts_dict_adj, tem_production)
            # Test all mts_dict DVectors match sum of attr_dict DVectors
            self._check_seg_dict(mts_dict_adj, seg_dict)
            # No longer need dictionary of mts attraction by purpose
            del mts_dict

            # ## TEM SEGMENTATION ## #
            # Take the pure segmentation, and aggregate to the desired TEM segmentation
            tem_dvec = self._create_tem_dvec(seg_dict)
            # Test all mts_dict DVectors match sum of attr_dict DVectors
            seg_dict_sum: float = 0
            for p, v in seg_dict.items():
                seg_dict_sum += v.sum()
            if not tem_dvec.sum_is_close(seg_dict_sum, 0.01, 100):
                LOG.warning(
                    f"The sum of the TEM Segmented segmented attraction (split by TEM Production) does not match the expected sum.\n"
                    f"Expected: {seg_dict_sum}\nGot: {tem_dvec.sum()}"
                )
            # No longer need dictionary of further segmented mts attraction by purpose
            del seg_dict

            # ## BALANCE TO PRODUCTIONS ## #
            balanced_dvec = self._balance_to_production(tem_dvec, tem_production)

            # ## TEM SEGMENTATION EXPORT ## #
            if export_reports:
                LOG.info(
                    f"Writing reports for tem segmented attractions to {report_paths.tem_segmented_from_home}"
                )
                utils.write_reports(
                    balanced_dvec.aggregate_comp_zones(self.model_zoning),
                    report_paths.tem_segmented_from_home,
                    year,
                )

            if export_tem_segmentation:
                LOG.info(
                    f"Saving tem segmented attractions to {export_paths.tem_segmented_from_home[year]}"
                )
                balanced_dvec.save(export_paths.tem_segmented_from_home[year])

            if return_tripends:
                tem_return_home_attr = self.create_tem_return_home(
                    balanced_dvec, "A", self.model_zoning
                )
                tem_return_home_attr = tem_return_home_attr.rename_segment(
                    {"p_return": "p", "tp_return": "tp"}
                )
                tem_return_home_prod = cb.DVector.load(
                    self.production_model.export_paths.tem_segmented_return_home[year]
                )
                agg_seg = [
                    i
                    for i in balanced_dvec.segmentation.naming_order
                    if i not in ["p", "m", "tp"]
                ]
                attr_targ = balanced_dvec.aggregate(agg_seg).aggregate_comp_zones(
                    self.model_zoning
                )
                targets = [
                    cb.data_structures.IpfTarget(data=attr_targ),
                    cb.data_structures.IpfTarget(
                        data=tem_return_home_prod.remove_zoning()
                    ),
                ]
                LOG.info(
                    "Matching return home attractions to from home attractions and "
                    "return home productions via IPF."
                )
                tem_return_home_attr_balanced, _ = tem_return_home_attr.ipf(targets)

                LOG.info(
                    f"Saving return home attractions to {export_paths.tem_segmented_return_home[year]}"
                )
                tem_return_home_attr_balanced.save(
                    export_paths.tem_segmented_return_home[year]
                )

            if self.params.postme_adj_fr is not None:
                LOG.info(
                    f"Applying post me adjustment factors saved here: {self.params.postme_adj_fr}"
                )
                postme_adj_fr_factor= cb.DVector.load(self.params.postme_adj_fr)
                if "direction_od" in postme_adj_fr_factor.segmentation:
                    if self.model.trip_origin == "hb":
                        postme_adj_fr_factor = postme_adj_fr_factor.filter_segment_value(
                            "direction_od", 1
                        )
                    else:
                        postme_adj_fr_factor = postme_adj_fr_factor.filter_segment_value(
                            "direction_od", 0
                        )

                balanced_dvec = balanced_dvec.mul(postme_adj_fr_factor, how="outer")
                # BALANCE TO PRODUCTIONS ## #
                balanced_dvec = self._balance_to_production_pm(
                    balanced_dvec, tem_production_pm
                )
                del tem_production_pm

                # export the adjusted tem segmented attractions from home
                if export_tem_segmentation:
                    LOG.info(
                        f"Saving tem segmented attractions after postme adjustment to {export_paths.tem_segmented_from_home_pm[year]}"
                    )
                    balanced_dvec.save(export_paths.tem_segmented_from_home_pm[year])
            del tem_dvec, mts_dict_adj, tem_production

            if self.params.postme_adj_to is not None:
                LOG.info(
                    f"Applying post me adjustment factors saved here: {self.params.postme_adj_to}"
                )
                postme_adj_to_factor = cb.DVector.load(self.params.postme_adj_to)
                if "direction_od" in postme_adj_to_factor.segmentation:
                    if self.model.trip_origin == "hb":
                        postme_adj_to_factor = postme_adj_to_factor.filter_segment_value(
                            "direction_od", 2
                        )
                    else:
                        postme_adj_to_factor = postme_adj_to_factor.filter_segment_value(
                            "direction_od", 0
                        )

                tem_return_home_attr_pm = tem_return_home_attr_balanced.mul(
                    postme_adj_to_factor, how="outer"
                )
                filters = {'m': postme_adj_to_factor.segmentation.input.subsets['m'],
                           'tp': postme_adj_to_factor.segmentation.input.subsets['tp']}
                
                tem_return_home_attr_pm_adj = tem_return_home_attr_pm.balance_protect_subset(balanced_dvec, self.model_zoning, filters)

                # check that the adjusted prod to home matches prod from home zonal totals
                LOG.info(f"Total after adjustment: {tem_return_home_attr_pm_adj.total:,.2f} (should match total from DVector: {balanced_dvec.total:,.2f})")

                tem_return_home_prod_pm = cb.DVector.load(
                    self.production_model.export_paths.tem_segmented_return_home_pm[year]
                )
                agg_seg = [
                    i
                    for i in balanced_dvec.segmentation.naming_order
                    if i not in ["p", "m", "tp"]
                ]
                attr_targ = balanced_dvec.aggregate(agg_seg).aggregate_comp_zones(
                    self.model_zoning
                )
                targets = [
                    cb.data_structures.IpfTarget(data=attr_targ),
                    cb.data_structures.IpfTarget(data=tem_return_home_prod_pm.remove_zoning()),
                ]
                LOG.info(
                    "Matching return home attractions pm to from home attractions pm and "
                    "return home productions pm via IPF."
                )
                tem_return_home_attr_pm_adj_balanced, _ = tem_return_home_attr_pm_adj.ipf(targets)
                
                if export_tem_segmentation:
                    LOG.info(
                        f"Saving tem segmented attractions after postme adjustment to {export_paths.tem_segmented_return_home_pm[year]}"
                    )
                    tem_return_home_attr_pm_adj_balanced.save(
                        export_paths.tem_segmented_return_home_pm[year]
                    )

    def _read_trip_rate(self, p: int) -> cb.DVector:
        """
        Read one purpose-specific trip rates DVector from the path given in the constructor.

        Parameters
        ----------
        p : int
            Purpose key.

        Returns
        -------
        cb.DVector
            Loaded trip rate vector.
        """
        # Each trip rate file is explicitly defined in the input dictionary by purpose HB Attraction Model, similar assumption for NHB
        LOG.info(f"Loading in purpose {p} trip rates from {self.trip_rates_paths[p]}.")
        if self.trip_rates_paths[p].name.endswith("csv"):
            trip_rate = pd.read_csv(self.trip_rates_paths[p], index_col=0).squeeze()
            trip_rate.index.name = self.agg_zoning.column_name
        else:
            trip_rate = cb.DVector.load(self.trip_rates_paths[p])

        return trip_rate

    def _read_adj_factors(self) -> dict[str, cb.DVector | None]:
        """
        Read trip-rate and MTS adjustment factors.

        Returns
        -------
        dict[str, cb.DVector]
            Dictionary with keys 'tr' and 'mts' for adjustment factors.
        """
        adj_factors_dict: dict[str, cb.DVector | None] = {"tr": None, "mts": None}
        if self.params.tr_adj is not None:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=UserWarning)
                tr = cb.DVector.load(self.params.tr_adj)
            # Ensure zoning system of mts matches the TEM Model zoning system
            tr.fill(0, 1)
            tr.fillna(1)
            adj_factors_dict["tr"] = tr
        if self.params.mts_adj is not None:
            mts = cb.DVector.load(self.params.mts_adj)
            # Ensure zoning system of mts matches the TEM Model zoning system
            mts.fill(0, 1)
            mts.fillna(1)
            mts = mts.add_segments(
                [cb.segmentation.SegmentsSuper("total").get_segment()]
            )
            adj_factors_dict["mts"] = mts

        return adj_factors_dict

    def _adjust_mts_attraction_return_home(
        self,
        mts_production: cb.DVector,
        adj_factors: cb.DVector,
        geo_constraint: cb.ZoningSystem | None = None,
    ) -> cb.DVector:
        """
        Apply adjustment factors to MTS return-home attractions, optionally constrained by geography.

        Parameters
        ----------
        mts_production : cb.DVector
            MTS production vector.
        adj_factors : cb.DVector
            Adjustment factors.
        geo_constraint : cb.ZoningSystem, optional
            Zoning system to constrain adjustment.

        Returns
        -------
        cb.DVector
            Adjusted MTS production vector.
        """
        if adj_factors is None:
            return mts_production

        adj_factors.fill(0, 1)
        adj = mts_production * adj_factors

        numerator = mts_production.aggregate(["p_return"])
        denominator = adj.aggregate(["p_return"])
        if geo_constraint is not None:
            if isinstance(mts_production.zoning_system, Sequence):
                if geo_constraint not in mts_production.zoning_system:
                    raise ValueError(
                        "Geo constraint must be contained in the zoning system"
                    )
            else:
                raise TypeError("Must be multi zoned.")
            numerator = numerator.aggregate_comp_zones(geo_constraint)
            denominator = denominator.aggregate_comp_zones(geo_constraint)
        adj = adj * (numerator / denominator)
        mts_production_adj = adj

        return mts_production_adj

    # Returns a year-specific dictionary of pure demand, for each purpose as the key
    def _create_attr_dict(
        self, landuses: dict[str, cb.DVector], trip_rates: dict[int, cb.DVector]
    ) -> dict[int, cb.DVector]:
        """
        Create the dictionary of pure attractions by purpose.

        Multiplies purpose-specific land use by trip rates, adds purpose segmentation,
        and aggregates as needed.

        Parameters
        ----------
        landuses : dict[str, cb.DVector | dict]
            Land use DVectors for employment and households.
        trip_rates : dict[int, cb.DVector]
            Trip rate DVectors by purpose.

        Returns
        -------
        dict[int, cb.DVector]
            Attractions by purpose.
        """
        LOG.info("Creating pure attractions.")
        # Create an empty dict to store attraction by purpose
        attr_dict: dict[int, cb.DVector] = {}
        # For each purpose...
        for p, trip_rate in trip_rates.items():
            # Access the landuse dvec (employment or household) with respect to travel purpose
            if p not in (7, 17):
                landuse = landuses["emp"]
            else:
                landuse = landuses["hh"]
            # Create the attraction DVector for the given purpose
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=SegmentationWarning)
                attr = landuse * trip_rate
            # Add the purpose segmentation to the DVector segmentation
            attr = attr.add_segments(
                [cb.segmentation.SegmentsSuper("p").get_segment(subset=[p])]
            )
            # Aggregate the attraction DVector to p and soc if soc is in the trip rate segmentation, p segmentation otherwise
            if isinstance(trip_rate, cb.DVector):
                if "soc" in trip_rate.segmentation.names:
                    attr = attr.aggregate(["total", "p", "soc"])
                else:
                    attr = attr.aggregate(["total", "p"])
            else:
                attr = attr.aggregate(["total", "p"])
            attr_dict[p] = attr

        return attr_dict

    def _adjust_attraction_dict(self, attr_dict, adj_factors: cb.DVector | None):
        """
        Apply trip-rate adjustment factors to the attraction dictionary.

        Parameters
        ----------
        attr_dict : dict[int, cb.DVector]
            Dictionary of attractions by purpose.
        adj_factors : cb.DVector
            Adjustment factors.

        Returns
        -------
        dict[int, cb.DVector]
            Adjusted attractions by purpose.
        """
        LOG.info("Adjusting pure attractions.")
        attr_dict_adj: dict[int, cb.DVector] = {}
        if adj_factors is not None:
            for p in attr_dict.keys():
                attr_dict_adj[p] = attr_dict[p] * adj_factors.filter_segment_value(
                    "p", [p]
                )
        else:
            attr_dict_adj = attr_dict

        return attr_dict_adj

    def _export_pure_attractions(
        self, attr_dict: dict[int, cb.DVector], year: int, adj: bool = False
    ) -> None:
        """
        Concatenate the DVectors stored in the Pure Attractions dictionary and save.

        Parameters
        ----------
        attr_dict : dict[int, cb.DVector]
            Attractions by purpose.
        year : int
            Year key.
        adj : bool, default False
            Whether these are adjusted attractions.

        Returns
        -------
        None
        """
        # Concatenate the (optionally balanced) Pure Attraction by purpose
        if self.model.export_paths is None:
            raise ValueError("This shouldn't be possible.")
        output_pure: cb.DVector | None = None
        for p in attr_dict.keys():
            if isinstance(output_pure, cb.DVector):
                output_pure = output_pure.concat(attr_dict[p].aggregate(["p"]))
            else:
                output_pure = attr_dict[p].aggregate(
                    ["p"]
                )  # Initialises the output object
        # Write Pure Attractions
        out_path = self.model.export_paths.pure_demand[year]
        if adj:
            out_path = self.model.export_paths.pure_demand_adj[year]
        assert isinstance(output_pure, cb.DVector)
        LOG.info(f"Saving pure attractions to {out_path}")
        output_pure.save(out_path)

    def _create_mts_dict(
        self,
        attr_dict: dict[int, cb.DVector],
        mts: cb.DVector,
        mts_uni: cb.DVector | None = None,
    ) -> dict[int, cb.DVector]:
        """
        Multiply the attraction DVector with the MTS DVector.

        Parameters
        ----------
        attr_dict : dict[int, cb.DVector]
            Attractions by purpose.
        mts : cb.DVector
            Mode-time split vector.
        mts_uni : cb.DVector or None, optional
            University-specific MTS vector.

        Returns
        -------
        dict[int, cb.DVector]
            MTS-attributed attractions by purpose.
        """
        LOG.info("Applying mode time splits to pure attractions.")
        mts_dict: dict[int, cb.DVector] = {}
        for p, trips in attr_dict.items():
            if mts_uni is None:
                mts_dict[p] = trips * mts
            else:
                # This does change segmentation by design
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", category=SegmentationWarning)
                    if p in mts_uni.segmentation.input.subsets["p"]:
                        mts_dict[p] = trips * mts_uni
                    else:
                        mts_dict[p] = trips * mts

        return mts_dict

    def _check_mts_dict(
        self, attr_dict: dict[int, cb.DVector], mts_dict: dict[int, cb.DVector]
    ) -> None:
        """
        Check that sum of all purpose-specific DVectors match after applying MTS.

        Parameters
        ----------
        attr_dict : dict[int, cb.DVector]
            Attractions by purpose.
        mts_dict : dict[int, cb.DVector]
            MTS-attributed attractions by purpose.

        Returns
        -------
        None
        """
        for p in mts_dict.keys():
            if not mts_dict[p].sum_is_close(attr_dict[p], 0.01, 100):
                LOG.warning(
                    f"The sum of mode-time split, of the Pure Attractions for purpose {p}, does not match the expected sum.\n"
                    f"Expected: {attr_dict[p].sum()}\nGot: {mts_dict[p].sum()}\n"
                )

    def _adjust_mts_dict(
        self,
        mts_dict: dict[int, cb.DVector],
        adj_factors: cb.DVector | None,
        geo_constraint: cb.ZoningSystem | None = None,
    ) -> dict[int, cb.DVector]:
        """
        Apply adjustment factors to MTS-attributed attractions, optionally constrained by geography.

        Parameters
        ----------
        mts_dict : dict[int, cb.DVector]
            MTS-attributed attractions by purpose.
        adj_factors : cb.DVector
            Adjustment factors.
        geo_constraint : cb.ZoningSystem or None, optional
            Zoning system to constrain adjustment.

        Returns
        -------
        dict[int, cb.DVector]
            Adjusted MTS-attributed attractions by purpose.
        """
        mts_dict_adj: dict[int, cb.DVector] = {}
        if adj_factors is not None:
            LOG.info("Adjusting mts attractions.")
            for p, mts in mts_dict.items():
                if "total" not in mts.segmentation.names:
                    mts = mts.add_segments(
                        [cb.segmentation.SegmentsSuper("total").get_segment()]
                    )
                adj_factors.fill(0, 1)
                adj_factors.fillna(1)
                adj = mts * adj_factors
                numerator = mts.aggregate(["p"])
                denominator = adj.aggregate(["p"])
                if geo_constraint is not None:
                    numerator = numerator.aggregate_comp_zones(geo_constraint)
                    denominator = denominator.aggregate_comp_zones(geo_constraint)
                adj = adj * (numerator / denominator)
                mts_dict_adj[p] = adj

        else:
            mts_dict_adj = mts_dict

        return mts_dict_adj

    def _export_mts_attractions(
        self, attr_dict: dict[int, cb.DVector], year: int, adj: bool = False
    ) -> None:
        """
        Concatenate the DVectors stored in the MTS attractions dictionary and save.

        Parameters
        ----------
        attr_dict : dict[int, cb.DVector]
            MTS-attributed attractions by purpose.
        year : int
            Year key.
        adj : bool, default False
            Whether these are adjusted attractions.

        Returns
        -------
        None
        """
        if self.model.export_paths is None:
            raise ValueError("This shouldn't be possible.")
        output_mts: cb.DVector | None = None
        for p in attr_dict.keys():
            if output_mts is not None:
                output_mts = output_mts.concat(attr_dict[p].aggregate(["p", "m", "tp"]))
            else:
                output_mts = attr_dict[p].aggregate(
                    ["p", "m", "tp"]
                )  # Initialises the output object
        # Write MTS Attractions
        out_path = self.model.export_paths.mts_demand[year]
        if adj:
            out_path = self.model.export_paths.mts_demand_adj[year]
        assert output_mts is not None
        LOG.info(f"Saving mts attractions to {out_path}")
        output_mts.save(out_path)

    def _create_seg_dict(
        self, mts_dict: dict[int, cb.DVector], tem_production: cb.DVector
    ) -> dict[int, cb.DVector]:
        """
        Apply the split_by_other method to each DVector in mts_dict.

        Expands the segmentation to match that of TEM Segmented Production.

        Parameters
        ----------
        mts_dict : dict[int, cb.DVector]
            MTS-attributed attractions by purpose.
        tem_production : cb.DVector
            TEM segmented production vector.

        Returns
        -------
        dict[int, cb.DVector]
            Segmented attractions by purpose.
        """
        LOG.info("Matching segmentation to tem_segmented_productions.")
        seg_dict: dict[int, cb.DVector] = {}
        for p, mts in mts_dict.items():
            agg_seg = list(self.tem_segmentation.overlap(mts.segmentation))
            agg_seg.remove("p")
            mts = mts.aggregate(agg_seg)
            seg_dict[p] = mts.split_by_other(
                tem_production.filter_segment_value("p", [p]),
                agg_zone=cb.ZoningSystem.get_zoning("gor"),
            )

        return seg_dict

    def _check_seg_dict(
        self, mts_dict: dict[int, cb.DVector], seg_dict: dict[int, cb.DVector]
    ) -> None:
        """
        Check that the sum of all purpose-specific DVectors match after applying TEM Production Segmentation.

        Parameters
        ----------
        mts_dict : dict[int, cb.DVector]
            MTS-attributed attractions by purpose.
        seg_dict : dict[int, cb.DVector]
            Segmented attractions by purpose.

        Returns
        -------
        None
        """
        for p in seg_dict.keys():
            if not seg_dict[p].sum_is_close(mts_dict[p], 0.01, 100):
                LOG.warning(
                    f"The sum of Segmented MTS Attractions, of the pre-segmented MTS Attractions for purpose {p}, does not match the expected sum.\n"
                    f"Expected: {mts_dict[p].sum()}\nGot: {seg_dict[p].sum()}\n"
                )

    def _create_tem_dvec(self, seg_dict: dict[int, cb.DVector]) -> cb.DVector:
        """
        Concatenate attraction trip-ends at TEM segmentation into a single DVector.

        Parameters
        ----------
        seg_dict : dict[int, cb.DVector]
            Segmented attractions by purpose.

        Returns
        -------
        cb.DVector
            Concatenated TEM-segmented attraction vector.
        """
        tem_dvec: cb.DVector | None = None
        for p in seg_dict.keys():
            if isinstance(tem_dvec, cb.DVector):
                tem_dvec = tem_dvec.concat(seg_dict[p])
            else:
                tem_dvec = seg_dict[p]
        assert tem_dvec is not None
        return tem_dvec

    def _balance_to_production(
        self, tem_dvec: cb.DVector, tem_production: cb.DVector
    ) -> cb.DVector:
        """
        Balance attraction to production based on arguments.

        Parameters
        ----------
        tem_dvec : cb.DVector
            TEM-segmented attraction vector.
        tem_production : cb.DVector
            TEM-segmented production vector.

        Returns
        -------
        cb.DVector
            Balanced attraction vector.
        """
        # If balancing_zones is True
        if self.balance_production is True:
            tem_dvec.fill(0, 1e-16)
            gb_factors = tem_production.remove_zoning() / tem_dvec.remove_zoning()
            balanced_dvec = tem_dvec * gb_factors
        # If zoning is specified for balancing
        elif isinstance(self.balance_production, (cb.BalancingZones, cb.ZoningSystem)):
            balanced_dvec = tem_dvec.balance_by_segments(
                tem_production, self.balance_production
            )
        # If balancing_zones is False
        else:
            balanced_dvec = tem_dvec

        return balanced_dvec

    def _balance_to_production_pm(
        self, tem_dvec: cb.DVector, tem_production: cb.DVector
    ) -> cb.DVector:
        """
        Balance attraction to production based on arguments.

        Parameters
        ----------
        tem_dvec : cb.DVector
            TEM-segmented attraction vector.
        tem_production : cb.DVector
            TEM-segmented production vector.

        Returns
        -------
        cb.DVector
            Balanced attraction vector.
        """
        # If balancing_zones is True
        if self.balance_production is True:
            tem_dvec.fill(0, 1e-16)
            gb_factors = tem_production.remove_zoning().aggregate(
                ["m", "tp", "p"]
            ) / tem_dvec.remove_zoning().aggregate(["m", "tp", "p"])
            balanced_dvec = tem_dvec * gb_factors
        # If zoning is specified for balancing
        elif isinstance(self.balance_production, (cb.BalancingZones, cb.ZoningSystem)):
            balanced_dvec = tem_dvec.balance_by_segments(
                tem_production, self.balance_production
            )
        # If balancing_zones is False
        else:
            balanced_dvec = tem_dvec

        return balanced_dvec
