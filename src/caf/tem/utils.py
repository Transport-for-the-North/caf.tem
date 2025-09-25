# -*- coding: utf-8 -*-
"""
Utility functions and constants for the Trip End Model (TEM).

This module provides helper functions for data transformation, file I/O, report writing,
and DVector/segmentation operations used throughout the TEM framework.
"""

from __future__ import annotations

# Built-in
import math
import copy
import os
import pathlib
import warnings
from typing import Union, Tuple
import glob

# Third-party
import pandas as pd

# Local
import caf.base as cb
from caf.base.segments import SegmentsSuper


# Local Imports
# pylint: disable=import-error,wrong-import-position
# Local imports here
# pylint: enable=import-error,wrong-import-position

# # # CONSTANTS # # #
tt_enum = ["adult_nssec", "gender_3", "ns_sec", "soc", "aws", "hh_type"]
TT = cb.SegmentationInput(
    enum_segments=[SegmentsSuper(i) for i in tt_enum],
    naming_order=tt_enum,
)

lad_seg = ["p", "m", "tp"]
LAD_REPORT_SEG: cb.SegmentationInput = cb.SegmentationInput(
    enum_segments=[SegmentsSuper(i) for i in lad_seg],
    naming_order=lad_seg,
    subsets={"tp": [1, 2, 3, 4, 5, 6]},
)

# # # CLASSES # # #


# # # FUNCTIONS # # #
def lu_to_tt(dvec: cb.DVector) -> cb.DVector:
    """
    Convert a land-use segmented DVector to a travel-type segmented DVector.

    This function aggregates and transforms the input DVector to match the segmentation
    required for travel-type modelling. It checks for conservation of totals and warns
    if the sum changes.

    Parameters
    ----------
    dvec : cb.DVector
        The input DVector containing land-use-based segmentation.

    Returns
    -------
    cb.DVector
        A new DVector segmented and aggregated for travel-type modelling.

    """
    out_dvec = dvec.aggregate(
        [
            "age_9",
            "g",
            "ns_sec",
            "soc",
            "pop_emp",
            "adults",
            "adult_nssec",
            "car_availability",
        ]
    )
    out_dvec = out_dvec.trans_seg_from_lookup("ag_g")
    out_dvec = out_dvec.trans_seg_from_lookup("apopemp_aws", drop_old=True)

    out_dvec = out_dvec.add_segments(["hh_type"]).aggregate(
        ["adult_nssec", "gender_3", "ns_sec", "soc", "aws", "hh_type"]
    )

    if not math.isclose(out_dvec.sum(), dvec.sum()):
        warnings.warn(
            f"The total has changed during conversion. Sum before = {dvec.sum()}, "
            f"sum after = {out_dvec.sum()}."
        )

    return out_dvec


def write_reports(dvec: cb.DVector, report_path, year: int) -> None:
    """
    Write sector and LAD reports for a DVector.

    Calls the DVector's write_sector_reports() method to generate and save reports
    for the specified year and report path.

    Parameters
    ----------
    dvec : cb.DVector
        The DVector to report on.
    report_path : object
        Object containing paths for various report types (must have .segment_total, .ca_sector,
        .ie_sector, .lad_report attributes, each indexed by year).
    year : int
        The year for which to write reports.

    Returns
    -------
    None
    """
    dvec.write_sector_reports(
        segment_totals_path=report_path.segment_total[year],
        ca_sector_path=report_path.ca_sector[year],
        ie_sector_path=report_path.ie_sector[year],
        lad_report_path=report_path.lad_report[year],
        lad_report_seg=cb.Segmentation(LAD_REPORT_SEG),
    )


def file_exists(file_path: os.PathLike) -> bool:
    """
    Check if a file exists at the given path.

    Parameters
    ----------
    file_path : os.PathLike
        Path to the file to check.

    Returns
    -------
    bool
        True if a file exists, else False.

    Raises
    ------
    IsADirectoryError
        If the path exists but is a directory, not a file.
    """
    if not os.path.exists(file_path):
        return False

    if not os.path.isfile(file_path):
        raise IsADirectoryError(
            f"The given path exists, but does not point to a file. Given path: {file_path}"
        )

    return True


def filter_segments(custom_seg_list, df) -> list:
    """
    Filter segment objects by keeping only values present in a DataFrame.

    Parameters
    ----------
    custom_seg_list : list
        List of segment objects (each having .name and .values attributes).
    df : pd.DataFrame
        DataFrame to filter categories against.

    Returns
    -------
    list
        List of filtered segment copies.
    """
    filtered_seg_list = []
    for seg in custom_seg_list:
        seg_copy = copy.deepcopy(seg)
        col_name = seg_copy.name
        seg_unique = set(df[col_name].unique())
        seg_copy.values = {i: j for i, j in seg_copy.values.items() if i in seg_unique}
        filtered_seg_list.append(seg_copy)

    return filtered_seg_list
