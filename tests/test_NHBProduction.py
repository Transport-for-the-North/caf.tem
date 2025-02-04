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
class TestNHBProductionModel(ct.NHBProductionModel):
    def test_run(self):
        a.run(True,True,True)

if __name__ == "__main__":
    #TestProductionModels.test_HBProduction(None)
    a = TestNHBProductionModel(
            tem_segs=ct.inputs.TEMSegmentations,
            hb_attraction_paths={2023: r"C:\Users\Spiral\Documents\Thomas Prince\NTS Processing DVec\outputs_is\attractions\hb\mode_time_splits\hb_mode_time_split_attraction_hb_fr.dvec"}# Dict[int, os.PathLike],
            trip_rates_path=str,
            time_splits_path=str,
            export_home=str,
            constraint_paths=Dict[int, os.PathLike] = None,
            process_count=int = 1,
        )
    a.test_run()