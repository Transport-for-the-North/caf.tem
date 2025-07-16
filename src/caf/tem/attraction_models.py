# -*- coding: utf-8 -*-
# Allow class self type hinting
from __future__ import annotations
import logging

# Builtins
import os
import warnings
import pathlib
import math
import glob
import gc

from pathlib import Path

# Third party imports
import pandas as pd

import caf.base as cb
from caf.base.segmentation import SegmentationWarning

from .inputs import ProductionModelPaths, AttractionModelPaths, Landuse

import caf.tem.utils as utils


class AttractionModel:

    def __init__(
        self,
        production_model: ProductionModelPaths,
        model: AttractionModelPaths,
        trip_rates_paths: dict[int, os.PathLike],
        adj_path: os.PathLike,
        balance_production: cb.zoning.BalancingZones | bool,
        emp_landuse: dict[int, Landuse],
        hh_landuse: dict[int, Landuse],
        mts_path: os.PathLike,
        mts_return_home_path:  os.PathLike,
        mts_adjustment_path: os.PathLike,
        mts_return_home_adj_factor_path: os.PathLike,
        phi_factors_path: os.PathLike,
        tem_segmentation: cb.Segmentation,
        mts_uni_path: os.PathLike,
        model_zoning: cb.ZoningSystem,
        agg_zoning: cb.ZoningSystem,
        translation: pd.DataFrame,

    ):
        self.production_model = production_model
        self.model = model
        self.trip_rates_paths = trip_rates_paths
        self.emp_landuse = emp_landuse
        self.hh_landuse = hh_landuse
        self.mts_path = mts_path
        self.mts_return_home_path = mts_return_home_path
        self.phi_factors_path = phi_factors_path
        self.tem_segmentation = tem_segmentation
        self.balance_production = balance_production
        self.tr_adjustment_path = adj_path
        self.mts_adjustment_path = mts_adjustment_path
        self.mts_return_home_adj_factor_path = mts_return_home_adj_factor_path
        self.mts_uni_path = mts_uni_path
        self.model_zoning = model_zoning
        self.agg_zoning = agg_zoning
        self.zone_trans = translation


    def _format_init_paths(
        self,
        trip_rates_paths: dict[int, os.PathLike],
        emp_landuse_paths: dict[int, os.PathLike],
        hh_landuse_dirs: dict[int, os.PathLike],
        hh_landuse_prefix: str,
        mts_path: os.PathLike,
    ) -> tuple[dict[int, Path], dict[int, Path], dict[int, dict[str, Path]], Path]:
        """
        - Ensures all paths in population_paths, trip_rates_path, and mts_path
        """
        # TODO add in trip rates adj and mts adj
        trip_rates_paths: dict[int, Path] = {
            p: Path(path) for p, path in trip_rates_paths.items()
        }
        emp_landuse_paths = {year: Path(file) for year, file in emp_landuse_paths.items()}
        hh_landuse_paths: dict[int, dict[str, Path]] = {
            year: {
                f"{gor}": Path(hh_landuse_dirs[year]) / f"{hh_landuse_prefix}_{gor}.hdf"
                for gor in utils.GOR
            }
            for year in hh_landuse_dirs.keys()
        }
        mts_path = Path(mts_path)

        for p, trip_rates_path in trip_rates_paths.items():
            if not trip_rates_path.is_file():
                raise FileNotFoundError(f"{trip_rates_path} is not a valid file.")
        for year, emp_landuse_path in emp_landuse_paths.items():
            if not emp_landuse_path.is_file():
                raise FileNotFoundError(f"{emp_landuse_path} is not a valid file.")
        for year, hh_landuse_dir in hh_landuse_paths.items():
            for gor, hh_landuse_path in hh_landuse_dir.items():
                if not hh_landuse_path.is_file():
                    raise FileNotFoundError(f"{hh_landuse_path} is not a valid file.")
        if not mts_path.is_file():
            raise FileNotFoundError(f"{hh_landuse_path} is not a valid file.")

        return trip_rates_paths, emp_landuse_paths, hh_landuse_paths, mts_path

    def run(
        self,
        export_pure_attractions: bool = True,
        export_tem_segmentation: bool = True,
        export_reports: bool = True,
        mts_geo_constraint: cb.ZoningSystem | None = None,
        return_tripends: bool = False,
    ) -> None:
        """
        Runs the HB/NHB Attraction Model.

        Completes the following steps for each year:
            - Reads in the employment land use data given in the constructor.
            - Reads in the household land use data given in the constructor.
            - Reads in the trip rates data given in the constructor.
            - Multiplies the purpose-specific landuse and trip rates, producing Attractions.
            - Reduces the attraction segmentation to soc, or otherwise to total if soc is not in the purpose-specific trip rate segmentation.
            - Reads in the mode time split data given in the constructor.
            - Mutiplies the purpose-specific attraction with the mode time split, producing MTS Attraction.
            - Expands the purpose-spcific MTS Attraction segmentation to that of Pure Production, creating "Pure Attraction".
            - Optionally balances "Pure Attractions" to "Pure Production", as exported in the HB/NHB Production Model, producing balanced Pure Attractions.
            - Optionally writes out a DVector of "Pure Attractions" at self.export_paths.pure_demand[year]
            - Optionally writes out a pickled DVector of "TEM Segmented Attractions" at self.export_paths.tem_segmented[year] # TODO TBC whether pickled - fix if so
            - Optionally writes out a number of reports throughout the process.

        Parameters
        ----------
        export_pure_attractions:
            Whether to export the pure attractions to disk or not.
            Will be written out to: self.export_paths.pure_demand[year]

        export_tem_segmentation:
            Whether to export the TEM specified return segmentation demand to disk or not.
            Will be written out to: self.export_paths.tem_segmented[year]

        export_reports:
            Whether to output reports while running. All reports will be
            written out to self.report_home

        Returns
        -------
        None
        """
        # ## START ## #

        # ## TEM PRE-REQUISITES ## #
        # If all exports are False, then the run() function is redundant.
        if not (export_pure_attractions or export_tem_segmentation or export_reports):
            raise IOError(
                "The code has been terminated. All HB Attraction Model exports are set to False, running the HB Attraction Model is redundant."
            )

        # Ensure production balance file exists... (if balance_production is True)
        for year in self.model.path_years:
            if not os.path.exists(self.production_model.export_paths.tem_segmented[year]):
                raise FileNotFoundError(
                    "The TEM Segmented Productions file is not found. Run the Home Based Production Model to create this file first."
                )

        # ## CONSTANTS ## #
        report_paths = self.model.report_paths
        export_paths = self.model.export_paths

        # ## READ INPUTS ## #
        # Read in the trip rates DVector files for each purpose. Trip rates are not year dependent.
        trip_rates: dict[int, cb.DVector] = {
            p: self._read_trip_rate(p) for p in self.trip_rates_paths
        }
        # Read in the MTS dvec file. MTS is not year dependent.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=SegmentationWarning)
            mts: cb.DVector = cb.DVector.load(self.mts_path)
            # Read in the adjustment factors, if passed
            adj_factors_dict: dict[str, cb.DVector] = (
                self._read_adj_factors()
            )  # TODO move to utils bc. both attraction and production use this?
            if self.mts_uni_path is not None:
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
        for (
            year
        ) in (
            self.emp_landuse.keys()
        ):  # -> TODO is this the correct iterable, path_years or keys of emp landuse? - or check path_years = dict keys of emp_landuse and hh_landuse. What if p7 isn't being tested, wouldn't need hh_landuse...

            # Read in the landuses dvec files specific to the year.
            landuses: dict[str, cb.DVector | dict[str, cb.DVector]] = {
                "emp": self.emp_landuse[year]
                .read_landuse(translation=self.zone_trans, model_zoning=self.model_zoning)
                .add_segments(["total"]),
                "hh": self.hh_landuse[year]
                .read_landuse(translation=self.zone_trans, model_zoning=self.model_zoning)
                .add_segments(["total"]),
            }

            # ## PURE ATTRACTION ## #
            # Create a dictionary of attractions by purpose
            attr_dict: dict[int, cb.DVector] = self._create_attr_dict(landuses, trip_rates)
            # Adjust trip rate
            attr_dict_adj = self._adjust_attraction_dict(attr_dict, adj_factors_dict["tr"])
            # No longer need landuses for the given year
            del landuses
            # Export Pure Attractions
            if export_pure_attractions:
                self._export_pure_attractions(attr_dict, year)
                self._export_pure_attractions(attr_dict_adj, year, adj=True)

            # ## MODE TIME SPLIT ## #
            # Create a dictionary of attractions, with mode time split applied, by purpose
            mts_dict = self._create_mts_dict(attr_dict_adj, mts, mts_uni)
            # Tests to the MTS dict created - TODO confirm rel/abs tolerance w Isaac for this test.
            self._check_mts_dict(attr_dict_adj, mts_dict)
            # Apply mts adjustment
            mts_dict_adj = self._adjust_mts_dict(
                mts_dict, adj_factors_dict["mts"], geo_constraint=mts_geo_constraint
            )  # TODO do I want an mts_dict_adj variable and/or output? To ask Isaac
            if export_pure_attractions:
                self._export_mts_attractions(mts_dict, year)
                self._export_mts_attractions(mts_dict_adj, year, adj=True)
            # No longer need dictionary of attractions by purpose
            del attr_dict, attr_dict_adj

            # ## SPLIT PRODUCTION SEGMENTATION ## #
            # Load the Adjusted TEM Production from the HB/NHB Production Model Output

            tem_production = cb.DVector.load(
                self.production_model.export_paths.tem_segmented[year]
            )  # TODO confirm not tem_segmented_adj i.e. are ==
            if (
                mts_dict_adj.keys()
                != tem_production.segmentation.get_segment("p").values.keys()
            ):
                mts_dict_adj = {i + 10: j for i, j in mts_dict_adj.items()}
            # Apply the split_by_other method to the mts DVectors, given the tem_production
            seg_dict = self._create_seg_dict(mts_dict_adj, tem_production)
            # Test all mts_dict DVectors match sum of attr_dict DVectors - TODO confirm rel/abs tolerance w Isaac for this test.
            self._check_seg_dict(mts_dict_adj, seg_dict)
            # No longer need dictionary of mts attraction by purpose
            del mts_dict

            # ## TEM SEGMENTATION ## #
            # Take the pure segmentation, and aggregate to the desired TEM segmentation
            tem_dvec = self._create_tem_dvec(seg_dict)
            # Test all mts_dict DVectors match sum of attr_dict DVectors - TODO confirm rel/abs tolerance w Isaac for this test.
            seg_dict_sum: float = 0
            for p in seg_dict.keys():
                seg_dict_sum += seg_dict[p].sum()
            if not tem_dvec.sum_is_close(seg_dict_sum, 0.01, 100):
                print(
                    f"The sum of the TEM Segmented segmented attraction (split by TEM Production) does not match the expected sum.\n"
                    f"Expected: {seg_dict[p].sum()}\nGot: {seg_dict[p].sum()}"
                )
            # No longer need dictionary of further segmented mts attraction by purpose
            del seg_dict

            # ## BALANCE TO PRODUCTIONS ## #
            balanced_dvec = self._balance_to_production(tem_dvec, tem_production)
            del tem_dvec, mts_dict_adj, tem_production

            # ## TEM SEGMENTATION EXPORT ## #
            if export_reports:
                utils.write_reports(
                    balanced_dvec.aggregate_comp_zones(self.model_zoning),
                    report_paths.tem_segmented,
                    year,
                )
            if export_tem_segmentation:
                if return_tripends:
                    balanced_dvec.save(export_paths.tem_segmented_from_home[year])
                else:
                    balanced_dvec.save(export_paths.tem_segmented[year])
            if return_tripends:
                tem_return_home_attr = self._create_tem_return_home_attraction(balanced_dvec)
                tem_return_home_attr.save(export_paths.tem_segmented_return_home[year])

        # ## END ## #
        return None

    # # # HELPER FUNCTIONS # # #

    def _read_trip_rate(self, p: int) -> cb.DVector:
        """
        - Reads one purpose-specific trip rates DVector, from the path given in the constructor
        - Translates the trip rates DVector zoning system to the TEM Model zoning system
        """
        # Each trip rate file is explicitly defined in the input dictionary by purpose HB Attraction Model, similar assumption for NHB
        if self.trip_rates_paths[p].endswith("csv"):
            trip_rate = pd.read_csv(self.trip_rates_paths[p], index_col=0).squeeze()
            trip_rate.index.name = self.agg_zoning.column_name
        else:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=SegmentationWarning)
                trip_rate = cb.DVector.load(self.trip_rates_paths[p])

        return trip_rate

    def _read_mts(self) -> cb.DVector:
        """
        - Reads the mode-time split (MTS) DVector, from the path given in the constructor
        - Translates the MTS DVector zoning system to the TEM Model zoning system
        """
        mts = cb.DVector.load(self.mts_path)
        # Ensure zoning system of mts matches the TEM Model zoning system
        # zoning_system = cb.ZoningSystem.get_zoning(self.model_zoning)
        # mts = mts.translate_zoning(zoning_system, check_totals=False, no_factors=True)

        return mts

    def _read_mts_return_home(self) -> cb.DVector:
        """
        - Reads the mode-time split (MTS) DVector, from the path given in the constructor
        - Translates the MTS DVector zoning system to the TEM Model zoning system
        """
        mts = cb.DVector.load(self.mts_return_home_path)

        return mts

    def _read_adj_factors(self) -> dict[str, cb.DVector]:
        """ """
        adj_factors_dict: dict[str, cb.DVector] = {"tr": None, "mts": None}
        if self.tr_adjustment_path is not None:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=UserWarning)
                tr = cb.DVector.load(self.tr_adjustment_path)
            # Ensure zoning system of mts matches the TEM Model zoning system
            tr = tr.translate_zoning(self.model_zoning, check_totals=False, no_factors=True)
            tr.fill(0, 1)
            tr.fillna(1)
            adj_factors_dict["tr"] = tr
        if self.mts_adjustment_path is not None:
            mts = cb.DVector.load(self.mts_adjustment_path)
            # Ensure zoning system of mts matches the TEM Model zoning system
            mts.fill(0, 1)
            mts.fillna(1)
            mts = mts.add_segments([cb.segmentation.SegmentsSuper("total").get_segment()])
            adj_factors_dict["mts"] = mts

        return adj_factors_dict

    def _read_mts_return_home_adjustment(self):
        """Reads in MTS adjustment factors"""
        if self.mts_return_home_adj_factor_path is None:
            return None

        adj_factors = cb.DVector.load(self.mts_return_home_adj_factor_path)

        return adj_factors

    def _adjust_mts_attraction_return_home(
            self,
            mts_production: cb.DVector,
            adj_factors: cb.DVector,
            geo_constraint: cb.ZoningSystem = None,
    ) -> cb.DVector:
        """ """
        if adj_factors is None:
            return mts_production


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

    def _read_emp_lu(self, year):
        """
        - Reads the employment land use DVector, for one given year, from the path given in the constructor
        - Checks if "uni" is a column in the translation vector
            -
        - Translates the employment landuse DVector(s) zoning system to the TEM Model zoning system
        - Returns a dictionary of landuses, one for employment, one for education (non-uni), one for education (uni)
        """
        # Read the employment landuse DVector for the given year
        emp_landuse = cb.DVector.load(self.emp_landuse_paths[year]).add_segments(
            [cb.segmentation.SegmentsSuper("total").get_segment()]
        )
        # Rename Segmentation
        emp_landuse = cb.DVector(
            segmentation=emp_landuse.segmentation,
            import_data=emp_landuse.data,
            zoning_system=cb.ZoningSystem.get_zoning("lsoa_2021"),
        )
        emp_landuse = emp_landuse.aggregate(["total", "sic_2_digit", "soc"])
        d = {}
        d["emp"] = emp_landuse
        d["edu"] = emp_landuse.filter_segment_value("sic_2_digit", [86])
        d["uni"] = None
        if self.emp_trans is not None and "uni" in self.emp_trans.columns:
            di = cb.ZoningSystem.get_zoning("lsoa_2021").id_to_name
            di = {
                val: key for key, val in di.items()
            }  # TODO will this will only be the case for Nhan's lsoa trans?
            trans = self.emp_trans
            emp_zones = trans.loc[trans["uni"] == 0]["lsoa_2021_id"]
            uni_zones = trans.loc[trans["uni"] > 0]["lsoa_2021_id"]
            uni_zones = uni_zones.apply(lambda x: di[x])
            emp_zones = emp_zones.apply(lambda x: di[x])
            uni = d["edu"].select_zone(
                list(uni_zones.values)
            )  # .data NB. Isaac may have fixed s/t the select_zone function returns DVec with Zoning.
            edu = d["edu"].select_zone(list(emp_zones.values))  # .data

            # cols = di.values()
            # empty = pd.DataFrame(columns=cols, index=edu.index).fillna(0)
            # uni = (uni+empty).fillna(0) # TODO - seems not to work... not sure why
            # edu = (edu+empty).fillna(0)
            # uni = cb.DVector(segmentation=d["edu"].segmentation, import_data=uni, zoning_system=cb.ZoningSystem.get_zoning("lsoa_2021"))
            # edu = cb.DVector(segmentation=d["edu"].segmentation, import_data=edu, zoning_system=cb.ZoningSystem.get_zoning("lsoa_2021"))
            d["edu"] = edu
            d["uni"] = uni

        # Translate the employment landuse to the TEM Model zoning system
        zoning_system = cb.ZoningSystem.get_zoning(self.model._zoning_system)
        d["emp"] = d["emp"].translate_zoning(
            zoning_system, trans_vector=self.emp_trans, check_totals=True, no_factors=False
        )
        d["edu"] = d["edu"].translate_zoning(
            zoning_system, trans_vector=self.emp_trans, check_totals=True, no_factors=False
        )
        if d["uni"] is not None:
            d["uni"] = d["uni"].translate_zoning(
                zoning_system, trans_vector=self.emp_trans, check_totals=True, no_factors=False
            )

        return d

    def _read_hh_lu(self, year):
        """
        - Reads all household landuse DVectors, for each Government Office Region (GOR), using the file prefix and the directory given in the constructor
        - Concatonates the household landuse DVectors
        - Translates the concatonated household DVector zoning system to the TEM Model zoning system
        DVector files, in the directory, should be formated: {hh_landuse_prefix}_{gor_code}.{hdf/dvec}
        """
        # Create an empty list of DVectors which will contain household landuse for each Government Office Region (GOR)
        hh_list: list[cb.DVector] = []
        # For each GOR...
        for gor in self.hh_landuse_paths[year].keys():
            dvec = cb.DVector.load(pathlib.Path(self.hh_landuse_paths[year][gor]))
            if "total" not in dvec.segmentation.names:
                dvec = dvec.add_segments(
                    [cb.segmentation.SegmentsSuper("total").get_segment()]
                )
            hh_list.append(dvec)
        # Horizontally concatonate each GOR's household landuse DVector
        data = pd.concat([d.data for d in hh_list], axis=1)
        hh_landuse = cb.DVector(
            import_data=data,
            segmentation=hh_list[0].segmentation,
            zoning_system=cb.ZoningSystem.get_zoning("lsoa_2021"),
        )
        # Translate the household landuse to the TEM Model zoning system
        zoning_system = cb.ZoningSystem.get_zoning(self.model._zoning_system)
        hh_landuse = hh_landuse.translate_zoning(
            zoning_system, trans_vector=self.hh_trans, check_totals=True, no_factors=False
        )

        return hh_landuse

    # Returns a year-specific dictionary of pure demand, for each purpose as the key
    def _create_attr_dict(
        self, landuses: dict[str, cb.DVector | dict], trip_rates: dict[int, cb.DVector]
    ) -> dict[int, cb.DVector]:
        """Creates the dictionary of pure attractions by purpose
        - Multiplies the purpose-specific landuse by the purpose-specific trip rates, creating attraction
        - Adds purpose segmentation to each DVector, based on the trip rates key
        - Reduces the attraction segmentation to p and soc, or otherwise to p if soc is not in the purpose-specific trip rate segmentation
        """
        # Create an empty dict to store attraction by purpose
        attr_dict: dict[int, cb.DVector] = {}
        # For each purpose...
        for p, trip_rate in trip_rates.items():
            # Access the landuse dvec (employment or household) with respect to travel purpose
            if (p != 7) and (p != 17):
                landuse = landuses["emp"]
            else:
                landuse = landuses["hh"]
            # Create the attraction DVector for the given purpose
            attr = landuse * trip_rate
            # Add the purpose segmentat to the DVector segmentation
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

    def _adjust_attraction_dict(self, attr_dict, adj_factors: cb.DVector):
        """
        - TODO
        """
        attr_dict_adj: dict[int, cb.DVector] = {}
        if adj_factors is not None:
            for p in attr_dict.keys():
                attr_dict_adj[p] = attr_dict[p] * adj_factors.filter_segment_value("p", [p])
        else:
            attr_dict_adj = attr_dict

        return attr_dict_adj

    def _export_pure_attractions(
        self, attr_dict: dict[int, cb.DVector], year: int, adj: bool = False
    ) -> None:
        """
        - Concatonates the DVectors stored in the Pure Attractions dictionary, aggregated to p segmentation
        - Saves the concatonated DVector to the pure_demand export path for the given year
        """
        # Concatonate the (optionally balanced) Pure Attraction by purpose
        for p in attr_dict.keys():
            try:
                output_pure = output_pure.concat(attr_dict[p].aggregate(["p"]))
            except NameError:
                output_pure = attr_dict[p].aggregate(["p"])  # Initialises the output object
        # Write Pure Attractions
        out_path = self.model.export_paths.pure_demand[year]
        if adj:
            out_path = self.model.export_paths.pure_demand_adj[year]
        output_pure.save(out_path)

        return None

    def _create_mts_dict(
        self,
        attr_dict: dict[int, cb.DVector],
        mts: cb.DVector,
        mts_uni: cb.DVector | None = None,
    ) -> dict[int, cb.DVector]:
        """
        - Multiplies the attraction DVector with the mts DVector, as read from the path given in the constructor
        """
        mts_dict: dict[int, cb.DVector] = {}
        for p, trips in attr_dict.items():
            if mts_uni is None:
                mts_dict[p] = trips * mts
            else:
                if p in mts_uni.segmentation.input.subsets["p"]:
                    mts_dict[p] = trips * mts_uni
                else:
                    mts_dict[p] = trips * mts

        return mts_dict

    def _check_mts_dict(
        self, attr_dict: dict[int, cb.DVector], mts_dict: dict[int, cb.DVector]
    ) -> None:
        # Checks that sum of all purpose-specific DVectors match following the application of MTS to Pure Attractions
        for p in mts_dict.keys():
            if not mts_dict[p].sum_is_close(attr_dict[p], 0.01, 100):
                print(
                    f"The sum of mode-time split, of the Pure Attractions for purpose {p}, does not match the expected sum.\n"
                    f"Expected: {attr_dict[p].sum()}\nGot: {mts_dict[p].sum()}\n"
                )

        return None

    def _adjust_mts_dict(
        self,
        mts_dict: dict[int, cb.DVector],
        adj_factors: cb.DVector,
        geo_constraint: cb.ZoningSystem | None = None,
    ) -> dict[int, cb.DVector]:
        mts_dict_adj: dict[int, cb.DVector] = (
            {}
        )  # TODO mts_dict_adj = mts_dict, removes need for else
        if adj_factors is not None:
            for (
                p
            ) in (
                mts_dict.keys()
            ):  # TODO - this definitely needs tidying. Perhaps there's an inbuilt DVector function to use instead?
                mts = mts_dict[p]
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
        """TODO fix description re: mts
        - Concatonates the DVectors stored in the Pure Attractions dictionary, aggregated to p segmentation
        - Saves the concatonated DVector to the pure_demand export path for the given year
        """
        # Concatonate the (optionally balanced) Pure Attraction by purpose
        for p in attr_dict.keys():
            try:
                output_pure = output_pure.concat(attr_dict[p].aggregate(["p", "m", "tp"]))
            except NameError:
                output_pure = attr_dict[p].aggregate(
                    ["p", "m", "tp"]
                )  # Initialises the output object
        # Write MTS Attractions
        out_path = self.model.export_paths.mts_demand[year]
        if adj:
            out_path = self.model.export_paths.mts_demand_adj[year]
        output_pure.save(out_path)

        return None

    def _create_seg_dict(
        self, mts_dict: dict[int, cb.DVector], tem_production: cb.DVector
    ) -> dict[int, cb.DVector]:
        """
        - Applies the split_by_other method to each DVector in mts_dict, expanding the segmentation to match that of TEM Segmented Production
        """
        seg_dict: dict[int, cb.DVector] = {}
        for p, mts in mts_dict.items():
            agg_seg = list(self.tem_segmentation.overlap(mts.segmentation))
            agg_seg.remove("p")
            mts = mts.aggregate(agg_seg)
            seg_dict[p] = mts.split_by_other(
                tem_production.filter_segment_value("p", [p]),
                agg_zone=cb.ZoningSystem.get_zoning("gor"),
            )  # TODO want zoning for splitting and balancing to both be arguments / levers re: issues down the line, optional arg with default "gor". splitting = gor, balancing = gb currently (remove zoning)

        return seg_dict

    def _check_seg_dict(
        self, mts_dict: dict[int, cb.DVector], seg_dict: dict[int, cb.DVector]
    ) -> None:
        # Checks that sum of all purpose-specific DVectors match following the application of TEM Production Segmentation
        for p in seg_dict.keys():
            if not seg_dict[p].sum_is_close(mts_dict[p], 0.01, 100):
                print(
                    f"The sum of Segmented MTS Attractions, of the pre-segmented MTS Attractions for purpose {p}, does not match the expected sum.\n"
                    f"Expected: {mts_dict[p].sum()}\nGot: {seg_dict[p].sum()}\n"
                )

        return None

    def _create_tem_dvec(self, seg_dict: dict[int, cb.DVector]) -> cb.DVector:
        """
        -
        """
        for p in seg_dict.keys():
            try:
                tem_dvec = tem_dvec.concat(
                    seg_dict[p]
                )  # .aggregate(list(self.tem_segmentation.overlap(seg_dict[p].segmentation))))
            except NameError:
                tem_dvec = seg_dict[p]  # .aggregate(self.tem_segmentation)

        return tem_dvec

    def _balance_to_production(
        self, tem_dvec: cb.DVector, tem_production: cb.DVector
    ) -> cb.DVector:
        """
        IF balance_prodcution is TRUE
        - Divides the TEM Production by the TEM Attraction with zoning removed (Great Britain level), producing segmentation balancing factors.
        - Multiplies the TEM Attractions by the factors.
        IF balance_production is BalancingZones OR ZoningSystem
        - Calls the balance_by_segments function on the TEM Attractions, balancing against TEM Productions using the specified balancing zones
        """
        # If balancing_zones is True
        if self.balance_production == True:
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


    def _create_tem_return_home_attraction(self,tem_attraction:cb.DVector):

        # Reading one Phi factor Dvec to get its segmentation
        self.phi_segmentation = self._read_phi_factor_dvec(1).segmentation.naming_order

        aggregation_segments = list(
            s for s in (
                    set(self.tem_segmentation) ^ set(self.phi_segmentation)
            # symmetric difference: keep segments that are in only one of the two
            )
            if s not in {"m", "tp"}  # manually exclude 'm' and 'tp' even if they are not common
        )

        tem_return_home_tripends_attraction = self.return_home_trip_ends(tem_attraction,aggregation_segments)
        mts_return_home = self._read_mts_return_home()

        # Check if 'tp_return' exists in either segmentation
        tp_in_tem = 'tp_return' in tem_attraction.segmentation.naming_order
        tp_in_mts = 'tp_return' in mts_return_home.segmentation.naming_order

        if not (tp_in_tem or tp_in_mts):
            raise SegmentationError(
                "Segment 'tp_return' (Return Time Period) must be present in either the phi factor DVector or the mode-time split DVector.")

        tem_return_home_tripends_attraction_mts = tem_return_home_tripends_attraction * mts_return_home
        mts_return_home_adj = self._read_mts_return_home_adjustment()

        tem_return_home_tripends_attraction_adj = self._adjust_mts_attraction_return_home(tem_return_home_tripends_attraction_mts,mts_return_home_adj,cb.ZoningSystem.get_zoning('gor'))

        return tem_return_home_tripends_attraction_adj

    def return_home_trip_ends(self, tem_attraction, agg_segments):
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
            tem_filtered = tem_attraction.filter_segment_value('p', p_val, keep_filtered=True)

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

    def _read_phi_factor_dvec(self, purpose: int):
        """
        Reads a phi factor DVector file for the given purpose segment.

        Parameters
        ----------
        purpose : int
            Purpose segment value (e.g., 1 to 8).

        Returns
        -------
        cb.DVector
            Loaded phi factor DVector.

        """
        phi_factors_file_path = Path(os.path.join(self.phi_factors_path, f"phi_factors_A_p{purpose}_reg.dvec"))

        if not phi_factors_file_path.exists():
            raise FileNotFoundError(f"[ERROR] Phi factor file not found: {phi_factors_file_path}")

        phi_factor = cb.DVector.load(phi_factors_file_path)
        return phi_factor
