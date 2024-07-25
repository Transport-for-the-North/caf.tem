# -*- coding: utf-8 -*-
"""
Module containing trip_end models.
"""
# Built-Ins
import enum
import os

# Third Party
import caf.core
import caf.toolkit as ctk

# Local Imports
# pylint: disable=import-error,wrong-import-position
# Local imports here
from inputs import Scenarios, TEMExportPaths, HBProdInput, NHBProdInput
from production_models import HBProductionModel, NHBProductionModel
from attraction_models import HBAttractionModel, NHBAttractionModel
# pylint: enable=import-error,wrong-import-position

# # # CONSTANTS # # #

# # # CLASSES # # #


class TEM(TEMExportPaths):
    EXPORT_PATHS_CLASS = TEMExportPaths
    _running_report_fname = "running_parameters.txt"
    _log_fname = "NoTEM_log.log"

    def __init__(
        self,
        years: list[int],
        scenario: Scenarios,
        iteration_name: str,
        export_home: os.PathLike,
        hbprodinput: HBProdInput = None,
        nhbprodinput: NHBProdInput = None,
        hb_attraction_balance_zoning: caf.core.BalancingZones | bool = True,
        nhb_attraction_balance_zoning: caf.core.BalancingZones | bool = True,
        process_count: int = 1

    ):
        # Assign
        self.years = years
        self.hb_attraction_balance_zoning = hb_attraction_balance_zoning
        self.nhb_attraction_balance_zoning = nhb_attraction_balance_zoning
        self.process_count = process_count
        self.hb_prod_input = hbprodinput
        self.nhb_prod_input = nhbprodinput
        pass

        super().__init__(
            export_home=export_home,
            path_years=self.years,
            scenario=scenario,
            iteration_name=iteration_name,
        )

    def _generate_hb_production(self):
        if self.hb_prod_input is None:
            raise ValueError("hbprodinput must be provided to generate hb production.")
        hb_prod = HBProductionModel(
            population_paths=self.hb_prod_input.population_paths,
            trip_rates_path=self.hb_prod_input.trip_rates_path,
            mode_time_splits_path=self.hb_prod_input.mode_time_splits_path,
            export_home=self.export_home,
            tem_segs=self.hb_prod_input.tem_segs,
            constraint_paths=self.hb_prod_input.constraint_paths,
            process_count=self.process_count
        )
        hb_prod.run(True, True, True, True)

    def run(self,
            generate_all: bool = False,
            generate_hb: bool = False,
            generate_hb_production: bool = False,
            generate_hb_attraction: bool = False,
            generate_nhb: bool = False,
            generate_nhb_production: bool = False,
            generate_nhb_attraction: bool = False,
            ) -> None:

        # Determine which models to run
        if generate_all:
            generate_hb = True
            generate_nhb = True

        if generate_hb:
            generate_hb_production = True
            generate_hb_attraction = True

        if generate_nhb:
            generate_nhb_production = True
            generate_nhb_attraction = True

        if generate_hb_production:
            self._generate_hb_production()

        if generate_hb_attraction:
            self._generate_hb_attraction()

        if generate_nhb_production:
            self._generate_nhb_production()

        if generate_nhb_attraction:
            self._generate_nhb_attraction()

# # # FUNCTIONS # # #
