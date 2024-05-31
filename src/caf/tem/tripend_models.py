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
from inputs import Scenarios, TEMExportPaths

# pylint: enable=import-error,wrong-import-position

# # # CONSTANTS # # #

# # # CLASSES # # #


class TEM(TEMExportPaths):
    EXPORT_PATHS_CLASS = TEMExportPaths
    _running_report_fname = 'running_parameters.txt'
    _log_fname = "NoTEM_log.log"

    def __init__(
        self,
        years: list[int],
        scenario: Scenarios,
        iteration_name: str,
        export_home: os.PathLike,
        hb_attraction_balance_zoning: caf.core.BalancingZones | bool = True,
        nhb_attraction_balance_zoning: caf.core.BalancingZones | bool = True,
    ):
        # Assign
        self.years = years
        self.hb_attraction_balance_zoning = hb_attraction_balance_zoning
        self.nhb_attraction_balance_zoning = nhb_attraction_balance_zoning
        pass

        super().__init__(
            export_home=export_home,
            path_years=self.years,
            scenario=scenario,
            iteration_name=iteration_name,
        )


# # # FUNCTIONS # # #
