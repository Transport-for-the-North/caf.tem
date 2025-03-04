# -*- coding: utf-8 -*-
# Allow class self type hinting
from __future__ import annotations
import logging

# Builtins
import os
import warnings
import pathlib

from pathlib import Path

# Third party imports
import pandas as pd

import caf.base as cb
from .inputs import ProductionModelPaths, AttractionModelPaths

import caf.tem.utils as utils


class AttractionModel:

    def __init__(
        self,
        production_model: ProductionModelPaths,
        model: AttractionModelPaths,
        trip_rates_paths: dict[int, os.PathLike],
        balance_production: cb.zoning.BalancingZones | bool,
        emp_landuse_paths: dict[int, os.PathLike],
        hh_landuse_dirs: dict[int, os.PathLike], 
        hh_landuse_prefix: str,
        mts_path: os.PathLike,
        tem_segmentation: cb.Segmentation
    ):
        self.production_model = production_model
        self.model = model
        self.trip_rates_paths, self.emp_landuse_paths, self.hh_landuse_paths, mts_path = self._format_init_paths(trip_rates_paths, emp_landuse_paths, hh_landuse_dirs, hh_landuse_prefix, mts_path)
        self.tem_segmentation = tem_segmentation
        self.balance_production = balance_production


    def _format_init_paths(self, trip_rates_paths: dict[int, os.PathLike], emp_landuse_paths: dict[int, os.PathLike], hh_landuse_dirs: dict[int, os.PathLike], hh_landuse_prefix: str, mts_path: os.PathLike) -> tuple[dict[int, Path], dict[int, Path], dict[int, dict[str, Path]], Path]:
        """
        - Ensures all paths in population_paths, trip_rates_path, and mts_path
        """
        # 
        trip_rates_paths: dict[int, Path] = {p: Path(path) for p, path in trip_rates_paths.items()}
        emp_landuse_paths = {year: Path(file) for year, file in emp_landuse_paths.items()}
        hh_landuse_paths: dict[int, dict[str, Path]] = {year: {f"{gor}": Path(dir) / f"{hh_landuse_prefix}_{gor}.hdf"} for year, dir in hh_landuse_dirs.items() for gor in utils.GOR}
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


    def run(self,
            export_pure_attractions: bool=True,
            export_tem_segmentation: bool=True,
            export_reports: bool=True
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
            raise IOError("The code has been terminated. All HB Attraction Model exports are set to False, running the HB Attraction Model is redundant.")

        # Ensure production balance file exists... (if balance_production is True)
        for year in self.model.path_years:
            if not os.path.exists(self.production_model.export_paths.pure_demand[year]):
                raise FileNotFoundError("The Pure Productions file is not found. Run the Home Based Production Model to create this file first.")

        # ## CONSTANTS ## #
        report_paths = self.model.report_paths
        export_paths = self.model.export_paths
        zoning_system_name = self.model._zoning_system

        # ## READ INPUTS ## #
        # Read in the trip rates DVector files for each purpose. Trip rates are not year dependent.
        trip_rates: dict[int, cb.DVector] = {p: self._read_trip_rate(p) for p in self.trip_rates_paths}
        # Read in the MTS dvec file. MTS is not year dependent.
        mts: cb.DVector = self._read_mts()

        # For each year the model is running for...
        for year in self.emp_landuse_paths.keys(): # -> TODO is this the correct iterable, path_years or keys of emp landuse? - or check path_years = dict keys of emp_landuse and hh_landuse. What if p7 isn't being tested, wouldn't need hh_landuse...
            
            # Read in the landuses dvec files specific to the year.
            landuses: dict[str, cb.DVector] = {"emp": self._read_emp_lu(year), "hh": self._read_hh_lu(year)}
            
            # ## PURE ATTRACTION ## #
            # Create a dictionary of attractions by purpose
            attr_dict: dict[int, cb.DVector] = self._create_attr_dict(landuses, trip_rates)
            # No longer need landuses for the given year
            del landuses
            # Export Pure Attractions
            if export_pure_attractions:
                self._export_pure_attractions(attr_dict, year) # TODO - ask Isaac whether pure attractions should be aggregated, and concatonated with only purpose segmentation, or whether it should include the likes of sic/soc and be purpose specific DVectors written

            # ## MODE TIME SPLIT ## #
            # Create a dictionary of attractions, with mode time split applied, by purpose
            mts_dict = self._create_mts_dict(attr_dict, mts)
            # Tests to the MTS dict created - TODO confirm rel/abs tolerance w Isaac for this test.
            self._check_mts_dict(attr_dict, mts_dict)
            # No longer need dictionary of attractions by purpose
            del attr_dict

            # ## SPLIT PRODUCTION SEGMENTATION ## #
            # Load the Adjusted TEM Production from the HB/NHB Production Model Output
            tem_production = cb.DVector.load(self.production_model.export_paths.tem_segmented_adj[year])
            # Apply the split_by_other method to the mts DVectors, given the tem_production
            seg_dict = self._create_seg_dict(mts_dict, tem_production)
            # Test all mts_dict DVectors match sum of attr_dict DVectors - TODO confirm rel/abs tolerance w Isaac for this test.
            self._check_seg_dict(mts_dict, seg_dict)
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
                print(f"The sum of the TEM Segmented segmented attraction (split by TEM Production) does not match the expected sum.\n"
                        f"Expected: {attr_dict[p].sum()}\nGot: {seg_dict[p].sum()}")
            # No longer need dictionary of further segmented mts attraction by purpose
            del seg_dict
            
            # ## BALANCE TO PRODUCTIONS ## #
            balanced_dvec = self._balance_to_production(tem_dvec, tem_production)
            del tem_dvec
            
            # ## TEM SEGMENTATION EXPORT ## #
            if export_reports:
                utils.write_dvec_reports(balanced_dvec, report_paths.tem_segmented)
            if export_tem_segmentation:
                balanced_dvec.save(export_paths.tem_segmented[year])


        # ## END ## #
        return None


    # # # HELPER FUNCTIONS # # #

    def _read_trip_rate(self, p: int) -> cb.DVector:
        """
        - Reads one purpose-specific trip rates DVector, from the path given in the constructor
        - Translates the trip rates DVector zoning system to the TEM Model zoning system
        """
        # Each trip rate file is explicitly defined in the input dictionary by purpose HB Attraction Model, similar assumption for NHB
        trip_rate = cb.DVector.load(self.trip_rates_paths[p])
        trip_rate = trip_rate.translate_zoning(
            cb.ZoningSystem.get_zoning(self.model._zoning_system),
            check_totals=False,
            no_factors=True,
        )

        return trip_rate
    

    def _read_mts(self) -> cb.DVector:
        """
        - Reads the mode-time split (MTS) DVector, from the path given in the constructor
        - Translates the MTS DVector zoning system to the TEM Model zoning system
        """
        mts = cb.DVector.load(self.mts_path)
        # Ensure zoning system of mts matches the TEM Model zoning system
        zoning_system = cb.ZoningSystem.get_zoning(self.model._zoning_system)
        mts = mts.translate_zoning(zoning_system, check_totals=False, no_factors=True)
        
        return mts
    

    def _read_emp_lu(self, year):
        """
        - Reads the employment land use DVector, for one given year, from the path given in the constructor
        - Translates the employment landuse DVector zoning system to the TEM Model zoning system
        """
        # Read the employment landuse DVector for the given year
        emp_landuse = cb.DVector.load(self.emp_landuse_paths[year])
        # Translate the employment landuse to the TEM Model zoning system
        zoning_system = cb.ZoningSystem.get_zoning(self.model._zoning_system)
        emp_landuse = emp_landuse.translate_zoning(zoning_system, check_totals=True, no_factors=False)

        return emp_landuse


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
            hh_list.append(
                cb.DVector.load(
                    pathlib.Path(self.hh_landuse_dirs[year])
                    / f"{self.hh_landuse_prefix}_{gor}.hdf"
                )
            )
        # Horizontally concatonate each GOR's household landuse DVector
        data = pd.concat([d.data for d in hh_list], axis=1)
        hh_landuse = cb.DVector(import_data=data, segmentation=hh_list[0].segmentation, zoning_system=hh_list[0].zoning_system)
        # Translate the household landuse to the TEM Model zoning system
        zoning_system = cb.ZoningSystem.get_zoning(self.model._zoning_system)
        hh_landuse = hh_landuse.translate_zoning(zoning_system, check_totals=True, no_factors=False)

        return hh_landuse


    # Returns a year-specific dictionary of pure demand, for each purpose as the key
    def _create_attr_dict(self, landuses: dict[str, cb.DVector], trip_rates: dict[int, cb.DVector]) -> dict[int, cb.DVector]:
        """
        - Multiplies the purpose-specific landuse by the purpose-specific trip rates, creating attraction
        - Adds purpose segmentation to each DVector, based on the trip rates key
        - Reduces the attraction segmentation to p and soc, or otherwise to p if soc is not in the purpose-specific trip rate segmentation
        """
        # Create an empty dict to store attraction by purpose
        attr_dict: dict[int, cb.DVector] = {}
        # For each purpose...
        for p in trip_rates.keys():
            # Access the purpose's trip rate dvec
            trip_rate = trip_rates[p]
            # Access the landuse dvec (employment or household) with respect to travel purpose
            if p!=7: landuse = landuses["emp"]
            else: landuse = landuses["hh"]
            # Create the attraction DVector for the given purpose
            attr = landuse * trip_rate
            # Add the purpose segmentat to the DVector segmentation
            attr = attr.add_segments([cb.segmentation.SegmentsSuper("p").get_segment(subset=[p])])
            # Aggregate the attraction DVector to p and soc if soc is in the trip rate segmentation, p segmentation otherwise
            if "soc" in trip_rate.segmentation.names: attr = attr.aggregate(["p", "soc"])
            else: attr = attr.aggregate(["p"])
            attr_dict[p] = attr

        return attr_dict
    

    def _export_pure_attractions(self, attr_dict: dict[int, cb.DVector], year: int) -> None:
        """
        - Concatonates the DVectors stored in the Pure Attractions dictionary, aggregated to p segmentation
        - Saves the concatonated DVector to the pure_demand export path for the given year
        """
        # Concatonate the (optionally balanced) Pure Attraction by purpose
        for p in attr_dict.keys():
            try: output_pure = output_pure.concat(attr_dict[p].aggregate(["p"]))
            except NameError: output_pure = attr_dict[p].aggregate(["p"]) # Initialises the output object
        # Write Pure Attractions
        output_pure.save(self.model.export_paths.pure_demand[year])

        return None
    

    def _create_mts_dict(self, attr_dict: dict[int, cb.DVector], mts: cb.DVector) -> dict[int, cb.DVector]:
        """
        - Multiplies the attraction DVector with the mts DVector, as read from the path given in the constructor
        - Removes total segmentation from the MTS Demand DVector if total is in the segmentation
        """
        mts_dict: dict[int, cb.DVector] = {}
        for p in attr_dict.keys():
            attr = attr_dict[p]
            mts_dict[p] = attr * mts.filter_segment_value("p", [p]) # TODO NB. to Isaac - error thrown if mts not filtered. Should look into this... Issue with order of operation?

        return mts_dict
    

    def _check_mts_dict(self, attr_dict: dict[int, cb.DVector], mts_dict: dict[int, cb.DVector]) -> None:
        # Checks that sum of all purpose-specific DVectors match following the application of MTS to Pure Attractions
        for p in mts_dict.keys():
            if not mts_dict[p].sum_is_close(attr_dict[p], 0.01, 100):
                print(f"The sum of mode-time split, of the Pure Attractions for purpose {p}, does not match the expected sum.\n"
                      f"Expected: {attr_dict[p].sum()}\nGot: {mts_dict[p].sum()}\n")
        
        return None
                    

    def _create_seg_dict(self, mts_dict: dict[int, cb.DVector], tem_production: cb.DVector) -> dict[int, cb.DVector]:
        """
        - Applies the split_by_other method to each DVector in mts_dict, expanding the segmentation to match that of TEM Segmented Production
        """
        seg_dict: dict[int, cb.DVector] = {}
        for p in mts_dict.keys():
            seg_dict[p] = mts_dict[p].split_by_other(tem_production.filter_segment_value("p", [p]),
                                                            agg_zone=cb.ZoningSystem.get_zoning("gor")
            ) # TODO want zoning for splitting and balancing to both be arguments / levers re: issues down the line, optional arg with default "gor". splitting = gor, balancing = gb currently (remove zoning)
            
        return seg_dict
    

    def _check_seg_dict(self, mts_dict: dict[int, cb.DVector], seg_dict: dict[int, cb.DVector]) -> None:
        # Checks that sum of all purpose-specific DVectors match following the application of TEM Production Segmentation
        for p in seg_dict.keys():
            if not seg_dict[p].sum_is_close(mts_dict[p], 0.01, 100):
                print(f"The sum of Segmented MTS Attractions, of the pre-segmented MTS Attractions for purpose {p}, does not match the expected sum.\n"
                      f"Expected: {mts_dict[p].sum()}\nGot: {seg_dict[p].sum()}\n")
                
        return None
                

    def _create_tem_dvec(self, seg_dict: dict[int, cb.DVector]) -> cb.DVector:
        """
        - 
        """
        for p in seg_dict.keys():
            try: tem_dvec = tem_dvec.concat(seg_dict[p].aggregate(self.tem_segmentation))
            except NameError: tem_dvec = seg_dict[p].aggregate(self.tem_segmentation)

        return tem_dvec


    def _balance_to_production(self, tem_dvec: cb.DVector, tem_production: cb.DVector) -> cb.DVector:
        """
        IF balance_prodcution is TRUE
        - Divides the TEM Production by the TEM Attraction with zoning removed (Great Britain level), producing segmentation balancing factors.
        - Multiplies the TEM Attractions by the factors.
        IF balance_production is BalancingZones OR ZoningSystem
        - Calls the balance_by_segments function on the TEM Attractions, balancing against TEM Productions using the specified balancing zones
        """
        # If balancing_zones is True
        if self.balance_production == True:
            tem_dvec.fill(0, 1e-6)
            gb_factors = tem_production.remove_zoning() / tem_dvec.remove_zoning()
            balanced_dvec = tem_dvec * gb_factors # check here that sums for productions and attractions do match.
        # If soning is specified for balancing
        elif isinstance(self.balance_production, (cb.BalancingZones, cb.ZoningSystem)):
                balanced_dvec = tem_dvec.balance_by_segments(tem_production, self.balance_production)
        # If balancing_zones is False
        else:
            balanced_dvec = tem_dvec

        return balanced_dvec