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

# Built-in
import math
import os
import pathlib
import warnings
from typing import Union, Tuple
import glob

# Third-party
import pandas as pd

# Local
import caf.base as cb



# Local Imports
# pylint: disable=import-error,wrong-import-position
# Local imports here
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

# # # CLASSES # # #


# # # FUNCTIONS # # #
def lu_to_tt(dvec: cb.DVector):
    """
    Args:
        dvec (cb.DVector): The input DVector containing land-use-based segmentation.

    Returns:
        cb.DVector: A new DVector segmented and aggregated for travel-type modelling.

    """
    out_dvec = dvec.aggregate(
        ["age_9", "g", "ns_sec", "soc", "pop_emp", "adults", "adult_nssec", "car_availability"]
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
            f"The given path exists, but does not point to a file. Given path: {file_path}"
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
        raise FileNotFoundError(f"Cannot find a path to: {file_path}")


def read_pop_lu(
    dir_: pathlib.Path,
    file_name: str,
    out_zoning: cb.ZoningSystem | None = None,
    geographies=("EM", "EoE", "Lon", "NE", "NW", "SE", "SW", "Wales", "WM", "YH", "Scotland"),
):
    """
    Reads population-level data from multiple regional files, converts them to TT-format DVector objects,
    and optionally translates the output to a specified zoning system.

    Parameters:
    ----------
    dir_ : pathlib.Path
        The directory path where the input population files are stored.

    file_name : str
        A string template for the file name, which should include a placeholder for the region (e.g., "population_{}.csv").

    out_zoning : cb.ZoningSystem, optional
        The desired output zoning system to which the aggregated DVector will be translated. If None, no translation is performed.

    geographies : tuple of str, optional
        The list of region codes to iterate over. Each region should correspond to a valid file when substituted into the file_name template.

    Returns:
    -------
    dvec : cb.DVector
        A combined and optionally translated DVector containing TT-format population data.

    trans : pd.Series or None
        The translation vector used for zoning conversion, or None if no translation was performed.
    """
    dvecs = []
    for region in geographies:
        dvec = cb.DVector.load(pathlib.Path(dir_) / file_name.format(region))
        dvec_tt = lu_to_tt(dvec)
        dvecs.append(dvec_tt)
    overall_data = pd.concat([d.data for d in dvecs], axis=1)
    zoning = cb.ZoningSystem.get_zoning("lsoa_2021")
    overall_data.rename(columns=zoning.name_to_id, inplace=True)
    dvec = cb.DVector(
        import_data=overall_data, segmentation=cb.Segmentation(TT), zoning_system=zoning
    )
    trans = None
    if out_zoning is not None:
        trans = dvec.zoning_system.translate(out_zoning)
        dvec = dvec.translate_zoning(out_zoning, trans_vector=trans)
    return dvec, trans


def read_hh_lu(
    dir_: pathlib.Path | str, file_name: str, out_seg: cb.Segmentation = SEG_HH, geographies=GOR
):
    """
    Reads and aggregates household-level look-up data from multiple regional files,
    combines them into a single DVector, and returns the result.

    Parameters:
    ----------
    dir_ : pathlib.Path or str
        The directory path where the household data files are located.

    file_name : str
        A string template for the file name, which must include a placeholder for region names
        (e.g., "households_{}.csv").

    out_seg : cb.Segmentation, optional
        The segmentation to which the input data should be aggregated. Defaults to SEG_HH.

    geographies : iterable of str, optional
        The list of region codes to iterate over. Each region should correspond to a file that
        can be resolved by applying it to the file_name template.

    Returns:
    -------
    dvec : cb.DVector
        A combined DVector object containing aggregated household data in the specified segmentation and
        using the "lsoa_2021" zoning system.
        """
    dvecs = []
    for region in geographies:
        dvec = cb.DVector.load(pathlib.Path(dir_) / file_name.format(region))
        dvec = dvec.aggregate(out_seg)
        print(f"    {region:8}: lu {dvec.data.sum(axis=1).sum():.2f}")
        dvecs.append(dvec)
    overall_data = pd.concat([d.data for d in dvecs], axis=1)
    zoning = cb.ZoningSystem.get_zoning("lsoa_2021")
    overall_data.rename(columns=zoning.name_to_id, inplace=True)
    dvec = cb.DVector(import_data=overall_data, segmentation=out_seg, zoning_system=zoning)
    return dvec


def read_lu_emp(dir_: pathlib.Path | str, file_name: str):
    """
    Load and process employment land use data from disk.

    Parameters
    ----------
    dir_ : pathlib.Path or str
        Directory path where the employment data file is located.
    file_name : str
        Name of the file to load.

    Returns
    -------
    cb.DVector
        A DVector object aggregated by employment categories (SEG_EMP),
        with zoning system set to "lsoa_2021" and segmentation updated to TT_EMP.

    """

    dvec = cb.DVector.load(pathlib.Path(dir_) / file_name)
    dvec = dvec.aggregate(SEG_EMP).data
    out = pd.DataFrame(dvec.groupby(level="soc").sum().sum(axis=1)).rename(columns={0: "emp"})
    out["prop"] = out["emp"].div(out["emp"].sum()) * 100
    print(f'    GB: lu {out["emp"].sum():.2f}')
    print(out)

    zoning = cb.ZoningSystem.get_zoning("lsoa_2021")
    dvec.rename(columns=zoning.name_to_id, inplace=True)
    dvec = cb.DVector(
        import_data=dvec, segmentation=cb.Segmentation(TT_EMP), zoning_system=zoning
    )
    return dvec


def return_home(pa: cb.DVector, phi_factors: cb.DVector, mode_split: cb.DVector | None = None):
    """
    Computes return trips from outbound home-based trips using phi factors and optional mode split.

    Args:
        pa (cb.DVector): The outbound home-based production-attraction trip matrix.
        phi_factors (cb.DVector): Factors used to convert outbound trips into return trips.
        mode_split (cb.DVector, optional): Mode share factors for further disaggregation by mode.

    Returns:
        cb.DVector: A new DVector representing return trips segmented according to `pa`.
    """
    pa_seg = pa.segmentation.naming_order
    temp_seg = list(map(lambda x: x + "_to" if x in ["p", "tp"] else x, pa_seg))
    hb_to = (pa * phi_factors).aggregate(temp_seg)
    hb_to_data = (
        hb_to.data.reset_index().rename(columns={"p_to": "p", "tp_to": "tp"}).set_index(pa_seg)
    )
    hb_to = cb.DVector(
        import_data=hb_to_data, segmentation=pa_seg, zoning_system=pa.zoning_system
    )
    if mode_split is not None:
        if "m" in pa_seg:
            pa_seg.remove("m")
            hb_to = hb_to.aggregate(pa_seg)
        hb_to = hb_to * mode_split
    if not math.isclose(pa.sum(), hb_to.sum()):
        warnings.warn(
            f"Return trips don't match outbound trips. Out = {pa.sum()}, return = {hb_to.sum()}"
        )

    return hb_to


def phi_to_dvec(phi_path: Union[pathlib.Path,str], output_fld: Union[pathlib.Path,str]) -> None:
    """
    Reads phi factor CSV files from the given directory, reshapes them, and saves them as .dvec files
    suitable for use with cb.DVector.

    Parameters:
    ----------
    phi_path : pathlib.Path
        Directory containing phi factor CSV files (pattern: 'phi_factors*_reg.csv').

    output_fld : pathlib.Path
        Output directory where reshaped .dvec files will be saved.

    Returns:
    -------
    None
    """

    if not isinstance(phi_path, pathlib.Path):
        phi_path = pathlib.Path(phi_path)

    if not isinstance(output_fld, pathlib.Path):
        output_fld = pathlib.Path(output_fld)

    pattern = str(phi_path / "phi_factors*_reg.csv")
    input_files = glob.glob(pattern)

    if not input_files:
        print(f"No matching files found in {phi_path}")
        return

    output_fld.mkdir(parents=True, exist_ok=True)

    for file_path in input_files:
        df = pd.read_csv(file_path)

        df_reshaped = df.pivot_table(
            index=['purpose.fr', 'purpose', 'period.fr', 'period'],
            columns='tfn_at',
            values='phi',
            aggfunc='sum'
        )

        df_reshaped.index.names = ['p', 'p_return', 'tp', 'tp_return']

        new_filename = pathlib.Path(file_path).stem.replace(".csv", ".dvec")
        output_path = output_fld / new_filename

        seg_inputs = cb.SegmentationInput(
            enum_segments=["p", "p_return", "tp", "tp_return"],
            naming_order=["p", "p_return", "tp", "tp_return"]
        )

        segmentation = cb.Segmentation(seg_inputs)
        zoning_system = cb.ZoningSystem.get_zoning('tfn_at')

        dvec = cb.DVector(import_data=df_reshaped, segmentation=segmentation, zoning_system=zoning_system)
        dvec.save(output_path)

        print(f"Saved: {output_path}")


def create_mts_production_return_home_dvec(
    csv_path: Union[str, pathlib.Path],
    zoning_name: str = 'tfn_at',
    mts_only_by_mode: bool = True
) -> cb.DVector:
    """
    Reads mode-time split production data from a CSV, calculates proportions or uses precomputed 'rho',
    reshapes the data, and converts it into a cb.DVector.

    Parameters
    ----------
    csv_path : str or Path
        Path to the input CSV file containing mode-time split production data.

    zoning_name : str, default='tfn_at'
        Name of the zoning system to use when constructing the DVector.

    mts_only_by_mode : bool, default=True
        If True, compute proportions from 'trips.est', because tp_return is a segment of phi factors.
        If False, use 'rho' column  use it directly, because tp_return is not a segment of phi factors.

    Returns
    -------
    cb.DVector
        A DVector containing reshaped mode split proportions for production trips.
    """
    csv_path = pathlib.Path(csv_path)
    df = pd.read_csv(csv_path)

    if mts_only_by_mode:
        # Step 1: Compute trip proportions within each group
        df['total_trips'] = df.groupby(['tfn_at', 'hh_type', 'purpose', 'period'])['trips.est'].transform('sum')
        df['rho'] = df['trips.est'] / df['total_trips']

        # Step 2: Aggregate proportions by mode
        df = df.groupby(['tfn_at', 'hh_type', 'purpose', 'period', 'mode'])['rho'].sum().reset_index()


    # Step 3:  Directly reshape precomputed 'rho'
    by_mode_reshaped = df.pivot_table(
        index=['hh_type', 'purpose', 'period', 'mode'],
        columns='tfn_at',
        values='rho',
        aggfunc='sum'
    )

    # Step 4: Rename index levels to match segmentation convention
    by_mode_reshaped.index.names = ['hh_type', 'p_return', 'tp_return', 'm']

    # Step 5: Construct segmentation and DVector
    seg_input = cb.SegmentationInput(
        enum_segments=['hh_type', 'p_return', 'tp_return', 'm'],
        naming_order=['hh_type', 'p_return', 'tp_return', 'm']
    )
    segmentation = cb.Segmentation(seg_input)
    zoning = cb.ZoningSystem.get_zoning(zoning_name)

    dvec = cb.DVector(
        import_data=by_mode_reshaped,
        segmentation=segmentation,
        zoning_system=zoning
    )

    return dvec

def create_mts_attraction_return_home_dvec(
    csv_path: Union[str, pathlib.Path],
    zoning_name: str = 'tfn_at',
    mts_only_by_mode: bool = True
) -> cb.DVector:
    """
    Reads mode-time split attraction data from a CSV file, calculates mode proportions,
    reshapes the data, and returns a cb.DVector.

    Parameters
    ----------
    csv_path : str or Path
        Path to the input CSV containing attraction trip records.

    zoning_name : str, default='tfn_at'
        The zoning system name used to create the cb.ZoningSystem object.

    mts_only_by_mode : bool, default=True
        If True, calculates mode proportions using only mode;
        otherwise it also take return time period also in consideration.

    Returns
    -------
    cb.DVector
        DVector containing reshaped mode split proportions for attraction trips.
    """
    csv_path = pathlib.Path(csv_path)
    df = pd.read_csv(csv_path)

    if mts_only_by_mode:
        # Step 1: Compute trip proportions for each segment group
        df['total_trips'] = df.groupby(['tfn_at', 'purpose', 'period'])['trips.est'].transform('sum')
        df['Proportion'] = df['trips.est'] / df['total_trips']

        # Step 2: Group by relevant mode-time splits and sum proportions
        df = df.groupby(['tfn_at', 'purpose', 'period', 'mode'])['Proportion'].sum().reset_index()
    else:
        # Step 1: Compute trip proportions for each segment group
        df = df.groupby(['tfn_at', 'purpose', 'mode', 'period'])['trips.est'].sum().reset_index()
        df['total_trips'] = df.groupby(['tfn_at', 'purpose'])['trips.est'].transform('sum')
        df['Proportion'] = df['trips.est'] / df['total_trips']

    # Step 3: Pivot the table into wide format
    by_mode_reshaped = df.pivot_table(
        index=['purpose', 'period', 'mode'],
        columns='tfn_at',
        values='Proportion',
        aggfunc='sum'
    )
    by_mode_reshaped.index.names = ['p_return', 'tp_return', 'm']

    # Step 4: Set segmentation and zoning
    seg_input = cb.SegmentationInput(
        enum_segments=['p_return', 'tp_return', 'm'],
        naming_order=['p_return', 'tp_return', 'm']
    )
    segmentation = cb.Segmentation(seg_input)
    zoning = cb.ZoningSystem.get_zoning(zoning_name)

    # Step 5: Create and return the DVector
    return cb.DVector(
        import_data=by_mode_reshaped,
        segmentation=segmentation,
        zoning_system=zoning
    )

def create_mts_return_home_adj_factor_dvectors(csv_path: Union[str, pathlib.Path]) -> Tuple[cb.DVector, cb.DVector]:
    """
    Reads a single CSV containing both production ('p') and attraction ('a') MTS adjustment factors,
    splits them, reshapes them into wide format, and converts each into a cb.DVector.

    Parameters
    ----------
    csv_path : str or Path
        Path to the input CSV containing adjustment factors. Must include a 'pa' column
        with values 'p' or 'a', and columns: 'purpose', 'mode', 'period', 'gor', 'adj'.

    Returns
    -------
    Tuple[cb.DVector, cb.DVector]
        A tuple containing (production_dvector, attraction_dvector).
    """
    csv_path = pathlib.Path(csv_path)
    df = pd.read_csv(csv_path)

    # Validate required columns
    required_cols = {'pa', 'purpose', 'mode', 'period', 'gor', 'adj'}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing columns in input CSV: {missing_cols}")

    # Common reshaping function
    def reshape(sub_df: pd.DataFrame) -> pd.DataFrame:
        reshaped = sub_df.pivot_table(
            index=['purpose', 'mode', 'period'],
            columns='gor',
            values='adj',
            aggfunc='sum'
        )
        reshaped.index.names = ['p_return', 'm', 'tp_return']
        return reshaped

    # Filter and reshape for production and attraction
    df_prod = df[df['pa'] == 'p']
    df_attr = df[df['pa'] == 'a']

    reshaped_prod = reshape(df_prod)
    reshaped_attr = reshape(df_attr)

    # Create segmentation object
    seg_input = cb.SegmentationInput(
        enum_segments=["p_return", "m", "tp_return"],
        naming_order=["p_return", "m", "tp_return"]
    )
    segmentation = cb.Segmentation(seg_input)
    zoning = cb.ZoningSystem.get_zoning('gor')

    # Construct DVector objects
    dvec_prod = cb.DVector(import_data=reshaped_prod, segmentation=segmentation, zoning_system=zoning)
    dvec_attr = cb.DVector(import_data=reshaped_attr, segmentation=segmentation, zoning_system=zoning)

    return dvec_prod, dvec_attr
