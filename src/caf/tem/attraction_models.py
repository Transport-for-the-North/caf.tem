# -*- coding: utf-8 -*-
# Allow class self type hinting
from __future__ import annotations
import logging

# Builtins
import os
import warnings
import pathlib

# Third party imports
import pandas as pd

import caf.base as cb
from .inputs import ProductionModelPaths, AttractionModelPaths
from .utils import *

# local imports


class AttractionModel_TP:

    def __init__(
        self,
        production_model: ProductionModelPaths,
        model: AttractionModelPaths,
        trip_rates_paths: dict[int, os.PathLike],
        balance_production: cb.zoning.BalancingZones | bool,
        production_paths: dict[int, os.PathLike],
        emp_landuse_paths: dict[int, os.PathLike],
        hh_landuse_dirs: dict[int, os.PathLike], 
        hh_landuse_prefix: str,
        mts_path: os.PathLike,
        tem_segmentation: cb.Segmentation
    ):
        self.production_model = production_model
        self.model = model
        self.trip_rates_paths = trip_rates_paths
        self.balance_production = balance_production
        self.production_paths = production_paths
        self.emp_landuse_paths = emp_landuse_paths
        self.hh_landuse_dirs = hh_landuse_dirs
        self.hh_landuse_prefix = hh_landuse_prefix
        self.mts_path = mts_path
        self.tem_segmentation = tem_segmentation

    def run(self, export_pure_attractions: bool=True, export_tem_segmentation: bool=True, export_reports: bool=True) -> None:
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
        if not (export_pure_attractions or export_tem_segmentation or export_reports):
            return None

        # Ensure production balance file already exists... (if balance_production is True)
        if self.balance_production:
            os.path.exists(self.production_model.export_paths.pure_demand[year])
            raise LookupError("The Pure Productions have not been created by running the HBProductionModel. Do this first.")

        # For each year the model is running for...
        for year in self.model.path_years:

            # ## ATTRACTION ## #
            # Nothing to do if the pure demand for the running attraction model, for the given year, is already completed.
            if os.path.exists(self.model.export_paths.pure_demand[year]): # TODO - correct this, may want to write tem / reports.
                continue
            else:
                # Read in the landuses dvec files specific to the year.
                landuses: dict[str, cb.DVector] = {"emp": self._read_emp_lu(year), "hh": self._read_hh_lu(year)}
                # Read in the trip rate dvec files for each purpose, if not already read. Trip rates are not year dependent.
                try: 
                    trip_rates
                except NameError:
                    trip_rates: dict[int, cb.DVector] = {p: self._read_trip_rate(p) for p in self.trip_rates_paths}
                # Create a dictionary of attractions by purpose
                attr_dict: dict[int, cb.DVector] = self._create_attr_dict(landuses, trip_rates)
                # No longer need landuses for the given year
                del landuses

            # ## MODE TIME SPLIT ## #
            # Ensure the MTS DVector has been read in
            try: 
                mts
            except NameError:
                mts = self._read_mts()
            # Create a dictionary of attractions, with mode time split applied, by purpose
            mts_dict = self._create_mts_dict(attr_dict, mts)
            # No longer need dictionary of attractions by purpose
            del attr_dict

            # ## PURE SEGMENTATION ## #
            pure_production = cb.DVector.load(self.production_model.export_paths.pure_demand[year])
            seg_demand_dict = self._create_seg_demand_dict(mts_dict, pure_production)
            del mts_dict

            # ## PRODUCTION BALANCING ## #
            pure_production_gb = pure_production.remove_zoning() # if/or function depending on balancing zones argument
            balanced_demand_dict: dict[int, cb.DVector] = {}
            if self.balance_production == True:
                for p in seg_demand_dict.keys():
                    factors  = pure_production_gb / seg_demand_dict[p].remove_zoning()
                    balanced_demand_dict[p] = seg_demand_dict[p] * factors # check here that sums for productions and attractions do match.
                    balanced_demand_dict[p].save(pathlib.Path(self.model.export_home) / f"bal_demand{p}.hdf")
                del seg_demand_dict
            elif type(self.balance_production) is cb.BalancingZones: # TODO
                pass
            else: 
                balanced_demand_dict = seg_demand_dict

            # ## PURE DEMAND OUTPUT ## #
            # Don't export if user has set export to False
            if export_pure_attractions:
                # Concatonate the (optionally balanced) Pure Attraction by purpose
                for p in balanced_demand_dict.keys():
                    try: output_pure = output_pure.concat(balanced_demand_dict[p])
                    except NameError: output_pure = balanced_demand_dict[p] # Initialises the output object
                # Write Pure Attractions
                output_pure.save(self.model.export_paths.pure_demand[year])
            
            # ## TEM SEGMENTATION ## #
            # Take the pure segmentation, and aggregate to the desired TEM segmentation
            if export_tem_segmentation:
                # If Pure Attractions has already been created 
                if os.path.exists(self.production_model.export_paths.pure_demand[year]):
                    try: output_pure
                    except NameError: output_pure = cb.DVector.load(self.production_model.export_paths.pure_demand[year])
                else:
                    for p in balanced_demand_dict.keys():
                        try: output_pure = output_pure.concat(balanced_demand_dict[p])
                        except NameError: output_pure = balanced_demand_dict[p] # Initialises the output object
                output_tem = output_pure.aggregate(self.tem_segmentation)
                output_tem.save(self.model.export_paths.tem_segmented[year])

        # ## END ## #
        return None


    def _read_emp_lu(self, year):
        # Read the employment landuse DVector for the given year
        emp_landuse = cb.DVector.load(self.emp_landuse_paths[year])
        # Translate the employment landuse to the TEM Model zoning system
        zoning_system = cb.ZoningSystem.get_zoning(self.model._zoning_system)
        emp_landuse = emp_landuse.translate_zoning(zoning_system, check_totals=False, no_factors=True)

        return emp_landuse


    def _read_hh_lu(self, year):
        # Create an empty list of DVectors which will contain household landuse for each Government Office Region (GOR)
        hh_list: list[cb.DVector] = []
        # For each GOR...
        for region in ["EM", "EoE", "Lon", "NE", "NW", "SE", "SW", "Wales", "WM", "YH", "Scotland"]:
            hh_list.append(
                cb.DVector.load(
                    pathlib.Path(self.hh_landuse_dirs[year])
                    / f"{self.hh_landuse_prefix}_{region}.hdf"
                )
            )
        # Horizontally concatonate each GOR's household landuse DVector
        data = pd.concat([d.data for d in hh_list], axis=1)
        hh_landuse = cb.DVector(import_data=data, segmentation=hh_list[0].segmentation, zoning_system=hh_list[0].zoning_system)
        # Translate the household landuse to the TEM Model zoning system
        zoning_system = cb.ZoningSystem.get_zoning(self.model._zoning_system)
        hh_landuse = hh_landuse.translate_zoning(zoning_system)

        return hh_landuse


    def _read_trip_rate(self, p):
        # Each trip rate file is explicitly defined in the input dictionary by purpose HB Attraction Model, similar assumption for NHB
        trip_rate = cb.DVector.load(self.trip_rates_paths[p])
        trip_rate = trip_rate.translate_zoning(
            cb.ZoningSystem.get_zoning(self.model._zoning_system),
            check_totals=False,
            no_factors=True,
        )

        return trip_rate


    # Returns a year-specific dictionary of pure demand, for each purpose as the key
    def _create_attr_dict(self, landuses: dict[str, cb.DVector], trip_rates: dict[int, cb.DVector]) -> dict[int, cb.DVector]:
        """
        - Multiplies the purpose-specific landuse by the purpose-specific trip rates, creating attraction
        - Reduces the attraction segmentation to soc, or otherwise to total if soc is not in the purpose-specific trip rate segmentation
        """
        # Create an empty dict to store attraction by purpose
        attr_dict: dict[int, cb.DVector] = {}
        # For each purpose...
        for p in trip_rates.keys():
            # Access the purpose's trip rate dvec
            trip_rate = trip_rates[p]
            # Access the landuse dvec (employment or household) with respect to travel purpose
            if p!=7:
                landuse = landuses["emp"]
            else:
                landuse = landuses["hh"] # Purpose 7 is Visiting Friends / Relatives and uses household landuse as the attraction
            # Create the attraction DVector for the given purpose
            attr = landuse * trip_rate # NB. it is assumed that trip_rate segmentation is a subset of landuse segmentation
            # Aggregate the attraction DVector to soc if soc is in the trip rate segmentation, total segmentation otherwise
            if "soc" in trip_rate.segmentation.names: 
                attr = attr.aggregate(["soc"])
            else:
                # Add the total segmentation to the attraction DVector and aggregate to total
                attr = attr.add_segments([cb.segmentation.SegmentsSuper("total").get_segment()]).aggregate(["total"])
            attr_dict[p] = attr

        return attr_dict
    

    def _read_mts(self):
        mts = cb.DVector.load(self.mts_path)
        # Ensure zoning system of mts matches the TEM Model zoning system
        zoning_system = cb.ZoningSystem.get_zoning(self.model._zoning_system)
        mts = mts.translate_zoning(zoning_system, check_totals=False, no_factors=True)
        
        return mts
    

    def _create_mts_dict(self, attr_dict: dict[int, cb.DVector], mts: cb.DVector) -> dict[int, cb.DVector]:
        """
        - Adds purpose segmentation to each attr_dict DVector
        - Multiplies the attraction DVector with the mts DVector, as read from the path given in the constructor
        - Removes total segmentation from the MTS Demand DVector if total is in the segmentation
        """
        mts_dict: dict[int, cb.DVector] = {}
        for p in attr_dict.keys():
            attr = attr_dict[p]
            # The purpose segment must be in attraction segmentation for multiplying with the MTS DVector
            attr = attr.add_segments([cb.segmentation.SegmentsSuper("p").get_segment(subset=[p])])
            mts_dict[p] = attr * mts.filter_segment_value("p", [p]) # TODO NB. to Isaac - error thrown if mts not filtered. Should look into this...
            # Remove total segment if it is in the segmentation, it is no longer needed
            if "total" in mts_dict[p].segmentation.names:
                segmentation = mts_dict[p].segmentation.remove_segment("total")
                mts_dict[p] = mts_dict[p].aggregate(segmentation.names)

        return mts_dict
    

    def _create_seg_demand_dict(self, mts_dict: dict[int, cb.DVector], pure_production: cb.DVector) -> dict[int, cb.DVector]:
        """
        - Applies the split_by_other method to each mts_dict DVector, expanding the segmentation to match that of Pure Production.
        """
        seg_demand_dict: dict[int, cb.DVector] = {}
        for p in mts_dict.keys():
            seg_demand_dict[p] = mts_dict[p].split_by_other(pure_production.filter_segment_value("p", [p]),
                                                            agg_zone=cb.ZoningSystem.get_zoning("gor")
            ) # TODO want zoning for splitting and balancing to both be arguments / levers re: issues down the line, optional arg with default "gor". splitting = gor, balancing = gb currently (remove zoning)
            
        return seg_demand_dict


    # class AttractionModel(AttractionModelPaths):
    #    _log_fname = "HBAttractionModel_log.log"
    #    """The Home-Based Attraction Model of NoTEM
    #
    #        The attraction model can be ran by calling the class run() method.
    #
    #        Attributes
    #        ----------
    #        employment_paths: Dict[int, os.PathLike]:
    #            Dictionary of {year: land_use_employment_data} pairs. As passed
    #            into the constructor.
    #
    #        production_balance_paths: Dict[int, os.PathLike]:
    #            Dictionary of {year: path_to_production_to_control_to} pairs. As passed
    #            into the constructor.
    #
    #        trip_weights_path: str
    #            The path to the attraction trip weights. As passed into the constructor.
    #
    #        mode_splits_path: str
    #            The path to attraction mode splits. As passed into the constructor.
    #
    #        constraint_paths: Dict[int, os.PathLike]
    #            Dictionary of {year: constraint_path} pairs. As passed into the
    #            constructor.
    #
    #        process_count: int
    #            The number of processes to create in the Pool. As passed into the
    #            constructor.
    #
    #        years: List[int]
    #            A list of years that the model will run for. Derived from the keys of
    #            land_use_paths
    #
    #        See HBAttractionModelPaths for documentation on:
    #            "path_years, export_home, report_home, export_paths, report_paths"
    #        """
    #
    #    def __init__(
    #        self,
    #        path_years: list[int],
    #        report_home: os.PathLike,
    #        zoning_system: str,
    #        trip_rates_paths: dict[str, os.PathLike],
    #        landuse_paths: dict[str, os.PathLike],
    #        #tem_segs: TEMSegmentations,
    #        #production_balance_paths: dict[int, os.PathLike], # this is the HB Production - by the HBProduction Model
    #        export_home: str,
    #        balance_zoning: cb.zoning.BalancingZones | bool = True,
    #        process_count: int = 2,
    #       # _trip_origin
    #    ) -> None:
    #        """
    #        Sets up and validates arguments for the Attraction model.
    #
    #        Parameters
    #        ----------
    #        employment_paths:
    #            Dictionary of {year: land_use_employment_data} pairs.
    #            Should have the columns as defined in:
    #            HBAttractionModel._target_cols['employment']
    #
    #        production_balance_paths:
    #            Dictionary of {year: path_to_production_to_control_to} pairs.
    #            These paths should be gotten from nd.HBProduction model.
    #            Must contain the same keys as land_use_paths, but it can contain
    #            more (any extras will be ignored).
    #            These productions will be used to control the produced attractions.
    #
    #        trip_weights_path:
    #            The path to the attraction trip weights.
    #            Should have the columns as defined in:
    #            HBAttractionModel._target_cols['trip_weight']
    #
    #        non_resi_path: str
    #            Path to the non residential data used as a temporary replacement
    #            for land use data. TODO Remove this parameter when using new version
    #            of land use.
    #
    #        export_home:
    #            Path to export attraction outputs.
    #
    #        balance_zoning:
    #            The zoning systems to balance the attractions to the productions at for
    #            each segment of the attractions segmentation. A translation must exist
    #            between this and the running zoning system, which is MSOA by default.
    #            If True, then no spatial balance is done, only a segmental balance and if
    #            False no balancing is done.
    #
    #        constraint_paths:
    #            Dictionary of {year: constraint_path} pairs.
    #            Must contain the same keys as land_use_paths, but it can contain
    #            more (any extras will be ignored).
    #            If set - will be used to constrain the attractions - a report will
    #            be written before and after.
    #
    #        process_count:
    #            The number of processes to create in the Pool. Typically this
    #            should not exceed the number of cores available.
    ##            Defaults to consts.PROCESS_COUNT.
    ##        """
    ##        # Check that the paths we need exist!
    ##        for path in production_balance_paths.values():
    ##            check_file_exists(path)
    ##
    ##        # Validate that we have data for all the years we're running for
    ##        for year in landuse_paths.keys():
    ##            if year not in production_balance_paths.keys():
    ##                raise ValueError(
    ##                    "Year %d found in land_use_paths\n"
    ##                    "But not found in control_production_paths" % year
    ##                )
    ##
    #        # Assign
    #        self.trip_rates_paths = trip_rates_paths
    #        self.landuse_paths = landuse_paths
    ##        self.tem_segments = tem_segs
    ##        self.production_balance_paths = production_balance_paths
    #        self.balance_zoning = balance_zoning
    #        self.process_count = process_count
    #        self.years = list(self.landuse_paths.keys())
    #
    #        # Make sure the reports paths exists
    #        export_home = pathlib.Path(export_home)
    #        report_home = export_home / "Reports"
    #        report_home.mkdir(exist_ok=True, parents=True)
    #
    #        # Build the output paths
    #        super().__init__(
    #            path_years=self.years,
    #            export_home=export_home,
    #            report_home=report_home,
    #        )
    # #       # Create a logger
    # #       logger_name = "%s.%s" % (nd.get_package_logger_name(), self.__class__.__name__)
    # #       log_file_path = os.path.join(self.export_home, self._log_fname)
    # #       self._logger = nd.get_logger(
    # #           logger_name=logger_name,
    # #           log_file_path=log_file_path,
    # #           instantiate_msg="Initialised HB Attraction Model",
    # #       )
    # #       # Save balancing zones to file
    # #       if isinstance(self.balance_zoning, cb.zoning.BalancingZones):
    # #           self.balance_zoning.save(self.export_home / "HB_balancing_zones.ini")
    ##
    #    def run(
    #        self,
    #        export_pure_attractions: bool = False,
    #        export_notem_segmentation: bool = True,
    #        export_reports: bool = True,
    #    ) -> None:
    #        """
    #        Runs the HB/NHB attraction model.
    #
    #        Completes the following steps for each year:
    #            - Reads in the land use employment data given in the constructor.
    #            - Reads in the trip rates data given in the constructor.
    #            - Multiplies the employment and trip rates on relevant segments,
    #              producing "pure attractions".
    #            - Optionally writes out a pickled DVector of "pure attractions"
    #              at self.export_paths.fully_segmented[year].
    #            - Balances "pure attractions" to production notem segmentation,
    #              producing "notem segmented" attractions.
    #            - Optionally writes out a pickled DVector of "notem segmented attractions"
    #              at self.export_paths.tem_segmented[year].
    #            - Optionally writes out a number of "notem segmented" reports, if
    #              reports is True.
    #
    #        Parameters
    #        ----------
    #        export_pure_attractions:
    #            Whether to export the pure attractions to disk or not.
    #            Will be written out to: self.export_paths.pure_demand[year]
    #
    #        export_notem_segmentation:
    #            Whether to export the notem segmented demand to disk or not.
    #            Will be written out to: self.export_paths.tem_segmented[year]
    #
    #        export_reports:
    #            Whether to output reports while running. All reports will be
    #            written out to self.report_home.
    #
    #        non_resi_path : bool, default True
    #            Whether to use the `non_resi_path` (True) or the
    #            `employment_paths` for the employment file.
    #
    #        Returns
    #        -------
    #        None
    #        """
    #        # Initialise timing
    #        start_time = ctk.timing.current_milli_time()
    #        self._logger.info("Starting HB Attraction Model")
    #
    #        # Generate the attractions for each year
    #        for year in self.years:
    #            year_start_time = ctk.timing.current_milli_time()
    #
    #            # ## GENERATE ATTRACTIONS BY MODE ## #
    #            self._logger.info("Loading the employment data")
    #
    #            self._logger.info("Applying trip rates")
    #            pure_attractions = self._generate_attractions()
    #
    #            if export_pure_attractions:
    #                self._logger.info("Exporting pure attractions to disk")
    #                pure_attractions.save(self.export_paths.pure_demand[year])
    #
    #            if export_reports:
    #                self._logger.info("Exporting pure demand reports to disk")
    #                pure_demand_paths = self.report_paths.pure_demand
    #                pure_attractions.write_sector_reports(
    #                    segment_totals_path=pure_demand_paths.segment_total[year],
    #                    ca_sector_path=pure_demand_paths.ca_sector[year],
    #                    ie_sector_path=pure_demand_paths.ie_sector[year],
    #                )
    #
    #            # Control the attractions to the productions, if desired - this also
    #            # adds in some segmentation to bring it in line with the productions
    #            tem_segmented = self._attractions_balance(
    #                a_dvec=pure_attractions,
    #                p_dvec_path=self.production_balance_paths[year],
    #            )
    #
    #            if export_notem_segmentation:
    #                self._logger.info("Exporting tem segmented attractions to disk")
    #                tem_segmented.save(self.export_paths.tem_segmented[year])
    #
    #            if export_reports:
    #                self._logger.info("Exporting notem segmented reports to disk")
    #                notem_segmented_paths = self.report_paths.notem_segmented
    #                tem_segmented.write_sector_reports(
    #                    segment_totals_path=notem_segmented_paths.segment_total[year],
    #                    ca_sector_path=notem_segmented_paths.ca_sector[year],
    #                    ie_sector_path=notem_segmented_paths.ie_sector[year],
    #                    lad_report_path=notem_segmented_paths.lad_report[year],
    #                    lad_report_seg=self.tem_segments.lad_report_seg,
    #                )
    #
    #            # Print timing stats for the year
    #            year_end_time = ctk.timing.current_milli_time()
    #            time_taken = ctk.timing.time_taken(year_start_time, year_end_time)
    #            self._logger.info("HB Attraction in year %s took: %s\n", year, time_taken)
    #
    #        # End timing
    #        end_time = ctk.timing.current_milli_time()
    #        time_taken = ctk.timing.time_taken(start_time, end_time)
    #        self._logger.info("HB Attraction Model took: %s", time_taken)
    #        self._logger.info("HB Attraction Model Finished")

    def _generate_attractions(self) -> cb.DVector:
        """
        Applies trip rates to the given HB employment.

        Parameters
        ----------
        emp_dvec:
            Dvector containing the employment.

        Returns
        -------
        pure_attraction:
            Returns the product of employment and attraction trip rate Dvector.
            ie., pure attraction
        """
        # Define the zoning and segmentations we want to use
        attr_dict: dict[int, cb.DVector] = {}
        segs = []
        longest = []
        # Different purposes have different segmentations
        for purpose, path in self.trip_rates_paths.items():
            trip_rate = cb.DVector.load(path)
            landuse: cb.DVector = cb.DVector.load[self.landuse_paths[purpose]]
            attr = landuse * trip_rate
            for seg in attr.segmentation.names:
                if seg not in segs:
                    segs.append(seg)
            attr_dict[purpose] = attr
            if len(attr) > len(longest):
                longest = attr
        for purpose, dvec in attr_dict.items():
            if dvec == longest:
                continue
            attr_dict[purpose] = dvec.expand_to_other(longest, match_props=True)
        purp_seg = cb.segments.SegmentsSuper("p").get_segment(subset=list(attr_dict.keys()))
        zone_system = longest.zone_system
        attr_dvec = cb.DVector.combine_from_dic(attr_dict, purp_seg, zone_system)

        return attr_dvec

    def _attractions_balance(
        self,
        a_dvec: cb.DVector,
        p_dvec_path: str,
    ) -> cb.DVector:
        """
        Balances attractions to production segmentation

        Parameters
        ----------
        a_dvec:
            The attractions Dvector to control.

        p_dvec_path:
            The path to the production Dvector to balance the attraction
            DVector to.

        Returns
        -------
        balanced_a_dvec:
            a_dvec controlled to p_dvec
        """
        # Read in the productions DVec from disk
        p_dvec = cb.DVector.load(p_dvec_path)

        # Split a_dvec into p_dvec segments and balance
        self._logger.info("Split attractions segmentations to match productions")
        a_dvec = a_dvec.split_by_other(p_dvec)

        return _attraction_balancing(a_dvec, p_dvec, self.balance_zoning, self._logger)


# class NHBAttractionModel(AttractionModelPaths):
#     _log_fname = "NHBAttractionModel_log.log"
#     """The Non Home-Based Attraction Model of NoTEM
#
#         The attraction model can be ran by calling the class run() method.
#
#         Attributes
#         ----------
#         hb_attraction_paths: Dict[int, os.PathLike]:
#             Dictionary of {year: notem_segmented_HB_attractions_data} pairs. As passed
#             into the constructor.
#
#         nhb_production_paths: Dict[int, os.PathLike]:
#             Dictionary of {year: notem_segmented_NHB_productions_data} pairs. As passed
#             into the constructor.
#
#         constraint_paths: Dict[int, os.PathLike]
#             Dictionary of {year: constraint_path} pairs. As passed into the
#             constructor.
#
#         process_count: int
#             The number of processes to create in the Pool. As passed into the
#             constructor.
#
#         See NHBAttractionModelPaths for documentation on:
#             "path_years, export_home, report_home, export_paths, report_paths"
#         """
#     def __init__(
#         self,
#         tem_segs: TEMSegmentations,
#         attr_landuse: dict[int, os.PathLike],
#         nhb_attraction_triprates: dict[int, os.PathLike],
#         nhb_production_paths: dict[int, os.PathLike],
#         export_home: str,
#         balance_zoning: cb.zoning.BalancingZones | bool = True,
#         process_count: int = 2,
#     ) -> None:
#         """
#         Sets up and validates arguments for the NHB Attraction model.
#
#         Parameters
#         ----------
#         hb_attraction_paths:
#             Dictionary of {year: notem_segmented_HB_attractions_data} pairs.
#             These paths should come from nd.HBAttraction model and should
#             be pickled Dvector paths.
#
#         nhb_production_paths:
#             Dictionary of {year: notem_segmented_NHB_productions_data} pairs.
#             These paths should come from nd.NHBProduction model and should
#             be pickled Dvector paths.
#             These productions will be used to control the produced attractions.
#
#         export_home:
#             Path to export NHB attraction outputs.
#
#         balance_zoning:
#             The zoning systems to balance the attractions to the productions at for
#             each segment of the attractions segmentation. A translation must exist
#             between this and the running zoning system, which is MSOA by default.
#             If True, then no spatial balance is done, only a segmental balance and if
#             False no balancing is done.
#
#         constraint_paths:
#             Dictionary of {year: constraint_path} pairs.
#             Must contain the same keys as land_use_paths, but it can contain
#             more (any extras will be ignored).
#             If set - will be used to constrain the attractions - a report will
#             be written before and after.
#
#         process_count:
#             The number of processes to create in the Pool. Typically this
#             should not exceed the number of cores available.
#             Defaults to consts.PROCESS_COUNT.
#         """
#         # Check that the paths we need exist!
#         [check_file_exists(x) for x in nhb_attraction_triprates.values()]
#         [check_file_exists(x) for x in nhb_production_paths.values()]
#
#
#         # Validate that we have data for all the years we're running for
#         for year in nhb_attraction_triprates.keys():
#             if year not in nhb_production_paths.keys():
#                 raise ValueError(
#                     "Year %d found in notem segmented hb_attractions_paths\n"
#                     "But not found in notem segmented nhb_productions_paths" % year
#                 )
#
#         # Assign
#         self.tem_segs = tem_segs
#         self.attr_landuse = attr_landuse
#         self.nhb_attraction_triprates = nhb_attraction_triprates
#         self.nhb_production_paths = nhb_production_paths
#         self.balance_zoning = balance_zoning
#         self.process_count = process_count
#         self.years = list(self.nhb_attraction_triprates.keys())
#
#         # Make sure the reports paths exists
#         export_home = pathlib.Path(export_home)
#         report_home = export_home / "Reports"
#         report_home.mkdir(exist_ok=True, parents=True)
#
#         # Build the output paths
#         super().__init__(
#             path_years=self.years,
#             export_home=export_home,
#             report_home=report_home,
#         )
#         # Create a logger
#         logger_name = "%s.%s" % ("placeholder", self.__class__.__name__)
#         log_file_path = self.export_home / self._log_fname
#         self._logger = logging.getLogger(logger_name)
#         # Save balancing zones to file
#         if isinstance(self.balance_zoning, cb.zoning.BalancingZones):
#             self.balance_zoning.save(os.path.join(self.export_home, "NHB_balancing_zones.ini"))
#
#     def run(
#         self,
#         export_nhb_pure_attractions: bool = False,
#         export_notem_segmentation: bool = True,
#         export_reports: bool = True,
#     ) -> None:
#         """
#         Runs the NHB Attraction model.
#
#         Completes the following steps for each year:
#             - Reads in the notem segmented HB attractions compressed pickle
#               given in the constructor.
#             - Changes HB purposes to NHB purposes.
#             - Optionally writes out a pickled DVector of "pure attractions" at
#               self.pure_attractions_out[year]
#             - Optionally writes out a number of "pure attractions" reports, if
#               reports is True.
#             - Balances "fully segmented attractions" to production notem segmentation,
#               producing "notem segmented" NHB attractions.
#             - Optionally writes out a pickled DVector of "notem segmented attractions"
#               at self.notem_segmented_paths[year].
#             - Optionally writes out a number of "notem segmented" reports, if
#               reports is True.
#
#         Parameters
#         ----------
#         export_nhb_pure_attractions:
#             Whether to export the pure attractions to disk or not.
#             Will be written out to: self.export_paths.pure_demand[year]
#
#         export_notem_segmentation:
#             Whether to export the notem segmented demand to disk or not.
#             Will be written out to: self.export_paths.notem_segmented[year]
#
#         export_reports:
#             Whether to output reports while running. All reports will be
#             written out to self.report_home.
#
#         Returns
#         -------
#         None
#         """
#         # Initialise timing
#         start_time = ctk.timing.current_milli_time()
#         self._logger.info("Starting NHB Attraction Model")
#
#         # Generate the nhb attractions for each year
#         for year in self.years:
#             year_start_time = ctk.timing.current_milli_time()
#
#             # ## GENERATE PURE ATTRACTIONS ## #
#             self._logger.info("Loading the employment data")
#             pure_nhb_attr = self._generate_attractions()
#
#             if export_nhb_pure_attractions:
#                 self._logger.info("Exporting NHB pure attractions to disk")
#                 pure_nhb_attr.save(self.export_paths.pure_demand[year])
#
#             if export_reports:
#                 self._logger.info("Exporting pure NHB attractions reports to disk")
#                 pure_demand_paths = self.report_paths.pure_demand
#                 pure_nhb_attr.write_sector_reports(
#                     segment_totals_path=pure_demand_paths.segment_total[year],
#                     ca_sector_path=pure_demand_paths.ca_sector[year],
#                     ie_sector_path=pure_demand_paths.ie_sector[year],
#                 )
#
#             # Control the attractions to the productions
#             notem_segmented = self._attractions_balance(
#                 a_dvec=pure_nhb_attr,
#                 p_dvec_path=self.nhb_production_paths[year],
#             )
#
#             if export_notem_segmentation:
#                 self._logger.info("Exporting notem segmented attractions to disk")
#                 notem_segmented.save(self.export_paths.notem_segmented[year])
#
#             if export_reports:
#                 self._logger.info("Exporting notem segmented attractions reports to disk")
#                 notem_segmented_paths = self.report_paths.notem_segmented
#                 notem_segmented.write_sector_reports(
#                     segment_totals_path=notem_segmented_paths.segment_total[year],
#                     ca_sector_path=notem_segmented_paths.ca_sector[year],
#                     ie_sector_path=notem_segmented_paths.ie_sector[year],
#                     lad_report_path=notem_segmented_paths.lad_report[year],
#                     lad_report_seg=self.tem_segs.lad_report_seg,
#                 )
#
#             # TODO: Bring in constraints (Validation)
#             #  Output some audits of what attractions was before and after control
#             #  By segment.
#             if self.constraint_paths is not None:
#                 msg = "No code implemented to constrain productions"
#                 self._logger.error(msg)
#                 raise NotImplementedError(msg)
#
#             # Print timing stats for the year
#             year_end_time = ctk.timing.current_milli_time()
#             time_taken = ctk.timing.time_taken(year_start_time, year_end_time)
#             self._logger.info("NHB Attraction in year %s took: %s\n" % (year, time_taken))
#
#         # End timing
#         end_time = ctk.timing.current_milli_time()
#         time_taken = ctk.timing.time_taken(start_time, end_time)
#         self._logger.info("NHB Attraction Model took: %s" % time_taken)
#         self._logger.info("NHB Attraction Model Finished")
#
#     def _generate_attractions(self) -> cb.DVector:
#         """
#         Applies trip rates to the given HB employment.
#
#         Parameters
#         ----------
#         emp_dvec:
#             Dvector containing the employment.
#
#         Returns
#         -------
#         pure_attraction:
#             Returns the product of employment and attraction trip rate Dvector.
#             ie., pure attraction
#         """
#         # Define the zoning and segmentations we want to use
#         attr_dict = {}
#         for att, path in self.nhb_attraction_triprates.items():
#             trip_rate = cb.DVector.load(path)
#             landuse = cb.DVector.load[self.attr_landuse[att]]
#             attr_dict[att] = landuse * trip_rate
#
#         return attr_dict
#
#     def _attractions_balance(
#         self,
#         a_dvec: cb.DVector,
#         p_dvec_path: str,
#     ) -> cb.DVector:
#         """
#         Balances attractions to production segmentation
#
#         Parameters
#         ----------
#         a_dvec:
#             The attractions Dvector to control.
#
#         p_dvec_path:
#             The path to the production Dvector to balance the attraction
#             DVector to.
#
#         Returns
#         -------
#         balanced_a_dvec:
#             a_dvec controlled to p_dvec
#         """
#         # Read in the productions DVec from disk
#         p_dvec = cb.DVector.load(p_dvec_path)
#
#         self._logger.info("Split attractions segmentations to match productions")
#         a_dvec = a_dvec.split_by_other(p_dvec)
#
#         return _attraction_balancing(a_dvec, p_dvec, self.balance_zoning, self._logger)


def _attraction_balancing(
    a_dvec: cb.DVector,
    p_dvec: cb.DVector,
    balancing_zones: cb.zoning.BalancingZones | bool,
    #logger: logging.Logger,
) -> cb.DVector:
    if isinstance(balancing_zones, [cb.BalancingZones, cb.ZoningSystem]) or balancing_zones:
        #logger.info("Balancing the attractions to the productions")
        if isinstance(balancing_zones, [cb.BalancingZones, cb.ZoningSystem]):
            balance_zoning = balancing_zones
        else:
            balance_zoning = None

        attractions = a_dvec.balance_by_segments(p_dvec, balance_zoning)
        msg = (
            "The attraction total after balancing to the productions is "
            "not similar enough to the productions. Are some zones being "
            "dropped in the zonal translation?\n"
            "Expected %f\nGot %f"
        )

    else:
        #logger.info("Attractions aren't balanced to productions")
        msg = (
            "Attraction total is different to the productions total.\n"
            "Productions: %f\nAttractions: %f"
        )
        attractions = a_dvec

    # ## ATTRACTIONS TOTAL CHECK ## #
    if not attractions.sum_is_close(p_dvec):
        #logger.warning(msg, p_dvec.sum(), attractions.sum())
        print(msg)
    return attractions
