# -*- coding: utf-8 -*-
"""Tests for the HBProduction module"""
# Built-Ins
from typing import Any

# Third Party
import pytest
from pathlib import Path
import caf.base as cb
import caf.tem as ct
import caf.toolkit as ctk
import caf.space as cs

# Local Imports
# pylint: disable=import-error,wrong-import-position

# pylint: enable=import-error,wrong-import-position

# # # CONSTANTS # # #

dvec_fldr = Path(r"C:\Users\Spiral\Documents\Thomas Prince\(normitsefs) Transfer\TP_20250128-copy\tem_inputs")
dvec1 = cb.DVector.load(dvec_fldr /"hb_trip_rates_production_dvector.dvec")
dvec2 = cb.DVector.load(dvec_fldr / "pop_2023.dvec")
dvec3 = cb.DVector.load(dvec_fldr / "hb_mode_time_split_production_hb_to.dvec")
dvec4 = cb.DVector.load(dvec_fldr / "hb_mode_time_split_production_hb_fr.dvec")

# # # FIXTURES # # #


# # # TESTS # # #
class TestProductionModels:
    def test_HBProduction(self):
        a = ct.HBProductionModel(
            population_paths={2023: dvec_fldr / "pop_2023.dvec"},
            trip_rates_path=dvec_fldr / "hb_trip_rates_production_dvector.dvec",
            mode_time_splits_path=dvec_fldr / "hb_mode_time_split_production_hb_to.dvec",
            export_home=dvec_fldr / "HBProductionTest2",
            return_segmentation=dvec1.segmentation,
            model_zoning=dvec1.zoning_system,
            process_count=1
        )

        a.run(True,True,True)  

if __name__ == "__main__":
    TestProductionModels.test_HBProduction(None)
