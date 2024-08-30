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
import pathlib

import caf.core
# Third Party
import caf.core as cc
import pandas as pd


# Local Imports
# pylint: disable=import-error,wrong-import-position
# Local imports here
# from inputs import TT
# pylint: enable=import-error,wrong-import-position

# # # CONSTANTS # # #
TT = cc.SegmentationInput(enum_segments=["adult_nssec", "gender_3", "ns_sec", "soc", "aws", "hh_type"],
                          naming_order=["adult_nssec", "gender_3", "ns_sec", "soc", "aws", "hh_type"])
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


def lu_to_tt(dvec: cc.DVector):
    out_dvec = dvec.aggregate(
        ["age_9", "g", "ns_sec", "soc", "pop_emp", "adults", "adult_nssec"]
    )
    out_dvec = out_dvec.trans_seg_from_lookup("ag_g")
    out_dvec = out_dvec.trans_seg_from_lookup("apopemp_aws", drop_old=True)

    return out_dvec.aggregate(["adult_nssec", "gender_3", "ns_sec", "soc", "aws"]).add_segments(['hh_type'])


def read_pop_lu(dir: pathlib.Path,
                file_name: str,
                out_zoning: caf.core.ZoningSystem | None = None,
                geographies=('EM', 'EoE', 'Lon', 'NE', 'NW', 'SE', 'SW', 'Wales', 'WM', 'YH', 'Scotland')):
    dvecs = []
    for region in geographies:
        dvec = cc.DVector.load(dir / file_name.format(region))
        dvec_tt = lu_to_tt(dvec)
        dvecs.append(dvec_tt)
    overall_data = pd.concat([d.data for d in dvecs], axis=1)
    zoning = cc.ZoningSystem.get_zoning('lsoa_2021')
    overall_data.rename(columns=zoning.name_to_id, inplace=True)
    dvec = cc.DVector(import_data=overall_data,
                            segmentation=cc.Segmentation(TT),
                            zoning_system=zoning)
    trans = None
    if out_zoning is not None:
        trans = dvec.zoning_system.translate(out_zoning)
        dvec = dvec.translate_zoning(
            out_zoning,
            trans_vector=trans
        )
    return dvec, trans

if __name__ == "__main__":
    normits = cc.ZoningSystem.get_zoning('normits')
    pop = read_pop_lu(pathlib.Path(r"F:\Working\Land-Use\OUTPUTS_full run_final"),
                "Output P11_{}.hdf",
                      out_zoning=normits)
    pop_vector = pop.data.sum().T
    pop_vector.to_csv(r"C:\Users\IsaacScott\projects\tem\pop_2021.csv")
    pop.save(r"F:\Working\Land-Use\OUTPUTS_revised exclusions age status_seeded\final_combined.hdf")
    print('debugging')

