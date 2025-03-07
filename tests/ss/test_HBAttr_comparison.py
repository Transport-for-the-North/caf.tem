# -*- coding: utf-8 -*-
"""Tests for the TEM module run() method"""
# Built-Ins
from typing import Any
import caf.tem as ct

# Third Party
import pytest
import caf.tem as ct

# Local Imports
# pylint: disable=import-error,wrong-import-position

# pylint: enable=import-error,wrong-import-position

# # # CONSTANTS # # #


# # # FIXTURES # # #


# # # TESTS # # #
tem = ct.TEM(
    model_years=[2023],
    scenario="Core",
    output_zoning="normits",
    iteration_name="20250304",
    export_home=r"T:\ThomasPrince\TEM Input\comparison\caf.tem output",
    return_segmentation=["hh_type", "p", "m", "tp"]
)

HBAttr = tem.HBAttractionModel(
    trip_rates_paths={
        1: r"T:\ThomasPrince\TEM Input\comparison\02_HBAttraction\input\trip_rates_p1.hdf",
        2: r"T:\ThomasPrince\TEM Input\comparison\02_HBAttraction\input\trip_rates_p2.hdf",
        3: r"T:\ThomasPrince\TEM Input\comparison\02_HBAttraction\input\trip_rates_p3.hdf",
        4: r"T:\ThomasPrince\TEM Input\comparison\02_HBAttraction\input\trip_rates_p4.hdf",
        5: r"T:\ThomasPrince\TEM Input\comparison\02_HBAttraction\input\trip_rates_p5.hdf",
        6: r"T:\ThomasPrince\TEM Input\comparison\02_HBAttraction\input\trip_rates_p6.hdf",
        7: r"T:\ThomasPrince\TEM Input\comparison\02_HBAttraction\input\trip_rates_p7.hdf",
        8: r"T:\ThomasPrince\TEM Input\comparison\02_HBAttraction\input\trip_rates_p8.hdf"
    },
    balance_production=True,
    emp_landuse_paths = {2023: r"F:\Working\Land-Use\OUTPUTS_base_employment_bres_2022_approach_a_weighting_3\02_Final Outputs\Output E6.hdf"},
    hh_landuse_dirs = {2023: r"F:\Deliverables\Land-Use\241220_Populationv2\02_Final Outputs"},
    hh_landuse_prefix = "Output P13.3",
    mode_time_splits_path=r"T:\ThomasPrince\TEM Input\comparison\02_HBAttraction\input\mode_time_split_attraction_hb_fr_reg.hdf"
)

HBAttr.run()