# -*- coding: utf-8 -*-
"""
Created on: 30/05/2024
Updated on:

Original author: Ben Taylor
Last update made by:
Other updates made by:

File purpose:

"""
from __future__ import annotations

# Built-Ins
import os
import pathlib
import warnings

# Third Party
import caf.base as cb
import pandas as pd
import math


# Local Imports
# pylint: disable=import-error,wrong-import-position
# Local imports here
# from inputs import TT
# pylint: enable=import-error,wrong-import-position

# # # CONSTANTS # # #
TT = cb.SegmentationInput(
    enum_segments=["adult_nssec", "gender_3", "ns_sec", "soc", "aws", "hh_type"],
    naming_order=["adult_nssec", "gender_3", "ns_sec", "soc", "aws", "hh_type"],
)
TT = cb.SegmentationInput(
    enum_segments=["adult_nssec", "gender_3", "ns_sec", "soc", "aws", "hh_type"],
    naming_order=["adult_nssec", "gender_3", "ns_sec", "soc", "aws", "hh_type"],
)
GOR = ("EM", "EoE", "Lon", "NE", "NW", "SE", "SW", "Wales", "WM", "YH", "Scotland")
SEG_POP = ["gender_3", "aws", "hh_type", "soc", "ns_sec", "adult_nssec"]
SEG_EMP = ["soc", "sic_1_digit", "sic_2_digit"]
SEG_HH = ["car_availability"]
TT_POP = cb.SegmentationInput(enum_segments=SEG_POP, naming_order=SEG_POP)
TT_EMP = cb.SegmentationInput(enum_segments=SEG_EMP, naming_order=SEG_EMP)
TT_HH = cb.SegmentationInput(enum_segments=SEG_HH, naming_order=SEG_HH)

LAD_REPORT_SEG: cb.SegmentationInput = cb.SegmentationInput(
        enum_segments=["p", "m", "tp"],
        naming_order=["p", "m", "tp"],
        subsets={"tp": [1, 2, 3, 4, 5, 6]},
    )

sic_to_ecode = {
    1: [],  # commuting
    2: [],  # e.bussiness
    3: [85],  # education
    4: [46, 47],  # Shopping: retail
    5: [86, 64, 65, 66, 68, 69, 75, 77, 79, 80, 95, 96, 56],
    6: [90, 91, 92, 93, 94],  # Social
    7: [],  # visit friend
    8: [55, 2, 3],
}


# # # CLASSES # # #

# # # FUNCTIONS # # #

def write_reports(dvec: cb.DVector, report_path, year: int) -> None:
    """
    - Calls the write_sector_reports() function on a DVector.
    - Writes reports given the report path to output to.
    """
    dvec.write_sector_reports(
                     segment_totals_path=report_path.segment_total[year],
                     ca_sector_path=report_path.ca_sector[year],
                     ie_sector_path=report_path.ie_sector[year],
                     lad_report_path=report_path.lad_report[year],
                     lad_report_seg=cb.Segmentation(LAD_REPORT_SEG),
                 )
    
    return None


def file_exists(file_path: os.PathLike) -> bool:
    """
    Checks if a file exists at the given path.

    Parameters
    ----------
    file_path:
        path to the file to check.

    Returns
    -------
    file_exists:
        True if a file exists, else False
    """
    if not os.path.exists(file_path):
        return False

    if not os.path.isfile(file_path):
        raise IsADirectoryError(
            "The given path exists, but does not point to a file. "
            "Given path: %s" % str(file_path)
        )

    return True


def check_file_exists(
    file_path: os.PathLike,
) -> None:
    """
    Checks if a file exists at the given path. Throws an error if not.

    Parameters
    ----------
    file_path:
        path to the file to check.

    find_similar:
        Whether to look for files with the same name, but a different file
        type extension. If True, this will call find_filename() using the
        default alternate file types: ['.pbz2', '.csv']

    Returns
    -------
    None
    """
    if not file_exists(file_path):
        raise FileNotFoundError("Cannot find a path to: %s" % str(file_path))



#if __name__ == "__main__":
#    normits = cb.ZoningSystem.get_zoning("normits")
#    pop = read_pop_lu(
#        pathlib.Path(r"F:\Working\Land-Use\OUTPUTS_full run_final"),
#        "Output P11_{}.hdf",
#        out_zoning=normits,
#    )
#    pop_vector = pop.data.sum().T
#    pop_vector.to_csv(r"C:\Users\IsaacScott\projects\tem\pop_2021.csv")
#    pop.save(
#        r"F:\Working\Land-Use\OUTPUTS_revised exclusions age status_seeded\final_combined.hdf"
#    )
#    print("debugging")
# TODO check if this function is what creates the input to HB Production i.e. pop_2023.dvec


