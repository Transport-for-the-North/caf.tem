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
import caf.base
import caf.toolkit as ctk
from .inputs import AttractionModelPaths, TEMSegmentations, AttractionTripRates
from .utils import check_file_exists

# local imports


class AttractionModel(AttractionModelPaths):
    _log_fname = "HBAttractionModel_log.log"
    """The Home-Based Attraction Model of NoTEM

        The attraction model can be ran by calling the class run() method.

        Attributes
        ----------
        employment_paths: Dict[int, os.PathLike]:
            Dictionary of {year: land_use_employment_data} pairs. As passed
            into the constructor.

        production_balance_paths: Dict[int, os.PathLike]:
            Dictionary of {year: path_to_production_to_control_to} pairs. As passed
            into the constructor.

        trip_weights_path: str
            The path to the attraction trip weights. As passed into the constructor.

        mode_splits_path: str
            The path to attraction mode splits. As passed into the constructor.

        constraint_paths: Dict[int, os.PathLike]
            Dictionary of {year: constraint_path} pairs. As passed into the
            constructor.

        process_count: int
            The number of processes to create in the Pool. As passed into the
            constructor.

        years: List[int]
            A list of years that the model will run for. Derived from the keys of
            land_use_paths

        See HBAttractionModelPaths for documentation on:
            "path_years, export_home, report_home, export_paths, report_paths"
        """
    # Constants

    def __init__(
        self,
        trip_rates_paths: dict[str, os.PathLike],
        landuse_paths: dict[str, os.PathLike],
        tem_segs: TEMSegmentations,
        production_balance_paths: dict[int, os.PathLike],
        export_home: str,
        balance_zoning: caf.core.zoning.BalancingZones | bool = True,
        process_count: int = 2,
    ) -> None:
        """
        Sets up and validates arguments for the Attraction model.

        Parameters
        ----------
        employment_paths:
            Dictionary of {year: land_use_employment_data} pairs.
            Should have the columns as defined in:
            HBAttractionModel._target_cols['employment']

        production_balance_paths:
            Dictionary of {year: path_to_production_to_control_to} pairs.
            These paths should be gotten from nd.HBProduction model.
            Must contain the same keys as land_use_paths, but it can contain
            more (any extras will be ignored).
            These productions will be used to control the produced attractions.

        trip_weights_path:
            The path to the attraction trip weights.
            Should have the columns as defined in:
            HBAttractionModel._target_cols['trip_weight']

        non_resi_path: str
            Path to the non residential data used as a temporary replacement
            for land use data. TODO Remove this parameter when using new version
            of land use.

        export_home:
            Path to export attraction outputs.

        balance_zoning:
            The zoning systems to balance the attractions to the productions at for
            each segment of the attractions segmentation. A translation must exist
            between this and the running zoning system, which is MSOA by default.
            If True, then no spatial balance is done, only a segmental balance and if
            False no balancing is done.

        constraint_paths:
            Dictionary of {year: constraint_path} pairs.
            Must contain the same keys as land_use_paths, but it can contain
            more (any extras will be ignored).
            If set - will be used to constrain the attractions - a report will
            be written before and after.

        process_count:
            The number of processes to create in the Pool. Typically this
            should not exceed the number of cores available.
            Defaults to consts.PROCESS_COUNT.
        """
        # Check that the paths we need exist!
        for path in production_balance_paths.values():
            check_file_exists(path)

        # Validate that we have data for all the years we're running for
        for year in landuse_paths.keys():
            if year not in production_balance_paths.keys():
                raise ValueError(
                    "Year %d found in land_use_paths\n"
                    "But not found in control_production_paths" % year
                )

        # Assign
        self.trip_rates_paths = trip_rates_paths
        self.landuse_paths = landuse_paths
        self.tem_segments = tem_segs
        self.production_balance_paths = production_balance_paths
        self.balance_zoning = balance_zoning
        self.process_count = process_count
        self.years = list(self.landuse_paths.keys())

        # Make sure the reports paths exists
        export_home = pathlib.Path(export_home)
        report_home = export_home / "Reports"
        report_home.mkdir(exist_ok=True, parents=True)

        # Build the output paths
        super().__init__(
            path_years=self.years,
            export_home=export_home,
            report_home=report_home,
        )
        # Create a logger
        logger_name = "%s.%s" % (nd.get_package_logger_name(), self.__class__.__name__)
        log_file_path = os.path.join(self.export_home, self._log_fname)
        self._logger = nd.get_logger(
            logger_name=logger_name,
            log_file_path=log_file_path,
            instantiate_msg="Initialised HB Attraction Model",
        )
        # Save balancing zones to file
        if isinstance(self.balance_zoning, caf.core.zoning.BalancingZones):
            self.balance_zoning.save(self.export_home / "HB_balancing_zones.ini")

    def run(
        self,
        export_pure_attractions: bool = False,
        export_notem_segmentation: bool = True,
        export_reports: bool = True,
    ) -> None:
        """
        Runs the HB Attraction model.

        Completes the following steps for each year:
            - Reads in the land use employment data given in the constructor.
            - Reads in the trip rates data given in the constructor.
            - Multiplies the employment and trip rates on relevant segments,
              producing "pure attractions".
            - Optionally writes out a pickled DVector of "pure attractions"
              at self.export_paths.fully_segmented[year].
            - Balances "pure attractions" to production notem segmentation,
              producing "notem segmented" attractions.
            - Optionally writes out a pickled DVector of "notem segmented attractions"
              at self.export_paths.tem_segmented[year].
            - Optionally writes out a number of "notem segmented" reports, if
              reports is True.

        Parameters
        ----------
        export_pure_attractions:
            Whether to export the pure attractions to disk or not.
            Will be written out to: self.export_paths.pure_demand[year]

        export_notem_segmentation:
            Whether to export the notem segmented demand to disk or not.
            Will be written out to: self.export_paths.tem_segmented[year]

        export_reports:
            Whether to output reports while running. All reports will be
            written out to self.report_home.

        non_resi_path : bool, default True
            Whether to use the `non_resi_path` (True) or the
            `employment_paths` for the employment file.

        Returns
        -------
        None
        """
        # Initialise timing
        start_time = ctk.timing.current_milli_time()
        self._logger.info("Starting HB Attraction Model")

        # Generate the attractions for each year
        for year in self.years:
            year_start_time = ctk.timing.current_milli_time()

            # ## GENERATE ATTRACTIONS BY MODE ## #
            self._logger.info("Loading the employment data")

            self._logger.info("Applying trip rates")
            pure_attractions = self._generate_attractions()

            if export_pure_attractions:
                self._logger.info("Exporting pure attractions to disk")
                pure_attractions.save(self.export_paths.pure_demand[year])

            if export_reports:
                self._logger.info("Exporting pure demand reports to disk")
                pure_demand_paths = self.report_paths.pure_demand
                pure_attractions.write_sector_reports(
                    segment_totals_path=pure_demand_paths.segment_total[year],
                    ca_sector_path=pure_demand_paths.ca_sector[year],
                    ie_sector_path=pure_demand_paths.ie_sector[year],
                )

            # Control the attractions to the productions, if desired - this also
            # adds in some segmentation to bring it in line with the productions
            tem_segmented = self._attractions_balance(
                a_dvec=pure_attractions,
                p_dvec_path=self.production_balance_paths[year],
            )

            if export_notem_segmentation:
                self._logger.info("Exporting tem segmented attractions to disk")
                tem_segmented.save(self.export_paths.tem_segmented[year])

            if export_reports:
                self._logger.info("Exporting notem segmented reports to disk")
                notem_segmented_paths = self.report_paths.notem_segmented
                tem_segmented.write_sector_reports(
                    segment_totals_path=notem_segmented_paths.segment_total[year],
                    ca_sector_path=notem_segmented_paths.ca_sector[year],
                    ie_sector_path=notem_segmented_paths.ie_sector[year],
                    lad_report_path=notem_segmented_paths.lad_report[year],
                    lad_report_seg=self.tem_segments.lad_report_seg,
                )

            # Print timing stats for the year
            year_end_time = ctk.timing.current_milli_time()
            time_taken = ctk.timing.time_taken(year_start_time, year_end_time)
            self._logger.info("HB Attraction in year %s took: %s\n", year, time_taken)

        # End timing
        end_time = ctk.timing.current_milli_time()
        time_taken = ctk.timing.time_taken(start_time, end_time)
        self._logger.info("HB Attraction Model took: %s", time_taken)
        self._logger.info("HB Attraction Model Finished")

    def _generate_attractions(self) -> caf.core.DVector:
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
        attr_dict = {}
        segs = []
        longest = []
        # Different purposes have different segmentations
        for purpose, path in self.trip_rates_paths.items():
            trip_rate = caf.core.DVector.load(path)
            landuse = caf.core.DVector.load[self.landuse_paths[purpose]]
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
        purp_seg = caf.core.segments.SegmentsSuper("p").get_segment(
            subset=list(attr_dict.keys())
        )
        zone_system = longest.zone_system
        attr_dvec = caf.core.DVector.combine_from_dic(attr_dict, purp_seg, zone_system)

        return attr_dvec

    def _attractions_balance(
        self,
        a_dvec: caf.core.DVector,
        p_dvec_path: str,
    ) -> caf.core.DVector:
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
        p_dvec = caf.core.DVector.load(p_dvec_path)

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
#         balance_zoning: caf.core.zoning.BalancingZones | bool = True,
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
#         if isinstance(self.balance_zoning, caf.core.zoning.BalancingZones):
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
#     def _generate_attractions(self) -> caf.core.DVector:
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
#             trip_rate = caf.core.DVector.load(path)
#             landuse = caf.core.DVector.load[self.attr_landuse[att]]
#             attr_dict[att] = landuse * trip_rate
#
#         return attr_dict
#
#     def _attractions_balance(
#         self,
#         a_dvec: caf.core.DVector,
#         p_dvec_path: str,
#     ) -> caf.core.DVector:
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
#         p_dvec = caf.core.DVector.load(p_dvec_path)
#
#         self._logger.info("Split attractions segmentations to match productions")
#         a_dvec = a_dvec.split_by_other(p_dvec)
#
#         return _attraction_balancing(a_dvec, p_dvec, self.balance_zoning, self._logger)


def _attraction_balancing(
    a_dvec: caf.core.DVector,
    p_dvec: caf.core.DVector,
    balancing_zones: caf.core.zoning.BalancingZones | bool,
    logger: logging.Logger,
) -> caf.core.DVector:
    if (
        isinstance(balancing_zones, [caf.core.BalancingZones, caf.core.ZoningSystem])
        or balancing_zones
    ):
        logger.info("Balancing the attractions to the productions")
        if isinstance(balancing_zones, [caf.core.BalancingZones, caf.core.ZoningSystem]):
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
        logger.info("Attractions aren't balanced to productions")
        msg = (
            "Attraction total is different to the productions total.\n"
            "Productions: %f\nAttractions: %f"
        )
        attractions = a_dvec

    # ## ATTRACTIONS TOTAL CHECK ## #
    if not attractions.sum_is_close(p_dvec):
        logger.warning(msg, p_dvec.sum(), attractions.sum())

    return attractions
