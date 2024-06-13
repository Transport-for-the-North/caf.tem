# -*- coding: utf-8 -*-
"""
Created on: 30/05/2024
Updated on:

Original author: Ben Taylor
Last update made by:
Other updates made by:

File purpose:

"""
# Built-Ins
import os

# Third Party
import caf.core

# Local Imports
# pylint: disable=import-error,wrong-import-position
# Local imports here
# pylint: enable=import-error,wrong-import-position

# # # CONSTANTS # # #

# # # CLASSES # # #

# # # FUNCTIONS # # #


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
        raise IOError(
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
        raise IOError("Cannot find a path to: %s" % str(file_path))


def lu_to_tt(dvec: caf.core.DVector):
    lu_seg = caf.core.SegmentationInput(
        enum_segments=[
            "ns_sec",
            "g",
            "adults",
            "accom_h",
            "pop_emp",
            "soc",
            "children",
            "car_availability",
            "pop_econ",
            "age_9",
        ],
        naming_order=[
            "age_9",
            "g",
            "pop_econ",
            "soc",
            "accom_h",
            "ns_sec",
            "pop_emp",
            "adults",
            "children",
            "car_availability",
        ],
    )
    lu_seg = caf.core.Segmentation(lu_seg)
    if dvec.segmentation != lu_seg:
        raise ValueError("Input segmentation is not as expected.")

    out_dvec = dvec.aggregate(
        ["age_9", "g", "ns_sec", "soc", "pop_emp", "adults", "car_availability"]
    )
    out_dvec = (
        out_dvec.trans_seg_from_lookup("ag_g")
        .trans_seg_from_lookup("apopemp_aws", drop_old=True)
        .trans_seg_from_lookup("caradult_hhtype", drop_old=True)
    )
    return out_dvec
